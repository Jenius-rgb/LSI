# Architecture Decision Records

Format per keputusan: konteks, keputusan, konsekuensi, status. Keputusan baru ditambahkan di bawah dengan nomor berikutnya. Keputusan lama tidak dihapus; tandai "Digantikan oleh ADR-xxx".

ADR-001 sampai ADR-007 adalah usulan awal dari starter kit (2026-11-09). Boleh direvisi lewat ADR baru, dengan alasan tertulis.

---

## ADR-001 — Dataflow output-stationary, lane per output channel
- **Konteks:** identitas checksum Σ_k W_k ∗ X = (Σ_k W_k) ∗ X berlaku jika semua lane memakai input X yang sama.
- **Keputusan:** K lane memproses K output channel berbeda untuk posisi output yang sama. Aktivasi di-broadcast ke semua lane.
- **Konsekuensi:** checksum langsung berlaku pada akumulator. Tidak perlu buffer reuse. Bandwidth memori K+1 byte per operand set.
- **Status:** Diterima (usulan awal).

## ADR-002 — Bobot checksum dihitung on-the-fly di domain aman
- **Konteks:** menyimpan wc1/wc2 di BRAM menambah memori sekitar 50% untuk K = 8, padahal BRAM Spartan-7 kecil sangat terbatas.
- **Keputusan:** wc1, wc2, dan wc3 dihitung dari K bobot yang sedang diambil, di domain aman, sebelum masuk FIFO operand.
- **Konsekuensi:** tidak ada BRAM tambahan. Error pada bobot lane data setelah keluar dari domain aman tetap terdeteksi. Biayanya pohon penjumlah kecil sebanyak R salinan.
- **Status:** Diterima (usulan awal).

## ADR-003 — Unit recompute = jendela pool × grup, ditunda ke akhir layer
- **Konteks:** mengganti clock per tile itu rumit. Pooling on-the-fly membutuhkan 4 posisi yang benar.
- **Keputusan:** unit yang gagal dicatat di log. Setelah layer selesai, clock dipindah ke aman dan unit di log dihitung ulang, termasuk pooling-nya.
- **Konsekuensi:** clock hanya berpindah di batas layer. Butuh log berkapasitas N_LOG; jika penuh, seluruh layer diulang.
- **Status:** Diterima (usulan awal).

## ADR-004 — Suplai operand R per siklus clk_safe
- **Konteks:** jika memori di domain aman hanya memberi 1 operand set per siklus clk_safe, overclocking lane tidak menambah throughput.
- **Keputusan:** domain aman menghasilkan R operand set per siklus (default R = 2), dengan syarat R · f_safe ≥ f_turbo_max.
- **Konsekuensi:** lebar baca BRAM bertambah. Counter STARVE mengukur kelaparan lane.
- **Status:** Diterima (usulan awal).

## ADR-005 — Kebijakan konservatif untuk error di lane checksum
- **Konteks:** tanpa C3, pola d1 ≠ 0 dan d2 = 0 bisa berasal dari error lane C1 atau dari error multi-lane yang saling meniadakan.
- **Keputusan:** default `TRUST_CSUM_LANE = 0`, sehingga kasus ambigu dihitung ulang.
- **Konsekuensi:** sedikit lebih banyak recompute, tetapi tidak ada data rusak yang lolos dari kasus ini. Evaluasi ulang setelah M3.
- **Status:** Diterima (usulan awal).

## ADR-006 — Requant dengan M (uint16) dan shift n per layer
- **Konteks:** requant shift-saja lebih murah, tetapi berisiko menurunkan akurasi.
- **Keputusan:** mulai dengan M dan n per layer (per-tensor). Per-channel hanya jika akurasi turun lebih dari 2 poin.
- **Konsekuensi:** satu pengali 32×16 di domain aman. Biayanya kecil karena laju output rendah.
- **Status:** Diterima (usulan awal).

