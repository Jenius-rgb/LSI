"""E4: the three modes compared: throughput and correctness against frequency."""
from __future__ import annotations

import argparse

import numpy as np

from sentinel.harness import make_backend, new_run_dir, test_images, write_csv, write_metadata

MODE_NAMES = {0: "unprotected", 1: "detect_recompute", 2: "correct"}


def run(backend, images, f_list: list[float]) -> list[dict]:
    golden = [backend.golden(img) for img in images]
    rows = []
    for mode in (0, 1, 2):
        for f in f_list:
            backend.set_mode(mode)
            backend.set_frequency(f)
            total_time, exact, fatal, recomputed = 0.0, 0, 0, 0
            for image_id, image in enumerate(images):
                res = backend.classify(image, image_id=image_id)
                total_time += res.fpga_time_s
                exact += int(np.array_equal(np.array(res.logits), golden[image_id].logits))
                fatal += int(res.fatal)
                recomputed += sum(res.recompute)
            rows.append(
                {
                    "mode": MODE_NAMES[mode], "f_mhz": f, "images": len(images),
                    "bit_exact_images": exact, "bit_exact_fraction": exact / len(images),
                    "fatal_images": fatal, "units_recomputed": recomputed,
                    "images_per_s": len(images) / total_time if total_time else 0.0,
                }
            )
    return rows


def summary(rows: list[dict]) -> dict:
    """Highest throughput per mode among frequencies where every image stayed bit-exact."""
    out = {}
    for mode in MODE_NAMES.values():
        exact = [r for r in rows if r["mode"] == mode and r["bit_exact_fraction"] == 1.0]
        out[mode] = max((r["images_per_s"] for r in exact), default=None)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", type=int, default=6)
    parser.add_argument("--model", default="xs")
    args = parser.parse_args()
    backend, weights = make_backend(args.model)
    images, source = test_images(args.images)
    rows = run(backend, images, [120.0 + i * 15.0 for i in range(10)])
    out = new_run_dir(backend.name, "e4")
    write_csv(out / "data.csv", rows)
    write_metadata(out, "e4", backend, {"weights": weights, "images": source, "best_bit_exact_throughput": summary(rows)})
    print(f"[SYNTHETIC] E4 wrote {out}" if backend.name == "mock" else f"E4 wrote {out}")


if __name__ == "__main__":
    main()
