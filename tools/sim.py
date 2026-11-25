#!/usr/bin/env python3
"""Compile and run RTL testbenches with Icarus Verilog or Vivado xsim.

Usage: python tools/run.py sim <bench ...> [--list] [--sim icarus|xsim] [--jobs N]

Each bench declares its sources, parameters and a vector generator. A bench passes only if
it prints ``PASS n/n`` with n == n and no FAIL line (and, under Icarus, vvp exits with 0).
xsim runs about ten times faster than Icarus, so long regressions use it when available.

Simulator output goes to build/sim/logs/<bench>[_s<shard>].log while it runs (engine benches print one
``IMG i done`` line per image), so a long regression can be followed with ``Get-Content -Wait``. On a
timeout the whole process tree is killed (xsim.bat starts xsim.exe, which starts xsimk.exe).
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
SIM_DIR = BUILD / "sim"
XSIM_DIR = BUILD / "xsim"
LOG_DIR = SIM_DIR / "logs"
VECTOR_DIR = BUILD / "vectors"

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
    timeout_s: int = 7200
    shards: int = 1  # split +first/+count across parallel simulations
    prefer_xsim: bool = False


def wc_widths(k: int) -> tuple[int, int, int]:
    """Signed widths of the checksum weights for weights in -127..127 (SPEC 6.1)."""
    def bits(limit: int) -> int:
        return limit.bit_length() + 1
    return bits(127 * k), bits(127 * sum(range(1, k + 1))), bits(127 * sum(i * i for i in range(1, k + 1)))


def _benches() -> dict[str, Bench]:
    from benches import BENCHES

    return BENCHES


PASS_RE = re.compile(r"PASS (\d+)/(\d+)")


def _verdict(output: str) -> bool:
    match = PASS_RE.search(output)
    return match is not None and match.group(1) == match.group(2) and "FAIL" not in output


def _vector_plusargs(bench: Bench) -> list[str]:
    workdir = VECTOR_DIR / bench.name
    workdir.mkdir(parents=True, exist_ok=True)
    return bench.vectors(workdir, bench.params) if bench.vectors else []


def compile_icarus(bench: Bench) -> Path:
    SIM_DIR.mkdir(parents=True, exist_ok=True)
    out = SIM_DIR / f"{bench.name}.vvp"
    cmd = ["iverilog", "-g2012", "-o", str(out), "-s", bench.top, "-I", "rtl/gen"]
    cmd += [f"-P{bench.top}.{key}={value}" for key, value in bench.params.items()]
    cmd += bench.sources
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"iverilog failed for {bench.name}:\n{res.stdout}{res.stderr}")
    return out


def kill_tree(proc: subprocess.Popen) -> None:
    """Kill a process and everything it started. Popen.kill() alone leaves xsim.exe and xsimk.exe running on Windows."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()


def run_logged(cmd: list[str], cwd: Path, log: Path, timeout_s: float) -> tuple[int | None, str]:
    """Run cmd with stdout and stderr streamed into log. Returns (exit code, or None on timeout, and the log text)."""
    log.parent.mkdir(parents=True, exist_ok=True)
    extra = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    code: int | None = None
    with open(log, "w", encoding="utf-8", errors="replace") as fh:
        proc = subprocess.Popen(cmd, cwd=cwd, stdout=fh, stderr=subprocess.STDOUT, **extra)
        deadline = time.monotonic() + timeout_s
        while code is None:
            try:
                code = proc.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                if time.monotonic() >= deadline:
                    kill_tree(proc)
                    break
    text = log.read_text(encoding="utf-8", errors="replace")
    if code is None:
        note = f"FAIL runner timeout after {timeout_s:.0f} s; process tree killed\n"
        with open(log, "a", encoding="utf-8") as fh:
            fh.write(note)
        text += note
    return code, text


def _log_path(bench: Bench, shard: int, shards: int) -> Path:
    return LOG_DIR / (f"{bench.name}_s{shard}.log" if shards > 1 else f"{bench.name}.log")


def _run_icarus(bench: Bench, plusargs: list[str], vvp: Path, log: Path) -> tuple[bool, str]:
    code, output = run_logged(["vvp", "-n", str(vvp), *plusargs], ROOT, log, bench.timeout_s)
    return code == 0 and _verdict(output), output


def _vivado_tool(name: str) -> str:
    from check_env import find_vivado

    vivado = find_vivado()
    if vivado is None:
        raise RuntimeError("Vivado not found")
    suffix = ".bat" if os.name == "nt" else ""
    return str(Path(vivado).parent / f"{name}{suffix}")


def build_xsim(bench: Bench, workdir: Path) -> None:
    """Analyse and elaborate. Options go through files: `=` in arguments breaks .bat wrappers."""
    workdir.mkdir(parents=True, exist_ok=True)
    rtl = [str(ROOT / s) for s in bench.sources if not s.startswith("tb/")]
    tbs = [str(ROOT / s) for s in bench.sources if s.startswith("tb/")]
    include = str(ROOT / "rtl" / "gen")

    def run(tool: str, args: list[str]) -> None:
        res = subprocess.run([_vivado_tool(tool), *args], cwd=workdir, capture_output=True, text=True, errors="replace")
        if res.returncode != 0:
            raise RuntimeError(f"{tool} failed for {bench.name}:\n{res.stdout[-3000:]}{res.stderr[-1000:]}")

    run("xvlog", ["-nolog", "-i", include, *rtl])
    run("xvlog", ["-nolog", "--sv", "-i", include, *tbs])
    generics = " ".join(f"-generic_top {k}={v}" for k, v in bench.params.items())
    (workdir / "ela.txt").write_text(f"--relax --timescale 1ns/1ps -debug off {generics} -s snap {bench.top}\n", encoding="ascii")
    run("xelab", ["-nolog", "-f", "ela.txt"])


