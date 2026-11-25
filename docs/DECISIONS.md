# Architecture Decision Records

Decision format: context, decision, consequences, status. New decisions are added below with the subsequent number. Prior decisions are not deleted; mark "Superseded by ADR-xxx".

ADR-001 through ADR-007 are initial proposals from the starter kit (2026-11-09). Revisions permitted via new ADR, with written justification.

---

## ADR-001 — Dataflow output-stationary, lane per output channel
- **Context:** checksum identity Σ_k W_k ∗ X = (Σ_k W_k) ∗ X holds if all lanes use the same input X.
- **Decision:** K lanes process K different output channels for the same output position. Activations are broadcast to all lanes.
- **Consequences:** checksum directly applies to accumulators. No reuse buffer needed. Memory bandwidth K+1 bytes per operand set.
- **Status:** Accepted (initial proposal).

## ADR-002 — Checksum weights computed on-the-fly in safe domain
- **Context:** storing wc1/wc2 in BRAM adds ~50% memory for K = 8, whereas small Spartan-7 BRAM is very constrained.
- **Decision:** wc1, wc2, and wc3 are computed from the K weights being fetched, in the safe domain, before entering operand FIFO.
- **Consequences:** no extra BRAM. Errors in data lane weights after leaving safe domain are still detected. Cost is small adder trees with R copies.
- **Status:** Accepted (initial proposal).

## ADR-003 — Recompute unit = pool window × group, deferred to layer end
- **Context:** switching clock per tile is complex. On-the-fly pooling requires 4 correct positions.
- **Decision:** failed units logged. After layer finishes, clock is switched to safe and logged units recalculated, including pooling.
- **Consequences:** clock only switches at layer boundaries. Requires log with capacity N_LOG; if full, entire layer repeated.
- **Status:** Accepted (initial proposal).

## ADR-004 — Operand supply R per clk_safe cycle
- **Context:** if memory in safe domain only provides 1 operand set per clk_safe cycle, overclocking lanes does not increase throughput.
- **Decision:** safe domain produces R operand sets per cycle (default R = 2), subject to R · f_safe ≥ f_turbo_max.
- **Consequences:** BRAM read width increases. STARVE counter measures lane starvation.
- **Status:** Accepted (initial proposal).

## ADR-005 — Conservative policy for errors in checksum lanes
- **Context:** without C3, patterns d1 ≠ 0 and d2 = 0 can originate from lane C1 errors or mutually cancelling multi-lane errors.
- **Decision:** default `TRUST_CSUM_LANE = 0`, so ambiguous cases are recalculated.
- **Consequences:** slightly more recomputations, but no corrupted data escapes from this case. Re-evaluate after M3.
- **Status:** Accepted (initial proposal).

## ADR-006 — Requant with per-layer M (uint16) and shift n
- **Context:** shift-only requantization is cheaper, but risks degrading accuracy.
- **Decision:** begin with per-layer (per-tensor) M and n. Per-channel only if accuracy drops > 2 points.
- **Consequences:** one 32×16 multiplier in safe domain. Cost is small due to low output rate.
- **Status:** Accepted (initial proposal).

## ADR-007 — Simulators and cross-platform flow
- **Context:** user uses Vivado 2025.2. Operating system can be Windows or Linux. Verilator is difficult to install on Windows.
- **Decision:** Icarus Verilog as primary simulator, xsim as reference (XPM, unisim), Verilator for lint if available. All commands via `tools/run.py`.
- **Consequences:** RTL constrained to portable Verilog-2005 subset. Xilinx primitives wrapped with simulation models.
- **Status:** Accepted (initial proposal).

