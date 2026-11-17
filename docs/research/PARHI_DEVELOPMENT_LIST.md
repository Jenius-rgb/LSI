# Development list from Parhi, *VLSI Digital Signal Processing Systems*

Written 17 Nov 2026 after reading the whole book (chapters 1–18 and appendices A–G; notes in `docs/research/parhi/`).
Book: K. K. Parhi, *VLSI Digital Signal Processing Systems: Design and Implementation*, Wiley, 1999 (year to confirm
against the title page of a licensed copy). Page numbers below are printed book pages.

Nothing here changes SPEC or RTL. Candidates that would change them are proposed as ADRs with status **Diusulkan**
(ADR-028 to ADR-031 in `docs/DECISIONS.md`) and wait for the user's approval.

Labels: [VIVADO] device capacity from the Vivado part database; [VIVADO-STA] static timing or utilization estimate;
[SIM] golden model or RTL simulation; [INFERENCE] reasoning not yet backed by a run; [UNKNOWN] not known yet.

## 1. Baseline the candidates are measured against

| Quantity | Value | Source |
| --- | --- | --- |
| Device capacity | 14,600 LUT, 29,200 FF, 45 BRAM36 tiles, 80 DSP [VIVADO] | `results/vivado/official/summary.json` |
| Official build (model s, K = 8, LUT lanes, C3 on) | 6,851 LUT, 6,149 FF, 2,488/3,650 slices (68.16 %), 14 BRAM tiles, 3 DSP; WNS +0.473 ns at 125 MHz [VIVADO-STA] | same |
| Worst path, `clk_safe_raw` | weight register → C3 checksum-weight tree, 10 logic levels, 7.408 ns [VIVADO-STA] | `results/vivado/official/impl_timing_summary.rpt` |
| Worst path, lane clocks | operand register → LUT multiplier product register, 9 levels, 7.202 ns, 55 % routing [VIVADO-STA] | same |
| Lane array | 1,711 LUT, 1,188 FF (data lanes 113–119 LUT each) [VIVADO-STA] | `impl_utilization_hier.rpt` |
| Ideal cycles per image, model s, K = 8 | 277,504; engine bench mean 277,887 [SIM] | `docs/RESULTS_SIM.md` |
| Lane utilization (MACs / (K × cycles)) | s: 99.86 % at K = 8 and 16; xs: 99.77 % at K = 8, 74.9 % at K = 16 [SIM] | `docs/research/parhi/CH06.md` |
| Operand sets with a zero activation | s: 35.9 % of 277,504; xs: 25.4 % of 83,456 [SIM, first 1000 CIFAR-10 test images] | `results/model/zero_taps_{s,xs}_k8.json` |
| Out-of-context engine, K = 8, C3 on, xc7s25-1 | LUT lanes: 5,717 LUT, Fmax safe 139.1 / lane 148.1 MHz; DSP-min lanes: 4,469 LUT, 14 DSP, 139.2 / 272.9 MHz; DSP-full: 4,471 LUT, 25 DSP, 142.5 / 265.0 MHz [VIVADO-STA] | `fpga/reports/summary.csv` |
| Operand supply limit | lanes can consume at most R·f_safe = 2 × 125 = 250 MHz of operand sets (ADR-013) | `docs/DECISIONS.md` |

Schedule: G1 on 13 Dec 2026, design freeze on 17 Jan 2027, report on 31 Jan 2027; board work from late November or
December depending on power (Q1). Effort figures below are estimates [INFERENCE] in working days for one person.

## 2. Candidates

Each entry: technique (chapter, pages) · SENTINEL module · benefit · resource cost on XC7S25 · effect on bit-exactness
and on the checksum mathematics · contest fit · priority · effort against the schedule.

### D1. Zero-activation skipping — **Should (high value)** → ADR-028

- **Technique:** switching-activity and strength-reduction ideas (ch. 17 pp. 653–654; ch. 9 p. 255), applied to SENTINEL's
  broadcast operand stream (ch. 1, ch. 7 data-broadcast form). Our own combination; not a technique the book states for
  CNNs (`CH17.md` item 2).
- **Module:** `operand_gen` (skip operand sets whose activation is zero; move the first/last-of-unit flags), engine cycle
  accounting and the cycle model (`docs/SPEC.md` 5.4).
- **Benefit:** up to 35.9 % fewer operand cycles for model s and 25.4 % for model xs [SIM]; the real gain is lower by
  pipeline and FIFO effects [UNKNOWN until an RTL bench measures it]. Fewer cycles also means less switching (power).
