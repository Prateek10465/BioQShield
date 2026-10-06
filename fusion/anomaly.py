"""Anomaly detection for QKD session telemetry.

This module provides functions to detect anomalies in QKD session telemetry
such as QBER trends, sift rate changes, and other statistical anomalies.
"""

from __future__ import annotations

import numpy as np
from typing import List, Dict, Tuple, Optional

from .link import LinkReport


def cusum_qber(qber_trace: List[Dict], threshold: float = 0.20, drift: float = 0.05) -> Tuple[bool, float]:
    """CUSUM (Cumulative Sum) detector for QBER changes.

    Args:
        qber_trace: List of binned QBER dictionaries from LinkReport.qber_trace
        threshold: Detection threshold (default 0.02 = 2% QBER change)
        drift: Drift parameter to detect small persistent changes (default 0.005)

    Returns:
        (anomaly_detected, cusum_score)
    """
    # Extract QBER values, filtering out None values
    qber_vals = []
    for bin_dict in qber_trace:
        qber = bin_dict.get("qber")
        if qber is not None:
            qber_vals.append(qber)

    if len(qber_vals) < 2:
        return False, 0.0

    # Initialize CUSUM
    # We'll detect increases in QBER (one-sided CUSUM for upward changes)
    # Target is the mean of the first half as baseline
    half = len(qber_vals) // 2
    if half < 1:
        half = 1
    baseline = np.mean(qber_vals[:half])

    # CUSUM algorithm
    s = 0.0
    max_s = 0.0
    for qber in qber_vals[half:]:
        # Accumulate deviation from baseline minus drift
        s = max(0, s + (qber - baseline - drift))
        max_s = max(max_s, s)

        # If we exceed threshold, anomaly detected
        if s > threshold:
            return True, s

    return False, max_s


def zscore_sift_rate(current_rate: float, baseline_rate: float, baseline_std: float) -> Tuple[bool, float]:
    """Z-score detector for sift rate changes.

    Args:
        current_rate: Current session sift rate
        baseline_rate: Historical baseline sift rate (mean)
        baseline_std: Historical baseline standard deviation

    Returns:
        (anomaly_detected, z_score)
    """
    if baseline_std <= 0:
        return False, 0.0

    z_score = abs(current_rate - baseline_rate) / baseline_std
    # Detect if z-score exceeds 3 (99.7% confidence for normal distribution)
    anomaly = z_score > 3.0
    return anomaly, z_score


def detect_temporal_anomaly(report: LinkReport, baseline_qber: float = 0.02,
                           baseline_qber_std: float = 0.005,
                           baseline_sift_rate: float = 0.5,
                           baseline_sift_rate_std: float = 0.05) -> Dict[str, any]:
    """Detect temporal anomalies in QKD session telemetry.

    Args:
        report: LinkReport containing session telemetry
        baseline_qber: Expected QBER baseline
        baseline_qber_std: Expected QBER standard deviation
        baseline_sift_rate: Expected sift rate baseline
        baseline_sift_rate_std: Expected sift rate standard deviation

    Returns:
        Dictionary with anomaly detection results
    """
    results = {
        "qber_cusum_anomaly": False,
        "qber_cusum_score": 0.0,
        "sift_rate_zscore_anomaly": False,
        "sift_rate_zscore": 0.0,
        "overall_anomaly": False,
        "anomaly_reasons": []
    }

    # CUSUM on QBER trace if available
    if report.qber_trace is not None and len(report.qber_trace) > 0:
        anomaly, score = cusum_qber(report.qber_trace)
        results["qber_cusum_anomaly"] = anomaly
        results["qber_cusum_score"] = score
        if anomaly:
            results["anomaly_reasons"].append("QBER CUSUM detected persistent increase")

    # Z-score on sift rate
    anomaly, zscore = zscore_sift_rate(report.sift_rate, baseline_sift_rate, baseline_sift_rate_std)
    results["sift_rate_zscore_anomaly"] = anomaly
    results["sift_rate_zscore"] = zscore
    if anomaly:
        results["anomaly_reasons"].append(f"Sift rate {report.sift_rate:.3f} deviates from baseline {baseline_sift_rate:.3f}")

    # Overall anomaly if any detector triggered
    results["overall_anomaly"] = results["qber_cusum_anomaly"] or results["sift_rate_zscore_anomaly"]

    return results


# Simple baseline class for link-specific baselines
class LinkBaseline:
    """Maintains baseline statistics for a link."""

    def __init__(self, decay: float = 0.98):
        self.decay = decay
        self.qber_errors = 0.0
        self.qber_bits = 0.0
        self.sift_count = 0.0
        self.total_qubits = 0.0
        self.ready = False

    @property
    def qber(self) -> float:
        return self.qber_errors / self.qber_bits if self.qber_bits > 0 else 0.0

    @property
    def sift_rate(self) -> float:
        return self.sift_count / self.total_qubits if self.total_qubits > 0 else 0.0

    @property
    def qber_std(self) -> float:
        # Approximate binomial std: sqrt(p*(1-p)/n)
        p = self.qber
        n = self.qber_bits
        if n > 0 and 0 < p < 1:
            return np.sqrt(p * (1 - p) / n)
        return 0.0

    @property
    def sift_rate_std(self) -> float:
        # Approximate binomial std for sift rate
        p = self.sift_rate
        n = self.total_qubits
        if n > 0 and 0 < p < 1:
            return np.sqrt(p * (1 - p) / n)
        return 0.0

    def update(self, qber: float, sample_size: int, sifted: int, total_qubits: int):
        """Update baseline with new session statistics."""
        self.qber_errors = self.qber_errors * self.decay + qber * sample_size
        self.qber_bits = self.qber_bits * self.decay + sample_size
        self.sift_count = self.sift_count * self.decay + sifted
        self.total_qubits = self.total_qubits * self.decay + total_qubits

        # Consider ready after enough samples
        if self.qber_bits > 1500:  # roughly two sessions worth
            self.ready = True

    def get_baselines(self) -> Tuple[float, float, float, float]:
        """Return (qber_mean, qber_std, sift_rate_mean, sift_rate_std)."""
        return (self.qber, self.qber_std, self.sift_rate, self.sift_rate_std)