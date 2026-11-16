#!/usr/bin/env python3
"""Draw every figure of the SENTINEL study guide into build/study_guide/fig/.

Numbers come from result files in the repository, or are computed here from the golden model
(model/golden.py), the checker model (model/checker.py) and the governor model
(model/governor.py). Each figure carries its provenance label and the document captions repeat
it. Worked-example numbers are written to build/study_guide/facts.json for the document builder.

Run: python tools/study_guide/figures.py
"""
from __future__ import annotations

import csv
import json
import shutil
import sys
from datetime import date
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import patches as mp  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, to_rgb  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FACTS, FIG, ROOT, latest_run, load_json, nf, part_short, vivado_rows  # noqa: E402

sys.path.insert(0, str(ROOT))
from model import checker as ck  # noqa: E402
from model import governor as gv  # noqa: E402
from model.golden import QModel, forward, requant  # noqa: E402

# Validated categorical palette shared with sw/sentinel/plots/all.py (fixed order).
BLUE, ORANGE, GREEN, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df"
NAVY, RED, STA_GREEN, HW_PURPLE = "#1f3a5f", "#b3261e", "#127a55", "#6b3fa0"
W = 6.6  # text width of the A4 document, inches
CLASSES_ID = ["pesawat", "mobil", "burung", "kucing", "rusa", "anjing", "katak", "kuda", "kapal", "truk"]


def mix(color: str, f: float, other: str = "#ffffff") -> tuple:
    a, b = np.array(to_rgb(color)), np.array(to_rgb(other))
    return tuple(a * (1 - f) + b * f)


SAFE_FILL, FAST_FILL, HOST_FILL = mix(BLUE, 0.9), mix(ORANGE, 0.9), "#f2f1ee"


def setup() -> None:
    plt.rcParams.update({
        "font.family": ["Calibri", "Segoe UI Symbol", "DejaVu Sans"],
        "font.size": 8.5, "axes.titlesize": 9.5, "axes.titleweight": "bold", "axes.titlecolor": INK,
        "axes.titlelocation": "left", "axes.labelsize": 8.5, "axes.labelcolor": INK2,
        "axes.edgecolor": GRID, "axes.linewidth": 0.8, "axes.spines.top": False, "axes.spines.right": False,
        "xtick.color": INK2, "ytick.color": INK2, "xtick.labelsize": 8, "ytick.labelsize": 8,
        "xtick.major.size": 0, "ytick.major.size": 0, "grid.color": GRID, "grid.linewidth": 0.7,
        "legend.frameon": False, "legend.fontsize": 8, "figure.facecolor": "white", "axes.facecolor": "white",
        "savefig.dpi": 220, "savefig.facecolor": "white",
        "mathtext.fontset": "custom", "mathtext.rm": "Calibri", "mathtext.it": "Calibri:italic",
        "mathtext.bf": "Calibri:bold", "mathtext.fallback": "stixsans",
    })


def save(fig, name: str) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.png", bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    print(f"  {name}.png")


def tag(fig, text: str, color: str = BLUE) -> None:
    fig.text(0.998, 0.998, text, ha="right", va="top", fontsize=7.5, color=color, fontweight="bold")


def canvas(h_in: float):
    fig, ax = plt.subplots(figsize=(W, h_in))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100 * h_in / W)
    ax.axis("off")
    fig.subplots_adjust(0, 0, 1, 1)
    return fig, ax


def box(ax, x, y, w, h, text="", fc="white", ec=INK2, lw=1.0, fs=7.4, bold=False, color=INK, r=0.9, ls="-", z=2):
    ax.add_patch(mp.FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=fc, ec=ec, lw=lw, ls=ls, zorder=z))
    if text:
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=color,
                fontweight="bold" if bold else "normal", zorder=z + 1, linespacing=1.2)


def arrow(ax, pts, color=INK2, lw=1.0, ms=7, z=4):
    """Polyline arrow through the given points; the head sits on the last point."""
    pts = list(pts)
    if len(pts) > 2:
        xs, ys = zip(*pts[:-1])
        ax.plot(xs, ys, color=color, lw=lw, zorder=z, solid_capstyle="butt")
    ax.annotate("", xy=pts[-1], xytext=pts[-2], zorder=z,
                arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, shrinkA=0, shrinkB=0, mutation_scale=ms))


def bar_axis(ax, axis="y"):
    ax.grid(axis=axis, color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)


# --------------------------------------------------------------------------- data


def load_images():
    from model.data import load_cifar10

    ds = load_cifar10(False, download=False)
    return ds.images, ds.labels, ds.classes


def pick_image(qm, images, labels):
    """First test image among the first 100 that the integer model classifies correctly,
    restricted to visually clear classes (ship, automobile, airplane, horse, truck)."""
    preds = forward(qm, images[:100]).pred
    for idx in range(100):
        if labels[idx] in (8, 1, 0, 7, 9) and preds[idx] == labels[idx]:
            return idx
    return 0


# --------------------------------------------------------------------------- CNN basics


def fig_path():
    fig, ax = canvas(1.15)
    steps = [("Dasar\nCNN", "Bab 2"), ("Kuantisasi\nINT8", "Bab 3"), ("FPGA &\nVivado", "Bab 4"),
             ("Arsitektur\nSENTINEL", "Bab 5"), ("Tur\nrepo", "Bab 6"), ("Hasil\nsejauh ini", "Bab 7"),
             ("Menunggu\nboard", "Bab 8")]
    n, top = len(steps), 100 * 1.15 / W
    w, tip, y0, y1 = 100 / n, 2.6, 2.0, top - 2.0
    for i, (title, sub) in enumerate(steps):
        x0, x1 = i * w, (i + 1) * w - 0.5
        ym = (y0 + y1) / 2
        pts = [(x0, y0), (x1 - tip, y0), (x1, ym), (x1 - tip, y1), (x0, y1)]
        if i:
            pts.append((x0 + tip, ym))
        last = i == n - 1
        fc = "#ecebe8" if last else (mix(BLUE, 0.80) if i % 2 == 0 else mix(BLUE, 0.70))
        ax.add_patch(mp.Polygon(pts, closed=True, fc=fc, ec="white", lw=1.5))
        cx = (x0 + x1) / 2 + (0.9 if i else -0.4)
        ax.text(cx, ym + 2.0, title, ha="center", va="center", fontsize=7.6, fontweight="bold",
                color=INK2 if last else NAVY, linespacing=1.05)
        ax.text(cx, ym - 4.4, sub, ha="center", va="center", fontsize=6.8, color=INK2)
    save(fig, "fig_path")


def fig_tensor(img, label_name):
    fig = plt.figure(figsize=(W, 1.9))
    gs = fig.add_gridspec(1, 5, width_ratios=[1, 1, 1, 1, 1.15], wspace=0.22)
    r0, c0 = 12, 12
    ax0 = fig.add_subplot(gs[0])
    ax0.imshow(np.transpose(img, (1, 2, 0)), interpolation="nearest")
    ax0.set_title(f"RGB 32×32 ({label_name})", loc="center", fontsize=8.2)
    for i, (cmap, name) in enumerate(zip(["Reds", "Greens", "Blues"], ["kanal R", "kanal G", "kanal B"])):
        ax = fig.add_subplot(gs[i + 1])
        ax.imshow(img[i], cmap=cmap, vmin=0, vmax=255, interpolation="nearest")
        ax.set_title(name, loc="center", fontsize=8.2)
        if i == 0:
            ax.add_patch(mp.Rectangle((c0 - 0.5, r0 - 0.5), 5, 5, fill=False, ec=INK, lw=1.3))
    axv = fig.add_subplot(gs[4])
    crop = img[0, r0:r0 + 5, c0:c0 + 5].astype(int)
    axv.imshow(crop, cmap="Reds", vmin=-60, vmax=420, interpolation="nearest")
    for (y, x), v in np.ndenumerate(crop):
        axv.text(x, y, str(v), ha="center", va="center", fontsize=7.4, color=INK)
    for k in range(6):
        axv.axhline(k - 0.5, color="white", lw=1.2)
        axv.axvline(k - 0.5, color="white", lw=1.2)
    axv.set_title("nilai di kotak hitam", loc="center", fontsize=8.2)
    for ax in fig.axes:
        ax.set_xticks([])
        ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)
    tag(fig, "[SIM] data")
    save(fig, "fig_tensor")


def fig_activation():
    fig, ax = plt.subplots(figsize=(W * 0.66, 1.9))
    v = np.linspace(-6, 6, 400)
    ax.plot(v, np.maximum(0, v) / 6, color=BLUE, lw=2, label="ReLU(v) = max(0, v)  (diskalakan 1/6)")
    ax.plot(v, 1 / (1 + np.exp(-v)), color=ORANGE, lw=2, label="sigmoid σ(v) = 1 / (1 + e^(−v))")
    ax.text(5.05, 0.6, "ReLU", color=INK2, fontsize=8, ha="left", va="center")
    ax.text(-5.8, 0.06, "sigmoid", color=INK2, fontsize=8, ha="left", va="bottom")
    ax.axhline(0, color=GRID, lw=0.8)
    ax.axvline(0, color=GRID, lw=0.8)
    ax.set_xlabel("v (jumlah berbobot + bias)")
    ax.set_ylabel("keluaran")
    ax.legend(loc="upper left", fontsize=7.4)
    bar_axis(ax)
    tag(fig, "[SIM] ilustrasi")
    save(fig, "fig_activation")


