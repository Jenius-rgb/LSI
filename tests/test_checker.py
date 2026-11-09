"""M3 level L0: the comparator decision table of SPEC 6.2, plus property tests."""
import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from model import checker as ck
from model.checker import CORRECT, DETECT_C1_RECOMPUTE, UNPROTECTED, Outcome


def clean(k=8, c3=False, seed=0):
    rng = np.random.default_rng(seed)
    y = [int(v) for v in rng.integers(-(2**20), 2**20, size=k)]
    s1, s2, s3 = ck.checksums(y)
    return y, s1, s2, s3 if c3 else 0


# --- decision table -------------------------------------------------------------------


def test_unprotected_returns_none_and_keeps_data():
    y, s1, s2, s3 = clean()
    r = ck.check(y, s1 + 5, s2, s3, UNPROTECTED, False, False)
    assert r.outcome == Outcome.NONE and r.y == y


def test_c1_mode_clean_and_recompute():
    y, s1, s2, s3 = clean()
    assert ck.check(y, s1, s2, s3, DETECT_C1_RECOMPUTE, False, False).outcome == Outcome.CLEAN
    assert ck.check(y, s1 + 1, s2, s3, DETECT_C1_RECOMPUTE, False, False).outcome == Outcome.RECOMPUTE
    # d2 is ignored in mode 1.
    assert ck.check(y, s1, s2 + 9, s3, DETECT_C1_RECOMPUTE, False, False).outcome == Outcome.CLEAN


def test_correct_mode_clean():
    y, s1, s2, s3 = clean()
    r = ck.check(y, s1, s2, s3, CORRECT, False, False)
    assert r.outcome == Outcome.CLEAN and r.y == y


@pytest.mark.parametrize("k,c3", [(8, False), (8, True), (16, False), (16, True)])
def test_every_single_lane_error_is_corrected(k, c3):
    y, s1, s2, s3 = clean(k, c3, 7)
    for lane in range(1, k + 1):
        bad = list(y)
        bad[lane - 1] += 12345
        r = ck.check(bad, s1, s2, s3, CORRECT, c3, False)
        assert r.outcome == Outcome.CORRECTED and r.lane == lane
        assert r.y == y


def test_csum_lane_errors_recompute_when_not_trusted():
    y, s1, s2, s3 = clean(c3=True)
    assert ck.check(y, s1 + 3, s2, s3, CORRECT, True, False).outcome == Outcome.RECOMPUTE
    assert ck.check(y, s1, s2 + 3, s3, CORRECT, True, False).outcome == Outcome.RECOMPUTE
    assert ck.check(y, s1, s2, s3 + 3, CORRECT, True, False).outcome == Outcome.RECOMPUTE


def test_csum_lane_errors_identified_when_trusted():
    y, s1, s2, s3 = clean(c3=True)
    for idx, args in enumerate([(s1 + 3, s2, s3), (s1, s2 + 3, s3), (s1, s2, s3 + 3)], start=1):
        r = ck.check(y, *args, CORRECT, True, True)
        assert r.outcome == Outcome.CSUM_LANE and r.lane == idx and r.y == y


def test_csum_lane_3_needs_c3_enabled():
    y, s1, s2, _ = clean()
    # Without C3, S3 is ignored entirely.
    assert ck.check(y, s1, s2, 999, CORRECT, False, True).outcome == Outcome.CLEAN


def test_spec_example_two_lanes_cancelling_in_d2():
    # SPEC 6.2: +2 on lane 1 and -1 on lane 2 gives d1 = 1, d2 = 0.
    y, s1, s2, s3 = clean()
    bad = list(y)
    bad[0] += 2
    bad[1] -= 1
    r = ck.check(bad, s1, s2, s3, CORRECT, False, False)
    assert (r.d1, r.d2) == (1, 0) and r.outcome == Outcome.RECOMPUTE


