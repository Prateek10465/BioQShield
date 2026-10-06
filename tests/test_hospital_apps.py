"""The two hospital apps, in-process: roles, records at rest, the signed protocol surface,
one-time keys, and what happens when the link is down. No network, no real QKD session."""
import json
import os
import sqlite3

import pytest
from fastapi.testclient import TestClient

from nodes import alice as alice_mod, bob as bob_mod
from nodes.common import load_config, seal
from nodes.secure_message import seal_message
from nodes.store import Store
from nodes.vault import Vault

PASSWORDS = {"admin": "admin-test-password", "dr.rao": "clinician-test-pw", "auditor": "auditor-test-pw"}
MARKER = "ZEBRA-PLAINTEXT-MARKER-7731"


@pytest.fixture
def env(tmp_path, monkeypatch):
    for k, v in {
        "QKD_DATA_DIR": str(tmp_path), "QKD_AUTH_KEY": "test-secret-" + "x" * 32,
        "QKD_ADMIN_PASSWORD": PASSWORDS["admin"], "QKD_DEMO_USERS": "1",
        "QKD_CLINICIAN_PASSWORD": PASSWORDS["dr.rao"], "QKD_AUDITOR_PASSWORD": PASSWORDS["auditor"],
        "QKD_CHANNEL_URL": "http://127.0.0.1:9",  # nothing listens here: the link is down
        "QKD_QUBITS": "2048",
    }.items():
        monkeypatch.setenv(k, v)
    return tmp_path


class Node:
    def __init__(self, role, module):
        self.cfg = load_config(role)
        self.app = module.create_app(self.cfg)
        self.http = TestClient(self.app)
        self.db = self.cfg.data_dir / f"{role}.db"
        self.store = Store(self.db, Vault(self.cfg.master_key))
        self.tokens: dict[str, dict] = {}

    def as_(self, user: str) -> dict:
        if user not in self.tokens:
            r = self.http.post("/api/auth/login", json={"username": user, "password": PASSWORDS[user]})
            assert r.status_code == 200, r.text
            self.tokens[user] = {"Authorization": "Bearer " + r.json()["token"]}
        return self.tokens[user]

    def audit_events(self) -> list[str]:
        r = self.http.get("/api/audit?limit=500", headers=self.as_("admin"))
        return [e["event"] for e in r.json()["entries"]]

    def raw(self) -> bytes:
        return self.db.read_bytes() + b"".join(p.read_bytes() for p in self.db.parent.glob(self.db.name + "-*"))


@pytest.fixture
def alice(env):
    return Node("alice", alice_mod)


@pytest.fixture
def bob(env):
    return Node("bob", bob_mod)


def signed(node: Node, kind: str, payload: dict, sid="s-test", seq=1) -> dict:
    kid, key = node.store.latest_auth_key()
    return seal(kid, key, sid, seq, kind, payload)


# ----------------------------------------------------------------------------- access control
@pytest.mark.parametrize("method,path", [
    ("get", "/api/records"), ("get", "/api/keys"), ("get", "/api/audit"), ("get", "/api/users"),
    ("get", "/api/sessions"), ("get", "/api/link"), ("post", "/api/keys/rotate"), ("post", "/api/keys/refill"),
])
def test_alice_needs_a_login_for_everything(alice, method, path):
    assert getattr(alice.http, method)(path).status_code == 401
    assert getattr(alice.http, method)(path, headers={"Authorization": "Bearer nonsense"}).status_code == 401


def test_roles_are_separate(alice):
    c, a, adm = alice.as_("dr.rao"), alice.as_("auditor"), alice.as_("admin")
    get, post = alice.http.get, alice.http.post
    # clinicians do clinical work and nothing administrative
    assert get("/api/records", headers=c).status_code == 200
    for path in ("/api/audit", "/api/audit/verify", "/api/users"):
        assert get(path, headers=c).status_code == 403
    assert post("/api/keys/rotate", headers=c).status_code == 403
    # auditors read the log and key activity but never patient records
    assert get("/api/audit", headers=a).status_code == 200
    assert get("/api/audit/verify", headers=a).status_code == 200
    assert get("/api/records", headers=a).status_code == 403
    assert post("/api/records", headers=a, json={"patient_ref": "P1", "title": "t", "body": "b"}).status_code == 403
    assert post("/api/keys/rotate", headers=a).status_code == 403
    # admins run the system but also cannot read records
    assert get("/api/users", headers=adm).status_code == 200
    assert get("/api/records", headers=adm).status_code == 403
    assert post("/api/keys/rotate", headers=adm).status_code == 200


