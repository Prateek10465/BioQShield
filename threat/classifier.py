"""A deliberately simple normal-vs-attack classifier on NSL-KDD.

Preprocessing and model live in one scikit-learn Pipeline, so a model fitted on
KDDTrain+ can score raw KDDTest+ rows (or live flows) without any manual steps.
The output that the quantum layer uses is `attack_probability`, a number in [0, 1].
"""
from __future__ import annotations

from dataclasses import dataclass, field

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score,
)
from sklearn.pipeline import Pipeline

from .nslkdd import FEATURES, build_preprocessor


def make_model(kind: str = "rf", seed: int = 0):
    if kind == "rf":
        return RandomForestClassifier(
            n_estimators=150, min_samples_leaf=2, n_jobs=-1, random_state=seed
        )
    if kind == "logreg":
        return LogisticRegression(max_iter=2000, random_state=seed)
    raise ValueError(f"unknown model kind {kind!r} (use 'rf' or 'logreg')")


@dataclass
class ThreatClassifier:
    kind: str = "rf"
    seed: int = 0
    pipeline: Pipeline = field(init=False)

    def __post_init__(self) -> None:
        self.pipeline = Pipeline([("prep", build_preprocessor()), ("model", make_model(self.kind, self.seed))])

    def fit(self, df: pd.DataFrame) -> "ThreatClassifier":
        self.pipeline.fit(df[FEATURES], df["y"])
        return self

    def attack_probability(self, df: pd.DataFrame) -> np.ndarray:
        """P(attack) for each connection, from features only (no label is read)."""
        return self.pipeline.predict_proba(df[FEATURES])[:, 1]

    def predict(self, df: pd.DataFrame, threshold: float = 0.5) -> np.ndarray:
        return (self.attack_probability(df) >= threshold).astype(int)

    def evaluate(self, df: pd.DataFrame, threshold: float = 0.5) -> dict:
        y = df["y"].to_numpy()
        p = self.attack_probability(df)
        pred = (p >= threshold).astype(int)
        tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
        out = {
            "n": int(len(y)),
            "accuracy": float(accuracy_score(y, pred)),
            "precision": float(precision_score(y, pred, zero_division=0)),
            "recall": float(recall_score(y, pred, zero_division=0)),
            "f1": float(f1_score(y, pred, zero_division=0)),
            "roc_auc": float(roc_auc_score(y, p)) if len(set(y)) == 2 else float("nan"),
            "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        }
        if "category" in df:  # recall per attack family: where does the model miss?
            att = df[df["y"] == 1]
            out["recall_by_category"] = {
                c: float((pred[att.index[att["category"] == c]] == 1).mean())
                for c in sorted(att["category"].unique())
            }
        return out

    def top_features(self, k: int = 10) -> list[tuple[str, float]]:
        model = self.pipeline.named_steps["model"]
        names = self.pipeline.named_steps["prep"].get_feature_names_out()
        if hasattr(model, "feature_importances_"):
            w = model.feature_importances_
        else:
            w = np.abs(model.coef_[0])
        order = np.argsort(w)[::-1][:k]
        return [(str(names[i]), float(w[i])) for i in order]

    def save(self, path: str) -> None:
        joblib.dump(self, path)

    @staticmethod
    def load(path: str) -> "ThreatClassifier":
        return joblib.load(path)


def threat_score(probabilities: np.ndarray) -> float:
    """Collapse a window of per-connection attack probabilities into one score in [0, 1].

    The mean attack probability over the window: 0 means every connection looks normal,
    1 means every connection looks like an attack. (A max or percentile would react to one
    odd connection; the mean needs sustained suspicious traffic, which suits a link policy.)
    """
    p = np.asarray(probabilities, dtype=float)
    return float(np.clip(p.mean(), 0.0, 1.0)) if p.size else 0.0
