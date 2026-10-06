"""Security decision: Accept / Monitor / Reject.

Two ideas drive the design.

1. QBER is physics, the threat score is context.
   A key is only as safe as the error rate says. A classifier verdict about *network
   traffic* can make the policy stricter but can never make it looser: the 11% hard
   limit and the minimum-key check apply no matter how benign the traffic looks.

2. Noise and an eavesdropper are indistinguishable from one QBER number.
   BB84 must blame every error on Eve. The only things a policy can add are (a) context
   (what is this link's normal noise? what is the network doing?) and (b) statistics
   (is this reading significantly higher than usual, given how many bits were sampled?).

Actions:
  ACCEPT   use the key.
  MONITOR  key withheld and a confirmation session is run; repeated Monitors escalate to Reject.
           Used when the evidence is ambiguous: noise vs a partial eavesdropper, or no usable key.
  REJECT   discard the key, send nothing, and rotate keys if it was in use.

Static policy:   fixed QBER thresholds.
Adaptive policy: thresholds move with (i) the threat score and (ii) the link's own
                 measured noise baseline (see `LinkBaseline`).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

from quantum import postprocess as pp
from . import anomaly


class Action(str, Enum):
    ACCEPT = "ACCEPT"
    MONITOR = "MONITOR"
    REJECT = "REJECT"

    @property
    def severity(self) -> int:
        return ("ACCEPT", "MONITOR", "REJECT").index(self.value)


def _worst(a: Action, b: Action) -> Action:
    return a if a.severity >= b.severity else b


@dataclass(frozen=True)
class PolicyConfig:
    accept_qber: float = 0.05  # at or below this, noise is an ordinary explanation
    reject_qber: float = pp.QBER_ABORT_THRESHOLD  # 11%: no secret key exists above this
    min_key_bits: int = pp.MIN_KEY_BITS  # AES-256 needs 256 secret bits
    # threat context
    threat_elevated: float = 0.5  # above this, "elevated" (tightens the accept limit)
    threat_high: float = 0.8  # above this, "high" (Monitor band becomes Reject; clean QBER becomes Monitor)
    tighten: float = 0.5  # at threat 1.0 the accept limit shrinks by this fraction
    # adaptive baseline test
    z_monitor: float = 4.0  # QBER this many sigma above the link's own baseline -> Monitor
    z_reject: float = 8.0  # ... this many -> Reject
    min_excess: float = 0.01  # and at least this much higher in absolute terms
    accept_ceiling: float = 0.08  # a noisy link's accept limit may rise, but never past this
    escalate_after: int = 3  # consecutive Monitors before Monitor becomes Reject


@dataclass
class LinkBaseline:
    """A link's ordinary QBER and telemetry, learned from sessions that were accepted.

    Exponentially forgotten counts (error bits / sampled bits). The variance of the
    baseline is kept so that a baseline learned from little data is not over-trusted.
    """

    decay: float = 0.98
    errors: float = 0.0
    bits: float = 0.0
    sift_count: float = 0.0
    total_qubits: float = 0.0

    @property
    def ready(self) -> bool:
        return self.bits >= 1500  # roughly two sessions' worth of samples

    @property
    def qber(self) -> float:
        return self.errors / self.bits if self.bits else 0.0

    @property
    def qber_std(self) -> float:
        if not self.ready or self.bits <= 0:
            return 0.0
        p = self.qber
        return math.sqrt(p * (1 - p) / self.bits)

    @property
    def sift_rate(self) -> float:
        return self.sift_count / self.total_qubits if self.total_qubits else 0.0

    @property
    def sift_rate_std(self) -> float:
        if not self.ready or self.total_qubits <= 0:
            return 0.0
        p = self.sift_rate
        return math.sqrt(p * (1 - p) / self.total_qubits)

    def update(self, qber: float, sample_size: int, sifted: int, total_qubits: int) -> None:
        self.errors = self.errors * self.decay + qber * sample_size
        self.bits = self.bits * self.decay + sample_size
        self.sift_count = self.sift_count * self.decay + sifted
        self.total_qubits = self.total_qubits * self.decay + total_qubits

    def z_score(self, qber: float, sample_size: int) -> float:
        """How many standard deviations `qber` sits above the baseline (binomial model)."""
        if not self.ready or sample_size <= 0:
            return 0.0
        b = min(max(self.qber, 0.002), 0.5)
        sigma = math.sqrt(b * (1 - b) * (1 / sample_size + 1 / self.bits))
        return (qber - b) / sigma

    def z_score_sift_rate(self, sifted: int, total_qubits: int) -> float:
        """How many standard deviations `sifted/total_qubits` sits above the baseline (binomial model)."""
        if not self.ready or total_qubits <= 0:
            return 0.0
        p = self.sift_rate
        # Binomial standard deviation for the difference between current session and baseline
        sigma = math.sqrt(p * (1 - p) * (1 / total_qubits + 1 / self.total_qubits))
        if sigma == 0:
            return 0.0
        current_rate = sifted / total_qubits if total_qubits > 0 else 0.0
        return (current_rate - p) / sigma


@dataclass
class Decision:
    action: Action
    reasons: list[str]
    mode: str
    qber: float
    threat: float | None
    accept_limit: float
    reject_limit: float
    z: float = 0.0

    def line(self) -> str:
        return f"{self.action.value:<7}  {'; '.join(self.reasons)}"


@dataclass
class LinkController:
    """Stateful decision-maker for one link. `mode` is "static" or "adaptive"."""

    mode: str = "adaptive"
    cfg: PolicyConfig = field(default_factory=PolicyConfig)
    baseline: LinkBaseline = field(default_factory=LinkBaseline)
    consecutive_monitor: int = 0

    def calibrate(self, reports) -> None:
        """Seed the baseline from sessions known to be clean (commissioning the link)."""
        for r in reports:
            self.baseline.update(r.qber, r.sample_size, r.n_sifted, r.n_qubits)

    def decide(self, report, threat: float | None = None) -> Decision:
        if self.mode not in ("static", "adaptive"):
            raise ValueError("mode must be 'static' or 'adaptive'")
        c = self.cfg
        adaptive = self.mode == "adaptive"
        t = threat if (adaptive and threat is not None) else None
        q, m = report.qber, report.sample_size
        # Use the original n_sifted and n_qubits fields for the current session
        sifted = report.n_sifted
        total_qubits = report.n_qubits
        reasons: list[str] = []

        # ---- effective limits ------------------------------------------------------
        accept_limit = c.accept_qber
        if adaptive and self.baseline.ready:
            # A link that is normally a little noisy gets room for it, within a ceiling.
            accept_limit = min(c.accept_ceiling, max(c.accept_qber, self.baseline.qber + 0.03))
        if t is not None:
            # More threat, less benefit of the doubt: shrink the headroom *above the link's
            # own noise*, never below it (a limit under the noise floor would reject healthy links).
            floor = self.baseline.qber if self.baseline.ready else 0.0
            accept_limit = floor + max(accept_limit - floor, 0.0) * (1.0 - c.tighten * t)
        reject_limit = c.reject_qber  # never moved: this one is physics

        threat_high = t is not None and t >= c.threat_high
        threat_elev = t is not None and t >= c.threat_elevated
        z = self.baseline.z_score(q, m) if (adaptive and self.baseline.ready) else 0.0

        # ---- rules, strictest first -------------------------------------------------
        action = Action.ACCEPT
        if q > reject_limit:
            action = Action.REJECT
            reasons.append(f"QBER {q:.1%} above the {reject_limit:.0%} limit: no secret key can be trusted")
        else:
            # PNS violation check - must be able to override Accept
            if getattr(report, 'pns_violation', False):
                action = Action.REJECT
                reasons.append("Photon-number-splitting attack detected via decoy-state method")
            elif q > accept_limit:
                if threat_high:
                    action = Action.REJECT
                    reasons.append(
                        f"QBER {q:.1%} above accept limit {accept_limit:.1%} while network threat is high ({t:.2f})"
                    )
                else:
                    action = Action.MONITOR
                    reasons.append(f"QBER {q:.1%} above accept limit {accept_limit:.1%}: noise or a partial eavesdropper")
            if report.qber_upper > reject_limit and action is Action.ACCEPT:
                action = Action.MONITOR
                reasons.append(f"QBER upper bound {report.qber_upper:.1%} crosses {reject_limit:.0%}: sample too small to be sure")
            if adaptive and z >= c.z_monitor and (q - self.baseline.qber) >= c.min_excess:
                if z >= c.z_reject:
                    action = _worst(action, Action.REJECT)
                    reasons.append(f"QBER {z:.1f} sigma above this link's baseline {self.baseline.qber:.1%}: active disturbance")
                else:
                    action = _worst(action, Action.MONITOR)
                    reasons.append(f"QBER {z:.1f} sigma above this link's baseline {self.baseline.qber:.1%}")
            if report.key_bits < c.min_key_bits:
                # No usable key is not proof of an attack (could be noise or a short session),
                # so it is Monitor, and repeated Monitors escalate.
                action = _worst(action, Action.MONITOR)
                reasons.append(f"only {report.key_bits} secret bits left (need {c.min_key_bits}): no usable key from this session")
            if action is Action.ACCEPT and threat_high:
                action = Action.MONITOR
                reasons.append(f"QBER is clean but network threat is high ({t:.2f}): classical side may be under attack")

        # ---- Temporal anomaly detection -------------------------------------------------
        # Use the baseline from previous sessions to detect anomalies in the current session
        from . import anomaly
        # Initialize anomaly flag
        temporal_anomaly = False
        anomaly_reasons = []

        # Check QBER CUSUM if trace is available (only when LinkReport comes from run_link_session)
        if report.qber_trace is not None and len(report.qber_trace) > 0:
            qber_cusum_anomaly, qber_cusum_score = anomaly.cusum_qber(report.qber_trace)
            if qber_cusum_anomaly:
                temporal_anomaly = True
                anomaly_reasons.append("QBER CUSUM detected persistent increase")

        # Check sift rate Z-score - calculate from n_sifted/n_qubits to handle both run_link_session
        # and directly constructed LinkReport objects (as in tests)
        if report.n_qubits > 0:
            sift_rate = report.n_sifted / report.n_qubits
            # We need to create a temporary LinkReport-like object to pass to zscore_sift_rate
            # or calculate the z-score directly. Let's calculate it directly for simplicity.
            # The z_score_sift_rate function expects: current_rate, baseline_rate, baseline_std
            baseline_rate = self.baseline.sift_rate
            baseline_std = self.baseline.sift_rate_std
            if baseline_std > 0:
                z_score = abs(sift_rate - baseline_rate) / baseline_std
                # Detect if z-score exceeds 10 (to avoid false positives in early sessions)
                if z_score > 10.0:
                    temporal_anomaly = True
                    anomaly_reasons.append(f"Sift rate z-score {z_score:.2f} exceeds threshold")

        # If temporal anomaly detected and current action is ACCEPT, then escalate to MONITOR
        if temporal_anomaly and action == Action.ACCEPT:
            action = Action.MONITOR
            reasons.append("Temporal anomaly detected in session telemetry")
        # Add any anomaly reasons to the reasons list
        reasons.extend(anomaly_reasons)

        if action is Action.ACCEPT:
            reasons.append(f"QBER {q:.1%} within {accept_limit:.1%}, key {report.key_bits} bits")
            if threat_elev:
                reasons[-1] += f" (threat {t:.2f}: limit tightened)"

        # ---- Monitor escalation and baseline learning ---------------------------------
        if action is Action.MONITOR:
            self.consecutive_monitor += 1
            if self.consecutive_monitor >= c.escalate_after:
                action = Action.REJECT
                reasons.append(f"{self.consecutive_monitor} Monitor results in a row: escalated")
        else:
            self.consecutive_monitor = 0
        if adaptive and action is Action.ACCEPT and not threat_elev:
            self.baseline.update(q, m, sifted, total_qubits)  # only clean, accepted sessions teach the baseline

        return Decision(action, reasons, self.mode, q, t, accept_limit, reject_limit, z)  # t: the threat actually used
