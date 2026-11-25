# SPEC — SENTINEL v0.1 (pre-board)

Date: 2026-11-09. Status: initial proposal. Any change made via ADR in `docs/DECISIONS.md`.
Updated 2026-11-16 via ADR-013 through ADR-020, after organizers published official chip and ZERO7 documents.
§7.8 expanded 2026-11-16 via ADR-021, after first complete implementation on official chip. §7.6 and §12.4 updated via ADR-023; Raspberry Pi 4 host via ADR-022, replaced by the Raspberry Pi 5 host via ADR-033 (25 Nov 2026). JTAG probe via ADR-034, camera via ADR-035.
Sections marked **(normative)** must be followed exactly by golden model and RTL.

---

## 0. Summary

SENTINEL is an INT8 CNN accelerator on Spartan-7 with **K parallel MAC lanes**. Each lane computes one output channel.

- MAC lanes reside in a **fast clock domain** that can be overclocked per layer.
- Two checksum lanes compute C1 = Σ_k W_k ∗ X and C2 = Σ_k k·W_k ∗ X. A third lane, C3 = Σ_k k²·W_k ∗ X, is optional.
- Single-lane errors are detected, localized, and accurately corrected. Errors that cannot be corrected are recalculated on safe clock.
- A **hardware governor** selects the clock for each layer.
- All memories, control, comparators, and governor reside in a **safe clock domain** that passes timing.

---

## 1. Global parameters (`config/*.yaml`)

| Name | Default | Meaning |
| --- | --- | --- |
| `K` | 8 | number of data lanes (8 or 16) |
| `R` | 2 | number of operand sets produced by safe domain per `clk_safe` cycle |
| `C3_EN` | 0 | third checksum lane (synthesis parameter) |
| `LANE_IMPL` | `lut` | `lut`, `dsp_min` (minimal DSP pipeline registers), or `dsp_full`. The `lut` lane registers the two activation-nibble products before their sum and keeps one activation register per lane (ADR-031 (c)): four stages (operands, nibble products, product, accumulator) |
| `ACT_W` | 8 | activation width, unsigned |
| `W_W` | 8 | weight width, signed, values −127..127 |
| `ACC_W` | 32 | data lane accumulator width |
| `ACC_CS_W` | 48 | checksum lane accumulator and d1/d2/d3 width |
| `N_LOG` | 256 | capacity of failed unit log per layer |
| `MODEL` | `s` | CNN architecture (`s` or `xs`) |
| `N_CLASSES` | 10 | number of classes (CIFAR-10 as temporary placeholder) |
| `N_CLASSES_MAX` | 16 | upper bound of classes supported by hardware without resynthesis (layer table loaded at runtime) |
| `IN_CH` | 3 | input channels (RGB) |
| `INJ_EN` | 1 | fault injection logic synthesized |
| `ZERO_SKIP` | 0 | 0: off. 1: operand sets with activation 0 are not sent to the lanes, except a set that closes a unit or opens a pass, and every unit keeps at least K + 2 + C3 sets (§5.4). 2: the same skipping with unit ends spaced by a stall in `fast_path` instead (comparison variant). Synthesis parameter (ADR-028); flag bit 4 of the ID word is set for 1 and 2 |

Official variant for ZERO7 and synthesis report is in `config/hw_zero7.yaml`: K = 8, R = 2, `C3_EN = 1`, `LANE_IMPL = lut`, model `s4` (ADR-013; model `s` until ADR-037). The bitstream does not depend on the model: weights are loaded over SPI.

---

## 2. CNN Model

[OFFICIAL] Input 32×32. Level 3 free.
[HISTORICAL] Specification of 23rd contest uses convolution, max pooling, sigmoid/ReLU activation, and fully connected.

### 2.1 Variant `s` (default; official variant for XC7S25CSGA225-1)

| Layer | Operation | Output | Weights | MACs |
| --- | --- | --- | --- | --- |
| conv1 | 3×3, 3→16, same, ReLU, maxpool 2×2 | 16×16×16 | 432 | 442,368 |
| conv2 | 3×3, 16→32, same, ReLU, maxpool 2×2 | 8×8×32 | 4,608 | 1,179,648 |
| conv3 | 3×3, 32→32, same, ReLU, maxpool 2×2 | 4×4×32 | 9,216 | 589,824 |
| fc | 512→N | N | 5,120 (N = 10) | 5,120 |
| **Total** | | | **19,376 + 90 biases** | **2,216,960** |

### 2.2 Variant `xs` (small variant, used for fast regression)

