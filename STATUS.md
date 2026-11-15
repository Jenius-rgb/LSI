# STATUS — SENTINEL

Terakhir diperbarui: 2026-11-16, sesi pembaruan ZERO7 (pra-board).
Fase: **PRA-BOARD**

Legenda: `[ ]` belum · `[~]` sedang dikerjakan · `[x]` selesai (ada bukti di Log bukti) · `[B]` terblokir (alasan di bagian Terblokir)

## Gerbang dan tanggal

| Gerbang | Tanggal | Syarat |
| --- | --- | --- |
| G1 | 13 Des 2026 | M0–M8 selesai di simulasi. Di board: CNN bit-exact di clock aman (butuh board). |
| G2 | 3 Jan 2027 | M10 selesai. Di board: governor berjalan dan data E4 ada. |
| Bekukan hardware | 17 Jan 2027 | Tidak ada fitur baru setelah tanggal ini, hanya pengukuran dan penulisan. |
| Laporan | 31 Jan 2027 | [OFFICIAL] batas pengiriman laporan |
| Lomba | 5 Mar 2027 | [OFFICIAL] Chitose, hybrid |

Jika G1 meleset lebih dari satu minggu, buang pemilihan clock per layer dan pakai satu clock turbo global (catat ADR).

---

## Fase PRA-BOARD

### M0 — Setup repo dan lingkungan
- [x] Struktur folder sesuai SPEC §17, `.gitignore` (build/, dataset, checkpoint besar), `git init`, `README.md` (English)
- [x] `requirements.txt` (numpy, torch, torchvision, pyyaml, pytest, hypothesis, matplotlib; opsional: opencv-python, flask; khusus Pi: spidev, picamera2)
- [x] `tools/check_env.py`: deteksi dan cetak versi Python, torch, numpy, pytest, iverilog/vvp, verilator, vivado/xvlog/xsim
- [x] `tools/run.py` dengan subcommand: check, test, gen, train, export, sim, campaign, ooc, plots
- [x] `docs/ENVIRONMENT.md` berisi versi alat yang benar-benar terdeteksi

**DoD:** `python tools/run.py check` dan `python tools/run.py test` berjalan di mesin ini (test boleh sedikit, tapi lulus). ENVIRONMENT.md terisi dari output check.

### M1 — Model float
- [x] `config/model_s.yaml`, `config/model_xs.yaml`; `model/arch.py` membangun model dari config
- [x] `model/arch_report.py`: jumlah parameter, MAC, dan siklus per K
- [x] `model/train.py`: CIFAR-10, seed tetap, augmentasi ringan, simpan checkpoint dan log
- [x] Dukung dataset folder (format ImageFolder) dan N_CLASSES bebas, supaya bisa langsung dilatih ulang saat panitia mengumumkan kelas target

**DoD:** arch_report cocok dengan SPEC §2 (kalau tidak, perbaiki SPEC lewat ADR). Akurasi float varian s dan xs tercatat di `results/model/` beserta seed.

### M2 — Kuantisasi, golden model, ekspor
- [~] `model/quant.py`: fold BN dan PTQ selesai; opsi QAT belum diimplementasi karena tidak diperlukan (penurunan akurasi model s 0,26 poin, target ≤ 2)
- [x] `model/golden.py`: SPEC §3 persis, NumPy int64
- [x] `model/export.py`: `.bin` + `manifest.json` + `.mem` + bound check (SPEC §3.6)
- [x] Test L0: requant (pembulatan .5, negatif, saturasi, n = 0), padding, flatten, argmax seri, batas bit

**DoD:** akurasi integer tercatat. Target penurunan ≤ 2 poin dari float; jika tidak tercapai, tulis ADR dan langkah perbaikannya. Semua test L0 hijau. Ekspor deterministik (hash sama jika dijalankan dua kali).

### M3 — Checker model dan kampanye fault (Python)
- [x] `model/checker.py` (SPEC §6.2 dan §11.2), `model/fault_model.py` (§11.3), `model/campaign.py`
- [x] Property test untuk tabel keputusan (hypothesis jika tersedia)
- [x] Kampanye untuk K ∈ {8, 16} dan C3 ∈ {0, 1}: 10.000 error satu lane, 10.000 dua lane, 1.000 di lane checksum. Injeksi pada akumulator nyata dari golden model (layer nyata, gambar nyata).

