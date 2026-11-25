# Notes: Raspberry Pi "Getting started"

- **URL:** https://www.raspberrypi.com/documentation/computers/getting-started.html
- **Accessed:** 2026-11-16
- **Status:** official Raspberry Pi documentation, third party to the contest. Referenced by the official guide `Initialize_20260618_EN.pdf` slide 4. Content is not copied; this is a summary.
- **Reading method:** entire page (around 120 thousand characters) via WebFetch in two parts. Instructions for enabling SPI and SSH are not on this page; taken from https://www.raspberrypi.com/documentation/computers/configuration.html (the section from character 100,000 to the end was read; the first 100,000 characters of that page were only checked for this topic).

## Content summary

**Hardware**
- Boot media: microSD card (newer models can also use USB, network, or NVMe). Recommended minimum: 32 GB for Raspberry Pi OS desktop, 8 GB for Lite. Cards of 2 TB or larger are not supported.
- Display: Pi 4B, 400, 5, 500 use a micro-HDMI to HDMI cable; primary display on HDMI0.
- Pi 5 power supply: 5 V 5 A (27 W USB-C adapter). With 5 V 3 A, USB peripheral current is limited to 600 mA. The Pi turns on as soon as power is supplied.
- SENTINEL note (2026-11-16): the team uses a Raspberry Pi 4 Model B with the official Pi 4 power supply (5.1 V 3 A); see `board/BRINGUP.md` and ADR-022.
- Networking: Pi 3B+ and newer have dual-band Wi-Fi; Pi 4B and newer have Gigabit Ethernet.

**Installing the OS with Raspberry Pi Imager**
1. Install Imager (installer for Windows/macOS; `sudo apt install rpi-imager` on Raspberry Pi OS).
2. Select Device, OS (recommended is at the very top), and Storage. Leave "Exclude system drives" enabled.
3. Customisation (recommended): Hostname (can be accessed as `<hostname>.local`), Localisation (city, time zone, keyboard layout, as well as Wi-Fi regulatory domain), User (lowercase username and password), Wi-Fi, Remote Access (Enable SSH with password or public key), and Raspberry Pi Connect.
4. Write image, allow verification to run, then Finish.

**Two setup methods**
- Desktop: insert boot media, connect keyboard, mouse, and display, then power last. First boot can take several minutes.
- Headless: select OS, enable SSH (or Raspberry Pi Connect) and fill in Wi-Fi in Imager, then log in via SSH. Manual method: create an empty `ssh` file and a `userconf.txt` file containing `<username>:<encrypted-password>` in the `bootfs` partition (`openssl passwd -6`).
- Network installation is available on Pi 4B, 400, 500, 500+ (hold Shift while powering on or insert empty media).

**First boot without Imager customisation:** wizard asks for country, user, wireless network, browser, and software updates.

**Shutting down:** `sudo poweroff`, `sudo reboot`; on Pi 5 press the power button twice.

**From the Configuration page**
- SPI: `sudo raspi-config` → `3 Interface Options` → `I4 SPI`; or desktop Preferences → Control Centre → Interfaces → SPI, then reboot. Device tree parameter `spi=on` is located in `/boot/firmware/config.txt`.
- SSH: `sudo raspi-config` → `3 Interface Options` → `I1 SSH`; or `touch /boot/firmware/ssh` then reboot.

## Relevance to SENTINEL

- [OFFICIAL] The committee states that the loan board "can be connected to a Raspberry Pi 5" (`GUIDE_LSI_2027_FINALE.pdf` p. 6). The 5 V 5 A power supply is important because ZERO7 draws power from the Pi header (slide 41: ZERO7 LED lights up when the Pi is powered).
- The SENTINEL driver uses `spidev` on SPI0, so SPI must be enabled before bring-up step 4 (`board/BRINGUP.md`).
- Headless setup with SSH is suitable for running `board/bringup.py` and experiment scripts from a PC.
- Official examples use Python 3.13.5 and the `gpiozero` library on the Pi (slides 9–11).