| Layer | Operation | Output | Weights | MACs |
| --- | --- | --- | --- | --- |
| conv1 | 3×3, 3→8 | 16×16×8 | 216 | 221,184 |
| conv2 | 3×3, 8→16 | 8×8×16 | 1,152 | 294,912 |
| conv3 | 3×3, 16→16 | 4×4×16 | 2,304 | 147,456 |
| fc | 256→N | N | 2,560 | 2,560 |
| **Total** | | | **6,232 + 50 biases** | **666,112** |

Numbers above calculated manually. `model/arch_report.py` must recompute from config, and that script's output is the reference.


### 2.3 Variant `s4` (official contest classes, ADR-037)

The architecture of `s` (§2.1) with a 4-output fully connected layer (512 → 4, 2,048 weights). Classes in the official
order: cat = 0, dog = 1, deer = 2, horse = 3 [OFFICIAL, Design Specification §4]. Trained on the CIFAR-10 images of these
four classes (dataset `cifar10_4`); `model/arch_report.py` gives the exact counts.
---

## 3. Integer arithmetic (normative)

`model/golden.py` implements this section exactly, using NumPy int64. RTL must be bit-exact with the golden model.

### 3.1 Representation

- **Activation** `a`: uint8 [0, 255], including raw input pixels. Real value = a · S_a.
- **Weight** `w`: int8 [−127, 127]. Value −128 is not used.
- **Bias** `b`: int32, with scale S_in · S_w.
- Tensor order (C, H, W). Flatten before FC: i = c·H·W + y·W + x.

### 3.2 Convolution

Stride 1, kernel 3×3, padding "same" with zero:

```
acc[o,y,x] = Σ_{c=0..Cin-1} Σ_{i=0..2} Σ_{j=0..2}  w[o,c,i,j] · a[c, y+i-1, x+j-1]
```

Value of a outside boundaries is taken as 0. This is cross-correlation, identical to `torch.nn.Conv2d(padding=1)`, without flipping kernel.

### 3.3 Conv post-processing

```
v = acc + b[o]
q = (v · M + 2^(n-1)) >> n        # arithmetic right shift; if n = 0, without rounding term
y = min(max(q, 0), 255)           # simultaneously functions as ReLU
```

M is uint16 (1..65535) and n is 0..31, per layer. Per-channel scaling may be adopted via ADR.

### 3.4 MaxPool

MaxPool 2×2 with stride 2, applied to y (uint8). Requant is monotonically increasing (M > 0), so pooling after requant produces identical results to pooling before requant.

### 3.5 Fully connected and argmax

```
z[o] = Σ_i w[o,i] · a[i] + b[o]   # int32, without requant
```

Class is the **smallest index o** having maximum z.

### 3.6 Bit bounds

Export script must compute worst-case bounds |acc| for each layer, then verify with assert:

- |acc| ≤ 2^(ACC_W−1) − 1,
- |S_c| (checksum accumulator) ≤ 2^(ACC_CS_W−1) − 1,
- |v · M| does not overflow on the width used by RTL.

---

## 4. Training and quantization

- **Temporary dataset**: CIFAR-10 (torchvision). Input normalized as x/255 only, without mean/std, so integer inputs equal raw pixels.
- **BatchNorm** may be used during training, but must be folded into weights and biases prior to quantization.
- **Quantization**:
  1. Start with PTQ: calibrate with 1,000 training images, S_out = 99.99th percentile of activations divided by 255.
  2. If integer model accuracy drops by more than 2 percentage points from float, try QAT (fake-quant with STE) or per-channel scaling. Record decision in ADR.
- **Selection of M and n**: n chosen as large as possible such that M = round(ratio · 2^n) ≤ 65535, with ratio = S_in·S_w / S_out.
- **Export outputs** (`model/export.py`):
  - `build/weights/<model>.bin` and `manifest.json`, with byte order exactly matching RTL memory,
  - `.mem` files for `$readmemh` in simulation,
  - per-layer requant parameters,
  - report of float vs integer accuracy in `results/model/`.
- **Target classes** from organizers not yet announced [UNKNOWN]. Training must support folder datasets (ImageFolder format) and arbitrary N_CLASSES, allowing retraining for other classes simply by changing dataset configuration. New weights loaded via SPI without resynthesis, as long as convolution architecture is identical and N_CLASSES ≤ N_CLASSES_MAX.

---

## 5. Dataflow and schedule

### 5.1 Lane mapping

Lane k (k = 1..K) computes output channel o = g·K + (k−1) for group g. If Cout is not a multiple of K, residual lanes use zero weights.

### 5.2 Output-stationary

For each compute unit, lanes accumulate over T cycles:

- conv: T = Cin · 9,
- FC: T = N_in.

Each cycle, all lanes receive one **operand set**: {a (1 byte, broadcast), w_1..w_K, wc1, wc2, (wc3)}.