def test_two_lanes_equal_error_miscorrects_without_c3_and_recomputes_with_c3():
    y, s1, s2, s3 = clean(c3=True)
    bad = list(y)
    bad[0] += 10  # lane 1
    bad[2] += 10  # lane 3: looks like lane 2 with error 20
    r = ck.check(bad, s1, s2, 0, CORRECT, False, False)
    assert r.outcome == Outcome.CORRECTED and r.lane == 2 and r.y != y
    assert ck.check(bad, s1, s2, s3, CORRECT, True, False).outcome == Outcome.RECOMPUTE


def test_d1_zero_d2_nonzero_is_not_corrected():
    y, s1, s2, s3 = clean()
    bad = list(y)
    bad[0] += 4
    bad[1] -= 4
    assert ck.check(bad, s1, s2, s3, CORRECT, False, False).outcome == Outcome.RECOMPUTE


# --- injection semantics (SPEC 11.1, 11.2) --------------------------------------------


def test_inject_truncates_mask_to_lane_width():
    assert ck.xor_inject(0, 1 << 40, 32) == 0
    assert ck.xor_inject(0, (1 << 40) | 1, 32) == 1
    assert ck.xor_inject(0, 1 << 40, 48) == 1 << 40


def test_inject_is_twos_complement():
    assert ck.xor_inject(-1, 1, 32) == -2
    assert ck.xor_inject(0, 1 << 31, 32) == -(2**31)
    assert ck.xor_inject(5, 0, 32) == 5


def test_inject_is_self_inverse():
    for v in (-123456, 0, 77, 2**30):
        assert ck.xor_inject(ck.xor_inject(v, 0xDEAD, 32), 0xDEAD, 32) == v


# --- property tests -------------------------------------------------------------------


accs = st.integers(-(2**30), 2**30)


@given(st.lists(accs, min_size=8, max_size=8), st.integers(1, 8), st.integers(1, 2**31 - 1).filter(lambda m: m))
@settings(max_examples=400, deadline=None)
def test_property_single_lane_xor_is_always_corrected(y, lane, mask):
    s1, s2, _ = ck.checksums(y)
    bad = list(y)
    bad[lane - 1] = ck.xor_inject(bad[lane - 1], mask, 32)
    r = ck.check(bad, s1, s2, 0, CORRECT, False, False)
    assert r.y == y
    assert r.outcome == Outcome.CORRECTED and r.lane == lane


@given(st.lists(accs, min_size=8, max_size=8), st.integers(-(2**29), 2**29).filter(bool))
@settings(max_examples=200, deadline=None)
def test_property_mode_0_never_touches_data(y, e):
    s1, s2, _ = ck.checksums(y)
    bad = [y[0] + e] + y[1:]
    r = ck.check(bad, s1, s2, 0, UNPROTECTED, False, False)
    assert r.y == bad and r.outcome == Outcome.NONE


@given(st.lists(accs, min_size=16, max_size=16), st.integers(1, 16), st.integers(1, 16), st.integers(1, 2**20), st.integers(1, 2**20))
@settings(max_examples=400, deadline=None)
def test_property_c3_never_reports_clean_for_nonzero_two_lane_error(y, a, b, ea, eb):
    if a == b:
        return
    s1, s2, s3 = ck.checksums(y)
    bad = list(y)
    bad[a - 1] += ea
    bad[b - 1] += eb
    r = ck.check(bad, s1, s2, s3, CORRECT, True, False)
    # With both lanes changed, d1 = d2 = d3 = 0 is impossible for a != b unless ea = eb = 0.
    assert r.outcome != Outcome.CLEAN


@given(st.lists(accs, min_size=8, max_size=8), st.integers(1, 8), st.integers(1, 2**25))
@settings(max_examples=200, deadline=None)
def test_property_outcomes_are_consistent_with_syndromes(y, lane, e):
    s1, s2, s3 = ck.checksums(y)
    bad = list(y)
    bad[lane - 1] += e
    r = ck.check(bad, s1, s2, s3, CORRECT, True, False)
    assert (r.d1, r.d2, r.d3) == (e, lane * e, lane * lane * e)