## ADR-008 — Comparator arithmetic width and serialization order
- **Context:** SPEC §6.2 pseudo-code uses unbounded integers, but SPEC §1 states d1/d2/d3 are `ACC_CS_W` bits wide. Errors in checksum lane upper bits could cause j·d1 to exceed 48 bits, causing RTL and model divergence. SPEC §6.4 overflow check also only applies to valid corrections; miscorrections from multi-lane errors could exceed `ACC_W`. In addition, computing Σk·Y_k and Σk²·Y_k with multipliers adds cost in safe domain.
- **Decision:** d1, d2, d3, as well as comparisons d2 = j·d1 and d3 = j²·d1 are computed modulo 2^`ACC_CS_W` (two's complement), both in `model/checker.py` and RTL. Correction results truncated to `ACC_W` bits with two's complement. Serializer outputs sequentially S1, S2, (S3), Y_K, …, Y_1, so checker sums using three chained accumulators A += Y, B += A, C += B; after K words, A = ΣY, B = Σk·Y, and Σk²·Y = 2C − B.
- **Consequences:** no multipliers in checker and RTL remains bit-exact with model, including for extreme errors. For values within §3.6 bounds results are identical to pseudo-code. Overflow assert §6.4 not implemented in hardware because miscorrections can indeed occur; that case counted as "miscorrected" in campaign.
- **Status:** Accepted.

## ADR-009 — Comparator module named `lane_checker`
- **Context:** SPEC §17 and STATUS mention `rtl/checker.v`, but `checker` is a SystemVerilog keyword rejected by `iverilog -g2012` and Verilator.
- **Decision:** module and file named `lane_checker` (`rtl/lane_checker.v`). Python model remains `model/checker.py`.
- **Consequences:** naming only; behavior unchanged.
- **Status:** Accepted.

## ADR-010 — MMCM2 reconfiguration and Spartan-7 limits
- **Context:** SPEC §7.6 calls for selecting between Clocking Wizard via AXI4-Lite (PG065), direct DRP (XAPP888), or plan B with multiple fixed CLKOUTs plus mux. Vivado 2025.2 on this machine lacks Spartan-7 device support (`get_parts xc7s*` empty), F_IN not yet known, and PG065/DS189 not yet available in repo.
- **Decision:** architecture uses `clk_gen` with interface `reconfig_start`/`reconfig_level`/`reconfig_busy`/`turbo_locked`. Primary choice for board phase: Clocking Wizard via AXI4-Lite (PG065), per SPEC. Direct DRP and plan B remain fallbacks if Wizard IP cannot be used. Simulation model and §7.7 sequence verified now via `rtl/clk_seq.v` and `tb/tb_system.v`; implementation of PG065 registers in `rtl/platform/xilinx/clk_gen_xilinx.v` deferred due to needing device support, F_IN, and PG065.
- **Consequences:** frequency table (`tools/gen_mmcm_table.py`) available with `verified: false` limits in `config/mmcm_limits.yaml`; these limits must be checked against DS189 with page numbers before board phase.
- **Status:** Temporarily accepted, reviewed during board phase.

## ADR-011 — Recommendation for third checksum lane (C3)
- **Context:** M3 campaign [SIM] (`results/sim/campaign_s.json`, script `model/campaign.py`) on real model `s` accumulators: 10,000 two-lane errors without C3 yielded 597 miscorrections (K=8) and 630 (K=16), whereas with C3 there were zero miscorrections (all went to RECOMPUTE). Single-lane errors 100% corrected in all configurations. Injections are XOR masks, not measured timing errors; real multi-lane error rate only measurable on board (E1).
- **Decision:** C3 remains synthesis parameter `C3_EN`. Repo default remains 0 until M11 resource data and E1 board data exist. Recommendation: enable `C3_EN=1` if part resources permit, as miscorrections without C3 constitute silent data corruption undetected by CORRECTED counter.
- **Consequences:** C3 cost is one additional checksum lane (DSP or LUT) and one word per unit in result FIFO. Net benefit comparison conducted in E8 after M11.
- **Status:** Temporarily accepted, final decision after M11 and E1.

## ADR-012 — Additional pipeline and interpretation of SPEC §7.4 margin
- **Context:** first OOC run (xc7s25csga225-1, K=8) showed critical path of fast domain is not MAC: XPM FIFO read pointer (fanout 205) and capture signal to holding registers. Safe domain constrained by activation address computation (10 logic levels). SPEC §7.4 specifies non-MAC slack "at least 30% greater", without numerical definition when MAC slack is small or negative.
- **Decision:** operand FIFO split into multiple parallel FIFOs (maximum width ~50 bits per slice) written and read together; holding register capture uses each lane's own done pulse; slot control in `fast_path` becomes register permitted to replicate; operand generator address adds one register stage. Margin §7.4 calculated as (non-MAC slack − MAC slack) divided by MAC delay (period − MAC slack), target ≥ 30%, by `fpga/parse_reports.py`.
- **Consequences:** cycle-level behavior of generator adds one latency stage but functionality intact; all benches rerun. Sliced FIFO outputs identical to single FIFO.
- **Status:** Accepted.

## ADR-013 — Target locked to XC7S25CSGA225-1, speed grade −1

- **Context:** since 10 Nov 2026 organizers require synthesis report for AMD Spartan-7 XC7S25CSGA225-1 for all classes, and Class 2 may only use ZERO7 carrying that chip [OFFICIAL, `docs/official/README.md`]. Part resources per Vivado database and official guide screenshot: 14,600 LUTs, 29,200 flip-flops, 45 block RAMs, 80 DSPs, 3 MMCMs [VIVADO; OFFICIAL IN-24]. M11 results for `engine` module on this part [VIVADO-STA]: model `s`, K = 8, lane `lut`, C3 = 0 uses 4,774 LUTs (32.7%), 4,364 FFs (14.9%), 14 block RAMs (31.1%), 3 DSPs; with C3 = 1 becomes 5,717 LUTs (39.2%); K = 16 uses 7,080 LUTs (48.5%) and 22 block RAMs (48.9%).
- **Alternatives:** (a) keep supporting multiple parts; (b) official part with K = 8 without C3; (c) official part with K = 8 and C3; (d) official part with K = 16.
- **Decision:** single target, `xc7s25csga225-1`. Official variant for synthesis report and for board: model `s`, K = 8, R = 2, `LANE_IMPL = lut`, `C3_EN = 1`, `INJ_EN = 1`, recorded in `config/hw_zero7.yaml`. C3 enabled because miscorrection without C3 is undetected corrupted data (ADR-011) and costs ~943 LUTs on a part only one-third full. K = 16 not chosen: `clk_safe` Fmax drops from 147.8 to 118.8 MHz [VIVADO-STA], lowering operand supply limit R·f_safe, and cycle overhead is 9.9% [SIM]. General defaults in SPEC §1 unchanged.
- **Impact:** SPEC §2 and §14 updated. `fpga/run_matrix.py` remains for exploration; other part and speed grade −2 results become comparison data. Resource budget citing DS180 page and MMCM limits citing DS189 page cannot yet be written as neither datasheet is in repo; until then, resource numbers labeled [VIVADO].
- **Status:** Accepted.

## ADR-014 — Official synthesis report as primary deliverable

- **Context:** XC7S25CSGA225-1 synthesis report mandatory, but format not yet explained by organizers. Until now only `engine` module ever synthesized (M11, out-of-context); `top_core` and `top_board` with MMCM and SPI have never passed through Vivado.
- **Alternatives:** (a) submit out-of-context `engine` report; (b) implement complete `top_board` design with board XDC and save post-synthesis and post-implementation reports; (c) GUI project like guide example.
- **Decision:** (b). `fpga/synth_official.tcl` runs in batch mode in Vivado 2025.2 with top `top_board`, part `xc7s25csga225-1`, and `board/zero7.xdc`. Output in `results/vivado/official/`: utilization (post-synthesis and post-implementation, including hierarchy), timing summary, clock networks, power (vectorless estimation), DRC, and methodology, plus `summary.json` labeled [VIVADO-STA]. Bitstream not generated while I/O standards uncertain. Command is `python tools/run.py synth-official`. This flow executed now as risk mitigation and rerun whenever RTL changes.
- **Impact:** new milestone M15. `clk_gen_xilinx` must be sufficiently complete to implement with 20 MHz clock (ADR-015). Results in `results/vivado/` committed.
- **Status:** Accepted.

## ADR-015 — 20 MHz board clock as MMCM input

- **Context:** board clock is net CLK20M on pin B13, 20 MHz [OFFICIAL, IN-31 and TK-1]; B13 is clock-capable pin [VIVADO]. Prior MMCM table used 100 MHz placeholder. MMCM limits in `config/mmcm_limits.yaml` not yet verified against DS189.
- **Alternatives:** f_safe 100 MHz or 125 MHz; turbo level spacing 5, 10, or 12.5 MHz with 16 levels (`LEVEL` field width 4 bits).
- **Decision:** `CLKIN1_PERIOD` = 50.0 ns for both MMCMs. MMCM1 uses VCO 1,000 MHz (M = 50, D = 1), middle of unverified 600–1,200 MHz range. f_safe = 125 MHz (divider 8) if official implementation passes timing; otherwise, 100 MHz (divider 10). This choice determined by STA results and recorded in `results/vivado/official/`. Turbo table: 16 levels starting from f_safe with 10 MHz spacing, all precisely achievable with 20 MHz input (`tools/gen_mmcm_table.py`). E1 sweep with 5 MHz steps requires host-writable table; decided together with DRP sequencer (ADR-010).
- **Impact:** `tools/gen_mmcm_table.py` uses 20 MHz default and no longer flags F_IN as placeholder; its tests updated. SPEC §7.6 updated. MMCM settings checked with Vivado DRC as provisional surrogate for DS189.
- **Status:** Accepted. Result 2026-11-16: f_safe = 125 MHz. After ADR-021, official implementation passes timing at 125 MHz [VIVADO-STA, `results/vivado/official/summary.md`]; 100 MHz fallback not used.

## ADR-016 — ZERO7 I/O map

- **Context:** official connection table provides SPI0 pins, LEDs, buttons, and WS2812B. Three colored LEDs and three buttons share traces with Raspberry Pi GPIO; button polarity not yet known. `top_board` currently has four ordinary LED outputs.
- **Alternatives:** (a) FPGA drives all LEDs and reads all buttons; (b) FPGA uses only its own dedicated traces, shared traces handled by Raspberry Pi software.
- **Decision:** (b).
  - SPI0 with CE0: SCLK A8, MOSI A6, MISO A7, CS D9. CE1 (C10) unused.
  - Done signal `irq_done` on RP_GPIO25 (C9), active high while `STATUS.DONE` = 1, so Pi can wait for signal edge and measure latency without polling.
  - Dedicated FPGA LEDs: D5 (R3) = busy, D6 (R2) = FATAL. Other status displayed via WS2812B (ADR-017).
  - START, STOP, RUN buttons and D3, D8, D9 LEDs read or driven by Pi software. This prevents bus contention, and button polarity is easily configured in software.
  - Board constraints located in `board/zero7.xdc`. Old template removed and `board/build_bitstream.py` uses that file; script still rejects while mandatory fields remain UNKNOWN.
- **Impact:** `top_board` ports change; XDC and board package tests follow. SPEC §12.1 updated.
- **Status:** Accepted.

## ADR-017 — WS2812B indicator driven by FPGA

- **Context:** WS2812B LED1 on pin N1 (net S7_LED0) driven by FPGA [OFFICIAL, TK-5]. Judges evaluate ideas and presentation; visually apparent error map directly on board strengthens demo. Number of LEDs per chain and color ordering not yet known.
- **Alternatives:** (a) standard LEDs only; (b) WS2812B driver in FPGA; (c) LED driven by Pi.
- **Decision:** (b). `rtl/ws2812_tx.v` module in `clk_safe` domain with parameter for LED count (default 1) and bit timing parameters derived from clock frequency. Status encoder maps state to color: idle, running on safe clock, running on turbo (color shifts per level), corrected error, recompute, FATAL. Testbench checks pulse width of every bit. Bit timing values must be checked against WS2812B datasheet before using on board.
- **Impact:** new milestone M17; `ws2812_dout` port on `top_board`; optional brightness register.
- **Status:** Accepted; implementation after M15.

## ADR-018 — Chip temperature from XADC

- **Context:** XC7S25 has XADC; Hardware Manager in official guide displays it [OFFICIAL, IN-48]. `TEMP` register already provided in register map. E6 requires temperature.
- **Alternatives:** (a) no temperature; (b) external sensor via PMOD or I2C; (c) internal XADC temperature sensor.
- **Decision:** (c). Wrapper `xadc_temp` in `rtl/platform/xilinx/` with simulation model in `rtl/platform/sim/`, reading 12-bit temperature code and placing in `TEMP`. Temperature recorded only; governor policy (SPEC §10) unchanged. Conversion formula to °C taken from UG480 during implementation, with page numbers cited.
- **Impact:** new milestone M18; official utilization report rerun afterwards.
- **Status:** Accepted; implementation after M15.

## ADR-019 — Boot from QSPI flash deferred

- **Context:** board has QSPI flash (IC2) and SW7 mode DIP switch [OFFICIAL]. Flash model and SW7 positions not yet known; official guide only explains programming via JTAG.
- **Alternatives:** (a) prepare flash configuration files now by guessing flash model; (b) defer until user manual or board arrives.
- **Decision:** (b). Supported path is JTAG. Flash boot becomes demo target to avoid reliance on JTAG cable, implemented after flash model is known from documentation or board.
- **Impact:** new `[B]` item in STATUS.
- **Status:** Deferred.

## ADR-020 — Category and claim boundaries following organizer updates

- **Context:** tasks divided into two classes (2 Nov 2026). Class 2 limited to ZERO7 with free task and Level 3 only; all classes must submit XC7S25CSGA225-1 synthesis report [OFFICIAL]. 16 Nov 2026 research found ABFT, dual checksums, checksum-based correction, and CNN accelerator overclocking already exist, and closest work (Marty et al.) appears to have considered then rejected checksum-based correction (`docs/research/RISET_WEB_2026-11.md`).
- **Alternatives:** move to Class 1 Level 3, or remain in Class 2 Level 3.
- **Decision:** target remains Class 2 Level 3 as proposal awaiting organizer confirmation. Image classification, validation data mode, and real-time camera mode maintained so Class 1 Level 3 requirements are also fulfilled. Highlighted contributions are our own design features: (1) single-lane error correction without recalculation compared directly against detect-then-recalculate on same bitstream and board, (2) timing error atlas of real CNN on small FPGA, (3) per-layer clock selection by in-FPGA governor, and (4) per-lane error map visible directly on board. Claim phrasing uses "to the best of our knowledge as of November 2026"; words "first" and "novel" not used before full texts of Marty et al. and Li et al. are read.
- **Impact:** `docs/PRIOR_ART.md` updated; report must include section answering Marty et al.'s rationale.
- **Status:** Accepted.

## ADR-021 — Resets, synchronizers, and clock domain crossing rules

- **Context:** first complete implementation of `top_board` on xc7s25csga225-1 at 125 MHz [VIVADO-STA, `results/vivado/official_preadr021/`]: intra-clock paths pass (WNS +0.286 ns on `clk_safe_raw` for 11,249 endpoints, +0.204 ns on `clk_fast_safe` for 5,597 endpoints). One inter-clock path failed with slack −0.499 ns: power-on reset in `top_board` (domain `clk_in`, 20 MHz) to first stage of reset shift register in `top_core` (domain `clk_safe`), with 2.000 ns requirement. That path is input to a synchronizer, but not yet declared so to Vivado, and Vivado packed reset shift register into an SRL. `report_methodology` gave TIMING-9 (crossing without recognized synchronizer) and TIMING-10 (synchronizer without `ASYNC_REG`). SPEC §7.8 had not yet governed reset from board clock (top-level board only existed since ADR-016) and had not listed signals crossing without synchronizers.
- **Alternatives:** (a) lower f_safe to 100 MHz using ADR-015 fallback: symptoms vanish, root cause remains; (b) asynchronous clock group between `clk_in` and `clk_safe`: overly broad, future crossings obscured; (c) mark synchronizers and exclude only reset synchronizer input path.
- **Decision:** (c), with five rules:
  1. Every synchronizer given `ASYNC_REG` attribute in RTL: `clk_safe` reset (`por_meta` and `lock_meta` in `top_core`), `clk_fast` reset (`rst_fast_meta` in `engine`), `pass_active` (`fast_path`), three SPI pins (`spi_slave`), and LOCKED MMCM2 (`clk_gen_xilinx`, new synchronizer). No logic in front of synchronizers: power-on reset and LOCKED MMCM1 each have two-flop synchronizers, then merged with soft reset in `clk_safe` domain. Intermediate run OR-ing three sources before single synchronizer flagged CDC-10 by `report_cdc` [VIVADO-STA, `results/vivado/official_adr021a/`]. Flops driving reset net separated from synchronizers so replication remains permitted. Each source reaches reset after four flops, so cycle-level behavior unchanged. Attributes are not primitives: simulators ignore them, and Xilinx primitives remain strictly in `rtl/platform/xilinx/`.
  2. Path from `clk_in` to first stage of `por_meta` is false path (`fpga/constraints/top_board_timing.tcl`). No other timing exceptions added.
  3. Signals crossing from `clk_safe` to `clk_fast` without synchronizer may only be quasi-static signals, i.e. signals changing only when fast domain is idle: injection configuration (`INJ*` registers) and layer index. Layer index guaranteed by engine state sequence (changes after all layer results returned and before next pass begins). `INJ*` registers become host rule: written only when `STATUS.BUSY` = 0. In reverse direction, `STARVE_CYCLES` read only when `STATUS.BUSY` = 0.
  4. Operands and results continue to cross exclusively via XPM asynchronous FIFOs.
  5. Official report flow adds `report_cdc` and `report_bus_skew`, with summaries including crossing counts per class and their architectural meanings.
- **Impact:** SPEC §7.8 expanded. `rtl/top_core.v`, `rtl/engine.v`, `rtl/fast_path.v`, `rtl/spi_slave.v`, `rtl/platform/xilinx/clk_gen_xilinx.v`, constraints, and official flow changed; all regressions rerun. f_safe choice in ADR-015 taken from run after this change. Hardware write-guard for `INJ*` during BUSY implemented in `regfile` (M20).
- **Status:** Accepted. Addition 2026-11-16: `INJ*` write guard during BUSY implemented in `regfile` (M20).

## ADR-022 — Host Raspberry Pi 4 Model B

- **Context:** organizers state loan board can be connected to Raspberry Pi 5 [OFFICIAL, G-6]. Team possesses only Raspberry Pi 4 Model B [USER, 2026-11-16]. ZERO7 is a HAT on 40-pin header and draws power from header [OFFICIAL, IN-41]. All signals used by SENTINEL (SPI0 on GPIO 7–11, done signal on GPIO25) use BCM GPIO numbers.
- **Alternatives:** (a) purchase Pi 5; (b) use Pi 4 and verify compatibility upon board arrival.
- **Decision:** (b). 40-pin header and BCM GPIO numbering on Pi 4 are identical to Pi 5 [INFERENCE], so `board/zero7.xdc` remains unchanged. Software uses only `spidev`, `gpiozero`, and `picamera2`, which run on both models; no Pi 5 specific code. Power supply uses official Pi 4 adapter (5.1 V, 3 A); ZERO7 header current draw [UNKNOWN] and measured in bring-up step 1. Camera uses standard 15-pin ribbon. `board/pi_check.py` checks Pi model, `/dev/spidev0.0`, and Python packages on Pi before step 2.
- **Impact:** `board/BOARD_INFO.md`, `board/BRINGUP.md`, `CLAUDE.md` §7, and study guide mention Pi 4. Recorded risks: official examples tested on Pi 5; mechanical fit and power budget only certain when board is present. If Pi 4 is incompatible, no RTL changes.
- **Status:** Accepted; superseded by ADR-033 (Raspberry Pi 5, 25 Nov 2026).

## ADR-023 — AMD documents: MMCM limits, MMCM2 reconfiguration, and XADC configuration

- **Context:** user authorized download of AMD documents on 2026-11-16. Saved in `docs/vendor/amd/`: DS189 (2024-10-18 edition), DS180 v2.6.1, UG480 v1.11, PG065 (Clocking Wizard v6.0). ADR-010 deferred MMCM2 reconfiguration choice; ADR-018 deferred temperature formula.
- **Decision:**
  1. MMCM limits taken from DS189 Table 37 (PDF p. 40): input 10–800 MHz, PFD 10–450 MHz (−1), VCO 600–1,200 MHz (−1), maximum output 800 MHz, maximum lock time 100 µs, maximum DRP clock 200 MHz. Old −2 value for max input/output (933 MHz) incorrect and replaced by 800 MHz. Part capacity taken from DS180 Table 2 (p. 2). `verified: true` with page numbers.
  2. MMCM2 reconfigured via Clocking Wizard v6.0 with AXI4-Lite interface (PG065, "Dynamic Reconfiguration through AXI4-Lite"), primary choice of SPEC §7.6. IP generated from Tcl in official flow (Vivado 2025.2 probe: 20 MHz input, 125 MHz output yields M = 50, D = 1, O = 8.0). Simple AXI4-Lite master `clkwiz_seq` (portable RTL) writes registers 0x200 (DIVCLK_DIVIDE, CLKFBOUT_MULT, CLKFBOUT_FRAC) and 0x208 (CLKOUT0_DIVIDE and FRAC), waits for SR (0x04) bit 0 = 1, writes 0x25C = 0x3, then waits for SR bit 0 and LOCKED to return to 1. Per-level values taken from `tools/gen_mmcm_table.py` generated to `rtl/gen/mmcm_turbo_table.vh`. Mux switching reported (`is_turbo`) after fixed delay, not immediately following request.
  3. XADC (UG480): continuous sequence mode with calibration and temperature channels (INIT_48 = 0x0101, p. 46), calibration correction active (INIT_41 = 0x20F0, Tables 3-5 and 3-9, pp. 36 and 38), DCLK divider 8 yielding ADCCLK = 125/8 = 15.625 MHz below 26 MHz limit (INIT_42 = 0x0800; DS189 Table 50: DCLK 8–250 MHz, ADCCLK 1–26 MHz). 12-bit temperature code read from DRP address 00h (12 MSBs). Temperature °C = code × 503.975 / 4096 − 273.15 (UG480 Eq. 2-6, p. 24); sensor error ±4 °C over −40 to 100 °C (DS189 Table 50). Conversion to °C performed in software.
  4. Wizard AXI reset derived from LOCKED MMCM1 alone (via synchronizer). MMCM1 held in reset by power-on reset, so its LOCKED is low during that reset. Two other attempts rejected by `report_cdc`: OR of reset and LOCKED before single synchronizer (CDC-10) and second synchronizer for power-on reset (CDC-11, single flop to two synchronizers).
- **Impact:** ADR-010 and ADR-018 resolved. SPEC §7.6 and §12.4 updated. Official flow rerun as MMCM2 is now inside IP. Simulation does not model AMD IP; `clkwiz_seq` tested with behavioral register model following PG065, and actual IP behavior only proven on board.
- **Status:** Accepted.

## ADR-024 — LVCMOS33 I/O standard from official evidence

- **Context:** user asked whether `Zero7.xdc` could be assembled independently from connection table. Pins already taken from that table (ADR-016). Not yet written is VCCO voltage for banks 15 and 34.
- **Evidence:** comment `##Clock (20MHz, 3.3V)` for B13 (bank 15) in official `Zero7.xdc` screenshot [OFFICIAL, IN-31]; all pins used by SENTINEL connect directly to Raspberry Pi GPIO operating at 3.3 V, and connection table shows no level shifters [OFFICIAL, TK-1 and TK-2]; CFGBVS and bank 0 VCCO on VCC3V3 [OFFICIAL]; banks 14, 15, and 34 HR type supporting 1.2–3.3 V (DS180 Table 3).
- **Decision:** LVCMOS33 for all SENTINEL pins in banks 15 and 34 as [INFERENCE] with evidence above. TODO comment in `board/zero7.xdc` remains until VCCO voltage is measured with multimeter on board arrival (bring-up step 1) or user manual published. `board/build_bitstream.py` continues to refuse bitstream generation for board before then. "Dry-run bitstream" check permitted now: `write_bitstream` from official checkpoint to `build/`, solely to prove bitstream DRC passes. File not used on board and not committed.
- **Impact:** board phase cannot start earlier; one risk (bitstream DRC) closed before board arrival.
- **Status:** Accepted.

## ADR-025 — Host via JTAG while Raspberry Pi is unavailable

- **Context:** ZERO7 and JTAG-HS3 available 20 Nov 2026; Raspberry Pi 4 may arrive later and compatibility [UNKNOWN] (team info, 17 Nov 2026). All SENTINEL experiments use host uploading weights, sending images, reading registers. JTAG-HS3 already connected to PC for programming; JTAG pins on bank 0 whose VCCO is VCC3V3 [OFFICIAL, TK].
- **Alternatives:**
  - (a) Host via JTAG: AMD JTAG-to-AXI Master IP in FPGA, AXI4-Lite bridge to SENTINEL host bus, and Vivado Tcl script controlled by Python (`JtagBackend`, identical interface to `HwBackend` and `MockBackend`). VIO also considered, but VIO only suitable for a few control signals; uploading thousands of weight bytes via VIO properties is too slow and complex.
  - (b) Weights and test images stored in BRAM, self-test mode executed by START button; PASS/FAIL from logit CRC compared to golden values displayed on LEDs or WS2812B.
  - (c) UART via PMOD with USB-UART adapter.
- **Comparison:**

  | Criteria | (a) JTAG-to-AXI | (b) self-test BRAM | (c) UART PMOD |
  | --- | --- | --- | --- |
  | Additional hardware | none (same JTAG cable) | none | USB-UART adapter |
  | Bank voltage must be certain | no (bank 0 = 3.3 V [OFFICIAL]) | no | yes (bank 15 uncertain) |
  | Change weights without resynthesis | yes | no | yes |
  | E1–E4, E7 with full logging | yes | no (PASS/FAIL only) | yes |
  | Reuse driver and harness | yes (SPI frames translated to AXI transactions) | no | partial (new protocol) |
  | Upload speed | slow (Vivado transactions), sufficient for experiments | no upload needed | moderate |
  | Risk | Hardware Manager Tcl commands untested on board | lowest | requires new UART RTL |

- **Decision:** (a). Details:
  1. `top_core` receives external host bus port (byte), ORed with bus from `spi_slave`; only one host active at a time. `top_board` ties this port to zero, so SPI bitstream unchanged.
  2. `rtl/axil_bus_bridge.v`: 32-bit AXI4-Lite slave decomposing each transaction into byte accesses on host bus (little-endian, bytes with `WSTRB` only), plus ID window at address 0xFFFFF8–0xFFFFFF returning same ID word as SPI 0x9F command.
  3. JTAG-to-AXI Master IP only in `rtl/platform/xilinx/`; simulation model `rtl/platform/sim/` replays transaction log and checks read data, so JTAG path passes bit-exact co-simulation like `spi_session`.
  4. `board/top_jtag.v` for ZERO7 without Pi: clock B13, LEDs R3/R2, WS2812B N1; SPI pins unused.
  5. Python: `JtagAxiTransport` translates SPI frames from `SentinelDriver` to word transactions; partial word writes only via read-modify-write in memory areas, never in registers. `JtagBackend` = `HwBackend` on top of that transport. Vivado side runs as persistent open Tcl session (`create_hw_axi_txn` and `run_hw_axi`, UG908); data ordering and command behavior checked with pattern test upon initial board connection.
  6. (b) remains viable as smoke test and hostless demo, but not implemented now.
- **Impact:** new SPEC §12.7. New co-simulation `jtag_session` and Python dry-run test. Official report (`top_board`) unchanged. Results from this path remain [HW] only if run on board, and end-to-end latency not representative of SPI.
- **Status:** Accepted.

## ADR-026 — ZERO7 bring-up without Raspberry Pi

- **Context:** board arrives 20 Nov 2026, Pi potentially later. Official documents only mention powering ZERO7 from Raspberry Pi GPIO header (IN-41); other methods [UNKNOWN]. Bank 15 and 34 VCCO voltage unwritten, and BGA VCCO balls cannot be probed.
- **Decision:**
  1. Three bring-up designs in `fpga/bringup/`: `blink_top` (blinking LED; clock frequency from stopwatch), `vcco_probe_top` (PMOD1 and N1/J7 at fixed levels, so bank 15 and 34 voltages readable with multimeter on header), `io_test_top` (buttons and switches to LEDs and WS2812B colors).
  2. Bring-up bitstreams may be created before VCCO is certain, because these designs only drive FPGA-owned pins (tested); `fpga/bringup/build.py` still rejects without `--accept-inferred-io`. Full SENTINEL bitstream for board continues waiting for measured VCCO (ADR-024).
  3. Powering without Pi not recommended from header pins without document basis. Written path is power from Raspberry Pi; any borrowed Pi used solely for power follows that path, noting Pi 4 compatibility [UNKNOWN] and Pi 5 mentioned by organizers.
  4. Milestone M22 (bring-up without Pi and JTAG host) in STATUS.
  5. BOARD phase still commences per CLAUDE.md §8. All created prior is preparation.
- **Impact:** `board/BRINGUP_NO_PI.md`; experiment map without Pi in STATUS.
- **Status:** Accepted.

## ADR-027 — BUFGCTRL select pin unconstrained by timing

- **Context:** official run 17 Nov 2026 after ADR-025 missed narrowly: WNS −0.044 ns on `clk_sel_turbo` path (`clk_safe` domain) to BUFGCTRL S1 pin, with half-period turbo clock requirement [VIVADO-STA]. Prior runs passed on same path with +0.27 to +0.65 ns slack; difference was placement. Turbo frequency changes dynamically, so this path is genuinely asynchronous; Vivado considered it synchronous only because turbo level 0 equals clk_safe and both originate from CLK20M.
- **Basis:** DS189 Table 32, note 1: TBCCCK_CE/TBCCKC_CE must be met for glitchless clock switching; other global clock setup/hold optional, only needed if switching must match cycle-by-cycle with simulation. In SENTINEL CE pin tied to 1 (constant), select only changes when fast domain is idle (SPEC §7.7), and `clk_gen_xilinx` reports mux status after fixed delay.
- **Alternatives:** (a) rely on fortuitous placement; (b) lower f_safe; (c) false path to BUFGCTRL S0/S1 pins based on DS189.
- **Decision:** (c). `fpga/constraints/top_board_timing.tcl` provides `set_false_path` to BUFGCTRL select pins. No other exceptions added (ADR-021). CE pin not excluded.
- **Impact:** official report rerun; test verifies this exception exists with citations. With false path, `report_cdc` logs this path as CDC-13 (crossing to non-flop primitive) with unsafe status; guard test of official report permits CDC-13 only on those BUFGCTRL S0/S1 pins and rejects others.
- **Status:** Accepted.

## ADR-028 — Skipping zero-activation operand sets

- **Context:** 35.9% of model s operand sets (25.4% model xs) carry zero activations, including padding taps [SIM, golden model, first 1,000 CIFAR-10 test images, `results/model/zero_taps_{s,xs}_k8.json`]. Because one activation is broadcast to all lanes (SPEC §5.2), in that cycle all data lanes and checksum lanes receive product 0.
- **Basis:** Parhi chapter 17 (switching activity) and chapter 9 (strength reduction), combined with SENTINEL data-broadcast format; `docs/research/PARHI_DEVELOPMENT_LIST.md` item D1. Originality claims only permissible after checking `docs/PRIOR_ART.md`.
- **Alternatives:** (a) retain current design; (b) `operand_gen` skips every operand set with a = 0 (padding or ReLU results) before operand FIFO; (c) only skip padding taps, whose positions are known statically.
- **Decision (proposal):** (b). Unit start/end flags move to first/last sent operand; units with all-zero operands still produce 0 (one zero operand sent or accumulators reset).
- **Impact:** SPEC §5.2 and §5.4 (cycle model becomes data-dependent), `rtl/operand_gen.v`, `model/engine_model.py`, engine benches and tests locking `CYCLES_TOTAL`. Results remain bit-exact; checksum identities (SPEC §6) unchanged because every skipped term is 0 across all lanes.
- **Test plan:** (1) new cycle model = ideal cycles − zero operands, computed by `model/zero_taps.py` per image, compared against bench `CYCLES_TOTAL`; (2) `engine_s_k8_n200` and `engine_xs_k8_n200`: logits and classes identical to golden (PASS n/n); (3) corner unit benches: all-zero unit, single non-zero operand at start or end of unit, full padding window; (4) [SYNTHETIC] injection campaign yields identical detection/correction; (5) official report rerun, WNS does not degrade.
- **User decision (17 Nov 2026):** approved for implementation **after G1**, under conditions: (1) only if G1 (13 Dec 2026) reached on time; if missed, deferred or cancelled; (2) implemented as disableable parameter (`ZERO_SKIP` = 0/1); non-skip mode remains baseline and bit-exact; (3) cycle savings and real time measured, including operand supply limits; 35.9% figure labeled [SIM] with dataset and image count (model s, golden model, first 1,000 CIFAR-10 test images, padding taps counted); (4) impact on timing error experiments recorded; every E1–E3 result notes whether zero-skip enabled; (5) if not bit-exact and stable by 10 Jan 2027, zero-skip disabled by default and unused in demo.
- **Review notes on conditions:** (a) supply limits: `operand_gen` still scans every tap, R per safe cycle, so simple speedup model is `min(1/(1−z), R·f_safe/f_lane)` with z zero operand fraction [INFERENCE]; zero-skip is most useful at safe clock and competes with lane overclock for supply bandwidth. Recorded as hypothesis to measure (condition 3). (b) Condition 4 expanded: every [HW] result, not just E1–E3, records zero-skip status; automatic via spare bit in ID flags byte (SPEC §12.2), like lane type. (c) `ZERO_SKIP` preferably synthesis parameter plus runtime control bit (A/B on same bitstream); confirmed during implementation.
- **Status:** Conditionally accepted (17 Nov 2026): implementation begins only after G1 reached on time.
- **Gate update (25–26 Nov 2026):** ADR-038 lifted the "only after G1" gate. On 26 Nov the user asked again for the G1 status and to stop zero-skip if G1 is threatened; the status is written in `STATUS.md` (G1 not missed, board half at risk for reasons outside this work, zero-skip takes nothing the board half needs).
- **Results (26 Nov 2026) [SIM]:**
  - First implementation (skip every zero set except unit-closing and pass-opening ones, no other guard): image 0 PASS, 195,134 cycles against 277,895. The 200-image regression hung. Rerun with a per-image watchdog and a simulation-only overrun check in `lane_array`: images 0–117 and 134–197 that were reached passed (182 images); images 118 and 198 printed `FAIL lane_array: result serializer overrun` (two units ended 10 and 8 cycles apart), then gave wrong logits and never finished. Logs: `results/sim/zero_skip/unguarded/`.
  - Cause: the lane-array result serializer sends K + 2 + C3 words per unit, one per `clk_fast` cycle, and a new unit end overwrote words still queued. Without zero-skip every unit lasts at least 27 cycles (SPEC §5.4). How the short spacing arises on these images (partly zero units queued behind an operand-FIFO backlog) is [INFERENCE]; synthetic black, sparse and half-black images did not trigger it.
  - Two guards, both bit-exact on all 200 images, same image set, xsim, model `s`, K = 8, C3 = 1 (`python tools/zs_compare.py`, `results/sim/zero_skip/compare.json`):

    | Variant | Images passed | Mean cycles per image | Fewer than `ZERO_SKIP = 0` (277,895) | Guard cost against the unguarded run (182 common images) |
    | --- | --- | --- | --- | --- |
    | unguarded (first implementation) | 182 of 200 reached (118 and 198 fail) | 189,959.1 | 31.64 % | — |
    | `ZERO_SKIP = 1`: at least K + 2 + C3 sets per unit (`operand_gen`) | 200/200 | 189,797.6 | 31.70 % | 5 cycles in total, at most 4 on one image |
    | `ZERO_SKIP = 2`: stall of unit-closing words (`fast_path`) | 200/200 | 189,797.6 | 31.70 % | 0 cycles |

    The two guards differ on two images only: image 57 (188,800 against 188,796) and image 81 (186,755 against 186,754), 5 cycles over 200 images. A result buffer behind the serializer was not built: it could only win back stall cycles of `ZERO_SKIP = 2`, and there were none on the 182 comparable images. On the four sparse test images the means are 181,097 (`ZERO_SKIP = 1`) and 181,094 (`ZERO_SKIP = 2`).
  - The testbench clocks `clk_safe` and `clk_fast` alike, so the operand-supply limit of condition 3 at the real clock ratio is not covered by these numbers.
- **Vivado (26 Nov 2026) [VIVADO-STA]:** official flow on xc7s25csga225-1, LUT lanes, both domains analysed at 8 ns; Fmax = 1000 / (8 − WNS). Side runs `python tools/run.py synth-official --zero-skip 1 --tag zs1` and `--zero-skip 2 --tag zs2` (`results/vivado/official_zs1/`, `official_zs2/`):

  | Build | clk_safe WNS (Fmax) | clk_fast WNS (Fmax) | LUT | FF |
  | --- | --- | --- | --- | --- |
  | `ZERO_SKIP = 0` (official report, `results/vivado/official/`) | 0.678 ns (136.6 MHz) | 0.898 ns (140.8 MHz) | 7,741 | 6,209 |
  | `ZERO_SKIP = 1` | 0.587 ns (134.9 MHz) | 0.637 ns (135.8 MHz) | 7,912 | 6,229 |
  | `ZERO_SKIP = 2` | 0.471 ns (132.8 MHz) | 0.292 ns (129.7 MHz) | 7,878 | 6,213 |

  A first baseline side run with the same RTL (`--tag base26`) did not match the official report (7,859 LUT, clk_safe WNS 0.811 ns): with `ZERO_SKIP = 0` the slot-shift multiplexer and the widened FIFO write enable were still synthesized, because synthesis cannot prove that a valid slot 1 implies a valid slot 0. Both are now gated by the parameter, so `ZERO_SKIP = 0` is the original slot wiring again; the gate does not change modes 1 and 2. The rerun of `--tag base26` after the gate matches the official report exactly (0.678 / 0.898 ns, 7,741 LUT, 6,209 FF, `results/vivado/official_base26/`); the reports of the first base26 run were overwritten by it.
- **Decision (26 Nov 2026):** the guard of `ZERO_SKIP = 1`. Both guards are bit-exact on 200 images and cut 31.70 % of the cycles; `ZERO_SKIP = 2` saves 5 cycles more over the 200 images (about 1.3 × 10⁻⁷ of all cycles) but loses 0.345 ns of `clk_fast` slack and 0.116 ns of `clk_safe` slack against `ZERO_SKIP = 1`, in the domain the lane-overclock research depends on. `ZERO_SKIP = 2` stays in the RTL as a comparison variant only, so these numbers can be reproduced.
- **Stop and report (user rule "if a change makes results worse, stop"):** with `ZERO_SKIP = 1`, Fmax drops against the official build (clk_safe −1.7 MHz, clk_fast −5.0 MHz at the 8 ns analysis), both still above 125 MHz. Zero-skip therefore stays off by default (`ZERO_SKIP = 0`, official reports unchanged) and is not taken further until the user decides whether 31.70 % fewer cycles is worth the lower slack. Still open if it goes ahead: test plan item 4 (injection campaign with zero-skip), condition 3 at the real clock ratio, and a run of model `s4`.
- **DSP variant check (26 Nov 2026, user: test zero-skip on the DSP speed and demo variant):**
  - Bit-exact: `engine_s_k8_c1_dsp_zs_n200` PASS 200/200, mean 189,791.7 cycles against 277,891 for the DSP baseline in the single-clock testbench [SIM] (`results/sim/zero_skip/dsp_zs1/`).
  - Vivado, `python tools/run.py synth-official --variant dsp --zero-skip 1 --tag zs1` against `results/vivado/official_dsp/` [VIVADO-STA]: clk_safe WNS 0.445 → 0.694 ns (132.4 → 136.9 MHz), lanes analysed at 250 MHz WNS 0.102 → 0.207 ns (256.5 → 263.6 MHz), LUT 6,096 → 6,254 (+2.6 %), FF 5,429 → 5,435. One implementation run each; the slack gain is within run-to-run placement variation and is not claimed as an effect of zero-skip.
  - Condition 3 at the real clock ratio, `tb_system` (separate `clk_safe` and `clk_fast`), model `s4`, DSP lanes, 10 verification images without injection, `clk_safe` cycles per image (`python tools/zs_compare.py`, `results/sim/zero_skip/speed_r2/`, `speed_r1/`) [SIM]:

    | Lane clock | `ZERO_SKIP = 0` | `ZERO_SKIP = 1` | Change |
    | --- | --- | --- | --- |
    | 2 × `clk_safe` (DSP variant, 250 MHz at `f_safe` = 125 MHz) | 162,397.0 | 162,394.1 | −0.002 % |
    | = `clk_safe` | 277,369.0 | 185,918.7 | −32.97 % |

    At 2 × `clk_safe` the lanes already consume every set the operand generator can scan (R = 2 taps per `clk_safe` cycle), so skipping zero sets only leaves the lanes idle; this confirms the bound min(1/(1 − z), R·f_safe/f_lane) of the review notes. Zero-skip shortens an image only while the lanes run below R·f_safe.
  - **Decision:** not used in the DSP demo build (no speed gain for 158 more LUTs); `variant_dsp` keeps `ZERO_SKIP = 0`. Zero-skip stays a tested option, worth it only for lanes below the supply limit (for example lanes on the safe clock as a fallback) [INFERENCE for configurations other than the two measured]. — Checksum weight generator as multi-operand CSD tree

- **Context:** worst path of `clk_safe_raw` runs from weight registers to C3 weight tree (`u_wc0/with_c3.u_sum3`): 10 logic levels, 7.408 ns, slack +0.473 ns at 125 MHz [VIVADO-STA, official report 17 Nov 2026]. Both wc generators consume 407 LUTs [VIVADO-STA].
- **Basis:** Parhi chapter 13 (CSD and tree-height reduction), chapter 15 (multiple constant multiplication for constant linear transforms), chapter 14 and appendix E (carry-save multi-operand addition, Wallace/Dadda trees). wc3 = signed sum of 14 shifted weight copies (CSD of k², k = 1…8); shared subexpression identities (k²·w = k·(k·w); wc2 = Σ S_j; wc3 = Σ (2j−1)·S_j with S_j = Σ_{k≥j} w_k) verified on 1,000 random weight vectors (`docs/research/parhi/CH15.md`).
- **Alternatives:** (a) retain; (b) balanced flat tree of CSD terms (~4 adder levels, ~3 with 3-input adders), with one register stage in middle if necessary; (c) minimum area with shared terms between wc2 and wc3.
- **Decision (proposal):** (b); term sharing (c) used only if not adding depth.
- **Impact:** `rtl/wc_gen.v` and its instantiations. wc values identical, so SPEC §6 unchanged; if additional register used, generator latency increases one stage and recorded.
- **Test plan:** (1) new `wc_gen` bench against formula: 10^6 random vectors (fixed seed) and corner vectors (all −127, all +127, alternating, single non-zero lane); (2) all engine and lane benches pass without vector changes; (3) official report rerun: worst path of `clk_safe_raw` no longer in C3 tree and WNS increases; official report guard test remains green.
- **User decision (17 Nov 2026):** approved, under conditions: (1) equivalence with old implementation proven via tests (property test + M3 campaign vectors) and bit-exact; (2) LUT, FF and Fmax [VIVADO-STA] compared before and after; if not better, revoked and rationale recorded here; (3) G1 (13 Dec 2026) must not slip; if > 5 days, halt and report.
- **Review notes on conditions:** (a) M3 campaign vectors test checker decisions on injected accumulators, not wc generation; appropriate equivalents used: `wc_gen` property test against formula (random vectors with fixed seed and corner vectors), all real weight groups of model s and xs (model data which also sourced M3 campaign units), then checker benches using M3 vectors and all engine benches rerun without vector changes. (b) "Better" defined as: out-of-context clk_safe Fmax increases (same settings as `final` row in `fpga/reports/summary.csv`: t_safe 7.0 ns, t_fast 6.4 ns, non-MAC factor 0.7), worst path of clk_safe no longer in C3 tree, and LUTs do not increase > 2%. "Before" comparison rerun on current RTL (`--tag pre029`), not old row, for fairness. Upper bound of benefit visible in old OOC data: without C3 entirely, clk_safe Fmax 147.8 MHz vs 139.1 MHz with C3 [VIVADO-STA].
- **Results (18 Nov 2026):** `rtl/wc_gen.v` rewritten as single flat tree per output. Each constant multiplication decomposed into shifted w_k copies, one per 1-bit of k or k²: at K = 8 there are 13 copies for wc2 and 14 for wc3, hence 16 leaves and 4 adder levels. Registers placed at middle level, so each stage contains 2 adders (previously 4 and 1). Ports and 2-cycle latency unchanged. Binary bits used, not CSD, because copy count is identical for k² with k = 1…8 without needing subtractions.
  - Equivalence [SIM]: new benches `wc_gen_k{8,16}_c{0,1}` (corner vectors, 20,000 random vectors seed 2027, all 3,777 real weight words of model s and xs at K = 8) pass on old and new RTL, and `wc_gen_k8_c1_1m` (10⁶ additional random words) PASS 1003821/1003821 on new RTL; Verilator lint for `wc_gen_k8_c1`, `wc_gen_k16_c1` and `engine_c{0,1}` clean; `python tools/run.py test` suite rerun (see STATUS).
  - OOC, same settings (t_safe 7.0 ns, t_fast 6.4 ns, factor 0.7) [VIVADO-STA, `fpga/reports/summary.csv`]: `pre029` 5,710 LUTs, 5,076 FFs, clk_safe Fmax 141.70 MHz → `post029` 5,668 LUTs (−0.7%), 5,118 FFs (+0.8%), 144.34 MHz (+1.9%). clk_safe worst path moved from wc tree to `u_post` shifter (16 levels).
  - Official report LUT variant [VIVADO-STA, `results/vivado/official/`]: 6,851 → 6,824 LUTs, 6,149 → 6,191 FFs, clk_safe 132.9 → 133.7 MHz (WNS +0.473 → +0.518 ns). clk_safe worst path now reset net `rst_safe_r` (0 logic levels), not C3 tree.
  - Official report DSP variant [VIVADO-STA, `results/vivado/official_dsp/`, compared against side run `official_dsp250` prior to this ADR]: clk_safe **dropped** from 129.2 to 126.7 MHz (WNS +0.262 → +0.109 ns), lane 265.5 → 262.0 MHz. clk_safe worst path is reset net `rst_safe_r` → `u_checker/sum_a_reg/R` with 0 logic levels, purely fan-out routing; wc tree no longer appears. Design still passes 125 MHz.
- **Decision on results:** retained. All three review note (b) criteria met: OOC clk_safe Fmax increased, C3 tree removed from worst path, LUTs decreased. DSP variant clk_safe drop stemmed from routing large fan-out reset net, already noted as next bottleneck; per user rules, reported and not forced. Recommendation: reset fan-out fix (duplicate reset register or `max_fanout` attribute in `rtl/top_core.v`, without SPEC change) as separate step, then rerun both official reports. Time spent: 1 day of 5-day limit; G1 did not slip.
- **Reset fan-out fix (18 Nov 2026, user approved):** `rst_safe_r` register in `rtl/top_core.v` given `max_fanout = 64` attribute, causing synthesis to replicate it; simulation behavior and SPEC unchanged. Results [VIVADO-STA]: LUT variant clk_safe 133.7 → 136.6 MHz (WNS +0.518 → +0.678 ns), 6,824 → 6,832 LUTs, 6,191 → 6,209 FFs; DSP variant clk_safe 126.7 → 132.4 MHz (WNS +0.109 → +0.445 ns), and clk_safe worst path moved to `u_checker` (12 levels). Side effect of re-placement, lane domain untouched: DSP lane analyzed at 250 MHz 262.0 → 256.5 MHz (WNS +0.183 → +0.102 ns, still passes), LUT lane at 125 MHz 141.9 → 140.8 MHz. Test suite: 257 passed.
- **Decision on side effects (18 Nov 2026, left by user to Claude):** reset fix retained. In DSP variant, engine rate bounded by supply R·f_safe = 250 MHz, so lane Fmax above 250 MHz adds no throughput, and lane still passes 250 MHz. The determining factor is clk_safe: it bounds supply and is prerequisite for ADR-032 (b), which requires 142.9 MHz. In LUT variant, lane difference 141.9 → 140.8 MHz (0.8%) is placement variation in untouched domain, whereas overclock research starting point is measured on board, not from STA. Reverting would return reset net to worst path with +0.109 ns margin in DSP variant.
- **Status:** Accepted (18 Nov 2026), implemented, plus reset fan-out fix (retained).

## ADR-030 — Lane implementation: LUT or DSP, and operand supply limits

- **Context:** ADR-013 selected `LANE_IMPL = lut` without comparing DSP variant. Out-of-context data xc7s25csga225-1, model s, K = 8, C3 = 1 [VIVADO-STA, `fpga/reports/summary.csv`]: LUT lane 5,717 LUTs, lane Fmax 148.1 MHz; `dsp_min` 4,469 LUTs, 14 DSPs, 272.9 MHz; `dsp_full` 4,471 LUTs, 25 DSPs, 265.0 MHz; clk_safe Fmax identical (139–143 MHz). Lanes can only receive operand sets up to R·f_safe = 2 × 125 = 250 MHz (ADR-013). DSP variant passes benches [SIM].
- **Basis:** Parhi chapter 13 (multiplier structures), chapter 17 (multiplier glitching up to ~40% power), chapter 3 (parallelism with idle hard multipliers); `PARHI_DEVELOPMENT_LIST.md` item D3.
- **Alternatives:** (a) keep LUT: lane exceeds static timing limit well below 250 MHz, enabling timing errors to be observed in accessible range; (b) `dsp_min` for official variant: faster and fewer LUTs, but lane safe up to supply limit, so overclock experiments yield almost zero errors unless supply increased; (c) `dsp_min` with R increased so supply exceeds lane Fmax (RTL changes in `operand_gen`/FIFO); (d) two variants: LUT for E-series experiments, DSP for speed demo, both from same parameters.
- **Decision (proposal):** awaiting user. Recommendation: (d), preserving overclock + checksum research narrative while delivering best speed numbers; difference is solely parameters and bitstream.
- **Impact:** `config/hw_zero7.yaml` or second variant, official report rerun. (c) modifies SPEC §5 (operand slot count) and RTL.
- **Preliminary results (17 Nov 2026):** official side run with `dsp_min` yields 5,550 LUTs (official 6,851), 5,307 FFs, 2,011 slices, 14 BRAM tiles, 14 DSPs, WNS +0.395 ns, WHS +0.049 ns at 125 MHz [VIVADO-STA, `results/vivado/official_dspmin/`]; worst path moved to high-fanout net (`acc_last` to hold registers, and safe reset to injection registers), no longer multiplier.
- **Test plan:** (1) official side run `python tools/run.py synth-official --lane-impl dsp_min --tag dspmin` (already executed, see preliminary results): LUTs, DSPs, WNS compared with official report; (2) `lane_array_k8_c1_dsp_min` and engine benches with `LANE_IMPL = 1` pass; (3) for (d): both bitstreams pass E7 on safe clock during board phase.
- **User decision (17 Nov 2026):** option (d), two lane variants, under conditions: (1) both variants use same golden model and bit-exact across all tests; (2) both fit in XC7S25CSGA225-1 with separate synthesis reports; (3) every number in reports and slides states variant; speedup claims from overclock + correction measured on LUT variant against same LUT variant on safe clock; cross-variant numbers not mixed; (4) this ADR includes answer to judges' question "if DSP lane is already safe up to 250 MHz, what is the purpose of SENTINEL?"; if answer is weak, report to user before proceeding.
- **Review notes on conditions:** (a) condition 2 met for fitting: 6,851 LUTs (LUT) and 5,550 LUTs (DSP) of 14,600 [VIVADO-STA]. Organizers require synthesis report for XC7S25CSGA225-1 but format unclear (Q6) [OFFICIAL/UNKNOWN]; two reports not prohibited, but determine primary (demo variant) vs appendix. (b) Condition 3 enforceable automatically: ID flags byte carries lane type (`IMPL_BITS`, `rtl/top_core.v`), allowing host tools to record variant in every result file.
- **Premise check (17 Nov 2026):** official side run `python tools/run.py synth-official --lane-impl dsp_min --turbo-mhz 250 --tag dsp250` analyzes `clk_fast_turbo` at 250 MHz: lane WNS +0.233 ns (Fmax 265.5 MHz), `clk_safe` +0.262 ns at 125 MHz (129.2 MHz), 5,542 LUTs, 5,494 FFs, 14 DSPs, 14 BRAM tiles, all nets routed [VIVADO-STA, `results/vivado/official_dsp250/`]. Premise of judges' question statically true: DSP lane safe up to operand supply limit.
- **Answer to judges' question (condition 4): "If DSP lane is already safe up to 250 MHz, what is the purpose of SENTINEL?"**
  1. True, and reported transparently. In XC7S25 with K = 8, DSP lane passes static timing up to 265.5 MHz in full design, above 250 MHz operand supply limit [VIVADO-STA]. For speed, DSP variant is superior, and its engine is bounded by operand supply, not lanes. LUT lane has static Fmax 137.0 MHz in official report [VIVADO-STA]. Overclock + correction at most brings it to 250 MHz, matching DSP variant on safe clock, no faster [INFERENCE from both figures].
  2. Checksum protection (C1/C2/C3: detection, localization, single-lane correction) remains active in DSP variant. It catches lane errors from any source, not merely timing. At statically safe clocks, expected errors are near zero [INFERENCE], serving as insurance. C3 cost in DSP variant is 775 LUTs and 1 DSP (OOC, `dsp_min` C3 = 0 vs 1) [VIVADO-STA].
  3. Overclock + correction is demonstrated on LUT variant, where multipliers form critical path with 137 → 250 MHz headroom below supply limit. This variant represents designs whose arithmetic is not mapped to hard DSPs. On this chip, that scenario is hypothetical: DSP variant consumes only 14 of 80 DSPs at K = 8, and 38 at K = 16 (OOC) [VIVADO-STA].
  4. Overclocking becomes beneficial for fastest variant only when operand supply is raised above DSP lane Fmax, e.g. via alternative (c) with larger R or higher f_safe. That alters SPEC §5 and `operand_gen` RTL, while `clk_safe` in full design currently has Fmax 129–133 MHz [VIVADO-STA].
- **Evaluation of answer:** weak for speed claim (items 1 and 3), sufficient for reliability and methodology claims (item 2). Per condition 4, implementation of (d) held and report submitted to user with recommendations: (R1) (d) retained, narrative adapted. DSP variant serves as speed and demo variant with active checksums. LUT variant serves as overclock research variant for E1–E3. Slides openly disclose that DSP lane on this chip requires no overclock. (R2) After G1, and only if G1 on time, feasibility study of increasing operand supply conducted, extending overclock + correction to fastest variant; study via new ADR. Decision with user.
- **R1/R2 decision (18 Nov 2026, delegated by user to Claude):** R1 executed now. R2 recorded as ADR-032 and executed only after G1. Rationale: R2 alters SPEC §5 and `operand_gen`, while `clk_safe` in full design has Fmax 129–133 MHz [VIVADO-STA]. Executing before 13 Dec 2026 jeopardizes G1, violating user constraints. R1 involves no RTL changes; parameters, reports, benches, and labels only.
- **R1 contents:** (1) `config/hw_zero7.yaml` receives `variant_dsp` block (`LANE_IMPL = dsp_min`, lane clock 250 MHz = R·f_safe). (2) `python tools/run.py synth-official --variant dsp` writes second official report to `results/vivado/official_dsp/`, with lane clock analyzed at 250 MHz; guard test `test_committed_variant_reports_are_clean` checks both reports. (3) Bit-exact benches for DSP variant: `engine_s_k8_c1_dsp` (fast), `engine_s_k8_c1_dsp_n200` and `system_s_k8_c1_dsp` (slow). (4) Every [HW] metadata includes `lane_impl`, `c3_hw`, and `inj_hw` read from bitstream ID flags byte (`sentinel.driver.lane_variant`). (5) Report and slides narrative: DSP variant is speed and demo variant with active checksums; LUT variant is overclock research variant (E1–E3). Slides state openly that DSP lane on this chip does not need overclocking, and overclock speedup compared strictly LUT vs LUT on safe clock.
- **Official report DSP variant (18 Nov 2026, after reset fan-out fix):** `python tools/run.py synth-official --variant dsp`: 5,472/14,600 LUTs, 5,429 FFs, 14 BRAM tiles, 14 DSPs, lane 256.5 MHz when analyzed at 250 MHz (WNS +0.102 ns), clk_safe 132.4 MHz (WNS +0.445 ns), WHS +0.060 ns, all nets routed [VIVADO-STA, `results/vivado/official_dsp/`, including ADR-029]. LUT variant: `results/vivado/official/`. Both reports fit in XC7S25CSGA225-1 and guarded by `test_committed_variant_reports_are_clean`. DSP variant bit-exact [SIM]: `engine_s_k8_c1_dsp` PASS 1/1 and `engine_s_k8_c1_dsp_n200` PASS 200/200.
- **Status:** Accepted (17 Nov 2026), option (d) with R1 narrative (18 Nov 2026); R2 moved to ADR-032.

## ADR-031 — Fine-grain pipelining of lane multiplier and C3 tree

- **Context:** relevant only if LUT lane retained (ADR-030 (a) or (d)). Worst path of lane: operand register → LUT multiplier product register, 9 levels, 7.202 ns, 55% routing; sourced from operand register shared by tool across lanes [VIVADO-STA].
- **Basis:** Parhi chapter 3 (registers only on feed-forward cutset, fine-grain pipelining), chapter 6 (folding equations to recalculate all delays), chapter 10 (registers inside loops alter algorithms), chapters 7 and 4 (local register per lane vs shared register).
- **Alternatives:** (a) no; (b) one register stage in middle of LUT multiplier (partial products | final addition) for all data and checksum lanes and `v/l/f` flags; (c) (b) plus per-lane operand registers (`KEEP` or `MAX_FANOUT`).
- **Decision (proposal):** (c) if LUT lane retained.
- **Impact:** `rtl/lane_lut.v`, `rtl/lane_array.v` (flags), checker alignment; pipeline latency increases by one cycle per operand stream, modifying tests that lock cycle counts. Results remain bit-exact if all lanes and flags receive identical stages.
- **Test plan:** (1) all `lane_array_*` and `engine_*` benches pass with identical vectors; (2) checker bench with injections in data and checksum lanes yields identical detections; (3) official report rerun: lane worst path shortens; (4) [SYNTHETIC] campaign unchanged.
- **Status:** Proposed (17 Nov 2026), contingent on ADR-030.
- **Results (26 Nov 2026, built after ADR-038 and the user's approval of 26 Nov) [VIVADO-STA unless marked]:**
  - (c) built: `rtl/lane_lut.v` keeps one activation register per lane (`dont_touch`, D5) and registers the two activation-nibble products before their sum, so p = (p_hi << 4) + p_lo (b). The identity holds for all 65,536 pairs at W_W = 8 and 40,084 seeded pairs at 11, 14 and 16 bits [SIM]. Every lane and the v/l/f flags get the same extra stage.
  - Simulation [SIM]: all 71 fast RTL benches, `engine_s4_k8_c1_n200` (PASS 200/200, 277,381 cycles per image, +4 from the extra stage) and `system_s4_k8_c1` with data- and checksum-lane injections (PASS 10/10).
  - Official flow, LUT variant, 8 ns analysis: D5 alone made both domains worse (clk_fast WNS 0.898 → 0.835 ns, clk_safe 0.678 → 0.148 ns, `results/vivado/official_d5/`). (c): clk_fast 0.898 → 1.180 ns (140.8 → 146.6 MHz), clk_safe 0.678 → 0.694 ns, LUT 7,741 → 7,645, FF 6,209 → 6,604; the worst clk_fast path is now the fast reset fan-out, not a lane multiplier (`results/vivado/official_adr031/`, then the official report regenerated identically).
  - Out-of-context, SPEC 7.4 settings (t_safe 7.0 ns, t_fast 6.4 ns, non-MAC endpoints held to 0.7 of the period), tags `pre031` (lane of HEAD) and `adr031`: MAC slack 0.001 → 0.671 ns; non-MAC slack 0.185 → 0.121 ns (still met, so the 30 % rule holds); fast-domain Fmax 156.3 → 159.3 MHz; clk_safe 144.3 → 144.6 MHz; LUT 5,668 → 5,641; FF 5,118 → 5,513 (`fpga/reports/summary.csv`). The first `adr031` OOC run counted the new `p_lo`/`p_hi` registers as non-MAC endpoints and held them to 0.7 of the period; `fpga/ooc.tcl` and `fpga/parse_reports.py` now treat them as MAC registers (test added), and the rerun replaced that row.
  - Not rerun: test plan item 4 ([SYNTHETIC] campaign), which runs on the Python model and does not see the RTL lane latency.
- **Decision (26 Nov 2026):** accepted as (c). The lane Fmax rises in both flows; clk_safe and LUT do not get worse; the cost is 395 FF (+6.4 %) and one lane cycle per operand stream.

## ADR-032 — Increasing operand supply to make DSP lane critical path (R2)

- **Context:** DSP variant passes static timing up to 265.5 MHz in lane, above supply limit R·f_safe = 250 MHz [VIVADO-STA, `results/vivado/official_dsp250/`]. While supply is below DSP lane Fmax, overclock + correction does not speed up fastest variant (ADR-030, judges' answer items 1 and 4).
- **Alternatives:** (a) retain; (b) f_safe raised to 1000/7 = 142.857 MHz, making supply 285.7 MHz, slightly above DSP lane Fmax (overclock headroom ~7.6% [INFERENCE]); prerequisite is `clk_safe` passing 142.9 MHz in full design, currently 129–133 MHz, with ADR-029 plus reset net fan-out being first paths to shorten; (c) R = 3 operand slots per safe cycle (375 MHz supply): `operand_gen`, operand FIFO, and weight port width change, SPEC §5.4 changes; (d) wider operand words (two operands per lane per cycle, item D9).
- **Decision (proposal):** pending. Feasibility study begins only after G1, and only if G1 on time (same rule as ADR-028). Study order: (b) first, as it depends solely on `clk_safe` timing and ADR-029 results; (c) only if (b) fails and remaining time before 31 Jan 2027 permits.
- **Test plan:** (1) official side run with `--safe-div 7` after ADR-029, to check `clk_safe` WNS at 142.857 MHz; (2) if passing: all engine and system benches with new supply ratio, then E1 on DSP variant in board phase; (3) if failing: record worst path and decide if (c) feasible.
- **Status:** Proposed (18 Nov 2026), awaiting G1. Accepted for the DSP variant on 26 Nov 2026 (decision below).
- **Study result (26 Nov 2026, test plan item 1; gate lifted by ADR-038) [VIVADO-STA]:** `python tools/run.py synth-official --variant dsp --safe-div 7 --tag sd7` (`results/vivado/official_dsp_sd7/`). Contrary to the expectation in ADR-038, timing is met: `clk_safe` at 7.000 ns (142.857 MHz) WNS +0.098 ns, lanes analysed at 250 MHz WNS +0.173 ns (lane Fmax 261.3 MHz), WHS +0.014 ns, no unrouted nets, 6,099 LUT, 5,467 FF (official DSP at divider 8: 6,096 LUT, 5,429 FF). The worst `clk_safe` path is now in post-processing, `u_engine/cfg_n_reg[0]` → `u_post/shifted_reg[22]` (16 logic levels, 12 of them CARRY4, 6.831 ns, 53 % routing). With f_safe = 142.857 MHz the operand supply R·f_safe = 285.7 MHz lies above the DSP lane Fmax, so the lanes, not the supply, would limit the DSP variant. The margin is thin (0.098 ns) and comes from one implementation run. Adopting it changes the clock plan (`config/hw_zero7.yaml` f_safe, SPEC §7, the MMCM tables) and needs test plan item 2 (all benches at the new ratio); that is a user decision. The LUT variant (clk_safe WNS 0.678 ns at 8 ns) was not run at divider 7.
- **Decision (26 Nov 2026, user: "choose the best"):** (b) for the DSP variant only. `config/hw_zero7.yaml` `variant_dsp`: `safe_div: 7` (clk_safe 142.857 MHz) and lanes analysed at `lane_mhz: 255.0`, turbo level 13 of the unchanged table (125 MHz + k × 10 MHz, k = 0…15), which lies below the lane Fmax of the study run (261.3 MHz). The operand supply R · f_safe = 285.7 MHz now covers every turbo level, so SPEC 7.5 holds for the DSP variant (at 125 MHz it did not: 250 < 275 MHz). The LUT variant keeps 125 MHz. No RTL change: the divider already reaches MMCM1 through `SENTINEL_SAFE_DIV`; `fpga/run_official.py` takes the variant's divider (`safe_divider`).
- **Test plan item 2 (26 Nov 2026) [SIM]:** `system_s4_k8_c1_dsp` (official scenarios with injections, model s4, DSP lanes, clock ratio 255 / 142.857 = 1.785) PASS 10/10. Time per image, `tb_system`, model s4, DSP lanes, 10 images without injection (`results/sim/clock_dsp142/`): 162,397.0 `clk_safe` cycles at ratio 2.0 with clk_safe 125 MHz = 1.299 ms; 175,745.7 cycles at ratio 1.785 with clk_safe 142.857 MHz = 1.230 ms, 5.3 % less, both inside static timing. Lanes overclocked to the supply limit (285.7 MHz, ratio 2.0) would need 162,397 cycles = 1.137 ms [INFERENCE: cycle count from the ratio-2 run; error-free operation there is the [HW] experiment E1].
- **Official DSP report (26 Nov 2026) [VIVADO-STA]:** `python tools/run.py synth-official --variant dsp` now builds with divider 7 and analyses the lanes at 255 MHz (`results/vivado/official_dsp/`): clk_safe WNS +0.198 ns at 7.000 ns (147.0 MHz), lanes WNS +0.173 ns at 3.922 ns (266.7 MHz), WHS +0.049 ns, 6,099 LUT, 5,566 FF, no unrouted nets. Before (divider 8, lanes at 250 MHz): clk_safe WNS +0.445 ns at 8 ns, lanes +0.102 ns at 4 ns, 6,096 LUT, 5,429 FF.

## ADR-033 — Host Raspberry Pi 5 (supersedes ADR-022)

- **Context:** team decision of 25 Nov 2026: a Raspberry Pi 5 (8 GB, photo `board/photos/2026-11-25_pi5_box.jpg`) is available now [USER]; ADR-022 chose a Raspberry Pi 4. The organizers name the Raspberry Pi 5 as the host of the loaned ZERO7 [OFFICIAL, G-6]; ZERO7 takes its power from the header [OFFICIAL, IN-41]. On the Pi 5 the 40-pin header is driven by the RP1 I/O controller; the gpiozero documentation states "Only lgpio works on the Pi 5" and marks the RPi.GPIO factory "(not Pi 5)" [VERIFIED EXTERNAL, gpiozero.readthedocs.io api_pins, read 2026-11-25].
- **Alternatives:** (a) keep the Pi 4; (b) Pi 5 with gpiozero on the lgpio pin factory; (c) Pi 5 with direct libgpiod.
- **Decision:** (b). SPI stays on `spidev` (`/dev/spidev0.0`, SPI0 CE0, GPIO 8–11, unchanged BCM numbers, so `board/zero7.xdc` does not change). GPIO users (`GpioDoneLine`, buttons) select `LGPIOFactory` explicitly through `sentinel.transport.lgpio_factory()`, which fails with an install hint if lgpio is missing. `board/pi_check.py` checks `lgpio` and states whether GPIO will work on a Pi 5. Setup (Imager, SSH, Wi-Fi, SPI, packages) in `board/BRINGUP.md`.
- **Impact:** `sw/sentinel/transport.py`, `sw/sentinel/buttons.py`, `board/pi_check.py`, `board/BRINGUP.md`, SPEC §12.1 and §15. Pi 5 compatibility with ZERO7 stays [UNKNOWN] until shown on the board. ZERO7 current draw from the 5 V header pins [UNKNOWN], measured in bring-up step 1. No RTL change.
- **Status:** Accepted (team decision, 25 Nov 2026). ADR-022 superseded.

## ADR-034 — SEGGER J-Link as JTAG probe through the J-Link XVCD Server

- **Context:** team decision of 25 Nov 2026: the team has a SEGGER J-Link (20-pin JTAG) and no Digilent cable [USER]. The official guide uses a Digilent JTAG-HS3 [OFFICIAL, IN-42]. The SEGGER J-Link XVCD Server (J-Link software from V7.92d, default port 2542) lets the Vivado Hardware Manager use a J-Link as a Xilinx Virtual Cable [VERIFIED EXTERNAL, kb.segger.com/J-Link_XVCD_Server]. openFPGALoader lists the cable keyword `jlink` and Spartan-7 xc7s25 [VERIFIED EXTERNAL]. The JTAG header of the team's white ZERO7 and its pin order are not documented [UNKNOWN].
- **Alternatives:** (a) obtain a Digilent cable (organizer question pending); (b) J-Link through XVCD for programming and ILA; (c) J-Link through openFPGALoader for programming only.
- **Decision:** (b), with (c) as the programming fallback and VIO, LEDs and SPI register reads from the Pi 5 as debug fallbacks if ILA through XVC fails. Wiring table, safety checklist (measure the header voltage before VTref is connected; never use J-Link pin 19 to power the board) and a five-step test order in `docs/JLINK_VIVADO.md`.
- **Impact:** `docs/JLINK_VIVADO.md`, `board/BRINGUP.md`, `board/BRINGUP_NO_PI.md` (Digilent wiring superseded), SPEC §14. Programming and ILA through the J-Link are [UNKNOWN] until the user runs the test order. No RTL change.
- **Status:** Accepted (team decision, 25 Nov 2026).

## ADR-035 — Camera only through the Raspberry Pi

- **Context:** team decision of 25 Nov 2026: no camera module on the FPGA side; a camera, if used, sits on the Raspberry Pi, which captures, scales to 32×32 and sends the image over SPI [USER]. Real-time camera input is a condition of the image classification task [OFFICIAL, website §2]; for Class 2 it is not mandatory (organizer response relayed by the user, 23 Nov 2026). The camera type (USB webcam or CSI module) is not decided [USER].
- **Alternatives:** (a) camera on the FPGA PMOD; (b) camera on the Pi.
- **Decision:** (b). `sentinel.camera.open_source` takes `picamera` (CSI through picamera2), a camera index (USB through OpenCV/V4L2) or a video file; `python -m sentinel.camera_mode --source …`. During development a video file stands in for the camera, and any report states that the real camera demo is untested until it is run.
- **Impact:** no RTL change; SPEC §15 records the decision.
- **Update (user, 25 Nov 2026):** no camera is used. For Class 2 real-time camera input is not mandatory (organizer response relayed 23 Nov 2026); input images come from files on the Raspberry Pi (validation-folder mode). The camera code stays in `sw/` but is not part of the evaluation or demo.
- **Status:** Accepted (team decision, 25 Nov 2026; no camera, 25 Nov 2026).

## ADR-036 — Contest class: Class 1 Level 3 or Class 2 (ZERO7)

- **Context:** the user chose Class 1 Level 3 on 18 Nov 2026 when no JTAG cable was available [USER, 25 Nov 2026]; with ZERO7 and a J-Link now in hand, Class 2 may be viable again [USER]. The record of 23 Nov 2026 (`docs/official/CORRESPONDENCE_2026-11.md` §1) says the organizers confirmed that the project belongs to Class 2; this has to be reconciled by the user. Official facts: both classes require the XC7S25CSGA225-1 synthesis report [OFFICIAL]. Class 1 is limited to image classification; Level 3 allows any board and architecture after a classifier that fits XC7S25CSGA225-1 with its synthesis report; the targets are four classes (cat, dog, deer, horse), classified on organizer photos on the contest day, with real-time camera input, and teams "compete on the image recognition accuracy and processing speed" [OFFICIAL, website, read 2026-11-23]. Class 2 is limited to ZERO7, the task is free, Level 3 only [OFFICIAL]; per the relayed response, the organizer validation images do not apply to Class 2 and each team defines its own evaluation method.
- **Alternatives:** (a) Class 1 Level 3: judged on four-class accuracy and speed against other teams; ZERO7 not required. (b) Class 2: SENTINEL's own evaluation method (bit-exact against the golden model, [HW] timing-error atlas, throughput of the three checker modes) on ZERO7, which must then be used.
- **Recommendation (not a decision):** (b), keeping a four-class classification mode and the camera mode so that (a) stays possible. Reasons [INFERENCE]: SENTINEL's distinguishing results (error atlas, correction against recompute) need the physical Spartan-7 and fit a self-defined evaluation; in Class 1 the 8-lane engine (about 2 GOP/s at 125 MHz [SIM × VIVADO-STA]) competes on raw accuracy and speed, where it is not designed to stand out. Risk of (b): every Class 2 result depends on the board working in time (power through the Pi, verified XDC, J-Link through XVC).
- **Impact:** `CLAUDE.md` §7 (target class) only after the user decides; an evaluation-method ADR and SPEC change (for example retraining for the four classes) follow the decision.
- **Decision (user, 25 Nov 2026):** (b) **Class 2 (ZERO7 Class), Level 3, with image classification as the task**, because ZERO7 and the Raspberry Pi 5 are in hand. The class set and evaluation method (for example the four official classes cat, dog, deer, horse, or the CIFAR-10 stand-in) are decided in a follow-up ADR.
- **Status:** Accepted (user decision, 25 Nov 2026). `CLAUDE.md` §7 target line updated accordingly.

## ADR-037 — Class set: the four official classes (cat, dog, deer, horse)

- **Context:** ADR-036 fixed Class 2 Level 3 with image classification as the task. The Design Specification names four recognition targets, cat, dog, deer and horse, with 32 × 32 input [OFFICIAL, website news 2026/11/19, read 2026-11-23]. User decision of 25 Nov 2026: use these four classes. All four are CIFAR-10 classes; the model so far was trained on all ten CIFAR-10 classes as a stand-in (model `s`, `n_classes: 10`). The hardware supports up to N_CLASSES_MAX = 16 classes with weights loaded over SPI, without resynthesis (SPEC §1, §4).
- **Alternatives:** (a) keep the 10-class stand-in; (b) a new model variant `s4`: the architecture of `s` (SPEC §2.1) with a 4-class fully connected layer, trained on the CIFAR-10 subset {cat, dog, deer, horse}; (c) change `s` itself to 4 classes.
- **Decision:** (b). Label order follows the official list: cat = 0, dog = 1, deer = 2, horse = 3. Training data: the CIFAR-10 training images of these classes (seeded validation split as in SPEC §4); test data: the 4,000 CIFAR-10 test images of these classes. Same seed (2027), same quantization (PTQ, SPEC §4). `s` and `xs` stay as regression references, so existing benches and results remain valid. `config/hw_zero7.yaml` MODEL becomes `s4` once `s4` is trained, exported and bit-exact in the RTL engine bench. Photos of the organizers are for Class 1 and do not apply to Class 2 (relayed 23 Nov 2026); SENTINEL defines its own evaluation set from the 4-class CIFAR-10 test images, and may add other photos of the four classes later.
- **Impact:** SPEC §2 (new variant `s4`), `config/model_s4.yaml`, `model/data.py` (`cifar10_4` dataset), model lists in `model/` and `tools/`, new engine benches for `s4`, `docs/RESULTS_SIM.md`. No RTL change: the fc layer with 4 outputs uses one lane group (G = 1).
- **Status:** Accepted (user decision, 25 Nov 2026).
- **Follow-up (26 Nov 2026, user: "do the best until it runs on s4"):** `config/hw_zero7.yaml` names `MODEL: s4` (its address widths hold s4, checked by `tests/test_export.py`); the weight manifest carries `classes`; `sw/sentinel/validate.py` maps class folders to the model order (sorted folder names would have swapped dog and deer); `board/bringup.py` loads the ZERO7 model by default; bench `system_s4_k8_c1` runs the official system scenarios with s4: PASS 10/10 [SIM]. `config/hw_default.yaml` keeps `s` as the research model of the earlier campaigns.

## ADR-038 — Which development proposals are built (D1–D11, ADR-028, ADR-031, ADR-032)

- **Context:** user instruction of 25 Nov 2026: build the open proposals if they are all very useful and needed. Each is judged below on usefulness for the Class 2 image-classification entry, need, cost and risk. The earlier conditions of the user on ADR-028 (switchable `ZERO_SKIP`, bit-exact baseline, measured savings, E1–E3 tagged with the zero-skip state, off by default if not bit-exact and stable by 10 Jan 2027) and the general rule "stop and report if a change makes results worse" still apply. The "only after G1" gate is lifted by this instruction.
- **Assessment and decision:**

  | Proposal | Useful and needed? | Decision |
  | --- | --- | --- |
  | ADR-028 zero-skip (D1) | Yes: 35.9 % of model `s` operand sets carry a zero activation [SIM]; a measurable throughput technique that strengthens the architecture; checksum-safe because the activation is broadcast | **Build**, behind `ZERO_SKIP` (synthesis parameter), default 0 until bit-exact and stable |
  | ADR-032 raise operand supply (R2) | Only for overclocking the DSP variant; option (b) needs clk_safe ≥ 142.9 MHz, the reports show 136.6 / 132.4 MHz [VIVADO-STA] | **Study only:** one side run with `--safe-div 7` to record the shortfall; option (c) (R = 3) not built: large operand-generator and memory-port change for a variant whose lanes are not the bottleneck |
  | ADR-031 fine-grain pipelining + D5 per-lane operand registers | Useful for the LUT research variant (worst lane path 55 % routing from a shared register [VIVADO-STA]); not needed for correctness | **Build after zero-skip**, keep only if the LUT-lane Fmax rises and no other result gets worse |
  | D8 Winograd tiles | Not needed: weeks of work, new datapath, weight memory × 16/9, input transform outside checksum protection | **Not built**; described as an evaluated direction in the report |
  | D9 two operands per lane | Needs twice the operand bandwidth, the same blocker as ADR-032 (c); zero-skip gives a comparable gain for less | **Not built** |
  | D10 accumulator-loop fallbacks | Only if the accumulator loop becomes critical; it is on no worst path [VIVADO-STA] | **Not built** |
  | D11 power optimisation | Power is not a listed criterion; no power measurement method on the board [UNKNOWN], so a gain could not be shown | **Not built**; revisit if a measurement method appears |

- **Order:** ADR-037 (four classes) first, then the ADR-032 study run, then ADR-028, then ADR-031 + D5. Each follows ADR → SPEC → golden model and tests → RTL, with Vivado before/after comparison.
- **Status:** Accepted (25 Nov 2026), decision delegated by the user.
