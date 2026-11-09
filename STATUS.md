# STATUS — SENTINEL

Terakhir diperbarui: 2026-11-09, dibuat dari starter kit. Belum ada kode.
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
- [ ] Struktur folder sesuai SPEC §17, `.gitignore` (build/, dataset, checkpoint besar), `git init`, `README.md` (English)
- [ ] `requirements.txt` (numpy, torch, torchvision, pyyaml, pytest, hypothesis, matplotlib; opsional: opencv-python, flask; khusus Pi: spidev, picamera2)
- [ ] `tools/check_env.py`: deteksi dan cetak versi Python, torch, numpy, pytest, iverilog/vvp, verilator, vivado/xvlog/xsim
- [ ] `tools/run.py` dengan subcommand: check, test, gen, train, export, sim, campaign, ooc, plots
- [ ] `docs/ENVIRONMENT.md` berisi versi alat yang benar-benar terdeteksi

**DoD:** `python tools/run.py check` dan `python tools/run.py test` berjalan di mesin ini (test boleh sedikit, tapi lulus). ENVIRONMENT.md terisi dari output check.

### M1 — Model float
- [ ] `config/model_s.yaml`, `config/model_xs.yaml`; `model/arch.py` membangun model dari config
- [ ] `model/arch_report.py`: jumlah parameter, MAC, dan siklus per K
- [ ] `model/train.py`: CIFAR-10, seed tetap, augmentasi ringan, simpan checkpoint dan log
- [ ] Dukung dataset folder (format ImageFolder) dan N_CLASSES bebas, supaya bisa langsung dilatih ulang saat panitia mengumumkan kelas target

**DoD:** arch_report cocok dengan SPEC §2 (kalau tidak, perbaiki SPEC lewat ADR). Akurasi float varian s dan xs tercatat di `results/model/` beserta seed.

### M2 — Kuantisasi, golden model, ekspor
- [ ] `model/quant.py`: fold BN, PTQ, opsi QAT
- [ ] `model/golden.py`: SPEC §3 persis, NumPy int64
- [ ] `model/export.py`: `.bin` + `manifest.json` + `.mem` + bound check (SPEC §3.6)
- [ ] Test L0: requant (pembulatan .5, negatif, saturasi, n = 0), padding, flatten, argmax seri, batas bit

**DoD:** akurasi integer tercatat. Target penurunan ≤ 2 poin dari float; jika tidak tercapai, tulis ADR dan langkah perbaikannya. Semua test L0 hijau. Ekspor deterministik (hash sama jika dijalankan dua kali).

### M3 — Checker model dan kampanye fault (Python)
- [ ] `model/checker.py` (SPEC §6.2 dan §11.2), `model/fault_model.py` (§11.3), `model/campaign.py`
- [ ] Property test untuk tabel keputusan (hypothesis jika tersedia)
- [ ] Kampanye untuk K ∈ {8, 16} dan C3 ∈ {0, 1}: 10.000 error satu lane, 10.000 dua lane, 1.000 di lane checksum. Injeksi pada akumulator nyata dari golden model (layer nyata, gambar nyata).

**DoD:** 100% error satu lane terkoreksi. Tabel laju (clean, corrected, csum_lane, recompute, salah koreksi, lolos) ada di `docs/RESULTS_SIM.md` dengan label [SIM]. Rekomendasi soal C3 ditulis sebagai ADR.

### M4 — RTL lane dan lane array
- [ ] `rtl/lane_lut.v`, `rtl/lane_dsp_min.v`, `rtl/lane_dsp_full.v`
- [ ] `rtl/lane_array.v`: K lane data + 2/3 lane checksum, register holding, serializer
- [ ] Testbench dengan vektor golden: ≥ 10.000 unit acak + ≥ 100 tile nyata

**DoD:** bit-exact untuk semua LANE_IMPL. Lint Verilator bersih (jika tersedia).

### M5 — RTL checker dan korektor
- [ ] `rtl/lane_checker.v` (ADR-009) sesuai SPEC §6.2: mode 0/1/2, C3_EN, TRUST_CSUM_LANE, pencarian j tanpa pembagi

**DoD:** bit-exact terhadap `model/checker.py` pada ≥ 2.000 kasus dari M3, mencakup setiap cabang keputusan.

### M6 — RTL engine satu clock
- [ ] Generator operand (alamat, padding, wc on-the-fly), kontrol layer berbasis tabel layer
- [ ] Post-processing (SPEC §3.3), pooling, FC, argmax, buffer aktivasi

**DoD:** logit dan kelas bit-exact untuk ≥ 200 gambar (varian s dan xs). Siklus nyata dibanding model ≤ 10% overhead. Semua kasus sudut SPEC §13.4 diuji.

