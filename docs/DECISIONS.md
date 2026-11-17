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
- **Status:** Diterima. Hasil 2026-11-16: f_safe = 125 MHz. Sesudah ADR-021, implementasi resmi lolos timing di 125 MHz [VIVADO-STA, `results/vivado/official/summary.md`]; cadangan 100 MHz tidak dipakai.

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

## ADR-021 — Reset, synchronizer, dan aturan penyeberangan domain clock

- **Konteks:** implementasi lengkap pertama `top_board` di xc7s25csga225-1 pada 125 MHz [VIVADO-STA, `results/vivado/official_preadr021/`]: semua jalur di dalam satu clock lolos (WNS +0,286 ns di `clk_safe_raw` untuk 11.249 endpoint, +0,204 ns di `clk_fast_safe` untuk 5.597 endpoint). Satu jalur antar-clock gagal dengan slack −0,499 ns: reset power-on di `top_board` (domain `clk_in`, 20 MHz) menuju tahap pertama register geser reset di `top_core` (domain `clk_safe`), dengan requirement 2,000 ns. Jalur itu masukan sebuah synchronizer, tetapi belum dinyatakan begitu ke Vivado, dan Vivado memadatkan register geser reset menjadi SRL. `report_methodology` memberi TIMING-9 (penyeberangan tanpa synchronizer yang dikenali) dan TIMING-10 (synchronizer tanpa `ASYNC_REG`). SPEC §7.8 belum mengatur reset dari clock board (top-level board baru ada sejak ADR-016) dan belum mendaftar sinyal yang menyeberang tanpa synchronizer.
- **Alternatif:** (a) menurunkan f_safe ke 100 MHz memakai aturan cadangan ADR-015: gejalanya hilang, sebabnya tetap; (b) clock group asinkron antara `clk_in` dan `clk_safe`: terlalu lebar, penyeberangan baru di masa depan ikut tersembunyi; (c) menandai synchronizer dan mengecualikan hanya jalur masuk synchronizer reset.
- **Keputusan:** (c), dengan lima aturan.
  1. Setiap synchronizer diberi atribut `ASYNC_REG` di RTL: reset `clk_safe` (`por_meta` dan `lock_meta` di `top_core`), reset `clk_fast` (`rst_fast_meta` di `engine`), `pass_active` (`fast_path`), tiga pin SPI (`spi_slave`), dan LOCKED MMCM2 (`clk_gen_xilinx`, synchronizer baru). Tidak boleh ada logika di depan synchronizer: reset power-on dan LOCKED MMCM1 masing-masing punya synchronizer dua flop, lalu digabung dengan soft reset di domain `clk_safe`. Run antara yang masih meng-OR ketiga sumber di depan satu synchronizer ditandai CDC-10 oleh `report_cdc` [VIVADO-STA, `results/vivado/official_adr021a/`]. Flop yang menggerakkan net reset dipisah dari synchronizer supaya tetap boleh direplikasi. Setiap sumber tetap sampai ke reset sesudah empat flop, jadi perilaku per siklus tidak berubah. Atribut bukan primitif: simulator mengabaikannya, dan primitif Xilinx tetap hanya ada di `rtl/platform/xilinx/`.
  2. Jalur dari `clk_in` ke tahap pertama `por_meta` adalah false path (`fpga/constraints/top_board_timing.tcl`). Tidak ada pengecualian timing lain yang ditambahkan.
  3. Sinyal yang menyeberang dari `clk_safe` ke `clk_fast` tanpa synchronizer hanya boleh sinyal quasi-statis, yaitu sinyal yang hanya berubah saat domain cepat idle: konfigurasi injeksi (register `INJ*`) dan indeks layer. Indeks layer dijamin oleh urutan state engine (berubah sesudah semua hasil layer kembali dan sebelum pass berikutnya dimulai). Register `INJ*` menjadi aturan host: hanya ditulis saat `STATUS.BUSY` = 0. Ke arah sebaliknya, `STARVE_CYCLES` hanya dibaca saat `STATUS.BUSY` = 0.
  4. Operand dan hasil tetap hanya menyeberang lewat FIFO asinkron XPM.
  5. Alur laporan resmi menambah `report_cdc` dan `report_bus_skew`, dan ringkasannya memuat jumlah penyeberangan per kelas beserta artinya di desain ini.
