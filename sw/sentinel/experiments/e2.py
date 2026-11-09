"""E2: are errors deterministic? Repeats the same images at a fixed frequency (H2)."""
from __future__ import annotations

import argparse

from sentinel.harness import make_backend, new_run_dir, test_images, write_csv, write_metadata


def run(backend, images, f_mhz: float, repeats: int) -> list[dict]:
    backend.set_frequency(f_mhz)
    backend.set_mode(2)
    rows = []
    for image_id, image in enumerate(images):
        patterns = []
        for _ in range(repeats):
            res = backend.classify(image, image_id=image_id)
            patterns.append(tuple(sorted((e["layer"], e["unit"], e["lane"], e["bit"]) for e in res.events)))
        identical = sum(1 for p in patterns if p == patterns[0])
        rows.append({"image": image_id, "f_mhz": f_mhz, "repeats": repeats, "identical_to_first": identical, "events_first": len(patterns[0])})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", type=int, default=6)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--f", type=float, default=200.0)
    parser.add_argument("--model", default="xs")
    args = parser.parse_args()
    backend, weights = make_backend(args.model)
    images, source = test_images(args.images)
    rows = run(backend, images, args.f, args.repeats)
    out = new_run_dir(backend.name, "e2")
    write_csv(out / "data.csv", rows)
    rate = sum(r["identical_to_first"] for r in rows) / sum(r["repeats"] for r in rows)
    write_metadata(out, "e2", backend, {"weights": weights, "images": source, "repeat_identity_rate": rate, "criterion": 0.95})
    print(f"[SYNTHETIC] E2 wrote {out}" if backend.name == "mock" else f"E2 wrote {out}")


if __name__ == "__main__":
    main()
