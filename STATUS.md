# STATUS — SENTINEL

Terakhir diperbarui: 2026-11-16 malam, sesi pembaruan ZERO7 sesudah jawaban user (pra-board).
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
- [x] Rekonfigurasi MMCM2 di RTL: Clocking Wizard dengan AXI4-Lite dan `clkwiz_seq` (ADR-023, M21; dikoreksi 2026-11-16, butir ini sebelumnya masih `[B]`). Bukti di hardware menunggu board (M21, B4)
- [x] `tools/gen_mmcm_table.py` dengan batas DS189 terverifikasi (Tabel 37, PDF hlm. 40) dan F_IN = 20 MHz [OFFICIAL] (ADR-015, ADR-023)
- [x] Testbench ≥ 50 skenario dengan event dari fault model sintetis

**Status:** `[x]` untuk semua bagian tanpa board: governor, protokol, rekonfigurasi MMCM2 di RTL, dan batas DS189. Rekonfigurasi sungguhan diukur di board (B4).

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
- [x] **T5** Review ulang repo (`docs/REVIEW_2026-11.md`)
- [x] **T6** ADR baru, lalu SPEC
- [x] **T7** Implementasi; prioritas laporan sintesis resmi XC7S25CSGA225-1 — semua bagian tanpa board dari M15 sampai M21 selesai; sisanya butuh board (lihat "Belum dikerjakan")
- [x] **T8** Simulasi juri (`docs/JUDGE_REVIEW.md`), tiga putaran
- [x] **T9** Revisi materi belajar ke versi 1.1 (sumber di `tools/study_guide/`, hasil di `build/study_guide/`)
- [x] **T10** Catatan sesi, commit, ringkasan

### Milestone baru dari ADR-013 sampai ADR-021

- **M15 — Laporan sintesis resmi XC7S25CSGA225-1 (ADR-013, ADR-014, ADR-015, ADR-016)**
  - [x] `config/hw_zero7.yaml` (varian resmi: s, K = 8, R = 2, lut, C3 = 1)
  - [x] `clk_gen_xilinx` untuk input 20 MHz; `top_board` dengan port ADR-016; `board/zero7.xdc` mengikuti
  - [x] `fpga/synth_official.tcl` dan `python tools/run.py synth-official`
  - [x] laporan di `results/vivado/official/` dan ringkasan [VIVADO-STA] di `docs/RESULTS_SIM.md`
  - Hasil [VIVADO-STA]: f_safe = 125 MHz (ADR-015), 6.170 dari 14.600 LUT, WNS desain +0,417 ns. Format laporan yang diminta panitia masih [UNKNOWN].
  - Definition of Done: implementasi selesai tanpa error; semua resource di bawah kapasitas part; WNS `clk_safe` ≥ 0 pada f_safe yang dipilih; laporan utilisasi, timing, daya, DRC, dan metodologi tersimpan; setiap angka bisa dilacak ke file laporan.
- **M16 — Regresi varian resmi di simulasi**
  - [x] engine model `s`, K = 8, C3 = 1 bit-exact terhadap golden model untuk ≥ 200 gambar [SIM] (`engine_s_k8_c1_n200`)
  - [x] sistem dua clock dengan varian resmi (`system_s_k8_c1`, C3 dipakai, termasuk injeksi dua lane)
- **M17 — Indikator WS2812B (ADR-017)**
  - [x] `rtl/ws2812_tx.v` dengan testbench lebar pulsa; encoder status (`rtl/status_led.v`); port `ws2812_dout` di `top_board`, pin N1
  - [B] waktu pulsa dicek ke datasheet LED di ZERO7 (jenis LED dan datasheet belum ada)
- **M18 — Suhu XADC (ADR-018)**
  - [x] `rtl/xadc_temp.v`, `rtl/platform/xilinx/xadc_prim_xilinx.v` (setelan UG480), model `rtl/platform/sim/xadc_prim_sim.v`; register `TEMP`; `sentinel.xadc` (UG480 Pers. 2-6)
  - [B] kolom suhu di harness E6 dengan pembacaan nyata (butuh board)
