"""Generate verification vectors for the RTL testbenches from the golden model.

Vectors always come from a fixed seed. Real weights and images are used when available
(results/model/<m>/quant.npz, data/cifar-10); otherwise seeded random stand-ins are used so
the RTL flow still runs, and the source is reported.
"""
from __future__ import annotations

import numpy as np

from model.config import ROOT, layer_shapes, load_model_config
from model.golden import QLayer, QModel


def load_or_random_qmodel(name: str, seed: int = 2027) -> tuple[QModel, str]:
    path = ROOT / "results" / "model" / name / "quant.npz"
    if path.exists():
        return QModel.load(path), "trained"
    return random_qmodel(name, seed), f"random(seed={seed})"


def random_qmodel(name: str, seed: int = 2027, n_classes: int | None = None) -> QModel:
    """A structurally valid model with random weights, for flows that have no training yet."""
    cfg = load_model_config(name)
    rng = np.random.default_rng(seed)
    layers = []
    for shape in layer_shapes(cfg, n_classes):
        if shape.kind == "conv":
            w = rng.integers(-127, 128, size=(shape.out_channels, shape.in_channels, 3, 3), dtype=np.int64)
            b = rng.integers(-3000, 3000, size=shape.out_channels, dtype=np.int64)
            layers.append(QLayer(shape.name, "conv", w, b, int(rng.integers(20000, 60000)), int(rng.integers(20, 26))))
        else:
            w = rng.integers(-127, 128, size=(shape.out_channels, shape.n_in), dtype=np.int64)
            b = rng.integers(-3000, 3000, size=shape.out_channels, dtype=np.int64)
            layers.append(QLayer(shape.name, "fc", w, b, 0, 0))
    c = cfg["input"]
    return QModel(name, (c["channels"], c["height"], c["width"]), layers)


def checksum_weights(word: np.ndarray) -> tuple[int, int, int]:
    """wc1, wc2, wc3 of one K-byte word (SPEC 6.1)."""
    lane = np.arange(1, len(word) + 1, dtype=np.int64)
    return int(word.sum()), int((lane * word).sum()), int((lane * lane * word).sum())


def pack_operand(last: int, a: int, word: np.ndarray, wc: tuple[int, int, int], widths: tuple[int, int, int], k: int) -> int:
    """Operand line for tb_lane_array: {last, a, w[K-1]..w[0], wc3, wc2, wc1}."""
    w1, w2, w3 = widths
    out = last
    out = (out << 8) | (a & 0xFF)
    for lane in reversed(range(k)):
        out = (out << 8) | (int(word[lane]) & 0xFF)
    out = (out << w3) | (wc[2] & ((1 << w3) - 1))
    out = (out << w2) | (wc[1] & ((1 << w2) - 1))
    out = (out << w1) | (wc[0] & ((1 << w1) - 1))
    return out


