"""Zero operands in the engine's operand stream (evaluation input for zero-activation skipping).

The engine issues one operand set per cycle: one activation byte broadcast to all lanes (SPEC 5.2), for every tap
(c, i, j) of every output position, including the zero-padded border taps, and once per lane group g (SPEC 5.3/5.4).
When that activation is zero, every data-lane product and every checksum-lane product is zero, so the cycle could be
skipped without changing any sum. This module counts how many operand sets carry a zero activation, using the golden
model on real images. Results are [SIM]: golden model, images from the configured dataset.

    python -m model.zero_taps --model s --images 1000
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from model.config import load_hw_config
from model.golden import QModel, forward

ROOT = Path(__file__).resolve().parents[1]


def conv_zero_taps(x: np.ndarray) -> tuple[int, int]:
    """(zero taps, all taps) of a 3x3 'same' convolution over x of shape (C, H, W) or (B, C, H, W)."""
    x = np.asarray(x)
    if x.ndim == 3:
        x = x[None]
    b, c, h, w = x.shape
    nonzero = np.zeros((b, h + 2, w + 2), dtype=np.int64)
    nonzero[:, 1:-1, 1:-1] = (x != 0).sum(axis=1)
    nonzero_taps = 0
    for i in range(3):
        for j in range(3):
            nonzero_taps += int(nonzero[:, i : i + h, j : j + w].sum())
    total = b * h * w * c * 9
    return total - nonzero_taps, total


def fc_zero_inputs(x: np.ndarray) -> tuple[int, int]:
    """(zero inputs, all inputs) of a fully connected layer over x of shape (N_in,) or (B, N_in)."""
    x = np.asarray(x)
    return int((x == 0).sum()), int(x.size)


def report(model: str, images: int, k: int | None = None, dataset: str = "cifar10") -> dict:
    hw = load_hw_config()
    k = int(k or hw["K"])
    qm = QModel.load(ROOT / "results" / "model" / model / "quant.npz")
    if dataset != "cifar10":
        raise ValueError("only the temporary dataset (cifar10) is wired in")
    from model.data import load_cifar10

    test = load_cifar10(train=False, download=False)
    batch = test.images[:images].astype(np.int64)
    trace = forward(qm, batch, trace=True).trace
    layers = []
    total_cycles = saved_cycles = 0
    for layer, rec in zip(qm.layers, trace):
        groups = math.ceil(layer.w.shape[0] / k)
        if layer.kind == "conv":
            zero, total = conv_zero_taps(rec.input)
        else:
            zero, total = fc_zero_inputs(rec.input.reshape(rec.input.shape[0], -1))
        per_image_total = total // images
        cycles = groups * per_image_total
        saved = groups * zero / images
        total_cycles += cycles
        saved_cycles += saved
        layers.append({
            "name": layer.name, "kind": layer.kind, "groups": groups,
            "operands_per_image": per_image_total, "zero_fraction": zero / total,
            "ideal_cycles_per_image": cycles, "zero_cycles_per_image": saved,
        })
    return {
        "label": "[SIM]", "model": model, "k": k, "images": images,
        "images_source": f"{dataset} test set, first {images} images",
        "layers": layers, "ideal_cycles_per_image": total_cycles,
        "zero_cycles_per_image": saved_cycles, "zero_cycle_fraction": saved_cycles / total_cycles,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", default="s")
    ap.add_argument("--images", type=int, default=1000)
    ap.add_argument("--k", type=int, default=None)
    args = ap.parse_args()
    rep = report(args.model, args.images, args.k)
    arch = json.loads((ROOT / "results" / "model" / f"arch_{args.model}.json").read_text(encoding="utf-8"))
    rep["ideal_cycles_arch_report"] = arch["ideal_cycles"].get(str(rep["k"]))
    out = ROOT / "results" / "model" / f"zero_taps_{args.model}_k{rep['k']}.json"
    out.write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8", newline="\n")
    for row in rep["layers"]:
        print(f"[SIM] {row['name']:6s} zero operands {100 * row['zero_fraction']:5.1f} %  "
              f"zero cycles {row['zero_cycles_per_image']:10.1f} / {row['ideal_cycles_per_image']}")
    print(f"[SIM] total zero cycles {100 * rep['zero_cycle_fraction']:.1f} % of {rep['ideal_cycles_per_image']} ideal cycles "
          f"(arch report: {rep['ideal_cycles_arch_report']}); written {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
