# CLAUDE.md — Proyek SENTINEL (LSI Design Contest 2027)

> "SENTINEL" hanya nama kerja. Kalau tim sudah memilih nama sendiri, ganti di file ini dan di README.
> File ini dibaca otomatis oleh Claude Code di setiap sesi. Jangan jalankan `/init`, karena itu akan menimpa file ini.

## 1. Misi

Membangun akselerator CNN di FPGA Spartan-7 (board ZERO7, Raspberry Pi HAT) yang:

1. mengklasifikasi gambar 32×32 secara **bit-exact** terhadap golden model Python,
2. menjaga lane MAC dengan **dual checksum** (C1, C2, opsional C3) untuk mendeteksi, melokalisasi, dan mengoreksi error,
3. menjalankan lane MAC lebih cepat dari frekuensi aman (**overclocking per layer**) dengan governor hardware,
4. menyediakan alat ukur lengkap untuk eksperimen E1–E8.

**Fase saat ini: PRA-BOARD.** Selesaikan semua pekerjaan yang tidak butuh board. Pekerjaan yang butuh board hanya boleh dimulai sesuai §8.

## 2. Sumber kebenaran (urutan prioritas)

1. Instruksi saya di sesi yang sedang berjalan.
2. `docs/official/` — dokumen resmi panitia. Hanya ini sumber aturan lomba. Jangan menambah aturan yang tidak tertulis di sana.
3. `docs/SPEC.md` — spesifikasi teknis. Golden model Python yang mengimplementasikan SPEC adalah **oracle** untuk RTL.
4. `docs/DECISIONS.md` — keputusan desain (format ADR). SPEC hanya boleh berubah lewat ADR baru.
5. `STATUS.md` — progres, gerbang, item terblokir, catatan antar sesi.
6. `board/BOARD_INFO.md` — fakta board. Field bertanda `UNKNOWN` tidak boleh ditebak.
7. `docs/PRIOR_ART.md` — karya terkait dan batas klaim orisinalitas.

## 3. Siklus kerja setiap sesi

1. **Baca** CLAUDE.md, STATUS.md (terutama "Catatan untuk sesi berikutnya"), board/BOARD_INFO.md, dan bagian SPEC yang relevan. Di sesi pertama, baca juga semua file di `docs/official/` (PDF-nya berupa gambar; baca secara visual).
2. **Periksa keadaan nyata.** Jalankan `python tools/run.py check` dan `python tools/run.py test` (setelah M0 ada). Jangan percaya centang di STATUS.md tanpa bukti. Kalau ada test merah, perbaiki dulu sebelum fitur baru. Kalau STATUS.md tidak sesuai kenyataan, koreksi STATUS.md dan jelaskan.
3. **Pilih tugas**: tugas pertama yang belum selesai di STATUS.md, sesuai urutan milestone. Kalau tugas itu terblokir (butuh board, alat, atau keputusan saya), tandai `[B]`, tulis alasannya di bagian "Terblokir", lalu ambil tugas berikutnya yang tidak terblokir.
4. **Rencana singkat** (3–7 butir) di chat sebelum mulai.
5. **Test dulu.** Buat unit test, vektor golden, atau testbench yang gagal lebih dulu, baru implementasi.
6. **Jalankan sampai hijau.** Simpan log ringkas (perintah dan hasil).
7. **Update STATUS.md.** Centang `[x]` hanya jika Definition of Done terpenuhi. Tulis bukti di "Log bukti": tanggal, perintah, dan hasil.
8. **Commit git** kecil dan jelas untuk setiap langkah hijau. Jangan `git push` kecuali saya minta.
9. **Lanjut** ke tugas berikutnya tanpa menunggu konfirmasi. Sebelum konteks hampir penuh (sekitar 70%), atau saat semua tugas yang tidak terblokir selesai: tulis "Catatan untuk sesi berikutnya" di STATUS.md, commit, lalu kirim ringkasan ke saya (§5).

## 4. Aturan keras (tidak boleh dilanggar)