def _grid(ax, x0, y0, m, face, fs=8.5, bold=None):
    rows, cols = m.shape
    for r in range(rows):
        for c in range(cols):
            x, y = x0 + c, y0 + rows - 1 - r
            ax.add_patch(mp.Rectangle((x, y), 1, 1, fc=face(r, c), ec="#b9b8b3", lw=0.8))
            v = m[r, c]
            txt = f"−{-v}" if v < 0 else str(v)
            ax.text(x + 0.5, y + 0.5, txt, ha="center", va="center", fontsize=fs,
                    fontweight="bold" if bold and bold(r, c) else "normal", color=INK)


def fig_conv(facts):
    x = np.array([[2, 4, 1, 0, 3], [5, 1, 3, 2, 1], [0, 2, 6, 4, 2], [1, 3, 2, 5, 0], [4, 0, 1, 2, 6]])
    k = np.array([[1, 0, -1], [2, 0, -2], [1, 0, -1]])
    out = np.array([[int((x[r:r + 3, c:c + 3] * k).sum()) for c in range(3)] for r in range(3)])
    orow, ocol = 1, 2
    fig, ax = plt.subplots(figsize=(W, 2.45))
    ax.set_xlim(-0.3, 16.3)
    ax.set_ylim(-2.6, 6.2)
    ax.set_aspect("equal")
    ax.axis("off")
    hl_in = mix(BLUE, 0.72)
    _grid(ax, 0, 0, x, lambda r, c: hl_in if orow <= r < orow + 3 and ocol <= c < ocol + 3 else "white")
    ax.add_patch(mp.Rectangle((ocol, 5 - orow - 3), 3, 3, fill=False, ec=BLUE, lw=2))
    ax.text(2.5, 5.45, "input X (5×5)", ha="center", fontsize=8.5, color=INK2)
    ax.text(5.75, 2.5, "∗", ha="center", va="center", fontsize=16, color=INK2)
    _grid(ax, 6.5, 1, k, lambda r, c: mix(ORANGE, 0.75))
    ax.text(8.0, 4.45, "filter W (3×3)", ha="center", fontsize=8.5, color=INK2)
    ax.text(10.25, 2.5, "=", ha="center", va="center", fontsize=16, color=INK2)
    _grid(ax, 11, 1, out, lambda r, c: mix(YELLOW, 0.6) if (r, c) == (orow, ocol) else "white",
          bold=lambda r, c: (r, c) == (orow, ocol))
    ax.text(12.5, 4.45, "output Y (3×3)", ha="center", fontsize=8.5, color=INK2)
    ax.annotate("", xy=(11 + ocol + 0.5, 1 + 2 - orow + 0.5), xytext=(ocol + 3.05, 5 - orow - 1.5),
                arrowprops=dict(arrowstyle="-|>", color=BLUE, lw=1.0, connectionstyle="arc3,rad=-0.28", mutation_scale=8))
    win = x[orow:orow + 3, ocol:ocol + 3]
    terms = [f"{win[i, j]}·({k[i, j]})" if k[i, j] < 0 else f"{win[i, j]}·{k[i, j]}" for i in range(3) for j in range(3)]
    line1 = "Y[1,2] = " + " + ".join(terms[:5]) + " +"
    line2 = "            " + " + ".join(terms[5:]) + f" = {out[orow, ocol]}"
    ax.text(0, -1.25, line1.replace("-", "−"), fontsize=8, color=INK, va="center")
    ax.text(0, -2.15, line2.replace("-", "−"), fontsize=8, color=INK, va="center")
    tag(fig, "[SIM] ilustrasi")
    save(fig, "fig_conv")
    facts["conv_example"] = {"x": x.tolist(), "k": k.tolist(), "out": out.tolist(), "pos": [orow, ocol]}


def fig_pool(facts):
    p = np.array([[12, 40, 7, 3], [25, 18, 9, 51], [0, 33, 64, 20], [8, 15, 30, 44]])
    tints = [mix(BLUE, 0.75), mix(ORANGE, 0.75), mix(GREEN, 0.75), mix(YELLOW, 0.7)]
    blk = lambda r, c: tints[(r // 2) * 2 + c // 2]  # noqa: E731
    out = p.reshape(2, 2, 2, 2).max(axis=(1, 3))
    fig, ax = plt.subplots(figsize=(W * 0.7, 1.75))
    ax.set_xlim(-0.3, 10.8)
    ax.set_ylim(-0.4, 4.9)
    ax.set_aspect("equal")
    ax.axis("off")
    _grid(ax, 0, 0, p, blk, bold=lambda r, c: p[r, c] == out[r // 2, c // 2])
    ax.text(2, 4.3, "Y (4×4) sesudah ReLU", ha="center", fontsize=8.3, color=INK2)
    ax.annotate("", xy=(6.6, 2), xytext=(4.4, 2), arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1.2, mutation_scale=9))
    ax.text(5.5, 2.45, "maxpool 2×2\nstride 2", ha="center", va="bottom", fontsize=7.6, color=INK2)
    _grid(ax, 7.2, 1, out, lambda r, c: tints[r * 2 + c], fs=9.5, bold=lambda r, c: True)
    ax.text(8.2, 3.3, "P (2×2)", ha="center", fontsize=8.3, color=INK2)
    tag(fig, "[SIM] ilustrasi")
    save(fig, "fig_pool")
    facts["pool_example"] = {"in": p.tolist(), "out": out.tolist()}


def _cuboid(ax, x, y, w, h, d, fc):
    dx, dy = d * 0.75, d * 0.55
    ax.add_patch(mp.Polygon([(x, y + h), (x + dx, y + h + dy), (x + w + dx, y + h + dy), (x + w, y + h)], closed=True,
                            fc=mix(fc, 0.45), ec="white", lw=0.8, zorder=3))
    ax.add_patch(mp.Polygon([(x + w, y), (x + w + dx, y + dy), (x + w + dx, y + h + dy), (x + w, y + h)], closed=True,
                            fc=mix(fc, 0.25, "#000000"), ec="white", lw=0.8, zorder=3))
    ax.add_patch(mp.Rectangle((x, y), w, h, fc=fc, ec="white", lw=0.8, zorder=4))


def fig_model(arch):
    fig, ax = canvas(2.35)
    base = 9.0
    shapes = [arch["layers"][0]["input"]] + [[l["output_channels"], l["input"][1] // 2, l["input"][2] // 2] for l in arch["layers"][:3]]
    xs = [2.0, 21.0, 40.0, 55.5]
    names = ["input", "conv1 + pool", "conv2 + pool", "conv3 + pool"]
    tints = [mix(BLUE, 0.35), BLUE, mix(BLUE, 0.15, "#000000"), mix(BLUE, 0.3, "#000000")]
    ops = ["konv 3×3\nReLU, maxpool", "konv 3×3\nReLU, maxpool", "konv 3×3\nReLU, maxpool"]
    rights = []
    for i, ((c, hh, _ww), x) in enumerate(zip(shapes, xs)):
        w = 0.7 + c * 0.13
        h = hh * 0.62
        d = h * 0.55
        _cuboid(ax, x, base + (20 - h) / 2 - 2, w, h, d, tints[i])
        rights.append(x + w + d * 0.75)
        ax.text(x + w / 2 + d * 0.35, 2.6, f"{names[i]}\n{c}×{hh}×{hh}", ha="center", va="center", fontsize=7.4, color=INK)
    for i in range(3):
        ax.annotate("", xy=(xs[i + 1] - 0.8, base + 8), xytext=(rights[i] + 0.8, base + 8),
                    arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1.0, mutation_scale=8))
        ax.text((rights[i] + xs[i + 1]) / 2, base + 10.2, ops[i], ha="center", va="bottom", fontsize=6.6, color=INK2)
    # flatten column, fc neurons, argmax
    fx = 69.5
    ax.annotate("", xy=(fx - 0.8, base + 8), xytext=(rights[3] + 0.8, base + 8), arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1.0, mutation_scale=8))
    for j in range(16):
        ax.add_patch(mp.Rectangle((fx, base - 1 + j * 1.25), 1.6, 1.1, fc=mix(BLUE, 0.15 + 0.04 * (j % 5)), ec="white", lw=0.5, zorder=3))
    ax.text(fx + 0.8, 2.6, "flatten\n512", ha="center", va="center", fontsize=7.4)
    nx = 80.0
    ax.annotate("", xy=(nx - 1.6, base + 8), xytext=(fx + 2.4, base + 8), arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1.0, mutation_scale=8))
    ax.text((fx + nx) / 2 + 0.2, base + 10.2, "fc", ha="center", va="bottom", fontsize=6.6, color=INK2)
    for j in range(10):
        ax.add_patch(mp.Circle((nx, base - 0.2 + j * 1.95), 0.75, fc=ORANGE if j == 8 else mix(ORANGE, 0.6), ec="white", lw=0.5, zorder=3))
    ax.text(nx, 2.6, "fc\n10 logit", ha="center", va="center", fontsize=7.4)
    ax.annotate("", xy=(88.5, base + 8), xytext=(nx + 1.6, base + 8), arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1.0, mutation_scale=8))
    box(ax, 89.0, base + 5.2, 10.5, 5.6, "argmax\n→ kelas", fc=mix(ORANGE, 0.85), ec=ORANGE, fs=7.4, bold=True)
    save(fig, "fig_model_s")


def fig_featuremaps(qm, img, idx, label, facts):
    res = forward(qm, img, trace=True)
    tr = res.trace
    c1, c2, logits = tr[0].output, tr[1].output, tr[3].output
    top1 = np.argsort(-c1.reshape(16, -1).std(axis=1), kind="stable")[:8]
    top2 = np.argsort(-c2.reshape(32, -1).std(axis=1), kind="stable")[:8]
    fig = plt.figure(figsize=(W, 3.55))
    gs = fig.add_gridspec(3, 9, height_ratios=[1, 1, 1.45], hspace=0.55, wspace=0.12)
    ax = fig.add_subplot(gs[0, 0])
    ax.imshow(np.transpose(img, (1, 2, 0)), interpolation="nearest")
    ax.set_title("input", loc="center", fontsize=8)
    for j, ch in enumerate(top1):
        a = fig.add_subplot(gs[0, j + 1])
        a.imshow(c1[ch], cmap="Greys_r", vmin=0, vmax=max(1, int(c1[ch].max())), interpolation="nearest")
        a.set_title(f"k{ch}", loc="center", fontsize=7, color=INK2, pad=2)
    for j, ch in enumerate(top2):
        a = fig.add_subplot(gs[1, j + 1])
        a.imshow(c2[ch], cmap="Greys_r", vmin=0, vmax=max(1, int(c2[ch].max())), interpolation="nearest")
        a.set_title(f"k{ch}", loc="center", fontsize=7, color=INK2, pad=2)
    for a in fig.axes:
        a.set_xticks([])
        a.set_yticks([])
        for s in a.spines.values():
            s.set_visible(False)
    fig.text(0.215, 0.965, "conv1 sesudah pool: 16×16, 8 dari 16 kanal", fontsize=8.2, fontweight="bold", color=INK)
    fig.text(0.215, 0.655, "conv2 sesudah pool: 8×8, 8 dari 32 kanal", fontsize=8.2, fontweight="bold", color=INK)
    axl = fig.add_subplot(gs[2, :])
    colors = [BLUE if i == res.pred else "#c9c8c3" for i in range(10)]
    axl.bar(range(10), logits, color=colors, width=0.62, edgecolor="white", linewidth=1)
    axl.set_xticks(range(10), CLASSES_ID, fontsize=7.8)
    axl.axhline(0, color=INK2, lw=0.8)
    axl.set_title("logit int32 dari fc (kelas = argmax)", fontsize=8.6)
    p = int(res.pred)
    axl.text(p, logits[p], f" {nf(int(logits[p]))}", ha="center", va="bottom", fontsize=7.6, color=INK)
    bar_axis(axl)
    axl.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: nf(v)))
    tag(fig, "[SIM]")
    save(fig, "fig_featuremaps")
    facts["image"] = {"index": int(idx), "label": int(label), "label_id": CLASSES_ID[label], "pred": p,
                      "pred_id": CLASSES_ID[p], "logits": [int(v) for v in logits]}
    return res


