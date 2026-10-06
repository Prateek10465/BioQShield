"""What happens to qubits on the fibre: Eve, noise, and Bob's detectors.

These are the same measurement statistics as `bb84.transmit`, split into the three
pieces that live in different places in network mode:

  * `eve_intercept` and `apply_noise` run in the link service (the fibre),
  * `measure` runs at the end of the fibre (Bob's detector, driven by Bob's bases).

Bits and bases are shipped as base64-packed bit arrays (`pack_bits` / `unpack_bits`).
"""
from __future__ import annotations

import base64

import numpy as np


def pack_bits(bits: np.ndarray) -> str:
    return base64.b64encode(np.packbits(bits.astype(np.uint8)).tobytes()).decode()


def unpack_bits(data: str, n: int) -> np.ndarray:
    raw = np.frombuffer(base64.b64decode(data), dtype=np.uint8)
    out = np.unpackbits(raw)[:n]
    if len(out) != n:
        raise ValueError(f"expected {n} bits, got {len(out)}")
    return out.astype(np.uint8)


def eve_intercept(
    bits: np.ndarray,
    bases: np.ndarray,
    rate: float,
    start: float,
    rng: np.random.Generator,
):
    """Intercept-resend attack on a fraction `rate` of the qubits after position `start`.

    Eve measures in a random basis and resends what she saw in that basis. When her
    basis differs from Alice's she disturbs the state (Bob then errs half the time).
    Returns (state_bits, state_bases, intercepted_mask, eve_knows_mask).
    """
    n = len(bits)
    intercepted = (rng.random(n) < rate) & (np.arange(n) >= int(start * n))
    e_bases = rng.integers(0, 2, n, dtype=np.uint8)
    e_match = e_bases == bases
    e_bits = np.where(e_match, bits, rng.integers(0, 2, n, dtype=np.uint8)).astype(np.uint8)
    out_bits = np.where(intercepted, e_bits, bits).astype(np.uint8)
    out_bases = np.where(intercepted, e_bases, bases).astype(np.uint8)
    return out_bits, out_bases, intercepted, intercepted & e_match


def apply_noise(bits: np.ndarray, noise: float, rng: np.random.Generator) -> np.ndarray:
    """Channel / detector noise: each bit flips with probability `noise`."""
    return (bits ^ (rng.random(len(bits)) < noise).astype(np.uint8)).astype(np.uint8)


def measure(
    state_bits: np.ndarray,
    state_bases: np.ndarray,
    measure_bases: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """Measure each qubit in the given basis. The wrong basis gives a uniformly random bit."""
    same = measure_bases == state_bases
    return np.where(same, state_bits, rng.integers(0, 2, len(state_bits), dtype=np.uint8)).astype(np.uint8)
