#!/usr/bin/env python3
"""Check a Raspberry Pi before bring-up step 2 (ADR-033: Raspberry Pi 5). Run on the Pi: python3 board/pi_check.py

Prints the Pi model, whether SPI0 CE0 is enabled (/dev/spidev0.0), and whether the Python packages
the SENTINEL scripts import are installed. It only reads; it touches no GPIO.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

# lgpio: gpiozero's pin factory on the Pi 5 ("Only lgpio works on the Pi 5", gpiozero docs). RPi.GPIO is not used.
MODULES = ("spidev", "gpiozero", "lgpio", "picamera2", "numpy", "cv2")


def gpio_note(model: str, has_lgpio: bool) -> str:
    """State of GPIO support for the SENTINEL scripts on this Pi model."""
    if "Raspberry Pi 5" in model and not has_lgpio:
        return "missing  Pi 5 needs gpiozero's lgpio factory: sudo apt install python3-lgpio python3-gpiozero"
    return "ok       gpiozero will use the lgpio pin factory" if has_lgpio else "missing  lgpio not installed"


def check(model_path: Path = Path("/proc/device-tree/model"), spidev_path: Path = Path("/dev/spidev0.0"),
          modules: tuple[str, ...] = MODULES) -> dict[str, tuple[str, str]]:
    rows: dict[str, tuple[str, str]] = {}
    if model_path.exists():
        rows["model"] = ("ok", model_path.read_bytes().rstrip(b"\x00").decode("ascii", "replace").strip())
    else:
        rows["model"] = ("missing", "not a Raspberry Pi, or the device tree is not readable")
    rows["spidev0.0"] = ("ok", str(spidev_path)) if spidev_path.exists() else ("missing", "enable SPI: raspi-config, Interface Options, SPI")
    for name in modules:
        found = importlib.util.find_spec(name) is not None
        rows[f"import {name}"] = ("ok", "") if found else ("missing", f"install the package that provides {name}")
    return rows


def main() -> int:
    rows = check()
    for key, (state, note) in rows.items():
        print(f"{state:8} {key:20} {note}")
    model = rows["model"][1]
    print("gpio     " + gpio_note(model, rows["import lgpio"][0] == "ok"))
    if rows["model"][0] == "ok" and "Raspberry Pi 5" not in model:
        print("note: the SENTINEL host is a Raspberry Pi 5 (ADR-033)")
    return 0 if all(state == "ok" for state, _ in rows.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
