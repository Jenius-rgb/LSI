"""Shared plumbing for the experiments: output folders, CSV, metadata, backend construction."""
from __future__ import annotations

import csv
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from model.config import load_model_config  # noqa: E402
from model.fault_model import FaultParams  # noqa: E402
from model.vectors import load_or_random_qmodel  # noqa: E402
from sentinel.backend import MockBackend  # noqa: E402


def new_run_dir(backend: str, experiment: str) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = ROOT / "results" / backend / experiment / stamp
    path.mkdir(parents=True, exist_ok=True)
    return path


def latest_run(backend: str, experiment: str) -> Path | None:
    base = ROOT / "results" / backend / experiment
    if not base.exists():
        return None
    runs = sorted(p for p in base.iterdir() if p.is_dir() and (p / "data.csv").exists())
    return runs[-1] if runs else None


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def git_hash() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
        return out.stdout.strip() or "unknown"
    except OSError:
        return "unknown"


def write_metadata(path: Path, experiment: str, backend, extra: dict | None = None) -> None:
    meta = {
        "experiment": experiment,
        "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
        "git_hash": git_hash(),
        "bitstream_id": "none (pre-board)",
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        **backend.metadata(),
    }
    if extra:
        meta.update(extra)
    (path / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8", newline="\n")


def make_backend(model: str = "xs", seed: int = 2027, fault: FaultParams | None = None, k: int = 8) -> tuple[MockBackend, str]:
    qm, source = load_or_random_qmodel(model, seed)
    sparsity = [0.05, 0.4, 0.55, 0.6]
    return MockBackend(qm, load_model_config(model), k=k, fault=fault or FaultParams(seed=seed), sparsity=sparsity), source


def test_images(count: int, model: str = "xs") -> tuple[np.ndarray, str]:
    from model.data import verification_images

    images, _, source = verification_images(count)
    return images, source


__test__ = False
