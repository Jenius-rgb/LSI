"""Frame sources for the real-time camera mode: Raspberry Pi camera, OpenCV device or a video file."""
from __future__ import annotations

from collections.abc import Iterator

import numpy as np


def open_source(source: str) -> Iterator[np.ndarray]:
    """Yield BGR frames. source is 'picamera', a camera index such as '0', or a video path."""
    if source == "picamera":
        return _picamera_frames()
    return _opencv_frames(int(source) if source.isdigit() else source)


def _picamera_frames() -> Iterator[np.ndarray]:
    from picamera2 import Picamera2  # available on the Pi only

    camera = Picamera2()
    camera.configure(camera.create_preview_configuration(main={"format": "BGR888", "size": (640, 480)}))
    camera.start()
    try:
        while True:
            yield camera.capture_array()
    finally:
        camera.stop()


def _opencv_frames(source) -> Iterator[np.ndarray]:
    import cv2

    capture = cv2.VideoCapture(source)
    if not capture.isOpened():
        raise ValueError(f"cannot open video source: {source}")
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                return
            yield frame
    finally:
        capture.release()
