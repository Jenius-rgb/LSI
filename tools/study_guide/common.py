"""Shared paths and helpers for the SENTINEL study-guide generator (tools/study_guide/)."""
from __future__ import annotations

import csv
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build" / "study_guide"
FIG = OUT / "fig"
FACTS = OUT / "facts.json"


def nf(x: float, dec: int = 0) -> str:
    """Indonesian number format: dot for thousands, comma for decimals."""
    s = f"{x:,.{dec}f}"
    return s.replace(",", "\0").replace(".", ",").replace("\0", ".")


def pct(fraction: float, dec: int = 2) -> str:
    return nf(fraction * 100, dec) + "%"


def load_json(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def vivado_rows() -> list[dict]:
    with open(ROOT / "fpga" / "reports" / "summary.csv", newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def regression_latest() -> dict[str, dict]:
    latest: dict[str, dict] = {}
    for line in (ROOT / "results" / "sim" / "rtl_regression.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            entry = json.loads(line)
            latest[entry["bench"]] = entry
    return latest


def latest_run(backend: str, exp: str) -> Path | None:
    base = ROOT / "results" / backend / exp
    runs = sorted(p for p in base.iterdir() if p.is_dir()) if base.exists() else []
    return runs[-1] if runs else None


def git_head() -> str:
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def part_short(part: str) -> str:
    """xc7s25csga225-1 -> 'XC7S25 −1'."""
    m = re.match(r"(xc7s\d+)[a-z]+\d+-(\d)", part)
    return f"{m.group(1).upper()} −{m.group(2)}" if m else part
