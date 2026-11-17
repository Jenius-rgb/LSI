"""M11: report parsing, BRAM arithmetic and the guard against a missing device."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "fpga"))
sys.path.insert(0, str(ROOT / "tools"))

import fit_report  # noqa: E402
import parse_reports as pr  # noqa: E402
import run_matrix  # noqa: E402

UTIL = """
| Site Type             | Used | Fixed | Prohibited | Available | Util% |
+-----------------------+------+-------+------------+-----------+-------+
| Slice LUTs            | 8123 |     0 |          0 |     14600 | 55.64 |
| Slice Registers       | 9321 |     0 |          0 |     29200 | 31.92 |
| Block RAM Tile        |  9.5 |     0 |          0 |        10 | 95.00 |
| DSPs                  |   10 |     0 |          0 |        20 | 50.00 |
"""

TIMING = """
Slack (MET) :             0.512ns  (required time - arrival time)
  Source:                 u_fast/u_lanes/data_lane[0].impl.u/m_reg[5]/C
                            (rising edge-triggered cell FDRE clocked by clk_fast  {rise@0.000ns fall@2.500ns period=5.000ns})
  Destination:            u_fast/u_lanes/data_lane[0].impl.u/acc_reg[12]/D
Slack (MET) :             1.750ns  (required time - arrival time)
  Source:                 u_fast/word_reg[3]/C
  Destination:            u_fast/set_r_reg[3]/D
