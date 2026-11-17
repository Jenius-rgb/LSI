# Bring-up of ZERO7 without the Raspberry Pi

Written 17 Nov 2026 for the board arriving on 20 Nov 2026 (ADR-025, ADR-026). Everything here is
preparation: the board phase starts only as `CLAUDE.md` section 8 says. Nothing in this file is a
`[HW]` result; fill in the "measured" columns only with what the board actually shows.

References: **TK-n** = `docs/official/ZERO7FPGA_Connection-table_261109_001.pdf` page n,
**IN-n** = `docs/official/Initialize_20260618_EN.pdf` slide n.

## 0. Power: read this first

- [OFFICIAL] The only documented way to power ZERO7 is through the GPIO header of a Raspberry Pi:
  "Connect their GPIO headers to each other. When Raspberry Pi is powered on, the LED on ZERO7 lights up" (IN-41).
- [UNKNOWN] Any other way. The connection table lists only on-board rails (VCC3V3, VCC1V8, VCC1V0) and the
  FPGA power pins; no separate power connector is described (all TK and IN pages checked on 17 Nov 2026).
- **Do not** feed 5 V or 3.3 V into the header pins from a bench supply or a USB cable: no document supports it.
- What to do, in order of preference:
  1. Ask the organisers how to power ZERO7 without a Raspberry Pi (question Q1 in `STATUS.md`).
  2. Use any Raspberry Pi only as the power source, as IN-41 describes. A Pi 5 is the model the organisers name;
     Pi 4 compatibility is [UNKNOWN] (team information, 17 Nov 2026). The Pi needs no software for this.
- Without power, steps 1 and 2 below can still be done; steps 3 and later cannot.

## 1. Inspect the board (no power)

| Check | Write it in `board/BOARD_INFO.md` |
| --- | --- |
| Board revision on the silkscreen | "Nama dan revisi board" (source: inspection by the team, date) |
| Labels of J1 (PMOD1), J2 (PMOD2), J7 and the JTAG pins | pin positions for steps 2 and 5 |
| LED3 and LED4: present or not | "Pin LED1–LED4" |
| Position of DIP SW7 (MODE0–MODE2) | "Cara konfigurasi FPGA" (do not change it) |
| Room for the Pi's CSI camera ribbon when ZERO7 is mounted (slot or gap above the Pi's camera connector) | note in `docs/CAMERA.md` section 3; decides whether a CSI module is usable |

## 2. Wire the JTAG-HS3 (no power)

[OFFICIAL] Six jumper wires from the JTAG-HS3 to the JTAG pins of ZERO7, colours as in IN-42. Tick every row
before power is applied; connect GND first.

| Signal | Wire colour in IN-42 | HS3 pin label | ZERO7 pin label | Checked |
| --- | --- | --- | --- | --- |
| VREF | red | VREF | Vref | [ ] |
| TMS | orange | TMS | TMS | [ ] |
| TCK | yellow | TCK | TCK | [ ] |
| TDO | green | TDO | TDO | [ ] |
| TDI | blue | TDI | TDI | [ ] |
| GND | black | GND | GND | [ ] |

Then connect the JTAG-HS3 to the PC with its USB cable (IN-42).

## 3. Vivado Hardware Manager (power on)

1. Vivado 2025.2 → **Open Hardware Manager** → **Open Target** → **Open New Target** → local server.
2. Set the JTAG clock to **3,000,000 Hz** (IN-46).
3. Expected [OFFICIAL, IN-46]: device `xc7s25_0`, IDCODE `037C4093`.

| Sign | Meaning |
| --- | --- |
| Device found with that IDCODE | step passed |
| "No target" or no device | check power (LED on ZERO7 from IN-41), VREF and GND wires, USB cable |
| Wrong IDCODE | stop: wrong board or wiring; do not program |

## 4. Blink: clock and LEDs

```
python tools/run.py bringup blink --accept-inferred-io
```

Program `build/bringup/blink/blink_top_BRINGUP.bit` from the Hardware Manager.

- Expected: D5 and D6 blink in turn (whatever their polarity), one full period per second at 20 MHz.
- Clock check with a stopwatch: count `n` full periods (D5 on, off, on again = one) over `t` seconds:
  `f_clk = 2 × HALF × n / t` with `HALF = 10,000,000` (`fpga/bringup/blink/blink_top.v`). For 30 periods
  at 20 MHz, t = 30 s. A stopwatch reading is good to a few tenths of a second, so this tells 20 MHz from,
  say, 16 or 25 MHz, not more. Record n, t and f as [HW].
