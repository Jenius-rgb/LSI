"""Host over the JTAG cable while the Raspberry Pi is not there (ADR-025).

`JtagAxiTransport` gives `SentinelDriver` the same `xfer` and `poll_status` as the SPI transport,
but turns each SPI frame into 32-bit word transactions on an AXI port:

* `SimulatedAxi` runs them against the Python device model (dry run, no hardware);
* `RecordingAxi` also writes a log that the RTL model of the JTAG-to-AXI master replays
  (bench `jtag_session_xs`), so the bridge and core are checked bit for bit;
* `VivadoTclAxi` sends them to the JTAG-to-AXI Master IP through a Vivado Tcl session
  (Hardware Manager commands of UG908). Not run on a board yet: check it with `self_test` first.

Bus map as seen over AXI: byte address = SPI address; words are little-endian; addresses
0xFFFFF8 and 0xFFFFFC return the ID word that SPI command 0x9F returns.
Partial-word writes are done as read-modify-write, and only in memory (address >= 0x1000):
registers are always written as whole words, because some register writes have side effects.
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

from sentinel.backend import HwBackend
from sentinel.driver import CMD_ID, CMD_READ, CMD_WRITE, SentinelDriver

ID_ADDR = 0xFFFFF8
MEMORY_BASE = 0x1000
OP_WRITE, OP_READ, OP_POLL, OP_END = 0x10, 0x11, 0x12, 0xFF


class AxiPort:
    """Word access; `read32` returns (value, compare mask)."""

    def write32(self, addr: int, data: int, strb: int = 0xF) -> None:
        raise NotImplementedError

    def read32(self, addr: int) -> tuple[int, int]:
        raise NotImplementedError

    def poll(self, addr: int, mask: int, value: int, timeout_s: float = 5.0) -> None:
        deadline = time.monotonic() + timeout_s
        while (self.read32(addr)[0] & mask) != value:
            if time.monotonic() > deadline:
                raise TimeoutError(f"0x{addr:06x}: timeout waiting for {value:#x} under {mask:#x}")


class SimulatedAxi(AxiPort):
    """Word transactions applied to `sentinel.device_model.ModelDevice` (dry run)."""

    def __init__(self, device):
        self.device = device
        self.writes = 0
        self.reads = 0

    def write32(self, addr: int, data: int, strb: int = 0xF) -> None:
        self.writes += 1
        for i in range(4):
            if strb >> i & 1:
                self.device.write_byte(addr + i, (data >> (8 * i)) & 0xFF)

    def read32(self, addr: int) -> tuple[int, int]:
        self.reads += 1
        if addr >= ID_ADDR:
            rx, _ = self.device.transaction(bytes([CMD_ID]) + bytes(8))
            ident = int.from_bytes(rx[1:9], "big")
            return (ident >> 32 if addr == ID_ADDR else ident) & 0xFFFFFFFF, 0xFFFFFFFF
        value = mask = 0
        for i in range(4):
            byte, comparable = self.device.read_byte(addr + i)
            value |= byte << (8 * i)
            mask |= (0xFF if comparable else 0) << (8 * i)
        return value, mask

    def poll(self, addr: int, mask: int, value: int, timeout_s: float = 5.0) -> None:
        self.device.poll_status(addr, mask, value)   # the model finishes at once, or raises


class RecordingAxi(AxiPort):
    """Forwards to another port and keeps a log for the RTL replay model (rtl/platform/sim/jtag_axi_master_sim.v)."""

    def __init__(self, inner: AxiPort):
        self.inner = inner
        self.entries: list[tuple[int, int, int, int]] = []

    def write32(self, addr: int, data: int, strb: int = 0xF) -> None:
        self.inner.write32(addr, data, strb)
        self.entries.append(((OP_WRITE << 24) | strb, addr, data, 0))

    def read32(self, addr: int) -> tuple[int, int]:
        value, mask = self.inner.read32(addr)
        self.entries.append((OP_READ << 24, addr, value, mask))
        return value, mask

    def poll(self, addr: int, mask: int, value: int, timeout_s: float = 5.0) -> None:
        self.inner.poll(addr, mask, value, timeout_s)
        self.entries.append((OP_POLL << 24, addr, value, mask))

    def write_log(self, path) -> int:
        words = [w for entry in self.entries for w in entry] + [OP_END << 24, 0, 0, 0]
        Path(path).write_text("".join(f"{w & 0xFFFFFFFF:08x}\n" for w in words), encoding="ascii", newline="\n")
        return len(words)


class JtagAxiTransport:
    """The SPI-frame interface of `SentinelDriver` on top of an AXI word port."""

    def __init__(self, port: AxiPort):
        self.port = port

    def _read_bytes(self, addr: int, n: int) -> bytes:
        out = bytearray()
        for word_addr in range(addr & ~3, addr + n, 4):
            out += self.port.read32(word_addr)[0].to_bytes(4, "little")
        start = addr & 3
        return bytes(out[start : start + n])

    def _write_bytes(self, addr: int, data: bytes) -> None:
        end = addr + len(data)
        for word_addr in range(addr & ~3, end, 4):
            lo, hi = max(addr, word_addr), min(end, word_addr + 4)
            chunk = data[lo - addr : hi - addr]
            if lo == word_addr and hi == word_addr + 4:
                self.port.write32(word_addr, int.from_bytes(chunk, "little"))
                continue
            if word_addr < MEMORY_BASE:
                raise ValueError(f"partial write to register 0x{word_addr:03x}: registers take whole words over JTAG")
            old = bytearray(self.port.read32(word_addr)[0].to_bytes(4, "little"))
            old[lo - word_addr : hi - word_addr] = chunk
            self.port.write32(word_addr, int.from_bytes(old, "little"))

    def xfer(self, tx: bytes) -> bytes:
        rx = bytearray(len(tx))
        cmd = tx[0]
        if cmd == CMD_ID:
            ident = (self.port.read32(ID_ADDR)[0] << 32) | self.port.read32(ID_ADDR + 4)[0]
            payload = ident.to_bytes(8, "big")
            rx[1 : len(tx)] = payload[: len(tx) - 1]
        elif cmd == CMD_WRITE:
            addr = int.from_bytes(tx[1:4], "big")
            self._write_bytes(addr, bytes(tx[4:]))
        elif cmd == CMD_READ:
            addr = int.from_bytes(tx[1:4], "big")
            rx[5:] = self._read_bytes(addr, len(tx) - 5)
        else:
            raise ValueError(f"unknown command 0x{cmd:02x}")
        return bytes(rx)

    def poll_status(self, offset: int, mask: int, value: int, timeout_s: float = 5.0) -> None:
        self.port.poll(offset, mask, value, timeout_s)


class VivadoTclAxi(AxiPort):
    """JTAG-to-AXI Master through a Vivado Tcl session that stays open.

    Commands follow UG908 (Hardware Manager): `create_hw_axi_txn`, `run_hw_axi`, property DATA.
    This class has not run on a board yet: call `self_test()` after connecting, before experiments.
    """

    MARK = "@@SENTINEL@@"

    def __init__(self, vivado: str, bitstream: str | None = None, url: str = "localhost:3121"):
        self.proc = subprocess.Popen([vivado, "-mode", "tcl", "-nojournal", "-nolog"], stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        setup = ["open_hw_manager", f"connect_hw_server -url {url}", "open_hw_target",
                 "current_hw_device [lindex [get_hw_devices xc7s25*] 0]", "refresh_hw_device [current_hw_device]"]
        if bitstream:
            setup += [f"set_property PROGRAM.FILE {{{bitstream}}} [current_hw_device]", "program_hw_devices [current_hw_device]",
                      "refresh_hw_device [current_hw_device]"]
        setup.append("set sentinel_axi [lindex [get_hw_axis] 0]")
        for line in setup:
            self._run(line)

    @staticmethod
    def write_command(addr: int, data: int) -> str:
        return (f"create_hw_axi_txn -force sentinel_w $sentinel_axi -type write -address {addr:08X} -data {data:08X} -len 1; "
                "run_hw_axi -quiet [get_hw_axi_txns sentinel_w]")

    @staticmethod
    def read_command(addr: int) -> str:
        return (f"create_hw_axi_txn -force sentinel_r $sentinel_axi -type read -address {addr:08X} -len 1; "
                "run_hw_axi -quiet [get_hw_axi_txns sentinel_r]; puts \"DATA=[get_property DATA [get_hw_axi_txns sentinel_r]]\"")

    def _run(self, command: str) -> list[str]:
        assert self.proc.stdin is not None and self.proc.stdout is not None
        self.proc.stdin.write(f"{command}\nputs {self.MARK}\n")
        self.proc.stdin.flush()
        lines = []
        for line in self.proc.stdout:
            if line.strip() == self.MARK:
                return lines
            if line.startswith("ERROR"):
                raise RuntimeError(f"Vivado: {line.strip()} (command: {command})")
            lines.append(line.rstrip("\n"))
        raise RuntimeError("Vivado session ended")

    def write32(self, addr: int, data: int, strb: int = 0xF) -> None:
        if strb != 0xF:
            raise ValueError("whole words only over JTAG (JtagAxiTransport does read-modify-write)")
        self._run(self.write_command(addr, data))

    def read32(self, addr: int) -> tuple[int, int]:
        for line in self._run(self.read_command(addr)):
            if line.startswith("DATA="):
                return int(line[5:], 16), 0xFFFFFFFF
        raise RuntimeError(f"no DATA for 0x{addr:06x}")

    def self_test(self, addr: int = 0x030000) -> None:
        """Write and read back two patterns in image memory; raises if the word order or data is wrong."""
        for pattern in (0x01234567, 0x89ABCDEF):
            self.write32(addr, pattern)
            got = self.read32(addr)[0]
            if got != pattern:
                raise RuntimeError(f"JTAG self-test: wrote {pattern:08x}, read {got:08x}")

    def close(self) -> None:
        if self.proc.poll() is None:
            self._run("close_hw_manager")
            self.proc.stdin.write("exit\n")
            self.proc.stdin.flush()
            self.proc.wait(timeout=30)


class JtagBackend(HwBackend):
    """`HwBackend` over JTAG (ADR-025): same interface as `HwBackend` and `MockBackend`.

    Results are [HW] only when the port is a `VivadoTclAxi` connected to the board.
    """

    name = "jtag"

    def __init__(self, port: AxiPort, qm, k: int, n_classes: int, f_safe_mhz: float):
        super().__init__(SentinelDriver(JtagAxiTransport(port)), qm, k, n_classes, f_safe_mhz)
