"""fpga/bringup/build.py: bring-up bitstreams are only built on request and only into build/ (ADR-026)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "fpga" / "bringup"))

import build as bb  # noqa: E402


def test_refuses_without_the_inferred_io_flag(capsys):
    assert bb.main(["blink"]) == 2
    assert "--accept-inferred-io" in capsys.readouterr().out


def test_designs_drive_only_fpga_only_pins():
    """No output of a bring-up design may sit on a line shared with the Raspberry Pi header (TK-1, TK-2)."""
    shared = {"B1", "B2", "A2", "A9", "A10", "C10", "D9", "A7", "A6", "A8", "D10", "B10", "B6", "C7", "C13",
              "A3", "D7", "B11", "C14", "B15", "A5", "C8", "D8", "C9", "B12"}
    for name, design in bb.DESIGNS.items():
        xdc = (ROOT / design["xdc"]).read_text(encoding="utf-8")
        outputs = set(design["outputs"])
        for line in xdc.splitlines():
            if "PACKAGE_PIN" in line and not line.lstrip().startswith("#"):
                pin, port = line.split("PACKAGE_PIN")[1].split("[get_ports")[0].strip(), line.split("get_ports")[1]
                if any(o in port for o in outputs):
                    assert pin not in shared, (name, line)


def test_output_goes_to_build_and_names_the_purpose(tmp_path):
    cmd = bb.vivado_command("vivado", "io_test", tmp_path)
    assert str(tmp_path) in " ".join(cmd) and "io_test_top" in " ".join(cmd)
    assert bb.bitstream_name("io_test").endswith("_BRINGUP.bit")
