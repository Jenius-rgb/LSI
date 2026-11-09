"""M7: the generated register map is current and the YAML is self-consistent."""
import gen_regmap


def test_generated_files_are_up_to_date():
    for path, text in gen_regmap.outputs().items():
        assert path.read_text(encoding="utf-8") == text, f"{path} is stale; run tools/run.py gen --regmap"


def test_register_offsets_are_unique_and_word_aligned():
    rm = gen_regmap.load()
    offsets = [r["offset"] for r in rm["registers"]]
    assert len(set(offsets)) == len(offsets)
    assert all(o % 4 == 0 and o < rm["counters"]["base"] for o in offsets)


def test_fields_fit_and_do_not_overlap():
    rm = gen_regmap.load()
    for reg in rm["registers"]:
        used = 0
        for name, lsb, width in gen_regmap._fields(reg):
            mask = ((1 << width) - 1) << lsb
            assert lsb + width <= 32, f"{reg['name']}.{name}"
            assert used & mask == 0, f"{reg['name']}.{name} overlaps"
            used |= mask


def test_memory_regions_do_not_overlap():
    regions = sorted((m["base"], m["base"] + m["size"]) for m in gen_regmap.load()["memory"].values())
    for (_, end), (start, _) in zip(regions, regions[1:]):
        assert end <= start


def test_required_registers_of_spec_12_4_exist():
    names = {r["name"] for r in gen_regmap.load()["registers"]}
    for required in (
        "ID", "VERSION", "CTRL", "STATUS", "RESULT_CLASS", "CYCLES_TOTAL", "CYCLES_RECOMPUTE", "STARVE_CYCLES",
        "GOV_CTRL", "GOV_PARAM", "GOV_STATE", "CLK_CTRL", "CLK_STATUS", "INJ0_CTRL", "INJ1_CTRL", "LANE_STATUS", "TEMP",
    ):
        assert required in names
