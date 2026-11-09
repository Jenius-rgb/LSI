"""All RTL testbenches and the Verilator lint, driven from pytest.

Benches run in parallel once per session; each is reported as its own test.
Slow benches are only run when RUN_SLOW_BENCHES=1 or through `run.py sim`.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

import benches as bench_registry
import check_env
from sim import run_bench

ROOT = Path(__file__).resolve().parents[1]
RUN_SLOW = os.environ.get("RUN_SLOW_BENCHES") == "1"
SELECTED = [n for n, b in bench_registry.BENCHES.items() if RUN_SLOW or not b.slow]


@pytest.fixture(scope="session")
def bench_results():
    if shutil.which("iverilog") is None:
        pytest.skip("iverilog not available")
    with ThreadPoolExecutor(max_workers=max(1, (os.cpu_count() or 2) // 2)) as pool:
        return dict(zip(SELECTED, pool.map(lambda n: run_bench(bench_registry.BENCHES[n]), SELECTED)))


@pytest.mark.parametrize("name", SELECTED)
def test_bench(name, bench_results):
    passed, output = bench_results[name]
    assert passed, output[-2000:]


LINT_TARGETS = bench_registry.LINT_TARGETS


@pytest.mark.parametrize("target", LINT_TARGETS, ids=[t["id"] for t in LINT_TARGETS])
def test_verilator_lint_is_clean(target):
    verilator = check_env.find_verilator()
    if verilator is None or not check_env._run([verilator, "--version"]):
        pytest.skip("verilator not available")
    cmd = [verilator, "--lint-only", "-Wall", "-Irtl/gen", "--top-module", target["top"]]
    cmd += [f"-G{k}={v}" for k, v in target.get("params", {}).items()]
    cmd += target["sources"]
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, errors="replace", env=check_env.verilator_env())
    assert res.returncode == 0 and "%Warning" not in res.stderr + res.stdout, res.stderr[-3000:]
