# BOARD_INFO — ZERO7

Isi file ini hanya dengan fakta yang punya sumber: dokumen resmi panitia atau Gigafirm, skematik, atau pengukuranmu sendiri. Jangan menebak.
Fase BOARD baru boleh dimulai jika semua field **wajib** terisi (tidak ada `UNKNOWN`) dan kamu menulis "board siap" ke Claude Code.

Terakhir diperbarui: 2026-11-16, dari dokumen resmi yang terbit 10 Nov 2026. Board fisik belum ada.

Rujukan singkat:
- **TK-n**: `docs/official/ZERO7FPGA_Connection-table_261109_001.pdf`, halaman n.
- **IN-n**: `docs/official/Initialize_20260618_EN.pdf`, slide n.
- **G-n**: `docs/official/GUIDE_LSI_2027_FINALE.pdf`, halaman n.
- **VIVADO**: basis data device Vivado 2025.2, lewat `results/vivado/part_check.txt` dan `results/vivado/pin_check.txt`. Ini fakta tentang chip, bukan tentang board.

## Field wajib

| Field | Nilai | Sumber |
| --- | --- | --- |
| Nama dan revisi board | ZERO7 buatan Gigafirm; sablon board "Q-SPARC ZERO7" [OFFICIAL]. Revisi: UNKNOWN (foto resmi menunjukkan dua tampilan board, putih dan kuning) | G-3, G-4; IN-41, IN-42 |
| Part number FPGA lengkap (contoh format: xc7sXX-Npkg) | xc7s25csga225-1 [OFFICIAL] | G-3, G-5, G-6; IN-14, IN-24, IN-25 |
| Speed grade | -1 [OFFICIAL] | IN-25 ("Speed Grade: -1"); nama part |
| Cara konfigurasi FPGA (JTAG, flash SPI, lewat Pi, dll.) | JTAG dari Vivado Hardware Manager [OFFICIAL]. Flash QSPI (IC2) dan DIP mode SW7 (MODE0–MODE2) ada di tabel koneksi [OFFICIAL]; posisi SW7 dan cara boot dari flash: UNKNOWN | IN-42 sampai IN-50; TK-3 sampai TK-6 |
| Alat programming (Vivado Hardware Manager + kabel, openFPGALoader, dll.) | Vivado 2025.2 Hardware Manager dengan kabel Digilent JTAG-HS3, disambung ke pin JTAG ZERO7 memakai kabel jumper (Vref, TMS, TCK, TDO, TDI, GND); clock JTAG 3.000.000 Hz [OFFICIAL]. Teks slide menulis "JTAG-H53"; fotonya menunjukkan "JTAG-HS3 Rev. A" | IN-42, IN-46 |
| Clock input ke FPGA: pin dan frekuensi (F_IN) | Pin B13, net CLK20M dari X1 [OFFICIAL]. 20 MHz pada 3,3 V menurut komentar `##Clock (20MHz, 3.3V)` di `Zero7.xdc` yang terlihat pada tangkapan layar [OFFICIAL]. B13 adalah `IO_L13P_T2_MRCC_15`, clock-capable [VIVADO] | TK-1; IN-31; pin_check |
| SPI Pi ↔ FPGA: pin FPGA untuk SCLK, MOSI, MISO, CS | SPI0: SCLK = GPIO11 = A8; MOSI = GPIO10 = A6; MISO = GPIO9 = A7; CE0 = GPIO8 = D9; CE1 = GPIO7 = C10 [OFFICIAL] | TK-1, TK-2; fungsi GPIO dari IN-59 |
| Bank I/O dan tegangan untuk pin SPI | Bank 15, jenis HR [OFFICIAL; VIVADO]. Tegangan VCCO bank 15 tidak ditulis di dokumen: UNKNOWN. Dugaan 3,3 V [INFERENCE] dari komentar clock "3.3V" (B13 juga di bank 15) dan dari GPIO Raspberry Pi yang 3,3 V | TK-1 sampai TK-3 (B7, C11, F12 = BANK15_VCCO); IN-31 |
| Pin LED1–LED4 | LED1 = WS2812B di N1 (net S7_LED0, juga ke J7); LED2 = WS2812B di D7 (net RP_GPIO18, juga ke J6, J15, J11) [OFFICIAL]. LED3 dan LED4: UNKNOWN (tidak ada di tabel koneksi FPGA). LED biasa: D5 = R3 (GPIO_LED1), D6 = R2 (GPIO_LED2), D3 biru = A10 (RP_GPIO6), D9 hijau = B10 (RP_GPIO13), D8 merah = B11 (RP_GPIO19), D1 = DONE [OFFICIAL] | TK-1, TK-2, TK-3, TK-5, TK-6; G-3 |
| File XDC atau skematik resmi (lokasi file) | `Zero7.xdc` disebut dan terlihat sebagian di panduan, tetapi filenya belum diterbitkan: UNKNOWN. Skematik: UNKNOWN. Sementara dipakai `board/zero7.xdc`, disusun dari tabel koneksi | IN-19, IN-31 |