- **Dampak:** SPEC §7.8 diperluas. `rtl/top_core.v`, `rtl/engine.v`, `rtl/fast_path.v`, `rtl/spi_slave.v`, `rtl/platform/xilinx/clk_gen_xilinx.v`, constraint, dan alur resmi berubah; seluruh regresi diulang. Pilihan f_safe pada ADR-015 diambil dari run sesudah perubahan ini. Masih terbuka dan dikerjakan bersama sequencer DRP (ADR-010): penjagaan di hardware supaya tulis `INJ*` saat BUSY ditolak (sekarang hanya aturan host), dan konfirmasi perpindahan mux yang nyata (`is_turbo` di `clk_gen_xilinx` masih melaporkan permintaan).
- **Status:** Diterima. Tambahan 2026-11-16: penjagaan tulis `INJ*` selama BUSY sudah diimplementasikan di `regfile` (M20).

## ADR-022 — Host Raspberry Pi 4 Model B

- **Konteks:** panitia menulis bahwa board pinjaman bisa dipasang di Raspberry Pi 5 [OFFICIAL, G-6]. Tim hanya punya Raspberry Pi 4 Model B [USER, 2026-11-16]. ZERO7 adalah HAT di header 40-pin dan mengambil daya dari header [OFFICIAL, IN-41]. Semua sinyal yang dipakai SENTINEL (SPI0 di GPIO 7–11, sinyal selesai di GPIO25) memakai nomor GPIO BCM.
- **Alternatif:** (a) membeli Pi 5; (b) memakai Pi 4 dan memeriksa kecocokan saat board datang.
- **Keputusan:** (b). Header 40-pin dan nomor GPIO BCM Pi 4 sama dengan Pi 5 [INFERENCE], jadi `board/zero7.xdc` tidak berubah. Perangkat lunak hanya memakai `spidev`, `gpiozero`, dan `picamera2`, yang berjalan di kedua model; tidak ada kode khusus Pi 5. Catu daya memakai adaptor resmi Pi 4 (5,1 V, 3 A); arus ZERO7 dari header [UNKNOWN] dan diukur di langkah bring-up 1. Kamera memakai kabel 15-pin standar. `board/pi_check.py` memeriksa model Pi, `/dev/spidev0.0`, dan paket Python di Pi sebelum langkah 2.
- **Dampak:** `board/BOARD_INFO.md`, `board/BRINGUP.md`, `CLAUDE.md` §7, dan materi belajar menyebut Pi 4. Risiko yang dicatat: contoh resmi diuji di Pi 5; kecocokan mekanis dan anggaran daya baru pasti saat board ada. Jika Pi 4 ternyata tidak cocok, tidak ada RTL yang berubah.
- **Status:** Diterima.

## ADR-023 — Dokumen AMD: batas MMCM, rekonfigurasi MMCM2, dan konfigurasi XADC

