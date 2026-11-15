# Dokumen resmi dan arsip

Terakhir diperbarui: 2026-11-16. Hanya folder ini (dan halaman panitia yang dirujuknya) yang boleh menjadi sumber aturan lomba.

## Daftar file

| File | Sumber | Diarsipkan | Isi | Catatan |
| --- | --- | --- | --- | --- |
| `GUIDE_LSI_2027_FINALE.pdf` | Tangkapan halaman Inggris `https://www.lsi-contest.com/index_e.html` dan `https://www.lsi-contest.com/shiyou_1e.html`, dibuat user | 2026-11-16, disalin dari folder Downloads user | 6 halaman: TOP (berita sampai 2026/11/10, jadwal, pedoman, presentasi, saran juri, akses, panitia) dan Design Specification §1–§5 | [OFFICIAL]. Menggantikan `superseded/GUIDE_LSI_2027.pdf`. sha256 `d09e86226bed66fa…` |
| `ZERO7FPGA_Connection-table_261109_001.pdf` | `https://www.lsi-contest.com/ZERO7FPGA_Connection-table_261109_001.pdf` (ditautkan dari `shiyou_1.html` dan `shiyou_1e.html`) | 2026-11-16, salinan dari user | 7 halaman, 225 pin: Pin #, BANK, Name, Connect 1–4 | [OFFICIAL]. sha256 `c595ac3d9c8531aa…` |
| `Initialize_20260618_EN.pdf` | `https://www.lsi-contest.com/Initialize_20260618_EN.pdf` (ditautkan dari `shiyou_1e.html`) | 2026-11-16, salinan dari user | 59 slide "Raspberry Pi and ZERO7: From Setup to Design and Operation", DSP Laboratory, bertanggal 2026/11/10 | [OFFICIAL]. sha256 `a03b92cd8c141682…` |
| (belum diarsipkan) `Initialize_20260618.pdf` | `https://www.lsi-contest.com/Initialize_20260618.pdf` (ditautkan dari `shiyou_1.html`) | — | Versi Jepang dari panduan di atas; 59 halaman menurut struktur PDF | Belum disalin ke repo: menunggu izin unduh dari user. Isinya dibaca dari versi Inggris resmi. |
| `superseded/GUIDE_LSI_2027.pdf` | Tangkapan situs sebelum pembaruan 2 dan 10 Nov 2026 | 2026-11-09 | 4 halaman | Sudah digantikan. Jangan dipakai sebagai sumber aturan. |
| `A_Overview_LSI_2019.pdf` | Paket awal dari user. Padanan daring yang dirujuk panitia sekarang: `https://www.lsi-contest.com/2020/shiyou_3e.html` (tautan "design overview" di `shiyou_1e.html`) | sebelum 2026-11-09 | Design specification kontes ke-23 (2020, Okinawa) | Nama file menyebut 2019, tetapi isinya spesifikasi kontes ke-23. [HISTORICAL]. |
| `CNN_Example_2019.pdf` | Paket awal dari user; URL sumber tidak tercatat | sebelum 2026-11-09 | Slide pengajaran CNN (contoh pengenalan ○/×) | [HISTORICAL]. |
| `CNN_2019.zip` | Paket awal dari user; URL sumber tidak tercatat | sebelum 2026-11-09 | Contoh kode MATLAB/Octave untuk training dan inferensi CNN kecil | Turunan sigmoid diterapkan dua kali pada backprop layer konvolusi. Jangan dijadikan acuan aritmetika. |

## Ringkasan aturan 2027, per 2026-11-16

Semua butir [OFFICIAL]. Rujukan "G-n" berarti halaman n di `GUIDE_LSI_2027_FINALE.pdf`; "JP" berarti halaman Jepang yang dibaca langsung pada 2026-11-16.

