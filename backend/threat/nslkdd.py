"""NSL-KDD loading and preprocessing (task 1).

Put the Kaggle files in data/ (KDDTrain+.txt / KDDTest+.txt, headerless, 43 columns;
or a CSV with a header and a 'class'/'label' column -- both are handled).
If no file is found, a SYNTHETIC stand-in with the same schema is generated so the
pipeline still runs. Synthetic numbers are NOT real NSL-KDD results.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

COLUMNS = [
    "duration", "protocol_type", "service", "flag", "src_bytes", "dst_bytes", "land",
    "wrong_fragment", "urgent", "hot", "num_failed_logins", "logged_in", "num_compromised",
    "root_shell", "su_attempted", "num_root", "num_file_creations", "num_shells",
    "num_access_files", "num_outbound_cmds", "is_host_login", "is_guest_login", "count",
    "srv_count", "serror_rate", "srv_serror_rate", "rerror_rate", "srv_rerror_rate",
    "same_srv_rate", "diff_srv_rate", "srv_diff_host_rate", "dst_host_count",
    "dst_host_srv_count", "dst_host_same_srv_rate", "dst_host_diff_srv_rate",
    "dst_host_same_src_port_rate", "dst_host_srv_diff_host_rate", "dst_host_serror_rate",
    "dst_host_srv_serror_rate", "dst_host_rerror_rate", "dst_host_srv_rerror_rate",
    "label", "difficulty",
]
CATEGORICAL = ["protocol_type", "service", "flag"]


def _read(path: Path) -> pd.DataFrame:
    first = path.open().readline()
    if first.split(",")[0].strip().lower() in ("duration",) or "class" in first.lower():
        df = pd.read_csv(path)
        df = df.rename(columns={"class": "label", "attack": "label"})
    else:
        df = pd.read_csv(path, header=None, names=COLUMNS)
    return df


def _synthetic(n: int, rng: np.random.Generator, attack_frac: float = 0.47) -> pd.DataFrame:
    """Rough NSL-KDD look-alike: DoS-like (SYN flood), probe-like and normal flows."""
    y = rng.random(n) < attack_frac
    kind = rng.choice(["dos", "probe", "r2l"], size=n, p=[0.6, 0.3, 0.1])
    df = pd.DataFrame(0.0, index=range(n), columns=COLUMNS[:-2])
    df["protocol_type"] = rng.choice(["tcp", "udp", "icmp"], n, p=[0.8, 0.12, 0.08])
    df["service"] = rng.choice(["http", "smtp", "ftp", "private", "domain_u", "ecr_i", "other"], n)
    df["flag"] = rng.choice(["SF", "S0", "REJ", "RSTO"], n, p=[0.7, 0.1, 0.1, 0.1])
    df["duration"] = rng.exponential(30, n) * (~y)
    df["src_bytes"] = np.where(y, rng.exponential(50, n), rng.lognormal(6, 1.5, n))
    df["dst_bytes"] = np.where(y, rng.exponential(30, n), rng.lognormal(7, 1.5, n))
    df["logged_in"] = ((~y) & (rng.random(n) < 0.8)).astype(float)
    df["count"] = np.where(y & (kind == "dos"), rng.integers(200, 511, n), rng.integers(1, 40, n))
    df["srv_count"] = np.where(y, rng.integers(50, 511, n), rng.integers(1, 30, n))
    sy = y & (kind == "dos")
    df["serror_rate"] = np.where(sy, rng.beta(9, 1, n), rng.beta(1, 15, n))
    df["srv_serror_rate"] = df["serror_rate"]
    df["rerror_rate"] = np.where(y & (kind == "probe"), rng.beta(6, 2, n), rng.beta(1, 20, n))
    df["same_srv_rate"] = np.where(y & (kind == "probe"), rng.beta(1, 6, n), rng.beta(8, 1, n))
    df["diff_srv_rate"] = np.where(y & (kind == "probe"), rng.beta(5, 3, n), rng.beta(1, 25, n))
    df["dst_host_count"] = np.where(y, rng.integers(150, 256, n), rng.integers(1, 255, n))
    df["dst_host_srv_count"] = np.where(y, rng.integers(1, 40, n), rng.integers(10, 256, n))
    df["dst_host_serror_rate"] = np.where(sy, rng.beta(9, 1, n), rng.beta(1, 15, n))
    df["dst_host_same_srv_rate"] = np.where(y, rng.beta(2, 4, n), rng.beta(6, 1.5, n))
    df["num_failed_logins"] = np.where(y & (kind == "r2l"), rng.integers(1, 5, n), 0)
    df["hot"] = np.where(y & (kind == "r2l"), rng.integers(0, 10, n), rng.integers(0, 2, n))
    # label noise so the task is not trivially separable
    flip = rng.random(n) < 0.03
    y = np.where(flip, ~y, y)
    df["label"] = np.where(y, "neptune", "normal")
    df["difficulty"] = 15
    return df


def load_raw(seed: int = 0) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    """Returns (train, test, source) where source is 'nsl-kdd' or 'synthetic'."""
    tr = next((p for p in (DATA_DIR / "KDDTrain+.txt", DATA_DIR / "KDDTrain+.csv", DATA_DIR / "Train_data.csv") if p.exists()), None)
    te = next((p for p in (DATA_DIR / "KDDTest+.txt", DATA_DIR / "KDDTest+.csv", DATA_DIR / "Test_data.csv") if p.exists()), None)
    if tr is not None and te is not None:
        return _read(tr), _read(te), "nsl-kdd"
    if tr is not None:  # only a train file: split it
        df = _read(tr).sample(frac=1, random_state=seed).reset_index(drop=True)
        k = int(0.8 * len(df))
        return df.iloc[:k], df.iloc[k:], "nsl-kdd"
    rng = np.random.default_rng(seed)
    return _synthetic(20000, rng), _synthetic(6000, rng, attack_frac=0.55), "synthetic"


def preprocess(train: pd.DataFrame, test: pd.DataFrame):
    """Binary label (0 normal, 1 attack), one-hot categoricals, scaled numerics.
    The encoder is fitted on train only; unseen test categories are ignored."""
    def split(df):
        df = df.drop(columns=[c for c in ("difficulty", "num_outbound_cmds") if c in df.columns])
        y = (df["label"].astype(str).str.strip().str.lower() != "normal").astype(int).to_numpy()
        return df.drop(columns=["label"]), y

    Xtr, ytr = split(train)
    Xte, yte = split(test)
    num = [c for c in Xtr.columns if c not in CATEGORICAL]
    ct = ColumnTransformer(
        [("num", StandardScaler(), num),
         ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL)]
    )
    return ct.fit_transform(Xtr), ytr, ct.transform(Xte), yte, ct
