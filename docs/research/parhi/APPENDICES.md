# Appendices A–G

| Item | Value |
| --- | --- |
| Pages read | PDF 726–781 = book pages 717–774: A 726–731 (pp. 717–722), B 732–751 (pp. 723–742), C 752–755 (pp. 743–746), D 756–760 (pp. 747–751), E 761–770 (pp. 753–762), F 771–777 (pp. 763–769), G 778–781 (pp. 771–774) |
| Read on | 17 Nov 2026, every page, from the local OCR text |
| Checked on the rendered page | none needed: no formula from the appendices is carried into SENTINEL work beyond what is stated in words |
| Pages that could not be read | none. Scan notes: PDF 759 and 760 are book pp. 751 and 750 in swapped order; book pp. 752 and 770 are not in the scan (probably blank). The index starts at PDF 782 (book p. 775), not at PDF 785 as first mapped; the index is not part of the text and was only skimmed (PDF 782–785) |

Book facts carry a page reference ("p. N" = printed book page). Statements about SENTINEL are
[INFERENCE] unless they point to a file or result in this repository.

## A. Shortest-path algorithms (pp. 717–722)

- **Bellman–Ford** finds shortest paths from one origin and reports whether a negative cycle exists; **Floyd–Warshall**
  finds all-pairs shortest paths and detects negative cycles through negative diagonal entries. The book gives both as
  O(n³) in its formulation; Floyd–Warshall is preferred when all pairs are needed (p. 721). They solve the iteration-bound
  (chapter 2), retiming (chapter 4) and retiming-for-folding (chapter 6) problems.
- SENTINEL: not needed; Vivado's timing engine does the equivalent work on the netlist (`CH02.md`, `CH04.md`).

## B. Scheduling and allocation (pp. 723–742)

- High-level synthesis turns a data-flow graph into an RTL architecture under area or time constraints; scheduling (which
  time step) and allocation (which unit) are interdependent and NP-complete in general (pp. 723–725).
- **ASAP** and **ALAP** schedules give each node's earliest and latest step, i.e. its scheduling range; **list scheduling**
  orders ready nodes by criticality (narrow range first) under a resource limit; **force-directed scheduling** balances
  expected concurrency through distribution graphs and self, predecessor and successor "forces" (pp. 726–733).
- Critical-path schedulers only use intra-iteration constraints; **loop-based scheduling** (the MARS system) also uses
  inter-iteration constraints and so pipelines and retimes implicitly; it starts from the lower bound on units of each
  type, `M = ⌈N·T_op / (P·T)⌉` (N operations of time T_op on units pipelined P deep, iteration period T), and adds units
  only when conflicts cannot be rescheduled (pp. 734–737). Example: a biquad at period 4 needs 1 multiplier and 1 adder
  instead of 2 and 2.
- **Integer linear programming** gives optimal schedules with binary variables "node i at step j", resource, uniqueness and
  precedence constraints, at the cost of run time (pp. 738–741).
- SENTINEL [INFERENCE + SIM]: the engine schedule is fixed by the loop order (`docs/SPEC.md` 5.3); the lower bound above,
  read with "units = lanes", is what the lane utilization in `CH06.md` measures. For model s at K = 8 the ideal cycle count
  is within 0.14 % of MACs/K (utilization 99.86 %, [SIM]), so the schedule is at the bound; more speed needs more lanes,
  more operands per lane, fewer operations (`CH08.md`) or a faster clock.

## C. Euclid's GCD (pp. 743–746)

- Division algorithm and iterated division for the GCD of integers and of polynomials, with back-substitution giving the
  coefficients of `GCD = a·s + b·r`; this supplies the inverses in the Chinese-remainder construction of Winograd's fast
  convolution (chapter 8).
- SENTINEL: needed only if the Winograd-type option of `CH08.md` is ever derived in detail.

## D. Orthonormality of Schur polynomials (pp. 747–751)

- Proof that the Schur polynomials of chapter 12 are orthogonal and then orthonormal under the power-based inner product.
- SENTINEL: no use.

## E. Fast binary adders and multipliers (pp. 753–762)

- Adders built from multiplexers only: a Manchester carry chain (delay grows with W), a carry-select adder (8-bit: 6
  multiplexer delays, 29 multiplexers) and a tree (binary look-ahead) carry generator using an associative operator on
  (generate, propagate) pairs (8-bit: 27 multiplexers and 19 AND gates, 6 multiplexer delays; delay ∝ log₂W) (pp. 754–757).
- **Wallace** and **Dadda** trees sum partial products with full and half adders in stages and one final carry-propagate
  adder. Dadda reduces the column height by at most 1.5× per stage and only as much as needed (heights 8 → 6 → 4 → 3 → 2);
  for 8 × 8 bits, Wallace uses 38 full and 15 half adders with a 10-bit final adder, Dadda 35 and 7 with a 14-bit one
  (pp. 758–761).
- SENTINEL [INFERENCE]: the FPGA's dedicated carry chain already makes two-operand adds fast; the Wallace/Dadda idea is the
  tool for the **multi-operand** checksum-weight sum (14 shifted terms for wc3, `CH13.md`), where a Dadda-style staged
  reduction followed by one carry chain is the standard way to keep the depth low.

## F. Scheduling bit-serial systems (pp. 763–769)

- With one operator per operation, bit-serial scheduling chooses start times so that every operand arrives on time,
  `T_j − T_i ≥ t_i − t_j` per edge (minus n·W for edges with n word delays), and minimises synchronising shift registers,
  sharing delays on fan-out (the cost of a node is its largest delay). This is an integer linear program (pp. 764–769).
- SENTINEL: not relevant (no bit-serial units, `CH05.md`).

## G. FIR coefficient quantization with signed powers of two (pp. 771–774)

- The NUS algorithm normalises the ideal coefficients, scales them by a variable factor between 0.4375 and 1.13, allocates
  signed power-of-two terms one at a time to the coefficient with the largest error, keeps the scale that gives the lowest
  normalised peak ripple, and undoes the scale after the filter (pp. 771–774).
- SENTINEL [INFERENCE]: weights are uniform INT8 from training and quantization (`docs/SPEC.md` 4); power-of-two weights would
  turn multipliers into shifts but would change the trained model, the golden model and accuracy. Not proposed. The idea of
  choosing the scale before rounding matches SENTINEL's per-layer scale selection in spirit only.

## Candidates noted for the development list

None new. Appendix E supports the multi-operand tree candidate (`CH13.md`), and appendix B gives the bound that explains why
SENTINEL's schedule is already at its limit for model s at K = 8.
