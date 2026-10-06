from fastapi.testclient import TestClient

from backend.main import app
from backend import crypto

client = TestClient(app)


def post(**body):
    r = client.post("/api/run", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def test_clean_session_delivers_the_record():
    d = post(seed=1)
    assert d["status"] == "secure" and d["reason"] is None
    assert [s["status"] for s in d["stages"]] == ["ok"] * 6
    assert d["stats"]["final_key_bits"] >= 256
    assert d["record"]["status"] == "delivered"
    assert d["record"]["decrypted"] == d["record"]["plaintext"]
    fps = {s["id"]: dict(s["metrics"]) for s in d["stages"]}["aes"]
    assert fps["Alice key fingerprint"] == fps["Bob key fingerprint"]


def test_full_eve_attack_is_caught_and_blocks_the_record():
    d = post(eve=True, eve_rate=1.0, seed=3)
    assert d["status"] == "aborted"
    assert d["stats"]["qber_est"] > 0.2
    ids = {s["id"]: s["status"] for s in d["stages"]}
    assert ids["qber"] == "abort" and ids["ec"] == ids["pa"] == ids["aes"] == "skipped"
    assert d["record"]["status"] == "blocked" and "ciphertext_hex" not in d["record"]


def test_eve_joining_halfway_shows_in_the_trace():
    d = post(eve=True, eve_start=0.5, seed=5)
    t = [b["qber"] for b in d["qber_trace"] if b["qber"] is not None]
    assert max(t[:6]) < 0.1 and sum(t[10:]) / len(t[10:]) > 0.15


def test_too_noisy_aborts_for_low_key_rate_not_eavesdropping():
    d = post(noise=0.08, seed=6)
    assert d["status"] == "aborted"
    assert "Secure key rate too low" in d["reason"]


def test_runs_are_random_unless_seeded():
    a, b = post(seed=11), post(seed=11)
    assert a["stats"]["qber_est"] == b["stats"]["qber_est"]
    assert a["record"]["nonce_hex"] != b["record"]["nonce_hex"]  # fresh AES nonce every time


def test_validation_rejects_bad_input():
    assert client.post("/api/run", json={"n_qubits": 10}).status_code == 422
    assert client.post("/api/run", json={"noise": 0.9}).status_code == 422


def test_wrong_key_cannot_decrypt():
    enc = crypto.encrypt_record(b"k" * 32)
    assert crypto.decrypt_record(b"k" * 32, enc["nonce"], enc["ciphertext"]) == enc["plaintext"]
    assert crypto.decrypt_record(b"x" * 32, enc["nonce"], enc["ciphertext"]) is None


def test_qiskit_endpoint_matches_the_physics():
    clean = client.post("/api/qiskit-demo", json={"n": 24, "seed": 4}).json()
    assert clean["qber"] in (0.0, None) and "H" in clean["circuit_ascii"]
    eve = client.post("/api/qiskit-demo", json={"n": 24, "eve": True, "seed": 4}).json()
    assert len(eve["rows"]) == 24 and all(r["eve_basis"] in ("X", "Z") for r in eve["rows"])


def test_frontend_is_served():
    r = client.get("/")
    assert r.status_code == 200 and "Quantum-secured patient records" in r.text
    assert client.get("/app.js").status_code == 200 and client.get("/style.css").status_code == 200
