#!/usr/bin/env python3
"""Generate docs/RESULTS_SIM.md from the result files, so every number traces to a file."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "RESULTS_SIM.md"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _pct(x) -> str:
    return f"{x * 100:.2f}%" if x is not None else "n/a"


def accuracy_section() -> list[str]:
    lines = ["## Model accuracy [SIM]", "", "Source: `results/model/<model>/float_result.json`, `quant_result.json` (scripts `model/train.py`, `model/export.py`).", "", "| Model | Dataset | Seed | Epochs | Float (test) | Integer PTQ (test) | Drop (points) |", "| --- | --- | --- | --- | --- | --- | --- |"]
    any_row = False
    for model in ("s", "xs"):
        f = _load(ROOT / "results" / "model" / model / "float_result.json")
        q = _load(ROOT / "results" / "model" / model / "quant_result.json")
        if f is None:
            lines.append(f"| {model} | (not trained yet) | | | | | |")
            continue
        any_row = True
        lines.append(
            f"| {model} | {f['dataset']} | {f['seed']} | {f['epochs']} | {_pct(f['test_acc_float'])} | "
            f"{_pct(q['test_acc_integer']) if q else 'n/a'} | {q['drop_points']:.2f} |" if q else
            f"| {model} | {f['dataset']} | {f['seed']} | {f['epochs']} | {_pct(f['test_acc_float'])} | n/a | n/a |"
        )
    if any_row:
        lines += ["", "CIFAR-10 is a temporary stand-in: the target classes of the contest are [UNKNOWN]. Integer accuracy is the golden model on the full test set."]
    return lines


def arch_section() -> list[str]:
    lines = ["## Architecture counts [SIM]", "", "Source: `results/model/arch_<m>.json` (script `model/arch_report.py`).", "", "| Model | Weights | Bias | MACs | Ideal cycles K=8 | Ideal cycles K=16 |", "| --- | --- | --- | --- | --- | --- |"]
    for model in ("s", "xs"):
        a = _load(ROOT / "results" / "model" / f"arch_{model}.json")
        if a:
            lines.append(f"| {model} | {a['total_weights']} | {a['total_bias']} | {a['total_macs']} | {a['ideal_cycles']['8']} | {a['ideal_cycles']['16']} |")
    return lines


def campaign_section() -> list[str]:
    d = _load(ROOT / "results" / "sim" / "campaign_s.json")
    if d is None:
        return ["## Fault-injection campaign [SIM]", "", "Not run yet."]
    lines = [
        "## Fault-injection campaign, Python model [SIM]", "",
        f"Source: `results/sim/campaign_s.json` (script `model/campaign.py`, seed {d['seed']}). Accumulators from the golden model on {d['images']} images ({d['image_source']}).",
        f"{d['note']}", "",
        "| K | C3 | Injection | Trials | Clean | Corrected | Checksum lane | Recompute | Miscorrected | Escaped |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in d["rows"]:
        lines.append(f"| {r['k']} | {r['c3']} | {r['kind']} | {r['n']} | {r['clean']} | {r['corrected']} | {r['csum_lane']} | {r['recompute']} | {r['miscorrected']} | {r['escaped']} |")
    return lines


def rtl_section() -> list[str]:
    path = ROOT / "results" / "sim" / "rtl_regression.jsonl"
    lines = ["## RTL regressions [SIM]", ""]
    if not path.exists():
        return lines + ["Not recorded yet."]
    latest: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        latest[entry["bench"]] = entry
    lines += ["Source: `results/sim/rtl_regression.jsonl` (script `tools/sim.py --record`; latest run per bench).", "", "| Bench | Simulator | Date | Result |", "| --- | --- | --- | --- |"]
    for name in sorted(latest):
        e = latest[name]
        lines.append(f"| {name} | {e['simulator']} | {e['date']} | {'PASS' if e['passed'] else 'FAIL'}: {e['summary']} |")
    lines += ["", "Passing means the RTL matched the golden or checker model bit for bit in simulation. Simulation cannot reproduce real timing errors."]
    return lines


def fit_section() -> list[str]:
    d = _load(ROOT / "results" / "sim" / "fit_report.json")
    if d is None:
        return ["## Memory estimate [SIM]", "", "Not run yet."]
    lines = ["## Block-RAM estimate [SIM]", "", "Source: `results/sim/fit_report.json` (script `tools/fit_report.py`). Arithmetic on design parameters; capacities in `config/parts.yaml` are unverified.", "", "| Model | K | C3 | BRAM36-equivalent needed |", "| --- | --- | --- | --- |"]
    for r in d["estimates"]:
        lines.append(f"| {r['model']} | {r['K']} | {r['C3_EN']} | {r['bram36_equivalent']:.1f} |")
    return lines


def vivado_section() -> list[str]:
    import csv

    path = ROOT / "fpga" / "reports" / "summary.csv"
    head = ["## Vivado out-of-context [VIVADO-STA]", ""]
    if not path.exists():
        return head + ["No data yet."]
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    names = {"0": "lut", "1": "dsp_min", "2": "dsp_full"}
    lines = head + [
        f"Source: `{path.relative_to(ROOT).as_posix()}` (script `fpga/run_matrix.py`, Vivado 2025.2, out of context, top `engine`, model s).",
        "Fmax = 1000 / (target period - WNS). Where the target is met, Fmax is a lower bound. Targets: clk_safe 7.0 ns; clk_fast 6.4 ns for lut, 3.0 ns for the DSP lanes.",
        "For lut, every non-MAC endpoint of clk_fast is held to 70% of the period (SPEC 7.4, ADR-012): its WNS is measured against that tighter limit.",
        "Static timing is conservative; the frequency at which a real device fails can only be measured on the board.",
        "",
        "| Part | K | Lane | C3 | LUT | FF | BRAM36 | DSP | Fmax clk_safe (MHz) | Fmax clk_fast (MHz) | WNS MAC (ns) | WNS non-MAC (ns) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in sorted(rows, key=lambda r: (r["part"], int(r["K"]), r["LANE_IMPL"], r["C3_EN"])):
        lines.append(
            f"| {r['part']} | {r['K']} | {names.get(r['LANE_IMPL'], r['LANE_IMPL'])} | {r['C3_EN']} | {float(r['lut']):.0f} | {float(r['ff']):.0f} | "
            f"{float(r['bram36_equiv']):.1f} | {float(r['dsp']):.0f} | {float(r['fmax_safe_mhz']):.1f} | {float(r['fmax_fast_mhz']):.1f} | "
            f"{r.get('wns_mac_ns', '')} | {r.get('wns_nonmac_ns', '')} |"
        )
    failed = sorted(p.name[: -len(".log")] for p in (ROOT / "fpga" / "reports").glob("*_final.log") if not (p.with_suffix("") / "summary.txt").exists())
    if failed:
        parts = sorted({name.split("_")[0] for name in failed})
        lines += ["", f"Did not fit ({len(failed)} runs, parts {', '.join(parts)}): the memories need more block RAM than these parts have (model s uses 14 BRAM36 tiles on xc7s25), so Vivado moved them to LUT RAM, which then overflowed (DRC UTLZ-1 in the local `*_final.log` files)."]
    return lines


def main() -> int:
    parts = [
        "# RESULTS_SIM", "",
        "Generated by `python tools/gen_results_doc.py`. Do not edit by hand.", "",
        "No number in this file was measured on hardware. Labels: [SIM] simulation or Python model, [VIVADO-STA] static Vivado estimate.", "",
    ]
    for section in (accuracy_section, arch_section, campaign_section, rtl_section, fit_section, vivado_section):
        parts += section() + [""]
    OUT.write_text("\n".join(parts), encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
