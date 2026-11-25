# CLAUDE.md — SENTINEL Project (LSI Design Contest 2027)

> "SENTINEL" is only a working title. If the team has chosen their own name, replace it in this file and in README.
> This file is read automatically by Claude Code in every session. Do not run `/init`, as that will overwrite this file.

## 1. Mission

Build a CNN accelerator on Spartan-7 FPGA (ZERO7 board, Raspberry Pi HAT) that:

1. classifies 32×32 images **bit-exact** against the Python golden model,
2. guards MAC lanes with **dual checksums** (C1, C2, optional C3) to detect, localize, and correct errors,
3. runs MAC lanes faster than safe frequency (**per-layer overclocking**) with a hardware governor,
4. provides a complete measurement suite for experiments E1–E8.

**Current phase: PRE-BOARD.** Finish all work that does not require the board. Work requiring the board may only begin in accordance with §8.

## 2. Source of truth (priority order)

1. My instructions in the ongoing session.
2. `docs/official/` — official organizer documents. Only this is the source of contest rules. Do not add rules not written there.
3. `docs/SPEC.md` — technical specification. The Python golden model implementing SPEC is the **oracle** for RTL.
4. `docs/DECISIONS.md` — design decisions (ADR format). SPEC may only change via a new ADR.
5. `STATUS.md` — progress, gates, blocked items, notes between sessions.
6. `board/BOARD_INFO.md` — board facts. Fields marked `UNKNOWN` must not be guessed.
7. `docs/PRIOR_ART.md` — related work and originality claim boundaries.

## 3. Work cycle each session

1. **Read** CLAUDE.md, STATUS.md (especially "Notes for next session"), board/BOARD_INFO.md, and relevant SPEC sections. In the first session, also read all files in `docs/official/` (PDFs are image-based; read visually).
2. **Examine real state.** Run `python tools/run.py check` and `python tools/run.py test` (after M0 exists). Do not trust checkmarks in STATUS.md without evidence. If there are red tests, fix them before new features. If STATUS.md does not match reality, correct STATUS.md and explain.
3. **Select task**: first unfinished task in STATUS.md, according to milestone order. If that task is blocked (needs board, tools, or my decision), mark `[B]`, write the reason in "Blocked" section, then take the next unblocked task.
4. **Brief plan** (3–7 bullets) in chat before starting.
5. **Test first.** Create unit tests, golden vectors, or testbenches that fail first, then implement.
6. **Run until green.** Save concise log (command and result).
7. **Update STATUS.md.** Check `[x]` only if Definition of Done is fulfilled. Write evidence in "Evidence log": date, command, and result.
8. **Git commit** small and clear for each green step. Do not `git push` unless I ask.
9. **Continue** to the next task without waiting for confirmation. Before context is nearly full (around 70%), or when all unblocked tasks are complete: write "Notes for next session" in STATUS.md, commit, then send summary to me (§5).

## 4. Hard rules (must not be violated)

- **Do not fabricate results.** Every number in documents, reports, or plots must be traceable to scripts and logs existing in the repo. If a tool cannot be run, say so. Do not write outputs that were not genuinely produced.
- **Simulation cannot produce real timing errors.** Never claim hardware behavior from simulation or from synthetic error models.
- **Mandatory labels** on every number, table, and plot:
  - `[SIM]` RTL simulation or Python model result,
  - `[SYNTHETIC]` using artificial timing error model (`model/fault_model.py`),
  - `[VIVADO-STA]` from Vivado timing or resource report (static estimation),
  - `[HW]` measured on real board.
    Plots from mock backend must be watermarked **"SYNTHETIC — NOT MEASURED"**.
- **Do not guess board facts**: part number, package, speed grade, pins, input clock, programming method, SPI speed, LED interfaces, presence of XADC. Use parameters or placeholders, then record in "Blocked".
- **Golden model and RTL must be bit-exact.** There is no "almost identical".
- **Do not alter tests to pass** without written justification. If specification needs to change, order: ADR in `docs/DECISIONS.md` → update SPEC → update golden model and its tests → update RTL.
- **Random seed fixed** and recorded. Record tool versions (Python, PyTorch, Icarus, Verilator, Vivado) in `docs/ENVIRONMENT.md`.
- **Contest rules**: distinguish `[OFFICIAL]` (written in docs/official), `[UNKNOWN]`, and `[INFERENCE]`. Do not write rules that do not exist.
- **Third-party code**: do not copy code with unclear licensing. Record every source and its license in `docs/THIRD_PARTY.md`.
- **Originality claims**: only those supported by `docs/PRIOR_ART.md`. Do not claim "first" or "novel" for things not yet checked.

## 5. Autonomy, questions, and reports

- Reversible steps (writing files, running tests, creating branches, local commits): **execute directly**, without asking permission.
- Inquire only if:
  (a) there is ambiguity in SPEC that changes architecture,
  (b) requires my action (installing tools, running Vivado on my PC, board data), or
  (c) contest rules are unclear.
  Ask once with your recommendation, then continue other unblocked tasks.
