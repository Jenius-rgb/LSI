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


CHILD = r'''
import subprocess, sys
beat = sys.argv[1]
code = "import sys, time\nwhile True:\n    open(sys.argv[1], 'w').write(repr(time.time()))\n    time.sleep(0.1)\n"
grand = subprocess.Popen([sys.executable, "-c", code, beat])
print("started", flush=True)
grand.wait()
'''


def test_timeout_kills_the_whole_process_tree(tmp_path):
    """26 Nov 2026: the 7200 s timeout killed only xsim.bat; xsim.exe and xsimk.exe ran on for hours and the runner
    waited on their pipes. A grandchild that keeps writing a heartbeat file must stop when the timeout fires."""
    import time

    beat = tmp_path / "beat.txt"
    script = tmp_path / "child.py"
    script.write_text(CHILD, encoding="utf-8")
    start = time.monotonic()
    code, text = sim.run_logged([sys.executable, str(script), str(beat)], tmp_path, tmp_path / "run.log", timeout_s=3)
    assert code is None
    assert time.monotonic() - start < 40
    assert "started" in text and "FAIL runner timeout" in text
    time.sleep(0.5)
    first = beat.read_text(encoding="utf-8")
    time.sleep(1.0)
    assert beat.read_text(encoding="utf-8") == first, "the grandchild is still running"


def test_output_reaches_the_log_while_the_simulator_runs(tmp_path):
    """Progress lines must be readable before the simulator exits (Get-Content -Wait on the log)."""
    import time

    log = tmp_path / "run.log"
    code = "import time\nprint('IMG 0 done cycles=1', flush=True)\ntime.sleep(4)\nprint('PASS 1/1')\n"
    result = {}
    worker = threading.Thread(target=lambda: result.update(out=sim.run_logged([sys.executable, "-c", code], tmp_path, log, 60)))
    worker.start()
    deadline = time.monotonic() + 3.5
    seen = False
    while time.monotonic() < deadline and not seen:
        time.sleep(0.2)
        seen = log.exists() and "IMG 0 done" in log.read_text(encoding="utf-8", errors="replace")
    worker.join()
    assert seen, "the progress line was not in the log while the process ran"
    assert result["out"][0] == 0 and "PASS 1/1" in result["out"][1]


def test_an_exact_bench_name_selects_only_that_bench(monkeypatch):
    """`sim engine_s_k8_c1_zs` also started the 200-image engine_s_k8_c1_zs_n200 (prefix match)."""
    names = ["engine_x", "engine_x_n200", "engine_y"]
    monkeypatch.setattr(sim, "_benches", lambda: {n: sim.Bench(n, "tb_fake", [], slow=n.endswith("n200")) for n in names})
    ran = []
    monkeypatch.setattr(sim, "run_bench", lambda bench, simulator="auto": (ran.append(bench.name), (True, "PASS 1/1"))[1])
    monkeypatch.setattr(sim.shutil, "which", lambda name: "iverilog")
    monkeypatch.setattr(sys, "argv", ["sim.py", "engine_x"])
    assert sim.main() == 0
    assert ran == ["engine_x"]
    ran.clear()
    monkeypatch.setattr(sys, "argv", ["sim.py", "engine_"])
    assert sim.main() == 0
    assert sorted(ran) == names
