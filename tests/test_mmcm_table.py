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


def test_repository_limits_match_ds189():
    """The limits were checked against DS189 on 2026-11-16 (Table 37, PDF page 40), so every value now
    carries a page and verified: true. This replaces the test that required verified: false before the
    data sheet was available. The -2 input and output maxima were wrong (933 MHz) and are 800 MHz."""
    import yaml

    data = yaml.safe_load((gmt.LIMITS_PATH).read_text(encoding="utf-8"))
    expected = {
        "-1": {"f_in_min": 10.0, "f_in_max": 800.0, "f_pfd_min": 10.0, "f_pfd_max": 450.0,
               "f_vco_min": 600.0, "f_vco_max": 1200.0, "f_out_max": 800.0},
        "-2": {"f_in_min": 10.0, "f_in_max": 800.0, "f_pfd_min": 10.0, "f_pfd_max": 500.0,
               "f_vco_min": 600.0, "f_vco_max": 1440.0, "f_out_max": 800.0},
    }
    for grade, values in expected.items():
        for key, value in values.items():
            entry = data["speed_grades"][grade][key]
            assert entry["value"] == value and entry["verified"] is True and entry["page"] == 40, (grade, key)
    assert gmt.load_limits("-1")["verified"] is True


def test_part_capacities_match_ds180():
    """DS180 v2.6.1, Table 2 (page 2), read 2026-11-16."""
    import yaml

    parts = yaml.safe_load((gmt.ROOT / "config" / "parts.yaml").read_text(encoding="utf-8"))["parts"]
    expected = {"xc7s6": (5, 10), "xc7s15": (10, 20), "xc7s25": (45, 80), "xc7s50": (75, 120)}
    for name, (bram36, dsp) in expected.items():
        assert parts[name]["bram36"] == {"value": bram36, "verified": True}
        assert parts[name]["dsp"] == {"value": dsp, "verified": True}


def test_selection_prefers_integer_settings_then_the_highest_vco():
    """ADR-023: among exact settings, integer M and O first (as Clocking Wizard picks M = 50, O = 8 for
    125 MHz from 20 MHz), then the highest VCO."""
    table = gmt.build_table(gmt.BOARD_F_IN_MHZ, 125.0, 10.0, 16, "-1")
    lv0 = table["levels"][0]
    assert (lv0["m"], lv0["d"], lv0["o"]) == (50.0, 1, 8.0)
    for lv in table["levels"]:
        assert abs(lv["f_out"] - lv["target_mhz"]) < 1e-9


def test_clocking_wizard_register_words():
    """PG065 Table 2-2: 0x200 = DIVCLK[7:0] | MULT[15:8] | MULT_FRAC[25:16]; 0x208 = DIV[7:0] | FRAC[17:8]
    (fractions in thousandths)."""
    assert gmt.clkwiz_words({"m": 50.0, "d": 1, "o": 8.0}) == (0x0000_3201, 0x0000_0008)
    assert gmt.clkwiz_words({"m": 8.125, "d": 2, "o": 2.25}) == ((125 << 16) | (8 << 8) | 2, (250 << 8) | 2)


def test_generated_verilog_table_is_up_to_date():
    for path, text in gmt.outputs().items():
        assert path.read_text(encoding="utf-8") == text, f"{path} is stale: run python tools/run.py gen --regmap"