## ADR-007 — Simulator dan alur lintas platform
- **Konteks:** pengguna memakai Vivado 2025.2. Sistem operasinya bisa Windows atau Linux. Verilator sulit dipasang di Windows.
- **Keputusan:** Icarus Verilog sebagai simulator utama, xsim sebagai referensi (XPM, unisim), Verilator untuk lint jika tersedia. Semua perintah lewat `tools/run.py`.
- **Konsekuensi:** RTL dibatasi pada subset Verilog-2005 yang portabel. Primitif Xilinx dibungkus dan punya model simulasi.
- **Status:** Diterima (usulan awal).

## ADR-008 — Lebar aritmetika komparator dan urutan serialisasi
- **Konteks:** pseudo-code SPEC §6.2 memakai bilangan bulat tak terbatas, tetapi SPEC §1 menyatakan d1/d2/d3 selebar `ACC_CS_W` bit. Error pada bit atas lane checksum dapat membuat j·d1 melewati 48 bit, sehingga RTL dan model bisa berbeda. Pemeriksaan overflow SPEC §6.4 juga hanya berlaku untuk koreksi yang benar; salah koreksi dari error multi-lane bisa melebihi `ACC_W`. Selain itu, menghitung Σk·Y_k dan Σk²·Y_k dengan pengali menambah biaya di domain aman.
- **Keputusan:** d1, d2, d3, serta perbandingan d2 = j·d1 dan d3 = j²·d1 dihitung modulo 2^`ACC_CS_W` (dua-komplemen), baik di `model/checker.py` maupun di RTL. Hasil koreksi dipotong ke `ACC_W` bit dengan dua-komplemen. Hasil serializer berurutan S1, S2, (S3), Y_K, …, Y_1, sehingga checker menjumlahkan dengan tiga akumulator berantai A += Y, B += A, C += B; setelah K kata, A = ΣY, B = Σk·Y, dan Σk²·Y = 2C − B.
- **Konsekuensi:** tidak ada pengali di checker dan RTL tetap bit-exact terhadap model, termasuk untuk error ekstrem. Untuk nilai dalam batas §3.6 hasilnya sama dengan pseudo-code. Assert overflow §6.4 tidak dipasang di hardware karena salah koreksi memang bisa terjadi; kasus itu dihitung sebagai "salah koreksi" di kampanye.
- **Status:** Diterima.

## ADR-009 — Modul komparator bernama `lane_checker`
- **Konteks:** SPEC §17 dan STATUS menyebut `rtl/checker.v`, tetapi `checker` adalah kata kunci SystemVerilog sehingga ditolak `iverilog -g2012` dan Verilator.
- **Keputusan:** modul dan berkasnya bernama `lane_checker` (`rtl/lane_checker.v`). Model Python tetap `model/checker.py`.
- **Konsekuensi:** hanya penamaan; perilaku tidak berubah.
- **Status:** Diterima.

## ADR-010 — Rekonfigurasi MMCM2 dan batas Spartan-7
- **Konteks:** SPEC §7.6 meminta pemilihan antara Clocking Wizard via AXI4-Lite (PG065), DRP langsung (XAPP888), atau rencana B dengan beberapa CLKOUT tetap ditambah mux. Vivado 2025.2 di mesin ini belum memiliki dukungan device Spartan-7 (`get_parts xc7s*` kosong), F_IN belum diketahui, dan PG065/DS189 belum tersedia di repo.
- **Keputusan:** arsitektur memakai `clk_gen` dengan antarmuka `reconfig_start`/`reconfig_level`/`reconfig_busy`/`turbo_locked`. Pilihan utama pada fase board: Clocking Wizard via AXI4-Lite (PG065), sesuai SPEC. DRP langsung dan rencana B tetap sebagai cadangan jika IP Wizard tidak dapat dipakai. Model simulasi dan urutan §7.7 diverifikasi sekarang lewat `rtl/clk_seq.v` dan `tb/tb_system.v`; implementasi register PG065 pada `rtl/platform/xilinx/clk_gen_xilinx.v` ditunda karena butuh dukungan device, F_IN, dan PG065.
- **Konsekuensi:** tabel frekuensi (`tools/gen_mmcm_table.py`) sudah tersedia dengan batas `verified: false` di `config/mmcm_limits.yaml`; batas ini wajib dicek ke DS189 beserta nomor halamannya sebelum fase board.
- **Status:** Diterima sementara, ditinjau saat fase board.