"""


def test_parse_utilization():
    util = pr.parse_utilization(UTIL)
    assert util == {"lut": 8123.0, "ff": 9321.0, "bram36_equiv": 9.5, "dsp": 10.0}


def test_fmax_from_period_and_slack():
    assert pr.fmax_mhz(5.0, 1.0) == 250.0
    assert round(pr.fmax_mhz(5.0, -1.0), 3) == 166.667


def test_spec_7_4_gap_is_relative_to_mac_delay():
    # MAC delay 4 ns (period 5, slack 1); non-MAC slack 2.2: margin 1.2 ns = 30% of 4 ns.
    assert round(pr.spec_7_4_gap(5.0, 1.0, 2.2), 6) == 30.0


def test_paths_and_mac_classification():
    paths = pr.parse_paths(TIMING)
    assert len(paths) == 2
    assert paths[0]["slack"] == 0.512 and pr.is_mac_path(paths[0])
    assert not pr.is_mac_path(paths[1])


def test_bram18_counts():
    assert fit_report.bram18_for(2048, 8) == 1
    assert fit_report.bram18_for(3072, 8) == 2
    assert fit_report.bram18_for(1024, 16) == 1
    assert fit_report.bram18_for(2806, 64) == 12


def test_estimate_matches_spec_memory_budget():
    est = fit_report.estimate("s", 8, 2, 0)
    assert est["memories"]["weights"]["depth"] == 54 + 576 + 1152 + 1024
    assert est["memories"]["act0"]["depth"] == 4096 + 512
    assert est["memories"]["act1"]["depth"] == 2048


def test_matrix_refuses_without_spartan7(monkeypatch, capsys):
    monkeypatch.setattr(run_matrix, "find_vivado", lambda: "vivado")
    monkeypatch.setattr(run_matrix, "available_parts", lambda _: {"xc7s6": [], "xc7s15": []})
    monkeypatch.setattr(sys, "argv", ["run_matrix.py"])
    assert run_matrix.main() == 2
    assert "Spartan-7" in capsys.readouterr().out


def test_choose_parts_covers_speed_grades_and_prefers_common_package():
    available = {"xc7s15": ["xc7s15ftgb196-1", "xc7s15ftgb196-2", "xc7s15cpga196-1"], "xc7s6": ["xc7s6ftgb196-1"]}
    chosen = run_matrix.choose_parts(available)
    assert ("xc7s15ftgb196-1", "s") in chosen and ("xc7s15ftgb196-2", "s") in chosen
    assert ("xc7s6ftgb196-1", "xs") in chosen


def test_official_config_is_the_contest_chip():
    """ADR-013: one target, xc7s25csga225-1, with the official variant."""
    import yaml

    cfg = yaml.safe_load((ROOT / "config" / "hw_zero7.yaml").read_text(encoding="utf-8"))
    assert cfg["part"] == "xc7s25csga225-1" and cfg["top"] == "top_board"
    assert (cfg["K"], cfg["C3_EN"], cfg["LANE_IMPL"]) == (8, 1, "lut")
    assert cfg["clock"]["f_in_mhz"] == 20.0


def test_official_tcl_targets_the_chip_and_writes_no_bitstream():
    """ADR-014: complete design, standard reports, no bitstream while I/O standards are unconfirmed."""
    text = (ROOT / "fpga" / "synth_official.tcl").read_text(encoding="utf-8")
    assert "set part xc7s25csga225-1" in text and "set top top_board" in text and "board/zero7.xdc" in text
    assert not any(line.strip().startswith("write_bitstream") for line in text.splitlines())
    for report in ("report_utilization", "report_timing_summary", "report_power", "report_drc", "report_methodology"):
        assert report in text


def test_official_report_parsers():
    import run_official as ro

    util = ro.parse_utilization(
        "| Site Type | Used | Fixed | Prohibited | Available | Util% |\n"
        "| Slice LUTs | 5321 | 0 | 0 | 14600 | 36.45 |\n| Block RAM Tile | 14 | 0 | 0 | 45 | 31.11 |\n")
    assert util["lut"] == {"used": 5321.0, "available": 14600.0, "util_pct": 36.45}
    assert util["bram_tile"]["used"] == 14.0
    summary = ro.parse_summary("part xc7s25csga225-1\nclock clk_fast_safe period_ns 8.000 wns_ns 0.250 whs_ns NA\ndesign_wns_ns 0.250\n")
    assert summary["part"] == "xc7s25csga225-1"
    assert summary["clocks"][0] == {"name": "clk_fast_safe", "period_ns": 8.0, "wns_ns": 0.25, "whs_ns": None}
    report = "| TIMING-18 | Warning | Missing input or output delay | 3 |\n| NSTD-1 | Critical Warning | x | 1 |\n"
    assert ro.count_violations(report) == {"Warning": 3, "Critical Warning": 1}


def test_reset_and_cdc_rules_of_the_complete_design():
    """ADR-021: synchronizers are marked, the reset crossing is excepted, and the flow reports CDC and bus skew."""
    import re

    tcl = (ROOT / "fpga" / "constraints" / "top_board_timing.tcl").read_text(encoding="utf-8")
    assert "set_false_path -from [get_clocks clk_in]" in tcl and "por_meta_reg[0]" in tcl
    # ADR-027: the BUFGCTRL select pins carry a false path (DS189 Table 32 note 1: only CE timing is needed
    # for glitch-free switching; CE is tied high, and the select changes only while clk_fast is idle).
    assert "REF_PIN_NAME =~ S*" in tcl and "set_false_path -to $mux_sel" in tcl and "DS189" in tcl
    flow = (ROOT / "fpga" / "synth_official.tcl").read_text(encoding="utf-8")
    assert "report_cdc" in flow and "report_bus_skew" in flow
    marked = {
        "rtl/top_core.v": "por_meta", "rtl/engine.v": "rst_fast_meta", "rtl/fast_path.v": "pass_s1",
        "rtl/spi_slave.v": "sclk_s1", "rtl/platform/xilinx/clk_gen_xilinx.v": "locked2_meta",
    }
    for path, name in marked.items():
        text = (ROOT / path).read_text(encoding="utf-8")
        assert re.search(r'\(\* ASYNC_REG = "TRUE" \*\)[^;]*\b' + name + r"\b", text), path
    # No logic in front of a synchronizer: each asynchronous reset source is sampled on its own.
    core = (ROOT / "rtl" / "top_core.v").read_text(encoding="utf-8")
    assert "{por_meta[0], rst}" in core and "{lock_meta[0], clocks_locked}" in core
    wizard = (ROOT / "rtl" / "platform" / "xilinx" / "clk_gen_xilinx.v").read_text(encoding="utf-8")
    # The wizard reset follows LOCKED of MMCM1 only, so the power-on reset feeds one synchronizer (no CDC-11).
    assert "{axi_lock_meta[0], locked1}" in wizard and "axi_rst_meta" not in wizard


def test_official_cdc_parser():
    import run_official as ro

    text = (
        "ID      Severity  Count  Description\n"
        "------  --------  -----  --------------------------------------------------\n"
        "CDC-1   Critical    696  1-bit unknown CDC circuitry\n"
        "CDC-3   Info         32  1-bit synchronized with ASYNC_REG property\n"
        "\nSource Clock: clk_safe_raw\n"
        "  1  CDC-2   Warning   1-bit synchronized with missing ASYNC_REG property      2  Asynch Clock Groups  a/C  b/D\n"
    )
    assert ro.parse_cdc(text) == {
        "CDC-1": {"severity": "Critical", "count": 696, "description": "1-bit unknown CDC circuitry"},
        "CDC-3": {"severity": "Info", "count": 32, "description": "1-bit synchronized with ASYNC_REG property"},
    }


CLOCK_TABLES = """
| Intra Clock Table
| -----------------