def fig_macs(arch):
    names = [l["name"] for l in arch["layers"]]
    macs = [l["macs"] for l in arch["layers"]]
    wts = [l["weights"] for l in arch["layers"]]
    fig, axes = plt.subplots(1, 2, figsize=(W, 2.05))
    for ax, vals, title in zip(axes, [macs, wts], ["MAC per gambar", "jumlah bobot"]):
        ax.bar(names, vals, color=BLUE, width=0.58, edgecolor="white", linewidth=1)
        for i, v in enumerate(vals):
            ax.text(i, v, nf(v), ha="center", va="bottom", fontsize=7.4, color=INK)
        ax.set_title(title, fontsize=9)
        ax.set_ylim(0, max(vals) * 1.18)
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: nf(v)))
        bar_axis(ax)
    tag(fig, "[SIM]")
    fig.tight_layout()
    save(fig, "fig_macs")


def fig_training(facts):
    rows = list(csv.DictReader(open(ROOT / "results/model/s/train_log.csv", encoding="utf-8")))
    ep = [int(r["epoch"]) for r in rows]
    loss = [float(r["train_loss"]) for r in rows]
    acc = [float(r["val_acc"]) * 100 for r in rows]
    fr = load_json("results/model/s/float_result.json")
    best = fr["best_epoch"]
    fig, axes = plt.subplots(1, 2, figsize=(W, 2.05))
    axes[0].plot(ep, loss, color=BLUE, lw=1.6)
    axes[0].set_title("loss training (cross-entropy)", fontsize=9)
    axes[0].set_xlabel("epoch")
    axes[1].plot(ep, acc, color=BLUE, lw=1.6)
    axes[1].plot([best], [acc[best]], "o", color=ORANGE, ms=6, mec="white", mew=1.5, zorder=5)
    axes[1].annotate(f"epoch terbaik {best}\nvalidasi {nf(acc[best], 2)}%", xy=(best, acc[best]), xytext=(58, 51.5),
                     fontsize=7.6, color=INK, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
    axes[1].set_title("akurasi validasi (%)", fontsize=9)
    axes[1].set_xlabel("epoch")
    for ax in axes:
        bar_axis(ax)
    tag(fig, "[SIM]")
    fig.tight_layout()
    save(fig, "fig_training")
    facts["training"] = {"best_epoch": best, "best_val": acc[best], "epochs": len(ep), "first_val": acc[0], "last_loss": loss[-1], "first_loss": loss[0]}


# --------------------------------------------------------------------------- quantisation


def fig_quant_stairs():
    s = 1 / 7
    r = np.linspace(-0.12, 1.12, 1200)
    q = np.clip(np.round(r / s), 0, 7)
    fig, axes = plt.subplots(1, 2, figsize=(W, 2.05), gridspec_kw={"width_ratios": [1.2, 1]})
    axes[0].plot(r, r, color=GRID, lw=1.2)
    axes[0].plot(r, q * s, color=BLUE, lw=1.8, drawstyle="steps-mid")
    axes[0].set_title("r → q → S·q (contoh 3 bit, 8 tingkat)", fontsize=9)
    axes[0].set_xlabel("nilai real r")
    axes[0].set_ylabel("rekonstruksi S·q")
    axes[0].text(0.62, 0.2, "garis abu-abu: tanpa kuantisasi", fontsize=7.4, color=INK2)
    err = r - q * s
    axes[1].plot(r, err, color=ORANGE, lw=1.4)
    axes[1].axhline(s / 2, color=GRID, lw=0.9)
    axes[1].axhline(-s / 2, color=GRID, lw=0.9)
    axes[1].text(0.0, s / 2 + 0.006, "+S/2", fontsize=7.4, color=INK2)
    axes[1].text(0.0, -s / 2 - 0.02, "−S/2", fontsize=7.4, color=INK2)
    axes[1].set_title("galat r − S·q", fontsize=9)
    axes[1].set_xlabel("nilai real r")
    for ax in axes:
        bar_axis(ax)
    tag(fig, "[SIM] ilustrasi")
    fig.tight_layout()
    save(fig, "fig_quant_stairs")


def fig_requant(qm, facts):
    lay = qm.layers[0]
    v = np.arange(-15000, 75001, 25)
    y = requant(v, lay.m, lay.n)
    v_sat = int(v[np.argmax(y >= 255)])
    lo = v_sat - 400
    while requant(np.array([lo]), lay.m, lay.n)[0] >= 255:
        lo -= 400
    for vv in range(lo, v_sat + 1):
        if requant(np.array([vv]), lay.m, lay.n)[0] >= 255:
            v_sat = vv
            break
    ex = facts["requant_example"]
    fig, ax = plt.subplots(figsize=(W, 2.1))
    ax.plot(v, y, color=BLUE, lw=2)
    ax.plot([ex["v"]], [ex["y"]], "o", color=ORANGE, ms=6, mec="white", mew=1.5, zorder=5)
    ax.annotate(f"contoh nyata: v = {nf(ex['v'])} → y = {ex['y']}", xy=(ex["v"], ex["y"]), xytext=(ex["v"] + 6000, ex["y"] - 70),
                fontsize=7.6, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
    ax.text(-14500, 45, "v < 0 → y = 0\n(berfungsi sebagai ReLU)", fontsize=7.6, color=INK2, va="bottom")
    ax.text(v_sat + 1500, 236, f"jenuh 255 mulai v = {nf(v_sat)}", fontsize=7.6, color=INK2, va="top")
    ax.set_xlabel("v = acc + bias (int32)")
    ax.set_ylabel("y (uint8)")
    ax.set_title(f"requant conv1: y = clamp((v·{lay.m} + 2^{lay.n - 1}) >> {lay.n}, 0, 255)", fontsize=9)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda val, _: nf(val)))
    ax.set_ylim(-12, 275)
    bar_axis(ax)
    tag(fig, "[SIM]")
    save(fig, "fig_requant")
    facts["requant_curve"] = {"m": lay.m, "n": lay.n, "v_sat": v_sat}


