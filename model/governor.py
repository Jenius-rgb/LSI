"""Reference model of the hardware governor (SPEC 10). rtl/governor.v must track it exactly."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GovParams:
    n_up: int = 8
    cooldown: int = 4
    corr_hi: int = 16
    l_min: int = 0
    l_max: int = 15
    auto: bool = True


@dataclass
class GovState:
    level: int = 0
    turbo_en: list[int] = field(default_factory=list)
    cool: list[int] = field(default_factory=list)
    clean_streak: int = 0

    def snapshot(self) -> tuple[int, int, int, tuple[int, ...]]:
        mask = sum(bit << i for i, bit in enumerate(self.turbo_en))
        return self.level, mask, self.clean_streak, tuple(self.cool)


def reset(params: GovParams, layers: int) -> GovState:
    return GovState(level=params.l_min, turbo_en=[1] * layers, cool=[0] * layers, clean_streak=0)


def step(state: GovState, params: GovParams, fails: list[int], corrected: list[int]) -> GovState:
    """End-of-image update, line by line from SPEC 10. No change in manual mode."""
    if not params.auto:
        return state
    any_fail = False
    for layer in range(len(fails)):
        if fails[layer] > 0:
            state.turbo_en[layer] = 0
            state.cool[layer] = params.cooldown
            any_fail = True
        elif not state.turbo_en[layer]:
            if state.cool[layer] > 0:
                state.cool[layer] -= 1
            if state.cool[layer] == 0:
                state.turbo_en[layer] = 1
    corr = sum(corrected)
    if any_fail or corr > params.corr_hi:
        state.level = max(state.level - 1, params.l_min)
        state.clean_streak = 0
    else:
        state.clean_streak += 1
        if state.clean_streak >= params.n_up:
            state.level = min(state.level + 1, params.l_max)
            state.clean_streak = 0
    return state
