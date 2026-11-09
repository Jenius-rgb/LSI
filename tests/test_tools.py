"""M0: the command-line entry points exist and report honestly."""
import subprocess
import sys
from pathlib import Path

import check_env

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_COMMANDS = {"check", "test", "gen", "train", "export", "sim", "campaign", "ooc", "plots"}


def test_run_py_lists_every_required_subcommand():
    out = subprocess.run(
        [sys.executable, "tools/run.py", "--help"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    missing = {c for c in REQUIRED_COMMANDS if c not in out}
    assert not missing, f"run.py lacks: {missing}"


def test_run_py_rejects_unknown_subcommand():
    res = subprocess.run([sys.executable, "tools/run.py", "nope"], cwd=ROOT, capture_output=True, text=True)
    assert res.returncode != 0


def test_detect_reports_this_interpreter():
    tools = {t.name: t for t in check_env.detect()}
    assert tools["python"].found
    assert tools["python"].version.split(".")[:2] == [str(sys.version_info[0]), str(sys.version_info[1])]
    for name in ("iverilog", "vvp", "vivado", "verilator (lint)", "torch"):
        assert name in tools


def test_missing_tool_is_reported_not_faked():
    report = check_env.report([check_env.Tool("ghost", False), check_env.Tool("opt", False, required=False)])
    assert "MISSING" in report and "absent" in report
