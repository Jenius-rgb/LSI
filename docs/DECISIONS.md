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