### 5.3 Conv loop order

```
for g in groups:
  for window in pool_windows (raster):
    for (dy,dx) in [(0,0),(0,1),(1,0),(1,1)]:
      for c, i, j:  (Cin × 3 × 3)
```

- **Compute unit** = one output position × one group.
- **Recompute unit** = one pool window × one group, consisting of 4 compute units.
- For FC, compute unit and recompute unit are both one group.

### 5.4 Cycle model

```
siklus_ideal = Σ_conv (H_out · W_out · G · Cin · 9) + Σ_fc (G · N_in)
```

H_out·W_out calculated before pooling. For variant `s` with K = 8: 277,504 cycles, ~2.78 ms at 100 MHz. Simulation must report actual cycles and difference against this model. Target overhead ≤ 10%.

---

## 6. Checksum (normative)


**Result serializer spacing.** The lane array sends K + 2 + C3 result words per unit (K data lanes, 2 or 3 checksum lanes), one per `clk_fast` cycle, so consecutive units must end at least K + 2 + C3 cycles apart. Without zero-skip a unit lasts t cycles, and the shortest t in every model is 27 (first convolution, C_in = 3), above the 19 needed at K = 16 with C3 (`tests/test_tools.py::test_every_unit_is_long_enough_for_the_result_serializer`). A model with t < K + 2 + C3 (for example a one-channel 3×3 layer, t = 9) would break this rule even with `ZERO_SKIP = 0`.

With `ZERO_SKIP` = 1 or 2 (ADR-028) the lane-side cycle count becomes data dependent: ideal cycles minus the operand sets with a zero activation that neither close a unit nor open a pass. Unguarded skipping lets units end closer than K + 2 + C3 cycles apart and overruns the serializer (seen on verification images 118 and 198, ADR-028 results). `ZERO_SKIP = 1` keeps zero sets near the end of a unit when fewer than K + 2 + C3 sets would remain; `ZERO_SKIP = 2` holds a unit-closing word in `fast_path` until K + 3 + C3 cycles have passed since the previous one. The safe side still scans every tap at R sets per `clk_safe` cycle, so the gain is bounded by min(1/(1 − z), R·f_safe/f_lane), with z the dropped fraction [INFERENCE]. Sums and checksum identities (§6) are unchanged because every dropped product is 0 in every lane.
### 6.1 Checksum weights, computed on-the-fly

Checksum weights are computed in the **safe domain**, from the same K weights sent to data lanes:

```
wc1 = Σ_{k=1..K} w_k        wc2 = Σ k · w_k        wc3 = Σ k² · w_k
```

| K | max \|wc1\| | max \|wc2\| | max \|wc3\| |
| --- | --- | --- | --- |
| 8 | 1,016 (11-bit signed) | 4,572 (14-bit) | 25,908 (16-bit) |
| 16 | 2,032 (12-bit) | 17,272 (16-bit) | 189,992 (19-bit) |

Checksum lane c computes S_c = Σ_t wc_c(t) · a(t).

Without errors, the following identities hold, with Y_k as data lane k accumulator before bias:

- S1 = Σ Y_k,
- S2 = Σ k·Y_k,
- S3 = Σ k²·Y_k.

These identities are exact in integer arithmetic as long as overflow does not occur, guaranteed by §3.6.

**Rationale for computing on-the-fly**: requires no additional BRAM, and safe domain passes timing so wc is always correct. Data lane weights corrupted after leaving safe domain are still detected.

### 6.2 Comparator decision

Implemented in `model/checker.py`, and RTL must be identical:

```
def check(Y, S1, S2, S3, mode, c3_en, trust_csum_lane):
    # Y[1..K] = data lane accumulators; S1, S2, S3 = checksum lane accumulators
    d1 = sum(Y[k] for k in 1..K) - S1
    d2 = sum(k * Y[k] for k in 1..K) - S2
    d3 = (sum(k*k * Y[k] for k in 1..K) - S3) if c3_en else 0

    if mode == UNPROTECTED:
        return NONE, Y
    if mode == DETECT_C1_RECOMPUTE:          # baseline a la Marty et al.
        return (RECOMPUTE if d1 != 0 else CLEAN), Y

    # mode == CORRECT (SENTINEL)
    if d1 == 0 and d2 == 0 and d3 == 0:
        return CLEAN, Y
    if d1 != 0:
        for j in 1..K:
            if d2 == j * d1 and (not c3_en or d3 == j*j * d1):
                Y[j] = Y[j] - d1
                return CORRECTED(j), Y
    if trust_csum_lane:
        if d1 != 0 and d2 == 0 and d3 == 0:           return CSUM_LANE(1), Y
        if d1 == 0 and d2 != 0 and d3 == 0:           return CSUM_LANE(2), Y
        if c3_en and d1 == 0 and d2 == 0 and d3 != 0: return CSUM_LANE(3), Y
    return RECOMPUTE, Y
```

