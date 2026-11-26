# SEGGER J-Link with Vivado and ZERO7

Team decision of 25 Nov 2026: the JTAG probe is a SEGGER J-Link (20-pin JTAG connector, photo in `board/photos/`); the
team has no Digilent cable. A J-Link is not a native Vivado cable. Nothing in this file has been tried on the board yet:
every step that touches hardware is an instruction for the user, and a result becomes [HW] only when the user has run it
and pasted the output into `results/hw/` or STATUS.md.

## Sources

| Ref | Source | Read |
| --- | --- | --- |
| SG-XVC | SEGGER Knowledge Base, "J-Link XVCD Server", https://kb.segger.com/J-Link_XVCD_Server | 2026-11-25 |
| SG-20 | SEGGER Knowledge Base, "20-pin J-Link Connector", https://kb.segger.com/20-pin_J-Link_Connector | 2026-11-25 |
| OFL-C | openFPGALoader cable list, https://trabucayre.github.io/openFPGALoader/compatibility/cable.html | 2026-11-25 |
| OFL-F | openFPGALoader FPGA list, https://trabucayre.github.io/openFPGALoader/compatibility/fpga.html | 2026-11-25 |
| IN-n | `docs/official/Initialize_20260618_EN.pdf`, slide n [OFFICIAL] | |
| TK-n | `docs/official/ZERO7FPGA_Connection-table_261109_001.pdf`, page n [OFFICIAL] | |

## Route 1: J-Link XVCD Server and the Vivado Hardware Manager (programming and ILA)

Facts [VERIFIED EXTERNAL, SG-XVC]:

- The J-Link Xilinx Virtual Cable Daemon Server is part of the J-Link software package starting with **V7.92d**.
- Program: `JLinkXVCDServer.exe` on Windows (`<PathToJLinkSoftware>\JLinkXVCDServer.exe`), `JLinkXVCDServer` on Linux/Mac.
- Before starting it, the J-Link must be connected to the PC and the target must be powered and connected to the J-Link.
- Default TCP port **2542**; options `-Port <PortNo>`, `-USB <SerialNo/Nickname>`, `-IP <IP/Tunnel/Nickname>`.
- On start it prints the firmware, hardware version, serial number, licences, USB speed, **`VTref=…V`**, the target
  interface, and "Listening on TCP/IP port 2542".
- Vivado: open the Hardware Manager, click "Auto Connect" (local hardware server), add a Xilinx Virtual Cable (XVC), host
  name `localhost`, port 2542. The server then prints "New XVC connection". The JTAG speed is negotiated between Vivado and
  the J-Link.
- Older Vivado versions do not disconnect cleanly, so the target has to be power-cycled before the next connection with
  J-Link software; "A power-cycle is not necessary for connections with Vivado 2023.1 and newer." The team uses Vivado
  2025.2 (`python tools/run.py check`). The page states no minimum Vivado version beyond this note.
- Limitation: the XVCD server cannot run in parallel with other J-Link tools (for example J-Link Commander).

Not stated on SG-XVC, so [UNKNOWN] until tested: which J-Link hardware models are supported, whether the team's unit is
accepted by J-Link software V7.92d or later, and whether ILA works through XVC (Vivado treats an XVC target like other
cables [INFERENCE]).

Steps for the user:

1. Install the SEGGER J-Link Software and Documentation Pack, version V7.92d or later, from segger.com.
2. Connect the J-Link to the PC (USB) and, with the board **unpowered**, wire it to ZERO7 (table below).
3. Power the board the documented way only: ZERO7 on the Raspberry Pi 5 header, Pi powered by its USB-C supply (IN-41).
4. Run `JLinkXVCDServer.exe` and paste its whole console output (it contains VTref and the hardware version).
5. Vivado 2025.2, Hardware Manager, "Open target", "Auto Connect"; then "Add Xilinx Virtual Cable (XVC)", host
   `localhost`, port 2542. Paste the Tcl console text.

## Route 2: openFPGALoader (programming only, no ILA)

