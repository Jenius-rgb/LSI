"""Integer golden model: SPEC section 3 exactly, in NumPy int64. Oracle for the RTL."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


def requant(v: np.ndarray, m: int, n: int) -> np.ndarray:
    """SPEC 3.3: q = (v*M + 2^(n-1)) >> n (no rounding term when n = 0), clamped to 0..255."""
    v = np.asarray(v, dtype=np.int64)
    q = (v * m + (1 << (n - 1))) >> n if n > 0 else v * m
    return np.clip(q, 0, 255)


def conv_accumulate(w: np.ndarray, a: np.ndarray) -> np.ndarray:
    """SPEC 3.2. w is (Cout, Cin, 3, 3); a is (Cin, H, W) or (B, Cin, H, W)."""
    a = np.asarray(a, dtype=np.int64)
    single = a.ndim == 3
    if single:
        a = a[None]
    b, cin, h, width = a.shape
    padded = np.zeros((b, cin, h + 2, width + 2), dtype=np.int64)
    padded[:, :, 1:-1, 1:-1] = a
    acc = np.zeros((b, w.shape[0], h, width), dtype=np.int64)
    for i in range(3):
        for j in range(3):
            window = padded[:, :, i : i + h, j : j + width]  # element [c, y, x] = a[c, y+i-1, x+j-1]
            acc += np.einsum("oc,bcyx->boyx", w[:, :, i, j], window)
    return acc[0] if single else acc


def maxpool2x2(y: np.ndarray) -> np.ndarray:
    """SPEC 3.4: 2x2 max pool with stride 2 over the last two axes."""
    h, width = y.shape[-2:]
    reshaped = y.reshape(*y.shape[:-2], h // 2, 2, width // 2, 2)
    return reshaped.max(axis=(-3, -1))


def flatten_chw(a: np.ndarray) -> np.ndarray:
    """SPEC 3.1: i = c*H*W + y*W + x, over the last three axes."""
    return a.reshape(*a.shape[:-3], -1)


def argmax_first(z: np.ndarray) -> np.ndarray:
    """SPEC 3.5: the smallest index holding the maximum (np.argmax returns the first)."""
    return np.argmax(z, axis=-1)


@dataclass
class QLayer:
    name: str
    kind: str  # "conv" or "fc"
    w: np.ndarray  # conv: (Cout, Cin, 3, 3); fc: (N, N_in)
    b: np.ndarray  # (Cout,)
    m: int = 0
    n: int = 0


@dataclass
class QModel:
    name: str
    in_shape: tuple[int, int, int]
    layers: list[QLayer] = field(default_factory=list)

    def save(self, path: Path) -> None:
        arrays = {"name": np.array(self.name), "in_shape": np.array(self.in_shape), "count": np.array(len(self.layers))}
        for i, layer in enumerate(self.layers):
            arrays[f"l{i}_name"] = np.array(layer.name)
            arrays[f"l{i}_kind"] = np.array(layer.kind)
            arrays[f"l{i}_w"] = layer.w.astype(np.int8)
            arrays[f"l{i}_b"] = layer.b.astype(np.int32)
            arrays[f"l{i}_m"] = np.array(layer.m)
            arrays[f"l{i}_n"] = np.array(layer.n)
        np.savez_compressed(path, **arrays)

    @classmethod
    def load(cls, path: Path) -> "QModel":
        with np.load(path) as d:
            layers = [
                QLayer(
                    str(d[f"l{i}_name"]), str(d[f"l{i}_kind"]),
                    d[f"l{i}_w"].astype(np.int64), d[f"l{i}_b"].astype(np.int64),
                    int(d[f"l{i}_m"]), int(d[f"l{i}_n"]),
                )
                for i in range(int(d["count"]))
            ]
            return cls(str(d["name"]), tuple(int(x) for x in d["in_shape"]), layers)


@dataclass
class LayerTrace:
    input: np.ndarray
    acc: np.ndarray  # lane accumulators before bias
    y: np.ndarray | None  # conv only: requantised, before pooling
    output: np.ndarray  # conv: after pooling; fc: logits


@dataclass
class GoldenResult:
    logits: np.ndarray
    pred: np.ndarray | int
    trace: list[LayerTrace] | None = None


def forward(qm: QModel, image: np.ndarray, trace: bool = False) -> GoldenResult:
    """Run an image (C, H, W) or a batch (B, C, H, W) through the integer model."""
    x = np.asarray(image, dtype=np.int64)
    records: list[LayerTrace] | None = [] if trace else None
    logits = None
    for layer in qm.layers:
        if layer.kind == "conv":
            acc = conv_accumulate(layer.w, x)
            v = acc + layer.b[:, None, None]
            y = requant(v, layer.m, layer.n)
            out = maxpool2x2(y)
        else:
            acc = flatten_chw(x) @ layer.w.T
            logits = acc + layer.b
            y, out = None, logits
        if records is not None:
            records.append(LayerTrace(x, acc, y, out))
        x = out
    pred = argmax_first(logits)
    return GoldenResult(logits, int(pred) if np.ndim(pred) == 0 else pred, records)
