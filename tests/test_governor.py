"""M10: governor reference model against the pseudo-code of SPEC 10."""
from hypothesis import given, settings
from hypothesis import strategies as st

from model.governor import GovParams, reset, step


def params(**kw):
    return GovParams(**{"n_up": 3, "cooldown": 2, "corr_hi": 5, "l_min": 1, "l_max": 4, **kw})


def test_starts_at_lowest_level_with_all_layers_turbo():
    s = reset(params(), 3)
    assert s.level == 1 and s.turbo_en == [1, 1, 1] and s.clean_streak == 0


def test_clean_images_raise_the_level_after_n_up():
    p = params()
    s = reset(p, 2)
    for i in range(3):
        step(s, p, [0, 0], [0, 0])
    assert s.level == 2 and s.clean_streak == 0
    step(s, p, [0, 0], [0, 0])
    assert s.clean_streak == 1 and s.level == 2


def test_level_is_capped_at_l_max():
    p = params(l_max=2, n_up=1)
    s = reset(p, 1)
    for _ in range(5):
        step(s, p, [0], [0])
    assert s.level == 2


def test_failure_disables_layer_and_lowers_level():
    p = params()
    s = reset(p, 2)
    s.level = 3
    step(s, p, [1, 0], [0, 0])
    assert s.level == 2 and s.turbo_en == [0, 1] and s.cool == [2, 0] and s.clean_streak == 0


def test_level_is_floored_at_l_min():
    p = params(l_min=1)
    s = reset(p, 1)
    step(s, p, [1], [0])
    assert s.level == 1


def test_cooldown_reenables_layer():
    p = params()
    s = reset(p, 1)
    step(s, p, [1], [0])
    assert s.turbo_en == [0] and s.cool == [2]
    step(s, p, [0], [0])
    assert s.turbo_en == [0] and s.cool == [1]
    step(s, p, [0], [0])
    assert s.turbo_en == [1] and s.cool == [0]


def test_many_corrections_lower_level_without_disabling_layers():
    p = params(corr_hi=5)
    s = reset(p, 2)
    s.level = 3
    step(s, p, [0, 0], [3, 3])
    assert s.level == 2 and s.turbo_en == [1, 1]
    step(s, p, [0, 0], [3, 2])
    assert s.level == 2 and s.clean_streak == 1


def test_manual_mode_freezes_the_state():
    p = params(auto=False)
    s = reset(p, 1)
    step(s, p, [9], [100])
    assert s.level == 1 and s.turbo_en == [1]


@given(st.lists(st.tuples(st.integers(0, 3), st.integers(0, 3), st.integers(0, 9)), max_size=60))
@settings(max_examples=120, deadline=None)
def test_invariants_hold_for_any_event_sequence(events):
    p = params()
    s = reset(p, 2)
    for f0, f1, corr in events:
        step(s, p, [f0, f1], [corr, 0])
        assert p.l_min <= s.level <= p.l_max
        assert 0 <= s.clean_streak < p.n_up
        assert all(0 <= c <= p.cooldown for c in s.cool)
        assert all(t in (0, 1) for t in s.turbo_en)