- Lane indexing begins at 1, not 0. With weight 0, an error in C1 lane would be mistaken for a data lane error.
- Default `trust_csum_lane = 0` (conservative). Without C3, pattern d2 = 0 can also originate from mutually cancelling multi-lane errors. Example: +2 on lane 1 and −1 on lane 2 yields d1 = 1 and d2 = 0.

### 6.3 Searching for j

May be sequential (K cycles, accumulating d1) or combinational. Dividers must not be used. Results must be identical to pseudo-code above, with documented latency.

### 6.4 Correction

Y_j ← Y_j − d1 computed in ACC_CS_W bits, then truncated to ACC_W with assert that overflow does not occur.

### 6.5 Coverage and limitations

This section must be written honestly in the report.

- **Checksums protect MAC calculations, not inputs.** Errors in activation a broadcast to all lanes after leaving safe domain are undetected. Mitigations are threefold:
  - operand paths in fast domain made short and given extra registers (§7.4),
  - operand parity bits (optional),
  - end-to-end SDC (silent data corruption) measurement against golden model in every experiment.
- **Multi-lane errors** can escape or be miscorrected. Rates measured in M3 and M9.

---

## 7. Clock domains and CDC

### 7.1 `clk_safe`

Contains BRAM, control, SPI, operand and wc generator, comparator and corrector, post-processing, pooling, governor, and counters. Must pass timing (WNS ≥ 0) at f_safe.

### 7.2 `clk_fast`

Contains data lanes, checksum lanes, result holding registers, result serializer, operand FIFO read side, and result FIFO write side.

`clk_fast = BUFGCTRL(clk_safe, clk_turbo)`.

### 7.3 Asynchronous FIFOs

`cdc_fifo` wrapper has two implementations:

- `xpm_fifo_async` for Vivado (see UG953),
- behavioral model with Gray-code pointers for portable simulation.

Two FIFOs used:

- **Operand FIFO**: write width R × set, read width 1 × set. Alternatively R parallel FIFOs read in rotation.
- **Result FIFO**: results of one unit serialized into K + 2 (+1) words of width ACC_CS_W bits. Requirement is K + 3 ≤ T. For conv1, T = 27.

Lane accumulators have holding registers, so subsequent unit can start immediately while prior unit results serialize.

### 7.4 Critical path principle

In fast domain, MAC and accumulator paths must be the critical path. All non-MAC paths (operands from FIFO to lanes, control, serializer) given additional registers until slack is at least 30% greater than worst MAC path. Verified in Vivado timing report (M11).

### 7.5 Operand supply

Requirement is R · f_safe ≥ f_turbo_max. Cycles when operand FIFO is empty counted by `STARVE_CYCLES`.

### 7.6 Clock generation (`clk_gen` wrapper)

**Xilinx implementation:**

- **MMCM1** generates `clk_safe` from F_IN.
- **MMCM2** generates `clk_turbo` from F_IN, with frequency changeable via dynamic reconfiguration.
- **BUFGCTRL** (UG472) selects clock for `clk_fast`.

**MMCM2 reconfiguration:**

- Primary choice: Clocking Wizard with dynamic reconfiguration via AXI4-Lite (PG065), using simple AXI-Lite master.
- Alternative: direct DRP per XAPP888.
- Choice recorded via ADR.
- Plan B: MMCM2 with multiple fixed CLKOUTs plus mux, without reconfiguration.

**Turbo frequency table** generated by `tools/gen_mmcm_table.py` from F_IN and datasheet limits. Limits for VCO, PFD, and input for speed grade used taken from DS189, with values and page numbers cited. F_IN = 20 MHz on pin B13 [OFFICIAL] (ADR-015). Limits taken from DS189 Table 37, PDF p. 40 (ADR-023). MMCM2 reconfigured via Clocking Wizard v6.0 with AXI4-Lite: registers 0x200 and 0x208, wait for SR bit 0, write 0x25C = 0x3, wait for lock (PG065; ADR-023).

**Simulation implementation:** behavioral clock with changeable period, and glitch-free mux model.

### 7.7 Clock switching protocol (normative)

1. `sel` only changes when fast domain is idle: between layers, or before and after recompute pass.
2. Before MMCM2 reconfiguration: set `sel = safe` and wait for switch confirmation. Only then reconfigure, then wait for `LOCKED = 1`. Afterwards `sel = turbo` may be used again.
3. Reconfiguration performed only between images.

