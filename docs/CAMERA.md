# Camera: required or not, and which one

Written 17 Nov 2026. Rule text from `docs/official/GUIDE_LSI_2027_FINALE.pdf` (English pages, read by OCR
of the rendered pages) and from `https://www.lsi-contest.com/shiyou_1.html` (Japanese, fetched and decoded
from Shift_JIS locally on 17 Nov 2026). Translations are ours.

## 1. What the official text says

| Where | Original | Translation |
| --- | --- | --- |
| Purpose, conditions (EN, G-5) | "Specified image validation data" / "Real-time camera input" | data validasi gambar yang ditentukan / input kamera real-time |
| Purpose, conditions (JP) | 指定画像検証データ / カメラ実時間入力 | data validasi gambar yang ditentukan / input kamera waktu nyata |
| Task (EN, G-5) | "Your system reads the images from a camera, an SD card, etc. and recognizes them." | sistem membaca gambar dari kamera, kartu SD, dan sebagainya, lalu mengenalinya |
| Task (JP) | カメラやSDカードなどから画像を読みその画像を認識してもらいます | gambar dibaca dari kamera, kartu SD, dan sebagainya, lalu dikenali |
| Presentation (EN, G-5) | "show how fast the recognition results are output" | tunjukkan seberapa cepat hasil pengenalan keluar |
| Class 2 (EN, G-6) | "the task is free (not limited to image classification)" | tugasnya bebas (tidak terbatas klasifikasi gambar) |
| Class 2 (JP) | 課題は自由です（画像分類に限りません） | tugasnya bebas (tidak terbatas klasifikasi gambar) |
| Raspberry Pi role (EN, G-4) | "you can use the interfaces of the Raspberry Pi (camera input and monitor output)" | antarmuka Raspberry Pi (input kamera dan keluaran monitor) bisa dipakai |

## 2. Answer

- **Class 1 (image classification):** [OFFICIAL] the purpose lists real-time camera input as a condition, next to
  the specified validation data. A camera is needed.
- **Class 2 (ZERO7, free task):** [UNKNOWN]. The conditions sit in the general "Purpose" section, but Class 2 says
  the task is free. Whether a Class 2 project that does image classification must still show real-time camera
  input is not written. Question Q2 for the organisers (`STATUS.md`).
- **For SENTINEL:** it targets Class 2 Level 3 but keeps the Class 1 requirements (CLAUDE.md section 7), and it
  does image classification. Treat the camera as **required**: it costs little and removes a risk.
- On the day, validation images may come "from a camera, an SD card, etc." [OFFICIAL], so the validation mode
  (files) and the camera mode both stay.

## 3. Which camera

The CNN input is 32 × 32, so resolution does not matter. Prices are list prices on the pages below, opened on
17 Nov 2026, in US dollars; prices in Indonesia differ.

| Option | Price seen | Works on Pi 4 | Works on the laptop now | Notes |
| --- | --- | --- | --- | --- |
| USB webcam, e.g. Logitech C270 | $29.99 (logitech.com, en-us) | through OpenCV / V4L2 [INFERENCE: UVC, the page does not state it] | yes, OpenCV with `--source 0` | no ribbon cable; same code on laptop and Pi |
| CSI module with OV5647, e.g. Waveshare RPi Camera (B) | $15.99 (waveshare.com) | yes, the page lists "Raspberry Pi 5 / 4B" | no | cheapest; picamera2; ribbon cable is fragile |
| Raspberry Pi Camera Module 3 (Sony IMX708) | "Available from $25" (raspberrypi.com) | yes; connector "15 × 1mm FPC" | no | official module, best supported by picamera2 |
| Raspberry Pi Camera Module 2 (Sony IMX219) | no price on the official page | yes ("works with all models of Raspberry Pi computers") | no | not compared on price |

**Recommendation:** a USB (UVC) webcam if the team has none yet. It is the only option that can be tested today
on the laptop with the same code, and it moves to the Pi 4 unchanged (`--source 0`). If the team wants the CSI
look for the demo, the OV5647 module is the cheapest and Camera Module 3 the best supported. Check that the
webcam works without a driver on Linux (UVC) before buying.

### Cheapest workable choice (added 17 Nov 2026, same sources)

1. **A USB webcam the team already owns costs nothing** and is enough: the network sees 32 × 32 pixels, so 640 × 480
   or 720p is plenty. Check that it works on Linux without a driver (UVC) before relying on it.
2. If one must be bought: the **cheapest price seen** is the OV5647 CSI module ($15.99, waveshare.com). Two risks:
   it only works with the Raspberry Pi (not testable on the laptop now), and its ribbon cable must reach the Pi 4's CSI
   connector while ZERO7 sits on the GPIO header. Whether ZERO7 leaves room for that ribbon is [UNKNOWN] (no board
   drawing in `docs/official/`); check it during board inspection (`board/BRINGUP_NO_PI.md` step 1) before buying.
3. Otherwise a **generic UVC USB webcam** is the safe economical buy: the same code runs on the laptop and the Pi 4,
   and no ribbon has to pass the HAT. Local prices in Indonesia were not checked; any UVC model with 640 × 480 or more
   will do, so the cheapest UVC listing is acceptable.
4. **Not recommended now: a bare camera sensor wired straight to the FPGA's PMOD pins** (e.g. an OV7670-class module).
   It would remove the Pi from the camera path, but needs new RTL (sensor configuration over SCCB/I²C, pixel capture,
   down-scaling to 32 × 32), about 14 FPGA pins (both PMOD headers), and the PMOD bank voltage is still [INFERENCE]
   (ADR-024). Not worth the risk before the freeze (17 Jan 2027); no price was checked for it.

Sources:
- https://www.raspberrypi.com/products/camera-module-3/
- https://www.raspberrypi.com/products/camera-module-v2/
- https://www.waveshare.com/rpi-camera-b.htm
- https://www.logitech.com/en-us/shop/p/c270-hd-webcam

## 4. Testing without the Pi

The camera mode (`sw/sentinel/camera_mode.py`) runs on the laptop with `MockBackend`, so the whole path
(capture, centre crop, resize to 32 × 32, classify) can be checked before the Pi and the board are there.
Results are [SYNTHETIC]: the mock stands in for the FPGA.

```
cd sw
python -m sentinel.camera_mode --source ../build/camera_dryrun.avi --model xs --frames 60   # a video file
python -m sentinel.camera_mode --source 0 --model xs --frames 100                          # the laptop webcam
```

- Done on 17 Nov 2026 with a generated 60-frame video: `[SYNTHETIC] frames 60` (the frame rate printed is the
  laptop running the mock, not the accelerator).
- `tests/test_software.py::test_camera_mode_runs_on_a_video_file_without_a_pi` writes a video with OpenCV and
  runs the same path in the test suite.
- On the Pi 4 later: `--source picamera` for a CSI module, `--source 0` for a USB webcam, and `--buttons` to
  start and stop with the START/STOP/RUN buttons once their polarity is measured.
