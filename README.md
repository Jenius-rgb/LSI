# SENTINEL

CNN accelerator for the 30th LSI Design Contest (2027), targeting the AMD Spartan-7
based ZERO7 board (Raspberry Pi HAT). "SENTINEL" is a working title. The contest chip is
XC7S25CSGA225-1; every team must hand in a synthesis report for it (`docs/official/README.md`).

The accelerator classifies 32×32 images bit-exactly against a Python golden model and
protects its MAC lanes with dual checksums, so that errors from overclocking the lanes
can be detected, localised and corrected.

**Project phase: pre-board.** Nothing in this repository has been measured on hardware
yet. Every number carries one of these labels:

| Label | Meaning |
| --- | --- |
| `[SIM]` | RTL simulation or Python model |
| `[SYNTHETIC]` | uses the artificial timing-error model (`model/fault_model.py`) |
| `[VIVADO-STA]` | Vivado timing or resource report (static estimate) |
| `[HW]` | measured on a real board |

## Getting started

Python 3.10 or newer, Icarus Verilog, and optionally Verilator (lint) and Vivado.

```
python -m venv --system-site-packages .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Linux: .venv/bin/python
python tools/run.py check
python tools/run.py test
```

`tools/run.py` uses `.venv` automatically when it exists.

| Command | Purpose |
| --- | --- |
| `python tools/run.py check` | detect tools and versions |
| `python tools/run.py test` | pytest and all RTL testbenches |
| `python tools/run.py gen` | generate register map, vectors and weights |
| `python tools/run.py train --model s` | train the float model |
| `python tools/run.py export --model s` | quantise and export |
| `python tools/run.py sim <tb>` | run one testbench |
| `python tools/run.py synth-official` | official synthesis report for XC7S25CSGA225-1 (`results/vivado/official/`) |
| `python tools/run.py campaign` | fault-injection campaigns |
| `python tools/run.py ooc` | Vivado out-of-context runs |
| `python tools/run.py plots` | regenerate all plots |

## Where things are

| Path | Content |
| --- | --- |
| `docs/SPEC.md` | technical specification; the golden model implements it and is the oracle for the RTL |
| `docs/DECISIONS.md` | design decisions (ADRs) |
| `STATUS.md` | milestones, evidence log, blocked items |
| `model/` | training, quantisation, golden model, checker, governor and fault models |
| `rtl/`, `tb/` | Verilog-2005 RTL and testbenches |
| `fpga/` | Vivado out-of-context flow |
| `sw/sentinel/` | Raspberry Pi software and experiment harness |
| `results/` | committed experiment data and metadata |
| `build/` | regenerable artefacts (not committed) |
