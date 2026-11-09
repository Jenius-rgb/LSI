"""M8/M9: the unit-level engine model reproduces the golden model and predicts recovery."""
import numpy as np

from model import golden
from model.checker import CORRECT, DETECT_C1_RECOMPUTE, UNPROTECTED
from model.engine_model import EngineConfig, InjectionSlot, run_image
from model.golden import forward


def micro():
    rng = np.random.default_rng(1)
    conv = golden.QLayer("conv1", "conv", rng.integers(-127, 128, size=(8, 3, 3, 3), dtype=np.int64),
                         rng.integers(-500, 500, size=8, dtype=np.int64), 9000, 18)
    fc = golden.QLayer("fc", "fc", rng.integers(-127, 128, size=(10, 8 * 4 * 4), dtype=np.int64),
                       rng.integers(-500, 500, size=10, dtype=np.int64), 0, 0)
    return golden.QModel("micro", (3, 8, 8), [conv, fc])


def image():
    return np.random.default_rng(2).integers(0, 256, size=(3, 8, 8), dtype=np.uint8)


def test_no_faults_matches_golden_in_every_mode():
    qm, img = micro(), image()
    gold = forward(qm, img)
    for mode in (UNPROTECTED, DETECT_C1_RECOMPUTE, CORRECT):
        res = run_image(qm, img, EngineConfig(mode=mode))
        assert np.array_equal(res.logits, gold.logits) and res.pred == gold.pred
        assert res.units == [64 * 1, 2]
        assert not res.fatal


def test_clean_counts_exclude_mode_0():
    qm, img = micro(), image()
    res = run_image(qm, img, EngineConfig(mode=UNPROTECTED))
    assert res.clean == [0, 0]
    res = run_image(qm, img, EngineConfig(mode=CORRECT))
    assert res.clean == res.units


def slot(**kw):
    return InjectionSlot(enable=True, oneshot=True, **kw)


def test_single_lane_injection_mode_2_is_corrected_and_bit_exact():
    qm, img = micro(), image()
    res = run_image(qm, img, EngineConfig(mode=CORRECT), [slot(layer=0, unit=5, lane=3, mask=1 << 9)])
    gold = forward(qm, img)
    assert np.array_equal(res.logits, gold.logits)
    assert res.corrected == [1, 0] and res.lane_corrections[2] == 1
    assert res.recompute == [0, 0] and res.injections_fired == 1


def test_single_lane_injection_mode_1_recomputes_and_stays_bit_exact():
    qm, img = micro(), image()
    res = run_image(qm, img, EngineConfig(mode=DETECT_C1_RECOMPUTE), [slot(layer=0, unit=5, lane=3, mask=1 << 9)])
    gold = forward(qm, img)
    assert np.array_equal(res.logits, gold.logits)
    assert res.recompute == [1, 0] and res.recompute_windows == [1, 0] and not res.fatal


def test_mode_0_propagates_the_error():
    # A single flipped unit can be masked by max pooling or saturation, so every unit of one
    # lane is corrupted here to make the error visible at the output.
    qm, img = micro(), image()
    persistent = InjectionSlot(enable=True, layer=0, any_unit=True, lane=3, mask=1 << 29, oneshot=False)
    res = run_image(qm, img, EngineConfig(mode=UNPROTECTED), [persistent])
    assert not np.array_equal(res.logits, forward(qm, img).logits)
    assert res.injections_fired == res.units[0]


def test_persistent_injection_in_recompute_pass_is_fatal():
    qm, img = micro(), image()
    persistent = InjectionSlot(enable=True, layer=0, any_unit=True, lane=2, mask=1 << 5, oneshot=False)
    res = run_image(qm, img, EngineConfig(mode=DETECT_C1_RECOMPUTE, n_log=1000), [persistent])
    assert res.fatal and res.fatal_count[0] > 0 and res.recompute[0] == 64


def test_log_overflow_redoes_the_whole_layer():
    qm, img = micro(), image()
    any_oneshot_off = InjectionSlot(enable=True, layer=0, any_unit=True, lane=2, mask=1 << 5, oneshot=False)
    res = run_image(qm, img, EngineConfig(mode=DETECT_C1_RECOMPUTE, n_log=4), [any_oneshot_off])
    assert res.log_ovf and res.log_overflow_count == 1 and res.fatal


def test_oneshot_fires_once_per_image_only():
    qm, img = micro(), image()
    res = run_image(qm, img, EngineConfig(mode=CORRECT), [InjectionSlot(enable=True, layer=0, any_unit=True, lane=4, mask=8, oneshot=True)])
    assert res.injections_fired == 1 and res.corrected == [1, 0]


def test_dual_slot_same_unit_two_lanes_goes_to_recompute_or_miscorrects():
    qm, img = micro(), image()
    slots = [slot(layer=0, unit=7, lane=1, mask=1 << 4), slot(layer=0, unit=7, lane=2, mask=1 << 9)]
    res = run_image(qm, img, EngineConfig(mode=CORRECT), slots)
    assert res.injections_fired == 2
    assert res.corrected[0] + res.recompute[0] == 1


def test_checksum_lane_injection_is_recomputed_when_not_trusted():
    qm, img = micro(), image()
    res = run_image(qm, img, EngineConfig(mode=CORRECT), [slot(layer=1, unit=1, lane=9, mask=1 << 6)])
    assert res.recompute == [0, 1] and np.array_equal(res.logits, forward(qm, img).logits)