def _run_xsim(bench: Bench, plusargs: list[str], workdir: Path, log: Path) -> tuple[bool, str]:
    tests = " ".join(f"-testplusarg {p[1:]}" for p in plusargs)
    (workdir / "sim.txt").write_text(f"snap -R {tests}\n", encoding="ascii")
    code, output = run_logged([_vivado_tool("xsim"), "-nolog", "-f", "sim.txt"], workdir, log, bench.timeout_s)
    return code is not None and _verdict(output), output


def _shard_plusargs(plusargs: list[str], shards: int) -> list[list[str]]:
    """Split +first/+count evenly. Without a +count plusarg the bench runs as one shard."""
    count_arg = next((p for p in plusargs if p.startswith("+count=")), None)
    if shards <= 1 or count_arg is None:
        return [plusargs]
    total = int(count_arg.split("=")[1])
    base = [p for p in plusargs if not p.startswith(("+first=", "+count="))]
    out = []
    first = 0
    for i in range(shards):
        size = total // shards + (1 if i < total % shards else 0)
        if size:
            out.append([*base, f"+first={first}", f"+count={size}"])
        first += size
    return out


def resolve_simulator(bench: Bench, requested: str) -> str:
    if requested != "auto":
        return requested
    if bench.prefer_xsim:
        try:
            _vivado_tool("xsim")
            return "xsim"
        except RuntimeError:
            pass
    return "icarus"


def run_bench(bench: Bench, simulator: str = "auto") -> tuple[bool, str]:
    """Generate vectors, compile, simulate every shard. Returns (passed, combined output)."""
    plusargs = _vector_plusargs(bench)
    shards = _shard_plusargs(plusargs, bench.shards)
    sim = resolve_simulator(bench, simulator)

    if sim == "icarus":
        vvp = compile_icarus(bench)
        run = lambda s: _run_icarus(bench, s[1], vvp, _log_path(bench, s[0], len(shards)))  # noqa: E731
    else:
        for i in range(len(shards)):
            build_xsim(bench, XSIM_DIR / bench.name / f"s{i}")
        run = lambda s: _run_xsim(bench, s[1], XSIM_DIR / bench.name / f"s{s[0]}",  # noqa: E731
                                  _log_path(bench, s[0], len(shards)))

    with ThreadPoolExecutor(max_workers=max(1, len(shards))) as pool:
        results = list(pool.map(run, enumerate(shards)))
    passed = all(r[0] for r in results)
    output = "\n".join(r[1] for r in results)
    return passed, output


def summarize(output: str) -> str:
    lines = [l for l in output.splitlines() if l.startswith(("PASS", "FAIL"))]
    if not lines:
        return output.strip()[-300:]
    fails = [l for l in lines if l.startswith("FAIL")]
    if fails:
        return fails[0]
    total = sum(int(PASS_RE.search(l).group(1)) for l in lines)
    return f"PASS {total}/{total} ({lines[0][5:]})" if len(lines) > 1 else lines[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("benches", nargs="*", help="bench names or prefixes (default: all fast benches)")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--jobs", type=int, default=6)
    parser.add_argument("--sim", default="auto", choices=["auto", "icarus", "xsim"])
    parser.add_argument("--record", default=None, help="append one JSON line per bench to this file")
    args = parser.parse_args()

    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "tools"))
    benches = _benches()
    if args.list:
        for name, bench in benches.items():
            print(f"{name}{'  (slow)' if bench.slow else ''}")
        return 0

    # An exact bench name selects only that bench; anything else is a prefix.
    def selected(name: str) -> bool:
        return any(name == p or (p not in benches and name.startswith(p)) for p in args.benches)

    chosen = [b for n, b in benches.items() if (not args.benches and not b.slow) or (args.benches and selected(n))]
    if not chosen:
        print("no matching bench", file=sys.stderr)
        return 2
    if args.sim != "xsim" and shutil.which("iverilog") is None:
        print("iverilog not found", file=sys.stderr)
        return 2

    def job(bench: Bench) -> tuple[Bench, bool, str]:
        passed, output = run_bench(bench, args.sim)
        return bench, passed, output

    print(f"logs (written while running): {LOG_DIR.relative_to(ROOT).as_posix()}/<bench>[_s<shard>].log", flush=True)
    failures = 0
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for bench, passed, output in pool.map(job, chosen):
            if args.record:
                # Written here, in the main thread only: appends from the worker threads lost a line on Windows.
                import datetime as dt
                import json

                entry = {
                    "date": dt.date.today().isoformat(), "bench": bench.name, "passed": passed,
                    "simulator": resolve_simulator(bench, args.sim), "summary": summarize(output), "params": bench.params,
                }
                with open(ROOT / args.record, "a", encoding="utf-8", newline="\n") as fh:
                    fh.write(json.dumps(entry) + "\n")
            print(f"[{'ok' if passed else 'FAIL'}] {bench.name}: {summarize(output)}", flush=True)
            failures += not passed
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
