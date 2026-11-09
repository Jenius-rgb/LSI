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