**DoD:** 100% error satu lane terkoreksi. Tabel laju (clean, corrected, csum_lane, recompute, salah koreksi, lolos) ada di `docs/RESULTS_SIM.md` dengan label [SIM]. Rekomendasi soal C3 ditulis sebagai ADR.

### M4 — RTL lane dan lane array
- [x] `rtl/lane_lut.v`, `rtl/lane_dsp_min.v`, `rtl/lane_dsp_full.v`
- [x] `rtl/lane_array.v`: K lane data + 2/3 lane checksum, register holding, serializer
- [x] Testbench dengan vektor golden: ≥ 10.000 unit acak + ≥ 100 tile nyata

**DoD:** bit-exact untuk semua LANE_IMPL. Lint Verilator bersih (jika tersedia).

### M5 — RTL checker dan korektor
- [x] `rtl/lane_checker.v` (ADR-009) sesuai SPEC §6.2: mode 0/1/2, C3_EN, TRUST_CSUM_LANE, pencarian j tanpa pembagi

**DoD:** bit-exact terhadap `model/checker.py` pada ≥ 2.000 kasus dari M3, mencakup setiap cabang keputusan.

### M6 — RTL engine satu clock
- [x] Generator operand (alamat, padding, wc on-the-fly), kontrol layer berbasis tabel layer
- [x] Post-processing (SPEC §3.3), pooling, FC, argmax, buffer aktivasi

**DoD:** logit dan kelas bit-exact untuk ≥ 200 gambar (varian s dan xs). Siklus nyata dibanding model ≤ 10% overhead. Semua kasus sudut SPEC §13.4 diuji.

### M7 — Antarmuka host
- [x] `spec/regmap.yaml` + `tools/gen_regmap.py` → `rtl/gen/` dan `sw/sentinel/regmap.py`
- [x] `rtl/spi_slave.v`, register file, muat bobot lewat SPI, buffer gambar ping-pong
- [x] Driver Python + `LogTransport`; testbench memutar ulang log transaksi

**DoD:** transaksi lengkap (ID → muat bobot → tulis gambar → START → baca kelas, logit, counter) bit-exact di simulasi. Ada test yang memastikan file hasil generate selalu terbaru.

### M8 — Dua domain clock, mode, recompute
- [x] `rtl/platform/*/cdc_fifo` (XPM dan behavioral), `clk_gen` (sim dan Xilinx)
- [x] Suplai operand R, pemilihan clock per layer, recompute pass + log, mode 0/1/2, counter STARVE
- [ ] Opsional: bit paritas operand (tidak dikerjakan di sesi ini; opsional menurut SPEC)

**DoD:** bit-exact end-to-end untuk rasio f_fast/f_safe ∈ {1,0; 1,3; 1,7; 2,0}. Dengan injeksi satu lane: mode 2 bit-exact, mode 1 bit-exact lewat recompute, mode 0 menunjukkan mismatch sesuai prediksi. Counter cocok dengan model.

### M9 — Injeksi hardware dan kampanye RTL
- [x] Register INJ0/INJ1 (SPEC §11.1)
- [x] Skrip kampanye RTL: ≥ 2.000 injeksi, termasuk dua lane

**DoD:** outcome RTL 100% sama dengan prediksi model Python. Hasil masuk `docs/RESULTS_SIM.md` dengan label [SIM].

### M10 — Governor dan rekonfigurasi clock
- [x] `model/governor.py`, `rtl/governor.v`
- [B] Rekonfigurasi MMCM2: pilihan dicatat di ADR-010 (Clocking Wizard via AXI-Lite); implementasi di `rtl/platform/xilinx/clk_gen_xilinx.v` menunggu dukungan device Spartan-7, F_IN, dan PG065 (lihat Terblokir)
- [B] `tools/gen_mmcm_table.py` selesai dan lolos test batas, tetapi batas di `config/mmcm_limits.yaml` belum dicek ke DS189 (halaman belum ada, `verified: false`); F_IN placeholder
- [x] Testbench ≥ 50 skenario dengan event dari fault model sintetis

**Status:** `[~]` governor dan protokol selesai di simulasi; rekonfigurasi MMCM asli `[B]` (ADR-010); batas MMCM belum diverifikasi ke DS189.

**DoD:** trajektori state RTL sama dengan model untuk semua skenario. Urutan SPEC §7.7 terverifikasi di simulasi. Tabel MMCM lolos test batas.

