# Notes: Wi-Fi on Raspberry Pi

- **URL:** https://www.raspberrypi.com/documentation/computers/getting-started.html#wi-fi
- **Accessed:** 2026-11-16
- **Status:** official Raspberry Pi documentation, third-party to the contest. Referenced by the official guide `Initialize_20260618_EN.pdf` slide 6. Content is not copied; this is a summary.
- **How to read:** the `#wi-fi` anchor points to the "Wi-Fi" section in the Imager customization step on the "Getting started" page. Command line commands are taken from https://www.raspberrypi.com/documentation/computers/configuration.html ("Connect to a wireless network" section).

## Content summary

**When writing an image with Imager**
- In the customization tab, Wi-Fi section: select a secure or open network, enter SSID and password. Imager often fills this automatically from the network currently used by the PC.
- Enable "Hidden SSID" for networks that do not broadcast their name.
- The city in the Localisation section also determines the Wi-Fi regulatory domain.
- For headless setup, Wi-Fi must be configured here. The legacy method with `wpa_supplicant.conf` is no longer available since Raspberry Pi OS Bookworm.

**At first boot (wizard):** "Wireless network" step: select a network, enter password, or skip.

**Afterwards, from desktop:** Wi-Fi icon in the top right corner, or Preferences → Control Centre.

**From the command line (NetworkManager)**
- View networks: `nmcli dev wifi list`
- Connect to password-protected network: `sudo nmcli --ask dev wifi connect <ssid>`
- Hidden network: `sudo nmcli --ask dev wifi connect <ssid> hidden yes`
- Radio status: `nmcli radio wifi`, and `nmcli radio wifi on` if off
- WLAN country: `sudo raspi-config` → `5 Localisation options` → `L4 WLAN Country`

**Wired:** Ethernet connects automatically in Raspberry Pi OS.

## Relevance to SENTINEL

- The network is only required for SSH, copying weights and scripts, and installing Python packages. The inference data path remains SPI.
- At the contest venue, a Wi-Fi network may not be available or may not be permitted to use; that is not yet known. SENTINEL's validation mode and camera mode do not depend on a network, and should preferably be tested with Wi-Fi turned off.
- A direct Ethernet cable from PC to Pi is the simplest fallback for SSH.
