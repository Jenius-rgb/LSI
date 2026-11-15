"""M14: board package: dry-run works, the build refuses while board facts are unknown."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def bringup(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "board/bringup.py", *args, "--dry-run"], cwd=ROOT, capture_output=True, text=True, timeout=120)


def test_dry_run_spi_loopback_and_id():
    for step in ("spi-loopback", "id"):
        res = bringup(step)
        assert res.returncode == 0, res.stdout + res.stderr


def test_dry_run_full_step_sequence_on_a_few_images():
    assert bringup("load", "--model", "xs").returncode in (0, 1)  # 1 only if weights were not generated
    res = bringup("validate", "--model", "xs", "--images", "3")
    assert res.returncode == 0 and "3/3" in res.stdout, res.stdout + res.stderr


def test_build_refuses_while_board_info_has_unknowns():
    res = subprocess.run([sys.executable, "board/build_bitstream.py"], cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert res.returncode == 2
    assert "UNKNOWN" in res.stdout


def test_required_unknowns_are_detected(tmp_path):
    """Detection logic on a fixture, so the test does not depend on what is known today."""
    sys.path.insert(0, str(ROOT / "board"))
    import bringup as b

    sample = tmp_path / "BOARD_INFO.md"
    sample.write_text(
        "# x\n\n## Field wajib\n\n| Field | Nilai | Sumber |\n| --- | --- | --- |\n"
        "| Part number FPGA | xc7s25csga225-1 | doc |\n| Speed grade | UNKNOWN | |\n"
        "| Clock input | pin B13; frekuensi UNKNOWN | doc |\n\n"
        "## Field opsional\n\n| Field | Nilai | Sumber |\n| --- | --- | --- |\n| Kamera | UNKNOWN | |\n",
        encoding="utf-8")
    assert b.required_unknowns(sample) == ["Speed grade", "Clock input"]


def test_official_facts_of_2026_11_10_are_filled_in():
    """The ZERO7 documents published on 2026-11-10 give the part, the clock and the SPI pins.

    Until 2026-11-16 this file asserted that "Part number" and "Clock input" were unknown.
    That described the state before the documents existed, so it was replaced by the fixture
    test above and by this check that the official facts stay filled in.
    """
    sys.path.insert(0, str(ROOT / "board"))
    import bringup as b

    missing = b.required_unknowns()
    for known in ("Part number", "Speed grade", "Clock input", "SPI Pi"):
        assert not any(known in m for m in missing), missing
    text = (ROOT / "board" / "BOARD_INFO.md").read_text(encoding="utf-8")
    assert "xc7s25csga225-1" in text and "B13" in text


def test_hardware_steps_refuse_on_the_real_path_while_unknown():
    res = subprocess.run([sys.executable, "board/bringup.py", "id"], cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert res.returncode == 2 and "UNKNOWN" in res.stdout


def test_xdc_template_has_placeholders_only():
    text = (ROOT / "board" / "xdc" / "sentinel_board.xdc.template").read_text(encoding="utf-8")
    assert "<PIN>" in text and all(line.startswith("#") or not line.strip() for line in text.splitlines())
    assert not (ROOT / "board" / "xdc" / "sentinel_board.xdc").exists()


# Configuration pins of ZERO7 (connection table): QSPI, JTAG, PROG, INIT, DONE, MODE, PUDC_B.
CONFIG_PINS = {"F5", "H14", "H15", "J12", "K13", "L11", "E5", "K4", "K5", "L4", "J5", "L5", "G5", "M5", "N5", "M6", "K11"}


def test_zero7_xdc_matches_the_connection_table():
    import re

    text = (ROOT / "board" / "zero7.xdc").read_text(encoding="utf-8")
    pins = {}
    for line in text.splitlines():
        m = re.search(r"PACKAGE_PIN (\S+)\s+\[get_ports \{?([\w\[\]]+)\}?\]", line)
        if m:
            assert m.group(1) not in CONFIG_PINS, line  # also for the reserved, commented lines
            if not line.lstrip().startswith("#"):
                pins[m.group(2)] = m.group(1)
        if "IOSTANDARD" in line and not line.lstrip().startswith("#"):
            assert "TODO: belum dikonfirmasi" in line, line
    expected = {"clk_in": "B13", "spi_sclk": "A8", "spi_mosi": "A6", "spi_miso": "A7", "spi_cs_n": "D9"}
    assert {k: pins.get(k) for k in expected} == expected
    assert len(set(pins.values())) == len(pins)
    assert "create_clock -name clk_in -period 50.000" in text
