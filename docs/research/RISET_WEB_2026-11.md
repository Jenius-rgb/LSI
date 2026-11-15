# Riset web dan media sosial, 15 Okt – 15 Nov 2026

Dikerjakan 2026-11-16. Tujuan: menemukan informasi terbaru tentang LSI Design Contest 2027, ZERO7, XC7S25, dan topik inti SENTINEL (overclocking akselerator CNN, error timing, checksum/ABFT).

Label yang dipakai:
- `[OFFICIAL]`: halaman atau dokumen panitia yang dibaca langsung.
- `[VERIFIED EXTERNAL]`: halaman pihak ketiga yang dibuka dan dibaca.
- `[UNVERIFIED]`: hanya cuplikan hasil pencarian; halamannya tidak terbuka atau tidak dibuka.

Catatan metode:
- Pencarian memakai mesin pencari web dan pembaca halaman. Ringkasan halaman dibuat oleh alat pembaca, jadi rincian `[VERIFIED EXTERNAL]` tetap perlu dicek ke halaman aslinya sebelum dikutip di laporan.
- Halaman Jepang panitia dibaca lewat browser, karena alat pembaca salah mendekode Shift_JIS.
- Skill `last30days` tidak dipakai: ia membutuhkan penyiapan, kunci API layanan pihak ketiga, dan bisa meminta akses cookie browser.
- Media sosial hanya dicari lewat mesin pencari. Tidak ada login ke akun apa pun.
- Nama proyek dan nama tim tidak dimasukkan ke kata kunci pencarian.

## (a) Pembaruan dari panitia

Semua `[OFFICIAL]`, dari `https://www.lsi-contest.com/index.html` dan `index_e.html` (dibaca 2026-11-16). Rincian aturan ada di `docs/official/README.md`.

| Tanggal | Isi |
| --- | --- |
| 2026-10-20 | Tema desain, Design Specification, dan tempat acara diterbitkan |
| 2026-10-22 | Informasi peminjaman board ZERO7 diterbitkan |
| 2026-11-02 | Tugas di Design Specification dibagi menjadi dua kelas: Image Classification Class dan ZERO7 Class |
| 2026-11-10 | Laporan sintesis untuk chip XC7S25CSGA225-1 menjadi syarat wajib |
| 2026-11-10 | Dokumen ZERO7 diterbitkan (setup guide, user manual, connection table); yang tertaut hanya setup guide dan connection table |

Yang belum diumumkan: kelas target, format laporan sintesis, bobot penilaian, aturan penggunaan AI.

## (b) Informasi ZERO7

| Sumber | Tanggal | Isi | Label |
| --- | --- | --- | --- |
| `docs/official/ZERO7FPGA_Connection-table_261109_001.pdf` | 2026-11-09 (nama file) | Tabel 225 pin FPGA: bank, nama net, tujuan sambungan | `[OFFICIAL]` |
| `docs/official/Initialize_20260618_EN.pdf` | 2026-11-10 (tanggal di slide) | Penyiapan Raspberry Pi, proyek Vivado, JTAG, contoh tombol dan LED | `[OFFICIAL]` |
| `GUIDE_LSI_2027_FINALE.pdf` hlm. 3–4 | 2026-11-16 (tangkapan) | Diagram arsitektur ZERO7 dan foto board; sablon board terbaca "Q-SPARC ZERO7" dan "SMART NINJA" | `[OFFICIAL]` |
| https://www.gigafirm.com/ | entri 25.7.1 | Daftar produk baru memuat "ZERO7  AMD Spartun-7 Board" (ejaan sesuai halaman). Tidak ada spesifikasi, harga, manual, atau skematik. Alamat yang tertulis: Fukuoka Branch R&D Center di Iizuka, dan Machida Design Office di Tokyo | `[VERIFIED EXTERNAL]` |
| https://www.gigafirm.com/ | entri 26.3.6 | Berita "第29回 LSIデザインコンテスト" | `[VERIFIED EXTERNAL]` |

Tidak ditemukan: user manual ZERO7, skematik, file `Zero7.xdc`, halaman produk, repo GitHub, atau artikel Qiita/Zenn/note tentang ZERO7. Fakta pin dan cara programming ada di `board/BOARD_INFO.md`.

## (c) Proyek tim lain yang terlihat publik

Tidak ditemukan proyek, repo, tulisan, atau unggahan publik tentang karya untuk kontes 2027 (ke-30). Yang ditemukan hanya konteks kontes sebelumnya:

| Sumber | Tanggal | Isi | Label |
| --- | --- | --- | --- |
| https://u-aizu.ac.jp/en/information/29-lsi2026.html | acara 2026-03-06 | Kontes ke-29 di Okinawa, tema GAN. 77 peserta dari 26 tim mendaftar; 11 tim diundang presentasi. Juara: Chiba University. Runner-up: Institut Teknologi Bandung, University of Aizu, Kyushu Institute of Technology. Tim Aizu membuat "SpikeGAN" (GAN berbasis spiking) | `[VERIFIED EXTERNAL]` |
| https://stei.itb.ac.id/en/dua-tim-stei-itb-raih-penghargaan-di-lsi-design-contest-2025/ | 2025 | Dua tim STEI ITB menjadi finalis kontes 2025 (tema Variational Autoencoder) | `[UNVERIFIED]` |
| https://stei.itb.ac.id/en/?p=24476 | tidak diketahui | Muncul di hasil pencarian; halamannya memberi HTTP 500 saat dibuka | `[UNVERIFIED]` |

Hasil pencarian lain (proyek kuliah akselerator LeNet-5, MNIST di FPGA kecil, dan sejenisnya) tidak berhubungan dengan kontes ini. Tidak ada ide atau kode tim lain yang dipakai.

## (d) Makalah dan dampaknya ke klaim kebaruan SENTINEL

### Dua makalah yang diminta dibaca

| Karya | Yang berhasil dibaca | Isi | Dampak |
| --- | --- | --- | --- |
| Li, Xu, Xing, Liu, Wang, Li, Li, "Squeezing the Last MHz for CNN Acceleration on FPGAs", ITC-Asia 2019, hlm. 151–156, DOI 10.1109/itc-asia.2019.00039 | Abstrak saja (lewat OpenAlex) `[VERIFIED EXTERNAL]` | Overclocking akselerator CNN di FPGA; jaringan dilatih di atas akselerator dengan error timing ikut serta; untuk overclocking kasus terburuk membahas alur dari deteksi fault sampai pemulihan; implementasi di Xilinx KCU1500 | Overclocking CNN di FPGA dengan deteksi lalu pemulihan sudah ada sejak 2019. Cara pemulihannya belum diketahui; teks lengkap wajib dibaca sebelum menulis klaim |
| Marty, Yuki, Derrien, "Algorithm Level Timing Speculation for Convolutional Neural Network Accelerators", laporan teknis Inria, Juni 2018 (HAL hal-01811231). Versi konferensi: "Enabling Overclocking through Algorithm-Level Error Detection", FPT 2018, hlm. 174–181. Versi jurnal: IEEE TCAD 2020 | Tidak ada teks yang terbuka. HAL menolak dengan proteksi bot, salinan di situs penulis memberi 403, CORE memberi halaman verifikasi | Dari cuplikan pencarian `[UNVERIFIED]`: ada komponen kernel, checksum input, dan checksum output; logika checksum ikut di-overclock; makalah menyebut bahwa sebagian teknik ABFT memakai dua checksum atau lebih untuk koreksi, dan menyatakan koreksi berbasis checksum tidak cocok untuk rancangan mereka (alasannya tidak terlihat di cuplikan). Versi jurnal: overhead di bawah 8% dengan tingkat deteksi mendekati 100% | **Paling penting.** Karya terdekat ini tampaknya sudah menimbang koreksi dengan checksum ganda lalu menolaknya. Laporan SENTINEL harus membaca alasannya dan menjelaskan mengapa koreksi tetap sah di rancangan SENTINEL |

### Karya lain yang ditemukan

