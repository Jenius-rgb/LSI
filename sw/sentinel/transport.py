"""Byte transports for the SENTINEL driver.

A transfer is one chip-select assertion: bytes out, the same number of bytes in.
``poll_status`` waits for bits in the low byte of a register; real hardware polls,
while the log transport records a wait instruction for the co-simulation.
"""
from __future__ import annotations

import time
from typing import Protocol


class Transport(Protocol):
    def xfer(self, tx: bytes) -> bytes: ...

    def poll_status(self, offset: int, mask: int, value: int, timeout_s: float = 5.0) -> None: ...


class SpidevTransport:
    """SPI through /dev/spidev on the Raspberry Pi. Speed and bus are board facts."""

    def __init__(self, bus: int = 0, device: int = 0, speed_hz: int = 1_000_000):
        import spidev  # available on the Pi only

        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)
        self.spi.mode = 0
        self.spi.max_speed_hz = speed_hz

    def xfer(self, tx: bytes) -> bytes:
        return bytes(self.spi.xfer2(list(tx)))

    def poll_status(self, offset: int, mask: int, value: int, timeout_s: float = 5.0) -> None:
        deadline = time.monotonic() + timeout_s
        while True:
            rx = self.xfer(bytes([0x03, 0, (offset >> 8) & 0xFF, offset & 0xFF, 0, 0]))
            if rx[5] & mask == value:
                return
            if time.monotonic() > deadline:
                raise TimeoutError(f"register 0x{offset:03x}: timeout waiting for {value:#x} under {mask:#x}")


class GpioDoneLine:
    """irq_done on a Raspberry Pi GPIO: RP_GPIO25, high while STATUS.DONE is set (ADR-016).

    Uses gpiozero with BCM numbering. Not exercised before the board phase; the tests use a stand-in.
    """

    def __init__(self, bcm_pin: int = 25):
        from gpiozero import DigitalInputDevice  # available on the Pi only

        self.line = DigitalInputDevice(bcm_pin, pull_up=False)

    def wait(self, timeout_s: float) -> bool:
        return bool(self.line.wait_for_active(timeout=timeout_s))


OP_BYTE = 0x01
OP_CS_LOW = 0x02
OP_CS_HIGH = 0x03
OP_POLL = 0x04
OP_END = 0xFF


class LogTransport:
    """Records transactions for replay in simulation (SPEC 12.6).

    The bytes returned to the driver, and the bytes the testbench expects from the RTL,
    both come from ``device``, a Python model of the SPI-visible behaviour.
    Each log entry is a 32-bit word: [op:8][a:8][b:8][c:8].
    """

    def __init__(self, device):
        self.device = device
        self.entries: list[int] = []

    def xfer(self, tx: bytes) -> bytes:
        rx, check = self.device.transaction(tx)
        self.entries.append(OP_CS_LOW << 24)
        for t, r, mask in zip(tx, rx, check):
            self.entries.append((OP_BYTE << 24) | (t << 16) | (r << 8) | mask)
        self.entries.append(OP_CS_HIGH << 24)
        return bytes(rx)

    def poll_status(self, offset: int, mask: int, value: int, timeout_s: float = 5.0) -> None:
        self.device.poll_status(offset, mask, value)
        self.entries.append((OP_POLL << 24) | ((offset & 0xFF) << 16) | (mask << 8) | value)

    def write_log(self, path) -> int:
        lines = [*self.entries, OP_END << 24]
        with open(path, "w", newline="\n", encoding="ascii") as fh:
            fh.writelines(f"{e:08x}\n" for e in lines)
        return len(lines)
