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


def spi_session_log(model: str, k: int, workdir, seed: int = 2027) -> tuple[int, dict]:
    """A complete driver session against the Python device model, as a replayable log."""
    from sentinel.device_model import ModelDevice
    from sentinel.driver import SentinelDriver
    from sentinel.transport import LogTransport

    from model.config import load_hw_config
    from model.data import verification_images
    from model.export import write_artifacts
    from model.golden import forward

    qm, qsource = load_or_random_qmodel(model, seed)
    manifest = write_artifacts(qm, {**load_hw_config(), "K": k}, workdir)
    images, _, isource = verification_images(2)
    device = ModelDevice(qm, k=k, flags=(1 << 1))
    drv = SentinelDriver(LogTransport(device))

    identity = drv.read_id()
    assert identity.magic == b"SNTL"
    assert drv.read_reg(0x000) == 0x534E544C
    stem = workdir / f"{qm.name}_k{k}"
    drv.load_model(stem.with_suffix(".bin"), stem.with_suffix(".manifest.json"))
    # Read a few weight bytes back through the device model and the RTL.
    assert len(drv.read(0x010000, 16)) == 16
    drv.write_image(images[0].tobytes(), slot=0)
    assert drv.read(0x030000, 8) == images[0].tobytes()[:8]
    drv.configure(mode=2, img_sel=0)
    drv.start()
    drv.wait_done()
    pred = drv.result_class()
    logits = drv.logits(int(manifest["n_classes"]))
    counters = drv.layer_counters(len(qm.layers))
    gold = forward(qm, images[0])
    assert pred == gold.pred and logits == [int(v) for v in gold.logits]
    assert all(c["units"] == c["clean"] for c in counters)

    # Ping-pong (SPEC 12.5): write IMG1 while the engine works on IMG0, then switch.
    drv.configure(mode=2, img_sel=0)
    drv.start()
    drv.write_image(images[1].tobytes(), slot=1)
    drv.wait_done()
    assert drv.result_class() == gold.pred
    drv.configure(mode=2, img_sel=1)
    drv.start()
    drv.wait_done()
    gold1 = forward(qm, images[1])
    assert drv.result_class() == gold1.pred
    assert drv.logits(int(manifest["n_classes"])) == [int(v) for v in gold1.logits]

    n_entries = drv.t.write_log(workdir / "spi_session.mem")
    return n_entries, {"weights": qsource, "images": isource}


def system_scenarios(model: str, k: int, c3_hw: int, scenarios: list[dict], workdir, images=None, n_log: int = 256, seed: int = 2027) -> dict:
    """Run each scenario through the engine model and write the expectations for tb_system.

    A scenario: {image, mode, c3_on, trust, slots: [InjectionSlot, InjectionSlot]}.
    """
    from model.config import load_hw_config
    from model.engine_model import EngineConfig, InjectionSlot, run_image
    from model.export import write_artifacts

    qm, qsource = load_or_random_qmodel(model, seed)
    write_artifacts(qm, {**load_hw_config(), "K": k}, workdir)
    if images is None:
        from model.data import verification_images

        images, _, isource = verification_images(max(s["image"] for s in scenarios) + 1)
    else:
        isource = "provided"

    def slot_ctrl(sl: InjectionSlot) -> int:
        return int(sl.enable) | (int(sl.any_unit) << 1) | (int(sl.oneshot) << 2) | ((sl.layer & 15) << 4) | ((sl.lane & 63) << 8)

    words: list[int] = []
    fired = dropped = 0
    for sc in scenarios:
        slots = sc.get("slots") or [InjectionSlot(), InjectionSlot()]
        cfg = EngineConfig(k=k, c3_hw=bool(c3_hw), c3_on=sc.get("c3_on", False), mode=sc["mode"], trust=sc.get("trust", False), n_log=n_log)
        res = run_image(qm, images[sc["image"]], cfg, slots)
        fired += res.injections_fired
        words += [sc["image"], (sc["mode"] & 3) | (int(cfg.trust) << 2) | (int(cfg.c3_on) << 3)]
        for sl in slots:
            words += [slot_ctrl(sl), sl.unit & 0xFFFF, sl.mask & 0xFFFFFFFF, (sl.mask >> 32) & 0xFFFF]
        words += [res.pred, int(res.fatal) | (int(res.log_ovf) << 1)]
        logits = np.zeros(16, dtype=np.int64)
        logits[: len(res.logits)] = res.logits
        words += [int(v) & 0xFFFFFFFF for v in logits]
        for layer in range(4):
            if layer < len(qm.layers):
                words += [res.units[layer], res.clean[layer], res.corrected[layer], res.csum_lane[layer], res.recompute[layer], res.fatal_count[layer]]
            else:
                words += [0] * 6
        lanes = list(res.lane_corrections) + [0] * (16 - k)
        words += lanes[:16]
        words.append(len(res.logits))
    write_hex(workdir / "scen.mem", words, 32)
    with open(workdir / "images.mem", "w", newline="\n", encoding="ascii") as fh:
        fh.writelines(f"{int(v):02x}\n" for v in images.reshape(-1).tolist())
    return {"scenarios": len(scenarios), "injections_fired": fired, "weights": qsource, "images": isource}


