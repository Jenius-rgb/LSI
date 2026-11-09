"""E3: error onset per layer (H3)."""
from __future__ import annotations

import argparse

from model.fault_model import FaultParams
from sentinel.harness import make_backend, new_run_dir, test_images, write_csv, write_metadata


def run(backend, images, f_list: list[float]) -> list[dict]:
    rows = []
    n_layers = len(backend.qm.layers)
    for f in f_list:
        backend.set_frequency(f)
        backend.set_mode(2)
        counts = [0] * n_layers
        for image_id, image in enumerate(images):
            for ev in backend.classify(image, image_id=image_id).events:
                counts[ev["layer"]] += 1
        rows.append({"f_mhz": f, **{f"layer{i}_errors": counts[i] for i in range(n_layers)}})
    return rows


def onsets(rows: list[dict]) -> dict[str, float | None]:
    keys = [k for k in rows[0] if k.startswith("layer")]
    out = {}
    for key in keys:
        out[key] = next((r["f_mhz"] for r in rows if r[key] > 0), None)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", type=int, default=8)
    parser.add_argument("--model", default="xs")
    parser.add_argument("--gamma", type=float, default=0.25, help="assumed H3 strength of the synthetic model")
    args = parser.parse_args()
    backend, weights = make_backend(args.model, fault=FaultParams(gamma=args.gamma))
    images, source = test_images(args.images)
    rows = run(backend, images, [130.0 + i * 5.0 for i in range(25)])
    out = new_run_dir(backend.name, "e3")
    write_csv(out / "data.csv", rows)
    write_metadata(out, "e3", backend, {"weights": weights, "images": source, "onsets_mhz": onsets(rows), "criterion": "deep layers onset >= 10% above layer 1"})
    print(f"[SYNTHETIC] E3 wrote {out}" if backend.name == "mock" else f"E3 wrote {out}")


if __name__ == "__main__":
    main()
