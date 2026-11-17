"""Counting of zero operands in the engine's operand stream (input to the zero-skipping evaluation)."""
import numpy as np

from model.zero_taps import conv_zero_taps, fc_zero_inputs


def _brute_force(x: np.ndarray) -> tuple[int, int]:
    """Zero taps of a 3x3 'same' convolution, counted one tap at a time."""
    cin, h, w = x.shape
    zero = total = 0
    for yy in range(h):
        for xx in range(w):
            for c in range(cin):
                for i in range(3):
                    for j in range(3):
                        sy, sx = yy + i - 1, xx + j - 1
                        value = x[c, sy, sx] if 0 <= sy < h and 0 <= sx < w else 0
                        total += 1
                        zero += int(value == 0)
    return zero, total


def test_all_zero_input_has_only_zero_taps():
    zero, total = conv_zero_taps(np.zeros((3, 4, 4), dtype=np.int64))
    assert total == 4 * 4 * 3 * 9
    assert zero == total


def test_padding_taps_count_as_zero():
    # 2x2 single-channel image of ones: each of the 4 positions sees 4 pixels and 5 padding taps
    zero, total = conv_zero_taps(np.ones((1, 2, 2), dtype=np.int64))
    assert (zero, total) == (20, 36)


def test_matches_tap_by_tap_count_on_random_inputs():
    rng = np.random.default_rng(2027)
    for _ in range(20):
        x = rng.integers(0, 3, size=(int(rng.integers(1, 4)), int(rng.integers(2, 6)), int(rng.integers(2, 6))))
        assert conv_zero_taps(x) == _brute_force(x)


def test_batch_is_the_sum_of_images():
    rng = np.random.default_rng(7)
    batch = rng.integers(0, 2, size=(5, 2, 4, 4))
    zero, total = conv_zero_taps(batch)
    parts = [conv_zero_taps(img) for img in batch]
    assert zero == sum(p[0] for p in parts) and total == sum(p[1] for p in parts)


def test_fc_zero_inputs():
    assert fc_zero_inputs(np.array([[0, 3, 0, 1], [0, 0, 0, 0]])) == (6, 8)
