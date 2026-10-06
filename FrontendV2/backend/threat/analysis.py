"""How channel conditions affect key security (task 6): QBER and secret key vs noise / Eve."""
from __future__ import annotations

import numpy as np

from backend.pipeline import run_session
from .policy import decide


def sweep(noises, eve_rates, seeds=(0, 1, 2), n_qubits=8192) -> list[dict]:
    out = []
    for nz in noises:
        for er in eve_rates:
            qs, ks, vs = [], [], []
            for sd in seeds:
                s = run_session(n_qubits=n_qubits, noise=nz, eve=er > 0, eve_rate=er, seed=1000 * sd + int(nz * 1e3) + int(er * 100))
                qs.append(s["stats"]["qber_est"])
                ks.append(s["stats"].get("final_key_bits", 0))
                vs.append(decide(s).verdict)
            verdict = max(set(vs), key=vs.count)
            out.append({"noise": nz, "eve_rate": er, "qber": float(np.mean(qs)),
                        "key_bits": float(np.mean(ks)), "verdict": verdict})
    return out