- **M19 — Sinyal selesai dan tombol (ADR-016)**
  - [x] `irq_done` di RTL (`top_board`) dan di driver (`SentinelDriver(done_line=...)`, `GpioDoneLine`; kelas GPIO belum pernah dijalankan di Pi)
  - [x] `board/bringup.py` memakai done line di board; mode kamera mengikuti tombol START/STOP/RUN (`--buttons`)
  - [B] polaritas tombol diukur di board
- **M20 — Aturan penyeberangan domain clock (ADR-021)**
  - [x] synchronizer bertanda `ASYNC_REG`; satu synchronizer per sumber reset asinkron; LOCKED MMCM2 disinkronkan
  - [x] false path reset power-on; `report_cdc` dan `report_bus_skew` di alur resmi; SPEC §7.8
  - [x] penjagaan di `regfile`: tulis `INJ*` selama BUSY dibuang (`tb_regfile_guard`)
  - [x] status mux dilaporkan sesudah jeda tetap di `clk_gen_xilinx`
- **M21 — Rekonfigurasi MMCM2 lewat Clocking Wizard (ADR-023, menutup ADR-010)**
  - [x] tabel level ke `rtl/gen/mmcm_turbo_table.vh` (aturan: tepat, M dan O bulat, VCO tertinggi); test kesegaran
  - [x] `rtl/clkwiz_seq.v` (master AXI4-Lite, urutan PG065) dengan `tb_clkwiz_seq` dan model register perilaku
  - [x] `clk_wiz_turbo` dibangkitkan di `fpga/synth_official.tcl`; `clk_gen_xilinx` memakainya
  - [B] rekonfigurasi sungguhan diukur di board (B4)
- [B] Boot dari flash QSPI (ADR-019): menunggu jenis flash dan posisi DIP SW7.

## Info tim, 17 Nov 2026

Belum dari dokumen resmi:
1. Kabel JTAG-HS3 diberikan satu set dengan board ZERO7 (menggantikan butir terblokir "apakah kabel termasuk paket pinjaman").
2. Setiap kelompok memakai Raspberry Pi 4 milik sendiri; kompatibilitas Pi 4 dengan ZERO7 [UNKNOWN] sampai panitia menjawab.
3. ZERO7 dan JTAG-HS3 tersedia mulai 20 Nov 2026; Raspberry Pi 4 mungkin datang lebih lambat.

PROMPT_UPDATE_ZERO7 dari sesi sebelumnya sudah selesai (T0–T10 `[x]`); tidak ada tahap yang tersisa. Sesi 17 Nov 2026 mengerjakan PROMPT_PARHI_KAMERA_TANPA_PI.

## Terblokir

Diperbarui 2026-11-16.

- [B] Board fisik ZERO7 dan Raspberry Pi 4 — dipakai mulai Desember 2026 atau Januari 2027 [USER]. Semua eksperimen `[HW]` (E1–E4, E6, E7 di board) menunggu.
- [B] `Zero7.xdc` resmi, tegangan VCCO, dan IOSTANDARD bank 14/15/34 — belum diterbitkan; `board/zero7.xdc` memakai LVCMOS33 bertanda TODO. Bitstream untuk board tidak boleh dibuat sebelum ini pasti.
- [B] ZERO7 User Manual dan skematik — disebut panitia, belum tertaut di situs.
- [B] Kompatibilitas Pi 4 dengan ZERO7 menunggu konfirmasi panitia. (info tim, 17 Nov 2026: setiap kelompok memakai Pi 4 sendiri; panitia belum memastikan.)
- [B] Daya ZERO7 tanpa Raspberry Pi — dokumen resmi hanya menyebut daya dari header GPIO Pi (IN-41); cara lain [UNKNOWN], tanyakan ke panitia. Tanpa daya, langkah tanpa Pi tidak bisa dimulai.
- [B] Kecepatan SPI nyata, polaritas tombol, rantai WS2812B, boot dari flash QSPI — butuh board atau user manual.
- [B] Kelas target — belum diumumkan panitia (pakai CIFAR-10 sementara).
- [B] Format laporan sintesis resmi — belum dijelaskan panitia; sementara berupa file `.rpt` Vivado dan `summary.md` di `results/vivado/official/`.
- [B] Teks lengkap Li dkk. (ITC-Asia 2019): user tidak menemukannya; klaim tentang pemulihan memakai kata "sejauh penelusuran kami".

