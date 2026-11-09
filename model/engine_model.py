"""Python model of the engine at the level of computing units (SPEC 5, 6, 9, 11).

It predicts what the RTL does for an image under a checking mode, fault injection or the
synthetic timing-error model: logits, counters, recompute log, FATAL and LOG_OVF.
Unit order, log order and injection semantics follow rtl/engine.v and rtl/lane_array.v.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from model.campaign import _checksum_weights
from model.checker import CORRECT, UNPROTECTED, Outcome, check, xor_inject
from model.golden import QModel, conv_accumulate, flatten_chw, maxpool2x2, requant


@dataclass
class InjectionSlot:
    enable: bool = False
    layer: int = 0
    unit: int = 0  # ignored when any_unit is set
    any_unit: bool = False
    lane: int = 1  # 1..K data, K+1.. checksum
    mask: int = 0
    oneshot: bool = False


@dataclass
class EngineConfig:
    k: int = 8
    c3_hw: bool = False
    c3_on: bool = False
    mode: int = CORRECT
    trust: bool = False
    n_log: int = 256
    acc_w: int = 32
    cs_w: int = 48


@dataclass
class EngineResult:
    logits: np.ndarray
    pred: int
    units: list[int]
    clean: list[int]
    corrected: list[int]
    csum_lane: list[int]
    recompute: list[int]
    fatal_count: list[int]
    lane_corrections: list[int]
    fatal: bool
    log_ovf: bool
    log_overflow_count: int
    recompute_windows: list[int]
    injections_fired: int = 0
    events: list[dict] = field(default_factory=list)


class _Injector:
    """Tracks slots and the per-pass unit counter exactly as rtl/lane_array.v does."""

    def __init__(self, slots: list[InjectionSlot], k: int, ncs: int, acc_w: int, cs_w: int):
        self.slots = slots
        self.k, self.ncs, self.acc_w, self.cs_w = k, ncs, acc_w, cs_w
        self.fired = [False] * len(slots)
        self.total = 0

    def rearm(self) -> None:
        self.fired = [False] * len(self.slots)

    def apply(self, layer: int, unit: int, y: list[int], s: list[int]) -> tuple[list[int], list[int]]:
        y, s = list(y), list(s)
        fires = [
            sl.enable and sl.layer == layer and not (sl.oneshot and self.fired[i]) and (sl.any_unit or sl.unit == unit)
            for i, sl in enumerate(self.slots)
        ]
        for i, sl in enumerate(self.slots):
            if fires[i]:
                self.total += 1
                if 1 <= sl.lane <= self.k:
                    y[sl.lane - 1] = xor_inject(y[sl.lane - 1], sl.mask, self.acc_w)
                elif self.k < sl.lane <= self.k + self.ncs:
                    s[sl.lane - self.k - 1] = xor_inject(s[sl.lane - self.k - 1], sl.mask, self.cs_w)
        for i, fire in enumerate(fires):
            self.fired[i] = self.fired[i] or fire
        return y, s


def _unit_iter(g: int, windows: int, is_fc: bool):
    """Main-pass order of SPEC 5.3: (g, wy, wx, pos)."""
    if is_fc:
        for group in range(g):
            yield group, 0, 0, 0
        return
    for group in range(g):
        for wy in range(windows):
            for wx in range(windows):
                for pos in range(4):
                    yield group, wy, wx, pos


def run_image(
    qm: QModel, image: np.ndarray, cfg: EngineConfig,
    slots: list[InjectionSlot] | None = None,
    extra_faults=None,
) -> EngineResult:
    """Model one image. extra_faults(layer_idx, unit_idx, pass_kind, y, s) may corrupt a unit."""
    k = cfg.k
    ncs = 3 if cfg.c3_hw else 2
    n_layers = len(qm.layers)
    injector = _Injector(slots or [], k, ncs, cfg.acc_w, cfg.cs_w)

    counts = {name: [0] * n_layers for name in ("units", "clean", "corrected", "csum", "recompute", "fatal")}
    lane_corr = [0] * k
    recompute_windows = [0] * n_layers
    fatal = False
    log_ovf_any = False
    log_ovf_count = 0

    x = np.asarray(image, dtype=np.int64)
    logits = None
    events: list[dict] = []

    for layer_idx, layer in enumerate(qm.layers):
        is_fc = layer.kind == "fc"
        cout = layer.w.shape[0]
        g = (cout + k - 1) // k
        wc = _checksum_weights(layer.w, k)
        if is_fc:
            flat = flatten_chw(x)
            acc = flat @ layer.w.T
            padded = np.zeros(g * k, dtype=np.int64)
            padded[:cout] = acc
            sums = np.stack([flat @ wc[:, p].T for p in range(3)], axis=-1)  # (g, 3)
            windows = 1
            h = width = 1
        else:
            h, width = x.shape[1:]
            acc = conv_accumulate(layer.w, x)  # (Cout, H, W)
            padded = np.zeros((g * k, h, width), dtype=np.int64)
            padded[:cout] = acc
            sums = np.stack([conv_accumulate(wc[:, p], x) for p in range(3)], axis=-1)  # (g, H, W, 3)
            windows = h // 2

        padded_b = np.zeros(g * k, dtype=np.int64)
        padded_b[:cout] = layer.b

        def unit_values(group: int, wy: int, wx: int, pos: int) -> tuple[list[int], list[int]]:
            if is_fc:
                return [int(v) for v in padded[group * k : (group + 1) * k]], [int(v) for v in sums[group]]
            y0, x0 = wy * 2 + (pos >> 1), wx * 2 + (pos & 1)
            return (
                [int(v) for v in padded[group * k : (group + 1) * k, y0, x0]],
                [int(v) for v in sums[group, y0, x0]],
            )

        # Results of the layer, per lane: accumulators actually accepted for each unit.
        accepted = padded.copy()

        def process(pass_kind: str, unit_index: int, group: int, wy: int, wx: int, pos: int) -> Outcome:
            y_true, s_true = unit_values(group, wy, wx, pos)
            y_seen, s_seen = injector.apply(layer_idx, unit_index, y_true, s_true)
            if extra_faults is not None:
                y_seen, s_seen = extra_faults(layer_idx, unit_index, pass_kind, y_seen, s_seen)
            res = check(
                y_seen, s_seen[0], s_seen[1], s_seen[2] if ncs == 3 else 0, cfg.mode,
                cfg.c3_on and cfg.c3_hw, cfg.trust, cfg.acc_w, cfg.cs_w,
            )
            values = res.y if cfg.mode != UNPROTECTED else y_seen
            if is_fc:
                accepted[group * k : (group + 1) * k] = values
            else:
                y0, x0 = wy * 2 + (pos >> 1), wx * 2 + (pos & 1)
                accepted[group * k : (group + 1) * k, y0, x0] = values
            if pass_kind == "main":
                counts["units"][layer_idx] += 1
                if res.outcome == Outcome.CLEAN:
                    counts["clean"][layer_idx] += 1
                elif res.outcome == Outcome.CORRECTED:
                    counts["corrected"][layer_idx] += 1
                    lane_corr[res.lane - 1] += 1
                elif res.outcome == Outcome.CSUM_LANE:
                    counts["csum"][layer_idx] += 1
                elif res.outcome == Outcome.RECOMPUTE:
                    counts["recompute"][layer_idx] += 1
            elif res.outcome not in (Outcome.CLEAN, Outcome.NONE):
                counts["fatal"][layer_idx] += 1
            return res.outcome

        if layer_idx == 0:
            injector.rearm()
        # ---- main pass ----
        log: list[tuple[int, int, int]] = []
        log_full = False
        window_fail = False
        for unit_index, (group, wy, wx, pos) in enumerate(_unit_iter(g, windows, is_fc)):
            outcome = process("main", unit_index, group, wy, wx, pos)
            failed = outcome == Outcome.RECOMPUTE
            if is_fc or pos == 3:
                if window_fail or failed:
                    if len(log) < cfg.n_log:
                        log.append((group, wy, wx))
                    else:
                        log_full = True
                window_fail = False
            elif failed:
                window_fail = True

        # ---- recompute pass ----
        if cfg.mode != UNPROTECTED and (log_full or log):
            recompute_windows[layer_idx] = len(log)
            recompute_items = (
                list(_unit_iter(g, windows, is_fc))
                if log_full
                else [(group, wy, wx, pos) for group, wy, wx in log for pos in (range(1) if is_fc else range(4))]
            )
            if log_full:
                log_ovf_any = True
                log_ovf_count += 1
            for unit_index, (group, wy, wx, pos) in enumerate(recompute_items):
                outcome = process("recompute", unit_index, group, wy, wx, pos)
                if outcome not in (Outcome.CLEAN, Outcome.NONE):
                    fatal = True

        # ---- post-processing with what the hardware finally holds ----
        if is_fc:
            logits = accepted[:cout] + layer.b
            x = logits
        else:
            v = accepted[:cout] + layer.b[:, None, None]
            x = maxpool2x2(requant(v, layer.m, layer.n))

    pred = int(np.argmax(logits))
    return EngineResult(
        logits=logits, pred=pred,
        units=counts["units"], clean=counts["clean"], corrected=counts["corrected"],
        csum_lane=counts["csum"], recompute=counts["recompute"], fatal_count=counts["fatal"],
        lane_corrections=lane_corr, fatal=fatal, log_ovf=log_ovf_any, log_overflow_count=log_ovf_count,
        recompute_windows=recompute_windows, injections_fired=injector.total, events=events,
    )
