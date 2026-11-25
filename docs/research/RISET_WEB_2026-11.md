# Web and social media research, 15 Oct – 15 Nov 2026

Conducted 2026-11-16. Purpose: find latest information regarding LSI Design Contest 2027, ZERO7, XC7S25, and core SENTINEL topics (CNN accelerator overclocking, timing errors, checksum/ABFT).

Labels used:
- `[OFFICIAL]`: organizer pages or documents read directly.
- `[VERIFIED EXTERNAL]`: third-party pages opened and read.
- `[UNVERIFIED]`: search result snippets only; page failed to open or was not opened.

Method notes:
- Searches used web search engines and page readers. Page summaries were produced by reading tools, so `[VERIFIED EXTERNAL]` details still need to be checked against the original page before being cited in the report.
- Organizers' Japanese pages were read via browser, because page reader incorrectly decoded Shift_JIS.
- `last30days` skill was not used: it requires setup, third-party API keys, and may request browser cookie access.
- Social media was searched via search engines only. No login to any account.
- Project name and team name were not included in search queries.

## (a) Updates from organizers

All `[OFFICIAL]`, from `https://www.lsi-contest.com/index.html` and `index_e.html` (read 2026-11-16). Rule details in `docs/official/README.md`.

| Date | Content |
| --- | --- |
| 2026-10-20 | Design theme, Design Specification, and event venue published |
| 2026-10-22 | ZERO7 board loan information published |
| 2026-11-02 | Tasks in Design Specification divided into two classes: Image Classification Class and ZERO7 Class |
| 2026-11-10 | Synthesis report for XC7S25CSGA225-1 chip becomes mandatory requirement |
| 2026-11-10 | ZERO7 documents published (setup guide, user manual, connection table); only setup guide and connection table linked |

Not yet announced: target classes, synthesis report format, evaluation weighting, AI usage rules.

## (b) ZERO7 information

| Source | Date | Content | Label |
| --- | --- | --- | --- |
| `docs/official/ZERO7FPGA_Connection-table_261109_001.pdf` | 2026-11-09 (filename) | Table of 225 FPGA pins: bank, net name, connection destination | `[OFFICIAL]` |
| `docs/official/Initialize_20260618_EN.pdf` | 2026-11-10 (date on slide) | Raspberry Pi setup, Vivado project, JTAG, button and LED examples | `[OFFICIAL]` |
| `GUIDE_LSI_2027_FINALE.pdf` pp. 3–4 | 2026-11-16 (capture) | ZERO7 architecture diagram and board photo; board silkscreen reads "Q-SPARC ZERO7" and "SMART NINJA" | `[OFFICIAL]` |
| https://www.gigafirm.com/ | entry 25.7.1 | New product list includes "ZERO7  AMD Spartun-7 Board" (spelling per page). No specifications, price, manual, or schematic. Written address: Fukuoka Branch R&D Center in Iizuka, and Machida Design Office in Tokyo | `[VERIFIED EXTERNAL]` |
| https://www.gigafirm.com/ | entry 26.3.6 | News "第29回 LSIデザインコンテスト" | `[VERIFIED EXTERNAL]` |

Not found: ZERO7 user manual, schematics, `Zero7.xdc` file, product page, GitHub repos, or Qiita/Zenn/note articles about ZERO7. Pin facts and programming methods in `board/BOARD_INFO.md`.

## (c) Other teams' publicly visible projects

No projects, repos, articles, or public posts found regarding work for the 2027 contest (30th). Only previous contest context found:

| Source | Date | Content | Label |
| --- | --- | --- | --- |
| https://u-aizu.ac.jp/en/information/29-lsi2026.html | event 2026-03-06 | 29th contest in Okinawa, GAN theme. 77 participants from 26 teams registered; 11 teams invited to present. Champion: Chiba University. Runners-up: Institut Teknologi Bandung, University of Aizu, Kyushu Institute of Technology. Aizu team built "SpikeGAN" (spiking-based GAN) | `[VERIFIED EXTERNAL]` |
| https://stei.itb.ac.id/en/dua-tim-stei-itb-raih-penghargaan-di-lsi-design-contest-2025/ | 2025 | Two STEI ITB teams became finalists in 2025 contest (Variational Autoencoder theme) | `[UNVERIFIED]` |
| https://stei.itb.ac.id/en/?p=24476 | unknown | Appeared in search results; page returned HTTP 500 when opened | `[UNVERIFIED]` |

Other search results (course projects on LeNet-5 accelerators, MNIST on small FPGAs, and similar) unrelated to this contest. No ideas or code from other teams used.

## (d) Papers and their impact on SENTINEL novelty claims

### Two papers requested to be read

