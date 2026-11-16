"""The simulation runner keeps exactly one record per bench, whatever the number of worker threads."""
import json
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import sim  # noqa: E402


def test_records_are_written_by_one_thread_only(monkeypatch, tmp_path):
    """Appending from the worker threads lost a line on Windows (2026-11-16: system_xs_r200 passed but left no record)."""
    names = [f"fake_{i:02d}" for i in range(60)]
    monkeypatch.setattr(sim, "_benches", lambda: {n: sim.Bench(n, "tb_fake", []) for n in names})
    monkeypatch.setattr(sim, "run_bench", lambda bench, simulator="auto": (True, "PASS 1/1"))
    monkeypatch.setattr(sim.shutil, "which", lambda name: "iverilog")
    writers = set()
    real_open = open

    def spy_open(path, mode="r", *args, **kwargs):
        if "a" in mode:
            writers.add(threading.current_thread().name)
        return real_open(path, mode, *args, **kwargs)

    monkeypatch.setattr("builtins.open", spy_open)
    record = tmp_path / "records.jsonl"
    monkeypatch.setattr(sys, "argv", ["sim.py", "fake_", "--jobs", "8", "--record", str(record)])
    assert sim.main() == 0
    monkeypatch.undo()
    entries = [json.loads(line) for line in record.read_text(encoding="utf-8").splitlines()]
    assert sorted(e["bench"] for e in entries) == names
    assert writers == {threading.main_thread().name}