- [VERIFIED EXTERNAL, OFL-C] The cable keyword for SEGGER J-Link probes is `jlink` (the list names "SEGGER J-Link Debug
  Probes", "SEGGER J-Link BASE Debug Probes" and "SEGGER J-Trace PRO Debug Probes" under that keyword); no limitations are
  noted there.
- [VERIFIED EXTERNAL, OFL-F] Spartan-7 xc7s15, xc7s25 and xc7s50 are listed as supported for memory (SRAM) and flash.
- Commands [INFERENCE: standard openFPGALoader usage, confirm with `openFPGALoader --help`]:
  `openFPGALoader -c jlink --detect` (reads the JTAG chain), then `openFPGALoader -c jlink design.bit` (loads SRAM).
- Risk [INFERENCE]: openFPGALoader talks to USB probes through libusb. On Windows that may need a different USB driver
  (for example with Zadig), which can stop the SEGGER software from seeing the probe until the SEGGER driver is
  restored. Try route 1 first, and use route 2 on Linux (for example on the Raspberry Pi 5) if it is needed.

## Wiring: J-Link 20-pin connector to the ZERO7 JTAG header

The J-Link pin functions are from SG-20 [VERIFIED EXTERNAL]. The ZERO7 side is **not documented** for this white board:
TK-2 to TK-6 give the FPGA JTAG pins (TCK = E5, TDO = K4, TMS = K5, TDI = L4) [OFFICIAL], but not the header that carries
them or its pin order. The official guide (IN-42) shows a yellow board variant with six jumper wires; its overlay labels
read, left to right, Vref, GND, TCK, TDO, TDI, TMS [OFFICIAL photo]. The photos of the team's white board do not show
which header carries JTAG (`board/BOARD_INFO.md`, photo observations).

| Signal | J-Link 20-pin (SG-20) | Direction (SG-20) | ZERO7 header pin | IN-42 wire colour | FPGA pin (TK) |
| --- | --- | --- | --- | --- | --- |
| VTref | 1 | input to J-Link: "the target reference voltage", used to check that the target has power and to set the logic levels; "must not have a series resistor" | [UNKNOWN] | red (Vref) | (supply net, see safety) |
| TMS | 7 | output | [UNKNOWN] | orange | K5 |
| TCK | 9 | output | [UNKNOWN] | yellow | E5 |
| TDI | 5 | output | [UNKNOWN] | blue | L4 |
| TDO | 13 | input | [UNKNOWN] | green | K4 |
| GND | 4, 6, 8, 10 or 12 | ground | [UNKNOWN] | black | |
| RTCK | 11 | input; "Connect to RTCK if available, otherwise to GND" | not on ZERO7 per IN-42 [INFERENCE] | | tie to a J-Link GND pin |
| nTRST | 3 | output | leave unconnected (the six IN-42 wires have no TRST) | | |
| nRESET | 15 | I/O | leave unconnected | | |
| 5V-Supply | 19 | output: "can be used to supply power to the target hardware", 5 V, max 300 mA | **leave unconnected**; never power ZERO7 from the J-Link | | |
| NC / Res | 2, 17, 14, 16, 18, 20 | not connected / reserved ("do not assume them to be connected to GND") | leave unconnected | | |

Practical note [INFERENCE]: the J-Link has a 2×10 box header; six female-to-female jumper wires on the J-Link pins listed
above (or a 20-pin ribbon breakout) reach the ZERO7 header. Label every wire before connecting.

## Safety checklist before any power is applied

Do every item with the Raspberry Pi switched off and unplugged.

1. Identify the JTAG header on the board and its pin order from an official source (user manual, schematic or an
   organizer answer). Until then the ZERO7 column above stays [UNKNOWN]: **do not guess a header from the photo.**
2. Bank 0 (configuration and JTAG) has its VCCO on the VCC3V3 net and CFGBVS is tied to VCC3V3 [OFFICIAL, TK-2 to TK-6];
   the actual voltage at the JTAG header is **[UNKNOWN]** and the header signals may pass through other parts of the board.
   With the board powered the documented way (on the Pi 5) and **nothing connected to the J-Link**, measure the voltage
   between the header's Vref pin and GND with a multimeter, and paste the value. Connect VTref only after that.
3. Continuity: check every jumper wire end to end with the multimeter, and check that no two wires are shorted. Check that
   J-Link pin 19 (5 V) is not connected to anything.
4. Ground first: connect GND before the signal wires.
5. Power ZERO7 only from the Raspberry Pi header (IN-41). Do not use the board's DC jack or any other supply: the
   organizers have not confirmed a standalone power method (`docs/official/CORRESPONDENCE_2026-11.md` §4).
6. Keep the Pi's GPIO lines that share FPGA pins as inputs while testing (`board/BRINGUP.md`).

## Test order

Results are [HW] only after the user has run the step and pasted its output.

| Step | Action | Pass | Fail and next action |
| --- | --- | --- | --- |
| 1. Safe power | Board on the Pi 5, Pi on its USB-C supply, J-Link not yet connected; observe the ZERO7 LEDs and measure the Vref voltage (checklist item 2); optional USB power meter on the Pi supply | IN-41: a ZERO7 LED lights when the Pi is powered; voltage pasted; no heat, smell or drop of the Pi supply | No LED, unexpected voltage or heat: power off and report; do not continue |
| 2. J-Link sees the target | Connect J-Link (GND first), start `JLinkXVCDServer.exe` | Console prints `VTref=` close to the measured voltage and "Listening on TCP/IP port 2542" | VTref about 0 V: wiring or header wrong. Server refuses the probe: report its message (hardware or software support) and try route 2 |
| 3. Vivado finds the FPGA | Hardware Manager, Auto Connect, Add XVC (localhost:2542) | Device `xc7s25_0` with IDCODE `037C4093` (IN-46) | No device: check TDI/TDO swap, lower the JTAG frequency if Vivado offers it (IN-46 used 3 MHz with the HS3), report the Tcl console text |
| 4. Program blink | Program `fpga/bringup/blink` (`python tools/run.py bringup blink …`, see `board/BRINGUP.md`, "Blink: clock and LEDs") | LED1 (D5) and LED2 (D6) alternate; one full period ≈ 1.000 s at 20 MHz; f_clk = 2 · HALF · n / t from a stopwatch count of n periods | DONE LED (D1) off: programming failed, paste the log. LEDs static: report |
| 5. ILA through XVC | Program a design with an ILA core, open the waveform window in the Hardware Manager | ILA triggers and shows waveforms | Fall back to VIO through XVC; if that fails too, debug with LEDs (bring-up designs) and with register reads over SPI from the Pi 5 (`fpga/bringup/spi_loopback`, then the SENTINEL host interface) |

## Open items for the user

- J-Link hardware version, firmware and serial number (printed by `JLinkXVCDServer.exe` in step 2).
- The JTAG header of the white ZERO7 and its pin order: ask the organizers together with the user manual and XDC questions.
- The measured voltage at the header's Vref pin (checklist item 2).