### M11 — Vivado out-of-context
- [x] `fpga/ooc.tcl`, `fpga/run_matrix.py` (matriks varian), parser laporan ke CSV
- [x] `tools/fit_report.py` (estimasi BRAM dan DSP per part dari config)

**Status:** `[x]` matriks lengkap 96 run (xc7s6, xc7s15, xc7s25, xc7s50; speed -1 dan -2; K 8/16; lut, dsp_min, dsp_full; C3 0/1). 48 run di xc7s25 dan xc7s50 berhasil; 48 run di xc7s6 dan xc7s15 tidak muat (BRAM kurang). Tabel dan analisis jalur kritis di `docs/RESULTS_SIM.md` [VIVADO-STA]. Part ZERO7 dan speed grade belum terverifikasi.

**DoD:** tabel resource dan Fmax [VIVADO-STA] per part dan varian di `docs/RESULTS_SIM.md`. Analisis jalur kritis sesuai SPEC §7.4. Jika Vivado tidak ada di lingkungan ini: instruksi persis untuk user, dan status `[B] perlu dijalankan user`.

### M12 — Software Pi dan harness eksperimen
- [x] Driver, `HwBackend`, `MockBackend`, `camera.py`, `preprocess.py`, dashboard
- [x] Mode validasi sesuai syarat resmi: baca folder gambar (dari kartu SD atau USB), klasifikasi semuanya, laporkan akurasi dan waktu per gambar (latensi dan FPS)
- [x] Mode kamera real-time sesuai syarat resmi: tampilkan kelas dan kecepatan pengenalan
- [x] `experiments/e1.py` sampai `e8.py`; plot dengan watermark untuk backend mock

**DoD:** mode validasi, mode kamera (dengan kamera atau file video pengganti), dan semua skrip e1–e8 jalan dengan MockBackend serta menghasilkan CSV + grafik bertanda SYNTHETIC. Unit test driver dibandingkan dengan log ko-simulasi.

### M13 — Dokumen dan draf laporan
- [x] `docs/ARCHITECTURE.md` (diagram Mermaid), `VERIFICATION.md`, `RESULTS_SIM.md`
- [x] `docs/AI_USAGE.md` (penggunaan AI secara jujur), `THIRD_PARTY.md`
- [x] `docs/REPORT_DRAFT.md` dengan placeholder `[HW-TBD]`, `docs/SLIDES_OUTLINE.md` (10 slide)

**DoD:** setiap angka punya rujukan skrip atau log. Tidak ada klaim hardware.

### M14 — Paket kesiapan board
- [x] `board/BRINGUP.md`: daya → programming → LED berkedip → loopback SPI → baca ID → muat bobot → 1 gambar → validasi penuh di clock aman → baru turbo
- [x] Skrip untuk setiap langkah bring-up
- [x] Top-level board dengan placeholder XDC; skrip build menolak jalan jika BOARD_INFO masih UNKNOWN

**DoD:** dry-run dengan MockBackend lulus.

---

## Fase BOARD (mulai hanya sesuai CLAUDE.md §8)

- [ ] **B1**: XDC dari dokumen resmi ZERO7, F_IN, bitstream, programming
- [ ] **B2**: bring-up langkah demi langkah sesuai BRINGUP.md
- [ ] **B3**: E7 di clock aman (bit-exact seluruh set validasi) [HW]
- [ ] **B4**: E1–E3, sapuan manual [HW]
- [ ] **B5**: E4 (tiga mode), governor otomatis, E6 [HW]
- [ ] **B6**: hasil final, perbarui laporan dan grafik, video demo

---

## Pembaruan ZERO7 (PROMPT_UPDATE_ZERO7, mulai 2026-11-16)

Panitia menerbitkan fakta resmi baru pada 2 dan 10 Nov 2026 (ringkasan dan rujukan di `docs/official/README.md`). Fase tetap PRA-BOARD untuk semua eksperimen `[HW]`; board fisik belum ada.

- [x] **T0** Orientasi: `check` dan `test` penuh
- [x] **T1** Baca dan arsipkan sumber resmi; catatan referensi di `docs/references/`
- [x] **T2** Riset web dan media sosial 15 Okt–15 Nov 2026 (`docs/research/RISET_WEB_2026-11.md`)
- [x] **T3** Cek Vivado dan part; catatan Raspberry Pi di `board/BRINGUP.md`
- [x] **T4** `board/BOARD_INFO.md`, `board/zero7.xdc`, perbarui Terblokir
- [ ] **T5** Review ulang repo (`docs/REVIEW_2026-11.md`)
- [ ] **T6** ADR baru, lalu SPEC
- [ ] **T7** Implementasi; prioritas laporan sintesis resmi XC7S25CSGA225-1
- [ ] **T8** Simulasi juri (`docs/JUDGE_REVIEW.md`)
- [ ] **T9** Revisi materi belajar
- [ ] **T10** Catatan sesi, commit, ringkasan

