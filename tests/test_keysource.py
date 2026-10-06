import os

import pytest
from fastapi.testclient import TestClient

from nodes import etsi_stub
from nodes.keysource import (Bb84Receiver, Bb84Sender, Etsi014Client, Etsi014Receiver, Etsi014Sender, KeySourceError,
                             KeyUnavailable)
from nodes.store import Store
from nodes.vault import Vault


@pytest.fixture(autouse=True)
def _reset_stub(monkeypatch):
    monkeypatch.setenv("STUB_ALLOW_CONTROL", "1")
    etsi_stub.state["down"] = False
    etsi_stub.pending.clear()
    yield
    etsi_stub.state["down"] = False


@pytest.fixture
def kme_a():
    return Etsi014Client(TestClient(etsi_stub.app, headers={"X-API-Key": "dev-key-a"}))


@pytest.fixture
def kme_b():
    return Etsi014Client(TestClient(etsi_stub.app, headers={"X-API-Key": "dev-key-b"}))


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "n.db", Vault(os.urandom(32)))


def test_status_has_the_standard_fields(kme_a):
    s = kme_a.status("hospital-b")
    for field in ("source_KME_ID", "target_KME_ID", "master_SAE_ID", "slave_SAE_ID", "key_size",
                  "stored_key_count", "max_key_count", "max_key_per_request", "max_key_size", "min_key_size"):
        assert field in s
    assert s["master_SAE_ID"] == "hospital-a" and s["slave_SAE_ID"] == "hospital-b" and s["key_size"] == 256


def test_master_gets_keys_and_slave_fetches_the_same_ones_exactly_once(kme_a, kme_b):
    keys = kme_a.enc_keys("hospital-b", 3)
    assert len(keys) == 3 and all(len(k) == 32 for _, k in keys) and len({i for i, _ in keys}) == 3
    kid, key = keys[0]
    assert kme_b.dec_keys("hospital-a", kid) == key
    assert kme_b.dec_keys("hospital-a", kid) is None  # delivered once
    assert kme_b.dec_keys("hospital-a", "00000000-0000-0000-0000-000000000000") is None
    assert kme_a.status("hospital-b")["stored_key_count"] == 2


def test_the_master_cannot_collect_the_slaves_copy(kme_a, kme_b):
    kid, key = kme_a.enc_keys("hospital-b", 1)[0]
    assert kme_a.dec_keys("hospital-b", kid) is None  # that id was issued for the other direction
    assert kme_b.dec_keys("hospital-a", kid) == key  # and the failed attempt did not burn it


def test_wrong_peer_wrong_credentials_and_bad_size(kme_a):
    with pytest.raises(KeySourceError):
        kme_a.enc_keys("hospital-z", 1)
    with pytest.raises(KeySourceError):
        kme_a.enc_keys("hospital-a", 1)  # not a peer of itself
    bad = Etsi014Client(TestClient(etsi_stub.app, headers={"X-API-Key": "nope"}))
    with pytest.raises(KeySourceError, match="credentials"):
        bad.enc_keys("hospital-b", 1)
    with pytest.raises(KeySourceError):
        kme_a.enc_keys("hospital-b", 1, size=100)  # not a multiple of 8


def test_outage_is_reported_as_unavailable_not_as_an_error(kme_a):
    TestClient(etsi_stub.app).post("/stub/outage", json={"down": True})
    with pytest.raises(KeyUnavailable, match="no key available"):
        kme_a.enc_keys("hospital-b", 1)
    TestClient(etsi_stub.app).post("/stub/outage", json={"down": False})
    assert len(kme_a.enc_keys("hospital-b", 1)) == 1


def test_stub_control_is_off_by_default(monkeypatch):
    monkeypatch.delenv("STUB_ALLOW_CONTROL")
    assert TestClient(etsi_stub.app).post("/stub/outage", json={"down": True}).status_code == 404


def test_etsi_sender_fills_the_local_pool_and_receiver_uses_it(kme_a, kme_b, store):
    sender = Etsi014Sender(kme_a, store, "hospital-b", ttl=600)
    refill = sender.refill(4)
    assert refill.added == 4 and store.available_count() == 4
    kid, key = store.reserve_key()
    assert Etsi014Receiver(kme_b, "hospital-a").obtain(kid) == key  # the other side gets the same key


def test_a_garbled_key_from_the_kme_is_rejected():
    class Bad:
        def post(self, *a, **k):
            class R:
                status_code = 200

                @staticmethod
                def json():
                    return {"keys": [{"key_ID": "x", "key": "AAAA"}]}
            return R()

    with pytest.raises(KeySourceError, match="256-bit"):
        Etsi014Client(Bad()).enc_keys("hospital-b", 1)


def test_unreachable_kme_is_unavailable():
    import httpx

    with pytest.raises(KeyUnavailable, match="unreachable"):
        Etsi014Client(httpx.Client(base_url="http://127.0.0.1:1", timeout=0.5)).enc_keys("hospital-b", 1)


def test_bb84_adapters(store):
    ok = Bb84Sender(lambda actor: {"status": "ok", "keys_added": 3, "reason": None})
    assert ok.refill(4).added == 3
    refused = Bb84Sender(lambda actor: {"status": "aborted", "reason": "Eavesdropper detected", "keys_added": 0})
    with pytest.raises(KeyUnavailable, match="Eavesdropper") as e:
        refused.refill(4)
    assert e.value.detail["status"] == "aborted"
    store.add_keys([("s-0", "s", 0, b"\x07" * 32)], ttl=100)
    assert Bb84Receiver(store).obtain("s-0") == b"\x07" * 32
    assert Bb84Receiver(store).obtain("s-0") is None