def jtag_session_log(model: str, k: int, workdir, seed: int = 2027) -> tuple[int, dict]:
    """The driver session of spi_session_log over the JTAG-to-AXI path (ADR-025), as a replayable AXI log."""
    from sentinel.device_model import ModelDevice
    from sentinel.driver import SentinelDriver
    from sentinel.transport_jtag import JtagAxiTransport, RecordingAxi, SimulatedAxi

    from model.config import load_hw_config
    from model.data import verification_images
    from model.export import write_artifacts
    from model.golden import forward

    qm, qsource = load_or_random_qmodel(model, seed)
    manifest = write_artifacts(qm, {**load_hw_config(), "K": k}, workdir)
    images, _, isource = verification_images(2)
    rec = RecordingAxi(SimulatedAxi(ModelDevice(qm, k=k, flags=(1 << 1))))
    drv = SentinelDriver(JtagAxiTransport(rec))
    assert drv.read_id().magic == b"SNTL"
    stem = workdir / f"{qm.name}_k{k}"
    drv.load_model(stem.with_suffix(".bin"), stem.with_suffix(".manifest.json"))
    drv.write_image(images[0].tobytes(), slot=0)
    drv.configure(mode=2, img_sel=0)
    drv.start()
    drv.write_image(images[1].tobytes(), slot=1)
    drv.wait_done()
    gold = forward(qm, images[0])
    assert drv.result_class() == gold.pred
    assert drv.logits(int(manifest["n_classes"])) == [int(v) for v in gold.logits]
    drv.configure(mode=2, img_sel=1)
    drv.start()
    drv.wait_done()
    gold1 = forward(qm, images[1])
    assert drv.result_class() == gold1.pred
    assert drv.logits(int(manifest["n_classes"])) == [int(v) for v in gold1.logits]
    assert drv.read_reg(0x000) == 0x534E544C
    n_words = rec.write_log(workdir / "jtag_session.mem")
    return n_words, {"weights": qsource, "images": isource, "transactions": len(rec.entries)}


