"""Experiments for tasks 6-8: how channel conditions affect key security, and how the
policies respond. All sessions use the numpy BB84 engine (same statistics as Qiskit)."""
from __future__ import annotations

import copy

import numpy as np
import pandas as pd

from .link import run_link_session
from .policy import Action, LinkController, PolicyConfig


def sweep(
    noises=(0.0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.10, 0.12),
    eve_rates=(0.0, 0.1, 0.2, 0.3, 0.5, 1.0),
    repeats: int = 30,
    n_qubits: int = 8192,
    seed: int = 0,
) -> pd.DataFrame:
    """Static policy on a grid of channel noise x eavesdropper share. One row per (noise, eve)."""
    rows = []
    for i, noise in enumerate(noises):
        for j, eve in enumerate(eve_rates):
            reps = [run_link_session(n_qubits, noise, eve, seed=seed + 100_003 * i + 1009 * j + k) for k in range(repeats)]
            acts = [LinkController("static").decide(r).action for r in reps]
            rows.append(
                {
                    "noise": noise, "eve_rate": eve,
                    "qber": np.mean([r.qber for r in reps]), "qber_sd": np.std([r.qber for r in reps]),
                    "key_bits": np.mean([r.key_bits for r in reps]),
                    "p_accept": np.mean([a is Action.ACCEPT for a in acts]),
                    "p_monitor": np.mean([a is Action.MONITOR for a in acts]),
                    "p_reject": np.mean([a is Action.REJECT for a in acts]),
                }
            )
    return pd.DataFrame(rows)


def calibrated(mode: str, base_noise: float, n_qubits: int, seed: int, cfg: PolicyConfig | None = None, sessions: int = 10) -> LinkController:
    """A controller whose baseline was learned from `sessions` clean commissioning sessions."""
    ctl = LinkController(mode, cfg or PolicyConfig())
    ctl.calibrate([run_link_session(n_qubits, base_noise, 0.0, seed=seed + k) for k in range(sessions)])
    return ctl


SCENARIOS = [  # (label, noise, eve_rate)  -- the link's commissioning noise is 2%
    ("normal (2% noise)", 0.02, 0.0),
    ("benign drift to 3%", 0.03, 0.0),
    ("benign drift to 4%", 0.04, 0.0),
    ("Eve on 5% of photons", 0.02, 0.05),
    ("Eve on 10%", 0.02, 0.10),
    ("Eve on 20%", 0.02, 0.20),
    ("Eve on 50%", 0.02, 0.50),
    ("Eve on 100%", 0.02, 1.0),
]


def policy_comparison(trials: int = 300, n_qubits: int = 8192, base_noise: float = 0.02, seed: int = 7) -> pd.DataFrame:
    """Static vs adaptive: how often is each scenario flagged (Monitor or Reject)?

    Every trial starts from the same commissioned baseline, so trials are independent
    (no Monitor escalation, no baseline drift between them).
    """
    ctl_static = LinkController("static")
    ctl_adapt = calibrated("adaptive", base_noise, n_qubits, seed=seed)
    rows = []
    for si, (label, noise, eve) in enumerate(SCENARIOS):
        flag = {"static": 0, "adaptive": 0}
        rej = {"static": 0, "adaptive": 0}
        for k in range(trials):
            r = run_link_session(n_qubits, noise, eve, seed=seed * 1_000_003 + si * 10_007 + k)
            for name, ctl in (("static", ctl_static), ("adaptive", ctl_adapt)):
                d = copy.deepcopy(ctl).decide(r)  # copy: no state leaks between trials
                flag[name] += d.action is not Action.ACCEPT
                rej[name] += d.action is Action.REJECT
        rows.append(
            {"scenario": label, "eve": eve > 0, "noise": noise, "eve_rate": eve,
             "static_flagged": flag["static"] / trials, "adaptive_flagged": flag["adaptive"] / trials,
             "static_rejected": rej["static"] / trials, "adaptive_rejected": rej["adaptive"] / trials}
        )
    return pd.DataFrame(rows)


QUANTUM_CASES = [  # what is physically happening on the fibre (set by the experimenter, never by the classifier)
    ("clean fibre", 0.02, 0.0),
    ("noisy fibre (4%)", 0.04, 0.0),
    ("partial Eve (10%)", 0.02, 0.10),
    ("full Eve", 0.02, 1.0),
]


def threat_matrix(
    threat_levels: dict[str, float], n_qubits: int = 8192, base_noise: float = 0.02, seed: int = 11, engine: str = "numpy"
) -> pd.DataFrame:
    """Same quantum session, different network-threat context: where does the decision change?"""
    rows = []
    for ci, (qlabel, noise, eve) in enumerate(QUANTUM_CASES):
        report = run_link_session(n_qubits, noise, eve, seed=seed + ci, engine=engine)  # one session per case, shared across threat levels
        for tlabel, t in threat_levels.items():
            ctl = calibrated("adaptive", base_noise, n_qubits, seed=seed + 500)
            d = ctl.decide(report, threat=t)
            rows.append({"quantum": qlabel, "engine": report.engine, "traffic": tlabel, "threat": t, "qber": report.qber,
                         "key_bits": report.key_bits, "action": d.action.value, "why": "; ".join(d.reasons)})
    return pd.DataFrame(rows)


def timeline(phases, n_qubits: int = 4096, base_noise: float = 0.02, seed: int = 21, engine: str = "numpy") -> pd.DataFrame:
    """A link over time. `phases` is a list of (label, n_sessions, noise, eve_rate, threat).

    One adaptive controller sees every session in order, so Monitor streaks escalate and the
    noise baseline is learned only from accepted, low-threat sessions.
    """
    ctl = calibrated("adaptive", base_noise, n_qubits, seed=seed + 900)
    rows, t = [], 0
    for label, count, noise, eve, threat in phases:
        for _ in range(count):
            r = run_link_session(n_qubits, noise, eve, seed=seed + t, engine=engine)
            d = ctl.decide(r, threat=threat)
            rows.append({"session": t + 1, "phase": label, "noise": noise, "eve_rate": eve, "threat": threat,
                         "qber": r.qber, "key_bits": r.key_bits, "accept_limit": d.accept_limit,
                         "baseline": ctl.baseline.qber, "z": d.z, "action": d.action.value, "why": "; ".join(d.reasons)})
            t += 1
    return pd.DataFrame(rows)
