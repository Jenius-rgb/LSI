"""Validation mode (official requirement): classify every image in a folder.

Layout: <folder>/<class_name>/<images> gives accuracy; plain <folder>/<images> only timing.
Reports FPGA computation time and end-to-end time separately (SPEC 15).
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from sentinel.preprocess import read_image_file

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp"}


def collect(folder: Path) -> tuple[list[tuple[Path, int | None]], list[str]]:
    classes = sorted(p.name for p in folder.iterdir() if p.is_dir())
    if classes:
        items = [(f, label) for label, c in enumerate(classes) for f in sorted((folder / c).iterdir()) if f.suffix.lower() in IMAGE_SUFFIXES]
    else:
        items = [(f, None) for f in sorted(folder.iterdir()) if f.suffix.lower() in IMAGE_SUFFIXES]
    return items, classes


def run(backend, folder: Path, class_names: list[str] | None = None) -> dict:
    items, classes = collect(folder)
    if not items:
        raise ValueError(f"no images in {folder}")
    correct = labelled = 0
    fpga_total = wall_total = 0.0
    per_image = []
    for index, (path, label) in enumerate(items):
        start = time.perf_counter()
        image = read_image_file(path)
        result = backend.classify(image, image_id=index)
        elapsed = time.perf_counter() - start
        wall_total += elapsed
        fpga_total += result.fpga_time_s
        if label is not None:
            labelled += 1
            correct += int(result.pred == label)
        per_image.append({"file": str(path), "pred": result.pred, "label": label, "fpga_ms": result.fpga_time_s * 1e3, "end_to_end_ms": elapsed * 1e3})
    n = len(items)
    return {
        "images": n,
        "accuracy": correct / labelled if labelled else None,
        "classes": class_names or classes,
        "fpga_latency_ms_mean": fpga_total / n * 1e3,
        "end_to_end_latency_ms_mean": wall_total / n * 1e3,
        "fps_end_to_end": n / wall_total if wall_total else 0.0,
        "per_image": per_image,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--model", default="xs")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    from sentinel.harness import make_backend

    backend, _ = make_backend(args.model)
    report = run(backend, args.folder)
    label = "[SYNTHETIC]" if backend.name == "mock" else "[HW]"
    print(f"{label} images={report['images']} accuracy={report['accuracy']} fpga_ms={report['fpga_latency_ms_mean']:.2f} end_to_end_ms={report['end_to_end_latency_ms_mean']:.2f} fps={report['fps_end_to_end']:.1f}")
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
