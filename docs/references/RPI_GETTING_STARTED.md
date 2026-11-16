# Catatan: Raspberry Pi "Getting started"

- **URL:** https://www.raspberrypi.com/documentation/computers/getting-started.html
- **Diakses:** 2026-11-16
- **Status:** dokumentasi resmi Raspberry Pi, pihak ketiga bagi lomba. Dirujuk oleh panduan resmi `Initialize_20260618_EN.pdf` slide 4. Isi tidak disalin; ini ringkasan.
- **Cara baca:** seluruh halaman (sekitar 120 ribu karakter) lewat WebFetch dalam dua bagian. Cara mengaktifkan SPI dan SSH tidak ada di halaman ini; diambil dari https://www.raspberrypi.com/documentation/computers/configuration.html (bagian karakter 100.000 sampai akhir dibaca; 100.000 karakter pertama halaman itu hanya dicek untuk topik ini).

## Ringkasan isi

**Perangkat keras**
- Media boot: kartu microSD (model baru juga bisa USB, jaringan, atau NVMe). Minimum yang disarankan: 32 GB untuk Raspberry Pi OS desktop, 8 GB untuk Lite. Kartu 2 TB atau lebih tidak didukung.
- Layar: Pi 4B, 400, 5, 500 memakai kabel micro-HDMI ke HDMI; layar utama di HDMI0.
- Catu daya Pi 5: 5 V 5 A (adaptor USB-C 27 W). Dengan 5 V 3 A, arus periferal USB dibatasi 600 mA. Pi menyala begitu diberi daya.
- Catatan SENTINEL (2026-11-16): tim memakai Raspberry Pi 4 Model B dengan catu daya resmi Pi 4 (5,1 V 3 A); lihat `board/BRINGUP.md` dan ADR-022.
- Jaringan: Pi 3B+ dan yang lebih baru punya Wi-Fi dual-band; Pi 4B dan yang lebih baru punya Gigabit Ethernet.

**Memasang OS dengan Raspberry Pi Imager**
1. Pasang Imager (installer untuk Windows/macOS; `sudo apt install rpi-imager` di Raspberry Pi OS).
2. Pilih Device, OS (yang disarankan ada di paling atas), dan Storage. Biarkan "Exclude system drives" aktif.
3. Kustomisasi (disarankan): Hostname (bisa diakses sebagai `<hostname>.local`), Localisation (kota, zona waktu, tata letak keyboard, sekaligus domain regulasi Wi-Fi), User (username huruf kecil dan password), Wi-Fi, Remote Access (Enable SSH dengan password atau kunci publik), dan Raspberry Pi Connect.
4. Tulis image, biarkan verifikasi berjalan, lalu Finish.

**Dua cara penyiapan**
- Desktop: pasang media boot, sambungkan keyboard, mouse, dan layar, lalu daya paling akhir. Boot pertama bisa beberapa menit.
- Headless: pilih OS, aktifkan SSH (atau Raspberry Pi Connect) dan isi Wi-Fi di Imager, lalu masuk lewat SSH. Cara manual: buat file kosong `ssh` dan file `userconf.txt` berisi `<username>:<password-terenkripsi>` di partisi `bootfs` (`openssl passwd -6`).
- Instalasi lewat jaringan tersedia di Pi 4B, 400, 500, 500+ (tahan Shift saat menyala atau pasang media kosong).

**Boot pertama tanpa kustomisasi Imager:** wizard menanyakan negara, user, jaringan nirkabel, browser, dan pembaruan software.

**Mematikan:** `sudo poweroff`, `sudo reboot`; di Pi 5 tekan tombol daya dua kali.

**Dari halaman Configuration**
- SPI: `sudo raspi-config` → `3 Interface Options` → `I4 SPI`; atau desktop Preferences → Control Centre → Interfaces → SPI, lalu reboot. Parameter device tree `spi=on` berada di `/boot/firmware/config.txt`.
- SSH: `sudo raspi-config` → `3 Interface Options` → `I1 SSH`; atau `touch /boot/firmware/ssh` lalu reboot.

## Relevansi untuk SENTINEL

- [OFFICIAL] Panitia menyebut board pinjaman "can be connected to a Raspberry Pi 5" (`GUIDE_LSI_2027_FINALE.pdf` hlm. 6). Catu daya 5 V 5 A penting karena ZERO7 mengambil daya dari header Pi (slide 41: LED ZERO7 menyala saat Pi diberi daya).
- Driver SENTINEL memakai `spidev` di SPI0, jadi SPI wajib diaktifkan sebelum langkah bring-up 4 (`board/BRINGUP.md`).
- Penyiapan headless dengan SSH cocok untuk menjalankan `board/bringup.py` dan skrip eksperimen dari PC.
- Contoh resmi memakai Python 3.13.5 dan pustaka `gpiozero` di Pi (slide 9–11).