- If a tool is unavailable (e.g. Vivado not in PATH): still create the script, write exact instructions for me, mark task `[B] requires user run`, then continue.
- **Summary at end of session** (concise):
  1. completed: what was done, with evidence (commands and test results),
  2. blocked: what and why,
  3. what I need to do, with exact steps,
  4. questions, each with recommendation.

## 6. Conventions

- **Language**: communication with me in Indonesian. Code, comments, filenames, and technical documents in repo in English (for contest report). STATUS.md may be in Indonesian.
- **RTL**: Synthesizable Verilog-2005, compatible with Icarus (`iverilog -g2012`), Verilator (`--lint-only -Wall`), and Vivado.
  - One module per file, filename = module name.
  - Synchronous active-high reset, unless written justification exists. No latches allowed.
  - All widths and lane counts use parameters (K, ACC_W, etc.).
- **Xilinx primitives** (MMCM, BUFGCTRL, XPM, Clocking Wizard) may only appear in `rtl/platform/xilinx/`. Each wrapper has a portable simulation model in `rtl/platform/sim/`.
- **Testbenches** use vector files (`$readmemh`) generated by golden model. Print `PASS n/n`, or `FAIL` along with first mismatch (layer, unit, lane, expected, got). Exit with failure status if mismatch occurs.
- **Python** ≥ 3.10, pytest, cross-platform (Windows and Linux). All commands via `tools/run.py`, not Makefile or bash scripts alone.
- **Register map**: single source, `spec/regmap.yaml`, generated to Verilog and Python by `tools/gen_regmap.py`. Do not edit generated files. Test exists ensuring generated files are always up-to-date.
- **Build folder**: `build/` (vectors, exported weights, simulation outputs) not committed and always regenerable. `results/` is committed, as it contains experiment data and metadata.

## 7. Contest context (concise; verify against docs/official)

Updated 2026-11-16 with user agreement, from `docs/official/README.md`.

- [OFFICIAL] 30th LSI Design Contest 2027 in Chitose, Hokkaido. Theme: hardware implementation of CNN, number of layers arbitrary.
- [OFFICIAL] Report deadline 31 Jan 2027. Contest 5 Mar 2027, hybrid. 10-minute presentation (at most 10 slides) and 5-minute Q&A.
- [OFFICIAL] Submissions: final report and synthesis report for AMD Spartan-7 XC7S25CSGA225-1. Synthesis report mandatory for all classes; format not yet explained (user will provide once published).
- [OFFICIAL] Judges evaluate not only speed and area, but also ideas, originality, uniqueness, and presentation. Participants' school grade is taken into account.
- [OFFICIAL] Purpose requirements: validation data specified by organizers and real-time camera input. Validation images provided on the day of the contest (from camera, SD card, etc.). Presentation must show how fast recognition results are output.
- [OFFICIAL] CNN accepts 32×32 input. Structure refers to 23rd contest design overview; hidden layer structure is free.
- [OFFICIAL] Class 1 (Image Classification): image classification only. Level 1 and Level 2 target XC7S25CSGA225-1. Level 3 board and architecture free, but must still show synthesis report fitting in XC7S25CSGA225-1.
- [OFFICIAL] Class 2 (ZERO7): ZERO7 board only, free task, Level 3 only.
- [OFFICIAL] ZERO7 by Gigafirm is a Raspberry Pi HAT; organizers state loan board can be connected to Raspberry Pi 5. Recommended Vivado: 2025.2.
- [USER, 25 Nov 2026] Team uses its own Raspberry Pi 5 as host (ADR-033, supersedes the Pi 4 of ADR-022). Board and Pi are in hand; work on the real hardware is on hold by user decision until development and architecture are finished (26 Nov 2026).
- [OFFICIAL] Training dataset is free, but target classes are specified by organizers. Therefore model must be retrainable, and weights reloadable via SPI **without resynthesis**. [OFFICIAL, website update read 23 Nov 2026] The image classification task lists four classes: cat, dog, deer, horse. [USER, 25 Nov 2026] The project uses these four classes (ADR-037, model `s4`).
- [OFFICIAL, differs between pages] Team size: English page 1–3 persons, Japanese page at most 4 persons. [USER] Team consists of 4 persons, hence relies on Japanese page rule. [USER, 17 Nov 2026] Organizers have confirmed 4-person team (Q5 in STATUS.md); modification of this line approved by user 18 Nov 2026.
- [OFFICIAL] Official documents contain no AI usage rules. [USER] User decision: AI may be used as long as compliant with contest provisions.
- [UNKNOWN] Evaluation weightings, report and synthesis report formats, and whether live hardware demo is permitted.
- **Target category [USER decision 25 Nov 2026, ADR-036; organizer confirmation relayed 23 Nov 2026]: Class 2 (ZERO7 Class), Level 3, task: image classification, no camera (ADR-035).** Previous text: [PROPOSAL, awaiting organizer confirmation]: Class 2 (ZERO7 Class), Level 3. Still maintain image classification, validation data mode, and real-time camera mode, so that project also fulfills Class 1 Level 3 requirements if class transfer is required. Do not write this category as a fact in report before confirmed.

