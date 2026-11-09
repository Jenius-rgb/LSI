"""E8: cost versus net gain, from Vivado reports ([VIVADO-STA]). Requires the OOC runs."""
from __future__ import annotations

import csv

from sentinel.harness import ROOT, new_run_dir, write_csv, write_metadata


class _Meta:
    name = "mock"

    def metadata(self) -> dict:
        return {"backend": "vivado-reports", "label": "[VIVADO-STA]"}


def main() -> None:
    source = ROOT / "fpga" / "reports" / "summary.csv"
    if not source.exists():
        print("E8: no Vivado results yet (fpga/reports/summary.csv); run `python tools/run.py ooc`")
        return
    with open(source, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    out = new_run_dir("sim", "e8")
    write_csv(out / "data.csv", rows)
    write_metadata(out, "e8", _Meta(), {"source": str(source.relative_to(ROOT))})
    print(f"[VIVADO-STA] E8 wrote {out}")


if __name__ == "__main__":
    main()
