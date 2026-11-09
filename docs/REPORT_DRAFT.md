# SENTINEL: draft report (pre-board)

Draft only. Numbers come from `docs/RESULTS_SIM.md` ([SIM]) and, once available, from Vivado
([VIVADO-STA]). Every value marked `[HW-TBD]` needs a measurement on a real board and must not be
filled from simulation or the synthetic error model. The contest category is [PROPOSAL] pending
confirmation by the organisers; the target classes are [UNKNOWN] and CIFAR-10 is a stand-in.

## 1. Goal

A CNN accelerator on Spartan-7 (ZERO7) that classifies 32x32 images, bit-exact against a Python
golden model, whose MAC lanes are protected by dual checksums so lanes can run above the safe
timing limit. Prior work and the limits of any claim are in `docs/PRIOR_ART.md`.

## 2. Architecture

See `docs/ARCHITECTURE.md`. K data lanes and 2 or 3 checksum lanes share a fast clock domain;
memory, control and checking stay in a safe domain. A hardware governor selects a clock per layer.

## 3. Model and training

Accuracy of the float and integer models: `docs/RESULTS_SIM.md`, section "Model accuracy" [SIM].

## 4. Error handling

Decision logic: SPEC 6.2, implemented in `rtl/lane_checker.v`, verified against `model/checker.py`.
Limits are stated in SPEC 6.5: the checksum protects MAC results, not the broadcast input.

## 5. Results

| Item | Value | Source |
| --- | --- | --- |
| Accuracy, float / integer | see RESULTS_SIM | [SIM] |
| Single-lane correction, two-lane miscorrection | see RESULTS_SIM | [SIM], injected XOR masks |
| RTL bit-exact checks | see RESULTS_SIM | [SIM] |
| Cycles and overhead vs model | see RESULTS_SIM | [SIM] |
| Resource and Fmax per part | [VIVADO-TBD] | [VIVADO-STA] after M11 |
| Throughput gain, three modes (E4) | [HW-TBD] | needs board |
| Error atlas across frequency (E1) | [HW-TBD] | needs board |
| Determinism (E2), onset per layer (E3) | [HW-TBD] | needs board |
| Governor and temperature (E6) | [HW-TBD] | needs board |
| Bit-exact on board (E7) | [HW-TBD] | needs board |

Figures from the mock backend exist only to test the scripts. They carry the watermark
"SYNTHETIC — NOT MEASURED" and must not appear in the report as results.

## 6. Conclusion

To be written after board results.