| Karya | Tanggal | Isi | Hubungan dengan SENTINEL | Dibaca |
| --- | --- | --- | --- | --- |
| Hari, Sullivan, Tsai, Keckler, "Making Convolutions Resilient via Algorithm-Based Error Detection Techniques", arXiv:2006.04984 | 2020-06-08 | Checksum untuk memverifikasi konvolusi di GPU; hanya deteksi; overhead 6–23%; sasaran error hardware transien | Deteksi berbasis checksum pada konvolusi; bukan FPGA, bukan overclocking, tanpa koreksi | Halaman abstrak `[VERIFIED EXTERNAL]` |
| Wen, Xie, Wang, Li, "DRIFT: Harnessing Inherent Fault Tolerance for Efficient and Reliable Diffusion Model Inference", DAC 2026, DOI 10.1145/3770743.3804042 (arXiv:2604.09073) | 2026-07-26 | DVFS yang sadar ketahanan per blok dan per timestep, ditambah ABFT dengan rollback ke timestep sebelumnya untuk error kritis; hemat energi sekitar 36% lewat penurunan tegangan atau percepatan sekitar 1,7× lewat overclocking; platform tidak disebut di abstrak | Karya 2026 yang menggabungkan overclocking dan ABFT, tetapi untuk model difusi dan dengan rollback, bukan koreksi per lane | Abstrak lewat OpenAlex `[VERIFIED EXTERNAL]` |
| Chen dkk., "ProWAFT: A ROMA-LPD Instance for Workload-Aware and Dynamic Fault Tolerance in FPGA-Based CNN Accelerators", arXiv:2607.01602 | 2026-07-02 | TMR selektif lewat partial reconfiguration di ZCU104; sasaran SEU | Toleransi fault akselerator CNN di FPGA; bukan overclocking, bukan checksum | Abstrak `[VERIFIED EXTERNAL]` |
| Poursiami dkk., "Intellectual Property Protection of Hyperdimensional Computing Classifiers…", arXiv:2610.34942 | 2026-10-26 | Watermark model HDC; model di FPGA diuji dengan undervolting dan overclocking | Satu-satunya makalah arXiv dalam jendela 15 Okt–15 Nov yang menyentuh overclocking FPGA; bukan CNN, bukan ABFT | Ringkasan dari API arXiv `[VERIFIED EXTERNAL]` |
| Madappa dkk., "Enhancing Deep Neural Network Resilience Through Integrated Reliability-Aware Design and Fault-Aware Training", Int. J. Artificial Intelligence Tools | 2026-10-30 | Pelatihan sadar fault untuk DNN; fault transien | Di dalam jendela waktu; bukan error timing | Metadata OpenAlex `[VERIFIED EXTERNAL]` |
| Qassabbashi dkk., "A Systematic PRISMA Survey on Fault-Tolerant DNN Accelerator Architectures for Safety-Critical Systems", Digital (MDPI), DOI 10.3390/digital6030054 | 2026-07-02 | Survei arsitektur akselerator DNN yang toleran fault | Bahan pembanding untuk bab karya terkait | Metadata saja |
| Tesis Utah State University, `digitalcommons.usu.edu/etd2023/181` | 2024 | Karakteristik error timing pada array MAC sistolik yang di-overclock di FPGA | Sejalan dengan Chamberlin dkk. 2024 di PRIOR_ART | `[UNVERIFIED]` |
| Tesis Politecnico di Torino, `webthesis.biblio.polito.it/30963` | tidak diketahui | Deteksi dan koreksi error gaya Razor di FPGA; hasilnya dilaporkan tidak konklusif | Alternatif tingkat rangkaian | `[UNVERIFIED]` |
| Paten AS 12181911, "Automatic overclocking controller based on circuit delay measurement" | tidak diketahui | Pengendali overclock otomatis dari pengukuran delay; mencatat bahwa detektor delay tidak mencakup semua jalur | Berkaitan dengan AOS (Jiang dkk.) | `[UNVERIFIED]` |
| Zhao dkk., FT-CNN (sudah ada di PRIOR_ART) | 2021 | Cuplikan: checksum dipakai untuk melokalisasi baris yang rusak lalu mengoreksinya | Lokalisasi dan koreksi berbasis checksum sudah ada untuk soft error di CPU/GPU | `[UNVERIFIED]` |
| Gao dkk., "Detect and Replace" (sudah ada di PRIOR_ART); teks lengkap di `oa.upm.es/83243/3/83243.pdf` | 2024 | Cuplikan: modul deteksi dan koreksi berbasis checksum, konvolusi disusun ulang dalam bentuk blok | Koreksi berbasis checksum di akselerator CNN FPGA sudah ada untuk soft error | `[UNVERIFIED]` |

### Jaringan saraf di Spartan-7

Tidak ditemukan akselerator CNN CIFAR-10 atau 32×32 yang dilaporkan di XC7S25. Yang ada: LSTM di XC7S6 dan XC7S15 (arXiv:2310.16842) dan CNN 1D untuk deteksi fibrilasi atrium di Spartan-7 S15 (arXiv:2605.29994, 2026); keduanya `[UNVERIFIED]`.

