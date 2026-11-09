# Dokumen resmi dan arsip

| File | Isi | Catatan |
| --- | --- | --- |
| `GUIDE_LSI_2027.pdf` | 4 halaman situs lsi-contest.com untuk kontes 2027 | Berupa gambar, jadi harus dibaca secara visual. Sumber aturan 2027 [OFFICIAL]. |
| `A_Overview_LSI_2019.pdf` | Design specification kontes ke-23 (2020, Okinawa) | Nama file menyebut 2019, tapi isinya spesifikasi kontes ke-23. Panduan 2027 merujuk ke dokumen ini untuk struktur CNN. Isinya [HISTORICAL]. |
| `CNN_Example_2019.pdf` | Slide pengajaran CNN (contoh pengenalan ○/×) | Materi belajar [HISTORICAL]. |
| `CNN_2019.zip` | Contoh kode MATLAB/Octave untuk training dan inferensi CNN kecil | Analisis sebelumnya menemukan turunan sigmoid diterapkan dua kali pada backprop layer konvolusi. Jangan dijadikan acuan aritmetika. |

## Ringkasan aturan 2027 dari GUIDE_LSI_2027.pdf

Verifikasi ulang dengan membaca PDF-nya.

- **Tujuan:** implementasi hardware CNN, dengan dua syarat: data validasi yang ditentukan panitia dan input kamera real-time.
- **Hari lomba:** gambar validasi diberikan pada hari lomba. Sistem membacanya dari kamera, kartu SD, dll., lalu mengenalinya. Presentasi menunjukkan seberapa cepat hasil keluar.
- **Input:** CNN menerima gambar 32×32. Dataset dan target pengenalan diumumkan kemudian.
- **Struktur:** mengacu ke design overview kontes ke-23; struktur hidden layer dan detail lain bebas.
- **Class 1 (klasifikasi gambar, board bebas):**
  - Level 1: CNN sederhana, misalnya input 3×3.
  - Level 2: CNN untuk input 32×32, dengan training dan validasi.
  - Level 3: bebas, selama klasifikasi gambar.
- **Class 2 (hanya ZERO7, tugas bebas):** hanya Level 3.
- **Lingkungan desain:** Synplify, Design Compiler, MATLAB/Simulink, Vivado, alat sintesis lain, RTL tulis tangan (VHDL atau Verilog). Lingkungan lain juga boleh.
- **Kontak peminjaman ZERO7:** Indonesia ke Prof. Trio Adiono, ITB (tadiono@itb.ac.id); negara lain ke support@LSI-contest.com.
