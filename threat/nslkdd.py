"""NSL-KDD loading and preprocessing.

NSL-KDD describes network *connections* with 41 features, a label (``normal`` or a
named attack) and, in the original files, a "difficulty" score. It models threats only;
nothing in it is medical. Healthcare is the application context, not the data.

Accepted file layouts (Kaggle uploads differ, so the loader is tolerant):
  * ``KDDTrain+.txt`` / ``KDDTest+.txt``: no header, 43 columns (41 features, label, difficulty)
  * the same with 42 columns (no difficulty) or with a header row
  * Kaggle CSVs whose label column is called ``class`` / ``label`` / ``attack`` and holds
    ``normal`` / ``anomaly`` (or attack names)
Anything that is not ``normal`` counts as an attack.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

FEATURES = [
    "duration", "protocol_type", "service", "flag", "src_bytes", "dst_bytes", "land",
    "wrong_fragment", "urgent", "hot", "num_failed_logins", "logged_in", "num_compromised",
    "root_shell", "su_attempted", "num_root", "num_file_creations", "num_shells",
    "num_access_files", "num_outbound_cmds", "is_host_login", "is_guest_login", "count",
    "srv_count", "serror_rate", "srv_serror_rate", "rerror_rate", "srv_rerror_rate",
    "same_srv_rate", "diff_srv_rate", "srv_diff_host_rate", "dst_host_count",
    "dst_host_srv_count", "dst_host_same_srv_rate", "dst_host_diff_srv_rate",
    "dst_host_same_src_port_rate", "dst_host_srv_diff_host_rate", "dst_host_serror_rate",
    "dst_host_srv_serror_rate", "dst_host_rerror_rate", "dst_host_srv_rerror_rate",
]
CATEGORICAL = ["protocol_type", "service", "flag"]
# Heavy-tailed counts: log1p before scaling, otherwise a few huge flows dominate.
HEAVY_TAIL = ["duration", "src_bytes", "dst_bytes"]
# Constant (always 0) in NSL-KDD, so it carries no information.
DROP = ["num_outbound_cmds"]
NUMERIC = [c for c in FEATURES if c not in CATEGORICAL + HEAVY_TAIL + DROP]
LABEL_NAMES = ("class", "label", "attack", "attack_type", "labels")

ATTACK_CATEGORY = {
    **dict.fromkeys(
        ["back", "land", "neptune", "pod", "smurf", "teardrop", "apache2", "udpstorm",
         "processtable", "mailbomb", "worm"], "DoS"),
    **dict.fromkeys(["ipsweep", "nmap", "portsweep", "satan", "mscan", "saint"], "Probe"),
    **dict.fromkeys(
        ["ftp_write", "guess_passwd", "imap", "multihop", "phf", "spy", "warezclient",
         "warezmaster", "sendmail", "named", "snmpgetattack", "snmpguess", "xlock", "xsnoop",
         "httptunnel"], "R2L"),
    **dict.fromkeys(
        ["buffer_overflow", "loadmodule", "perl", "rootkit", "ps", "sqlattack", "xterm"], "U2R"),
}


def find_files(data_dir: str | Path) -> tuple[Path | None, Path | None]:
    """Locate the train and test files under `data_dir` (searched recursively)."""
    root = Path(data_dir)
    if not root.exists():
        return None, None
    files = [p for p in root.rglob("*") if p.suffix.lower() in (".txt", ".csv", ".arff") and p.is_file()]

    def pick(*needles: str) -> Path | None:
        for p in sorted(files):
            n = p.name.lower()
            if any(k in n for k in needles) and "20" not in n.replace("+", ""):  # skip *_20Percent*
                return p
        return None

    return pick("train"), pick("test")


def load_nslkdd(path: str | Path) -> pd.DataFrame:
    """Read one NSL-KDD file into a frame with the 41 features plus ``label``, ``y``, ``category``.

    ``y`` is 1 for attack, 0 for normal. ``label`` is NaN-free when the file has labels;
    a file without a label column (some Kaggle test splits) gets ``y = -1``.
    """
    path = Path(path)
    raw = pd.read_csv(path, header=None, low_memory=False)
    first = str(raw.iloc[0, 0]).strip().lower()
    has_header = first in {c.lower() for c in FEATURES} or first.isalpha()
    if has_header:
        raw = pd.read_csv(path, low_memory=False)
        raw.columns = [str(c).strip().lower() for c in raw.columns]
    else:
        ncol = raw.shape[1]
        if ncol == 43:
            raw.columns = FEATURES + ["label", "difficulty"]
        elif ncol == 42:
            raw.columns = FEATURES + ["label"]
        elif ncol == 41:
            raw.columns = FEATURES
        else:
            raise ValueError(f"{path.name}: expected 41-43 columns, found {ncol}")

    missing = [c for c in FEATURES if c not in raw.columns]
    if missing:
        raise ValueError(f"{path.name}: missing feature columns {missing[:5]}")

    label_col = next((c for c in LABEL_NAMES if c in raw.columns), None)
    df = raw[FEATURES].copy()
    for c in CATEGORICAL:
        df[c] = df[c].astype(str).str.strip().str.lower()
    for c in FEATURES:
        if c not in CATEGORICAL:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

    if label_col is None:
        df["label"], df["y"], df["category"] = "unknown", -1, "unknown"
    else:
        lab = raw[label_col].astype(str).str.strip().str.lower().str.rstrip(".")
        df["label"] = lab
        df["y"] = (lab != "normal").astype(int)
        df["category"] = [
            "normal" if x == "normal" else ATTACK_CATEGORY.get(x, "attack") for x in lab
        ]
    return df.reset_index(drop=True)


def build_preprocessor() -> ColumnTransformer:
    """One-hot the three categorical columns, log+scale byte counts, scale the rest.

    ``handle_unknown='ignore'`` matters: KDDTest+ contains service names never seen in
    KDDTrain+, and they must not crash the pipeline.
    """
    log_scale = Pipeline(
        [("log", FunctionTransformer(np.log1p, feature_names_out="one-to-one")),
         ("scale", StandardScaler())]
    )
    return ColumnTransformer(
        [
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL),
            ("log", log_scale, HEAVY_TAIL),
            ("num", StandardScaler(), NUMERIC),
        ],
        remainder="drop",  # drops num_outbound_cmds and the label columns
        verbose_feature_names_out=False,
    )


def describe(df: pd.DataFrame) -> dict:
    """Short summary used in reports: size, class balance, attack categories."""
    return {
        "rows": int(len(df)),
        "normal": int((df["y"] == 0).sum()),
        "attack": int((df["y"] == 1).sum()),
        "categories": df["category"].value_counts().to_dict(),
        "services": int(df["service"].nunique()),
    }