## Info tim, 17 Nov 2026

Informasi dari tim, belum dari dokumen resmi. Diberi label [TEAM] dan tidak dipakai sebagai sumber field wajib.

| Hal | Isi | Sumber |
| --- | --- | --- |
| Kabel JTAG | Kabel yang dipakai tim: Digilent JTAG-HS2 Rev. A [USER, foto]. Label header 6 pin di casing, dari atas ke bawah: TMS, TDI, TDO, TCK, GND, VDD; PCB bertanda "JTAG 14PA DIGILENT Inc.". Panduan resmi memakai JTAG-HS3 (IN-42). Info 17 Nov 2026 bahwa HS3 diberikan satu set dengan board diganti oleh info ini | user, foto, 18 Nov 2026 |
| Raspberry Pi | Setiap kelompok memakai Raspberry Pi 4 milik sendiri [TEAM]. Kompatibilitas Pi 4 dengan ZERO7: [UNKNOWN] sampai panitia menjawab | info tim, 17 Nov 2026 |
| Jadwal | ZERO7 dan kabel JTAG tersedia mulai 20 Nov 2026; Raspberry Pi 4 mungkin datang lebih lambat [TEAM] | info tim, 17 Nov 2026 |
| Daya tanpa Pi | Dokumen resmi hanya menyebut daya dari header GPIO Raspberry Pi (IN-41: "When Raspberry Pi is powered on, the LED on ZERO7 lights up"). Cara lain: [UNKNOWN], tanyakan ke panitia | IN-41; OCR semua halaman TK dan IN, 17 Nov 2026 |

## Field opsional