| Work | What was successfully read | Content | Impact |
| --- | --- | --- | --- |
| Li, Xu, Xing, Liu, Wang, Li, Li, "Squeezing the Last MHz for CNN Acceleration on FPGAs", ITC-Asia 2019, pp. 151–156, DOI 10.1109/itc-asia.2019.00039 | Abstract only (via OpenAlex) `[VERIFIED EXTERNAL]` | CNN accelerator overclocking on FPGA; network trained on top of accelerator with timing errors present; for worst-case overclocking discusses flow from fault detection to recovery; implementation on Xilinx KCU1500 | Overclocking CNN on FPGA with detection then recovery has existed since 2019. Recovery method not yet known; full text must be read before writing claims |
| Marty, Yuki, Derrien, "Algorithm Level Timing Speculation for Convolutional Neural Network Accelerators", Inria technical report, June 2018 (HAL hal-01811231). Conference version: "Enabling Overclocking through Algorithm-Level Error Detection", FPT 2018, pp. 174–181. Journal version: IEEE TCAD 2020 | No open text. HAL rejected with bot protection, author site copy gave 403, CORE gave verification page | From search snippets `[UNVERIFIED]`: contains kernel components, input checksum, and output checksum; checksum logic also overclocked; paper mentions that some ABFT techniques use two or more checksums for correction, and states checksum-based correction is unsuitable for their design (reasons not visible in snippet). Journal version: overhead under 8% with detection rate near 100% | **Most important.** This closest work appears to have considered dual checksum correction and rejected it. SENTINEL report must read the reasons and explain why correction remains valid in SENTINEL's design |

### Other works found

| Work | Date | Content | Relation to SENTINEL | Read |
| --- | --- | --- | --- | --- |
| Hari, Sullivan, Tsai, Keckler, "Making Convolutions Resilient via Algorithm-Based Error Detection Techniques", arXiv:2006.04984 | 2020-06-08 | Checksums to verify convolution on GPU; detection only; overhead 6–23%; target transient hardware errors | Checksum-based detection on convolution; not FPGA, not overclocking, without correction | Abstract page `[VERIFIED EXTERNAL]` |
| Wen, Xie, Wang, Li, "DRIFT: Harnessing Inherent Fault Tolerance for Efficient and Reliable Diffusion Model Inference", DAC 2026, DOI 10.1145/3770743.3804042 (arXiv:2604.09073) | 2026-07-26 | Resilience-aware DVFS per block and per timestep, plus ABFT with rollback to previous timestep for critical errors; energy savings around 36% via voltage reduction or speedup around 1.7× via overclocking; platform not mentioned in abstract | 2026 work combining overclocking and ABFT, but for diffusion models and with rollback, not per-lane correction | Abstract via OpenAlex `[VERIFIED EXTERNAL]` |
| Chen et al., "ProWAFT: A ROMA-LPD Instance for Workload-Aware and Dynamic Fault Tolerance in FPGA-Based CNN Accelerators", arXiv:2607.01602 | 2026-07-02 | Selective TMR via partial reconfiguration on ZCU104; target SEUs | Fault tolerance for CNN accelerators on FPGA; not overclocking, not checksums | Abstract `[VERIFIED EXTERNAL]` |
| Poursiami et al., "Intellectual Property Protection of Hyperdimensional Computing Classifiers…", arXiv:2610.34942 | 2026-10-26 | HDC model watermarking; model on FPGA tested with undervolting and overclocking | Sole arXiv paper in 15 Oct–15 Nov window touching FPGA overclocking; not CNN, not ABFT | Summary from arXiv API `[VERIFIED EXTERNAL]` |
| Madappa et al., "Enhancing Deep Neural Network Resilience Through Integrated Reliability-Aware Design and Fault-Aware Training", Int. J. Artificial Intelligence Tools | 2026-10-30 | Fault-aware training for DNNs; transient faults | Within time window; not timing errors | OpenAlex metadata `[VERIFIED EXTERNAL]` |
| Qassabbashi et al., "A Systematic PRISMA Survey on Fault-Tolerant DNN Accelerator Architectures for Safety-Critical Systems", Digital (MDPI), DOI 10.3390/digital6030054 | 2026-07-02 | Survey of fault-tolerant DNN accelerator architectures | Comparison material for related work chapter | Metadata only |
| Utah State University Thesis, `digitalcommons.usu.edu/etd2023/181` | 2024 | Timing error characteristics on overclocked systolic MAC array in FPGA | Consistent with Chamberlin et al. 2024 in PRIOR_ART | `[UNVERIFIED]` |
| Politecnico di Torino Thesis, `webthesis.biblio.polito.it/30963` | unknown | Razor-style error detection and correction on FPGA; results reported inconclusive | Circuit-level alternative | `[UNVERIFIED]` |
| US Patent 12181911, "Automatic overclocking controller based on circuit delay measurement" | unknown | Automatic overclock controller from delay measurements; notes delay detector does not cover all paths | Related to AOS (Jiang et al.) | `[UNVERIFIED]` |
| Zhao et al., FT-CNN (already in PRIOR_ART) | 2021 | Snippet: checksums used to localize damaged rows and correct them | Checksum-based localization and correction already exists for soft errors on CPU/GPU | `[UNVERIFIED]` |
| Gao et al., "Detect and Replace" (already in PRIOR_ART); full text at `oa.upm.es/83243/3/83243.pdf` | 2024 | Snippet: checksum-based detection and correction module, convolution reorganized into blocks | Checksum-based correction in FPGA CNN accelerators already exists for soft errors | `[UNVERIFIED]` |

