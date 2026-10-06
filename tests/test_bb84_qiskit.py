"""Run only where Qiskit + Aer are installed (they are in requirements.txt)."""
import numpy as np
import pytest

pytest.importorskip("qiskit")
pytest.importorskip("qiskit_aer")

from quantum import bb84  # noqa: E402
from quantum.bb84_qiskit import build_circuit, transmit_qiskit  # noqa: E402


def qber(tx):
    s = bb84.sift(tx)
    return float((s.alice != s.bob).mean()), len(s.alice)


def test_no_noise_no_eve_is_error_free():
    q, kept = qber(transmit_qiskit(300, noise=0.0, rng=np.random.default_rng(1)))
    assert q == 0.0 and kept > 100


def test_full_intercept_resend_gives_about_25_percent():
    q, _ = qber(transmit_qiskit(1200, noise=0.0, eve_rate=1.0, rng=np.random.default_rng(2)))
    assert 0.17 < q < 0.33


def test_noise_is_reflected():
    q, _ = qber(transmit_qiskit(1200, noise=0.08, rng=np.random.default_rng(3)))
    assert 0.04 < q < 0.12


def test_matches_numpy_engine_statistically():
    kw = dict(noise=0.03, eve_rate=0.4)
    qa = qber(transmit_qiskit(1500, rng=np.random.default_rng(4), **kw))[0]
    qb = np.mean([qber(bb84.transmit(1500, rng=np.random.default_rng(s), **kw))[0] for s in range(10)])
    assert abs(qa - qb) < 0.05


def test_measurements_in_the_wrong_basis_are_independent_across_circuits():
    """Guards against every circuit in a batch reusing the same random stream."""
    from qiskit_aer import AerSimulator

    circs = [build_circuit(0, 1, 0, None) for _ in range(400)]  # |+> measured in Z: 50/50
    res = AerSimulator().run(circs, shots=1, seed_simulator=7).result()
    ones = np.mean([int(next(iter(res.get_counts(i)))[0]) for i in range(400)])
    assert 0.38 < ones < 0.62


def test_eve_not_intercepting_means_one_less_measurement():
    assert build_circuit(1, 0, 0, None).count_ops().get("measure") == 1
    assert build_circuit(1, 0, 0, 1).count_ops().get("measure") == 2
