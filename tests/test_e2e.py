"""End to end, with real processes and real HTTP: link service, Hospital A, Hospital B (and a
stub key-management server for the ETSI mode). These are the tests that show the system works
as a system, not just as parts. They take about a minute; run alone with `pytest tests/test_e2e.py`.
"""
import time

import httpx
import pytest

from scripts.stack import DEMO, Stack

pytestmark = pytest.mark.e2e
T = 90  # seconds: a full BB84 session takes a few seconds


def login(base: str, user: str) -> dict:
    r = httpx.post(base + "/api/auth/login", json={"username": user, "password": DEMO[user]}, timeout=20)
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


class Rig:
    """A running stack plus logged-in sessions on both hospitals."""

    def __init__(self, stack: Stack):
        self.st = stack
        self.a, self.b = login(stack.alice, "dr.rao"), login(stack.bob, "dr.rao")
        self.admin, self.admin_b = login(stack.alice, "admin"), login(stack.bob, "admin")
        self.auditor_a, self.auditor_b = login(stack.alice, "auditor"), login(stack.bob, "auditor")

    def draft(self, title="Referral", body="Synthetic: BP 120/80") -> str:
        r = httpx.post(self.st.alice + "/api/records", headers=self.a, json={"patient_ref": "P-1", "title": title, "body": body})
        assert r.status_code == 201, r.text
        return r.json()["id"]

    def send(self, rid: str) -> httpx.Response:
        return httpx.post(f"{self.st.alice}/api/records/{rid}/send", headers=self.a, timeout=T)

    def status(self, rid: str) -> str:
        return httpx.get(f"{self.st.alice}/api/records/{rid}", headers=self.a).json()["status"]

    def inbox(self) -> list[dict]:
        return httpx.get(self.st.bob + "/api/inbox", headers=self.b).json()["records"]

    def pool(self, which="alice") -> dict:
        base, h = (self.st.alice, self.a) if which == "alice" else (self.st.bob, self.b)
        return httpx.get(base + "/api/keys", headers=h).json()["pool"]

    def link(self, **conf):
        return httpx.post(self.st.link + "/api/config", json=conf).json()

    def rotate(self) -> dict:
        return httpx.post(self.st.alice + "/api/keys/rotate", headers=self.admin, timeout=T).json()

    def events(self, which="alice") -> list[str]:
        base, h = (self.st.alice, self.auditor_a) if which == "alice" else (self.st.bob, self.auditor_b)
        return [e["event"] for e in httpx.get(base + "/api/audit?limit=500", headers=h).json()["entries"]]

    def reset(self):
        self.link(eve=False, tamper=False, noise=0.02)


@pytest.fixture(scope="module")
def rig(tmp_path_factory):
    with Stack(tmp_path_factory.mktemp("e2e"), fresh=True) as st:
        yield Rig(st)


def test_a_record_travels_from_hospital_a_to_hospital_b(rig):
    rig.reset()
    rid = rig.draft(body="Synthetic: echo results normal")
    r = rig.send(rid)
    assert r.status_code == 200, r.text
    assert r.json()["record"]["status"] == "sent" and rig.status(rid) == "sent"

    (rec,) = rig.inbox()
    assert rec["from"] == "Hospital A" and rec["sent_by"] == "dr.rao"
    body = httpx.get(f"{rig.st.bob}/api/inbox/{rec['id']}", headers=rig.b).json()["body"]
    assert body == "Synthetic: echo results normal"
    assert rec["key_id"] == r.json()["key_id"]
    # the key was spent on both sides and the channel signing key was renewed from QKD output
    assert rig.pool("alice")["used"] == 1 and rig.pool("bob")["used"] == 1
    assert rig.pool("alice")["auth_key_version"] >= 2 and rig.pool("bob")["auth_key_version"] >= 2
    assert rig.send(rid).status_code == 409  # a sent record is not sent twice