def test_bob_inbox_is_for_clinicians_only(bob):
    assert bob.http.get("/api/inbox").status_code == 401
    assert bob.http.get("/api/inbox", headers=bob.as_("dr.rao")).status_code == 200
    assert bob.http.get("/api/inbox", headers=bob.as_("auditor")).status_code == 403
    assert bob.http.get("/api/inbox", headers=bob.as_("admin")).status_code == 403


def test_key_listing_shows_ids_but_never_key_material(alice):
    alice.store.add_keys([("k-1", "s", 0, bytes(range(32)))], 3600)
    for user in ("dr.rao", "auditor", "admin"):
        body = alice.http.get("/api/keys", headers=alice.as_(user)).text
        assert bytes(range(32)).hex() not in body and "AAECAwQFBgc" not in body
    assert "keys" not in alice.http.get("/api/keys", headers=alice.as_("dr.rao")).json()  # no per-key table for clinicians
    assert alice.http.get("/api/keys", headers=alice.as_("auditor")).json()["keys"][0]["key_id"] == "k-1"


def test_login_failures_are_throttled_and_logged(alice):
    for _ in range(5):
        assert alice.http.post("/api/auth/login", json={"username": "dr.rao", "password": "wrong-password"}).status_code == 401
    r = alice.http.post("/api/auth/login", json={"username": "dr.rao", "password": PASSWORDS["dr.rao"]})
    assert r.status_code == 429 and int(r.headers["Retry-After"]) > 0
    events = alice.audit_events()
    assert "login_failed" in events and "login_throttled" in events


def test_admin_creates_and_disables_users(alice):
    adm = alice.as_("admin")
    assert alice.http.post("/api/users", headers=adm, json={"username": "new.doc", "password": "short", "role": "clinician"}).status_code == 422
    assert alice.http.post("/api/users", headers=adm, json={"username": "new.doc", "password": "a-long-enough-pass", "role": "wizard"}).status_code == 422
    assert alice.http.post("/api/users", headers=adm, json={"username": "new.doc", "password": "a-long-enough-pass", "role": "clinician"}).status_code == 201
    assert alice.http.post("/api/users", headers=adm, json={"username": "new.doc", "password": "a-long-enough-pass", "role": "clinician"}).status_code == 409
    login = alice.http.post("/api/auth/login", json={"username": "new.doc", "password": "a-long-enough-pass"})
    token = {"Authorization": "Bearer " + login.json()["token"]}
    assert alice.http.get("/api/records", headers=token).status_code == 200
    assert alice.http.post("/api/users/new.doc/disable", headers=adm).status_code == 200
    assert alice.http.get("/api/records", headers=token).status_code == 401  # signed out immediately
    assert alice.http.post("/api/users/admin/disable", headers=adm).status_code == 400  # not yourself


def test_logout_ends_the_session(alice):
    h = alice.as_("dr.rao")
    assert alice.http.post("/api/auth/logout", headers=h).status_code == 200
    assert alice.http.get("/api/records", headers=h).status_code == 401


# ----------------------------------------------------------------------------- records
def test_records_are_validated_and_encrypted_at_rest(alice):
    h = alice.as_("dr.rao")
    bad = alice.http.post("/api/records", headers=h, json={"patient_ref": "has spaces", "title": "t", "body": "b"})
    assert bad.status_code == 422
    r = alice.http.post("/api/records", headers=h, json={"patient_ref": "P-9", "title": "Referral", "body": MARKER})
    assert r.status_code == 201 and r.json()["status"] == "draft" and "body" not in r.json()
    got = alice.http.get(f"/api/records/{r.json()['id']}", headers=h).json()
    assert got["body"] == MARKER
    assert MARKER.encode() not in alice.raw() and b"Referral" not in alice.raw()


