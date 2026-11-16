# Simulasi Juri — SENTINEL

Ditulis 2026-11-16 (PROMPT_UPDATE_ZERO7, Tahap 8). Dokumen ini penilaian diri untuk menentukan prioritas kerja. Ini bukan prediksi hasil lomba: bobot resmi belum diumumkan, juri sungguhan bisa menilai sangat berbeda, dan tidak ada janji lolos finalis atau menang.

Angka di dokumen ini disalin dari file hasil di repo oleh skrip sekali pakai saat dokumen ditulis; setiap angka menyebut filenya. Kalau file hasil berubah, dokumen ini tidak ikut berubah.

## 1. Dasar penilaian

Kriteria [OFFICIAL] dari `docs/official/README.md` (panduan G-2, G-5, G-6):

- Juri menilai bukan hanya kecepatan dan area, tetapi juga ide, orisinalitas, dan keunikan.
- Presentasi yang baik dihargai: 10 menit, maksimal 10 slide, 5 menit tanya jawab.
- Tingkat pendidikan peserta ikut dipertimbangkan.
- "We like fun ideas. Please do something different from others."
- Wajib: laporan sintesis untuk XC7S25CSGA225-1; data validasi dari panitia dan input kamera real-time; presentasi menunjukkan seberapa cepat hasil pengenalan keluar.
- Halaman Jepang menambah satu butir: perubahan sebagian spesifikasi diterima secara fleksibel.

Bobot resmi [UNKNOWN]. Rubrik di bawah ini rubrik internal [PROPOSAL]: tujuh butir, skor 0–5, bobot berjumlah 100. Nilai akhir = jumlah (bobot × skor) / 5.

## 2. Apakah ide ini sudah ada?

Rujukan: `docs/PRIOR_ART.md` dan `docs/research/RISET_WEB_2026-11.md`.

| Komponen SENTINEL | Status di literatur | Sumber |
| --- | --- | --- |
| Checksum (ABFT) untuk konvolusi | sudah ada | Huang & Abraham 1984; Zhao dkk. 2021; Hari dkk. 2020 |
| Overclocking akselerator CNN di FPGA dengan deteksi checksum lalu hitung ulang | sudah ada | Marty dkk. FPT 2018 dan versi jurnal 2020 |
| Overclocking otomatis dengan monitor delay | sudah ada | Jiang dkk. (AOS) 2023 |
| Overclocking dengan alur deteksi sampai pemulihan | sudah ada; cara pemulihannya belum kami baca | Li dkk. ITC-Asia 2019 (baru abstrak) |
| Koreksi keluaran berbasis kode pada array PE | disebut sudah bisa | Gao dkk. 2024 (abstrak) |
| Karakterisasi error timing array MAC di FPGA | sudah ada, bukan CNN | Chamberlin dkk. 2024 |
| Lokalisasi dan koreksi satu lane tanpa jeda, digabung dengan overclocking | belum kami temukan | sejauh penelusuran kami per November 2026 |
| Clock per layer dengan governor seluruhnya di FPGA | belum kami temukan | sejauh penelusuran kami per November 2026 |
| Atlas error timing CNN sungguhan di Spartan-7 | belum kami temukan | sejauh penelusuran kami per November 2026 |

Penilaian juri simulasi: gabungannya menarik dan berbeda dari proyek CNN kontes yang umum (akurasi dan FPS), tetapi konsep dasarnya bukan hal baru. Nilai orisinalitas bergantung pada dua hal yang belum ada: teks lengkap Marty dkk. dan Li dkk. (apakah koreksi atau clock per layer sudah mereka lakukan), dan data board yang menunjukkan koreksi memang lebih baik daripada hitung ulang. Kata "pertama" atau "baru" tidak boleh dipakai (ADR-020).

## 3. Tiga putaran

