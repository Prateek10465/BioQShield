import numpy as np
from quantum import bb84


def run(n=20000, **kw):
    rng = np.random.default_rng(kw.pop("seed", 0))
    tx = bb84.transmit(n, rng=rng, **kw)
    s = bb84.sift(tx)
    return tx, s, float((s.alice != s.bob).mean())


def test_sifting_keeps_about_half():
    _, s, _ = run(noise=0.0)
    assert 0.47 < len(s.alice) / 20000 < 0.53


def test_no_noise_no_eve_gives_identical_keys():
    _, s, q = run(noise=0.0)
    assert q == 0.0 and np.array_equal(s.alice, s.bob)


def test_noise_is_reflected_unbiased():
    qs = [run(noise=0.04, seed=i)[2] for i in range(15)]
    assert abs(np.mean(qs) - 0.04) < 0.005


def test_full_intercept_resend_gives_25_percent():
    _, _, q = run(noise=0.0, eve_rate=1.0)
    assert 0.22 < q < 0.28


def test_partial_eve_scales_linearly():
    _, _, q = run(noise=0.0, eve_rate=0.4)
    assert 0.08 < q < 0.12


def test_eve_knows_half_the_sifted_bits_she_touched():
    _, s, _ = run(noise=0.0, eve_rate=1.0)
    assert 0.46 < s.eve_knows.mean() < 0.54


def test_eve_start_leaves_first_half_clean():
    rng = np.random.default_rng(1)
    tx = bb84.transmit(20000, noise=0.0, eve_rate=1.0, eve_start=0.5, rng=rng)
    assert not tx.intercepted[:10000].any() and tx.intercepted[10000:].mean() > 0.99
    est = bb84.estimate_qber(bb84.sift(tx), 0.25, rng)
    trace = bb84.qber_trace(est, 20000, bins=4)
    assert trace[0]["qber"] < 0.02 and trace[3]["qber"] > 0.15


def test_estimator_sample_size_and_upper_bound():
    rng = np.random.default_rng(2)
    s = bb84.sift(bb84.transmit(8192, noise=0.03, rng=rng))
    est = bb84.estimate_qber(s, 0.25, rng)
    assert len(est.sample_errors) == int(len(s.alice) * 0.25)
    assert len(est.alice_key) + len(est.sample_errors) == len(s.alice)
    assert est.qber_upper > est.qber