def test_audit_log_never_contains_patient_text(alice):
    h = alice.as_("dr.rao")
    rid = alice.http.post("/api/records", headers=h, json={"patient_ref": "P-9", "title": "T", "body": MARKER}).json()["id"]
    alice.http.get(f"/api/records/{rid}", headers=h)
    assert MARKER not in alice.http.get("/api/audit?limit=500", headers=alice.as_("auditor")).text


def test_nothing_is_sent_when_the_link_is_down(alice):
    h = alice.as_("dr.rao")
    rid = alice.http.post("/api/records", headers=h, json={"patient_ref": "P-9", "title": "T", "body": MARKER}).json()["id"]
    r = alice.http.post(f"/api/records/{rid}/send", headers=h)
    assert r.status_code == 503, r.text
    assert r.json()["detail"]["code"] == "no_secure_key"
    assert alice.http.get(f"/api/records/{rid}", headers=h).json()["status"] == "draft"
    assert "transfer_blocked" in alice.audit_events()
    assert alice.http.post("/api/records/nope/send", headers=h).status_code == 404


def test_audit_api_reports_tampering_with_the_database_file(alice):
    h = alice.as_("dr.rao")
    alice.http.post("/api/records", headers=h, json={"patient_ref": "P-9", "title": "T", "body": "b"})
    assert alice.http.get("/api/audit/verify", headers=alice.as_("auditor")).json()["ok"] is True
    con = sqlite3.connect(alice.db)
    con.execute("UPDATE audit SET actor='someone.else' WHERE id=2")
    con.commit(); con.close()
    result = alice.http.get("/api/audit/verify", headers=alice.as_("auditor")).json()
    assert result["ok"] is False and result["bad_id"] == 2


# ------------------------------------------------------------------------ Bob's signed surface
def test_bob_refuses_unsigned_altered_and_replayed_messages(bob):
    assert bob.http.post("/proto/abort", json={"hello": 1}).status_code == 401
    good = signed(bob, "abort", {"reason": "test"}, sid="s-a", seq=1)
    altered = dict(good, payload={"reason": "different"})
    assert bob.http.post("/proto/abort", json=altered).status_code == 401
    assert bob.http.post("/proto/abort", json=good).status_code == 200
    assert bob.http.post("/proto/abort", json=good).status_code == 401  # the same message again
    assert bob.http.post("/proto/sift", json=good).status_code == 401   # kind in the URL must match the signed kind
    assert bob.audit_events().count("auth_failure") >= 3


def test_bob_refuses_a_stale_message(bob):
    kid, key = bob.store.latest_auth_key()
    old = seal(kid, key, "s-old", 1, "abort", {})
    body = {k: old[k] for k in ("kid", "sid", "seq", "kind", "payload")} | {"ts": old["ts"] - 3600}
    import hashlib, hmac
    from nodes.common import canonical
    body["mac"] = hmac.new(key, canonical({f: body[f] for f in ("kid", "sid", "seq", "kind", "ts", "payload")}), hashlib.sha256).hexdigest()
    assert bob.http.post("/proto/abort", json=body).status_code == 401


def deliver(bob: Node, key_id: str, key: bytes, *, record_id="rec-1", body=MARKER, sid="s-msg", seq=1, mutate=None):
    data = json.dumps({"record_id": record_id, "sent_by": "dr.rao", "patient_ref": "P-9", "title": "Referral", "body": body}).encode()
    payload = seal_message(key, key_id, data, f"record-{record_id}.json", "application/json", "")
    if mutate:
        payload = mutate(payload)
    return bob.http.post("/proto/message", json=signed(bob, "message", payload, sid=sid, seq=seq))