| Butir [PROPOSAL] | Bobot | Putaran 1 | Putaran 2 | Putaran 3 |
| --- | --- | --- | --- | --- |
| Ide dan orisinalitas | 25 | 3,5 | 3,5 | 3,5 |
| Keunikan dan daya tarik ("fun", berbeda dari tim lain) | 10 | 3,0 | 3,0 | 3,0 |
| Bukti teknis dan kematangan | 20 | 2,5 | 3,0 | 3,5 |
| Kecepatan dan area | 15 | 2,0 | 2,5 | 2,5 |
| Pemenuhan tugas wajib (validasi, kamera real-time, laporan sintesis) | 15 | 1,5 | 2,5 | 3,0 |
| Presentasi dan demo | 10 | 2,0 | 2,0 | 2,0 |
| Kejujuran metodologi dan klaim | 5 | 4,5 | 4,5 | 4,5 |
| **Nilai akhir (0–100)** | | **52,5** | **59,0** | **62,5** |

### Putaran 1: keadaan sesudah ADR-013 sampai ADR-020 (commit 7919db7)

Kelemahan terbesar menurut juri simulasi:

1. Belum ada satu pun hasil [HW]. Inti proyek, yaitu bahwa error timing mengenai satu lane dan bisa dikoreksi (H1), baru diuji dengan error buatan. Kalau error nyata ternyata mengenai banyak lane sekaligus, koreksi tidak berguna dan desain jatuh ke hitung ulang seperti Marty dkk.
2. Laporan sintesis resmi, yang wajib, belum ada. Desain lengkap belum pernah diimplementasikan di chip resmi.
3. Sequencer rekonfigurasi MMCM2 belum ada (ADR-010), jadi clock turbo belum bisa dinaikkan walaupun board sudah ada.
4. Waktu ujung ke ujung kemungkinan didominasi pengiriman gambar lewat SPI dan kamera, bukan komputasi. Keuntungan overclocking bisa tidak terlihat pada "seberapa cepat hasil keluar".
5. Kelas target belum diumumkan; akurasi integer model `s` 80,22% di CIFAR-10 [SIM, `results/model/s/quant_result.json`] hanya pengganti sementara.
6. Dua karya terdekat belum dibaca penuh, jadi klaim orisinalitas rapuh.
7. Belum ada elemen demo yang terlihat mata dan belum ada slide. Proyek ini rumit untuk 10 menit.
8. Kategori Class 2, ukuran tim, dan aturan pemakaian AI belum dikonfirmasi.

### Perbaikan sebelum putaran 2

- Alur laporan resmi dibuat (`python tools/run.py synth-official`, ADR-014) dan desain lengkap `top_board` diimplementasikan di xc7s25csga225-1: 6.172 dari 14.600 LUT (42,27%), 14 dari 45 block RAM, semua net ter-route [VIVADO-STA, `results/vivado/official_preadr021/`].
- Varian resmi (model `s`, K = 8, C3 aktif) lulus regresi: `PASS 200/200 (34/34 cycles_mean=277895 ideal=277504)` dan sistem dua clock `PASS 10/10 reconfigs=0` [SIM, `results/sim/rtl_regression.jsonl`].

### Putaran 2: temuan baru

Run pertama itu membuka kelemahan yang sebelumnya tidak terlihat:

1. Satu jalur gagal timing di 125 MHz dengan slack −0,499 ns: reset power-on yang menyeberang dari clock board ke `clk_safe`. Jalur di dalam satu clock semuanya lolos (+0,286 ns di `clk_safe`, +0,204 ns di `clk_fast`) [VIVADO-STA, `results/vivado/official_preadr021/`].
2. Synchronizer belum ditandai, dan Vivado memadatkan register reset menjadi SRL.
3. Sinyal konfigurasi injeksi menyeberang ke domain cepat tanpa synchronizer, dan aturan yang membuatnya aman tidak tertulis di SPEC.
4. LOCKED MMCM2 masuk ke FSM `clk_seq` tanpa synchronizer.

### Perbaikan sebelum putaran 3

- ADR-021 dan SPEC §7.8: setiap sumber reset asinkron punya synchronizer sendiri, semua synchronizer bertanda `ASYNC_REG`, LOCKED MMCM2 disinkronkan, daftar penyeberangan yang diizinkan ditulis, dan register `INJ*` hanya boleh ditulis saat `STATUS.BUSY` = 0.
- Alur resmi menambah `report_cdc` dan `report_bus_skew`.
- Anggaran latensi ditambahkan ke `docs/RESULTS_SIM.md` supaya kelemahan nomor 4 putaran 1 bisa dibahas dengan angka.