### 7.8 Constraints and clock domain crossings

- `clk_safe` and `clk_fast` are asynchronous clock groups.
- Two clocks at BUFGCTRL output are physically exclusive.
- XPM constraints applied automatically.
- For OOC: `create_clock` on clock ports with target period.

**Reset (ADR-021).** Power-on reset generated in board clock domain. That reset and LOCKED MMCM1 each enter `clk_safe` via two-flop synchronizer with no preceding logic, then merged with soft reset and pass through two more flops; final flop drives reset net. Path from board clock to first synchronizer stage is false path; no other timing exceptions. `clk_fast` reset derived from `clk_safe` reset via two-flop synchronizer followed by single driving flop.

**Permitted crossings (ADR-021).** Every synchronizer given `ASYNC_REG` attribute. Signals outside this table must not cross.

| Signal | Direction | Method |
| --- | --- | --- |
| operands and results | `clk_safe` ↔ `clk_fast` | XPM asynchronous FIFO |
| reset | `clk_safe` → `clk_fast` | two-flop synchronizer |
| `pass_active` | `clk_safe` → `clk_fast` | two-flop synchronizer |
| injection config (`INJ*`), layer index | `clk_safe` → `clk_fast` | quasi-static: changes only when fast domain is idle |
| `STARVE_CYCLES` | `clk_fast` → `clk_safe` | quasi-static: read only when `STATUS.BUSY` = 0 |
| clock selector `sel` | `clk_safe` → BUFGCTRL | sequence §7.7 |
| SPI pins | external → `clk_safe` | two-flop synchronizer |
| LOCKED MMCM1 and MMCM2 | asynchronous → `clk_safe` | synchronizer |

**Host rules, guarded by hardware.** `INJ*` registers only written when `STATUS.BUSY` = 0; `regfile` discards writes to `INJ*` while BUSY = 1 (`tb/tb_regfile_guard.v`).

**Reports.** Official report flow executes `report_cdc` and `report_bus_skew`; crossing counts per class recorded in `results/vivado/official/summary.md`.

---

## 8. Operating modes (`CTRL.MODE` register)

| Value | Name | Behavior |
| --- | --- | --- |
| 0 | `UNPROTECTED` | without check, results used as-is |
| 1 | `DETECT_C1_RECOMPUTE` | baseline a la Marty et al.: d1 ≠ 0 → recompute |
| 2 | `CORRECT` | SENTINEL, per §6.2 |

All three present in same bitstream for fair E4 comparison. For area comparison, build synthesis variant without C2.

---

## 9. Recompute

1. While layer runs in turbo, recompute units with RECOMPUTE status logged (capacity N_LOG).
2. After layer completes: `sel = safe` (§7.7). All logged units recalculated, then outputs rewritten after post-processing and pooling. Subsequent layer begins only afterwards.
3. Comparator remains active during recompute pass. If results on safe clock are still not CLEAN, set `FATAL` flag, indicating bug or non-timing error.
4. If log full, entire layer repeated on safe clock and `LOG_OVF` counter incremented.

---

## 10. Governor (initial normative)

Reference model is `model/governor.py`.

**State**: level L (turbo frequency table index), `turbo_en[l]` per layer, `cool[l]`, and `clean_streak`.

**Parameters (registers)**: `N_UP`, `COOLDOWN`, `CORR_HI`, `L_MIN`, `L_MAX`, `AUTO`.

**At end of each image:**

```
any_fail = False
for l in layers:
    if fails[l] > 0:
        turbo_en[l] = 0; cool[l] = COOLDOWN; any_fail = True
    elif not turbo_en[l]:
        if cool[l] > 0: cool[l] -= 1
        if cool[l] == 0: turbo_en[l] = 1
corr = sum(corrected[l] for l in layers)
if any_fail or corr > CORR_HI:
    L = max(L - 1, L_MIN); clean_streak = 0
else:
    clean_streak += 1
    if clean_streak >= N_UP:
        L = min(L + 1, L_MAX); clean_streak = 0
```

- Change in L implies MMCM2 reconfigured per §7.7 before next image.
- **Manual mode** (`AUTO = 0`): L and `turbo_en` written by host. This mode used for E1 sweep.
- RTL governor must produce state trajectories identical to Python model for identical event sequences.
- Policy may be revised via ADR, provided Python model and RTL are updated concurrently.

---

## 11. Fault injection

### 11.1 Hardware

Synthesizable, active if `INJ_EN = 1`. Two injection slots, INJ0 and INJ1. Each slot has fields:

- `LAYER`,
- `UNIT` (compute unit index within layer, or ANY),
- `LANE` (1..K for data lanes; K+1..K+3 for checksum lanes),
- `MASK` (ACC_CS_W bits),
- `ONESHOT`.