Sudah tidak terblokir sejak dokumen resmi 10 Nov 2026: part number dan speed grade (xc7s25csga225-1), pin (tabel koneksi), F_IN, cara programming. Yang sekarang bisa dikerjakan tanpa board: XDC, tabel MMCM untuk 20 MHz, top-level board, sintesis dan implementasi di part resmi, dan laporan sintesis resmi.

## Catatan untuk sesi berikutnya

Ditulis 2026-11-16 malam, sesudah jawaban user atas pertanyaan sesi.

**Posisi:** PROMPT_UPDATE_ZERO7 Tahap 0 sampai 10 selesai. Semua pekerjaan yang bisa dilakukan tanpa board sudah dikerjakan dan diuji di simulasi; yang tersisa butuh board, data panitia, atau keputusan user (lihat "Belum dikerjakan" di bawah). Desain lengkap, termasuk Clocking Wizard, XADC, dan WS2812B, muat dan lolos timing di xc7s25csga225-1 pada clk_safe 125 MHz [VIVADO-STA]. Belum ada hasil `[HW]`. Fase tetap PRA-BOARD.

**Untuk melanjutkan:** perintah "lanjutkan PROMPT_UPDATE_ZERO7 dari tahap terakhir di STATUS.md" berarti: tidak ada tahap prompt yang tersisa; kerjakan butir terbuka di bawah sesuai urutan, lalu fase board sesudah user menulis "board siap".

**Belum dikerjakan dan alasannya:**
1. Bitstream untuk board: standar I/O masih [INFERENCE] (ADR-024); tegangan VCCO diukur dulu di langkah bring-up 1. Pemeriksaan bitstream kering sudah lolos (lihat Log bukti).
2. Rekonfigurasi MMCM2, suhu XADC, WS2812B, tombol, done line: RTL dan perangkat lunak selesai dan diuji dengan model; perilaku perangkat AMD dan board hanya bisa dibuktikan di board.
3. Waktu pulsa WS2812B: jenis LED dan datasheet di ZERO7 belum diketahui.
4. Kelas target dan format laporan sintesis: menunggu panitia (user akan mengirim).
5. Li dkk. (ITC-Asia 2019): teks lengkap tidak ditemukan.
6. Draf laporan akhir dan slide (`docs/REPORT_DRAFT.md`, `docs/SLIDES_OUTLINE.md`): butuh angka `[HW]`; struktur sudah ada.

**Tahapan yang butuh board (fase BOARD, `board/BRINGUP.md`):**
1. B1: pasang ZERO7 di Pi 4, ukur arus 5 V dan tegangan VCCO bank 14, 15, 34; `board/pi_check.py`; isi field `UNKNOWN` di `board/BOARD_INFO.md`.
2. Hapus tanda TODO di `board/zero7.xdc` bila tegangan cocok, lalu `board/build_bitstream.py`; program lewat JTAG.
3. B2: SPI loopback, `ID`, unggah bobot; ukur kecepatan SPI tertinggi yang stabil (mulai 1 MHz, batas desain 15,6 MHz).
4. B3 (E7): bit-exact di clock aman untuk seluruh set validasi.
5. Cek rekonfigurasi MMCM2 per level, warna WS2812B, polaritas tombol, pembacaan suhu.
6. B4 (E1–E3): sapuan frekuensi, uji H1; B5 (E4, E6): tiga mode, governor otomatis, suhu; B6: hasil final, laporan, video demo.

