# Simulated Judges — SENTINEL

Written 2026-11-16 (PROMPT_UPDATE_ZERO7, Stage 8). This document is a self-assessment to determine work priorities. This is not a contest result prediction: official weightings have not been announced, real judges may evaluate very differently, and there is no guarantee of qualifying as finalists or winning.

Numbers in this document were copied from result files in the repo by a one-off script when the document was written; every number cites its file. If result files change, this document does not automatically update.

## 1. Basis of evaluation

[OFFICIAL] criteria from `docs/official/README.md` (guidelines G-2, G-5, G-6):

- Judges evaluate not only speed and area, but also ideas, originality, and uniqueness.
- Good presentation is appreciated: 10 minutes, at most 10 slides, 5 minutes Q&A.
- Participants' educational level is taken into account.
- "We like fun ideas. Please do something different from others."
- Mandatory: synthesis report for XC7S25CSGA225-1; validation data from organizers and real-time camera input; presentation shows how fast recognition results are output.
- Japanese page adds one item: partial specification changes flexibly accepted.

Official weightings [UNKNOWN]. The rubric below is an internal rubric [PROPOSAL]: seven items, score 0–5, weights summing to 100. Final score = sum(weight × score) / 5.

## 2. Does this idea already exist?

References: `docs/PRIOR_ART.md` and `docs/research/RISET_WEB_2026-11.md`.

| SENTINEL Component | Status in literature | Source |
| --- | --- | --- |
| Checksums (ABFT) for convolution | already exists | Huang & Abraham 1984; Zhao et al. 2021; Hari et al. 2020 |
| CNN accelerator overclocking on FPGA with checksum detection then recalculation | already exists | Marty et al. FPT 2018 and journal version 2020 |
| Automated overclocking with delay monitor | already exists | Jiang et al. (AOS) 2023 |
| Overclocking with flow from detection to recovery | already exists; recovery method not yet read by us | Li et al. ITC-Asia 2019 (abstract only) |
| Code-based output correction on PE array | stated as already possible | Gao et al. 2024 (abstract) |
| Characterization of MAC array timing errors on FPGA | already exists, not CNN | Chamberlin et al. 2024 |
| Zero-stall single-lane localization and correction, combined with overclocking | not yet found by us | to the best of our knowledge as of November 2026 |
| Per-layer clock with governor entirely inside FPGA | not yet found by us | to the best of our knowledge as of November 2026 |
| Timing error atlas of real CNN on Spartan-7 | not yet found by us | to the best of our knowledge as of November 2026 |

Simulated judges' assessment: the combination is attractive and differs from typical contest CNN projects (accuracy and FPS), but the underlying concepts are not new. Originality value depends on two things not yet available: full texts of Marty et al. and Li et al. (whether correction or per-layer clock has already been done by them), and board data demonstrating that correction is indeed better than recalculation. The words "first" or "novel" must not be used (ADR-020).

## 3. Three rounds

| Item [PROPOSAL] | Weight | Round 1 | Round 2 | Round 3 |
| --- | --- | --- | --- | --- |
| Ideas and originality | 25 | 3.5 | 3.5 | 3.5 |
| Uniqueness and appeal ("fun", distinct from other teams) | 10 | 3.0 | 3.0 | 3.0 |
| Technical proof and maturity | 20 | 2.5 | 3.0 | 3.5 |
| Speed and area | 15 | 2.0 | 2.5 | 2.5 |
| Fulfillment of mandatory tasks (validation, real-time camera, synthesis report) | 15 | 1.5 | 2.5 | 3.0 |
| Presentation and demo | 10 | 2.0 | 2.0 | 2.0 |
| Methodological honesty and claims | 5 | 4.5 | 4.5 | 4.5 |
| **Final score (0–100)** | | **52.5** | **59.0** | **62.5** |

### Round 1: state following ADR-013 through ADR-020 (commit 7919db7)

Largest weaknesses according to simulated judges:

1. No [HW] results yet. The core of the project, namely that timing errors affect a single lane and can be corrected (H1), has only been tested with artificial errors. If real errors turn out to affect many lanes simultaneously, correction is useless and design falls back to recalculation like Marty et al.
2. Official synthesis report, which is mandatory, is not yet present. Full design has never been implemented on the official chip.
3. MMCM2 reconfiguration sequencer does not exist yet (ADR-010), so turbo clock cannot yet be increased even if board were present.
4. End-to-end time is likely dominated by image transmission over SPI and camera, not computation. Overclocking gains may not be visible in "how fast recognition results are output".
5. Target classes not yet announced; integer accuracy of model `s` 80.22% on CIFAR-10 [SIM, `results/model/s/quant_result.json`] is only a temporary placeholder.
6. Two closest works not yet read in full, making originality claims fragile.
7. No visually apparent demo elements and no slides yet. This project is complex for 10 minutes.
8. Class 2 category, team size, and AI usage rules not yet confirmed.

### Improvements prior to round 2

- Official report flow created (`python tools/run.py synth-official`, ADR-014) and full `top_board` design implemented on xc7s25csga225-1: 6,172 of 14,600 LUTs (42.27%), 14 of 45 block RAMs, all nets routed [VIVADO-STA, `results/vivado/official_preadr021/`].
- Official variant (model `s`, K = 8, C3 active) passes regression: `PASS 200/200 (34/34 cycles_mean=277895 ideal=277504)` and dual-clock system `PASS 10/10 reconfigs=0` [SIM, `results/sim/rtl_regression.jsonl`].

### Round 2: new findings

That first run revealed weaknesses previously not visible:

1. One path failed timing at 125 MHz with slack −0.499 ns: power-on reset crossing from board clock to `clk_safe`. Intra-clock paths all passed (+0.286 ns in `clk_safe`, +0.204 ns in `clk_fast`) [VIVADO-STA, `results/vivado/official_preadr021/`].
2. Synchronizers not yet marked, and Vivado packed reset registers into SRLs.
3. Injection configuration signals cross to fast domain without synchronizers, and rules making this safe were unwritten in SPEC.
4. LOCKED MMCM2 entered `clk_seq` FSM without synchronizer.

### Improvements prior to round 3

- ADR-021 and SPEC §7.8: each asynchronous reset source has its own synchronizer, all synchronizers marked `ASYNC_REG`, LOCKED MMCM2 synchronized, permitted crossing list written, and `INJ*` registers only writable when `STATUS.BUSY` = 0.
- Official flow added `report_cdc` and `report_bus_skew`.
- Latency budget added to `docs/RESULTS_SIM.md` so weakness 4 of round 1 can be discussed with numbers.

### Round 3: final state of this session

Official run results [VIVADO-STA, `results/vivado/official/summary.md`], clk_safe 125 MHz:

- 6,170 of 14,600 LUTs (42.26%), 5,704 flip-flops, 14 of 45 block RAMs, 3 DSPs.
- Design worst setup slack +0.417 ns; within `clk_safe` +0.417 ns (Fmax 131.9 MHz), within `clk_fast` +0.481 ns (Fmax 133.0 MHz). Zero unrouted nets.
- `report_cdc`: zero crossings with unsafe status and zero synchronizers without `ASYNC_REG`. Remaining are 412 "unknown" endpoints per clock pair, which are quasi-static signals (injection configuration and layer index) whose rules are in SPEC §7.8. FIFO pointer bus skew: 16 constraints, worst slack +6.962 ns.
- Power according to `report_power` without activity data: 0.505 W. This is an estimate, not a measurement.
- Latency budget [SIM] × [VIVADO-STA] (`docs/RESULTS_SIM.md`): computation 277,895 cycles × 8.000 ns = 2.223 ms per image with safe clock. Transmitting 3,072 image bytes over SPI requires 2.458 ms at 10 MHz and 24.576 ms at 1 MHz; board SPI speed [UNKNOWN]. Thus transmission can be equal to or larger than computation.

No further meaningful improvements can be carried out without board, AMD documents, or closest works full texts, so simulation stops at round 3.

## 4. Remaining weaknesses, ordered by impact on score

