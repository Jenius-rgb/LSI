"""M1: the architecture report must reproduce the hand-computed tables in SPEC 2 and 5.4."""
import pytest

from model.arch_report import report


@pytest.mark.parametrize(
    "model,weights,macs,bias,total_w,total_m,total_b",
    [
        ("s", [432, 4608, 9216, 5120], [442368, 1179648, 589824, 5120], [16, 32, 32, 10], 19376, 2216960, 90),
        ("xs", [216, 1152, 2304, 2560], [221184, 294912, 147456, 2560], [8, 16, 16, 10], 6232, 666112, 50),
    ],
)
def test_matches_spec_tables(model, weights, macs, bias, total_w, total_m, total_b):
    rep = report(model)
    assert [l["weights"] for l in rep["layers"]] == weights
    assert [l["macs"] for l in rep["layers"]] == macs
    assert [l["bias"] for l in rep["layers"]] == bias
    assert (rep["total_weights"], rep["total_macs"], rep["total_bias"]) == (total_w, total_m, total_b)


def test_ideal_cycles_match_spec_5_4():
    assert report("s")["ideal_cycles"]["8"] == 277504


def test_t_conv1_matches_spec_7_3():
    assert report("s")["layers"][0]["t"] == 27