Effect: holding register on selected lane XORed with MASK (truncated to lane width) when unit matches. This injection passes through FIFO, serializer, and comparator, exactly like genuine timing errors.

### 11.2 Semantics in Python model

Injection semantics identical in `model/checker.py`, so RTL outcomes can be predicted.

### 11.3 Synthetic timing error model

`model/fault_model.py` for development only, results always labeled `[SYNTHETIC]`.

- Each lane has f_onset_k deterministic from seed.
- Layer effect: f_onset_kl = f_onset_k · (1 + γ · s_l), with s_l = activation sparsity of layer l input. This is assumption H3; γ may be 0.
- Error probability: p(f) = 0 if f ≤ f_onset_kl, otherwise min(1, ((f − f_onset_kl)/Δ)^α).
- Deterministic error decision: error occurs if hash(seed, image_id, layer, unit, lane, f) < p(f). Mimics H2.
- Error value: single-bit XOR, selected with bias toward MSB of active range of true accumulator value. Mimics Chamberlin et al. (2024) finding that upper bits fail first.
- All parameters recorded in results metadata.

---

## 12. Host interface (SPI)

### 12.1 Physical

- SPI mode 0 (CPOL = 0, CPHA = 0), MSB first, active-low CS.
- FPGA acts as slave with oversampling in `clk_safe` (2-FF synchronizer).
- Guaranteed operational for f_SCLK ≤ f_safe / 8.
- Pins: Raspberry Pi SPI0 with CE0: SCLK A8, MOSI A6, MISO A7, CS D9 [OFFICIAL]. Done signal `irq_done` on RP_GPIO25, pin C9 (ADR-016).
- WS2812B LED1 indicator on pin N1 (ADR-017), driven by `status_led` in `clk_safe` domain: red FATAL, magenta busy in turbo, blue busy, green done, dim white idle. Pulse timing (T0H 400 ns, T1H 800 ns, bit 1,250 ns, latch reset 300 µs) not yet checked against ZERO7 LED datasheet.
- Voltage levels not yet written in official documents [UNKNOWN]; see `board/BOARD_INFO.md`.

### 12.2 Commands

| Byte | Format | Function |
| --- | --- | --- |
| `0x02` WRITE | `[0x02][A23:16][A15:8][A7:0][data…]` | write, auto-incrementing byte address |
| `0x03` READ | `[0x03][A23:16][A15:8][A7:0][dummy]` then data out on MISO | read, auto-increment |
| `0x9F` ID | 8 bytes out | `"SNTL"`, major version, minor version, K, flags (bit 0 C3, bit 1 INJ, bits 3:2 lane implementation, bit 4 ZERO_SKIP) |

### 12.3 Address map

24-bit byte address. Source of truth is `spec/regmap.yaml`.

| Range | Contents |
| --- | --- |
| `0x000000–0x000FFF` | 32-bit little-endian registers |
| `0x010000–` | weight memory |
| `0x020000–` | bias, requant parameters, layer table |
| `0x030000–` | IMG0 (3,072 B) |
| `0x034000–` | IMG1 |
| `0x040000–` | logits (int32 × N) |
| `0x050000–` | event log (optional) |

### 12.4 Initial registers

May be extended. Final names in YAML.

- `ID`, `VERSION`
- `CTRL`: `START`, `SOFT_RESET`, `MODE[1:0]`, `C3_EN`, `TRUST_CSUM_LANE`, `IMG_SEL`
- `STATUS`: `BUSY`, `DONE`, `FATAL`, `LOG_OVF`, `MMCM2_LOCKED`, `FAST_IS_TURBO`
- `RESULT_CLASS`, `CYCLES_TOTAL`, `CYCLES_RECOMPUTE`, `STARVE_CYCLES`
- `GOV_CTRL` (`AUTO`, `LEVEL`, manual `TURBO_MASK`), `GOV_PARAM` (`N_UP`, `COOLDOWN`, `CORR_HI`, `L_MIN`, `L_MAX`), `GOV_STATE`
- `CLK_CTRL` and `CLK_STATUS` for reconfiguration
- `INJ0_*`, `INJ1_*`
- Per-layer counters: `UNITS`, `CLEAN`, `CORRECTED`, `CSUM_LANE`, `RECOMPUTE`, `FATAL`
- Per-lane correction counters, and `LANE_STATUS` (for LEDs)
- `TEMP`: 12-bit temperature code from XADC in bits [11:0] and valid bit in bit 16 (ADR-018, ADR-023). Temperature °C = code × 503.975 / 4096 − 273.15 (UG480 Eq. 2-6), computed in software.