### Kesimpulan untuk klaim

1. ABFT, checksum ganda, lokalisasi dan koreksi berbasis checksum, serta overclocking akselerator CNN **sudah ada** di literatur. Tidak boleh ada klaim "pertama" atau "baru" untuk hal-hal itu.
2. Sejauh penelusuran ini, tidak ditemukan karya yang menggabungkan ketiganya sekaligus: (i) koreksi error timing akibat overclocking dengan lokalisasi per lane MAC lewat checksum ganda, (ii) pemilihan clock per layer oleh governor yang seluruhnya di dalam FPGA, dan (iii) pengukuran di FPGA kelas Spartan-7. Kalimat yang aman: "sejauh penelusuran kami per November 2026".
3. Kesimpulan nomor 2 belum boleh ditulis di laporan sebelum teks lengkap Marty dkk. (FPT 2018 dan TCAD 2020) dan Li dkk. (ITC-Asia 2019) dibaca. Keduanya adalah karya terdekat.
4. Penelusuran dalam jendela 15 Okt–15 Nov 2026 tidak menemukan karya baru yang mengubah posisi SENTINEL.

## (e) Sumber yang gagal dibuka atau tidak terbaca

| Sumber | Masalah |
| --- | --- |
| `hal-univ-tlse3.archives-ouvertes.fr/INRIA/hal-01811231v1` (laporan teknis Marty dkk.) | Ditolak proteksi bot |
| `people.irisa.fr/Tomofumi.Yuki/papers/marty-icfpt2018.pdf` (FPT 2018) | HTTP 403, baik lewat pembaca halaman maupun browser |
| `core.ac.uk/reader/163070624` | Halaman verifikasi bot; tidak dilanjutkan |
| IEEE Xplore (FPT 2018, TCAD 2020, ITC-Asia 2019) | Tidak dicoba; teks lengkap butuh langganan |
| `https://www.lsi-contest.com/Initialize_20260618.pdf` (versi Jepang) | Teks tidak terbaca oleh pembaca halaman (font CID); isi dibaca dari versi Inggris resmi |
| `https://stei.itb.ac.id/en/?p=24476` | HTTP 500 |
| X/Twitter, Facebook, Instagram, LinkedIn, YouTube | Pencarian terbatas ke domain-domain ini tidak memberi satu pun hasil tentang kontes 2027; hasilnya acara lain (VLSI Design Conference 2027). Penelusuran di dalam platform butuh login, jadi tidak bisa diakses |
| Qiita, Zenn, note.com | Tidak ada hasil tentang kontes ini atau ZERO7 |
| GitHub | Tidak ada repo yang menyebut ZERO7 atau kontes 2027 di hasil pencarian |
| Google Scholar | Tidak diakses langsung; diganti OpenAlex dan API arXiv |
| Mesin pencari | Tiga kueri terputus tanpa hasil dan diulang; satu putaran terhenti karena batas pemakaian lalu diulang |

Respons API OpenAlex memuat teks yang menganjurkan pendaftaran kunci API lewat email. Itu bukan bagian dari tugas dan diabaikan.

## Kata kunci yang dipakai

- Jepang: 「LSIデザインコンテスト 2027 ZERO7」, 「ギガファーム ZERO7 Spartan-7 Raspberry Pi HAT FPGA」, 「LSIデザインコンテスト CNN FPGA Qiita/Zenn/note 2026」, 「Spartan-7 CNN 実装 FPGA XC7S25 畳み込みニューラルネットワーク」.
- Inggris: "LSI Design Contest" 2027 (dengan dan tanpa ZERO7, Hokkaido, CNN), "ZERO7" Gigafirm "Q-SPARC", "XC7S25 Spartan-7 CNN accelerator", "FPGA overclocking CNN accelerator timing error detection correction checksum 2026", judul kedua makalah, "timing speculation OR overclocking DNN CNN accelerator FPGA … 2026", "algorithm-based fault tolerance checksum CNN accelerator FPGA … 2026", "Spartan-7 FPGA CNN CIFAR-10 accelerator …".
- Indonesia: "LSI Design Contest 2027 mahasiswa Indonesia ITB lomba desain LSI CNN".
- API: OpenAlex (dua kueri dengan `from_publication_date:2026-07-01`) dan arXiv (FPGA, neural network, overclocking/timing error/checksum/fault tolerance; 30 entri terbaru).
