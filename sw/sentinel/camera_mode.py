"""Real-time camera mode (official requirement): classify frames continuously, show speed."""
from __future__ import annotations

import argparse
import time

from sentinel.camera import open_source
from sentinel.preprocess import preprocess_bgr


def run(backend, source: str, max_frames: int | None = None) -> dict:
    frames = 0
    start = time.perf_counter()
    last = None
    for frame in open_source(source):
        result = backend.classify(preprocess_bgr(frame), image_id=frames)
        last = result
        frames += 1
        if max_frames and frames >= max_frames:
            break
    elapsed = time.perf_counter() - start
    return {"frames": frames, "fps": frames / elapsed if elapsed else 0.0, "last_pred": last.pred if last else None, "elapsed_s": elapsed}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="0", help="'picamera', a camera index, or a video file")
    parser.add_argument("--model", default="xs")
    parser.add_argument("--frames", type=int, default=None)
    args = parser.parse_args()
    from sentinel.harness import make_backend

    backend, _ = make_backend(args.model)
    report = run(backend, args.source, args.frames)
    print(f"[{'SYNTHETIC' if backend.name == 'mock' else 'HW'}] {report}")


if __name__ == "__main__":
    main()
