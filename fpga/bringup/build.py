#!/usr/bin/env python3
"""Build the bring-up bitstreams for ZERO7 without the Raspberry Pi (ADR-026).

    python tools/run.py bringup <blink|vcco_probe|io_test> --accept-inferred-io [--ila]

The I/O standards in the constraints are an inference (ADR-024). The designs drive only FPGA-only
pins (a test checks this), so a wrong bank voltage costs function, not hardware. The bitstreams go to
build/bringup/<design>/ and are not committed. This is preparation: the board phase itself starts
only as CLAUDE.md section 8 says.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

DESIGNS = {
    "blink": {"top": "blink_top", "rtl": ["fpga/bringup/blink/blink_top.v"], "xdc": "fpga/bringup/blink/blink_top.xdc",
              "outputs": ["led1", "led2"]},
    "vcco_probe": {"top": "vcco_probe_top", "rtl": ["fpga/bringup/blink/blink_top.v", "fpga/bringup/vcco_probe/vcco_probe_top.v"],
                   "xdc": "fpga/bringup/vcco_probe/vcco_probe_top.xdc", "outputs": ["led1", "led2", "pmod1_hi", "pmod1_lo", "ws2812_dout"]},
    "io_test": {"top": "io_test_top", "rtl": ["rtl/ws2812_tx.v", "fpga/bringup/io_test/io_test_top.v"],
                "xdc": "fpga/bringup/io_test/io_test_top.xdc", "outputs": ["led1", "led2", "ws2812_dout"]},
    # The full SENTINEL core with the PC as host over JTAG (ADR-025); its own Tcl generates the IP cores.
    "jtag_host": {"top": "top_jtag", "tcl": "fpga/bringup/jtag_host/build.tcl", "xdc": "fpga/bringup/jtag_host/top_jtag.xdc",
                  "outputs": ["led_busy", "led_fatal", "ws2812_dout"]},
}


def bitstream_name(design: str) -> str:
    return f"{DESIGNS[design]['top']}_BRINGUP.bit"


def vivado_command(vivado: str, design: str, outdir: Path, ila: bool = False) -> list[str]:
    d = DESIGNS[design]
    log = ["-log", str(outdir / "vivado.log")]
    if "tcl" in d:
        return [vivado, "-mode", "batch", "-nojournal", *log, "-source", str(ROOT / d["tcl"]), "-tclargs", str(outdir), bitstream_name(design), "8"]
    rtl = "+".join(str(ROOT / f) for f in d["rtl"])   # "+": cmd.exe splits commas in the vivado.bat arguments
    return [vivado, "-mode", "batch", "-nojournal", "-log", str(outdir / "vivado.log"), "-source", str(ROOT / "fpga" / "bringup" / "build.tcl"),
            "-tclargs", d["top"], rtl, str(ROOT / d["xdc"]), str(outdir), bitstream_name(design), "1" if ila else "0"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("design", choices=sorted(DESIGNS))
    parser.add_argument("--accept-inferred-io", action="store_true", help="confirm that LVCMOS33 is an inference (ADR-024, ADR-026)")
    parser.add_argument("--ila", action="store_true", help="add an ILA to io_test (debug probes file next to the bitstream)")
    args = parser.parse_args(argv)
    if not args.accept_inferred_io:
        print("Refusing: the I/O standards are an inference (ADR-024). Re-run with --accept-inferred-io to build a bring-up "
              "bitstream that drives only FPGA-only pins (ADR-026).")
        return 2
    from check_env import find_vivado

    vivado = find_vivado()
    if vivado is None:
        print("Vivado not found. Install Vivado 2025.2 or set VIVADO_BIN.")
        return 2
    outdir = ROOT / "build" / "bringup" / args.design
    outdir.mkdir(parents=True, exist_ok=True)
    res = subprocess.run(vivado_command(vivado, args.design, outdir, args.ila), cwd=ROOT, capture_output=True, text=True, errors="replace")
    bit = outdir / bitstream_name(args.design)
    if res.returncode != 0 or not bit.exists():
        print(f"failed; see {(outdir / 'vivado.log').relative_to(ROOT)}")
        return 1
    print(f"[VIVADO] wrote {bit.relative_to(ROOT).as_posix()} (bring-up only, not committed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