def fig_accuracy():
    models = ["s", "xs"]
    data = {m: (load_json(f"results/model/{m}/float_result.json"), load_json(f"results/model/{m}/quant_result.json")) for m in models}
    fl = [data[m][0]["test_acc_float"] * 100 for m in models]
    it = [data[m][1]["test_acc_integer"] * 100 for m in models]
    dr = [data[m][1]["drop_points"] for m in models]
    fig, axes = plt.subplots(1, 2, figsize=(W, 2.1), gridspec_kw={"width_ratios": [1.35, 1]})
    x = np.arange(2)
    for off, vals, color, name in [(-0.17, fl, BLUE, "float"), (0.17, it, ORANGE, "integer (golden model)")]:
        axes[0].bar(x + off, vals, width=0.32, color=color, label=name, edgecolor="white", linewidth=1)
        for xi, v in zip(x + off, vals):
            axes[0].text(xi, v + 1, nf(v, 2), ha="center", va="bottom", fontsize=7.2)
    axes[0].set_xticks(x, [f"model {m}" for m in models])
    axes[0].set_ylim(0, 100)
    axes[0].set_title("akurasi uji CIFAR-10 (%)", fontsize=9)
    axes[0].legend(loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.38), fontsize=7.6)
    axes[1].bar(x, dr, width=0.45, color=BLUE, edgecolor="white", linewidth=1)
    for xi, v in zip(x, dr):
        axes[1].text(xi, v + 0.05, nf(v, 2), ha="center", va="bottom", fontsize=7.4)
    axes[1].axhline(2.0, color=INK2, lw=1)
    axes[1].text(1.42, 2.06, "batas 2 poin (SPEC §4)", ha="right", va="bottom", fontsize=7.4, color=INK2)
    axes[1].set_xticks(x, [f"model {m}" for m in models])
    axes[1].set_ylim(0, 2.6)
    axes[1].set_title("penurunan (poin persen)", fontsize=9)
    for ax in axes:
        bar_axis(ax)
    tag(fig, "[SIM]")
    fig.tight_layout()
    save(fig, "fig_accuracy")


# --------------------------------------------------------------------------- FPGA


def fig_fpga_fabric():
    fig, ax = canvas(2.25)
    H = 100 * 2.25 / W
    x0, y0, x1, y1 = 1.0, 1.0, 64.0, H - 1.0
    ax.add_patch(mp.FancyBboxPatch((x0, y0), x1 - x0, y1 - y0, boxstyle="round,pad=0,rounding_size=1.2", fc="#fbfbfa", ec=INK2, lw=1.2))
    for i in range(30):
        xx = x0 + 1.2 + i * 2.07
        ax.add_patch(mp.Rectangle((xx, y1 - 1.3), 1.1, 0.8, fc=mix(INK2, 0.55), ec="none"))
        ax.add_patch(mp.Rectangle((xx, y0 + 0.5), 1.1, 0.8, fc=mix(INK2, 0.55), ec="none"))
    cols = ["c", "c", "b", "c", "c", "d", "c", "c", "c", "b", "c", "c", "d", "c", "c", "c", "c"]
    cx = x0 + 2.2
    for kind in cols:
        if kind == "c":
            for j in range(9):
                ax.add_patch(mp.Rectangle((cx, y0 + 2.6 + j * 3.0), 2.6, 2.4, fc=mix(INK2, 0.82), ec="white", lw=0.6))
            cx += 3.4
        elif kind == "b":
            for j in range(3):
                ax.add_patch(mp.Rectangle((cx, y0 + 2.6 + j * 9.0), 3.0, 8.4, fc=mix(BLUE, 0.55), ec="white", lw=0.6))
            cx += 3.9
        else:
            for j in range(4):
                ax.add_patch(mp.Rectangle((cx, y0 + 2.6 + j * 6.75), 3.0, 6.2, fc=mix(ORANGE, 0.45), ec="white", lw=0.6))
            cx += 3.9
    ax.plot([x0 + 1.0, x1 - 1.0], [(y0 + y1) / 2 + 0.3] * 2, color=GREEN, lw=1.4)
    lx = 67.5
    items = [(mix(INK2, 0.82), "CLB: LUT6 + flip-flop + carry chain\n(logika & register; UG474)"),
             (mix(BLUE, 0.55), "BRAM36: memori blok 36 Kb\n(bobot, aktivasi, FIFO; UG473)"),
             (mix(ORANGE, 0.45), "DSP48E1: pengali 25×18 + akumulator\n(UG479)"),
             (GREEN, "jaringan clock: MMCM, BUFG,\nBUFGCTRL (UG472)"),
             (mix(INK2, 0.55), "blok I/O di tepi chip\n(pin ke board)")]
    for i, (c, t) in enumerate(items):
        yy = y1 - 3.4 - i * 6.6
        if c == GREEN:
            ax.plot([lx, lx + 3.0], [yy + 1.0] * 2, color=GREEN, lw=1.6)
        else:
            ax.add_patch(mp.Rectangle((lx, yy), 3.0, 2.2, fc=c, ec="none"))
        ax.text(lx + 4.4, yy + 1.1, t, fontsize=7.3, va="center", color=INK, linespacing=1.15)
    save(fig, "fig_fpga_fabric")


def _clock(ax, y, period, x_start, x_end, first_edge, amp=3.2):
    xs, ys = [x_start], [y]
    e = first_edge
    while e < x_end:
        xs += [e, e, min(e + period / 2, x_end), min(e + period / 2, x_end)]
        ys += [y, y + amp, y + amp, y]
        e += period
    xs.append(x_end)
    ys.append(y)
    ax.plot(xs, ys, color=INK, lw=1.2)


def _bus(ax, y, t, x_start, x_end, amp=3.2, color=INK):
    s = 0.9
    ax.plot([x_start, t - s], [y, y], color=color, lw=1.1)
    ax.plot([x_start, t - s], [y + amp, y + amp], color=color, lw=1.1)
    ax.plot([t - s, t + s], [y, y + amp], color=color, lw=1.1)
    ax.plot([t - s, t + s], [y + amp, y], color=color, lw=1.1)
    ax.plot([t + s, x_end], [y, y], color=color, lw=1.1)
    ax.plot([t + s, x_end], [y + amp, y + amp], color=color, lw=1.1)


def fig_timing():
    fig, ax = canvas(3.25)
    # circuit
    box(ax, 6, 37.5, 9, 9, "FF1", fc=mix(BLUE, 0.85), ec=BLUE, fs=8, bold=True)
    ax.add_patch(mp.Ellipse((40, 42), 34, 9.5, fc=mix(ORANGE, 0.85), ec=ORANGE, lw=1.0))
    ax.text(40, 42, "logika kombinasional\n(pengali + penjumlah MAC)", ha="center", va="center", fontsize=7.6)
    box(ax, 65, 37.5, 9, 9, "FF2", fc=mix(BLUE, 0.85), ec=BLUE, fs=8, bold=True)
    arrow(ax, [(15, 42), (23, 42)])
    arrow(ax, [(57, 42), (65, 42)])
    ax.plot([3, 3, 70.5, 70.5], [37.5 - 2.5, 34.2, 34.2, 37.5 - 2.5], color=INK2, lw=0.9)
    ax.plot([10.5, 10.5], [34.2, 35.0], color=INK2, lw=0.9)
    ax.plot([10.5, 10.5], [35.0, 37.5], color=INK2, lw=0.9)
    ax.plot([70.5, 70.5], [35.0, 37.5], color=INK2, lw=0.9)
    ax.text(1.0, 34.2, "clk", fontsize=7.6, color=INK2, va="center", ha="left")
    ax.text(77, 45.5, "t_cq: clock → Q di FF1\nt_logika + t_route: jalur\nt_setup: data harus stabil\nsebelum tepi clock FF2", fontsize=7.2, color=INK2, va="top", linespacing=1.2)
    # waveforms
    lab_x = 1.0
    ax.text(lab_x, 27.0, "clock aman\n(periode T_aman)", fontsize=7.4, va="center", color=INK)
    ax.text(lab_x, 20.0, "data di D FF2", fontsize=7.4, va="center", color=INK)
    ax.text(lab_x, 10.0, "clock turbo\n(T_turbo < T_aman)", fontsize=7.4, va="center", color=INK)
    ax.text(lab_x, 3.0, "data di D FF2", fontsize=7.4, va="center", color=INK)
    e0, ta, tt, setup = 24.0, 52.0, 40.0, 5.0
    arr_t = e0 + 37.0
    _clock(ax, 25.4, ta, 18, 99, e0)
    _bus(ax, 18.4, arr_t, 18, 99)
    ax.add_patch(mp.Rectangle((e0 + ta - setup, 17.6), setup, 13.5, fc=mix(GREEN, 0.8), ec="none", zorder=0))
    ax.annotate("", xy=(e0 + ta - setup, 23.0), xytext=(arr_t + 1, 23.0), arrowprops=dict(arrowstyle="<->", color=GREEN, lw=1.0, mutation_scale=7))
    ax.text((arr_t + e0 + ta - setup) / 2, 23.6, "slack > 0", ha="center", va="bottom", fontsize=7.2, color=STA_GREEN)
    _clock(ax, 8.4, tt, 18, 99, e0)
    _bus(ax, 1.4, arr_t, 18, 99, color=RED)
    ax.add_patch(mp.Rectangle((e0 + tt - setup, 0.6), setup, 13.5, fc=mix(RED, 0.82), ec="none", zorder=0))
    ax.text(e0 + tt + 1.5, 6.4, "data tiba di dalam jendela setup:\nFF2 menangkap nilai lama/acak = error timing", fontsize=7.2, color=RED, va="center")
    ax.text(e0 - 0.4, 30.0, "tepi 1", fontsize=6.8, color=INK2, ha="center")
    ax.text(e0 + ta, 30.0, "tepi 2", fontsize=6.8, color=INK2, ha="center")
    save(fig, "fig_timing")


