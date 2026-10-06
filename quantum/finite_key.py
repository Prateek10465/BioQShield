"""Composable finite-key security bound for QKD following Tomamichel et al.

This module implements the finite-key secret key length calculation using
the composable security framework from Tomamichel et al. (2012).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple

from .bb84 import h2


@dataclass
class FiniteKeyParameters:
    """Parameters for the finite-key security bound."""
    epsilon_sec: float = 1e-9      # secrecy parameter
    epsilon_corr: float = 1e-9     # correctness parameter
    epsilon_hash: float = 1e-9     # hashing parameter for privacy amplification
    epsilon_smooth: float = 1e-9   # smoothing parameter
    # Derived parameters
    epsilon_total: float = 0.0     # will be computed

    def __post_init__(self):
        # Total error probability: ε_sec + ε_corr + ε_hash + ε_smooth
        self.epsilon_total = self.epsilon_sec + self.epsilon_corr + self.epsilon_hash + self.epsilon_smooth


def finite_key_secret_key_length(
    n_sifted: int,
    qber: float,
    leaked_bits: int,
    n_sample: int | None = None,
    params: FiniteKeyParameters | None = None
) -> Tuple[int, dict]:
    """Compute secret key length using composable finite-key bounds.

    Implements the Tomamichel bound:
    ℓ ≤ n_sifted [1 - h2(Q+δ)] - λ_EC - 2 log2(1/(2 ε_sec)) - log2(1/ε_hash)
    with δ = sqrt( (ln(1/ε^2))/(2 n_sample) ) for Hoeffding's inequality.

    Parameters
    ----------
    n_sifted : int
        Number of sifted bits
    qber : float
        Quantum bit error rate (measured or upper bound)
    leaked_bits : int
        Number of bits leaked during error correction
    n_sample : int | None, optional
        Number of bits used for parameter estimation (default: n_sifted//4)
    params : FiniteKeyParameters | None, optional
        Finite-key parameters (default: uses default values)

    Returns
    -------
    key_length : int
        Secret key length in bits (non-negative)
    info : dict
        Additional information including:
        - delta: the statistical fluctuation
        - h2_term: h2(Q+δ)
        - security_params: the epsilon values used
        - bound_terms: breakdown of the bound calculation
    """
    if params is None:
        params = FiniteKeyParameters()

    if n_sample is None:
        n_sample = max(1, n_sifted // 4)  # typical sample fraction

    # Statistical fluctuation for Hoeffding's inequality
    # δ = sqrt( (ln(1/ε^2))/(2 n_sample) )
    # Using ε = ε_sec + ε_corr + ε_hash (smoothing parameter handled separately)
    eps = params.epsilon_sec + params.epsilon_corr + params.epsilon_hash
    if eps <= 0.0:
        delta = 0.0
    else:
        delta = math.sqrt(math.log(1.0 / (eps * eps)) / (2.0 * n_sample))

    # QBER upper bound with statistical fluctuation
    qber_upper = min(0.5, qber + delta)

    # Calculate the bound terms
    # Term 1: n_sifted [1 - h2(Q+δ)]
    h2_term = h2(qber_upper)
    term1 = n_sifted * (1.0 - h2_term)

    # Term 2: - λ_EC (error correction leakage)
    term2 = -leaked_bits

    # Term 3: - 2 log2(1/(2 ε_sec))
    term3 = -2.0 * math.log2(1.0 / (2.0 * params.epsilon_sec)) if params.epsilon_sec > 0 else 0.0

    # Term 4: - log2(1/ε_hash)
    term4 = -math.log2(1.0 / params.epsilon_hash) if params.epsilon_hash > 0 else 0.0

    # Secret key length
    key_length_raw = term1 + term2 + term3 + term4
    key_length = max(0, int(math.floor(key_length_raw)))

    # Additional information
    info = {
        "delta": delta,
        "qber_upper": qber_upper,
        "h2_term": h2_term,
        "term1": term1,
        "term2": term2,
        "term3": term3,
        "term4": term4,
        "key_length_raw": key_length_raw,
        "security_params": {
            "epsilon_sec": params.epsilon_sec,
            "epsilon_corr": params.epsilon_corr,
            "epsilon_hash": params.epsilon_hash,
            "epsilon_smooth": params.epsilon_smooth,
            "epsilon_total": params.epsilon_total
        }
    }

    return key_length, info


def simple_secret_key_length(n: int, qber_upper: float, leaked_bits: int) -> int:
    """Original simplified secret key length for backward compatibility.

    l = n * (1 - h2(q_upper)) - leaked - 2*log2(1/eps)
    """
    from .postprocess import PA_SECURITY_BITS
    l = n * (1.0 - h2(qber_upper)) - leaked_bits - 2 * PA_SECURITY_BITS
    return max(0, int(math.floor(l)))


# Example usage and testing
if __name__ == "__main__":
    # Test with some example values
    n_sifted = 1000
    qber = 0.02
    leaked_bits = 200

    key_len, info = finite_key_secret_key_length(n_sifted, qber, leaked_bits)
    print(f"Finite-key secret key length: {key_len} bits")
    print(f"Delta: {info['delta']:.6f}")
    print(f"QBER upper: {info['qber_upper']:.6f}")

    # Compare with simple bound
    simple_len = simple_secret_key_length(n_sifted, info['qber_upper'], leaked_bits)
    print(f"Simple secret key length: {simple_len} bits")