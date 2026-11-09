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


ENGINE_SOURCES = [
    *LANES, "rtl/lane_checker.v", "rtl/ram_tdp.v", "rtl/sum_tree.v", "rtl/wc_gen.v", "rtl/operand_gen.v",
    "rtl/postproc.v", "rtl/pool.v", "rtl/counter_bank.v", "rtl/cdc_fifo.v", "rtl/platform/sim/cdc_fifo_sim.v",
    "rtl/fast_path.v", "rtl/engine.v",
]


def _engine_vectors(model: str, count: int):
    def gen(workdir: Path, params: dict) -> list[str]:
        from model.config import layer_shapes, load_model_config
        from model.vectors import engine_vectors

        k = params["K"]
        ideal = sum(s.ideal_cycles(k) for s in layer_shapes(load_model_config(model)))
        v = engine_vectors(model, k, count, workdir)
        return [
            f"+weights={v['weights']}", f"+params={v['params']}", f"+images={v['images']}",
            f"+logits={v['logits']}", f"+classes={v['classes']}", f"+nclasses={v['n_classes']}",
            f"+ideal={ideal}", "+first=0", f"+count={count}",
        ]

    return gen


def _engine_params(model: str, k: int, c3: int = 0, impl: int = 0) -> dict:
    wc1, wc2, wc3 = wc_widths(k)
    aw = {"s": (13, 11), "xs": (12, 10)}[model]
    words = {("s", 8): 12, ("s", 16): 11, ("xs", 8): 11, ("xs", 16): 10}[(model, k)]
    return {"K": k, "C3_EN": c3, "LANE_IMPL": impl, "WC1_W": wc1, "WC2_W": wc2, "WC3_W": wc3,
            "WEIGHT_AW": words, "ACT0_AW": aw[0], "ACT1_AW": aw[1]}


def engine_benches() -> dict[str, Bench]:
    out = {}
    # Quick smoke runs (part of `run.py test`), then the full DoD regressions (slow, xsim).
    for model, k, count, slow, shards in [
        ("xs", 8, 2, False, 1),
        ("s", 8, 1, False, 1),
        ("xs", 8, 200, True, 6),
        ("s", 8, 200, True, 6),
        ("s", 16, 20, True, 4),
    ]:
        name = f"engine_{model}_k{k}" + (f"_n{count}" if count >= 20 else "")
        out[name] = Bench(
            name, "tb_engine", [*ENGINE_SOURCES, "tb/tb_engine.v"], _engine_params(model, k),
            _engine_vectors(model, count), slow=slow, shards=shards, prefer_xsim=slow,
        )
    return out


def misc_benches() -> dict[str, Bench]:
    return {
        "spi_slave": Bench("spi_slave", "tb_spi_slave", ["rtl/spi_slave.v", "tb/tb_spi_slave.v"]),
    }


BENCHES: dict[str, Bench] = {**lane_array_benches(), **checker_benches(), **engine_benches(), **misc_benches()}

_W = {f"WC{i+1}_W": v for i, v in enumerate(wc_widths(8))}
LINT_TARGETS = [
    {"id": "spi_slave", "top": "spi_slave", "sources": ["rtl/spi_slave.v"]},
    *[
        {"id": f"engine_c{c3}", "top": "engine", "sources": ENGINE_SOURCES, "params": {"C3_EN": c3, **_W}}
        for c3 in (0, 1)
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
