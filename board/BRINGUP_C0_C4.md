# Panduan bring-up C0–C4: Raspberry Pi 5, ZERO7, SEGGER J-Link

Panduan langkah demi langkah untuk checkpoint C0 sampai C4 dari `PROMPT_BRINGUP_ZERO7_PI5_JLINK` (26 Nov 2026).
Kerjakan **satu langkah, lalu laporkan hasilnya** (angka, foto, atau screenshot) sebelum lanjut. Sebuah langkah dianggap
LULUS hanya setelah hasilnya dilaporkan dan dicek. C5 dan seterusnya (menyambung J-Link) **tidak** termasuk di sini dan
menunggu hasil C4 serta konfirmasimu. Fase BOARD resmi (CLAUDE.md §8) baru dimulai setelah kamu menulis "board siap".

Label: [OFFICIAL] dokumen panitia, SEGGER, atau Raspberry Pi; [INFERENCE] dugaan beralasan; [UNKNOWN] belum diketahui;
[HW] hasil ukur atau uji yang kamu laporkan.

---

## Aturan keselamatan (baca sebelum setiap langkah)

1. **Matikan daya** sebelum menyentuh kabel, jumper, atau konektor. Header GPIO Pi dan header JTAG tidak boleh dicolok atau
   dicabut saat menyala.
2. Daya hanya dari **adaptor resmi Pi 5 (5 V 5 A)**. ZERO7 mendapat daya **hanya lewat header Pi** [OFFICIAL, panduan hlm. 41].
   **Jangan** memakai colokan "DC 5V" di ZERO7 [UNKNOWN sampai panitia menjawab].
3. **Jangan** memotong, menyolder, atau menyambung jumper bertanda CUT (JP9, JP10, JP11, JP12) [OFFICIAL, tabel koneksi].
   Jangan mengubah apa pun di board.
4. **Jangan** memberi sinyal atau tegangan dari luar ke pin FPGA sebelum tegangan bank pin itu terukur (C4).
5. Probe multimeter hanya ke pin konektor, titik uji, atau kaki komponen yang jelas, tidak ke bola BGA atau pin chip yang
   rapat. Satu probe menyentuh satu titik saja.
6. Sentuh benda logam ber-ground dulu (anti statis), jangan bekerja di atas karpet, pegang board di tepinya.
7. **Bau terbakar, komponen panas, LED aneh, atau tegangan tidak sesuai → cabut adaptor segera** dan laporkan sebelum
   menyalakan lagi.

---

## Fakta yang sudah dibaca dari sumber resmi

| Hal | Isi | Sumber |
| --- | --- | --- |
| Pin JTAG di FPGA | TCK = E5 dan TDO = K4 lewat U8; TMS = K5 dan TDI = L4 lewat U7 | [OFFICIAL] tabel koneksi |
| Tegangan bank 0 (bank pin JTAG) | VCCO bank 0 (E6, P5) dan CFGBVS (H5) ke VCC3V3 | [OFFICIAL] tabel koneksi |
| VCCO bank 14 / 15 / 34 | Pin: bank 14 J14, M12, P9; bank 15 B7, C11, F12; bank 34 C3, G2, L3. **Nilainya tidak tertulis** | [OFFICIAL] pin, [UNKNOWN] nilai |
| Clock dan LED | CLK20M = B13; GPIO_LED1 = R3 (D5); GPIO_LED2 = R2 (D6) | [OFFICIAL] tabel koneksi |
| SPI0 dari Pi | MOSI RP_GPIO10 = A6 (JP9 CUT); MISO RP_GPIO9 = A7; SCLK RP_GPIO11 = A8 (JP11 CUT); CE0 RP_GPIO8 = D9 | [OFFICIAL] tabel koneksi |
| Kabel JTAG panduan | Enam kabel: Vref, GND, TCK, TDO, TDI, TMS, ke header di board **kuning** dekat "DC 5V"; clock JTAG 3 MHz | [OFFICIAL] panduan hlm. 42 |
| Board tim | **Putih**; header JTAG belum teridentifikasi. Kandidat: P2 (10 pin) di samping U7/U8 | [INFERENCE], `board/BOARD_INFO.md` |
| Konektor 20 pin J-Link | 1 VTref (masukan tegangan acuan target); 5 TDI; 7 TMS; 9 TCK; 13 TDO; 4, 6, 8, 10, 12 GND; 19 keluaran 5 V (**tidak pernah disambung**) | [OFFICIAL] kb.segger.com "20-pin J-Link Connector" |
| J-Link XVCD Server | Software J-Link ≥ V7.92d, port 2542; dukungan ILA tidak disebut | [OFFICIAL] kb.segger.com "J-Link XVCD Server"; ILA [UNKNOWN] |

