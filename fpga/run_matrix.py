#!/usr/bin/env python3
"""Run the Vivado out-of-context matrix (SPEC 14), or say exactly what is missing.

Parts are taken from `get_parts xc7s*`, never guessed. Results go to fpga/reports/ with the
label [VIVADO-STA]. Refuses to start if Vivado has no Spartan-7 device support.
"""
from __future__ import annotations

import argparse
import itertools
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_env import find_vivado  # noqa: E402

REPORTS = ROOT / "fpga" / "reports"
LIST_TCL = """
foreach base {xc7s6 xc7s15 xc7s25 xc7s50} {
    puts "PARTS $base [get_parts -quiet ${base}*]"
}
"""
INSTRUCTIONS = """Vivado found, but it has no Spartan-7 device support: get_parts xc7s* returned nothing.

Do this once, then run `python tools/run.py ooc` again:
1. Open Vivado 2025.2.
2. Help > Add Design Tools or Devices (sign in with your AMD account).
3. Tick 7 Series > Spartan-7, click Next, and let it install.
"""
# Target periods in ns. They only steer the implementation; Fmax is derived from the slack.
T_SAFE_NS = 10.0
T_FAST_NS = 5.0
AW = {"s": (12, 13, 11), "xs": (11, 12, 10)}


def available_parts(vivado: str) -> dict[str, list[str]]:
    tcl = ROOT / "build" / "list_parts.tcl"
    tcl.parent.mkdir(parents=True, exist_ok=True)
    tcl.write_text(LIST_TCL, encoding="ascii")
    res = subprocess.run([vivado, "-mode", "batch", "-nojournal", "-nolog", "-notrace", "-source", str(tcl)],
                         cwd=tcl.parent, capture_output=True, text=True, errors="replace")
    parts = {}
    for line in res.stdout.splitlines():
        if line.startswith("PARTS "):
            fields = line.split()
            parts[fields[1]] = fields[2:]
    return parts


def choose_parts(available: dict[str, list[str]]) -> list[tuple[str, str]]:
    """One part per device family member and speed grade, with the model that fits it."""
    chosen = []
    model_for = {"xc7s6": "xs", "xc7s15": "s", "xc7s25": "s", "xc7s50": "s"}
    for base, names in available.items():
        for speed in ("-1", "-2"):
            picks = [n for n in names if n.endswith(speed) and "ftgb196" in n] or [n for n in names if n.endswith(speed)]
            if picks:
                chosen.append((sorted(picks)[0], model_for[base]))
    return chosen


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list-parts", action="store_true")
    parser.add_argument("--k", type=int, nargs="+", default=[8, 16])
    parser.add_argument("--impl", type=int, nargs="+", default=[0, 1, 2], help="0 lut, 1 dsp_min, 2 dsp_full")
    parser.add_argument("--c3", type=int, nargs="+", default=[0, 1])
    parser.add_argument("--parts", nargs="*", help="restrict to these part names")
    args = parser.parse_args()

    vivado = find_vivado()
    if vivado is None:
        print("Vivado not found. Install it or set VIVADO_BIN, then run this again.")
        return 2
    available = available_parts(vivado)
    if not any(available.values()):
        print(INSTRUCTIONS)
        return 2
    parts = choose_parts(available)
    if args.parts:
        parts = [p for p in parts if p[0] in args.parts]
    if args.list_parts:
        for part, model in parts:
            print(f"{part}  model {model}")
        return 0

    tcl = ROOT / "fpga" / "ooc.tcl"
    failures = 0
    for (part, model), k, impl, c3 in itertools.product(parts, args.k, args.impl, args.c3):
        weight_aw, act0_aw, act1_aw = AW[model]
        name = f"{part}_{model}_k{k}_impl{impl}_c{c3}"
        out = REPORTS / name
        print(f"[VIVADO-STA] {name}", flush=True)
        res = subprocess.run(
            [vivado, "-mode", "batch", "-nojournal", "-log", str(out.with_suffix(".log")), "-source", str(tcl), "-tclargs",
             part, str(k), str(impl), str(c3), str(weight_aw), str(act0_aw), str(act1_aw), str(T_SAFE_NS), str(T_FAST_NS), str(out)],
            cwd=ROOT, capture_output=True, text=True, errors="replace",
        )
        if res.returncode != 0 or not (out / "summary.txt").exists():
            print(f"  failed; see {out.with_suffix('.log')}")
            failures += 1
    subprocess.call([sys.executable, str(ROOT / "fpga" / "parse_reports.py")], cwd=ROOT)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
