# Verification plan and status

Every result here is `[SIM]`. Simulation cannot reproduce real timing errors; no hardware behaviour
is claimed from it. Latest bench outcomes are in `docs/RESULTS_SIM.md` (from
`results/sim/rtl_regression.jsonl`).

## Levels (SPEC 13.3)

| Level | Where | What |
| --- | --- | --- |
| L0 | `tests/test_golden.py`, `tests/test_checker.py`, `tests/test_export.py`, `tests/test_quant.py` | requant, padding, flatten, argmax ties, decision table, property tests, bit bounds |
| L1 | `tb/tb_lane_array.v`, `tb/tb_checker.v`, `tb/tb_spi_slave.v`, `tb/tb_governor.v` | lanes (each `LANE_IMPL`), checker, SPI slave, governor |
| L2/L3 | `tb/tb_engine.v` | engine, single clock, logits and class against golden |
| L4 | `tb/tb_system.v`, `tb/tb_spi_log.v` | system with SPI and two clock domains; driver log replay; injection |
| L5 | `tb/tb_governor.v` | governor state trajectory, 60 scenarios from the synthetic fault model |

## Corner cases (SPEC 13.4)

| Case | Bench |
| --- | --- |
| Cin = 3 | every engine bench (conv1) |
| Groups with zero-weight lanes | `engine_corner_zero_lanes`, and FC with N = 10 at K = 8 in every engine bench |
| Extremes a = 255, w = +/-127 | `engine_corner_extreme` |
| Zero image | image 0 of `model.vectors.corner_images` |
| Saturation | `engine_corner_saturate` (also n = 0 and n = 31) |
| Ties in pooling and argmax | `engine_corner_ties` |
| Log full, FATAL path | `system_micro_corners` |

## Simulators

Icarus Verilog runs the short benches and xsim the long regressions (about ten times faster in the
one direct comparison made, `engine_xs_k8`: both passed with identical cycle counts). Verilator is
used for lint only: no C++ toolchain is installed on this machine, so its simulation path is not used.

## Injection semantics

Injection (`rtl/lane_array.v`, SPEC 11) XORs a holding register at capture. The Python model
`model/engine_model.py` mirrors it: the unit counter restarts each pass, and ONESHOT slots re-arm
at the first pass of an image.

## How to reproduce

```
python tools/run.py check
python tools/run.py test                 # fast benches
python tools/run.py sim engine_s_k8_n200 # long regressions (xsim)
python tools/run.py sim system_micro_campaign
python tools/run.py campaign --model s
```
