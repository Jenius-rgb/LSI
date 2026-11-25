#!/usr/bin/env python3
"""Check the SPI path from the Raspberry Pi 5 to the FPGA with fpga/bringup/spi_loopback loaded.

Run on the Pi (SPI enabled, /dev/spidev0.0 present):  python3 board/spi_loopback_check.py
Each transfer (one CE0 assertion) must return 0xA5, then every sent byte one position late. The script tries a
few SPI clocks from slow to fast and prints the error count per clock; paste its whole output. The design limit is
2.5 MHz (20 MHz FPGA clock / 8), so faster clocks are expected to fail.
"""
from __future__ import annotations

import random

FIRST = 0xA5
SPEEDS_HZ = (100_000, 500_000, 1_000_000, 2_000_000, 4_000_000)


def expected_echo(tx: bytes) -> bytes:
    return bytes([FIRST]) + tx[:-1]


def compare(tx: bytes, rx: bytes) -> int:
    """Number of received bytes that differ from the expected echo."""
    return sum(1 for a, b in zip(expected_echo(tx), rx) if a != b)


def diagnose(rx: bytes) -> str:
    """A hint when the reply carries no information at all."""
    if rx and all(b == 0xFF for b in rx):
        return "all 0xFF: MISO not driven (FPGA not configured, wrong pin, or CE0 not reaching the FPGA)"
    if rx and all(b == 0x00 for b in rx):
        return "all 0x00: MISO stuck low or the FPGA never saw CE0"
    return ""


def run(frames: int = 50, length: int = 16, seed: int = 2027) -> int:
    import spidev  # available on the Pi only

    spi = spidev.SpiDev()
    spi.open(0, 0)
    spi.mode = 0
    rng = random.Random(seed)
    failures = 0
    for speed in SPEEDS_HZ:
        spi.max_speed_hz = speed
        errors = 0
        hint = ""
        for _ in range(frames):
            tx = bytes(rng.randrange(256) for _ in range(length))
            rx = bytes(spi.xfer2(list(tx)))
            errors += compare(tx, rx)
            hint = hint or diagnose(rx)
        failures += errors > 0
        print(f"{speed:>9} Hz  {frames * length:5d} bytes  errors {errors:5d}  {hint}")
    spi.close()
    return 1 if failures == len(SPEEDS_HZ) else 0


if __name__ == "__main__":
    raise SystemExit(run())
