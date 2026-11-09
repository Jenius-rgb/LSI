"""E6: governor behaviour as the error onset drifts with temperature ([SYNTHETIC])."""
from __future__ import annotations

import argparse

import numpy as np

from model.governor import GovParams
from sentinel.harness import make_backend, new_run_dir, test_images, write_csv, write_metadata


def run(backend, images, n_iter: int, freqs: list[float]) -> list[dict]:
    backend.enable_governor(freqs)
    golden = [backend.golden(img) for img in images]
    base_onset = backend.fault.f_onset.copy()
    rows = []
    for step in range(n_iter):
        # Synthetic temperature ramp: the onset falls over the first half and recovers.
        drift = 1.0 - 0.12 * np.sin(np.pi * step / n_iter)
        backend.fault.f_onset = base_onset * drift
        image_id = step % len(images)
        res = backend.classify(images[image_id], image_id=step)
        rows.append(
            {
                "image_index": step, "onset_scale": float(drift), "level": res.level,
                "turbo_mhz": freqs[res.level], "turbo_mask": res.turbo_mask,
                "corrected": sum(res.corrected), "recompute": sum(res.recompute),
                "bit_exact": int(np.array_equal(np.array(res.logits), golden[image_id].logits)),
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", type=int, default=6)
    parser.add_argument("--iters", type=int, default=120)
    parser.add_argument("--model", default="xs")
    args = parser.parse_args()
    backend, weights = make_backend(args.model)
    gov = GovParams(n_up=4, cooldown=3, corr_hi=8, l_min=0, l_max=15)
    backend.gov_params = gov
    from model.governor import reset

    backend.gov_state = reset(gov, len(backend.qm.layers))
    freqs = [110.0 + 8.0 * i for i in range(16)]
    images, source = test_images(args.images)
    rows = run(backend, images, args.iters, freqs)
    out = new_run_dir(backend.name, "e6")
    write_csv(out / "data.csv", rows)
    write_metadata(out, "e6", backend, {"weights": weights, "images": source, "freq_table_mhz": freqs, "all_bit_exact": all(r["bit_exact"] for r in rows)})
    print(f"[SYNTHETIC] E6 wrote {out}")


if __name__ == "__main__":
    main()
