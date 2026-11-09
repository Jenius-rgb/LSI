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
