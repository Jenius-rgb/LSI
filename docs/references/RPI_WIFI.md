# Catatan: Wi-Fi di Raspberry Pi

- **URL:** https://www.raspberrypi.com/documentation/computers/getting-started.html#wi-fi
- **Diakses:** 2026-11-16
- **Status:** dokumentasi resmi Raspberry Pi, pihak ketiga bagi lomba. Dirujuk oleh panduan resmi `Initialize_20260618_EN.pdf` slide 6. Isi tidak disalin; ini ringkasan.
- **Cara baca:** jangkar `#wi-fi` menunjuk ke bagian "Wi-Fi" pada langkah kustomisasi Imager di halaman "Getting started". Perintah baris perintah diambil dari https://www.raspberrypi.com/documentation/computers/configuration.html (bagian "Connect to a wireless network").

## Ringkasan isi

**Saat menulis image dengan Imager**
- Di tab kustomisasi, bagian Wi-Fi: pilih jaringan aman atau terbuka, isi SSID dan password. Imager sering mengisi otomatis dari jaringan yang sedang dipakai PC.
- Aktifkan "Hidden SSID" untuk jaringan yang tidak menyiarkan namanya.
- Kota di bagian Localisation ikut menentukan domain regulasi Wi-Fi.
- Untuk penyiapan headless, Wi-Fi harus diisi di sini. Cara lama dengan `wpa_supplicant.conf` tidak tersedia lagi sejak Raspberry Pi OS Bookworm.

**Saat boot pertama (wizard):** langkah "Wireless network": pilih jaringan, isi password, atau lewati.

**Sesudahnya, dari desktop:** ikon Wi-Fi di pojok kanan atas, atau Preferences → Control Centre.

**Dari baris perintah (NetworkManager)**
- Lihat jaringan: `nmcli dev wifi list`
- Sambung ke jaringan berpassword: `sudo nmcli --ask dev wifi connect <ssid>`
- Jaringan tersembunyi: `sudo nmcli --ask dev wifi connect <ssid> hidden yes`
- Status radio: `nmcli radio wifi`, dan `nmcli radio wifi on` bila mati
- Negara WLAN: `sudo raspi-config` → `5 Localisation options` → `L4 WLAN Country`

**Kabel:** Ethernet tersambung otomatis di Raspberry Pi OS.

## Relevansi untuk SENTINEL

- Jaringan hanya diperlukan untuk SSH, menyalin bobot dan skrip, dan memasang paket Python. Jalur data inferensi tetap SPI.
- Di lokasi lomba, jaringan Wi-Fi mungkin tidak tersedia atau tidak boleh dipakai; itu belum diketahui. Mode validasi dan mode kamera SENTINEL tidak bergantung pada jaringan, dan sebaiknya diuji dengan Wi-Fi dimatikan.
- Kabel Ethernet langsung PC ke Pi adalah cadangan yang paling sederhana untuk SSH.
