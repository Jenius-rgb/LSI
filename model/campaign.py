"""Python fault-injection campaign (STATUS M3, experiment E5).

Errors are XOR masks injected into real accumulators: layers, images and weights come
from the golden model, and checksum accumulators are computed independently from the
checksum weights, not derived from the data lanes.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field

import numpy as np

from model.checker import CORRECT, Outcome, check, xor_inject
from model.config import ROOT, load_hw_config, model_names
from model.golden import QModel, conv_accumulate, flatten_chw, forward

CLASSES = ("clean", "corrected", "csum_lane", "recompute", "miscorrected", "escaped")


@dataclass
class Unit:
    y: np.ndarray  # K data lane accumulators
    s: np.ndarray  # S1, S2, S3


def _checksum_weights(w: np.ndarray, k: int) -> np.ndarray:
    """Per-group checksum weights for lanes k=1..K. Output shape (g, 3, ...weight dims)."""
    cout = w.shape[0]
    g = (cout + k - 1) // k
    padded = np.zeros((g * k, *w.shape[1:]), dtype=np.int64)
    padded[:cout] = w
    grouped = padded.reshape(g, k, *w.shape[1:])
    lane = np.arange(1, k + 1, dtype=np.int64).reshape(1, k, *([1] * (w.ndim - 1)))
    return np.stack([(grouped * lane**p).sum(axis=1) for p in (0, 1, 2)], axis=1)


class UnitPool:
    """All computing units of the given images, as true lane and checksum accumulators."""

    def __init__(self, qm: QModel, images: np.ndarray, k: int):
        self.k = k
        self.layers = [layer.name for layer in qm.layers]
        self.y: dict[str, np.ndarray] = {}
        self.s: dict[str, np.ndarray] = {}
        self.identity_violations = 0
        trace = forward(qm, images, trace=True).trace
        for layer, tr in zip(qm.layers, trace):
            wc = _checksum_weights(layer.w, k)  # (g, 3, ...)
            g = wc.shape[0]
            cout = layer.w.shape[0]
            if layer.kind == "conv":
                b, _, h, width = tr.acc.shape
                padded = np.zeros((b, g * k, h, width), dtype=np.int64)
                padded[:, :cout] = tr.acc
                # y: (image, y, x, group, lane)
                y = padded.reshape(b, g, k, h, width).transpose(0, 3, 4, 1, 2)
                s = np.stack([conv_accumulate(wc[:, p], tr.input) for p in range(3)], axis=-1)
                # conv_accumulate returns (B, G, H, W); s: (image, y, x, group, 3)
                s = s.transpose(0, 2, 3, 1, 4)
            else:
                b, n = tr.acc.shape
                padded = np.zeros((b, g * k), dtype=np.int64)
                padded[:, :cout] = tr.acc
                y = padded.reshape(b, 1, 1, g, k)
                a = flatten_chw(tr.input)  # (B, N_in)
                s = np.stack([a @ wc[:, p].T for p in range(3)], axis=-1)  # (B, g, 3)
                s = s.reshape(b, 1, 1, g, 3)
            lane = np.arange(1, k + 1, dtype=np.int64)
            expected = np.stack([(y * lane**p).sum(axis=-1) for p in (0, 1, 2)], axis=-1)
            self.identity_violations += int((expected != s).sum())
            self.y[layer.name] = y
            self.s[layer.name] = s

    def count(self, layer: str) -> int:
        return int(np.prod(self.y[layer].shape[:4]))

    def unit(self, layer: str, image: int, position: tuple[int, int], group: int) -> Unit:
        y, x = position
        return Unit(self.y[layer][image, y, x, group], self.s[layer][image, y, x, group])

    def sample(self, rng: np.random.Generator) -> tuple[str, Unit]:
        """Pick a layer uniformly, then a unit uniformly inside it."""
        layer = self.layers[int(rng.integers(len(self.layers)))]
        shape = self.y[layer].shape
        idx = tuple(int(rng.integers(n)) for n in shape[:4])
        return layer, Unit(self.y[layer][idx], self.s[layer][idx])


def classify(outcome: Outcome, final_y: list[int], true_y: list[int]) -> str:
    correct = list(final_y) == list(true_y)
    if outcome == Outcome.RECOMPUTE:
        return "recompute"
    if outcome == Outcome.CORRECTED:
        return "corrected" if correct else "miscorrected"
    if outcome == Outcome.CSUM_LANE:
        return "csum_lane" if correct else "escaped"
    return "clean" if correct else "escaped"


def random_mask(rng: np.random.Generator, value: int, width: int) -> int:
    """A non-zero XOR mask: one to three bits biased towards the top of the active range."""
    active = min(max(abs(int(value)).bit_length() + 1, 2), width)
    count = 1 if rng.random() < 0.7 else int(rng.integers(2, 4))
    mask = 0
    while mask == 0:
        for _ in range(count):
            u = rng.random()
            mask |= 1 << (active - 1 - int(active * u * u))
    return mask


@dataclass
class Trial:
    layer: str
    y_true: list[int]
    s_true: list[int]
    y_seen: list[int]
    s_seen: list[int]
    lanes: list[int]
    masks: list[int]
    outcome: Outcome
    lane: int
    y_out: list[int]
    d: tuple[int, int, int]
    klass: str


@dataclass
class CampaignResult:
    kind: str
    n: int
    k: int
    c3: bool
    trust: bool
    seed: int
    counts: dict = field(default_factory=dict)
    trials: list[Trial] = field(default_factory=list)


def run(pool: UnitPool, kind: str, n: int, c3: bool, trust: bool, seed: int, mode: int = CORRECT, acc_w: int = 32, cs_w: int = 48) -> CampaignResult:
    """kind: 'single' (one data lane), 'dual' (two data lanes), 'csum' (one checksum lane)."""
    rng = np.random.default_rng(seed)
    k = pool.k
    counts = dict.fromkeys(CLASSES, 0)
    trials: list[Trial] = []
    n_csum = 3 if c3 else 2
    for _ in range(n):
        layer, unit = pool.sample(rng)
        y_true = [int(v) for v in unit.y]
        s_true = [int(v) for v in unit.s]
        y_seen, s_seen = list(y_true), list(s_true)
        lanes: list[int] = []
        masks: list[int] = []
        if kind == "single":
            picks = [int(rng.integers(1, k + 1))]
        elif kind == "dual":
            picks = [int(v) + 1 for v in rng.choice(k, size=2, replace=False)]
        elif kind == "csum":
            picks = [k + int(rng.integers(1, n_csum + 1))]
        else:
            raise ValueError(kind)
        for lane in picks:
            if lane <= k:
                while True:
                    mask = random_mask(rng, y_seen[lane - 1], acc_w)
                    corrupted = xor_inject(y_seen[lane - 1], mask, acc_w)
                    if corrupted != y_seen[lane - 1]:
                        break
                y_seen[lane - 1] = corrupted
            else:
                idx = lane - k - 1
                while True:
                    mask = random_mask(rng, s_seen[idx], cs_w)
                    corrupted = xor_inject(s_seen[idx], mask, cs_w)
                    if corrupted != s_seen[idx]:
                        break
                s_seen[idx] = corrupted
            lanes.append(lane)
            masks.append(mask)
        res = check(y_seen, s_seen[0], s_seen[1], s_seen[2], mode, c3, trust)
        klass = classify(res.outcome, res.y, y_true)
        counts[klass] += 1
        trials.append(Trial(layer, y_true, s_true, y_seen, s_seen, lanes, masks, res.outcome, res.lane, res.y, (res.d1, res.d2, res.d3), klass))
    return CampaignResult(kind, n, k, c3, trust, seed, counts, trials)


def load_pool(model: str, k: int, count: int) -> tuple[UnitPool, str]:
    from model.data import verification_images

    qm_path = ROOT / "results" / "model" / model / "quant.npz"
    qm = QModel.load(qm_path)
    images, _, source = verification_images(count)
    return UnitPool(qm, images, k), source


def full_campaign(model: str, n_images: int, seed: int, sizes: dict[str, int]) -> dict:
    rows = []
    source = ""
    for k in (8, 16):
        pool, source = load_pool(model, k, n_images)
        if pool.identity_violations:
            raise RuntimeError(f"checksum identity violated {pool.identity_violations} times")
        for c3 in (False, True):
            for kind, n in sizes.items():
                res = run(pool, kind, n, c3, False, seed)
                rows.append({"k": k, "c3": int(c3), "kind": kind, "n": n, **res.counts})
                print(f"[SIM] K={k} C3={int(c3)} {kind:<6} n={n:<6} {res.counts}", flush=True)
    return {
        "label": "[SIM]",
        "note": "XOR masks injected into accumulators from the golden model; not a timing-error measurement.",
        "model": model,
        "images": n_images,
        "image_source": source,
        "seed": seed,
        "trust_csum_lane": 0,
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=load_hw_config()["MODEL"], choices=model_names())
    parser.add_argument("--images", type=int, default=50)
    parser.add_argument("--seed", type=int, default=2027)
    parser.add_argument("--single", type=int, default=10000)
    parser.add_argument("--dual", type=int, default=10000)
    parser.add_argument("--csum", type=int, default=1000)
    args = parser.parse_args()
    report = full_campaign(args.model, args.images, args.seed, {"single": args.single, "dual": args.dual, "csum": args.csum})
    out = ROOT / "results" / "sim"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"campaign_{args.model}.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
