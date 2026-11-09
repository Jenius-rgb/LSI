#!/usr/bin/env python3
"""Turn Vivado reports under fpga/reports/ into one CSV (label [VIVADO-STA])."""
from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "fpga" / "reports"

UTIL_FIELDS = {
    "lut": r"\|\s*Slice LUTs\*?\s*\|\s*([\d.]+)",
    "ff": r"\|\s*Slice Registers\s*\|\s*([\d.]+)",
    "bram36_equiv": r"\|\s*Block RAM Tile\s*\|\s*([\d.]+)",
    "dsp": r"\|\s*DSPs\s*\|\s*([\d.]+)",
}


def parse_utilization(text: str) -> dict:
    out = {}
    for key, pattern in UTIL_FIELDS.items():
        match = re.search(pattern, text)
        out[key] = float(match.group(1)) if match else None
    return out


def parse_summary(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2:
            out[parts[0]] = parts[1]
    return out


def fmax_mhz(period_ns: float, wns_ns: float) -> float:
    """Maximum frequency that closes setup timing, from the target period and the worst slack."""
    return 1000.0 / (period_ns - wns_ns)


PATH_RE = re.compile(r"Source:\s+(\S+).*?Destination:\s+(\S+).*?Slack \(([A-Z]+)\)\s*:\s*(-?[\d.]+)ns", re.S)


def parse_paths(text: str) -> list[dict]:
    """Source, destination and slack of each path in a report_timing report."""
    paths = []
    for block in re.split(r"(?=^Slack \()", text, flags=re.M):
        match = re.search(r"Slack \(([A-Z]+)\)\s*:\s*(-?[\d.]+)ns.*?Source:\s+(\S+).*?Destination:\s+(\S+)", block, re.S)
        if match:
            paths.append({"status": match.group(1), "slack": float(match.group(2)), "source": match.group(3), "destination": match.group(4)})
    return paths


def is_mac_path(path: dict) -> bool:
    """A path whose endpoints sit in the MAC and accumulator registers of a lane."""
    pattern = r"(data_lane|csum_lane).*impl.*(/p_reg|/m_reg|/acc_reg|/a_r|/w_r|/p\[|/m\[|/acc\[)"
    return bool(re.search(pattern, path["destination"]) and re.search(r"(data_lane|csum_lane)", path["source"]))


def collect(report_dir: Path = REPORTS) -> list[dict]:
    rows = []
    for variant in sorted(p for p in report_dir.iterdir() if p.is_dir()):
        summary_path = variant / "summary.txt"
        util_path = variant / "utilization.rpt"
        if not summary_path.exists() or not util_path.exists():
            continue
        s = parse_summary(summary_path.read_text(encoding="utf-8", errors="replace"))
        u = parse_utilization(util_path.read_text(encoding="utf-8", errors="replace"))
        t_safe, t_fast = float(s["T_SAFE_NS"]), float(s["T_FAST_NS"])
        row = {
            "variant": variant.name, "label": "[VIVADO-STA]", "part": s.get("part"), "K": s.get("K"),
            "LANE_IMPL": s.get("LANE_IMPL"), "C3_EN": s.get("C3_EN"), **u,
            "wns_safe_ns": s.get("WNS_clk_safe"), "wns_fast_ns": s.get("WNS_clk_fast"),
            "fmax_safe_mhz": fmax_mhz(t_safe, float(s["WNS_clk_safe"])),
            "fmax_fast_mhz": fmax_mhz(t_fast, float(s["WNS_clk_fast"])),
        }
        rows.append(row)
    return rows


def main() -> int:
    rows = collect()
    if not rows:
        print("no reports under fpga/reports/")
        return 1
    out = REPORTS / "summary.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {out.relative_to(ROOT)}: {len(rows)} variants [VIVADO-STA]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