## Terblokir

Diperbarui 2026-11-16.

- [B] Board fisik ZERO7 — peminjaman sedang diproses. Semua eksperimen `[HW]` (E1–E4, E6, E7 di board) menunggu.
- [B] `Zero7.xdc` resmi, tegangan VCCO, dan IOSTANDARD bank 14/15/34 — belum diterbitkan; `board/zero7.xdc` memakai LVCMOS33 bertanda TODO. Bitstream untuk board tidak boleh dibuat sebelum ini pasti.
- [B] ZERO7 User Manual dan skematik — disebut panitia, belum tertaut di situs.
- [B] Kabel JTAG-HS3 — belum jelas apakah termasuk paket pinjaman.
- [B] Kecepatan SPI nyata, polaritas tombol, rantai WS2812B, boot dari flash QSPI — butuh board atau user manual.
- [B] Kelas target — belum diumumkan panitia (pakai CIFAR-10 sementara).
- [B] `config/mmcm_limits.yaml` dan `config/parts.yaml`: batas DS189/DS180 belum diverifikasi (`verified: false`); butuh PDF datasheet AMD (mengunduhnya perlu izin user).
- [B] Rekonfigurasi MMCM2 di `clk_gen_xilinx.v` (ADR-010): F_IN sekarang diketahui (20 MHz); masih butuh PG065 atau XAPP888.

Sudah tidak terblokir sejak dokumen resmi 10 Nov 2026: part number dan speed grade (xc7s25csga225-1), pin (tabel koneksi), F_IN, cara programming. Yang sekarang bisa dikerjakan tanpa board: XDC, tabel MMCM untuk 20 MHz, top-level board, sintesis dan implementasi di part resmi, dan laporan sintesis resmi.

## Catatan untuk sesi berikutnya

Ditulis di akhir sesi 2026-11-09, paragraf "Posisi" dikoreksi 2026-11-12.

**Posisi:** semua milestone M0–M9, M11–M14 selesai di simulasi dan Vivado OOC. M10 selesai untuk governor dan verifikasi protokol, tapi rekonfigurasi MMCM asli `[B]` (butuh F_IN dan PG065; ADR-010). M11 selesai: matriks 96 run `[VIVADO-STA]`, 48 berhasil di xc7s25/xc7s50 (lihat Temuan M11). Belum ada satu pun hasil `[HW]`.

**Langkah berikutnya:**
1. M11 selesai (lihat Temuan M11). Konfirmasi part dan speed grade ZERO7; jalankan ulang `python tools/run.py ooc --parts <part> --tag final` untuk part itu saja bila berbeda.
2. Verifikasi `config/mmcm_limits.yaml` ke DS189 (nomor halaman) dan `config/parts.yaml` ke DS180, ganti `verified: false`.
3. Implementasi register Clocking Wizard AXI4-Lite di `rtl/platform/xilinx/clk_gen_xilinx.v` sesuai ADR-010.
4. Evaluasi muatan BRAM: estimasi [SIM] model s K=8 = 11,0 BRAM36-eq, melebihi 10 di XC7S15 (kapasitas belum terverifikasi). Jika part-nya XC7S15: pakai xs, atau kurangi buffer (mis. tanpa ping-pong).
5. Setelah BOARD_INFO terisi dan user menulis "board siap": mulai B1 sesuai `board/BRINGUP.md`, dari clock aman.

**Temuan M11 (2026-11-10):**
- Lane `lut` adalah pilihan yang sesuai tujuan proyek: jalur MAC menjadi jalur kritis (Fmax clk_fast sekitar 148–167 MHz di xc7s25/xc7s50), sedangkan suplai operand R·f_safe sekitar 280 MHz, jadi ruang overclock ada.
- Lane DSP lebih cepat secara STA (sekitar 265–336 MHz di K=8), tetapi batasnya adalah FIFO dan suplai operand (R·f_safe), bukan MAC; tidak cocok untuk eksperimen overclock MAC tanpa menaikkan R.
- `dsp_full` dipetakan Vivado ke dua DSP per lane (produk dan akumulator terpisah); K=16 `dsp_min` lambat (jalur DSP tanpa MREG sekitar 5 ns). Perlu ditinjau bila varian DSP dipakai.
- Jika part ternyata xc7s15 atau xc7s6, organisasi memori harus dihemat (kedalaman bukan pangkat dua, tanpa buffer ping-pong, atau model xs) sebelum bisa muat.

