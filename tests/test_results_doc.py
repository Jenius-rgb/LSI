"""docs/RESULTS_SIM.md generator: the efficiency figures follow the definitions of Jiang et al. (2025)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import gen_results_doc as grd  # noqa: E402


def test_compute_efficiency_and_throughput():
    """Compute efficiency = throughput / (2 x MAC units x f); with one image that is MACs / (lanes x cycles)."""
    eff, gops = grd.efficiency(macs=2_216_960, cycles=277_895, lanes=8, f_mhz=125.0)
    assert abs(eff - 2_216_960 / (8 * 277_895)) < 1e-12
    assert abs(gops - 2 * 2_216_960 / (277_895 / 125e6) / 1e9) < 1e-9
