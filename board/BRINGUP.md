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
| 6. Load weights | `python board/bringup.py load --model s` | Read-back of the first 256 weight bytes matches the file | Lower the SPI speed |
| 7. One image | `python board/bringup.py one-image` | Class and logits match the golden model | Stop. Do not raise the clock |
| 8. Full validation at the safe clock | `python board/bringup.py validate --images 200` | 100% logits match (this is E7) | Stop. Do not raise the clock |
| 9. Turbo, one step at a time | `python board/bringup.py turbo` | Only after step 8. Raises the turbo level step by step and reports `[HW]` counters; stops at the first FATAL | Lower the level, re-run E7 at the safe clock |

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

### JTAG cable

- [OFFICIAL] Digilent JTAG-HS3, six jumper wires to the JTAG pins of ZERO7: Vref red, TMS orange,
  TCK yellow, TDO green, TDI blue, GND black (IN-42; the slide text misspells it "JTAG-H53").
- [OFFICIAL] In "Open New Target" set the JTAG clock to 3,000,000 Hz (IN-46). The device shows as
  `xc7s25_0`, ID code `037C4093` (IN-46). Program with the `.bit` file (IN-49).
- Not known: whether the cable comes with the loaned board. Ask when arranging the loan.

### Raspberry Pi

- [OFFICIAL] The loaned boards connect to a Raspberry Pi 5 (G-6). A Pi 5 wants a 5 V 5 A supply; ZERO7
  takes its power from the header (IN-41).
- Operating system: Raspberry Pi Imager, pick the device, Raspberry Pi OS and the microSD card (32 GB or
  more for the desktop image). In the customisation step set hostname, user, Wi-Fi and enable SSH.
- SPI: `sudo raspi-config`, `3 Interface Options`, `I4 SPI`, then reboot. `ls /dev/spidev0.*` must list
  `spidev0.0`. SENTINEL uses SPI0 with CE0: GPIO11 SCLK, GPIO10 MOSI, GPIO9 MISO, GPIO8 CE0.
- SSH: `3 Interface Options`, `I1 SSH`. Wi-Fi from a terminal: `nmcli dev wifi list`, then
  `sudo nmcli --ask dev wifi connect <ssid>`.
- GPIO lines that ZERO7 shares with its own parts must stay inputs on the Pi unless a script means to
  drive them: GPIO13 and GPIO19 (LEDs D9 and D8, driven by the FPGA in `board/zero7.xdc`), GPIO6 (LED D3),
  GPIO16, GPIO20, GPIO21 (buttons RUN, START, STOP), GPIO18 (WS2812B LED2).
- Copy the repository to the Pi and install the Python packages the Pi scripts import (`spidev`, `numpy`,
  and a camera package) before step 4.

### Still open

`board/zero7.xdc` carries LVCMOS33 on every pin as an unconfirmed value. Steps 2 and later stay blocked
until the official `Zero7.xdc` or the user manual confirms the I/O standards (`board/BOARD_INFO.md`).