| Field | Nilai | Sumber |
| --- | --- | --- |
| Pin GPIO tambahan Pi ↔ FPGA (IRQ/DONE) | RP_GPIO2 sampai RP_GPIO27 semuanya tersambung ke FPGA [OFFICIAL]; daftar di bawah. Pilihan pin untuk sinyal selesai ditetapkan lewat ADR | TK-1, TK-2 |
| Antarmuka controller LED RGB (protokol, pin) | WS2812B. LED1 di N1 dikendalikan FPGA; LED2 di D7 berbagi jalur dengan RP_GPIO18 [OFFICIAL]. Jumlah LED per rantai dan urutan warna: UNKNOWN | TK-2, TK-5 |
| Tombol, DIP switch, pin PMOD1/PMOD2 | SW5 START = C14 (RP_GPIO20); SW4 STOP = B15 (RP_GPIO21); SW6 RUN = C13 (RP_GPIO16); SW1 = R4 (GPIO_PSW); SW3 DIP = M4 (GPIO_DIPSW); SW2 = PROG; SW7 DIP = MODE0, MODE1, MODE2 (M5, N5, M6). PMOD1 (J1) pin 1–8 = D15, E15, F15, G15, E13, E14, F14, G14. PMOD2 (J2) pin 1–8 = G13, G11, E11, D12, G12, F11, E12, D13 [OFFICIAL]. Polaritas tombol dan pull-up/pull-down: UNKNOWN | TK-1 sampai TK-6 |
| Apakah chip punya XADC (sensor suhu internal) | Ada: Hardware Manager menampilkan "XADC (System Monitor)" untuk xc7s25 [OFFICIAL, tangkapan layar]. Input analog AIN32_P/N = A13/A14 (fungsi AD5P/N) dan AIN33_P/N = A11/A12 (fungsi AD12P/N) [OFFICIAL; VIVADO]. Rangkaian referensi dan rentang tegangan input: UNKNOWN | IN-48, IN-50; TK-1; pin_check |
| Jumlah CMT/MMCM di chip | 3 MMCM menurut basis data part [VIVADO]. DS180 belum dicek | part_check |
| Kecepatan SPI stabil yang terukur | UNKNOWN | ukur saat bring-up |
| Cara mengukur daya (USB power meter, dll.) | UNKNOWN | |
| Model Raspberry Pi yang dipakai dan versi OS | Raspberry Pi 4 Model B milik kelompok [USER, 2026-11-16; info tim, 17 Nov 2026] (ADR-022). Kompatibilitas dengan ZERO7: [UNKNOWN], menunggu konfirmasi panitia. Panitia hanya menyebut Raspberry Pi 5 [OFFICIAL: board pinjaman "can be connected to a Raspberry Pi 5"]. Kecocokan header 40-pin dan nomor GPIO Pi 4 dengan Pi 5: [INFERENCE], dicek fisik saat board datang. Versi OS: UNKNOWN; contoh resmi berjalan dengan Python 3.13.5 dan `gpiozero` | G-6; IN-9; user |
| Modul kamera yang dipakai | UNKNOWN | |
| Clock eksternal | EXT_CLK = H1 (`IO_L12P_T1_MRCC_34`) ke J16 [OFFICIAL; VIVADO] | TK-3; pin_check |
| I2C | FPGA_SDA = H3, FPGA_SCL = H4 ke U11; RP_GPIO2 = B1 dan RP_GPIO3 = B2 ke J6 dan U11 [OFFICIAL]. Fungsi U11: UNKNOWN | TK-1, TK-3 |
| UART Pi | GPIO14 (TXD) = B6, GPIO15 (RXD) = C7 [OFFICIAL] | TK-1, TK-2; IN-59 |
| Pin konfigurasi | CFGBVS dan VCCO bank 0 (E6, P5) ke VCC3V3; DONE = G5 ke D1; PROG = J5 ke SW2; INIT = L5; PUDC_B = K11 ke BANK14_VCCO; JTAG: TCK = E5, TDO = K4, TMS = K5, TDI = L4 [OFFICIAL] | TK-2 sampai TK-6 |
| Flash QSPI | QSPI_SCK = F5, DQ0 = H14, DQ1 = H15, DQ2 = J12, DQ3 = K13, CS = L11 ke IC2 [OFFICIAL]. Jenis dan kapasitas flash: UNKNOWN | TK-3 sampai TK-5 |
| Jumper potong | JP9(CUT) pada A6 dan H15; JP10(CUT) pada H15; JP11(CUT) pada A8, F5, K12; JP12(CUT) pada F5, K12 [OFFICIAL]. Arti "(CUT)" dan keadaan bawaannya: UNKNOWN | TK-1, TK-3, TK-4 |
| Net lain | HDMI_* di bank 34 (J3) dan HDMI_*_LS di bank 14 (J4); CTRL_EN = C6, CTRL_R1 = H13, CTRL_R2 = H12 ke P1 [OFFICIAL]. Fungsinya: UNKNOWN; tidak dipakai SENTINEL | TK-1 sampai TK-6 |

## Pin Raspberry Pi ke FPGA

[OFFICIAL] TK-1 dan TK-2. Kolom "Juga tersambung ke" memuat komponen lain di jalur yang sama.

