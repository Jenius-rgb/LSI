"""Registry of RTL testbenches and their vector generators."""
from __future__ import annotations

from pathlib import Path

from sim import LANES, Bench, wc_widths

IMPLS = {0: "lut", 1: "dsp_min", 2: "dsp_full"}


def _lane_array_vectors(n_random: int, n_real: int):
    def gen(workdir: Path, params: dict) -> list[str]:
        from model.vectors import lane_array_vectors, write_hex

        k, c3 = params["K"], params["C3_EN"]
        widths = (params["WC1_W"], params["WC2_W"], params["WC3_W"])
        ops, words, _ = lane_array_vectors(k, c3, widths, n_random, n_real)
        op_w = 1 + 8 + k * 8 + sum(widths)
        write_hex(workdir / "stim.mem", ops, op_w)
        write_hex(workdir / "exp.mem", words, 48)
        return [f"+stim={(workdir / 'stim.mem').as_posix()}", f"+exp={(workdir / 'exp.mem').as_posix()}", f"+n_ops={len(ops)}", f"+n_words={len(words)}"]

    return gen


def lane_array_benches() -> dict[str, Bench]:
    out = {}
    for k in (8, 16):
        for c3 in (0, 1):
            for impl, name in IMPLS.items():
                wc1, wc2, wc3 = wc_widths(k)
                params = {"K": k, "C3_EN": c3, "LANE_IMPL": impl, "WC1_W": wc1, "WC2_W": wc2, "WC3_W": wc3}
                bench_name = f"lane_array_k{k}_c{c3}_{name}"
                # One configuration carries the full DoD load per implementation; the
                # remaining combinations run a smaller smoke set to keep `run.py test` short.
                full = k == 8 and c3 == 0
                out[bench_name] = Bench(
                    bench_name, "tb_lane_array", [*LANES, "tb/tb_lane_array.v"], params,
                    _lane_array_vectors(10000 if full else 500, 100 if full else 20),
                )
    return out


