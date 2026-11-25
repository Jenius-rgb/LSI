"""M12: software stack on the mock backend. Everything here is [SYNTHETIC]."""
import csv
import json

import numpy as np

import pytest

from model import golden
from model.fault_model import FaultParams
from sentinel.backend import MockBackend
from sentinel.harness import write_csv, write_metadata
from sentinel.device_model import ModelDevice
from sentinel.driver import SentinelDriver
from sentinel.transport import LogTransport


def micro_qm():
    rng = np.random.default_rng(1)
    conv = golden.QLayer("conv1", "conv", rng.integers(-127, 128, size=(8, 3, 3, 3), dtype=np.int64),
                         rng.integers(-500, 500, size=8, dtype=np.int64), 9000, 18)
    fc = golden.QLayer("fc", "fc", rng.integers(-127, 128, size=(10, 8 * 4 * 4), dtype=np.int64),
                       rng.integers(-500, 500, size=10, dtype=np.int64), 0, 0)
    return golden.QModel("micro", (3, 8, 8), [conv, fc])


def images(n=4):
    return np.random.default_rng(2).integers(0, 256, size=(n, 3, 8, 8), dtype=np.uint8)


def backend(**fault):
    return MockBackend(micro_qm(), fault=FaultParams(seed=3, **fault), sparsity=[0.1, 0.3])


def test_mock_below_onset_is_clean_and_bit_exact():
    b = backend()
    b.set_frequency(100.0)
    for i, img in enumerate(images()):
        res = b.classify(img, image_id=i)
        assert res.logits == [int(v) for v in b.golden(img).logits]
        assert res.events == []


def test_mock_above_onset_produces_events_deterministically():
    a, b = backend(), backend()
    a.set_frequency(190.0)
    b.set_frequency(190.0)
    img = images(1)[0]
    ra, rb = a.classify(img, image_id=7), b.classify(img, image_id=7)
    assert ra.events and ra.events == rb.events


def test_mock_time_model_is_inverse_in_frequency():
    b = backend()
    img = images(1)[0]
    b.set_frequency(100.0)
    t100 = b.classify(img, image_id=0).fpga_time_s
    b.set_frequency(110.0)
    t110 = b.classify(img, image_id=0).fpga_time_s
    assert t110 == pytest.approx(t100 * 100.0 / 110.0, rel=1e-6)


def test_governor_runs_inside_mock():
    from model.governor import GovParams, reset

    b = backend()
    gov = GovParams(n_up=2, cooldown=1, corr_hi=4, l_min=0, l_max=3)
    b.gov_params, b.gov_state = gov, reset(gov, 2)
    b.enable_governor([100.0, 105.0, 110.0, 115.0])
    levels = []
    for i, img in enumerate(images(4)):
        levels.append(b.classify(img, image_id=i).level)
    assert levels[0] == 0 and max(levels) >= 1


def test_driver_session_against_device_model_is_consistent():
    qm = micro_qm()
    device = ModelDevice(qm, k=8)
    drv = SentinelDriver(LogTransport(device))
    identity = drv.read_id()
    assert identity.magic == b"SNTL" and identity.k == 8
    drv.write_image(images(1)[0].tobytes(), slot=0)
    drv.configure(mode=2)
    drv.start()
    drv.wait_done()
    gold = golden.forward(qm, images(1)[0])
    assert drv.result_class() == gold.pred
    assert drv.logits(10) == [int(v) for v in gold.logits]


def test_log_transport_records_framing(tmp_path):
    qm = micro_qm()
    t = LogTransport(ModelDevice(qm))
    SentinelDriver(t).read_id()
    n = t.write_log(tmp_path / "log.mem")
    lines = (tmp_path / "log.mem").read_text().split()
    assert len(lines) == n and lines[0].startswith("02") and lines[-1].startswith("ff")


def test_write_csv_and_metadata(tmp_path):
    write_csv(tmp_path / "data.csv", [{"a": 1, "b": 2}])
    with open(tmp_path / "data.csv", encoding="utf-8") as fh:
        assert list(csv.DictReader(fh))[0]["b"] == "2"
    write_metadata(tmp_path, "t", backend())
    meta = json.loads((tmp_path / "metadata.json").read_text(encoding="utf-8"))
    assert meta["backend"] == "mock" and meta["label"] == "[SYNTHETIC]" and "fault_model" in meta


def test_plot_watermark_applied_for_mock(tmp_path):
    from sentinel.plots import all as plots

    fig, ax = plots.figure("x", "mock", "a", "b")
    ax.plot([0, 1], [0, 1], label="s")
    out = tmp_path / "p.png"
    plots.finish(fig, ax, out, "mock")
    assert out.exists() and out.stat().st_size > 0