### 12.5 Image format

32×32×3 uint8, order (C, H, W), identical to golden model. Ping-pong: host writes IMG(1−sel) while engine processes IMG(sel).

### 12.6 Protocol co-simulation

Python driver can write transaction byte logs. Testbench replays that log to RTL SPI slave, then compares responses against driver expectations.

---

## 13. Verification

### 13.1 Oracles

Integer golden model (`model/golden.py`), checker model, and governor model.

### 13.2 Vectors

Generated with fixed seed into `build/vectors/`. Not committed; `run.py gen` regenerates them.

### 13.3 Verification levels

- **L0 (pytest)**:
  - requant: rounding at .5, negative values, saturation 255, n = 0,
  - padding, flatten, argmax with tied values,
  - complete checker decision table plus property tests,
  - bit bounds.
- **L1 (RTL TB units)**: lane (every `LANE_IMPL`), lane array, operand and wc generator, checker, post-processing, pooling, `cdc_fifo` (random clock ratios), SPI slave.
- **L2**: single conv layer compared against golden.
- **L3**: single-clock engine; logits and class bit-exact for ≥ 200 images.
- **L4**: system with SPI and dual clock domains (ratio f_fast/f_safe ∈ {1.0, 1.3, 1.7, 2.0}), plus injection.
- **L5**: governor, ≥ 50 scenarios compared against Python model.

### 13.4 Mandatory corner cases

- Cin = 3,
- groups with zero-weight lanes,
- extreme values (a = 255, w = ±127),
- all-zero images,
- saturation,
- ties in pooling and argmax,
- full log,
- FATAL path.

### 13.5 Simulators

- **Icarus**: primary simulator, portable.
- **xsim**: reference, for XPM and unisim.
- **Verilator**: mandatory lint if available; optional fast simulation.

---

## 14. FPGA non-board flow (OOC)

- **Programming and debug** (ADR-034): SEGGER J-Link through the J-Link XVCD Server (Vivado "Add Xilinx Virtual Cable", localhost:2542), openFPGALoader `-c jlink` as programming fallback; untested until the board phase (`docs/JLINK_VIVADO.md`).

- **`fpga/ooc.tcl`** executes:
  - `synth_design -mode out_of_context`, then opt, place, route,
  - `report_utilization -hierarchical`, `report_timing_summary`,
  - `report_timing -max_paths 20` per clock,
  - `report_power` (labeled vectorless estimate).
- **Parts**: official target `xc7s25csga225-1` (ADR-013). M11 matrix for other parts and speed grade −2 is comparison data only.
- **`fpga/synth_official.tcl`** (ADR-014) implements complete `top_board` design with `board/zero7.xdc` and saves official reports in `results/vivado/official/`.
- **Variants**: K ∈ {8, 16}, `LANE_IMPL` ∈ {lut, dsp_min, dsp_full}, `C3_EN` ∈ {0, 1}.
- **Mandatory analysis**:
  - fast domain STA Fmax for each variant, and safe domain Fmax,
  - 20 critical paths of fast domain must be MAC paths,
  - slack gap between MAC and non-MAC paths (§7.4),
  - resource fit per part (BRAM36, DSP, LUT, FF).
- **`tools/fit_report.py`** estimates BRAM and DSP requirements from config before running Vivado. In XC7S25, `engine` module variant `s` with K = 8 uses 14 of 45 block RAMs [VIVADO-STA].
- All numbers labeled `[VIVADO-STA]`. STA is conservative; real failure frequencies can only be measured on board.
- If Vivado unavailable in this environment: create scripts and instructions, mark "requires user run", then save returned reports to `fpga/reports/`.

---

## 15. Raspberry Pi software and experiment harness

- **Package `sw/sentinel/`**:
  - `regmap.py` (generated), `driver.py`,
  - transport: `SpidevTransport` (for board) and `LogTransport` (for co-simulation),
  - backend: `HwBackend` and `MockBackend`. MockBackend uses golden, checker, governor, and synthetic fault models, with identical API to HwBackend.
