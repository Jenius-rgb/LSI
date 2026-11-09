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


def test_required_unknowns_are_detected():
    sys.path.insert(0, str(ROOT / "board"))
    import bringup as b

    missing = b.required_unknowns()
    assert any("Part number" in m for m in missing)
    assert any("Clock input" in m for m in missing)


def test_hardware_steps_refuse_on_the_real_path_while_unknown():
    res = subprocess.run([sys.executable, "board/bringup.py", "id"], cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert res.returncode == 2 and "UNKNOWN" in res.stdout


def test_xdc_template_has_placeholders_only():
    text = (ROOT / "board" / "xdc" / "sentinel_board.xdc.template").read_text(encoding="utf-8")
    assert "<PIN>" in text and all(line.startswith("#") or not line.strip() for line in text.splitlines())
    assert not (ROOT / "board" / "xdc" / "sentinel_board.xdc").exists()
