# Slide outline (10 slides, 10 minutes)

[OFFICIAL] maximum 10 slides, 10 minutes plus 5 minutes of questions. The live demo format is [UNKNOWN].

1. **Problem**: fast CNN inference on a small FPGA, and why overclocking needs a safety net.
2. **Idea**: dual checksums over K lanes: detect, locate, correct one lane without a retry.
3. **Architecture**: two clock domains, operand and result FIFOs (ARCHITECTURE diagram).
4. **Checksum math**: C1, C2, optional C3, the decision table (one line per case).
5. **Governor**: per-layer clock selection in hardware.
6. **Verification**: golden model, bit-exact RTL, injection campaign [SIM] numbers.
7. **Resource and timing**: [VIVADO-STA] table after M11, per part.
8. **Board results**: [HW-TBD] error atlas and throughput by mode, with E7 bit-exactness.
9. **Live or video demo**: validation images and real-time camera speed [HW-TBD].
10. **Originality and limits**: what is new per PRIOR_ART, what is not protected (SPEC 6.5).
