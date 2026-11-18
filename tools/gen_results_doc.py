#!/usr/bin/env python3
"""Generate docs/RESULTS_SIM.md from the result files, so every number traces to a file."""
from __future__ import annotations

import json
import re
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
        "Run: `final` is the M11 matrix; `pre029` and `post029` are the same variant before and after ADR-029.",
        "",
        "| Part | K | Lane | C3 | Run | LUT | FF | BRAM36 | DSP | Fmax clk_safe (MHz) | Fmax clk_fast (MHz) | WNS MAC (ns) | WNS non-MAC (ns) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in sorted(rows, key=lambda r: (r["part"], int(r["K"]), r["LANE_IMPL"], r["C3_EN"], r["variant"])):
        lines.append(
            f"| {r['part']} | {r['K']} | {names.get(r['LANE_IMPL'], r['LANE_IMPL'])} | {r['C3_EN']} | {r['variant'].rsplit('_', 1)[-1]} | "
            f"{float(r['lut']):.0f} | {float(r['ff']):.0f} | "
            f"{float(r['bram36_equiv']):.1f} | {float(r['dsp']):.0f} | {float(r['fmax_safe_mhz']):.1f} | {float(r['fmax_fast_mhz']):.1f} | "
            f"{r.get('wns_mac_ns', '')} | {r.get('wns_nonmac_ns', '')} |"
        )
    failed = sorted(p.name[: -len(".log")] for p in (ROOT / "fpga" / "reports").glob("*_final.log") if not (p.with_suffix("") / "summary.txt").exists())
    if failed:
        parts = sorted({name.split("_")[0] for name in failed})
        lines += ["", f"Did not fit ({len(failed)} runs, parts {', '.join(parts)}): the memories need more block RAM than these parts have (model s uses 14 BRAM36 tiles on xc7s25), so Vivado moved them to LUT RAM, which then overflowed (DRC UTLZ-1 in the local `*_final.log` files)."]
    return lines


def official_section() -> list[str]:
    """Complete design on the contest chip (ADR-014); side runs are listed by their tag."""
    base = ROOT / "results" / "vivado"
    head = ["## Official synthesis on XC7S25CSGA225-1, complete design [VIVADO-STA]", ""]
    main_run = _load(base / "official" / "summary.json")
    if main_run is None:
        return head + ["No data yet. Run `python tools/run.py synth-official`."]
    util = main_run["utilization_post_route"]
    names = {"lut": "Slice LUTs", "ff": "Slice registers", "bram_tile": "Block RAM tiles", "dsp": "DSP48E1", "bufgctrl": "Global clock buffers", "mmcm": "MMCM"}
    lines = head + [
        f"Source: `results/vivado/official/summary.json` and the reports next to it (`{main_run['command']}`, Vivado {main_run['vivado']}).",
        f"Top `{main_run['top']}` with `board/zero7.xdc`: model s, K = {main_run['K']}, lut lanes, C3_EN = {main_run['C3_EN']}, "
        f"clk_safe = {1000.0 / float(main_run['SAFE_DIV']):g} MHz. After place and route; no bitstream, because the I/O standards of the board are unconfirmed.",
        "", "| Resource | Used | Available | Utilisation |", "| --- | --- | --- | --- |",
    ]
    lines += [f"| {label} | {util[key]['used']:g} | {util[key]['available']:g} | {util[key]['util_pct']:.2f}% |" for key, label in names.items() if key in util]
    lines += ["", "| Clock | Period (ns) | Endpoints | WNS setup (ns) | WHS hold (ns) | Fmax (MHz) |", "| --- | --- | --- | --- | --- | --- |"]
    lines += [f"| {c['name']} | {c['period_ns']:.3f} | {c['intra_endpoints']} | {c['intra_wns_ns']:.3f} | {c['intra_whs_ns']:.3f} | {c['fmax_mhz']:.1f} |"
              for c in main_run["clocks"] if "fmax_mhz" in c]
    lines += ["", f"Paths inside one clock; Fmax = 1000 / (period - WNS). Design worst setup slack {main_run['design_wns_ns']} ns, worst hold slack "
                  f"{main_run['design_whs_ns']} ns, unrouted nets {main_run['unrouted_nets']}.",
              "`clk_fast_turbo` is analysed at turbo level 0, the safe frequency. Running the lanes faster than that is the experiment of the project; "
              "static timing says nothing about it."]
    if main_run.get("cdc"):
        counts = ", ".join(f"{rule} {row['count']} ({row['severity'].lower()})" for rule, row in main_run["cdc"].items())
        lines += ["", f"Clock-domain crossings by `report_cdc` rule: {counts}. Their meaning in this design is in `results/vivado/official/summary.md` and SPEC 7.8."]
    if main_run.get("power"):
        power = main_run["power"]
        lines += ["", f"Power by `report_power` without switching-activity data: total {power['total_w']} W (dynamic {power['dynamic_w']} W, "
                      f"device static {power['static_w']} W), Vivado confidence \"{power['confidence']}\". An estimate, not a measurement."]
    side = [(d.name, _load(d / "summary.json")) for d in sorted(base.glob("official_*")) if (d / "summary.json").exists()]
    if side:
        lines += ["", "Side runs:", ""]
        lines += [f"- `results/vivado/{name}/`: clk_safe = {1000.0 / float(run['SAFE_DIV']):g} MHz, design worst setup slack {run['design_wns_ns']} ns. {run.get('note', '')}".rstrip()
                  for name, run in side]
    return lines


