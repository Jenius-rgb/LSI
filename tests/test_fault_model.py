"""M3: the synthetic timing-error model of SPEC 11.3 (development only, [SYNTHETIC])."""
import numpy as np

from model.fault_model import FaultParams, TimingFaultModel


def model(seed=1, **kw):
    params = FaultParams(seed=seed, f_onset_mhz=150.0, spread=0.15, gamma=kw.get("gamma", 0.0), delta_mhz=40.0, alpha=2.0)
    return TimingFaultModel(k=8, n_csum=2, params=params, sparsity=kw.get("sparsity", [0.0, 0.5, 0.8, 0.9]))


def test_onset_is_deterministic_from_seed_and_differs_between_lanes():
    a, b = model(5), model(5)
    assert np.array_equal(a.f_onset, b.f_onset)
    assert len(set(a.f_onset.tolist())) > 1
    assert not np.array_equal(model(6).f_onset, a.f_onset)


def test_probability_is_zero_below_onset_and_saturates():
    m = model()
    lane = 2
    onset = m.onset(lane, 0)
    assert m.probability(onset - 1.0, lane, 0) == 0.0
    assert m.probability(onset, lane, 0) == 0.0
    assert m.probability(onset + 40.0, lane, 0) == 1.0
    assert m.probability(onset + 1000.0, lane, 0) == 1.0
    assert 0.0 < m.probability(onset + 20.0, lane, 0) < 1.0


def test_probability_law_power_alpha():
    m = model()
    onset = m.onset(1, 0)
    assert m.probability(onset + 20.0, 1, 0) == (20.0 / 40.0) ** 2.0


def test_gamma_scales_onset_by_sparsity():
    m = model(gamma=0.2)
    assert m.onset(0, 2) == m.f_onset[0] * (1 + 0.2 * 0.8)
    assert model(gamma=0.0).onset(0, 2) == m.f_onset[0]


def test_error_decisions_are_deterministic():
    m = model()
    f = float(m.f_onset.max() + 30.0)
    runs = [[m.error_occurs(9, 1, u, l, f) for u in range(200) for l in range(8)] for _ in range(2)]
    assert runs[0] == runs[1]
    assert any(runs[0]) and not all(runs[0])


def test_error_rate_tracks_probability():
    m = model()
    lane = 3
    f = m.onset(lane, 0) + 20.0
    hits = sum(m.error_occurs(1, 0, u, lane, f) for u in range(20000))
    assert abs(hits / 20000 - m.probability(f, lane, 0)) < 0.02


def test_no_errors_at_or_below_onset():
    m = model()
    f = float(m.f_onset.min())
    assert not any(m.error_occurs(1, 0, u, int(np.argmin(m.f_onset)), f) for u in range(2000))


def test_error_mask_is_single_bit_inside_active_range_and_msb_biased():
    m = model()
    true = 0x3FFF  # 14 active bits
    masks = [m.error_mask(1, 0, u, 2, 200.0, true) for u in range(4000)]
    assert all(bin(x).count("1") == 1 for x in masks)
    bits = np.array([int(np.log2(x)) for x in masks])
    assert bits.max() <= 14
    assert (bits >= 7).mean() > 0.7  # upper half dominates


def test_error_mask_handles_negative_and_zero_values():
    m = model()
    assert bin(m.error_mask(1, 0, 3, 1, 200.0, -5)).count("1") == 1
    assert bin(m.error_mask(1, 0, 3, 1, 200.0, 0)).count("1") == 1


def test_metadata_records_every_parameter():
    meta = model().metadata()
    for key in ("seed", "f_onset_mhz", "spread", "gamma", "delta_mhz", "alpha", "f_onset_per_lane", "label"):
        assert key in meta
    assert meta["label"] == "[SYNTHETIC]"
