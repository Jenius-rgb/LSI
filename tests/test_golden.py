"""M2 level L0: integer arithmetic of SPEC section 3."""
import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from model import golden


# --- requantisation (SPEC 3.3) --------------------------------------------------------


@pytest.mark.parametrize(
    "v,m,n,expected",
    [
        (1, 1, 1, 1),  # +0.5 rounds up
        (3, 1, 1, 2),  # +1.5 rounds up
        (2, 1, 2, 1),  # +0.5 rounds up
        (-1, 1, 1, 0),  # -0.5 rounds up to 0
        (-3, 1, 1, 0),  # negative saturates to 0 (ReLU)
        (-1000, 3, 4, 0),
        (5, 3, 0, 15),  # n = 0: no rounding term
        (1 << 20, 1, 0, 255),  # saturates to 255
        (255, 1, 0, 255),
        (256, 1, 0, 255),
        (510, 1, 1, 255),
        (511, 1, 1, 255),
    ],
)
def test_requant_cases(v, m, n, expected):
    assert golden.requant(np.array([v]), m, n)[0] == expected


def test_requant_shift_is_arithmetic_on_large_negative():
    v = np.array([-(2**32)], dtype=np.int64)
    assert golden.requant(v, 65535, 31)[0] == 0


@given(st.integers(-(2**32), 2**32), st.integers(1, 65535), st.integers(0, 31))
@settings(max_examples=300, deadline=None)
def test_requant_matches_python_integers(v, m, n):
    rounded = (v * m + (1 << (n - 1))) >> n if n else v * m
    assert golden.requant(np.array([v], dtype=np.int64), m, n)[0] == min(max(rounded, 0), 255)


# --- convolution and padding (SPEC 3.2) -----------------------------------------------


def naive_conv(w, a):
    cout, cin = w.shape[:2]
    h, width = a.shape[1:]
    acc = np.zeros((cout, h, width), dtype=np.int64)
    for o in range(cout):
        for y in range(h):
            for x in range(width):
                for c in range(cin):
                    for i in range(3):
                        for j in range(3):
                            yy, xx = y + i - 1, x + j - 1
                            if 0 <= yy < h and 0 <= xx < width:
                                acc[o, y, x] += int(w[o, c, i, j]) * int(a[c, yy, xx])
    return acc


def test_padding_uses_zero_outside_bounds():
    a = np.zeros((1, 4, 4), dtype=np.int64)
    a[0, 0, 0] = 7
    w = np.zeros((1, 1, 3, 3), dtype=np.int64)
    w[0, 0, 2, 2] = 1  # picks a[y+1, x+1]
    acc = golden.conv_accumulate(w, a)
    assert acc[0, 0, 0] == 0  # a[1,1] is zero
    w[0, 0, 2, 2] = 0
    w[0, 0, 0, 0] = 1  # picks a[y-1, x-1]
    acc = golden.conv_accumulate(w, a)
    assert acc[0, 1, 1] == 7 and acc[0, 0, 0] == 0


def test_kernel_is_not_flipped():
    a = np.zeros((1, 3, 3), dtype=np.int64)
    a[0, 1, 2] = 5  # right of centre
    w = np.zeros((1, 1, 3, 3), dtype=np.int64)
    w[0, 0, 1, 2] = 2  # i=1 (y), j=2 (x+1)
    assert golden.conv_accumulate(w, a)[0, 1, 1] == 10


@given(st.integers(0, 2**31 - 1))
@settings(max_examples=40, deadline=None)
def test_conv_matches_naive_formula(seed):
    rng = np.random.default_rng(seed)
    w = rng.integers(-127, 128, size=(4, 3, 3, 3), dtype=np.int64)
    a = rng.integers(0, 256, size=(3, 8, 8), dtype=np.int64)
    assert np.array_equal(golden.conv_accumulate(w, a), naive_conv(w, a))