SPI_CLOCKS_MHZ = (1, 5, 10, 20)   # assumptions for the table; the real limit of the board is unknown
IMAGE_BYTES = 3 * 32 * 32


def efficiency(macs: int, cycles: int, lanes: int, f_mhz: float) -> tuple[float, float]:
    """Compute efficiency and throughput as defined by Jiang et al. (arXiv 2505.13461, Eq. 5-7).

    Throughput = 2 x MACs / latency; compute efficiency = throughput / (2 x MAC units x f), which for
    one image is MACs / (MAC units x cycles). Only the data lanes count as MAC units here.
    """
    latency_s = cycles / (f_mhz * 1e6)
    return macs / (lanes * cycles), 2 * macs / latency_s / 1e9


def latency_section() -> list[str]:
    """Where the time of one image goes: compute from simulated cycles and the STA clock, transfer as a function of the SPI clock."""
    head = ["## Latency budget per image, official variant [SIM] x [VIVADO-STA]", ""]
    run = _load(ROOT / "results" / "vivado" / "official" / "summary.json")
    path = ROOT / "results" / "sim" / "rtl_regression.jsonl"
    cycles = None
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            entry = json.loads(line)
            m = re.search(r"cycles_mean=(\d+)", entry["summary"])
            if entry["bench"] == "engine_s_k8_c1_n200" and entry["passed"] and m:
                cycles = int(m.group(1))
    if run is None or cycles is None:
        return head + ["No data yet."]
    period_ns = next(c["period_ns"] for c in run["clocks"] if c["name"] == "clk_fast_safe")
    compute_ms = cycles * period_ns * 1e-6
    lines = head + [
        "An estimate, not a measurement. Inputs: mean clk_safe cycles per image of bench `engine_s_k8_c1_n200` [SIM] "
        f"({cycles}, `results/sim/rtl_regression.jsonl`) and the clock period of the official run [VIVADO-STA] ({period_ns:.3f} ns, "
        "`results/vivado/official/summary.json`), with clk_fast on the safe clock.",
        f"Compute time = cycles x period = {compute_ms:.3f} ms per image, {1000.0 / compute_ms:.0f} images per second if nothing else took time.",
        f"The image is {IMAGE_BYTES} bytes and travels over SPI. Transfer time below counts the payload bits only (no command bytes, no polling, "
        "no camera capture); the SPI clocks are assumptions, because the speed the board allows is [UNKNOWN].",
        "", "| Assumed SPI clock (MHz) | Image transfer (ms) | Compute (ms) | Sum (ms) | Share of transfer |", "| --- | --- | --- | --- | --- |",
    ]
    for mhz in SPI_CLOCKS_MHZ:
        transfer_ms = IMAGE_BYTES * 8 / (mhz * 1e6) * 1e3
        total = transfer_ms + compute_ms
        lines.append(f"| {mhz} | {transfer_ms:.3f} | {compute_ms:.3f} | {total:.3f} | {100.0 * transfer_ms / total:.0f}% |")
    arch = _load(ROOT / "results" / "model" / "arch_s.json")
    if arch:
        f_mhz = 1000.0 / period_ns
        eff, gops = efficiency(arch["total_macs"], cycles, run["K"] if isinstance(run.get("K"), int) else int(run["K"]), f_mhz)
        lines += ["", f"With the definitions of Jiang et al. (arXiv 2505.13461): compute efficiency = MACs / (data lanes x cycles) = "
                      f"{arch['total_macs']} / ({run['K']} x {cycles}) = {100 * eff:.2f}%, throughput {gops:.2f} GOP/s at {f_mhz:g} MHz "
                      "(one operation = one multiply or one add). Small next to the designs in that review, because the official variant has "
                      "eight lanes; the point of SENTINEL is how fast those lanes can run without wrong results, which only the board can show."]
    lines += ["", "Reading: a faster clk_fast only shortens the compute column. The measured SPI speed (board phase) decides how much of an "
                  "overclocking gain is visible end to end, so results must report compute time and end-to-end time separately."]
    return lines


def main() -> int:
    parts = [
        "# RESULTS_SIM", "",
        "Generated by `python tools/gen_results_doc.py`. Do not edit by hand.", "",
        "No number in this file was measured on hardware. Labels: [SIM] simulation or Python model, [VIVADO-STA] static Vivado estimate.", "",
    ]
    for section in (accuracy_section, arch_section, campaign_section, rtl_section, fit_section, vivado_section, official_section, latency_section):
        parts += section() + [""]
    OUT.write_text("\n".join(parts), encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
