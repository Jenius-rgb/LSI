"""Backends with one API: MockBackend (Python models, [SYNTHETIC]) and HwBackend (real board)."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from model.engine_model import EngineConfig, InjectionSlot, run_image
from model.fault_model import FaultParams, TimingFaultModel
from model.governor import GovParams, GovState, reset, step
from model.golden import QModel, forward
from model.config import layer_shapes


@dataclass
class ClassifyResult:
    pred: int
    logits: list[int]
    fpga_cycles: int
    cycles_recompute: int
    fpga_time_s: float
    fatal: bool
    log_ovf: bool
    units: list[int]
    clean: list[int]
    corrected: list[int]
    csum_lane: list[int]
    recompute: list[int]
    lane_corrections: list[int]
    events: list[dict] = field(default_factory=list)
    level: int = 0
    turbo_mask: int = 0


class MockBackend:
    """Golden, checker, governor and the synthetic timing-error model. Never measures hardware."""

    name = "mock"

    def __init__(
        self, qm: QModel, cfg: dict | None = None, k: int = 8, c3_hw: bool = False, f_safe_mhz: float = 100.0,
        fault: FaultParams | None = None, sparsity: list[float] | None = None, gov: GovParams | None = None,
    ):
        self.qm = qm
        self.cfg = cfg
        self.k = k
        self.c3_hw = c3_hw
        self.f_safe = f_safe_mhz
        self.mode = 2
        self.f_turbo = f_safe_mhz
        self.turbo_mask = (1 << len(qm.layers)) - 1
        self.fault = TimingFaultModel(k, 3 if c3_hw else 2, fault or FaultParams(), sparsity)
        self.gov_params = gov
        self.gov_state: GovState | None = reset(gov, len(qm.layers)) if gov else None
        self.gov_freqs = None
        self.counter_image = 0

    def set_frequency(self, f_mhz: float) -> None:
        self.f_turbo = f_mhz

    def set_mode(self, mode: int) -> None:
        self.mode = mode

    def set_turbo_mask(self, mask: int) -> None:
        self.turbo_mask = mask

    def enable_governor(self, freq_table: list[float]) -> None:
        self.gov_freqs = freq_table

    def _layer_freq(self, layer: int) -> float:
        if self.gov_state is not None:
            f = self.gov_freqs[self.gov_state.level]
            return f if self.gov_state.turbo_en[layer] else self.f_safe
        return self.f_turbo if (self.turbo_mask >> layer) & 1 else self.f_safe

    def classify(self, image: np.ndarray, image_id: int | None = None, slots: list[InjectionSlot] | None = None) -> ClassifyResult:
        image_id = self.counter_image if image_id is None else image_id
        self.counter_image += 1
        fault, f_safe, k = self.fault, self.f_safe, self.k
        n_lanes = k + (3 if self.c3_hw else 2)
        min_onset = float(fault.f_onset.min())
        layer_freq = [self._layer_freq(l) for l in range(len(self.qm.layers))]
        events: list[dict] = []

        def extra_faults(layer: int, unit: int, pass_kind: str, y: list[int], s: list[int]):
            f = f_safe if pass_kind == "recompute" else layer_freq[layer]
            if f <= min_onset:
                return y, s
            for lane in range(n_lanes):
                if fault.error_occurs(image_id, layer, unit, lane, f):
                    from model.checker import xor_inject

                    if lane < k:
                        mask = fault.error_mask(image_id, layer, unit, lane, f, y[lane])
                        y[lane] = xor_inject(y[lane], mask, 32)
                    else:
                        mask = fault.error_mask(image_id, layer, unit, lane, f, s[lane - k])
                        s[lane - k] = xor_inject(s[lane - k], mask, 48)
                    events.append({"layer": layer, "unit": unit, "lane": lane, "bit": int(np.log2(mask)), "f": f})
            return y, s

        cfg = EngineConfig(k=k, c3_hw=self.c3_hw, c3_on=self.c3_hw, mode=self.mode)
        res = run_image(self.qm, image, cfg, slots, extra_faults=extra_faults)

        cycles = cycles_recompute = 0
        time_s = 0.0
        shapes = [(lyr.w.shape, lyr.kind) for lyr in self.qm.layers]
        for layer_idx, (shape, kind) in enumerate(shapes):
            cout, t = shape[0], shape[1] * 9 if kind == "conv" else shape[1]
            if kind == "conv":
                h = self.qm.in_shape[1] // (2**layer_idx)
                ideal = h * h * ((cout + k - 1) // k) * t
            else:
                ideal = ((cout + k - 1) // k) * t
            f = layer_freq[layer_idx]
            cycles += ideal
            time_s += ideal / (f * 1e6)
            redo = res.recompute[layer_idx] * t
            cycles_recompute += redo
            time_s += redo / (f_safe * 1e6)

        out = ClassifyResult(
            res.pred, [int(v) for v in res.logits], cycles + cycles_recompute, cycles_recompute, time_s,
            res.fatal, res.log_ovf, res.units, res.clean, res.corrected, res.csum_lane, res.recompute,
            res.lane_corrections, events,
            level=self.gov_state.level if self.gov_state else 0,
            turbo_mask=sum(b << i for i, b in enumerate(self.gov_state.turbo_en)) if self.gov_state else self.turbo_mask,
        )
        if self.gov_state is not None:
            step(self.gov_state, self.gov_params, res.recompute, res.corrected)
        return out

    def golden(self, image: np.ndarray):
        return forward(self.qm, image)

    def metadata(self) -> dict:
        return {"backend": "mock", "k": self.k, "c3_hw": self.c3_hw, "f_safe_mhz": self.f_safe, "fault_model": self.fault.metadata(), "label": "[SYNTHETIC]"}


class HwBackend:
    """The real accelerator through the SPI driver. Results are [HW] only when run on a board."""

    name = "hw"

    def __init__(self, driver, qm: QModel, k: int, n_classes: int, f_safe_mhz: float):
        self.driver = driver
        self.qm = qm
        self.k = k
        self.n_classes = n_classes
        self.f_safe = f_safe_mhz

    def set_mode(self, mode: int) -> None:
        self.driver.configure(mode=mode)

    def set_turbo_mask(self, mask: int) -> None:
        from sentinel import regmap as rm

        self.driver.write_reg(rm.REG_GOV_CTRL, mask << rm.GOV_CTRL_TURBO_MASK_LSB)

    def set_frequency(self, f_mhz: float) -> None:
        raise NotImplementedError("frequency selection needs the board facts (F_IN); see board/BRINGUP.md")

    def classify(self, image: np.ndarray, image_id: int | None = None, slots=None) -> ClassifyResult:
        from sentinel import regmap as rm

        self.driver.write_image(image.tobytes(), slot=0)
        self.driver.start()
        self.driver.wait_done()
        counters = self.driver.layer_counters(len(self.qm.layers))
        cycles = self.driver.read_reg(rm.REG_CYCLES_TOTAL)
        recompute = self.driver.read_reg(rm.REG_CYCLES_RECOMPUTE)
        status = self.driver.status()
        return ClassifyResult(
            self.driver.result_class(), self.driver.logits(self.n_classes), cycles, recompute, cycles / (self.f_safe * 1e6),
            bool(status & (1 << rm.STATUS_FATAL_LSB)), bool(status & (1 << rm.STATUS_LOG_OVF_LSB)),
            [c["units"] for c in counters], [c["clean"] for c in counters], [c["corrected"] for c in counters],
            [c["csum_lane"] for c in counters], [c["recompute"] for c in counters],
            self.driver.lane_corrections(self.k),
        )

    def metadata(self) -> dict:
        return {"backend": "hw", "k": self.k, "f_safe_mhz": self.f_safe, "label": "[HW]"}


def layer_names(qm: QModel) -> list[str]:
    return [lyr.name for lyr in qm.layers]


__all__ = ["ClassifyResult", "MockBackend", "HwBackend", "layer_shapes", "layer_names"]
