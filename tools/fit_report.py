#!/usr/bin/env python3
"""Estimate BRAM and DSP needs from the configuration before running Vivado (SPEC 14).

Device capacities are in config/parts.yaml, marked verified: false until confirmed with
`get_parts` properties or DS180. Estimates here are label [SIM]: they are arithmetic on the
design parameters, not implementation results.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def bram18_for(depth: int, width: int) -> int:
    """BRAM18 count for a true dual-port memory (per port: 16K x 1 ... 1K x 18, in TDP mode)."""
    if depth <= 0:
        return 0
    if width <= 1:
        rows, per = math.ceil(depth / 16384), 1
    elif width <= 2:
        rows, per = math.ceil(depth / 8192), 2
    elif width <= 4:
        rows, per = math.ceil(depth / 4096), 4
    elif width <= 9:
        rows, per = math.ceil(depth / 2048), 9
    else:
        rows, per = math.ceil(depth / 1024), 18
    return rows * math.ceil(width / per)


def estimate(model: str, k: int, r: int, c3: int) -> dict:
    from model.config import layer_shapes, load_model_config

    shapes = layer_shapes(load_model_config(model))
    weight_words = sum(s.groups(k) * s.t for s in shapes)
    act = {"ACT0": 0, "ACT1": 0}
    alternate = "ACT0"
    for s in shapes:
        if s.kind == "conv":
            act[alternate] += s.out_channels * s.out_height * s.out_width
            alternate = "ACT1" if alternate == "ACT0" else "ACT0"
    mem = {
        "weights": (weight_words, k * 8),
        "img0": (3072, 8),
        "img1": (3072, 8),
        "act0": (act["ACT0"], 8),
        "act1": (act["ACT1"], 8),
        "params": (512, 32),
    }
    brams = {name: bram18_for(d, w) for name, (d, w) in mem.items()}
    bram18_total = sum(brams.values())
    ncs = 2 + c3
    return {
        "label": "[SIM] estimate from parameters, not an implementation result",
        "model": model, "K": k, "R": r, "C3_EN": c3,
        "memories": {n: {"depth": d, "width": w, "bram18": brams[n]} for n, (d, w) in mem.items()},
        "bram18_total": bram18_total,
        "bram36_equivalent": bram18_total / 2.0,
        "dsp_lanes_dsp_impl": k + ncs,
        "dsp_lanes_note": "only for lane implementations mapped to DSP slices; the lut variant uses none",
        "dsp_postproc": "1 to 2 (v*M multiplier in clk_safe)",
    }


def fit_table(rows: list[dict]) -> list[dict]:
    parts = yaml.safe_load((ROOT / "config" / "parts.yaml").read_text(encoding="utf-8"))["parts"]
    out = []
    for row in rows:
        for name, cap in parts.items():
            out.append(
                {
                    "model": row["model"], "K": row["K"], "part": name,
                    "bram36_needed": row["bram36_equivalent"], "bram36_available": cap["bram36"]["value"],
                    "fits_bram": row["bram36_equivalent"] <= cap["bram36"]["value"],
                    "capacity_verified": cap["bram36"]["verified"],
                }
            )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r", type=int, default=2)
    parser.add_argument("--out", default="results/sim/fit_report.json")
    args = parser.parse_args()
    rows = [estimate(model, k, args.r, c3) for model in ("s", "xs") for k in (8, 16) for c3 in (0, 1)]
    table = fit_table(rows)
    report = {"estimates": rows, "fit": table}
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    for row in rows:
        print(f"[SIM] {row['model']:>2} K={row['K']:<2} C3={row['C3_EN']} BRAM36-eq={row['bram36_equivalent']:.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