## ADR-011 — Rekomendasi lane checksum ketiga (C3)
- **Konteks:** kampanye M3 [SIM] (`results/sim/campaign_s.json`, skrip `model/campaign.py`) pada akumulator nyata model `s`: 10.000 error dua lane tanpa C3 memberi 597 salah koreksi (K=8) dan 630 (K=16), sedangkan dengan C3 tidak ada salah koreksi (seluruhnya masuk RECOMPUTE). Error satu lane 100% terkoreksi di semua konfigurasi. Injeksi berupa mask XOR, bukan error timing terukur; laju error multi-lane yang nyata hanya bisa diukur di board (E1).
- **Keputusan:** C3 tetap parameter sintesis `C3_EN`. Default repo tetap 0 sampai data resource M11 dan data E1 di board ada. Rekomendasi: aktifkan `C3_EN=1` bila resource part yang dipakai mencukupi, karena salah koreksi tanpa C3 adalah silent data corruption yang tidak terdeteksi oleh counter CORRECTED.
- **Konsekuensi:** biaya C3 adalah satu lane checksum lagi (DSP atau LUT) dan satu kata per unit di FIFO hasil. Perbandingan keuntungan bersih dilakukan di E8 setelah M11.
- **Status:** Diterima sementara, keputusan akhir setelah M11 dan E1.

## ADR-012 — Pipeline tambahan dan tafsir margin SPEC §7.4
- **Konteks:** run OOC pertama (xc7s25csga225-1, K=8) menunjukkan jalur kritis domain cepat bukan MAC: pointer baca FIFO XPM (fanout 205) dan sinyal capture ke register holding. Domain aman dibatasi perhitungan alamat aktivasi (10 tingkat logika). SPEC §7.4 menyebut slack non-MAC "minimal 30% lebih besar", tanpa definisi angka saat slack MAC kecil atau negatif.
- **Keputusan:** FIFO operand dipecah menjadi beberapa FIFO paralel (lebar maksimum sekitar 50 bit per irisan) yang ditulis dan dibaca bersama; capture register holding memakai pulsa selesai milik lane masing-masing; kontrol slot di `fast_path` menjadi register yang boleh direplikasi; alamat generator operand ditambah satu tahap register. Margin §7.4 dihitung sebagai (slack non-MAC − slack MAC) dibagi delay MAC (periode − slack MAC), target ≥ 30%, oleh `fpga/parse_reports.py`.
- **Konsekuensi:** perilaku cycle-level generator bertambah satu tahap latensi tetapi fungsi tetap; semua bench diulang. Keluaran FIFO irisan identik dengan FIFO tunggal.
- **Status:** Diterima.

## ADR-013 — Target dikunci ke XC7S25CSGA225-1, speed grade −1

