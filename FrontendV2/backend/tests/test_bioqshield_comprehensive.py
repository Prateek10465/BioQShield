"""Comprehensive acceptance test suite for BioQShield (Hackathon Track 2.2).
Covers:
1. Health endpoint
2. Valid /api/run
3. Invalid /api/run
4. Clean scenario (ACCEPT -> usable key + delivered record)
5. Noisy scenario (noise 5% -> ACCEPT)
6. Eve scenario (eve=True -> REJECT -> blocked record)
7. Hostile traffic (threat > 0.8 -> escalated REJECT)
8. QBER threshold (>= 11% aborts)
9. Static policy behavior
10. Adaptive policy behavior
11. High-threat escalation (threat >= 0.8 escalates MONITOR to REJECT)
12. Error correction (Cascade verification)
13. Privacy amplification (Toeplitz universal hash)
14. AES-256-GCM encryption and decryption round-trip
15. Blocked transfer behavior (no key released, no ciphertext leaked)
16. Qiskit demo endpoint (Qiskit Aer, quantum circuit, per-qubit outcomes)
17. Scenario endpoint (7 combinations)
"""
from __future__ import annotations

import json
from fastapi.testclient import TestClient

from backend.main import app
from backend import crypto
from backend.quantum import bb84, postprocess as pp
from backend.threat import policy

client = TestClient(app)


def test_1_health_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"ok": True}


def test_2_valid_run_endpoint():
    payload = {
        "n_qubits": 8192,
        "noise": 0.02,
        "eve": False,
        "eve_rate": 1.0,
        "eve_start": 0.0,
        "seed": 42,
        "traffic": "benign",
        "adaptive": True,
    }
    res = client.post("/api/run", json=payload)
    assert res.status_code == 200
    d = res.json()
    assert "params" in d
    assert "status" in d
    assert "stats" in d
    assert "stages" in d
    assert "record" in d
    assert "threat" in d
    assert "decision_static" in d
    assert "decision" in d
    assert "qber_trace" in d
    assert d["stats"]["display_rules"]["ui_unit"] == "percent"


def test_3_invalid_run_inputs():
    # Negative noise
    assert client.post("/api/run", json={"noise": -0.1}).status_code == 422
    # Too large noise (> 0.2)
    assert client.post("/api/run", json={"noise": 0.25}).status_code == 422
    # Invalid traffic class
    assert client.post("/api/run", json={"traffic": "unknown_class"}).status_code == 422
    # Invalid qubit count (< 512)
    assert client.post("/api/run", json={"n_qubits": 100}).status_code == 422


def test_4_clean_scenario_accept_and_delivered():
    res = client.post(
        "/api/run",
        json={
            "n_qubits": 8192,
            "noise": 0.02,
            "eve": False,
            "traffic": "benign",
            "adaptive": True,
            "seed": 101,
        },
    )
    assert res.status_code == 200
    d = res.json()
    assert d["status"] == "secure"
    assert d["decision"]["verdict"] == "ACCEPT"
    assert d["stats"]["key_available"] is True
    assert d["stats"]["final_key_bits"] >= 256
    assert d["record"]["status"] == "delivered"
    assert d["record"]["ciphertext_hex"] is not None
    assert d["record"]["decrypted"] == d["record"]["plaintext"]


def test_5_noisy_link_tolerates_moderate_noise():
    res = client.post(
        "/api/run",
        json={
            "n_qubits": 8192,
            "noise": 0.05,
            "eve": False,
            "traffic": "benign",
            "adaptive": True,
            "seed": 1,
        },
    )
    assert res.status_code == 200
    d = res.json()
    assert d["status"] == "secure"
    assert d["decision"]["verdict"] == "ACCEPT"

    assert d["stats"]["key_available"] is True
    assert d["record"]["status"] == "delivered"


def test_6_eve_listening_triggers_reject_and_blocks():
    res = client.post(
        "/api/run",
        json={
            "n_qubits": 8192,
            "noise": 0.02,
            "eve": True,
            "eve_rate": 1.0,
            "eve_start": 0.0,
            "traffic": "benign",
            "adaptive": True,
            "seed": 103,
        },
    )
    assert res.status_code == 200
    d = res.json()
    assert d["status"] == "aborted"
    assert d["decision"]["verdict"] == "REJECT"
    assert d["stats"]["key_available"] is False
    assert d["record"]["status"] == "blocked"
    assert "ciphertext_hex" not in d["record"] or d["record"].get("ciphertext_hex") is None


def test_7_hostile_network_escalation_rejects():
    # Attack traffic has high threat score (> 0.8), which escalates to REJECT under adaptive policy
    res = client.post(
        "/api/run",
        json={
            "n_qubits": 8192,
            "noise": 0.05,
            "eve": False,
            "traffic": "attack",
            "adaptive": True,
            "seed": 104,
        },
    )
    assert res.status_code == 200
    d = res.json()
    assert d["threat"]["score"] >= 0.8
    assert d["threat"]["classification"] == "attack"
    assert d["decision"]["verdict"] == "REJECT"
    # Even though QKD itself would have been clean, the security policy blocks key release
    assert d["stats"]["key_available"] is False
    assert d["record"]["status"] == "blocked"