- **Tema:** "CNN implementation (any number of layers)" (G-1, G-2; JP: 「CNNの実装（層数は任意）」).
- **Tanggal:** batas laporan Minggu 31 Januari 2027; presentasi Jumat 5 Maret 2027 (G-2).
- **Tempat:** Hokkaido Gas Bunka Hall (Chitose Civic Cultural Center), 2-2-11 Hokuei, Chitose, Hokkaido 066-0036; format hybrid lewat Zoom dan di tempat (G-2).
- **Presentasi:** 10 menit dengan maksimal 10 slide, lalu 5 menit tanya jawab (G-2; JP: 発表時間10分、質疑応答5分、パワーポイント10枚以内).
- **Yang dikumpulkan:** laporan akhir dan laporan sintesis untuk AMD Spartan-7 XC7S25CSGA225-1, wajib (G-2).
- **Wajib untuk semua kelas:** desain disintesis sehingga muat di XC7S25CSGA225-1 dan hasil sintesisnya (laporan) dikumpulkan, juga bila memakai board lain di Unlimited (G-6). Format laporan sintesis tidak dijelaskan.
- **Lingkungan desain:** Vivado direkomendasikan versi 2025.2; part diatur sebagai XC7S25CSGA225-1 (G-5).
- **Tujuan:** implementasi hardware CNN dengan syarat data validasi yang ditentukan dan input kamera real-time (G-5). Gambar validasi diberikan pada hari lomba; sistem membacanya dari kamera, kartu SD, dan sebagainya; presentasi menunjukkan seberapa cepat hasil pengenalan keluar (G-5). Rincian tugas "will be updated at a later date".
- **CNN:** input 32×32. Dataset latih bebas, tetapi target pengenalan (kelas) ditentukan panitia dan akan diumumkan pada pembaruan berikutnya (G-5; JP: 「学習に使用するデータセットは自由です．ただし，認識する対象（分類するクラス）はこちらで指定します」). Struktur mengacu ke design overview kontes ke-23; hidden layer bebas.
- **Class 1, Image Classification Class:** hanya klasifikasi gambar. Level 1 (CNN sederhana, misalnya input 3×3) dan Level 2 (CNN 32×32 dengan training dan validasi) harus menargetkan XC7S25CSGA225-1. Level 3 (Unlimited): rancang dulu pengklasifikasi yang muat di XC7S25CSGA225-1 dan tunjukkan laporan sintesisnya; selain itu board dan arsitektur bebas selama klasifikasi gambar (G-6).
- **Class 2, ZERO7 Class:** board hanya ZERO7, tugas bebas (tidak terbatas klasifikasi gambar), hanya Level 3 (G-6).
- **Board:** ZERO7 buatan Gigafirm adalah HAT Raspberry Pi di header GPIO 40-pin (G-3). Panitia meminjamkan board Spartan-7 "that can be connected to a Raspberry Pi 5" (G-6; JP: 「Raspberry Pi5に接続できるSpartan7 FPGAのボード」).
- **Peminjaman ZERO7:** Indonesia lewat Prof. Trio Adiono, ITB (tadiono@itb.ac.id); Vietnam lewat Assoc. Prof. Lâm Đức Khải (khaild@uit.edu.vn); negara lain lewat support@LSI-contest.com. Judul email: "Zero7 board Univ. name Your name" (G-2, G-6).
- **Saran juri:** bukan hanya kecepatan dan area, tetapi juga ide, orisinalitas, keunikan; presentasi yang baik; "We definitely take your school grade into account"; "We like fun ideas. Please do something different from others." (G-2).
- **Peserta:** lihat perbedaan di bawah.

Belum diumumkan, jadi [UNKNOWN]: kelas target, format laporan dan laporan sintesis, bobot penilaian, aturan penggunaan AI, dan apakah demo hardware langsung dilakukan saat presentasi.

## Perbedaan halaman Jepang dan Inggris (2026-11-16)