- **Resource cost:** a zero detector on the 8-bit activation and flag logic: tens of LUTs [INFERENCE]; no BRAM, no DSP.
- **Bit-exact / checksum:** unchanged. A skipped cycle contributes 0 to every data lane and 0 to every checksum lane
  (`wc_c·0 = 0`), so all sums and the identities of SPEC 6 are identical; detection, localization and correction are
  unaffected. Cycle counts become data dependent, so tests that fix `CYCLES_TOTAL` must change by ADR.
- **Contest fit:** speed is shown at the contest ("how fast results come out" [OFFICIAL]); the reason it is safe — the
  broadcast makes skipping invisible to the checksums — is a point for the originality discussion, to be checked against
  `docs/PRIOR_ART.md` before any claim.
- **Effort:** 6–10 days (RTL, golden cycle model, benches incl. all-zero units and padding taps). Fits between G1 and the
  freeze if started right after G1.

### D2. Checksum-weight generator as a flat CSD / MCM tree — **Should (high value, low risk)** → ADR-029

- **Technique:** CSD constant multiplication and tree-height reduction (ch. 13 pp. 505–510), multiple-constant
  multiplication of a constant linear transform (ch. 15 pp. 560–564), carry-save multi-operand addition (ch. 14 p. 530;
  appendix E pp. 758–761), substructure sharing (ch. 9).
- **Module:** `wc_gen` inside `operand_gen` (`u_wc0`, `u_wc1`).
- **Benefit:** wc3 is a signed sum of 14 shifted weights (CSD of k² for k = 1…8); a balanced tree needs about ⌈log₂14⌉ = 4
  adder levels, about 3 with three-input adders [INFERENCE], against the 10 logic levels of today's worst `clk_safe_raw`
  path [VIVADO-STA]. More `clk_safe` margin; possibly a higher f_safe and so a higher operand supply R·f_safe.
- **Resource cost:** about the present 407 LUT of the two wc generators, possibly less with shared terms ([VIVADO-STA] for
  the present figure; the new one [UNKNOWN] until a run).
- **Bit-exact / checksum:** the same integers by construction (identities checked on 1000 random weight vectors,
  `CH15.md`); nothing in the checksum mathematics changes.
- **Contest fit:** robustness of the safe clock (the fallback the error recovery relies on) and timing margin in the official
  report.
- **Effort:** 3–5 days (RTL, an exhaustive or random bench of `wc_gen` against the formula, official rerun).

### D3. Lane implementation: DSP slices instead of LUT multipliers — **Should (decision needed)** → ADR-030

- **Technique:** bit-level multiplier structure (ch. 13), glitch power in multipliers (ch. 17 p. 654), parallelism with
  spare hard multipliers (ch. 3).
- **Module:** `lane_array` (`LANE_IMPL`), already parameterised; DSP variants pass their benches
  (`lane_array_k8_c{0,1}_dsp_{min,full}`, [SIM]).
- **Benefit:** out-of-context, the lane clock's Fmax rises from 148.1 to 272.9 MHz (dsp_min) and LUTs fall by 1,248
  [VIVADO-STA]; DSP use 14 of 80. In the full official flow (side run of 17 Nov 2026) the design drops from 6,851 to 5,550 LUT
  with WNS +0.395 ns at 125 MHz [VIVADO-STA]; details in section 4.
- **Trade-off for the research:** with DSP lanes the lane domain reaches the operand-supply limit (250 MHz) inside its static
  timing, so overclocking up to that limit would produce few or no timing errors. The overclock-with-checksum story then
  needs a higher supply (more operand slots R) or targets the LUT lanes on purpose. This is the user's decision.
- **Bit-exact / checksum:** unchanged (same products, verified in simulation).
- **Contest fit:** speed and area both improve; the research narrative changes.
- **Effort:** 1 day for the switch and reruns; more if R is raised.

### D4. Fine-grain pipelining of the multiplier and the C3 tree — **Could (only if LUT lanes stay)** → ADR-031

- **Technique:** pipelining on feed-forward cutsets (ch. 3 pp. 64–69), fine-grain pipelining (p. 69), folding equation for
  the bookkeeping of all delays (ch. 6 p. 151), and the warning that registers inside a loop change the algorithm (ch. 10
  p. 316).
- **Module:** `lane_lut`, `wc_gen`, the control flags travelling with the products, checker alignment.
- **Benefit:** shorter worst lane path (7.2 ns now) → more static headroom for the lane clock [INFERENCE]; latency + 1 cycle per
  operand stream, negligible against 277,504 cycles.
