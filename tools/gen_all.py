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
    parser.add_argument("--no-vectors", action="store_true", help="skip verification vectors")
    args = parser.parse_args()
    gen_regmap.main()
    import gen_mmcm_table

    for path, text in gen_mmcm_table.outputs().items():
        path.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {path.relative_to(ROOT).as_posix()}")
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
    if not args.no_vectors:
        import benches as bench_registry
        from sim import _vector_plusargs

        for name, bench in bench_registry.BENCHES.items():
            if not bench.slow and bench.vectors is not None:
                _vector_plusargs(bench)
                print(f"vectors: build/vectors/{name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
