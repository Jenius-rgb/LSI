# STATUS — SENTINEL

Last updated: 2026-11-26, zero-skip (ADR-028) fixed and compared, model s4 (ADR-037), G1 status. Before: 2026-11-23, organizer clarifications integrated (pre-board). Previous: 2026-11-16 night, ZERO7 update session after user response.
Phase: **PRE-BOARD**

Legend: `[ ]` not started · `[~]` in progress · `[x]` completed (evidence in Evidence log) · `[B]` blocked (reason in Blocked section)

## Gates and dates

| Gate | Date | Requirement |
| --- | --- | --- |
| G1 | 13 Dec 2026 | M0–M8 completed in simulation. On board: CNN bit-exact on safe clock (needs board). |
| G2 | 3 Jan 2027 | M10 completed. On board: governor running and E4 data present. |
| Freeze hardware | 17 Jan 2027 | No new features after this date, only measurements and writing. |
| Report | 31 Jan 2027 | [OFFICIAL] report submission deadline |
| Contest | 5 Mar 2027 | [OFFICIAL] Chitose, hybrid |

If G1 slips by more than one week, drop per-layer clock selection and use a single global turbo clock (record ADR).

**At risk (23 Nov 2026):** G1 and G2 both need the board running. ZERO7 power without a Raspberry Pi is still unanswered by the organizers, and the only Raspberry Pi confirmed so far (a Raspberry Pi 5 from the user's lecturer) arrives about 3–4 Jan 2027. Unless another way to power and program ZERO7 is found in December, G1 slips by more than one week. Re-planning the gates and applying the fallback rule above are user decisions; see "Organizer clarifications and hardware dependencies (23 Nov 2026)".

**G1 status (26 Nov 2026, written for the ADR-028 condition):**
- Simulation half: done. M0–M8 are checked off with evidence; only optional items stay open (QAT in M2, operand parity in M8).
- Board half (B1–B3, CNN bit-exact on the safe clock): not started. Open: the user put every hardware step on hold on 25 Nov ("tunggu instruksi"); the CLAUDE.md §8 conditions are not met (`board/BOARD_INFO.md` mandatory fields such as the JTAG header P2 signal order and the bank voltages are still UNKNOWN, and "board siap" has not been written); the J-Link XVCD path is untested.
- Change since 23 Nov: the Raspberry Pi risk above is gone. The team's own Raspberry Pi 5 is the host (ADR-033), and the board and the Pi are in hand (user, 25 Nov).
- 17 days remain until 13 Dec. How long bring-up up to E7 takes is [UNKNOWN]; nothing has been measured.
- Verdict: G1 is not missed. Its board half is at risk, for reasons outside the zero-skip work. Zero-skip is PC-side only, `ZERO_SKIP` defaults to 0 and the baseline benches are unchanged, so it takes nothing the board half needs. Rule from here on: when the user resumes the hardware steps, board work comes first; if G1 is missed, zero-skip stays off by default and its work stops (ADR-028 condition 1).

---

## PRE-BOARD Phase

### M0 — Repo setup and environment
- [x] Folder structure according to SPEC §17, `.gitignore` (build/, dataset, large checkpoints), `git init`, `README.md` (English)
- [x] `requirements.txt` (numpy, torch, torchvision, pyyaml, pytest, hypothesis, matplotlib; optional: opencv-python, flask; Pi-specific: spidev, picamera2)
- [x] `tools/check_env.py`: detect and print versions of Python, torch, numpy, pytest, iverilog/vvp, verilator, vivado/xvlog/xsim
- [x] `tools/run.py` with subcommands: check, test, gen, train, export, sim, campaign, ooc, plots
- [x] `docs/ENVIRONMENT.md` containing genuinely detected tool versions

**DoD:** `python tools/run.py check` and `python tools/run.py test` run on this machine (tests may be few, but passing). ENVIRONMENT.md populated from check output.

### M1 — Float model
- [x] `config/model_s.yaml`, `config/model_xs.yaml`; `model/arch.py` constructs model from config
- [x] `model/arch_report.py`: parameter count, MACs, and cycles per K
- [x] `model/train.py`: CIFAR-10, fixed seed, light augmentation, save checkpoint and log
- [x] Support folder dataset (ImageFolder format) and arbitrary N_CLASSES, to allow immediate retraining when organizers announce target classes

**DoD:** arch_report matches SPEC §2 (if not, fix SPEC via ADR). Float accuracy of s and xs variants recorded in `results/model/` along with seeds.

### M2 — Quantization, golden model, export
- [~] `model/quant.py`: BN fold and PTQ complete; QAT option not yet implemented as unnecessary (model s accuracy drop 0.26 points, target ≤ 2)
- [x] `model/golden.py`: exact SPEC §3, NumPy int64
- [x] `model/export.py`: `.bin` + `manifest.json` + `.mem` + bound check (SPEC §3.6)
- [x] Test L0: requant (rounding at .5, negatives, saturation, n = 0), padding, flatten, series argmax, bit bounds

**DoD:** integer accuracy recorded. Target drop ≤ 2 points from float; if unachieved, write ADR and remediation steps. All L0 tests green. Export deterministic (same hash if run twice).

### M3 — Checker model and fault campaign (Python)
- [x] `model/checker.py` (SPEC §6.2 and §11.2), `model/fault_model.py` (§11.3), `model/campaign.py`
- [x] Property test for decision table (hypothesis if available)
- [x] Campaign for K ∈ {8, 16} and C3 ∈ {0, 1}: 10,000 single-lane errors, 10,000 two-lane, 1,000 in checksum lane. Injection on real accumulators from golden model (real layers, real images).

**DoD:** 100% single-lane errors corrected. Rate table (clean, corrected, csum_lane, recompute, miscorrected, escaped) present in `docs/RESULTS_SIM.md` with [SIM] label. Recommendation regarding C3 written as ADR.

### M4 — RTL lane and lane array
- [x] `rtl/lane_lut.v`, `rtl/lane_dsp_min.v`, `rtl/lane_dsp_full.v`
- [x] `rtl/lane_array.v`: K data lanes + 2/3 checksum lanes, holding register, serializer
- [x] Testbench with golden vectors: ≥ 10,000 random units + ≥ 100 real tiles

**DoD:** bit-exact for all LANE_IMPL. Verilator lint clean (if available).

### M5 — RTL checker and corrector
- [x] `rtl/lane_checker.v` (ADR-009) per SPEC §6.2: mode 0/1/2, C3_EN, TRUST_CSUM_LANE, j search without divider

**DoD:** bit-exact against `model/checker.py` on ≥ 2,000 cases from M3, covering every decision branch.

### M6 — RTL single-clock engine
- [x] Operand generator (address, padding, on-the-fly wc), layer control based on layer table
- [x] Post-processing (SPEC §3.3), pooling, FC, argmax, activation buffers

**DoD:** logits and class bit-exact for ≥ 200 images (s and xs variants). Real cycles vs model ≤ 10% overhead. All SPEC §13.4 corner cases tested.

### M7 — Host interface
- [x] `spec/regmap.yaml` + `tools/gen_regmap.py` → `rtl/gen/` and `sw/sentinel/regmap.py`
- [x] `rtl/spi_slave.v`, register file, load weights via SPI, ping-pong image buffer
- [x] Python driver + `LogTransport`; testbench replays transaction log

**DoD:** complete transaction (ID → load weights → write image → START → read class, logits, counters) bit-exact in simulation. Test exists ensuring generated files are always up-to-date.

### M8 — Dual clock domains, modes, recompute
- [x] `rtl/platform/*/cdc_fifo` (XPM and behavioral), `clk_gen` (sim and Xilinx)
- [x] Operand supply R, per-layer clock selection, recompute pass + log, mode 0/1/2, STARVE counter
- [ ] Optional: operand parity bit (not done in this session; optional per SPEC)

**DoD:** bit-exact end-to-end for ratio f_fast/f_safe ∈ {1.0, 1.3, 1.7, 2.0}. With single-lane injection: mode 2 bit-exact, mode 1 bit-exact via recompute, mode 0 shows mismatch as predicted. Counters match model.

### M9 — Hardware injection and RTL campaign
- [x] INJ0/INJ1 registers (SPEC §11.1)
- [x] RTL campaign script: ≥ 2,000 injections, including two lanes

**DoD:** RTL outcome 100% matches Python model prediction. Results in `docs/RESULTS_SIM.md` with [SIM] label.

### M10 — Governor and clock reconfiguration
- [x] `model/governor.py`, `rtl/governor.v`
- [x] MMCM2 reconfiguration in RTL: Clocking Wizard with AXI4-Lite and `clkwiz_seq` (ADR-023, M21; corrected 2026-11-16, this item previously still `[B]`). Hardware evidence awaits board (M21, B4)
- [x] `tools/gen_mmcm_table.py` with verified DS189 limits (Table 37, PDF p. 40) and F_IN = 20 MHz [OFFICIAL] (ADR-015, ADR-023)
- [x] Testbench ≥ 50 scenarios with events from synthetic fault model

**Status:** `[x]` for all parts without board: governor, protocol, MMCM2 reconfiguration in RTL, and DS189 limits. Genuine reconfiguration measured on board (B4).

**DoD:** RTL state trajectory matches model for all scenarios. SPEC §7.7 sequence verified in simulation. MMCM table passes limit tests.

### M11 — Vivado out-of-context
- [x] `fpga/ooc.tcl`, `fpga/run_matrix.py` (variant matrix), report parser to CSV
- [x] `tools/fit_report.py` (BRAM and DSP estimation per part from config)

**Status:** `[x]` full matrix of 96 runs (xc7s6, xc7s15, xc7s25, xc7s50; speed -1 and -2; K 8/16; lut, dsp_min, dsp_full; C3 0/1). 48 runs on xc7s25 and xc7s50 succeeded; 48 runs on xc7s6 and xc7s15 did not fit (insufficient BRAM). Table and critical path analysis in `docs/RESULTS_SIM.md` [VIVADO-STA]. ZERO7 part and speed grade not yet verified.

**DoD:** resource and Fmax table [VIVADO-STA] per part and variant in `docs/RESULTS_SIM.md`. Critical path analysis per SPEC §7.4. If Vivado not in this environment: exact instructions for user, and status `[B] requires user run`.

### M12 — Pi software and experiment harness
- [x] Driver, `HwBackend`, `MockBackend`, `camera.py`, `preprocess.py`, dashboard
- [x] Validation mode per official requirements: read image folder (from SD card or USB), classify all, report accuracy and per-image time (latency and FPS)
- [x] Real-time camera mode per official requirements: display class and recognition speed
- [x] `experiments/e1.py` through `e8.py`; plots with watermark for mock backend

**DoD:** validation mode, camera mode (with camera or surrogate video file), and all e1–e8 scripts run with MockBackend and produce CSV + plots marked SYNTHETIC. Driver unit tests compared against co-simulation log.

### M13 — Documentation and draft report
- [x] `docs/ARCHITECTURE.md` (Mermaid diagram), `VERIFICATION.md`, `RESULTS_SIM.md`
- [x] `docs/AI_USAGE.md` (honest AI usage), `THIRD_PARTY.md`
- [x] `docs/REPORT_DRAFT.md` with `[HW-TBD]` placeholders, `docs/SLIDES_OUTLINE.md` (10 slides)

**DoD:** every number has script or log citation. No hardware claims.

### M14 — Board readiness package
- [x] `board/BRINGUP.md`: power → programming → blinking LED → SPI loopback → read ID → load weights → 1 image → full validation on safe clock → then turbo
- [x] Scripts for every bring-up step
- [x] Top-level board with placeholder XDC; build script refuses to run if BOARD_INFO still UNKNOWN

**DoD:** dry-run with MockBackend passes.

---

## BOARD Phase (start only per CLAUDE.md §8)

- [ ] **B1**: XDC from official ZERO7 documents, F_IN, bitstream, programming
- [ ] **B2**: step-by-step bring-up according to BRINGUP.md
- [ ] **B3**: E7 on safe clock (bit-exact across full validation set) [HW]
- [ ] **B4**: E1–E3, manual sweep [HW]
- [ ] **B5**: E4 (three modes), automatic governor, E6 [HW]
- [ ] **B6**: final results, update report and plots, demo video

---

## ZERO7 Updates (PROMPT_UPDATE_ZERO7, starting 2026-11-16)

Organizers published new official facts on 2 and 10 Nov 2026 (summary and references in `docs/official/README.md`). Phase remains PRE-BOARD for all `[HW]` experiments; physical board not yet in hand.

- [x] **T0** Orientation: full `check` and `test`
- [x] **T1** Read and archive official sources; reference notes in `docs/references/`
- [x] **T2** Web and social media research 15 Oct–15 Nov 2026 (`docs/research/RISET_WEB_2026-11.md`)
- [x] **T3** Check Vivado and parts; Raspberry Pi notes in `board/BRINGUP.md`
- [x] **T4** `board/BOARD_INFO.md`, `board/zero7.xdc`, update Blocked
- [x] **T5** Re-review repo (`docs/REVIEW_2026-11.md`)
- [x] **T6** New ADRs, then SPEC
- [x] **T7** Implementation; priority official XC7S25CSGA225-1 synthesis report — all non-board parts of M15 through M21 completed; remainder needs board (see "Not yet done")
- [x] **T8** Simulated judges (`docs/JUDGE_REVIEW.md`), three rounds
- [x] **T9** Revise study guide to version 1.1 (source in `tools/study_guide/`, output in `build/study_guide/`)
- [x] **T10** Session notes, commit, summary

### New milestones from ADR-013 through ADR-021

- **M15 — Official synthesis report XC7S25CSGA225-1 (ADR-013, ADR-014, ADR-015, ADR-016)**
  - [x] `config/hw_zero7.yaml` (official variant: s, K = 8, R = 2, lut, C3 = 1)
  - [x] `clk_gen_xilinx` for 20 MHz input; `top_board` with ADR-016 ports; `board/zero7.xdc` conforming
  - [x] `fpga/synth_official.tcl` and `python tools/run.py synth-official`
  - [x] reports in `results/vivado/official/` and [VIVADO-STA] summary in `docs/RESULTS_SIM.md`
  - Results [VIVADO-STA]: f_safe = 125 MHz (ADR-015), 6,170 of 14,600 LUTs, design WNS +0.417 ns. Report format requested by organizers still [UNKNOWN].
  - Definition of Done: implementation finishes without error; all resources below part capacity; `clk_safe` WNS ≥ 0 at chosen f_safe; utilization, timing, power, DRC, and methodology reports saved; every number traceable to report files.
- **M16 — Simulation regression of official variant**
  - [x] engine model `s`, K = 8, C3 = 1 bit-exact against golden model for ≥ 200 images [SIM] (`engine_s_k8_c1_n200`)
  - [x] dual-clock system with official variant (`system_s_k8_c1`, C3 active, including two-lane injection)
- **M17 — WS2812B Indicator (ADR-017)**
  - [x] `rtl/ws2812_tx.v` with pulse-width testbench; status encoder (`rtl/status_led.v`); `ws2812_dout` port on `top_board`, pin N1
  - [B] pulse timing checked against ZERO7 LED datasheet (LED model and datasheet not yet available)
- **M18 — XADC Temperature (ADR-018)**
  - [x] `rtl/xadc_temp.v`, `rtl/platform/xilinx/xadc_prim_xilinx.v` (UG480 settings), simulation model `rtl/platform/sim/xadc_prim_sim.v`; `TEMP` register; `sentinel.xadc` (UG480 Eq. 2-6)
  - [B] temperature column in E6 harness with real readings (needs board)
- **M19 — Done signal and buttons (ADR-016)**
  - [x] `irq_done` in RTL (`top_board`) and in driver (`SentinelDriver(done_line=...)`, `GpioDoneLine`; GPIO class never run on Pi yet)
  - [x] `board/bringup.py` uses done line on board; camera mode follows START/STOP/RUN buttons (`--buttons`)
  - [B] button polarities measured on board
- **M20 — Clock domain crossing rules (ADR-021)**
  - [x] synchronizers marked `ASYNC_REG`; one synchronizer per asynchronous reset source; LOCKED MMCM2 synchronized
  - [x] power-on reset false path; `report_cdc` and `report_bus_skew` in official flow; SPEC §7.8
  - [x] guard in `regfile`: writes to `INJ*` during BUSY discarded (`tb_regfile_guard`)
  - [x] mux status reported after fixed delay in `clk_gen_xilinx`
- **M21 — MMCM2 reconfiguration via Clocking Wizard (ADR-023, closing ADR-010)**
  - [x] level table to `rtl/gen/mmcm_turbo_table.vh` (rules: exact, integer M and O, highest VCO); freshness test
  - [x] `rtl/clkwiz_seq.v` (AXI4-Lite master, PG065 sequence) with `tb_clkwiz_seq` and behavioral register model
  - [x] `clk_wiz_turbo` generated in `fpga/synth_official.tcl`; `clk_gen_xilinx` uses it
  - [B] genuine reconfiguration measured on board (B4)
- [B] Boot from QSPI flash (ADR-019): awaiting flash model and DIP SW7 positions.
- **M22 — Bring-up without Raspberry Pi and host via JTAG (ADR-025, ADR-026)**
  - [x] `board/BRINGUP_NO_PI.md`: power (only via Pi per IN-41; other methods [UNKNOWN]), JTAG-HS3 cable, Hardware Manager, blink, bank voltages, I/O, XADC, ILA, JTAG host
  - [x] designs in `fpga/bringup/` (blink, vcco_probe, io_test) with `tb_bringup`; `python tools/run.py bringup <design> --accept-inferred-io`
  - [x] `top_core` with second host port; `rtl/axil_bus_bridge.v`; `board/top_jtag.v`; JTAG log player model; bench `jtag_session_xs`
  - [x] `sentinel.transport_jtag` (`JtagAxiTransport`, `SimulatedAxi`, `RecordingAxi`, `VivadoTclAxi`, `JtagBackend`); `bringup.py --host jtag` passes dry-run
  - [B] all on-board steps: awaiting power, board, and "board ready" (CLAUDE.md §8)

### Experiment map without Raspberry Pi (ADR-025, ADR-026)

| Experiment | Without Pi (JTAG-HS2 + PC) | Notes |
| --- | --- | --- |
| Bring-up: clock, LED, bank voltages, buttons, XADC | yes | `board/BRINGUP_NO_PI.md` steps 3–8 (needs power) |
| E7 bit-exact on safe clock | yes | `bringup.py validate --host jtag` |
| E1 error atlas (frequency sweep) | yes | frequency via register; image upload slower than SPI |
| E2 determinism | yes | same image and settings repeated |
| E3 onset per layer | yes | `TURBO_MASK` per layer |
| E4 three modes | yes, for accelerator throughput | end-to-end time via JTAG not representative of SPI |
| E5 fault injection | already [SIM]; on board yes | `INJ*` registers |
| E6 governor and temperature | yes | `TEMP` and XADC dashboard |
| E8 resource and power costs | does not need board | [VIVADO-STA] |
| Native SPI and its speed | no, needs Pi | |
| `irq_done` signal | no, needs Pi | |
| Real-time camera mode | no, needs Pi (or laptop with MockBackend, without FPGA) | `docs/CAMERA.md` |
| End-to-end latency and final demo | no, needs Pi | |


## Team info, 17 Nov 2026

Not yet from official documents:
1. JTAG-HS3 cable is provided as a set with ZERO7 board (replaces blocked item "whether cable is included in loan package").
2. Each team uses their own Raspberry Pi 4; Pi 4 compatibility with ZERO7 [UNKNOWN] until organizers reply.
3. ZERO7 and JTAG-HS3 available starting 20 Nov 2026; Raspberry Pi 4 may arrive later.

PROMPT_UPDATE_ZERO7 from previous session is finished (T0–T10 `[x]`); no remaining stages. Session 17 Nov 2026 works on PROMPT_PARHI_KAMERA_TANPA_PI.

## Team decisions, 25 Nov 2026 (keputusan tim)

These supersede conflicting entries in this file and in earlier prompts (details and photo observations in `board/BOARD_INFO.md`).

1. **Raspberry Pi 5 is available now** (8 GB, photo) and replaces the Raspberry Pi 4 plan (ADR-022) and the "Pi 5 from ~3–4 Jan" note below. Pi 5 compatibility with ZERO7: [UNKNOWN] until shown on the board or confirmed by the organizers.
2. **ZERO7 is in the user's hands** (photos in `board/photos/`). The board phase still starts only per CLAUDE.md §8 (mandatory BOARD_INFO fields without UNKNOWN, and "board siap").
3. **Debugger: SEGGER J-Link** (20-pin JTAG), no Digilent cable. Vivado route: J-Link XVCD Server (J-Link software ≥ V7.92d, port 2542 [VERIFIED EXTERNAL]); programming and ILA through it [UNKNOWN] until the user tests it. `docs/JLINK_VIVADO.md`.
4. **Camera only through the Raspberry Pi** (Pi captures, scales to 32×32, sends over SPI); no camera module on the FPGA. Camera type (USB or CSI) is a question for the user; a video file is the development stand-in, and the report must say the real camera demo is untested until it is.
5. **Contest class (decided 25 Nov 2026): Class 2 Level 3, image classification, no camera** (ADR-036, ADR-035). Earlier text: contest class: user decision pending. ADR-036 (Proposed) compares Class 1 Level 3 and Class 2. Conflict to reconcile: the 23 Nov record says the organizers confirmed Class 2 (below and `docs/official/CORRESPONDENCE_2026-11.md` §1). `CLAUDE.md` §7 is not changed. The XC7S25CSGA225-1 synthesis report is mandatory either way [OFFICIAL].

Effect on the board phase: power through the Raspberry Pi header is the only documented method (IN-41) and is now available; a standalone supply stays unconfirmed. The remaining hardware blockers are the verified XDC (bank voltages, I/O standards), the JTAG header location on this board, and whether the J-Link works through XVC.

## Stage 3: board preparation on the PC side (PROMPT_TAHAP3, 25 Nov 2026)

- [x] 3.1 Pi 5 software: gpiozero on the lgpio factory chosen explicitly, `pi_check` checks lgpio, `board/BRINGUP.md` Pi 5 setup; camera mode takes picamera / USB index / video file and is tested on a video file without a Pi
- [x] 3.2 `docs/JLINK_VIVADO.md`: J-Link XVCD Server route, openFPGALoader fallback, wiring table (ZERO7 header UNKNOWN), safety checklist, five-step test order
- [x] 3.3 Bring-up: `blink` (CLK20M B13, LED R3/R2, f_clk = 2·HALF·n/t), `io_test` (buttons, WS2812B), new `spi_loopback` (SPI0 CE0 echo, `tb_spi_loopback` PASS 619/619 [SIM], `board/spi_loopback_check.py` for the Pi); `board/zero7.xdc` uses no QSPI, JTAG or configuration pin
- [x] 3.4 Vivado reports for the bring-up designs in `results/vivado/bringup/` (blink, io_test, spi_loopback: all fit, WNS > 0 at 20 MHz, DRC 0 checks; Evidence log); SENTINEL already fits (LUT variant 6,832 LUT, DSP variant 5,472 LUT + 14 DSP of 14,600 LUT / 80 DSP [VIVADO-STA])
- [x] 3.5 ADR-033 (Pi 5), ADR-034 (J-Link), ADR-035 (camera via Pi) accepted as team decisions; ADR-036 (class) Proposed; SPEC header, §14 and §15 updated

**On hold by the user (25 Nov 2026): the hardware steps below wait for the user's instruction; development continues first.**

**Waiting for the user (hardware), in this order** (details in `docs/JLINK_VIVADO.md` and `board/BRINGUP.md`):
1. Identify the JTAG header on the white ZERO7 from an official source (ask the organizers with the user manual / XDC question).
2. Board on the Pi 5, Pi on its USB-C supply: confirm a ZERO7 LED lights (IN-41); measure the header Vref voltage; optional USB power meter.
3. Install J-Link software ≥ V7.92d; run `JLinkXVCDServer.exe`; paste the output (VTref, hardware version).
4. Vivado Hardware Manager, Add XVC localhost:2542: paste the device list (expect `xc7s25_0`, IDCODE `037C4093`).
5. Program `blink`; report LED behaviour and a stopwatch count.
6. Try an ILA through XVC; if it fails, report and use VIO / LEDs / SPI.
7. On the Pi 5: `python3 board/pi_check.py`, then program `spi_loopback` and run `python3 board/spi_loopback_check.py`; paste both outputs.
Each pasted output becomes [HW] evidence in `results/hw/` and the Evidence log. The board phase itself (B1–B6) starts only per CLAUDE.md §8.

## Organizer clarifications and hardware dependencies (23 Nov 2026)

Source: organizer responses as relayed by the user on 23 Nov 2026, and the organizer website checked the same day. Full record with status labels: `docs/official/CORRESPONDENCE_2026-11.md`. Nothing below changes the SPEC or any ADR; decisions still needed are listed at the end.

**A. Confirmed by organizer**
- SENTINEL is **Class 2 (ZERO7 Class), Level 3** only. Topic and evaluation method are free; the implementation **must use ZERO7**.
- Class 2 is not limited to image classification. The organizer validation images are for Class 1 and **do not apply to Class 2**.
- Real-time camera input is **not mandatory** for Class 2; other input sources are allowed.
- All teams submit a synthesis report for **XC7S25CSGA225-1**. Final report and synthesis report are both due **31 Jan 2027**. The final report is recommended to include hardware design, implementation details and available test or evaluation results.
- Final contest **5 Mar 2027**, hybrid (on-site and Zoom), 10 min presentation + 5 min Q&A.
- ZERO7 technical documentation is published on the specification page (setup guide, user manual, connection table, as stated by the organizers).

**Official website, 23 Nov 2026**
- News 2026/11/19: recognition targets of the Design Specification are four classes, cat, dog, deer, horse, with 32 × 32 input and organizer photos on the contest day. Per the Class 2 clarification above, this task is not mandatory for SENTINEL.
- The ZERO7 documents section links only the setup guide and the connection table; **no user manual and no XDC file are linked** (conflicts with the organizer statement above; ask for the link).

**B. Pending organizer response**
- ZERO7 power without a Raspberry Pi: methods and specifications. No standalone power method is confirmed; do not attempt one.
- Separate provision of the official `Zero7.xdc`. Bank voltages and IOSTANDARD remain unverified; `board/zero7.xdc` keeps its TODO markers and no board bitstream is built.
- JTAG: whether alternative cables can replace the Digilent JTAG-HS2; whether additional JTAG-HS2 cables will be provided; borrowing or distribution procedure.
- Exact synthesis report format and contents.
- Live hardware demonstration requirements and procedure.

**C. User-provided**
- A Raspberry Pi 5 from the user's lecturer is expected from about **3–4 Jan 2027**: 27–28 days before the report deadline, 60–61 days before the contest.

**D. Dependencies of the board phase**

| Work | Needs | Status |
| --- | --- | --- |
| Verified XDC (bank voltages, IOSTANDARD) | official XDC, user manual or schematic | pending (B) |
| Powering ZERO7 | Raspberry Pi (Pi 5 from ~3–4 Jan) or an organizer-confirmed alternative | pending (B, C) |
| Programming and debugging (B1–B3, JTAG host experiments) | working JTAG cable compatible with ZERO7, plus power | cable availability to be confirmed with user; alternatives pending (B) |
| Native SPI, `irq_done`, end-to-end latency, optional camera | Raspberry Pi | Pi 5 from ~3–4 Jan (C) |
| E7, E1–E4, E6 [HW] | all of the above | not started |

Host software uses `gpiozero` and `spidev`, the same libraries as the official ZERO7 examples on a Raspberry Pi 5 [INFERENCE: no Pi-4-specific library]; `board/pi_check.py` checks them on the Pi.

**E. Schedule assessment** [TECHNICAL RECOMMENDATION, not an organizer requirement]
- Everything that does not need the board is done (M0–M14 and M15–M22 non-board parts; 257 tests; both XC7S25 synthesis reports). The open work is the whole board phase B1–B6 plus the final report.
- If the board can only be powered from 3–4 Jan: about one week for B1–B2 (verified XDC, bitstream, JTAG, bring-up), one week for B3 (E7 bit-exact on safe clock), one week for B4 (E1 atlas, E4 three modes on the LUT variant, DSP variant throughput), and the last week for the report. This has no slack: any delay from power, XDC or JTAG moves [HW] results past 31 Jan. E6 and the automatic governor on board would likely move to the period before 5 Mar.
- The "freeze hardware 17 Jan" date and G1/G2 do not fit this timeline; re-planning is a user decision.
- Before 3 Jan: get the user manual / XDC answer and finish the verified XDC; confirm JTAG cable on hand; decide the Class 2 evaluation method (see below); prepare the report parts that do not need hardware; keep the bitstream build ready to run once I/O standards are verified.

**F. Decisions needed from the user (none taken)**
1. Class 2 evaluation method: keep the CIFAR-10 10-class stand-in, or retrain for the four official classes (cat, dog, deer, horse are all CIFAR-10 classes; the pipeline supports any class count up to 16 without resynthesis). A change goes through an ADR → SPEC → golden model → RTL as usual.
2. Re-plan G1, G2 and the hardware freeze date; whether to apply the documented fallback (single global turbo clock).
3. ADR-022 assumes a Raspberry Pi 4; switching the host to the Raspberry Pi 5 needs an ADR once the user confirms.
4. `CLAUDE.md` §7 still lists the category as a proposal and real-time camera as a requirement; updating it needs user approval.

## Questions for organizers (17 Nov 2026)

Status of answers (communicated by user, 17 Nov 2026): Q1 not yet informed; Q2 not yet known; Q3 LSI team still finding out; Q4 awaiting LSI reply; **Q5 answered: 4-person team confirmed** [USER]; Q6 awaiting further information.

Status update (23 Nov 2026, organizer responses relayed by user; details in `docs/official/CORRESPONDENCE_2026-11.md`): **Q1** pending (committee must first confirm power methods and specifications). **Q2 answered:** camera not mandatory for Class 2. **Q3** no answer recorded (Raspberry Pi 4 compatibility). **Q4** partly answered: organizers say documentation is published; website shows no user manual link; separate XDC provision pending. **Q6** partly answered: Class 2 Level 3 confirmed; synthesis report format pending. **Q7** partly answered: final report recommended to include available test or evaluation results; organizer validation images do not apply to Class 2; live demonstration procedure pending. **Q8 (new, pending):** alternative JTAG cables to the Digilent JTAG-HS2, additional JTAG-HS2 cables, and the procedure to obtain them.

1. **Q1 Power:** how to power ZERO7 without Raspberry Pi? Document only mentions power from Pi header (IN-41). Recommendation: ask; until an answer exists, use any Raspberry Pi solely as power source.
2. **Q2 Camera in Class 2:** is real-time camera input mandatory also for Class 2 if the task is image classification? Recommendation: consider mandatory (`docs/CAMERA.md`).
3. **Q3 Raspberry Pi 4:** is ZERO7 officially compatible with Pi 4? Recommendation: request written confirmation.
4. **Q4 Documents:** when will `Zero7.xdc`, ZERO7 User Manual, and schematics be published? Recommendation: request alongside board.
5. **Q5 Team size:** English page 1–3 persons, Japanese page at most 4; team has 4 members. **Answered (user, 17 Nov 2026): 4 persons confirmed.** Remaining action: save written confirmation proof (email/organizer message) for appendix if requested.
6. **Q6 Category and report format:** confirm Class 2 Level 3 and synthesis report format. Recommendation: ask concurrently.
7. **Q7 Board in final report (added 18 Nov 2026):** for Class 2, must final report on 31 Jan 2027 already include results running on ZERO7, and will validation image recognition on 5 Mar 2027 be demonstrated live (on-site or via Zoom)? Official website (checked 18 Nov 2026, latest news 10 Nov 2026) only mandates final report and XC7S25CSGA225-1 synthesis report by 31 Jan; Class 2 is defined as using ZERO7, and validation images are provided on the day of the contest [OFFICIAL]. Recommendation: inquire alongside Q6; until an answer exists, plan for [HW] results prior to 31 Jan.

## Blocked

Updated 2026-11-26.

- [B] Work on the real hardware — board and Raspberry Pi 5 are in hand (25 Nov 2026), but the user holds every hardware step until development and architecture are finished (26 Nov 2026) [USER]. All `[HW]` experiments (E1–E4, E6, E7 on board) waiting. Earlier text: board and Raspberry Pi 4 from December 2026 or January 2027.
- [B] Official `Zero7.xdc`, VCCO voltage, and bank 14/15/34 IOSTANDARD — not yet published; `board/zero7.xdc` uses LVCMOS33 marked TODO. Bitstream for board must not be built before this is certain.
- [B] ZERO7 User Manual and schematics — mentioned by organizers, not yet linked on website.
- ~~[B] Pi 4 compatibility with ZERO7~~ superseded 25 Nov 2026: the team uses its own Raspberry Pi 5 (ADR-033).
- [B] ZERO7 power without Raspberry Pi — official documents only mention power from Pi GPIO header (IN-41); other methods [UNKNOWN], ask organizers. Without power, steps without Pi cannot begin.
- [B] Actual SPI speed, button polarities, WS2812B chain, boot from QSPI flash — needs board or user manual.
- ~~[B] Target classes~~ decided 25 Nov 2026: the four official classes cat, dog, deer, horse (ADR-037, model `s4`). History: not announced at first (CIFAR-10 used temporarily). Update 23 Nov 2026: the website lists four classes (cat, dog, deer, horse) for the image classification task; for Class 2 they are not mandatory (organizer). Choice of the Class 2 evaluation method is a user decision.
- [B] JTAG programming and debug (updated 25 Nov 2026): the team uses a SEGGER J-Link through the J-Link XVCD Server, untested [UNKNOWN]; JTAG header location and pin order on this white ZERO7 not identified; VCC3V3 at the header to be measured by the user before VTref is connected. Organizer question on alternative cables still pending. Blocks B1–B3 and the JTAG-host experiments.
- ~~[B] Raspberry Pi for power and SPI~~ resolved 25 Nov 2026: Raspberry Pi 5 available now [USER]; Pi 5 compatibility with ZERO7 [UNKNOWN] until tested.
- ~~[B] Camera type~~ resolved 25 Nov 2026: no camera (ADR-035 update); images from files on the Pi.
- ~~[B] Contest class~~ decided 25 Nov 2026: Class 2 Level 3, image classification (ADR-036); class set decided by ADR-037.
- [B] Official synthesis report format — not yet explained by organizers; currently in the form of Vivado `.rpt` files and `summary.md` in `results/vivado/official/` (LUT variant) and `results/vivado/official_dsp/` (DSP variant).
- [B] Full text of Li et al. (ITC-Asia 2019): user did not find it; claims regarding recovery use the phrase "to the best of our knowledge".

No longer blocked since official documents of 10 Nov 2026: part number and speed grade (xc7s25csga225-1), pins (connection table), F_IN, programming method. What can now be done without board: XDC, MMCM table for 20 MHz, board top-level, synthesis and implementation on official part, and official synthesis report.

## Decisions ADR-028 through ADR-032 (18 Nov 2026)

- [x] ADR-029 checksum weight flat tree (`rtl/wc_gen.v`): bench `wc_gen_*` bit-exact between old and new RTL, 10⁶ vectors PASS; OOC Fmax clk_safe 141.7 → 144.3 MHz; LUT official report 132.9 → 133.7 MHz [VIVADO-STA]; accepted (see Evidence log)
- [x] ADR-030 option (d) with R1 narrative: `variant_dsp` block in `config/hw_zero7.yaml`, `synth-official --variant dsp` → `results/vivado/official_dsp/`, guard test for both reports, benches `engine_s_k8_c1_dsp*` and `system_s_k8_c1_dsp`, variant labels in [HW] metadata, slides and draft report adjusted
- [x] Reset fan-out fix `rst_safe_r` (`max_fanout = 64`, approved by user 18 Nov 2026): clk_safe LUT 133.7 → 136.6 MHz, DSP 126.7 → 132.4 MHz; DSP lane at 250 MHz 262.0 → 256.5 MHz (still passing) [VIVADO-STA]
- [~] ADR-028 zero-skip (gate lifted by ADR-038; G1 status above): implemented behind `ZERO_SKIP` (default 0). The first version hung on images 118 and 198 (result serializer overrun); guard `ZERO_SKIP = 1` chosen over the `fast_path` stall (`ZERO_SKIP = 2`): both bit-exact 200/200 and 31.70 % fewer cycles [SIM], mode 1 keeps more slack [VIVADO-STA]. With zero-skip on, the LUT variant loses Fmax (clk_safe 136.6 → 134.9 MHz, clk_fast 140.8 → 135.8 MHz). DSP variant (user asked to test it): bit-exact 200/200 and no Fmax loss, but no speed gain at the real clock ratio (lanes at 2 × clk_safe: −0.002 %; lanes at clk_safe: −32.97 %) [SIM]. Decision: not used in either build; `ZERO_SKIP = 0` stays the default; zero-skip remains a tested option for lanes below the supply limit
- [x] ADR-032 (b) for the DSP variant (user: "choose the best", 26 Nov): clk_safe 142.857 MHz, lanes analysed at turbo level 255 MHz; official DSP report clean (clk_safe WNS +0.198 ns, lanes +0.173 ns) [VIVADO-STA]; official system scenarios PASS 10/10 at the new ratio; 1.230 ms per image instead of 1.299 ms (−5.3 %) [SIM]; LUT variant stays at 125 MHz
- [x] ADR-031 (c) split LUT multiplier + per-lane activation register (D5): bit-exact [SIM]; official clk_fast 140.8 → 146.6 MHz, OOC fast domain 156.3 → 159.3 MHz with SPEC 7.4 kept, clk_safe not worse, +395 FF [VIVADO-STA]; accepted 26 Nov 2026

## Notes for next session

**Written 26 Nov 2026 (zero-skip fix, model s4).** Read this block first.

- Update later on 26 Nov: the user approved the reviewed CLAUDE.md/AGENTS.md/translations (committed), asked to test zero-skip on the DSP variant (done: no speed gain at the supply limit, not used, see ADR-028) and to move the official build to s4 (done: `config/hw_zero7.yaml` MODEL s4, `system_s4_k8_c1` PASS 10/10). Real-hardware work stays on hold until development and architecture are finished. ADR-032 study and ADR-031 + D5 approved by the user later the same day: ADR-031 (c) accepted (split LUT multiplier + D5); ADR-032 study met timing at 142.857 MHz, adoption waits for the user.
- Position: model `s4` (four official classes, ADR-037) trained, exported and bit-exact in RTL (200/200). Zero-skip (ADR-028) implemented behind `ZERO_SKIP`; the first version overran the lane-array result serializer on images 118 and 198; guard `ZERO_SKIP = 1` chosen (details in ADR-028). Zero-skip is **stopped and reported**: with it on, Fmax drops (clk_safe 136.6 → 134.9 MHz, clk_fast 140.8 → 135.8 MHz) for 31.70 % fewer cycles; `ZERO_SKIP = 0` stays the default and the official reports are unchanged (base26 rerun identical).
- Waiting for the user: (1) nothing open from ADR-038 (ADR-032 (b) adopted for the DSP variant on 26 Nov); (2) when to resume the hardware steps (on hold until development and architecture are finished); (3) whether G1 counts as threatened (see "G1 status" at the top).
- ADR-038 list: all items handled (ADR-037 done, ADR-028 tested and not used, ADR-031 accepted, ADR-032 (b) adopted for the DSP variant).
- `docs/REPORT_DRAFT.md` and `docs/SLIDES_OUTLINE.md` still describe the DSP lanes at 250 MHz and the LUT lane before ADR-031; update them when the report is written (the user asked not to write the report yet).
- New tools: `build/sim/logs/<bench>[_s<shard>].log` fill while a bench runs (`Get-Content -Wait`); tb_engine prints `IMG i done cycles=n` and fails an image after `+maxcycles` (default 2,000,000); the runner kills the whole process tree on timeout; an exact bench name no longer also runs longer names that start with it. `python tools/zs_compare.py` builds the zero-skip table from logs.
- Gotchas: under xsim `$fatal` printed the FAIL and the run went on, so tb_engine now calls `$finish` after it (other testbenches still rely on the runner's FAIL check). Do not judge a netlist change from simulation alone: the ungated zero-skip mux was bit-exact but added 118 LUTs with `ZERO_SKIP = 0`. A bench with the same name overwrites its logs; copy them to `results/` before a rerun if they are evidence.

**Written 25 Nov 2026 (PROMPT_TAHAP3, stage 3 board preparation).** Read "Team decisions, 25 Nov 2026" and "Stage 3" above first; they supersede the Pi 4, Digilent cable and Pi-5-in-January notes further down.

- Position: the PC-side preparation is done (3.1–3.5 `[x]`). The board phase (B1–B6) has not started: CLAUDE.md §8 still needs the mandatory BOARD_INFO fields without UNKNOWN (board revision, bank-15 voltage, LED3/LED4, official XDC or schematic, SW7 positions) and the user's "board siap".
- Next, in order: (1) the user's hardware steps 1–7 in "Stage 3"; turn each pasted output into `results/hw/` evidence with label [HW]; (2) the user's decision on ADR-036 (class), then an evaluation-method ADR (for example retraining for cat/dog/deer/horse) through ADR → SPEC → golden model → RTL; (3) once I/O standards are verified from an official source, remove the TODO markers in the XDC files and build the SENTINEL bitstream for E7.
- Open questions for the user: camera type (USB webcam or CSI); class decision and the conflict with the 23 Nov record of an organizer Class 2 confirmation; JTAG header location on the white board; whether the DC jack "POW" may be used (ask the organizers, do not use meanwhile).
- Gotchas: Bash heredocs that write Python with `\\n` inside triple-quoted strings produce real newlines; use the Edit tool for such strings. `results/vivado/bringup/` holds reports only; bitstreams stay in `build/bringup/`. The working tree still holds uncommitted work of another agent (CLAUDE.md §10, AGENTS.md, `.agents/`, `graphify-out/`, translated docs, a deleted `docs/official/superseded/GUIDE_LSI_2027.pdf`); it was left untouched.

**Update 23 Nov 2026:** read "Organizer clarifications and hardware dependencies (23 Nov 2026)" above first; it supersedes the category, camera and target-class assumptions in the notes below. The full handoff will be written separately when the user authorizes it.

Written 18 Nov 2026.

**To resume:** decisions ADR-028 through ADR-032 are in the section above and in `docs/DECISIONS.md`. Reset fan-out fix already completed. Board phase not yet started (CLAUDE.md §8).

**Position:**
- ADR-030: user left choice of R1/R2 to Claude. Claude chose R1 now and R2 after G1 (ADR-032), because R2 changes SPEC §5 and jeopardizes G1. DSP variant = speed and demo variant; LUT variant = overclock research variant. Numbers across variants must not be mixed.
- ADR-029 accepted; only side effect was clk_safe DSP variant (126.7 MHz, still passes 125 MHz), caused by routing reset net, not `wc_gen`.
- `CLAUDE.md` §7 updated: 4-person team confirmed (approved by user 18 Nov 2026).
- Team JTAG cable: Digilent JTAG-HS2 Rev. A [USER, photo]; `board/BRINGUP_NO_PI.md` step 2 already uses HS2 label. VDD pin function (equivalent to VREF) not yet checked in Digilent manual (site rejects automated access).
- User message of 18 Nov 2026 contained an empty "2." item; ask for its content.

**Next steps, in order:**
1. Organizer replies on Q6 and Q7 (category, report format, whether ZERO7 results mandatory in final report).
2. 20 Nov 2026 and after: as soon as power is available and user writes "board ready", follow `board/BRINGUP_NO_PI.md` (check HS2 VDD pin first).
3. After G1: ADR-028, then ADR-032 study (`--safe-div 7` first).
4. Report item D6 anytime before 31 Jan 2027.

**Gotchas discovered:**
- System Python lacks torchvision; use `.venv/Scripts/python` or `tools/run.py`.
- `run.py sim <name>` matches prefixes: `wc_gen_k8_c1` also runs `wc_gen_k8_c1_1m`, `engine_s_k8_c1` also runs all n200 and DSP variants.
- Do not run same bench from two processes (e.g. `run.py sim` while `run.py test` is running): both use same `build/` folder and corrupt results.
- Many `assign`s to slices of one vector make Icarus very slow; use a single packaging function (see `rtl/wc_gen.v`).
- `always @*` not evaluated at time zero in Icarus if inputs do not change; produces X in early cycles.
- PC memory around 12 GB with around 2 GB free: run Vivado runs sequentially, not in parallel.
- `fpga/parse_reports.py` with tag now merges rows into `summary.csv` (previously overwrote entire table).
- Timing margin at 125 MHz is narrow; on every RTL change: rerun both `synth-official`; guard test rejects unclean reports.

## Evidence log

| Date | Milestone | Command | Result |
| --- | --- | --- | --- |
| 2026-11-10 | M11 | timing fix ADR-012, rounds v2–v4 on xc7s25csga225-1 | [VIVADO-STA] Fmax clk_safe increased from around 102 to 139–148 MHz (K=8) |
| 2026-11-10 | M11 | `python tools/run.py ooc ... --nonmac-factor 0.7` (lut, K=8) | [VIVADO-STA] C3=0: non-MAC paths pass 70% period (slack +0.226 ns), 20 worst paths of clk_fast are MAC; C3=1 misses by 0.008 ns |
| 2026-11-10 | M11 | `python tools/run.py ooc --parts <8 part> --tag final` | [VIVADO-STA] 48/96 runs succeeded (xc7s25, xc7s50); xc7s6 and xc7s15 did not fit: insufficient BRAM. Table in docs/RESULTS_SIM.md |
| 2026-11-10 | M4–M10 | `python tools/run.py sim lane_array checker engine spi system governor --record ...` | [SIM] 37/37 benches passed after pipeline changes; s K=8 200/200, xs K=8 200/200, overhead s K=16 9.9% |
| 2026-11-10 | M11 | `python tools/run.py ooc --parts xc7s25csga225-1 --k 8` | [VIVADO-STA] 6 variants completed; see fpga/reports/summary.csv. Safe domain passes 10 ns target; LUT lane fails 5 ns target |
| 2026-11-09 | M0 | `python tools/run.py check --write` | Python 3.13.1, Icarus 12.0 devel, Vivado 2025.2 detected, Verilator 5.053 lint; see docs/ENVIRONMENT.md |
| 2026-11-09 | M0 | `python tools/run.py test` | 189 passed (pytest, lint, fast benches) |
| 2026-11-09 | M1 | `python tools/run.py train --model s` | [SIM] float test 0.8048, seed 2027, 120 epochs; results/model/s/float_result.json |
| 2026-11-09 | M1 | `python tools/run.py train --model xs` | [SIM] float test 0.7290, seed 2027, 120 epochs; results/model/xs/float_result.json |
| 2026-11-09 | M1 | `pytest tests/test_arch_report.py` | SPEC §2 numbers and §5.4 cycles match (no ADR needed) |
| 2026-11-09 | M2 | `python tools/run.py export --model s` | [SIM] integer 0.8022 vs float 0.8048, dropped 0.26 points; per-tensor PTQ |
| 2026-11-09 | M2 | `python tools/run.py export --model xs` | [SIM] integer 0.7250 vs float 0.7290, dropped 0.40 points |
| 2026-11-09 | M2 | `export --model s --from-quant` twice, `sha256sum build/weights/s_k8.bin` | identical hash: 534f3862cf31b5e8 (twice); test_export_is_deterministic passed |
| 2026-11-09 | M3 | `python tools/run.py campaign --model s` | [SIM] K=8 C3=0: single 10000/10000 corrected, two lane 9403 recompute and 597 miscorrected, checksum lane 1000/1000 recompute; C3=1 two lane 0 miscorrected. Full table in docs/RESULTS_SIM.md |
| 2026-11-09 | M4 | `python tools/run.py sim lane_array` | lane_array_k8_c1_dsp_full: PASS 5720/5720 (icarus); lane_array_k8_c1_dsp_min: PASS 5720/5720 (icarus); lane_array_k8_c1_lut: PASS 5720/5720 (icarus); lane_array_k16_c0_lut: PASS 9360/9360 (icarus); lane_array_k16_c0_dsp_full: PASS 9360/9360 (icarus); lane_array_k16_c0_dsp_min: PASS 9360/9360 (icarus); lane_array_k16_c1_lut: PASS 9880/9880 (icarus); lane_array_k16_c1_dsp_full: PASS 9880/9880 (icarus); lane_array_k16_c1_dsp_min: PASS 9880/9880 (icarus); lane_array_k8_c0_lut: PASS 101000/101000 (icarus); lane_array_k8_c0_dsp_full: PASS 101000/101000 (icarus); lane_array_k8_c0_dsp_min: PASS 101000/101000 (icarus) |
| 2026-11-09 | M5 | `python tools/run.py sim checker` | checker_k8_c0: PASS 5034/5034 max_latency=11 (icarus); checker_k16_c0: PASS 5050/5050 max_latency=19 (icarus); checker_k8_c1: PASS 10068/10068 max_latency=11 (icarus); checker_k16_c1: PASS 10100/10100 max_latency=19 (icarus) (covering all decision branches; see build/vectors/.../meta.json) |
| 2026-11-09 | M6 | `python tools/run.py sim engine_corner_extreme engine_corner_saturate engine_corner_ties engine_corner_zero_lanes engine_s_k16_n20 engine_s_k8_n200 engine_xs_k8_n200` | engine_xs_k8_n200: PASS 200/200 (34/34 cycles_mean=83823 ideal=83456) (xsim); engine_s_k8_n200: PASS 200/200 (34/34 cycles_mean=277871 ideal=277504) (xsim); engine_s_k16_n20: PASS 20/20 (5/5 cycles_mean=150436 ideal=138752) (xsim); engine_corner_zero_lanes: PASS 6/6 cycles_mean=173804 ideal=0 (xsim); engine_corner_extreme: PASS 6/6 cycles_mean=173804 ideal=0 (xsim); engine_corner_ties: PASS 6/6 cycles_mean=173804 ideal=0 (xsim); engine_corner_saturate: PASS 6/6 cycles_mean=173804 ideal=0 (xsim) cycle overhead: s K=8 0.13%, xs K=8 0.44%, s K=16 8.4% [SIM] |
| 2026-11-09 | M7 | `python tools/run.py sim spi_session_xs spi_slave` | spi_session_xs: PASS 224/224 polls=421 (xsim); spi_slave: PASS 19/19 (icarus) (ID, load weights, write image, START, read class/logits/counters, ping-pong IMG0/IMG1); test_generated_files_are_up_to_date passed |
| 2026-11-09 | M8 | `python tools/run.py sim system_micro_corners system_xs_r100 system_xs_r130 system_xs_r170 system_xs_r200` | system_xs_r100: PASS 8/8 reconfigs=0 (xsim); system_xs_r130: PASS 8/8 reconfigs=0 (xsim); system_xs_r170: PASS 8/8 reconfigs=0 (xsim); system_xs_r200: PASS 8/8 reconfigs=0 (xsim); system_micro_corners: PASS 5/5 reconfigs=0 (xsim) (f_fast/f_safe ratio 1.0/1.3/1.7/2.0; mode 0/1/2 injection; counters and FATAL/full log match model) |
| 2026-11-09 | M9 | `python tools/run.py sim system_micro_campaign_k16_c1 system_micro_campaign_k8_c0 system_micro_campaign_k8_c1` | system_micro_campaign_k8_c0: PASS 2400/2400 reconfigs=0 (xsim); system_micro_campaign_k8_c1: PASS 2400/2400 reconfigs=0 (xsim); system_micro_campaign_k16_c1: PASS 2400/2400 reconfigs=0 (xsim) (7,200 scenarios including two lanes and checksum lane; using random-weight micro model [SIM]) |
| 2026-11-09 | M10 | `python tools/run.py sim governor system_micro_autogov` | governor: PASS 2400/2400 scenarios=60 (icarus); system_micro_autogov: PASS 12/12 reconfigs=8 (xsim) (60 state trajectory scenarios; SPEC §7.7 sequence monitored by protocol monitor, 8 reconfigurations); pytest tests/test_mmcm_table.py passed with unverified limits |
| 2026-11-09 | M11 | `python tools/run.py ooc` | exit code 2: Vivado has no Spartan-7 device; written instructions; [B] requires user run |
| 2026-11-09 | M12 | `pytest tests/test_software.py`; `python -m sentinel.experiments.e1..e8`; `python tools/run.py plots` | 7 plots; e1-e4,e6,e7 mock [SYNTHETIC], e5 [SIM], e8 estimation [SIM] |
| 2026-11-09 | M13 | `python tools/gen_results_doc.py` | docs/RESULTS_SIM.md from result files; other docs written without new numbers |
| 2026-11-09 | M14 | `pytest tests/test_board_package.py`; `python board/bringup.py validate --dry-run` | dry-run passed; build refused to run because BOARD_INFO UNKNOWN |
| 2026-11-16 | T0 | `python tools/run.py check`; `python tools/run.py test` | all tools ok (Vivado 2025.2, Icarus 12.0, Verilator 5.053); 190 passed in 227.70s; log `build/test_full_2026-11-16.log` |
| 2026-11-16 | T1 | read `GUIDE_LSI_2027_FINALE.pdf` (6 pp.), `ZERO7FPGA_Connection-table_261109_001.pdf` (7 pp.), `Initialize_20260618_EN.pdf` (59 slides), `index.html` and `shiyou_1.html` (Japanese) | three PDFs archived to `docs/official/`, old guide to `superseded/`; `docs/official/README.md` and three `docs/references/` notes written; Japanese PDF `Initialize_20260618.pdf` not yet archived (awaiting download permission) |
| 2026-11-16 | T2 | web search (20 queries), OpenAlex, arXiv API; organizer Japanese page via browser | `docs/research/RISET_WEB_2026-11.md`; no publicly visible other teams' projects for 2027 contest; full text of Marty et al. and Li et al. not yet readable (access denied) |
| 2026-11-16 | T3 | `vivado -mode batch -source tools/vivado_check_part.tcl` | status SUFFICIENT: Vivado 2025.2, xc7s25csga225-1 found; 14600 LUT, 29200 FF, 45 block RAM, 80 DSP, 3 MMCM [VIVADO] (`results/vivado/part_check.txt`); `vivado` not in PATH; Zynq-7000 not installed |
| 2026-11-16 | T4 | `vivado -mode batch -source board/pin_check.tcl` | B13 = IO_L13P_T2_MRCC_15, clock-capable; bank 14/15/34 HR type [VIVADO] (`results/vivado/pin_check.txt`); `board/BOARD_INFO.md` populated from official documents; `board/zero7.xdc` created |
| 2026-11-16 | T4 | `pytest tests/test_board_package.py` | 8 passed. Old tests mandating "Part number" and "Clock input" still UNKNOWN replaced (reason: both facts now official): detection logic tested with fixtures, official facts tested remaining filled, and `board/zero7.xdc` tested against connection table; guards rejecting build and hardware steps while UNKNOWN fields remain were unchanged |
| 2026-11-16 | T5 | targeted text search across entire repo | `docs/REVIEW_2026-11.md`: 20 findings, each with follow-up |
| 2026-11-16 | T6 | ADR-013 through ADR-020 in `docs/DECISIONS.md`; SPEC §1, §2, §7.6, §12.1, §12.4, §14, §18 updated | target locked to xc7s25csga225-1; official variant K=8, lut, C3=1; milestones M15–M19 added |
| 2026-11-16 | M15 | `python tools/run.py synth-official` on commit 7a2d369 (saved as `results/vivado/official_preadr021/`) | [VIVADO-STA] full design fits: 6,172 LUTs, 14 of 45 block RAMs, all nets routed; intra-clock paths pass at 125 MHz (+0.286 ns `clk_safe`, +0.204 ns `clk_fast`); one inter-clock path fails −0.499 ns (power-on reset from `clk_in`) |
| 2026-11-16 | M20 | ADR-021; `pytest tests/test_fpga_scripts.py` | test written first (failed), then RTL, constraints, and report flow modified; 16 passed |
| 2026-11-16 | M20 | `python tools/run.py synth-official` (intermediate run, `results/vivado/official_adr021a/`) | [VIVADO-STA] passed timing (WNS +0.326 ns), but `report_cdc` gave CDC-10 on reset synchronizers; reset structure modified to one synchronizer per source |
| 2026-11-16 | M15 | `python tools/run.py synth-official` (final, `results/vivado/official/`) | [VIVADO-STA] clk_safe 125 MHz: 6,170/14,600 LUTs (42.26%), 5,704 FFs, 14/45 block RAMs, 3 DSPs; design WNS +0.417 ns, WHS +0.037 ns, 0 unrouted nets; intra-clock Fmax 131.9 MHz (`clk_safe`) and 133.0 MHz (`clk_fast`); CDC: CDC-1 760, CDC-3 40, CDC-4 2, CDC-15 784, zero unsafe; bus skew 16 constraints, worst slack +6.962 ns; power 0.505 W (estimate) |
| 2026-11-16 | M16 | `python tools/run.py sim <all benches> --record results/sim/rtl_regression.jsonl` on final RTL | [SIM] 40 benches re-recorded, all passed; official variant: `PASS 200/200 (34/34 cycles_mean=277895 ideal=277504)`; dual-clock system `PASS 10/10 reconfigs=0` |
| 2026-11-16 | M16 | `pytest tests/test_sim_runner.py`; `python tools/run.py sim system_xs_r200 --record results/sim/rtl_regression.jsonl` | record writer fixed (test first); bench re-recorded: `PASS 8/8 reconfigs=0` dated 2026-11-16 |
| 2026-11-16 | M15–M20 | `python tools/run.py test` on final RTL | 206 passed in 293.53s (0:04:53); log `build/test_full_final.log` |
| 2026-11-16 | M15 | `python tools/gen_results_doc.py` | `docs/RESULTS_SIM.md` contains official [VIVADO-STA] report and [SIM] × [VIVADO-STA] latency budget |
| 2026-11-16 | M19 | `pytest tests/test_software.py` | 13 passed; driver waits for `irq_done` via done line then checks `STATUS.DONE`; test uses surrogate, not real GPIO |
| 2026-11-16 | T8 | `docs/JUDGE_REVIEW.md` | three rounds with internal rubric [PROPOSAL]; largest weaknesses: no [HW] results yet and MMCM2 sequencer missing |
| 2026-11-16 | T9 | `python tools/study_guide/figures.py`; `build_docx.py`; `finalize_word.ps1` | study guide version 1.1 with "Changes" section at start; `build/study_guide/SENTINEL_materi_belajar.pdf`, 46 pages (`build/` folder not committed) |
| 2026-11-16 | ADR-023 | read DS189 Table 37 (PDF p. 40), DS180 Table 2 (p. 2), UG480 v1.11, PG065; `pytest tests/test_mmcm_table.py` | limits and capacities `verified: true` with pages; old −2 value for max input/output corrected 933 → 800 MHz; old test requiring `verified: false` replaced (reason: datasheets verified) |
| 2026-11-16 | PRIOR_ART | read full Marty et al. TCAD 2020 (14 pp.), Xue et al. arXiv 2202.08675 (7 pp.), Jiang et al. arXiv 2505.13461 (19 pp.) | answers to three reasons of Marty et al. rejecting correction in `docs/PRIOR_ART.md` |
| 2026-11-16 | M17–M21 | `python tools/run.py sim xadc_temp regfile_guard ws2812_tx status_led clkwiz_seq` | [SIM] `PASS 4/4 reads=6`, `PASS 6/6`, `PASS 49/49`, `PASS 7/7 frames=10`, `PASS 49/49` |
| 2026-11-16 | M15 | `python tools/run.py synth-official` (with Clocking Wizard, XADC, WS2812B) | [VIVADO-STA] 6,862/14,600 LUTs (47.00%), 6,154 FFs, 14/45 block RAMs, 3 DSPs; WNS +0.648 ns, WHS +0.040 ns; power 0.510 W (estimate) |
| 2026-11-16 | ADR-024 | `vivado -mode batch -source fpga/bitstream_dryrun.tcl` | [VIVADO] `write_bitstream` passed (Bitgen Completed Successfully); bitstream DRC: 0 errors, 1 warning (RTSTAT-10); file `build/bitstream_dryrun/top_board_DRYRUN_NOT_FOR_BOARD.bit`, not used on board and not committed |
| 2026-11-16 | all | `python tools/run.py sim <all benches> --record ...`; `python tools/run.py test` | [SIM] 45 benches, all passed; 224 passed in 303.17s (0:05:03); log `build/test_full_partb.log` |
| 2026-11-16 | T9 | `python tools/study_guide/figures.py`; `build_docx.py`; `finalize_word.ps1` | study guide 1.1 rebuilt with Pi 4, ADR-022 through ADR-024, and latest official report; 46 pages (`build/`, not committed) |
| 2026-11-17 | Stage 0 | `python tools/run.py check`; `python tools/run.py test` | all tools ok; 224 passed in 434.38s (`build/test_tahap0.log`) |
| 2026-11-17 | M22 | local OCR (Windows OCR) of all TK and IN pages; search for power terms | ZERO7 power only stated via Raspberry Pi header (IN-41); other methods [UNKNOWN] |
| 2026-11-17 | M22 | `python tools/run.py sim bringup jtag_session_xs spi_session_xs system_s_k8_c1 system_micro ... --record` | [SIM] `bringup` PASS 10/10, `jtag_session_xs` PASS 25/25, `spi_session_xs` PASS 224/224, system passed all |
| 2026-11-17 | M22 | `python tools/run.py bringup blink/vcco_probe/io_test/jtag_host --accept-inferred-io` | [VIVADO] four bring-up bitstreams in `build/bringup/` (not committed); `top_jtag`: 8,048 LUTs (55.12%), 16.5 block RAMs, WNS +0.147 ns at 125 MHz [VIVADO-STA] |
| 2026-11-17 | M22 | `python board/bringup.py id/validate --dry-run --host jtag` | [SIM] ID OK, 3/3 images match golden model via JTAG path (device model) |
| 2026-11-17 | Task B | citations from `GUIDE_LSI_2027_FINALE.pdf` (OCR) and `shiyou_1.html` (Shift_JIS, local decode); prices from raspberrypi.com, waveshare.com, logitech.com (accessed 17 Nov 2026); `python -m sentinel.camera_mode --source ../build/camera_dryrun.avi` | `docs/CAMERA.md`: camera mandatory in Class 1 [OFFICIAL], Class 2 [UNKNOWN] (Q2); USB webcam recommended; test without Pi passes [SYNTHETIC] |
| 2026-11-17 | ADR-027 | `python tools/run.py synth-official` after ADR-025 | first run WNS −0.044 ns on `clk_sel_turbo` path to BUFGCTRL S1 (not committed); after ADR-027: 6,851/14,600 LUTs, WNS +0.473 ns, WHS +0.027 ns [VIVADO-STA] |
| 2026-11-17 | Task C | check book PDF (791 scanned pages, without text); local OCR of all pages to `build/parhi/ocr/` | no chapters read yet; map of chapter start pages in session notes |
| 2026-11-17 | end of session | `python tools/run.py test` | 237 passed in 230.19s (`build/test_end_17nov.log`) |
| 2026-11-17 | Task C | read OCR `build/parhi/ocr/page-018.txt` … `page-568.txt` per chapter; formulas and numbers checked on rendered pages `tools/parhi/render_pages.ps1` (PDF 35, 65, 66, 70, 88, 92, 99, 114, 118, 137, 151, 167, 170, 187, 248, 250, 252, 259, 274, 299) | Chapters 1–14 read in full, notes `docs/research/parhi/CH01.md`–`CH14.md`; zero unreadable pages; missing or duplicate scanned pages recorded per chapter (book pp. 62, 90, 188, 254, 312, 376, 420; PDF 79 = duplicate of p. 60) |
| 2026-11-17 | Task C | duplicate check script: 10-word n-grams from OCR of each chapter compared with CH01–CH14 | 0 identical 10-word sequences across 14 notes |
| 2026-11-17 | end of follow-up session | `python tools/run.py check` | all tools ok, including Vivado v2025.2, Icarus 12.0, Verilator 5.053 |
| 2026-11-17 | end of follow-up session | `python tools/run.py test` | 237 passed in 284.87s, exit 0 (`build/test_session_end.log`) |
| 2026-11-17 | Stage 0 | organizer answers from user | Q5 answered (4-person team confirmed); Q1, Q2, Q3, Q4, Q6 awaiting; recorded in Questions for organizers section |
| 2026-11-17 | Task B | `docs/CAMERA.md` section 3, cheapest options; `board/BRINGUP_NO_PI.md` step 1 | USB webcam already owned (free), then generic UVC webcam; OV5647 CSI $15.99 but ribbon clearance under ZERO7 [UNKNOWN] |
| 2026-11-17 | Task C | read OCR `build/parhi/ocr/page-569.txt` … `page-781.txt`; visual check of PDF 612, 613, 619 | Chapters 15–18 and appendices A–G completed (`CH15.md`–`CH18.md`, `APPENDICES.md`); book reading completed; PDF 759/760 swapped, book pp. 558, 752, 770 missing from scan; index starts at PDF 782 |
| 2026-11-17 | Task C | `.venv/Scripts/python -m model.zero_taps --model s --images 1000` and `--model xs` (test `tests/test_zero_taps.py`) | [SIM] operand sets with zero activation: s 35.9% of 277,504 ideal cycles (matches `arch_s.json`), xs 25.4% of 83,456 |
| 2026-11-17 | Task C | `docs/research/PARHI_DEVELOPMENT_LIST.md`; `docs/DECISIONS.md` | items D1–D11; ADR-028 through ADR-031 in Proposed status |
| 2026-11-17 | ADR-030 | `python tools/run.py synth-official --lane-impl dsp_min --tag dspmin` (user approved) | 5,550/14,600 LUTs, 5,307 FFs, 2,011 slices, 14 BRAM tiles, 14 DSPs, WNS +0.395 ns, WHS +0.049 ns [VIVADO-STA], `results/vivado/official_dspmin/` |
| 2026-11-17 | end of follow-up session | `python tools/run.py test` | 243 passed in 281.33s, exit 0 (`build/test_session2_end.log`) |
| 2026-11-18 | ADR-030 | `python tools/run.py synth-official --lane-impl dsp_min --turbo-mhz 250 --tag dsp250` | lane +0.233 ns at 250 MHz (265.5 MHz), clk_safe +0.262 ns, 5,542 LUTs, 5,494 FFs, 14 DSPs [VIVADO-STA]; answer to judges evaluated weak for speed claim, implementation (d) held |
| 2026-11-18 | ADR-029 | `fpga/run_matrix.py --k 8 --impl 0 --c3 1 --parts xc7s25csga225-1 --t-safe 7.0 --t-fast 6.4 --nonmac-factor 0.7 --tag pre029` | 5,710 LUTs, 5,076 FFs, Fmax clk_safe 141.7 MHz, clk_fast 155.4 MHz [VIVADO-STA] |
| 2026-11-18 | ADR-029 | `python tools/run.py sim wc_gen_k8_c0` (old wc_gen) | PASS 23821/23821 |
| 2026-11-18 | script | `.venv/Scripts/python -m pytest -q tests/test_fpga_scripts.py` | 23 passed (tagged OOC CSV merged, turbo sentence correct) |
| 2026-11-18 | ADR-029 | `python tools/run.py sim wc_gen_k8_c1`, `wc_gen_k16_c0`, `wc_gen_k16_c1` (old wc_gen) | PASS 23821/23821, 21978/21978, 21978/21978 |
| 2026-11-18 | ADR-029 | same benches on new `rtl/wc_gen.v`, plus `wc_gen_k8_c1_1m` | PASS 23821/23821 (K=8, C3 0 and 1), 21978/21978 (K=16, C3 0 and 1), 1003821/1003821; lint 25 targets clean |
| 2026-11-18 | ADR-029 | `fpga/run_matrix.py ... --tag post029` (same settings as pre029) | 5,668 LUTs, 5,118 FFs, Fmax clk_safe 144.34 MHz, clk_fast 156.27 MHz [VIVADO-STA]; clk_safe worst path at `u_post` |
| 2026-11-18 | ADR-029 | `python tools/run.py synth-official` | 6,824 LUTs, 6,191 FFs, 3 DSPs, 14 BRAMs, clk_safe 133.7 MHz (WNS +0.518 ns), lane 141.9 MHz [VIVADO-STA] |
| 2026-11-18 | ADR-030 | `python tools/run.py synth-official --variant dsp` | 5,468 LUTs, 5,451 FFs, 14 DSPs, 14 BRAMs, lane 262.0 MHz analyzed at 250 MHz (WNS +0.183 ns), clk_safe 126.7 MHz (WNS +0.109 ns) [VIVADO-STA] |
| 2026-11-18 | ADR-030 | `python tools/run.py sim engine_s_k8_c1_dsp` (old wc_gen, before ADR-029) | PASS 1/1 and `engine_s_k8_c1_dsp_n200` PASS 200/200 [SIM] |
| 2026-11-18 | end of session | `python tools/run.py test` | 257 passed in 205.30s (`build/test_session3.log`) |
| 2026-11-18 | slow regression | `python tools/sim.py --record results/sim/rtl_regression.jsonl --jobs 2 engine_s_k8_c1_n200 engine_s_k8_c1_dsp_n200 system_s_k8_c1 wc_gen_k8_c1_1m` | PASS: wc_gen_k8_c1_1m 1003821/1003821, engine_s_k8_c1_n200 200/200, engine_s_k8_c1_dsp_n200 200/200, system_s_k8_c1 10/10, system_s_k8_c1_dsp 10/10 [SIM] |
| 2026-11-18 | reset fan-out | `python tools/run.py synth-official` after `max_fanout = 64` on `rst_safe_r` | 6,832 LUTs, 6,209 FFs, clk_safe 136.6 MHz (WNS +0.678 ns), lane 140.8 MHz [VIVADO-STA] |
| 2026-11-18 | reset fan-out | `python tools/run.py synth-official --variant dsp` | 5,472 LUTs, 5,429 FFs, 14 DSPs, clk_safe 132.4 MHz (WNS +0.445 ns), lane 256.5 MHz at 250 MHz analysis (WNS +0.102 ns) [VIVADO-STA] |
| 2026-11-18 | reset fan-out | `python tools/run.py test` | 257 passed in 215.99s (`build/test_session3b.log`) |
| 2026-11-25 | orientation | `python tools/run.py check`; `python tools/run.py test` | check ok (Python 3.13.1, Icarus 12, Verilator 5.053, Vivado 2025.2); 257 passed in 288.53s (`build/test_tahap3.log`) |
| 2026-11-25 | 3.3 | `python tools/run.py sim spi_loopback` | PASS 619/619 frames=42 [SIM]; lint `spi_loopback` clean |
| 2026-11-25 | 3.4 | `python tools/run.py bringup blink --accept-inferred-io` | 8 LUT, 33 FF, WNS +45.476 ns at 50 ns, WHS +0.260 ns, DRC 0 checks, 0.058 W [VIVADO-STA], `results/vivado/bringup/blink/` |
| 2026-11-25 | 3.4 | `python tools/run.py bringup io_test --accept-inferred-io` | 52 LUT, 76 FF, WNS +42.493 ns, WHS +0.122 ns, DRC 0 checks, 0.062 W [VIVADO-STA], `results/vivado/bringup/io_test/` |
| 2026-11-25 | 3.4 | `python tools/run.py bringup spi_loopback --accept-inferred-io` | 14 LUT, 29 FF, WNS +44.709 ns, WHS +0.131 ns, DRC 0 checks, 0.062 W [VIVADO-STA], `results/vivado/bringup/spi_loopback/` |
| 2026-11-25 | end of stage 3 | `python tools/run.py test` | 264 passed in 208.84s (`build/test_tahap3_end.log`); new: lgpio factory, pi_check lgpio, spi_loopback bench/lint, bring-up report publishing |
| 2026-11-25 | ADR-037 | `python tools/run.py train --model s4`, `python tools/run.py export --model s4` | four official classes (cat, dog, deer, horse; CIFAR-10 subset `cifar10_4`), 18,000 train / 2,000 val / 4,000 test images: float 83.8 %, INT8 83.5 % (drop 0.30 points) [SIM], `results/model/s4/` |
| 2026-11-25 | ADR-037 | `python tools/sim.py engine_s4_k8_c1_n200` (xsim) | PASS 200/200, cycles_mean 277,377, ideal 276,992 [SIM]; recorded in `results/sim/rtl_regression.jsonl` |
| 2026-11-26 | ADR-028 | `python tools/sim.py engine_s_k8_c1_zs_n200` with the first zero-skip RTL (no spacing guard) | hung: shards for images 101–133 and 167–199 ran 4 h 43 min; the 7200 s runner timeout killed only `xsim.bat`, leaving `xsim.exe`/`xsimk.exe` running (stopped by hand, PIDs 27636, 5064) |
| 2026-11-26 | ADR-028 | same bench, rerun with the watchdog, per-image progress and the lane-array overrun check | images 0–100 and 134–166 PASS (134 images); `FAIL lane_array: result serializer overrun` on image 118 (1 word left) and image 198 (3 words left), then wrong logits and a timeout [SIM]; logs `results/sim/zero_skip/unguarded/` |
| 2026-11-26 | ADR-028 | `python tools/sim.py engine_s_k8_c1_sparse engine_s_k8_c1_zs_sparse` (pre-fix RTL) | both PASS 4/4 (black, sparse, half-black, real image), no overrun [SIM]. Likely reason [INFERENCE]: scanning R = 2 taps per cycle already spaces fully zero first-layer units 14 cycles apart; the trigger needs partly zero units queued behind a FIFO backlog, as in images 118 and 198 |
| 2026-11-26 | runner | `pytest tests/test_sim_runner.py` | 4 passed: whole process tree killed on timeout, log readable while running, exact bench name selects one bench |
| 2026-11-26 | ADR-028 | `pytest tests/test_tools.py -k serializer` | shortest unit t = 27 (conv1, C_in = 3) in micro, s, s4, xs; serializer needs 10/11/18/19 cycles (K = 8/16, C3 = 0/1): no layer is too short without zero-skip |
| 2026-11-26 | ADR-028 | `python tools/sim.py engine_s_k8_c1_zs_overrun engine_s_k8_c1_zs2_overrun` (inside `run.py test`) | both guards on images 118 and 198: PASS 2/2, no overrun line; 186,909 and 192,020 cycles with either guard [SIM] |
| 2026-11-26 | ADR-028 | `python tools/sim.py engine_s_k8_c1_zs engine_s_k8_c1_zs2` (Icarus) | PASS 1/1 each, 195,134 cycles (image 0, same as before the guard) [SIM] |
| 2026-11-26 | ADR-028 | `python tools/sim.py engine_s_k8_c1_zs_n200 engine_s_k8_c1_zs2_n200 --record ...` (xsim) | both PASS 200/200, cycles_mean of the first shard 191,090; all images: mean 189,797.6, 31.70 % below 277,895; guard cost against the unguarded run 5 cycles (mode 1) and 0 (mode 2) over 182 images [SIM]; `python tools/zs_compare.py` → `results/sim/zero_skip/compare.json`, logs `results/sim/zero_skip/zs1/`, `zs2/` |
| 2026-11-26 | ADR-028 | `python tools/run.py synth-official --zero-skip 1 --tag zs1`, then `--zero-skip 2 --tag zs2` | mode 1: clk_safe WNS 0.587 ns, clk_fast 0.637 ns, 7,912 LUT, 6,229 FF; mode 2: 0.471 ns, 0.292 ns, 7,878 LUT, 6,213 FF; official baseline 0.678 / 0.898 ns, 7,741 LUT [VIVADO-STA]; `results/vivado/official_zs1/`, `official_zs2/` |
| 2026-11-26 | ADR-028 | `python tools/run.py synth-official --tag base26` (ZERO_SKIP = 0, today's RTL) | first run: 7,859 LUT, clk_safe WNS 0.811 ns, not the official netlist (ungated slot-shift mux; numbers from the session diff, reports overwritten by the rerun); after gating `shift1` and `fifo_wr` by the parameter: identical to `results/vivado/official/` (0.678 / 0.898 ns, 7,741 LUT, 6,209 FF) [VIVADO-STA] |
| 2026-11-26 | ADR-028 | `python tools/run.py test` (after the gate) | 286 passed in 793 s (`build/test_zs_fix2.log`; run beside Vivado); before the gate also 286 passed in 442 s |
| 2026-11-26 | review | `git diff` of CLAUDE.md, AGENTS.md, README.md, STATUS.md; script check of the translated docs | translations keep every number, label, URL and code span (same line counts); CLAUDE.md §7 (Pi 5, four classes, hardware hold), §8 ("board siap"/"board ready"), §10 naming, AGENTS.md priority rule fixed; `docs/official/superseded/GUIDE_LSI_2027.pdf` restored (still listed in `docs/official/README.md`); commits 8827907, f303886, fd3733f; `.agents/` and `graphify-out/` left untracked |
| 2026-11-26 | ADR-037 | `python tools/sim.py system_s4_k8_c1` (xsim) | PASS 10/10 reconfigs=0: official system scenarios (C3 in use, injections, recompute) with model s4 [SIM]; `config/hw_zero7.yaml` MODEL s4; manifest `classes`; validation labels in model order |
| 2026-11-26 | ADR-028 | `python tools/sim.py engine_s_k8_c1_dsp_zs engine_s_k8_c1_dsp_zs_n200` | PASS 1/1 (195,128 cycles) and PASS 200/200, mean 189,791.7 against 277,891 for the DSP baseline [SIM]; logs `results/sim/zero_skip/dsp_zs1/` |
| 2026-11-26 | ADR-028 | `python tools/run.py synth-official --variant dsp --zero-skip 1 --tag zs1` | clk_safe WNS 0.694 ns, lanes at 250 MHz WNS 0.207 ns, 6,254 LUT, 5,435 FF; official DSP 0.445 / 0.102 ns, 6,096 LUT [VIVADO-STA]; `results/vivado/official_dsp_zs1/` |
| 2026-11-26 | ADR-028 | `python tools/sim.py system_s4_dsp_speed_r2_zs0 ..._r2_zs1 ..._r1_zs0 ..._r1_zs1` | all PASS 10/10; clk_safe cycles per image, lanes at 2 × clk_safe: 162,397.0 → 162,394.1 (−0.002 %); lanes at clk_safe: 277,369.0 → 185,918.7 (−32.97 %) [SIM]; zero-skip gives nothing at the operand supply limit, so it is not used in the DSP demo build |
| 2026-11-26 | end of session | `python tools/run.py test` | 291 passed in 996 s (`build/test_s4_dsp.log`); afterwards five comparison-only benches (mode 2, baseline sparse, DSP zero-skip one image) moved to the slow set: 286 tests in the default run |
| 2026-11-26 | ADR-032 study | `python tools/run.py synth-official --variant dsp --safe-div 7 --tag sd7` | timing met at clk_safe 142.857 MHz: WNS +0.098 ns, lanes at 250 MHz +0.173 ns (261.3 MHz), WHS +0.014 ns, 6,099 LUT, 5,467 FF [VIVADO-STA]; worst clk_safe path post-processing `cfg_n_reg` → `u_post/shifted_reg` (16 levels); adoption is a user decision; `results/vivado/official_dsp_sd7/` |
| 2026-11-26 | ADR-031 | `python tools/run.py synth-official --tag d5` (D5 only: `dont_touch` per-lane activation register) | clk_fast WNS 0.898 → 0.835 ns, clk_safe 0.678 → 0.148 ns (reset-net routing), 7,741 LUT, 6,281 FF [VIVADO-STA]: worse alone; the lane worst path moved inside one lane (C3 checksum lane, 10 levels); `results/vivado/official_d5/` |
| 2026-11-26 | ADR-031 | `pytest tests/test_rtl.py` (fast set) and `python tools/sim.py engine_s4_k8_c1_n200 system_s4_k8_c1` with the split LUT multiplier + D5 | 71 passed; PASS 200/200 (cycles_mean 277,381, +4 from the extra lane stage) and PASS 10/10 with injections [SIM]; split-multiplier identity checked for all 65,536 pairs at W_W = 8 and 40,084 pairs at 11/14/16 bits |
| 2026-11-26 | ADR-031 | `python tools/run.py synth-official --tag adr031`, then `python tools/run.py synth-official` | clk_fast WNS 0.898 → 1.180 ns (140.8 → 146.6 MHz at 8 ns), clk_safe 0.678 → 0.694 ns, 7,645 LUT (−96), 6,604 FF (+395), WHS 0.036 ns [VIVADO-STA]; worst clk_fast path now the fast reset fan-out, no longer a lane multiplier; official report regenerated, identical to the side run |
| 2026-11-26 | ADR-031 | `python fpga/run_matrix.py --k 8 --impl 0 --c3 1 --parts xc7s25csga225-1 --t-safe 7.0 --t-fast 6.4 --nonmac-factor 0.7 --tag pre031` (HEAD lane) and `--tag adr031` | MAC slack 0.001 → 0.671 ns, non-MAC 0.185 → 0.121 ns at 0.7 of the period, fast Fmax 156.3 → 159.3 MHz, clk_safe 144.3 → 144.6 MHz, LUT 5,668 → 5,641, FF 5,118 → 5,513 [VIVADO-STA]; first adr031 run misclassified the new p_lo/p_hi registers as non-MAC (patterns fixed, test added, row replaced by the rerun) |
| 2026-11-26 | ADR-032 | `python tools/sim.py system_s4_dsp_speed_r1785_zs0 system_s4_k8_c1_dsp` | both PASS 10/10; 175,745.7 clk_safe cycles per image at ratio 255/142.857 = 1.785 → 1.230 ms at 142.857 MHz, against 162,397.0 cycles at ratio 2 → 1.299 ms at 125 MHz (−5.3 %) [SIM]; `results/sim/clock_dsp142/` |
| 2026-11-26 | ADR-032 | `python tools/run.py synth-official --variant dsp` (divider 7 and lanes at 255 MHz from `config/hw_zero7.yaml`) | clk_safe WNS +0.198 ns at 7.000 ns (147.0 MHz), lanes +0.173 ns at 3.922 ns (266.7 MHz), WHS +0.049 ns, 6,099 LUT, 5,566 FF, no unrouted nets [VIVADO-STA]; `results/vivado/official_dsp/` regenerated; LUT summary text rebuilt (`--summary-only`) |
