import numpy as np

from backend.pipeline import run_session
from threat.classifier import train_classifier
from threat.nslkdd import load_raw, preprocess
from threat.policy import decide


def test_preprocess_shapes_and_labels():
    tr, te, _ = load_raw()
    Xtr, ytr, Xte, yte, _ = preprocess(tr, te)
    assert Xtr.shape[1] == Xte.shape[1]
    assert set(np.unique(ytr)) == {0, 1}
    assert not np.isnan(Xtr).any()


def test_classifier_beats_chance():
    _, _, _, m = train_classifier()
    assert m["accuracy"] > 0.9


def test_decisions():
    assert decide(run_session(noise=0.02, seed=1)).verdict == "ACCEPT"
    assert decide(run_session(eve=True, seed=1)).verdict == "REJECT"
    assert decide(run_session(noise=0.09, seed=1)).verdict == "MONITOR"


def test_adaptive_tightens_with_threat():
    s = run_session(noise=0.05, seed=2)
    assert decide(s, threat=0.0, adaptive=True).verdict in ("ACCEPT", "MONITOR")
    assert decide(s, threat=0.95, adaptive=True).verdict == "REJECT"
