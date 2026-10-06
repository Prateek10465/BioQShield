import numpy as np
import pandas as pd
import pytest

from threat import nslkdd, synthetic
from threat.classifier import ThreatClassifier, threat_score


@pytest.fixture(scope="module")
def data():
    return synthetic.generate(3000, seed=1), synthetic.generate(1500, seed=2, shifted=True)


def test_txt_roundtrip_43_columns(tmp_path, data):
    train, _ = data
    synthetic.write_nslkdd_txt(train, tmp_path / "KDDTrain+.txt")
    back = nslkdd.load_nslkdd(tmp_path / "KDDTrain+.txt")
    assert len(back) == len(train)
    assert (back["y"].to_numpy() == train["y"].to_numpy()).all()
    assert set(back["category"]) == set(train["category"])
    assert list(back.columns[:41]) == nslkdd.FEATURES


def test_kaggle_style_csv_with_header_and_anomaly_label(tmp_path, data):
    train, _ = data
    df = train[nslkdd.FEATURES].copy()
    df["class"] = np.where(train["y"] == 1, "anomaly", "normal")
    df.to_csv(tmp_path / "Train_data.csv", index=False)
    back = nslkdd.load_nslkdd(tmp_path / "Train_data.csv")
    assert (back["y"].to_numpy() == train["y"].to_numpy()).all()


def test_file_without_labels_gets_minus_one(tmp_path, data):
    train, _ = data
    train[nslkdd.FEATURES].head(50).to_csv(tmp_path / "Test_data.csv", index=False)
    assert (nslkdd.load_nslkdd(tmp_path / "Test_data.csv")["y"] == -1).all()


def test_wrong_column_count_is_a_clear_error(tmp_path):
    pd.DataFrame(np.zeros((3, 10))).to_csv(tmp_path / "x.txt", header=False, index=False)
    with pytest.raises(ValueError, match="41-43 columns"):
        nslkdd.load_nslkdd(tmp_path / "x.txt")


def test_find_files_ignores_20percent_subset(tmp_path):
    for n in ("KDDTrain+.txt", "KDDTrain+_20Percent.txt", "KDDTest+.txt"):
        (tmp_path / n).write_text("x")
    tr, te = nslkdd.find_files(tmp_path)
    assert tr.name == "KDDTrain+.txt" and te.name == "KDDTest+.txt"


def test_preprocessor_handles_unseen_service_and_drops_constant(data):
    train, test = data
    prep = nslkdd.build_preprocessor().fit(train[nslkdd.FEATURES])
    odd = test.head(5).copy()
    odd["service"] = "never_seen_service"
    X = prep.transform(odd[nslkdd.FEATURES])  # must not raise
    assert X.shape[0] == 5 and np.isfinite(X).all()
    assert "num_outbound_cmds" not in prep.get_feature_names_out()


def test_classifier_is_far_better_than_chance_and_never_reads_labels(data):
    train, test = data
    clf = ThreatClassifier("rf").fit(train)
    m = clf.evaluate(test)
    assert m["accuracy"] > 0.9 and m["roc_auc"] > 0.95
    scrambled = test.copy()
    scrambled["y"], scrambled["label"], scrambled["category"] = 0, "normal", "normal"
    assert np.allclose(clf.attack_probability(test), clf.attack_probability(scrambled))


def test_logreg_also_works(data):
    train, test = data
    assert ThreatClassifier("logreg").fit(train).evaluate(test)["accuracy"] > 0.9


def test_threat_score_bounds_and_ordering():
    assert threat_score(np.array([])) == 0.0
    assert threat_score(np.zeros(10)) == 0.0 and threat_score(np.ones(10)) == 1.0
    assert threat_score(np.array([0.1] * 9 + [0.9])) < threat_score(np.array([0.9] * 9 + [0.1]))