### Putaran 3: keadaan akhir sesi ini

Hasil run resmi [VIVADO-STA, `results/vivado/official/summary.md`], clk_safe 125 MHz:

- 6.170 dari 14.600 LUT (42,26%), 5.704 flip-flop, 14 dari 45 block RAM, 3 DSP.
- Slack setup terburuk desain +0,417 ns; di dalam `clk_safe` +0,417 ns (Fmax 131,9 MHz), di dalam `clk_fast` +0,481 ns (Fmax 133,0 MHz). Tidak ada net yang belum ter-route.
- `report_cdc`: tidak ada penyeberangan berstatus unsafe dan tidak ada synchronizer tanpa `ASYNC_REG`. Yang tersisa 412 endpoint "unknown" per pasangan clock, yaitu sinyal quasi-statis (konfigurasi injeksi dan indeks layer) yang aturannya ada di SPEC §7.8. Bus skew pointer FIFO: 16 constraint, slack terburuk +6,962 ns.
- Daya menurut `report_power` tanpa data aktivitas: 0,505 W. Ini estimasi, bukan pengukuran.
- Anggaran latensi [SIM] × [VIVADO-STA] (`docs/RESULTS_SIM.md`): komputasi 277.895 siklus × 8,000 ns = 2,223 ms per gambar dengan clock aman. Mengirim 3.072 byte gambar lewat SPI butuh 2,458 ms pada 10 MHz dan 24,576 ms pada 1 MHz; kecepatan SPI board [UNKNOWN]. Jadi pengiriman bisa sama besar atau lebih besar dari komputasi.

Tidak ada perbaikan berarti lagi yang bisa dikerjakan tanpa board, dokumen AMD, atau teks lengkap karya terdekat, jadi simulasi berhenti di putaran 3.

## 4. Kelemahan yang masih ada, diurutkan menurut dampak pada nilai

| No | Kelemahan | Kenapa penting | Yang membukanya |
| --- | --- | --- | --- |
| 1 | Belum ada hasil [HW]; H1 belum teruji | menentukan butir ide, bukti, dan kecepatan sekaligus | board ZERO7, lalu B1 sampai B5 |
| 2 | Sequencer rekonfigurasi MMCM2 belum ada | tanpa itu tidak ada overclocking nyata | PG065 atau XAPP888 dan DS189 (perlu izin unduh) |
| 3 | Dua karya terdekat belum dibaca penuh | klaim bisa gugur saat tanya jawab | akses kampus ke IEEE Xplore |
| 4 | Latensi ujung ke ujung dibatasi SPI dan kamera | syarat resmi menilai seberapa cepat hasil keluar | ukur SPI di board; laporkan waktu komputasi dan ujung ke ujung terpisah |
| 5 | Kelas target belum diumumkan | akurasi akhir belum bisa dilaporkan | pengumuman panitia; alur latih ulang sudah ada |
| 6 | Belum ada demo yang terlihat mata | butir "fun" dan presentasi | indikator WS2812B (M17), mode kamera, tombol |
| 7 | Margin timing tipis di 125 MHz | perubahan kecil bisa membuat laporan resmi gagal timing | ulangi `synth-official` setiap RTL berubah; cadangan 100 MHz (ADR-015) |
| 8 | Aturan host untuk `INJ*` belum dijaga hardware | fitur uji bisa mengganggu engine kalau ditulis saat berjalan | penjagaan tulis di `regfile` (kecil, belum dikerjakan) |
| 9 | Kategori, ukuran tim, dan aturan AI belum pasti | risiko administratif | tanya panitia |

## 5. Pertanyaan yang mungkin ditanyakan juri

