"""Load model and hardware configuration and derive layer shapes (no torch needed)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
KERNEL = 3


@dataclass(frozen=True)
class LayerShape:
    """Shape of one computing layer as seen by the hardware."""

    name: str
    kind: str  # "conv" or "fc"
    in_channels: int  # conv: Cin; fc: 1
    in_height: int
    in_width: int
    out_channels: int  # conv: Cout; fc: N
    pool: bool

    @property
    def out_height(self) -> int:
        return self.in_height // 2 if self.pool else self.in_height

    @property
    def out_width(self) -> int:
        return self.in_width // 2 if self.pool else self.in_width

    @property
    def n_in(self) -> int:
        """FC only: number of input activations."""
        return self.in_channels * self.in_height * self.in_width

    @property
    def weights(self) -> int:
        if self.kind == "conv":
            return self.in_channels * self.out_channels * KERNEL * KERNEL
        return self.n_in * self.out_channels

    @property
    def macs(self) -> int:
        if self.kind == "conv":
            return self.weights * self.in_height * self.in_width
        return self.weights

    @property
    def t(self) -> int:
        """Accumulation cycles per computing unit (SPEC 5.2)."""
        return self.in_channels * KERNEL * KERNEL if self.kind == "conv" else self.n_in

    def groups(self, k: int) -> int:
        return (self.out_channels + k - 1) // k

    def ideal_cycles(self, k: int) -> int:
        """SPEC 5.4: H_out and W_out are taken before pooling."""
        if self.kind == "conv":
            return self.in_height * self.in_width * self.groups(k) * self.t
        return self.groups(k) * self.t

    def units(self, k: int) -> int:
        """Number of computing units in the layer."""
        if self.kind == "conv":
            return self.in_height * self.in_width * self.groups(k)
        return self.groups(k)


def result_words(k: int, c3: int) -> int:
    """Words the lane-array result serializer sends per computing unit: K data lanes plus 2 or 3 checksum lanes.

    One word leaves per clk_fast cycle, so consecutive units must end at least this many cycles apart
    (rtl/lane_array.v). Without zero-skip a unit lasts ``LayerShape.t`` cycles.
    """
    return k + 2 + (1 if c3 else 0)


def shortest_unit(shapes: list[LayerShape]) -> tuple[str, int]:
    """(layer name, t) of the layer with the fewest accumulation cycles per unit."""
    layer = min(shapes, key=lambda s: s.t)
    return layer.name, layer.t


def model_names() -> list[str]:
    """Model variants with a config/model_<name>.yaml, sorted; `micro` is a test-only model and is left out."""
    return sorted(f.stem[len("model_"):] for f in CONFIG_DIR.glob("model_*.yaml") if f.stem != "model_micro")


def load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_model_config(name: str) -> dict:
    return load_yaml(CONFIG_DIR / f"model_{name}.yaml")


def load_hw_config(name: str = "hw_default") -> dict:
    return load_yaml(CONFIG_DIR / f"{name}.yaml")


def layer_shapes(cfg: dict, n_classes: int | None = None) -> list[LayerShape]:
    """Derive the hardware view of each layer from a model config."""
    channels, height, width = cfg["input"]["channels"], cfg["input"]["height"], cfg["input"]["width"]
    shapes: list[LayerShape] = []
    for layer in cfg["layers"]:
        if layer["type"] == "conv":
            pool = bool(layer.get("pool", False))
            shape = LayerShape(layer["name"], "conv", channels, height, width, layer["out_channels"], pool)
            channels, height, width = shape.out_channels, shape.out_height, shape.out_width
        elif layer["type"] == "fc":
            n = n_classes if n_classes is not None else cfg["n_classes"]
            shape = LayerShape(layer["name"], "fc", channels, height, width, n, False)
        else:
            raise ValueError(f"unknown layer type: {layer['type']}")
        shapes.append(shape)
    return shapes
