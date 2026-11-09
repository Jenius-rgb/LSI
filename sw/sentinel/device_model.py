"""Python model of the SPI-visible behaviour of the accelerator.

Used by LogTransport (to know what the RTL should answer) and by MockBackend. It holds
registers and memories, and runs the unit-level engine model on START.
"""
from __future__ import annotations

import numpy as np

from model.engine_model import EngineConfig, EngineResult, InjectionSlot, run_image
from model.golden import QModel
from sentinel import regmap as rm

CHECK_ALL = 0xFF
CHECK_NONE = 0x00


class ModelDevice:
    def __init__(self, qm: QModel, k: int = 8, c3_hw: bool = False, flags: int = 0):
        self.qm = qm
        self.k = k
        self.c3_hw = c3_hw
        self.flags = flags
        self.memory: dict[int, int] = {}
        self.regs: dict[int, int] = {}
        self.result: EngineResult | None = None
        self.status = 0
        self.ctrl = 0
        self.cycles_total = 0

    # ---- SPI ----------------------------------------------------------------------------
    def transaction(self, tx: bytes) -> tuple[bytes, list[int]]:
        """Return (bytes MISO shifts out, per-byte mask of bits the testbench must compare)."""
        n = len(tx)
        rx = bytearray(n)
        check = [CHECK_NONE] * n
        cmd = tx[0]
        if cmd == 0x9F:
            payload = b"SNTL" + bytes([rm.VERSION_MAJOR, rm.VERSION_MINOR, self.k, self.flags])
            for i, b in enumerate(payload[: n - 1]):
                rx[1 + i] = b
                check[1 + i] = CHECK_ALL
        elif cmd == 0x02:
            addr = (tx[1] << 16) | (tx[2] << 8) | tx[3]
            for i, b in enumerate(tx[4:]):
                self.write_byte(addr + i, b)
        elif cmd == 0x03:
            addr = (tx[1] << 16) | (tx[2] << 8) | tx[3]
            for i in range(5, n):
                value, comparable = self.read_byte(addr + i - 5)
                rx[i] = value
                check[i] = CHECK_ALL if comparable else CHECK_NONE
        return bytes(rx), check

    def poll_status(self, offset: int, mask: int, value: int) -> None:
        if offset != rm.REG_STATUS or (self.status_word() & mask) != value:
            raise TimeoutError("model device: poll would never finish")

    def status_word(self) -> int:
        return self.status

    # ---- registers and memories ------------------------------------------------------------
    def write_byte(self, addr: int, value: int) -> None:
        if addr < rm.MEM_REGS_SIZE:
            word_addr = addr & ~3
            shift = (addr & 3) * 8
            word = self.regs.get(word_addr, 0) & ~(0xFF << shift) | (value << shift)
            if word_addr == rm.REG_CTRL and addr & 3 == 0:
                self.ctrl = word & 0xFF & ~((1 << rm.CTRL_START_LSB) | (1 << rm.CTRL_SOFT_RESET_LSB))
                self.regs[word_addr] = self.ctrl
                if value & (1 << rm.CTRL_START_LSB):
                    self.run()
                return
            self.regs[word_addr] = word
        else:
            self.memory[addr] = value

    def read_byte(self, addr: int) -> tuple[int, bool]:
        """Return (value, comparable). Values that depend on timing are not comparable."""
        if addr >= rm.MEM_REGS_SIZE:
            if rm.MEM_LOGITS_BASE <= addr < rm.MEM_LOGITS_BASE + rm.MEM_LOGITS_SIZE:
                return self._logit_byte(addr - rm.MEM_LOGITS_BASE), True
            return self.memory.get(addr, 0), addr in self.memory
        word_addr = addr & ~3
        value, comparable = self.read_reg(word_addr)
        return (value >> ((addr & 3) * 8)) & 0xFF, comparable

    def _logit_byte(self, offset: int) -> int:
        if self.result is None:
            return 0
        index = offset // 4
        logits = self.result.logits
        value = int(logits[index]) & 0xFFFFFFFF if index < len(logits) else 0
        return (value >> ((offset & 3) * 8)) & 0xFF

    def read_reg(self, offset: int) -> tuple[int, bool]:
        if offset == rm.REG_ID:
            return 0x534E544C, True
        if offset == rm.REG_VERSION:
            return (rm.VERSION_MAJOR << 8) | rm.VERSION_MINOR, True
        if offset == rm.REG_STATUS:
            return self.status_word(), False
        if offset == rm.REG_RESULT_CLASS:
            return (self.result.pred if self.result else 0), True
        if offset in (rm.REG_CYCLES_TOTAL, rm.REG_CYCLES_RECOMPUTE, rm.REG_STARVE_CYCLES):
            return 0, False
        if rm.COUNTER_BASE <= offset < rm.COUNTER_BASE + 0x400:
            return self._counter((offset - rm.COUNTER_BASE) // 4), True
        return self.regs.get(offset, 0), True

    def _counter(self, index: int) -> int:
        if self.result is None:
            return 0
        if index < rm.LANE_CORRECTION_BASE:
            layer, kind = divmod(index, rm.COUNTER_STRIDE)
            if layer >= len(self.qm.layers) or kind >= len(rm.COUNTER_TYPES):
                return 0
            r = self.result
            series = {
                "UNITS": r.units, "CLEAN": r.clean, "CORRECTED": r.corrected,
                "CSUM_LANE": r.csum_lane, "RECOMPUTE": r.recompute, "FATAL": r.fatal_count,
            }[rm.COUNTER_TYPES[kind]]
            return series[layer]
        lane = index - rm.LANE_CORRECTION_BASE
        return self.result.lane_corrections[lane] if lane < len(self.result.lane_corrections) else 0

    # ---- execution ----------------------------------------------------------------------
    def _injection_slots(self) -> list[InjectionSlot]:
        slots = []
        for prefix in (rm.REG_INJ0_CTRL, rm.REG_INJ1_CTRL):
            ctrl = self.regs.get(prefix, 0)
            unit = self.regs.get(prefix + 4, 0) & 0xFFFF
            mask = self.regs.get(prefix + 8, 0) | (self.regs.get(prefix + 12, 0) << 32)
            slots.append(
                InjectionSlot(
                    enable=bool(ctrl & (1 << rm.INJ0_CTRL_EN_LSB)),
                    layer=(ctrl >> rm.INJ0_CTRL_LAYER_LSB) & 15,
                    unit=unit,
                    any_unit=bool(ctrl & (1 << rm.INJ0_CTRL_ANY_LSB)),
                    lane=(ctrl >> rm.INJ0_CTRL_LANE_LSB) & 63,
                    mask=mask,
                    oneshot=bool(ctrl & (1 << rm.INJ0_CTRL_ONESHOT_LSB)),
                )
            )
        return slots

    def _image_bytes(self) -> np.ndarray:
        base = rm.MEM_IMG1_BASE if (self.ctrl >> rm.CTRL_IMG_SEL_LSB) & 1 else rm.MEM_IMG0_BASE
        c, h, w = self.qm.in_shape
        data = np.array([self.memory.get(base + i, 0) for i in range(c * h * w)], dtype=np.uint8)
        return data.reshape(c, h, w)

    def run(self) -> None:
        mode = (self.ctrl >> rm.CTRL_MODE_LSB) & 3
        c3_on = bool(self.ctrl & (1 << rm.CTRL_C3_EN_LSB))
        trust = bool(self.ctrl & (1 << rm.CTRL_TRUST_CSUM_LANE_LSB))
        cfg = EngineConfig(k=self.k, c3_hw=self.c3_hw, c3_on=c3_on, mode=mode, trust=trust)
        self.result = run_image(self.qm, self._image_bytes(), cfg, self._injection_slots())
        self.status = (1 << rm.STATUS_DONE_LSB) | (int(self.result.fatal) << rm.STATUS_FATAL_LSB) | (int(self.result.log_ovf) << rm.STATUS_LOG_OVF_LSB)
