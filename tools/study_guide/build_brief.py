#!/usr/bin/env python3
"""Build the SENTINEL explanation for the team's supervisor (Indonesian) as
build/study_guide/SENTINEL_penjelasan_dosen.docx, then (Windows + Word) a PDF next to it.

The document explains the goal, the algorithm, every technique, the evidence so far and the
limits of the claims. Every number is read from result files in the repository (or from
build/study_guide/facts.json, which tools/study_guide/figures.py computes from the golden,
checker and governor models) and carries its provenance label.

    python tools/study_guide/figures.py      # figures and facts.json (once per result change)
    python tools/study_guide/build_brief.py  # this document; --no-pdf skips Word
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FACTS, FIG, OUT, ROOT, git_head, load_json, nf, pct, regression_latest  # noqa: E402
from docx_lib import BLUE, INK2, NAVY, TEXT_W, Doc, delim, frac, gap, mi, mt, nary, para, run, sub, sup  # noqa: E402

OUT_DOCX = OUT / "SENTINEL_penjelasan_dosen.docx"
TODAY = date(2026, 11, 18)


def fig(name: str) -> Path:
    return FIG / f"{name}.png"


def sn(x: int) -> str:
    return ("−" if x < 0 else "") + nf(abs(x))


# ============================================================================ context


def clocks(summary: dict) -> dict:
    return {c["name"]: c for c in summary["clocks"] if "fmax_mhz" in c}


def load_context() -> dict:
    if not FACTS.exists():
        raise SystemExit("build/study_guide/facts.json is missing: run tools/study_guide/figures.py first")
    ctx = {"facts": json.loads(FACTS.read_text(encoding="utf-8")), "head": git_head()}
    ctx["arch"] = load_json("results/model/arch_s.json")
    ctx["fl"] = {m: load_json(f"results/model/{m}/float_result.json") for m in ("s", "xs")}
    ctx["qr"] = {m: load_json(f"results/model/{m}/quant_result.json") for m in ("s", "xs")}
    ctx["camp"] = load_json("results/sim/campaign_s.json")
    ctx["reg"] = regression_latest()
    ctx["lut"] = load_json("results/vivado/official/summary.json")
    ctx["dsp"] = load_json("results/vivado/official_dsp/summary.json")
    ctx["zero"] = load_json("results/model/zero_taps_s_k8.json")
    status = (ROOT / "STATUS.md").read_text(encoding="utf-8")
    ctx["tests"] = re.findall(r"\| (\d+) passed in [\d.]+s", status)[-1]
    return ctx


def camp_row(ctx, k, c3, kind) -> dict:
    return next(r for r in ctx["camp"]["rows"] if r["k"] == k and r["c3"] == c3 and r["kind"] == kind)


def cycles(entry: dict) -> tuple[int, int]:
    m = re.search(r"cycles_mean=(\d+) ideal=(\d+)", entry["summary"])
    return int(m.group(1)), int(m.group(2))


# ============================================================================ new figures


def make_figures(ctx) -> None:
    import matplotlib.pyplot as plt
    import figures as F

    F.setup()
    lut, dsp = ctx["lut"], ctx["dsp"]
    names = [("lut", "Slice LUT"), ("ff", "Flip-flop"), ("bram_tile", "Block RAM"), ("dsp", "DSP48E1")]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(F.W, 2.75), gridspec_kw={"width_ratios": [1.0, 1.15], "wspace": 0.42})
    y = list(range(len(names)))[::-1]
    h = 0.36
    for off, (s, col, lab) in zip((h / 2 + 0.02, -h / 2 - 0.02), ((lut, F.BLUE, "varian LUT"), (dsp, F.ORANGE, "varian DSP"))):
        u = s["utilization_post_route"]
        vals = [u[k]["util_pct"] for k, _ in names]
        a1.barh([v + off for v in y], vals, height=h, color=col, label=lab)
        for yy, v, (k, _) in zip(y, vals, names):
            a1.text(v + 1.2, yy + off, f"{nf(u[k]['used'])}", va="center", fontsize=6.8, color=F.INK2)
    a1.set_yticks(y, [n for _, n in names])
    a1.set_xlim(0, 60)
    a1.set_xlabel("% dari kapasitas XC7S25")
    a1.set_title("Resource sesudah place & route")
    F.bar_axis(a1, "x")
    a1.legend(loc="lower right", fontsize=7)
    cl_l, cl_d = clocks(lut), clocks(dsp)
    rows = [("LUT: clk_safe", cl_l["clk_safe_raw"]["fmax_mhz"], F.BLUE), ("LUT: lane", cl_l["clk_fast_turbo"]["fmax_mhz"], F.BLUE),
            ("DSP: clk_safe", cl_d["clk_safe_raw"]["fmax_mhz"], F.ORANGE), ("DSP: lane", cl_d["clk_fast_turbo"]["fmax_mhz"], F.ORANGE)]
    yy = list(range(len(rows)))[::-1]
    a2.barh(yy, [r[1] for r in rows], height=0.55, color=[r[2] for r in rows])
    for y0, (lab, v, _) in zip(yy, rows):
        a2.text(v + 4, y0, f"{nf(v, 1)} MHz", va="center", fontsize=6.8, color=F.INK2)
    a2.set_yticks(yy, [r[0] for r in rows])
    a2.set_xlim(0, 320)
    for x, txt in ((125, "clock aman\n125 MHz"), (250, "batas suplai\noperand 250 MHz")):
        a2.axvline(x, color=F.INK2, lw=0.9, ls=(0, (3, 2)))
        a2.text(x, len(rows) - 0.35, txt, ha="center", va="bottom", fontsize=6.5, color=F.INK2, linespacing=1.0)
    a2.set_xlabel("Fmax statis (MHz)")
    a2.set_title("Frekuensi menurut STA", pad=22)
    F.bar_axis(a2, "x")
    F.tag(fig, "[VIVADO-STA]", F.STA_GREEN)
    F.save(fig, "fig_brief_variants")

    import matplotlib.dates as mdates

    fig = plt.figure(figsize=(F.W, 2.5))
    gs = fig.add_gridspec(2, 1, height_ratios=[1.0, 1.4], hspace=0.25)
    ax = fig.add_subplot(gs[0])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 10)
    ax.axis("off")
    chips = [(f"M{i}", "part" if i == 10 else "done") for i in range(15)] + [(f"B{i}", "todo") for i in range(1, 7)]
    x = 0.3
    for i, (t, st) in enumerate(chips):
        if i == 15:
            x += 2.6
        fc = {"done": F.BLUE, "part": F.YELLOW, "todo": "#e4e3df"}[st]
        F.box(ax, x, 4.2, 4.0, 4.6, t, fc=fc, ec="white", fs=6.8, color="white" if st == "done" else F.INK, bold=True, r=0.6)
        x += 4.45
    ax.text(33.6, 1.6, "pra-board: selesai di simulasi (M10: rekonfigurasi MMCM asli menunggu board)", ha="center", fontsize=6.9, color=F.INK2)
    ax.text(84.5, 1.6, "fase board: belum mulai", ha="center", fontsize=6.9, color=F.INK2)
    ax2 = fig.add_subplot(gs[1])
    from datetime import date as D

    ax2.set_xlim(D(2026, 11, 1), D(2027, 3, 15))
    ax2.set_ylim(-3.3, 3.3)
    ax2.axhline(0, color=F.INK2, lw=1)
    for s in ax2.spines.values():
        s.set_visible(False)
    ax2.set_yticks([])
    months = [D(2026, 11, 1), D(2026, 12, 1), D(2027, 1, 1), D(2027, 2, 1), D(2027, 3, 1)]
    ax2.xaxis.set_major_locator(mdates.MonthLocator())
    ax2.set_xticks(months, ["Nov 2026", "Des", "Jan 2027", "Feb", "Mar"], fontsize=7.4)
    ev = [(TODAY, "dokumen ini\n18 Nov", "now", 1), (D(2026, 11, 20), "board tiba\n20 Nov [TEAM]", "int", -1),
          (D(2026, 12, 13), "G1\n13 Des", "int", 1), (D(2027, 1, 3), "G2\n3 Jan", "int", -1),
          (D(2027, 1, 17), "bekukan HW\n17 Jan", "int", 1), (D(2027, 1, 31), "laporan\n31 Jan [OFFICIAL]", "off", -1),
          (D(2027, 3, 5), "lomba\n5 Mar [OFFICIAL]", "off", 1)]
    for dt, lab, kind, side in ev:
        color = {"now": F.ORANGE, "int": F.INK2, "off": F.NAVY}[kind]
        ax2.plot([dt, dt], [0, 0.9 * side], color=color, lw=1)
        ax2.plot(dt, 0, "o", ms=6.5, color=color if kind != "int" else "white", mec=color, mew=1.4, zorder=5)
        ax2.text(dt, 1.05 * side, lab, ha="center", va="bottom" if side > 0 else "top", fontsize=6.6, color=color, linespacing=1.05)
    F.save(fig, "fig_brief_timeline")


# ============================================================================ document


def cover(d: Doc, ctx) -> None:
    d.add(para([run("LSI DESIGN CONTEST 2027  ·  PENJELASAN UNTUK DOSEN PEMBIMBING", b=True, color=BLUE, size=18, spacing=20)],
               before=300, after=80))
    d.add(para([run("SENTINEL", b=True, color=NAVY, size=84)], after=0, line=240))
    d.add(para([run("Akselerator CNN di FPGA Spartan-7 yang memeriksa hitungannya sendiri, sehingga lane perkaliannya "
                    "bisa dijalankan lebih cepat dari batas timing statis tanpa menghasilkan jawaban yang salah", color=INK2, size=27)],
               after=260, line=260))
    d.add(para([d.picture(fig("fig_dataflow"), 17.0, "Aliran data SENTINEL: K lane data dan lane checksum")], align="center", after=60))
    d.p("K lane data menghitung K kanal keluaran sekaligus. Dua atau tiga lane tambahan menghitung checksum dari bobot yang sama, "
        "dan komparator di domain clock aman memakai keduanya untuk menemukan lalu memperbaiki lane yang salah.",
        align="center", size=17, color=INK2, after=260)
    rows = [["Tim", "Tim SENTINEL (4 orang)"],
            ["Tanggal", "18 November 2026"],
            ["Fase proyek", "pra-board: board ZERO7 belum dipakai, jadi belum ada hasil yang diukur di hardware"],
            ["Kategori yang dituju", "Class 2 (ZERO7 Class), Level 3 [PROPOSAL]; menunggu konfirmasi panitia"],
            ["Sumber angka", f"repo SENTINEL, branch `pra-board`, commit `{ctx['head']}`; setiap angka menyebut file sumbernya"],
            ["Dibangun ulang dengan", "`python tools/study_guide/figures.py` lalu `python tools/study_guide/build_brief.py`"]]
    d.table([], rows, [2600, TEXT_W - 2600], size=19, first_col_bold=True)
    d.page_break()
    d.add(para([run("Cara membaca angka di dokumen ini", b=True, color=NAVY, size=30)], after=160, border_bottom=BLUE))
    d.p("Setiap angka diberi label asal-usulnya. Label ini dipakai di seluruh proyek supaya hasil simulasi tidak pernah terbaca "
        "sebagai hasil pengukuran.")
    d.table(["Label", "Artinya"], [
        ["[SIM]", "hasil simulasi RTL atau model Python (golden model, model checker, model governor)"],
        ["[SYNTHETIC]", "memakai model error timing buatan; hanya untuk menguji skrip, bukan bukti"],
        ["[VIVADO-STA]", "estimasi statis dari laporan Vivado (timing, resource, daya tanpa data aktivitas)"],
        ["[HW]", "diukur di board sungguhan; belum ada satu pun angka seperti ini"],
        ["[OFFICIAL]", "tertulis di dokumen resmi panitia"],
        ["[INFERENCE]", "kesimpulan kami dari data yang ada, belum diuji langsung"],
        ["[PROPOSAL]", "usulan atau target internal tim"],
        ["[UNKNOWN]", "belum diketahui; tidak boleh ditebak"]], [2200, TEXT_W - 2200], size=19)
    d.add(para([run("Daftar isi", b=True, color=NAVY, size=30)], before=240, after=160, border_bottom=BLUE))
    d.toc()


def summary(d: Doc, ctx) -> None:
    lut, dsp = ctx["lut"], ctx["dsp"]
    cyc, ideal = cycles(ctx["reg"]["engine_s_k8_c1_n200"])
    d.chapter = "R"
    d.add(para([run("Ringkasan")], style="Heading1", page_break_before=True))
    d.p("SENTINEL adalah akselerator jaringan saraf konvolusi (CNN) untuk gambar 32×32 yang kami rancang untuk chip AMD Spartan-7 "
        "XC7S25CSGA225-1 di board ZERO7. Hasil klasifikasinya harus sama persis, bit demi bit, dengan model integer di Python yang kami "
        "pakai sebagai acuan.")
    d.p("Frekuensi clock yang dianggap aman oleh alat sintesis berasal dari analisis timing statis (STA). Analisis ini mengandaikan chip "
        "terlambat, suhu terpanas, dan tegangan terendah sekaligus, sehingga chip nyata di meja biasanya masih bekerja benar di frekuensi "
        "yang lebih tinggi. Masalahnya, ketika batas itu terlewati, kesalahan muncul diam-diam: angka di register salah, tanpa tanda apa pun. "
        "SENTINEL memasang pemeriksa supaya ruang kecepatan itu bisa dipakai tanpa menerima jawaban salah.")
    d.p("Caranya memakai checksum berbasis algoritma (ABFT). Engine menghitung K kanal keluaran secara paralel di K lane perkalian-penjumlahan "
        "(MAC). Di samping K lane itu ada lane C1 yang menghitung jumlah semua bobot, lane C2 yang menghitung jumlah berbobot k·w_{k}, dan lane C3 "
        "dengan bobot k²·w_{k}. Kalau tidak ada error, jumlah hasil semua lane harus sama dengan C1, dan seterusnya. Selisihnya memberi tahu "
        "tiga hal: ada error atau tidak, lane mana yang salah (dari perbandingan selisih C2 dan C1), dan berapa nilai koreksinya. Error satu lane "
        "langsung diperbaiki di tempat; pola yang tidak bisa dipastikan dihitung ulang di clock aman. Governor di dalam FPGA menaikkan atau "
        "menurunkan clock lane per layer berdasarkan jumlah error yang tertangkap.")
    d.p("Status per 18 November 2026, semuanya pra-board:")
    d.bullets([
        f"Model CNN `s` mencapai akurasi {pct(ctx['qr']['s']['test_acc_integer'])} dalam bentuk integer 8 bit di CIFAR-10, dataset pengganti "
        "karena kelas lomba belum diumumkan [SIM].",
        f"RTL lengkap cocok bit demi bit dengan golden model pada 200 gambar uji, termasuk sistem dua clock lengkap, untuk lane berbasis LUT "
        f"maupun DSP [SIM]; {ctx['tests']} test otomatis lulus.",
        f"Pada 10.000 error satu lane yang disuntikkan, semuanya terkoreksi; dengan C3, tidak satu pun dari 10.000 error dua lane salah dikoreksi [SIM].",
        f"Desain lengkap muat dan lolos timing di chip resmi dalam dua varian: {nf(lut['utilization_post_route']['lut']['used'])} LUT (lane LUT) dan "
        f"{nf(dsp['utilization_post_route']['lut']['used'])} LUT plus 14 DSP (lane DSP) dari 14.600 LUT [VIVADO-STA].",
        f"Satu gambar butuh rata-rata {nf(cyc)} siklus, hanya {pct(cyc / ideal - 1)} di atas jumlah siklus ideal [SIM].",
    ])
    d.p("Yang belum terbukti adalah inti hipotesisnya: bahwa error timing nyata di Spartan-7 cukup sering hanya mengenai satu lane, sehingga "
        "koreksi lebih menguntungkan daripada hitung ulang. Simulasi tidak bisa menjawabnya. Jawabannya baru datang dari eksperimen di board, "
        "yang dijadwalkan mulai akhir November 2026. Dokumen ini menuliskan semua batasan itu secara terbuka di Bab 8.")


def ch1(d: Doc, ctx) -> None:
    d.h1("1", "Latar belakang")
    d.h2("1.1 Lomba yang kami ikuti")
    d.p("LSI Design Contest ke-30 diadakan di Chitose, Hokkaido. Temanya implementasi hardware CNN dengan jumlah layer bebas [OFFICIAL]. "
        "Butir yang mengikat desain SENTINEL:")
    d.bullets([
        "Laporan akhir dan laporan sintesis untuk AMD Spartan-7 XC7S25CSGA225-1 dikumpulkan paling lambat 31 Januari 2027, dan laporan sintesis "
        "itu wajib untuk semua kelas [OFFICIAL].",
        "Lomba dan presentasi pada 5 Maret 2027: 10 menit, paling banyak 10 slide, lalu 5 menit tanya jawab [OFFICIAL].",
        "CNN menerima input 32×32. Dataset latih bebas, tetapi kelas yang harus dikenali ditentukan panitia dan belum diumumkan [OFFICIAL]. "
        "Karena itu model harus bisa dilatih ulang, dan bobot harus bisa dimuat ulang tanpa sintesis ulang.",
        "Gambar validasi diberikan pada hari lomba dan dibaca dari kamera, kartu SD, atau sejenisnya. Presentasi harus menunjukkan seberapa cepat "
        "hasil pengenalan keluar [OFFICIAL].",
        "Class 2 (ZERO7 Class) membatasi board pada ZERO7, membebaskan tugas, dan hanya punya Level 3 [OFFICIAL]. Kami menargetkan kelas ini "
        "[PROPOSAL], tetapi tetap menjaga mode klasifikasi, mode data validasi, dan mode kamera supaya proyek juga memenuhi Class 1 Level 3.",
        "Juri menilai kecepatan dan area, ide, orisinalitas, keunikan, dan presentasi. Tingkat pendidikan peserta ikut dipertimbangkan [OFFICIAL].",
    ])
    d.p("ZERO7 adalah HAT Raspberry Pi buatan Gigafirm yang membawa XC7S25. Chip ini kecil: 14.600 LUT, 29.200 flip-flop, 45 block RAM, "
        "80 DSP, dan 3 MMCM menurut basis data Vivado [VIVADO-STA].")
    d.h2("1.2 Dari mana kecepatan akselerator datang")
    d.p("Kecepatan akselerator CNN kira-kira sama dengan jumlah unit MAC yang bekerja paralel dikali frekuensi clock. Di chip sekecil "
        "XC7S25, jumlah unit dibatasi area. Varian resmi SENTINEL memakai 8 lane data karena dengan itu desain lengkap, termasuk memori, "
        "kontrol, checksum, dan antarmuka, masih menyisakan ruang dan lolos timing. Yang tersisa adalah frekuensi.")
    d.p("Frekuensi maksimum yang dilaporkan Vivado berasal dari STA. Gambar 1.1 menunjukkan apa yang diperiksa STA: data harus sampai di flip-flop "
        "tujuan sebelum tepi clock berikutnya, dengan selisih waktu yang disebut slack. STA menghitung slack untuk kondisi terburuk: proses "
        "fabrikasi paling lambat, suhu tertinggi, dan tegangan terendah. Chip yang bekerja di suhu ruang dengan catu daya normal hampir selalu "
        "lebih cepat dari itu.")
    d.figure(fig("fig_timing"), "Jalur timing antara dua flip-flop. Di clock aman, data stabil sebelum tepi clock (slack positif). Di clock "
             "yang terlalu cepat, data masih berubah saat ditangkap, dan flip-flop menyimpan nilai yang salah.", 16.0)
    d.p("Literatur memberi gambaran seberapa besar ruang itu. Chamberlin dkk. (2024) mengukur array MAC kecil di board Zybo Z7-20: error baru "
        "muncul di sekitar 315 MHz, padahal STA memperkirakan sekitar 168 MHz. Marty dkk. (2020) menjalankan akselerator CNN di atas frekuensi "
        "nominal dengan pemeriksaan checksum dan mendapat rata-rata 68% throughput lebih tinggi. Angka-angka ini milik penelitian lain di "
        "chip lain; untuk Spartan-7 di ZERO7, ruangnya baru bisa diketahui dengan mengukur sendiri.")
    d.h2("1.3 Masalahnya: error timing tidak memberi tanda")
    d.p("Ketika clock melewati batas chip, sebagian bit di akumulator tertangkap salah tanpa alarm atau exception apa pun. Bagi akselerator "
        "CNN, akibatnya bisa berupa satu kanal fitur yang menyimpang, logit yang bergeser, atau kelas yang berubah. Dalam lomba yang menilai "
        "hasil pengenalan, overclocking tanpa pemeriksa menaikkan kecepatan sambil diam-diam mengurangi jumlah jawaban yang benar.")
    d.p("Dari sini datang pertanyaan yang ingin dijawab SENTINEL: bisakah lane MAC dijalankan di atas frekuensi aman, sementara setiap "
        "kesalahan yang muncul tertangkap, dan kalau mungkin diperbaiki langsung, sehingga hasil akhirnya tetap sama persis dengan model acuan?")


def ch2(d: Doc, ctx) -> None:
    d.h1("2", "Tujuan dan pertanyaan riset")
    d.h2("2.1 Tujuan")
    d.numbered([
        "Mengklasifikasi gambar 32×32 secara bit-exact terhadap golden model Python: kelas dan semua logit harus identik.",
        "Menjaga lane MAC dengan dua checksum (C1, C2) dan satu checksum opsional (C3), untuk mendeteksi, melokalisasi, dan mengoreksi error.",
        "Menjalankan lane MAC di atas frekuensi aman, dengan frekuensi dipilih per layer oleh governor hardware di dalam FPGA.",
        "Menyediakan alat ukur lengkap untuk delapan eksperimen (E1 sampai E8), supaya setiap klaim bisa dibuktikan atau dibantah dengan data.",
    ])
    d.h2("2.2 Hipotesis yang akan diuji")
    d.p("Desain SENTINEL bertumpu pada tiga hipotesis. Ketiganya bisa saja salah, dan hasil negatif yang diukur dengan jujur tetap akan dilaporkan.")
    d.table(["Kode", "Hipotesis", "Kenapa penting", "Diuji di"], [
        ["H1", "Pada frekuensi terendah tempat error mulai muncul, sebagian besar kejadian error hanya mengenai satu lane.",
         "Koreksi hanya berguna kalau error satu lane dominan; kalau tidak, SENTINEL jatuh ke hitung ulang biasa.", "E1"],
        ["H2", "Error timing bersifat deterministik: input dan frekuensi yang sama memberi pola error yang sama.",
         "Menentukan apakah governor bisa belajar dari gambar sebelumnya.", "E2"],
        ["H3", "Layer yang lebih dalam mulai error di frekuensi yang lebih tinggi daripada layer pertama.",
         "Alasan memilih clock per layer, bukan satu clock untuk semua.", "E3"]],
        [800, 3700, 3900, 1238], caption="Hipotesis SENTINEL (SPEC §16)", size=18)
    d.h2("2.3 Kriteria keberhasilan")
    d.p("Kriteria ini kami tetapkan sendiri sebelum ada data board, supaya hasilnya tidak bisa diatur sesudahnya.")
    d.table(["ID", "Pertanyaan", "Kriteria berhasil [PROPOSAL]", "Status pra-board"], [
        ["E1", "Atlas error: sapuan frekuensi per 5 MHz", "≥ 90% kejadian error di tiga frekuensi error terendah hanya mengenai satu lane", "skrip diuji dengan data buatan"],
        ["E2", "Apakah error deterministik?", "≥ 95% pengulangan memberi pola error identik", "skrip diuji dengan data buatan"],
        ["E3", "Onset error per layer", "layer dalam mulai error ≥ 10% lebih tinggi dari layer 1", "skrip diuji dengan data buatan"],
        ["E4", "Tiga mode: throughput dan akurasi", "throughput bit-exact mode koreksi ≥ 1,2× mode hitung ulang dan ≥ 1,4× baseline yang lolos timing", "skrip diuji dengan data buatan"],
        ["E5", "Fault injection: cakupan dan salah koreksi", "100% error satu lane terkoreksi; laju dua lane dilaporkan", "selesai [SIM]"],
        ["E6", "Governor dan suhu", "frekuensi mengikuti suhu tanpa hasil salah", "skrip diuji dengan data buatan"],
        ["E7", "Bit-exact di set validasi", "100% kelas dan logit identik", "selesai di RTL [SIM]; board menyusul"],
        ["E8", "Biaya: resource, daya, keuntungan bersih", "keuntungan bersih positif", "resource dan daya statis [VIVADO-STA]"]],
        [700, 2900, 3700, 2338], caption="Eksperimen dan kriteria (SPEC §16)", size=17)


def ch3(d: Doc, ctx) -> None:
    d.h1("3", "Ide inti dalam satu gambar")
    d.p("SENTINEL membagi chip menjadi dua domain clock. Gambar 3.1 menunjukkan pembagiannya.")
    d.figure(fig("fig_system"), "Arsitektur SENTINEL. Hanya lane MAC (kanan) yang berjalan di clock cepat. Memori, generator operand, "
             "komparator, governor, dan antarmuka berada di domain clock aman yang wajib lolos timing.", 17.0)
    d.p("Domain `clk_safe` berisi semua yang tidak boleh salah: memori bobot dan aktivasi, pembangkit operand, pembangkit bobot checksum, "
        "komparator dan korektor, post-processing, pooling, governor, dan antarmuka SPI. Domain ini selalu berjalan di frekuensi yang lolos STA, "
        "125 MHz di varian resmi. Domain `clk_fast` hanya berisi lane MAC dan register penampung hasilnya. Clock domain ini dipilih oleh sebuah "
        "BUFGCTRL antara clock aman dan clock turbo dari MMCM kedua yang frekuensinya bisa diubah saat berjalan.")
    d.p("Pembagian ini menjawab keberatan yang paling sering muncul: \"bagaimana kalau pemeriksanya sendiri ikut salah karena overclock?\" "
        "Pemeriksa tidak pernah di-overclock. Lane checksum memang ikut berjalan cepat, tetapi error di lane checksum punya pola sendiri dan "
        "dikenali sebagai kelas tersendiri (Bagian 4.5). Data menyeberang antar-domain lewat FIFO asinkron, sehingga kedua clock tidak perlu "
        "punya hubungan fase.")
    d.callout("intuisi", [
        "Bayangkan delapan kasir menghitung belanjaan secara bersamaan, lalu satu pengawas yang tidak terburu-buru mengecek totalnya. "
        "Kasir kesembilan menghitung total semua belanjaan sekaligus (C1). Kalau jumlah hasil delapan kasir tidak sama dengan total itu, "
        "ada yang salah. Kasir kesepuluh menghitung total dengan bobot nomor kasir (C2): belanjaan kasir 1 dikali 1, kasir 2 dikali 2, dan "
        "seterusnya. Kalau kasir nomor 5 salah sebesar e, selisih C1 adalah e dan selisih C2 adalah 5e. Pembagian keduanya langsung menunjuk "
        "kasir nomor 5, dan nilai e memberi tahu berapa koreksinya."], title="ANALOGI")


def ch4(d: Doc, ctx) -> None:
    arch, qs = ctx["arch"], ctx["qr"]["s"]
    d.h1("4", "Algoritma")
    d.h2("4.1 Model CNN")
    d.p("Varian resmi bernama `s`: tiga layer konvolusi 3×3 dengan ReLU dan max pooling 2×2, lalu satu layer fully connected. "
        "Jumlah bobot dan MAC di Tabel 4.1 dihitung ulang dari konfigurasi oleh `model/arch_report.py` [SIM].")
    rows = []
    for L in arch["layers"]:
        inp = L["input"]
        if L["kind"] == "conv":
            desc = f"konvolusi 3×3, {inp[0]} → {L['output_channels']} kanal pada {inp[1]}×{inp[2]}, ReLU, max pooling 2×2"
        else:
            n_in = 1
            for v in inp:
                n_in *= v
            desc = f"fully connected, {nf(n_in)} → {L['output_channels']} kelas"
        rows.append([L["name"], desc, nf(L["weights"]), nf(L["macs"])])
    d.table(["Layer", "Operasi", "Bobot", "MAC"], rows + [["Total", "", f"{nf(arch['total_weights'])} + {arch['total_bias']} bias", nf(arch["total_macs"])]],
            [1500, 4638, 1900, 1600], caption="Struktur model `s` [SIM], dari `results/model/arch_s.json`", size=18, align=["left", "left", "right", "right"])
    d.p("Semua aritmetika di hardware berupa bilangan bulat. Aktivasi adalah uint8 (0..255), bobot int8 (−127..127), dan bias int32. "
        "Satu keluaran konvolusi dihitung sebagai:")
    d.eq(mt("acc") + delim(mi("o,y,x"), "[", "]") + mi("=") + nary(mi("c"), "", nary(mi("i,j"), "", sub(mi("w"), mi("o,c,i,j")) + mi("·") +
         sub(mi("a"), mi("c, y+i−1, x+j−1")))))
    d.p("Hasilnya ditambah bias, lalu dikecilkan kembali ke uint8 dengan satu perkalian bilangan bulat M (16 bit) dan satu geser kanan n "
        "(requantization). Pemotongan ke rentang 0..255 sekaligus berfungsi sebagai ReLU:")
    d.eq(mi("q=") + delim(delim(mt("acc") + mi("+b")) + mi("·M+") + sup(mi("2"), mi("n−1"))) + mi("≫n") + gap() + mi("y=") + mt("min") +
         delim(mt("max") + delim(mi("q,0")) + mi(",255")))
    d.p("Layer terakhir tidak di-requant: logit int32 langsung dibandingkan, dan kelas adalah indeks terkecil dengan logit terbesar. "
        "Aturan pembulatan, urutan pooling, dan penanganan nilai sama ditulis normatif di SPEC §3, sehingga golden model dan RTL bisa dibuat identik.")
    d.h2("4.2 Kuantisasi 8 bit")
    d.p(f"Model dilatih dalam floating point dengan PyTorch (seed 2027, {ctx['fl']['s']['epochs']} epoch), lalu dikuantisasi setelah training (PTQ): "
        f"skala setiap layer diambil dari persentil 99,99 aktivasi pada {nf(qs['calib_images'])} gambar kalibrasi, dan M serta n dipilih supaya "
        "rasio skala terwakili seteliti mungkin dalam 16 bit. BatchNorm dilebur ke bobot sebelum kuantisasi.")
    d.table(["Model", "Float", "Integer 8 bit", "Penurunan"], [
        [m, pct(ctx["qr"][m]["test_acc_float"]), pct(ctx["qr"][m]["test_acc_integer"]), f"{nf(ctx['qr'][m]['drop_points'], 2)} poin"]
        for m in ("s", "xs")], [2400, 2400, 2438, 2400], caption="Akurasi di set uji CIFAR-10 (10.000 gambar) [SIM]", size=19,
        align=["left", "right", "right", "right"])
    d.p("CIFAR-10 hanya pengganti sementara. Begitu panitia mengumumkan kelas target, model dilatih ulang dari folder gambar, dan bobot baru dimuat "
        "lewat SPI tanpa sintesis ulang selama arsitektur konvolusinya sama dan jumlah kelas paling banyak 16.")
    d.h2("4.3 Pemetaan ke K lane")
    d.p("Engine memakai dataflow output-stationary. Lane k menghitung kanal keluaran o = g·K + (k − 1) untuk grup g. Selama satu unit hitung "
        "(satu posisi keluaran untuk satu grup), setiap lane mengakumulasi T = C_{in}·9 suku untuk konvolusi, atau T = N_{in} untuk fully "
        "connected. Setiap siklus, semua lane menerima satu operand set: satu aktivasi a yang disiarkan ke semua lane, K bobot (satu per lane), "
        "dan bobot checksum wc1, wc2, wc3. Jumlah siklus ideal untuk satu gambar adalah:")
    d.eq(sub(mt("siklus"), mt("ideal")) + mi("=") + nary(mt("conv"), "", sub(mi("H"), mt("out")) + mi("·") + sub(mi("W"), mt("out")) + mi("·G·") +
         sub(mi("C"), mt("in")) + mi("·9")) + mi("+") + nary(mt("fc"), "", mi("G·") + sub(mi("N"), mt("in"))))
    cyc, ideal = cycles(ctx["reg"]["engine_s_k8_c1_n200"])
    eff = arch["total_macs"] / (8 * cyc)
    d.p(f"Untuk model `s` dengan K = 8 hasilnya {nf(ideal)} siklus. RTL membutuhkan rata-rata {nf(cyc)} siklus per gambar pada 200 gambar uji [SIM], "
        f"jadi lane terpakai {pct(eff)} dari waktunya. Pada clock aman 125 MHz, itu berarti {nf(cyc * 8e-6, 3)} ms komputasi per gambar "
        "[SIM] × [VIVADO-STA].")
    d.h2("4.4 Checksum tertimbang")
    d.p("Inti SENTINEL adalah identitas aljabar sederhana. Untuk setiap siklus t, pembangkit di domain aman menghitung tiga bobot checksum "
        "dari K bobot yang sama yang dikirim ke lane data:")
    k1 = mi("k=1")
    d.eq(sub(mi("wc"), mi("1")) + mi("=") + nary(k1, mi("K"), sub(mi("w"), mi("k"))) + gap() + sub(mi("wc"), mi("2")) + mi("=") +
         nary(k1, mi("K"), mi("k·") + sub(mi("w"), mi("k"))) + gap() + sub(mi("wc"), mi("3")) + mi("=") + nary(k1, mi("K"), sup(mi("k"), mi("2")) + mi("·") + sub(mi("w"), mi("k"))))
    d.p("Lane checksum c mengakumulasi S_{c} = Σ_{t} wc_{c}(t)·a(t), dengan aktivasi a(t) yang sama yang diterima semua lane data. Karena perkalian "
        "dan penjumlahan bilangan bulat bersifat distributif, akumulator lane data Y_{k} memenuhi tiga identitas berikut jika tidak ada error:")
    d.eq(sub(mi("S"), mi("1")) + mi("=") + nary(k1, mi("K"), sub(mi("Y"), mi("k"))) + gap() + sub(mi("S"), mi("2")) + mi("=") +
         nary(k1, mi("K"), mi("k·") + sub(mi("Y"), mi("k"))) + gap() + sub(mi("S"), mi("3")) + mi("=") + nary(k1, mi("K"), sup(mi("k"), mi("2")) + mi("·") + sub(mi("Y"), mi("k"))))
    d.p("Identitas ini berlaku eksak. Tidak ada pembulatan, karena semuanya bilangan bulat dan lebar akumulator dijamin cukup "
        "(akumulator lane checksum 48 bit; batasnya dicek oleh skrip ekspor). Bobot checksum dihitung ulang setiap siklus di domain aman, jadi "
        "tidak butuh memori tambahan, dan bobot lane data yang rusak setelah keluar dari domain aman tetap ketahuan.")
    d.h2("4.5 Deteksi, lokalisasi, dan koreksi")
    d.p("Setelah satu unit selesai, komparator menghitung tiga selisih. Misalkan lane j salah sebesar e, sehingga yang terbaca adalah Y_{j} + e:")
    d.eq(sub(mi("d"), mi("1")) + mi("=") + nary(mi("k"), "", sub(mi("Y"), mi("k"))) + mi("−") + sub(mi("S"), mi("1")) + mi("=e") + gap() +
         sub(mi("d"), mi("2")) + mi("=") + nary(mi("k"), "", mi("k·") + sub(mi("Y"), mi("k"))) + mi("−") + sub(mi("S"), mi("2")) + mi("=j·e") + gap() +
         sub(mi("d"), mi("3")) + mi("=") + sup(mi("j"), mi("2")) + mi("·e"))
    d.p("Dari sini lane yang salah adalah j = d_{2}/d_{1}, dan koreksinya Y_{j} ← Y_{j} − d_{1}. Hardware tidak memakai pembagi: komparator "
        "mencoba j = 1..K dan memeriksa apakah d_{2} = j·d_{1} (dan d_{3} = j²·d_{1} bila C3 aktif). Gambar 4.1 memperlihatkan seluruh keputusan.")
    d.figure(fig("fig_decision"), "Keputusan komparator untuk satu unit (SPEC §6.2). Mode 0 dan 1 adalah pembanding; mode 2 adalah SENTINEL.", 15.0)
    d.p("Tiga detail kecil membuat skema ini aman:")
    d.bullets([
        "Bobot lane dimulai dari 1, bukan 0. Dengan bobot 0, error di lane C1 akan terlihat persis seperti error di lane data pertama.",
        "Error di lane checksum sendiri memberi pola d_{1} ≠ 0 dengan d_{2} = 0 (atau sebaliknya). Secara default pola ini tidak dipercaya "
        "sebagai error checksum, karena tanpa C3 pola yang sama bisa berasal dari dua error yang saling meniadakan; unit itu dihitung ulang.",
        "C3 menutup celah dua error. Dua lane yang salah bersamaan bisa kebetulan memenuhi d_{2} = j·d_{1} untuk j yang salah, tetapi dengan C3 "
        "hal itu tidak bisa terjadi. Misalkan lane a dan b (a ≠ b) salah sebesar e_{a} dan e_{b}, dan p = e_{a}/(e_{a} + e_{b}). Koreksi palsu "
        "butuh j = a·p + b·(1 − p) dan sekaligus j² = a²·p + b²·(1 − p). Selisih kedua syarat itu adalah p·(1 − p)·(a − b)², yang hanya nol "
        "kalau salah satu error bernilai nol. Jadi selama tidak ada overflow, dua error selalu jatuh ke hitung ulang. Untuk tiga error atau "
        "lebih, jaminan ini tidak berlaku.",
    ])
    d.h2("4.6 Contoh dengan angka nyata")
    ce = ctx["facts"]["checksum_example"]
    s1 = ce["single"]
    du = ce["dual"]
    img = ctx["facts"]["image"]
    d.p(f"Angka berikut diambil dari golden model untuk gambar uji CIFAR-10 nomor {img['index']} ({img['label_id']}), layer {ce['layer']}, "
        f"grup {ce['group']}, posisi ({ce['pos'][0]}, {ce['pos'][1]}) [SIM]. Delapan lane menghasilkan akumulator Y_{{1}}..Y_{{8}}, dan lane checksum "
        f"menghasilkan S_{{1}} = {sn(ce['s1'])} dan S_{{2}} = {sn(ce['s2'])}.")
    rows = []
    for k in range(8):
        rows.append([str(k + 1), sn(ce["y"][k]), sn(s1["observed"][k]), sn(du["observed"][k])])
    d.table(["Lane k", "Y_{k} benar", f"Error di lane {s1['lane']} (bit {s1['bit']})", f"Error di lane {du['lanes'][0]} dan {du['lanes'][1]} (bit {du['bit']})"],
            rows, [1500, 2600, 2700, 2838], caption="Akumulator conv2 sebelum dan sesudah bit dibalik [SIM], dari `build/study_guide/facts.json`", size=18,
            align=["center", "right", "right", "right"])
    d.p(f"Kasus satu lane. Bit {s1['bit']} di lane {s1['lane']} dibalik. Komparator mendapat d_{{1}} = {sn(s1['d1'])} dan d_{{2}} = {sn(s1['d2'])}. "
        f"Karena {sn(s1['d2'])} = {s1['j']} × ({sn(s1['d1'])}), lane {s1['j']} ditunjuk dan dikoreksi dengan mengurangkan d_{{1}}. Hasilnya kembali "
        f"tepat {sn(s1['corrected'][s1['lane'] - 1])}, tanpa hitung ulang.")
    d.p(f"Kasus dua lane. Bit {du['bit']} di lane {du['lanes'][0]} dan {du['lanes'][1]} dibalik bersamaan, dengan arah yang sama. Selisihnya "
        f"d_{{1}} = {sn(du['d1'])} dan d_{{2}} = {sn(du['d2'])}, dan kebetulan {sn(du['d2'])} = {du['j_c3_off']} × ({sn(du['d1'])}). Tanpa C3, komparator "
        f"menunjuk lane {du['j_c3_off']}, lane yang sebenarnya benar, dan merusaknya. Dengan C3, d_{{3}} = {sn(du['d3'])}, padahal lane {du['j_c3_off']} "
        f"menuntut {du['j_c3_off']}² × ({sn(du['d1'])}) = {sn(du['j_c3_off'] ** 2 * du['d1'])}. Syarat itu gagal, dan unit dihitung ulang. Contoh inilah "
        "alasan varian resmi memakai C3 (ADR-011, ADR-013).")
    d.h2("4.7 Hitung ulang di clock aman")
    d.p("Unit yang tidak bisa dipastikan dicatat di log (kapasitas 256 per layer). Setelah layer selesai, clock lane dipindah ke clock aman, semua "
        "unit di log dihitung ulang, dan hasilnya ditulis ulang setelah requantization dan pooling. Komparator tetap aktif selama hitung ulang. "
        "Kalau hasil di clock aman pun tidak bersih, flag FATAL dinyalakan, karena itu tanda bug atau error yang bukan timing. Kalau log penuh, "
        "seluruh layer diulang di clock aman. Jadi setiap jalur keluar dari komparator berakhir di hasil yang benar atau di flag yang terlihat.")
    d.h2("4.8 Governor: clock per layer")
    d.p("Governor memilih level frekuensi turbo L (indeks tabel frekuensi MMCM kedua) dan, untuk setiap layer, apakah layer itu boleh berjalan "
        "di turbo. Keputusannya diambil di akhir setiap gambar, seluruhnya di dalam FPGA:")
    d.code([
        "untuk setiap layer l:",
        "    jika ada unit gagal di l : turbo_en[l] = 0, cool[l] = COOLDOWN",
        "    jika l sedang cooldown   : kurangi cool[l]; jika habis, turbo_en[l] = 1",
        "jika ada layer gagal atau total koreksi > CORR_HI:  L = max(L - 1, L_MIN), streak = 0",
        "selain itu: streak += 1; jika streak >= N_UP:     L = min(L + 1, L_MAX), streak = 0",
    ])
    d.figure(fig("fig_governor"), "Contoh trajektori governor dengan urutan kejadian buatan [SIM]. Level naik setelah N_UP gambar bersih, turun saat "
             "ada unit gagal atau terlalu banyak koreksi, dan layer yang gagal istirahat selama COOLDOWN gambar.", 14.0)
    d.p("RTL governor dibandingkan dengan model Python pada 60 skenario dan menghasilkan trajektori state yang identik [SIM]. Perubahan level berarti "
        "MMCM kedua direkonfigurasi, dan itu hanya dilakukan di antara gambar dengan urutan tetap: lane dipindah ke clock aman, MMCM direkonfigurasi, "
        "tunggu LOCKED, baru turbo dipakai lagi (SPEC §7.7).")
    d.h2("4.9 Tiga mode dalam satu bitstream")
    d.p("Register `CTRL.MODE` memilih mode 0 (tanpa pemeriksaan), mode 1 (hanya C1: ada selisih berarti hitung ulang, seperti cara Marty dkk.), "
        "atau mode 2 (SENTINEL: deteksi, lokalisasi, koreksi). Ketiganya ada di bitstream yang sama, sehingga perbandingan di eksperimen E4 "
        "memakai chip, routing, dan suhu yang sama. Kalau koreksi ternyata tidak lebih baik dari hitung ulang, data itu yang akan dilaporkan.")


def ch5(d: Doc, ctx) -> None:
    d.h1("5", "Teknik yang digunakan")
    d.p("Tabel 5.1 merangkum teknik yang dipakai, di bagian mana, dan kenapa. Rujukan ADR menunjuk keputusan desain yang tercatat di "
        "`docs/DECISIONS.md`; setiap perubahan spesifikasi harus lewat ADR lebih dulu.")
    rows = [
        ["Algorithm-based fault tolerance (ABFT) dengan checksum tertimbang", "lane C1, C2, C3 dan `lane_checker`", "mendeteksi, menunjuk, dan memperbaiki error satu lane secara eksak", "SPEC §6; Huang & Abraham 1984"],
        ["Overclocking dengan pemeriksaan (timing speculation)", "domain `clk_fast`", "memakai margin antara STA dan chip nyata", "SPEC §7; Marty dkk. 2020"],
        ["Penskalaan frekuensi dinamis tanpa mengubah tegangan", "governor, MMCM kedua, BUFGCTRL", "clock per layer; tegangan tidak pernah disentuh", "SPEC §10, ADR-010, ADR-023"],
        ["Dua domain clock dan FIFO asinkron (pointer Gray code)", "operand dan hasil", "memisahkan bagian yang boleh salah dari yang tidak", "SPEC §7.3, ADR-021"],
        ["Synchronizer dua flip-flop dan aturan penyeberangan", "reset, LOCKED, SPI, sinyal quasi-statis", "mencegah metastabilitas; diperiksa `report_cdc`", "ADR-021, ADR-027"],
        ["Kuantisasi 8 bit setelah training (PTQ) dan requant M/2ⁿ", "model dan `postproc`", "aritmetika integer murah dan bisa dibuat bit-exact", "SPEC §3–4, ADR-006"],
        ["Peleburan BatchNorm ke bobot", "ekspor model", "tidak ada operasi BatchNorm di hardware", "SPEC §4"],
        ["Dataflow output-stationary dengan siaran aktivasi", "`operand_gen`, `lane_array`", "satu aktivasi dipakai K lane; syarat checksum berlaku", "ADR-001"],
        ["Pembangkitan bobot checksum on-the-fly", "`wc_gen` di domain aman", "tanpa memori tambahan; bobot rusak tetap terdeteksi", "ADR-002"],
        ["Pohon penjumlah datar dari salinan bobot yang digeser", "`wc_gen`", "memendekkan jalur kritis clk_safe", "ADR-029; Parhi bab 13, 15"],
        ["Dua implementasi lane: LUT dan DSP48E1", "`lane_lut`, `lane_dsp_min`", "varian riset overclock dan varian kecepatan", "ADR-030"],
        ["Replikasi register reset (max_fanout)", "`top_core`", "net reset ber-fan-out besar tidak lagi membatasi clk_safe", "ADR-029 (catatan)"],
        ["Hitung ulang tertunda per jendela pool", "`engine`", "satu jalur cadangan yang pasti benar", "SPEC §9, ADR-003"],
        ["Fault injection hardware (XOR mask di register)", "dua slot INJ di lane", "menguji seluruh jalur deteksi seperti error sungguhan", "SPEC §11"],
        ["Golden model sebagai oracle dan verifikasi bit-exact", "semua testbench", "RTL harus identik, bukan mirip", "SPEC §13"],
        ["Vektor uji dari model dengan seed tetap", "`model/vectors.py`, `tb/`", "setiap hasil bisa diulang", "SPEC §13.2"],
        ["Satu sumber peta register (YAML ke Verilog dan Python)", "`spec/regmap.yaml`", "hardware dan software tidak bisa berbeda", "SPEC §12"],
        ["Analisis timing statis dan matriks out-of-context", "`fpga/`", "mengukur Fmax dan resource sebelum board ada", "SPEC §14, ADR-013, ADR-014"],
    ]
    d.table(["Teknik", "Di SENTINEL", "Alasan", "Rujukan"], rows, [2900, 2200, 2800, 1738],
            caption="Teknik yang dipakai SENTINEL", size=16, keep=False)
    d.h2("5.1 Optimasi dari buku Parhi")
    d.p("Selama pra-board kami membaca seluruh buku Parhi, ~VLSI Digital Signal Processing Systems: Design and Implementation~ (Wiley, 1999), dan "
        "mencatat teknik yang relevan per bab di `docs/research/parhi/`. Hasilnya daftar sebelas kandidat pengembangan (D1 sampai D11). Tiga sudah "
        "dikerjakan dan diukur:")
    lut = ctx["lut"]
    dsp = ctx["dsp"]
    d.bullets([
        "Pohon penjumlah bobot checksum (ADR-029). Setiap perkalian konstan k·w_{k} dan k²·w_{k} dipecah menjadi salinan w_{k} yang digeser, lalu "
        "semua salinan masuk satu pohon penjumlah datar dengan register di tengah. Kesetaraannya dibuktikan pada 10⁶ vektor acak dan semua bobot "
        "nyata [SIM]. Fmax clk_safe di sintesis out-of-context naik dari 141,7 ke 144,3 MHz [VIVADO-STA].",
        "Dua varian lane (ADR-030). Lane berbasis DSP48E1 lolos STA sampai "
        f"{nf(clocks(dsp)['clk_fast_turbo']['fmax_mhz'], 1)} MHz di desain lengkap, sedangkan lane LUT {nf(clocks(lut)['clk_fast_turbo']['fmax_mhz'], 1)} MHz "
        "[VIVADO-STA]. Keduanya memakai golden model yang sama dan lulus regresi bit-exact yang sama.",
        "Replikasi register reset. Net reset yang menggerakkan ribuan flip-flop menjadi jalur terburuk clk_safe; dengan register yang direplikasi, "
        f"Fmax clk_safe varian LUT menjadi {nf(clocks(lut)['clk_safe_raw']['fmax_mhz'], 1)} MHz dan varian DSP {nf(clocks(dsp)['clk_safe_raw']['fmax_mhz'], 1)} MHz [VIVADO-STA].",
    ])
    z = ctx["zero"]
    d.p(f"Satu kandidat berikutnya, melewati operand dengan aktivasi nol (ADR-028), terlihat menjanjikan: {pct(z['zero_cycle_fraction'], 1)} operand set model `s` "
        f"membawa aktivasi nol [SIM] (golden model, {nf(z['images'])} gambar uji CIFAR-10 pertama). Karena aktivasi disiarkan, siklus itu menghasilkan nol di semua lane "
        "termasuk lane checksum, jadi bisa dilewati tanpa merusak identitas checksum. Pekerjaan ini sengaja ditunda sampai setelah gerbang G1.")
    d.h2("5.2 Metode verifikasi")
    d.p("Setiap modul diuji dengan urutan yang sama: test atau vektor golden ditulis lebih dulu dan harus gagal, baru RTL ditulis sampai lulus. "
        "Tingkat verifikasinya bertahap, dari unit sampai sistem:")
    d.bullets([
        "L0: test Python untuk requantization, padding, argmax, tabel keputusan checker, dan batas bit.",
        "L1: testbench per modul RTL (lane untuk setiap implementasi, checker, FIFO dengan rasio clock acak, SPI slave, pembangkit bobot checksum).",
        "L2 dan L3: engine satu clock dibandingkan dengan golden model; logit dan kelas harus identik untuk paling sedikit 200 gambar.",
        "L4: sistem lengkap dengan SPI dan dua domain clock pada rasio clock 1,0; 1,3; 1,7; dan 2,0, ditambah fault injection.",
        "L5: governor dibandingkan dengan model Python pada paling sedikit 50 skenario.",
    ])
    d.p("Simulator utama adalah Icarus Verilog; xsim dari Vivado dipakai untuk modul vendor; Verilator dipakai untuk lint. Semua perintah berjalan "
        "lewat `python tools/run.py`, di Windows maupun Linux.")


def ch6(d: Doc, ctx) -> None:
    reg, lut, dsp = ctx["reg"], ctx["lut"], ctx["dsp"]
    d.h1("6", "Hasil sampai saat ini")
    d.callout("board", ["Semua hasil di bab ini berasal dari simulasi atau estimasi statis. Belum ada angka [HW]. Simulasi bisa membuktikan bahwa "
                        "logika SENTINEL benar, tetapi tidak bisa memunculkan error timing nyata."], title="SEMUA PRA-BOARD")
    d.h2("6.1 RTL cocok bit demi bit dengan golden model")
    pick = [("engine_s_k8_c1_n200", "engine, model `s`, lane LUT, C3 aktif, 200 gambar"),
            ("engine_s_k8_c1_dsp_n200", "engine, model `s`, lane DSP, C3 aktif, 200 gambar"),
            ("system_s_k8_c1", "sistem lengkap (SPI, dua clock), lane LUT"),
            ("system_s_k8_c1_dsp", "sistem lengkap (SPI, dua clock), lane DSP"),
            ("system_xs_r200", "sistem, lane di 2× clock aman"),
            ("checker_k8_c1", "komparator melawan model checker"),
            ("governor", "governor melawan model Python"),
            ("wc_gen_k8_c1_1m", "pembangkit bobot checksum, 10⁶ vektor"),
            ("system_micro_autogov", "governor otomatis dengan rekonfigurasi MMCM (model)")]
    rows = []
    for name, desc in pick:
        e = reg.get(name)
        if e:
            rows.append([f"`{name}`", desc, e["summary"].replace("PASS ", "", 1) if e["summary"].startswith("PASS PASS") else e["summary"], e["date"]])
    d.table(["Bench", "Yang diuji", "Hasil", "Tanggal"], rows, [2700, 3400, 2338, 1200],
            caption="Regresi RTL terpilih [SIM], dari `results/sim/rtl_regression.jsonl`", size=16)
    d.p(f"Lulus berarti setiap logit, kelas, dan keputusan identik dengan model acuan. Seluruh suite otomatis ({ctx['tests']} test) lulus pada 18 November 2026.")
    d.h2("6.2 Kampanye fault injection")
    single = camp_row(ctx, 8, 1, "single")
    dual0 = camp_row(ctx, 8, 0, "dual")
    dual1 = camp_row(ctx, 8, 1, "dual")
    d.p(f"Model checker diberi akumulator nyata dari golden model ({ctx['camp']['images']} gambar uji) dan disuntik error XOR [SIM]. Ini menguji logika "
        "keputusan, bukan perilaku timing chip.")
    d.figure(fig("fig_campaign"), "Hasil kampanye injeksi untuk K = 8 dan K = 16 [SIM], dari `results/sim/campaign_s.json`.", 16.5)
    d.bullets([
        f"Error satu lane: {nf(single['corrected'])} dari {nf(single['n'])} terkoreksi, dengan atau tanpa C3.",
        f"Error dua lane tanpa C3: {nf(dual0['miscorrected'])} dari {nf(dual0['n'])} salah dikoreksi ({pct(dual0['miscorrected'] / dual0['n'], 1)}); sisanya dihitung ulang.",
        f"Error dua lane dengan C3: {nf(dual1['miscorrected'])} salah koreksi; {nf(dual1['recompute'])} dari {nf(dual1['n'])} dihitung ulang.",
        "Error di lane checksum: semuanya dihitung ulang, sesuai kebijakan konservatif.",
    ])
    d.h2("6.3 Sintesis di chip resmi")
    d.p("Desain lengkap, termasuk MMCM, SPI, memori, dan semua logika pemeriksa, diimplementasikan di XC7S25CSGA225-1 dengan Vivado 2025.2. "
        "Bitstream belum dibuat karena standar I/O board belum dikonfirmasi panitia.")
    ul, ud = lut["utilization_post_route"], dsp["utilization_post_route"]
    cl, cd = clocks(lut), clocks(dsp)
    rows = [["Slice LUT", f"{nf(ul['lut']['used'])} ({nf(ul['lut']['util_pct'], 1)}%)", f"{nf(ud['lut']['used'])} ({nf(ud['lut']['util_pct'], 1)}%)"],
            ["Flip-flop", nf(ul["ff"]["used"]), nf(ud["ff"]["used"])],
            ["Block RAM", f"{nf(ul['bram_tile']['used'])} dari 45", f"{nf(ud['bram_tile']['used'])} dari 45"],
            ["DSP48E1", f"{nf(ul['dsp']['used'])} dari 80", f"{nf(ud['dsp']['used'])} dari 80"],
            ["clk_safe (target 125 MHz)", f"{nf(cl['clk_safe_raw']['fmax_mhz'], 1)} MHz", f"{nf(cd['clk_safe_raw']['fmax_mhz'], 1)} MHz"],
            ["Lane, dianalisis di", f"{nf(1000 / cl['clk_fast_turbo']['period_ns'], 0)} MHz → Fmax {nf(cl['clk_fast_turbo']['fmax_mhz'], 1)} MHz",
             f"{nf(1000 / cd['clk_fast_turbo']['period_ns'], 0)} MHz → Fmax {nf(cd['clk_fast_turbo']['fmax_mhz'], 1)} MHz"],
            ["Daya (tanpa data aktivitas)", f"{lut['power']['total_w']} W", f"{dsp['power']['total_w']} W"]]
    d.table(["Butir", "Varian LUT", "Varian DSP"], rows, [3400, 3119, 3119],
            caption="Dua varian lengkap di XC7S25CSGA225-1 [VIVADO-STA], dari `results/vivado/official/` dan `results/vivado/official_dsp/`", size=18,
            align=["left", "right", "right"])
    d.figure(fig("fig_brief_variants"), "Kiri: pemakaian resource kedua varian. Kanan: Fmax statis clk_safe dan lane, dibandingkan dengan clock "
             "aman 125 MHz dan batas suplai operand 250 MHz [VIVADO-STA].", 15.5)
    d.p("Gambar 6.2 memperlihatkan hal yang penting untuk cerita SENTINEL. Generator operand menghasilkan R = 2 operand set per siklus clock aman, "
        "jadi lane tidak bisa diberi makan lebih cepat dari 2 × 125 = 250 MHz. Lane DSP sudah melewati batas itu menurut STA, sedangkan lane LUT "
        "berhenti di sekitar 141 MHz. Akibatnya dibahas terbuka di Bagian 8.2.")
    d.h2("6.4 Waktu per gambar")
    cyc, _ = cycles(reg["engine_s_k8_c1_n200"])
    t_c = cyc * 8e-6
    rows = []
    for mhz in (1, 5, 10, 20):
        t_s = 3072 * 8 / (mhz * 1e6) * 1e3
        rows.append([f"{mhz}", nf(t_s, 3), nf(t_c, 3), nf(t_s + t_c, 3), pct(t_s / (t_s + t_c), 0)])
    d.p(f"Komputasi satu gambar di clock aman memakan {nf(t_c, 3)} ms [SIM] × [VIVADO-STA]. Gambar 3.072 byte harus dikirim lewat SPI, dan kecepatan "
        "SPI board belum diketahui [UNKNOWN]. Tabel 6.3 memakai beberapa asumsi.")
    d.table(["SPI (MHz, asumsi)", "Kirim gambar (ms)", "Komputasi (ms)", "Jumlah (ms)", "Porsi kirim"], rows, [2100, 1900, 1900, 1900, 1838],
            caption="Anggaran latensi per gambar [SIM] × [VIVADO-STA]; kecepatan SPI adalah asumsi", size=18, align=["right"] * 5)
    d.p("Overclocking hanya memendekkan kolom komputasi. Karena itu laporan akhir akan memisahkan waktu komputasi FPGA dan waktu ujung ke ujung.")


def ch7(d: Doc, ctx) -> None:
    d.h1("7", "Apakah ini ide baru?", page_break=False)
    d.p("Jawaban singkatnya: komponen dasarnya sudah ada. Yang kami tawarkan adalah gabungan tertentu dan cara pemulihannya, yang sejauh "
        "penelusuran kami per November 2026 belum kami temukan dalam bentuk yang sama. Kata \"pertama\" atau \"baru\" tidak kami pakai untuk "
        "ABFT, dual checksum, atau overclocking CNN. Teks lengkap Li dkk. (ITC-Asia 2019) belum kami dapat, jadi klaim tentang cara pemulihan "
        "selalu disertai \"sejauh penelusuran kami\".")
    d.h2("7.1 Yang sudah ada di literatur")
    d.table(["Komponen", "Status", "Karya"], [
        ["Checksum (ABFT) untuk konvolusi", "sudah ada", "Huang & Abraham 1984; Zhao dkk. 2021 (FT-CNN); Hari dkk. 2020"],
        ["Overclocking akselerator CNN di FPGA dengan deteksi checksum lalu hitung ulang", "sudah ada", "Marty, Yuki & Derrien, IEEE TCAD 2020"],
        ["Overclocking otomatis dengan monitor delay", "sudah ada", "Jiang dkk. (AOS), IEEE TCAD 2023"],
        ["Overclocking dengan alur deteksi sampai pemulihan", "sudah ada; cara pemulihannya belum kami baca", "Li dkk., ITC-Asia 2019 (baru abstrak)"],
        ["Karakterisasi error timing array MAC di FPGA", "sudah ada, bukan CNN", "Chamberlin dkk., JLPEA 2024"],
        ["Koreksi keluaran berbasis kode di array PE terhadap soft error", "disebut sudah bisa", "Gao dkk., IEEE TVLSI 2024 (abstrak)"]],
        [3900, 2300, 3438], caption="Karya terkait (`docs/PRIOR_ART.md`)", size=17)
    d.h2("7.2 Yang berbeda di SENTINEL")
    d.p("Tiga hal ini belum kami temukan dalam literatur yang sudah kami baca. Ketiganya baru boleh ditulis sebagai hasil kalau datanya ada.")
    d.numbered([
        "Koreksi error satu lane di tempat, tanpa jeda dan tanpa hitung ulang, digabung dengan overclocking akselerator CNN, lalu dibandingkan "
        "langsung dengan cara deteksi-lalu-ulang pada desain dan board yang sama (mode 1 lawan mode 2).",
        "Pemilihan clock per layer pada satu engine oleh governor yang seluruhnya berada di dalam FPGA, tanpa CPU. Marty dkk. mengatur frekuensi "
        "dari software per tile, dan frekuensi per layer hanya mereka sebut untuk akselerator streaming dengan clock manager terpisah per layer.",
        "Atlas error timing untuk CNN sungguhan di FPGA kelas kecil (Spartan-7), per frekuensi, layer, lane, dan posisi bit.",
    ])
    d.h2("7.3 Menjawab alasan Marty dkk. menolak koreksi")
    d.p("Marty dkk. (Bagian VI-C makalah mereka) memberi tiga alasan untuk tidak mengoreksi. Tanggapan kami berupa rencana pengukuran:")
    d.table(["Alasan mereka", "Tanggapan SENTINEL"], [
        ["Dua error atau lebih sering terjadi saat overclocking.",
         "Mereka memeriksa satu checksum per tile berisi ratusan sampai ribuan keluaran. SENTINEL memeriksa per unit: satu posisi keluaran untuk K kanal. "
         "Peluang dua error dalam satu pemeriksaan jauh lebih kecil pada frekuensi yang sama [INFERENCE]. Dua error tetap dikenali C3 dan dihitung "
         "ulang. Seberapa sering hal itu terjadi adalah H1, diukur di E1."],
        ["Hitung ulang tidak mahal.",
         "Benar ketika laju error rendah. Koreksi memberi manfaat di laju error menengah, tempat hitung ulang mulai memakan keuntungan. E4 "
         "membandingkan keduanya; kalau koreksi tidak menang, itu dilaporkan."],
        ["Logika pemulihan mahal di area.",
         "Biaya pemeriksa dan korektor diambil dari laporan Vivado [VIVADO-STA]. Contohnya biaya C3 di sintesis out-of-context: 943 LUT pada lane LUT, dan 775 LUT plus 1 DSP pada lane DSP."]],
        [3000, 6638], caption="Tiga alasan dan tanggapannya", size=17)


def ch8(d: Doc, ctx) -> None:
    dsp, lut = ctx["dsp"], ctx["lut"]
    d.h1("8", "Keterbatasan dan risiko", page_break=False)
    d.p("Bab ini mendaftar batasan yang perlu diketahui sebelum menilai SENTINEL, termasuk yang melemahkan klaim kami sendiri.")
    d.h2("8.1 Batasan teknis")
    d.bullets([
        "Checksum melindungi perhitungan MAC, bukan input. Aktivasi yang rusak setelah keluar dari domain aman dikirim sama ke semua lane, termasuk "
        "lane checksum, sehingga identitasnya tetap berlaku dan error itu lolos. Mitigasinya: jalur operand di domain cepat dibuat pendek dan diberi "
        "register tambahan, dan setiap eksperimen membandingkan hasil akhir dengan golden model untuk menghitung silent data corruption.",
        "Error di banyak lane sekaligus bisa lolos atau salah dikoreksi tanpa C3; dengan C3 jatuh ke hitung ulang. Lajunya di hardware belum diketahui.",
        "Simulasi tidak bisa memunculkan error timing nyata. Semua angka deteksi dan koreksi di Bab 6 menguji logika, bukan chip.",
        "Waktu ujung ke ujung mungkin didominasi pengiriman gambar lewat SPI dan kamera, bukan komputasi (Tabel 6.3).",
        "Akurasi sekitar 80% adalah angka CIFAR-10. Yang dijamin desain ini adalah hasil bit-exact terhadap model integer, bukan akurasi tertinggi.",
    ])
    d.h2("8.2 Pertanyaan tentang lane DSP")
    d.p(f"Pertanyaan yang hampir pasti muncul: kalau lane DSP sudah aman sampai {nf(clocks(dsp)['clk_fast_turbo']['fmax_mhz'], 1)} MHz menurut STA, "
        "apa gunanya SENTINEL? Jawaban kami terbagi dua.")
    d.p("Untuk kecepatan murni di chip ini dengan K = 8, varian DSP memang lebih baik. Engine-nya dibatasi suplai operand 250 MHz, bukan lane, sehingga "
        f"overclock lane DSP tidak menambah throughput. Lane LUT berhenti di sekitar {nf(clocks(lut)['clk_fast_turbo']['fmax_mhz'], 0)} MHz; overclock "
        "ditambah koreksi paling jauh membawanya ke 250 MHz, setara varian DSP di clock aman, tidak lebih [INFERENCE]. Bagian ini kami akui sebagai "
        "kelemahan klaim kecepatan.")
    d.p("Karena itu kedua varian punya peran berbeda (ADR-030). Varian DSP menjadi varian kecepatan dan demo, dengan checksum tetap aktif menangkap error "
        "dari sumber apa pun. Varian LUT menjadi varian riset, tempat pengali benar-benar jalur kritis, sehingga perilaku error timing, koreksi, dan "
        "governor bisa dipelajari. Percepatan overclock hanya dibandingkan varian LUT lawan varian LUT yang sama di clock aman, dan angka kedua varian "
        "tidak pernah dicampur. Supaya overclock juga berguna untuk varian tercepat, suplai operand harus dinaikkan (ADR-032); studi itu dijadwalkan "
        "setelah gerbang G1.")
    d.h2("8.3 Risiko proyek")
    d.table(["Risiko", "Dampak", "Penanganan"], [
        ["H1 ternyata salah: error nyata sering mengenai banyak lane", "koreksi jarang terpakai; SENTINEL setara deteksi-lalu-ulang",
         "tetap dilaporkan sebagai temuan; mode 1 dan atlas error tetap bernilai"],
        ["Board belum bisa diberi daya tanpa Raspberry Pi; standar I/O belum resmi", "fase board tertunda",
         "pertanyaan sudah dikirim ke panitia; Raspberry Pi apa pun bisa dipakai sebagai sumber daya"],
        ["Margin timing tipis di clock aman", "perubahan kecil bisa membuat laporan resmi gagal timing",
         "laporan resmi diulang setiap RTL berubah; ada cadangan 100 MHz (ADR-015)"],
        ["Kelas target diumumkan terlambat", "akurasi akhir belum bisa dilaporkan", "alur latih ulang dan muat ulang bobot lewat SPI sudah ada"],
        ["Kategori Class 2 belum dikonfirmasi", "risiko administratif", "proyek juga memenuhi syarat Class 1 Level 3"]],
        [3200, 2900, 3538], caption="Risiko utama dan penanganannya", size=17)


def ch9(d: Doc, ctx) -> None:
    d.h1("9", "Rencana kerja")
    d.figure(fig("fig_brief_timeline"), "Milestone pra-board (M0–M14) dan fase board (B1–B6), dengan gerbang internal dan tanggal resmi. "
             "Tanggal board tiba berasal dari info tim.", 17.0)
    d.p("Semua milestone pra-board selesai di simulasi. Satu bagian M10, rekonfigurasi MMCM yang sebenarnya, baru bisa dibuktikan di board. "
        "Fase board berjalan berurutan:")
    d.table(["Tahap", "Isi", "Hasil"], [
        ["B1", "XDC dari dokumen resmi, bitstream, pemrograman lewat JTAG", "desain berjalan di ZERO7"],
        ["B2", "Bring-up langkah demi langkah (clock, LED, SPI, suhu XADC)", "setiap blok terbukti hidup"],
        ["B3", "E7 di clock aman: seluruh set validasi", "bit-exact di hardware (gerbang G1, 13 Desember 2026)"],
        ["B4", "E1 sampai E3: sapuan frekuensi manual", "atlas error; uji H1, H2, H3"],
        ["B5", "E4, governor otomatis, E6", "throughput tiga mode; perilaku terhadap suhu (gerbang G2, 3 Januari 2027)"],
        ["B6", "Hasil final, grafik, video demo", "laporan 31 Januari 2027"]],
        [900, 5000, 3738], caption="Fase board", size=18)
    d.p("Aturan fase board: selalu mulai dari clock aman, overclocking baru dimulai setelah E7 bit-exact, tegangan tidak pernah diubah, dan suhu "
        "dipantau. Kalau G1 meleset lebih dari satu minggu, pemilihan clock per layer diganti satu clock turbo global supaya jadwal tetap aman. "
        "Setelah 17 Januari 2027 tidak ada fitur baru, hanya pengukuran dan penulisan.")


def ch10(d: Doc, ctx) -> None:
    single = camp_row(ctx, 8, 1, "single")
    dual1 = camp_row(ctx, 8, 1, "dual")
    d.h1("10", "Pertanyaan yang mungkin diajukan")
    qa = [
        ("Apa tujuan utama SENTINEL dalam satu kalimat?",
         "Mempercepat akselerator CNN di FPGA kecil dengan menjalankan lane MAC di atas frekuensi aman, sambil menjamin hasil tetap sama persis "
         "dengan model acuan lewat checksum yang mendeteksi dan memperbaiki error."),
        ("Algoritmanya apa?",
         "CNN integer 8 bit (tiga konvolusi dan satu fully connected) yang dijalankan di K lane MAC paralel, ditambah checksum tertimbang "
         "(ABFT): C1 = Σw_{k}, C2 = Σk·w_{k}, C3 = Σk²·w_{k}. Selisih d_{1}, d_{2}, d_{3} menentukan ada error atau tidak, lane mana (j = d_{2}/d_{1}), "
         "dan nilai koreksinya (Bagian 4.4 sampai 4.6). Governor memilih clock per layer dari jumlah error."),
        ("Apakah ini terbaru?",
         "Komponennya tidak baru: ABFT ada sejak 1984 dan overclocking CNN dengan checksum sudah dilakukan Marty dkk. Yang belum kami temukan adalah "
         "koreksi di tempat yang digabung dengan overclocking, governor clock per layer di dalam FPGA, dan atlas error CNN di Spartan-7 (Bab 7)."),
        ("Bagaimana pemeriksa bisa dipercaya kalau chip sedang di-overclock?",
         "Pemeriksa, memori, dan kontrol tidak di-overclock. Mereka di domain clock aman yang lolos STA. Yang dipercepat hanya lane MAC."),
        ("Dari mana tahu error hanya mengenai satu lane?",
         f"Belum tahu. Itu hipotesis H1 dan diukur di E1. Simulasi hanya menunjukkan apa yang terjadi kalau memang begitu: {nf(single['corrected'])} "
         f"dari {nf(single['n'])} error satu lane terkoreksi, dan dengan C3 tidak ada salah koreksi pada {nf(dual1['n'])} error dua lane [SIM]."),
        ("Kenapa tidak cukup deteksi lalu hitung ulang?",
         "Mungkin memang cukup. Mode 1 SENTINEL adalah cara itu, mode 2 adalah koreksi, dan keduanya ada di bitstream yang sama supaya E4 bisa "
         "membandingkannya dengan adil. Koreksi diharapkan menang ketika laju error menengah."),
        ("Kalau lane DSP sudah cepat, kenapa repot dengan overclock?",
         "Untuk kecepatan di chip ini, varian DSP memang lebih baik, dan kami mengakuinya. Varian DSP menjadi varian demo dengan checksum aktif; "
         "varian LUT menjadi varian riset overclock (Bagian 8.2)."),
        ("Apakah tegangan chip diubah?",
         "Tidak pernah. SENTINEL hanya mengubah frekuensi clock, dan suhu dipantau lewat XADC."),
        ("Berapa percepatannya?",
         "Belum ada angka [HW]. Targetnya ditulis sebelum pengukuran: throughput bit-exact mode koreksi ≥ 1,2× mode hitung ulang dan ≥ 1,4× desain "
         "yang lolos timing [PROPOSAL]. Kalau target itu tidak tercapai, hasilnya tetap dilaporkan."),
        ("Akurasinya hanya sekitar 80%?",
         "Itu angka CIFAR-10, dataset pengganti karena kelas lomba belum diumumkan. Model akan dilatih ulang untuk kelas resmi tanpa sintesis ulang."),
        ("Apa yang terjadi kalau board terlambat?",
         "Laporan sintesis resmi, verifikasi bit-exact, dan kampanye injeksi sudah selesai tanpa board. Klaim inti tentang error timing baru bisa ditulis "
         "dengan data board, jadi fase board diprioritaskan begitu daya tersedia."),
    ]
    for q, a in qa:
        d.h3(q)
        d.p(a)


def appendices(d: Doc, ctx) -> None:
    d.h1("A", "Glosarium", page_break=False)
    d.table(["Istilah", "Arti"], [
        ["ABFT", "algorithm-based fault tolerance: pemeriksaan hasil hitungan memakai sifat aljabar algoritmanya, misalnya checksum"],
        ["Akumulator", "register yang menjumlahkan hasil perkalian selama satu unit hitung"],
        ["BUFGCTRL", "buffer clock global Xilinx yang bisa memilih salah satu dari dua clock tanpa glitch"],
        ["CDC", "clock domain crossing: sinyal yang menyeberang dari satu domain clock ke domain lain"],
        ["Fmax", "frekuensi tertinggi yang masih lolos timing menurut STA: 1000 / (periode − WNS)"],
        ["Golden model", "model integer Python yang menjadi acuan; RTL harus identik dengannya"],
        ["Lane", "satu unit MAC yang menghitung satu kanal keluaran"],
        ["MAC", "multiply-accumulate: satu perkalian lalu penjumlahan ke akumulator"],
        ["MMCM", "mixed-mode clock manager: pembangkit clock di FPGA Xilinx; yang kedua bisa diubah frekuensinya saat berjalan"],
        ["PTQ", "post-training quantization: kuantisasi setelah training selesai"],
        ["RTL", "register-transfer level: deskripsi hardware dalam Verilog"],
        ["Slack, WNS", "sisa waktu sebelum tepi clock; WNS adalah slack terburuk di desain"],
        ["STA", "static timing analysis: analisis timing kasus terburuk oleh alat sintesis"],
        ["Unit hitung", "satu posisi keluaran untuk satu grup K kanal"]], [2200, TEXT_W - 2200], size=18)
    d.h1("B", "Keputusan desain yang penting", page_break=False)
    d.p("Daftar lengkap ada di `docs/DECISIONS.md`. Yang paling menentukan bentuk SENTINEL:")
    d.table(["ADR", "Keputusan"], [
        ["ADR-001", "dataflow output-stationary, satu lane per kanal keluaran"],
        ["ADR-002", "bobot checksum dihitung on-the-fly di domain aman"],
        ["ADR-003", "unit hitung ulang = jendela pool × grup, ditunda ke akhir layer"],
        ["ADR-011", "lane checksum ketiga (C3) untuk mencegah salah koreksi dua lane"],
        ["ADR-013", "target dikunci ke XC7S25CSGA225-1; varian resmi model `s`, K = 8, C3 aktif"],
        ["ADR-014", "laporan sintesis resmi desain lengkap sebagai deliverable utama"],
        ["ADR-021", "reset, synchronizer, dan aturan penyeberangan domain clock"],
        ["ADR-029", "pohon penjumlah datar untuk bobot checksum"],
        ["ADR-030", "dua varian lane: DSP untuk kecepatan dan demo, LUT untuk riset overclock"],
        ["ADR-028, ADR-032", "melewati aktivasi nol dan menaikkan suplai operand; setelah G1"]], [2400, TEXT_W - 2400], size=18)
    d.h1("C", "Referensi", page_break=False)
    d.bullets([
        "K. K. Parhi, ~VLSI Digital Signal Processing Systems: Design and Implementation~, John Wiley & Sons, 1999.",
        "T. Marty, T. Yuki, S. Derrien, \"Safe Overclocking for CNN Accelerators through Algorithm-Level Error Detection\", IEEE TCAD 39(12):4777–4790, 2020.",
        "W. Jiang dkk., \"AOS: An Automated Overclocking System for High-Performance CNN Accelerator Through Timing Delay Measurement on FPGA\", IEEE TCAD, 2023.",
        "Chamberlin dkk., \"Understanding Timing Error Characteristics from Overclocked Systolic Multiply–Accumulate Arrays in FPGAs\", JLPEA 14(1):4, 2024.",
        "K.-H. Huang, J. A. Abraham, \"Algorithm-Based Fault Tolerance for Matrix Operations\", IEEE Transactions on Computers, 1984.",
        "K. Zhao dkk., \"FT-CNN: Algorithm-Based Fault Tolerance for Convolutional Neural Networks\", IEEE TPDS, 2021.",
        "S. K. S. Hari, M. Sullivan, T. Tsai, S. W. Keckler, \"Making Convolutions Resilient via Algorithm-Based Error Detection Techniques\", arXiv 2006.04984, 2020.",
        "Li dkk., \"Squeezing the Last MHz for CNN Acceleration on FPGAs\", ITC-Asia 2019, hlm. 151–156.",
        "Gao dkk., \"Detect and Replace: Efficient Soft Error Protection of FPGA-Based CNN Accelerators\", IEEE TVLSI 33(1), 2024.",
        "LSI Design Contest, halaman resmi <<https://www.lsi-contest.com/shiyou_1e.html>>, dibaca 18 November 2026.",
    ])


def build(ctx) -> Doc:
    d = Doc()
    cover(d, ctx)
    summary(d, ctx)
    for ch in (ch1, ch2, ch3, ch4, ch5, ch6, ch7, ch8, ch9, ch10, appendices):
        ch(d, ctx)
    return d


def main() -> int:
    ctx = load_context()
    make_figures(ctx)
    d = build(ctx)
    d.save(OUT_DOCX, "SENTINEL: penjelasan untuk dosen pembimbing", "SENTINEL · penjelasan untuk dosen pembimbing · 18 November 2026")
    print(f"wrote {OUT_DOCX.relative_to(ROOT)}")
    if "--no-pdf" not in sys.argv:
        ps = ROOT / "tools" / "study_guide" / "finalize_word.ps1"
        res = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(ps), "-Docx", str(OUT_DOCX)],
                             capture_output=True, text=True, cwd=ROOT)
        print(res.stdout.strip() or res.stderr.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