def governor_vectors(n_scenarios: int = 60, n_images: int = 40, seed: int = 2027) -> tuple[list[int], dict]:
    """Closed-loop governor scenarios driven by the synthetic fault model. [SYNTHETIC]"""
    from model.fault_model import FaultParams, TimingFaultModel
    from model.governor import GovParams, reset, step

    rng = np.random.default_rng(seed)
    layers = 4
    units_per_layer = [48, 32, 16, 2]
    words: list[int] = []
    for scenario in range(n_scenarios):
        l_min = int(rng.integers(0, 4))
        params = GovParams(
            n_up=int(rng.integers(1, 7)), cooldown=int(rng.integers(0, 6)), corr_hi=int(rng.integers(0, 12)),
            l_min=l_min, l_max=int(rng.integers(l_min + 1, 16)), auto=bool(scenario % 10 != 9),
        )
        fault = TimingFaultModel(
            8, 2, FaultParams(seed=seed + scenario, f_onset_mhz=float(rng.uniform(120, 200)), spread=0.2, delta_mhz=float(rng.uniform(20, 60))),
            sparsity=[0.1, 0.4, 0.6, 0.7],
        )
        state = reset(params, layers)
        words += [1, params.n_up, params.cooldown, params.corr_hi, params.l_min, params.l_max, int(params.auto), n_images]
        for image in range(n_images):
            f_mhz = 100.0 + 5.0 * state.level
            fails, corrected = [0] * layers, [0] * layers
            for layer in range(layers):
                for unit in range(units_per_layer[layer]):
                    hit = sum(fault.error_occurs(image, layer, unit, lane, f_mhz) for lane in range(10))
                    if hit == 1:
                        corrected[layer] += 1
                    elif hit > 1:
                        fails[layer] += 1
            step(state, params, fails, corrected)
            mask = sum(1 << i for i, f in enumerate(fails) if f)
            turbo_mask = sum(bit << i for i, bit in enumerate(state.turbo_en))
            words += [mask, min(sum(corrected), 0xFFFF), state.level, turbo_mask, state.clean_streak, *state.cool]
    return words, {"scenarios": n_scenarios, "images": n_images, "label": "[SYNTHETIC]"}


CORNER_KINDS = ("zero_lanes", "extreme", "ties", "saturate")


def corner_qmodel(kind: str, seed: int = 2027) -> QModel:
    """SPEC 13.4 corner models. Output channels are not multiples of K, so lanes are padded."""
    rng = np.random.default_rng(seed)
    shape = [(3, 12), (12, 20), (20, 20)]
    layers: list[QLayer] = []
    for index, (cin, cout) in enumerate(shape):
        name = f"conv{index + 1}"
        if kind == "extreme":
            w = rng.choice([-127, 127], size=(cout, cin, 3, 3)).astype(np.int64)
            b = rng.choice([-100000, 100000], size=cout).astype(np.int64)
            m, n = 40000, 24
        elif kind == "ties":
            w = np.zeros((cout, cin, 3, 3), dtype=np.int64)
            b = np.full(cout, 12345, dtype=np.int64)
            m, n = 1000, 16
        elif kind == "saturate":
            w = rng.integers(-3, 4, size=(cout, cin, 3, 3), dtype=np.int64)
            b = rng.choice([-(10**7), 10**7], size=cout).astype(np.int64)
            m, n = 65535, 0 if index == 0 else 31
        else:
            w = rng.integers(-127, 128, size=(cout, cin, 3, 3), dtype=np.int64)
            b = rng.integers(-3000, 3000, size=cout, dtype=np.int64)
            m, n = 20000, 22
        layers.append(QLayer(name, "conv", w, b, m, n))
    n_in = 20 * 4 * 4
    if kind == "ties":
        w = np.zeros((13, n_in), dtype=np.int64)
        b = np.zeros(13, dtype=np.int64)
        b[3:7] = 99  # equal maxima: the smallest index wins
    else:
        w = rng.integers(-127, 128, size=(13, n_in), dtype=np.int64)
        b = rng.integers(-3000, 3000, size=13, dtype=np.int64)
    layers.append(QLayer("fc", "fc", w, b, 0, 0))
    return QModel(f"corner_{kind}", (3, 32, 32), layers)


def corner_images(seed: int = 2027) -> np.ndarray:
    """Zero image, full-scale image, and random images."""
    rng = np.random.default_rng(seed)
    images = rng.integers(0, 256, size=(6, 3, 32, 32), dtype=np.uint8)
    images[0] = 0
    images[1] = 255
    return images