- **Konteks:** sejak 10 Nov 2026 panitia mewajibkan laporan sintesis untuk AMD Spartan-7 XC7S25CSGA225-1 bagi semua kelas, dan Class 2 hanya boleh memakai ZERO7 yang membawa chip itu [OFFICIAL, `docs/official/README.md`]. Resource part menurut basis data Vivado dan tangkapan layar di panduan resmi: 14.600 LUT, 29.200 flip-flop, 45 block RAM, 80 DSP, 3 MMCM [VIVADO; OFFICIAL IN-24]. Hasil M11 untuk modul `engine` di part ini [VIVADO-STA]: model `s`, K = 8, lane `lut`, C3 = 0 memakai 4.774 LUT (32,7%), 4.364 FF (14,9%), 14 block RAM (31,1%), 3 DSP; dengan C3 = 1 menjadi 5.717 LUT (39,2%); K = 16 memakai 7.080 LUT (48,5%) dan 22 block RAM (48,9%).
- **Alternatif:** (a) tetap menjaga beberapa part; (b) part resmi dengan K = 8 tanpa C3; (c) part resmi dengan K = 8 dan C3; (d) part resmi dengan K = 16.
- **Keputusan:** satu target, `xc7s25csga225-1`. Varian resmi untuk laporan sintesis dan untuk board: model `s`, K = 8, R = 2, `LANE_IMPL = lut`, `C3_EN = 1`, `INJ_EN = 1`, dicatat di `config/hw_zero7.yaml`. C3 diaktifkan karena salah koreksi tanpa C3 adalah data rusak yang tidak terdeteksi (ADR-011) dan biayanya sekitar 943 LUT di part yang baru terisi sepertiga. K = 16 tidak dipilih: Fmax `clk_safe` turun dari 147,8 ke 118,8 MHz [VIVADO-STA], sehingga batas suplai operand R·f_safe ikut turun, dan overhead siklusnya 9,9% [SIM]. Default umum di SPEC §1 tidak diubah.
- **Dampak:** SPEC §2 dan §14 diperbarui. `fpga/run_matrix.py` tetap ada untuk eksplorasi; hasil part lain dan speed grade −2 menjadi data pembanding. Anggaran resource dengan kutipan halaman DS180 dan batas MMCM dengan kutipan halaman DS189 belum bisa ditulis karena kedua datasheet belum ada di repo; sampai itu ada, angka resource berlabel [VIVADO].
- **Status:** Diterima.

## ADR-014 — Laporan sintesis resmi sebagai deliverable utama

- **Konteks:** laporan sintesis XC7S25CSGA225-1 wajib, tetapi formatnya belum dijelaskan panitia. Sampai sekarang hanya modul `engine` yang pernah disintesis (M11, out-of-context); `top_core` dan `top_board` dengan MMCM dan SPI belum pernah melewati Vivado.
- **Alternatif:** (a) menyerahkan laporan out-of-context `engine`; (b) mengimplementasikan desain lengkap `top_board` dengan XDC board dan menyimpan laporan sesudah sintesis dan sesudah implementasi; (c) proyek GUI seperti contoh di panduan.
- **Keputusan:** (b). `fpga/synth_official.tcl` berjalan dalam mode batch di Vivado 2025.2 dengan top `top_board`, part `xc7s25csga225-1`, dan `board/zero7.xdc`. Keluarannya di `results/vivado/official/`: utilisasi (sesudah sintesis dan sesudah implementasi, termasuk hierarki), ringkasan timing, jaringan clock, daya (estimasi tanpa vektor), DRC, dan metodologi, ditambah `summary.json` berlabel [VIVADO-STA]. Bitstream tidak dibuat selama standar I/O belum pasti. Perintahnya `python tools/run.py synth-official`. Alur ini dikerjakan sekarang sebagai mitigasi risiko dan diulang setiap kali RTL berubah.
- **Dampak:** milestone baru M15. `clk_gen_xilinx` harus cukup lengkap untuk diimplementasikan dengan clock 20 MHz (ADR-015). Hasil di `results/vivado/` di-commit.
- **Status:** Diterima.

## ADR-015 — Clock board 20 MHz sebagai input MMCM

