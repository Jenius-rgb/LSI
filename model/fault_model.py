"""Artificial timing-error model (SPEC 11.3). Development only.

Everything produced with this model is labelled [SYNTHETIC]. It says nothing about how a
real FPGA fails: its purpose is to exercise the checker, the governor and the experiment
scripts before a board exists.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np


@dataclass(frozen=True)
class FaultParams:
    seed: int = 2027
    f_onset_mhz: float = 150.0  # mean onset frequency (synthetic)
    spread: float = 0.15  # relative lane-to-lane spread of the onset
    gamma: float = 0.0  # H3 assumption: onset scales with input sparsity
    delta_mhz: float = 40.0  # distance from onset to probability 1
    alpha: float = 2.0  # exponent of the probability law


def _mix64(x: int) -> int:
    """SplitMix64 finaliser."""
    x &= (1 << 64) - 1
    x = ((x ^ (x >> 30)) * 0xBF58476D1CE4E5B9) & ((1 << 64) - 1)
    x = ((x ^ (x >> 27)) * 0x94D049BB133111EB) & ((1 << 64) - 1)
    return x ^ (x >> 31)


def _hash64(*fields: int) -> int:
    h = 0x9E3779B97F4A7C15
    for value in fields:
        h = _mix64((h ^ (value & ((1 << 64) - 1))) + 0x9E3779B97F4A7C15)
    return h


class TimingFaultModel:
    def __init__(self, k: int, n_csum: int, params: FaultParams, sparsity: list[float] | None = None):
        self.k = k
        self.n_csum = n_csum
        self.params = params
        self.sparsity = list(sparsity) if sparsity is not None else []
        rng = np.random.default_rng(params.seed)
        lanes = k + n_csum
        self.f_onset = params.f_onset_mhz * (1.0 + params.spread * rng.uniform(-1.0, 1.0, size=lanes))

    def onset(self, lane: int, layer: int) -> float:
        """Onset of lane (0-based) in a layer: f_onset_k * (1 + gamma * s_l)."""
        s = self.sparsity[layer] if layer < len(self.sparsity) else 0.0
        return float(self.f_onset[lane] * (1.0 + self.params.gamma * s))

    def probability(self, f_mhz: float, lane: int, layer: int) -> float:
        onset = self.onset(lane, layer)
        if f_mhz <= onset:
            return 0.0
        return min(1.0, ((f_mhz - onset) / self.params.delta_mhz) ** self.params.alpha)

    def _uniform(self, image_id: int, layer: int, unit: int, lane: int, f_mhz: float, salt: int = 0) -> float:
        h = _hash64(self.params.seed, image_id, layer, unit, lane, int(round(f_mhz * 1000)), salt)
        return h / 2.0**64

    def error_occurs(self, image_id: int, layer: int, unit: int, lane: int, f_mhz: float) -> bool:
        """Deterministic for a given (seed, image, layer, unit, lane, f), mimicking H2."""
        return self._uniform(image_id, layer, unit, lane, f_mhz) < self.probability(f_mhz, lane, layer)

    def error_mask(self, image_id: int, layer: int, unit: int, lane: int, f_mhz: float, true_value: int) -> int:
        """A single-bit XOR mask, biased towards the MSB of the bits active in the true value."""
        magnitude = abs(int(true_value))
        active = max(magnitude.bit_length(), 1)
        u = self._uniform(image_id, layer, unit, lane, f_mhz, salt=1)
        # Cubing keeps most of the mass near the top of the range (about 79% in the upper half).
        bit = active - 1 - int(active * u * u * u)
        return 1 << max(bit, 0)

    def metadata(self) -> dict:
        return {
            "label": "[SYNTHETIC]",
            **asdict(self.params),
            "f_onset_per_lane": [float(v) for v in self.f_onset],
            "sparsity": self.sparsity,
        }
