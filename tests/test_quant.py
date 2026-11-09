"""M2: BatchNorm folding and quantisation parameter selection (SPEC section 4)."""
import numpy as np
import pytest

from model import golden, quant


def test_choose_m_n_takes_largest_n_with_m_in_range():
    ratio = 0.0015
    m, n = quant.choose_m_n(ratio)
    assert 1 <= m <= 65535 and 0 <= n <= 31
    assert abs(m / 2**n - ratio) / ratio < 1e-3
    assert round(ratio * 2 ** (n + 1)) > 65535 or n == 31


def test_choose_m_n_caps_n_at_31():
    m, n = quant.choose_m_n(1e-8)
    assert n == 31 and m == round(1e-8 * 2**31)


def test_choose_m_n_handles_ratio_above_one():
    m, n = quant.choose_m_n(3.25)
    assert m / 2**n == pytest.approx(3.25, rel=1e-3)
    assert m <= 65535


def test_choose_m_n_rejects_unrepresentable():
    with pytest.raises(ValueError):
        quant.choose_m_n(0.0)
    with pytest.raises(ValueError):
        quant.choose_m_n(70000.0)


def test_bn_fold_matches_torch_eval():
    torch = pytest.importorskip("torch")
    from model.arch import SentinelNet
    from model.config import load_model_config

    cfg = load_model_config("xs")
    torch.manual_seed(1)
    net = SentinelNet(cfg, 10, 0.0)
    net.train()
    with torch.no_grad():
        for _ in range(3):
            net(torch.rand(16, 3, 32, 32))
    net.eval()
    x = (torch.rand(4, 3, 32, 32) * 255).round().to(torch.uint8)
    with torch.no_grad():
        expected = net(x.float() / 255).numpy()
    folded = quant.fold_bn(net.state_dict(), cfg, 10)
    got = quant.float_forward(folded, x.numpy())
    assert np.allclose(expected, got, atol=1e-3, rtol=1e-3)


def test_quantize_produces_values_in_spec_ranges():
    rng = np.random.default_rng(0)
    layers = [
        quant.FloatLayer("conv1", "conv", rng.normal(0, 0.2, (4, 3, 3, 3)), rng.normal(0, 0.1, 4)),
        quant.FloatLayer("fc", "fc", rng.normal(0, 0.2, (3, 4 * 16 * 16)), rng.normal(0, 0.1, 3)),
    ]
    pytest.importorskip("torch")
    images = rng.integers(0, 256, size=(16, 3, 32, 32), dtype=np.uint8)
    qm, info = quant.quantize(layers, images, "t", (3, 32, 32))
    conv, fc = qm.layers
    assert conv.w.min() >= -127 and conv.w.max() <= 127
    assert max(abs(conv.w.min()), conv.w.max()) == 127
    assert 1 <= conv.m <= 65535 and 0 <= conv.n <= 31
    assert fc.w.min() >= -127 and fc.w.max() <= 127
    assert info[0]["m"] == conv.m
    golden.forward(qm, images[:2])