---

## C0 — Persiapan (semua langkah: **[DAYA MATI]**)

**Tujuan:** tahu alat yang dipakai, menemukan header JTAG di board putih, dan menyusun tabel kabel J-Link → ZERO7 yang kamu
setujui. Belum ada yang disambung atau dinyalakan.

### C0-1 Data alat dan foto
1. Baca stiker di bawah J-Link: tulis **model** dan **versi hardware** (contoh: "J-Link BASE V11"). Tulis merek dan model
   multimeter.
2. Foto ZERO7 utuh dari **atas** dan dari **bawah** (terang, tajam, tulisan kecil terbaca, tanpa flash, cahaya dari samping).
3. Foto dekat header **P2** dan **P1** beserta tulisan di sekitarnya, dan chip **U7** serta **U8** sampai kodenya terbaca.
4. Foto konektor 20 pin J-Link dan kabelnya, dengan tanda **pin 1** terlihat (segitiga kecil, atau garis merah di kabel pita).

- Hasil yang diharapkan: semua tulisan terbaca; mungkin ada label TCK/TMS/TDI/TDO/VREF atau "JTAG" di dekat salah satu header.
- Tanda gagal: foto buram (ulangi). Tidak ada label sinyal sama sekali bukan kegagalan; lanjut ke C0-2.
- Kirim: model dan versi J-Link, model multimeter, 5–6 foto.

### C0-2 Identifikasi header JTAG (dikerjakan bersama setelah C0-1)
Dari foto C0-1 kita cocokkan: (a) tulisan di board, (b) kode chip U7/U8 dan datasheet resminya, (c) bila perlu uji
kontinuitas **dengan daya mati** dari pin header ke jalur JTAG (dilakukan di C2). Jika tetap tidak pasti, kirim pertanyaan
ke panitia (draf disiapkan). **Pin yang tidak dipakai panduan tidak boleh disambung.**

### C0-3 Tabel kabel J-Link → ZERO7 (diisi setelah C0-2, lalu kamu setujui)

| Sinyal | Pin J-Link 20 pin [OFFICIAL SEGGER] | Pin header ZERO7 | Bukti untuk pin ZERO7 |
| --- | --- | --- | --- |
| VTref | 1 | [UNKNOWN] | |
| GND | 4 (atau 6, 8, 10, 12) | [UNKNOWN] | |
| TCK | 9 | [UNKNOWN] | |
| TDO | 13 | [UNKNOWN] | |
| TDI | 5 | [UNKNOWN] | |
| TMS | 7 | [UNKNOWN] | |
| (pin 19, 5 V) | 19 | **tidak disambung** | |

**C0 LULUS** bila: header JTAG teridentifikasi dengan bukti, dan tabel di atas lengkap dan kamu setujui.

---

## C1 — Pi 5 berjalan sendiri (ZERO7 **belum** dipasang)

### C1-1 Tulis OS ke flashdisk (di laptop) **[DAYA MATI]** untuk Pi
1. Instal **Raspberry Pi Imager** dari situs resmi Raspberry Pi.
2. Pilih: Device **Raspberry Pi 5**, OS **Raspberry Pi OS (64-bit)**, Storage **flashdisk** kamu (pastikan bukan disk lain).
3. Di pengaturan OS (Edit settings): isi **hostname** (misalnya `sentinel-pi`), **username dan password**, **Wi-Fi**
   (nama dan sandi, negara ID), dan aktifkan **SSH** (password authentication). Simpan, lalu tulis.

- Hasil: Imager melaporkan "Write Successful".
- Kirim: screenshot hasil Imager (sembunyikan password).

### C1-2 Boot pertama **[DAYA MATI → NYALA]**
1. Pastikan **tidak ada SD card** di Pi (SD card didahulukan saat boot) [INFERENCE].
2. Colok flashdisk ke **port USB 3 (biru)**. Belum ada apa pun di header GPIO.
3. Colok adaptor 5 V 5 A. Tunggu 2–3 menit.