def fig_vivado_flow():
    fig, ax = canvas(1.95)
    rows = [
        (17.0, "Alur OOC\n(sudah berjalan)", [("RTL\nrtl/*.v", True), ("Sintesis\nsynth_design", True), ("Optimasi\nopt_design", True),
                                              ("Place\nplace_design", True), ("Route\nroute_design", True), ("Laporan timing\n& utilisasi", True)]),
        (3.0, "Alur board\n(menunggu board)", [("XDC pin\n(BOARD_INFO)", False), ("Sintesis +\nimplementasi", False), ("Bitstream\nwrite_bitstream", False),
                                               ("Program\nZERO7", False), ("Bring-up\nbringup.py", False), ("Eksperimen\n[HW]", False)]),
    ]
    for y, label, items in rows:
        ax.text(0.5, y + 4.5, label, fontsize=7.6, fontweight="bold", color=NAVY if items[0][1] else INK2, va="center")
        for i, (t, done) in enumerate(items):
            x = 15.5 + i * 14.1
            box(ax, x, y, 12.4, 9.0, t, fc=mix(BLUE, 0.85) if done else "#efeeeb", ec=BLUE if done else MUTED, fs=7.1, ls="-" if done else (0, (3, 2)))
            if i:
                arrow(ax, [(x - 1.6, y + 4.5), (x, y + 4.5)], color=INK2 if done else MUTED)
    save(fig, "fig_vivado_flow")


# --------------------------------------------------------------------------- SENTINEL architecture


def fig_system():
    fig, ax = canvas(4.3)
    box(ax, 0.5, 16, 16, 44, "", fc=HOST_FILL, ec=MUTED, lw=1.1, r=1.4, z=1)
    ax.text(8.5, 57.0, "Raspberry Pi", ha="center", fontsize=8.4, fontweight="bold", color=INK)
    for yb, t in [(46, "driver.py"), (37, "kamera +\npreprocess"), (28, "dashboard"), (19, "eksperimen\nE1–E8")]:
        box(ax, 2.2, yb, 12.6, 6.3, t, fc="white", ec=MUTED, fs=7.2)
    box(ax, 20.5, 14, 41, 49, "", fc=SAFE_FILL, ec=BLUE, lw=1.2, r=1.4, z=1)
    ax.text(41, 60.6, "domain clk_safe (wajib lolos timing)", ha="center", fontsize=8.2, fontweight="bold", color=NAVY)
    box(ax, 72.5, 14, 27, 49, "", fc=FAST_FILL, ec=ORANGE, lw=1.2, r=1.4, z=1)
    ax.text(86, 60.6, "domain clk_fast (di-overclock)", ha="center", fontsize=8.2, fontweight="bold", color="#8a3a12")
    blue_boxes = [(22, 49, "spi_slave + regfile\n(spec/regmap.yaml)"), (41, 49, "RAM: bobot, parameter,\nIMG0/IMG1, ACT0/ACT1"),
                  (22, 38, "engine: tabel layer,\nlog recompute, counter"), (41, 38, "operand_gen + wc_gen\n(R = 2 set per siklus)"),
                  (22, 27, "postproc + pool\n(requant, maxpool)"), (41, 27, "lane_checker\n(d1, d2, d3 → koreksi)"),
                  (22, 16, "governor + clk_seq\n(clock per layer)")]
    for x, y, t in blue_boxes:
        box(ax, x, y, 17.5 if x == 22 else 19, 8, t, fc="white", ec=BLUE, fs=7.0)
    box(ax, 74, 50, 24, 7, "slot serializer\n(baca FIFO operand)", fc="white", ec=ORANGE, fs=7.0)
    ax.text(74.4, 45.8, "lane MAC: K data + checksum", ha="left", fontsize=7.0, color=INK)
    lanes = [("1", BLUE), ("2", BLUE), ("…", None), ("K", BLUE), ("C1", GREEN), ("C2", GREEN), ("C3", "dash")]
    for i, (t, c) in enumerate(lanes):
        x = 74.4 + i * 3.37
        if c is None:
            ax.text(x + 1.4, 38.5, "…", ha="center", va="center", fontsize=9, color=INK2)
            continue
        box(ax, x, 34.5, 2.8, 8.5, t, fc="white" if c == "dash" else mix(c, 0.75), ec=MUTED if c == "dash" else c,
            fs=6.6, r=0.5, ls=(0, (2, 1.5)) if c == "dash" else "-")
    box(ax, 74, 23.5, 24, 7.5, "register holding +\nserializer hasil", fc="white", ec=ORANGE, fs=7.0)
    box(ax, 62.6, 46.5, 9, 8.5, "FIFO\noperand\n(CDC)", fc="white", ec=INK2, fs=6.8)
    box(ax, 62.6, 23.0, 9, 8.5, "FIFO\nhasil\n(CDC)", fc="white", ec=INK2, fs=6.8)
    box(ax, 41, 1, 58.5, 9.5, "clk_gen:  MMCM1 → clk_safe   ·   MMCM2 (rekonfigurasi) → clk_turbo\nBUFGCTRL(clk_safe, clk_turbo) → clk_fast",
        fc=HOST_FILL, ec=MUTED, fs=7.1)
    arrow(ax, [(16.5, 49.2), (22, 49.2)])
    ax.text(19.2, 50.2, "SPI", ha="center", fontsize=6.8, color=INK2)
    arrow(ax, [(39.5, 53), (41, 53)])
    arrow(ax, [(50.5, 49), (50.5, 46)])
    arrow(ax, [(39.5, 42), (41, 42)])
    arrow(ax, [(60, 42), (61.8, 42), (61.8, 50.7), (62.6, 50.7)])
    arrow(ax, [(71.6, 50.7), (73.2, 50.7), (73.2, 53.5), (74, 53.5)])
    arrow(ax, [(96, 50), (96, 43)])
    arrow(ax, [(96, 34.5), (96, 31)])
    arrow(ax, [(74, 27.2), (71.6, 27.2)])
    arrow(ax, [(62.6, 27.2), (61.8, 27.2), (61.8, 31), (60, 31)])
    arrow(ax, [(41, 31), (39.5, 31)])
    arrow(ax, [(39.5, 29), (40.25, 29), (40.25, 50.5), (41, 50.5)])
    arrow(ax, [(30.75, 16), (30.75, 5.8), (41, 5.8)])
    arrow(ax, [(56, 10.5), (56, 14)])
    ax.text(56.8, 11.9, "clk_safe", fontsize=6.6, color=INK2, va="center")
    arrow(ax, [(90, 10.5), (90, 14)])
    ax.text(90.8, 11.9, "clk_fast", fontsize=6.6, color=INK2, va="center")
    save(fig, "fig_system")


