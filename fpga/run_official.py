#!/usr/bin/env python3
"""Official synthesis report for the contest chip XC7S25CSGA225-1 (ADR-014).

Runs fpga/synth_official.tcl on the variant of config/hw_zero7.yaml, keeps the Vivado reports
in results/vivado/official/ and writes summary.json and summary.md next to them. Every number
is a static Vivado estimate, labelled [VIVADO-STA]; nothing here is measured on a board.

A run with --tag NAME is a side run (for example another clk_safe divider): its reports go to
results/vivado/official_NAME/ and its log to build/official_synth_NAME.log, and the official
folder stays untouched.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from check_env import find_vivado  # noqa: E402

CONFIG = ROOT / "config" / "hw_zero7.yaml"
OUT = ROOT / "results" / "vivado" / "official"
LANE_IMPL = {"lut": 0, "dsp_min": 1, "dsp_full": 2}
UTIL_ROWS = {
    "Slice LUTs": "lut", "Slice Registers": "ff", "Block RAM Tile": "bram_tile", "DSPs": "dsp",
    "Bonded IOB": "iob", "BUFGCTRL": "bufgctrl", "MMCME2_ADV": "mmcm", "Slice": "slice",
}


def parse_utilization(text: str) -> dict:
    """Used, available and percentage for the rows of interest of report_utilization."""
    found: dict[str, dict] = {}
    for line in text.splitlines():
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 5 or cells[0] not in UTIL_ROWS or UTIL_ROWS[cells[0]] in found:
            continue
        try:
            used, available, util = float(cells[1]), float(cells[-2]), float(cells[-1])
        except ValueError:
            continue
        found[UTIL_ROWS[cells[0]]] = {"used": used, "available": available, "util_pct": util}
    return found


def parse_summary(text: str) -> dict:
    """Key/value lines and per-clock lines written by fpga/synth_official.tcl."""
    out: dict = {"clocks": []}
    for line in text.splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "clock":
            entry = {"name": parts[1]}
            for key, value in zip(parts[2::2], parts[3::2]):
                entry[key] = None if value == "NA" else float(value)
            out["clocks"].append(entry)
        else:
            out[parts[0]] = " ".join(parts[1:])
    return out


def count_violations(text: str) -> dict:
    """Number of violations per severity in report_drc / report_methodology."""
    counts: dict[str, int] = {}
    for m in re.finditer(r"^\|\s*[A-Z0-9-]+\s*\|\s*(Error|Critical Warning|Warning|Advisory)\s*\|.*\|\s*(\d+)\s*\|\s*$", text, re.M):
        counts[m.group(1)] = counts.get(m.group(1), 0) + int(m.group(2))
    return counts


def parse_clock_tables(text: str) -> dict:
    """Intra-clock and inter-clock tables of report_timing_summary: worst slacks and endpoint counts."""
    intra: dict[str, dict] = {}
    inter: list[dict] = []
    section = None
    for line in text.splitlines():
        if line.startswith("| "):
            title = line[2:].strip()
            if not title.startswith("-"):   # the ruler under a title keeps the section
                section = {"Intra Clock Table": "intra", "Inter Clock Table": "inter"}.get(title)
            continue
        cells = line.split()
        try:
            if section == "intra" and len(cells) >= 9:
                intra[cells[0]] = {"wns_ns": float(cells[1]), "whs_ns": float(cells[5]), "endpoints": int(cells[4])}
            elif section == "inter" and len(cells) >= 10:
                inter.append({"from": cells[0], "to": cells[1], "wns_ns": float(cells[2]), "whs_ns": float(cells[6]), "endpoints": int(cells[5])})
        except ValueError:
            continue   # header and ruler lines
    return {"intra": intra, "inter": inter}


CDC_MEANING = {
    "CDC-1": "single-bit crossing without a synchronizer: the quasi-static injection configuration and layer index (SPEC 7.8)",
    "CDC-2": "two-flop synchronizer without ASYNC_REG",
    "CDC-3": "two-flop synchronizer with ASYNC_REG",
    "CDC-4": "multi-bit crossing without a synchronizer: quasi-static injection masks (SPEC 7.8)",
    "CDC-10": "logic in front of a synchronizer; SPEC 7.8 does not allow it",
    "CDC-15": "crossing captured under a clock enable: the memories of the asynchronous FIFOs and the quasi-static STARVE_CYCLES word",
}


def parse_cdc_pairs(text: str) -> list[dict]:
    """The table per clock pair at the top of report_cdc."""
    rows: list[dict] = []
    for line in text.splitlines():
        cells = re.split(r"\s{2,}", line.strip())
        if len(cells) == 10 and cells[0] in ("Critical", "Warning", "Info") and all(c.isdigit() for c in cells[5:]):
            counts = [int(c) for c in cells[5:]]
            rows.append({"severity": cells[0], "from": cells[1], "to": cells[2], "type": cells[3], "exception": cells[4], "endpoints": counts[0],
                         "safe": counts[1], "unsafe": counts[2], "unknown": counts[3], "no_async_reg": counts[4]})
    return rows


POWER_ROWS = {"Total On-Chip Power (W)": "total_w", "Dynamic (W)": "dynamic_w", "Device Static (W)": "static_w", "Confidence Level": "confidence"}


def parse_power(text: str) -> dict:
    """Headline rows of report_power.  A vectorless estimate, not a measurement."""
    found: dict = {}
    for line in text.splitlines():
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) == 2 and cells[0] in POWER_ROWS and POWER_ROWS[cells[0]] not in found:
            key = POWER_ROWS[cells[0]]
            found[key] = cells[1] if key == "confidence" else float(cells[1])
    return found


def parse_bus_skew(text: str) -> dict:
    """Number of bus-skew constraints and the worst case, from the summary table of report_bus_skew."""
    start = text.rfind("1. Bus Skew Report Summary")
    end = text.find("2. Bus Skew Report Per Constraint", start)
    rows = re.findall(r"^\s+(?:Slow|Fast)\s+([\d.]+)\s+([\d.]+)\s+(-?[\d.]+)\s*$", text[start:end if end > 0 else None], re.M)
    if not rows:
        return {"constraints": 0, "worst_slack_ns": None, "worst_actual_ns": None}
    return {"constraints": len(rows), "worst_slack_ns": min(float(r[2]) for r in rows), "worst_actual_ns": max(float(r[1]) for r in rows)}


def parse_cdc(text: str) -> dict:
    """Rule, severity and count from the summary table at the top of report_cdc."""
    found: dict[str, dict] = {}
    for line in text.splitlines():
        if line.startswith("Source Clock"):
            break
        m = re.match(r"^(CDC-\d+)\s+(Critical|Warning|Info)\s+(\d+)\s+(.*\S)\s*$", line)
        if m:
            found[m.group(1)] = {"severity": m.group(2), "count": int(m.group(3)), "description": m.group(4)}
    return found


def build_summary(out: Path) -> dict:
    summary = parse_summary((out / "summary.txt").read_text(encoding="utf-8"))
    summary["utilization_post_route"] = parse_utilization((out / "impl_utilization.rpt").read_text(encoding="utf-8", errors="replace"))
    summary["utilization_post_synth"] = parse_utilization((out / "synth_utilization.rpt").read_text(encoding="utf-8", errors="replace"))
    summary["drc"] = count_violations((out / "impl_drc.rpt").read_text(encoding="utf-8", errors="replace"))
    summary["methodology"] = count_violations((out / "impl_methodology.rpt").read_text(encoding="utf-8", errors="replace"))
    read = lambda name: (out / name).read_text(encoding="utf-8", errors="replace")  # noqa: E731
    summary["power"] = parse_power(read("impl_power.rpt"))
    if (out / "impl_cdc_details.rpt").exists():
        summary["cdc"] = parse_cdc(read("impl_cdc_details.rpt"))
        summary["cdc_pairs"] = parse_cdc_pairs(read("impl_cdc.rpt"))
        summary["bus_skew"] = parse_bus_skew(read("impl_bus_skew.rpt"))
    else:
        summary["cdc"] = None
    tables = parse_clock_tables((out / "impl_timing_summary.rpt").read_text(encoding="utf-8", errors="replace"))
    for clk in summary["clocks"]:
        row = tables["intra"].get(clk["name"])
        if row:
            clk["intra_wns_ns"], clk["intra_whs_ns"], clk["intra_endpoints"] = row["wns_ns"], row["whs_ns"], row["endpoints"]
            clk["fmax_mhz"] = 1000.0 / (clk["period_ns"] - row["wns_ns"])
    summary["inter_clock"] = tables["inter"]
    return summary


def by_severity(counts: dict) -> str:
    return ", ".join(f"{name} {count}" for name, count in counts.items()) or "none"


def write_markdown(summary: dict, out: Path) -> None:
    util = summary["utilization_post_route"]
    names = {"lut": "Slice LUTs", "ff": "Slice registers", "bram_tile": "Block RAM tiles", "dsp": "DSP48E1", "iob": "Bonded IOB",
             "bufgctrl": "BUFGCTRL (global buffers)", "mmcm": "MMCME2_ADV"}
    lines = [
        "# Official synthesis report: summary [VIVADO-STA]", "",
        f"Generated by `{summary['command']}` (`fpga/run_official.py`, `fpga/synth_official.tcl`). Do not edit by hand.", "",
        f"Tool: Vivado {summary['vivado']}. Part: `{summary['part']}`. Top: `{summary['top']}` with `board/zero7.xdc`.",
        f"Variant: model s, K = {summary['K']}, LANE_IMPL = {summary['LANE_IMPL']} (0 = lut), C3_EN = {summary['C3_EN']}, safe divider {summary['SAFE_DIV']} "
        f"(VCO 1000 MHz, so clk_safe = {1000.0 / float(summary['SAFE_DIV']):g} MHz).",
        "All numbers are static estimates after place and route. Nothing in this file was measured on a board.",
        "The I/O standards in `board/zero7.xdc` are unconfirmed (LVCMOS33 assumed), so no bitstream is written.", "",
        "## Resources after place and route [VIVADO-STA]", "",
        "| Resource | Used | Available | Utilisation |", "| --- | --- | --- | --- |",
    ]
    for key, label in names.items():
        if key in util:
            u = util[key]
            lines.append(f"| {label} | {u['used']:g} | {u['available']:g} | {u['util_pct']:.2f}% |")
    lines += ["", "## Timing after place and route [VIVADO-STA]", "",
              "Paths inside one clock. Clocks without such paths (the MMCM feedback clocks and the raw turbo clock) are left out.", "",
              "| Clock | Period (ns) | Endpoints | WNS setup (ns) | WHS hold (ns) | Fmax = 1000 / (period - WNS) (MHz) |",
              "| --- | --- | --- | --- | --- | --- |"]
    for clk in summary["clocks"]:
        if "fmax_mhz" in clk:
            lines.append(f"| {clk['name']} | {clk['period_ns']:.3f} | {clk['intra_endpoints']} | {clk['intra_wns_ns']:.3f} | "
                         f"{clk['intra_whs_ns']:.3f} | {clk['fmax_mhz']:.1f} |")
    lines += ["", "Timed paths between two clocks. The crossings between `clk_safe` and `clk_fast` are asynchronous by design (SPEC 7.8) "
                  "and appear in the clock-domain crossing section instead.", "",
              "| From | To | Endpoints | WNS setup (ns) | WHS hold (ns) |", "| --- | --- | --- | --- | --- |"]
    for row in summary["inter_clock"]:
        lines.append(f"| {row['from']} | {row['to']} | {row['endpoints']} | {row['wns_ns']:.3f} | {row['whs_ns']:.3f} |")
    if not summary["inter_clock"]:
        lines.append("| none | | | | |")
    lines += ["", f"Design worst setup slack {summary['design_wns_ns']} ns, worst hold slack {summary['design_whs_ns']} ns, "
                  f"unrouted nets {summary['unrouted_nets']}.",
              "`clk_fast_turbo` is analysed at turbo level 0, which equals the safe frequency. Running the lanes above that "
              "frequency is the experiment of the project and is outside what static timing covers.", "",
              "## Checks [VIVADO-STA]", "",
              f"- DRC violations by severity: {by_severity(summary['drc'])}.",
              f"- Methodology violations by severity: {by_severity(summary['methodology'])}.", ""]
    if summary.get("cdc") is not None:
        lines += ["## Clock-domain crossings [VIVADO-STA]", "",
                  "From `report_cdc` (`impl_cdc.rpt`, endpoints in `impl_cdc_details.rpt`). The crossing rules are in SPEC 7.8 and ADR-021.", "",
                  "| Rule | Severity | Endpoints | Vivado description | What it is in this design |", "| --- | --- | --- | --- | --- |"]
        for rule, row in summary["cdc"].items():
            lines.append(f"| {rule} | {row['severity']} | {row['count']} | {row['description']} | {CDC_MEANING.get(rule, 'not classified yet')} |")
        lines += ["", "| From | To | Exception | Endpoints | Safe | Unsafe | Unknown | Without ASYNC_REG |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
        for row in summary["cdc_pairs"]:
            lines.append(f"| {row['from']} | {row['to']} | {row['exception']} | {row['endpoints']} | {row['safe']} | {row['unsafe']} | "
                         f"{row['unknown']} | {row['no_async_reg']} |")
        skew = summary["bus_skew"]
        lines += ["", "\"Unknown\" endpoints are the quasi-static signals: `report_cdc` cannot see the rule that they only change while the fast "
                      "domain is idle.",
                  f"Bus skew of the FIFO pointer crossings (`impl_bus_skew.rpt`): {skew['constraints']} constraints, worst slack "
                  f"{skew['worst_slack_ns']} ns, largest skew {skew['worst_actual_ns']} ns.", ""]
    power = summary["power"]
    lines += ["## Power estimate [VIVADO-STA]", "",
              f"`report_power` without switching-activity data (`impl_power.rpt`): total {power['total_w']} W, of which dynamic {power['dynamic_w']} W "
              f"and device static {power['static_w']} W; Vivado rates its own confidence as \"{power['confidence']}\". An estimate, not a measurement.", ""]
    if summary.get("note"):
        lines += ["## Note", "", summary["note"], ""]
    lines += ["## Report files", ""]
    for path in sorted(out.glob("*.rpt")):
        lines.append(f"- `{path.name}`")
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--safe-div", type=float, default=None, help="clk_safe divider of the 1000 MHz VCO; default from config/hw_zero7.yaml")
    parser.add_argument("--summary-only", action="store_true", help="rebuild summary.json and summary.md from existing reports")
    parser.add_argument("--note", default="", help="one sentence of provenance kept in summary.json and summary.md")
    parser.add_argument("--tag", default="", help="side run: reports in results/vivado/official_TAG/, log in build/official_synth_TAG.log")
    args = parser.parse_args()
    if args.tag and not re.fullmatch(r"[a-z0-9]+", args.tag):
        parser.error("--tag takes lower-case letters and digits only")
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    safe_div = args.safe_div or cfg["clock"]["vco_mhz"] / cfg["clock"]["f_safe_mhz"]
    out = OUT.with_name(f"{OUT.name}_{args.tag}") if args.tag else OUT
    command = "python tools/run.py synth-official" + (f" --safe-div {safe_div:g}" if args.safe_div else "") + (f" --tag {args.tag}" if args.tag else "")
    out.mkdir(parents=True, exist_ok=True)
    if not args.summary_only:
        vivado = find_vivado()
        if vivado is None:
            print("Vivado not found. Install Vivado 2025.2 or set VIVADO_BIN, then run this again.")
            return 2
        for old in out.glob("*.rpt"):
            old.unlink()
        (out / "summary.txt").unlink(missing_ok=True)
        log = ROOT / "build" / (f"official_synth_{args.tag}.log" if args.tag else "official_synth.log")
        log.parent.mkdir(parents=True, exist_ok=True)
        print(f"[VIVADO-STA] official run on {cfg['part']}: K={cfg['K']} lane={cfg['LANE_IMPL']} C3={cfg['C3_EN']} safe_div={safe_div:g}", flush=True)
        res = subprocess.run(
            [vivado, "-mode", "batch", "-nojournal", "-log", str(log), "-source", str(ROOT / "fpga" / "synth_official.tcl"), "-tclargs",
             str(out), str(cfg["K"]), str(LANE_IMPL[cfg["LANE_IMPL"]]), str(cfg["C3_EN"]),
             str(cfg["WEIGHT_AW"]), str(cfg["ACT0_AW"]), str(cfg["ACT1_AW"]), f"{safe_div:g}"],
            cwd=ROOT, capture_output=True, text=True, errors="replace",
        )
        if res.returncode != 0 or not (out / "summary.txt").exists():
            print(f"failed; see {log.relative_to(ROOT)}")
            return 1
    # Rebuilding a summary keeps the command and the note of the run that produced the reports.
    kept = json.loads((out / "summary.json").read_text(encoding="utf-8")) if args.summary_only and (out / "summary.json").exists() else {}
    summary = build_summary(out)
    summary["command"] = kept.get("command", command)
    note = args.note or kept.get("note", "")
    if note:
        summary["note"] = note
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8", newline="\n")
    write_markdown(summary, out)
    util = summary["utilization_post_route"]
    print(f"[VIVADO-STA] LUT {util['lut']['used']:g}/{util['lut']['available']:g}, FF {util['ff']['used']:g}, "
          f"BRAM tiles {util['bram_tile']['used']:g}/{util['bram_tile']['available']:g}, WNS {summary['design_wns_ns']} ns")
    print(f"wrote {out.relative_to(ROOT).as_posix()}/summary.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
