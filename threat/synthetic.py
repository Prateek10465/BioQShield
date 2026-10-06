"""A synthetic stand-in with NSL-KDD's schema. NOT NSL-KDD and NOT real traffic.

Why this exists: the real files come from Kaggle and must be downloaded by you. This
generator lets the whole pipeline (loader, preprocessing, classifier, QKD decision) run
and be tested without them. It draws normal traffic and four attack families (DoS, Probe,
R2L, U2R) from hand-written distributions loosely modelled on how those families look in
KDD data (SYN floods have S0 flags and huge counts, smurf is ICMP echo, scans touch many
services, password guessing fails logins, ...). The test split deliberately contains
overlap and attack variants that are absent from the training split, as KDDTest+ does.

Any accuracy figure measured on this data says nothing about NSL-KDD.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .nslkdd import ATTACK_CATEGORY, FEATURES

SERVICES = ["http", "smtp", "ftp", "ftp_data", "domain_u", "private", "telnet", "ssh", "pop_3", "other", "ecr_i", "eco_i"]
NORMAL_FLAGS = ["SF"] * 9 + ["REJ", "S1"]


def _base(n: int) -> dict:
    d = {c: np.zeros(n) for c in FEATURES}
    d.update({c: np.array(["tcp"] * n, dtype=object) for c in ("protocol_type",)})
    d["service"] = np.array(["http"] * n, dtype=object)
    d["flag"] = np.array(["SF"] * n, dtype=object)
    return d


def _normal(n: int, rng: np.random.Generator, hard: bool) -> tuple[dict, list[str]]:
    d = _base(n)
    d["protocol_type"] = rng.choice(["tcp", "udp", "icmp"], n, p=[0.8, 0.17, 0.03]).astype(object)
    d["service"] = rng.choice(SERVICES[:10], n, p=[0.45, 0.1, 0.05, 0.1, 0.1, 0.05, 0.03, 0.04, 0.04, 0.04]).astype(object)
    d["flag"] = rng.choice(NORMAL_FLAGS, n).astype(object)
    d["duration"] = rng.exponential(30, n) * (rng.random(n) < 0.3)
    d["src_bytes"] = rng.lognormal(5.5, 1.6, n)
    d["dst_bytes"] = rng.lognormal(7.0, 2.0, n)
    d["logged_in"] = (rng.random(n) < 0.7).astype(float)
    d["count"] = rng.integers(1, 40, n)
    d["srv_count"] = np.minimum(d["count"], rng.integers(1, 30, n))
    for c in ("same_srv_rate", "dst_host_same_srv_rate"):
        d[c] = np.clip(rng.normal(0.9, 0.15, n), 0, 1)
    d["diff_srv_rate"] = np.clip(rng.normal(0.05, 0.08, n), 0, 1)
    d["serror_rate"] = np.clip(rng.normal(0.02, 0.08, n), 0, 1)
    d["rerror_rate"] = np.clip(rng.normal(0.03, 0.1, n), 0, 1)
    d["dst_host_count"] = rng.integers(1, 256, n)
    d["dst_host_srv_count"] = rng.integers(1, 256, n)
    if hard:  # a slice of busy / odd-but-benign traffic that looks suspicious
        m = rng.random(n) < 0.08
        d["count"] = np.where(m, rng.integers(100, 400, n), d["count"])
        d["serror_rate"] = np.where(m, rng.uniform(0.3, 0.9, n), d["serror_rate"])
    return d, ["normal"] * n


def _attack(kind: str, n: int, rng: np.random.Generator, variant: str) -> tuple[dict, list[str]]:
    d, _ = _normal(n, rng, hard=False)  # start from ordinary traffic, then override what the attack changes
    names = [variant] * n
    if kind == "DoS":
        if variant == "neptune":  # SYN flood
            d["flag"] = rng.choice(["S0", "S0", "S0", "REJ"], n).astype(object)
            d["service"] = rng.choice(["private", "http", "other"], n).astype(object)
            d["count"] = rng.integers(100, 511, n)
            d["srv_count"] = rng.integers(5, 30, n)
            d["serror_rate"] = np.clip(rng.normal(0.95, 0.1, n), 0, 1)
            d["srv_serror_rate"] = d["serror_rate"]
            d["dst_host_serror_rate"] = np.clip(rng.normal(0.95, 0.1, n), 0, 1)
            d["same_srv_rate"] = np.clip(rng.normal(0.1, 0.1, n), 0, 1)
        else:  # smurf / pod style ICMP flood
            d["protocol_type"] = np.array(["icmp"] * n, dtype=object)
            d["service"] = np.array(["ecr_i"] * n, dtype=object)
            d["src_bytes"] = rng.choice([1032.0, 520.0, 1480.0], n)
            d["count"] = rng.integers(200, 511, n)
            d["srv_count"] = d["count"]
            d["same_srv_rate"] = np.ones(n)
            d["dst_host_same_srv_rate"] = np.ones(n)
            d["wrong_fragment"] = (rng.random(n) < 0.3) * 1.0
        d["dst_host_count"] = rng.integers(200, 256, n)
    elif kind == "Probe":
        d["protocol_type"] = rng.choice(["tcp", "icmp"], n, p=[0.7, 0.3]).astype(object)
        d["service"] = rng.choice(SERVICES, n).astype(object)
        d["flag"] = rng.choice(["REJ", "RSTO", "SF", "S0"], n, p=[0.5, 0.2, 0.2, 0.1]).astype(object)
        d["src_bytes"] = rng.choice([0.0, 8.0, 18.0, 42.0], n)
        d["count"] = rng.integers(1, 120, n)
        d["rerror_rate"] = np.clip(rng.normal(0.7, 0.25, n), 0, 1)
        d["diff_srv_rate"] = np.clip(rng.normal(0.6, 0.25, n), 0, 1)
        d["dst_host_diff_srv_rate"] = np.clip(rng.normal(0.5, 0.25, n), 0, 1)
        d["dst_host_srv_count"] = rng.integers(1, 40, n)
        d["dst_host_count"] = rng.integers(1, 256, n)
    elif kind == "R2L":
        d["service"] = rng.choice(["ftp", "telnet", "ssh", "pop_3", "http"], n).astype(object)
        d["src_bytes"] = rng.lognormal(5.0, 1.2, n)
        d["dst_bytes"] = rng.lognormal(6.0, 1.5, n)
        d["duration"] = rng.exponential(5, n)
        d["num_failed_logins"] = rng.integers(0, 5, n)
        d["hot"] = rng.integers(0, 6, n)
        d["is_guest_login"] = (rng.random(n) < 0.4) * 1.0
        d["logged_in"] = (rng.random(n) < 0.5) * 1.0
        d["count"] = rng.integers(1, 12, n)
        d["same_srv_rate"] = np.clip(rng.normal(0.85, 0.2, n), 0, 1)
    else:  # U2R
        d["service"] = rng.choice(["telnet", "ftp_data", "ssh", "other"], n).astype(object)
        d["logged_in"] = np.ones(n)
        d["root_shell"] = (rng.random(n) < 0.6) * 1.0
        d["num_root"] = rng.integers(0, 12, n)
        d["num_compromised"] = rng.integers(0, 6, n)
        d["num_file_creations"] = rng.integers(0, 10, n)
        d["num_shells"] = (rng.random(n) < 0.3) * 1.0
        d["src_bytes"] = rng.lognormal(6.0, 1.5, n)
        d["dst_bytes"] = rng.lognormal(7.0, 1.5, n)
        d["duration"] = rng.exponential(60, n)
        d["count"] = rng.integers(1, 6, n)
    return d, names


TRAIN_MIX = {  # (category, variant): weight
    ("DoS", "neptune"): 0.40, ("DoS", "smurf"): 0.25, ("Probe", "portsweep"): 0.15,
    ("Probe", "satan"): 0.08, ("R2L", "guess_passwd"): 0.08, ("U2R", "buffer_overflow"): 0.04,
}
TEST_MIX = {  # shifted: fewer floods, more of the hard families, plus variants the model never saw
    ("DoS", "neptune"): 0.22, ("DoS", "smurf"): 0.08, ("Probe", "portsweep"): 0.12,
    ("Probe", "mscan"): 0.14, ("R2L", "guess_passwd"): 0.14, ("R2L", "warezmaster"): 0.14,
    ("U2R", "buffer_overflow"): 0.06, ("U2R", "rootkit"): 0.10,
}


def generate(n: int = 6000, attack_fraction: float = 0.46, seed: int = 0, shifted: bool = False) -> pd.DataFrame:
    """Draw `n` synthetic connections in NSL-KDD's schema (``shifted=True`` for the test mix)."""
    rng = np.random.default_rng(seed)
    n_att = int(n * attack_fraction)
    parts: list[pd.DataFrame] = []

    d, lab = _normal(n - n_att, rng, hard=shifted)
    parts.append(_frame(d, lab, "normal"))
    mix = TEST_MIX if shifted else TRAIN_MIX
    keys, w = list(mix), np.array(list(mix.values()))
    counts = rng.multinomial(n_att, w / w.sum())
    for (cat, variant), k in zip(keys, counts):
        if k:
            d, lab = _attack(cat, int(k), rng, variant)
            # Blur the boundary so neither split is trivially separable. The test split is blurrier.
            _blend_toward_normal(d, rng, strength=0.35 if shifted else 0.12)
            parts.append(_frame(d, lab, cat))
    df = pd.concat(parts, ignore_index=True).sample(frac=1.0, random_state=seed).reset_index(drop=True)
    return df


