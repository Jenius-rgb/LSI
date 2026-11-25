#!/usr/bin/env python3
"""Compare the zero-skip fixes of ADR-028 from per-image simulator logs [SIM].

    python tools/zs_compare.py --baseline 277895 \
        --run unguarded=results/sim/zero_skip/unguarded \
        --run min_sets=results/sim/zero_skip/zs1 --run stall=results/sim/zero_skip/zs2

Each --run names a directory of tb_engine logs (one per shard). tb_engine prints ``IMG i done cycles=n`` for every
image that matched the golden model, so an image that failed or hung has no line. The baseline is the data-independent
cycle count with ZERO_SKIP = 0. The guard cost of a fix is its cycles minus the unguarded cycles on the images the
unguarded design finished; a result buffer could at best win back that cost.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMG_RE = re.compile(r"^IMG (\d+) done cycles=(\d+)", re.M)
FAIL_RE = re.compile(r"^FAIL.*$", re.M)


def read_run(directory: Path) -> tuple[dict[int, int], list[str]]:
    cycles: dict[int, int] = {}
    fails: list[str] = []
    for log in sorted(directory.glob("*.log")):
        text = log.read_text(encoding="utf-8", errors="replace")
        first_fail = FAIL_RE.search(text)
        for match in IMG_RE.finditer(text):
            # Lines after a FAIL are not trusted (xsim ran on after $fatal before tb_engine called $finish).
            if first_fail is None or match.start() < first_fail.start():
                cycles[int(match.group(1))] = int(match.group(2))
        fails += [f"{log.name}: {line}" for line in FAIL_RE.findall(text)]
    return cycles, fails


def compare(baseline: int, runs: dict[str, Path], reference: str = "unguarded") -> dict:
    data = {name: read_run(path) for name, path in runs.items()}
    ref = data.get(reference, ({}, []))[0]
    out = {"label": "[SIM]", "baseline_cycles": baseline, "runs": {}}
    for name, (cycles, fails) in data.items():
        if not cycles:
            continue
        mean = sum(cycles.values()) / len(cycles)
        row = {
            "source": runs[name].relative_to(ROOT).as_posix() if runs[name].is_relative_to(ROOT) else str(runs[name]),
            "images_passed": len(cycles), "mean_cycles": round(mean, 1),
            "saving_vs_baseline_pct": round(100 * (1 - mean / baseline), 2),
            "min_cycles": min(cycles.values()), "max_cycles": max(cycles.values()),
            "fail_lines": fails[:6],
        }
        if name != reference and ref:
            common = sorted(set(cycles) & set(ref))
            cost = [cycles[i] - ref[i] for i in common]
            row["guard_cost_vs_unguarded"] = {
                "images": len(common), "total_cycles": sum(cost), "max_per_image": max(cost) if cost else 0,
                "images_with_cost": sum(1 for c in cost if c), "min_per_image": min(cost) if cost else 0,
            }
        out["runs"][name] = row
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--baseline", type=int, required=True)
    ap.add_argument("--run", action="append", required=True, help="name=directory of tb_engine logs")
    ap.add_argument("--out", default="results/sim/zero_skip/compare.json")
    args = ap.parse_args()
    runs = {r.split("=", 1)[0]: (ROOT / r.split("=", 1)[1]).resolve() for r in args.run}
    rep = compare(args.baseline, runs)
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8", newline="\n")
    for name, row in rep["runs"].items():
        cost = row.get("guard_cost_vs_unguarded")
        extra = f"; guard cost {cost['total_cycles']} cycles over {cost['images']} images (max {cost['max_per_image']})" if cost else ""
        print(f"[SIM] {name:10s} {row['images_passed']:3d} images, mean {row['mean_cycles']:.1f} cycles, "
              f"{row['saving_vs_baseline_pct']:.2f} % below {args.baseline}{extra}; {len(row['fail_lines'])} FAIL lines")
    print(f"written {out.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
