"""Quantise a trained model and export the hardware memory image (SPEC 3.6, 4).

The memory image is byte-for-byte what the RTL holds:

* weights: K-byte words, word = wbase + g*T + t, lane k in byte k of the word;
* params: 32-bit words holding the bias table, then at LAYER_TABLE_INDEX the layer records.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from model.config import ROOT, load_hw_config, load_model_config
from model.golden import QModel, forward

# Activation buffer selectors used in the layer table.
SRC_IMG = 0
BUF_ACT0 = 1
BUF_ACT1 = 2

RECORD_WORDS = 8
LAYER_TABLE_INDEX = 256  # word index of the first layer record in the params memory
MAX_LAYERS = 8
PARAM_WORDS = LAYER_TABLE_INDEX + RECORD_WORDS * MAX_LAYERS
DEFAULT_PROD_W = 50


class BitBoundError(ValueError):
    """A value could overflow the width the RTL uses (SPEC 3.6)."""


@dataclass
class MemoryImage:
    weights: np.ndarray  # (words, K) int8-valued
    bias: np.ndarray  # int32-valued, one entry per lane per group
    records: list[dict]
    k: int

    def record_words(self) -> list[list[int]]:
        return [pack_record(r) for r in self.records]

    def params(self) -> list[int]:
        """The whole params memory as unsigned 32-bit words."""
        words = [int(b) & 0xFFFFFFFF for b in self.bias]
        if len(words) > LAYER_TABLE_INDEX:
            raise BitBoundError(f"bias table needs {len(words)} words, only {LAYER_TABLE_INDEX} available")
        words += [0] * (LAYER_TABLE_INDEX - len(words))
        for rec in self.record_words():
            words += rec
        return words


def pack_record(r: dict) -> list[int]:
    """Layer record layout. Normative for rtl/engine.v."""
    return [
        (r["kind"] & 1) | ((r["src_sel"] & 3) << 2) | ((r["dst_sel"] & 3) << 4) | ((r["log2w"] & 15) << 8),
        (r["cin"] & 0xFFFF) | ((r["cout"] & 0xFFFF) << 16),
        r["n_in"] & 0xFFFFFFFF,
        (r["t"] & 0xFFFF) | ((r["g"] & 0xFFFF) << 16),
        r["wbase"] & 0xFFFFFFFF,
        r["bbase"] & 0xFFFFFFFF,
        (r["src_base"] & 0xFFFF) | ((r["dst_base"] & 0xFFFF) << 16),
        (r["m"] & 0xFFFF) | ((r["n"] & 0x1F) << 16),
    ]


def unpack_record(w: list[int]) -> dict:
    return {
        "kind": w[0] & 1,
        "src_sel": (w[0] >> 2) & 3,
        "dst_sel": (w[0] >> 4) & 3,
        "log2w": (w[0] >> 8) & 15,
        "cin": w[1] & 0xFFFF,
        "cout": w[1] >> 16,
        "n_in": w[2],
        "t": w[3] & 0xFFFF,
        "g": w[3] >> 16,
        "wbase": w[4],
        "bbase": w[5],
        "src_base": w[6] & 0xFFFF,
        "dst_base": w[6] >> 16,
        "m": w[7] & 0xFFFF,
        "n": (w[7] >> 16) & 0x1F,
    }


def _log2_exact(v: int) -> int:
    if v <= 0 or v & (v - 1):
        raise BitBoundError(f"{v} is not a power of two")
    return v.bit_length() - 1


def _allocate_buffers(qm: QModel) -> list[dict]:
    """Assign layer outputs to two activation buffers.

    A layer must not read and write the same buffer: both RAM ports serve operand reads.
    Conv outputs alternate between ACT0 and ACT1, each one placed after earlier ones.
    """
    used = {BUF_ACT0: 0, BUF_ACT1: 0}
    placement: list[dict] = []
    channels, height, width = qm.in_shape
    src_sel, src_base = SRC_IMG, 0
    next_dst = BUF_ACT0
    for layer in qm.layers:
        entry = {"src_sel": src_sel, "src_base": src_base, "dst_sel": 0, "dst_base": 0, "h": height, "w": width, "c": channels}
        if layer.kind == "conv":
            channels, height, width = layer.w.shape[0], height // 2, width // 2
            entry["dst_sel"], entry["dst_base"] = next_dst, used[next_dst]
            used[next_dst] += channels * height * width
            src_sel, src_base = entry["dst_sel"], entry["dst_base"]
            next_dst = BUF_ACT1 if next_dst == BUF_ACT0 else BUF_ACT0
        placement.append(entry)
    return placement


def buffer_sizes(qm: QModel) -> dict:
    """Bytes needed per activation buffer."""
    placement = _allocate_buffers(qm)
    sizes = {BUF_ACT0: 0, BUF_ACT1: 0}
    channels, height, width = qm.in_shape
    for layer, entry in zip(qm.layers, placement):
        if layer.kind == "conv":
            channels, height, width = layer.w.shape[0], height // 2, width // 2
            sizes[entry["dst_sel"]] = max(sizes[entry["dst_sel"]], entry["dst_base"] + channels * height * width)
    return sizes


def memory_image(qm: QModel, hw: dict) -> MemoryImage:
    k = hw["K"]
    words: list[np.ndarray] = []
    bias: list[np.ndarray] = []
    records: list[dict] = []
    placement = _allocate_buffers(qm)
    wbase = bbase = 0
    for layer, place in zip(qm.layers, placement):
        cout = layer.w.shape[0]
        g = (cout + k - 1) // k
        if layer.kind == "conv":
            cin = layer.w.shape[1]
            t = cin * 9
            flat = layer.w.reshape(cout, t)
            if place["h"] != place["w"]:
                raise BitBoundError("hardware addressing requires square activations")
            log2w = _log2_exact(place["w"])
            n_in = 0
        else:
            cin = 0
            flat = layer.w
            t = flat.shape[1]
            log2w = 0
            n_in = t
        padded = np.zeros((g * k, t), dtype=np.int64)
        padded[:cout] = flat
        # (groups, T, K): lane k of word (g, t) is padded[g*K+k, t]
        words.append(padded.reshape(g, k, t).transpose(0, 2, 1).reshape(-1, k))
        pad_bias = np.zeros(g * k, dtype=np.int64)
        pad_bias[:cout] = layer.b
        bias.append(pad_bias)
        records.append(
            {
                "kind": 0 if layer.kind == "conv" else 1,
                "src_sel": place["src_sel"], "dst_sel": place["dst_sel"], "log2w": log2w,
                "cin": cin, "cout": cout, "n_in": n_in, "t": t, "g": g,
                "wbase": wbase, "bbase": bbase,
                "src_base": place["src_base"], "dst_base": place["dst_base"],
                "m": layer.m, "n": layer.n,
            }
        )
        wbase += g * t
        bbase += g * k
    if len(records) > MAX_LAYERS:
        raise BitBoundError(f"{len(records)} layers exceed MAX_LAYERS={MAX_LAYERS}")
    return MemoryImage(np.concatenate(words), np.concatenate(bias), records, k)


def check_bit_bounds(qm: QModel, hw: dict) -> list[dict]:
    """SPEC 3.6: assert worst-case bounds for the actual weights. Returns the per-layer report."""
    k = hw["K"]
    acc_limit = 2 ** (hw["ACC_W"] - 1) - 1
    cs_limit = 2 ** (hw["ACC_CS_W"] - 1) - 1
    prod_w = hw.get("PROD_W", DEFAULT_PROD_W)
    prod_limit = 2 ** (prod_w - 1) - 1
    act_max = 2 ** hw["ACT_W"] - 1
    report = []
    for layer in qm.layers:
        w = layer.w.reshape(layer.w.shape[0], -1)
        if w.min() < -127 or w.max() > 127:
            raise BitBoundError(f"{layer.name}: weight outside -127..127")
        if layer.b.min() < -(2**31) or layer.b.max() > 2**31 - 1:
            raise BitBoundError(f"{layer.name}: bias outside int32")
        acc_max = int(np.abs(w).sum(axis=1).max()) * act_max
        if acc_max > acc_limit:
            raise BitBoundError(f"{layer.name}: |acc| {acc_max} exceeds {acc_limit} (ACC_W={hw['ACC_W']})")

        cout, t = w.shape
        g = (cout + k - 1) // k
        padded = np.zeros((g * k, t), dtype=np.int64)
        padded[:cout] = w
        groups = padded.reshape(g, k, t)  # (g, k, t)
        lane = np.arange(1, k + 1, dtype=np.int64)[None, :, None]
        wc = [(groups * lane**p).sum(axis=1) for p in (0, 1, 2)]  # each (g, t)
        cs_max = [int(np.abs(x).sum(axis=1).max()) * act_max for x in wc]
        if max(cs_max) > cs_limit:
            raise BitBoundError(f"{layer.name}: |S_c| {max(cs_max)} exceeds {cs_limit} (ACC_CS_W={hw['ACC_CS_W']})")

        v_max = acc_max + int(np.abs(layer.b).max())
        prod_max = v_max * layer.m + (1 << (layer.n - 1) if layer.n else 0)
        if prod_max > prod_limit:
            raise BitBoundError(f"{layer.name}: |v*M| {prod_max} exceeds {prod_limit} (PROD_W={prod_w})")
        report.append({"layer": layer.name, "acc_max": acc_max, "cs_max": cs_max, "v_max": v_max, "prod_max": prod_max})
    return report


def write_artifacts(qm: QModel, hw: dict, out_dir: Path) -> dict:
    """Write .bin, .mem and manifest. Output depends only on the inputs (no timestamps)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    bounds = check_bit_bounds(qm, hw)
    img = memory_image(qm, hw)
    stem = f"{qm.name}_k{img.k}"

    weight_bytes = (img.weights & 0xFF).astype(np.uint8).tobytes()
    params = img.params()
    param_bytes = b"".join(int(p).to_bytes(4, "little") for p in params)
    (out_dir / f"{stem}.bin").write_bytes(weight_bytes + param_bytes)

    with open(out_dir / f"{stem}_weights.mem", "w", newline="\n", encoding="ascii") as fh:
        for word in img.weights.tolist():
            fh.write("".join(f"{v & 0xFF:02x}" for v in reversed(word)) + "\n")
    with open(out_dir / f"{stem}_params.mem", "w", newline="\n", encoding="ascii") as fh:
        for word in params:
            fh.write(f"{word:08x}\n")

    manifest = {
        "model": qm.name,
        "classes": class_names(qm.name),
        "K": img.k,
        "n_layers": len(img.records),
        "n_classes": int(qm.layers[-1].w.shape[0]),
        "weight_words": int(img.weights.shape[0]),
        "weight_bytes": len(weight_bytes),
        "param_words": len(params),
        "layer_table_index": LAYER_TABLE_INDEX,
        "buffer_bytes": {"act0": buffer_sizes(qm)[BUF_ACT0], "act1": buffer_sizes(qm)[BUF_ACT1]},
        "records": img.records,
        "bit_bounds": bounds,
        "sha256": hashlib.sha256(weight_bytes + param_bytes).hexdigest(),
    }
    (out_dir / f"{stem}.manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return manifest


def class_names(model: str) -> list[str] | None:
    """Class names in label order from config/model_<model>.yaml, or None if the config lists none (ADR-037)."""
    from model.config import CONFIG_DIR, load_yaml

    path = CONFIG_DIR / f"model_{model}.yaml"
    return list(load_yaml(path).get("classes") or []) or None if path.exists() else None


def integer_accuracy(qm: QModel, images: np.ndarray, labels: np.ndarray, batch: int = 256) -> float:
    correct = 0
    for i in range(0, len(images), batch):
        correct += int((np.atleast_1d(forward(qm, images[i : i + batch]).pred) == labels[i : i + batch]).sum())
    return correct / len(images)


def quantize_and_evaluate(model: str, dataset: str, data_dir: str | None, calib_count: int, seed: int, out_dir: Path) -> QModel:
    import torch

    from model.arch import SentinelNet
    from model.data import load_dataset
    from model.quant import float_forward, fold_bn, quantize
    from model.train import accuracy as float_accuracy

    ckpt = torch.load(out_dir / "float.pt", map_location="cpu", weights_only=False)
    cfg = load_model_config(model)
    train_set, test_set = load_dataset(dataset, data_dir)
    n_classes = ckpt["n_classes"]

    rng = np.random.default_rng(seed)
    calib_idx = rng.choice(len(train_set.images), size=min(calib_count, len(train_set.images)), replace=False)
    folded = fold_bn(ckpt["state_dict"], cfg, n_classes)
    in_shape = (cfg["input"]["channels"], cfg["input"]["height"], cfg["input"]["width"])
    qm, info = quantize(folded, train_set.images[calib_idx], model, in_shape)

    net = SentinelNet(cfg, n_classes, 0.0)
    net.load_state_dict(ckpt["state_dict"])
    float_acc = float_accuracy(net, test_set.images, test_set.labels, torch.device("cpu"))
    folded_acc = float((float_forward(folded, test_set.images).argmax(1) == test_set.labels).mean())
    int_acc = integer_accuracy(qm, test_set.images, test_set.labels)

    qm.save(out_dir / "quant.npz")
    result = {
        "label": "[SIM]",
        "model": model,
        "dataset": dataset,
        "method": "PTQ per-tensor, S_out = p99.99/255",
        "calib_images": int(len(calib_idx)),
        "calib_seed": seed,
        "test_size": int(len(test_set.images)),
        "test_acc_float": float_acc,
        "test_acc_folded": folded_acc,
        "test_acc_integer": int_acc,
        "drop_points": (float_acc - int_acc) * 100,
        "layers": info,
    }
    (out_dir / "quant_result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"[SIM] {model}: float {float_acc:.4f} folded {folded_acc:.4f} integer {int_acc:.4f} (drop {result['drop_points']:.2f} points)")
    return qm


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, choices=["s", "s4", "xs"])
    parser.add_argument("--dataset", default=None, choices=["cifar10", "cifar10_4", "folder"],
                        help="default: the dataset in the model config, else cifar10")
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--calib-count", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=2027)
    parser.add_argument("--k", type=int, nargs="+", default=[8, 16])
    parser.add_argument("--from-quant", action="store_true", help="skip quantisation; reuse results/model/<m>/quant.npz")
    args = parser.parse_args()

    from model.config import load_model_config

    args.dataset = args.dataset or load_model_config(args.model).get("dataset", "cifar10")
    result_dir = ROOT / "results" / "model" / args.model
    if args.from_quant:
        qm = QModel.load(result_dir / "quant.npz")
    else:
        qm = quantize_and_evaluate(args.model, args.dataset, args.data_dir, args.calib_count, args.seed, result_dir)
    hw = load_hw_config()
    for k in args.k:
        manifest = write_artifacts(qm, {**hw, "K": k}, ROOT / "build" / "weights")
        print(f"exported {qm.name} K={k}: {manifest['weight_bytes']} weight bytes, sha256 {manifest['sha256'][:16]}")


if __name__ == "__main__":
    main()