- **Jangan mengarang hasil.** Setiap angka di dokumen, laporan, atau grafik harus bisa dilacak ke skrip dan log yang ada di repo. Kalau sebuah alat tidak bisa dijalankan, katakan itu. Jangan menulis output yang tidak benar-benar keluar.
- **Simulasi tidak bisa memunculkan error timing nyata.** Jangan pernah mengklaim perilaku hardware dari simulasi atau dari model error sintetis.
- **Label wajib** pada setiap angka, tabel, dan grafik:
  - `[SIM]` hasil simulasi RTL atau model Python,
  - `[SYNTHETIC]` memakai model error timing buatan (`model/fault_model.py`),
  - `[VIVADO-STA]` dari laporan timing atau resource Vivado (estimasi statis),
  - `[HW]` diukur di board sungguhan.
  Grafik dari backend mock wajib diberi watermark **"SYNTHETIC — NOT MEASURED"**.
- **Jangan menebak fakta board**: part number, package, speed grade, pin, clock input, cara programming, kecepatan SPI, antarmuka LED, ada tidaknya XADC. Pakai parameter atau placeholder, lalu catat di "Terblokir".
- **Golden model dan RTL harus bit-exact.** Tidak ada "hampir sama".
- **Jangan mengubah test agar lulus** tanpa alasan tertulis. Kalau spesifikasi perlu berubah, urutannya: ADR di `docs/DECISIONS.md` → update SPEC → update golden model dan testnya → update RTL.
- **Seed acak tetap** dan tercatat. Catat versi alat (Python, PyTorch, Icarus, Verilator, Vivado) di `docs/ENVIRONMENT.md`.
- **Aturan lomba**: bedakan `[OFFICIAL]` (tertulis di docs/official), `[UNKNOWN]`, dan `[INFERENCE]`. Jangan menulis aturan yang tidak ada.
- **Kode pihak ketiga**: jangan menyalin kode dengan lisensi tidak jelas. Catat setiap sumber dan lisensinya di `docs/THIRD_PARTY.md`.
- **Klaim orisinalitas**: hanya yang didukung `docs/PRIOR_ART.md`. Jangan mengklaim "pertama" atau "baru" untuk hal yang belum dicek.

## 5. Otonomi, pertanyaan, dan laporan

- Langkah yang bisa dibatalkan (menulis file, menjalankan test, membuat branch, commit lokal): **langsung kerjakan**, tanpa minta izin.
- Bertanya hanya jika:
  (a) ada ambiguitas di SPEC yang mengubah arsitektur,
  (b) butuh tindakan saya (instal alat, menjalankan Vivado di PC saya, data board), atau
  (c) aturan lomba tidak jelas.
  Ajukan pertanyaan sekali dengan rekomendasimu, lalu lanjutkan tugas lain yang tidak terblokir.
- Kalau sebuah alat tidak tersedia (misalnya Vivado tidak ada di PATH): tetap buat skripnya, tulis instruksi persis untuk saya, tandai tugasnya `[B] perlu dijalankan user`, lalu lanjut.
- **Ringkasan di akhir sesi** (bahasa Indonesia, singkat):
  1. selesai: apa saja, dengan bukti (perintah dan hasil test),
  2. terblokir: apa dan kenapa,
  3. yang perlu saya lakukan, dengan langkah persis,
  4. pertanyaan, masing-masing dengan rekomendasi.

## 6. Konvensi

- **Bahasa**: komunikasi dengan saya dalam bahasa Indonesia. Kode, komentar, nama file, dan dokumen teknis di repo dalam bahasa Inggris (untuk laporan lomba). STATUS.md boleh bahasa Indonesia.
- **RTL**: Verilog-2005 yang dapat disintesis, kompatibel dengan Icarus (`iverilog -g2012`), Verilator (`--lint-only -Wall`), dan Vivado.
  - Satu modul per file, nama file = nama modul.
  - Reset sinkron aktif tinggi, kecuali ada alasan tertulis. Tidak boleh ada latch.
  - Semua lebar dan jumlah lane memakai parameter (K, ACC_W, dll.).