- **Host** (ADR-033): Raspberry Pi 5; SPI through `spidev`, GPIO through gpiozero with the lgpio pin factory (`sentinel.transport.lgpio_factory`).
- **Camera** (ADR-035): only on the Raspberry Pi, never on the FPGA; source `picamera` (CSI), a camera index (USB) or a video file.
- **`camera.py`** (picamera2 or OpenCV) and **`preprocess.py`** (center-crop → resize 32×32 with INTER_AREA → RGB uint8 (C, H, W)). Identical functions used for camera data during fine-tuning.
- **Dashboard** (lightweight web or OpenCV window) displays camera, class, FPS, turbo frequency, turbo layers, counters, and lane map. Runnable with MockBackend on PC.
- **Validation mode** [OFFICIAL: validation data provided on contest day via camera, SD card, etc.]: read all images in a folder, classify, then report accuracy (if labels available), latency per image, and FPS. FPGA compute time (from `CYCLES_TOTAL`) and end-to-end time reported separately. With labels in subfolders (`<folder>/<class>/`), labels follow the class order of the model (`classes` in `config/model_<name>.yaml`, copied into the weight manifest; `s4`: cat = 0, dog = 1, deer = 2, horse = 3), not the alphabetical folder order (ADR-037).
- **Camera mode** [OFFICIAL: real-time camera input]: continuous classification displaying recognition speed.
- **Experiments** `sw/sentinel/experiments/e1.py` through `e8.py`. Output to `results/<backend>/<exp>/<timestamp>/`:
  - `data.csv`,
  - `metadata.json`: git hash, config, backend, bitstream id, tool versions, fault model parameters.
- **Plots** in `sw/sentinel/plots/` read CSV. If backend = mock, watermark "SYNTHETIC — NOT MEASURED" is mandatory.
- Every HW result compared per image against golden model (`logits_match` column). Any mismatch counted as SDC.

---

## 16. Experiments

| ID | Question | Success criteria [PROPOSAL] | Before board |
| --- | --- | --- | --- |
| E1 | Error atlas (frequency sweep, 5 MHz steps); tests H1 | ≥ 90% error occurrences at lowest 3 error frequencies affect only single lane | script tested with mock |
| E2 | Are errors deterministic? (H2) | ≥ 95% repetitions yield identical error patterns | script tested with mock |
| E3 | Per-layer error onset (H3) | deep layers begin erroring ≥ 10% higher than layer 1 | script tested with mock |
| E4 | Three modes: throughput and accuracy vs frequency | maximum bit-exact throughput mode 2 ≥ 1.2× mode 1 and ≥ 1.4× timing-passing baseline | script tested with mock |
| E5 | Fault injection: coverage and miscorrections | 100% single-lane errors corrected; two-lane rate reported | **full [SIM]** (Python and RTL) |
| E6 | Governor and temperature | frequency tracks temperature without incorrect results | script tested with mock |
| E7 | Bit-exact on validation set | 100% classes and logits identical | [SIM] in RTL |
| E8 | Cost: resources, power, net benefit | positive net benefit | **[VIVADO-STA]** |

Hypotheses H1–H3 may be incorrect. Negative results honestly measured are still reported.

---

## 17. Repo structure

```
sentinel/
  CLAUDE.md  STATUS.md  README.md  requirements.txt
  config/              model_s.yaml, model_xs.yaml, hw_default.yaml
  spec/                regmap.yaml
  model/               arch.py, arch_report.py, train.py, quant.py, golden.py, export.py,
                       checker.py, governor.py, fault_model.py, campaign.py
  rtl/                 lane_*.v, lane_array.v, operand_gen.v, lane_checker.v, postproc.v, pool.v,
                       engine.v, spi_slave.v, regfile.v, governor.v, top_core.v
  rtl/gen/             regmap generated outputs (do not edit)
  rtl/platform/sim/    clk_gen_sim.v, cdc_fifo_sim.v, ...
  rtl/platform/xilinx/ clk_gen_xilinx.v, cdc_fifo_xpm.v, ...
  tb/                  testbenches
  fpga/                ooc.tcl, run_matrix.py, constraints/, reports/
  board/               BOARD_INFO.md, BRINGUP.md, xdc/ (filled in board phase)
  sw/sentinel/         driver, backend, camera, preprocess, dashboard, experiments/, plots/
  tests/               pytest
  tools/               run.py, check_env.py, gen_regmap.py, gen_mmcm_table.py, fit_report.py
  results/             model/, sim/, mock/, hw/
  docs/                SPEC.md, DECISIONS.md, PRIOR_ART.md, ENVIRONMENT.md, ARCHITECTURE.md,
                       VERIFICATION.md, RESULTS_SIM.md, AI_USAGE.md, THIRD_PARTY.md,
                       REPORT_DRAFT.md, SLIDES_OUTLINE.md, official/
  build/               (not committed)
```

---

## 18. Items blocked by board

Already answered by 10 Nov 2026 official documents: part number, package, speed grade, pins, F_IN, and programming method via JTAG (`board/BOARD_INFO.md`).

- Official `Zero7.xdc`, VCCO voltage, and I/O standards for each bank.
- Actual SPI speed, button polarities, number of WS2812B LEDs per chain, and boot from QSPI flash.
- Power measurement method.
- All `[HW]` results: E1–E4, E6, and E7 on board.
