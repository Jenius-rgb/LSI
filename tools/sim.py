#!/usr/bin/env python3
"""Compile and run RTL testbenches with Icarus Verilog.

Usage: python tools/run.py sim <bench> [--list]
Each bench declares its sources, parameters and a vector generator (model/vectors.py).
A bench passes only if vvp exits with status 0 and prints ``PASS n/n``.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
SIM_DIR = BUILD / "sim"

RTL = "rtl"
LANES = [f"{RTL}/lane_lut.v", f"{RTL}/lane_dsp_min.v", f"{RTL}/lane_dsp_full.v", f"{RTL}/lane_array.v"]


@dataclass
class Bench:
    name: str
    top: str
    sources: list[str]
    params: dict = field(default_factory=dict)
    vectors: Callable[[Path, dict], list[str]] | None = None
    slow: bool = False
    timeout_s: int = 3600
    include_dirs: list[str] = field(default_factory=list)


def wc_widths(k: int) -> tuple[int, int, int]:
    """Signed widths of the checksum weights for weights in -127..127 (SPEC 6.1)."""
    def bits(limit: int) -> int:
        return limit.bit_length() + 1
    return bits(127 * k), bits(127 * sum(range(1, k + 1))), bits(127 * sum(i * i for i in range(1, k + 1)))


def _benches() -> dict[str, Bench]:
    from benches import BENCHES

    return BENCHES


def compile_bench(bench: Bench) -> Path:
    SIM_DIR.mkdir(parents=True, exist_ok=True)
    out = SIM_DIR / f"{bench.name}.vvp"
    cmd = ["iverilog", "-g2012", "-o", str(out), "-s", bench.top]
    for inc in ["rtl/gen", *bench.include_dirs]:
        cmd += ["-I", inc]
    for key, value in bench.params.items():
        cmd.append(f"-P{bench.top}.{key}={value}")
    cmd += bench.sources
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"iverilog failed for {bench.name}:\n{res.stdout}{res.stderr}")
    return out


PASS_RE = re.compile(r"^PASS (\d+)/(\d+)", re.M)


def run_bench(bench: Bench, extra_plusargs: list[str] | None = None) -> tuple[bool, str]:
    """Generate vectors, compile, simulate. Returns (passed, output)."""
    workdir = SIM_DIR / bench.name
    workdir.mkdir(parents=True, exist_ok=True)
    plusargs = bench.vectors(workdir, bench.params) if bench.vectors else []
    vvp = compile_bench(bench)
    res = subprocess.run(
        ["vvp", "-n", str(vvp), *plusargs, *(extra_plusargs or [])],
        cwd=ROOT, capture_output=True, text=True, timeout=bench.timeout_s, errors="replace",
    )
    output = res.stdout + res.stderr
    match = PASS_RE.search(output)
    passed = res.returncode == 0 and match is not None and match.group(1) == match.group(2) and "FAIL" not in output
    return passed, output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("benches", nargs="*", help="bench names or prefixes (default: all fast benches)")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--jobs", type=int, default=6)
    args = parser.parse_args()

    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "tools"))
    benches = _benches()
    if args.list:
        for name, bench in benches.items():
            print(f"{name}{'  (slow)' if bench.slow else ''}")
        return 0

    chosen = [b for n, b in benches.items() if (not args.benches and not b.slow) or any(n == p or n.startswith(p) for p in args.benches)]
    if not chosen:
        print("no matching bench", file=sys.stderr)
        return 2
    if shutil.which("iverilog") is None:
        print("iverilog not found", file=sys.stderr)
        return 2

    def job(bench: Bench) -> tuple[str, bool, str]:
        passed, output = run_bench(bench)
        return bench.name, passed, output

    failures = 0
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for name, passed, output in pool.map(job, chosen):
            summary = next((l for l in output.splitlines() if l.startswith(("PASS", "FAIL"))), output.strip()[-300:])
            print(f"[{'ok' if passed else 'FAIL'}] {name}: {summary}", flush=True)
            failures += not passed
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