- Hasil: LED hijau Pi berkedip lalu stabil; perangkat muncul di jaringan Wi-Fi.
- Tanda gagal: LED hijau tidak aktif atau berkedip berpola → cabut daya, laporkan pola kedipnya (bootloader lama bisa
  diperbarui lewat Imager: *Misc utility images → Bootloader*).
- Kirim: keterangan LED.

### C1-3 SSH dari laptop
1. Di PowerShell laptop: `ssh <username>@sentinel-pi.local` (ganti hostname bila berbeda).
2. Setelah masuk: `cat /proc/device-tree/model` dan `uname -a`.

- Hasil: muncul "Raspberry Pi 5 Model B …".
- Tanda gagal: hostname tidak ditemukan → cari alamat IP Pi di halaman router, lalu `ssh <username>@<IP>`.
- Kirim: keluaran kedua perintah.

### C1-4 Aktifkan SPI dan pasang paket
1. `sudo raspi-config` → *Interface Options* → *SPI* → *Yes*, lalu `sudo reboot`. Setelah SSH lagi: `ls /dev/spidev*`.
2. `sudo apt update && sudo apt install -y python3-gpiozero python3-lgpio python3-spidev git`
   (di Pi 5 GPIO memakai lgpio; RPi.GPIO tidak dipakai, ADR-033).

- Hasil: `ls` menampilkan `/dev/spidev0.0` (dan `/dev/spidev0.1`); apt selesai tanpa error.
- Kirim: keluaran `ls /dev/spidev*` dan baris terakhir apt.

### C1-5 Cek dengan skrip proyek (hanya membaca, tidak menyentuh GPIO)
1. Salin repo ke Pi (`git clone` dari remote tim, atau salin folder `board/` lewat `scp`).
2. Jalankan `python3 board/pi_check.py`.

- Hasil: baris `model`, `spidev0.0`, `spidev`, `gpiozero`, `lgpio` berstatus ok (`picamera2` dan `cv2` boleh "missing":
  kamera tidak dipakai, ADR-035).
- Kirim: seluruh keluaran.

**C1 LULUS** bila: SSH berjalan, `/dev/spidev0.0` ada, `pi_check.py` menunjukkan gpiozero, lgpio, dan spidev ok.

---

## C2 — Inspeksi ZERO7 dan uji korsleting (semua: **[DAYA MATI]**, ZERO7 terlepas dari Pi)

### C2-1 Inspeksi visual
Periksa dengan cahaya terang (dan kaca pembesar bila ada): tidak ada solder menyambung antar-pin, komponen lepas atau miring,
pin header bengkok, atau bekas terbakar. Kirim foto bagian yang mencurigakan bila ada.

### C2-2 Uji korsleting rail daya
1. Multimeter ke mode **resistansi (Ω)** atau **kontinuitas**.
2. Ukur antara pin **3,3 V** dan **GND**, lalu antara **5 V** dan **GND**, di header 40 pin ZERO7. Pada header Raspberry Pi,
   pin 1 dan 17 = 3,3 V, pin 2 dan 4 = 5 V, pin 6/9/14/20/25/30/34/39 = GND [OFFICIAL Raspberry Pi]; ZERO7 dipasang
   pin-ke-pin di header itu, jadi nomornya sama [INFERENCE]. **Letak pin 1 di ZERO7 dipastikan dulu dari foto C0-1**
   (catatan sebelumnya: pin 1 CN1 di kanan atas, `board/BOARD_INFO.md`).

- Hasil normal [INFERENCE]: bukan mendekati 0 Ω; nilainya bisa naik pelan karena kapasitor sedang terisi.
- Tanda gagal: kurang dari sekitar 5 Ω atau multimeter berbunyi terus → **berhenti**, jangan pernah menyalakan board itu,
  laporkan.
- Kirim: kedua nilai (Ω) dan foto posisi probe.

**C2 LULUS** bila: tidak ada korsleting dan tidak ada kondisi aneh.

---

## C3 — ZERO7 terpasang di Pi dan menyala

