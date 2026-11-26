"""Validation mode (official requirement): classify every image in a folder.

Layout: <folder>/<class_name>/<images> gives accuracy; plain <folder>/<images> only timing.
Labels follow the class order of the model (config/model_<name>.yaml `classes`, e.g. s4: cat, dog, deer, horse), not
the alphabetical order of the folder names; folder names are matched without regard to case.
Reports FPGA computation time and end-to-end time separately (SPEC 15).
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from sentinel.preprocess import read_image_file

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp"}


def collect(folder: Path, class_names: list[str] | None = None) -> tuple[list[tuple[Path, int | None]], list[str]]:
    dirs = sorted(p.name for p in folder.iterdir() if p.is_dir())
    if not dirs:
        return [(f, None) for f in sorted(folder.iterdir()) if f.suffix.lower() in IMAGE_SUFFIXES], []
    if class_names:
        index = {c.lower(): i for i, c in enumerate(class_names)}
        unknown = [d for d in dirs if d.lower() not in index]
        if unknown:
            raise ValueError(f"folders {unknown} are not classes of the model ({class_names})")
        labels, classes = {d: index[d.lower()] for d in dirs}, list(class_names)
    else:
        labels, classes = {d: i for i, d in enumerate(dirs)}, dirs
    items = [(f, labels[d]) for d in sorted(dirs, key=labels.get) for f in sorted((folder / d).iterdir())
             if f.suffix.lower() in IMAGE_SUFFIXES]
    return items, classes


def run(backend, folder: Path, class_names: list[str] | None = None) -> dict:
    items, classes = collect(folder, class_names)
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
        "classes": classes,
        "fpga_latency_ms_mean": fpga_total / n * 1e3,
        "end_to_end_latency_ms_mean": wall_total / n * 1e3,
        "fps_end_to_end": n / wall_total if wall_total else 0.0,
        "per_image": per_image,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--model", default="s4b", help="s4b = the four official classes with camera-style training (ADR-040)")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    from model.export import class_names
    from sentinel.harness import make_backend

    backend, _ = make_backend(args.model)
    report = run(backend, args.folder, class_names(args.model))
    label = "[SYNTHETIC]" if backend.name == "mock" else "[HW]"
    print(f"{label} images={report['images']} accuracy={report['accuracy']} fpga_ms={report['fpga_latency_ms_mean']:.2f} end_to_end_ms={report['end_to_end_latency_ms_mean']:.2f} fps={report['fps_end_to_end']:.1f}")
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
