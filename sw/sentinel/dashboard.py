"""Lightweight web dashboard: live frame, class, FPS, turbo frequency and counters (SPEC 15)."""
from __future__ import annotations

import argparse
import threading
import time

import numpy as np

PAGE = """<!doctype html><meta charset=utf-8><title>SENTINEL</title>
<style>body{font:15px/1.4 system-ui;margin:2rem;color:#0b0b0b;background:#fcfcfb}
main{display:grid;grid-template-columns:320px 1fr;gap:2rem}img{width:320px;image-rendering:pixelated;background:#ddd}
.note{color:#b3261e;font-weight:600}table{border-collapse:collapse}td{padding:.2rem .8rem .2rem 0}</style>
<h1>SENTINEL</h1><p class=note id=label></p>
<main><div><img id=f src=/frame.jpg></div><table id=t></table></main>
<script>
async function tick(){const s=await (await fetch('/stats.json')).json();
document.getElementById('label').textContent=s.label;
document.getElementById('t').innerHTML=Object.entries(s.values).map(([k,v])=>`<tr><td>${k}</td><td>${v}</td></tr>`).join('');
document.getElementById('f').src='/frame.jpg?'+Date.now();}
setInterval(tick,500);tick();</script>"""


class State:
    def __init__(self, backend):
        self.backend = backend
        self.jpeg = b""
        self.values: dict = {}
        self.lock = threading.Lock()

    def update(self, frame_bgr, result, fps: float) -> None:
        import cv2

        ok, buf = cv2.imencode(".jpg", frame_bgr)
        with self.lock:
            if ok:
                self.jpeg = buf.tobytes()
            self.values = {
                "class": result.pred, "FPS": f"{fps:.1f}", "FPGA time (ms)": f"{result.fpga_time_s * 1e3:.2f}",
                "turbo mask": hex(result.turbo_mask), "governor level": result.level,
                "corrected units": sum(result.corrected), "recomputed units": sum(result.recompute),
                "lane corrections": result.lane_corrections,
            }


def create_app(state: State):
    from flask import Flask, Response, jsonify

    app = Flask(__name__)

    @app.route("/")
    def index():
        return PAGE

    @app.route("/frame.jpg")
    def frame():
        with state.lock:
            return Response(state.jpeg, mimetype="image/jpeg")

    @app.route("/stats.json")
    def stats():
        label = "SYNTHETIC — NOT MEASURED (mock backend)" if state.backend.name == "mock" else ""
        with state.lock:
            return jsonify({"label": label, "values": state.values})

    return app


def camera_loop(state: State, source: str) -> None:
    from sentinel.camera import open_source
    from sentinel.preprocess import preprocess_bgr

    last = time.perf_counter()
    for index, frame in enumerate(open_source(source)):
        result = state.backend.classify(preprocess_bgr(frame), image_id=index)
        now = time.perf_counter()
        state.update(frame, result, 1.0 / max(now - last, 1e-6))
        last = now


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="0")
    parser.add_argument("--model", default="xs")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    from sentinel.harness import make_backend

    backend, _ = make_backend(args.model)
    state = State(backend)
    threading.Thread(target=camera_loop, args=(state, args.source), daemon=True).start()
    create_app(state).run(host="127.0.0.1", port=args.port)


__all__ = ["State", "create_app", "camera_loop", "np"]


if __name__ == "__main__":
    main()