| No | Weakness | Why important | What unlocks it |
| --- | --- | --- | --- |
| 1 | No [HW] results yet; H1 untested | simultaneously determines ideas, proof, and speed items | ZERO7 board, then B1 through B5 |
| 2 | MMCM2 reconfiguration sequencer does not exist yet | without it no real overclocking | PG065 or XAPP888 and DS189 (requires download permission) |
| 3 | Two closest works not yet read in full | claims may fall during Q&A | campus access to IEEE Xplore |
| 4 | End-to-end latency constrained by SPI and camera | official requirements assess how fast results emerge | measure SPI on board; report computation and end-to-end times separately |
| 5 | Target classes not yet announced | final accuracy cannot yet be reported | organizer announcement; retraining flow already exists |
| 6 | No visually apparent demo yet | "fun" and presentation items | WS2812B indicator (M17), camera mode, buttons |
| 7 | Narrow timing margin at 125 MHz | small changes can make official report fail timing | repeat `synth-official` on every RTL change; 100 MHz fallback (ADR-015) |
| 8 | Host rules for `INJ*` not yet guarded by hardware | test feature could disturb engine if written while running | write guard in `regfile` (small, not yet done) |
| 9 | Category, team size, and AI rules uncertain | administrative risk | inquire with organizers |

## 5. Questions judges might ask

1. **Why is detect-then-recalculate like Marty et al. not enough?** Honest answer at present: not yet proven better. SENTINEL mode 1 is that method, mode 2 is correction, both on the same bitstream; E4 compares them on the same board. If correction does not win, that is reported.
2. **How do you know errors only affect one lane?** We do not know yet. That is hypothesis H1 and measured in E1. [SIM] campaign only shows what happens if that is indeed the case: 10,000 of 10,000 single-lane errors corrected, and with C3 zero miscorrections on 10,000 two-lane errors (`results/sim/campaign_s.json`).
3. **Can checkers themselves err due to overclocking?** Checkers, control, memory, and SPI run on `clk_safe` passing STA. Only MAC lanes are accelerated. Checksum lanes are accelerated together; errors there are recognized as a separate class.
4. **What is the end-to-end speedup?** No [HW] number yet. Latency budget shows SPI transmission can dominate, so what will be claimed is accelerator throughput remaining bit-exact, with end-to-end times reported separately.
5. **What is original?** In-place correction instead of recalculation, per-layer clock with in-FPGA governor, and error atlas on Spartan-7, all with the phrase "to the best of our knowledge".
6. **Accuracy is only around 80%?** CIFAR-10 is only a placeholder because target classes have not been announced. What this design guarantees is bit-exact results against the integer model, not highest accuracy.

## 6. Simulated judges' conclusion

Internal score rose from 52.5 to 62.5 [PROPOSAL] because mandatory requirement (synthesis report) is now fulfilled with evidence, and complete design is proven to fit and pass timing on official chip [VIVADO-STA]. The most heavily weighted items, ideas and hardware proof, did not move and cannot move without the board. Order of work that most increases score: MMCM2 sequencer, bring-up and E7 on safe clock, E1 to test H1, then demo with WS2812B and camera.

## 7. Update following round 3 (2026-11-16, after user response)

There is no fourth round; this section only records section 4 weaknesses that changed. Rubric not re-evaluated.

| No | Weakness | Change |
| --- | --- | --- |
| 2 | MMCM2 reconfiguration sequencer does not exist yet | MMCM2 now inside Clocking Wizard v6.0 with AXI4-Lite; `clkwiz_seq` passes bench with register model following PG065 [SIM]. Actual IP behavior only proven on board. |
| 3 | Two closest works not yet read in full | Marty et al. (TCAD 2020) read in full; their reasons for rejecting correction and SENTINEL's answer in `docs/PRIOR_ART.md`. Li et al. (ITC-Asia 2019) still abstract. |
| 6 | No visually apparent demo yet | WS2812B indicator on LED1 shows status via color; START/STOP/RUN buttons can control camera mode. |
| 8 | Host rules for `INJ*` not guarded by hardware | `regfile` discards `INJ*` writes during BUSY [SIM]. |
| 9 | Category, team size, AI rules | 4-person team (matches Japanese page, differs from English page 1–3); official documents contain no AI rules. Category still needs confirmation. |

What remains most heavy: no [HW] results yet, and H1 untested. Board and Raspberry Pi 4 only used starting December 2026 or January 2027.
