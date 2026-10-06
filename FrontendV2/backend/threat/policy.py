"""Security decision: Accept / Monitor / Reject (tasks 7 and optional extension).

Static policy (fixed thresholds):
    QBER < 6%                      -> ACCEPT   (channel noise only, key is usable)
    6% <= QBER < 11%               -> MONITOR  (suspicious or very noisy: use key, re-check, raise alert)
    QBER >= 11% or failed key verification -> REJECT (no security possible, record not sent)
    (noise so high that no 256-bit key survives, QBER < 11%, is MONITOR: nothing is sent, retry)

Adaptive policy: thresholds tighten as the classical threat score t (0..1) rises:
    accept_below = 6% - 3% * t       monitor_below = 11% - 4% * t
    and when t >= 0.8, a MONITOR verdict is escalated to REJECT.
A learned noise baseline (calibrated on a known-clean link) is also honoured:
QBER well above baseline + 4 sigma can never be ACCEPT.
"""
from __future__ import annotations

from dataclasses import dataclass

ACCEPT_QBER = 0.06
REJECT_QBER = 0.11


@dataclass
class Decision:
    verdict: str  # ACCEPT | MONITOR | REJECT
    reason: str
    accept_below: float
    reject_at: float
    description: str = ""


def decide(session: dict, threat: float | None = None, adaptive: bool = False,
           baseline_qber: float | None = None, baseline_sigma: float = 0.01) -> Decision:
    st = session["stats"]
    q = st.get("qber_est", 0.0)
    acc, rej = ACCEPT_QBER, REJECT_QBER
    desc = (
        "Final security decision using the adaptive threat-aware policy when adaptive=true; otherwise it follows the static policy."
        if adaptive
        else "Security decision using fixed QBER thresholds only."
    )

    if adaptive and threat is not None:
        acc = ACCEPT_QBER - 0.03 * threat
        rej = REJECT_QBER - 0.04 * threat
    if adaptive and baseline_qber is not None:
        acc = min(acc, baseline_qber + 4 * baseline_sigma)

    if session.get("status") != "secure" and q >= rej:
        return Decision("REJECT", f"QBER {q:.1%} >= {rej:.1%}: eavesdropping cannot be ruled out", acc, rej, desc)
    if q >= rej:
        return Decision("REJECT", f"QBER {q:.1%} >= {rej:.1%}: exceeds security threshold", acc, rej, desc)
    if session.get("status") != "secure":
        reason = session.get("reason") or "session failed"
        if "Secure key rate too low" in reason:
            return Decision("MONITOR", f"QBER {q:.1%} is noise-like but leaves no usable key: retry with more qubits", acc, rej, desc)
        return Decision("REJECT", reason, acc, rej, desc)
    if q < acc:
        return Decision("ACCEPT", f"QBER {q:.1%} < {acc:.1%}: consistent with channel noise", acc, rej, desc)
    if adaptive and threat is not None and threat >= 0.8:
        return Decision("REJECT", f"QBER {q:.1%} is in monitor range ({acc:.1%}-{rej:.1%}) and network threat is high ({threat:.0%}): escalated to REJECT", acc, rej, desc)
    return Decision("MONITOR", f"QBER {q:.1%} is between {acc:.1%} and {rej:.1%}: requires elevated monitoring", acc, rej, desc)

