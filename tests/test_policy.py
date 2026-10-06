import itertools

import pytest

from fusion.link import LinkReport
from fusion.policy import Action, LinkBaseline, LinkController, PolicyConfig


def rep(qber, key_bits=800, m=1000, upper=None):
    return LinkReport(n_qubits=8192, n_sifted=4096, sample_size=m, qber=qber,
                      qber_upper=upper if upper is not None else qber + 0.015, true_qber=qber,
                      leaked_bits=0, key_bits=key_bits, engine="numpy", eve_rate=0.0, noise=qber)


def ready_baseline(q=0.02):
    b = LinkBaseline()
    for _ in range(10):
        # Assuming 50% sift rate for simplicity in tests
        b.update(q, 1000, 500, 1000)
    return b


def test_static_three_outcomes():
    s = LinkController("static")
    assert s.decide(rep(0.02)).action is Action.ACCEPT
    assert LinkController("static").decide(rep(0.07, key_bits=400)).action is Action.MONITOR
    assert LinkController("static").decide(rep(0.12)).action is Action.REJECT


def test_no_usable_key_or_uncertain_upper_bound_is_monitor_not_accept():
    assert LinkController("static").decide(rep(0.02, key_bits=100)).action is Action.MONITOR
    assert LinkController("static").decide(rep(0.045, upper=0.115)).action is Action.MONITOR


def test_static_ignores_threat():
    a = LinkController("static").decide(rep(0.02), threat=0.99)
    assert a.action is Action.ACCEPT and a.threat is None


def test_above_11_percent_rejected_whatever_the_context():
    for mode, t in itertools.product(("static", "adaptive"), (None, 0.0, 0.5, 1.0)):
        ctl = LinkController(mode, baseline=ready_baseline(0.12))  # even a link whose "normal" is 12%
        assert ctl.decide(rep(0.2), threat=t).action is Action.REJECT


def test_threat_can_only_tighten():
    """For the same session, more threat never gives a milder decision."""
    for q in (0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10, 0.13):
        sev = []
        for t in (0.0, 0.3, 0.6, 0.9, 1.0):
            ctl = LinkController("adaptive", baseline=ready_baseline())
            sev.append(ctl.decide(rep(q), threat=t).action.severity)
        assert sev == sorted(sev), f"q={q}: {sev}"


def test_high_threat_turns_clean_into_monitor_and_ambiguous_into_reject():
    clean = LinkController("adaptive", baseline=ready_baseline()).decide(rep(0.02), threat=0.95)
    assert clean.action is Action.MONITOR
    amb_low = LinkController("adaptive", baseline=ready_baseline()).decide(rep(0.055, key_bits=500), threat=0.05)
    amb_high = LinkController("adaptive", baseline=ready_baseline()).decide(rep(0.055, key_bits=500), threat=0.95)
    assert amb_low.action is Action.MONITOR and amb_high.action is Action.REJECT


def test_threat_tightening_never_goes_below_link_noise_floor():
    ctl = LinkController("adaptive", baseline=ready_baseline(0.03))
    d = ctl.decide(rep(0.03), threat=1.0)
    assert d.accept_limit >= 0.03  # a healthy link at its own baseline must not be rejected for it


def test_adaptive_flags_a_rise_that_static_accepts():
    r = rep(0.045)  # below the static 5% limit, but 5+ sigma over a 2% baseline at 1000 samples
    assert LinkController("static").decide(r).action is Action.ACCEPT
    d = LinkController("adaptive", baseline=ready_baseline(0.02)).decide(r)
    assert d.action is Action.MONITOR and d.z > 4


def test_adaptive_accepts_a_link_that_is_stably_noisy():
    ctl = LinkController("adaptive", baseline=ready_baseline(0.06))
    assert ctl.decide(rep(0.06, key_bits=600)).action is Action.ACCEPT  # static would Monitor (6% > 5%)
    assert LinkController("static").decide(rep(0.06, key_bits=600)).action is Action.MONITOR


def test_baseline_not_ready_means_no_z_test():
    ctl = LinkController("adaptive")
    assert ctl.decide(rep(0.045)).z == 0.0


def test_monitor_streak_escalates_and_accept_resets():
    ctl = LinkController("adaptive", baseline=ready_baseline())
    acts = [ctl.decide(rep(0.055, key_bits=300)).action for _ in range(3)]  # ~7 sigma: Monitor, not direct Reject
    assert acts == [Action.MONITOR, Action.MONITOR, Action.REJECT]
    assert ctl.decide(rep(0.02)).action is Action.ACCEPT
    assert ctl.consecutive_monitor == 0
    assert ctl.decide(rep(0.055, key_bits=300)).action is Action.MONITOR  # streak restarted


def test_baseline_learns_only_from_accepted_low_threat_sessions():
    ctl = LinkController("adaptive", baseline=ready_baseline())
    before = ctl.baseline.bits
    ctl.decide(rep(0.09, key_bits=300))  # not accepted: must not teach the baseline
    ctl.decide(rep(0.02), threat=0.7)  # accepted but threat elevated: must not teach it
    assert ctl.baseline.bits == before
    ctl.decide(rep(0.02), threat=0.0)
    assert ctl.baseline.bits > before * 0.97


def test_bad_mode_rejected():
    with pytest.raises(ValueError):
        LinkController("clever").decide(rep(0.02))


def test_config_threshold_is_the_protocols_abort_limit():
    from quantum import postprocess as pp

    assert PolicyConfig().reject_qber == pp.QBER_ABORT_THRESHOLD
