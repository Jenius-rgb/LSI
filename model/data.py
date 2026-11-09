"""Dataset access as raw uint8 tensors in (N, C, H, W) order.

Supports CIFAR-10 and any ImageFolder-style directory tree, so the model can be
retrained as soon as the organisers announce the target classes.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from model.config import ROOT

DATA_ROOT = ROOT / "data"


@dataclass
class ImageSet:
    images: np.ndarray  # (N, C, H, W) uint8
    labels: np.ndarray  # (N,) int64
    classes: list[str]


def load_cifar10(train: bool, root: Path = DATA_ROOT, download: bool = True) -> ImageSet:
    from torchvision.datasets import CIFAR10

    ds = CIFAR10(root=str(root), train=train, download=download)
    images = np.transpose(np.asarray(ds.data, dtype=np.uint8), (0, 3, 1, 2))
    return ImageSet(images, np.asarray(ds.targets, dtype=np.int64), list(ds.classes))


def _load_rgb_32(path: Path) -> np.ndarray:
    """Centre-crop to a square, area-resize to 32x32 and return (C, H, W) uint8."""
    from PIL import Image

    with Image.open(path) as img:
        img = img.convert("RGB")
        side = min(img.size)
        left, top = (img.width - side) // 2, (img.height - side) // 2
        img = img.crop((left, top, left + side, top + side)).resize((32, 32), Image.Resampling.BOX)
        return np.transpose(np.asarray(img, dtype=np.uint8), (2, 0, 1))


def load_image_folder(root: Path) -> ImageSet:
    """Read <root>/<class_name>/<image files>. Classes are in sorted order."""
    root = Path(root)
    classes = sorted(p.name for p in root.iterdir() if p.is_dir())
    if not classes:
        raise ValueError(f"no class folders under {root}")
    images, labels = [], []
    for label, name in enumerate(classes):
        for path in sorted((root / name).iterdir()):
            if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp"}:
                images.append(_load_rgb_32(path))
                labels.append(label)
    if not images:
        raise ValueError(f"no images under {root}")
    return ImageSet(np.stack(images), np.asarray(labels, dtype=np.int64), classes)


def load_dataset(name: str, data_dir: str | None = None) -> tuple[ImageSet, ImageSet]:
    """Return (train, test). For a folder dataset expects <data_dir>/train and <data_dir>/val."""
    if name == "cifar10":
        return load_cifar10(True), load_cifar10(False)
    if name == "folder":
        if not data_dir:
            raise ValueError("--data-dir is required for a folder dataset")
        return load_image_folder(Path(data_dir) / "train"), load_image_folder(Path(data_dir) / "val")
    raise ValueError(f"unknown dataset: {name}")


def verification_images(count: int, seed: int = 2027) -> tuple[np.ndarray, np.ndarray | None, str]:
    """Images for verification vectors: real CIFAR-10 test images when available.

    Falls back to seeded pseudo-random images, reported in the third return value, so
    the RTL flow never depends on the dataset being present.
    """
    try:
        ds = load_cifar10(False, download=False)
    except (ImportError, RuntimeError):
        rng = np.random.default_rng(seed)
        images = rng.integers(0, 256, size=(count, 3, 32, 32), dtype=np.uint8)
        return images, None, f"synthetic(seed={seed})"
    return ds.images[:count], ds.labels[:count], "cifar10-test"
