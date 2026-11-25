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
    """No output of a bring-up design may sit on a line shared with the Raspberry Pi header (TK-1, TK-2), unless the
    design declares it in "shared_outputs" with a reason. Extended 25 Nov 2026 for spi_loopback, whose purpose is the
    Pi-to-FPGA SPI path: its MISO (A7) is an input on the Pi when SPI0 is enabled and is tri-stated while CE0 is high."""
    shared = {"B1", "B2", "A2", "A9", "A10", "C10", "D9", "A7", "A6", "A8", "D10", "B10", "B6", "C7", "C13",
              "A3", "D7", "B11", "C14", "B15", "A5", "C8", "D8", "C9", "B12"}
    for name, design in bb.DESIGNS.items():
        xdc = (ROOT / design["xdc"]).read_text(encoding="utf-8")
        outputs = set(design["outputs"])
        for line in xdc.splitlines():
            if "PACKAGE_PIN" in line and not line.lstrip().startswith("#"):
                pin, port = line.split("PACKAGE_PIN")[1].split("[get_ports")[0].strip(), line.split("get_ports")[1]
                if any(o in port for o in outputs):
                    declared = {port_name for port_name in design.get("shared_outputs", {}) if port_name in port}
                    assert pin not in shared or declared, (name, line)


def test_spi_loopback_shares_only_miso_and_tristates_it():
    d = bb.DESIGNS["spi_loopback"]
    assert set(d["shared_outputs"]) == {"spi_miso"} and d["shared_outputs"]["spi_miso"]
    xdc = (ROOT / d["xdc"]).read_text(encoding="utf-8")
    for pin, port in (("A8", "spi_sclk"), ("A6", "spi_mosi"), ("A7", "spi_miso"), ("D9", "spi_cs_n")):
        assert f"PACKAGE_PIN {pin} [get_ports {port}]" in xdc
    rtl = (ROOT / d["rtl"][0]).read_text(encoding="utf-8")
    assert "1'bz" in rtl  # MISO released while chip select is high


def test_output_goes_to_build_and_names_the_purpose(tmp_path):
    cmd = bb.vivado_command("vivado", "io_test", tmp_path)
    assert str(tmp_path) in " ".join(cmd) and "io_test_top" in " ".join(cmd)
    assert bb.bitstream_name("io_test").endswith("_BRINGUP.bit")