- **Konteks:** user mengizinkan unduhan dokumen AMD pada 2026-11-16. Tersimpan di `docs/vendor/amd/`: DS189 (edisi 2024-10-18), DS180 v2.6.1, UG480 v1.11, PG065 (Clocking Wizard v6.0). ADR-010 menunda pilihan cara rekonfigurasi MMCM2; ADR-018 menunda rumus suhu.
- **Keputusan:**
  1. Batas MMCM diambil dari DS189 Tabel 37 (PDF hlm. 40): input 10–800 MHz, PFD 10–450 MHz (−1), VCO 600–1.200 MHz (−1), keluaran maksimum 800 MHz, waktu lock maksimum 100 µs, clock DRP maksimum 200 MHz. Nilai −2 lama untuk input dan keluaran maksimum (933 MHz) salah dan diganti 800 MHz. Kapasitas part diambil dari DS180 Tabel 2 (hlm. 2). `verified: true` dengan nomor halaman.
  2. MMCM2 direkonfigurasi lewat Clocking Wizard v6.0 dengan antarmuka AXI4-Lite (PG065, "Dynamic Reconfiguration through AXI4-Lite"), pilihan utama SPEC §7.6. IP dibangkitkan dari Tcl di alur resmi (probe Vivado 2025.2: input 20 MHz, keluaran 125 MHz memberi M = 50, D = 1, O = 8,0). Master AXI4-Lite sederhana `clkwiz_seq` (RTL portabel) menulis register 0x200 (DIVCLK_DIVIDE, CLKFBOUT_MULT, CLKFBOUT_FRAC) dan 0x208 (CLKOUT0_DIVIDE dan FRAC), menunggu SR (0x04) bit 0 = 1, menulis 0x25C = 0x3, lalu menunggu SR bit 0 dan LOCKED kembali 1. Nilai per level diambil dari tabel `tools/gen_mmcm_table.py` yang dibangkitkan ke `rtl/gen/mmcm_turbo_table.vh`. Perpindahan mux baru dilaporkan (`is_turbo`) sesudah jeda tetap, bukan langsung mengikuti permintaan.
  3. XADC (UG480): mode sequence kontinu dengan kanal kalibrasi dan suhu (INIT_48 = 0x0101, hlm. 46), koreksi kalibrasi aktif (INIT_41 = 0x20F0, Tabel 3-5 dan 3-9, hlm. 36 dan 38), pembagi DCLK 8 sehingga ADCCLK = 125/8 = 15,625 MHz di bawah batas 26 MHz (INIT_42 = 0x0800; DS189 Tabel 50: DCLK 8–250 MHz, ADCCLK 1–26 MHz). Kode suhu 12 bit dibaca dari alamat DRP 00h (12 MSB). Suhu °C = kode × 503,975 / 4096 − 273,15 (UG480 Persamaan 2-6, hlm. 24); galat sensor ±4 °C pada −40 sampai 100 °C (DS189 Tabel 50). Konversi ke °C dilakukan di perangkat lunak.
  4. Reset AXI wizard diturunkan dari LOCKED MMCM1 saja (lewat synchronizer). MMCM1 ditahan reset oleh reset power-on, jadi LOCKED-nya rendah selama reset itu. Dua percobaan lain ditolak `report_cdc`: OR reset dan LOCKED di depan satu synchronizer (CDC-10) dan synchronizer kedua untuk reset power-on (CDC-11, satu flop ke dua synchronizer).
- **Dampak:** ADR-010 dan ADR-018 terjawab. SPEC §7.6 dan §12.4 diperbarui. Alur resmi diulang karena MMCM2 sekarang di dalam IP. Simulasi tidak memodelkan IP AMD; `clkwiz_seq` diuji dengan model register perilaku yang mengikuti PG065, dan perilaku IP yang sebenarnya baru terbukti di board.
- **Status:** Diterima.

## ADR-024 — Standar I/O LVCMOS33 dari bukti resmi

- **Konteks:** user bertanya apakah `Zero7.xdc` bisa disusun sendiri dari tabel koneksi. Pin sudah diambil dari tabel itu (ADR-016). Yang belum tertulis adalah tegangan VCCO bank 15 dan 34.
- **Bukti:** komentar `##Clock (20MHz, 3.3V)` untuk B13 (bank 15) di tangkapan layar `Zero7.xdc` resmi [OFFICIAL, IN-31]; semua pin yang dipakai SENTINEL tersambung langsung ke GPIO Raspberry Pi, yang bekerja pada 3,3 V, dan tabel koneksi tidak menunjukkan level shifter [OFFICIAL, TK-1 dan TK-2]; CFGBVS dan VCCO bank 0 di VCC3V3 [OFFICIAL]; bank 14, 15, dan 34 jenis HR yang mendukung 1,2–3,3 V (DS180 Tabel 3).
- **Keputusan:** LVCMOS33 untuk semua pin SENTINEL di bank 15 dan 34 sebagai [INFERENCE] dengan bukti di atas. Tanda TODO di `board/zero7.xdc` tetap sampai tegangan VCCO diukur dengan multimeter saat board datang (langkah bring-up 1) atau user manual terbit. `board/build_bitstream.py` tetap menolak membuat bitstream untuk board sebelum itu. Pemeriksaan "bitstream kering" boleh dijalankan sekarang: `write_bitstream` dari checkpoint resmi ke `build/`, hanya untuk membuktikan bahwa DRC pembuatan bitstream lolos. File itu tidak dipakai di board dan tidak di-commit.
- **Dampak:** fase board tidak bisa dimulai lebih awal; satu risiko (DRC bitstream) bisa ditutup sebelum board datang.
- **Status:** Diterima.

## ADR-025 — Host lewat JTAG selama Raspberry Pi belum ada