def fig_dataflow():
    fig, ax = canvas(3.1)
    H = 100 * 3.1 / W
    ax.add_patch(mp.Rectangle((27.5, 0.5), 34.5, H - 1.0, fc=FAST_FILL, ec="none", zorder=0))
    ax.add_patch(mp.Rectangle((63.0, 0.5), 36.5, H - 1.0, fc=SAFE_FILL, ec="none", zorder=0))
    ax.text(1.0, H - 2.2, "clk_safe: bobot dan bobot checksum", fontsize=7.4, color=NAVY, fontweight="bold", va="center")
    ax.text(28.5, H - 2.2, "clk_fast: lane MAC", fontsize=7.4, color="#8a3a12", fontweight="bold", va="center")
    ax.text(64.0, H - 2.2, "clk_safe: komparator", fontsize=7.4, color=NAVY, fontweight="bold", va="center")
    bus_x = 33.0
    ax.plot([bus_x, bus_x], [H - 6.0, 3.0], color=INK, lw=1.4, zorder=1)
    ax.text(bus_x + 1.0, H - 5.4, "a(t): satu aktivasi, disiarkan ke semua lane", fontsize=7.0, color=INK, va="center")
    rows = [(36.5, r"$w_1(t)$", r"$Y_1$", BLUE), (30.5, r"$w_2(t)$", r"$Y_2$", BLUE), (24.5, None, None, None),
            (18.5, r"$w_K(t)$", r"$Y_K$", BLUE), (11.0, r"$wc_1(t)=\sum_k w_k(t)$", r"$S_1$", GREEN),
            (4.5, r"$wc_2(t)=\sum_k k\cdot w_k(t)$", r"$S_2$", GREEN)]
    for y, wt, out, c in rows:
        if wt is None:
            for xx in (13.5, 40, 47.5):
                ax.text(xx, y, "⋮", ha="center", va="center", fontsize=11, color=INK2)
            continue
        box(ax, 1.0, y - 2.1, 25.0, 4.2, "", fc="white", ec=c, fs=7.4)
        ax.text(13.5, y, wt, ha="center", va="center", fontsize=8.6)
        arrow(ax, [(26.0, y), (31.3, y)])
        ax.add_patch(mp.Circle((bus_x, y), 1.6, fc="white", ec=INK, lw=1.0, zorder=5))
        ax.text(bus_x, y, "×", ha="center", va="center", fontsize=9, zorder=6)
        arrow(ax, [(34.6, y), (38.4, y)])
        ax.add_patch(mp.Circle((40.0, y), 1.6, fc="white", ec=INK, lw=1.0, zorder=5))
        ax.text(40.0, y, "+", ha="center", va="center", fontsize=9, zorder=6)
        arrow(ax, [(41.6, y), (44.0, y)])
        box(ax, 44.0, y - 1.7, 7.0, 3.4, "acc", fc=mix(c, 0.8), ec=c, fs=7.2, r=0.5)
        arrow(ax, [(47.5, y - 1.7), (47.5, y - 2.6), (40.0, y - 2.6), (40.0, y - 1.6)], lw=0.8, ms=5)
        ax.text(54.3, y + 0.15, out, ha="center", va="center", fontsize=9)
        arrow(ax, [(56.5, y), (65.0, y)], color=MUTED)
    box(ax, 65.0, 2.5, 33.5, 37.5, "", fc="white", ec=BLUE, lw=1.1)
    ax.text(81.75, 34.5, "lane_checker", ha="center", fontsize=8.4, fontweight="bold", color=NAVY)
    ax.text(81.75, 30.2, "(hasil datang lewat FIFO hasil)", ha="center", fontsize=7.0, color=INK2)
    ax.text(81.75, 22.5, r"$d_1=\sum_k Y_k - S_1$", ha="center", fontsize=9.4)
    ax.text(81.75, 17.0, r"$d_2=\sum_k k\cdot Y_k - S_2$", ha="center", fontsize=9.4)
    ax.text(81.75, 9.0, "CLEAN · CORRECTED(j)\n· RECOMPUTE", ha="center", va="center", fontsize=7.6, color=INK)
    save(fig, "fig_dataflow")


def fig_decision():
    fig, ax = canvas(3.75)
    cx, cw, bh = 21.5, 47.0, 6.4
    ys = [49.0, 40.0, 31.0, 22.0, 13.0, 4.0]
    texts = ["satu unit selesai: Y_1 … Y_K dari lane data; S1, S2, (S3) dari lane checksum",
             "d1 = ΣY_k − S1      d2 = Σk·Y_k − S2      d3 = Σk²·Y_k − S3",
             "MODE = 2 (CORRECT)?",
             "d1 = d2 = d3 = 0 ?",
             "d1 ≠ 0 dan ada j ∈ {1…K} dengan d2 = j·d1\n(dan d3 = j²·d1 bila C3 aktif)?",
             "TRUST_CSUM_LANE = 1 dan hanya\nsatu selisih yang bukan nol?"]
    for i, (y, t) in enumerate(zip(ys, texts)):
        decision = i >= 2
        box(ax, cx, y, cw, bh, t, fc="#f6f5f2" if decision else mix(BLUE, 0.88), ec=INK2 if decision else BLUE, fs=7.4, bold=decision and i == 2)
        if i:
            arrow(ax, [(cx + cw / 2, ys[i - 1]), (cx + cw / 2, y + bh)])
    for i, lab in [(3, "ya"), (4, "tidak"), (5, "tidak")]:
        ax.text(cx + cw / 2 + 1.0, ys[i] + bh + 1.3, lab, fontsize=6.9, color=INK2, va="center")
    ox, ow = 73.0, 26.5
    outs = [(2, "MODE 0: tanpa cek\nMODE 1: d1 ≠ 0 → RECOMPUTE", "#efeeeb", MUTED, "tidak"),
            (3, "CLEAN\nhasil dipakai", mix(GREEN, 0.82), GREEN, "ya"),
            (4, "CORRECTED(j)\nY_j ← Y_j − d1", mix(BLUE, 0.8), BLUE, "ya"),
            (5, "CSUM_LANE\nerror di lane checksum", mix(NAVY, 0.85), NAVY, "ya")]
    for i, t, fc, ec, lab in outs:
        box(ax, ox, ys[i], ow, bh, t, fc=fc, ec=ec, fs=7.3)
        arrow(ax, [(cx + cw, ys[i] + bh / 2), (ox, ys[i] + bh / 2)])
        ax.text((cx + cw + ox) / 2, ys[i] + bh / 2 + 0.9, lab, ha="center", fontsize=6.9, color=INK2)
    box(ax, 0.5, ys[5] - 2.6, 17.5, 11.6, "RECOMPUTE\ncatat di log,\nhitung ulang\ndi clk_safe", fc=mix(YELLOW, 0.75), ec=YELLOW, fs=7.3)
    arrow(ax, [(cx, ys[5] + bh / 2), (18.0, ys[5] + bh / 2)])
    ax.text(19.75, ys[5] + bh / 2 + 0.9, "tidak", ha="center", fontsize=6.9, color=INK2)
    save(fig, "fig_decision")


def fig_clockswitch():
    fig, ax = canvas(2.15)
    rows = {"clk": 20.5, "act": 11.5, "lock": 3.0}
    ax.text(13.2, rows["clk"] + 3.0, "clk_fast memakai", ha="right", va="center", fontsize=7.4)
    ax.text(13.2, rows["act"] + 3.0, "pekerjaan engine", ha="right", va="center", fontsize=7.4)
    ax.text(13.2, rows["lock"] + 2.5, "MMCM2 LOCKED", ha="right", va="center", fontsize=7.4)
    segs = [("conv1", "T", 14, 27), ("R", "S", 27, 30.5), ("conv2", "T", 30.5, 46), ("R", "S", 46, 49.5), ("conv3", "T", 49.5, 59.5),
            ("R", "S", 59.5, 63), ("fc", "T", 63, 66.5), ("governor + rekonfigurasi\nMMCM2", "S", 66.5, 84), ("conv1 gambar\nberikut (L baru)", "T", 84, 99.5)]
    for name, kind, a, b in segs:
        fc = mix(ORANGE, 0.55) if kind == "T" else mix(BLUE, 0.6)
        ax.add_patch(mp.Rectangle((a, rows["clk"]), b - a, 6.0, fc=fc, ec="white", lw=1.2))
        ax.add_patch(mp.Rectangle((a, rows["act"]), b - a, 6.0, fc="#f6f5f2", ec="white", lw=1.2))
        ax.text((a + b) / 2, rows["act"] + 3.0, name, ha="center", va="center", fontsize=6.6 if "\n" in name else 7.2, linespacing=1.05)
        if b - a > 6:
            ax.text((a + b) / 2, rows["clk"] + 3.0, "turbo" if kind == "T" else "aman", ha="center", va="center", fontsize=7.2)
    lx = [14, 70, 70, 80, 80, 99.5]
    ly = [7.0, 7.0, 3.0, 3.0, 7.0, 7.0]
    ax.plot(lx, [v + rows["lock"] - 3.0 for v in ly], color=INK, lw=1.3)
    ax.plot([14, 66.5], [28.3, 28.3], color=INK2, lw=0.9)
    ax.text(40.25, 29.3, "satu gambar (4 layer)", ha="center", fontsize=7.2, color=INK2)
    ax.plot([66.5, 84], [28.3, 28.3], color=INK2, lw=0.9)
    ax.text(75.25, 29.3, "di antara gambar", ha="center", fontsize=7.2, color=INK2)
    ax.text(14.0, 0.4, "R = unit gagal dihitung ulang di clock aman. sel hanya berubah saat domain cepat idle (SPEC §7.7).",
            fontsize=6.8, color=INK2, va="bottom")
    save(fig, "fig_clockswitch")