| GPIO | Pin FPGA | Bank | Juga tersambung ke |
| --- | --- | --- | --- |
| 2 | B1 | 34 | U11 |
| 3 | B2 | 34 | U11 |
| 4 | A2 | 34 | |
| 5 | A9 | 15 | |
| 6 | A10 | 15 | D3 (biru) |
| 7 | C10 | 15 | |
| 8 | D9 | 15 | |
| 9 | A7 | 15 | |
| 10 | A6 | 15 | JP9(CUT) |
| 11 | A8 | 15 | JP11(CUT) |
| 12 | D10 | 15 | |
| 13 | B10 | 15 | D9 (hijau) |
| 14 | B6 | 15 | |
| 15 | C7 | 15 | |
| 16 | C13 | 15 | SW6 (RUN) |
| 17 | A3 | 34 | |
| 18 | D7 | 15 | J15, J11, LED2 (WS2812B) |
| 19 | B11 | 15 | D8 (merah) |
| 20 | C14 | 15 | SW5 (START) |
| 21 | B15 | 15 | SW4 (STOP) |
| 22 | A5 | 15 | |
| 23 | C8 | 15 | |
| 24 | D8 | 15 | |
| 25 | C9 | 15 | |
| 26 | B12 | 15 | |
| 27 | A4 | 34 | |

## Fakta lain yang sudah diketahui

- [OFFICIAL] ZERO7 adalah HAT Raspberry Pi di header GPIO 40-pin. Diagram arsitektur menunjukkan LED1–LED4, PMOD1, PMOD2, dua antarmuka 1,8 V, ROM, serta GPIO, SPI, UART, dan I2C ke Raspberry Pi (G-3).
- [OFFICIAL] Saat Raspberry Pi diberi daya, LED di ZERO7 menyala (IN-41).
- [OFFICIAL] Di Hardware Manager, device terbaca sebagai `xc7s25_0` dengan ID code `037C4093` dan panjang IR 6 (IN-46).
- [OFFICIAL, tangkapan layar Vivado; VIVADO] Resource xc7s25csga225-1: 14.600 LUT, 29.200 flip-flop, 45 block RAM, 80 DSP, 150 IOB tersedia, 225 pin (IN-24; part_check).
- [OFFICIAL] Contoh resmi memakai `raspi-zer07_button.py`, `pi_button_receiver.v`, dan `Zero7.xdc` "provided in the same folder as this manual"; ketiganya belum ditemukan di situs (IN-7, IN-19).
- [OFFICIAL] Panduan menyebut "Refer to the ZERO7 User Manual" (IN-14); dokumen itu belum tertaut di situs.
- [VERIFIED EXTERNAL] Situs Gigafirm mencantumkan "ZERO7 AMD Spartun-7 Board" (ejaan sesuai halaman) sebagai produk baru bertanggal 25.7.1, tanpa spesifikasi.
- Kontak peminjaman untuk Indonesia: Prof. Trio Adiono, ITB (tadiono@itb.ac.id), judul email "Zero7 board Univ. name Your name" [OFFICIAL, G-2].

## Yang masih harus dipastikan sebelum fase board

1. File `Zero7.xdc` resmi, terutama IOSTANDARD dan tegangan VCCO bank 14, 15, dan 34.
2. ZERO7 User Manual dan, jika ada, skematik.
3. Fungsi pin VDD JTAG-HS2 (masukan tegangan referensi target, padanan VREF HS3 [INFERENCE]) dan rentang tegangannya, dari manual resmi Digilent; halaman Digilent menolak akses otomatis (HTTP 403), jadi belum dicek.
4. Polaritas tombol, jumlah LED WS2812B per rantai, dan arti jumper "(CUT)".
5. Posisi DIP SW7 untuk boot dari JTAG dan dari flash QSPI.

## Observasi lama (sudah terjawab)

- 2026-11-09: foto chip buram dari user terbaca `XC7S?5` dan `CSGA225`. Dugaan saat itu XC7S25 CSGA225. Dokumen resmi 10 Nov 2026 memastikan part-nya xc7s25csga225-1.