def test_conv_batch_matches_single():
    rng = np.random.default_rng(1)
    w = rng.integers(-127, 128, size=(2, 3, 3, 3), dtype=np.int64)
    batch = rng.integers(0, 256, size=(5, 3, 6, 6), dtype=np.int64)
    out = golden.conv_accumulate(w, batch)
    for i in range(5):
        assert np.array_equal(out[i], golden.conv_accumulate(w, batch[i]))


# --- pooling, flatten and argmax (SPEC 3.1, 3.4, 3.5) ---------------------------------


def test_maxpool_2x2_with_ties():
    y = np.array([[[1, 9, 2, 2], [3, 9, 2, 2], [0, 0, 7, 1], [0, 0, 1, 7]]], dtype=np.int64)
    assert np.array_equal(golden.maxpool2x2(y), np.array([[[9, 2], [0, 7]]]))


def test_flatten_order_c_h_w():
    a = np.arange(2 * 2 * 3).reshape(2, 2, 3)
    flat = golden.flatten_chw(a)
    for c in range(2):
        for y in range(2):
            for x in range(3):
                assert flat[c * 2 * 3 + y * 3 + x] == a[c, y, x]


def test_argmax_picks_smallest_index_on_ties():
    z = np.array([[3, 7, 7, 1], [9, 9, 9, 9], [-5, -2, -2, -9]], dtype=np.int64)
    assert golden.argmax_first(z).tolist() == [1, 0, 1]


# --- full forward pass ----------------------------------------------------------------


def tiny_model(seed=0, m=9000, n=20):
    rng = np.random.default_rng(seed)
    conv = golden.QLayer(
        "conv1", "conv",
        w=rng.integers(-127, 128, size=(4, 3, 3, 3), dtype=np.int64),
        b=rng.integers(-1000, 1000, size=4, dtype=np.int64),
        m=m, n=n,
    )
    fc = golden.QLayer(
        "fc", "fc",
        w=rng.integers(-127, 128, size=(3, 4 * 2 * 2), dtype=np.int64),
        b=rng.integers(-1000, 1000, size=3, dtype=np.int64),
        m=0, n=0,
    )
    return golden.QModel("tiny", (3, 4, 4), [conv, fc])


def test_forward_composes_the_primitives():
    qm = tiny_model()
    rng = np.random.default_rng(3)
    img = rng.integers(0, 256, size=(3, 4, 4), dtype=np.uint8)
    out = golden.forward(qm, img, trace=True)

    conv = qm.layers[0]
    acc = golden.conv_accumulate(conv.w, img.astype(np.int64))
    y = golden.requant(acc + conv.b[:, None, None], conv.m, conv.n)
    pooled = golden.maxpool2x2(y)
    z = conv_z = qm.layers[1].w @ golden.flatten_chw(pooled) + qm.layers[1].b
    assert np.array_equal(out.logits, z)
    assert out.pred == int(np.argmax(conv_z))
    assert np.array_equal(out.trace[0].acc, acc)
    assert np.array_equal(out.trace[0].y, y)
    assert np.array_equal(out.trace[0].output, pooled)


def test_forward_batch_matches_single():
    qm = tiny_model(5)
    rng = np.random.default_rng(9)
    batch = rng.integers(0, 256, size=(6, 3, 4, 4), dtype=np.uint8)
    out = golden.forward(qm, batch)
    for i in range(6):
        single = golden.forward(qm, batch[i])
        assert np.array_equal(out.logits[i], single.logits)
        assert out.pred[i] == single.pred


def test_save_and_load_roundtrip(tmp_path):
    qm = tiny_model(7)
    path = tmp_path / "q.npz"
    qm.save(path)
    loaded = golden.QModel.load(path)
    assert loaded.name == qm.name and loaded.in_shape == qm.in_shape
    for a, b in zip(loaded.layers, qm.layers):
        assert (a.name, a.kind, a.m, a.n) == (b.name, b.kind, b.m, b.n)
        assert np.array_equal(a.w, b.w) and np.array_equal(a.b, b.b)
