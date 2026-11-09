#!/usr/bin/env python3
"""Board bring-up, one subcommand per step of board/BRINGUP.md.

Steps from `led` onwards run on the Raspberry Pi. `--dry-run` rehearses the software path on a
PC against the Python device model: it verifies the scripts, not the hardware.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "sw"))

from sentinel.device_model import ModelDevice  # noqa: E402
from sentinel.driver import SentinelDriver  # noqa: E402
from sentinel.transport import LogTransport, SpidevTransport  # noqa: E402
from sentinel import regmap as rm  # noqa: E402

BOARD_INFO = ROOT / "board" / "BOARD_INFO.md"


def required_unknowns(path: Path = BOARD_INFO) -> list[str]:
    """Required fields of BOARD_INFO.md still marked UNKNOWN."""
    section, unknown = None, []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section = line
        if section == "## Field wajib" and line.startswith("|") and "UNKNOWN" in line:
            unknown.append(line.split("|")[1].strip())
    return unknown


def need_board_facts() -> bool:
    missing = required_unknowns()
    if missing:
        print("BOARD_INFO.md still has UNKNOWN required fields. Not touching any hardware:")
        for field in missing:
            print(f"  - {field}")
        return False
    return True


def open_driver(dry_run: bool, model: str = "xs") -> tuple[SentinelDriver, object, str]:
    from model.vectors import load_or_random_qmodel

    qm, source = load_or_random_qmodel(model)
    if dry_run:
        return SentinelDriver(LogTransport(ModelDevice(qm))), qm, f"dry-run ({source})"
    return SentinelDriver(SpidevTransport()), qm, f"board ({source})"


def step_power(args) -> int:
    print("Manual checklist before applying power:")
    print("  [ ] Board seated on the Raspberry Pi 40-pin header.")
    print("  [ ] No shorts; PMOD headers clear.")
    print("  [ ] Supply and voltage as stated in the ZERO7 documentation (not assumed here).")
    print("Measure with a meter, record the readings in results/hw/bringup/power.txt.")
    return 0


def step_program(args) -> int:
    if not args.dry_run and not need_board_facts():
        return 2
    print("Program the bitstream with the method named in BOARD_INFO.md, using Vivado on the PC:")
    print("  vivado -mode tcl, then open_hw_manager, connect_hw_server, program_hw_devices.")
    return 0


def step_led(args) -> int:
    print("Expect LED1=busy, LED2=done, LED3=fast clock on turbo, LED4=fatal (see rtl/top_core.v).")
    return 0


def step_spi_loopback(args) -> int:
    if not args.dry_run and not need_board_facts():
        return 2
    drv, _, where = open_driver(args.dry_run)
    pattern = 0xA5C3F00F
    drv.write_reg(rm.REG_INJ0_UNIT, pattern)
    got = drv.read_reg(rm.REG_INJ0_UNIT)
    ok = got == pattern
    print(f"[{where}] SPI register loopback: wrote {pattern:#010x} read {got:#010x}: {'OK' if ok else 'FAIL'}")
    return 0 if ok else 1


def step_id(args) -> int:
    if not args.dry_run and not need_board_facts():
        return 2
    drv, _, where = open_driver(args.dry_run)
    ident = drv.read_id()
    ok = ident.magic == b"SNTL"
    print(f"[{where}] ID {ident}: {'OK' if ok else 'FAIL'}")
    return 0 if ok else 1


def step_load(args) -> int:
    if not args.dry_run and not need_board_facts():
        return 2
    drv, _, where = open_driver(args.dry_run, args.model)
    stem = ROOT / "build" / "weights" / f"{args.model}_k8"
    if not stem.with_suffix(".bin").exists():
        print(f"Missing {stem}.bin: run `python tools/run.py gen` first")
        return 1
    manifest = drv.load_model(stem.with_suffix(".bin"), stem.with_suffix(".manifest.json"))
    print(f"[{where}] loaded {manifest['weight_bytes']} weight bytes")
    return 0


def run_images(args, count: int) -> int:
    if not args.dry_run and not need_board_facts():
        return 2
    from model.data import verification_images
    from model.golden import forward

    drv, qm, where = open_driver(args.dry_run, args.model)
    drv.configure(mode=2)
    images, _, _ = verification_images(count)
    matches = 0
    for image in images:
        drv.write_image(image.tobytes(), slot=0)
        drv.start()
        drv.wait_done()
        gold = forward(qm, image)
        ok = drv.result_class() == gold.pred and drv.logits(int(qm.layers[-1].w.shape[0])) == [int(v) for v in gold.logits]
        matches += ok
    print(f"[{where}] {matches}/{count} images match the golden model")
    return 0 if matches == count else 1


def step_one_image(args) -> int:
    return run_images(args, 1)


def step_validate(args) -> int:
    return run_images(args, args.images)


def step_turbo(args) -> int:
    print("Turbo ramp is enabled only after step 8 passes. It needs F_IN and the MMCM table (M10).")
    print("Use tools/gen_mmcm_table.py with the real F_IN and verified DS189 limits, then rebuild.")
    return 0


STEPS = {
    "power": step_power, "program": step_program, "led": step_led, "spi-loopback": step_spi_loopback, "id": step_id,
    "load": step_load, "one-image": step_one_image, "validate": step_validate, "turbo": step_turbo,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("step", choices=sorted(STEPS))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--model", default="xs", choices=["s", "xs"])
    parser.add_argument("--images", type=int, default=200)
    args = parser.parse_args()
    return STEPS[args.step](args)


if __name__ == "__main__":
    raise SystemExit(main())
