# Board bring-up plan (ZERO7)

Only start this when `board/BOARD_INFO.md` has no `UNKNOWN` in its required fields and the
user has confirmed the board is in hand (CLAUDE.md section 8). Do not change any voltage.
Always start at the safe clock. Overclocking comes only after E7 is bit-exact at the safe clock.

Each step is one subcommand of `board/bringup.py`. Steps 1 and 2 run on the PC, the rest on the
Raspberry Pi. Every step can be rehearsed on a PC with `--dry-run`, which uses the Python model
of the device and proves nothing about hardware. Save the output of each step under
`results/hw/bringup/` and label it `[HW]`.

| Step | Command | Pass criterion | If it fails |
| --- | --- | --- | --- |
| 1. Power | `python board/bringup.py power` | The checklist in the script is confirmed by hand; voltages read with a meter | Stop. Check the power source and the board documentation |
| 2. Programming | `python board/bringup.py program` | Vivado Hardware Manager (or the method documented for ZERO7) programs the bitstream; DONE indicator, if the board has one | Check cable and part number in BOARD_INFO |
| 3. LED blink | `python board/bringup.py led` | LED1 to LED4 follow the pattern from the bitstream | Check XDC pin assignment |
| 4. SPI loopback | `python board/bringup.py spi-loopback` | A pattern written to a scratch register reads back identically at the lowest SPI speed | Check SPI pins, mode, CS polarity, level voltage |
| 5. Read ID | `python board/bringup.py id` | Returns `SNTL` and the expected version and K | Check the bitstream build |
| 6. Load weights | `python board/bringup.py load` (model from `config/hw_zero7.yaml`, s4b) | Read-back of the first 256 weight bytes matches the file | Lower the SPI speed |
| 7. One image | `python board/bringup.py one-image` | Class and logits match the golden model | Stop. Do not raise the clock |
| 8. Full validation at the safe clock | `python board/bringup.py validate --images 200` | 100% logits match (this is E7) | Stop. Do not raise the clock |
| 9. Turbo, one step at a time | `python board/bringup.py turbo` | Only after step 8. Raises the turbo level step by step and reports `[HW]` counters; stops at the first FATAL | Lower the level, re-run E7 at the safe clock |

Checkpoints C0–C4 (inspection, Pi 5 set-up, power, voltage map) come first: `board/BRINGUP_C0_C4.md`.

Facts this plan needs but does not assume are listed in `board/BOARD_INFO.md`. The script stops
with a message if a required field is still `UNKNOWN`.

## Preparation before the board arrives (2026-11-16)

Sources: `docs/official/Initialize_20260618_EN.pdf` (IN-n = slide n), `docs/official/GUIDE_LSI_2027_FINALE.pdf`
(G-n = page n), and the notes in `docs/references/`. Facts about the board are in `board/BOARD_INFO.md`.

### Vivado on the PC

- Status **CUKUP**: Vivado 2025.2 with part `xc7s25csga225-1` installed (`results/vivado/part_check.txt`,
  from `tools/vivado_check_part.tcl`). The guide names Windows 11 and Vivado 2025.2 (IN-14).
- `vivado` is not on PATH on this PC. The repository scripts find it through `tools/check_env.py`.
  To call it by hand, add `C:\AMDDesignTools\2025.2\Vivado\bin` to PATH, or run
  `C:\AMDDesignTools\2025.2\Vivado\settings64.bat` in the terminal first.
- The guide lists Spartan-7 and Zynq-7000 as the minimum device families (IN-18). Zynq-7000 is not
  installed here (0 parts). SENTINEL does not need it; add it with Help > Add Design Tools or Devices >
  SoCs > Zynq-7000 if the Hardware Manager misbehaves.
- The cable drivers option of the installer must be on for the JTAG cable (IN-18).

### JTAG cable (team decision 25 Nov 2026: SEGGER J-Link)

- [OFFICIAL] The guide uses a Digilent JTAG-HS3 with six jumper wires to the JTAG pins of ZERO7: Vref red, TMS orange,
  TCK yellow, TDO green, TDI blue, GND black (IN-42; the slide text misspells it "JTAG-H53").
- [OFFICIAL] In "Open New Target" set the JTAG clock to 3,000,000 Hz (IN-46). The device shows as
  `xc7s25_0`, ID code `037C4093` (IN-46). Program with the `.bit` file (IN-49).
