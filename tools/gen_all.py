#!/usr/bin/env python3
"""Regenerate register map, weights and verification vectors (`python tools/run.py gen`)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import gen_regmap  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regmap", action="store_true", help="only the register map")
    args = parser.parse_args()
    gen_regmap.main()
    if args.regmap:
        return 0
    from model.config import load_hw_config
    from model.export import write_artifacts
    from model.vectors import load_or_random_qmodel

    hw = load_hw_config()
    for model in ("s", "xs"):
        qm, source = load_or_random_qmodel(model)
        for k in (8, 16):
            manifest = write_artifacts(qm, {**hw, "K": k}, ROOT / "build" / "weights")
            print(f"exported {model} K={k} from {source}: sha256 {manifest['sha256'][:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
