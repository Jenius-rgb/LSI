#!/usr/bin/env python3
"""Generate the MMCM2 turbo frequency table (SPEC 7.6).

F_IN is the 20 MHz board clock CLK20M (board/BOARD_INFO.md, ADR-015); other values can still be
passed for exploration and are then flagged as placeholders. MMCM limits live in
config/mmcm_limits.yaml. Values there are marked ``verified: false`` until someone
checks them against DS189 and records the page number; the generated table carries that flag.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
BOARD_F_IN_MHZ = 20.0  # CLK20M on pin B13 [OFFICIAL: board/BOARD_INFO.md]
LIMITS_PATH = ROOT / "config" / "mmcm_limits.yaml"


def load_limits(speed_grade: str, path: Path = LIMITS_PATH) -> dict:
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    limits = data["speed_grades"][speed_grade]
    return {"f_vco_min": limits["f_vco_min"]["value"], "f_vco_max": limits["f_vco_max"]["value"],
            "f_pfd_min": limits["f_pfd_min"]["value"], "f_pfd_max": limits["f_pfd_max"]["value"],
            "f_in_min": limits["f_in_min"]["value"], "f_in_max": limits["f_in_max"]["value"],
            "f_out_max": limits["f_out_max"]["value"],
            "verified": all(limits[k].get("verified", False) for k in limits),
            "source": data["source"]}


def search(f_in: float, target: float, limits: dict) -> dict | None:
    """Best (M, D, O) with M, O in eighths and D integer, inside the limits. None if impossible."""
    if not limits["f_in_min"] <= f_in <= limits["f_in_max"]:
        return None
    best = None
    for d in range(1, 107):
        pfd = f_in / d
        if not limits["f_pfd_min"] <= pfd <= limits["f_pfd_max"]:
            continue
        for m8 in range(16, 513):  # 2.000 .. 64.000
            m = m8 / 8
            vco = f_in * m / d
            if not limits["f_vco_min"] <= vco <= limits["f_vco_max"]:
                continue
            o8 = max(8, min(1024, round(vco / target * 8)))
            o = o8 / 8
            f_out = vco / o
            if f_out > limits["f_out_max"]:
                continue
            err = abs(f_out - target)
            if best is None or err < best["error_mhz"] - 1e-9:
                best = {"m": m, "d": d, "o": o, "f_vco": vco, "f_pfd": pfd, "f_out": f_out, "error_mhz": err}
    return best


def build_table(f_in: float, f_base: float, step: float, levels: int, speed_grade: str, limits: dict | None = None) -> dict:
    limits = limits or load_limits(speed_grade)
    table = []
    for level in range(levels):
        target = f_base + level * step
        cfg = search(f_in, target, limits)
        table.append({"level": level, "target_mhz": target, **(cfg or {"m": None})})
    return {
        "f_in_mhz": f_in,
        "f_in_is_placeholder": f_in != BOARD_F_IN_MHZ,
        "f_in_source": "board/BOARD_INFO.md: CLK20M, 20 MHz [OFFICIAL]" if f_in == BOARD_F_IN_MHZ else "caller-supplied value, not the board clock",
        "speed_grade": speed_grade,
        "limits": limits,
        "limits_verified_against_ds189": limits["verified"],
        "levels": table,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--f-in", type=float, default=BOARD_F_IN_MHZ, help="board clock in MHz; 20 MHz on ZERO7")
    parser.add_argument("--f-base", type=float, default=125.0, help="turbo level 0 in MHz; equals f_safe (ADR-015)")
    parser.add_argument("--step", type=float, default=10.0, help="turbo level spacing in MHz (ADR-015)")
    parser.add_argument("--levels", type=int, default=16)
    parser.add_argument("--speed-grade", default="-1", choices=["-1", "-2"])
    parser.add_argument("--out", default="build/mmcm_table.json")
    args = parser.parse_args()
    table = build_table(args.f_in, args.f_base, args.step, args.levels, args.speed_grade)
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(table, indent=2) + "\n", encoding="utf-8", newline="\n")
    ok = sum(1 for lv in table["levels"] if lv.get("m") is not None)
    print(f"wrote {out.relative_to(ROOT)}: {ok}/{len(table['levels'])} levels feasible; limits verified: {table['limits_verified_against_ds189']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