def test_validation_mode_reports_accuracy_and_timing(tmp_path):
    cv2 = pytest.importorskip("cv2")
    from sentinel.validate import run as validate_run

    qm = micro_qm()
    b = MockBackend(qm, fault=FaultParams(seed=3), sparsity=[0.1, 0.3])
    b.set_frequency(100.0)
    pred = b.classify(images(1)[0]).pred
    folder = tmp_path / "val"
    (folder / "a").mkdir(parents=True)
    (folder / "b").mkdir(parents=True)
    img = np.transpose(images(1)[0], (1, 2, 0))[:, :, ::-1]
    for name in ("a", "b"):
        cv2.imwrite(str(folder / name / "x.png"), cv2.resize(img, (64, 64), interpolation=cv2.INTER_NEAREST))
    report = validate_run(_Resize(b), folder)
    assert report["images"] == 2 and report["accuracy"] is not None
    assert report["fpga_latency_ms_mean"] > 0 and report["end_to_end_latency_ms_mean"] > 0 and pred >= 0


class _Resize:
    """Adapter: validation preprocess gives 32x32, the micro model expects 8x8."""

    def __init__(self, b):
        self.b = b
        self.name = b.name

    def classify(self, image, image_id=None):
        return self.b.classify(image[:, ::4, ::4], image_id=image_id)


def test_camera_mode_and_dashboard_with_video_file(tmp_path):
    cv2 = pytest.importorskip("cv2")
    pytest.importorskip("flask")
    from sentinel.camera_mode import run as camera_run
    from sentinel.dashboard import State, create_app

    path = str(tmp_path / "v.avi")
    writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"MJPG"), 10, (64, 64))
    assert writer.isOpened()
    for i in range(5):
        frame = np.full((64, 64, 3), i * 40, dtype=np.uint8)
        writer.write(frame)
    writer.release()
    b = _Resize(MockBackend(micro_qm(), fault=FaultParams(seed=3), sparsity=[0.1, 0.3]))
    report = camera_run(b, path, max_frames=5)
    assert report["frames"] == 5 and report["fps"] > 0

    state = State(b)
    res = b.classify(np.zeros((3, 32, 32), dtype=np.uint8), image_id=0)
    state.update(np.zeros((16, 16, 3), dtype=np.uint8), res, 12.3)
    client = create_app(state).test_client()
    stats = client.get("/stats.json").get_json()
    assert "NOT MEASURED" in stats["label"] and stats["values"]["FPS"] == "12.3"
    assert client.get("/frame.jpg").status_code == 200
    assert client.get("/").status_code == 200


def test_every_experiment_script_exists_and_runs_help():
    import importlib

    for name in ("e1", "e2", "e3", "e4", "e5", "e6", "e7", "e8"):
        mod = importlib.import_module(f"sentinel.experiments.{name}")
        assert callable(mod.main)


class _FakeDoneLine:
    def __init__(self, active: bool):
        self.active = active
        self.waits: list[float] = []

    def wait(self, timeout_s: float) -> bool:
        self.waits.append(timeout_s)
        return self.active


def test_driver_waits_on_the_done_line_instead_of_polling():
    """ADR-016: irq_done on RP_GPIO25 is high while STATUS.DONE is set."""
    from sentinel.transport import OP_POLL

    qm = micro_qm()
    transport = LogTransport(ModelDevice(qm, k=8))
    line = _FakeDoneLine(active=True)
    drv = SentinelDriver(transport, done_line=line)
    drv.write_image(images(1)[0].tobytes(), slot=0)
    drv.configure(mode=2)
    drv.start()
    drv.wait_done(timeout_s=2.0)
    assert line.waits == [2.0]
    assert not any(entry >> 24 == OP_POLL for entry in transport.entries)
    assert drv.result_class() == golden.forward(qm, images(1)[0]).pred


def test_driver_done_line_timeout_and_disagreement():
    qm = micro_qm()
    drv = SentinelDriver(LogTransport(ModelDevice(qm, k=8)), done_line=_FakeDoneLine(active=False))
    with pytest.raises(TimeoutError):
        drv.wait_done(timeout_s=0.1)
    # The line reads high although nothing was started: the driver checks STATUS.DONE before it believes the line.
    drv = SentinelDriver(LogTransport(ModelDevice(qm, k=8)), done_line=_FakeDoneLine(active=True))
    with pytest.raises(RuntimeError):
        drv.wait_done()


