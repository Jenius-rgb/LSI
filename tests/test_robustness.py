"""Camera-style robustness test set (ADR-040): deterministic distortions of uint8 images."""
import numpy as np
import pytest

from model import robustness as rb


def _images(n: int = 6, seed: int = 1) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, 256, size=(n, 3, 32, 32), dtype=np.uint8)


@pytest.mark.parametrize("name", list(rb.CORRUPTIONS))
def test_every_corruption_keeps_shape_and_dtype_and_is_deterministic(name):
    x = _images()
    a = rb.apply(name, x, seed=7)
    b = rb.apply(name, x, seed=7)
    assert a.shape == x.shape and a.dtype == np.uint8
    assert np.array_equal(a, b)


def test_clean_is_the_identity_and_the_others_change_the_image():
    x = _images()
    assert np.array_equal(rb.apply("clean", x), x)
    for name in rb.CORRUPTIONS:
        if name != "clean":
            assert not np.array_equal(rb.apply(name, x, seed=3), x), name


def test_brightness_and_colour_shifts_go_the_right_way():
    x = np.full((1, 3, 32, 32), 128, dtype=np.uint8)
    assert rb.apply("dark", x).mean() < 128 < rb.apply("bright", x).mean()
    warm = rb.apply("warm", x)
    assert warm[0, 0].mean() > warm[0, 2].mean()          # red above blue


def test_held_out_corruptions_are_not_used_in_training():
    assert set(rb.HELD_OUT) <= set(rb.CORRUPTIONS) and "clean" not in rb.HELD_OUT
    assert set(rb.HELD_OUT).isdisjoint(rb.TRAINED_KINDS)


def test_confusion_matrix_counts_every_image_once():
    labels = np.array([0, 1, 2, 3, 1])
    pred = np.array([0, 2, 2, 3, 1])
    m = rb.confusion(labels, pred, 4)
    assert m.sum() == 5 and m[1, 2] == 1 and np.trace(m) == 4


def test_camera_augmentation_is_seeded_and_stays_in_range():
    """ADR-040 training augmentation: same generator seed, same batch; values stay within 0..255."""
    import torch

    from model.train import camera_augment

    x = torch.from_numpy(_images(16)).float()
    a = camera_augment(x.clone(), torch.Generator().manual_seed(5))
    b = camera_augment(x.clone(), torch.Generator().manual_seed(5))
    assert torch.equal(a, b) and a.shape == x.shape
    assert float(a.min()) >= 0.0 and float(a.max()) <= 255.0 and not torch.equal(a, x)


def test_camera_augmentation_strength_zero_is_the_identity():
    """ADR-040 s4b: strength scales every probability and range toward no change."""
    import torch

    from model.train import camera_augment

    x = torch.from_numpy(_images(8)).float()
    assert torch.equal(camera_augment(x.clone(), torch.Generator().manual_seed(1), strength=0.0), x)
