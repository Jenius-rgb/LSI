# Usulan teks pengganti CLAUDE.md §7

Status: usulan untuk user (temuan 14 di `docs/REVIEW_2026-11.md`). `CLAUDE.md` adalah file instruksi user, jadi tidak diubah tanpa persetujuan. Semua butir merujuk `docs/official/README.md`.

```
## 7. Konteks lomba (ringkas; verifikasi ke docs/official)

- [OFFICIAL] 30th LSI Design Contest 2027 di Chitose, Hokkaido. Tema: implementasi hardware CNN, jumlah layer bebas.
- [OFFICIAL] Batas laporan 31 Jan 2027. Lomba 5 Mar 2027, hybrid. Presentasi 10 menit (maksimal 10 slide) dan tanya jawab 5 menit.
- [OFFICIAL] Yang dikumpulkan: laporan akhir dan laporan sintesis untuk AMD Spartan-7 XC7S25CSGA225-1. Laporan sintesis wajib untuk semua kelas; formatnya belum dijelaskan.
- [OFFICIAL] Juri menilai bukan hanya kecepatan dan area, tetapi juga ide, orisinalitas, keunikan, dan presentasi. Tingkat pendidikan peserta ikut dipertimbangkan.
- [OFFICIAL] Syarat tujuan: data validasi yang ditentukan panitia dan input kamera real-time. Gambar validasi diberikan pada hari lomba (dari kamera, kartu SD, dll.). Presentasi harus menunjukkan seberapa cepat hasil pengenalan keluar.
- [OFFICIAL] CNN menerima input 32×32. Struktur mengacu ke design overview kontes ke-23; struktur hidden layer bebas.
- [OFFICIAL] Class 1 (Image Classification): hanya klasifikasi gambar. Level 1 dan Level 2 menargetkan XC7S25CSGA225-1. Level 3 bebas board dan arsitektur, tetapi tetap harus menunjukkan laporan sintesis yang muat di XC7S25CSGA225-1.
- [OFFICIAL] Class 2 (ZERO7): hanya board ZERO7, tugas bebas, hanya Level 3.
- [OFFICIAL] ZERO7 buatan Gigafirm adalah HAT Raspberry Pi; board pinjaman bisa dipasang di Raspberry Pi 5. Vivado yang direkomendasikan: 2025.2.
- [OFFICIAL] Dataset latih bebas, tetapi kelas target ditentukan panitia dan belum diumumkan. Karena itu model harus bisa dilatih ulang, dan bobot harus bisa dimuat ulang lewat SPI **tanpa sintesis ulang**.
- [OFFICIAL, berbeda antar halaman] Ukuran tim: halaman Inggris 1–3 orang, halaman Jepang paling banyak 4 orang.
- [UNKNOWN] Bobot penilaian, format laporan dan laporan sintesis, kelas target, apakah demo hardware langsung diizinkan, dan aturan penggunaan AI.
- **Target kategori [PROPOSAL, menunggu konfirmasi panitia]: Class 2 (ZERO7 Class), Level 3.** Tetap pertahankan klasifikasi gambar, mode data validasi, dan mode kamera real-time, supaya proyek juga memenuhi syarat Class 1 Level 3 jika ternyata harus pindah kelas. Jangan menulis kategori ini sebagai fakta di laporan sebelum dikonfirmasi.
```
