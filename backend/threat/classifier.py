"""Simple normal-vs-attack classifier (task 2)."""
from __future__ import annotations

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score

from .nslkdd import load_raw, preprocess


def train_classifier(seed: int = 0):
    train, test, source = load_raw(seed)
    Xtr, ytr, Xte, yte, ct = preprocess(train, test)
    clf = RandomForestClassifier(n_estimators=100, max_depth=20, n_jobs=-1, random_state=seed)
    clf.fit(Xtr, ytr)
    pred = clf.predict(Xte)
    metrics = {
        "source": source,
        "n_train": int(len(ytr)), "n_test": int(len(yte)),
        "accuracy": float(accuracy_score(yte, pred)),
        "precision": float(precision_score(yte, pred)),
        "recall": float(recall_score(yte, pred)),
        "f1": float(f1_score(yte, pred)),
        "confusion_matrix": confusion_matrix(yte, pred).tolist(),
    }
    return clf, ct, (Xte, yte), metrics


def threat_score(clf, X: np.ndarray, flag_at: float = 0.5) -> dict:
    """Aggregate per-flow attack probabilities over a window of flows into one 0..1 score.
    Score = fraction of flows flagged as attack (robust to a few misclassified flows)."""
    p = clf.predict_proba(X)[:, 1]
    return {"score": float((p >= flag_at).mean()), "mean_prob": float(p.mean()), "n_flows": int(len(p))}