- **Konteks:** clock board adalah net CLK20M di pin B13, 20 MHz [OFFICIAL, IN-31 dan TK-1]; B13 pin clock-capable [VIVADO]. Tabel MMCM sebelumnya memakai placeholder 100 MHz. Batas MMCM di `config/mmcm_limits.yaml` belum diverifikasi ke DS189.
- **Alternatif:** f_safe 100 MHz atau 125 MHz; jarak level turbo 5, 10, atau 12,5 MHz dengan 16 level (lebar field `LEVEL` 4 bit).
- **Keputusan:** `CLKIN1_PERIOD` = 50,0 ns untuk kedua MMCM. MMCM1 memakai VCO 1.000 MHz (M = 50, D = 1), di tengah rentang 600–1.200 MHz yang belum terverifikasi. f_safe = 125 MHz (pembagi 8) jika implementasi resmi lolos timing; jika tidak, 100 MHz (pembagi 10). Pilihan ini ditetapkan oleh hasil STA dan dicatat di `results/vivado/official/`. Tabel turbo: 16 level mulai dari f_safe dengan jarak 10 MHz, semuanya tercapai tepat dengan input 20 MHz (`tools/gen_mmcm_table.py`). Sapuan E1 dengan langkah 5 MHz butuh tabel yang bisa ditulis host; itu diputuskan bersama sequencer DRP (ADR-010).
- **Dampak:** `tools/gen_mmcm_table.py` memakai 20 MHz sebagai default dan tidak lagi menandai F_IN sebagai placeholder; test-nya diperbarui. SPEC §7.6 diperbarui. Setelan MMCM dicek dengan DRC Vivado sebagai pengganti sementara DS189.
- **Status:** Diterima; f_safe menunggu hasil STA.

## ADR-016 — Peta I/O ZERO7

- **Konteks:** tabel koneksi resmi memberi pin SPI0, LED, tombol, dan WS2812B. Tiga LED warna dan tiga tombol berbagi jalur dengan GPIO Raspberry Pi; polaritas tombol belum diketahui. `top_board` sekarang punya empat keluaran LED biasa.
- **Alternatif:** (a) FPGA menggerakkan semua LED dan membaca semua tombol; (b) FPGA hanya memakai jalur miliknya sendiri, sedangkan jalur bersama diserahkan ke perangkat lunak Raspberry Pi.
- **Keputusan:** (b).
  - SPI0 dengan CE0: SCLK A8, MOSI A6, MISO A7, CS D9. CE1 (C10) tidak dipakai.
  - Sinyal selesai `irq_done` di RP_GPIO25 (C9), aktif tinggi selama `STATUS.DONE` = 1, supaya Pi bisa menunggu tepi sinyal dan mengukur latensi tanpa polling.
  - LED milik FPGA: D5 (R3) = sibuk, D6 (R2) = FATAL. Status lain ditampilkan lewat WS2812B (ADR-017).
  - Tombol START, STOP, RUN dan LED D3, D8, D9 dibaca atau digerakkan perangkat lunak Pi. Dengan begitu tidak ada dua penggerak di satu jalur, dan polaritas tombol cukup diatur di perangkat lunak.
  - Constraint board ada di `board/zero7.xdc`. Template lama dihapus dan `board/build_bitstream.py` memakai file itu; skrip tetap menolak selama ada field wajib yang UNKNOWN.
- **Dampak:** port `top_board` berubah; XDC dan test paket board mengikuti. SPEC §12.1 diperbarui.
- **Status:** Diterima.

## ADR-017 — Indikator WS2812B yang digerakkan FPGA

- **Konteks:** LED1 WS2812B di pin N1 (net S7_LED0) digerakkan FPGA [OFFICIAL, TK-5]. Juri menilai ide dan presentasi; peta error yang terlihat langsung di board memperkuat demo. Jumlah LED per rantai dan urutan warna belum diketahui.
- **Alternatif:** (a) hanya LED biasa; (b) driver WS2812B di FPGA; (c) LED digerakkan Pi.
- **Keputusan:** (b). Modul `rtl/ws2812_tx.v` di domain `clk_safe` dengan parameter jumlah LED (default 1) dan parameter waktu bit yang diturunkan dari frekuensi clock. Encoder status memetakan keadaan ke warna: idle, berjalan di clock aman, berjalan di turbo (warna bergeser menurut level), ada koreksi, ada recompute, FATAL. Testbench memeriksa lebar pulsa setiap bit. Nilai waktu bit harus dicek ke datasheet WS2812B sebelum dipakai di board.
- **Dampak:** milestone baru M17; port `ws2812_dout` di `top_board`; register kecerahan opsional.
- **Status:** Diterima; implementasi sesudah M15.

