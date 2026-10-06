"""One QKD session on a link, reduced to the numbers a security decision needs."""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np

from quantum import bb84, postprocess as pp

SAMPLE_FRACTION = 0.25
CASCADE_EFFICIENCY = 1.16  # typical Cascade leakage as a multiple of the Shannon limit n*h2(q)


@dataclass
class LinkReport:
    n_qubits: int
    n_sifted: int
    sample_size: int  # sifted bits revealed to measure the QBER
    qber: float  # measured on the sample: what Alice and Bob can see
    qber_upper: float  # qber + 4 sigma
    true_qber: float  # whole sifted key; only a simulation can know this
    leaked_bits: int
    key_bits: int  # secret bits left after error correction and privacy amplification
    engine: str
    eve_rate: float
    noise: float

    def as_dict(self) -> dict:
        return asdict(self)


def run_link_session(
    n_qubits: int = 4096,
    noise: float = 0.02,
    eve_rate: float = 0.0,
    eve_start: float = 0.0,
    engine: str = "numpy",
    seed: int | None = None,
    full_cascade: bool = False,
) -> LinkReport:
    """BB84 -> sift -> QBER estimate -> (error correction) -> secret key length.

    engine:        "numpy" (fast, for sweeps), "qiskit" (Aer circuits), or "auto" (qiskit if installed).
    full_cascade:  run the real Cascade from `quantum.postprocess` to count leaked bits.
                   False uses leakage = 1.16 * n * h2(q) + 40 (verification), which is
                   what Cascade typically costs and is much faster for large sweeps.
    """
    rng = np.random.default_rng(seed)
    if engine == "auto":
        from quantum.bb84_qiskit import qiskit_available

        engine = "qiskit" if qiskit_available() else "numpy"
    if engine == "qiskit":
        from quantum.bb84_qiskit import transmit_qiskit

        tx = transmit_qiskit(n_qubits, noise=noise, eve_rate=eve_rate, eve_start=eve_start, rng=rng)
    elif engine == "numpy":
        tx = bb84.transmit(n_qubits, noise=noise, eve_rate=eve_rate, eve_start=eve_start, rng=rng)
    else:
        raise ValueError(f"unknown engine {engine!r}")

    s = bb84.sift(tx)
    est = bb84.estimate_qber(s, SAMPLE_FRACTION, rng)
    true_q = float((s.alice != s.bob).mean()) if len(s.alice) else 0.0

    leaked, key_bits = 0, 0
    if est.qber <= pp.QBER_ABORT_THRESHOLD and len(est.alice_key) > 0:
        n_key = len(est.alice_key)
        if full_cascade:
            leaked = pp.reconcile(est.alice_key, est.bob_key, est.qber, rng=rng).leaked_bits
        else:
            leaked = int(np.ceil(CASCADE_EFFICIENCY * n_key * bb84.h2(est.qber))) + pp.VERIFY_BITS
        key_bits = pp.secret_key_length(n_key, est.qber_upper, leaked)

    return LinkReport(
        n_qubits=n_qubits, n_sifted=int(len(s.alice)), sample_size=int(len(est.sample_errors)),
        qber=est.qber, qber_upper=est.qber_upper, true_qber=true_q, leaked_bits=leaked,
        key_bits=key_bits, engine=engine, eve_rate=eve_rate, noise=noise,
    )