def fig_governor(facts):
    params = gv.GovParams()
    n_layers, n_img = 4, 64
    fails = {18: [0, 1, 0, 0], 31: [0, 0, 2, 0], 52: [1, 0, 0, 0]}
    corr = {44: [6, 9, 5, 0]}
    st = gv.reset(params, n_layers)
    levels, turbo = [], []
    for i in range(n_img):
        st = gv.step(st, params, fails.get(i, [0] * n_layers), corr.get(i, [0] * n_layers))
        levels.append(st.level)
        turbo.append(list(st.turbo_en))
    fig, axes = plt.subplots(2, 1, figsize=(W, 2.75), sharex=True, gridspec_kw={"height_ratios": [2.1, 1.0], "hspace": 0.18})
    x = np.arange(n_img)
    axes[0].step(x, levels, where="post", color=BLUE, lw=1.8, label="level L (indeks tabel frekuensi turbo)")
    for i in fails:
        axes[0].plot(i, levels[i], "X", color=ORANGE, ms=7, mec="white", mew=0.8, zorder=5)
    for i in corr:
        axes[0].plot(i, levels[i], "^", color=YELLOW, ms=7, mec="white", mew=0.8, zorder=5)
    axes[0].plot([], [], "X", color=ORANGE, ms=7, label="ada unit gagal (fails > 0)")
    axes[0].plot([], [], "^", color=YELLOW, ms=7, label="koreksi > CORR_HI")
    axes[0].set_ylabel("level L")
    axes[0].yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
    axes[0].legend(loc="upper left", fontsize=7.2, ncol=3, bbox_to_anchor=(0, 1.22))
    bar_axis(axes[0])
    mat = np.array(turbo).T
    cmap = LinearSegmentedColormap.from_list("t", ["#e4e3df", mix(ORANGE, 0.35)])
    axes[1].imshow(mat, aspect="auto", cmap=cmap, vmin=0, vmax=1, interpolation="nearest", extent=(-0.5, n_img - 0.5, n_layers - 0.5, -0.5))
    axes[1].set_yticks(range(n_layers), ["conv1", "conv2", "conv3", "fc"], fontsize=7.4)
    axes[1].set_xlabel("gambar ke-")
    axes[1].set_title("turbo_en per layer (oranye = boleh turbo, abu-abu = cooldown)", fontsize=8, pad=3)
    for s in axes[1].spines.values():
        s.set_visible(False)
    tag(fig, "[SIM] event ilustrasi")
    save(fig, "fig_governor")
    facts["governor"] = {"params": {"n_up": params.n_up, "cooldown": params.cooldown, "corr_hi": params.corr_hi, "l_min": params.l_min, "l_max": params.l_max},
                         "fail_images": sorted(fails), "corr_images": sorted(corr), "levels": levels}


def fig_pipeline():
    fig, ax = canvas(2.55)
    top = [("config/*.yaml\nparameter model & HW", True), ("model/train.py\nlatih float (PyTorch)", True),
           ("model/export.py\nPTQ → INT8, M dan n", True), ("tools/run.py gen\nvektor uji (build/)", True),
           ("tb/*.v + Icarus/xsim\nbandingkan bit-exact", True)]
    bottom = [("fpga/run_matrix.py\nVivado OOC [VIVADO-STA]", True), ("board/build_bitstream.py\nXDC + bitstream", False),
              ("board/bringup.py\nbring-up di Raspberry Pi", False), ("sw/sentinel/experiments\nE1–E7 → results/hw", False),
              ("docs/REPORT_DRAFT.md\nlaporan dan slide", False)]
    yt, yb, bw, bh = 21.0, 3.0, 18.2, 10.0
    for i, (t, done) in enumerate(top):
        x = 0.5 + i * 20.0
        box(ax, x, yt, bw, bh, t, fc=mix(BLUE, 0.85), ec=BLUE, fs=7.0)
        if i:
            arrow(ax, [(x - 1.8, yt + bh / 2), (x, yt + bh / 2)])
    for i, (t, done) in enumerate(bottom):
        x = 80.5 - i * 20.0
        box(ax, x, yb, bw, bh, t, fc=mix(BLUE, 0.85) if done else "#efeeeb", ec=BLUE if done else MUTED, fs=7.0, ls="-" if done else (0, (3, 2)))
        if i:
            arrow(ax, [(x + bw + 1.8, yb + bh / 2), (x + bw, yb + bh / 2)], color=INK2 if i == 1 else MUTED)
    arrow(ax, [(89.6, yt), (89.6, yb + bh)])
    ax.text(0.5, 35.4, "biru: sudah berjalan   ·   abu-abu putus-putus: menunggu board", fontsize=7.2, color=INK2, va="center")
    save(fig, "fig_pipeline")


# --------------------------------------------------------------------------- results


def fig_campaign():
    d = load_json("results/sim/campaign_s.json")
    kinds = [("single", "1 lane"), ("dual", "2 lane"), ("csum", "lane checksum")]
    fig, axes = plt.subplots(1, 2, figsize=(W, 2.55), sharey=True)
    for ax, k in zip(axes, (8, 16)):
        labels, rows = [], []
        for kind, kname in kinds:
            for c3 in (0, 1):
                r = next(r for r in d["rows"] if r["k"] == k and r["c3"] == c3 and r["kind"] == kind)
                labels.append(f"{kname}, {'dengan' if c3 else 'tanpa'} C3")
                rows.append(r)
        y = np.arange(len(rows))[::-1]
        left = np.zeros(len(rows))
        for key, color, name in [("corrected", BLUE, "terkoreksi"), ("recompute", YELLOW, "dihitung ulang"), ("miscorrected", ORANGE, "salah koreksi")]:
            vals = np.array([100 * r[key] / r["n"] for r in rows])
            ax.barh(y, vals, left=left, color=color, height=0.62, edgecolor="white", linewidth=1, label=name)
            left += vals
        for yi, r in zip(y, rows):
            if r["miscorrected"]:
                ax.text(101.5, yi, f"{nf(r['miscorrected'])} dari {nf(r['n'])}\nsalah koreksi", va="center", fontsize=6.8, color=INK, linespacing=1.0)
            main = "corrected" if r["corrected"] else "recompute"
            share = 100 * r[main] / r["n"]
            ax.text(2.0, yi, f"{nf(share, 1 if share % 1 else 0)}%", va="center", fontsize=7.0, color="white" if main == "corrected" else INK)
        ax.set_yticks(y, labels, fontsize=7.6)
        ax.set_xlim(0, 135)
        ax.set_xticks([0, 25, 50, 75, 100])
        ax.set_title(f"K = {k}", fontsize=9)
        ax.set_xlabel("% dari percobaan")
        bar_axis(ax, "x")
    handles, names = axes[0].get_legend_handles_labels()
    fig.legend(handles, names, loc="lower center", ncol=3, bbox_to_anchor=(0.55, -0.06), fontsize=7.6)
    tag(fig, "[SIM]")
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    save(fig, "fig_campaign")


def fig_fmax():
    rows = vivado_rows()
    sel = lambda p, k, impl, c3: next(r for r in rows if r["part"] == p and r["K"] == k and r["LANE_IMPL"] == impl and r["C3_EN"] == c3)  # noqa: E731
    parts = ["xc7s25csga225-1", "xc7s25csga225-2", "xc7s50ftgb196-1", "xc7s50ftgb196-2"]
    fig, axes = plt.subplots(1, 2, figsize=(W, 2.55), gridspec_kw={"width_ratios": [1.45, 1]})
    x = np.arange(len(parts))
    for off, key, color, name in [(-0.18, "fmax_safe_mhz", BLUE, "clk_safe"), (0.18, "fmax_fast_mhz", ORANGE, "clk_fast")]:
        vals = [float(sel(p, "8", "0", "0")[key]) for p in parts]
        axes[0].bar(x + off, vals, width=0.34, color=color, label=name, edgecolor="white", linewidth=1)
        for xi, v in zip(x + off, vals):
            axes[0].text(xi, v + 3, nf(v, 1), ha="center", va="bottom", fontsize=6.8)
    axes[0].set_xticks(x, [part_short(p) for p in parts], fontsize=7.6)
    axes[0].set_ylim(0, 205)
    axes[0].set_ylabel("Fmax STA (MHz)")
    axes[0].set_title("lane lut, K = 8, C3 = 0", fontsize=9)
    axes[0].legend(loc="upper left", ncol=2, fontsize=7.4, bbox_to_anchor=(0, 1.02))
    impls = [("0", "lut"), ("1", "dsp_min"), ("2", "dsp_full")]
    p = "xc7s25csga225-1"
    fast = [float(sel(p, "8", i, "0")["fmax_fast_mhz"]) for i, _ in impls]
    supply = [2 * float(sel(p, "8", i, "0")["fmax_safe_mhz"]) for i, _ in impls]
    xi = np.arange(3)
    axes[1].bar(xi, fast, width=0.5, color=ORANGE, edgecolor="white", linewidth=1, label="Fmax clk_fast")
    for j in range(3):
        axes[1].plot([j - 0.33, j + 0.33], [supply[j]] * 2, color=INK, lw=1.8, label="batas suplai R·f_safe (R = 2)" if j == 0 else None)
        axes[1].text(j, fast[j] + 4 if fast[j] < supply[j] - 20 else min(fast[j], supply[j]) - 32, nf(fast[j], 1), ha="center", va="bottom", fontsize=6.8,
                     color=INK if fast[j] < supply[j] - 20 else "white")
    axes[1].set_xticks(xi, [n for _, n in impls], fontsize=7.6)
    axes[1].set_ylim(0, 370)
    axes[1].set_title(f"{part_short(p)}: jenis lane", fontsize=9)
    axes[1].legend(loc="upper left", fontsize=7.0, bbox_to_anchor=(0, 1.04))
    for ax in axes:
        bar_axis(ax)
    tag(fig, "[VIVADO-STA]", STA_GREEN)
    fig.tight_layout()
    save(fig, "fig_fmax")


