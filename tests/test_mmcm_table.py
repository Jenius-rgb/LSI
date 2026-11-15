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
    """A clock other than the board clock is still flagged; the limits stay unverified."""
    table = gmt.build_table(100.0, 100.0, 5.0, 4, "-1", LIMITS)
    assert table["f_in_is_placeholder"] is True
    assert table["limits_verified_against_ds189"] is False


def test_board_clock_of_20_mhz_gives_an_exact_table():
    """ADR-015: CLK20M is official since 2026-11-10, so 20 MHz is no longer a placeholder."""
    table = gmt.build_table(gmt.BOARD_F_IN_MHZ, 125.0, 10.0, 16, "-1", LIMITS)
    assert table["f_in_is_placeholder"] is False and "OFFICIAL" in table["f_in_source"]
    assert [round(lv["f_out"], 6) for lv in table["levels"]] == [125.0 + 10.0 * i for i in range(16)]
    assert all(lv["d"] == 1 and LIMITS["f_vco_min"] <= lv["f_vco"] <= LIMITS["f_vco_max"] for lv in table["levels"])


def test_repository_limits_are_flagged_until_checked():
    limits = gmt.load_limits("-1")
    assert limits["verified"] is False  # flip only after DS189 has been checked, with page numbers