- [USER, 25 Nov 2026] The team has no Digilent cable and uses a SEGGER J-Link (20-pin JTAG). Vivado reaches it through
  the SEGGER J-Link XVCD Server ("Add Xilinx Virtual Cable"); openFPGALoader (`--cable jlink`) is the programming-only
  fallback. Wiring, safety checks and the test order are in `docs/JLINK_VIVADO.md`. Programming and ILA through the
  J-Link are [UNKNOWN] until the user runs the tests there.
- The earlier notes on a Digilent JTAG-HS2 (18 Nov 2026) and on cheaper cable options are superseded.

### Raspberry Pi 5 (team decision 25 Nov 2026, ADR-033)

Sources: Raspberry Pi documentation (raspberrypi.com/documentation/computers: raspberry-pi, getting-started, imager,
remote-access, config_txt), gpiozero documentation (installing, api_pins), read 2026-11-25.

- [OFFICIAL] The organisers say the loaned boards connect to a Raspberry Pi 5 (G-6), and ZERO7 takes its power from the
  header (IN-41). [USER] The team now has a Raspberry Pi 5 with 8 GB RAM. Pi 5 compatibility with ZERO7 is [UNKNOWN] until
  shown on the board; check on arrival that the board seats fully on the 40-pin header and that nothing underneath touches
  the Pi's connectors or cooler.
- Power: Raspberry Pi documentation recommends the 27 W USB-C supply (5 V, 5 A); with a 5 V 3 A supply the Pi limits USB
  peripherals to 600 mA. How much ZERO7 draws from the 5 V header pins is [UNKNOWN]; measure it with a USB power meter in
  step 1. Do not power ZERO7 any other way (its DC jack is unconfirmed, `board/BOARD_INFO.md`).
- Operating system: Raspberry Pi Imager, device "Raspberry Pi 5", Raspberry Pi OS (64-bit). In the OS customisation step
  set the hostname (letters, numbers, hyphens), a lowercase username and password, Wi-Fi (the country in Localisation sets
  the Wi-Fi regulatory domain), and in Remote access turn on "Enable SSH". SSH is off by default otherwise.
- GPIO on the Pi 5 (RP1 I/O controller): gpiozero with the **lgpio** pin factory. The gpiozero documentation says "Only
  lgpio works on the Pi 5"; RPi.GPIO is not used anywhere in this repository. `sentinel.transport.lgpio_factory()` selects
  it explicitly, so a missing lgpio fails with an install hint instead of a silent fallback.
- Packages (apt, the system Python; Bookworm does not allow pip into the system Python):
  `sudo apt install python3-spidev python3-gpiozero python3-lgpio python3-numpy python3-picamera2 python3-opencv`.
- SPI: `sudo raspi-config`, Interface Options, SPI, then reboot (or `dtparam=spi=on` in `/boot/firmware/config.txt`).
  `ls /dev/spidev0.*` must list `spidev0.0`; the user needs the `spi` and `gpio` groups. SENTINEL uses SPI0 with CE0:
  GPIO11 SCLK, GPIO10 MOSI, GPIO9 MISO, GPIO8 CE0. On the Pi 5 SPI comes from RP1. Start at 1 MHz (`SpidevTransport`
  default); the FPGA side is guaranteed up to f_safe / 8 = 15.6 MHz (SPEC 12.1); the speed the wiring allows is measured
  with `fpga/bringup/spi_loopback`: build it with `python tools/run.py bringup spi_loopback --accept-inferred-io`, program it through the J-Link, then run `python3 board/spi_loopback_check.py` on the Pi and paste the output. The connection table marks JP11 "(CUT)" on SCLK (A8) and JP9 "(CUT)" on MOSI (A6); if those jumpers are open the FPGA never sees SCLK or MOSI and the check reports constant replies. Their default state is UNKNOWN; do not modify them without an official source. GPIO pins are 3.3 V and not 5 V tolerant [OFFICIAL, Raspberry Pi documentation].
- Camera (team decision: only through the Pi): picamera2 for a CSI module, OpenCV/V4L2 for a USB webcam, or a video file:
  `python -m sentinel.camera_mode --source picamera|0|video.mp4`. The Pi 5 uses 22-pin camera ribbons [INFERENCE, not checked in the documentation read] (the older 15-pin
  ribbon needs an adapter cable). The camera type is not decided yet.
- Done signal: `irq_done` arrives on GPIO25 (pin C9); `sentinel.transport.GpioDoneLine` waits on it.
- Run `python3 board/pi_check.py` on the Pi before step 2. It prints the Pi model, whether `/dev/spidev0.0` exists,
  whether `spidev`, `gpiozero`, `lgpio`, `picamera2`, `numpy` and `cv2` import, and whether GPIO will work on a Pi 5.
