"""Threat classifier + QKD layer working together (task 8)."""
from __future__ import annotations

import numpy as np

try:
    from backend.pipeline import run_session
except ImportError:
    from pipeline import run_session
from .classifier import threat_score
from .policy import decide


def sample_window(X, y, kind: str, n: int, rng) -> np.ndarray:
    """Draw a window of flows: 'benign' = normal traffic, 'attack' = mostly attack flows."""
    p_attack = {"benign": 0.03, "mixed": 0.4, "attack": 0.9}[kind]
    n_att = int(n * p_attack)
    ia = rng.choice(np.flatnonzero(y == 1), n_att)
    ib = rng.choice(np.flatnonzero(y == 0), n - n_att)
    return X[np.concatenate([ia, ib])]


SCENARIOS = [
    # name, traffic, noise, eve
    ("Normal traffic, clean link",     "benign", 0.02, False),
    ("Normal traffic, noisy link",     "benign", 0.05, False),
    ("Normal traffic, very noisy",     "benign", 0.08, False),
    ("Attack traffic, clean link",     "attack", 0.02, False),
    ("Attack traffic, noisy link",     "attack", 0.05, False),
    ("Normal traffic, Eve on link",    "benign", 0.02, True),
    ("Attack traffic, Eve on link",    "attack", 0.02, True),
]


def run_scenarios(clf, X, y, seed: int = 1, n_qubits: int = 8192, window: int = 300) -> list[dict]:
    rng = np.random.default_rng(seed)
    rows = []
    for i, (name, traffic, noise, eve) in enumerate(SCENARIOS):
        t = threat_score(clf, sample_window(X, y, traffic, window, rng))
        s = run_session(n_qubits=n_qubits, noise=noise, eve=eve, seed=seed * 100 + i)
        stat = decide(s, adaptive=False)
        adap = decide(s, threat=t["score"], adaptive=True)
        rows.append({
            "scenario": name, "threat": t["score"], "qber": s["stats"]["qber_est"],
            "key_bits": s["stats"].get("final_key_bits", 0),
            "static": stat.verdict, "adaptive": adap.verdict, "reason": adap.reason,
        })
    return rows