def engine_vectors_custom(qm: QModel, images: np.ndarray, k: int, workdir) -> dict:
    """Like engine_vectors, for an arbitrary QModel and image set."""
    from model.config import load_hw_config
    from model.export import write_artifacts
    from model.golden import forward

    hw = {**load_hw_config(), "K": k}
    manifest = write_artifacts(qm, hw, workdir)
    res = forward(qm, images)
    with open(workdir / "images.mem", "w", newline="\n", encoding="ascii") as fh:
        fh.writelines(f"{int(v):02x}\n" for v in images.reshape(-1).tolist())
    padded = np.zeros((len(images), 16), dtype=np.int64)
    padded[:, : res.logits.shape[1]] = res.logits
    write_hex(workdir / "logits.mem", [int(v) & 0xFFFFFFFF for v in padded.reshape(-1).tolist()], 32)
    write_hex(workdir / "classes.mem", [int(v) for v in np.atleast_1d(res.pred).tolist()], 32)
    stem = f"{qm.name}_k{k}"
    return {
        "weights": (workdir / f"{stem}_weights.mem").as_posix(), "params": (workdir / f"{stem}_params.mem").as_posix(),
        "images": (workdir / "images.mem").as_posix(), "logits": (workdir / "logits.mem").as_posix(),
        "classes": (workdir / "classes.mem").as_posix(), "n_classes": int(res.logits.shape[1]), "manifest": manifest,
    }


def write_hex(path, values: list[int], width_bits: int) -> None:
    digits = (width_bits + 3) // 4
    with open(path, "w", newline="\n", encoding="ascii") as fh:
        fh.writelines(f"{v:0{digits}x}\n" for v in values)


def wc_gen_vectors(k: int, c3: int, widths: tuple[int, int, int], n_random: int, models: tuple[str, ...] = ("s", "xs"),
                   seed: int = 2027) -> tuple[list[int], list[int], dict]:
    """Weight words and expected {wc3, wc2, wc1} for tb_wc_gen (ADR-029): corner words, seeded random words over the
    full int8 range, then every weight word of the given models in the export layout (lane k in byte k)."""
    from model.export import memory_image

    rng = np.random.default_rng(seed)
    corners = [np.full(k, v, dtype=np.int64) for v in (0, 1, -1, 127, -127, -128)]
    alt = np.array([127 if i % 2 == 0 else -127 for i in range(k)], dtype=np.int64)
    corners += [alt, -alt, np.array([127 if i % 2 == 0 else -128 for i in range(k)], dtype=np.int64),
                np.array([-128 if i % 2 == 0 else 127 for i in range(k)], dtype=np.int64)]
    for lane in range(k):
        for v in (127, -128, 1, -1):
            word = np.zeros(k, dtype=np.int64)
            word[lane] = v
            corners.append(word)
    corners += [np.arange(k, dtype=np.int64) - k // 2, (np.arange(k, dtype=np.int64)[::-1] * 15 - 60).clip(-128, 127)]
    parts = [np.array(corners, dtype=np.int64), rng.integers(-128, 128, size=(n_random, k), dtype=np.int64)]
    sources = {}
    for name in models:
        qm, src = load_or_random_qmodel(name, seed)
        words = memory_image(qm, {"K": k}).weights.astype(np.int64)
        parts.append(words)
        sources[name] = {"weights": src, "words": int(len(words))}
    allw = np.concatenate(parts)
    lane = np.arange(1, k + 1, dtype=np.int64)
    wc = [allw.sum(axis=1), allw @ lane, allw @ (lane * lane)]
    if not c3:
        wc[2] = np.zeros_like(wc[2])
    w1, w2, w3 = widths
    packed_words = [sum((int(v) & 0xFF) << (8 * i) for i, v in enumerate(row)) for row in allw.tolist()]
    expected = [((int(c) & ((1 << w3) - 1)) << (w1 + w2)) | ((int(b) & ((1 << w2) - 1)) << w1) | (int(a) & ((1 << w1) - 1))
                for a, b, c in zip(*(x.tolist() for x in wc))]
    meta = {"seed": seed, "corner_words": len(corners), "random_words": n_random, "models": sources, "total": len(packed_words)}
    return packed_words, expected, meta
