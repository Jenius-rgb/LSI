"""M3: fault-injection campaign on real accumulators from the golden model."""
import numpy as np

from model import campaign, golden
from model.checker import Outcome


def small_model():
    rng = np.random.default_rng(3)
    conv = golden.QLayer(
        "conv1", "conv", rng.integers(-127, 128, size=(8, 3, 3, 3), dtype=np.int64),
        rng.integers(-500, 500, size=8, dtype=np.int64), 9000, 18,
    )
    fc = golden.QLayer(
        "fc", "fc", rng.integers(-127, 128, size=(10, 8 * 4 * 4), dtype=np.int64),
        rng.integers(-500, 500, size=10, dtype=np.int64), 0, 0,
    )
    return golden.QModel("tiny", (3, 8, 8), [conv, fc])


def images(n=4):
    return np.random.default_rng(1).integers(0, 256, size=(n, 3, 8, 8), dtype=np.uint8)


def test_units_satisfy_the_checksum_identity_independently():
    pool = campaign.UnitPool(small_model(), images(), k=8)
    assert pool.identity_violations == 0
    assert pool.layers == ["conv1", "fc"]
    assert pool.count("conv1") == 8 * 8 * 4 * 1  # images * H * W * groups
    assert pool.count("fc") == 4 * 2  # N=10 needs two groups of 8


def test_units_match_the_golden_trace():
    qm, imgs = small_model(), images()
    pool = campaign.UnitPool(qm, imgs, k=8)
    tr = golden.forward(qm, imgs[2], trace=True).trace
    unit = pool.unit("conv1", image=2, position=(3, 5), group=0)
    assert unit.y.tolist() == tr[0].acc[:8, 3, 5].tolist()
    unit = pool.unit("fc", image=2, position=(0, 0), group=1)
    assert unit.y[:2].tolist() == tr[1].acc[8:10].tolist()
    assert unit.y[2:].tolist() == [0] * 6


def test_single_lane_campaign_corrects_everything():
    pool = campaign.UnitPool(small_model(), images(), k=8)
    res = campaign.run(pool, "single", 2000, c3=False, trust=False, seed=5)
    assert res.counts["corrected"] == 2000
    assert res.counts["miscorrected"] == 0 and res.counts["escaped"] == 0


def test_dual_lane_campaign_counts_partition_the_trials():
    pool = campaign.UnitPool(small_model(), images(), k=8)
    res = campaign.run(pool, "dual", 2000, c3=False, trust=False, seed=6)
    assert sum(res.counts.values()) == 2000
    assert res.counts["recompute"] > 0


def test_c3_reduces_miscorrection():
    pool = campaign.UnitPool(small_model(), images(8), k=8)
    without = campaign.run(pool, "dual", 3000, c3=False, trust=False, seed=8)
    with_c3 = campaign.run(pool, "dual", 3000, c3=True, trust=False, seed=8)
    assert with_c3.counts["miscorrected"] <= without.counts["miscorrected"]
    assert with_c3.counts["escaped"] <= without.counts["escaped"]


def test_checksum_lane_errors_never_change_data():
    pool = campaign.UnitPool(small_model(), images(), k=8)
    res = campaign.run(pool, "csum", 500, c3=False, trust=False, seed=9)
    assert res.counts["recompute"] == 500
    res = campaign.run(pool, "csum", 500, c3=False, trust=True, seed=9)
    assert res.counts["csum_lane"] == 500


def test_campaign_is_reproducible():
    pool = campaign.UnitPool(small_model(), images(), k=8)
    a = campaign.run(pool, "dual", 500, c3=True, trust=False, seed=4)
    b = campaign.run(pool, "dual", 500, c3=True, trust=False, seed=4)
    assert a.counts == b.counts
    assert [t.outcome for t in a.trials] == [t.outcome for t in b.trials]


def test_classification_of_outcomes():
    y = [1, 2, 3]
    assert campaign.classify(Outcome.CLEAN, y, y) == "clean"
    assert campaign.classify(Outcome.CLEAN, [9, 2, 3], y) == "escaped"
    assert campaign.classify(Outcome.CORRECTED, y, y) == "corrected"
    assert campaign.classify(Outcome.CORRECTED, [9, 2, 3], y) == "miscorrected"
    assert campaign.classify(Outcome.CSUM_LANE, y, y) == "csum_lane"
    assert campaign.classify(Outcome.CSUM_LANE, [9, 2, 3], y) == "escaped"
    assert campaign.classify(Outcome.RECOMPUTE, [9, 2, 3], y) == "recompute"
