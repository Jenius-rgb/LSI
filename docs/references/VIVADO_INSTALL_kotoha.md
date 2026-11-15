# Catatan: panduan instalasi Vivado (kotoha sensorium)

- **URL:** https://kotohasensorium.com/vivado-install-windows/
- **Judul:** 「Vivado インストール方法【Xilinx FPGA環境構築】Windows」
- **Terbit / diperbarui:** 2024.02.23 / 2024.03.21 (menurut halaman)
- **Diakses:** 2026-11-16
- **Status:** blog pribadi pihak ketiga, bukan dokumen panitia. Panduan resmi `Initialize_20260618_EN.pdf` (slide 17) meminta langkahnya diikuti, dengan pengecualian di bawah. Isi halaman tidak disalin; ini ringkasan.
- **Cara baca:** seluruh artikel lewat WebFetch (ringkasan oleh alat), lalu empat fakta dicek langsung di halaman lewat browser (versi 2022.2, edisi Vivado ML Standard, pilihan device, kebutuhan disk). Keempatnya cocok.

## Ringkasan isi

Artikel menjelaskan instalasi **Vivado 2022.2** edisi gratis **Vivado ML Standard** di Windows.

1. Prasyarat: Windows, akun Xilinx/AMD (untuk pemakaian pribadi, isi nama perusahaan dengan 「個人利用」), ruang disk kosong sekitar 50 GB. Hasil instalasi sekitar 20 GB, tetapi proses instalasi butuh ruang lebih. Waktu total sekitar 1 jam.
2. Buka halaman unduh resmi, pilih bagian 2022.2, unduh installer Windows, lalu masuk dengan akun.
3. Jalankan file EXE. Layar Welcome: Next. Masukkan email dan password akun (password peka huruf besar-kecil dan tidak bisa diisi otomatis).
4. Pilih produk **Vivado**. Pilihan lain: Vitis (pengembangan software, perlu untuk MicroBlaze, ikut memasang Vivado) dan Lab Edition (hanya untuk memprogram FPGA dari bitstream).
5. Pilih edisi **Vivado ML Standard**. Edisi Enterprise berbayar dan hanya perlu untuk sebagian part kelas atas.
6. Pilih device. Artikel memilih Kria SOMs, Zynq, dan UltraScale+ (sekitar 18 GB) dan menyarankan memilih hanya device yang diperlukan supaya hemat disk.
7. Setujui lisensi, periksa folder instalasi dan ruang disk, lihat ringkasan, lalu Install. Setelah selesai klik OK; penulis menyarankan restart.
8. Verifikasi: jalankan Vivado sampai layar awal muncul.
9. Catatan lain: di PC kantor, periksa dulu syarat lisensi. Driver kabel tidak dibahas.

## Pengecualian dari panduan resmi ZERO7

[OFFICIAL] `Initialize_20260618_EN.pdf` slide 18, "Target Device Families (Minimum)":

- **7 Series → Spartan-7**
- **SoCs → Zynq-7000**

Tangkapan layar di slide itu memakai installer 2023.1 dengan ukuran unduh 21,25 GB dan kebutuhan disk 70,6 GB untuk pilihan yang ditampilkan (pilihannya lebih banyak dari minimum). Slide 14 menyebut lingkungan Windows 11 dan Vivado 2025.2.

## Relevansi untuk SENTINEL

- Vivado 2025.2 sudah terpasang di PC ini dan part `xc7s25csga225-1` tersedia (lihat `docs/ENVIRONMENT.md` dan hasil `tools/vivado_check_part.tcl`). Artikel ini hanya rujukan bila perlu instalasi ulang.
- Versi di artikel (2022.2) berbeda dari versi yang direkomendasikan panitia (2025.2); nama menu installer bisa berbeda.
- Zynq-7000 tidak dipakai SENTINEL. Panduan resmi memintanya sebagai minimum tanpa menjelaskan alasannya, jadi saat ini belum dipasang. Bila Vivado Hardware Manager bermasalah saat fase board, memasangnya adalah langkah pertama yang dicoba.
- Driver kabel: opsi "Install Cable Drivers" terlihat dicentang di tangkapan layar slide 18; diperlukan untuk kabel Digilent JTAG-HS3.
