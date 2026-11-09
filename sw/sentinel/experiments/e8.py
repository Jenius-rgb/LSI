"""E8: cost versus net gain, from Vivado reports ([VIVADO-STA]). Requires the OOC runs."""
from __future__ import annotations

import csv
import json

from sentinel.harness import ROOT, new_run_dir, write_csv, write_metadata


class _Meta:
    name = "mock"

    def metadata(self) -> dict:
        return {"backend": "vivado-reports", "label": "[VIVADO-STA]"}


def main() -> None:
    source = ROOT / "fpga" / "reports" / "summary.csv"
    if not source.exists():
        # No implementation data yet: keep the parameter-based estimate, clearly labelled.
        fit = ROOT / "results" / "sim" / "fit_report.json"
        if not fit.exists():
            print("E8: run `python tools/fit_report.py` first")
            return
        report = json.loads(fit.read_text(encoding="utf-8"))
        rows = [{"label": "[SIM] parameter estimate, NOT [VIVADO-STA]", **r} for r in report["fit"]]
        out = new_run_dir("sim", "e8")
        write_csv(out / "data.csv", rows)
        write_metadata(out, "e8", _Meta(), {"source": str(fit.relative_to(ROOT)), "label": "[SIM]", "note": "no Vivado reports: Spartan-7 device support missing"})
        print(f"[SIM] E8 estimate wrote {out}; `python tools/run.py ooc` gives [VIVADO-STA] data once Vivado has Spartan-7")
        return
    with open(source, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    out = new_run_dir("sim", "e8")
    write_csv(out / "data.csv", rows)
    write_metadata(out, "e8", _Meta(), {"source": str(source.relative_to(ROOT))})
    print(f"[VIVADO-STA] E8 wrote {out}")


if __name__ == "__main__":
    main()