### C3-1 Pasang **[DAYA MATI]**
Cabut adaptor Pi. Pasang ZERO7 ke header 40 pin Pi **sejajar penuh** (semua 40 pin masuk, tidak bergeser satu baris)
seperti foto panduan hlm. 41 [OFFICIAL]. Jangan ada kabel lain di header. Kirim foto dari samping dan dari atas sebelum
menyalakan; **tunggu konfirmasi** baru lanjut.

### C3-2 Nyalakan **[DAYA NYALA]**
Colok adaptor 5 V 5 A. Amati 30 detik.

- Hasil: LED di ZERO7 menyala [OFFICIAL, hlm. 41]; Pi boot dan bisa di-SSH; tidak ada bau atau panas aneh.
- Tanda gagal: LED ZERO7 tidak menyala, ada bau atau panas → cabut daya segera, laporkan.
- Kirim: foto LED menyala dan keterangan SSH.

### C3-3 Ukur 3,3 V dan 5 V **[DAYA NYALA]**
Titik ukur ditentukan dari foto (pin header yang masih terjangkau atau titik uji yang jelas); jangan menebak titiknya.
Multimeter ke **DC V (V⎓)**, probe hitam ke GND, probe merah ke titik ukur.

- Hasil yang diharapkan: sekitar 3,300 V dan 5,000 V; di luar ±5 % → berhenti.
- Kirim: nilai dengan tiga desimal dan foto posisi probe.

**C3 LULUS** bila: ZERO7 menyala, Pi normal, 3,3 V dan 5 V dalam toleransi.

---

## C4 — Peta tegangan **[DAYA NYALA]**, FPGA belum diprogram, tanpa kabel tambahan

Setiap titik ukur **ditunjuk dari foto dulu**. Bila titik tidak jelas atau terlalu rapat, lewati dan tulis "tidak terjangkau"
(alternatif: skema atau tanya panitia). Catat tiga desimal.

| Titik | Nilai harapan | Hasil [HW] | Titik ukur | Catatan |
| --- | --- | --- | --- | --- |
| 3,3 V header Pi | 3,300 V [OFFICIAL Raspberry Pi] | | | dari C3 |
| 5 V header Pi | 5,000 V [OFFICIAL Raspberry Pi] | | | dari C3 |
| Vref pin header JTAG | [UNKNOWN]; diduga 3,3 V karena bank 0 di VCC3V3 [INFERENCE] | | | penentu VTref J-Link |
| VCC1V0 | sekitar 1,0 V (dari nama net) [INFERENCE] | | | |
| VCC1V8 | sekitar 1,8 V (dari nama net) [INFERENCE] | | | |
| VCC3V3 | sekitar 3,3 V (dari nama net) [INFERENCE] | | | |
| BANK15_VCCO | [UNKNOWN] | | | bank SPI dari Pi |
| BANK34_VCCO | [UNKNOWN] | | | bank LED, tombol, GPIO Pi |
| BANK14_VCCO | [UNKNOWN] | | | bank QSPI, HDMI_LS |

- Tanda gagal: nilai berbeda lebih dari ±5 % dari harapan → berhenti dan laporkan.
- Jika tegangan bank GPIO tidak bisa dipastikan: kirim pertanyaan ke panitia (draf disiapkan) dan **tahan semua sinyal dari
  Pi ke FPGA**.

**C4 LULUS** bila: semua nilai yang terjangkau tercatat dengan titiknya, dan kita sepakat tegangan tiap bank yang dipakai.
Hasil ditulis ke `board/BOARD_INFO.md` dengan label [HW], tanggal, alat, dan titik ukur **setelah kamu mengonfirmasi angkanya**.

---

## Setelah C4 (belum dikerjakan)

C5 kabel J-Link (daya mati), C6 J-Link membaca VTref, C7 Vivado membaca IDCODE lewat J-Link XVCD Server (port 2542,
clock JTAG ≤ 3 MHz), C8 desain LED berkedip (`fpga/bringup/blink/`), C9 ILA, C10 jalur Pi ke FPGA. Semuanya menunggu
C4 LULUS dan konfirmasimu.

## Format laporan per langkah

```
Langkah: C?-?
Keadaan daya: mati / nyala
Hasil: (angka dengan satuan, atau apa yang terlihat)
Foto/screenshot: (lampirkan)
Ada yang aneh: ya / tidak (jelaskan)
```
