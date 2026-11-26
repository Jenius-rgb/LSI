"""M2: memory image layout, bit-bound checks (SPEC 3.6) and export determinism."""
import numpy as np
import pytest

from model import export, golden


def tiny_model(cout=5, n=3):
    """A conv layer with Cout not a multiple of K and a small FC layer."""
    rng = np.random.default_rng(11)
    conv = golden.QLayer(
        "conv1", "conv", rng.integers(-127, 128, size=(cout, 3, 3, 3), dtype=np.int64),
        rng.integers(-500, 500, size=cout, dtype=np.int64), 12345, 22,
    )
    fc = golden.QLayer(
        "fc", "fc", rng.integers(-127, 128, size=(n, cout * 2 * 2), dtype=np.int64),
        rng.integers(-500, 500, size=n, dtype=np.int64), 0, 0,
    )
    return golden.QModel("tiny", (3, 4, 4), [conv, fc])


ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
HW = {"K": 4, "ACT_W": 8, "W_W": 8, "ACC_W": 32, "ACC_CS_W": 48, "N_CLASSES_MAX": 16}


def test_weight_words_follow_group_t_lane_order():
    qm = tiny_model()
    img = export.memory_image(qm, HW)
    conv = qm.layers[0]
    # Cout=5, K=4 -> 2 groups of T=27 words.
    for g in range(2):
        for t in range(27):
            c, s = divmod(t, 9)
            i, j = divmod(s, 3)
            word = img.weights[g * 27 + t]
            for k in range(4):
                o = g * 4 + k
                expected = conv.w[o, c, i, j] if o < 5 else 0
                assert word[k] == expected


def test_fc_words_follow_input_index():
    qm = tiny_model()
    img = export.memory_image(qm, HW)
    fc = qm.layers[1]
    base = 2 * 27
    for t in range(fc.w.shape[1]):
        word = img.weights[base + t]
        for k in range(3):
            assert word[k] == fc.w[k, t]
        assert word[3] == 0


def test_bias_entries_are_padded_to_whole_groups():
    qm = tiny_model()
    img = export.memory_image(qm, HW)
    conv, fc = qm.layers
    assert img.bias[:5].tolist() == conv.b.tolist()
    assert img.bias[5:8].tolist() == [0, 0, 0]
    assert img.bias[8:11].tolist() == fc.b.tolist()
    assert img.bias[11:].tolist() == [0]


def test_layer_records_carry_addresses_and_requant():
    qm = tiny_model()
    img = export.memory_image(qm, HW)
    rec = img.records
    assert rec[0]["kind"] == 0 and rec[1]["kind"] == 1
    assert rec[0]["t"] == 27 and rec[0]["g"] == 2
    assert rec[1]["t"] == 20 and rec[1]["g"] == 1
    assert rec[0]["wbase"] == 0 and rec[1]["wbase"] == 54
    assert rec[0]["bbase"] == 0 and rec[1]["bbase"] == 8
    assert (rec[0]["m"], rec[0]["n"]) == (12345, 22)
    assert rec[0]["src_sel"] == export.SRC_IMG
    assert rec[0]["dst_sel"] == export.BUF_ACT0
    assert rec[1]["src_sel"] == export.BUF_ACT0


def test_packed_records_roundtrip():
    qm = tiny_model()
    img = export.memory_image(qm, HW)
    for rec, words in zip(img.records, img.record_words()):
        assert len(words) == export.RECORD_WORDS
        assert export.unpack_record(words) == rec


def test_bit_bounds_pass_for_valid_model():
    qm = tiny_model()
    report = export.check_bit_bounds(qm, HW)
    assert report[0]["acc_max"] <= 2**31 - 1


def test_bit_bounds_reject_narrow_accumulator():
    qm = tiny_model()
    with pytest.raises(export.BitBoundError):
        export.check_bit_bounds(qm, {**HW, "ACC_W": 12})


def test_bit_bounds_reject_narrow_checksum_accumulator():
    qm = tiny_model()
    with pytest.raises(export.BitBoundError):
        export.check_bit_bounds(qm, {**HW, "ACC_CS_W": 16})


def test_bit_bounds_reject_v_times_m_overflow():
    qm = tiny_model()
    qm.layers[0].b[0] = 2**30
    with pytest.raises(export.BitBoundError):
        export.check_bit_bounds(qm, {**HW, "PROD_W": 40})


def test_bit_bounds_reject_weight_out_of_range():
    qm = tiny_model()
    qm.layers[0].w[0, 0, 0, 0] = -128
    with pytest.raises(export.BitBoundError):
        export.check_bit_bounds(qm, HW)


def test_export_is_deterministic(tmp_path):
    qm = tiny_model()
    a = export.write_artifacts(qm, HW, tmp_path / "a")
    b = export.write_artifacts(qm, HW, tmp_path / "b")
    assert a["sha256"] == b["sha256"]
    assert (tmp_path / "a" / "tiny_k4.manifest.json").read_bytes() == (tmp_path / "b" / "tiny_k4.manifest.json").read_bytes()
    assert (tmp_path / "a" / "tiny_k4.bin").read_bytes() == (tmp_path / "b" / "tiny_k4.bin").read_bytes()


def test_mem_files_match_binary_words(tmp_path):
    qm = tiny_model()
    export.write_artifacts(qm, HW, tmp_path)
    img = export.memory_image(qm, HW)
    lines = (tmp_path / "tiny_k4_weights.mem").read_text().split()
    assert len(lines) == len(img.weights)
    for line, word in zip(lines, img.weights):
        # Lane 0 is the least significant byte of the word.
        expected = "".join(f"{int(v) & 0xff:02x}" for v in reversed(word.tolist()))
        assert line == expected
    params = (tmp_path / "tiny_k4_params.mem").read_text().split()
    assert all(len(p) == 8 for p in params)


def test_manifest_carries_the_class_names_of_model_s4(tmp_path):
    """The Pi software reads the class order from the manifest (ADR-037: cat, dog, deer, horse)."""
    from model.golden import QModel

    qm = QModel.load(ROOT / "results" / "model" / "s4" / "quant.npz")
    manifest = export.write_artifacts(qm, {**HW, "K": 8}, tmp_path)
    assert manifest["classes"] == ["cat", "dog", "deer", "horse"]


def test_zero7_config_runs_the_official_model_and_its_memories_fit(tmp_path):
    """config/hw_zero7.yaml names the model of the official build; its address widths must hold that model.
    ADR-037 made it s4; ADR-040 (26 Nov 2026) replaced it by s4b, the same layers with camera-style training."""
    import yaml
    from model.golden import QModel

    cfg = yaml.safe_load((ROOT / "config" / "hw_zero7.yaml").read_text(encoding="utf-8"))
    assert cfg["MODEL"] == "s4b"
    qm = QModel.load(ROOT / "results" / "model" / cfg["MODEL"] / "quant.npz")
    manifest = export.write_artifacts(qm, {**HW, "K": cfg["K"]}, tmp_path)
    assert manifest["weight_words"] <= 2 ** cfg["WEIGHT_AW"]
    assert manifest["buffer_bytes"]["act0"] <= 2 ** cfg["ACT0_AW"] and manifest["buffer_bytes"]["act1"] <= 2 ** cfg["ACT1_AW"]
