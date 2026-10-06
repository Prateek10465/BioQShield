"""One full QKD session: quantum transmission -> post-processing -> AES-256 record transfer."""
from __future__ import annotations

import time

import numpy as np

from quantum import bb84, postprocess as pp
from . import crypto

SAMPLE_FRACTION = 0.25


def _stage(sid: str, title: str, status: str, metrics: list[list[str]], note: str = "") -> dict:
    return {"id": sid, "title": title, "status": status, "metrics": metrics, "note": note}


def _skipped(sid: str, title: str) -> dict:
    return _stage(sid, title, "skipped", [], "Not reached: session aborted earlier.")


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def run_session(
    n_qubits: int = 8192,
    noise: float = 0.02,
    eve: bool = False,
    eve_rate: float = 1.0,
    eve_start: float = 0.0,
    seed: int | None = None,
) -> dict:
    t0 = time.perf_counter()
    rng = np.random.default_rng(seed)
    rate = eve_rate if eve else 0.0
    stages: list[dict] = []

    result: dict = {
        "params": {
            "n_qubits": n_qubits,
            "noise": noise,
            "eve": eve,
            "eve_rate": eve_rate,
            "eve_start": eve_start,
        },
        "status": "aborted",
        "reason": None,
        "stats": {},
        "qber_trace": [],
        "stages": stages,
        "record": None,
    }

    # 1. Quantum transmission ------------------------------------------------
    tx = bb84.transmit(n_qubits, noise=noise, eve_rate=rate, eve_start=eve_start, rng=rng)
    n_int = int(tx.intercepted.sum())
    stages.append(
        _stage(
            "transmit",
            "Quantum transmission",
            "ok",
            [
                ["Qubits sent", f"{n_qubits:,}"],
                ["Channel noise", _pct(noise)],
                ["Eve intercepted", f"{n_int:,}" if eve else "none"],
            ],
            "Alice encodes random bits in random bases (Z or X); Bob measures in random bases.",
        )
    )

    # 2. Sifting -------------------------------------------------------------
    s = bb84.sift(tx)
    stages.append(
        _stage(
            "sift",
            "Basis sifting",
            "ok",
            [
                ["Bases matched", f"{len(s.alice):,}"],
                ["Sift rate", _pct(len(s.alice) / n_qubits)],
            ],
            "Alice and Bob publicly compare bases (not bits) and keep only matching positions.",
        )
    )

    # 3. QBER estimation -----------------------------------------------------
    est = bb84.estimate_qber(s, SAMPLE_FRACTION, rng)
    result["qber_trace"] = bb84.qber_trace(est, n_qubits)
    stats = result["stats"]
    stats.update(
        {
            "n_sent": n_qubits,
            "n_sifted": int(len(s.alice)),
            "sample_size": int(len(est.sample_errors)),
            "qber_est": est.qber,
            "qber_upper": est.qber_upper,
            "threshold": pp.QBER_ABORT_THRESHOLD,
            # Ground truth only a simulation can know -- a real link can't see these.
            "sim_true_qber": float((s.alice != s.bob).mean()),
            "sim_eve_known_fraction": float(est.eve_knows.mean()) if len(est.eve_knows) else 0.0,
        }
    )
    high = est.qber > pp.QBER_ABORT_THRESHOLD
    stages.append(
        _stage(
            "qber",
            "QBER estimation",
            "abort" if high else "ok",
            [
                ["Bits revealed", f"{len(est.sample_errors):,}"],
                ["Measured QBER", _pct(est.qber)],
                ["Abort threshold", _pct(pp.QBER_ABORT_THRESHOLD)],
            ],
            "Eavesdropper detected: error rate is too high to be channel noise."
            if high
            else "Error rate is consistent with channel noise. Continuing.",
        )
    )
    if high:
        return _abort(
            result,
            "Eavesdropper detected: QBER above the 11% security threshold.",
            [("ec", "Error correction"), ("pa", "Privacy amplification"), ("aes", "AES-256-GCM transfer")],
            t0,
        )

    # 4. Error correction (Cascade) + verification --------------------------
    cas = pp.reconcile(est.alice_key, est.bob_key, est.qber, rng=rng)
    verified = cas.verified
    leaked = cas.leaked_bits
    stats.update(
        {
            "ec_errors_fixed": cas.errors_fixed,
            "ec_leaked_bits": leaked,
            "ec_verified": verified,
            "ec_rounds": cas.rounds,
        }
    )
    stages.append(
        _stage(
            "ec",
            "Error correction (Cascade)",
            "ok" if verified else "abort",
            [
                ["Errors fixed", f"{cas.errors_fixed:,}"],
                ["Parity bits leaked", f"{leaked:,}"],
                ["Key verified", "yes" if verified else "NO"],
            ],
            "Block parities and binary search locate and flip Bob's wrong bits. "
            "Every revealed parity is subtracted from the final key."
            + (f" Verification caught leftover errors, so a second round ran ({cas.rounds} rounds)." if cas.rounds > 1 else ""),
        )
    )
    if not verified:
        return _abort(
            result,
            "Key verification failed after error correction.",
            [("pa", "Privacy amplification"), ("aes", "AES-256-GCM transfer")],
            t0,
        )

    # 5. Privacy amplification -----------------------------------------------
    n_key = len(est.alice_key)
    out_bits = pp.secret_key_length(n_key, est.qber_upper, leaked)
    stats.update({"pa_input_bits": n_key, "final_key_bits": out_bits})
    enough = out_bits >= pp.MIN_KEY_BITS
    stages.append(
        _stage(
            "pa",
            "Privacy amplification",
            "ok" if enough else "abort",
            [
                ["Key before", f"{n_key:,} bits"],
                ["Secret key after", f"{out_bits:,} bits"],
                ["Needed for AES-256", f"{pp.MIN_KEY_BITS} bits"],
            ],
            "A universal (Toeplitz) hash shrinks the key so anything Eve might know is squeezed out."
            if enough
            else "Not enough secure key left after removing what noise, leakage and a possible "
            "eavesdropper could account for.",
        )
    )
    if not enough:
        return _abort(
            result,
            "Secure key rate too low: not enough secret bits for AES-256.",
            [("aes", "AES-256-GCM transfer")],
            t0,
        )

    seed_bits = rng.integers(0, 2, n_key + out_bits - 1, dtype=np.uint8)
    alice_final = pp.privacy_amplify(est.alice_key, out_bits, seed_bits)
    bob_final = pp.privacy_amplify(cas.corrected, out_bits, seed_bits)
    alice_aes = crypto.derive_aes_key(pp.bits_to_bytes(alice_final))
    bob_aes = crypto.derive_aes_key(pp.bits_to_bytes(bob_final))

    # 6. Encrypted record transfer ---------------------------------------------
    enc = crypto.encrypt_record(alice_aes)
    decrypted = crypto.decrypt_record(bob_aes, enc["nonce"], enc["ciphertext"])
    ok = decrypted is not None and decrypted == enc["plaintext"]
    fp_a, fp_b = crypto.key_fingerprint(alice_aes), crypto.key_fingerprint(bob_aes)
    stages.append(
        _stage(
            "aes",
            "AES-256-GCM transfer",
            "ok" if ok else "abort",
            [
                ["Alice key fingerprint", fp_a],
                ["Bob key fingerprint", fp_b],
                ["Record decrypted", "yes" if ok else "NO"],
            ],
            "The QKD key encrypts the patient record. Anyone tapping the line sees only ciphertext.",
        )
    )
    ct_hex = enc["ciphertext"].hex()
    result["record"] = {
        "status": "delivered" if ok else "failed",
        "plaintext": enc["plaintext"],
        "nonce_hex": enc["nonce"].hex(),
        "ciphertext_hex": ct_hex,
        "ciphertext_bytes": len(enc["ciphertext"]),
        "decrypted": decrypted,
    }
    result["status"] = "secure" if ok else "aborted"
    result["reason"] = None if ok else "Decryption failed."
    result["elapsed_ms"] = round((time.perf_counter() - t0) * 1000)
    return result


def _abort(result: dict, reason: str, skipped: list[tuple[str, str]], t0: float) -> dict:
    for sid, title in skipped:
        result["stages"].append(_skipped(sid, title))
    result["status"] = "aborted"
    result["reason"] = reason
    result["record"] = {
        "status": "blocked",
        "plaintext": crypto.json.dumps(crypto.DEMO_RECORD, indent=2),
        "note": "No secure key was established, so the record was never sent.",
    }
    result["elapsed_ms"] = round((time.perf_counter() - t0) * 1000)
    return result