def test_8_qber_threshold_aborts_above_11_pct():
    # Eve rate 1.0 creates ~25% QBER >> 11%
    res = client.post("/api/run", json={"n_qubits": 4096, "eve": True, "eve_rate": 1.0, "seed": 105})
    d = res.json()
    assert d["status"] == "aborted"
    assert d["stats"]["qber_est"] >= 0.11
    # stages should show qber aborted, ec, pa, aes skipped
    stage_map = {s["id"]: s["status"] for s in d["stages"]}
    assert stage_map["qber"] == "abort"
    assert stage_map["ec"] == "skipped"
    assert stage_map["pa"] == "skipped"
    assert stage_map["aes"] == "skipped"


def test_9_static_policy_thresholds():
    mock_session = {"stats": {"qber_est": 0.04}, "status": "secure"}
    dec = policy.decide(mock_session, adaptive=False)
    assert dec.verdict == "ACCEPT"

    mock_session["stats"]["qber_est"] = 0.08
    dec = policy.decide(mock_session, adaptive=False)
    assert dec.verdict == "MONITOR"

    mock_session["stats"]["qber_est"] = 0.12
    dec = policy.decide(mock_session, adaptive=False)
    assert dec.verdict == "REJECT"


def test_10_adaptive_policy_tightening():
    mock_session = {"stats": {"qber_est": 0.045}, "status": "secure"}
    # High threat (0.7) tightens accept threshold below 0.06 - 0.03*0.7 = 0.039
    dec = policy.decide(mock_session, threat=0.7, adaptive=True)
    assert dec.verdict == "MONITOR"


def test_11_high_threat_escalates_monitor_to_reject():
    mock_session = {"stats": {"qber_est": 0.05}, "status": "secure"}
    # Threat >= 0.8 escalates MONITOR to REJECT
    dec = policy.decide(mock_session, threat=0.85, adaptive=True)
    assert dec.verdict == "REJECT"
    assert "escalated" in dec.reason.lower()


def test_12_error_correction_verification():
    # Test error correction mechanics directly
    import numpy as np
    rng = np.random.default_rng(42)
    alice = rng.integers(0, 2, 2048, dtype=np.uint8)
    bob = alice.copy()
    # Flip 2% bits
    flips = rng.random(2048) < 0.02
    bob[flips] ^= 1
    res = pp.reconcile(alice, bob, 0.02, rng=rng)
    assert res.verified is True
    assert np.array_equal(alice, res.corrected)
    assert res.errors_fixed > 0


def test_13_privacy_amplification_produces_keys():
    import numpy as np
    rng = np.random.default_rng(42)
    key = rng.integers(0, 2, 2000, dtype=np.uint8)
    out_len = 512
    seed_bits = rng.integers(0, 2, len(key) + out_len - 1, dtype=np.uint8)
    amp = pp.privacy_amplify(key, out_len, seed_bits)
    assert len(amp) == out_len
    raw_bytes = pp.bits_to_bytes(amp)
    assert len(raw_bytes) == out_len // 8


def test_14_aes_256_gcm_roundtrip():
    key = crypto.os.urandom(32)
    enc = crypto.encrypt_record(key)
    dec = crypto.decrypt_record(key, enc["nonce"], enc["ciphertext"])
    assert dec == enc["plaintext"]
    record_obj = json.loads(dec)
    assert record_obj["patient_id"] == "PT-2048"
    assert "SYNTHETIC DEMONSTRATION DATA" in record_obj["disclaimer"]


def test_15_blocked_transfer_leaks_no_ciphertext():
    res = client.post("/api/run", json={"noise": 0.08, "seed": 77})
    d = res.json()
    assert d["status"] == "aborted"
    assert d["record"]["status"] == "blocked"
    assert d["record"].get("ciphertext_hex") is None
    assert d["record"].get("decrypted") is None


def test_16_qiskit_demo_endpoint():
    res = client.post("/api/qiskit-demo", json={"n": 10, "eve": True, "noise": 0.0, "seed": 42})
    assert res.status_code == 200
    data = res.json()
    assert data["protocol"] == "BB84"
    assert data["engine"] == "Qiskit Aer"
    assert len(data["rows"]) == 10
    assert "circuit" in data
    assert len(data["circuit"]) > 0
    first_row = data["rows"][0]
    assert "alice" in first_row
    assert "bob" in first_row
    assert "outcome" in first_row


def test_17_scenarios_endpoint_returns_seven_combos():
    res = client.get("/api/scenarios")
    assert res.status_code == 200
    scenarios = res.json()
    assert len(scenarios) == 7
    for sc in scenarios:
        assert "scenario" in sc
        assert "threat" in sc
        assert "qber" in sc
        assert "key_bits" in sc
        assert "static" in sc
        assert "adaptive" in sc
        assert "reason" in sc
