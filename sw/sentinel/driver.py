"""Host driver for the SENTINEL accelerator (SPEC 12)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from sentinel import regmap as rm
from sentinel.transport import Transport

CMD_WRITE = 0x02
CMD_READ = 0x03
CMD_ID = 0x9F
MAX_CHUNK = 256


@dataclass
class DeviceId:
    magic: bytes
    major: int
    minor: int
    k: int
    flags: int


class SentinelDriver:
    def __init__(self, transport: Transport):
        self.t = transport

    # ---- raw access ---------------------------------------------------------------------
    def read_id(self) -> DeviceId:
        rx = self.t.xfer(bytes([CMD_ID]) + bytes(8))
        return DeviceId(rx[1:5], rx[5], rx[6], rx[7], rx[8])

    def write(self, address: int, data: bytes) -> None:
        for start in range(0, len(data), MAX_CHUNK):
            chunk = data[start : start + MAX_CHUNK]
            a = address + start
            self.t.xfer(bytes([CMD_WRITE, (a >> 16) & 0xFF, (a >> 8) & 0xFF, a & 0xFF]) + chunk)

    def read(self, address: int, count: int) -> bytes:
        out = bytearray()
        for start in range(0, count, MAX_CHUNK):
            n = min(MAX_CHUNK, count - start)
            a = address + start
            rx = self.t.xfer(bytes([CMD_READ, (a >> 16) & 0xFF, (a >> 8) & 0xFF, a & 0xFF, 0]) + bytes(n))
            out += rx[5:]
        return bytes(out)

    def write_reg(self, offset: int, value: int) -> None:
        self.write(offset, int(value).to_bytes(4, "little"))

    def read_reg(self, offset: int) -> int:
        return int.from_bytes(self.read(offset, 4), "little")

    # ---- model and images ---------------------------------------------------------------
    def load_model(self, bin_path: Path, manifest_path: Path) -> dict:
        """Upload weights and parameters. Works without resynthesis for any compatible model."""
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        blob = Path(bin_path).read_bytes()
        n_weights = manifest["weight_bytes"]
        self.write(rm.MEM_WEIGHTS_BASE, blob[:n_weights])
        self.write(rm.MEM_PARAMS_BASE, blob[n_weights:])
        return manifest

    def write_image(self, image: bytes, slot: int = 0) -> None:
        self.write(rm.MEM_IMG1_BASE if slot else rm.MEM_IMG0_BASE, image)

    # ---- running ------------------------------------------------------------------------
    def configure(self, mode: int = 2, c3: bool = False, trust: bool = False, img_sel: int = 0) -> None:
        self._ctrl = (mode << rm.CTRL_MODE_LSB) | (int(c3) << rm.CTRL_C3_EN_LSB) | (int(trust) << rm.CTRL_TRUST_CSUM_LANE_LSB) | (img_sel << rm.CTRL_IMG_SEL_LSB)
        self.write_reg(rm.REG_CTRL, self._ctrl)

    def start(self) -> None:
        self.write_reg(rm.REG_CTRL, self._ctrl | (1 << rm.CTRL_START_LSB))

    def wait_done(self, timeout_s: float = 5.0) -> None:
        done = 1 << rm.STATUS_DONE_LSB
        self.t.poll_status(rm.REG_STATUS, done, done, timeout_s)

    def status(self) -> int:
        return self.read_reg(rm.REG_STATUS)

    def result_class(self) -> int:
        return self.read_reg(rm.REG_RESULT_CLASS)

    def logits(self, n: int) -> list[int]:
        raw = self.read(rm.MEM_LOGITS_BASE, 4 * n)
        return [int.from_bytes(raw[i : i + 4], "little", signed=True) for i in range(0, 4 * n, 4)]

    def layer_counters(self, n_layers: int) -> list[dict]:
        out = []
        for layer in range(n_layers):
            base = rm.COUNTER_BASE + layer * rm.COUNTER_STRIDE * 4
            out.append({name.lower(): self.read_reg(base + i * 4) for i, name in enumerate(rm.COUNTER_TYPES)})
        return out

    def lane_corrections(self, k: int) -> list[int]:
        base = rm.COUNTER_BASE + rm.LANE_CORRECTION_BASE * 4
        return [self.read_reg(base + i * 4) for i in range(k)]
