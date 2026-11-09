#!/usr/bin/env python3
"""Turn Vivado reports under fpga/reports/ into one CSV (label [VIVADO-STA])."""
from __future__ import annotations

import csv
import re
import sys
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


def spec_7_4_gap(period_ns: float, wns_mac: float, wns_nonmac: float) -> float:
    """Margin of non-MAC paths over the worst MAC path, in percent of the MAC delay (ADR-012)."""
    return 100.0 * (wns_nonmac - wns_mac) / (period_ns - wns_mac)


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


def collect(report_dir: Path = REPORTS, tag: str = "") -> list[dict]:
    """Collect report directories; with a tag, only those whose name ends in _<tag>."""
    rows = []
    for variant in sorted(p for p in report_dir.iterdir() if p.is_dir() and (not tag or p.name.endswith(f"_{tag}"))):
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
            "t_safe_ns": t_safe, "t_fast_ns": t_fast,
        }
        if "WNS_MAC" in s and "WNS_NONMAC" in s:
            mac, nonmac = float(s["WNS_MAC"]), float(s["WNS_NONMAC"])
            factor = float(s.get("NONMAC_FACTOR", "1.0"))
            row.update({
                "wns_mac_ns": mac, "wns_nonmac_ns": nonmac, "nonmac_factor": factor,
                # With a factor below 1, non-MAC slack is already measured against the tighter limit.
                "gap_pct_of_mac_delay": spec_7_4_gap(t_fast, mac, nonmac) if factor == 1.0 else "",
                "worst_nonmac": s.get("WORST_NONMAC_ENDPOINT", ""),
            })
        rows.append(row)
    return rows


def main() -> int:
    tag = sys.argv[1] if len(sys.argv) > 1 else ""
    rows = collect(tag=tag)
    if not rows:
        print("no reports under fpga/reports/")
        return 1
    out = REPORTS / "summary.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        fields = list(dict.fromkeys(k for row in rows for k in row))
        writer = csv.DictWriter(fh, fieldnames=fields, restval="")
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {out.relative_to(ROOT)}: {len(rows)} variants [VIVADO-STA]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
