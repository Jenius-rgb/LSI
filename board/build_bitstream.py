#!/usr/bin/env python3
"""Build the ZERO7 bitstream. Refuses to run until the board facts exist.

The refusal is the safety net of the pre-board phase: nothing here may guess a part number,
a pin or an input clock.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "board"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "sw"))

from bringup import required_unknowns  # noqa: E402


def main() -> int:
    missing = required_unknowns()
    if missing:
        print("Refusing to build: board/BOARD_INFO.md has UNKNOWN required fields:")
        for field in missing:
            print(f"  - {field}")
        return 2
    xdc = ROOT / "board" / "xdc" / "sentinel_board.xdc"
    if not xdc.exists():
        print("Refusing to build: fill board/xdc/sentinel_board.xdc from the board documentation first.")
        return 2
    print("Board facts present. The build flow (Vivado project, BRAM parameters from the model) is set up in the board phase.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