Clock                   WNS(ns)      TNS(ns)  TNS Failing Endpoints  TNS Total Endpoints      WHS(ns)      THS(ns)  THS Failing Endpoints  THS Total Endpoints     WPWS(ns)     TPWS(ns)  TPWS Failing Endpoints  TPWS Total Endpoints
-----                   -------      -------  ---------------------  -------------------      -------      -------  ---------------------  -------------------     --------     --------  ----------------------  --------------------
clk_in                   48.466        0.000                      0                    2        0.257        0.000                      0                    2       15.000        0.000                       0                     5
  clk_safe_raw            0.286        0.000                      0                11249        0.052        0.000                      0                11249        1.500        0.000                       0                  5766
  clk_turbo_raw                                                                                                                                                       5.845        0.000                       0                     2


| Inter Clock Table
| -----------------

From Clock     To Clock           WNS(ns)      TNS(ns)  TNS Failing Endpoints  TNS Total Endpoints      WHS(ns)      THS(ns)  THS Failing Endpoints  THS Total Endpoints
----------     --------           -------      -------  ---------------------  -------------------      -------      -------  ---------------------  -------------------
clk_in         clk_safe_raw        -0.499       -0.499                      1                    1        0.073        0.000                      0                    1


| Other Path Groups Table
"""


def test_official_clock_tables():
    """Fmax is a property of the paths inside one clock, so it is read from the intra-clock table."""
    import run_official as ro

    tables = ro.parse_clock_tables(CLOCK_TABLES)
    assert tables["intra"] == {
        "clk_in": {"wns_ns": 48.466, "whs_ns": 0.257, "endpoints": 2},
        "clk_safe_raw": {"wns_ns": 0.286, "whs_ns": 0.052, "endpoints": 11249},
    }
    assert tables["inter"] == [{"from": "clk_in", "to": "clk_safe_raw", "wns_ns": -0.499, "whs_ns": 0.073, "endpoints": 1}]


def test_official_cdc_pairs_and_bus_skew():
    import run_official as ro

    pairs = ro.parse_cdc_pairs(
        "Severity  Source Clock      Destination Clock  CDC Type                 Exceptions           Endpoints  Safe  Unsafe  Unknown  No ASYNC_REG  \n"
        "--------  ----------------  -----------------  -----------------------  -------------------  ---------  ----  ------  -------  ------------  \n"
        "Critical  clk_safe_raw      clk_fast_safe      User Ignored             Asynch Clock Groups        686   274       0      412             0  \n"
        "Info      input port clock  clk_safe_raw       No Common Primary Clock  False Path                   3     3       0        0             0  \n"
    )
    assert pairs == [
        {"severity": "Critical", "from": "clk_safe_raw", "to": "clk_fast_safe", "type": "User Ignored", "exception": "Asynch Clock Groups",
         "endpoints": 686, "safe": 274, "unsafe": 0, "unknown": 412, "no_async_reg": 0},
        {"severity": "Info", "from": "input port clock", "to": "clk_safe_raw", "type": "No Common Primary Clock", "exception": "False Path",
         "endpoints": 3, "safe": 3, "unsafe": 0, "unknown": 0, "no_async_reg": 0},
    ]
    skew = ro.parse_bus_skew(
        "1. Bus Skew Report Summary\n2. Bus Skew Report Per Constraint\n\n1. Bus Skew Report Summary\n---\n\n"
        "Id  Position  From  To  Corner  Requirement(ns)  Actual(ns)  Slack(ns)\n"
        "1   5         [get_cells a]\n              [get_cells b]\n                    Slow              8.000       0.558      7.442\n"
        "2   7         [get_cells c]\n              [get_cells d]\n                    Fast              8.000       0.845      7.155\n"
        "\n2. Bus Skew Report Per Constraint\n   Slow              8.000       9.000      -1.000\n"
    )
    assert skew == {"constraints": 2, "worst_slack_ns": 7.155, "worst_actual_ns": 0.845}


def test_official_power_parser():
    import run_official as ro

    text = ("| Total On-Chip Power (W)  | 0.503        |\n| Design Power Budget (W)  | Unspecified* |\n| Dynamic (W)              | 0.440        |\n"
            "| Device Static (W)        | 0.062        |\n| Confidence Level         | Medium       |\n")
    assert ro.parse_power(text) == {"total_w": 0.503, "dynamic_w": 0.44, "static_w": 0.062, "confidence": "Medium"}


def test_turbo_mmcm_is_a_reconfigurable_clocking_wizard():
    """ADR-023: MMCM2 lives in a Clocking Wizard v6.0 with AXI4-Lite reconfiguration, driven by clkwiz_seq."""
    flow = (ROOT / "fpga" / "synth_official.tcl").read_text(encoding="utf-8")
    assert "create_ip -name clk_wiz" in flow and "CONFIG.USE_DYN_RECONFIG {true}" in flow and "CONFIG.INTERFACE_SELECTION {Enable_AXI}" in flow
    assert "CONFIG.PRIM_IN_FREQ {20.000}" in flow and "rtl/clkwiz_seq.v" in flow
    wrapper = (ROOT / "rtl" / "platform" / "xilinx" / "clk_gen_xilinx.v").read_text(encoding="utf-8")
    assert "clk_wiz_turbo" in wrapper and "clkwiz_seq" in wrapper and "MMCME2_ADV" not in wrapper
    assert "assign is_turbo      = sel_turbo;" not in wrapper   # the mux state is reported after a settle time


def test_committed_official_report_is_clean():
    """The official report in the repository meets timing and has no unsafe or logic-fed crossing (ADR-014, ADR-021)."""
    import json

    summary = json.loads((ROOT / "results" / "vivado" / "official" / "summary.json").read_text(encoding="utf-8"))
    assert float(summary["design_wns_ns"]) >= 0 and float(summary["design_whs_ns"]) >= 0
    assert int(summary["unrouted_nets"]) == 0
    assert not {"CDC-2", "CDC-10", "CDC-11"} & set(summary["cdc"])
    assert all(row["no_async_reg"] == 0 for row in summary["cdc_pairs"])
    # ADR-027 (written after this test): the clk_fast BUFGCTRL select is an intended crossing into a non-flop
    # primitive (DS189 Table 32 note 1), so report_cdc lists it as CDC-13 / unsafe. That endpoint, and only that
    # endpoint, is allowed; any other unsafe crossing still fails.
    allowed = [pin for pin in summary.get("cdc13_endpoints", []) if pin.endswith(("u_mux/S0", "u_mux/S1"))]
    assert allowed == summary.get("cdc13_endpoints", [])
    assert sum(row["unsafe"] for row in summary["cdc_pairs"]) == len(allowed)


def test_official_cdc_endpoint_parser():
    import run_official as ro

    text = ("  1  CDC-13  Critical  1-bit CDC path on a non-FD primitive      0  False Path  a/clk_sel_turbo_reg/C  u_core/u_clk/u_clk/u_mux/S1\n"
            "  2  CDC-3   Info      1-bit synchronized with ASYNC_REG property      2  Asynch Clock Groups  x/C  y/D\n")
    assert ro.parse_cdc_endpoints(text, "CDC-13") == ["u_core/u_clk/u_clk/u_mux/S1"]


def test_official_lane_override_needs_a_tag():
    """A different lane implementation may only go to a side folder, never to results/vivado/official/."""
    import pytest
    import run_official as ro

    with pytest.raises(SystemExit):
        ro.parse_args(["--lane-impl", "dsp_min"])
    args = ro.parse_args(["--lane-impl", "dsp_min", "--tag", "dspmin"])
    assert args.lane_impl == "dsp_min" and args.tag == "dspmin"
    assert ro.parse_args([]).lane_impl is None
