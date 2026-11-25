# Notes: Vivado installation guide (kotoha sensorium)

- **URL:** https://kotohasensorium.com/vivado-install-windows/
- **Title:** 「Vivado インストール方法【Xilinx FPGA環境構築】Windows」
- **Published / updated:** 2024.02.23 / 2024.03.21 (according to the page)
- **Accessed:** 2026-11-16
- **Status:** third-party personal blog, not an organizer document. The official guide `Initialize_20260618_EN.pdf` (slide 17) asks to follow its steps, with the exceptions below. Page content is not copied; this is a summary.
- **How to read:** entire article via WebFetch (summary by tool), then four facts checked directly on the page via browser (version 2022.2, Vivado ML Standard edition, device selection, disk requirements). All four matched.

## Content summary

The article explains the installation of **Vivado 2022.2** free edition **Vivado ML Standard** on Windows.

1. Prerequisites: Windows, Xilinx/AMD account (for personal use, fill company name with 「個人利用」), free disk space around 50 GB. Installed result around 20 GB, but the installation process needs more space. Total time around 1 hour.
2. Open the official download page, select 2022.2 section, download Windows installer, then log in with account.
3. Run the EXE file. Welcome screen: Next. Enter account email and password (password is case-sensitive and cannot be auto-filled).
4. Select product **Vivado**. Other options: Vitis (software development, required for MicroBlaze, also installs Vivado) and Lab Edition (only for programming FPGA from bitstream).
5. Select edition **Vivado ML Standard**. Enterprise edition is paid and only necessary for certain high-end parts.
6. Select devices. The article selects Kria SOMs, Zynq, and UltraScale+ (around 18 GB) and suggests selecting only required devices to save disk space.
7. Agree to license, verify installation directory and disk space, view summary, then Install. After completion click OK; author recommends a restart.
8. Verification: launch Vivado until the home screen appears.
9. Other notes: on office PCs, check license terms first. Cable drivers are not discussed.

## Exceptions from the official ZERO7 guide

[OFFICIAL] `Initialize_20260618_EN.pdf` slide 18, "Target Device Families (Minimum)":

- **7 Series → Spartan-7**
- **SoCs → Zynq-7000**

The screenshot in that slide uses installer 2023.1 with a download size of 21.25 GB and disk space requirement of 70.6 GB for the displayed options (options shown are more than the minimum). Slide 14 mentions Windows 11 environment and Vivado 2025.2.

## Relevance to SENTINEL

- Vivado 2025.2 is already installed on this PC and part `xc7s25csga225-1` is available (see `docs/ENVIRONMENT.md` and results of `tools/vivado_check_part.tcl`). This article is only a reference if reinstallation is needed.
- The version in the article (2022.2) differs from the version recommended by the committee (2025.2); installer menu names may differ.
- Zynq-7000 is not used by SENTINEL. The official guide asks for it as a minimum without explaining the reason, so currently it is not installed. If Vivado Hardware Manager encounters issues during the board phase, installing it is the first step to try.
- Cable drivers: the "Install Cable Drivers" option is visibly checked in the screenshot on slide 18; required for the Digilent JTAG-HS3 cable.