- **Konteks:** ZERO7 dan JTAG-HS3 tersedia mulai 20 Nov 2026; Raspberry Pi 4 mungkin datang lebih lambat dan kompatibilitasnya dengan ZERO7 [UNKNOWN] (info tim, 17 Nov 2026). Semua eksperimen SENTINEL memakai host yang mengunggah bobot, mengirim gambar, dan membaca register. JTAG-HS3 sudah tersambung ke PC untuk memprogram FPGA; pin JTAG ada di bank 0 yang VCCO-nya VCC3V3 [OFFICIAL, TK].
- **Alternatif:**
  - (a) Host lewat JTAG: IP JTAG-to-AXI Master milik AMD di FPGA, jembatan AXI4-Lite ke bus host SENTINEL, dan skrip Tcl Vivado yang dikendalikan Python (`JtagBackend`, antarmuka sama dengan `HwBackend` dan `MockBackend`). VIO juga dipertimbangkan, tetapi VIO hanya cocok untuk beberapa sinyal kontrol; mengunggah ribuan byte bobot lewat properti VIO terlalu lambat dan rumit.
  - (b) Bobot dan beberapa gambar uji disimpan di BRAM, dengan mode self-test yang dijalankan tombol START; hasil PASS/FAIL dari CRC logit dibandingkan nilai golden dan ditampilkan di LED atau WS2812B.
  - (c) UART lewat PMOD dengan adaptor USB-UART.
- **Perbandingan:**

  | Kriteria | (a) JTAG-to-AXI | (b) self-test BRAM | (c) UART PMOD |
  | --- | --- | --- | --- |
  | Perangkat tambahan | tidak ada (kabel JTAG yang sama) | tidak ada | adaptor USB-UART |
  | Tegangan bank harus pasti | tidak (bank 0 = 3,3 V [OFFICIAL]) | tidak | ya (bank 15 belum pasti) |
  | Ganti bobot tanpa sintesis ulang | ya | tidak | ya |
  | E1–E4, E7 dengan log lengkap | ya | tidak (hanya PASS/FAIL) | ya |
  | Memakai ulang driver dan harness | ya (frame SPI diterjemahkan ke transaksi AXI) | tidak | sebagian (protokol baru) |
  | Kecepatan unggah | lambat (transaksi Vivado), cukup untuk eksperimen | tidak perlu unggah | sedang |
  | Risiko | perintah Tcl Hardware Manager belum dicoba di board | paling kecil | butuh RTL UART baru |

- **Keputusan:** (a). Rinciannya:
  1. `top_core` mendapat port bus host eksternal (byte), di-OR dengan bus dari `spi_slave`; satu host saja yang aktif pada satu waktu. `top_board` mengikat port ini ke nol, jadi bitstream SPI tidak berubah fungsinya.
  2. `rtl/axil_bus_bridge.v`: slave AXI4-Lite 32 bit yang memecah tiap transaksi menjadi akses byte pada bus host (little-endian, byte dengan `WSTRB` saja), plus jendela ID di alamat 0xFFFFF8–0xFFFFFF yang mengembalikan kata ID yang sama dengan perintah SPI 0x9F.
  3. IP JTAG-to-AXI Master hanya di `rtl/platform/xilinx/`; model simulasinya `rtl/platform/sim/` memutar ulang log transaksi dan memeriksa data baca, supaya jalur JTAG lulus ko-simulasi bit-exact seperti `spi_session`.
  4. `board/top_jtag.v` untuk ZERO7 tanpa Pi: clock B13, LED R3/R2, WS2812B N1; pin SPI tidak dipakai.
  5. Python: `JtagAxiTransport` menerjemahkan frame SPI dari `SentinelDriver` ke transaksi word; tulis sebagian word hanya dilakukan dengan baca-ubah-tulis di area memori, tidak pernah di register. `JtagBackend` = `HwBackend` di atas transport itu. Sisi Vivado dijalankan sebagai sesi Tcl yang tetap terbuka (perintah `create_hw_axi_txn` dan `run_hw_axi`, UG908); urutan data dan perilaku perintah dicek dengan uji pola saat pertama kali tersambung ke board.
  6. (b) tetap layak sebagai uji asap tambahan dan demo tanpa host, tetapi tidak dikerjakan sekarang.
