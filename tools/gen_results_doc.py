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
    path = ROOT / "fpga" / "reports" / "summary.csv"
    if path.exists():
        return ["## Vivado out-of-context [VIVADO-STA]", "", f"See `{path.relative_to(ROOT).as_posix()}` (script `fpga/run_matrix.py`)."]
    return ["## Vivado out-of-context [VIVADO-STA]", "", "No data yet. Vivado 2025.2 on this machine has no Spartan-7 device support; see STATUS.md, M11."]


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