def test_xadc_code_to_celsius_follows_ug480():
    """UG480 Equation 2-6: T = code * 503.975 / 4096 - 273.15 (ADR-023)."""
    from sentinel.xadc import code_to_celsius, temperature_from_register

    assert code_to_celsius(0) == pytest.approx(-273.15)
    assert code_to_celsius(2423) == pytest.approx(2423 * 503.975 / 4096 - 273.15)
    assert 24.9 < code_to_celsius(2423) < 25.0
    assert temperature_from_register((1 << 16) | 2423) == pytest.approx(code_to_celsius(2423))
    assert temperature_from_register(2423) is None   # VALID clear: no reading yet
    with pytest.raises(ValueError):
        code_to_celsius(4096)


def test_device_model_reports_the_simulated_temperature():
    from sentinel import regmap as rm

    drv = SentinelDriver(LogTransport(ModelDevice(micro_qm(), k=8)))
    assert drv.read_reg(rm.REG_TEMP) == (1 << rm.TEMP_VALID_LSB) | 2423
    assert 24.9 < drv.temperature_c() < 25.0


class _FakeButton:
    def __init__(self):
        self.when_pressed = None

    def press(self):
        self.when_pressed()


def test_buttons_start_stop_run_drive_the_camera_loop():
    """M19 (ADR-016): START runs continuously, STOP pauses, RUN classifies one frame while paused."""
    from sentinel.buttons import ButtonControl

    start, stop, run = _FakeButton(), _FakeButton(), _FakeButton()
    ctl = ButtonControl(start, stop, run)
    assert ctl.should_classify() is False          # paused until START
    run.press()
    assert ctl.should_classify() is True and ctl.should_classify() is False   # one frame only
    start.press()
    assert all(ctl.should_classify() for _ in range(3))
    stop.press()
    assert ctl.should_classify() is False


def test_camera_loop_skips_frames_while_paused(monkeypatch):
    import numpy as np

    from sentinel import camera_mode
    from sentinel.buttons import ButtonControl

    frames = [np.zeros((48, 64, 3), dtype=np.uint8)] * 5
    monkeypatch.setattr(camera_mode, "open_source", lambda source: iter(frames))
    calls = []

    class Backend:
        def classify(self, image, image_id=None):
            calls.append(image_id)
            return type("R", (), {"pred": 1})()

    start, stop, run = _FakeButton(), _FakeButton(), _FakeButton()
    ctl = ButtonControl(start, stop, run)
    run.press()
    report = camera_mode.run(Backend(), "x", control=ctl)
    assert report["frames"] == 1 and report["skipped"] == 4 and calls == [0]


def test_pi_check_reports_what_it_finds(tmp_path):
    """board/pi_check.py on a fake Pi file system (ADR-022)."""
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("pi_check", Path(__file__).resolve().parents[1] / "board" / "pi_check.py")
    pc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pc)
    model = tmp_path / "model"
    model.write_bytes(b"Raspberry Pi 4 Model B Rev 1.5\x00")
    dev = tmp_path / "spidev0.0"
    dev.write_text("")
    rows = pc.check(model_path=model, spidev_path=dev, modules=("json", "no_such_module_xyz"))
    assert rows["model"] == ("ok", "Raspberry Pi 4 Model B Rev 1.5")
    assert rows["spidev0.0"][0] == "ok"
    assert rows["import json"][0] == "ok" and rows["import no_such_module_xyz"][0] == "missing"
    rows = pc.check(model_path=tmp_path / "none", spidev_path=tmp_path / "none", modules=())
    assert rows["model"][0] == "missing" and rows["spidev0.0"][0] == "missing"


def test_jtag_transport_runs_a_driver_session_against_the_device_model():
    """ADR-025 dry run: the unchanged SentinelDriver over JTAG-to-AXI word transactions classifies like the golden model."""
    from sentinel.transport_jtag import JtagAxiTransport, SimulatedAxi

    qm = micro_qm()
    axi = SimulatedAxi(ModelDevice(qm, k=8))
    drv = SentinelDriver(JtagAxiTransport(axi))
    identity = drv.read_id()
    assert identity.magic == b"SNTL" and identity.k == 8
    drv.write_image(images(1)[0].tobytes(), slot=0)
    drv.configure(mode=2)
    drv.start()
    drv.wait_done()
    gold = golden.forward(qm, images(1)[0])
    assert drv.result_class() == gold.pred and drv.logits(10) == [int(v) for v in gold.logits]
    assert axi.writes > 0 and axi.reads > 0