### Neural networks on Spartan-7

No CIFAR-10 or 32×32 CNN accelerators reported on XC7S25 were found. Found: LSTM on XC7S6 and XC7S15 (arXiv:2310.16842) and 1D CNN for atrial fibrillation detection on Spartan-7 S15 (arXiv:2605.29994, 2026); both `[UNVERIFIED]`.

### Conclusions for claims

1. ABFT, dual checksums, checksum-based localization and correction, and CNN accelerator overclocking **already exist** in the literature. There must be no claim of "first" or "novel" for those aspects.
2. As far as this search covered, no works were found combining all three simultaneously: (i) overclocking timing error correction with per-MAC-lane localization via dual checksums, (ii) per-layer clock selection by a governor entirely inside the FPGA, and (iii) measurements on a Spartan-7 class FPGA. Safe wording: "to the best of our knowledge as of November 2026".
3. Conclusion 2 must not yet be written in the report before full texts of Marty et al. (FPT 2018 and TCAD 2020) and Li et al. (ITC-Asia 2019) are read. Both are the closest works.
4. Searches within the 15 Oct–15 Nov 2026 window found no new works altering SENTINEL's position.

## (e) Sources failing to open or unreadable

| Source | Issue |
| --- | --- |
| `hal-univ-tlse3.archives-ouvertes.fr/INRIA/hal-01811231v1` (Marty et al. technical report) | Rejected by bot protection |
| `people.irisa.fr/Tomofumi.Yuki/papers/marty-icfpt2018.pdf` (FPT 2018) | HTTP 403, both via page reader and browser |
| `core.ac.uk/reader/163070624` | Bot verification page; not pursued |
| IEEE Xplore (FPT 2018, TCAD 2020, ITC-Asia 2019) | Not attempted; full text requires subscription |
| `https://www.lsi-contest.com/Initialize_20260618.pdf` (Japanese version) | Text not readable by page reader (CID fonts); content read from official English version |
| `https://stei.itb.ac.id/en/?p=24476` | HTTP 500 |
| X/Twitter, Facebook, Instagram, LinkedIn, YouTube | Searches restricted to these domains yielded no results for 2027 contest; results were other events (VLSI Design Conference 2027). In-platform searching requires login, hence inaccessible |
| Qiita, Zenn, note.com | No results about this contest or ZERO7 |
| GitHub | No repos mentioning ZERO7 or 2027 contest in search results |
| Google Scholar | Not accessed directly; replaced by OpenAlex and arXiv API |
| Search engines | Three queries disconnected with no results and repeated; one run stalled due to usage quota and repeated |

OpenAlex API response included text suggesting API key registration via email. That was not part of the task and was ignored.

## Keywords used

- Japanese: 「LSIデザインコンテスト 2027 ZERO7」, 「ギガファーム ZERO7 Spartan-7 Raspberry Pi HAT FPGA」, 「LSIデザインコンテスト CNN FPGA Qiita/Zenn/note 2026」, 「Spartan-7 CNN 実装 FPGA XC7S25 畳み込みニューラルネットワーク」.
- English: "LSI Design Contest" 2027 (with and without ZERO7, Hokkaido, CNN), "ZERO7" Gigafirm "Q-SPARC", "XC7S25 Spartan-7 CNN accelerator", "FPGA overclocking CNN accelerator timing error detection correction checksum 2026", titles of both papers, "timing speculation OR overclocking DNN CNN accelerator FPGA … 2026", "algorithm-based fault tolerance checksum CNN accelerator FPGA … 2026", "Spartan-7 FPGA CNN CIFAR-10 accelerator …".
- Indonesian: "LSI Design Contest 2027 mahasiswa Indonesia ITB lomba desain LSI CNN".
- API: OpenAlex (two queries with `from_publication_date:2026-07-01`) and arXiv (FPGA, neural network, overclocking/timing error/checksum/fault tolerance; 30 most recent entries).
