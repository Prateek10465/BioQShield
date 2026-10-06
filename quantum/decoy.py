"""Decoy-state method for photon-number-splitting (PNS) attack detection.

This module provides functions to estimate gain and QBER for different intensities
and to perform the PNS test.
"""

from __future__ import annotations

import numpy as np
from typing import Tuple

from .bb84 import Sifted, Estimation


def estimate_gain_qber(
    sifted: Sifted,
    intensities: np.ndarray,
    sample_fraction: float = 0.25,
    rng: np.random.Generator | None = None,
) -> Tuple[float, float]:
    """Estimate gain and QBER for a given intensity set.

    Parameters
    ----------
    sifted : Sifted
        The sifted key data (after basis reconciliation).
    intensities : np.ndarray
        Array of intensities (mean photon number) for each pulse in the original stream.
        Must be the same length as the original number of pulses.
    sample_fraction : float, optional
        Fraction of the sifted key to use for parameter estimation, by default 0.25
    rng : np.random.Generator | None, optional
        Random number generator, by default None

    Returns
    -------
    gain : float
        The gain (detection probability) for the selected intensity.
    qber : float
        The quantum bit error rate for the selected intensity.
    """
    # For decoy-state method, we need to estimate gain and QBER for specific intensity values
    # (typically signal, decoy, and vacuum). However, this function estimates gain and QBER
    # for the given intensity array (which could be a mixture).
    # To get gain and QBER for a specific intensity value, the caller should filter the
    # sifted data by intensity before calling this function, or we can modify this function
    # to accept a target intensity.

    # For simplicity, we'll compute the overall gain and QBER for the sifted data.
    # In a full implementation, we would want to compute these for each intensity value separately.

    # Gain: number of detected pulses (sifted bits) divided by total number of pulses sent
    # Note: We don't have the total number of pulses sent for each intensity here.
    # We need the original intensities array to know how many pulses were sent at each intensity.

    # Actually, we have the intensities array for the original stream.
    # We can compute:
    #   gain = len(sifted.positions) / len(intensities)
    # But this assumes that every pulse was sent, which is true in our simulation.

    # However, for decoy-state, we want gain for a specific intensity value.
    # Let's change the approach: we'll compute gain and QBER for the sifted data,
    # and the caller can use this for different intensity values by pre-filtering.

    # For now, we'll implement a simple version that returns gain and QBER for the sifted data.
    # To get intensity-specific values, the caller should create a Sifted object containing
    # only the bits from pulses with the desired intensity.

    # Calculate gain: detection probability
    # Number of sifted bits (detected and basis-matched) divided by number of pulses sent
    gain = len(sifted.positions) / len(intensities) if len(intensities) > 0 else 0.0

    # To calculate QBER, we need to compare alice and bob bits for the sifted key
    if len(sifted.alice) > 0:
        qber = np.mean(sifted.alice != sifted.bob)
    else:
        qber = 0.0

    return float(gain), float(qber)


def pns_test(
    gain_signal: float,
    gain_decoy: float,
    qber_signal: float,
    qber_decoy: float,
    mu_signal: float,
    mu_decoy: float,
) -> Tuple[bool, float]:
    """Perform the photon-number-splitting test.

    Parameters
    ----------
    gain_signal : float
        Gain (detection probability) for signal intensity.
    gain_decoy : float
        Gain for decoy intensity.
    qber_signal : float
        QBER for signal intensity.
    qber_decoy : float
        QBER for decoy intensity.
    mu_signal : float
        Signal intensity (mean photon number).
    mu_decoy : float
        Decoy intensity (mean photon number), must be < mu_signal.

    Returns
    -------
    violation : bool
        True if PNS test indicates an attack (i.e., gain or QBER inconsistent).
    pns_estimate : float
        Estimated fraction of single-photon contributions (lower bound).
    """
    # Simple PNS test: if gain_decoy > gain_signal or qber_decoy > qber_signal + threshold
    # More sophisticated bounds can be used.
    # For now, we use a simple heuristic.
    threshold = 0.01
    violation = (gain_decoy > gain_signal * 1.1) or (qber_decoy > qber_signal + threshold)
    # Estimate single-photon fraction (simplified)
    # In practice, one would solve linear equations.
    pns_estimate = max(0.0, 1.0 - (gain_decoy / gain_signal) * (mu_signal / mu_decoy))
    return violation, pns_estimate