## 8. BOARD Phase

Board phase (milestones B1–B6 in STATUS.md) may only begin if two conditions are fulfilled:

1. all **mandatory** fields in `board/BOARD_INFO.md` are filled (no `UNKNOWN`) and each has a source, and
2. I write that the board is in hand (e.g. "board siap" or "board ready").

Rules in board phase:

- Always start from safe clock. Overclocking may only be conducted after E7 is bit-exact on safe clock.
- Never alter voltage. Monitor temperature.
- Board results labeled `[HW]` and stored in `results/hw/`, separated from `results/mock/`.
- Vivado runs on PC, not on Raspberry Pi. Scripts for Pi must be runnable standalone on Pi, and results copied back to repo.

## 9. Standard commands (created in M0)

```
python tools/run.py check            # check tools and versions
python tools/run.py test             # pytest + all testbenches
python tools/run.py gen              # regmap, vectors, weights
python tools/run.py train --model s  # training
python tools/run.py export --model s # quantization + export
python tools/run.py sim <tb>         # single testbench
python tools/run.py campaign         # fault injection campaign
python tools/run.py ooc              # Vivado out-of-context (if Vivado exists)
python tools/run.py plots            # all plots
```


## 10. AI Memory, Graphity, and Tool Integration

### 10.1 Graphity Integration

"Graphity" in this section means the `graphify` tool (skill `graphify`); its output lives in `graphify-out/`.

Graphity is used to document and visualize relationships between project files, modules, dependencies, and architecture.

When working on relevant project changes:

1. Consult `graphify-out/GRAPH_REPORT.md` when architectural relationships are relevant.
2. Consult `graphify-out/GRAPHITY_3D_AUDIT_REPORT.md` when modifying graph data or when the user explicitly requests a 3D visualization update.
3. Use the installed Graphity skill when analyzing project relationships.
4. After adding, modifying, moving, or deleting relevant files, evaluate whether Graphity needs updating.
5. Update the underlying Graphity graph data using the existing Graphity workflow when necessary.
6. Run the available consistency validation before declaring graph synchronization complete.
7. Never assume Graphity is automatically synchronized.
8. Do not overwrite existing graph data without understanding its structure and generation process.
9. Avoid unnecessary full repository rescans when incremental updates are supported.
10. Always verify Graphity findings against the actual source code before making decisions.
11. Treat Graphity as a navigation and analysis aid, not as the source of truth.

#### 3D Visualization Update Policy

- Do NOT automatically regenerate or update the Graphity 3D web visualization after code changes or graph data updates.
- Preserve existing visualization files, including `graph3d.html`, `graph3d.backup.html`, and related assets.
- Update the underlying Graphity graph data when necessary, but defer 3D visualization regeneration.
- Only regenerate or update the 3D web visualization when explicitly requested by the user.
- Do not spend tokens checking, rebuilding, or auditing the 3D visualization during routine development sessions unless explicitly requested.
- When the user requests a 3D visualization update:
  1. Read the latest validated Graphity graph data.
  2. Consult `graphify-out/GRAPHITY_3D_AUDIT_REPORT.md`.
  3. Use the existing Graphity workflow to regenerate or synchronize the 3D visualization.
  4. Run the available consistency validation.
  5. Verify that the generated visualization reflects the latest graph data.
- Do not modify or regenerate unrelated Graphity outputs unless required by the existing workflow.

### 10.2 AI Memory Integration

- Claude-Mem supplements project documentation; it does not replace it.
- `STATUS.md` remains the authoritative source for current project progress.
- `docs/SPEC.md` remains the authoritative technical specification.
- `docs/DECISIONS.md` remains the authoritative design decision record.
- Record important technical decisions, discoveries, and unresolved issues in their appropriate project documents.
- Do not rely exclusively on conversational memory for critical project information.

### 10.3 Skills, Agents, and Plugins

- Use installed skills and agents when they are relevant to the current task.
- Prefer specialized tools for RTL development, verification, debugging, architecture analysis, and documentation.
- Avoid activating unnecessary agents or hooks.
- Do not duplicate functionality already provided by existing project tools.
- Verify tool execution rather than assuming installation means functionality is active.

### 10.4 Context and Token Efficiency

- Read only the project documents relevant to the current task, while respecting the mandatory session startup checklist.
- Avoid repeatedly analyzing unchanged files.
- Prefer targeted updates over full repository rescans.
- Preserve important findings in project documentation so future sessions can continue efficiently.
- Avoid unnecessary Graphity analysis, regeneration, and visualization tasks that do not contribute to the current objective.
- Prioritize essential project work and verification over optional visualization and reporting tasks.
