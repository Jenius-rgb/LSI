"""Image preprocessing shared by the camera, validation mode and fine-tuning (SPEC 15)."""
from __future__ import annotations

import numpy as np


def preprocess_bgr(frame: np.ndarray, size: int = 32) -> np.ndarray:
    """Centre-crop, area-resize to size x size, convert BGR to RGB, return (C, H, W) uint8."""
    import cv2

    h, w = frame.shape[:2]
    side = min(h, w)
    top, left = (h - side) // 2, (w - side) // 2
    crop = frame[top : top + side, left : left + side]
    small = cv2.resize(crop, (size, size), interpolation=cv2.INTER_AREA)
    rgb = small[:, :, ::-1]
    return np.transpose(rgb, (2, 0, 1)).astype(np.uint8)


def read_image_file(path) -> np.ndarray:
    import cv2

    frame = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError(f"cannot read image: {path}")
    return preprocess_bgr(frame)
