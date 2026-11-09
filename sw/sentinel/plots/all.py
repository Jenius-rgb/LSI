"""Regenerate every experiment plot from the latest CSV of each experiment.

Single y axis per chart, fixed categorical order (validated palette), and for mock data
the mandatory watermark "SYNTHETIC — NOT MEASURED".
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from sentinel.harness import ROOT, latest_run  # noqa: E402

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
GRID = "#e4e3df"
WATERMARK = "SYNTHETIC — NOT MEASURED"
LABELS = {"mock": "[SYNTHETIC]", "hw": "[HW]", "sim": "[SIM]"}


def figure(title: str, backend: str, xlabel: str, ylabel: str):
    fig, ax = plt.subplots(figsize=(7.2, 4.2), dpi=140)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    ax.set_title(f"{title} {LABELS.get(backend, '')}", color=TEXT, fontsize=11, loc="left", pad=10)
    ax.set_xlabel(xlabel, color=TEXT_2, fontsize=9)
    ax.set_ylabel(ylabel, color=TEXT_2, fontsize=9)
    ax.tick_params(colors=TEXT_2, labelsize=8, length=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    return fig, ax


def finish(fig, ax, out: Path, backend: str, legend: bool = True) -> None:
    if legend:
        ax.legend(frameon=False, fontsize=8, labelcolor=TEXT_2, loc="best")
    if backend == "mock":
        fig.text(0.5, 0.5, WATERMARK, ha="center", va="center", fontsize=26, color="#b3261e", alpha=0.20, rotation=24, fontweight="bold", zorder=20)
    fig.tight_layout()
    fig.savefig(out, facecolor=SURFACE)
    plt.close(fig)


def read_rows(run_dir: Path) -> list[dict]:
    with open(run_dir / "data.csv", newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def f_float(rows: list[dict], key: str) -> list[float]:
    return [float(r[key]) if r[key] != "" else float("nan") for r in rows]


def plot_e1(backend: str, run_dir: Path) -> Path:
    rows = read_rows(run_dir)
    fig, ax = figure("E1 error events per layer", backend, "Turbo frequency (MHz)", "Error events")
    x = f_float(rows, "f_mhz")
    layers = sorted(k for k in rows[0] if k.endswith("_events") and k.startswith("layer"))
    for color, key in zip(SERIES, layers):
        ax.plot(x, f_float(rows, key), color=color, linewidth=1.5, marker="o", markersize=4, label=key.replace("_events", ""))
    out = run_dir / "e1_events.png"
    finish(fig, ax, out, backend)
    return out


def plot_e2(backend: str, run_dir: Path) -> Path:
    rows = read_rows(run_dir)
    fig, ax = figure("E2 repeats identical to the first run", backend, "Image", "Fraction identical")
    x = [int(r["image"]) for r in rows]
    y = [int(r["identical_to_first"]) / int(r["repeats"]) for r in rows]
    ax.bar(x, y, color=SERIES[0], width=0.6)
    ax.set_ylim(0, 1.05)
    out = run_dir / "e2_identity.png"
    finish(fig, ax, out, backend, legend=False)
    return out


def plot_e3(backend: str, run_dir: Path) -> Path:
    rows = read_rows(run_dir)
    fig, ax = figure("E3 errors per layer against frequency", backend, "Turbo frequency (MHz)", "Errors")
    x = f_float(rows, "f_mhz")
    layers = sorted(k for k in rows[0] if k.startswith("layer"))
    for color, key in zip(SERIES, layers):
        ax.plot(x, f_float(rows, key), color=color, linewidth=1.5, marker="o", markersize=4, label=key.replace("_errors", ""))
    out = run_dir / "e3_onset.png"
    finish(fig, ax, out, backend)
    return out


def plot_e4(backend: str, run_dir: Path) -> Path:
    rows = read_rows(run_dir)
    fig, ax = figure("E4 throughput by mode", backend, "Turbo frequency (MHz)", "Images per second")
    for color, mode in zip(SERIES, ("unprotected", "detect_recompute", "correct")):
        sel = [r for r in rows if r["mode"] == mode]
        ax.plot(f_float(sel, "f_mhz"), f_float(sel, "images_per_s"), color=color, linewidth=1.5, marker="o", markersize=4, label=mode)
    out = run_dir / "e4_throughput.png"
    finish(fig, ax, out, backend)
    return out


def plot_e6(backend: str, run_dir: Path) -> Path:
    rows = read_rows(run_dir)
    fig, ax = figure("E6 governor turbo frequency", backend, "Image index", "Turbo frequency (MHz)")
    ax.plot(f_float(rows, "image_index"), f_float(rows, "turbo_mhz"), color=SERIES[0], linewidth=1.5)
    out = run_dir / "e6_governor.png"
    finish(fig, ax, out, backend, legend=False)
    return out


def plot_e5(backend: str, run_dir: Path) -> Path:
    rows = [r for r in read_rows(run_dir) if r["k"] == "8"]
    fig, ax = figure("E5 outcome of injected errors, K=8", backend, "Injection kind and C3 setting", "Trials")
    labels = [f"{r['kind']} C3={r['c3']}" for r in rows]
    x = range(len(rows))
    bottom = [0.0] * len(rows)
    for color, key in zip(SERIES, ("corrected", "recompute", "miscorrected", "escaped")):
        values = [float(r[key]) for r in rows]
        ax.bar(x, values, bottom=bottom, color=color, width=0.6, label=key, edgecolor=SURFACE, linewidth=1.0)
        bottom = [b + v for b, v in zip(bottom, values)]
    ax.set_xticks(list(x), labels, rotation=20, ha="right", fontsize=8)
    out = run_dir / "e5_outcomes.png"
    finish(fig, ax, out, backend)
    return out


def plot_e8(backend: str, run_dir: Path) -> Path:
    rows = [r for r in read_rows(run_dir) if r["part"] == "xc7s15"]
    fig, ax = figure("E8 block RAM needed against capacity of xc7s15", backend, "Model and K", "BRAM36 equivalents")
    labels = [f"{r['model']} K={r['K']}" for r in rows]
    x = range(len(rows))
    ax.bar(x, [float(r["bram36_needed"]) for r in rows], color=SERIES[0], width=0.6, label="needed (parameter estimate)")
    ax.axhline(float(rows[0]["bram36_available"]), color=SERIES[1], linewidth=1.5, label="xc7s15 capacity (unverified)")
    ax.set_xticks(list(x), labels, fontsize=8)
    out = run_dir / "e8_bram.png"
    finish(fig, ax, out, backend)
    return out


PLOTTERS = {"e1": plot_e1, "e2": plot_e2, "e3": plot_e3, "e4": plot_e4, "e6": plot_e6, "e5": plot_e5, "e8": plot_e8}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", default="all", choices=["all", "mock", "hw", "sim"])
    args = parser.parse_args()
    backends = ["mock", "hw", "sim"] if args.backend == "all" else [args.backend]
    produced = 0
    for backend in backends:
        for name, plotter in PLOTTERS.items():
            run_dir = latest_run(backend, name)
            if run_dir is None:
                continue
            path = plotter(backend, run_dir)
            produced += 1
            print(f"{LABELS.get(backend, '')} {path.relative_to(ROOT)}")
    print(f"{produced} plots")


if __name__ == "__main__":
    main()