- **Primitif Xilinx** (MMCM, BUFGCTRL, XPM, Clocking Wizard) hanya boleh muncul di `rtl/platform/xilinx/`. Setiap wrapper punya model simulasi portabel di `rtl/platform/sim/`.
- **Testbench** memakai file vektor (`$readmemh`) yang dibangkitkan golden model. Cetak `PASS n/n`, atau `FAIL` beserta mismatch pertama (layer, unit, lane, expected, got). Keluar dengan status gagal jika ada mismatch.
- **Python** ≥ 3.10, pytest, lintas platform (Windows dan Linux). Semua perintah lewat `tools/run.py`, bukan Makefile atau skrip bash saja.
- **Register map**: satu sumber, `spec/regmap.yaml`, dibangkitkan ke Verilog dan Python oleh `tools/gen_regmap.py`. Jangan mengedit file hasil generate. Ada test yang memastikan hasil generate selalu terbaru.
- **Folder build**: `build/` (vektor, bobot hasil ekspor, hasil simulasi) tidak di-commit dan selalu bisa dibangkitkan ulang. `results/` di-commit, karena berisi data eksperimen dan metadata.

## 7. Konteks lomba (ringkas; verifikasi ke docs/official)

- [OFFICIAL] 30th LSI Design Contest 2027 di Chitose, Hokkaido. Tema: implementasi hardware CNN.
- [OFFICIAL] Batas laporan 31 Jan 2027. Lomba 5 Mar 2027, hybrid. Presentasi 10 menit (maksimal 10 slide) dan tanya jawab 5 menit.
- [OFFICIAL] Juri menilai bukan hanya kecepatan dan area, tetapi juga ide, orisinalitas, keunikan, dan presentasi.
- [OFFICIAL] Syarat tujuan: data validasi yang ditentukan panitia dan input kamera real-time. Gambar validasi diberikan pada hari lomba (dari kamera, kartu SD, dll.). Presentasi harus menunjukkan seberapa cepat hasil pengenalan keluar.
- [OFFICIAL] CNN menerima input 32×32. Struktur mengacu ke design overview kontes ke-23; struktur hidden layer bebas.
- [OFFICIAL] Class 1: board bebas, hanya klasifikasi gambar. Level 1 (CNN sederhana, misalnya input 3×3), Level 2 (CNN untuk input 32×32 dengan training dan validasi), Level 3 (bebas). Class 2: hanya ZERO7, tugas bebas, hanya Level 3.
- [OFFICIAL, halaman Jepang] Dataset latih bebas, tetapi kelas target ditentukan panitia dan belum diumumkan. Karena itu model harus bisa dilatih ulang, dan bobot harus bisa dimuat ulang lewat SPI **tanpa sintesis ulang**.
- [UNKNOWN] Bobot penilaian, format laporan, kelas target, apakah demo hardware langsung diizinkan, dan aturan penggunaan AI.
- **Target kategori [PROPOSAL, menunggu konfirmasi panitia]: Class 2 (ZERO7 Class), Level 3.** Tetap pertahankan klasifikasi gambar, mode data validasi, dan mode kamera real-time, supaya proyek juga memenuhi syarat Class 1 Level 3 jika ternyata harus pindah kelas. Jangan menulis kategori ini sebagai fakta di laporan sebelum dikonfirmasi.

## 8. Fase BOARD

Fase board (milestone B1–B6 di STATUS.md) hanya boleh dimulai jika dua syarat terpenuhi:

1. semua field **wajib** di `board/BOARD_INFO.md` sudah terisi (tidak ada `UNKNOWN`) dan masing-masing punya sumber, dan
2. saya menulis bahwa board sudah ada di tangan (misalnya "board siap").

Aturan di fase board:

- Selalu mulai dari clock aman. Overclocking baru boleh dilakukan setelah E7 bit-exact di clock aman.
- Jangan pernah mengubah tegangan. Pantau suhu.
- Hasil board diberi label `[HW]` dan disimpan di `results/hw/`, terpisah dari `results/mock/`.
- Vivado berjalan di PC, tidak di Raspberry Pi. Skrip untuk Pi harus bisa dijalankan sendiri di Pi, dan hasilnya disalin kembali ke repo.

## 9. Perintah standar (dibuat di M0)

```
python tools/run.py check            # cek alat dan versi
python tools/run.py test             # pytest + semua testbench
python tools/run.py gen              # regmap, vektor, bobot
python tools/run.py train --model s  # training
python tools/run.py export --model s # kuantisasi + ekspor
python tools/run.py sim <tb>         # satu testbench
python tools/run.py campaign         # kampanye fault injection
python tools/run.py ooc              # Vivado out-of-context (jika Vivado ada)
python tools/run.py plots            # semua grafik
```