1. **Kenapa tidak cukup deteksi lalu hitung ulang seperti Marty dkk.?** Jawaban jujur saat ini: belum terbukti lebih baik. Mode 1 SENTINEL adalah cara itu, mode 2 adalah koreksi, keduanya di bitstream yang sama; E4 membandingkannya di board yang sama. Kalau koreksi tidak menang, itu dilaporkan.
2. **Dari mana tahu error hanya mengenai satu lane?** Belum tahu. Itu hipotesis H1 dan diukur di E1. Kampanye [SIM] hanya menunjukkan apa yang terjadi kalau memang begitu: 10.000 dari 10.000 error satu lane terkoreksi, dan dengan C3 tidak ada salah koreksi pada 10.000 error dua lane (`results/sim/campaign_s.json`).
3. **Apakah pemeriksa sendiri bisa salah karena overclocking?** Pemeriksa, kontrol, memori, dan SPI berjalan di `clk_safe` yang lolos STA. Yang dipercepat hanya lane MAC. Lane checksum ikut dipercepat; error di sana dikenali sebagai kelas tersendiri.
4. **Berapa percepatan ujung ke ujung?** Belum ada angka [HW]. Anggaran latensi menunjukkan pengiriman SPI bisa mendominasi, jadi yang akan diklaim adalah throughput akselerator yang tetap bit-exact, dengan waktu ujung ke ujung dilaporkan terpisah.
5. **Apa yang orisinal?** Koreksi di tempat sebagai pengganti hitung ulang, clock per layer dengan governor di dalam FPGA, dan atlas error di Spartan-7, semuanya dengan kata "sejauh penelusuran kami".
6. **Akurasinya hanya sekitar 80%?** CIFAR-10 hanya pengganti karena kelas target belum diumumkan. Yang dijamin desain ini adalah hasil bit-exact terhadap model integer, bukan akurasi tertinggi.

## 6. Kesimpulan juri simulasi

Nilai internal naik dari 52,5 ke 62,5 [PROPOSAL] karena syarat wajib (laporan sintesis) sekarang terpenuhi dengan bukti, dan desain lengkap terbukti muat dan lolos timing di chip resmi [VIVADO-STA]. Butir yang paling berat, yaitu ide dan bukti di hardware, tidak bergerak dan tidak bisa bergerak tanpa board. Urutan kerja yang paling menaikkan nilai: sequencer MMCM2, bring-up dan E7 di clock aman, E1 untuk menguji H1, lalu demo dengan WS2812B dan kamera.

## 7. Pembaruan sesudah putaran 3 (2026-11-16, sesudah jawaban user)

Tidak ada putaran keempat; bagian ini hanya mencatat kelemahan bagian 4 yang berubah. Rubrik tidak dinilai ulang.

| No | Kelemahan | Perubahan |
| --- | --- | --- |
| 2 | Sequencer rekonfigurasi MMCM2 belum ada | MMCM2 sekarang di dalam Clocking Wizard v6.0 dengan AXI4-Lite; `clkwiz_seq` lulus bench dengan model register yang mengikuti PG065 [SIM]. Perilaku IP yang sebenarnya baru terbukti di board. |
| 3 | Dua karya terdekat belum dibaca penuh | Marty dkk. (TCAD 2020) sudah dibaca penuh; alasan mereka menolak koreksi dan jawaban SENTINEL ada di `docs/PRIOR_ART.md`. Li dkk. (ITC-Asia 2019) masih abstrak. |
| 6 | Belum ada demo yang terlihat mata | Indikator WS2812B di LED1 menunjukkan status dengan warna; tombol START/STOP/RUN bisa mengendalikan mode kamera. |
| 8 | Aturan host `INJ*` belum dijaga hardware | `regfile` membuang tulis `INJ*` selama BUSY [SIM]. |
| 9 | Kategori, ukuran tim, aturan AI | Tim 4 orang (sesuai halaman Jepang, tidak sesuai halaman Inggris 1–3); dokumen resmi tidak memuat aturan AI. Kategori tetap perlu dikonfirmasi. |

Yang tetap paling berat: belum ada hasil [HW], dan H1 belum teruji. Board dan Raspberry Pi 4 baru dipakai Desember 2026 atau Januari 2027.