def test_each_record_gets_its_own_one_time_key(rig):
    rig.reset()
    before = rig.pool("alice")["used"]
    ids = [rig.send(rig.draft(title=f"Note {i}")).json()["key_id"] for i in range(3)]
    assert len(set(ids)) == 3
    assert rig.pool("alice")["used"] == before + 3 and rig.pool("bob")["used"] == before + 3
    assert len(rig.inbox()) >= 3


def test_an_eavesdropper_blocks_the_transfer_and_the_record_stays_a_draft(rig):
    rig.reset()
    assert rig.rotate()["expired"] >= 0           # empty the pool so a fresh session is needed
    rig.link(eve=True, eve_rate=1.0, eve_start=0.0)
    rid = rig.draft(title="Must not travel")
    r = rig.send(rid)
    assert r.status_code == 503, r.text
    detail = r.json()["detail"]
    assert detail["code"] == "no_secure_key" and "Eavesdropper" in detail["message"]
    stages = {s["id"]: s["status"] for s in detail["session"]["stages"]}
    assert stages["qber"] == "abort" and stages["ec"] == "skipped" and stages["commit"] == "skipped"
    assert detail["session"]["stats"]["qber"] > 0.11
    assert rig.status(rid) == "draft"
    assert not any(x["title"] == "Must not travel" for x in rig.inbox())
    assert rig.pool("alice")["available"] == 0 and rig.pool("bob")["available"] == 0
    ev = rig.events()
    assert "eavesdropper_suspected" in ev and "transfer_blocked" in ev
    # Eve leaves; the very same record now goes through
    rig.link(eve=False)
    r = rig.send(rid)
    assert r.status_code == 200, r.text
    assert any(x["title"] == "Must not travel" for x in rig.inbox())


def test_partial_eavesdropping_is_still_caught(rig):
    rig.reset()
    rig.rotate()
    rig.link(eve=True, eve_rate=0.6, eve_start=0.0)  # 60% of qubits -> about 15% errors
    r = rig.send(rig.draft())
    assert r.status_code == 503 and "Eavesdropper" in r.json()["detail"]["message"]
    rig.link(eve=False)


def test_altered_messages_are_refused_and_the_key_is_not_reused(rig):
    rig.reset()
    rig.rotate()
    assert httpx.post(rig.st.alice + "/api/keys/refill", headers=rig.a, timeout=T).json()["status"] == "ok"
    ready = rig.pool("alice")["available"]
    rig.link(tamper=True)
    rid = rig.draft(title="Altered in flight")
    r = rig.send(rid)
    assert r.status_code == 502, r.text
    assert r.json()["detail"]["code"] == "peer_error" and "MAC" in r.json()["detail"]["message"]
    assert rig.status(rid) == "draft"
    assert not any(x["title"] == "Altered in flight" for x in rig.inbox())
    assert "auth_failure" in rig.events("bob")
    assert rig.pool("alice")["available"] == ready - 1          # the exposed key was burned
    assert rig.pool("bob")["available"] == ready - 1            # and Bob was told to burn his copy too
    rig.link(tamper=False)
    assert rig.send(rid).status_code == 200


def test_rotation_wipes_unused_keys_on_both_sides(rig):
    rig.reset()
    httpx.post(rig.st.alice + "/api/keys/refill", headers=rig.a, timeout=T)
    assert rig.pool("alice")["available"] > 0 and rig.pool("bob")["available"] > 0
    out = rig.rotate()
    assert out["expired"] > 0 and out["peer_notified"] is True
    assert rig.pool("alice")["available"] == 0 and rig.pool("bob")["available"] == 0
    assert "keys_rotated" in rig.events("alice") and "keys_rotated" in rig.events("bob")
    assert httpx.post(rig.st.alice + "/api/keys/rotate", headers=rig.a).status_code == 403  # clinicians cannot


def test_audit_logs_are_intact_on_both_hospitals_after_all_of_that(rig):
    for base, h in ((rig.st.alice, rig.auditor_a), (rig.st.bob, rig.auditor_b)):
        v = httpx.get(base + "/api/audit/verify", headers=h).json()
        assert v["ok"] is True and v["checked"] > 20
    # patient text appears in neither hospital's audit log
    assert "echo results" not in httpx.get(rig.st.alice + "/api/audit?limit=500", headers=rig.auditor_a).text
    assert "echo results" not in httpx.get(rig.st.bob + "/api/audit?limit=500", headers=rig.auditor_b).text