def _blend_toward_normal(d: dict, rng: np.random.Generator, strength: float) -> None:
    n = len(d["count"])
    m = rng.random(n) < strength  # this share of attack rows looks like ordinary traffic
    d["flag"] = np.where(m, "SF", d["flag"]).astype(object)
    d["serror_rate"] = np.where(m, rng.uniform(0, 0.1, n), d["serror_rate"])
    d["rerror_rate"] = np.where(m, rng.uniform(0, 0.1, n), d["rerror_rate"])
    d["count"] = np.where(m, rng.integers(1, 30, n), d["count"])
    d["num_failed_logins"] = np.where(m, 0, d["num_failed_logins"])
    d["root_shell"] = np.where(m, 0, d["root_shell"])


def _frame(d: dict, labels: list[str], category: str) -> pd.DataFrame:
    df = pd.DataFrame({c: d[c] for c in FEATURES})
    df["label"] = labels
    df["y"] = int(category != "normal")
    df["category"] = category
    return df


def write_nslkdd_txt(df: pd.DataFrame, path: str | Path) -> None:
    """Write in the original KDDTrain+.txt layout (no header, 41 features, label, difficulty)."""
    out = df[FEATURES].copy()
    out["label"] = df["label"]
    out["difficulty"] = 0
    out.to_csv(path, header=False, index=False)


__all__ = ["generate", "write_nslkdd_txt", "ATTACK_CATEGORY"]