- Fail signs: no blinking (check DONE LED and the programming result), blinking at a clearly different rate
  (clock is not 20 MHz: stop and record).

## 5. Bank voltages with a multimeter

```
python tools/run.py bringup vcco_probe --accept-inferred-io
```

The VCCO balls of the BGA cannot be probed, but an unloaded output driven high sits at its bank voltage.

| Where | Driven | Expected if the inference (ADR-024) holds | Measured |
| --- | --- | --- | --- |
| J1 table pins 1–4 (D15, E15, F15, G15; bank 15) to GND | high | about 3.3 V | |
| J1 table pins 5–8 (E13, E14, F14, G14; bank 15) to GND | low | about 0 V | |
| J7, the pin wired to S7_LED0 (N1; bank 34) to GND | high | about 3.3 V | |

- The physical position of the table pins on J1 and the J7 pinout are [UNKNOWN]: find them from the silkscreen.
- If bank 15 or 34 reads about 1.8 V: stop, write the value in `BOARD_INFO.md`, and an ADR changes the I/O
  standard before any further bitstream. The architecture diagram mentions two 1.8 V interfaces (G-3), so
  this is not impossible.
- If both read about 3.3 V: write them in `BOARD_INFO.md` (source: team measurement, date), remove the
  `TODO: belum dikonfirmasi` marks in `board/zero7.xdc` and the bring-up constraints, and record it in STATUS.

## 6. Buttons, switches and the WS2812B

```
python tools/run.py bringup io_test --accept-inferred-io
```

- D5 shows SW1 (PSW), D6 shows SW3 (DIP), and the WS2812B LED1 shows START as red, STOP as green, RUN as blue.
- These are raw levels: the polarity is [UNKNOWN]. Record whether pressing turns the colour on or off:

| Input | Level released | Level pressed or on |
| --- | --- | --- |
| START (C14) | | |
| STOP (B15) | | |
| RUN (C13) | | |
| PSW (R4) | | |
| DIP (M4) | | |

- If a reading flickers, the input may float: note it; a later build can add a pull resistor.
- The WS2812B timing is the commonly published one, not checked against the data sheet of this LED.
  If the LED stays dark or shows wrong colours, check with the ILA (step 8) and note it.

## 7. XADC in the Hardware Manager

After programming any design: open the **System Monitor** (XADC) dashboard in the Hardware Manager
(the official guide shows it, IN-48). Record temperature, VCCINT, VCCAUX and VCCBRAM as [HW] readings and
compare them with the DS189 recommended operating conditions. The sensor error is ±4 °C between −40 and
100 °C (DS189 Table 50).

## 8. ILA and VIO

- ILA on the I/O test: `python tools/run.py bringup io_test --accept-inferred-io --ila`, then program with
  the `.bit` and the `io_test_top.ltx` next to it; trigger on a button input or on the WS2812B line.
- VIO is not used: the full design is controlled through JTAG-to-AXI (step 9), which also reaches every
  register and memory.

## 9. SENTINEL with the PC as host (no Pi)

```
python tools/run.py bringup jtag_host --accept-inferred-io
python board/bringup.py id --host jtag --bitstream build/bringup/jtag_host/top_jtag_BRINGUP.bit
python board/bringup.py load --host jtag
python board/bringup.py validate --host jtag --images 200
```

- `top_jtag` is the full core with the JTAG-to-AXI Master; the PC reaches the same registers and memories
  as over SPI (ADR-025). Each connection starts with a write/read pattern test (`VivadoTclAxi.self_test`).
- Dry run before the board (passes on 17 Nov 2026, [SIM]): add `--dry-run` to the commands above; the
  RTL path is covered by the bench `jtag_session_xs` (PASS 25/25).
- Uploads are slower than SPI. Cycle counts from `CYCLES_TOTAL` are on-chip and valid; end-to-end time
  over JTAG does not stand for SPI.

## 10. What needs the Raspberry Pi anyway

The real SPI link and its speed, the `irq_done` line, camera mode, the final demo, and end-to-end latency.
See the experiment map in `STATUS.md`.