def test_the_link_console_shows_ciphertext_not_patient_text(rig):
    rig.reset()
    rig.send(rig.draft(title="Wire check", body="TOP-SECRET-WIRE-MARKER"))
    wire = httpx.get(rig.st.link + "/api/wire").text
    assert "message" in wire and "ciphertext" in wire and "TOP-SECRET-WIRE-MARKER" not in wire
    assert httpx.get(rig.st.link + "/").status_code == 200


def test_data_and_logins_survive_a_restart(tmp_path):
    with Stack(tmp_path / "d", fresh=True) as st:
        r = Rig(st)
        rid = r.draft(title="Survives restart")
        assert r.send(rid).status_code == 200
        httpx.post(st.alice + "/api/keys/refill", headers=r.a, timeout=T)
        pool_before = r.pool("alice")
    with Stack(tmp_path / "d", ports=st.ports) as st2:  # same data directory, new processes
        r2 = Rig(st2)
        assert r2.status(rid) == "sent"
        assert any(x["title"] == "Survives restart" for x in r2.inbox())
        pool_after = r2.pool("alice")
        assert pool_after["available"] == pool_before["available"] and pool_after["used"] == pool_before["used"]
        assert httpx.get(st2.alice + "/api/audit/verify", headers=r2.auditor_a).json()["ok"] is True
        assert r2.send(r2.draft(title="After restart")).status_code == 200  # signing key and key pool still agree


def test_keys_expire_and_are_wiped_on_both_sides(tmp_path):
    env = {"QKD_KEY_TTL": "3", "QKD_MAINTAIN_SECONDS": "1"}
    with Stack(tmp_path / "ttl", fresh=True, env=env) as st:
        r = Rig(st)
        made = httpx.post(st.alice + "/api/keys/refill", headers=r.a, timeout=T).json()
        assert made["status"] == "ok" and r.pool("alice")["available"] > 0
        time.sleep(5)
        for which in ("alice", "bob"):
            p = r.pool(which)
            assert p["available"] == 0 and p["expired"] >= made["keys_added"], (which, p)
        assert "keys_expired" in r.events("alice") and "keys_expired" in r.events("bob")
        # keys this close to expiry are never handed out, so a send cannot use a key Bob may refuse
        rid = r.draft()
        assert r.send(rid).status_code == 503 and r.status(rid) == "draft"


def test_the_hardware_key_interface_works_through_a_kme(tmp_path):
    """Same hospitals, but keys come from an ETSI GS QKD 014 key manager (a stub here)."""
    with Stack(tmp_path / "etsi", fresh=True, etsi=True) as st:
        r = Rig(st)
        assert httpx.get(st.alice + "/api/node").json()["key_source"] == "etsi014"
        rid = r.draft(title="Via KME", body="Synthetic: via ETSI interface")
        resp = r.send(rid)
        assert resp.status_code == 200, resp.text
        (rec,) = r.inbox()
        assert httpx.get(f"{st.bob}/api/inbox/{rec['id']}", headers=r.b).json()["body"] == "Synthetic: via ETSI interface"
        assert httpx.get(st.alice + "/api/link", headers=r.a).json()["source"] == "etsi014"
        # no BB84 session ever ran: the link service saw no qubits
        assert httpx.get(st.link + "/api/config").json()["stats"]["qubits_sent"] == 0
        # key-manager outage: nothing is sent, the record stays a draft, and it recovers
        httpx.post(st.kme + "/stub/outage", json={"down": True})
        r.rotate()
        rid2 = r.draft(title="During outage")
        out = r.send(rid2)
        assert out.status_code in (502, 503) and r.status(rid2) == "draft"
        assert httpx.get(st.alice + "/api/link", headers=r.a).json()["reachable"] is False
        httpx.post(st.kme + "/stub/outage", json={"down": False})
        assert r.send(rid2).status_code == 200