| Hal | Halaman Jepang | Halaman Inggris |
| --- | --- | --- |
| Ukuran tim | 「大学・高専生による4人以下のチーム」 (paling banyak 4 orang) | "the team of 1-3 University or college students" |
| Butir penilaian | Ada butir 「仕様の部分変更など、柔軟に受け付けます」 (perubahan sebagian spesifikasi diterima secara fleksibel) | Butir itu tidak ada |
| Tingkat peserta | 「大学院生、学部学生、高専生のレベルに応じて審査します」 | "We definitely take your school grade into account" |
| Kontak peminjaman | Hanya untuk mahasiswa di Jepang: support@LSI-contest.com | Vietnam, Indonesia, dan negara lain (lihat atas) |

Untuk tim dari Indonesia, halaman Inggris yang berlaku sampai ada klarifikasi; ukuran tim perlu ditanyakan ke panitia jika anggota lebih dari tiga.

Berita 2026/11/10 menyebut tiga dokumen ZERO7: 導入資料 (setup guide), ユーザーマニュアル (user manual), dan コネクションテーブル (connection table). Halaman spesifikasi hanya menautkan dua PDF (panduan dan tabel koneksi). Panduan itu sendiri menulis "Refer to the ZERO7 User Manual" (slide 14) dan menyebut file contoh `raspi-zer07_button.py`, `pi_button_receiver.v`, dan `Zero7.xdc` yang "provided in the same folder as this manual". User manual dan ketiga file contoh itu belum ditemukan di situs.

## Istilah Jepang yang dipakai panitia

| Jepang | Arti |
| --- | --- |
| 設計仕様書 | design specification |
| 募集要項 | pedoman pendaftaran (guidelines for applicants) |
| 審査のポイント | butir penilaian |
| 設計課題 / 課題 | tugas desain / tugas |
| 層数は任意 | jumlah layer bebas |
| 論理合成・実装 | sintesis logika dan implementasi |
| 合成レポート | laporan sintesis |
| 指定チップ | chip yang ditentukan |
| 必須要件 | syarat wajib |
| 導入資料 | panduan pengenalan (setup guide) |
| コネクションテーブル | tabel koneksi |
| 貸与 | peminjaman |
| 指定画像検証データ | data validasi gambar yang ditentukan |
| カメラ実時間入力 | input kamera real-time |
| 認識する対象（分類するクラス） | target pengenalan (kelas klasifikasi) |
| 画像分類クラス / ZERO7クラス | Image Classification Class / ZERO7 Class |
| 初心者向け / 中級者向け / 上級者向け | pemula / menengah / lanjut |
| 発表会 | acara presentasi |

## Catatan pembacaan (2026-11-16)

| Sumber | Yang dibaca | Cara | Catatan |
| --- | --- | --- | --- |
| `index.html` (Jepang) | seluruh halaman | browser, teks halaman | WebFetch salah membaca halaman ini (Shift_JIS) dan menghasilkan beberapa frasa yang tidak ada di halaman; hasil WebFetch dibuang |
| `index_e.html` (Inggris) | seluruh isi lewat `GUIDE_LSI_2027_FINALE.pdf` hlm. 1–2; cek langsung butir ukuran tim dan tautan | PDF + browser | — |
| `shiyou_1.html` (Jepang) | seluruh halaman, §1–§5, dan tautan PDF | browser | — |
| `shiyou_1e.html` (Inggris) | seluruh isi lewat `GUIDE_LSI_2027_FINALE.pdf` hlm. 3–6; cek langsung tautan PDF | PDF + browser | — |
| `ZERO7FPGA_Connection-table_261109_001.pdf` | 7 dari 7 halaman | PDF | — |
| `Initialize_20260618_EN.pdf` | 59 dari 59 slide | PDF | Lampiran SSH yang disebut di slide 6 tidak ada di versi ini; lampiran hanya berisi pemetaan GPIO (slide 59) |
| `Initialize_20260618.pdf` (Jepang) | tidak dibaca | — | Teksnya tidak terbaca lewat WebFetch (font CID); istilah Jepang dari dokumen ini belum dicatat |
| `A_Overview_LSI_2019.pdf`, `CNN_Example_2019.pdf`, `CNN_2019.zip` | dibaca pada sesi 2026-11-09 | visual | Tidak dibaca ulang pada 2026-11-16 |
