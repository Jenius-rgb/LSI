"""Camera-style robustness of a quantised model (ADR-040).

The contest validation images come from a camera or an SD card on the contest day [OFFICIAL], not from CIFAR-10. This
module distorts the test images in ways a camera does (exposure, contrast, sensor noise, defocus, white balance, low
resolution, compression, framing) and measures the accuracy of the integer golden model on each. Every distortion is
deterministic (fixed seed). "jpeg" and "zoom" are held out: the camera-style training augmentation of ADR-040 does not
use them, so they show whether robustness carries over to distortions the model never saw. Results are [SIM].

    python -m model.robustness --model s4
"""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path

import numpy as np

from model.golden import QModel, forward

ROOT = Path(__file__).resolve().parents[1]

TRAINED_KINDS = ("dark", "bright", "low_contrast", "noise", "blur", "warm", "cool", "low_res")
HELD_OUT = ("jpeg", "zoom")


def _clip(x: np.ndarray) -> np.ndarray:
    return np.clip(np.rint(x), 0, 255).astype(np.uint8)


def _blur(x: np.ndarray) -> np.ndarray:
    """Separable [1, 2, 1] / 4 filter, applied twice (about sigma 1 pixel), edges replicated."""
    y = x.astype(np.float64)
    for _ in range(2):
        for axis in (2, 3):
            pad = [(0, 0)] * 4
            pad[axis] = (1, 1)
            p = np.pad(y, pad, mode="edge")
            a = np.take(p, range(0, p.shape[axis] - 2), axis=axis)
            b = np.take(p, range(1, p.shape[axis] - 1), axis=axis)
            c = np.take(p, range(2, p.shape[axis]), axis=axis)
            y = (a + 2 * b + c) / 4
    return _clip(y)


def _pil_each(x: np.ndarray, fn) -> np.ndarray:
    from PIL import Image

    out = np.empty_like(x)
    for i, img in enumerate(x):
        pil = Image.fromarray(np.transpose(img, (1, 2, 0)))
        out[i] = np.transpose(np.asarray(fn(pil), dtype=np.uint8), (2, 0, 1))
    return out


def _jpeg(pil):
    from PIL import Image

    buf = io.BytesIO()
    pil.save(buf, format="JPEG", quality=25)
    return Image.open(io.BytesIO(buf.getvalue())).convert("RGB")


def _zoom(pil):
    from PIL import Image

    w, h = pil.size
    m = round(w * 0.1)                     # keep the central 80 %: the object fills more of the frame
    return pil.crop((m, m, w - m, h - m)).resize((w, h), Image.BILINEAR)


def _gain(x: np.ndarray, rgb: tuple[float, float, float]) -> np.ndarray:
    return _clip(x.astype(np.float64) * np.asarray(rgb)[None, :, None, None])


def _low_contrast(x: np.ndarray) -> np.ndarray:
    y = x.astype(np.float64)
    mean = y.mean(axis=(1, 2, 3), keepdims=True)
    return _clip((y - mean) * 0.5 + mean)


def _low_res(x: np.ndarray) -> np.ndarray:
    n, c, h, w = x.shape
    small = x.astype(np.float64).reshape(n, c, h // 2, 2, w // 2, 2).mean(axis=(3, 5))
    return _clip(small.repeat(2, axis=2).repeat(2, axis=3))


CORRUPTIONS = {
    "clean": lambda x, rng: x.copy(),
    "dark": lambda x, rng: _clip(x.astype(np.float64) * 0.55),
    "bright": lambda x, rng: _clip(x.astype(np.float64) + 60),
    "low_contrast": lambda x, rng: _low_contrast(x),
    "noise": lambda x, rng: _clip(x.astype(np.float64) + rng.normal(0.0, 12.0, size=x.shape)),
    "blur": lambda x, rng: _blur(x),
    "warm": lambda x, rng: _gain(x, (1.2, 1.0, 0.8)),
    "cool": lambda x, rng: _gain(x, (0.8, 1.0, 1.2)),
    "low_res": lambda x, rng: _low_res(x),
    "jpeg": lambda x, rng: _pil_each(x, _jpeg),
    "zoom": lambda x, rng: _pil_each(x, _zoom),
}


def apply(name: str, images: np.ndarray, seed: int = 2027) -> np.ndarray:
    """Distort uint8 images of shape (N, 3, H, W); the same seed gives the same result."""
    return CORRUPTIONS[name](np.asarray(images, dtype=np.uint8), np.random.default_rng(seed))


def confusion(labels: np.ndarray, pred: np.ndarray, n_classes: int) -> np.ndarray:
    """Rows: true class, columns: predicted class."""
    m = np.zeros((n_classes, n_classes), dtype=np.int64)
    np.add.at(m, (np.asarray(labels), np.asarray(pred)), 1)
    return m


def predict(qm: QModel, images: np.ndarray, batch: int = 500) -> np.ndarray:
    return np.concatenate([np.atleast_1d(forward(qm, images[i : i + batch].astype(np.int64)).pred) for i in range(0, len(images), batch)])


def report(model: str, images: int | None = None, seed: int = 2027) -> dict:
    from model.config import load_model_config
    from model.data import load_dataset

    cfg = load_model_config(model)
    dataset = cfg.get("dataset", "cifar10")
    qm = QModel.load(ROOT / "results" / "model" / model / "quant.npz")
    _, test = load_dataset(dataset)
    x, y = test.images[:images] if images else test.images, test.labels[:images] if images else test.labels
    n_classes = int(qm.layers[-1].w.shape[0])
    acc, matrices = {}, {}
    for name in CORRUPTIONS:
        pred = predict(qm, apply(name, x, seed))
        acc[name] = float((pred == y).mean())
        matrices[name] = confusion(y, pred, n_classes).tolist()
    mean = lambda names: float(np.mean([acc[n] for n in names]))  # noqa: E731
    clean_m = np.asarray(matrices["clean"])
    return {
        "label": "[SIM]", "model": model, "dataset": dataset, "images": int(len(x)), "seed": seed,
        "images_source": f"{dataset} test set, first {len(x)} images", "classes": list(test.classes),
        "accuracy": acc,
        "mean_trained_kinds": mean(TRAINED_KINDS), "mean_held_out": mean(HELD_OUT),
        "mean_all_distortions": mean(TRAINED_KINDS + HELD_OUT),
        "per_class_clean": (np.diag(clean_m) / clean_m.sum(axis=1)).round(4).tolist(),
        "confusion_clean": matrices["clean"],
        "confusion": matrices,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", default="s4")
    ap.add_argument("--images", type=int, default=None, help="default: the whole test set")
    args = ap.parse_args()
    rep = report(args.model, args.images)
    out = ROOT / "results" / "model" / args.model / "robustness.json"
    out.write_text(json.dumps(rep, indent=1) + "\n", encoding="utf-8", newline="\n")
    for name, value in rep["accuracy"].items():
        print(f"[SIM] {args.model} {name:12s} {100 * value:5.1f} %")
    print(f"[SIM] mean trained kinds {100 * rep['mean_trained_kinds']:.1f} %, held out {100 * rep['mean_held_out']:.1f} %, "
          f"all distortions {100 * rep['mean_all_distortions']:.1f} %; per class (clean) {rep['per_class_clean']}; "
          f"written {out.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
