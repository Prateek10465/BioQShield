"""One QKD session on a link, reduced to the numbers a security decision needs."""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np

from quantum import bb84, postprocess as pp, decoy
from quantum.bb84 import Sifted, Estimation

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
    # Decoy-state extensions
    gain_signal: float = 0.0
    gain_decoy: float = 0.0
    qber_signal: float = 0.0
    qber_decoy: float = 0.0
    pns_violation: bool = False
    # Anomaly detection extensions
    qber_trace: list[dict] | None = None  # binned QBER across the stream
    sift_rate: float = 0.0  # fraction of qubits that were sifted
    gain: float = 0.0  # overall gain (detection rate)
    eve_knows_fraction: float = 0.0  # fraction of sifted bits that Eve knows
    # Randomness test extensions
    randomness_pass: bool = False  # whether the key passes randomness tests

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
    # Decoy-state parameters
    p_signal: float = 0.7,
    p_decoy: float = 0.2,
    p_vacuum: float = 0.1,
    mu_signal: float = 0.5,
    mu_decoy: float = 0.1,
    mu_vacuum: float = 0.0,
) -> LinkReport:
    """BB84 -> sift -> QBER estimate -> (error correction) -> secret key length.

    engine:        "numpy" (fast, for sweeps), "qiskit" (Aer circuits), or "auto" (qiskit if installed).
    full_cascade:  run the real Cascade from `quantum.postprocess` to count leaked bits.
                   False uses leakage = 1.16 * n * h2(q) + 40 (verification), which is
                   what Cascade typically costs and is much faster for large sweeps.
    Decoy-state:   p_signal/p_decoy/p_vacuum: probabilities of signal/decoy/vacuum pulses.
                   mu_signal/mu_decoy/mu_vacuum: mean photon numbers for each intensity.
    """
    rng = np.random.default_rng(seed)
    if engine == "auto":
        from quantum.bb84_qiskit import qiskit_available

        engine = "qiskit" if qiskit_available() else "numpy"
    if engine == "qiskit":
        # Note: Qiskit version doesn't support decoy-state yet, fallback to numpy for decoy features
        from quantum.bb84_qiskit import transmit_qiskit

        tx = transmit_qiskit(n_qubits, noise=noise, eve_rate=eve_rate, eve_start=eve_start, rng=rng)
        # For Qiskit engine, we can't do decoy-state yet, so set defaults
        gain_signal = gain_decoy = 0.0
        qber_signal = qber_decoy = 0.0
        pns_violation = False
    elif engine == "numpy":
        # Generate intensities for decoy-state: signal, decoy, vacuum
        # Choose intensity for each pulse based on probabilities
        intensity_choice = rng.choice([0, 1, 2], size=n_qubits, p=[p_signal, p_decoy, p_vacuum])
        intensities = np.where(intensity_choice == 0, mu_signal,
                              np.where(intensity_choice == 1, mu_decoy, mu_vacuum))
        tx = bb84.transmit(n_qubits, noise=noise, eve_rate=eve_rate, eve_start=eve_start, intensities=intensities, rng=rng)

        # Decoy-state analysis: estimate gain and QBER for signal and decoy intensities
        s = bb84.sift(tx)

        # Create masks for signal and decoy intensities in the sifted key
        if s.intensities is not None:
            signal_mask = np.abs(s.intensities - mu_signal) < 1e-10
            decoy_mask = np.abs(s.intensities - mu_decoy) < 1e-10

            # Estimate gain and QBER for signal intensity
            if np.any(signal_mask):
                # Create a temporary Sifted object with only signal intensity bits
                signal_sifted = Sifted(
                    positions=s.positions[signal_mask],
                    alice=s.alice[signal_mask],
                    bob=s.bob[signal_mask],
                    eve_knows=s.eve_knows[signal_mask],
                    intensities=s.intensities[signal_mask],
                    photon_numbers=s.photon_numbers[signal_mask]
                )
                gain_signal, qber_signal = decoy.estimate_gain_qber(signal_sifted, intensities)
            else:
                gain_signal, qber_signal = 0.0, 0.0

            # Estimate gain and QBER for decoy intensity
            if np.any(decoy_mask):
                # Create a temporary Sifted object with only decoy intensity bits
                decoy_sifted = Sifted(
                    positions=s.positions[decoy_mask],
                    alice=s.alice[decoy_mask],
                    bob=s.bob[decoy_mask],
                    eve_knows=s.eve_knows[decoy_mask],
                    intensities=s.intensities[decoy_mask],
                    photon_numbers=s.photon_numbers[decoy_mask]
                )
                gain_decoy, qber_decoy = decoy.estimate_gain_qber(decoy_sifted, intensities)
            else:
                gain_decoy, qber_decoy = 0.0, 0.0

            # Perform PNS test
            _, pns_violation = decoy.pns_test(gain_signal, gain_decoy, qber_signal, qber_decoy, mu_signal, mu_decoy)
        else:
            # Fallback if intensities not available (shouldn't happen with numpy engine)
            gain_signal = gain_decoy = 0.0
            qber_signal = qber_decoy = 0.0
            pns_violation = False
    else:
        raise ValueError(f"unknown engine {engine!r}")

    est = bb84.estimate_qber(s, SAMPLE_FRACTION, rng)
    true_q = float((s.alice != s.bob).mean()) if len(s.alice) else 0.0

    # Additional telemetry for anomaly detection
    sift_rate = len(s.alice) / n_qubits if n_qubits > 0 else 0.0
    gain = sift_rate  # in current simulation, gain equals sift rate (no loss besides basis mismatch)
    eve_knows_fraction = float(est.eve_knows.mean()) if len(est.eve_knows) > 0 else 0.0
    qber_trace = bb84.qber_trace(est, n_qubits)

    leaked, key_bits = 0, 0
    if est.qber <= pp.QBER_ABORT_THRESHOLD and len(est.alice_key) > 0:
        n_key = len(est.alice_key)
        if full_cascade:
            leaked = pp.reconcile(est.alice_key, est.bob_key, est.qber, rng=rng).leaked_bits
        else:
            leaked = int(np.ceil(CASCADE_EFFICIENCY * n_key * bb84.h2(est.qber))) + pp.VERIFY_BITS
        # Use finite-key bound for secret key length if enabled, otherwise use simple bound
        # To enable finite-key bound, set environment variable BIOQSHIELD_USE_FINITE_KEY=1
        import os
        if os.environ.get("BIOQSHIELD_USE_FINITE_KEY", "0") == "1":
            from quantum.finite_key import finite_key_secret_key_length
            key_bits, _ = finite_key_secret_key_length(n_key, est.qber_upper, leaked)
        else:
            # Use simple secret key length for backward compatibility
            key_bits = pp.secret_key_length(n_key, est.qber_upper, leaked)

    # Run randomness tests on the final key if we have a key
    randomness_passed = False
    if key_bits > 0 and len(est.alice_key) > 0:
        from quantum.randomness import randomness_pass
        randomness_passed = randomness_pass(est.alice_key)

    return LinkReport(
        n_qubits=n_qubits, n_sifted=int(len(s.alice)), sample_size=int(len(est.sample_errors)),
        qber=est.qber, qber_upper=est.qber_upper, true_qber=true_q, leaked_bits=leaked,
        key_bits=key_bits, engine=engine, eve_rate=eve_rate, noise=noise,
        gain_signal=gain_signal, gain_decoy=gain_decoy,
        qber_signal=qber_signal, qber_decoy=qber_decoy,
        pns_violation=pns_violation,
        # Anomaly detection extensions
        qber_trace=qber_trace,
        sift_rate=sift_rate,
        gain=gain,
        eve_knows_fraction=eve_knows_fraction,
        # Randomness test extensions
        randomness_pass=randomness_passed,
    )
