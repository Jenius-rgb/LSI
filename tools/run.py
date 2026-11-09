#!/usr/bin/env python3
"""Single entry point for every project command (see CLAUDE.md section 9).

Uses the project's .venv automatically when it exists, so plain
``python tools/run.py <command>`` works without activating anything.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".venv"
VENV_PYTHON = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _reexec_in_venv() -> None:
    if VENV_PYTHON.exists() and Path(sys.prefix).resolve() != VENV.resolve():
        raise SystemExit(subprocess.call([str(VENV_PYTHON), *sys.argv]))


def _env() -> dict[str, str]:
    env = os.environ.copy()
    extra = [str(ROOT), str(ROOT / "sw")]
    env["PYTHONPATH"] = os.pathsep.join(extra + [env.get("PYTHONPATH", "")]).rstrip(os.pathsep)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


def call(*args: str) -> int:
    """Run a Python module or script from the repo root with the project paths set."""
    return subprocess.call([sys.executable, *args], cwd=ROOT, env=_env())


def cmd_check(rest: list[str]) -> int:
    return call("tools/check_env.py", *rest)


def cmd_test(rest: list[str]) -> int:
    return call("-m", "pytest", "tests", "-q", *rest)


def cmd_gen(rest: list[str]) -> int:
    return call("tools/gen_all.py", *rest)


def cmd_train(rest: list[str]) -> int:
    return call("-m", "model.train", *rest)


def cmd_export(rest: list[str]) -> int:
    return call("-m", "model.export", *rest)


def cmd_sim(rest: list[str]) -> int:
    return call("tools/sim.py", *rest)


def cmd_campaign(rest: list[str]) -> int:
    return call("-m", "model.campaign", *rest)


def cmd_ooc(rest: list[str]) -> int:
    return call("fpga/run_matrix.py", *rest)


def cmd_plots(rest: list[str]) -> int:
    return call("-m", "sentinel.plots.all", *rest)


COMMANDS = {
    "check": (cmd_check, "detect tools and versions"),
    "test": (cmd_test, "pytest plus all RTL testbenches"),
    "gen": (cmd_gen, "generate regmap, vectors and weights"),
    "train": (cmd_train, "train the float model"),
    "export": (cmd_export, "quantise and export a trained model"),
    "sim": (cmd_sim, "run one RTL testbench"),
    "campaign": (cmd_campaign, "run the fault-injection campaigns"),
    "ooc": (cmd_ooc, "Vivado out-of-context runs (when Vivado has the parts)"),
    "plots": (cmd_plots, "regenerate all plots"),
}


def main() -> int:
    _reexec_in_venv()
    parser = argparse.ArgumentParser(description="SENTINEL project commands")
    parser.add_argument("command", choices=sorted(COMMANDS), help="; ".join(f"{k}: {v[1]}" for k, v in COMMANDS.items()))
    args, rest = parser.parse_known_args()
    return COMMANDS[args.command][0](rest)


if __name__ == "__main__":
    raise SystemExit(main())
