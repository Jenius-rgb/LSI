"""M0: the command-line entry points exist and report honestly."""
import subprocess
import sys
from pathlib import Path

import check_env
import pytest

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_COMMANDS = {"check", "test", "gen", "train", "export", "sim", "campaign", "ooc", "plots"}


def test_run_py_lists_every_required_subcommand():
    out = subprocess.run(
        [sys.executable, "tools/run.py", "--help"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    missing = {c for c in REQUIRED_COMMANDS if c not in out}
    assert not missing, f"run.py lacks: {missing}"


def test_run_py_rejects_unknown_subcommand():
    res = subprocess.run([sys.executable, "tools/run.py", "nope"], cwd=ROOT, capture_output=True, text=True)
    assert res.returncode != 0


def test_detect_reports_this_interpreter():
    tools = {t.name: t for t in check_env.detect()}
    assert tools["python"].found
    assert tools["python"].version.split(".")[:2] == [str(sys.version_info[0]), str(sys.version_info[1])]
    for name in ("iverilog", "vvp", "vivado", "verilator (lint)", "torch"):
        assert name in tools


def test_missing_tool_is_reported_not_faked():
    report = check_env.report([check_env.Tool("ghost", False), check_env.Tool("opt", False, required=False)])
    assert "MISSING" in report and "absent" in report


def test_cifar10_4_keeps_only_the_official_classes_in_official_order(monkeypatch):
    """ADR-037: dataset cifar10_4 = CIFAR-10 images of cat, dog, deer, horse, relabelled 0..3 in that order."""
    import numpy as np
    from model import data

    names = ["airplane", "automobile", "bird", "cat", "deer", "dog", "frog", "horse", "ship", "truck"]
    labels = np.arange(10).repeat(2)
    full = data.ImageSet(np.zeros((20, 3, 32, 32), dtype=np.uint8) + labels[:, None, None, None].astype(np.uint8), labels, names)
    monkeypatch.setattr(data, "load_cifar10", lambda train, **kw: full)
    tr, te = data.load_dataset("cifar10_4")
    assert tr.classes == ["cat", "dog", "deer", "horse"] and te.classes == tr.classes
    assert list(tr.labels) == [0, 0, 2, 2, 1, 1, 3, 3]
    assert list(tr.images[:, 0, 0, 0]) == [3, 3, 4, 4, 5, 5, 7, 7]  # original CIFAR-10 label of each kept image


def test_model_s4_is_s_with_four_classes():
    from model.config import load_model_config

    s, s4 = load_model_config("s"), load_model_config("s4")
    assert s4["n_classes"] == 4 and s4["layers"] == s["layers"] and s4["classes"] == ["cat", "dog", "deer", "horse"]


@pytest.mark.parametrize("model", ["micro", "s", "s4", "xs"])
def test_every_unit_is_long_enough_for_the_result_serializer(model):
    """Without zero-skip a unit lasts t cycles; the lane-array serializer needs K + 2 + C3 cycles per unit. A model whose
    shortest unit were shorter (e.g. a 1-channel 3x3 layer, t = 9) would overrun it even with ZERO_SKIP = 0."""
    from model.config import layer_shapes, load_model_config, result_words, shortest_unit

    name, t = shortest_unit(layer_shapes(load_model_config(model)))
    for k in (8, 16):          # SPEC 13: K in {8, 16}
        for c3 in (0, 1):
            assert t >= result_words(k, c3), f"{model} {name}: t = {t} < {result_words(k, c3)} (K = {k}, C3 = {c3})"


def test_zs_compare_reads_progress_lines_and_ignores_lines_after_a_fail(tmp_path):
    import zs_compare

    unguarded, fixed = tmp_path / "u", tmp_path / "f"
    unguarded.mkdir()
    fixed.mkdir()
    (unguarded / "a_s0.log").write_text("IMG 0 done cycles=100\nIMG 1 done cycles=90\n", encoding="utf-8")
    (unguarded / "a_s1.log").write_text("IMG 2 done cycles=95\nFAIL lane_array: overrun\nIMG 3 done cycles=999\n",
                                        encoding="utf-8")
    (fixed / "b.log").write_text("IMG 0 done cycles=100\nIMG 1 done cycles=93\nIMG 2 done cycles=95\nIMG 3 done cycles=97\n"
                                 "PASS 4/4\n", encoding="utf-8")
    rep = zs_compare.compare(200, {"unguarded": unguarded, "fixed": fixed})
    assert rep["runs"]["unguarded"]["images_passed"] == 3          # image 3 came after the FAIL
    assert rep["runs"]["fixed"]["mean_cycles"] == 96.2
    assert rep["runs"]["fixed"]["guard_cost_vs_unguarded"] == {
        "images": 3, "total_cycles": 3, "max_per_image": 3, "images_with_cost": 1, "min_per_image": 0}
    assert rep["runs"]["fixed"]["saving_vs_baseline_pct"] == 51.88


def test_model_names_come_from_the_config_folder():
    """CLI model choices follow config/model_*.yaml (ADR-040 adds s4a without editing five lists); micro stays test-only."""
    from model.config import model_names

    names = model_names()
    assert {"s", "s4", "s4a", "xs"} <= set(names) and "micro" not in names and names == sorted(names)
