import numpy as np
import pytest

from quantum import bb84, postprocess as pp


def noisy_pair(n, q, rng):
    a = rng.integers(0, 2, n, dtype=np.uint8)
    flips = (rng.random(n) < q).astype(np.uint8)
    return a, a ^ flips


@pytest.mark.parametrize("q", [0.0, 0.01, 0.03, 0.06])
def test_cascade_corrects_everything(q):
    for seed in range(5):
        rng = np.random.default_rng(seed)
        a, b = noisy_pair(3000, q, rng)
        res = pp.cascade(a, b, max(q, 0.005), rng=rng)
        assert np.array_equal(res.corrected, a), f"residual errors at q={q}, seed={seed}"


def test_cascade_leakage_is_reasonable():
    rng = np.random.default_rng(3)
    a, b = noisy_pair(4000, 0.03, rng)
    res = pp.cascade(a, b, 0.03, rng=rng)
    shannon = 4000 * bb84.h2(0.03)
    assert shannon < res.leaked_bits < 2.0 * shannon


def test_cascade_does_not_touch_alices_key():
    rng = np.random.default_rng(4)
    a, b = noisy_pair(500, 0.05, rng)
    a0 = a.copy()
    pp.cascade(a, b, 0.05, rng=rng)
    assert np.array_equal(a, a0)


def test_verify_catches_a_residual_error():
    rng = np.random.default_rng(5)
    a = rng.integers(0, 2, 1000, dtype=np.uint8)
    b = a.copy()
    assert pp.verify(a, b, rng=rng)[0]
    b[123] ^= 1
    assert not pp.verify(a, b, rng=rng)[0]


def test_privacy_amplification_is_linear_and_seeded():
    rng = np.random.default_rng(6)
    n, l = 700, 300
    k1 = rng.integers(0, 2, n, dtype=np.uint8)
    k2 = rng.integers(0, 2, n, dtype=np.uint8)
    seed = rng.integers(0, 2, n + l - 1, dtype=np.uint8)
    h1, h2_, h12 = (pp.privacy_amplify(k, l, seed) for k in (k1, k2, k1 ^ k2))
    assert h1.shape == (l,)
    assert np.array_equal(h1 ^ h2_, h12)  # a hash that is linear over GF(2)
    assert np.array_equal(h1, pp.privacy_amplify(k1, l, seed))
    other = rng.integers(0, 2, n + l - 1, dtype=np.uint8)
    assert not np.array_equal(h1, pp.privacy_amplify(k1, l, other))


def test_privacy_amplification_slab_boundary():
    rng = np.random.default_rng(7)
    n, l = 600, 513  # not a multiple of the 256-row slab
    k = rng.integers(0, 2, n, dtype=np.uint8)
    seed = rng.integers(0, 2, n + l - 1, dtype=np.uint8)
    out = pp.privacy_amplify(k, l, seed)
    i, j = np.arange(l)[:, None], np.arange(n)[None, :]
    full = (seed[i - j + n - 1].astype(np.int64) @ k.astype(np.int64)) & 1
    assert np.array_equal(out, full.astype(np.uint8))


def test_key_length_shrinks_as_qber_grows():
    lens = [pp.secret_key_length(3000, q, int(3000 * 1.2 * bb84.h2(q))) for q in (0.0, 0.02, 0.05, 0.08, 0.11)]
    assert lens == sorted(lens, reverse=True)
    assert lens[0] > 2500 and lens[-1] == 0


def test_one_cascade_round_can_leave_errors_but_reconcile_fixes_them():
    # Seed found by search: two errors share a block on every pass, so the parities
    # cancel and a single Cascade round leaves them behind. reconcile() must recover.
    rng = np.random.default_rng(87)
    a, b = noisy_pair(1500, 0.02, rng)
    q = float((a != b).mean())
    single = pp.cascade(a, b, q, rng=rng)
    assert not np.array_equal(single.corrected, a), "seed no longer reproduces the weakness"

    rng = np.random.default_rng(87)
    a, b = noisy_pair(1500, 0.02, rng)
    res = pp.reconcile(a, b, q, rng=rng)
    assert res.verified and res.rounds >= 2
    assert np.array_equal(res.corrected, a)
    assert res.leaked_bits > single.leaked_bits  # the retry is paid for in revealed bits


def test_reconcile_uses_one_round_when_that_is_enough():
    rng = np.random.default_rng(1)
    a, b = noisy_pair(3000, 0.03, rng)
    res = pp.reconcile(a, b, 0.03, rng=rng)
    assert res.verified and res.rounds == 1 and np.array_equal(res.corrected, a)
