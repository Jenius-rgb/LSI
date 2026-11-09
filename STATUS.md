# STATUS — SENTINEL

Terakhir diperbarui: 2026-11-09, akhir sesi pertama (pra-board).
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

**Status:** `[B]` perlu dijalankan user: skrip dan `fit_report` selesai; Vivado butuh dukungan device Spartan-7 (lihat Terblokir).

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

## Terblokir

- [B] Part number, package, speed grade ZERO7 — belum dipublikasikan panitia
- [B] XDC/pin, F_IN, metode programming — butuh dokumen board
- [B] Kecepatan SPI nyata, antarmuka LED RGB, XADC — butuh board
- [B] Semua eksperimen [HW] — butuh board
- [B] Kelas target — belum diumumkan panitia (pakai CIFAR-10 sementara)

- [B] Dukungan device Spartan-7 belum ada di Vivado 2025.2 (`get_parts xc7s*` kosong): M11 perlu dijalankan user setelah menambah device lewat Help > Add Design Tools or Devices, lalu `python tools/run.py ooc`
- [B] `config/mmcm_limits.yaml` dan `config/parts.yaml`: angka batas DS189/DS180 belum diverifikasi (`verified: false`); butuh dokumen resmi
- [B] Rekonfigurasi MMCM2 di `clk_gen_xilinx.v` (ADR-010): butuh Spartan-7 di Vivado, F_IN, dan PG065

## Catatan untuk sesi berikutnya

Ditulis di akhir sesi 2026-11-09.

**Posisi:** semua milestone M0–M9, M12–M14 selesai di simulasi. M10 selesai untuk governor dan verifikasi protokol, tapi rekonfigurasi MMCM asli `[B]` (butuh dukungan device, F_IN, PG065; ADR-010). M11 menunggu dukungan device Spartan-7 di Vivado (`[B]`, langkah di bawah). Tidak ada satu pun hasil `[HW]` atau `[VIVADO-STA]` Spartan-7.

**Langkah berikutnya:**
1. Setelah user memasang device Spartan-7 di Vivado: `python tools/run.py ooc`, lalu `python fpga/parse_reports.py`, `python tools/gen_results_doc.py`, lanjut analisis jalur kritis (SPEC §7.4) dan isi E8.
2. Verifikasi `config/mmcm_limits.yaml` ke DS189 (nomor halaman) dan `config/parts.yaml` ke DS180, ganti `verified: false`.
3. Implementasi register Clocking Wizard AXI4-Lite di `rtl/platform/xilinx/clk_gen_xilinx.v` sesuai ADR-010.
4. Evaluasi muatan BRAM: estimasi [SIM] model s K=8 = 11,0 BRAM36-eq, melebihi 10 di XC7S15 (kapasitas belum terverifikasi). Jika part-nya XC7S15: pakai xs, atau kurangi buffer (mis. tanpa ping-pong).
5. Setelah BOARD_INFO terisi dan user menulis "board siap": mulai B1 sesuai `board/BRINGUP.md`, dari clock aman.

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