def fig_roadmap():
    import matplotlib.dates as mdates

    fig = plt.figure(figsize=(W, 2.45))
    gs = fig.add_gridspec(2, 1, height_ratios=[1.0, 1.35], hspace=0.25)
    ax = fig.add_subplot(gs[0])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 10)
    ax.axis("off")
    chips = [(f"M{i}", "part" if i == 10 else "done") for i in range(15)] + [(f"B{i}", "todo") for i in range(1, 7)]
    x = 0.3
    for i, (t, st) in enumerate(chips):
        if i == 15:
            x += 2.6
        fc = {"done": BLUE, "part": YELLOW, "todo": "#e4e3df"}[st]
        box(ax, x, 4.2, 4.0, 4.6, t, fc=fc, ec="white", fs=6.8, color="white" if st == "done" else INK, bold=True, r=0.6)
        x += 4.45
    ax.text(33.6, 1.6, "pra-board: selesai di simulasi (M10 sebagian: rekonfigurasi MMCM asli belum)", ha="center", fontsize=7.0, color=INK2)
    ax.text(84.5, 1.6, "fase board: belum mulai", ha="center", fontsize=7.0, color=INK2)
    ax2 = fig.add_subplot(gs[1])
    d0, d1 = date(2026, 11, 1), date(2027, 3, 15)
    ax2.set_xlim(d0, d1)
    ax2.set_ylim(-3.2, 3.2)
    ax2.axhline(0, color=INK2, lw=1)
    for s in ax2.spines.values():
        s.set_visible(False)
    ax2.set_yticks([])
    months = [date(2026, 11, 1), date(2026, 12, 1), date(2027, 1, 1), date(2027, 2, 1), date(2027, 3, 1)]
    ax2.set_xticks(months, ["Nov 2026", "Des", "Jan 2027", "Feb", "Mar"], fontsize=7.4)
    ev = [(date(2026, 11, 16), "hari ini\n16 Nov", "now", 1), (date(2026, 12, 13), "G1 (internal)\n13 Des", "int", -1),
          (date(2027, 1, 3), "G2 (internal)\n3 Jan", "int", 1), (date(2027, 1, 17), "bekukan HW\n17 Jan", "int", -1),
          (date(2027, 1, 31), "laporan [OFFICIAL]\n31 Jan", "off", 1), (date(2027, 3, 5), "lomba [OFFICIAL]\n5 Mar", "off", -1)]
    for dt, lab, kind, side in ev:
        color = {"now": ORANGE, "int": INK2, "off": NAVY}[kind]
        ax2.plot([dt, dt], [0, 0.9 * side], color=color, lw=1)
        ax2.plot(dt, 0, "o", ms=6.5, color=color if kind != "int" else "white", mec=color, mew=1.4, zorder=5)
        ax2.text(dt, 1.05 * side, lab, ha="center", va="bottom" if side > 0 else "top", fontsize=6.9, color=color, linespacing=1.05)
    ax2.xaxis.set_major_locator(mdates.MonthLocator())
    ax2.set_xticks(months, ["Nov 2026", "Des", "Jan 2027", "Feb", "Mar"], fontsize=7.4)
    save(fig, "fig_roadmap")


def fig_cover(c1, img):
    fig = plt.figure(figsize=(W, 1.85), facecolor=NAVY)
    cmap = LinearSegmentedColormap.from_list("navy", [NAVY, "#3f6ea8", "#dce9f8"])
    a = fig.add_axes((0.015, 0.1, 0.17, 0.8))
    a.imshow(np.transpose(img, (1, 2, 0)), interpolation="nearest")
    a.axis("off")
    fig.text(0.207, 0.5, "→", color="#dce9f8", fontsize=20, ha="center", va="center")
    for i in range(16):
        r, c = divmod(i, 8)
        ax = fig.add_axes((0.235 + c * 0.095, 0.53 - r * 0.45, 0.085, 0.4))
        ax.imshow(c1[i], cmap=cmap, vmin=0, vmax=max(1, int(c1[i].max())), interpolation="nearest")
        ax.axis("off")
    fig.savefig(FIG / "fig_cover.png", dpi=220, facecolor=NAVY)
    plt.close(fig)
    print("  fig_cover.png")


# --------------------------------------------------------------------------- facts


def checksum_facts(res, facts):
    acc = res.trace[1].acc  # conv2 accumulators before bias, (32, 16, 16)
    py, px = 7, 9
    y = [int(v) for v in acc[0:8, py, px]]
    s1, s2, s3 = ck.checksums(y)
    lane, bit = 5, 14
    obs = list(y)
    obs[lane - 1] = ck.xor_inject(y[lane - 1], 1 << bit, 32)
    r = ck.check(obs, s1, s2, s3, ck.CORRECT, False, False)
    single = {"lane": lane, "bit": bit, "observed": obs, "d1": r.d1, "d2": r.d2, "outcome": r.outcome.name, "j": r.lane, "corrected": r.y}
    la, lb = 2, 6
    b2 = next(b for b in range(12, 31) if (y[la - 1] >> b) & 1 == (y[lb - 1] >> b) & 1)  # same bit value: equal error on both lanes
    obs2 = list(y)
    obs2[la - 1] = ck.xor_inject(y[la - 1], 1 << b2, 32)
    obs2[lb - 1] = ck.xor_inject(y[lb - 1], 1 << b2, 32)
    r0 = ck.check(obs2, s1, s2, s3, ck.CORRECT, False, False)
    r1 = ck.check(obs2, s1, s2, s3, ck.CORRECT, True, False)
    dual = {"lanes": [la, lb], "bit": b2, "observed": obs2, "d1": r0.d1, "d2": r0.d2, "d3": r1.d3,
            "outcome_c3_off": r0.outcome.name, "j_c3_off": r0.lane, "outcome_c3_on": r1.outcome.name}
    facts["checksum_example"] = {"layer": "conv2", "group": 0, "pos": [py, px], "y": y, "s1": s1, "s2": s2, "s3": s3, "single": single, "dual": dual}


def requant_facts(qm, res, facts):
    lay = qm.layers[0]
    acc = res.trace[0].acc
    yq = res.trace[0].y
    for c in range(acc.shape[0]):
        for yy in range(acc.shape[1]):
            for xx in range(acc.shape[2]):
                if 100 <= yq[c, yy, xx] <= 140:
                    v = int(acc[c, yy, xx] + lay.b[c])
                    prod = v * lay.m
                    half = 1 << (lay.n - 1)
                    q = (prod + half) >> lay.n
                    facts["requant_example"] = {"layer": "conv1", "channel": c, "pos": [yy, xx], "acc": int(acc[c, yy, xx]), "bias": int(lay.b[c]),
                                                "v": v, "m": lay.m, "n": lay.n, "prod": prod, "half": half, "q": q, "y": int(min(max(q, 0), 255))}
                    return


def main() -> int:
    setup()
    FIG.mkdir(parents=True, exist_ok=True)
    facts: dict = {}
    arch = load_json("results/model/arch_s.json")
    qm = QModel.load(ROOT / "results/model/s/quant.npz")
    images, labels, _classes = load_images()
    idx = pick_image(qm, images, labels)
    img = images[idx]
    print(f"image {idx}: label {CLASSES_ID[labels[idx]]}")
    fig_path()
    fig_tensor(img, CLASSES_ID[labels[idx]])
    fig_activation()
    fig_conv(facts)
    fig_pool(facts)
    fig_model(arch)
    res = fig_featuremaps(qm, img, idx, int(labels[idx]), facts)
    fig_macs(arch)
    fig_training(facts)
    fig_quant_stairs()
    requant_facts(qm, res, facts)
    fig_requant(qm, facts)
    fig_accuracy()
    fig_fpga_fabric()
    fig_timing()
    fig_vivado_flow()
    fig_system()
    fig_dataflow()
    fig_decision()
    fig_clockswitch()
    fig_governor(facts)
    fig_pipeline()
    fig_campaign()
    fig_fmax()
    fig_roadmap()
    fig_cover(res.trace[0].output, img)
    checksum_facts(res, facts)
    for exp, name in [("e1", "e1_events.png"), ("e4", "e4_throughput.png"), ("e6", "e6_governor.png")]:
        run = latest_run("mock", exp)
        if run and (run / name).exists():
            shutil.copyfile(run / name, FIG / f"fig_mock_{exp}.png")
            facts.setdefault("mock_sources", {})[exp] = str((run / name).relative_to(ROOT)).replace("\\", "/")
            print(f"  fig_mock_{exp}.png (copied)")
    FACTS.write_text(json.dumps(facts, indent=1), encoding="utf-8")
    print(f"wrote {FACTS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
