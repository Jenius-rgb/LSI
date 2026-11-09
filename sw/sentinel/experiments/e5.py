"""E5: fault-injection coverage. Summarises the Python campaign of results/sim/ ([SIM])."""
from __future__ import annotations

import json

from sentinel.harness import ROOT, write_csv, write_metadata, new_run_dir


class _Meta:
    name = "mock"

    def metadata(self) -> dict:
        return {"backend": "python-model", "label": "[SIM]"}


def main() -> None:
    path = ROOT / "results" / "sim" / "campaign_s.json"
    if not path.exists():
        print("E5: run `python tools/run.py campaign` first")
        return
    report = json.loads(path.read_text(encoding="utf-8"))
    rows = report["rows"]
    out = new_run_dir("sim", "e5")
    write_csv(out / "data.csv", rows)
    write_metadata(out, "e5", _Meta(), {"source": str(path.relative_to(ROOT)), "note": report["note"], "criterion": "100% of single-lane errors corrected"})
    print(f"[SIM] E5 wrote {out}")


if __name__ == "__main__":
    main()