- **Resource cost:** about one extra register per product bit per lane: roughly 11 lanes × 17 bits ≈ 190 FF [INFERENCE].
- **Bit-exact / checksum:** unchanged if every lane, every checksum lane and the flags get the same stage (cutset rule);
  a partial cut would misalign data and checksum sums.
- **Contest fit:** timing margin; superseded by D3 if DSP lanes are chosen.
- **Effort:** 4–6 days.

### D5. Per-lane operand registers / one broadcast register level — **Should (cheap)**

- **Technique:** broadcast versus systolic data movement (ch. 7 pp. 189–201); register sharing at fan-out (ch. 4 p. 106);
  retiming registers to block glitches (ch. 17 p. 664).
- **Module:** operand registers at the lane array input (attribute such as KEEP or MAX_FANOUT, or one extra register level).
- **Benefit:** the worst lane path is 55 % routing and starts at a register the tool shared between lanes [VIVADO-STA];
  a local register per lane should cut the route part [UNKNOWN until a run]. Matters more at larger K.
- **Resource cost:** tens to about a hundred FF [INFERENCE].
- **Bit-exact / checksum:** unchanged (a feed-forward cutset adds the same latency to every lane).
- **Contest fit:** timing margin; small.
- **Effort:** 1–2 days. An RTL attribute counts as an RTL change, so it waits for approval; it could join ADR-031.

### D6. Report material — **Must (documentation, cheap)**

- **Technique:** iteration bound (ch. 2), clock skew conditions (ch. 16 eqs. 16.2, 16.6), path-delay spread (ch. 16 p. 607),
  roundoff model (ch. 11 eq. 11.9), schedule lower bound (appendix B p. 736).
- **Content for the report:** (1) the critical paths are feed-forward, the accumulator loop sets the floor; (2) overclocking
  can only cause setup (late data) errors, hold is frequency independent; (3) timing errors are data dependent because only
  some operands sensitise the long paths; (4) on-chip cycles and end-to-end time are reported separately; (5) requant
  rounding error ≤ ½ step, variance 1/12 step²; (6) the schedule is at the lane-count bound for model s.
- **Bit-exact / checksum:** no effect. **Effort:** 1–2 days of writing, any time before 31 Jan 2027.

### D7. K = 16 — **Could (not now)**

- **Technique:** parallel processing (ch. 3), null operations in folding sets (ch. 6), memory bandwidth (ch. 18).
- **Facts:** ADR-013 rejected it (f_safe 147.8 → 118.8 MHz OOC, 9.9 % cycle overhead [VIVADO-STA, SIM]); with DSP lanes the
  OOC f_safe is 103–105 MHz [VIVADO-STA]; model xs would use its lanes at 74.9 % [SIM]. Weight path width doubles.
- **Bit-exact / checksum:** unchanged in simulation (`engine_s_k16_n20` passes). **Effort:** reruns only, but the safe-clock
  drop makes it unattractive.

### D8. Winograd-type 2 × 2 tiles for 3 × 3 layers — **Could (evaluated option for the report)**

- **Technique:** Cook–Toom and Winograd fast convolution (ch. 8 pp. 228–244), nesting (iterated convolution, p. 245),
  Euclid's algorithm for the CRT (appendix C), multiplier cost ∝ word length² (ch. 12 p. 450).
- **Benefit:** 16 instead of 36 multiplications per pool window and input channel (2.25×) [INFERENCE from the book's
  4-multiplication short algorithm nested in two dimensions]. The pool window is already the compute and recompute unit.
- **Cost:** transformed operands of about 11–12 bits (LUT multipliers about 2.1× larger, or DSP slices), 16 accumulators per
  lane instead of 1, weight memory × 16/9, a new datapath and memory layout.
- **Bit-exact / checksum:** possible with doubled filter terms and exact division; the checksum identities hold after the
  output transform, but the input transform is outside checksum protection and must run in the safe domain (`CH08.md`).
- **Effort:** weeks; does not fit before the freeze. Report it as an evaluated direction.

### D9. Two operands per lane (unfolding) — **Could**

- **Technique:** unfolding (ch. 5 pp. 119–140). **Benefit:** halves conv cycles if Cin is even, at twice the operand bandwidth
  (two activations and two weight words per cycle) and twice the multipliers. **Bit-exact / checksum:** unchanged (sums are
  associative; checksum lanes take two products too). **Effort:** 1–2 weeks; D1 gives a comparable gain for less.

### D10. Accumulator-loop fallbacks — **Could (only if the loop becomes critical)**

- **Technique:** two partial sums (ch. 2 Fig. 2.3), 2-slow interleaving (ch. 4 p. 99), look-ahead with a = 1 (ch. 10 eq. 10.4),
  carry-save accumulators (ch. 14 p. 530). **Facts:** the accumulator is not on any worst path [VIVADO-STA]. **Bit-exact /
  checksum:** exact integer re-association, unchanged. **Effort:** days each; not needed now.