**Langkah berikutnya tanpa board (bila ada waktu):**
1. Draf laporan akhir dan 10 slide dengan angka `[SIM]` dan `[VIVADO-STA]` yang sudah ada, bertanda jelas.
2. Latih ulang begitu kelas target diumumkan; ulangi regresi, laporan resmi, dan materi belajar.
3. Setiap kali RTL berubah: `python tools/run.py synth-official`, `vivado -mode batch -source fpga/bitstream_dryrun.tcl`, `python tools/gen_results_doc.py`.

**Jebakan yang ditemukan (tambahan):**
- Di heredoc Git Bash, `\n` di dalam string Python menjadi baris baru sungguhan; perbaiki dengan `chr(92)` atau tulis file lewat alat tulis.
- `before` adalah kata kunci SystemVerilog (iverilog -g2012); `always @*` tanpa perubahan input tidak dievaluasi Icarus di waktu 0, jadi pakai `assign` untuk logika kombinasional sederhana.
- Nama register synchronizer dipakai constraint (`*por_meta_reg[0]`, `*axi_rst_meta_reg[0]`); ganti nama berarti ganti constraint dan test.
- `report_cdc` menolak dua bentuk reset: logika di depan synchronizer (CDC-10) dan satu flop ke dua synchronizer di clock yang sama (CDC-11). `tests/test_fpga_scripts.py::test_committed_official_report_is_clean` sekarang menjaga laporan resmi yang di-commit.
- Clocking Wizard dibangkitkan ulang setiap run resmi di `build/ip_official/`; tidak ada sumber IP yang di-commit.
- PDF AMD di `docs/vendor/` tidak di-commit (syarat redistribusi); checksum ada di `docs/vendor/README.md`.

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
| 2026-11-16 | T5 | pencarian teks terarah di seluruh repo | `docs/REVIEW_2026-11.md`: 20 temuan, masing-masing dengan tindak lanjut |
| 2026-11-16 | T6 | ADR-013 sampai ADR-020 di `docs/DECISIONS.md`; SPEC §1, §2, §7.6, §12.1, §12.4, §14, §18 diperbarui | target dikunci ke xc7s25csga225-1; varian resmi K=8, lut, C3=1; milestone M15–M19 ditambahkan |
| 2026-11-16 | M15 | `python tools/run.py synth-official` di commit 7a2d369 (disimpan sebagai `results/vivado/official_preadr021/`) | [VIVADO-STA] desain lengkap muat: 6.172 LUT, 14 dari 45 block RAM, semua net ter-route; jalur dalam satu clock lolos di 125 MHz (+0,286 ns `clk_safe`, +0,204 ns `clk_fast`); satu jalur antar-clock gagal −0,499 ns (reset power-on dari `clk_in`) |
| 2026-11-16 | M20 | ADR-021; `pytest tests/test_fpga_scripts.py` | test ditulis dulu (gagal), lalu RTL, constraint, dan alur laporan diubah; 16 passed |
| 2026-11-16 | M20 | `python tools/run.py synth-official` (run antara, `results/vivado/official_adr021a/`) | [VIVADO-STA] lolos timing (WNS +0,326 ns), tetapi `report_cdc` memberi CDC-10 pada synchronizer reset; struktur reset diubah menjadi satu synchronizer per sumber |
| 2026-11-16 | M15 | `python tools/run.py synth-official` (final, `results/vivado/official/`) | [VIVADO-STA] clk_safe 125 MHz: 6.170/14.600 LUT (42,26%), 5.704 FF, 14/45 block RAM, 3 DSP; WNS desain +0,417 ns, WHS +0,037 ns, 0 net belum ter-route; Fmax dalam clock 131,9 MHz (`clk_safe`) dan 133,0 MHz (`clk_fast`); CDC: CDC-1 760, CDC-3 40, CDC-4 2, CDC-15 784, tanpa unsafe; bus skew 16 constraint, slack terburuk +6,962 ns; daya 0,505 W (estimasi) |
| 2026-11-16 | M16 | `python tools/run.py sim <semua bench> --record results/sim/rtl_regression.jsonl` pada RTL final | [SIM] 40 bench dicatat ulang, semuanya lulus; varian resmi: `PASS 200/200 (34/34 cycles_mean=277895 ideal=277504)`; sistem dua clock `PASS 10/10 reconfigs=0` |
| 2026-11-16 | M16 | `pytest tests/test_sim_runner.py`; `python tools/run.py sim system_xs_r200 --record results/sim/rtl_regression.jsonl` | penulis catatan diperbaiki (test dulu); bench direkam ulang: `PASS 8/8 reconfigs=0` tertanggal 2026-11-16 |
| 2026-11-16 | M15–M20 | `python tools/run.py test` pada RTL final | 206 passed in 293.53s (0:04:53); log `build/test_full_final.log` |
| 2026-11-16 | M15 | `python tools/gen_results_doc.py` | `docs/RESULTS_SIM.md` memuat laporan resmi [VIVADO-STA] dan anggaran latensi [SIM] × [VIVADO-STA] |
| 2026-11-16 | M19 | `pytest tests/test_software.py` | 13 passed; driver menunggu `irq_done` lewat done line lalu memeriksa `STATUS.DONE`; test memakai pengganti, bukan GPIO sungguhan |
| 2026-11-16 | T8 | `docs/JUDGE_REVIEW.md` | tiga putaran dengan rubrik internal [PROPOSAL]; kelemahan terbesar: belum ada hasil [HW] dan sequencer MMCM2 belum ada |
| 2026-11-16 | T9 | `python tools/study_guide/figures.py`; `build_docx.py`; `finalize_word.ps1` | materi belajar versi 1.1 dengan bagian "Perubahan" di awal; `build/study_guide/SENTINEL_materi_belajar.pdf`, 46 halaman (folder `build/` tidak di-commit) |
| 2026-11-16 | ADR-023 | baca DS189 Tabel 37 (PDF hlm. 40), DS180 Tabel 2 (hlm. 2), UG480 v1.11, PG065; `pytest tests/test_mmcm_table.py` | batas dan kapasitas `verified: true` dengan halaman; nilai −2 input/keluaran maksimum dikoreksi 933 → 800 MHz; test lama yang mewajibkan `verified: false` diganti (alasan: datasheet sudah dicek) |
| 2026-11-16 | PRIOR_ART | baca penuh Marty dkk. TCAD 2020 (14 hlm.), Xue dkk. arXiv 2202.08675 (7 hlm.), Jiang dkk. arXiv 2505.13461 (19 hlm.) | jawaban atas tiga alasan Marty dkk. menolak koreksi di `docs/PRIOR_ART.md` |
| 2026-11-16 | M17–M21 | `python tools/run.py sim xadc_temp regfile_guard ws2812_tx status_led clkwiz_seq` | [SIM] `PASS 4/4 reads=6`, `PASS 6/6`, `PASS 49/49`, `PASS 7/7 frames=10`, `PASS 49/49` |
| 2026-11-16 | M15 | `python tools/run.py synth-official` (dengan Clocking Wizard, XADC, WS2812B) | [VIVADO-STA] 6.862/14.600 LUT (47,00%), 6.154 FF, 14/45 block RAM, 3 DSP; WNS +0,648 ns, WHS +0,040 ns; daya 0,510 W (estimasi) |
| 2026-11-16 | ADR-024 | `vivado -mode batch -source fpga/bitstream_dryrun.tcl` | [VIVADO] `write_bitstream` lolos (Bitgen Completed Successfully); DRC bitstream: 0 error, 1 warning (RTSTAT-10); file `build/bitstream_dryrun/top_board_DRYRUN_NOT_FOR_BOARD.bit`, tidak dipakai di board dan tidak di-commit |
| 2026-11-16 | semua | `python tools/run.py sim <semua bench> --record ...`; `python tools/run.py test` | [SIM] 45 bench, semuanya lulus; 224 passed in 303.17s (0:05:03); log `build/test_full_partb.log` |
| 2026-11-16 | T9 | `python tools/study_guide/figures.py`; `build_docx.py`; `finalize_word.ps1` | materi belajar 1.1 dibangun ulang dengan Pi 4, ADR-022 sampai ADR-024, dan laporan resmi terbaru; 46 halaman (`build/`, tidak di-commit) |