### M7 — Antarmuka host
- [ ] `spec/regmap.yaml` + `tools/gen_regmap.py` → `rtl/gen/` dan `sw/sentinel/regmap.py`
- [ ] `rtl/spi_slave.v`, register file, muat bobot lewat SPI, buffer gambar ping-pong
- [ ] Driver Python + `LogTransport`; testbench memutar ulang log transaksi

**DoD:** transaksi lengkap (ID → muat bobot → tulis gambar → START → baca kelas, logit, counter) bit-exact di simulasi. Ada test yang memastikan file hasil generate selalu terbaru.

### M8 — Dua domain clock, mode, recompute
- [ ] `rtl/platform/*/cdc_fifo` (XPM dan behavioral), `clk_gen` (sim dan Xilinx)
- [ ] Suplai operand R, pemilihan clock per layer, recompute pass + log, mode 0/1/2, counter STARVE
- [ ] Opsional: bit paritas operand

**DoD:** bit-exact end-to-end untuk rasio f_fast/f_safe ∈ {1,0; 1,3; 1,7; 2,0}. Dengan injeksi satu lane: mode 2 bit-exact, mode 1 bit-exact lewat recompute, mode 0 menunjukkan mismatch sesuai prediksi. Counter cocok dengan model.

### M9 — Injeksi hardware dan kampanye RTL
- [ ] Register INJ0/INJ1 (SPEC §11.1)
- [ ] Skrip kampanye RTL: ≥ 2.000 injeksi, termasuk dua lane

**DoD:** outcome RTL 100% sama dengan prediksi model Python. Hasil masuk `docs/RESULTS_SIM.md` dengan label [SIM].

### M10 — Governor dan rekonfigurasi clock
- [ ] `model/governor.py`, `rtl/governor.v`
- [ ] Rekonfigurasi MMCM2: Clocking Wizard via AXI-Lite (PG065) atau DRP (XAPP888). Pilih lewat ADR.
- [ ] `tools/gen_mmcm_table.py`: batas dari DS189 dengan kutipan halaman; F_IN berupa placeholder
- [ ] Testbench ≥ 50 skenario dengan event dari fault model sintetis

**DoD:** trajektori state RTL sama dengan model untuk semua skenario. Urutan SPEC §7.7 terverifikasi di simulasi. Tabel MMCM lolos test batas.

### M11 — Vivado out-of-context
- [ ] `fpga/ooc.tcl`, `fpga/run_matrix.py` (matriks varian), parser laporan ke CSV
- [ ] `tools/fit_report.py` (estimasi BRAM dan DSP per part dari config)

**DoD:** tabel resource dan Fmax [VIVADO-STA] per part dan varian di `docs/RESULTS_SIM.md`. Analisis jalur kritis sesuai SPEC §7.4. Jika Vivado tidak ada di lingkungan ini: instruksi persis untuk user, dan status `[B] perlu dijalankan user`.

### M12 — Software Pi dan harness eksperimen
- [ ] Driver, `HwBackend`, `MockBackend`, `camera.py`, `preprocess.py`, dashboard
- [ ] Mode validasi sesuai syarat resmi: baca folder gambar (dari kartu SD atau USB), klasifikasi semuanya, laporkan akurasi dan waktu per gambar (latensi dan FPS)
- [ ] Mode kamera real-time sesuai syarat resmi: tampilkan kelas dan kecepatan pengenalan
- [ ] `experiments/e1.py` sampai `e8.py`; plot dengan watermark untuk backend mock

**DoD:** mode validasi, mode kamera (dengan kamera atau file video pengganti), dan semua skrip e1–e8 jalan dengan MockBackend serta menghasilkan CSV + grafik bertanda SYNTHETIC. Unit test driver dibandingkan dengan log ko-simulasi.

### M13 — Dokumen dan draf laporan
- [ ] `docs/ARCHITECTURE.md` (diagram Mermaid), `VERIFICATION.md`, `RESULTS_SIM.md`
- [ ] `docs/AI_USAGE.md` (penggunaan AI secara jujur), `THIRD_PARTY.md`
- [ ] `docs/REPORT_DRAFT.md` dengan placeholder `[HW-TBD]`, `docs/SLIDES_OUTLINE.md` (10 slide)

**DoD:** setiap angka punya rujukan skrip atau log. Tidak ada klaim hardware.

### M14 — Paket kesiapan board
- [ ] `board/BRINGUP.md`: daya → programming → LED berkedip → loopback SPI → baca ID → muat bobot → 1 gambar → validasi penuh di clock aman → baru turbo
- [ ] Skrip untuk setiap langkah bring-up
- [ ] Top-level board dengan placeholder XDC; skrip build menolak jalan jika BOARD_INFO masih UNKNOWN

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

## Catatan untuk sesi berikutnya

(kosong; diisi di akhir setiap sesi)

## Log bukti

| Tanggal | Milestone | Perintah | Hasil |
| --- | --- | --- | --- |