def lane_array_vectors(k: int, c3: int, widths: tuple[int, int, int], n_random: int, n_real: int, seed: int = 2027) -> tuple[list[int], list[int], dict]:
    """Operand stream and expected result words: random units first, then real tiles."""
    from model.data import verification_images
    from model.golden import forward

    rng = np.random.default_rng(seed)
    ops: list[int] = []
    words: list[int] = []
    mask48 = (1 << 48) - 1

    def emit(a_seq: np.ndarray, w_seq: np.ndarray) -> None:
        t = len(a_seq)
        y = np.zeros(k, dtype=np.int64)
        s = [0, 0, 0]
        for idx in range(t):
            word = w_seq[idx]
            wc = checksum_weights(word)
            ops.append(pack_operand(int(idx == t - 1), int(a_seq[idx]), word, wc, widths, k))
            y += word * int(a_seq[idx])
            for c in range(3):
                s[c] += wc[c] * int(a_seq[idx])
        words.extend(v & mask48 for v in s[: 2 + c3])
        words.extend(int(v) & mask48 for v in y[::-1])

    for _ in range(n_random):
        t = int(rng.choice([27, 36, 45, 54]))
        kind = rng.random()
        if kind < 0.05:  # extreme values (SPEC 13.4)
            a_seq = np.full(t, 255, dtype=np.int64)
            w_seq = np.full((t, k), 127 if rng.random() < 0.5 else -127, dtype=np.int64)
        else:
            a_seq = rng.integers(0, 256, size=t, dtype=np.int64)
            w_seq = rng.integers(-127, 128, size=(t, k), dtype=np.int64)
        emit(a_seq, w_seq)

    qm, qsource = load_or_random_qmodel("s")
    images, _, isource = verification_images(4)
    trace = forward(qm, images, trace=True).trace
    real = 0
    layers = list(zip(qm.layers, trace))
    while real < n_real:
        layer, tr = layers[int(rng.integers(len(layers)))]
        im = int(rng.integers(len(images)))
        cout = layer.w.shape[0]
        g = int(rng.integers((cout + k - 1) // k))
        o_idx = [g * k + lane for lane in range(k)]
        if layer.kind == "conv":
            cin = layer.w.shape[1]
            h, width = tr.input.shape[2:]
            y0, x0 = int(rng.integers(h)), int(rng.integers(width))
            a_list, w_list = [], []
            for c in range(cin):
                for i in range(3):
                    for j in range(3):
                        yy, xx = y0 + i - 1, x0 + j - 1
                        a_list.append(tr.input[im, c, yy, xx] if 0 <= yy < h and 0 <= xx < width else 0)
                        w_list.append([layer.w[o, c, i, j] if o < cout else 0 for o in o_idx])
            a_seq, w_seq = np.array(a_list, dtype=np.int64), np.array(w_list, dtype=np.int64)
        else:
            a_seq = tr.input[im].reshape(-1).astype(np.int64)
            w_seq = np.array([[layer.w[o, t] if o < cout else 0 for o in o_idx] for t in range(a_seq.size)], dtype=np.int64)
        emit(a_seq, w_seq)
        real += 1
    return ops, words, {"random_units": n_random, "real_tiles": n_real, "weights": qsource, "images": isource}


def checker_vectors(k: int, c3_hw: int, seed: int = 2027, n_campaign: int = 2500) -> tuple[list[int], list[int], dict]:
    """Checker cases from the M3 campaign plus directed cases for every decision branch.

    Returns input lines, expected lines and a count of cases per decision branch.
    """
    from model import campaign
    from model.checker import CORRECT, DETECT_C1_RECOMPUTE, UNPROTECTED, Outcome, check, checksums, to_signed
    from model.data import verification_images

    qm, qsource = load_or_random_qmodel("s")
    images, _, isource = verification_images(8)
    pool = campaign.UnitPool(qm, images, k)
    rng = np.random.default_rng(seed)
    cs_mask = (1 << 48) - 1
    in_lines: list[int] = []
    exp_lines: list[int] = []
    coverage: dict[str, int] = {}

    def add(y: list[int], s: list[int], mode: int, trust: bool, c3: bool) -> None:
        res = check(y, s[0], s[1], s[2], mode, c3, trust)
        line = (mode << 2) | (int(trust) << 1) | int(c3)
        for v in s:
            line = (line << 48) | (v & cs_mask)
        for v in reversed(y):  # YK first in the line, matching the wire order
            line = (line << 48) | (v & cs_mask)
        in_lines.append(line)
        out = (int(res.outcome) << 8) | res.lane
        for v in res.y:
            out = (out << 32) | (v & 0xFFFFFFFF)
        exp_lines.append(out)
        key = res.outcome.name + (f"_{res.lane}" if res.outcome in (Outcome.CORRECTED, Outcome.CSUM_LANE) else "")
        coverage[key] = coverage.get(key, 0) + 1

    for kind in ("single", "dual", "csum"):
        for c3 in ([False, True] if c3_hw else [False]):
            for trust in (False, True):
                res = campaign.run(pool, kind, n_campaign // 3, c3, trust, seed + len(in_lines))
                for tr in res.trials:
                    s = list(tr.s_seen)
                    add(tr.y_seen, s, CORRECT, trust, c3)
    # Other modes on the same kind of data, and directed corner cases.
    base = [int(v) for v in rng.integers(-(2**24), 2**24, size=k)]
    s1, s2, s3 = checksums(base)
    for c3 in ([False, True] if c3_hw else [False]):
        for trust in (False, True):
            clean = [s1, s2, s3]
            add(base, clean, UNPROTECTED, trust, c3)
            add(base, [s1 + 1, s2, s3], UNPROTECTED, trust, c3)
            add(base, clean, DETECT_C1_RECOMPUTE, trust, c3)
            add(base, [s1 + 1, s2, s3], DETECT_C1_RECOMPUTE, trust, c3)
            add(base, clean, CORRECT, trust, c3)
            for lane in range(k):
                bad = list(base)
                bad[lane] = to_signed(bad[lane] ^ 0x1000, 32)
                add(bad, clean, CORRECT, trust, c3)
            add(base, [s1 + 3, s2, s3], CORRECT, trust, c3)
            add(base, [s1, s2 + 3, s3], CORRECT, trust, c3)
            add(base, [s1, s2, s3 + 3], CORRECT, trust, c3)
            # d1 != 0 with no matching lane, and a large checksum flip that wraps j*d1.
            add(base, [s1 + 1, s2 + 3 * k + 1, s3], CORRECT, trust, c3)
            add(base, [to_signed(s1 ^ (1 << 47), 48), s2, s3], CORRECT, trust, c3)
    return in_lines, exp_lines, {"coverage": coverage, "weights": qsource, "images": isource}


def engine_vectors(model: str, k: int, count: int, workdir, n_classes: int = 10, seed: int = 2027) -> dict:
    """Weights, params, images and expected logits for tb_engine."""
    from model.data import verification_images
    from model.export import write_artifacts
    from model.golden import forward
    from model.config import load_hw_config

    qm, qsource = load_or_random_qmodel(model, seed)
    images, labels, isource = verification_images(count)
    if len(images) < count:
        raise ValueError(f"only {len(images)} images available")
    hw = {**load_hw_config(), "K": k}
    manifest = write_artifacts(qm, hw, workdir)
    res = forward(qm, images)
    logits = res.logits
    pred = np.atleast_1d(res.pred)

    stem = f"{qm.name}_k{k}"
    with open(workdir / "images.mem", "w", newline="\n", encoding="ascii") as fh:
        fh.writelines(f"{int(v):02x}\n" for v in images.reshape(-1).tolist())
    padded = np.zeros((len(images), 16), dtype=np.int64)
    padded[:, : logits.shape[1]] = logits
    write_hex(workdir / "logits.mem", [int(v) & 0xFFFFFFFF for v in padded.reshape(-1).tolist()], 32)
    write_hex(workdir / "classes.mem", [int(v) for v in pred.tolist()], 32)
    return {
        "weights": (workdir / f"{stem}_weights.mem").as_posix(),
        "params": (workdir / f"{stem}_params.mem").as_posix(),
        "images": (workdir / "images.mem").as_posix(),
        "logits": (workdir / "logits.mem").as_posix(),
        "classes": (workdir / "classes.mem").as_posix(),
        "n_classes": int(logits.shape[1]),
        "manifest": manifest,
        "weights_source": qsource,
        "image_source": isource,
    }


def write_hex(path, values: list[int], width_bits: int) -> None:
    digits = (width_bits + 3) // 4
    with open(path, "w", newline="\n", encoding="ascii") as fh:
        fh.writelines(f"{v:0{digits}x}\n" for v in values)
