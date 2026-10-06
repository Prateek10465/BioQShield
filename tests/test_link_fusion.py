import numpy as np

from fusion import experiments as ex
from fusion.link import run_link_session
from fusion.policy import Action, LinkController


def test_clean_link_makes_an_aes_key():
    r = run_link_session(8192, noise=0.02, seed=1)
    assert 0.0 < r.qber < 0.05 and r.key_bits >= 256 and r.engine == "numpy"


def test_full_eve_gives_about_25_percent_and_no_key():
    r = run_link_session(8192, noise=0.0, eve_rate=1.0, seed=1)
    assert 0.2 < r.qber < 0.3 and r.key_bits == 0 and r.leaked_bits == 0


def test_more_noise_means_less_key():
    keys = [np.mean([run_link_session(8192, n, seed=s).key_bits for s in range(8)]) for n in (0.0, 0.03, 0.06)]
    assert keys[0] > keys[1] > keys[2]


def test_fast_leak_estimate_is_not_optimistic_vs_real_cascade():
    fast = np.mean([run_link_session(8192, 0.03, seed=s).key_bits for s in range(6)])
    full = np.mean([run_link_session(8192, 0.03, seed=s, full_cascade=True).key_bits for s in range(6)])
    assert fast <= full * 1.05  # estimate may be a bit pessimistic, must not overstate the key


def test_unknown_engine_is_an_error():
    import pytest

    with pytest.raises(ValueError):
        run_link_session(256, engine="abacus")


def test_sweep_qber_rises_with_eve_and_noise():
    df = ex.sweep(noises=(0.0, 0.05), eve_rates=(0.0, 0.5, 1.0), repeats=4, n_qubits=4096)
    g = df.set_index(["noise", "eve_rate"])
    assert g.loc[(0.0, 0.0), "qber"] < g.loc[(0.0, 0.5), "qber"] < g.loc[(0.0, 1.0), "qber"]
    assert g.loc[(0.0, 0.0), "qber"] < g.loc[(0.05, 0.0), "qber"]
    assert g.loc[(0.0, 1.0), "p_reject"] == 1.0 and g.loc[(0.0, 0.0), "p_accept"] == 1.0


def test_timeline_escalates_during_attack_and_recovers():
    tl = ex.timeline([("ok", 6, 0.02, 0.0, 0.05), ("eve", 4, 0.02, 0.2, 0.05), ("ok2", 4, 0.02, 0.0, 0.05)], n_qubits=4096, seed=5)
    acts = tl["action"].tolist()
    assert set(acts[:6]) == {"ACCEPT"}
    assert "REJECT" in acts[6:10]
    assert set(acts[-3:]) == {"ACCEPT"}


def test_threat_matrix_full_eve_always_rejected():
    m = ex.threat_matrix({"low": 0.0, "high": 1.0}, n_qubits=4096)
    assert (m[m["quantum"] == "full Eve"]["action"] == "REJECT").all()
    assert m[(m["quantum"] == "clean fibre") & (m["traffic"] == "low")]["action"].iloc[0] == Action.ACCEPT.value
