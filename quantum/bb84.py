"""BB84 quantum key distribution -- fast numpy simulation.

Models, per qubit:
  * Alice picks a random bit and a random basis (0 = Z, 1 = X) and sends the qubit.
  * Eve (optional) runs an intercept-resend attack on a chosen fraction of qubits:
    she measures in a random basis and resends what she saw. When her basis
    differs from Alice's she disturbs the state.
  * The channel flips Bob's measurement outcome with probability `noise`.
  * Bob measures in a random basis. A wrong basis gives a uniformly random bit.

This is a classical simulation of the measurement statistics. It is exact for
BB84 with ideal single-qubit states, which is why it scales to tens of
thousands of qubits instantly. `qiskit_demo.py` runs the same protocol as real
circuits on Qiskit Aer for a handful of qubits.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def h2(p: float) -> float:
    """Binary entropy in bits."""
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return float(-p * np.log2(p) - (1 - p) * np.log2(1 - p))


@dataclass
class Transmission:
    n: int
    alice_bits: np.ndarray
    alice_bases: np.ndarray
    bob_bases: np.ndarray
    bob_bits: np.ndarray
    intercepted: np.ndarray  # bool: Eve measured this qubit
    eve_knows: np.ndarray  # bool: Eve's basis matched Alice's, so she learned the bit
    # Decoy-state extensions
    intensities: np.ndarray | None  # intensity mu for each pulse
    photon_numbers: np.ndarray | None  # photon number for each pulse


@dataclass
class Sifted:
    positions: np.ndarray  # index of each kept qubit in the original stream
    alice: np.ndarray
    bob: np.ndarray
    eve_knows: np.ndarray
    # Decoy-state extensions
    intensities: np.ndarray | None  # intensity for each sifted bit
    photon_numbers: np.ndarray | None  # photon number for each sifted bit


@dataclass
class Estimation:
    sample_positions: np.ndarray
    sample_errors: np.ndarray  # bool per sampled bit
    qber: float  # measured error rate on the sample
    qber_upper: float  # qber + 4 sigma, used for the key-length bound
    alice_key: np.ndarray  # remaining (unrevealed) bits
    bob_key: np.ndarray
    eve_knows: np.ndarray
    positions: np.ndarray
    # Decoy-state extensions
    intensities: np.ndarray | None  # intensity for each bit in the sample (or key?)
    photon_numbers: np.ndarray | None  # photon number for each bit


def qber_upper_bound(q: float, m: int, sigmas: float = 4.0) -> float:
    """Measured error rate plus `sigmas` standard deviations of the binomial estimate.

    A simplification of a full finite-key analysis. Alice and Bob each compute it
    from the public sample, so neither has to trust the other's number.
    """
    sigma = float(np.sqrt(max(q * (1 - q), 1e-12) / m))
    return min(0.5, q + sigmas * sigma)


def transmit(
    n: int,
    noise: float = 0.02,
    eve_rate: float = 0.0,
    eve_start: float = 0.0,
    intensities: np.ndarray | None = None,
    rng: np.random.Generator | None = None,
) -> Transmission:
    """Send `n` qubits from Alice to Bob.

    eve_rate:  fraction of qubits Eve intercepts (0 = no Eve, 1 = full attack).
    eve_start: Eve only attacks qubits after this fraction of the stream (0..1).
    intensities: per-pulse intensity μ (mean photon number). If None, use coherent state with μ=0.5 for all pulses.
    """
    rng = rng or np.random.default_rng()
    a_bits = rng.integers(0, 2, n, dtype=np.uint8)
    a_bases = rng.integers(0, 2, n, dtype=np.uint8)

    # --- Eve: intercept-resend ---
    idx = np.arange(n)
    intercepted = (rng.random(n) < eve_rate) & (idx >= int(eve_start * n))
    e_bases = rng.integers(0, 2, n, dtype=np.uint8)
    e_match = e_bases == a_bases
    e_bits = np.where(e_match, a_bits, rng.integers(0, 2, n, dtype=np.uint8)).astype(np.uint8)
    state_bits = np.where(intercepted, e_bits, a_bits).astype(np.uint8)
    state_bases = np.where(intercepted, e_bases, a_bases).astype(np.uint8)
    eve_knows = intercepted & e_match

    # --- Bob ---
    b_bases = rng.integers(0, 2, n, dtype=np.uint8)
    same = b_bases == state_bases
    b_bits = np.where(same, state_bits, rng.integers(0, 2, n, dtype=np.uint8)).astype(np.uint8)
    b_bits ^= (rng.random(n) < noise).astype(np.uint8)  # channel / detector noise

    # Decoy-state extensions
    if intensities is None:
        intensities = np.full(n, 0.5, dtype=np.float64)
    photon_numbers = rng.poisson(intensities)

    return Transmission(n, a_bits, a_bases, b_bases, b_bits, intercepted, eve_knows,
                        intensities, photon_numbers)


def sift(tx: Transmission) -> Sifted:
    """Keep only the qubits where Alice's and Bob's bases matched (announced publicly)."""
    keep = tx.alice_bases == tx.bob_bases
    return Sifted(
        positions=np.flatnonzero(keep),
        alice=tx.alice_bits[keep],
        bob=tx.bob_bits[keep],
        eve_knows=tx.eve_knows[keep],
        intensities=tx.intensities[keep] if tx.intensities is not None else None,
        photon_numbers=tx.photon_numbers[keep] if tx.photon_numbers is not None else None,
    )


def estimate_qber(
    s: Sifted, sample_fraction: float = 0.25, rng: np.random.Generator | None = None
) -> Estimation:
    """Publicly reveal a random sample of the sifted key to measure the error rate.

    The revealed bits are discarded. The upper bound adds 4 standard deviations
    of the binomial estimate (a simplification of a full finite-key analysis).
    """
    rng = rng or np.random.default_rng()
    m_total = len(s.alice)
    m = max(1, int(m_total * sample_fraction))
    pick = np.zeros(m_total, dtype=bool)
    pick[rng.choice(m_total, size=m, replace=False)] = True

    errors = s.alice[pick] != s.bob[pick]
    q = float(errors.mean())
    q_upper = qber_upper_bound(q, m)

    # For the sample and key arrays, we also need to carry intensities and photon_numbers if present.
    sample_intensities = s.intensities[pick] if s.intensities is not None else None
    sample_photon_numbers = s.photon_numbers[pick] if s.photon_numbers is not None else None
    key_intensities = s.intensities[~pick] if s.intensities is not None else None
    key_photon_numbers = s.photon_numbers[~pick] if s.photon_numbers is not None else None

    return Estimation(
        sample_positions=s.positions[pick],
        sample_errors=errors,
        qber=q,
        qber_upper=q_upper,
        alice_key=s.alice[~pick],
        bob_key=s.bob[~pick],
        eve_knows=s.eve_knows[~pick],
        positions=s.positions[~pick],
        intensities=key_intensities,
        photon_numbers=key_photon_numbers,
    )


def qber_trace(est: Estimation, n_total: int, bins: int = 16) -> list[dict]:
    """Error rate of the revealed sample across the stream (shows when an attack starts)."""
    order = np.argsort(est.sample_positions)
    pos = est.sample_positions[order]
    err = est.sample_errors[order]
    edges = np.linspace(0, n_total, bins + 1)
    out = []
    for i in range(bins):
        mask = (pos >= edges[i]) & (pos < edges[i + 1])
        cnt = int(mask.sum())
        out.append(
            {
                "bin": i,
                "start": int(edges[i]),
                "end": int(edges[i + 1]),
                "n": cnt,
                "qber": float(err[mask].mean()) if cnt else None,
            }
        )
    return out