def test_a_record_decrypts_once_and_the_key_cannot_be_reused(bob):
    key = os.urandom(32)
    bob.store.add_keys([("kk-0", "s", 0, key)], 3600)
    assert deliver(bob, "kk-0", key).status_code == 200
    inbox = bob.http.get("/api/inbox", headers=bob.as_("dr.rao")).json()["records"]
    assert [r["title"] for r in inbox] == ["Referral"] and inbox[0]["sent_by"] == "dr.rao" and "body" not in inbox[0]
    opened = bob.http.get(f"/api/inbox/{inbox[0]['id']}", headers=bob.as_("dr.rao")).json()
    assert opened["body"] == MARKER and opened["from"] == "Hospital A"
    assert MARKER.encode() not in bob.raw()                                   # sealed at rest
    again = deliver(bob, "kk-0", key, record_id="rec-2", sid="s-msg2")        # same key, new record
    assert again.status_code == 400 and "already used" in again.text
    assert len(bob.http.get("/api/inbox", headers=bob.as_("dr.rao")).json()["records"]) == 1
    assert "record_received" in bob.audit_events() and "message_rejected" in bob.audit_events()
    assert bob.store.pool_stats()["used"] == 1


def test_a_modified_ciphertext_is_rejected_and_the_key_is_burned(bob):
    key = os.urandom(32)
    bob.store.add_keys([("kk-1", "s", 0, key)], 3600)

    def flip(p):
        ct = p["ciphertext"]
        return dict(p, ciphertext=ct[:10] + ("A" if ct[10] != "A" else "B") + ct[11:])

    r = deliver(bob, "kk-1", key, mutate=flip)
    assert r.status_code == 400 and "decryption failed" in r.text
    assert "decrypt_failed" in bob.audit_events()
    assert deliver(bob, "kk-1", key, sid="s-retry").status_code == 400  # the key is not offered again
    assert bob.http.get("/api/inbox", headers=bob.as_("dr.rao")).json()["records"] == []


def test_an_expired_or_unknown_key_is_refused(bob):
    key = os.urandom(32)
    bob.store.add_keys([("old", "s", 0, key)], -10)  # already past its lifetime
    assert deliver(bob, "old", key).status_code == 400
    assert deliver(bob, "never-existed", key, sid="s2").status_code == 400
    assert bob.http.get("/api/inbox", headers=bob.as_("dr.rao")).json()["records"] == []


def test_rotation_on_bob_wipes_the_named_keys(bob):
    keys = {f"r-{i}": os.urandom(32) for i in range(3)}
    bob.store.add_keys([(k, "s", i, v) for i, (k, v) in enumerate(keys.items())], 3600)
    r = bob.http.post("/proto/rotate", json=signed(bob, "rotate", {"key_ids": ["r-0", "r-1"]}))
    assert r.status_code == 200 and r.json()["payload"]["expired"] == 2
    assert deliver(bob, "r-0", keys["r-0"], sid="a").status_code == 400
    assert deliver(bob, "r-2", keys["r-2"], sid="b").status_code == 200


# ------------------------------------------------------------------------------ web UI and headers
@pytest.mark.parametrize("which", ["alice", "bob"])
def test_pages_and_security_headers(env, which):
    node = Node(which, alice_mod if which == "alice" else bob_mod)
    page = node.http.get("/")
    assert page.status_code == 200 and "Select your hospital" in page.text
    assert "default-src 'self'" in page.headers["content-security-policy"]
    assert page.headers["x-content-type-options"] == "nosniff" and page.headers["x-frame-options"] == "DENY"
    assert node.http.get("/portal/eve.js").status_code == 200
    assert node.http.get("/api/link-state").status_code == 200
    assert node.http.get("/api/node").json()["role"] == which
    assert node.http.get("/api/keys").headers["cache-control"] == "no-store"
    big = node.http.post("/api/auth/login", content=b"x" * 3_000_000, headers={"content-type": "application/json"})
    assert big.status_code == 413


def test_the_wrong_master_key_is_refused_at_start(env, monkeypatch):
    monkeypatch.setenv("QKD_MASTER_KEY", "11" * 32)
    Node("alice", alice_mod)                      # creates the database under this key
    Node("alice", alice_mod)                      # same key: starts fine
    monkeypatch.setenv("QKD_MASTER_KEY", "22" * 32)
    with pytest.raises(RuntimeError, match="does not match the database"):
        Node("alice", alice_mod)
    monkeypatch.setenv("QKD_MASTER_KEY", "not-hex")
    with pytest.raises(ValueError, match="64 hex"):
        Node("alice", alice_mod)
