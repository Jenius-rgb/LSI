"""Real-time camera mode (official requirement): classify frames continuously, show speed."""
from __future__ import annotations

import argparse
import time

from sentinel.camera import open_source
from sentinel.preprocess import preprocess_bgr


def run(backend, source: str, max_frames: int | None = None, control=None) -> dict:
    """Classify frames from the source. With a ButtonControl, frames are only classified while it says so."""
    frames = skipped = 0
    start = time.perf_counter()
    last = None
    for frame in open_source(source):
        if control is not None and not control.should_classify():
            skipped += 1
            continue
        result = backend.classify(preprocess_bgr(frame), image_id=frames)
        last = result
        frames += 1
        if max_frames and frames >= max_frames:
            break
    elapsed = time.perf_counter() - start
    return {"frames": frames, "skipped": skipped, "fps": frames / elapsed if elapsed else 0.0,
            "last_pred": last.pred if last else None, "elapsed_s": elapsed}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="0", help="'picamera', a camera index, or a video file")
    parser.add_argument("--model", default="xs")
    parser.add_argument("--frames", type=int, default=None)
    parser.add_argument("--buttons", choices=["off", "active-high", "active-low"], default="off",
                        help="START/STOP/RUN on GPIO20/21/16; the polarity is not documented, measure it first")
    args = parser.parse_args()
    from sentinel.harness import make_backend

    backend, _ = make_backend(args.model)
    control = None
    if args.buttons != "off":
        from sentinel.buttons import open_pi_buttons

        control = open_pi_buttons(active_high=args.buttons == "active-high")
    report = run(backend, args.source, args.frames, control)
    print(f"[{'SYNTHETIC' if backend.name == 'mock' else 'HW'}] {report}")


if __name__ == "__main__":
    main()