**Jebakan yang ditemukan:**
- `verilator` di oss-cad-suite Windows hanya bisa lewat `verilator_bin` + `VERILATOR_ROOT` (sudah ditangani `tools/check_env.py`); tidak ada g++/make sehingga Verilator tidak dipakai untuk simulasi.
- Icarus sekitar 14x lebih lambat dari xsim untuk engine; regresi panjang pakai xsim (Icarus tetap untuk bench pendek). `.bat` Vivado memecah argumen berisi `=`: opsi lewat file `-f`.
- `always @*` tidak peka sinyal yang hanya dibaca di dalam function (membuat X di Icarus). `checker` adalah kata kunci SystemVerilog (ADR-009).
- Uji sintesis pada part xczu3eg (bukan Spartan-7, bukan hasil) menemukan batas `PROG_FULL_THRESH` XPM; sudah diperbaiki. Dataset folder sudah diuji dengan pelatihan satu epoch.
- Di Windows, menulis berkas tepat setelah berkas itu diubah proses lain kadang gagal `OSError: [Errno 22]` (kemungkinan pengawas file); ulangi penulisan. Beberapa heredoc `<<'EOF'` dalam satu perintah bash gagal: pakai satu heredoc per perintah.
- Kampanye RTL (M9) memakai model `micro` berbobot acak karena tiap skenario harus cepat; kampanye model nyata ada di M3 (Python) dan M8 (RTL, xs).

## Log bukti

