"""E7: bit-exact check on a validation set, per image against the golden model."""
from __future__ import annotations

import argparse

import numpy as np

from sentinel.harness import make_backend, new_run_dir, test_images, write_csv, write_metadata


def run(backend, images, labels=None) -> list[dict]:
    backend.set_mode(2)
    backend.set_frequency(backend.f_safe)
    rows = []
    for image_id, image in enumerate(images):
        gold = backend.golden(image)
        res = backend.classify(image, image_id=image_id)
        logits_match = int(np.array_equal(np.array(res.logits), gold.logits))
        rows.append({"image": image_id, "logits_match": logits_match, "class_match": int(res.pred == gold.pred), "pred": res.pred, "sdc": 1 - logits_match})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", type=int, default=50)
    parser.add_argument("--model", default="xs")
    args = parser.parse_args()
    backend, weights = make_backend(args.model)
    images, source = test_images(args.images)
    rows = run(backend, images)
    out = new_run_dir(backend.name, "e7")
    write_csv(out / "data.csv", rows)
    write_metadata(out, "e7", backend, {"weights": weights, "images": source, "bit_exact_images": sum(r["logits_match"] for r in rows), "total": len(rows)})
    print(f"[SYNTHETIC] E7 wrote {out}" if backend.name == "mock" else f"E7 wrote {out}")


if __name__ == "__main__":
    main()