- **Dampak:** SPEC §12.7 baru. Ko-simulasi baru `jtag_session` dan test Python dry-run. Laporan resmi (`top_board`) tidak berubah. Hasil dari jalur ini tetap [HW] hanya bila dijalankan di board, dan latensi ujung ke ujungnya tidak mewakili SPI.
- **Status:** Diterima.

## ADR-026 — Bring-up ZERO7 tanpa Raspberry Pi

- **Konteks:** board datang 20 Nov 2026, Pi mungkin belakangan. Dokumen resmi hanya menyebut daya ZERO7 dari header GPIO Raspberry Pi (IN-41); cara lain [UNKNOWN]. Tegangan VCCO bank 15 dan 34 belum tertulis, dan bola VCCO BGA tidak bisa disentuh probe.
- **Keputusan:**
  1. Tiga desain bring-up di `fpga/bringup/`: `blink_top` (LED berkedip; frekuensi clock dari stopwatch), `vcco_probe_top` (PMOD1 dan N1/J7 pada level tetap, supaya tegangan bank 15 dan 34 terbaca dengan multimeter di header), `io_test_top` (tombol dan switch ke LED dan warna WS2812B).
  2. Bitstream bring-up boleh dibuat sebelum VCCO pasti, karena desain ini hanya menggerakkan pin milik FPGA (dicek test); `fpga/bringup/build.py` tetap menolak tanpa `--accept-inferred-io`. Bitstream SENTINEL penuh untuk board tetap menunggu VCCO terukur (ADR-024).
  3. Daya tanpa Pi tidak disarankan dari pin header tanpa dasar dokumen. Jalur yang tertulis adalah daya dari Raspberry Pi; Pi apa pun yang dipinjam hanya untuk daya tetap mengikuti jalur itu, dengan catatan kompatibilitas Pi 4 [UNKNOWN] dan Pi 5 yang disebut panitia.
  4. Milestone M22 (bring-up tanpa Pi dan host JTAG) di STATUS.
  5. Fase BOARD tetap dimulai sesuai CLAUDE.md §8. Semua yang dibuat sebelum itu adalah persiapan.
- **Dampak:** `board/BRINGUP_NO_PI.md`; peta eksperimen tanpa Pi di STATUS.
- **Status:** Diterima.

## ADR-027 — Pin select BUFGCTRL tidak di-timing

- **Konteks:** run resmi 17 Nov 2026 sesudah ADR-025 meleset tipis: WNS −0,044 ns pada jalur `clk_sel_turbo` (domain `clk_safe`) ke pin S1 BUFGCTRL, dengan requirement setengah periode clock turbo [VIVADO-STA]. Run sebelumnya lolos di jalur yang sama dengan slack +0,27 sampai +0,65 ns; bedanya hanya penempatan. Frekuensi turbo berubah saat berjalan, jadi jalur ini sebenarnya asinkron; Vivado hanya menganggapnya sinkron karena turbo level 0 sama dengan clk_safe dan keduanya berasal dari CLK20M.
- **Dasar:** DS189 Tabel 32, catatan 1: TBCCCK_CE/TBCCKC_CE wajib dipenuhi untuk perpindahan clock tanpa glitch; setup/hold global clock lainnya opsional, hanya perlu bila perpindahan harus cocok siklus-per-siklus dengan simulasi. Di SENTINEL pin CE diikat 1 (konstan), pemilih hanya berubah saat domain cepat diam (SPEC §7.7), dan `clk_gen_xilinx` melaporkan status mux sesudah jeda tetap.
- **Alternatif:** (a) mengandalkan penempatan yang kebetulan lolos; (b) menurunkan f_safe; (c) false path ke pin S0/S1 BUFGCTRL dengan dasar DS189.
- **Keputusan:** (c). `fpga/constraints/top_board_timing.tcl` memberi `set_false_path` ke pin select BUFGCTRL. Pengecualian lain tetap tidak ada (ADR-021). Pin CE tidak dikecualikan.
- **Dampak:** laporan resmi diulang; test memastikan pengecualian ini ada beserta rujukannya. Dengan false path, `report_cdc` mencatat jalur ini sebagai CDC-13 (penyeberangan ke primitif bukan flip-flop) berstatus unsafe; guard test laporan resmi hanya mengizinkan CDC-13 di pin S0/S1 BUFGCTRL itu dan menolak yang lain.
- **Status:** Diterima.
