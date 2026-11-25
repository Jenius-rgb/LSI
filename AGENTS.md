# AGENTS.md — SENTINEL-LSI-2027

This document serves as the shared main instructions for all AI coding agents working on the SENTINEL-LSI-2027 repository.

## Main Instruction Source

@CLAUDE.md

Read and comply with all project rules stated in `CLAUDE.md`, including its source-of-truth order (§2): the user's
instruction in the running session first, then `docs/official/`, `docs/SPEC.md`, `docs/DECISIONS.md`, `STATUS.md`,
`board/BOARD_INFO.md` and `docs/PRIOR_ART.md`. If this file and `CLAUDE.md` ever disagree, `CLAUDE.md` wins.

Do not create alternative instructions that conflict with `CLAUDE.md`.

## Development Rules

1. Comply with all official constraints and provisions of the LSI Design Contest 2027.
2. Do not fabricate specifications, data, test results, or technical decisions.
3. Prioritize official documents and project specifications as the source of truth.
4. Maintain compatibility with the existing architecture.
5. Do not delete or overwrite unverified changes.
6. Perform testing before declaring work complete.
7. Document important changes so other AIs can continue the work.

## Inter-AI Collaboration

All AI coding agents must:

- Read the project context before working.
- Check Git status and recent changes.
- Update documentation when there are important changes.
- Avoid change conflicts between agents.
- Ensure work can be continued by other agents.

## Core Principle

Adherence to contest rules, technical correctness, code integrity, and quality of results are more important than implementation speed.