### D11. Power optimisation run and clock enables for idle lanes — **Could**

- **Technique:** clock gating (ch. 17 pp. 668–669). **Facts:** power is not a listed criterion (`docs/official/README.md`);
  the official report only carries Vivado's power estimate. **Effort:** one run; low priority.

## 3. Evaluation of the themes requested

| Theme | Chapter(s) | Verdict | Entry |
| --- | --- | --- | --- |
| Iteration bound | 2, appendix A | analysis tool; the lane loops are not critical; used for the report | D6, D10 |
| Pipelining and parallel processing | 3, 10 | fine-grain pipelining useful if LUT lanes stay; parallelism via DSP lanes or K | D3, D4, D7 |
| Retiming | 4 | stage balancing of the C3 tree after a timing check; tool retiming option [UNKNOWN] | D2, D4 |
| Unfolding / folding | 5, 6 | SENTINEL is a folded design; folding equation for bookkeeping; unfolding as two operands per lane | D4, D9, D7 |
| Systolic array | 7 | SENTINEL is B2-like with broadcast; full systolic movement not proposed | D5 |
| Fast convolution (Cook–Toom, Winograd) | 8, 9, appendix C | 2.25× fewer multiplications for 3 × 3 tiles; too large before the freeze | D8 |
| Strength reduction | 9, 15 | MCM / CSD sharing in the checksum-weight generator; zero skipping | D2, D1 |
| Scaling and roundoff noise | 11 | SENTINEL already uses worst-case (l1-type) bounds; requant error model for the report | D6 |
| Bit-level, carry-save, redundant arithmetic | 13, 14, appendix E | multi-operand tree for wc; carry-save accumulators only as fallback | D2, D10 |
| CSD | 13, 15 | wc2/wc3 constants in CSD (14 terms for wc3) | D2 |
| Clocking styles, clock skew, wave pipelining | 16 | setup-only error model under overclock; wave pipelining and asynchronous pipelines unsuitable for FPGA | D6 |
| Low power | 17 | no voltage changes allowed; zero skipping and DSP lanes reduce switching; clock-enable run optional | D1, D3, D11 |

## 4. Experiments approved by the user (17 Nov 2026)

| Experiment | Command | Result |
| --- | --- | --- |
| Official flow with DSP-min lanes (side run, official folder untouched) | `python tools/run.py synth-official --lane-impl dsp_min --tag dspmin` | 5,550 LUT (official LUT lanes: 6,851), 5,307 FF (6,149), 2,011 slices (2,488), 14 BRAM tiles (14), 14 DSP (3); WNS +0.395 ns (+0.473), WHS +0.049 ns (+0.027) at 125 MHz [VIVADO-STA], `results/vivado/official_dspmin/`. The multiplier is no longer among the worst paths: the lane clocks are now limited by the `acc_last` flag fanning out to the hold registers (1 logic level, 89 % routing, slack +0.697 ns) and `clk_safe_raw` by the safe reset fanning out to the injection registers (0 levels, 94 % routing, +0.395 ns). Both are high-fan-out nets that register replication (D5-type) would address. |

## 5. Not proposed (with the reason)

| Technique | Chapter | Reason |
| --- | --- | --- |
| Relaxed look-ahead, approximate processing | 10, 17 | change results; SENTINEL must be bit-exact (`CLAUDE.md` §4) |
| Supply-voltage scaling, multiple supplies, multi-V_t | 3, 17 | `CLAUDE.md` §8 forbids changing voltages; VCCINT is fixed by the board |
| Wave pipelining, asynchronous pipelines | 16 | need equal, data-independent delays or delay matching that FPGA routing cannot guarantee |
| Distributed arithmetic | 13 | needs constant coefficients; weights are reloaded at run time |
| Bit-serial / digit-serial lanes | 5, 13, appendix F | trade lanes for cycles; would touch every bench before the freeze |
| Fully systolic data movement | 7 | skews data and checksum lanes against each other; little gain at K = 8 |
| FFA tiles | 9 | 25/36 multiplications for 3 × 3 tiles, dominated by Winograd-type tiles (16/36) |
| Packing two INT8 products per DSP slice | 18 | 77 of 80 DSP slices are free; no need |
| Narrower accumulators, modular checksums | 11, 13 | small gain; localization needs true values; must cover every model loaded without resynthesis |
| Power-of-two (SPT) weights | appendix G | changes the trained model and the golden model |