def _checker_vectors(workdir: Path, params: dict) -> list[str]:
    import json

    from model.vectors import checker_vectors, write_hex

    k, c3 = params["K"], params["C3_EN"]
    in_lines, exp_lines, meta = checker_vectors(k, c3)
    write_hex(workdir / "in.mem", in_lines, 4 + 3 * 48 + k * 48)
    write_hex(workdir / "exp.mem", exp_lines, 12 + k * 32)
    (workdir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return [f"+in={(workdir / 'in.mem').as_posix()}", f"+exp={(workdir / 'exp.mem').as_posix()}", f"+n={len(in_lines)}"]


def checker_benches() -> dict[str, Bench]:
    out = {}
    for k in (8, 16):
        for c3 in (0, 1):
            name = f"checker_k{k}_c{c3}"
            out[name] = Bench(name, "tb_checker", ["rtl/lane_checker.v", "tb/tb_checker.v"], {"K": k, "C3_EN": c3}, _checker_vectors)
    return out


def _wc_gen_vectors(n_random: int):
    def gen(workdir: Path, params: dict) -> list[str]:
        import json

        from model.vectors import wc_gen_vectors, write_hex

        widths = (params["WC1_W"], params["WC2_W"], params["WC3_W"])
        words, exp, meta = wc_gen_vectors(params["K"], params["C3_EN"], widths, n_random)
        write_hex(workdir / "in.mem", words, params["K"] * 8)
        write_hex(workdir / "exp.mem", exp, sum(widths))
        (workdir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return [f"+in={(workdir / 'in.mem').as_posix()}", f"+exp={(workdir / 'exp.mem').as_posix()}", f"+n={len(words)}"]

    return gen


def wc_gen_benches() -> dict[str, Bench]:
    """ADR-029 condition 1: wc_gen against the formula (corners, seeded random words, all real weight words of s and xs)."""
    out = {}
    sources = ["rtl/sum_tree.v", "rtl/wc_gen.v", "tb/tb_wc_gen.v"]
    for k in (8, 16):
        for c3 in (0, 1):
            wc1, wc2, wc3 = wc_widths(k)
            params = {"K": k, "C3_EN": c3, "WC1_W": wc1, "WC2_W": wc2, "WC3_W": wc3}
            out[f"wc_gen_k{k}_c{c3}"] = Bench(f"wc_gen_k{k}_c{c3}", "tb_wc_gen", sources, params, _wc_gen_vectors(20000))
    wc1, wc2, wc3 = wc_widths(8)
    params = {"K": 8, "C3_EN": 1, "WC1_W": wc1, "WC2_W": wc2, "WC3_W": wc3, "MAX_CASES": 1100000}
    out["wc_gen_k8_c1_1m"] = Bench("wc_gen_k8_c1_1m", "tb_wc_gen", sources, params, _wc_gen_vectors(1000000), slow=True)
    return out


ENGINE_SOURCES = [
    *LANES, "rtl/lane_checker.v", "rtl/ram_tdp.v", "rtl/sum_tree.v", "rtl/wc_gen.v", "rtl/operand_gen.v",
    "rtl/postproc.v", "rtl/pool.v", "rtl/counter_bank.v", "rtl/cdc_fifo.v", "rtl/platform/sim/cdc_fifo_sim.v",
    "rtl/fast_path.v", "rtl/engine.v",
]


def _engine_vectors(model: str, count: int, first: int = 0):
    """Vectors for the first first+count verification images; the bench runs images [first, first+count)."""
    def gen(workdir: Path, params: dict) -> list[str]:
        from model.config import layer_shapes, load_model_config
        from model.vectors import engine_vectors

        k = params["K"]
        ideal = sum(s.ideal_cycles(k) for s in layer_shapes(load_model_config(model)))
        v = engine_vectors(model, k, first + count, workdir)
        return [
            f"+weights={v['weights']}", f"+params={v['params']}", f"+images={v['images']}",
            f"+logits={v['logits']}", f"+classes={v['classes']}", f"+nclasses={v['n_classes']}",
            f"+ideal={ideal}", f"+first={first}", f"+count={count}",
        ]

    return gen


def _corner_vectors(kind: str):
    def gen(workdir: Path, params: dict) -> list[str]:
        from model.vectors import corner_images, corner_qmodel, engine_vectors_custom

        images = corner_images()
        v = engine_vectors_custom(corner_qmodel(kind), images, params["K"], workdir)
        return [
            f"+weights={v['weights']}", f"+params={v['params']}", f"+images={v['images']}", f"+logits={v['logits']}",
            f"+classes={v['classes']}", f"+nclasses={v['n_classes']}", "+first=0", f"+count={len(images)}",
        ]

    return gen


def _sparse_vectors(model: str):
    """Trained model, images with almost-all-zero operand units (model.vectors.sparse_images, ADR-028)."""
    def gen(workdir: Path, params: dict) -> list[str]:
        from model.vectors import engine_vectors_custom, load_or_random_qmodel, sparse_images

        qm, _ = load_or_random_qmodel(model)
        images = sparse_images()
        v = engine_vectors_custom(qm, images, params["K"], workdir)
        return [
            f"+weights={v['weights']}", f"+params={v['params']}", f"+images={v['images']}", f"+logits={v['logits']}",
            f"+classes={v['classes']}", f"+nclasses={v['n_classes']}", "+first=0", f"+count={len(images)}",
        ]

    return gen


# Verification images whose units end fewer than K + 2 + C3 cycles apart under unguarded zero-skip: the
# pre-fix RTL overran the lane-array result serializer on them (diagnosis run of 26 Nov 2026, build/sim/logs).
ZS_OVERRUN_IMAGES = [118, 198]


def _picked_vectors(model: str, indices: list[int]):
    """Trained model, the listed verification images only (in that order)."""
    def gen(workdir: Path, params: dict) -> list[str]:
        from model.data import verification_images
        from model.vectors import engine_vectors_custom, load_or_random_qmodel

        qm, _ = load_or_random_qmodel(model)
        images, _, _ = verification_images(max(indices) + 1)
        v = engine_vectors_custom(qm, images[indices], params["K"], workdir)
        return [
            f"+weights={v['weights']}", f"+params={v['params']}", f"+images={v['images']}", f"+logits={v['logits']}",
            f"+classes={v['classes']}", f"+nclasses={v['n_classes']}", "+first=0", f"+count={len(indices)}",
        ]

    return gen


def _layers_of(model: str) -> str:
    """Models that share the layers of another one: s4, s4a and s4b have the layers of s with a 4-class FC (ADR-037, ADR-040)."""
    return "s" if model in ("s4", "s4a", "s4b") else model


def _engine_params(model: str, k: int, c3: int = 0, impl: int = 0) -> dict:
    wc1, wc2, wc3 = wc_widths(k)
    model = _layers_of(model)
    aw = {"s": (13, 11), "xs": (12, 10)}[model]
    words = {("s", 8): 12, ("s", 16): 11, ("xs", 8): 11, ("xs", 16): 10}[(model, k)]
    return {"K": k, "C3_EN": c3, "LANE_IMPL": impl, "WC1_W": wc1, "WC2_W": wc2, "WC3_W": wc3,
            "WEIGHT_AW": words, "ACT0_AW": aw[0], "ACT1_AW": aw[1]}


def engine_benches() -> dict[str, Bench]:
    out = {}
    # Quick smoke runs (part of `run.py test`), then the full DoD regressions (slow, xsim).
    # The c3 = 1 rows are the official ZERO7 variant of config/hw_zero7.yaml (ADR-013).
    for model, k, c3, count, slow, shards in [
        ("xs", 8, 0, 2, False, 1),
        ("s", 8, 0, 1, False, 1),
        ("s", 8, 1, 1, False, 1),
        ("xs", 8, 0, 200, True, 6),
        ("s", 8, 0, 200, True, 6),
        ("s", 8, 1, 200, True, 6),
        ("s4", 8, 1, 1, True, 1),      # official contest classes (ADR-037), superseded by s4b
        ("s4", 8, 1, 200, True, 6),
        ("s4b", 8, 1, 1, False, 1),    # official model since ADR-040 (camera-style training, same layers)
        ("s4b", 8, 1, 200, True, 6),
        ("s", 16, 0, 20, True, 4),
    ]:
        name = f"engine_{model}_k{k}" + ("_c1" if c3 else "") + (f"_n{count}" if count >= 20 else "")
        out[name] = Bench(
            name, "tb_engine", [*ENGINE_SOURCES, "tb/tb_engine.v"], _engine_params(model, k, c3),
            _engine_vectors(model, count), slow=slow, shards=shards, prefer_xsim=slow,
        )
    # ADR-030 (d): the DSP lane variant (variant_dsp in config/hw_zero7.yaml) must be bit-exact in the same benches.
    for count, slow, shards in [(1, False, 1), (200, True, 6)]:
        name = "engine_s_k8_c1_dsp" + (f"_n{count}" if count >= 20 else "")
        out[name] = Bench(name, "tb_engine", [*ENGINE_SOURCES, "tb/tb_engine.v"], _engine_params("s", 8, 1, impl=1),
                          _engine_vectors("s", count), slow=slow, shards=shards, prefer_xsim=slow)
    # ADR-028 on the DSP variant (speed and demo variant): ZERO_SKIP = 1 must stay bit-exact there too.
    for count, slow, shards in [(1, False, 1), (200, True, 6)]:
        name = "engine_s_k8_c1_dsp_zs" + (f"_n{count}" if count >= 20 else "")
        out[name] = Bench(name, "tb_engine", [*ENGINE_SOURCES, "tb/tb_engine.v"], {**_engine_params("s", 8, 1, impl=1), "ZERO_SKIP": 1},
                          _engine_vectors("s", count), slow=True, shards=shards, prefer_xsim=slow)
    # ADR-028 zero-skip: the same logits as the golden model with fewer cycles. ZERO_SKIP = 1 keeps at least
    # K + 2 + C3 sets per unit (operand_gen); ZERO_SKIP = 2 stalls unit ends in fast_path instead.
    for zs in (1, 2):
        for count, slow, shards in [(1, False, 1), (200, True, 6)]:
            name = f"engine_s_k8_c1_zs{zs if zs > 1 else ''}" + (f"_n{count}" if count >= 20 else "")
            out[name] = Bench(name, "tb_engine", [*ENGINE_SOURCES, "tb/tb_engine.v"], {**_engine_params("s", 8, 1), "ZERO_SKIP": zs},
                              _engine_vectors("s", count), slow=slow or zs == 2, shards=shards, prefer_xsim=slow)
    # ADR-028: units with almost all activations zero. Without a guard these end fewer than K + 2 + C3 cycles apart
    # and overrun the lane-array result serializer (found 26 Nov 2026: engine_s_k8_c1_zs_n200 hung). Baseline row for
    # the cycle comparison.
    for zs in (1, 2):
        name = f"engine_s_k8_c1_zs{zs if zs > 1 else ''}_overrun"
        out[name] = Bench(name, "tb_engine", [*ENGINE_SOURCES, "tb/tb_engine.v"], {**_engine_params("s", 8, 1), "ZERO_SKIP": zs},
                          _picked_vectors("s", ZS_OVERRUN_IMAGES), slow=zs == 2, prefer_xsim=True)
    for zs in (0, 1, 2):
        name = "engine_s_k8_c1_" + (f"zs{zs if zs > 1 else ''}_" if zs else "") + "sparse"
        out[name] = Bench(name, "tb_engine", [*ENGINE_SOURCES, "tb/tb_engine.v"], {**_engine_params("s", 8, 1), "ZERO_SKIP": zs},
                          _sparse_vectors("s"), slow=zs != 1, prefer_xsim=True)
    # SPEC 13.4 corner cases on padded lanes, extreme values, ties, saturation, zero image.
    for kind in ("zero_lanes", "extreme", "ties", "saturate"):
        name = f"engine_corner_{kind}"
        params = {**_engine_params("xs", 8), "WEIGHT_AW": 11, "ACT0_AW": 12, "ACT1_AW": 11}
        out[name] = Bench(name, "tb_engine", [*ENGINE_SOURCES, "tb/tb_engine.v"], params, _corner_vectors(kind), prefer_xsim=True)
    return out


TOP_SOURCES = [
    *ENGINE_SOURCES, "rtl/spi_slave.v", "rtl/regfile.v", "rtl/clk_gen.v", "rtl/platform/sim/clk_gen_sim.v",
    "rtl/governor.v", "rtl/clk_seq.v", "rtl/xadc_temp.v", "rtl/platform/sim/xadc_prim_sim.v", "rtl/ws2812_tx.v", "rtl/status_led.v", "rtl/top_core.v",
]


def _spi_log_vectors(model: str):
    def gen(workdir: Path, params: dict) -> list[str]:
        from model.vectors import spi_session_log

        n_entries, _ = spi_session_log(model, params["K"], workdir)
        return [f"+log={(workdir / 'spi_session.mem').as_posix()}", f"+entries={n_entries}"]

    return gen


def _system_params(model: str, k: int, c3: int, turbo_ns: float, log_aw: int = 8) -> dict:
    wc1, wc2, wc3 = wc_widths(k)
    model = _layers_of(model)
    aw = {"s": (13, 11, 12), "xs": (12, 10, 11), "micro": (9, 8, 9)}[model]
    img_bytes = {"s": 3072, "xs": 3072, "micro": 192}[model]
    return {"K": k, "C3_EN": c3, "WC1_W": wc1, "WC2_W": wc2, "WC3_W": wc3, "WEIGHT_AW": aw[2], "ACT0_AW": aw[0],
            "ACT1_AW": aw[1], "LOG_AW": log_aw, "IMG_BYTES": img_bytes, "TURBO_NS": turbo_ns}


def _system_vectors(model: str, scenario_fn, n_log: int = 256, micro: bool = False):
    def gen(workdir: Path, params: dict) -> list[str]:
        from model.vectors import system_scenarios

        k, c3 = params["K"], params["C3_EN"]
        images = None
        if micro:
            from model.data import micro_images

            images = micro_images(MICRO_IMAGES)
        scenarios = scenario_fn(k, c3)
        meta = system_scenarios(model, k, c3, scenarios, workdir, images=images, n_log=n_log)
        stem = f"{model}_k{k}"
        return [
            f"+scen={(workdir / 'scen.mem').as_posix()}", f"+images={(workdir / 'images.mem').as_posix()}", f"+n={meta['scenarios']}",
            f"+weights={(workdir / (stem + '_weights.mem')).as_posix()}", f"+params={(workdir / (stem + '_params.mem')).as_posix()}",
        ]

    return gen


MICRO_IMAGES = 16


def _m8_scenarios(k: int, c3: int) -> list[dict]:
    """Clean images and one single-lane injection under each mode (M8 DoD)."""
    from model.engine_model import InjectionSlot as S

    no = lambda: [S(), S()]  # noqa: E731
    inj = lambda: [S(enable=True, layer=1, unit=37, lane=3, mask=(1 << 12) | 1, oneshot=True), S()]  # noqa: E731
    inj2 = lambda: [S(enable=True, layer=2, any_unit=True, lane=5, mask=1 << 18, oneshot=True), S()]  # noqa: E731
    out: list[dict] = []
    for img in range(3):
        out.append({"image": img, "mode": 2, "slots": no()})
    out.append({"image": 0, "mode": 2, "slots": inj()})
    out.append({"image": 1, "mode": 1, "slots": inj()})
    out.append({"image": 2, "mode": 0, "slots": inj()})
    out.append({"image": 0, "mode": 2, "slots": inj2()})
    out.append({"image": 1, "mode": 1, "slots": inj2()})
    return out


def _official_scenarios(k: int, c3: int) -> list[dict]:
    """The M8 scenarios with the C3 lane in use, plus two data lanes hit in one unit (official variant, ADR-013)."""
    from model.engine_model import InjectionSlot as S

    dual = lambda: [S(enable=True, layer=1, unit=37, lane=2, mask=1 << 9, oneshot=True),  # noqa: E731
                    S(enable=True, layer=1, unit=37, lane=6, mask=1 << 14, oneshot=True)]
    out = [{**sc, "c3_on": bool(c3)} for sc in _m8_scenarios(k, c3)]
    out.append({"image": 0, "mode": 2, "c3_on": bool(c3), "slots": dual()})
    out.append({"image": 1, "mode": 1, "c3_on": bool(c3), "slots": dual()})
    return out


def _corner_scenarios(k: int, c3: int) -> list[dict]:
    """SPEC 13.4: log full and FATAL path, on the micro model."""
    from model.engine_model import InjectionSlot as S

    persistent = lambda: [S(enable=True, layer=0, any_unit=True, lane=2, mask=1 << 7, oneshot=False), S()]  # noqa: E731
    dual = lambda: [S(enable=True, layer=0, any_unit=True, lane=2, mask=1 << 7, oneshot=False),  # noqa: E731
                    S(enable=True, layer=0, any_unit=True, lane=3, mask=1 << 9, oneshot=False)]
    oneshot_any = lambda: [S(enable=True, layer=0, any_unit=True, lane=4, mask=8, oneshot=True), S()]  # noqa: E731
    out = [
        {"image": 0, "mode": 1, "slots": persistent()},      # recompute also fails: FATAL
        {"image": 1, "mode": 2, "slots": dual()},            # every unit uncorrectable, log overflows
        {"image": 2, "mode": 2, "slots": oneshot_any()},     # ONESHOT re-arms per image
        {"image": 3, "mode": 2, "slots": oneshot_any()},
        {"image": 4, "mode": 0, "slots": persistent()},      # mode 0 never recomputes
    ]
    return out


def m9_campaign_scenarios(k: int, c3: int, count: int = 2400, seed: int = 99) -> list[dict]:
    """Random injections for the RTL campaign: one data lane, two data lanes, one checksum lane."""
    import numpy as np

    from model.engine_model import InjectionSlot as S

    rng = np.random.default_rng(seed)
    n_units = [64, 2]
    out = []
    for i in range(count):
        layer = int(rng.integers(2))
        unit = int(rng.integers(n_units[layer]))
        mode = int(rng.choice([2, 2, 2, 1, 0]))
        trust = bool(rng.random() < 0.25)
        kind = int(rng.integers(3))
        def mask():
            return int(rng.integers(1, 1 << 22)) if rng.random() < 0.7 else (1 << int(rng.integers(0, 31)))
        if kind == 0:
            slots = [S(enable=True, layer=layer, unit=unit, lane=int(rng.integers(1, k + 1)), mask=mask(), oneshot=True), S()]
        elif kind == 1:
            a, b = (int(v) + 1 for v in rng.choice(k, size=2, replace=False))
            slots = [S(enable=True, layer=layer, unit=unit, lane=a, mask=mask(), oneshot=True),
                     S(enable=True, layer=layer, unit=unit, lane=b, mask=mask(), oneshot=True)]
        else:
            lane = k + int(rng.integers(1, (3 if c3 else 2) + 1))
            slots = [S(enable=True, layer=layer, unit=unit, lane=lane, mask=(1 << int(rng.integers(0, 44))), oneshot=True), S()]
        out.append({"image": i % MICRO_IMAGES, "mode": mode, "trust": trust, "c3_on": bool(c3), "slots": slots})
    return out


# DSP variant clocks (ADR-032 (b)): clk_safe = 1000 / 7 MHz, lanes analysed at turbo level 255 MHz.
DSP_F_SAFE_MHZ = 1000.0 / 7.0
DSP_LANE_MHZ = 255.0


def system_benches() -> dict[str, Bench]:
    out = {}
    for ratio, name in [(1.0, "r100"), (1.3, "r130"), (1.7, "r170"), (2.0, "r200")]:
        bench = f"system_xs_{name}"
        out[bench] = Bench(bench, "tb_system", SYSTEM_SOURCES, _system_params("xs", 8, 0, 10.0 / ratio),
                           _system_vectors("xs", _m8_scenarios), slow=True, prefer_xsim=True)
    # Official ZERO7 variant (ADR-013): model s, K = 8, C3 built in and in use, turbo period 10 / 1.3 ns.
    bench = "system_s_k8_c1"
    out[bench] = Bench(bench, "tb_system", SYSTEM_SOURCES, _system_params("s", 8, 1, 10.0 / 1.3),
                       _system_vectors("s", _official_scenarios), slow=True, prefer_xsim=True)
    # The same official variant with the model of config/hw_zero7.yaml since ADR-037: s4 (four official classes).
    bench = "system_s4_k8_c1"
    out[bench] = Bench(bench, "tb_system", SYSTEM_SOURCES, _system_params("s4", 8, 1, 10.0 / 1.3),
                       _system_vectors("s4", _official_scenarios), slow=True, prefer_xsim=True)
    # Official model since ADR-040: s4b, both lane variants.
    bench = "system_s4b_k8_c1"
    out[bench] = Bench(bench, "tb_system", SYSTEM_SOURCES, _system_params("s4b", 8, 1, 10.0 / 1.3),
                       _system_vectors("s4b", _official_scenarios), slow=True, prefer_xsim=True)
    bench = "system_s4b_k8_c1_dsp"
    out[bench] = Bench(bench, "tb_system", SYSTEM_SOURCES,
                       {**_system_params("s4b", 8, 1, 10.0 * DSP_F_SAFE_MHZ / DSP_LANE_MHZ), "LANE_IMPL": 1},
                       _system_vectors("s4b", _official_scenarios), slow=True, prefer_xsim=True)
    # Official DSP variant since ADR-032 (b): model s4, clk_safe 1000/7 MHz, lanes at turbo level 255 MHz (ratio 1.785).
    bench = "system_s4_k8_c1_dsp"
    out[bench] = Bench(bench, "tb_system", SYSTEM_SOURCES,
                       {**_system_params("s4", 8, 1, 10.0 * DSP_F_SAFE_MHZ / DSP_LANE_MHZ), "LANE_IMPL": 1},
                       _system_vectors("s4", _official_scenarios), slow=True, prefer_xsim=True)
    # DSP lane variant (ADR-030 (d)): lanes at the operand supply limit, R = 2 times the safe clock.
    bench = "system_s_k8_c1_dsp"
    out[bench] = Bench(bench, "tb_system", SYSTEM_SOURCES, {**_system_params("s", 8, 1, 10.0 / 2.0), "LANE_IMPL": 1},
                       _system_vectors("s", _official_scenarios), slow=True, prefer_xsim=True)
    # ADR-028 condition 3: zero-skip at the real clock ratio. Model s4, DSP lanes, no injection, ten images; lanes at
    # 2 x clk_safe (the DSP variant, operand supply limit) and at clk_safe, each without and with ZERO_SKIP = 1.
    for ratio, tag in [(2.0, "r2"), (1.0, "r1"), (DSP_LANE_MHZ / DSP_F_SAFE_MHZ, "r1785")]:
        for zs in ((0, 1) if tag != "r1785" else (0,)):
            bench = f"system_s4_dsp_speed_{tag}_zs{zs}"
            out[bench] = Bench(bench, "tb_system", SYSTEM_SOURCES,
                               {**_system_params("s4", 8, 1, 10.0 / ratio), "LANE_IMPL": 1, "ZERO_SKIP": zs},
                               _system_vectors("s4", lambda k, c3: [{"image": i, "mode": 2} for i in range(10)]),
                               slow=True, prefer_xsim=True)
    # Governor in automatic mode: the level climbs every image, so MMCM2 reconfigures between images.
    bench = "system_micro_autogov"
    out[bench] = Bench(bench, "tb_system", SYSTEM_SOURCES,
                       {**_system_params("micro", 8, 0, 9.5), "AUTO_GOV": 1, "N_UP": 1, "L_MAX": 8, "TURBO_STEP_NS": 0.4},
                       _system_vectors("micro", lambda k, c3: [{"image": i % MICRO_IMAGES, "mode": 2} for i in range(12)], micro=True), prefer_xsim=True)
    bench = "system_micro_corners"
    out[bench] = Bench(bench, "tb_system", SYSTEM_SOURCES, {**_system_params("micro", 8, 0, 7.0, log_aw=2)},
                       _system_vectors("micro", _corner_scenarios, n_log=4, micro=True), prefer_xsim=True)
    for k, c3 in [(8, 0), (8, 1), (16, 1)]:
        bench = f"system_micro_campaign_k{k}_c{c3}"
        out[bench] = Bench(bench, "tb_system", SYSTEM_SOURCES, _system_params("micro", k, c3, 6.0),
                           _system_vectors("micro", m9_campaign_scenarios, micro=True), slow=True, prefer_xsim=True)
    return out


def _governor_vectors(workdir: Path, params: dict) -> list[str]:
    from model.vectors import governor_vectors, write_hex

    words, _ = governor_vectors()
    write_hex(workdir / "gov.mem", words, 32)
    return [f"+vec={(workdir / 'gov.mem').as_posix()}", f"+n={len(words)}"]


def _clkwiz_vectors(workdir: Path, params: dict) -> list[str]:
    """Expected Clocking Wizard words per level, straight from tools/gen_mmcm_table.py (ADR-023)."""
    import gen_mmcm_table as gmt

    table = gmt.build_table(gmt.BOARD_F_IN_MHZ, 125.0, 10.0, 16, "-1")
    path = workdir / "clkwiz_expected.mem"
    with open(path, "w", newline="\n", encoding="ascii") as fh:
        for lv in table["levels"]:
            fh.writelines(f"{w:08x}\n" for w in gmt.clkwiz_words(lv))
    return [f"+exp={path.as_posix()}"]


def _jtag_log_vectors(model: str):
    def gen(workdir: Path, params: dict) -> list[str]:
        from model.vectors import jtag_session_log

        jtag_session_log(model, params["K"], workdir)
        return [f"+log={(workdir / 'jtag_session.mem').as_posix()}"]

    return gen


JTAG_SOURCES = [*TOP_SOURCES, "rtl/axil_bus_bridge.v", "rtl/jtag_axi_master.v", "rtl/platform/sim/jtag_axi_master_sim.v",
                "board/top_jtag.v", "tb/tb_jtag_log.v"]


def _spi_loopback_vectors(workdir: Path, params: dict) -> list[str]:
    """Frames for tb_spi_loopback: corner bytes, then seeded random frames; each frame echoes 0xA5, then byte n-1."""
    import numpy as np

    from model.vectors import write_hex

    rng = np.random.default_rng(2027)
    frames = [[0x00, 0xFF, 0x55, 0xAA, 0x01, 0x80], [0x5A]] + [list(rng.integers(0, 256, size=int(rng.integers(1, 33))))
                                                               for _ in range(40)]
    tx, exp = [], []
    for frame in frames:
        tx += [int(b) for b in frame]
        exp += [0xA5] + [int(b) for b in frame[:-1]]
    write_hex(workdir / "tx.mem", tx, 8)
    write_hex(workdir / "exp.mem", exp, 8)
    write_hex(workdir / "len.mem", [len(f) for f in frames], 16)
    return [f"+tx={(workdir / 'tx.mem').as_posix()}", f"+exp={(workdir / 'exp.mem').as_posix()}",
            f"+len={(workdir / 'len.mem').as_posix()}", f"+frames={len(frames)}", f"+bytes={len(tx)}"]


def misc_benches() -> dict[str, Bench]:
    return {
        "governor": Bench("governor", "tb_governor", ["rtl/governor.v", "tb/tb_governor.v"], {}, _governor_vectors),
        "spi_slave": Bench("spi_slave", "tb_spi_slave", ["rtl/spi_slave.v", "tb/tb_spi_slave.v"]),
        "clkwiz_seq": Bench("clkwiz_seq", "tb_clkwiz_seq", ["rtl/clkwiz_seq.v", "tb/tb_clkwiz_seq.v"], {}, _clkwiz_vectors),
        "regfile_guard": Bench("regfile_guard", "tb_regfile_guard", ["rtl/regfile.v", "tb/tb_regfile_guard.v"]),
        "ws2812_tx": Bench("ws2812_tx", "tb_ws2812_tx", ["rtl/ws2812_tx.v", "tb/tb_ws2812_tx.v"]),
        "bringup": Bench("bringup", "tb_bringup", ["rtl/ws2812_tx.v", "fpga/bringup/blink/blink_top.v",
                                                   "fpga/bringup/vcco_probe/vcco_probe_top.v", "fpga/bringup/io_test/io_test_top.v",
                                                   "tb/tb_bringup.v"]),
        "spi_loopback": Bench("spi_loopback", "tb_spi_loopback", ["fpga/bringup/spi_loopback/spi_loopback_top.v",
                                                                "tb/tb_spi_loopback.v"], {}, _spi_loopback_vectors),
        "status_led": Bench("status_led", "tb_status_led", ["rtl/ws2812_tx.v", "rtl/status_led.v", "tb/tb_status_led.v"]),
        "xadc_temp": Bench("xadc_temp", "tb_xadc_temp", ["rtl/xadc_temp.v", "rtl/platform/sim/xadc_prim_sim.v", "tb/tb_xadc_temp.v"]),
        "jtag_session_xs": Bench(
            "jtag_session_xs", "tb_jtag_log", JTAG_SOURCES,
            {k: v for k, v in _engine_params("xs", 8).items() if k in ("K", "C3_EN", "WEIGHT_AW", "ACT0_AW", "ACT1_AW")},
            _jtag_log_vectors("xs"), slow=True, prefer_xsim=True,
        ),
        "spi_session_xs": Bench(
            "spi_session_xs", "tb_spi_log", [*TOP_SOURCES, "tb/tb_spi_log.v"],
            {k: v for k, v in _engine_params("xs", 8).items() if k != "LANE_IMPL"},
            _spi_log_vectors("xs"), slow=True, prefer_xsim=True,
        ),
    }


SYSTEM_SOURCES = [*TOP_SOURCES, "tb/tb_system.v"]

BENCHES: dict[str, Bench] = {
    **lane_array_benches(), **checker_benches(), **wc_gen_benches(), **engine_benches(), **misc_benches(), **system_benches(),
}

_W = {f"WC{i+1}_W": v for i, v in enumerate(wc_widths(8))}
LINT_TARGETS = [
    {"id": "regfile", "top": "regfile", "sources": ["rtl/regfile.v"]},
    {"id": "spi_loopback", "top": "spi_loopback_top", "sources": ["fpga/bringup/spi_loopback/spi_loopback_top.v"]},
    {"id": "top_core", "top": "top_core", "sources": TOP_SOURCES, "params": _W},
    {"id": "top_board", "top": "top_board", "sources": TOP_SOURCES + ["board/top_board.v"]},
    {"id": "top_jtag", "top": "top_jtag", "sources": TOP_SOURCES + ["rtl/axil_bus_bridge.v", "rtl/jtag_axi_master.v", "rtl/platform/sim/jtag_axi_master_sim.v", "board/top_jtag.v"]},
    {"id": "axil_bus_bridge", "top": "axil_bus_bridge", "sources": ["rtl/axil_bus_bridge.v"]},
    {"id": "spi_slave", "top": "spi_slave", "sources": ["rtl/spi_slave.v"]},
    {"id": "governor", "top": "governor", "sources": ["rtl/governor.v"]},
    {"id": "clk_seq", "top": "clk_seq", "sources": ["rtl/clk_seq.v"]},
    {"id": "clkwiz_seq", "top": "clkwiz_seq", "sources": ["rtl/clkwiz_seq.v"]},
    *[
        {"id": f"engine_c{c3}", "top": "engine", "sources": ENGINE_SOURCES, "params": {"C3_EN": c3, **_W}}
        for c3 in (0, 1)
    ],
    *[
        {"id": f"engine_c1_zs{zs}", "top": "engine", "sources": ENGINE_SOURCES, "params": {"C3_EN": 1, "ZERO_SKIP": zs, **_W}}
        for zs in (1, 2)
    ],
    *[
        {"id": f"wc_gen_k{k}_c1", "top": "wc_gen", "sources": ["rtl/sum_tree.v", "rtl/wc_gen.v"],
         "params": {"K": k, "C3_EN": 1, **{f"WC{i+1}_W": v for i, v in enumerate(wc_widths(k))}}}
        for k in (8, 16)
    ],
    {"id": "lane_lut", "top": "lane_lut", "sources": ["rtl/lane_lut.v"]},
    {"id": "lane_dsp_min", "top": "lane_dsp_min", "sources": ["rtl/lane_dsp_min.v"]},
    {"id": "lane_dsp_full", "top": "lane_dsp_full", "sources": ["rtl/lane_dsp_full.v"]},
    {"id": "checker_c0", "top": "lane_checker", "sources": ["rtl/lane_checker.v"], "params": {"C3_EN": 0}},
    {"id": "checker_c1", "top": "lane_checker", "sources": ["rtl/lane_checker.v"], "params": {"C3_EN": 1}},
    {"id": "checker_k16", "top": "lane_checker", "sources": ["rtl/lane_checker.v"], "params": {"K": 16, "C3_EN": 1}},
    *[
        {"id": f"lane_array_c{c3}_impl{impl}", "top": "lane_array", "sources": LANES,
         "params": {"C3_EN": c3, "LANE_IMPL": impl, **_W}}
        for c3 in (0, 1) for impl in (0, 1, 2)
    ],
]
