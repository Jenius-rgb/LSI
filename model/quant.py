"""Fold BatchNorm and quantise a trained float model to the integer form of SPEC section 3."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from model.config import layer_shapes
from model.golden import QLayer, QModel

BN_EPS = 1e-5  # torch.nn.BatchNorm2d default


@dataclass
class FloatLayer:
    name: str
    kind: str
    w: np.ndarray  # conv: (Cout, Cin, 3, 3); fc: (N, N_in)
    b: np.ndarray


def fold_bn(state_dict: dict, cfg: dict, n_classes: int) -> list[FloatLayer]:
    """Merge each BatchNorm into its convolution: BN(conv(x)) = conv'(x) with new w and b."""
    shapes = layer_shapes(cfg, n_classes)
    layers: list[FloatLayer] = []
    conv_idx = 0
    for shape in shapes:
        if shape.kind == "conv":
            prefix = f"blocks.{conv_idx}"
            w = state_dict[f"{prefix}.conv.weight"].cpu().numpy().astype(np.float64)
            b = state_dict[f"{prefix}.conv.bias"].cpu().numpy().astype(np.float64)
            gamma = state_dict[f"{prefix}.bn.weight"].cpu().numpy().astype(np.float64)
            beta = state_dict[f"{prefix}.bn.bias"].cpu().numpy().astype(np.float64)
            mean = state_dict[f"{prefix}.bn.running_mean"].cpu().numpy().astype(np.float64)
            var = state_dict[f"{prefix}.bn.running_var"].cpu().numpy().astype(np.float64)
            factor = gamma / np.sqrt(var + BN_EPS)
            layers.append(FloatLayer(shape.name, "conv", w * factor[:, None, None, None], (b - mean) * factor + beta))
            conv_idx += 1
        else:
            layers.append(
                FloatLayer(
                    shape.name, "fc",
                    state_dict["fc.weight"].cpu().numpy().astype(np.float64),
                    state_dict["fc.bias"].cpu().numpy().astype(np.float64),
                )
            )
    return layers


def float_forward(layers: list[FloatLayer], images_u8: np.ndarray, collect: bool = False):
    """Run the folded float network; optionally return post-pool activations per conv layer."""
    import torch
    import torch.nn.functional as F

    x = torch.from_numpy(images_u8.astype(np.float32) / 255.0).double()
    activations: list[np.ndarray] = []
    for layer in layers:
        if layer.kind == "conv":
            x = F.relu(F.conv2d(x, torch.from_numpy(layer.w), torch.from_numpy(layer.b), padding=1))
            x = F.max_pool2d(x, 2)
            if collect:
                activations.append(x.numpy())
        else:
            x = torch.flatten(x, 1) @ torch.from_numpy(layer.w).T + torch.from_numpy(layer.b)
    return (x.numpy(), activations) if collect else x.numpy()


def choose_m_n(ratio: float) -> tuple[int, int]:
    """SPEC 4: the largest n in 0..31 such that M = round(ratio * 2^n) <= 65535."""
    if ratio <= 0:
        raise ValueError(f"non-positive requant ratio: {ratio}")
    best = None
    for n in range(32):
        m = int(np.round(ratio * 2.0**n))
        if m > 65535:
            break
        if m >= 1:
            best = (m, n)
    if best is None:
        raise ValueError(f"requant ratio cannot be represented: {ratio}")
    return best


def quantize(layers: list[FloatLayer], calib_images: np.ndarray, name: str, in_shape: tuple[int, int, int], percentile: float = 99.99) -> tuple[QModel, list[dict]]:
    """Post-training quantisation (SPEC 4): S_out from a high percentile of the activations."""
    _, activations = float_forward(layers, calib_images, collect=True)
    s_out = [float(np.percentile(a, percentile)) / 255.0 for a in activations]

    s_in = 1.0 / 255.0
    qlayers: list[QLayer] = []
    info: list[dict] = []
    for idx, layer in enumerate(layers):
        s_w = float(np.max(np.abs(layer.w))) / 127.0
        w_int = np.clip(np.round(layer.w / s_w), -127, 127).astype(np.int64)
        b_int = np.round(layer.b / (s_in * s_w)).astype(np.int64)
        if layer.kind == "conv":
            ratio = s_in * s_w / s_out[idx]
            m, n = choose_m_n(ratio)
            qlayers.append(QLayer(layer.name, "conv", w_int, b_int, m, n))
            info.append({"layer": layer.name, "s_in": s_in, "s_w": s_w, "s_out": s_out[idx], "ratio": ratio, "m": m, "n": n})
            s_in = s_out[idx]
        else:
            qlayers.append(QLayer(layer.name, "fc", w_int, b_int, 0, 0))
            info.append({"layer": layer.name, "s_in": s_in, "s_w": s_w})
    return QModel(name, in_shape, qlayers), info
