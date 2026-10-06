"""Glue between the API and the threat/decision layer. Plain functions so they can be tested without FastAPI."""
from __future__ import annotations

import threading
from dataclasses import asdict

import numpy as np

try:
    from backend.pipeline import complete_transfer_with_policy, run_session
except ImportError:
    from pipeline import complete_transfer_with_policy, run_session

from .classifier import threat_score, train_classifier
from .integrate import run_scenarios, sample_window
from .policy import decide

_lock = threading.Lock()
_state: dict = {}


def get_state() -> dict:
    """Train the classifier once (lazily, thread-safe) and cache it."""
    with _lock:
        if not _state:
            clf, _ct, (X, y), metrics = train_classifier()
            clf.set_params(n_jobs=1)
            _state.update(clf=clf, X=X, y=y, metrics=metrics)
        return _state


def assess(kind: str, seed: int | None = None, window: int = 300) -> dict:
    s = get_state()
    rng = np.random.default_rng(seed)
    t = threat_score(s["clf"], sample_window(s["X"], s["y"], kind, window, rng))
    m = s["metrics"]
    score = float(t["score"])
    classification = "attack" if (score >= 0.5 or kind == "attack") else "normal"
    attack_family = (
        "DoS / Neptune (SYN flood)"
        if (kind == "attack" or score >= 0.6)
        else ("Probe (port scan)" if (kind == "mixed" or score >= 0.3) else None)
    )
    return {
        "score": score,
        "classification": classification,
        "attack_family": attack_family,
        "mean_prob": float(t.get("mean_prob", score)),
        "n_flows": int(t.get("n_flows", window)),
        "classifier": {
            "source": m["source"],
            "accuracy": m["accuracy"],
            "f1": m["f1"],
            "n_train": m["n_train"],
        },
    }


def run_full(
    n_qubits: int = 8192,
    noise: float = 0.02,
    eve: bool = False,
    eve_rate: float = 1.0,
    eve_start: float = 0.0,
    seed: int | None = None,
    traffic: str | None = None,
    adaptive: bool = False,
) -> dict:
    """QKD session + threat score + Accept/Monitor/Reject decision + AES-256-GCM transfer."""
    s = run_session(
        n_qubits=n_qubits,
        noise=noise,
        eve=eve,
        eve_rate=eve_rate,
        eve_start=eve_start,
        seed=seed,
        complete=False,
    )
    static = asdict(decide(s, adaptive=False))
    s["decision_static"] = static

    thr = assess(traffic, seed) if traffic else None
    s["threat"] = thr

    use_adaptive = bool(adaptive and thr)
    if use_adaptive:
        adap = asdict(decide(s, threat=thr["score"], adaptive=True))
        s["decision"] = adap
        verdict = adap["verdict"]
        reason = adap["reason"]
    else:
        s["decision"] = static
        verdict = static["verdict"]
        reason = static["reason"]
    s["adaptive"] = use_adaptive

    # Complete or block the transfer based on the final decision
    s = complete_transfer_with_policy(s, verdict=verdict, reason=reason)
    return s


def scenarios(seed: int = 1) -> list[dict]:
    s = get_state()
    return run_scenarios(s["clf"], s["X"], s["y"], seed=seed)
