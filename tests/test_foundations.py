import os
import sqlite3

import pytest

from nodes.accounts import THROTTLE_FAILS, TOKEN_TTL, Accounts, Throttled
from nodes.audit import AuditLog
from nodes.store import Store
from nodes.vault import Vault, VaultError


class Clock:
    def __init__(self, t=1_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


@pytest.fixture
def vault():
    return Vault(os.urandom(32))


@pytest.fixture
def store(tmp_path, vault):
    return Store(tmp_path / "node.db", vault)


def raw_db_bytes(store: Store) -> bytes:
    with sqlite3.connect(store.path) as c:
        c.execute("PRAGMA wal_checkpoint(FULL)")
    return open(store.path, "rb").read()


# ---------------------------------------------------------------- vault ----
def test_vault_roundtrip_and_binding(vault):
    blob = vault.seal(b"secret", "row:1")
    assert vault.open(blob, "row:1") == b"secret"
    with pytest.raises(VaultError):
        vault.open(blob, "row:2")  # copied into another row
    with pytest.raises(VaultError):
        Vault(os.urandom(32)).open(blob, "row:1")  # wrong master key
    with pytest.raises(VaultError):
        vault.open(blob[:-4] + "AAAA", "row:1")  # altered


# ------------------------------------------------------------------ keys ---
def test_key_material_is_encrypted_at_rest_and_zeroised_after_use(store):
    key = bytes(range(32))
    store.add_keys([("s1-0", "s1", 0, key)], ttl=100, now=0)
    assert key.hex().encode() not in raw_db_bytes(store) and key not in raw_db_bytes(store)
    got = store.reserve_key(now=1)
    assert got == ("s1-0", key)
    store.finish_key("s1-0", now=2)
    assert store.reserve_key(now=3) is None
    assert store.consume_key("s1-0", now=3) is None  # used once, never again
    assert store.pool_listing()[0]["status"] == "used"


def test_consume_is_one_shot_and_respects_expiry(store):
    store.add_keys([("a-0", "a", 0, b"\x01" * 32), ("a-1", "a", 1, b"\x02" * 32)], ttl=100, now=0)
    assert store.consume_key("a-0", now=10) == b"\x01" * 32
    assert store.consume_key("a-0", now=11) is None
    assert store.consume_key("a-1", now=101) is None  # expired
    assert store.consume_key("nope", now=1) is None


def test_expiry_rotation_and_min_ttl(store):
    store.add_keys([(f"k-{i}", "k", i, bytes([i]) * 32) for i in range(4)], ttl=100, now=0)
    assert store.available_count(now=50) == 4
    assert store.reserve_key(now=50, min_ttl=60) is None  # too close to expiry for the peer's clock
    assert store.reserve_key(now=50, min_ttl=10)[0] == "k-0"
    assert store.expire_keys(["k-1"]) == ["k-1"]
    assert store.expire_keys() == ["k-2", "k-3"]  # rotate: everything still available
    assert store.pool_stats(now=50)["available"] == 0
    assert store.pool_stats(now=50)["expired"] == 3
    assert store.expire_due(now=1000) == ["k-0"]  # the reserved one times out too


def test_pool_listing_never_contains_key_material(store):
    store.add_keys([("z-0", "z", 0, b"\xaa" * 32)], ttl=100, now=0)
    dump = str(store.pool_listing())
    assert "aa" * 32 not in dump and "key_enc" not in dump


def test_auth_keys_are_sealed_and_latest_wins(store):
    store.ensure_bootstrap_auth(b"\x11" * 32)
    assert store.latest_auth_key() == ("boot", b"\x11" * 32)
    store.add_auth_key("s9", b"\x22" * 32)
    assert store.latest_auth_key() == ("s9", b"\x22" * 32)
    assert store.get_auth_key("boot") == b"\x11" * 32
    assert b"\x22" * 32 not in raw_db_bytes(store)


def test_records_are_sealed_at_rest(store):
    store.add_record("r1", "outbox", "draft", "dr.rao", {"patient_ref": "P-1", "title": "Zebra-fever-note", "body": "plain secret"})
    blob = raw_db_bytes(store)
    assert b"Zebra-fever-note" not in blob and b"plain secret" not in blob
    rec = store.get_record("r1", "outbox")
    assert rec["payload"]["body"] == "plain secret" and rec["status"] == "draft"
    store.update_record("r1", status="sent", key_id="s-0")
    assert store.get_record("r1", "outbox")["status"] == "sent"
    assert store.get_record("r1", "inbox") is None


# ----------------------------------------------------------------- audit ---
def test_audit_chain_detects_edits_deletes_and_truncation(store, vault):
    log = AuditLog(store, vault, "alice")
    assert log.verify()["ok"] and log.verify()["checked"] == 0
    for i in range(6):
        log.record("dr.rao", "record_created", record=f"r{i}")
    assert log.verify() == {"ok": True, "checked": 6, "bad_id": None, "problem": None}
    assert [e["id"] for e in log.entries(3)] == [6, 5, 4]

    def with_db(sql, *args):
        with sqlite3.connect(store.path) as c:
            c.execute(sql, args)

    with_db("UPDATE audit SET detail=? WHERE id=3", '{"record":"forged"}')
    bad = log.verify()
    assert not bad["ok"] and bad["bad_id"] == 3 and "modified" in bad["problem"]
    with_db("UPDATE audit SET detail=? WHERE id=3", '{"record":"r2"}')
    assert log.verify()["ok"]

    with_db("DELETE FROM audit WHERE id=4")
    assert not log.verify()["ok"]


def test_audit_detects_truncation_and_wrong_key(tmp_path):
    v = Vault(os.urandom(32))
    s = Store(tmp_path / "t.db", v)
    log = AuditLog(s, v, "bob")
    for i in range(3):
        log.record("system", "evt", i=i)
    with sqlite3.connect(s.path) as c:
        c.execute("DELETE FROM audit WHERE id=3")
    bad = log.verify()
    assert not bad["ok"] and "end of the log" in bad["problem"]
    # Someone with the database but not the master key cannot rebuild a valid chain.
    assert not AuditLog(s, Vault(os.urandom(32)), "bob").verify()["ok"]


def test_audit_chain_is_per_node(store, vault):
    a, b = AuditLog(store, vault, "alice"), AuditLog(store, vault, "bob")
    a.record("x", "e")
    assert a.verify()["ok"] and not b.verify()["ok"]  # different genesis


# -------------------------------------------------------------- accounts ---
def test_login_roles_tokens_and_disable(store):
    clock = Clock()
    acc = Accounts(store, now=clock)
    assert acc.create_user("dr.rao", "correct-horse-battery", "clinician")
    assert not acc.create_user("dr.rao", "another-long-password", "admin")  # already exists
    with pytest.raises(ValueError):
        acc.create_user("x", "short", "clinician")
    with pytest.raises(ValueError):
        acc.create_user("x", "long-enough-password", "superuser")

    assert acc.authenticate("dr.rao", "wrong-password-here") is None
    assert acc.authenticate("ghost", "whatever-password") is None
    user = acc.authenticate("dr.rao", "correct-horse-battery")
    assert user.role == "clinician"

    token, expires = acc.issue_token(user)
    assert expires == clock.t + TOKEN_TTL
    assert acc.resolve(token).username == "dr.rao"
    assert token not in raw_db_bytes(store).decode("latin1")  # only its hash is stored
    clock.t += TOKEN_TTL + 1
    assert acc.resolve(token) is None  # expired

    clock.t = 1_000_000.0
    token2, _ = acc.issue_token(user)
    store.set_user_disabled("dr.rao", True)
    assert acc.resolve(token2) is None
    assert acc.authenticate("dr.rao", "correct-horse-battery") is None


def test_logout_revokes_and_login_is_throttled(store):
    clock = Clock()
    acc = Accounts(store, now=clock)
    acc.create_user("u", "right-password-123", "auditor")
    user = acc.authenticate("u", "right-password-123")
    token, _ = acc.issue_token(user)
    acc.revoke(token)
    assert acc.resolve(token) is None

    for _ in range(THROTTLE_FAILS):
        assert acc.authenticate("u", "nope-nope-nope") is None
    with pytest.raises(Throttled) as e:
        acc.authenticate("u", "right-password-123")  # even the right password is refused while locked
    assert e.value.retry_after > 0
    clock.t += 301
    assert acc.authenticate("u", "right-password-123") is not None


def test_seed_generates_random_admin_when_nothing_configured(store):
    logged = []
    acc = Accounts(store)
    acc.seed("", False, "", "", "Hospital A", log=logged.append)
    assert store.get_user("admin") and "Generated admin password" in logged[0]
    pw = logged[0].rsplit(": ", 1)[1]
    assert acc.authenticate("admin", pw).role == "admin"
    acc.seed("", False, "", "", "Hospital A", log=logged.append)  # restart: nothing new, nothing printed
    assert len(logged) == 1


def test_seed_demo_users(store):
    acc = Accounts(store)
    acc.seed("admin-pass-123", True, "clin-pass-123", "audit-pass-123", "Hospital B")
    assert {u["username"]: u["role"] for u in store.list_users()} == {
        "admin": "admin", "dr.rao": "clinician", "auditor": "auditor"}