- Wi-Fi from a terminal: `nmcli dev wifi list`, then `sudo nmcli --ask dev wifi connect <ssid>`.
- GPIO lines that ZERO7 shares with its own parts must stay inputs on the Pi unless a script means to
  drive them: GPIO13 and GPIO19 (LEDs D9 and D8), GPIO6 (LED D3), GPIO16, GPIO20, GPIO21 (buttons RUN,
  START, STOP), GPIO18 (WS2812B LED2).
- Copy the repository to the Pi before step 4.

### Still open

`board/zero7.xdc` carries LVCMOS33 on every pin as an unconfirmed value. Steps 2 and later stay blocked
until the official `Zero7.xdc` or the user manual confirms the I/O standards (`board/BOARD_INFO.md`).

## Board checks after the J-Link works (C8–C10 of the bring-up prompt)

Moved here on 26 Nov 2026 from the removed `board/BRINGUP_NO_PI.md` (the team has the Raspberry Pi 5, ZERO7 and the
SEGGER J-Link, so the no-Pi path is gone). Program each bitstream through the J-Link XVCD Server and the Hardware Manager
(`docs/JLINK_VIVADO.md`). These designs drive only FPGA-owned pins; `fpga/bringup/build.py` refuses to build without
`--accept-inferred-io` because the I/O standards are an inference (ADR-024). Results are [HW] only when the board shows them.

### Blink: clock and LEDs

`python tools/run.py bringup blink --accept-inferred-io`, then program `build/bringup/blink/blink_top_BRINGUP.bit`.

- Expected: D5 and D6 blink in turn, one full period per second at 20 MHz.
- Clock check with a stopwatch: count `n` full periods over `t` seconds; `f_clk = 2 × HALF × n / t` with `HALF = 10,000,000`
  (`fpga/bringup/blink/blink_top.v`). A stopwatch tells 20 MHz from 16 or 25 MHz, not finer. Record n, t and f as [HW].
- Fail signs: no blinking (check the DONE LED and the programming result), or a clearly different rate (stop and record).

### Bank voltages through driven outputs

`python tools/run.py bringup vcco_probe --accept-inferred-io`. The VCCO balls of the BGA cannot be probed, but an unloaded
output driven high sits at its bank voltage; use this when C4 could not reach a VCCO decoupling point.

| Where | Driven | Expected if the inference (ADR-024) holds | Measured |
| --- | --- | --- | --- |
| J1 table pins 1–4 (D15, E15, F15, G15; bank 15) to GND | high | about 3.3 V | |
| J1 table pins 5–8 (E13, E14, F14, G14; bank 15) to GND | low | about 0 V | |
| J7, the pin wired to S7_LED0 (N1; bank 34) to GND | high | about 3.3 V | |

- The physical position of the table pins on J1 and the J7 pinout are [UNKNOWN]: find them from the silkscreen first.
- About 1.8 V on bank 15 or 34: stop, write it in `BOARD_INFO.md`; an ADR changes the I/O standard before any further
  bitstream (the architecture diagram mentions two 1.8 V interfaces, G-3).
- About 3.3 V on both: write them in `BOARD_INFO.md` (team measurement, date), remove the `TODO: belum dikonfirmasi` marks
  in `board/zero7.xdc` and the bring-up constraints, and record it in STATUS.

### Buttons, switches and the WS2812B

`python tools/run.py bringup io_test --accept-inferred-io`. D5 shows SW1 (PSW), D6 shows SW3 (DIP), the WS2812B LED1 shows
START red, STOP green, RUN blue. Polarity is [UNKNOWN]: record the level released and pressed for START (C14), STOP (B15),
RUN (C13), PSW (R4) and DIP (M4). A flickering reading may mean a floating input; note it.

### XADC

After programming any design, open the System Monitor (XADC) dashboard in the Hardware Manager (guide slide 48). Record
temperature, VCCINT, VCCAUX and VCCBRAM as [HW] and compare them with the DS189 recommended operating conditions.

### ILA

`python tools/run.py bringup io_test --accept-inferred-io --ila`, then program with the `.bit` and the `io_test_top.ltx` next
to it; trigger on a button input or on the WS2812B line. ILA through the J-Link XVCD Server is [UNKNOWN] until this is tried
(C9); if it fails, record it as a [HW] finding and debug through LEDs, VIO or SPI instead.
