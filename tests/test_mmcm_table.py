"""M10: every generated MMCM setting respects the configured limits."""
import gen_mmcm_table as gmt


LIMITS = {
    "f_in_min": 10.0, "f_in_max": 800.0, "f_pfd_min": 10.0, "f_pfd_max": 450.0,
    "f_vco_min": 600.0, "f_vco_max": 1200.0, "f_out_max": 800.0, "verified": False, "source": "test",
}


def test_every_level_is_inside_the_limits():
    table = gmt.build_table(100.0, 100.0, 5.0, 16, "-1", LIMITS)
    for lv in table["levels"]:
        assert lv["m"] is not None
        assert 2 <= lv["m"] <= 64 and 1 <= lv["d"] <= 106 and 1 <= lv["o"] <= 128
        assert LIMITS["f_pfd_min"] <= 100.0 / lv["d"] <= LIMITS["f_pfd_max"]
        vco = 100.0 * lv["m"] / lv["d"]
        assert LIMITS["f_vco_min"] <= vco <= LIMITS["f_vco_max"]
        assert vco / lv["o"] <= LIMITS["f_out_max"]
        assert abs(vco / lv["o"] - lv["target_mhz"]) <= 0.5


def test_infeasible_input_clock_is_reported_not_guessed():
    assert gmt.search(5.0, 100.0, LIMITS) is None


def test_table_records_placeholder_and_unverified_limits():
    table = gmt.build_table(100.0, 100.0, 5.0, 4, "-1", LIMITS)
    assert table["f_in_is_placeholder"] is True
    assert table["limits_verified_against_ds189"] is False


def test_repository_limits_are_flagged_until_checked():
    limits = gmt.load_limits("-1")
    assert limits["verified"] is False  # flip only after DS189 has been checked, with page numbers
