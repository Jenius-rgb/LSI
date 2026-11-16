#!/usr/bin/env python3
"""Build the SENTINEL study guide (Indonesian) as build/study_guide/SENTINEL_materi_belajar.docx.

Prose is Indonesian because the guide is learning material for the team; every number is read
from result files in the repository or from build/study_guide/facts.json, which
tools/study_guide/figures.py computes from the golden, checker and governor models.
Run figures.py first, then this script, then (optional, Windows + Word) finalize_word.ps1 to
fill the table of contents and export a PDF.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FACTS, FIG, OUT, ROOT, git_head, load_json, nf, part_short, pct, regression_latest, vivado_rows  # noqa: E402
from docx_lib import (BLUE, INK2, NAVY, TEXT_W, Doc, delim, frac, func, gap, mi, mt, nary, para, rad, run, sub,  # noqa: E402
                      subsup, sup, acc)

OUT_DOCX = OUT / "SENTINEL_materi_belajar.docx"


def sn(x: int) -> str:
    """Signed integer with a true minus sign and Indonesian grouping."""
    return ("−" if x < 0 else "") + nf(abs(x))


def fig(name: str) -> Path:
    return FIG / f"{name}.png"


def load_context() -> dict:
    if not FACTS.exists():
        raise SystemExit("build/study_guide/facts.json is missing: run tools/study_guide/figures.py first")
    ctx = {"facts": json.loads(FACTS.read_text(encoding="utf-8")), "head": git_head()}
    ctx["arch"] = load_json("results/model/arch_s.json")
    ctx["fl"] = {m: load_json(f"results/model/{m}/float_result.json") for m in ("s", "xs")}
    ctx["qr"] = {m: load_json(f"results/model/{m}/quant_result.json") for m in ("s", "xs")}
    ctx["camp"] = load_json("results/sim/campaign_s.json")
    ctx["fit"] = load_json("results/sim/fit_report.json")
    ctx["viv"] = vivado_rows()
    ctx["reg"] = regression_latest()
    reports = ROOT / "fpga" / "reports"
    ctx["viv_failed"] = sorted(p.name[: -len(".log")] for p in reports.glob("*_final.log") if not (p.with_suffix("") / "summary.txt").exists())
    ctx["n_tests"] = len(list((ROOT / "tests").glob("test_*.py")))
    official = ROOT / "results" / "vivado" / "official" / "summary.json"
    ctx["official"] = json.loads(official.read_text(encoding="utf-8")) if official.exists() else None
    part_check = ROOT / "results" / "vivado" / "part_check.txt"
    ctx["part"] = {}
    if part_check.exists():
        for line in part_check.read_text(encoding="utf-8").splitlines():
            words = line.split()
            if len(words) >= 4 and words[:2] == ["CHECK", "part_property"]:
                ctx["part"][words[2]] = words[3]
    return ctx


def viv(ctx, part, k, impl, c3):
    return next(r for r in ctx["viv"] if r["part"] == part and r["K"] == str(k) and r["LANE_IMPL"] == str(impl) and r["C3_EN"] == str(c3))


def cycles_from(summary: str) -> tuple[int, int]:
    m = re.search(r"cycles_mean=(\d+) ideal=(\d+)", summary)
    return int(m.group(1)), int(m.group(2))


# ============================================================================ cover + TOC


def cover(d: Doc, ctx) -> None:
    d.add(para([run("LSI DESIGN CONTEST 2027  ·  MATERI BELAJAR TIM", b=True, color=BLUE, size=18, spacing=20)], before=360, after=80))
    d.add(para([run("SENTINEL", b=True, color=NAVY, size=84)], after=0, line=240))
    d.add(para([run("CNN, akselerator FPGA, dan isi repo — dijelaskan dari dasar", color=INK2, size=30)], after=280, line=260))
    d.add(para([d.picture(fig("fig_cover"), 17.0, "Gambar uji CIFAR-10 dan 16 peta fitur conv1")], align="center", after=60))
    d.p("Sampul: gambar uji CIFAR-10 nomor 1 (kapal) dan 16 peta fitur conv1 dari golden model integer [SIM]; kecerahan dinormalisasi per kanal.",
        align="center", size=17, color=INK2, after=280)
    d.p("Materi ini menjelaskan CNN dari nol, cara CNN dijalankan sebagai hardware di FPGA, dan apa yang sudah dibangun di repo SENTINEL: "
        "akselerator CNN INT8 dengan dual checksum dan overclocking per layer untuk board ZERO7 (Spartan-7). Satu bab khusus menjelaskan "
        "dengan jujur apa yang belum bisa dijawab karena board belum ada, dan bab terakhir memberi daftar bacaan.", after=240)
    rows = [["Versi materi", "1.1, 16 November 2026 (versi 1.0: 12 November 2026)"],
            ["Fase proyek", "PRA-BOARD: board ZERO7 belum ada di tangan"],
            ["Sumber angka", f"repo SENTINEL, branch `pra-board`, commit `{ctx['head']}`"],
            ["Dibangun ulang dengan", "`python tools/study_guide/figures.py` lalu `python tools/study_guide/build_docx.py`"],
            ["Penting", "Tidak ada angka [HW] di materi ini. Semua angka berasal dari simulasi [SIM], model error buatan [SYNTHETIC], "
                        "atau estimasi statis Vivado [VIVADO-STA]."]]
    d.table([], rows, [2600, TEXT_W - 2600], size=19, first_col_bold=True)
    d.page_break()
    d.add(para([run("Daftar isi", b=True, color=NAVY, size=40)], after=240, border_bottom=BLUE))
    d.toc()


# ============================================================================ change log


def changes(d: Doc, ctx) -> None:
    off = ctx["official"]
    d.chapter = "P"
    d.add(para([run("Perubahan sejak versi 1.0")], style="Heading1", page_break_before=True))
    d.p("Versi 1.0 ditulis 12 November 2026, sebelum dokumen ZERO7 dibaca. Versi 1.1 memuat fakta resmi yang terbit 2 dan 10 November 2026, "
        "keputusan baru, dan hasil pengembangan sesudahnya. Dasar CNN, kuantisasi, dan timing (Bab 2 sampai 4) tidak berubah.")
    d.h2("Fakta resmi baru")
    d.bullets(["Chip lomba adalah AMD Spartan-7 XC7S25CSGA225-1, dan laporan sintesis untuk chip itu wajib bagi semua tim [OFFICIAL].",
               "Tugas dibagi dua kelas: Image Classification Class dan ZERO7 Class [OFFICIAL].",
               "Dokumen ZERO7 terbit: tabel pin FPGA dan panduan penyiapan. Clock board 20 MHz di pin B13, SPI0 Raspberry Pi di pin A8, A6, A7, D9, "
               "LED WS2812B di pin N1, pemrograman lewat kabel JTAG-HS3, dan board dipasang di Raspberry Pi 5 [OFFICIAL].",
               "Yang masih belum tertulis: tegangan dan standar I/O tiap bank, serta file `Zero7.xdc` resmi [UNKNOWN]."])
    d.h2("Keputusan baru")
    d.bullets(["ADR-013: target dikunci ke XC7S25CSGA225-1 dengan varian resmi model `s`, K = 8, lane `lut`, C3 aktif.",
               "ADR-014: laporan sintesis resmi untuk desain lengkap menjadi deliverable utama.",
               "ADR-015: clock 20 MHz menjadi input MMCM; clk_safe diturunkan dari VCO 1.000 MHz dan frekuensinya ditetapkan hasil STA (Bagian 7.5).",
               "ADR-016: peta I/O ZERO7. FPGA hanya memakai jalur miliknya; tombol dan LED yang berbagi jalur diserahkan ke perangkat lunak Pi.",
               "ADR-017 dan ADR-018: indikator WS2812B dan suhu XADC diterima, implementasinya menyusul.",
               "ADR-019: boot dari flash QSPI ditunda. ADR-020: kategori tetap Class 2 Level 3 dan kalimat klaim diperketat.",
               "ADR-021: aturan reset, synchronizer, dan penyeberangan domain clock, ditulis sesudah implementasi lengkap pertama."])
    d.h2("Hasil baru")
    items = []
    if off:
        u = off["utilization_post_route"]
        items.append(f"Desain lengkap `top_board` terimplementasi di chip resmi dengan clk_safe {nf(1000 / float(off['SAFE_DIV']))} MHz: "
                     f"{nf(u['lut']['used'])} dari {nf(u['lut']['available'])} LUT "
                     f"({nf(u['lut']['util_pct'], 1)}%), {nf(u['ff']['used'])} flip-flop, {nf(u['bram_tile']['used'], 1 if u['bram_tile']['used'] % 1 else 0)} dari "
                     f"{nf(u['bram_tile']['available'])} block RAM, slack setup terburuk {nf(float(off['design_wns_ns']), 3)} ns [VIVADO-STA] (Bagian 7.5).")
    c1 = ctx["reg"].get("engine_s_k8_c1_n200")
    if c1:
        items.append(f"Varian resmi (C3 aktif) bit-exact di simulasi RTL: `{c1['summary']}` [SIM].")
    sysb = ctx["reg"].get("system_s_k8_c1")
    if sysb:
        items.append(f"Sistem dua clock dengan varian resmi lulus di simulasi RTL: `{sysb['summary']}` [SIM].")
    items.append("Penelusuran literatur diperbarui (`docs/research/RISET_WEB_2026-11.md`): koreksi berbasis checksum dan overclocking akselerator CNN "
                 "sudah ada di literatur, sehingga laporan memakai kalimat \"sejauh penelusuran kami\".")
    d.bullets(items)
    d.h2("Bagian materi yang berubah")
    d.table(["Bagian", "Perubahan"], [
        ["1.2", "aturan lomba terbaru: dua kelas, laporan sintesis wajib, Raspberry Pi 5"],
        ["4.1", "chip dan resource-nya sekarang resmi"],
        ["5.7", "clock input 20 MHz; yang belum ada tinggal sequencer rekonfigurasi"],
        ["6.5", "ADR-013 sampai ADR-021"],
        ["7.5, 7.6", "laporan sintesis resmi; ringkasan status baru"],
        ["8.3, 8.4, 8.6", "fakta board yang sudah dan belum diketahui; pekerjaan yang menunggu"],
        ["9.5, Lampiran C", "dokumen ZERO7 dari panitia; file sumber baru"],
    ], [1800, TEXT_W - 1800], size=18)


# ============================================================================ chapter 0


def ch0(d: Doc, ctx) -> None:
    d.h1("0", "Cara memakai materi ini")
    d.p("Materi ini disusun seperti buku pegangan kuliah singkat. Setiap bab dibuka dengan tujuan belajar, lalu berisi penjelasan, rumus, "
        "dan gambar, dan ditutup dengan latihan. Kunci jawaban ada di Lampiran B. Prasyaratnya cukup aljabar SMA, sedikit Python, dan logika "
        "digital dasar (gerbang logika dan flip-flop); kalkulus hanya muncul sekilas di bagian training.")
    d.figure(fig("fig_path"), "Jalur belajar. Bab 2 sampai 4 membangun dasar, bab 5 sampai 7 menjelaskan SENTINEL dan buktinya, "
                              "bab 8 membahas yang masih menunggu board, dan bab 9 berisi sumber bacaan.", width_cm=15.0)
    d.h2("0.1 Label angka")
    d.p("Proyek ini punya aturan keras: setiap angka harus bisa dilacak ke skrip dan log di repo, dan harus diberi label asal-usulnya. "
        "Label yang sama dipakai di seluruh materi ini.")
    d.table(["Label", "Artinya", "Contoh di materi ini"], [
        ["[SIM]", "Hasil simulasi RTL atau model Python. Contoh hitung yang dihitung skrip Python di repo juga memakai label ini, dengan tambahan kata \"ilustrasi\".", "akurasi model integer, hasil testbench, contoh konvolusi"],
        ["[SYNTHETIC]", "Memakai model error timing buatan (`model/fault_model.py`). Bukan pengukuran. Grafiknya wajib diberi watermark \"SYNTHETIC — NOT MEASURED\".", "contoh grafik E1, E4, E6 di Bab 8"],
        ["[VIVADO-STA]", "Estimasi statis dari laporan timing atau resource Vivado. Sifatnya konservatif.", "Fmax dan jumlah LUT di Bab 7"],
        ["[HW]", "Diukur di board sungguhan.", "belum ada"],
        ["[OFFICIAL]", "Tertulis di dokumen resmi panitia (`docs/official/`).", "batas laporan 31 Januari 2027"],
        ["[UNKNOWN] [INFERENCE] [PROPOSAL]", "Belum diketahui, dugaan, atau usulan yang belum dikonfirmasi.", "part number ZERO7, kategori lomba"],
    ], [1900, 4900, TEXT_W - 6800], caption="Label asal-usul angka.", size=17)
    d.h2("0.2 Kotak-kotak di materi ini")
    d.bullets(["**Intuisi**: penjelasan dengan analogi sebelum masuk ke rumus.",
               "**Rumus kunci**: rumus yang perlu diingat.",
               "**Di SENTINEL**: bagaimana konsep umum itu dipakai di proyek ini.",
               "**Belum bisa dijawab tanpa board**: pertanyaan yang jawabannya hanya bisa datang dari pengukuran [HW].",
               "**Latihan**: soal singkat untuk mengecek pemahaman."])
    d.h2("0.3 Dari mana angka di materi ini")
    d.p("Semua gambar dan angka dibangkitkan ulang oleh dua skrip di repo. Skrip itu membaca file hasil yang sudah di-commit, misalnya "
        "`results/model/s/quant_result.json`, `results/sim/campaign_s.json`, dan `fpga/reports/summary.csv`, lalu menjalankan golden model "
        "untuk contoh hitung. Daftar lengkap file sumber ada di Lampiran C.", keep_next=True)
    d.code(["python tools/study_guide/figures.py     # gambar + build/study_guide/facts.json",
            "python tools/study_guide/build_docx.py  # dokumen .docx ini"])


# ============================================================================ chapter 1


def ch1(d: Doc, ctx) -> None:
    d.h1("1", "SENTINEL dalam satu halaman")
    d.p("SENTINEL adalah nama kerja proyek akselerator CNN untuk 30th LSI Design Contest 2027 di Chitose, Hokkaido [OFFICIAL]. Board targetnya "
        "ZERO7, sebuah HAT Raspberry Pi dengan FPGA AMD Spartan-7 [OFFICIAL]. Idenya bisa diringkas dalam empat kalimat:")
    d.numbered(["Mengklasifikasi gambar 32×32 dengan CNN integer yang hasilnya **bit-exact** dengan golden model Python: setiap bit logit sama, bukan hanya \"hampir sama\".",
                "Menjalankan lane MAC (pengali-penjumlah) **lebih cepat dari frekuensi aman** hasil analisis timing, supaya throughput naik.",
                "Menjaga lane itu dengan **dual checksum** (C1, C2, dan opsional C3), sehingga error akibat overclocking bisa dideteksi, dilokalisasi ke lane tertentu, lalu dikoreksi tanpa menghitung ulang.",
                "Memilih clock untuk **setiap layer** secara otomatis dengan **governor** di dalam FPGA, dan menyediakan alat ukur untuk eksperimen E1–E8."])
    d.callout("intuisi", [
        "Bayangkan delapan kasir yang menghitung belanjaan sangat cepat. Sesekali ada yang salah hitung karena terburu-buru. Supervisor menyimpan "
        "dua angka kontrol: jumlah semua hasil kasir, dan jumlah berbobot (hasil kasir ke-1 dikali 1, kasir ke-2 dikali 2, dan seterusnya).",
        "Kalau jumlah biasa meleset sebesar e, supervisor tahu ~besarnya~ kesalahan. Kalau jumlah berbobot meleset sebesar 5e, berarti kasir nomor 5 "
        "yang salah. Hasil kasir 5 langsung dibetulkan tanpa menghitung ulang seluruh belanjaan. Itulah inti checksum SENTINEL."])
    d.figure(fig("fig_system"), "Arsitektur SENTINEL. Raspberry Pi mengirim gambar dan bobot lewat SPI. Semua memori dan kontrol ada di domain clk_safe "
                                "yang wajib lolos timing; hanya lane MAC di domain clk_fast yang boleh di-overclock. Data menyeberang lewat dua FIFO "
                                "asinkron (CDC). Diagram ini menggambarkan desain RTL, bukan board.")
    d.h2("1.1 Kenapa ide ini menarik")
    d.p("Vivado menghitung frekuensi maksimum secara konservatif: ia mengasumsikan chip paling lambat, suhu terburuk, dan tegangan terendah yang "
        "diizinkan. Chip sungguhan sering masih bekerja benar di atas angka itu. Overclocking memanfaatkan sisa margin tersebut, tetapi risikonya "
        "muncul error timing, yaitu hasil perkalian yang salah tanpa peringatan apa pun.")
    d.p("Overclocking akselerator CNN dengan checksum sudah pernah dilakukan, misalnya oleh Marty dkk. (FPT 2018), yang mendeteksi error lalu menghitung "
        "ulang bagian yang salah (Bab 9). SENTINEL mencoba melangkah lebih jauh: lokasi error dicari lalu langsung dikoreksi, dan pemilihan clock per "
        "layer dilakukan seluruhnya di dalam FPGA. Klaim seperti ini baru boleh ditulis di laporan kalau datanya sudah diukur di board "
        "(`docs/PRIOR_ART.md`).")
    d.h2("1.2 Lomba dan kategori")
    d.bullets(["Tema lomba adalah implementasi hardware CNN dengan jumlah layer bebas. Syaratnya data validasi dari panitia dan input kamera real-time. "
               "Gambar validasi diberikan pada hari lomba, dan presentasi harus menunjukkan seberapa cepat hasil pengenalan keluar [OFFICIAL].",
               "CNN menerima input 32\u00d732. Dataset latih bebas, tetapi kelas target ditentukan panitia dan belum diumumkan [OFFICIAL].",
               "Sejak 2 November 2026 tugas dibagi dua kelas. Class 1 terbatas pada klasifikasi gambar. Class 2 hanya boleh memakai board ZERO7, "
               "tugasnya bebas, dan hanya punya Level 3 [OFFICIAL]. Target SENTINEL adalah Class 2 Level 3; ini masih usulan yang menunggu "
               "konfirmasi panitia [PROPOSAL].",
               "Sejak 10 November 2026 semua kelas wajib menyerahkan laporan sintesis untuk chip AMD Spartan-7 XC7S25CSGA225-1, yaitu chip di ZERO7 [OFFICIAL].",
               "Board pinjaman dipasang di Raspberry Pi 5 [OFFICIAL].",
               "Batas laporan 31 Januari 2027. Presentasi 5 Maret 2027: 10 menit dengan maksimal 10 slide, lalu 5 menit tanya jawab [OFFICIAL]."])
    d.figure(fig("fig_roadmap"), "Posisi proyek per 16 November 2026. Atas: milestone pra-board M0\u2013M14 sudah selesai di simulasi (M10 sebagian), "
                                 "fase board B1\u2013B6 belum mulai; milestone M15 sampai M19 ditambahkan sesudah fakta resmi terbit (Bagian 7.6). "
                                 "Bawah: gerbang internal dari `STATUS.md` dan tanggal resmi panitia.")


# ============================================================================ chapter 2


def ch2(d: Doc, ctx) -> None:
    f = ctx["facts"]
    arch = ctx["arch"]
    img = f["image"]
    d.h1("2", "Dasar CNN")
    d.p("**Tujuan bab ini:** memahami apa yang dihitung CNN, dari piksel sampai kelas, dan berapa banyak perhitungannya. Contohnya memakai model `s` milik SENTINEL.")
    d.h2("2.1 Gambar adalah tabel angka")
    d.p("Komputer melihat gambar sebagai tabel angka. Setiap piksel punya tiga nilai, yaitu merah (R), hijau (G), dan biru (B), masing-masing 8 bit "
        "dengan rentang 0 sampai 255. Gambar berwarna 32×32 disimpan sebagai tensor 3×32×32 dengan urutan (kanal, baris, kolom). Totalnya "
        "3 · 32 · 32 = 3.072 byte, persis ukuran wilayah memori IMG0 di SENTINEL (`docs/SPEC.md` §12.3).")
    d.figure(fig("fig_tensor"), f"Gambar uji CIFAR-10 nomor {img['index']} ({img['label_id']}) sebagai tensor 3×32×32 [SIM]. Kotak hitam di kanal R "
                                "menandai 5×5 piksel yang nilainya ditampilkan di kanan. Data dibaca lewat `model/data.py`.")
    d.h2("2.2 Neuron: bobot, bias, dan aktivasi")
    d.p("Satuan dasar jaringan saraf adalah neuron. Neuron mengalikan setiap input x_{i} dengan bobot w_{i}, menjumlahkan semuanya, menambah bias b, "
        "lalu melewatkan hasilnya ke fungsi aktivasi f:")
    d.eq(mi("y=") + mi("f") + delim(nary(mi("i=1"), mi("n"), sub(mi("w"), mi("i")) + sub(mi("x"), mi("i"))) + mi("+b")))
    d.p("Bobot menentukan seberapa penting setiap input. Bias menggeser ambang. Fungsi aktivasi membuat jaringan tidak linear, sehingga bisa "
        "mempelajari pola yang rumit. Dua fungsi yang paling dikenal:")
    d.eq(func("ReLU", delim(mi("v"))) + mi("=") + func("max", delim(mi("0, v"))) + gap() + mi("σ") + delim(mi("v")) + mi("=") +
         frac(mi("1"), mi("1+") + sup(mi("e"), mi("−v"))))
    d.figure(fig("fig_activation"), "ReLU dan sigmoid [SIM] ilustrasi. ReLU jauh lebih murah di hardware karena cukup membuang nilai negatif. "
                                    "SENTINEL memakai ReLU, dan Bab 3 menunjukkan bahwa ReLU bahkan muncul gratis dari operasi clamp.", width_cm=11.5)
    d.callout("rumus", ["Satu operasi **MAC** (~multiply-accumulate~) adalah satu perkalian ditambah satu penjumlahan ke akumulator: acc ← acc + w·x. "
                        "Seluruh CNN pada dasarnya adalah jutaan MAC, sehingga akselerator CNN pada dasarnya adalah mesin MAC."])
    d.h2("2.3 Konvolusi: satu filter menyapu gambar")
    d.p("Neuron biasa terhubung ke semua input, dan untuk gambar itu boros. Lapisan konvolusi memakai filter kecil, misalnya 3×3, yang digeser ke "
        "seluruh gambar. Di setiap posisi, filter dikalikan elemen demi elemen dengan potongan gambar di bawahnya, lalu hasilnya dijumlahkan:")
    d.eq(mi("Y") + delim(mi("y,x"), "[", "]") + mi("=") + nary(mi("i=0"), mi("2"), nary(mi("j=0"), mi("2"),
         mi("W") + delim(mi("i,j"), "[", "]") + mi("·X") + delim(mi("y+i, x+j"), "[", "]"))))
    d.p("Filter yang sama dipakai di semua posisi (~weight sharing~), sehingga jumlah bobotnya kecil tetapi tetap bisa mendeteksi pola yang sama di "
        "mana pun, misalnya tepi tegak atau sudut. Library CNN, termasuk PyTorch, sebenarnya menghitung ~cross-correlation~ (filter tidak dibalik), "
        "dan SENTINEL mengikuti itu (`docs/SPEC.md` §3.2).")
    d.figure(fig("fig_conv"), "Konvolusi tanpa padding [SIM] ilustrasi: input 5×5, filter Sobel 3×3 yang peka terhadap tepi tegak, output 3×3. "
                              "Kotak biru adalah jendela yang menghasilkan sel kuning; perhitungannya ditulis di bawah.")
    d.h2("2.4 Padding, stride, dan ukuran output")
    d.p("Tanpa tambahan apa pun, output selalu lebih kecil dari input. ~Padding~ menambahkan bingkai nol di tepi gambar, sedangkan ~stride~ adalah "
        "besar langkah filter. Untuk input I, filter K, padding P, dan stride S, ukuran output adalah:")
    d.eq(mi("O=") + delim(frac(mi("I+2P−K"), mi("S")), "⌊", "⌋") + mi("+1"))
    cases = [(5, 3, 0, 1, "contoh Gambar 2.3"), (32, 3, 0, 1, "tanpa padding: gambar mengecil"),
             (32, 3, 1, 1, "padding \"same\": ukuran tetap, dipakai SENTINEL"), (32, 3, 1, 2, "stride 2: ukuran jadi setengah")]
    d.table(["I", "K", "P", "S", "O", "Keterangan"],
            [[str(i), str(k), str(p), str(s), str((i + 2 * p - k) // s + 1), t] for i, k, p, s, t in cases],
            [700, 700, 700, 700, 700, TEXT_W - 3500], caption="Contoh ukuran output konvolusi [SIM] ilustrasi.",
            align=["center"] * 5 + ["left"])
    d.h2("2.5 Banyak kanal input dan output")
    d.p("Gambar berwarna punya 3 kanal, dan keluaran lapisan konvolusi bisa punya puluhan kanal. Setiap kanal output o punya filternya sendiri "
        "berukuran C_{in}×3×3, dan hasil dari semua kanal input dijumlahkan. Ini rumus normatif SENTINEL dengan padding nol dan stride 1 "
        "(`docs/SPEC.md` §3.2):")
    d.eq(mt("acc") + delim(mi("o,y,x"), "[", "]") + mi("=") + nary(mi("c=0"), sub(mi("C"), mt("in")) + mi("−1"),
         nary(mi("i=0"), mi("2"), nary(mi("j=0"), mi("2"), mi("w") + delim(mi("o,c,i,j"), "[", "]") + mi("·a") +
                                             delim(mi("c, y+i−1, x+j−1"), "[", "]")))))
    c2 = arch["layers"][1]
    d.p(f"Jumlah bobot satu lapisan adalah C_{{out}} · C_{{in}} · 9. Untuk conv2 model `s`: {c2['output_channels']} · {c2['input'][0]} · 9 = "
        f"{nf(c2['weights'])} bobot [SIM] (`results/model/arch_s.json`).")
    d.callout("sentinel", ["Setiap **lane** MAC menghitung satu kanal output o. Dengan K = 8 lane, delapan kanal output dihitung bersamaan untuk posisi "
                           "(y, x) yang sama, dan semua lane menerima aktivasi a yang sama (di-~broadcast~). Karena inputnya sama, jumlah hasil semua "
                           "lane bisa dicek dengan satu lane tambahan. Inilah yang membuat checksum mungkin (ADR-001)."])
    d.h2("2.6 Pooling")
    d.p("Max pooling 2×2 dengan stride 2 mengambil nilai terbesar dari setiap blok 2×2. Ukuran peta fitur menjadi seperempatnya, jumlah "
        "perhitungan di lapisan berikutnya turun, dan jaringan menjadi sedikit lebih toleran terhadap pergeseran posisi.")
    d.eq(mi("P") + delim(mi("c,y,x"), "[", "]") + mi("=") + func("max", mi("Y") + delim(mi("c, 2y+i, 2x+j"), "[", "]"), lim=mi("0≤i,j≤1")))
    d.figure(fig("fig_pool"), "Max pooling 2×2 [SIM] ilustrasi. Setiap warna adalah satu blok; angka tebal adalah nilai maksimum yang diteruskan.", width_cm=12.0)
    d.h2("2.7 Fully connected, softmax, dan argmax")
    d.p("Setelah beberapa lapisan konvolusi dan pooling, peta fitur diratakan (~flatten~) menjadi vektor, lalu lapisan ~fully connected~ (FC) "
        "menghitung satu skor, disebut ~logit~, untuk setiap kelas:")
    d.eq(sub(mi("z"), mi("o")) + mi("=") + nary(mi("i"), "", sub(mi("w"), mi("o,i")) + sub(mi("a"), mi("i"))) + mi("+") + sub(mi("b"), mi("o")))
    d.p("Saat training, logit diubah menjadi probabilitas dengan softmax. Untuk menentukan kelas cukup argmax, karena softmax tidak mengubah urutan:")
    d.eq(sub(mi("p"), mi("o")) + mi("=") + frac(sup(mi("e"), sub(mi("z"), mi("o"))), nary(mi("j"), "", sup(mi("e"), sub(mi("z"), mi("j"))))) +
         gap() + mt("kelas") + mi("=") + func("argmax", sub(mi("z"), mi("o")), lim=mi("o")))
    d.callout("sentinel", ["Hardware tidak menghitung softmax. Logit int32 dibandingkan langsung, dan kalau ada nilai yang sama, kelas dengan indeks "
                           "terkecil yang dipilih (`docs/SPEC.md` §3.5). Aturan seri seperti ini harus ditulis eksplisit supaya golden model dan RTL "
                           "memberi jawaban yang sama."])
    d.h2("2.8 Arsitektur model s")
    d.p("SENTINEL punya dua varian model. Model `s` adalah default; model `xs` lebih kecil untuk FPGA yang memorinya sangat sedikit. Struktur model `s`:")
    d.figure(fig("fig_model_s"), "Model `s`: tiga blok konvolusi 3×3 + ReLU + maxpool, lalu FC ke 10 kelas. Ukuran kotak sebanding dengan jumlah kanal "
                                 "dan resolusi; lingkaran oranye tua menandai kelas pemenang pada contoh Gambar 2.7.")
    rows = []
    for lay in arch["layers"]:
        cin, h, w = lay["input"]
        if lay["kind"] == "conv":
            out = f"{lay['output_channels']}×{h // 2}×{w // 2}"
        else:
            out = f"{lay['output_channels']} logit"
        rows.append([f"`{lay['name']}`", f"{cin}×{h}×{w}", out, nf(lay["weights"]), nf(lay["bias"]), nf(lay["macs"]), nf(lay["t"])])
    rows.append(["**total**", "", "", f"**{nf(arch['total_weights'])}**", f"**{nf(arch['total_bias'])}**", f"**{nf(arch['total_macs'])}**", ""])
    d.table(["Layer", "Input", "Output", "Bobot", "Bias", "MAC", "T"], rows, [1100, 1500, 1500, 1350, 1000, 1700, TEXT_W - 8150],
            caption="Ukuran dan beban model `s` [SIM], dari `results/model/arch_s.json` (skrip `model/arch_report.py`). T adalah panjang akumulasi per output (Bab 5).",
            align=["left", "center", "center", "right", "right", "right", "right"])
    d.p("Jumlah MAC lapisan konvolusi dihitung dari ukuran output sebelum pooling:")
    d.eq(sub(mt("MAC"), mt("conv")) + mi("=") + sub(mi("H"), mt("out")) + mi("·") + sub(mi("W"), mt("out")) + mi("·") +
         sub(mi("C"), mt("out")) + mi("·") + sub(mi("C"), mt("in")) + mi("·9"))
    c1 = arch["layers"][0]
    share = 100 * c2["macs"] / arch["total_macs"]
    d.p(f"Contoh: conv1 = 32 · 32 · 16 · 3 · 9 = {nf(c1['macs'])} MAC. Total satu gambar {nf(arch['total_macs'])} MAC [SIM], dan conv2 "
        f"sendiri menyumbang {nf(share, 1)}% dari seluruh MAC.")
    d.figure(fig("fig_macs"), "MAC dan jumlah bobot per layer model `s` [SIM]. Beban hitung terbesar ada di conv2, sedangkan bobot terbanyak ada di conv3.")
    d.figure(fig("fig_featuremaps"), f"Apa yang \"dilihat\" model `s` untuk gambar uji nomor {img['index']} [SIM], dihitung oleh golden model integer. Baris atas "
                                     "dan tengah: 8 kanal dengan variasi terbesar dari conv1 dan conv2 (kecerahan dinormalisasi per kanal). Bawah: logit "
                                     f"int32; kelas terpilih {img['pred_id']}, sesuai label {img['label_id']}.")
    fl, qr = ctx["fl"]["s"], ctx["qr"]["s"]
    tr = f["training"]
    d.h2("2.9 Belajar dari data: training")
    d.p("Bobot tidak ditulis tangan, tetapi dipelajari dari contoh. Dataset dibagi tiga: data latih untuk mengubah bobot, data validasi untuk memilih "
        "model terbaik, dan data uji untuk mengukur akurasi akhir secara jujur. Untuk model `s`: "
        f"{nf(fl['train_size'])} / {nf(fl['val_size'])} / {nf(fl['test_size'])} gambar CIFAR-10 [SIM].")
    d.p("Kesalahan satu gambar diukur dengan ~cross-entropy~, yaitu minus logaritma probabilitas kelas yang benar y:")
    d.eq(mi("L=−") + func("log", sub(mi("p"), mi("y"))))
    d.p("~Backpropagation~ menghitung gradien g = ∂L/∂w untuk setiap bobot dengan aturan rantai; PyTorch melakukannya otomatis. Bobot lalu "
        "digeser sedikit melawan gradien. SENTINEL memakai SGD dengan momentum μ dan ~weight decay~ λ, dalam bentuk yang dipakai PyTorch:")
    d.eq(sub(mi("v"), mi("t+1")) + mi("=μ") + sub(mi("v"), mi("t")) + mi("+") + delim(sub(mi("g"), mi("t")) + mi("+λ") + sub(mi("w"), mi("t"))) +
         gap() + sub(mi("w"), mi("t+1")) + mi("=") + sub(mi("w"), mi("t")) + mi("−η") + sub(mi("v"), mi("t+1")))
    cfg = fl["train_cfg"]
    d.p(f"Pengaturan model `s` (`config/model_s.yaml`): η = {nf(cfg['lr'], 2)}; μ = {nf(cfg['momentum'], 1)}; λ = {nf(cfg['weight_decay'], 4)}; "
        f"batch {cfg['batch_size']}; {cfg['epochs']} epoch; dropout {nf(cfg['dropout'], 1)}; seed {cfg['seed']} [SIM]. Training di CPU memakan sekitar "
        f"{nf(fl['elapsed_s'] / 60, 0)} menit [SIM] (`results/model/s/float_result.json`).")
    d.figure(fig("fig_training"), f"Kurva training model `s` [SIM], dari `results/model/s/train_log.csv`. Akurasi validasi terbaik {nf(tr['best_val'], 2)}% di "
                                  f"epoch {tr['best_epoch']}; akurasi uji model float {pct(fl['test_acc_float'])} [SIM].")
    d.callout("catatan", ["CIFAR-10 hanya pengganti sementara, karena kelas target lomba belum diumumkan [UNKNOWN]. Training mendukung dataset folder "
                          "(format ImageFolder) dengan jumlah kelas bebas, dan bobot baru bisa dimuat lewat SPI tanpa sintesis ulang selama arsitektur "
                          "konvolusinya sama dan jumlah kelas paling banyak 16 (`docs/SPEC.md` §4)."])
    d.h2("2.10 Batch normalization dan folding")
    d.p("Batch normalization (BN) menormalkan keluaran lapisan saat training supaya belajar lebih stabil:")
    d.eq(acc(mi("y")) + mi("=γ") + frac(mi("y−") + sub(mi("μ"), mi("B")), rad(subsup(mi("σ"), mi("B"), mi("2")) + mi("+ε"))) + mi("+β"))
    d.p("Saat inferensi, nilai μ, σ², γ, dan β sudah tetap, sehingga BN bisa dilebur (~folding~) ke bobot dan bias konvolusi "
        "sebelumnya. Hardware tidak perlu blok BN sama sekali:")
    d.eq(mi("w′=") + frac(mi("γw"), rad(sup(mi("σ"), mi("2")) + mi("+ε"))) + gap() + mi("b′=") +
         frac(mi("γ") + delim(mi("b−μ")), rad(sup(mi("σ"), mi("2")) + mi("+ε"))) + mi("+β"))
    d.p(f"Di repo, folding dilakukan oleh `model/quant.py` (fungsi `fold_bn`). Akurasi sesudah folding sama dengan sebelum folding, "
        f"yaitu {pct(qr['test_acc_folded'])} [SIM] (`results/model/s/quant_result.json`).")
    d.callout("latihan", [("num", "1.\tBerapa ukuran output konvolusi 3×3, stride 1, tanpa padding, pada input 16×16?"),
                          ("num", "2.\tBerapa jumlah bobot conv3 model `s` (3×3, 32 kanal masuk, 32 kanal keluar)?"),
                          ("num", "3.\tMengapa hardware SENTINEL tidak perlu menghitung softmax?"),
                          ("num", "4.\tHitung MAC conv3 jika H_{out} = W_{out} = 8 dan C_{in} = C_{out} = 32.")])


# ============================================================================ chapter 3


def ch3(d: Doc, ctx) -> None:
    f = ctx["facts"]
    qr = ctx["qr"]
    d.h1("3", "Kuantisasi INT8 dan aritmetika integer")
    d.p("**Tujuan bab ini:** memahami bagaimana bobot dan aktivasi float diubah menjadi bilangan bulat 8 bit, bagaimana satu lapisan dihitung hanya "
        "dengan integer, dan apa arti bit-exact.")
    d.h2("3.1 Kenapa integer")
    d.bullets(["**Murah di FPGA.** Pengali 8×8 bit hanya butuh puluhan LUT atau sebagian kecil satu DSP. Pengali float32 jauh lebih besar dan lambat.",
               "**Hemat memori.** Bobot INT8 empat kali lebih kecil dari float32. Ini penting karena memori blok (BRAM) di Spartan-7 kecil sangat terbatas.",
               "**Deterministik.** Penjumlahan integer selalu memberi hasil yang sama apa pun urutannya, selama tidak overflow. Inilah yang memungkinkan "
               "perbandingan bit-exact antara Python dan RTL."])
    d.h2("3.2 Skala: menghubungkan integer dengan nilai real")
    d.p("Setiap tensor punya satu faktor skala S. Nilai real r didekati dengan integer q:")
    d.eq(mi("r≈S·q"))
    d.p("Di SENTINEL, aktivasi adalah uint8 (0..255) dan bobot adalah int8 (−127..127). Nilai −128 sengaja tidak dipakai supaya rentangnya simetris "
        "(`docs/SPEC.md` §3.1). Karena aktivasi selalu ≥ 0 sesudah ReLU dan bobot simetris, tidak perlu ~zero-point~.")
    d.figure(fig("fig_quant_stairs"), "Kuantisasi sebagai tangga [SIM] ilustrasi, memakai 3 bit supaya anak tangganya terlihat; INT8 punya 256 anak tangga. "
                                      "Galat pembulatan selalu di antara −S/2 dan +S/2 selama nilai tidak melewati batas.")
    q = qr["s"]
    d.p(f"Skala aktivasi dipilih dengan kalibrasi: {nf(q['calib_images'])} gambar latih dilewatkan ke model float, lalu S_{{out}} = persentil 99,99 "
        "aktivasi dibagi 255 (`docs/SPEC.md` §4). Memakai persentil, bukan nilai maksimum, mencegah satu nilai ekstrem membuat skala terlalu kasar. "
        "Metode ini disebut ~post-training quantization~ (PTQ).")
    d.h2("3.3 Requant: dari akumulator ke aktivasi berikutnya")
    d.p("Akumulator lapisan konvolusi bernilai real S_{in}·S_{w}·acc. Supaya menjadi aktivasi uint8 lapisan berikutnya dengan skala S_{out}, "
        "akumulator ditambah bias lalu dikalikan rasio S_{in}·S_{w}/S_{out}. Rasio ini pecahan kecil, jadi didekati dengan pengali integer M dan "
        "geser kanan n bit:")
    d.eq(frac(sub(mi("S"), mt("in")) + mi("·") + sub(mi("S"), mi("w")), sub(mi("S"), mt("out"))) + mi("≈") + frac(mi("M"), sup(mi("2"), mi("n"))))
    d.eq(mi("q=") + delim(mi("v·M+") + sup(mi("2"), mi("n−1"))) + mi("≫ n"))
    d.eq(mi("y=") + func("min", delim(func("max", delim(mi("q, 0"))) + mi(", 255"))))
    d.p("Tanda ≫ berarti geser kanan aritmetika (`>>` di kode). Penjumlahan 2^{n−1} sebelum geser adalah pembulatan ke nilai terdekat. Clamp ke "
        "0..255 sekaligus bekerja sebagai ReLU, karena nilai negatif menjadi 0. Nilai n dipilih sebesar mungkin sehingga M tetap muat di 16 bit "
        "(paling besar 65.535).")
    rows = []
    for lay in q["layers"]:
        if "m" in lay:
            rows.append([f"`{lay['layer']}`", nf(lay["s_in"], 5), nf(lay["s_w"], 5), nf(lay["s_out"], 5), nf(lay["ratio"], 6), nf(lay["m"]), str(lay["n"]),
                         nf(lay["m"] / 2 ** lay["n"], 6)])
        else:
            rows.append([f"`{lay['layer']}`", nf(lay["s_in"], 5), nf(lay["s_w"], 5), "—", "—", "—", "—", "tanpa requant (logit int32)"])
    d.table(["Layer", "S_in", "S_w", "S_out", "rasio", "M", "n", "M / 2^n"], rows, [900, 1100, 1100, 1100, 1250, 1000, 600, TEXT_W - 7050],
            caption="Parameter requant per layer model `s` [SIM], dari `results/model/s/quant_result.json`.",
            align=["left"] + ["right"] * 7, size=17)
    ex = f["requant_example"]
    d.callout("rumus", [
        f"Dari golden model, gambar uji nomor {f['image']['index']}, conv1 kanal {ex['channel']}, posisi ({ex['pos'][0]}, {ex['pos'][1]}) [SIM]:",
        ("num", f"1.\tacc = {sn(ex['acc'])} dan bias = {sn(ex['bias'])}, sehingga v = acc + bias = {sn(ex['v'])}."),
        ("num", f"2.\tv · M = {sn(ex['v'])} · {nf(ex['m'])} = {sn(ex['prod'])}."),
        ("num", f"3.\tTambah 2^{{{ex['n'] - 1}}} = {nf(ex['half'])}, hasilnya {sn(ex['prod'] + ex['half'])}."),
        ("num", f"4.\tGeser kanan {ex['n']} bit (bagi {nf(2 ** ex['n'])}, buang sisa): q = {sn(ex['q'])}."),
        ("num", f"5.\tClamp ke 0..255: y = {ex['y']}. Nilai inilah yang ditulis ke memori aktivasi.")], title="CONTOH HITUNG NYATA")
    rc = f["requant_curve"]
    d.figure(fig("fig_requant"), f"Fungsi requant conv1 [SIM]. Di bawah nol keluarannya 0 (ReLU gratis), lalu naik linear, dan jenuh di 255 mulai "
                                 f"v = {nf(rc['v_sat'])}. Titik oranye adalah contoh hitung di atas.")
    d.h2("3.4 Golden model dan bit-exact")
    d.p("Golden model (`model/golden.py`) adalah implementasi Python dari aritmetika integer SPEC §3, memakai NumPy int64. Ia berfungsi sebagai "
        "~oracle~: setiap testbench RTL membandingkan logit dan kelas dari hardware dengan golden model, dan satu bit yang berbeda saja sudah dihitung gagal.")
    acc_rows = []
    for m in ("s", "xs"):
        acc_rows.append([f"`{m}`", pct(ctx["fl"][m]["test_acc_float"]), pct(qr[m]["test_acc_folded"]), pct(qr[m]["test_acc_integer"]),
                         f"{nf(qr[m]['drop_points'], 2)} poin"])
    d.table(["Model", "Float", "Sesudah folding BN", "Integer (golden)", "Penurunan"], acc_rows, [1300, 1900, 2300, 2200, TEXT_W - 7700],
            caption="Akurasi uji CIFAR-10, 10.000 gambar [SIM].", align=["left", "right", "right", "right", "right"])
    d.figure(fig("fig_accuracy"), "Akurasi float dan integer [SIM]. Penurunan akibat kuantisasi jauh di bawah batas 2 poin yang akan memicu QAT "
                                  "(`docs/SPEC.md` §4), sehingga QAT tidak diperlukan.")
    n200 = ctx["reg"].get("engine_s_k8_n200", {}).get("summary", "")
    d.callout("sentinel", ["Akurasi yang dilaporkan untuk hardware adalah akurasi golden model integer. Kalau RTL bit-exact dengan golden model, akurasi "
                           f"hardware otomatis sama. Di simulasi, RTL engine model `s` K = 8 sudah bit-exact: `{n200}` [SIM] (Bab 7)."])
    d.h2("3.5 Batas bit: memastikan tidak ada overflow")
    d.p("Akumulator lane data selebar ACC_W = 32 bit, sedangkan lane checksum serta selisih d1, d2, d3 selebar ACC_CS_W = 48 bit. Skrip ekspor "
        "menghitung batas terburuk setiap layer dan memastikannya dengan assert (`docs/SPEC.md` §3.6). Perhitungan kasarnya:")
    d.bullets([f"Lane data, conv3 (T = 288): |acc| ≤ 288 · 255 · 127 = {nf(288 * 255 * 127)}, jauh di bawah 2^{{31}} − 1 = {nf(2 ** 31 - 1)} [SIM] ilustrasi.",
               f"Lane checksum C2 dengan K = 8: |wc2| ≤ 4.572 (`docs/SPEC.md` §6.1), sehingga untuk FC (T = 512) |S2| ≤ 512 · 255 · 4.572 = "
               f"{nf(512 * 255 * 4572)}, jauh di bawah 2^{{47}} [SIM] ilustrasi."])
    d.callout("latihan", [("num", "1.\tRasio requant sebuah layer adalah 0,01. Dengan aturan SENTINEL (n sebesar mungkin sehingga M ≤ 65.535), berapa n dan M?"),
                          ("num", "2.\tBerapa y untuk v = −500?"),
                          ("num", "3.\tMengapa bobot −128 tidak dipakai?")])


# ============================================================================ chapter 4


def ch4(d: Doc, ctx) -> None:
    d.h1("4", "Dasar FPGA, timing, dan Vivado")
    d.p("**Tujuan bab ini:** memahami isi FPGA, arti jalur kritis dan slack, alasan overclocking memunculkan error, dan apa yang bisa serta tidak bisa "
        "dijawab oleh simulasi dan analisis Vivado.")
    d.h2("4.1 Isi sebuah FPGA")
    d.p("FPGA adalah chip yang rangkaiannya bisa diprogram ulang. Di dalamnya ada ribuan blok kecil yang disambung lewat jaringan routing yang juga "
        "bisa diprogram:")
    d.figure(fig("fig_fpga_fabric"), "Skema sederhana fabric FPGA keluarga 7-series. Jumlah dan letak blok sebenarnya bergantung pada part; angka "
                                     "spesifik Spartan-7 harus dicek di DS180.")
    d.table(["Blok", "Fungsi", "Dipakai SENTINEL untuk"], [
        ["LUT (6 input)", "fungsi logika apa pun dari 6 input", "logika kontrol, pengali di lane `lut`"],
        ["Flip-flop", "menyimpan 1 bit, berubah di tepi clock", "register pipeline dan akumulator"],
        ["Carry chain", "penjumlah cepat", "akumulator 32 dan 48 bit"],
        ["BRAM36", "memori blok 36 Kb", "bobot, aktivasi, FIFO"],
        ["DSP48E1", "pengali 25×18 dengan akumulator 48 bit", "lane `dsp_min` dan `dsp_full`"],
        ["MMCM, BUFG, BUFGCTRL", "membangkitkan dan memilih clock", "clk_safe, clk_turbo, clk_fast"],
    ], [2300, 3700, TEXT_W - 6000], caption="Blok utama FPGA 7-series (UG474, UG473, UG479, UG472) dan pemakaiannya di SENTINEL.")
    part = ctx["part"]
    if part:
        d.p(f"Board ZERO7 memakai AMD Spartan-7 XC7S25CSGA225-1, speed grade \u22121 [OFFICIAL]. Menurut basis data Vivado, chip ini punya "
            f"{nf(int(part['LUT_ELEMENTS']))} LUT, {nf(int(part['FLIPFLOPS']))} flip-flop, {part['BLOCK_RAMS']} block RAM, {part['DSP']} DSP, dan "
            f"{part['MMCM']} MMCM (`results/vivado/part_check.txt`). Clock board 20 MHz masuk di pin B13, sebuah pin clock-capable "
            "[OFFICIAL] (`board/BOARD_INFO.md`).")
    else:
        d.p("Board ZERO7 memakai AMD Spartan-7 XC7S25CSGA225-1, speed grade \u22121 [OFFICIAL] (`board/BOARD_INFO.md`).")
    d.h2("4.2 Clock, jalur kritis, dan slack")
    d.p("Desain digital sinkron bekerja seperti lari estafet. Di setiap tepi clock, flip-flop pertama mengeluarkan data, data melewati logika "
        "kombinasional, lalu harus sudah stabil di flip-flop berikutnya sebelum tepi clock berikutnya. Jadi periode clock harus lebih panjang dari "
        "waktu tempuh jalur:")
    t = lambda name: sub(mi("t"), mt(name))  # noqa: E731
    path_sum = t("cq") + mi("+") + t("logika") + mi("+") + t("route") + mi("+") + t("setup")
    d.eq(sub(mi("T"), mt("clk")) + mi("≥") + path_sum)
    d.p("Selisihnya disebut ~slack~. Slack positif berarti aman; slack negatif berarti jalur itu terlalu lambat untuk periode yang diminta. Jalur "
        "dengan slack terkecil disebut ~jalur kritis~, dan slack terburuk di seluruh desain disebut WNS (~worst negative slack~):")
    d.eq(mt("slack") + mi("=") + sub(mi("T"), mt("clk")) + mi("−") + delim(path_sum))
    d.p("Dari WNS, frekuensi maksimum diperkirakan dengan rumus yang juga dipakai skrip repo (`tools/gen_results_doc.py`):")
    d.eq(sub(mi("f"), mt("max")) + mi("=") + frac(mi("1"), sub(mi("T"), mt("target")) + mi("−") + mt("WNS")))
    r = viv(ctx, "xc7s25csga225-1", 8, 0, 0)
    d.p(f"Contoh dari laporan Vivado [VIVADO-STA]: lane `lut`, K = 8, XC7S25 −1, target clk_fast {nf(float(r['t_fast_ns']), 1)} ns. WNS clk_fast "
        f"{nf(float(r['wns_fast_ns']), 3)} ns, sehingga f_{{max}} = 1 / ({nf(float(r['t_fast_ns']), 1)} − {nf(float(r['wns_fast_ns']), 3)}) ns "
        f"≈ {nf(float(r['fmax_fast_mhz']), 1)} MHz.")
    d.figure(fig("fig_timing"), "Atas: satu jalur antara dua flip-flop. Bawah: di clock aman, data tiba sebelum jendela setup (slack positif). Di clock turbo "
                                "periodenya lebih pendek, data tiba di dalam jendela setup, dan FF2 menangkap nilai yang salah. Diagram konsep tanpa angka.")
    d.h2("4.3 Apa yang terjadi saat clock dinaikkan melewati batas")
    d.p("Kalau periode clock lebih pendek dari waktu tempuh jalur, flip-flop menangkap nilai lama atau nilai yang sedang berubah. Hasilnya error timing: "
        "beberapa bit salah, tanpa peringatan apa pun. Ada tiga sifat penting:")
    d.bullets(["**Bergantung data.** Waktu tempuh penjumlah bergantung pada seberapa jauh carry merambat. Input tertentu memicu jalur panjang, input lain tidak.",
               "**Bit atas cenderung salah lebih dulu**, karena carry ke bit tinggi melewati jalur terpanjang. Chamberlin dkk. (2024) mengamati ini pada "
               "array MAC 2×2 di FPGA. Itu hasil hardware milik mereka, bukan pengukuran SENTINEL.",
               "**Bergantung suhu, tegangan, dan chip.** Chip yang lebih panas lebih lambat, dan dua chip dengan part yang sama bisa berbeda. Karena itu "
               "dibutuhkan governor yang bereaksi terhadap error. SENTINEL tidak pernah mengubah tegangan."])
    d.p("Analisis timing Vivado (STA) menghitung kasus terburuk, jadi frekuensi gagal yang nyata biasanya lebih tinggi dari Fmax STA. Chamberlin dkk. "
        "melaporkan error baru muncul di sekitar 315 MHz, padahal estimasi STA mereka sekitar 168 MHz (hasil hardware mereka, `docs/PRIOR_ART.md`). "
        "Seberapa besar margin itu untuk SENTINEL di ZERO7 hanya bisa diukur di board.")
    d.callout("board", ["Di frekuensi berapa lane SENTINEL mulai error? Apakah error pertama hanya mengenai satu lane? Apakah polanya berulang? Simulasi "
                        "tidak bisa menjawab satu pun, karena simulasi RTL tidak memodelkan waktu tempuh fisik. Ini adalah eksperimen E1–E3 di Bab 8."])
    d.h2("4.4 Alur Vivado")
    d.p("Vivado mengubah kode RTL menjadi file konfigurasi FPGA (~bitstream~) lewat beberapa tahap:")
    d.numbered(["**Sintesis** (`synth_design`): RTL diubah menjadi netlist berisi LUT, flip-flop, DSP, dan BRAM.",
                "**Optimasi, place, dan route**: setiap elemen ditempatkan di lokasi fisik chip, lalu kabelnya disambung.",
                "**STA** (~static timing analysis~): waktu tempuh semua jalur dihitung dari model delay chip, tanpa simulasi, lalu dibandingkan dengan constraint clock.",
                "**Bitstream** (`write_bitstream`): file yang dimuat ke FPGA. Tahap ini butuh pin board yang benar (file XDC)."])
    d.figure(fig("fig_vivado_flow"), "Alur OOC yang sudah dijalankan untuk SENTINEL, dan alur board yang menunggu fakta board (pin, clock input, cara programming).")
    d.p("Karena board belum ada, SENTINEL memakai alur ~out-of-context~ (OOC): modul `engine` disintesis dan di-route sendiri tanpa pin board. Hasilnya "
        "estimasi resource dan timing [VIVADO-STA] untuk beberapa part kandidat. Skripnya `fpga/ooc.tcl` dan `fpga/run_matrix.py`.")
    d.callout("sentinel", ["clk_safe dan clk_fast dinyatakan sebagai grup clock asinkron. Untuk membuktikan bahwa jalur MAC benar-benar menjadi jalur "
                           "kritis di domain cepat (SPEC §7.4), semua jalur non-MAC di clk_fast diberi batas `set_max_delay` 0,7 × periode, "
                           "sehingga harus punya margin minimal 30% (ADR-012)."])
    d.h2("4.5 Dua domain clock dan CDC")
    d.p("Sinyal yang menyeberang antara dua clock yang tidak berhubungan bisa tertangkap tepat saat berubah, sehingga flip-flop masuk keadaan "
        "~metastabil~ sesaat. Ini disebut masalah CDC (~clock domain crossing~). Ada dua solusi baku:")
    d.bullets(["**Sinkronizer 2-FF** untuk sinyal satu bit: dua flip-flop berurutan memberi waktu bagi keadaan metastabil untuk hilang.",
               "**FIFO asinkron** untuk aliran data: penulis dan pembaca punya clock sendiri. Pointer baca dan tulis dikirim ke sisi lain dalam "
               "~Gray code~, sehingga setiap kenaikan hanya mengubah satu bit dan tidak ada nilai antara yang salah."])
    d.eq(mi("g=b⊕") + delim(mi("b≫1")))
    d.table(["Desimal", "Biner", "Gray"], [[str(i), format(i, "03b"), format(i ^ (i >> 1), "03b")] for i in range(8)],
            [2000, 2000, 2000], caption="Biner dan Gray code 3 bit: setiap langkah Gray hanya mengubah satu bit [SIM] ilustrasi.",
            align=["center", "center", "center"])
    d.callout("sentinel", ["Wrapper `rtl/cdc_fifo.v` punya dua implementasi: `xpm_fifo_async` dari Xilinx untuk Vivado, dan model Gray-code untuk simulasi "
                           "portabel. Ada dua FIFO, yaitu FIFO operand (clk_safe → clk_fast) dan FIFO hasil (clk_fast → clk_safe). FIFO yang lebar "
                           "dipecah menjadi beberapa irisan paralel supaya fanout pointer kecil (ADR-012)."])
    d.h2("4.6 Simulasi, STA, model sintetis, dan board")
    d.p("Ini tabel paling penting di materi ini. Setiap cara menjawab pertanyaan yang berbeda, dan tidak ada yang bisa menggantikan board.")
    d.table(["Cara", "Menjawab", "Tidak bisa menjawab", "Label"], [
        ["Simulasi RTL (Icarus, xsim)", "apakah logika benar dan bit-exact; protokol SPI dan perpindahan clock", "kapan error timing muncul; perilaku fisik", "[SIM]"],
        ["Analisis statis Vivado", "resource; Fmax terburuk; jalur kritis", "frekuensi gagal sesungguhnya; daya nyata", "[VIVADO-STA]"],
        ["Model error sintetis", "apakah skrip eksperimen dan grafik bekerja", "apa pun tentang chip nyata, karena ini asumsi kita sendiri", "[SYNTHETIC]"],
        ["Board ZERO7", "semua pertanyaan yang tersisa", "—", "[HW]"],
    ], [2200, 3100, 2900, TEXT_W - 8200], caption="Empat sumber bukti dan batasnya.")
    d.callout("latihan", [("num", "1.\tTarget periode 5 ns dan WNS −0,5 ns. Berapa f_{max}?"),
                          ("num", "2.\tMengapa pointer FIFO asinkron dikirim dalam Gray code, bukan biner?"),
                          ("num", "3.\tSebutkan tiga hal fisik yang mengubah waktu tempuh jalur.")])


# ============================================================================ chapter 5


def ch5(d: Doc, ctx) -> None:
    f = ctx["facts"]
    arch = ctx["arch"]
    d.h1("5", "Arsitektur SENTINEL")
    d.p("**Tujuan bab ini:** memahami bagaimana CNN dipetakan ke lane, bagaimana checksum mendeteksi dan mengoreksi error, serta bagaimana clock, "
        "governor, injeksi fault, dan antarmuka host bekerja.")
    d.h2("5.1 Peta modul")
    d.p("Gambar 1.1 sudah menunjukkan blok-blok utamanya. Tabel berikut memetakan blok ke file RTL (`docs/ARCHITECTURE.md`):")
    d.table(["Modul", "Domain", "Peran"], [
        ["`rtl/operand_gen.v`", "safe", "menjalankan loop SPEC §5.3, membaca aktivasi dan bobot, menangani padding"],
        ["`rtl/wc_gen.v`, `rtl/sum_tree.v`", "safe", "bobot checksum dihitung on-the-fly (ADR-002)"],
        ["`rtl/cdc_fifo.v`", "keduanya", "FIFO asinkron FWFT; XPM di Vivado, model Gray-code di simulasi"],
        ["`rtl/fast_path.v`", "fast", "slot serializer, counter STARVE, lane array"],
        ["`rtl/lane_array.v`, `rtl/lane_*.v`", "fast", "lane MAC, register holding, serializer, injeksi"],
        ["`rtl/lane_checker.v`", "safe", "d1, d2, d3, pencarian j, koreksi"],
        ["`rtl/postproc.v`, `rtl/pool.v`", "safe", "requant dan max pooling"],
        ["`rtl/engine.v`", "safe", "tabel layer, pass, log recompute, counter"],
        ["`rtl/spi_slave.v`, `rtl/regfile.v`", "safe", "antarmuka host; register map dari `spec/regmap.yaml`"],
        ["`rtl/governor.v`, `rtl/clk_seq.v`", "safe", "kebijakan governor dan urutan rekonfigurasi MMCM2"],
        ["`rtl/top_core.v`, `board/top_board.v`", "keduanya", "integrasi tanpa dan dengan pin board"],
    ], [3500, 1100, TEXT_W - 4600], caption="Modul RTL utama.", size=17)
    d.h2("5.2 Dataflow output-stationary")
    d.p("Setiap siklus clk_fast, semua lane menerima satu ~operand set~: satu aktivasi a yang sama untuk semua lane, K bobot w_{1}..w_{K} (satu per lane), "
        "serta bobot checksum wc1, wc2, dan wc3 bila C3 aktif. Setiap lane mengakumulasi hasil kali selama T siklus, lalu hasilnya keluar. Akumulator "
        "tetap di tempat sampai satu output selesai, sehingga disebut ~output-stationary~ (ADR-001). Panjang akumulasinya:")
    d.eq(sub(mi("T"), mt("conv")) + mi("=") + sub(mi("C"), mt("in")) + mi("·9") + gap() + sub(mi("T"), mt("fc")) + mi("=") + sub(mi("N"), mt("in")))
    d.figure(fig("fig_dataflow"), "Satu unit hitung. Aktivasi a(t) disiarkan ke semua lane; setiap lane mengalikan dengan bobotnya sendiri lalu mengakumulasi. "
                                  "Dua lane checksum memakai bobot wc1 dan wc2 yang dihitung dari bobot lane data. Hasilnya dibandingkan di lane_checker.")
    d.p("Satu ~unit hitung~ adalah satu posisi output untuk satu grup K kanal. Empat unit yang membentuk satu jendela pool 2×2 disebut ~unit recompute~: "
        "kalau ada yang gagal, keempatnya dihitung ulang bersama supaya pooling-nya benar (ADR-003). Urutan loop untuk satu layer konvolusi "
        "(`docs/SPEC.md` §5.3):")
    d.code(["for g in groups:",
            "  for window in pool_windows (raster):",
            "    for (dy,dx) in [(0,0),(0,1),(1,0),(1,1)]:",
            "      for c, i, j:  (Cin x 3 x 3)"])
    d.p("Dari urutan ini, jumlah siklus ideal satu gambar adalah sebagai berikut, dengan G jumlah grup dan H_{out}·W_{out} dihitung sebelum pooling:")
    d.eq(sub(mt("siklus"), mt("ideal")) + mi("=") + nary(mt("conv"), "", sub(mi("H"), mt("out")) + mi("·") + sub(mi("W"), mt("out")) + mi("·G·") +
         sub(mi("C"), mt("in")) + mi("·9")) + mi("+") + nary(mt("fc"), "", mi("G·") + sub(mi("N"), mt("in"))) + gap() + mi("G=") +
         delim(frac(sub(mi("C"), mt("out")), mi("K")), "⌈", "⌉"))
    rows = [[f"`{l['name']}`", nf(l["t"]), str(l["groups"]["8"]), nf(l["ideal_cycles"]["8"]), str(l["groups"]["16"]), nf(l["ideal_cycles"]["16"])] for l in arch["layers"]]
    rows.append(["**total**", "", "", f"**{nf(arch['ideal_cycles']['8'])}**", "", f"**{nf(arch['ideal_cycles']['16'])}**"])
    d.table(["Layer", "T", "Grup K = 8", "Siklus ideal K = 8", "Grup K = 16", "Siklus ideal K = 16"], rows, [1300, 1000, 1500, 2100, 1600, TEXT_W - 7500],
            caption="Siklus ideal model `s` per layer [SIM], dari `results/model/arch_s.json`.", align=["left"] + ["right"] * 5)
    c8, i8 = cycles_from(ctx["reg"]["engine_s_k8_n200"]["summary"])
    c16, i16 = cycles_from(ctx["reg"]["engine_s_k16_n20"]["summary"])
    d.p(f"Simulasi RTL engine mengukur {nf(c8)} siklus per gambar untuk K = 8, hanya {nf(100 * (c8 - i8) / i8, 2)}% di atas ideal {nf(i8)}. Untuk K = 16 "
        f"hasilnya {nf(c16)} siklus, {nf(100 * (c16 - i16) / i16, 1)}% di atas ideal {nf(i16)} [SIM] (`results/sim/rtl_regression.jsonl`). Sebagai "
        f"contoh hitung saja: {nf(i8)} siklus di 100 MHz sama dengan sekitar {nf(i8 / 100e6 * 1e3, 2)} ms (`docs/SPEC.md` §5.4). Itu aritmetika, "
        "bukan kecepatan terukur, karena kecepatan nyata bergantung pada clock board yang belum diketahui.")
    d.p("Lane hanya bisa lebih cepat kalau operandnya juga datang lebih cepat. Domain aman menghasilkan R = 2 operand set per siklus clk_safe, sehingga "
        "syaratnya (ADR-004):")
    d.eq(mi("R·") + sub(mi("f"), mt("safe")) + mi("≥") + sub(mi("f"), mt("turbo,max")))
    d.p("Siklus ketika lane menunggu operand dihitung oleh counter `STARVE_CYCLES`.")
    # --- checksum maths
    d.h2("5.3 Matematika checksum")
    d.p("Kuncinya adalah sifat linear konvolusi: jumlah hasil beberapa filter sama dengan hasil satu filter yang bobotnya dijumlahkan. Karena semua lane "
        "memakai input yang sama, bobot checksum dibuat dari bobot lane data, dihitung di domain aman (ADR-002):")
    k1 = mi("k=1")
    d.eq(sub(mi("wc"), mi("1")) + mi("=") + nary(k1, mi("K"), sub(mi("w"), mi("k"))) + gap() + sub(mi("wc"), mi("2")) + mi("=") +
         nary(k1, mi("K"), mi("k·") + sub(mi("w"), mi("k"))) + gap() + sub(mi("wc"), mi("3")) + mi("=") +
         nary(k1, mi("K"), sup(mi("k"), mi("2")) + mi("·") + sub(mi("w"), mi("k"))))
    d.p("Lane checksum c menghitung S_{c} = Σ_{t} wc_{c}(t)·a(t). Kalau tidak ada error, berlaku identitas yang eksak dalam aritmetika integer:")
    d.eq(sub(mi("S"), mi("1")) + mi("=") + nary(k1, mi("K"), sub(mi("Y"), mi("k"))) + gap() + sub(mi("S"), mi("2")) + mi("=") +
         nary(k1, mi("K"), mi("k·") + sub(mi("Y"), mi("k"))) + gap() + sub(mi("S"), mi("3")) + mi("=") +
         nary(k1, mi("K"), sup(mi("k"), mi("2")) + mi("·") + sub(mi("Y"), mi("k"))))
    d.p("Sekarang misalkan lane j mengalami error sebesar e, sehingga yang teramati adalah Y′_{j} = Y_{j} + e. Selisih antara hasil lane data dan "
        "lane checksum menjadi:")
    yk = subsup(mi("Y"), mi("k"), mi("′"))
    d.eq(sub(mi("d"), mi("1")) + mi("=") + nary(mi("k"), "", yk) + mi("−") + sub(mi("S"), mi("1")) + mi("=e") + gap() +
         sub(mi("d"), mi("2")) + mi("=") + nary(mi("k"), "", mi("k·") + yk) + mi("−") + sub(mi("S"), mi("2")) + mi("=j·e"))
    d.p("Artinya d1 memberi ~besar~ error, dan rasio d2/d1 memberi ~nomor lane~ yang salah. Koreksinya cukup satu pengurangan:")
    d.eq(mi("j=") + frac(sub(mi("d"), mi("2")), sub(mi("d"), mi("1"))) + gap() + sub(mi("Y"), mi("j")) + mi("←") +
         subsup(mi("Y"), mi("j"), mi("′")) + mi("−") + sub(mi("d"), mi("1")))
    d.p("Nomor lane sengaja dimulai dari 1, bukan 0. Kalau lane pertama berbobot 0, error di lane itu tidak terlihat di d2, sehingga tidak bisa dibedakan "
        "dari error di lane checksum C1 (`docs/SPEC.md` §6.2).")
    ce = f["checksum_example"]
    s = ce["single"]
    lane = s["lane"]
    d.h3("Contoh nyata: satu lane error [SIM]")
    d.p(f"Akumulator ini diambil dari golden model: conv2, grup 0, posisi ({ce['pos'][0]}, {ce['pos'][1]}), gambar uji nomor {f['image']['index']}, K = 8. "
        f"Lalu bit {s['bit']} di lane {lane} dibalik dengan XOR, seperti injeksi fault di hardware [SIM].")
    rows = []
    for k in range(1, 9):
        y, o = ce["y"][k - 1], s["observed"][k - 1]
        cells = [str(k), sn(y), sn(o), sn(k * o)]
        rows.append([f"**{c}**" for c in cells] if k == lane else cells)
    sum_o = sum(s["observed"])
    sum_ko = sum(k * v for k, v in enumerate(s["observed"], start=1))
    rows.append(["Σ", sn(sum(ce["y"])), sn(sum_o), sn(sum_ko)])
    d.table(["Lane k", "Y_k benar", "Y_k teramati", "k · Y_k teramati"], rows, [1500, 2600, 2600, TEXT_W - 6700],
            caption="Contoh deteksi dan koreksi satu lane [SIM], dihitung dengan `model/checker.py`. Baris tebal adalah lane yang dirusak.",
            align=["center", "right", "right", "right"])
    j = s["j"]
    d.p(f"Dari lane checksum (yang tidak rusak): S1 = {sn(ce['s1'])} dan S2 = {sn(ce['s2'])}. Jadi d1 = {sn(sum_o)} − ({sn(ce['s1'])}) = {sn(s['d1'])} "
        f"dan d2 = {sn(sum_ko)} − ({sn(ce['s2'])}) = {sn(s['d2'])}. Karena d2 = {j} · d1, lane yang salah adalah j = {j}, dan Y_{{{j}}} dikoreksi "
        f"menjadi {sn(s['observed'][j - 1])} − ({sn(s['d1'])}) = {sn(s['corrected'][j - 1])}, persis nilai benarnya. Hasil `check()`: "
        f"{s['outcome']}({j}) [SIM].")
    du = ce["dual"]
    e = du["d1"] // 2
    d.h3("Kenapa C3 diperlukan: dua lane error [SIM]")
    d.p(f"Sekarang bit {du['bit']} di lane {du['lanes'][0]} dan lane {du['lanes'][1]} dibalik bersamaan, dan keduanya kebetulan mendapat error yang sama, "
        f"e = {sn(e)}. Maka d1 = 2e = {sn(du['d1'])} dan d2 = ({du['lanes'][0]} + {du['lanes'][1]})·e = {sn(du['d2'])}. Rasio d2/d1 = "
        f"{du['d2'] // du['d1']}, sehingga tanpa C3 checker menyimpulkan lane {du['j_c3_off']} yang salah dan \"mengoreksi\" lane yang sebenarnya benar "
        f"(`check()` memberi {du['outcome_c3_off']}({du['j_c3_off']})) [SIM]. Inilah ~salah koreksi~: data rusak yang lolos tanpa tanda apa pun.")
    d.p("Dengan C3, checker juga memeriksa syarat berikut:")
    d.eq(sub(mi("d"), mi("3")) + mi("=") + nary(mi("k"), "", sup(mi("k"), mi("2")) + mi("·") + yk) + mi("−") + sub(mi("S"), mi("3")) + mi("=") +
         sup(mi("j"), mi("2")) + mi("·") + sub(mi("d"), mi("1")))
    jj = du["j_c3_off"]
    d.p(f"Di sini d3 = ({du['lanes'][0]}² + {du['lanes'][1]}²)·e = {sn(du['d3'])}, sedangkan j²·d1 = {jj * jj} · ({sn(du['d1'])}) = "
        f"{sn(jj * jj * du['d1'])}. Tidak cocok, sehingga hasilnya {du['outcome_c3_on']}: unit dihitung ulang di clock aman [SIM].")
    d.callout("jujur", [("bullet", "Checksum melindungi **perhitungan MAC**, bukan input. Error pada aktivasi a yang disiarkan ke semua lane setelah keluar dari "
                                   "domain aman tidak terdeteksi, karena semua lane dan lane checksum menerima nilai salah yang sama."),
                        ("bullet", "Error di **beberapa lane sekaligus** bisa lolos atau salah dikoreksi. Kampanye di Bab 7 mengukur seberapa sering untuk error "
                                   "buatan [SIM]; laju untuk error timing nyata belum diketahui."),
                        ("bullet", "Mitigasinya: jalur operand di domain cepat dibuat pendek dan diberi register tambahan, bit paritas operand (opsional, belum "
                                   "dibuat), dan perbandingan setiap hasil dengan golden model di setiap eksperimen (`docs/SPEC.md` §6.5).")])
    # --- comparator
    d.h2("5.4 Keputusan komparator")
    d.p("`rtl/lane_checker.v` menerapkan keputusan SPEC §6.2 secara identik dengan `model/checker.py`:")
    d.figure(fig("fig_decision"), "Alur keputusan untuk satu unit. MODE 2 adalah mode SENTINEL; MODE 0 dan 1 ada di bitstream yang sama untuk perbandingan "
                                  "yang adil di E4.")
    d.table(["Hasil", "Arti", "Tindak lanjut"], [
        ["CLEAN", "semua selisih nol", "hasil dipakai"],
        ["CORRECTED(j)", "tepat satu lane data salah dan cocok dengan pola j", "Y_j dikoreksi, counter CORRECTED naik"],
        ["CSUM_LANE(c)", "hanya lane checksum c yang salah (jika TRUST_CSUM_LANE = 1)", "hasil lane data dipakai"],
        ["RECOMPUTE", "pola lain", "unit recompute dicatat di log, lalu dihitung ulang di clock aman"],
    ], [1900, 4100, TEXT_W - 6000], caption="Empat hasil keputusan dan tindak lanjutnya.")
    d.p("Pencarian j dilakukan berurutan tanpa pembagi (SPEC §6.3). Triknya ada di urutan serialisasi hasil: S1, S2, (S3), lalu Y_{K} sampai Y_{1}. "
        "Checker menjumlahkan A ← A + Y dan B ← B + A. Setelah K langkah, Y_{k} sudah tertambah ke B sebanyak k kali, sehingga "
        "B = Σ k·Y_{k} tanpa satu pun pengali. Semua selisih dihitung modulo 2^{48} supaya RTL tetap bit-exact dengan model, bahkan untuk "
        "error ekstrem (ADR-008).")
    d.p("Secara default TRUST_CSUM_LANE = 0 (ADR-005). Tanpa C3, pola \"hanya d1 yang bukan nol\" bisa juga berasal dari error dua lane yang saling "
        "meniadakan. Contohnya, +2 di lane 1 dan −1 di lane 2 memberi d1 = 1 dan d2 = 0. Jadi kasus ambigu lebih aman dihitung ulang.")
    d.h2("5.5 Recompute, log, dan FATAL")
    d.numbered(["Selama layer berjalan di clock turbo, setiap unit recompute yang berstatus RECOMPUTE dicatat di log berkapasitas N_LOG = 256.",
                "Setelah layer selesai, clk_fast dipindah ke clock aman, semua unit di log dihitung ulang, lalu hasilnya ditulis ulang sesudah requant "
                "dan pooling. Layer berikutnya baru mulai setelah itu.",
                "Komparator tetap aktif saat recompute. Kalau hasil di clock aman pun tidak CLEAN, flag FATAL dinyalakan, karena itu tanda bug atau error "
                "yang bukan error timing.",
                "Kalau log penuh, seluruh layer diulang di clock aman dan counter LOG_OVF bertambah."])
    d.h2("5.6 Tiga mode operasi")
    d.table(["Nilai", "Nama", "Perilaku"], [
        ["0", "UNPROTECTED", "tanpa cek; hasil dipakai apa adanya"],
        ["1", "DETECT_C1_RECOMPUTE", "baseline ala Marty dkk.: d1 ≠ 0 berarti hitung ulang"],
        ["2", "CORRECT", "SENTINEL: deteksi, lokalisasi, koreksi (Bagian 5.3 dan 5.4)"],
    ], [900, 3000, TEXT_W - 3900], caption="Mode di register `CTRL.MODE` (`docs/SPEC.md` §8).", align=["center", "left", "left"])
    d.p("Ketiganya ada di bitstream yang sama, sehingga perbandingan throughput dan akurasi di E4 adil: chip, placement, dan routing sama persis.")
    d.h2("5.7 Pembangkit clock dan protokol perpindahan")
    d.p("`clk_gen` membangkitkan dua clock dari clock input board F_{IN} [UNKNOWN]. MMCM1 menghasilkan clk_safe, dan MMCM2 menghasilkan clk_turbo yang "
        "frekuensinya bisa diubah lewat ~dynamic reconfiguration~. Primitif BUFGCTRL memilih salah satunya tanpa glitch sebagai clk_fast. Protokol "
        "perpindahannya punya tiga aturan (`docs/SPEC.md` §7.7):")
    d.numbered(["`sel` hanya berubah saat domain cepat idle: di antara layer, atau sebelum dan sesudah recompute.",
                "Sebelum MMCM2 direkonfigurasi, `sel` dipindah ke clock aman dan perpindahannya dikonfirmasi. Setelah rekonfigurasi, tunggu `LOCKED = 1` "
                "sebelum memakai turbo lagi.",
                "Rekonfigurasi hanya dilakukan di antara gambar."])
    d.figure(fig("fig_clockswitch"), "Urutan clock untuk satu gambar dan perpindahan ke gambar berikutnya. Diagram konsep tanpa skala waktu.")
    d.callout("catatan", ["Protokol ini sudah diverifikasi di simulasi oleh monitor di `tb/tb_system.v` [SIM]. Clock input sekarang diketahui, "
                          "yaitu 20 MHz di pin B13 [OFFICIAL], dan `clk_gen_xilinx` memakai VCO 1.000 MHz (ADR-015). Yang "
                          "belum ada adalah sequencer yang mengubah frekuensi MMCM2 saat berjalan (ADR-010); tanpa itu clock turbo tetap sama "
                          "dengan clock aman."])
    g = f["governor"]
    gp = g["params"]
    d.h2("5.8 Governor")
    d.p("Governor memilih level L, yaitu indeks tabel frekuensi turbo, dan bit `turbo_en` per layer. Kebijakannya sederhana dan seluruhnya ada di dalam "
        "FPGA (`docs/SPEC.md` §10, model `model/governor.py`). Di akhir setiap gambar:")
    d.code(["any_fail = False",
            "for l in layers:",
            "    if fails[l] > 0:",
            "        turbo_en[l] = 0; cool[l] = COOLDOWN; any_fail = True",
            "    elif not turbo_en[l]:",
            "        if cool[l] > 0: cool[l] -= 1",
            "        if cool[l] == 0: turbo_en[l] = 1",
            "corr = sum(corrected[l] for l in layers)",
            "if any_fail or corr > CORR_HI:",
            "    L = max(L - 1, L_MIN); clean_streak = 0",
            "else:",
            "    clean_streak += 1",
            "    if clean_streak >= N_UP:",
            "        L = min(L + 1, L_MAX); clean_streak = 0"])
    d.figure(fig("fig_governor"), f"Perilaku model governor dengan parameter bawaan (N_UP = {gp['n_up']}, COOLDOWN = {gp['cooldown']}, "
                                  f"CORR_HI = {gp['corr_hi']}) untuk urutan event buatan [SIM]: unit gagal di gambar "
                                  f"{', '.join(str(i) for i in g['fail_images'])}, dan koreksi berlebih di gambar "
                                  f"{', '.join(str(i) for i in g['corr_images'])}. Event ini ilustrasi, bukan pengukuran.")
    gov = ctx["reg"].get("governor", {}).get("summary", "")
    d.p(f"RTL governor (`rtl/governor.v`) harus menghasilkan trajektori state yang identik dengan model Python untuk urutan event yang sama. Testbench-nya "
        f"melaporkan `{gov}` [SIM].")
    d.h2("5.9 Fault injection")
    d.p("Untuk menguji checker tanpa menunggu error timing sungguhan, hardware punya dua slot injeksi, INJ0 dan INJ1. Setiap slot memilih LAYER, UNIT "
        "(atau ANY), LANE (1..K untuk lane data, K+1..K+3 untuk lane checksum), MASK, dan ONESHOT. Register holding lane terpilih di-XOR dengan MASK, "
        "sehingga error berjalan melewati FIFO, serializer, dan komparator persis seperti error timing (`docs/SPEC.md` §11).")
    d.callout("catatan", ["Injeksi membuktikan bahwa ~logika deteksi dan koreksi~ bekerja untuk pola error yang kita pilih. Injeksi ~tidak~ membuktikan bahwa "
                          "error timing nyata berpola sama. Itu pertanyaan E1 dan E2."])
    d.h2("5.10 Antarmuka host: SPI dan peta memori")
    d.p("Raspberry Pi berbicara dengan FPGA lewat SPI mode 0 (CPOL = 0, CPHA = 0), MSB dulu, CS aktif rendah. FPGA bertindak sebagai slave dan "
        "meng-~oversample~ sinyal SPI di clk_safe, dengan jaminan desain f_{SCLK} ≤ f_{safe}/8. Kecepatan SPI yang stabil di board belum diketahui [UNKNOWN].")
    d.table(["Perintah", "Format", "Fungsi"], [
        ["`0x02` WRITE", "`[0x02][A23:16][A15:8][A7:0][data…]`", "tulis, alamat byte auto-increment"],
        ["`0x03` READ", "`[0x03][A23:16][A15:8][A7:0][dummy]`, lalu data keluar di MISO", "baca, auto-increment"],
        ["`0x9F` ID", "8 byte keluar", "`\"SNTL\"`, versi major, versi minor, K, flags"],
    ], [1700, 4600, TEXT_W - 6300], caption="Perintah SPI (`docs/SPEC.md` §12.2).", size=17)
    d.table(["Rentang alamat", "Isi"], [
        ["`0x000000–0x000FFF`", "register 32-bit little-endian"], ["`0x010000–`", "memori bobot"],
        ["`0x020000–`", "bias, parameter requant, tabel layer"], ["`0x030000–`", "IMG0 (3.072 byte)"],
        ["`0x034000–`", "IMG1"], ["`0x040000–`", "logit (int32 × N)"], ["`0x050000–`", "log event (opsional)"],
    ], [3200, TEXT_W - 3200], caption="Peta alamat byte 24-bit; sumber kebenarannya `spec/regmap.yaml`.", size=17)
    d.p("Dua buffer gambar dipakai bergantian (~ping-pong~): host menulis IMG1 selagi engine memproses IMG0. Tabel layer dimuat saat runtime, sehingga "
        "model yang dilatih ulang untuk kelas lain cukup dimuat lewat SPI tanpa sintesis ulang, selama arsitektur konvolusinya sama dan N_CLASSES "
        "paling banyak 16.")
    d.h2("5.11 Perangkat lunak di Raspberry Pi")
    d.bullets(["`sw/sentinel/driver.py`: membaca dan menulis register, memuat bobot dan gambar, menjalankan inferensi.",
               "Transport: `SpidevTransport` untuk board dan `LogTransport` untuk ko-simulasi. Log byte dari driver diputar ulang ke SPI slave RTL di "
               "testbench (`tb/tb_spi_log.v`).",
               "Backend: `HwBackend` untuk board dan `MockBackend` yang memakai golden model, checker, governor, dan model error sintetis. API keduanya "
               "sama, jadi skrip eksperimen bisa diuji tanpa board; hasil mock selalu berlabel [SYNTHETIC].",
               "`camera.py` dan `preprocess.py`: center-crop, resize ke 32×32 dengan INTER_AREA, lalu RGB uint8 (C, H, W).",
               "Mode validasi (folder gambar ke akurasi, latensi, dan FPS) dan mode kamera real-time, sesuai syarat lomba [OFFICIAL]. Dashboard "
               "menampilkan kelas, FPS, frekuensi turbo, dan counter.",
               "`sw/sentinel/experiments/e1.py` sampai `e8.py` menulis `data.csv` dan `metadata.json` ke `results/<backend>/<exp>/<timestamp>/`."])
    d.callout("latihan", [("num", "1.\tK = 8 dan error e = −64 di lane 3. Berapa d1, d2, dan j?"),
                          ("num", "2.\tError +δ di lane 1 dan lane 5 sekaligus, tanpa C3. Lane mana yang akan dikoreksi checker? Apa yang terjadi kalau C3 aktif?"),
                          ("num", "3.\tMengapa clock hanya boleh dipindah saat domain cepat idle?"),
                          ("num", "4.\tDari sisi pengguna, apa beda antara koreksi yang tercatat di counter CORRECTED dan salah koreksi?")])


# ============================================================================ chapter 6


def ch6(d: Doc, ctx) -> None:
    d.h1("6", "Tur repo SENTINEL")
    d.p("**Tujuan bab ini:** tahu di mana setiap bagian berada, bagaimana alur kerja dari data sampai board, dan dokumen mana yang dibaca lebih dulu.")
    d.h2("6.1 Peta folder")
    d.table(["Folder", "Isi", "File penting"], [
        ["`config/`", "parameter model dan hardware", "`model_s.yaml`, `hw_default.yaml`; `mmcm_limits.yaml` dan `parts.yaml` belum diverifikasi ke datasheet"],
        ["`spec/`", "satu-satunya sumber register map", "`regmap.yaml`"],
        ["`model/`", "Python: training, kuantisasi, golden model, checker, governor, model error sintetis, kampanye", "`golden.py`, `checker.py`, `export.py`"],
        ["`rtl/`", "Verilog-2005 yang bisa disintesis", "`engine.v`, `lane_array.v`, `lane_checker.v`"],
        ["`rtl/platform/`", "wrapper primitif: `xilinx/` untuk Vivado, `sim/` untuk simulasi", "`cdc_fifo_xpm.v`, `clk_gen_sim.v`"],
        ["`rtl/gen/`", "hasil generate register map; jangan diedit", "`sentinel_regmap.vh`"],
        ["`tb/`", "testbench yang mencetak PASS n/n atau FAIL", "`tb_engine.v`, `tb_system.v`"],
        ["`tools/`", "semua perintah lewat `run.py`", "`run.py`, `sim.py`, `gen_regmap.py`, `study_guide/`"],
        ["`fpga/`", "alur Vivado OOC dan laporannya", "`ooc.tcl`, `run_matrix.py`, `reports/summary.csv`"],
        ["`board/`", "fakta board, rencana bring-up, top level board", "`BOARD_INFO.md`, `BRINGUP.md`, `bringup.py`"],
        ["`sw/sentinel/`", "perangkat lunak Raspberry Pi", "`driver.py`, `backend.py`, `experiments/`"],
        ["`tests/`", f"pytest, {ctx['n_tests']} file", "`test_golden.py`, `test_checker.py`, `test_rtl.py`"],
        ["`results/`", "data hasil yang di-commit", "`model/`, `sim/`, `mock/`, `hw/` (masih kosong)"],
        ["`docs/`", "spesifikasi, keputusan, verifikasi, hasil, draf laporan", "`SPEC.md`, `DECISIONS.md`, `RESULTS_SIM.md`"],
        ["`build/`", "hasil generate; tidak di-commit dan selalu bisa dibangkitkan ulang", "`vectors/`, `weights/`, `study_guide/`"],
    ], [1700, 4000, TEXT_W - 5700], caption="Folder utama repo.", size=17)
    d.h2("6.2 Alur kerja dari data sampai board")
    d.figure(fig("fig_pipeline"), "Alur kerja repo. Baris atas dan Vivado OOC sudah berjalan; langkah berlatar abu-abu menunggu board.")
    d.h2("6.3 Perintah standar")
    d.p("Semua perintah lewat `tools/run.py` (`CLAUDE.md` §9), supaya sama di Windows dan Linux:")
    d.code(["python tools/run.py check            # cek alat dan versi",
            "python tools/run.py test             # pytest + semua testbench",
            "python tools/run.py gen              # regmap, vektor, bobot",
            "python tools/run.py train --model s  # training",
            "python tools/run.py export --model s # kuantisasi + ekspor",
            "python tools/run.py sim <tb>         # satu testbench",
            "python tools/run.py campaign         # kampanye fault injection",
            "python tools/run.py ooc              # Vivado out-of-context",
            "python tools/run.py plots            # semua grafik"])
    reg = ctx["reg"]
    npass = sum(1 for e in reg.values() if e["passed"])
    d.h2("6.4 Verifikasi berlapis")
    d.table(["Tingkat", "Yang diuji", "Alat"], [
        ["L0", "requant, padding, flatten, argmax saat seri, tabel keputusan checker, batas bit", "pytest"],
        ["L1", "unit RTL: lane, lane array, generator operand, checker, postproc, pool, FIFO, SPI slave", "Icarus"],
        ["L2", "satu layer konvolusi dibandingkan dengan golden model", "Icarus, xsim"],
        ["L3", "engine satu clock: logit dan kelas bit-exact untuk ≥ 200 gambar", "xsim"],
        ["L4", "sistem dengan SPI, dua domain clock (rasio 1,0; 1,3; 1,7; 2,0) dan injeksi", "xsim"],
        ["L5", "governor, ≥ 50 skenario dibandingkan dengan model Python", "Icarus"],
    ], [1000, 6400, TEXT_W - 7400], caption="Tingkat verifikasi (`docs/SPEC.md` §13.3).", align=["center", "left", "left"])
    d.p(f"Regresi RTL terakhir: {npass} dari {len(reg)} testbench lulus [SIM] (`results/sim/rtl_regression.jsonl`, entri terbaru per bench). "
        "Ringkasannya ada di Bab 7.")
    d.h2("6.5 Keputusan desain (ADR)")
    d.p("Spesifikasi hanya boleh berubah lewat ADR (~architecture decision record~) di `docs/DECISIONS.md`. Urutannya selalu ADR, lalu SPEC, lalu golden "
        "model dan test, lalu RTL.")
    d.table(["ADR", "Keputusan"], [
        ["ADR-001", "dataflow output-stationary, satu lane per kanal output"],
        ["ADR-002", "bobot checksum dihitung on-the-fly di domain aman, tanpa BRAM tambahan"],
        ["ADR-003", "unit recompute = jendela pool × grup, dihitung ulang di akhir layer"],
        ["ADR-004", "suplai operand R = 2 set per siklus clk_safe"],
        ["ADR-005", "kebijakan konservatif untuk error di lane checksum (TRUST_CSUM_LANE = 0)"],
        ["ADR-006", "requant dengan M (uint16) dan geser n per layer"],
        ["ADR-007", "Icarus sebagai simulator utama, xsim sebagai referensi, Verilator untuk lint"],
        ["ADR-008", "selisih checker dihitung modulo 2^{48}; urutan serialisasi S1, S2, (S3), Y_K sampai Y_1"],
        ["ADR-009", "modul komparator bernama `lane_checker`, karena `checker` adalah kata kunci SystemVerilog"],
        ["ADR-010", "rekonfigurasi MMCM2 lewat Clocking Wizard AXI4-Lite (menunggu fase board)"],
        ["ADR-011", "rekomendasi C3: aktifkan bila resource cukup; keputusan akhir setelah E1"],
        ["ADR-012", "pipeline tambahan dan tafsir margin 30% SPEC §7.4"],
        ["ADR-013", "target dikunci ke XC7S25CSGA225-1; varian resmi model `s`, K = 8, lane `lut`, C3 aktif"],
        ["ADR-014", "laporan sintesis resmi desain lengkap sebagai deliverable utama"],
        ["ADR-015", "clock board 20 MHz sebagai input MMCM; clk_safe 125 MHz"],
        ["ADR-016", "peta I/O ZERO7: SPI0, sinyal selesai di GPIO25, LED milik FPGA; tombol dibaca Pi"],
        ["ADR-017", "indikator WS2812B yang digerakkan FPGA"],
        ["ADR-018", "suhu chip dari XADC"],
        ["ADR-019", "boot dari flash QSPI ditunda"],
        ["ADR-020", "kategori Class 2 Level 3 dan batas klaim"],
        ["ADR-021", "reset, synchronizer, dan aturan penyeberangan domain clock"],
    ], [1400, TEXT_W - 1400], caption="Daftar ADR di `docs/DECISIONS.md`.", size=18)
    d.h2("6.6 Urutan membaca dokumen repo")
    d.numbered(["`CLAUDE.md`: misi, aturan keras, cara kerja.",
                "`docs/SPEC.md`: spesifikasi teknis lengkap. Baca §0 sampai §6 dulu.",
                "`docs/ARCHITECTURE.md`: bagaimana RTL mewujudkan SPEC.",
                "`docs/DECISIONS.md`: alasan di balik setiap keputusan.",
                "`docs/VERIFICATION.md` dan `docs/RESULTS_SIM.md`: bagaimana semuanya diuji, dan hasilnya.",
                "`STATUS.md`: progres, item terblokir, dan catatan antar sesi.",
                "`board/BOARD_INFO.md` dan `board/BRINGUP.md`: apa yang dibutuhkan dari board.",
                "`docs/PRIOR_ART.md`: karya terkait dan batas klaim orisinalitas."])
    d.h2("6.7 Aturan kerja proyek")
    d.bullets(["Jangan mengarang hasil: setiap angka harus bisa dilacak ke skrip dan log di repo.",
               "Simulasi tidak bisa memunculkan error timing nyata; jangan mengklaim perilaku hardware dari simulasi atau model sintetis.",
               "Label wajib pada setiap angka, tabel, dan grafik: [SIM], [SYNTHETIC], [VIVADO-STA], atau [HW].",
               "Golden model dan RTL harus bit-exact, dan test tidak boleh dilemahkan supaya lulus.",
               "Jangan menebak fakta board; field UNKNOWN tetap UNKNOWN sampai ada sumber.",
               "Seed acak tetap, dan versi alat dicatat di `docs/ENVIRONMENT.md`.",
               "Primitif Xilinx hanya boleh ada di `rtl/platform/xilinx/`, masing-masing dengan model simulasi."])
    d.callout("latihan", [("num", "1.\tDi file mana register map didefinisikan, dan apa yang terjadi kalau `rtl/gen/` diedit tangan?"),
                          ("num", "2.\tMengapa folder `build/` tidak di-commit, sedangkan `results/` di-commit?"),
                          ("num", "3.\tKamu ingin mengubah rumus requant. Sebutkan urutan langkahnya.")])


# ============================================================================ chapter 7


def ch7(d: Doc, ctx) -> None:
    fl, qr, camp = ctx["fl"], ctx["qr"], ctx["camp"]
    d.h1("7", "Hasil sejauh ini")
    d.p("**Tujuan bab ini:** membaca hasil yang sudah ada dengan benar, termasuk label dan batasnya. Tidak ada satu pun angka di bab ini yang diukur di board.")
    d.h2("7.1 Akurasi model [SIM]")
    d.p(f"Model `s`: float {pct(fl['s']['test_acc_float'])}, integer {pct(qr['s']['test_acc_integer'])}, turun {nf(qr['s']['drop_points'], 2)} poin. "
        f"Model `xs`: float {pct(fl['xs']['test_acc_float'])}, integer {pct(qr['xs']['test_acc_integer'])}, turun {nf(qr['xs']['drop_points'], 2)} poin [SIM]. "
        "Semuanya diukur pada 10.000 gambar uji CIFAR-10 (Tabel 3.2).")
    d.h2("7.2 Kampanye fault injection [SIM]")
    d.p(f"`model/campaign.py` menyuntikkan mask XOR ke akumulator nyata dari golden model ({camp['images']} gambar uji, seed {camp['seed']}), lalu "
        "menjalankan checker. Kampanye ini menguji logika deteksi, bukan mengukur error timing [SIM].")
    d.figure(fig("fig_campaign"), "Hasil kampanye fault injection model `s` [SIM], dari `results/sim/campaign_s.json`. Error satu lane selalu terkoreksi. "
                                  "Tanpa C3, sekitar 6% error dua lane salah dikoreksi; dengan C3 semuanya dihitung ulang. Tidak ada error yang lolos tanpa "
                                  "terdeteksi (escaped = 0) di semua baris.")
    kname = {"single": "1 lane", "dual": "2 lane", "csum": "lane checksum"}
    rows = [[str(r["k"]), str(r["c3"]), kname[r["kind"]], nf(r["n"]), nf(r["corrected"]), nf(r["recompute"]), nf(r["miscorrected"]), nf(r["escaped"])]
            for r in camp["rows"]]
    d.table(["K", "C3", "Jenis error", "Percobaan", "Terkoreksi", "Hitung ulang", "Salah koreksi", "Lolos"], rows,
            [600, 600, 1700, 1300, 1300, 1400, 1400, TEXT_W - 8300], caption="Data lengkap kampanye [SIM].",
            align=["center", "center", "left"] + ["right"] * 5, size=17)
    d.p("Pelajaran utamanya: tanpa C3, salah koreksi adalah ~silent data corruption~ yang tidak terlihat dari counter CORRECTED. Karena itu ADR-011 "
        "merekomendasikan C3 bila resource part mencukupi.")
    d.h2("7.3 Regresi RTL [SIM]")
    reg = ctx["reg"]
    groups = [("lane_array", "lane dan lane array (3 jenis lane, K, C3)"), ("checker", "lane_checker vs model"), ("engine", "engine vs golden model"),
              ("spi", "SPI slave dan sesi driver"), ("system", "sistem dua clock, kampanye, autogov"), ("governor", "governor vs model Python")]
    rows = []
    for prefix, desc in groups:
        es = [e for name, e in sorted(reg.items()) if name.startswith(prefix)]
        ex = next((e for e in es if "n200" in e["bench"]), es[0])
        rows.append([f"`{prefix}*`", desc, str(len(es)), str(sum(e["passed"] for e in es)), f"`{ex['bench']}`: {ex['summary']}"])
    d.table(["Kelompok", "Isi", "Bench", "Lulus", "Contoh hasil"], rows, [1500, 2600, 700, 700, TEXT_W - 5500],
            caption="Ringkasan regresi RTL terakhir per kelompok [SIM], dari `results/sim/rtl_regression.jsonl`.", align=["left", "left", "center", "center", "left"], size=16)
    d.p("Lulus artinya keluaran RTL sama bit demi bit dengan golden model, checker model, atau governor model di simulasi. Simulasi tidak bisa "
        "memunculkan error timing nyata.")
    d.h2("7.4 Vivado out-of-context [VIVADO-STA]")
    ok, failed = len(ctx["viv"]), len(ctx["viv_failed"])
    failed_parts = sorted({re.match(r"xc7s\d+", n).group(0).upper() for n in ctx["viv_failed"]}, key=lambda x: int(x[4:]))
    d.p(f"`fpga/run_matrix.py` menjalankan {ok + failed} kombinasi dengan Vivado 2025.2: part XC7S6, XC7S15, XC7S25, dan XC7S50 dengan speed grade −1 "
        "dan −2, K ∈ {8, 16}, tiga jenis lane, dan C3 ∈ {0, 1}. Sebanyak "
        f"{ok} run berhasil (XC7S25 dan XC7S50), sedangkan {failed} run di {' dan '.join(failed_parts)} tidak muat karena BRAM kurang [VIVADO-STA] "
        "(`docs/RESULTS_SIM.md`).")
    d.figure(fig("fig_fmax"), "Fmax statis [VIVADO-STA], dari `fpga/reports/summary.csv`. Kiri: lane `lut` di empat part. Kanan: jenis lane di XC7S25 −1; "
                              "garis hitam adalah batas suplai operand R·f_{safe}. Target periode: clk_safe 7,0 ns; clk_fast 6,4 ns untuk `lut` dan "
                              "3,0 ns untuk lane DSP.")
    parts = ["xc7s25csga225-1", "xc7s25csga225-2", "xc7s50ftgb196-1", "xc7s50ftgb196-2"]
    rows = []
    for k in (8, 16):
        for p in parts:
            r = viv(ctx, p, k, 0, 0)
            rows.append([part_short(p), str(k), nf(float(r["lut"])), nf(float(r["ff"])), nf(float(r["bram36_equiv"]), 0), nf(float(r["dsp"])),
                         nf(float(r["fmax_safe_mhz"]), 1), nf(float(r["fmax_fast_mhz"]), 1)])
    d.table(["Part", "K", "LUT", "FF", "BRAM36", "DSP", "Fmax clk_safe (MHz)", "Fmax clk_fast (MHz)"], rows,
            [1400, 600, 1000, 1000, 1000, 800, 1900, TEXT_W - 7700], caption="Resource dan Fmax lane `lut`, model `s`, C3 = 0 [VIVADO-STA].",
            align=["left", "center"] + ["right"] * 6, size=17)
    supply = [2 * float(viv(ctx, p, 8, 0, 0)["fmax_safe_mhz"]) for p in parts]
    r0, r1 = viv(ctx, "xc7s25csga225-1", 8, 0, 0), viv(ctx, "xc7s25csga225-1", 8, 0, 1)
    est = next(e for e in ctx["fit"]["estimates"] if e["model"] == "s" and e["K"] == 8 and e["C3_EN"] == 0)
    d.h3("Cara membaca hasil ini")
    d.bullets([f"**Lane `lut` sesuai tujuan proyek.** Jalur MAC menjadi jalur kritis di domain cepat, dan suplai operand R·f_{{safe}} "
               f"({nf(min(supply), 0)}–{nf(max(supply), 0)} MHz untuk K = 8) jauh di atas Fmax lane, jadi masih ada ruang untuk overclock [VIVADO-STA].",
               "**Lane DSP lebih cepat secara STA**, tetapi batasnya menjadi FIFO dan suplai operand, bukan MAC. Untuk eksperimen overclock MAC, lane DSP "
               "baru berguna kalau R dinaikkan.",
               f"**Memori adalah batas ukuran part.** Model `s` K = 8 memakai {nf(float(r0['bram36_equiv']), 0)} BRAM36 di Vivado [VIVADO-STA], lebih banyak dari "
               f"estimasi awal {nf(est['bram36_equivalent'], 1)} BRAM36-ekuivalen dari `tools/fit_report.py` [SIM]. Karena itu XC7S6 dan XC7S15 tidak muat.",
               f"**Margin SPEC §7.4.** Dengan semua jalur non-MAC dibatasi 0,7 × periode, lane `lut` C3 = 0 di XC7S25 −1 memenuhi syarat (WNS non-MAC "
               f"{sn_float(r0['wns_nonmac_ns'])} ns), sedangkan C3 = 1 meleset tipis (WNS non-MAC {sn_float(r1['wns_nonmac_ns'])} ns) [VIVADO-STA].",
               "**Chip resmi adalah XC7S25 \u22121.** Baris lain di tabel dan grafik ini sekarang hanya pembanding (ADR-013).",
               "**STA itu konservatif.** Frekuensi saat chip benar-benar gagal hanya bisa diukur di board."])
    off = ctx["official"]
    d.h2("7.5 Laporan sintesis resmi XC7S25CSGA225-1 [VIVADO-STA]")
    d.p("Sejak 10 November 2026 laporan sintesis untuk chip ini wajib bagi semua tim [OFFICIAL]. `python tools/run.py synth-official` "
        "mengimplementasikan desain lengkap `top_board` (SPI, register, engine, governor, dan dua MMCM) dengan `board/zero7.xdc` pada varian "
        "resmi: model `s`, K = 8, lane `lut`, C3 aktif (ADR-013, ADR-014). Bitstream belum dibuat karena standar I/O board belum pasti.")
    if off:
        util = off["utilization_post_route"]
        label = {"lut": "Slice LUT", "ff": "Slice register", "bram_tile": "Block RAM", "dsp": "DSP48E1", "iob": "IOB", "bufgctrl": "Buffer clock global", "mmcm": "MMCM"}
        rows = [[label[k], nf(util[k]["used"], 1 if util[k]["used"] % 1 else 0), nf(util[k]["available"]), f"{nf(util[k]['util_pct'], 2)}%"]
                for k in label if k in util]
        d.table(["Resource", "Terpakai", "Tersedia", "Utilisasi"], rows, [3200, 2000, 2000, TEXT_W - 7200],
                caption="Resource desain lengkap sesudah place and route [VIVADO-STA], dari `results/vivado/official/summary.json`.",
                align=["left", "right", "right", "right"])
        crow = [[f"`{c['name']}`", nf(c["period_ns"], 3), nf(c["intra_endpoints"]), sn_float(str(c["intra_wns_ns"])), sn_float(str(c["intra_whs_ns"])),
                 nf(c["fmax_mhz"], 1)] for c in off["clocks"] if "fmax_mhz" in c]
        d.table(["Clock", "Periode (ns)", "Endpoint", "WNS setup (ns)", "WHS hold (ns)", "Fmax (MHz)"], crow, [2600, 1400, 1300, 1600, 1600, TEXT_W - 8500],
                caption="Timing jalur di dalam satu clock sesudah place and route [VIVADO-STA]. Fmax = 1000 / (periode − WNS).",
                align=["left", "right", "right", "right", "right", "right"], size=17)
        inter = "; ".join(f"`{r['from']}` ke `{r['to']}` {sn_float(str(r['wns_ns']))} ns" for r in off["inter_clock"]) or "tidak ada"
        d.p(f"Run ini memakai clk_safe {nf(1000 / float(off['SAFE_DIV']))} MHz. Jalur antar-clock yang ikut dianalisis: {inter}. Slack setup terburuk "
            f"desain {sn_float(off['design_wns_ns'])} ns, slack hold terburuk {sn_float(off['design_whs_ns'])} ns, dan net yang tidak ter-route "
            f"{off['unrouted_nets']} [VIVADO-STA]. Clock `clk_fast_turbo` dianalisis pada level turbo 0, yaitu sama dengan frekuensi aman. "
            "Menjalankan lane di atas frekuensi itu adalah eksperimen proyek ini dan berada di luar jangkauan analisis statis.")
        if off.get("cdc"):
            counts = ", ".join(f"{rule} {nf(row['count'])}" for rule, row in off["cdc"].items())
            d.p(f"Penyeberangan domain clock menurut `report_cdc` [VIVADO-STA]: {counts}. CDC-3 adalah synchronizer yang sudah bertanda. CDC-15 adalah "
                "memori FIFO asinkron dan kata status yang dibaca saat engine diam. CDC-1 dan CDC-4 adalah sinyal quasi-statis, yaitu konfigurasi "
                "injeksi dan indeks layer, yang hanya berubah saat domain cepat diam. Aturannya ada di SPEC §7.8 (ADR-021).")
    else:
        d.p("Laporan resmi belum dijalankan saat materi ini dibangun.")
    d.h2("7.6 Ringkasan status")
    c1 = ctx["reg"].get("engine_s_k8_c1_n200")
    d.table(["Bagian", "Status", "Bukti"], [
        ["Model dan kuantisasi", "selesai", "akurasi [SIM]"],
        ["Golden model dan RTL bit-exact", "selesai di simulasi", "200/200 gambar" + (", juga untuk varian resmi" if c1 else "") + " [SIM]"],
        ["Checker, koreksi, recompute", "selesai di simulasi", "kampanye dan regresi [SIM]"],
        ["Dua domain clock, protokol \u00a77.7", "selesai di simulasi", "`tb_system` [SIM]"],
        ["Governor", "selesai di simulasi", "`tb_governor` [SIM]"],
        ["Clock 20 MHz dan peta I/O ZERO7", "selesai di RTL dan XDC", "ADR-015, ADR-016; standar I/O belum pasti"],
        ["Aturan penyeberangan domain clock", "selesai", "ADR-021; `report_cdc` [VIVADO-STA]"],
        ["Laporan sintesis resmi", "selesai" if off else "belum", "[VIVADO-STA]"],
        ["Sequencer rekonfigurasi MMCM2", "belum", "ADR-010"],
        ["Sinyal selesai `irq_done` di driver", "selesai, diuji dengan pengganti GPIO", "ADR-016"],
        ["Indikator WS2812B dan suhu XADC", "belum", "ADR-017, ADR-018"],
        ["Software Pi dan skrip eksperimen", "selesai, diuji dengan mock", "[SYNTHETIC]"],
        ["Semua eksperimen di board", "belum mulai", "\u2014"],
    ], [3900, 2400, TEXT_W - 6300], caption="Status per 16 November 2026.")


def sn_float(v: str) -> str:
    x = float(v)
    return ("−" if x < 0 else "+") + nf(abs(x), 3)


# ============================================================================ chapter 8


def ch8(d: Doc, ctx) -> None:
    f = ctx["facts"]
    d.h1("8", "Yang belum bisa dijelaskan karena board belum ada")
    d.p("**Tujuan bab ini:** jujur tentang batas pengetahuan saat ini. Bagian ini sama pentingnya dengan bab hasil, karena juri akan menanyakan apa yang "
        "benar-benar sudah terbukti.")
    d.h2("8.1 Kenapa simulasi tidak bisa menggantikan board")
    d.p("Simulator RTL menghitung ~apa~ yang dihasilkan logika, tetapi tidak menghitung ~kapan~ sinyal benar-benar tiba. Di simulasi, perkalian selalu "
        "selesai tepat waktu berapa pun frekuensinya. Error timing lahir dari fisika chip: panjang kabel, variasi proses pembuatan, suhu, dan tegangan. "
        "STA memberi batas aman terburuk, dan model sintetis hanyalah asumsi kita sendiri. Ketiganya tidak bisa mengatakan apa yang akan dilakukan "
        "chip ZERO7 tertentu di meja kita.")
    d.h2("8.2 Pertanyaan riset yang masih terbuka")
    d.table(["ID", "Pertanyaan", "Kriteria berhasil [PROPOSAL]", "Status sekarang"], [
        ["E1", "Atlas error: di frekuensi, layer, lane, dan bit mana error muncul? Apakah error pertama hanya mengenai satu lane (H1)?",
         "≥ 90% kejadian di 3 frekuensi error terendah hanya satu lane", "skrip diuji dengan mock [SYNTHETIC]"],
        ["E2", "Apakah error deterministik (H2)?", "≥ 95% pengulangan memberi pola identik", "mock [SYNTHETIC]"],
        ["E3", "Apakah layer dalam mulai error di frekuensi lebih tinggi dari layer 1 (H3)?", "≥ 10% lebih tinggi", "mock [SYNTHETIC]"],
        ["E4", "Throughput dan akurasi tiga mode terhadap frekuensi", "mode 2 ≥ 1,2× mode 1 dan ≥ 1,4× baseline yang lolos timing", "mock [SYNTHETIC]"],
        ["E5", "Cakupan dan salah koreksi fault injection", "100% error satu lane terkoreksi", "sudah selesai [SIM]"],
        ["E6", "Governor mengikuti suhu tanpa hasil salah", "frekuensi mengikuti suhu tanpa hasil salah", "mock [SYNTHETIC]"],
        ["E7", "Bit-exact di set validasi pada board", "100% kelas dan logit identik", "[SIM] di RTL"],
        ["E8", "Biaya: resource, daya, keuntungan bersih", "keuntungan bersih positif", "resource [VIVADO-STA]; daya belum"],
    ], [600, 3700, 2800, TEXT_W - 7100], caption="Eksperimen SENTINEL (`docs/SPEC.md` §16).", size=17)
    d.p("Hipotesis H1–H3 bisa saja salah. Hasil negatif yang diukur dengan jujur tetap dilaporkan (`docs/SPEC.md` §16).")
    d.h2("8.3 Fakta board: yang sudah dan yang belum diketahui")
    d.p("Dokumen resmi 10 November 2026 menjawab sebagian besar pertanyaan (`board/BOARD_INFO.md`):")
    d.bullets(["Chip xc7s25csga225-1, speed grade \u22121 [OFFICIAL].",
               "Clock 20 MHz di pin B13 [OFFICIAL].",
               "SPI0 Raspberry Pi: SCLK di A8, MOSI di A6, MISO di A7, CE0 di D9 [OFFICIAL].",
               "LED WS2812B yang digerakkan FPGA di pin N1, LED biasa D5 dan D6, serta tombol START, STOP, dan RUN [OFFICIAL].",
               "Pemrograman lewat kabel Digilent JTAG-HS3 dari Vivado Hardware Manager dengan clock JTAG 3 MHz [OFFICIAL].",
               "Board dipasang di Raspberry Pi 5 [OFFICIAL]."])
    d.p("Yang masih [UNKNOWN]:")
    d.bullets(["tegangan VCCO dan standar I/O tiap bank; file `Zero7.xdc` resmi belum terbit",
               "ZERO7 User Manual dan skematik",
               "revisi board, LED3 dan LED4, polaritas tombol, dan jumlah LED WS2812B per rantai",
               "jenis flash QSPI dan posisi DIP mode untuk boot dari flash",
               "apakah kabel JTAG termasuk paket pinjaman"])
    d.callout("catatan", ["Versi 1.0 materi ini menduga chipnya XC7S25 dari foto yang buram. Dokumen resmi sekarang memastikannya. Aturannya tetap "
                          "berlaku: dugaan dicatat sebagai dugaan sampai ada sumber."])
    d.h2("8.4 Pekerjaan teknis yang menunggu")
    d.bullets(["Sequencer rekonfigurasi MMCM2 (ADR-010). Ini syarat overclocking nyata: tanpa itu clock turbo tidak bisa dinaikkan.",
               "Verifikasi batas MMCM ke DS189 dan kapasitas chip ke DS180; keduanya butuh datasheet AMD.",
               "Konfirmasi standar I/O dari `Zero7.xdc` resmi, lalu bitstream pertama.",
               "Indikator WS2812B (ADR-017), suhu XADC (ADR-018), dan tombol di perangkat lunak Pi (ADR-016).",
               "Keputusan akhir C3 setelah data E1 (ADR-011); varian resmi sementara memakai C3 aktif (ADR-013).",
               "Pengukuran kecepatan SPI di board."])
    d.h2("8.5 Seperti apa grafiknya nanti")
    d.p("Skrip eksperimen sudah diuji dengan MockBackend, yang memakai model error buatan. Grafiknya berguna untuk memeriksa skrip dan tata letak, tetapi "
        "bentuk kurvanya ~bukan ramalan~: bentuk itu berasal dari parameter yang kita pilih sendiri di `model/fault_model.py`. Semua grafik mock diberi "
        "watermark.")
    src = f.get("mock_sources", {})
    caps = {"e1": "Contoh keluaran E1 dari MockBackend [SYNTHETIC]: kejadian error per layer terhadap frekuensi turbo. Bukan pengukuran.",
            "e4": "Contoh keluaran E4 dari MockBackend [SYNTHETIC]: throughput tiga mode terhadap frekuensi turbo. Bukan pengukuran.",
            "e6": "Contoh keluaran E6 dari MockBackend [SYNTHETIC]: frekuensi turbo yang dipilih governor. Bukan pengukuran."}
    for exp in ("e1", "e4", "e6"):
        if exp in src:
            d.figure(fig(f"fig_mock_{exp}"), f"{caps[exp]} Sumber: `{src[exp]}`.", width_cm=13.0)
    d.h2("8.6 Rencana saat board datang")
    d.p("Fase board baru boleh dimulai jika semua field wajib di `board/BOARD_INFO.md` sudah terisi beserta sumbernya, dan pemilik proyek menulis "
        "\"board siap\" (`CLAUDE.md` §8). Aturan keselamatannya:")
    d.bullets(["Selalu mulai dari clock aman. Overclocking baru boleh setelah E7 bit-exact di clock aman.",
               "Jangan pernah mengubah tegangan, dan pantau suhu.",
               "Hasil board diberi label [HW] dan disimpan di `results/hw/`, terpisah dari `results/mock/`."])
    d.table(["Langkah", "Perintah", "Lulus jika"], [
        ["1. Daya", "`bringup.py power`", "checklist dikonfirmasi dan tegangan diukur dengan multimeter"],
        ["2. Programming", "`bringup.py program`", "bitstream termuat"],
        ["3. LED", "`bringup.py led`", "LED1–LED4 mengikuti pola dari bitstream"],
        ["4. SPI loopback", "`bringup.py spi-loopback`", "pola tulis-baca identik di kecepatan SPI terendah"],
        ["5. Baca ID", "`bringup.py id`", "mengembalikan `SNTL` dengan versi dan K yang benar"],
        ["6. Muat bobot", "`bringup.py load --model s`", "256 byte pertama terbaca sama dengan file"],
        ["7. Satu gambar", "`bringup.py one-image`", "kelas dan logit sama dengan golden model"],
        ["8. Validasi penuh", "`bringup.py validate --images 200`", "100% logit sama (E7)"],
        ["9. Turbo bertahap", "`bringup.py turbo`", "level naik satu per satu dan berhenti di FATAL pertama"],
    ], [2000, 3300, TEXT_W - 5300], caption="Langkah bring-up (`board/BRINGUP.md`). Setiap langkah bisa dilatih dulu dengan `--dry-run`, yang tidak "
                                            "membuktikan apa pun tentang hardware.", size=17)
    d.callout("catatan", [("bullet", "Minta `Zero7.xdc`, ZERO7 User Manual, dan file contoh ke panitia saat mengurus peminjaman board."),
                          ("bullet", "Tanyakan apakah kabel JTAG-HS3 termasuk paket pinjaman."),
                          ("bullet", "Siapkan Raspberry Pi 5 (catu daya 5 V 5 A, OS, SPI aktif, SSH) dan modul kamera."),
                          ("bullet", "Baca teks lengkap Marty dkk. dan Li dkk. (Bab 9) sebelum menulis klaim di laporan."),
                          ("bullet", "Konfirmasi kategori Class 2 Level 3 ke panitia dan tunggu pengumuman kelas target.")],
              title="YANG BISA DIKERJAKAN SEKARANG")


# ============================================================================ chapter 9


def ch9(d: Doc, ctx) -> None:
    d.h1("9", "Sumber belajar")
    d.p("Daftar ini disusun dari yang paling dasar. Untuk dokumen AMD, cari nomor dokumennya di <<https://docs.amd.com>>. Urutan membaca "
        "dokumen repo SENTINEL ada di Bagian 6.6; dokumen resmi lomba ada di `docs/official/` dengan ringkasan di `docs/official/README.md`.")
    d.h2("9.1 Rencana belajar empat minggu")
    d.table(["Minggu", "Fokus", "Bacaan utama", "Target"], [
        ["1", "CNN dasar", "CS231n modul CNN; d2l.ai bab CNN; Bab 2 materi ini", "bisa menghitung ukuran output, jumlah bobot, dan MAC sendiri"],
        ["2", "Kuantisasi dan hardware CNN", "Jacob dkk. 2018; Nagel dkk. 2021; Sze dkk. 2017", "paham skala, requant, dan dataflow"],
        ["3", "Desain digital, FPGA, Vivado", "Harris & Harris; UG901, UG903, UG906; Cummings 2002", "paham timing, slack, CDC, dan laporan Vivado"],
        ["4", "Fault tolerance dan SENTINEL", "Huang & Abraham 1984; Marty dkk. 2018; Chamberlin dkk. 2024; SPEC dan DECISIONS", "bisa menjelaskan SENTINEL dan batas klaimnya"],
    ], [900, 2300, 3500, TEXT_W - 6700], caption="Rencana belajar yang disarankan.", align=["center", "left", "left", "left"])
    d.h2("9.2 CNN dan deep learning")
    d.bullets(["Goodfellow, Bengio, dan Courville (2016). ~Deep Learning~. MIT Press. Bab 6 (jaringan feedforward) dan Bab 9 (CNN). <<https://www.deeplearningbook.org>>",
               "Stanford CS231n, catatan kuliah ~Convolutional Neural Networks for Visual Recognition~. Penjelasan konvolusi yang paling jelas untuk pemula. <<https://cs231n.github.io>>",
               "Zhang, Lipton, Li, dan Smola. ~Dive into Deep Learning~. Buku interaktif dengan kode PyTorch. <<https://d2l.ai>>",
               "Nielsen (2015). ~Neural Networks and Deep Learning~. Intuisi backpropagation. <<http://neuralnetworksanddeeplearning.com>>",
               "Dumoulin dan Visin (2016). ~A guide to convolution arithmetic for deep learning~. arXiv:1603.07285. Semua variasi padding dan stride, lengkap dengan gambar.",
               "LeCun, Bottou, Bengio, dan Haffner (1998). ~Gradient-based learning applied to document recognition~. Proceedings of the IEEE 86(11). Makalah klasik LeNet.",
               "Krizhevsky (2009). ~Learning Multiple Layers of Features from Tiny Images~. Laporan teknis University of Toronto; asal dataset CIFAR-10.",
               "Ioffe dan Szegedy (2015). ~Batch Normalization: Accelerating Deep Network Training by Reducing Internal Covariate Shift~. ICML; arXiv:1502.03167.",
               "`docs/official/CNN_Example_2019.pdf`: slide pengajaran CNN dari panitia. Catatan: contoh kode MATLAB di `CNN_2019.zip` menerapkan turunan "
               "sigmoid dua kali pada backprop konvolusi, jadi jangan dijadikan acuan aritmetika (`docs/official/README.md`)."])
    d.h2("9.3 Kuantisasi")
    d.bullets(["Jacob dkk. (2018). ~Quantization and Training of Neural Networks for Efficient Integer-Arithmetic-Only Inference~. CVPR; arXiv:1712.05877. "
               "Dasar requant dengan pengali dan geser.",
               "Krishnamoorthi (2018). ~Quantizing deep convolutional networks for efficient inference: A whitepaper~. arXiv:1806.08342.",
               "Nagel dkk. (2021). ~A White Paper on Neural Network Quantization~. arXiv:2106.08295. PTQ, QAT, dan jebakannya."])
    d.h2("9.4 Akselerator CNN")
    d.bullets(["Sze, Chen, Yang, dan Emer (2017). ~Efficient Processing of Deep Neural Networks: A Tutorial and Survey~. Proceedings of the IEEE 105(12); "
               "arXiv:1703.09039. Pengantar terbaik untuk dataflow seperti output-stationary.",
               "Chen, Krishna, Emer, dan Sze (2017). ~Eyeriss: An Energy-Efficient Reconfigurable Accelerator for Deep Convolutional Neural Networks~. IEEE JSSC 52(1).",
               "Zhang dkk. (2015). ~Optimizing FPGA-based Accelerator Design for Deep Convolutional Neural Networks~. FPGA ’15."])
    d.h2("9.5 Desain digital, FPGA, dan Vivado")
    d.bullets(["Dokumen ZERO7 dari panitia: `docs/official/Initialize_20260618_EN.pdf` (penyiapan Raspberry Pi, proyek Vivado, JTAG) dan `docs/official/ZERO7FPGA_Connection-table_261109_001.pdf` (tabel pin). Ringkasannya di `board/BOARD_INFO.md`.",
               "Harris dan Harris. ~Digital Design and Computer Architecture~. Morgan Kaufmann. Bab timing (setup dan hold) serta Verilog.",
               "Cummings (2002). ~Simulation and Synthesis Techniques for Asynchronous FIFO Design~. SNUG San Jose. Rujukan klasik FIFO asinkron dengan Gray code.",
               "Cummings (2008). ~Clock Domain Crossing (CDC) Design & Verification Techniques Using SystemVerilog~. SNUG Boston.",
               "AMD 7-series: UG474 (CLB), UG473 (memori blok), UG479 (DSP48E1), UG472 (clocking: MMCM, BUFGCTRL), DS180 (ringkasan keluarga dan jumlah "
               "resource per part), DS189 (karakteristik DC dan AC Spartan-7, termasuk batas MMCM), PG065 (Clocking Wizard), XAPP888 (rekonfigurasi dinamis MMCM).",
               "AMD Vivado: UG901 (sintesis), UG903 (constraint), UG904 (implementasi), UG906 (analisis desain dan timing closure), UG949 (UltraFast Design "
               "Methodology), UG900 (simulasi), UG953 (library 7-series, termasuk XPM).",
               "Dokumentasi Icarus Verilog <<https://steveicarus.github.io/iverilog/>> dan Verilator <<https://verilator.org>>."])
    d.h2("9.6 Fault tolerance dan overclocking")
    d.bullets(["Huang dan Abraham (1984). ~Algorithm-Based Fault Tolerance for Matrix Operations~. IEEE Transactions on Computers C-33(6). Asal-usul ABFT dan checksum.",
               "Marty, Yuki, dan Derrien (2018). ~Enabling Overclocking through Algorithm-Level Error Detection~. FPT 2018. Versi jurnal 2020: ~Safe "
               "Overclocking for CNN Accelerators through Algorithm-Level Error Detection~. Kode: <<https://github.com/ThibautMarty/conv-hls-overclocking>>",
               "Chamberlin dkk. (2024). ~Understanding Timing Error Characteristics from Overclocked Systolic Multiply–Accumulate Arrays in FPGAs~. "
               "JLPEA 14(1):4. <<https://www.mdpi.com/2079-9268/14/1/4>>",
               "Jiang, Yu, Chen, dan Ha (2023). ~AOS: An Automated Overclocking System for High-Performance CNN Accelerator Through Timing Delay Measurement on FPGA~. IEEE TCAD.",
               "Zhao dkk. (2021). ~FT-CNN: Algorithm-Based Fault Tolerance for Convolutional Neural Networks~. IEEE TPDS; arXiv:2003.12203.",
               "Ernst dkk. (2003). ~Razor: A Low-Power Pipeline Based on Circuit-Level Timing Speculation~. MICRO-36. Latar belakang deteksi error timing di tingkat rangkaian.",
               "Zhang dkk. (2018). ~ThUnderVolt: Enabling Aggressive Voltage Underscaling and Timing Error Resilience for Energy Efficient Deep Learning "
               "Accelerators~. arXiv:1802.03806."])
    d.p("Status bacaan setiap karya terkait (baru abstrak atau sudah teks lengkap) dicatat di `docs/PRIOR_ART.md`. Sebelum menulis klaim orisinalitas, "
        "baca dulu tiga karya di bagian \"Wajib dibaca\" pada file itu.")


# ============================================================================ appendices


def appendix_a(d: Doc, ctx) -> None:
    d.h1("A", "Glosarium")
    terms = [
        ("ABFT", "~algorithm-based fault tolerance~: mendeteksi atau mengoreksi error memakai sifat matematika algoritma, misalnya checksum"),
        ("Akumulator", "register yang menjumlahkan hasil kali berturut-turut"),
        ("argmax", "indeks dari nilai terbesar"),
        ("Bit-exact", "setiap bit keluaran sama persis dengan acuan"),
        ("BRAM", "~block RAM~, memori blok di FPGA (36 Kb per blok di 7-series)"),
        ("BUFGCTRL", "buffer clock global yang bisa memilih satu dari dua clock tanpa glitch"),
        ("CDC", "~clock domain crossing~: sinyal berpindah antar domain clock"),
        ("Lane checksum", "lane tambahan yang menghitung jumlah (berbobot) hasil lane data"),
        ("clk_safe, clk_fast, clk_turbo", "clock aman yang lolos timing; clock lane yang bisa turbo; clock turbo dari MMCM2"),
        ("DSP48E1", "blok pengali-akumulator di FPGA 7-series"),
        ("Epoch", "satu putaran penuh atas seluruh data latih"),
        ("FIFO asinkron", "antrean dengan clock tulis dan clock baca yang berbeda"),
        ("Fmax", "frekuensi maksimum perkiraan STA"),
        ("Golden model", "model acuan Python yang hasilnya dianggap benar"),
        ("Governor", "pengendali yang memilih frekuensi turbo dan layer mana yang boleh turbo"),
        ("Gray code", "kode biner yang hanya berubah satu bit setiap langkah"),
        ("HAT", "papan tambahan yang dipasang di header GPIO Raspberry Pi"),
        ("Lane", "satu jalur MAC yang menghitung satu kanal output"),
        ("LUT", "~look-up table~: blok logika yang bisa membuat fungsi apa pun dari 6 input"),
        ("MAC", "~multiply-accumulate~: acc ← acc + w·x"),
        ("MMCM", "~mixed-mode clock manager~: pembangkit clock di FPGA"),
        ("OOC", "~out-of-context~: sintesis satu modul tanpa pin board"),
        ("Oracle", "acuan yang menentukan benar atau salah dalam sebuah test"),
        ("Output-stationary", "dataflow tempat akumulator tetap di lane sampai satu output selesai"),
        ("PTQ dan QAT", "~post-training quantization~ dan ~quantization-aware training~"),
        ("Requant", "mengubah akumulator 32 bit menjadi aktivasi 8 bit dengan pengali M dan geser n"),
        ("SDC", "~silent data corruption~: hasil salah yang tidak terdeteksi"),
        ("Setup time", "waktu minimum data harus stabil sebelum tepi clock"),
        ("Slack dan WNS", "sisa waktu sebuah jalur; slack terburuk di seluruh desain"),
        ("SPI", "~serial peripheral interface~: bus serial antara Raspberry Pi dan FPGA"),
        ("STA", "~static timing analysis~: analisis waktu tempuh semua jalur tanpa simulasi"),
        ("Unit hitung, unit recompute", "satu posisi output × satu grup; satu jendela pool × satu grup"),
        ("XADC", "ADC internal 7-series yang juga bisa membaca suhu chip (ada tidaknya di part ZERO7 belum diketahui)"),
        ("XDC", "file constraint Vivado untuk pin dan clock"),
        ("XPM", "~Xilinx Parameterized Macros~, misalnya `xpm_fifo_async`"),
    ]
    d.table(["Istilah", "Arti"], [[f"**{a}**", b] for a, b in terms], [2700, TEXT_W - 2700], size=18)


def appendix_b(d: Doc, ctx) -> None:
    d.h1("B", "Kunci jawaban latihan")
    d.h3("Bab 2")
    d.numbered(["O = (16 + 0 − 3)/1 + 1 = 14, jadi output 14×14.",
                "32 · 32 · 9 = 9.216 bobot, cocok dengan Tabel 2.2.",
                "Softmax monoton naik, sehingga urutan logit sama dengan urutan probabilitas; argmax logit sudah memberi kelas.",
                "8 · 8 · 32 · 32 · 9 = 589.824 MAC, cocok dengan Tabel 2.2."])
    d.h3("Bab 3")
    d.numbered(["Syaratnya round(0,01 · 2^{n}) ≤ 65.535. Dengan n = 22: M = round(0,01 · 4.194.304) = 41.943, masih muat. Dengan n = 23: "
                "M = 83.886, terlalu besar. Jadi n = 22 dan M = 41.943.",
                "v negatif membuat q negatif, sehingga clamp memberi y = 0. Inilah ReLU.",
                "Supaya rentang bobot simetris (−127..127): negasi −128 tidak muat di int8, dan batas terburuk akumulator menjadi simetris."])
    d.h3("Bab 4")
    d.numbered(["f_{max} = 1/(5 − (−0,5)) ns = 1/5,5 ns ≈ 181,8 MHz.",
                "Gray code hanya mengubah satu bit setiap kenaikan. Kalau pointer tertangkap tepat saat berubah, nilainya paling jauh salah satu langkah "
                "(nilai lama atau nilai baru), bukan nilai acak.",
                "Suhu, tegangan, dan variasi proses pembuatan chip (ditambah panjang routing hasil place and route)."])
    d.h3("Bab 5")
    d.numbered(["d1 = −64, d2 = 3 · (−64) = −192, sehingga j = d2/d1 = 3.",
                "d1 = 2δ dan d2 = (1 + 5)δ = 6δ, jadi j = 3: lane 3 yang benar malah \"dikoreksi\" (salah koreksi). Dengan C3: d3 = (1 + 25)δ "
                "= 26δ, sedangkan j²·d1 = 9 · 2δ = 18δ. Tidak cocok, sehingga hasilnya RECOMPUTE.",
                "Supaya tidak ada unit yang sebagian dihitung di clock turbo dan sebagian di clock aman. Dengan begitu log recompute, counter, dan "
                "perbandingan per layer tetap bermakna, dan tidak ada data yang sedang berjalan di jalur saat clock berpindah.",
                "CORRECTED berarti error terdeteksi dan diperbaiki, dan tercatat. Salah koreksi berarti checker yakin memperbaiki padahal mengubah lane yang "
                "benar: hasil akhirnya salah dan tidak ada tanda apa pun (SDC)."])
    d.h3("Bab 6")
    d.numbered(["`spec/regmap.yaml`. File di `rtl/gen/` dibangkitkan ulang oleh `tools/gen_regmap.py`, dan ada test yang memastikan hasil generate "
                "selalu terbaru, jadi editan tangan akan tertimpa atau membuat test gagal.",
                "`build/` selalu bisa dibangkitkan ulang dari skrip dan seed tetap, sedangkan `results/` berisi data eksperimen dan metadata yang menjadi bukti.",
                "ADR baru di `docs/DECISIONS.md`, lalu perbarui SPEC, lalu golden model dan test-nya, lalu RTL, lalu jalankan semua test sampai hijau."])


def appendix_c(d: Doc, ctx) -> None:
    d.h1("C", "File sumber setiap angka")
    d.table(["Angka atau gambar", "File sumber", "Skrip"], [
        ["Akurasi dan kurva training", "`results/model/<m>/float_result.json`, `quant_result.json`, `train_log.csv`", "`model/train.py`, `model/export.py`"],
        ["Ukuran model, MAC, siklus ideal", "`results/model/arch_s.json`", "`model/arch_report.py`"],
        ["Parameter requant, bobot integer", "`results/model/s/quant_result.json`, `quant.npz`", "`model/export.py`"],
        ["Peta fitur, contoh requant, contoh checksum", "`results/model/s/quant.npz` dan CIFAR-10 test set", "`model/golden.py`, `model/checker.py` lewat `tools/study_guide/figures.py`"],
        ["Kampanye fault injection", "`results/sim/campaign_s.json`", "`model/campaign.py`"],
        ["Regresi RTL dan siklus terukur", "`results/sim/rtl_regression.jsonl`", "`tools/sim.py --record`"],
        ["Estimasi BRAM", "`results/sim/fit_report.json`", "`tools/fit_report.py`"],
        ["Resource dan Fmax Vivado", "`fpga/reports/summary.csv`; run yang tidak muat dari log lokal `fpga/reports/*_final.log`", "`fpga/run_matrix.py`, `fpga/parse_reports.py`"],
        ["Grafik mock E1, E4, E6", "`results/mock/<exp>/<timestamp>/`", "`sw/sentinel/experiments/`, `sw/sentinel/plots/all.py`"],
        ["Laporan sintesis resmi", "`results/vivado/official/summary.json` dan file `.rpt` di folder yang sama", "`fpga/run_official.py`, `fpga/synth_official.tcl`"],
        ["Resource chip dan fungsi pin", "`results/vivado/part_check.txt`, `results/vivado/pin_check.txt`", "`tools/vivado_check_part.tcl`, `board/pin_check.tcl`"],
        ["Fakta board", "`board/BOARD_INFO.md`", "dokumen resmi di `docs/official/`"],
        ["Trajektori governor", "urutan event buatan di skrip", "`model/governor.py` lewat `tools/study_guide/figures.py`"],
    ], [2900, 3800, TEXT_W - 6700], caption="Jejak setiap angka ke file dan skrip di repo.", size=17)
    d.p(f"Materi ini dibangkitkan dari commit `{ctx['head']}`. Kalau hasil di repo berubah, jalankan ulang dua perintah di Bagian 0.3.", before=200)


def main() -> int:
    ctx = load_context()
    d = Doc()
    cover(d, ctx)
    for chapter in (changes, ch0, ch1, ch2, ch3, ch4, ch5, ch6, ch7, ch8, ch9, appendix_a, appendix_b, appendix_c):
        chapter(d, ctx)
    d.save(OUT_DOCX, "SENTINEL — Materi Belajar", "SENTINEL  ·  Materi belajar CNN, FPGA, dan repo")
    print(f"wrote {OUT_DOCX.relative_to(ROOT)} ({OUT_DOCX.stat().st_size // 1024} KB, {len(d.media)} gambar)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