## ADR-018 — Suhu chip dari XADC

- **Konteks:** XC7S25 punya XADC; Hardware Manager di panduan resmi menampilkannya [OFFICIAL, IN-48]. Register `TEMP` sudah disediakan di peta register. E6 membutuhkan suhu.
- **Alternatif:** (a) tanpa suhu; (b) sensor luar lewat PMOD atau I2C; (c) sensor suhu internal XADC.
- **Keputusan:** (c). Wrapper `xadc_temp` di `rtl/platform/xilinx/` dengan model simulasi di `rtl/platform/sim/`, membaca kode suhu 12 bit dan menaruhnya di `TEMP`. Suhu hanya dicatat; kebijakan governor (SPEC §10) tidak diubah. Rumus konversi ke °C diambil dari UG480 saat implementasi, dengan nomor halaman.
- **Dampak:** milestone baru M18; laporan utilisasi resmi diulang sesudahnya.
- **Status:** Diterima; implementasi sesudah M15.

## ADR-019 — Boot dari flash QSPI ditunda

- **Konteks:** board punya flash QSPI (IC2) dan DIP mode SW7 [OFFICIAL]. Jenis flash dan posisi SW7 belum diketahui; panduan resmi hanya menjelaskan pemrograman lewat JTAG.
- **Alternatif:** (a) menyiapkan file konfigurasi flash sekarang dengan menebak jenis flash; (b) menunda sampai user manual atau board ada.
- **Keputusan:** (b). Jalur yang didukung adalah JTAG. Boot dari flash menjadi target demo supaya tidak bergantung pada kabel JTAG, dan dikerjakan setelah jenis flash diketahui dari dokumen atau dari board.
- **Dampak:** butir `[B]` baru di STATUS.
- **Status:** Ditunda.

## ADR-020 — Kategori dan batas klaim sesudah pembaruan panitia

- **Konteks:** tugas dibagi dua kelas (2 Nov 2026). Class 2 terbatas pada ZERO7 dengan tugas bebas dan hanya Level 3; semua kelas wajib menyerahkan laporan sintesis XC7S25CSGA225-1 [OFFICIAL]. Riset 16 Nov 2026 menemukan bahwa ABFT, checksum ganda, koreksi berbasis checksum, dan overclocking akselerator CNN sudah ada, dan bahwa karya terdekat (Marty dkk.) tampaknya menimbang lalu menolak koreksi berbasis checksum (`docs/research/RISET_WEB_2026-11.md`).
- **Alternatif:** pindah ke Class 1 Level 3, atau tetap di Class 2 Level 3.
- **Keputusan:** target tetap Class 2 Level 3 sebagai usulan yang menunggu konfirmasi panitia. Klasifikasi gambar, mode data validasi, dan mode kamera real-time tetap dipertahankan supaya syarat Class 1 Level 3 juga terpenuhi. Kontribusi yang ditonjolkan adalah milik rancangan sendiri: (1) koreksi error satu lane tanpa hitung ulang yang dibandingkan langsung dengan deteksi-lalu-ulang pada bitstream dan board yang sama, (2) atlas error timing CNN nyata di FPGA kecil, (3) pemilihan clock per layer oleh governor di dalam FPGA, dan (4) peta error per lane yang terlihat langsung di board. Kalimat klaim memakai "sejauh penelusuran kami per November 2026"; kata "pertama" dan "baru" tidak dipakai sebelum teks lengkap Marty dkk. dan Li dkk. dibaca.
- **Dampak:** `docs/PRIOR_ART.md` sudah diperbarui; laporan harus memuat bagian yang menjawab alasan Marty dkk.
- **Status:** Diterima.
