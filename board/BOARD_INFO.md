# BOARD_INFO — ZERO7

Isi file ini hanya dengan fakta yang punya sumber: dokumen resmi panitia atau Gigafirm, skematik, atau pengukuranmu sendiri. Jangan menebak.
Fase BOARD baru boleh dimulai jika semua field **wajib** terisi (tidak ada `UNKNOWN`) dan kamu menulis "board siap" ke Claude Code.

Terakhir diperbarui: 2026-11-09

## Field wajib

| Field | Nilai | Sumber |
| --- | --- | --- |
| Nama dan revisi board | UNKNOWN | |
| Part number FPGA lengkap (contoh format: xc7sXX-Npkg) | UNKNOWN | |
| Speed grade | UNKNOWN | |
| Cara konfigurasi FPGA (JTAG, flash SPI, lewat Pi, dll.) | UNKNOWN | |
| Alat programming (Vivado Hardware Manager + kabel, openFPGALoader, dll.) | UNKNOWN | |
| Clock input ke FPGA: pin dan frekuensi (F_IN) | UNKNOWN | |
| SPI Pi ↔ FPGA: pin FPGA untuk SCLK, MOSI, MISO, CS | UNKNOWN | |
| Bank I/O dan tegangan untuk pin SPI | UNKNOWN | |
| Pin LED1–LED4 | UNKNOWN | |
| File XDC atau skematik resmi (lokasi file) | UNKNOWN | |

## Field opsional

| Field | Nilai | Sumber |
| --- | --- | --- |
| Pin GPIO tambahan Pi ↔ FPGA (IRQ/DONE) | UNKNOWN | |
| Antarmuka controller LED RGB (protokol, pin) | UNKNOWN | |
| Tombol, DIP switch, pin PMOD1/PMOD2 | UNKNOWN | |
| Apakah chip punya XADC (sensor suhu internal) | UNKNOWN | cek DS180 setelah part diketahui |
| Jumlah CMT/MMCM di chip | UNKNOWN | cek DS180 setelah part diketahui |
| Kecepatan SPI stabil yang terukur | UNKNOWN | ukur saat bring-up |
| Cara mengukur daya (USB power meter, dll.) | UNKNOWN | |
| Model Raspberry Pi yang dipakai dan versi OS | UNKNOWN | |
| Modul kamera yang dipakai | UNKNOWN | |

## Fakta yang sudah diketahui (2026-11-09)

- [OFFICIAL] ZERO7 adalah HAT Raspberry Pi di header GPIO 40-pin, dengan FPGA AMD Spartan-7. Terhubung ke Pi lewat GPIO, SPI, UART, dan I2C. Ada PMOD1, PMOD2, dua antarmuka 1,8 V, LED1–LED4, dan ROM (Gambar 1 di panduan 2027).
- [OFFICIAL] Spesifikasi dan lingkungan pengembangan ZERO7 "akan diposting" oleh panitia; belum ada per 9 Nov 2026.
- [VERIFIED EXTERNAL] Gigafirm (Iizuka, Fukuoka) memamerkan ZERO7 berukuran 60×30 mm dengan controller LED warna penuh.
- Kontak peminjaman: support@LSI-contest.com, atau untuk Indonesia Prof. Trio Adiono (tadiono@itb.ac.id).