| Tanggal | Milestone | Perintah | Hasil |
| --- | --- | --- | --- |
| 2026-11-10 | M11 | perbaikan timing ADR-012, putaran v2–v4 di xc7s25csga225-1 | [VIVADO-STA] Fmax clk_safe naik dari sekitar 102 ke 139–148 MHz (K=8) |
| 2026-11-10 | M11 | `python tools/run.py ooc ... --nonmac-factor 0.7` (lut, K=8) | [VIVADO-STA] C3=0: jalur non-MAC lolos 70% periode (slack +0,226 ns), 20 jalur terburuk clk_fast adalah MAC; C3=1 meleset 0,008 ns |
| 2026-11-10 | M11 | `python tools/run.py ooc --parts <8 part> --tag final` | [VIVADO-STA] 48/96 run berhasil (xc7s25, xc7s50); xc7s6 dan xc7s15 tidak muat: BRAM kurang. Tabel di docs/RESULTS_SIM.md |
| 2026-11-10 | M4–M10 | `python tools/run.py sim lane_array checker engine spi system governor --record ...` | [SIM] 37/37 bench lulus setelah perubahan pipeline; s K=8 200/200, xs K=8 200/200, overhead s K=16 9,9% |
| 2026-11-10 | M11 | `python tools/run.py ooc --parts xc7s25csga225-1 --k 8` | [VIVADO-STA] 6 varian selesai; lihat fpga/reports/summary.csv. Domain aman lolos target 10 ns; lane LUT gagal target 5 ns |
| 2026-11-09 | M0 | `python tools/run.py check --write` | Python 3.13.1, Icarus 12.0 devel, Vivado 2025.2 terdeteksi, Verilator 5.053 lint; lihat docs/ENVIRONMENT.md |
| 2026-11-09 | M0 | `python tools/run.py test` | 189 passed (pytest, lint, benches cepat) |
| 2026-11-09 | M1 | `python tools/run.py train --model s` | [SIM] test float 0.8048, seed 2027, 120 epoch; results/model/s/float_result.json |
| 2026-11-09 | M1 | `python tools/run.py train --model xs` | [SIM] test float 0.7290, seed 2027, 120 epoch; results/model/xs/float_result.json |
| 2026-11-09 | M1 | `pytest tests/test_arch_report.py` | angka SPEC §2 dan siklus §5.4 cocok (tidak perlu ADR) |
| 2026-11-09 | M2 | `python tools/run.py export --model s` | [SIM] integer 0.8022 vs float 0.8048, turun 0.26 poin; PTQ per-tensor |
| 2026-11-09 | M2 | `python tools/run.py export --model xs` | [SIM] integer 0.7250 vs float 0.7290, turun 0.40 poin |
| 2026-11-09 | M2 | `export --model s --from-quant` dua kali, `sha256sum build/weights/s_k8.bin` | hash sama: 534f3862cf31b5e8 (dua kali); test_export_is_deterministic lulus |
| 2026-11-09 | M3 | `python tools/run.py campaign --model s` | [SIM] K=8 C3=0: tunggal 10000/10000 terkoreksi, dua lane 9403 recompute dan 597 salah koreksi, checksum lane 1000/1000 recompute; C3=1 dua lane 0 salah koreksi. Tabel lengkap di docs/RESULTS_SIM.md |
| 2026-11-09 | M4 | `python tools/run.py sim lane_array` | lane_array_k8_c1_dsp_full: PASS 5720/5720 (icarus); lane_array_k8_c1_dsp_min: PASS 5720/5720 (icarus); lane_array_k8_c1_lut: PASS 5720/5720 (icarus); lane_array_k16_c0_lut: PASS 9360/9360 (icarus); lane_array_k16_c0_dsp_full: PASS 9360/9360 (icarus); lane_array_k16_c0_dsp_min: PASS 9360/9360 (icarus); lane_array_k16_c1_lut: PASS 9880/9880 (icarus); lane_array_k16_c1_dsp_full: PASS 9880/9880 (icarus); lane_array_k16_c1_dsp_min: PASS 9880/9880 (icarus); lane_array_k8_c0_lut: PASS 101000/101000 (icarus); lane_array_k8_c0_dsp_full: PASS 101000/101000 (icarus); lane_array_k8_c0_dsp_min: PASS 101000/101000 (icarus) |
| 2026-11-09 | M5 | `python tools/run.py sim checker` | checker_k8_c0: PASS 5034/5034 max_latency=11 (icarus); checker_k16_c0: PASS 5050/5050 max_latency=19 (icarus); checker_k8_c1: PASS 10068/10068 max_latency=11 (icarus); checker_k16_c1: PASS 10100/10100 max_latency=19 (icarus) (mencakup semua cabang keputusan; lihat build/vectors/.../meta.json) |
| 2026-11-09 | M6 | `python tools/run.py sim engine_corner_extreme engine_corner_saturate engine_corner_ties engine_corner_zero_lanes engine_s_k16_n20 engine_s_k8_n200 engine_xs_k8_n200` | engine_xs_k8_n200: PASS 200/200 (34/34 cycles_mean=83823 ideal=83456) (xsim); engine_s_k8_n200: PASS 200/200 (34/34 cycles_mean=277871 ideal=277504) (xsim); engine_s_k16_n20: PASS 20/20 (5/5 cycles_mean=150436 ideal=138752) (xsim); engine_corner_zero_lanes: PASS 6/6 cycles_mean=173804 ideal=0 (xsim); engine_corner_extreme: PASS 6/6 cycles_mean=173804 ideal=0 (xsim); engine_corner_ties: PASS 6/6 cycles_mean=173804 ideal=0 (xsim); engine_corner_saturate: PASS 6/6 cycles_mean=173804 ideal=0 (xsim) overhead siklus: s K=8 0,13%, xs K=8 0,44%, s K=16 8,4% [SIM] |
| 2026-11-09 | M7 | `python tools/run.py sim spi_session_xs spi_slave` | spi_session_xs: PASS 224/224 polls=421 (xsim); spi_slave: PASS 19/19 (icarus) (ID, muat bobot, tulis gambar, START, baca kelas/logit/counter, ping-pong IMG0/IMG1); test_generated_files_are_up_to_date lulus |
| 2026-11-09 | M8 | `python tools/run.py sim system_micro_corners system_xs_r100 system_xs_r130 system_xs_r170 system_xs_r200` | system_xs_r100: PASS 8/8 reconfigs=0 (xsim); system_xs_r130: PASS 8/8 reconfigs=0 (xsim); system_xs_r170: PASS 8/8 reconfigs=0 (xsim); system_xs_r200: PASS 8/8 reconfigs=0 (xsim); system_micro_corners: PASS 5/5 reconfigs=0 (xsim) (rasio f_fast/f_safe 1,0/1,3/1,7/2,0; injeksi mode 0/1/2; counter dan FATAL/log penuh cocok dengan model) |
| 2026-11-09 | M9 | `python tools/run.py sim system_micro_campaign_k16_c1 system_micro_campaign_k8_c0 system_micro_campaign_k8_c1` | system_micro_campaign_k8_c0: PASS 2400/2400 reconfigs=0 (xsim); system_micro_campaign_k8_c1: PASS 2400/2400 reconfigs=0 (xsim); system_micro_campaign_k16_c1: PASS 2400/2400 reconfigs=0 (xsim) (7.200 skenario termasuk dua lane dan lane checksum; pakai model micro bobot acak [SIM]) |
| 2026-11-09 | M10 | `python tools/run.py sim governor system_micro_autogov` | governor: PASS 2400/2400 scenarios=60 (icarus); system_micro_autogov: PASS 12/12 reconfigs=8 (xsim) (60 skenario trajektori state; urutan SPEC §7.7 diawasi monitor protokol, 8 rekonfigurasi); pytest tests/test_mmcm_table.py lulus dengan batas belum terverifikasi |
| 2026-11-09 | M11 | `python tools/run.py ooc` | keluar kode 2: Vivado tidak punya device Spartan-7; instruksi tertulis; [B] perlu dijalankan user |
| 2026-11-09 | M12 | `pytest tests/test_software.py`; `python -m sentinel.experiments.e1..e8`; `python tools/run.py plots` | 7 grafik; e1-e4,e6,e7 mock [SYNTHETIC], e5 [SIM], e8 estimasi [SIM] |
| 2026-11-09 | M13 | `python tools/gen_results_doc.py` | docs/RESULTS_SIM.md dari file hasil; dokumen lain ditulis tanpa angka baru |
| 2026-11-09 | M14 | `pytest tests/test_board_package.py`; `python board/bringup.py validate --dry-run` | dry-run lulus; build menolak jalan karena BOARD_INFO UNKNOWN |
| 2026-11-16 | T0 | `python tools/run.py check`; `python tools/run.py test` | semua alat ok (Vivado 2025.2, Icarus 12.0, Verilator 5.053); 190 passed in 227.70s; log `build/test_full_2026-11-16.log` |
| 2026-11-16 | T1 | baca `GUIDE_LSI_2027_FINALE.pdf` (6 hlm), `ZERO7FPGA_Connection-table_261109_001.pdf` (7 hlm), `Initialize_20260618_EN.pdf` (59 slide), `index.html` dan `shiyou_1.html` (Jepang) | tiga PDF diarsipkan ke `docs/official/`, panduan lama ke `superseded/`; `docs/official/README.md` dan tiga catatan `docs/references/` ditulis; PDF Jepang `Initialize_20260618.pdf` belum diarsipkan (menunggu izin unduh) |
| 2026-11-16 | T2 | pencarian web (20 kueri), OpenAlex, API arXiv; halaman panitia Jepang lewat browser | `docs/research/RISET_WEB_2026-11.md`; tidak ada proyek tim lain untuk kontes 2027 yang terlihat publik; teks lengkap Marty dkk. dan Li dkk. belum terbaca (akses ditolak) |
| 2026-11-16 | T3 | `vivado -mode batch -source tools/vivado_check_part.tcl` | status CUKUP: Vivado 2025.2, xc7s25csga225-1 ditemukan; 14600 LUT, 29200 FF, 45 block RAM, 80 DSP, 3 MMCM [VIVADO] (`results/vivado/part_check.txt`); `vivado` tidak ada di PATH; Zynq-7000 tidak terpasang |
| 2026-11-16 | T4 | `vivado -mode batch -source board/pin_check.tcl` | B13 = IO_L13P_T2_MRCC_15, clock-capable; bank 14/15/34 jenis HR [VIVADO] (`results/vivado/pin_check.txt`); `board/BOARD_INFO.md` diisi dari dokumen resmi; `board/zero7.xdc` dibuat |
| 2026-11-16 | T4 | `pytest tests/test_board_package.py` | 8 passed. Test lama yang mewajibkan "Part number" dan "Clock input" masih UNKNOWN diganti (alasan: kedua fakta itu sekarang resmi): logika deteksi diuji dengan fixture, fakta resmi diuji tetap terisi, dan `board/zero7.xdc` diuji terhadap tabel koneksi; guard yang menolak build dan langkah hardware selama masih ada field UNKNOWN tidak diubah |
