"""E1: error atlas across frequency. Tests H1 (errors first hit one lane)."""
from __future__ import annotations

import argparse
from collections import Counter

from sentinel.harness import make_backend, new_run_dir, test_images, write_csv, write_metadata


def run(backend, images, f_list: list[float]) -> list[dict]:
    rows = []
    for f in f_list:
        backend.set_frequency(f)
        backend.set_mode(2)
        units_hit = single = 0
        layer_counts: Counter = Counter()
        lane_counts: Counter = Counter()
        for image_id, image in enumerate(images):
            res = backend.classify(image, image_id=image_id)
            per_unit: dict = {}
            for ev in res.events:
                per_unit.setdefault((ev["layer"], ev["unit"]), []).append(ev["lane"])
                lane_counts[ev["lane"]] += 1
                layer_counts[ev["layer"]] += 1
            units_hit += len(per_unit)
            single += sum(1 for lanes in per_unit.values() if len(lanes) == 1)
        rows.append(
            {
                "f_mhz": f, "images": len(images), "units_with_error": units_hit, "single_lane_units": single,
                "single_lane_fraction": single / units_hit if units_hit else "",
                "events_total": sum(lane_counts.values()),
                **{f"layer{i}_events": layer_counts.get(i, 0) for i in range(4)},
            }
        )
    return rows


def evaluate_h1(rows: list[dict], criterion: float = 0.90) -> dict:
    with_errors = [r for r in rows if r["units_with_error"]]
    lowest = with_errors[:3]
    hit = sum(r["units_with_error"] for r in lowest)
    single = sum(r["single_lane_units"] for r in lowest)
    fraction = single / hit if hit else None
    return {"lowest_error_freqs_mhz": [r["f_mhz"] for r in lowest], "single_lane_fraction": fraction, "criterion": criterion, "h1_holds": fraction is not None and fraction >= criterion}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", type=int, default=10)
    parser.add_argument("--model", default="xs")
    parser.add_argument("--f-start", type=float, default=120.0)
    parser.add_argument("--f-stop", type=float, default=240.0)
    parser.add_argument("--f-step", type=float, default=10.0)
    args = parser.parse_args()
    backend, weights = make_backend(args.model)
    images, source = test_images(args.images)
    freqs = [args.f_start + i * args.f_step for i in range(int((args.f_stop - args.f_start) / args.f_step) + 1)]
    rows = run(backend, images, freqs)
    out = new_run_dir(backend.name, "e1")
    write_csv(out / "data.csv", rows)
    write_metadata(out, "e1", backend, {"weights": weights, "images": source, "h1": evaluate_h1(rows), "f_step_mhz": args.f_step})
    print(f"[{'SYNTHETIC' if backend.name == 'mock' else 'HW'}] E1 wrote {out}")


if __name__ == "__main__":
    main()