def test_jtag_transport_never_does_partial_register_writes():
    from sentinel.transport_jtag import JtagAxiTransport, SimulatedAxi

    t = JtagAxiTransport(SimulatedAxi(ModelDevice(micro_qm(), k=8)))
    with pytest.raises(ValueError):
        t.xfer(bytes([0x02, 0x00, 0x00, 0x05, 0xAA]))      # one byte into a register: refused
    t.xfer(bytes([0x02, 0x03, 0x00, 0x01, 0x11, 0x22]))     # two bytes into image memory: read-modify-write
    rx = t.xfer(bytes([0x03, 0x03, 0x00, 0x00, 0x00, 0, 0, 0, 0]))
    assert rx[6:8] == bytes([0x11, 0x22])


def test_jtag_recording_writes_a_replayable_log(tmp_path):
    from sentinel.transport_jtag import OP_END, OP_POLL, JtagAxiTransport, RecordingAxi, SimulatedAxi

    rec = RecordingAxi(SimulatedAxi(ModelDevice(micro_qm(), k=8)))
    drv = SentinelDriver(JtagAxiTransport(rec))
    drv.read_id()
    drv.configure(mode=2)
    drv.start()
    drv.wait_done()
    n = rec.write_log(tmp_path / "jtag.mem")
    words = [int(w, 16) for w in (tmp_path / "jtag.mem").read_text().split()]
    assert len(words) == n and words[-4] >> 24 == OP_END and any(w >> 24 == OP_POLL for w in words[::4])


def test_vivado_tcl_commands_for_axi_transactions():
    from sentinel.transport_jtag import VivadoTclAxi

    w = VivadoTclAxi.write_command(0x030000, 0x11223344)
    assert "create_hw_axi_txn" in w and "-type write" in w and "-address 00030000" in w and "-data 11223344" in w and "run_hw_axi" in w
    r = VivadoTclAxi.read_command(0x000004)
    assert "-type read" in r and "-address 00000004" in r and "get_property DATA" in r


def test_camera_mode_runs_on_a_video_file_without_a_pi(tmp_path):
    """docs/CAMERA.md: the camera path works on a laptop with a video file and MockBackend [SYNTHETIC]."""
    import cv2
    import numpy as np

    from sentinel import camera_mode
    from sentinel.harness import make_backend

    path = tmp_path / "clip.avi"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10, (64, 48))
    assert writer.isOpened()
    rng = np.random.default_rng(2027)
    for _ in range(12):
        writer.write(rng.integers(0, 256, size=(48, 64, 3), dtype=np.uint8))
    writer.release()
    backend, _ = make_backend("xs")
    report = camera_mode.run(backend, str(path), max_frames=10)
    assert report["frames"] == 10 and report["last_pred"] is not None


def test_hw_metadata_names_the_lane_variant():
    """ADR-030 condition 3: every [HW] result file names its lane variant, read from the ID flags (SPEC 12.2)."""
    from sentinel.backend import HwBackend
    from sentinel.driver import lane_variant

    assert lane_variant(0b0011) == {"lane_impl": "lut", "inj_hw": True, "c3_hw": True}
    assert lane_variant(0b0111)["lane_impl"] == "dsp_min" and lane_variant(0b1000)["lane_impl"] == "dsp_full"
    qm = micro_qm()
    drv = SentinelDriver(LogTransport(ModelDevice(qm, k=8, flags=0b0111)))
    meta = HwBackend(drv, qm, 8, 10, 125.0).metadata()
    assert meta["lane_impl"] == "dsp_min" and meta["c3_hw"] and meta["label"] == "[HW]"


def test_pi_check_requires_lgpio_on_a_pi5(tmp_path):
    """On a Raspberry Pi 5 only the lgpio pin factory of gpiozero works (gpiozero docs, api_pins); pi_check says so."""
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("pi_check", Path(__file__).resolve().parents[1] / "board" / "pi_check.py")
    pc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pc)
    assert "lgpio" in pc.MODULES and "RPi" not in " ".join(pc.MODULES)
    assert pc.gpio_note("Raspberry Pi 5 Model B Rev 1.0", has_lgpio=False).startswith("missing")
    assert pc.gpio_note("Raspberry Pi 5 Model B Rev 1.0", has_lgpio=True).startswith("ok")


def test_gpio_lines_use_the_lgpio_factory(monkeypatch):
    """GPIO users pick gpiozero's lgpio factory explicitly and fail with an install hint when it is missing."""
    import sys
    import types

    import pytest
    from sentinel import transport

    monkeypatch.setitem(sys.modules, "gpiozero.pins.lgpio", None)
    with pytest.raises(RuntimeError, match="lgpio"):
        transport.lgpio_factory()
    fake = types.ModuleType("gpiozero.pins.lgpio")
    fake.LGPIOFactory = lambda: "lgpio-factory"
    monkeypatch.setitem(sys.modules, "gpiozero.pins.lgpio", fake)
    assert transport.lgpio_factory() == "lgpio-factory"
