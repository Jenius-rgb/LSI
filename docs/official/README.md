# Official documents and archives

Last updated: 2026-11-16. Only this folder (and the organizer pages referenced by it) may serve as the source of contest rules.

## File list

| File | Source | Archived | Content | Notes |
| --- | --- | --- | --- | --- |
| `GUIDE_LSI_2027_FINALE.pdf` | Capture of English pages `https://www.lsi-contest.com/index_e.html` and `https://www.lsi-contest.com/shiyou_1e.html`, created by user | 2026-11-16, copied from user Downloads folder | 6 pages: TOP (news up to 2026/11/10, schedule, guidelines, presentation, judges' advice, access, committee) and Design Specification §1–§5 | [OFFICIAL]. Replaces `superseded/GUIDE_LSI_2027.pdf`. sha256 `d09e86226bed66fa…` |
| `ZERO7FPGA_Connection-table_261109_001.pdf` | `https://www.lsi-contest.com/ZERO7FPGA_Connection-table_261109_001.pdf` (linked from `shiyou_1.html` and `shiyou_1e.html`) | 2026-11-16, copy from user | 7 pages, 225 pins: Pin #, BANK, Name, Connect 1–4 | [OFFICIAL]. sha256 `c595ac3d9c8531aa…` |
| `Initialize_20260618_EN.pdf` | `https://www.lsi-contest.com/Initialize_20260618_EN.pdf` (linked from `shiyou_1e.html`) | 2026-11-16, copy from user | 59 slides "Raspberry Pi and ZERO7: From Setup to Design and Operation", DSP Laboratory, dated 2026/11/10 | [OFFICIAL]. sha256 `a03b92cd8c141682…` |
| (not yet archived) `Initialize_20260618.pdf` | `https://www.lsi-contest.com/Initialize_20260618.pdf` (linked from `shiyou_1.html`) | — | Japanese version of guide above; 59 pages according to PDF structure | Not yet copied to repo: awaiting download permission from user. Content read from official English version. |
| `superseded/GUIDE_LSI_2027.pdf` | Website capture before 2 and 10 Nov 2026 updates | 2026-11-09 | 4 pages | Already superseded. Do not use as rule source. |
| `A_Overview_LSI_2019.pdf` | Initial package from user. Online equivalent currently referenced by organizers: `https://www.lsi-contest.com/2020/shiyou_3e.html` ("design overview" link in `shiyou_1e.html`) | before 2026-11-09 | Design specification of the 23rd contest (2020, Okinawa) | Filename mentions 2019, but content is 23rd contest specification. [HISTORICAL]. |
| `CNN_Example_2019.pdf` | Initial package from user; source URL not recorded | before 2026-11-09 | CNN instructional slides (○/× recognition example) | [HISTORICAL]. |
| `CNN_2019.zip` | Initial package from user; source URL not recorded | before 2026-11-09 | Sample MATLAB/Octave code for small CNN training and inference | Sigmoid derivative applied twice in convolution layer backprop. Do not use as arithmetic reference. |
| `CORRESPONDENCE_2026-11.md` | Organizer responses as relayed by the user on 2026-11-23, plus a website check of the same day | 2026-11-23 | Class 2 confirmation, camera and validation images for Class 2, power, XDC, JTAG cables, report and contest procedure, the 2026/11/19 four-class update | Record, not the original e-mails; archive the e-mails here when available. Supersedes the "not yet announced" items below where it differs. |

## 2027 rules summary, as of 2026-11-16

All items [OFFICIAL]. Reference "G-n" means page n in `GUIDE_LSI_2027_FINALE.pdf`; "JP" means Japanese page read directly on 2026-11-16.

- **Theme:** "CNN implementation (any number of layers)" (G-1, G-2; JP: 「CNNの実装（層数は任意）」).
- **Dates:** report deadline Sunday 31 January 2027; presentation Friday 5 March 2027 (G-2).
- **Venue:** Hokkaido Gas Bunka Hall (Chitose Civic Cultural Center), 2-2-11 Hokuei, Chitose, Hokkaido 066-0036; hybrid format via Zoom and on-site (G-2).
- **Presentation:** 10 minutes with at most 10 slides, followed by 5 minutes Q&A (G-2; JP: 発表時間10分、質疑応答5分、パワーポイント10枚以内).
- **Submissions:** final report and synthesis report for AMD Spartan-7 XC7S25CSGA225-1, mandatory (G-2).
- **Mandatory for all classes:** design synthesized to fit in XC7S25CSGA225-1 and its synthesis result (report) submitted, even when using another board in Unlimited (G-6). Synthesis report format is not explained.
- **Design environment:** Vivado recommended version 2025.2; part set to XC7S25CSGA225-1 (G-5).
- **Purpose:** hardware implementation of CNN with conditions of specified validation data and real-time camera input (G-5). Validation images provided on the day of the contest; system reads them from camera, SD card, etc.; presentation shows how fast recognition results are output (G-5). Task details "will be updated at a later date".
- **CNN:** input 32×32. Training dataset is free, but recognition target (classes) is specified by organizers and will be announced in next update (G-5; JP: 「学習に使用するデータセットは自由です．ただし，認識する対象（分類するクラス）はこちらで指定します」). Structure refers to 23rd contest design overview; hidden layers are free.
- **Class 1, Image Classification Class:** image classification only. Level 1 (simple CNN, e.g. 3×3 input) and Level 2 (32×32 CNN with training and validation) must target XC7S25CSGA225-1. Level 3 (Unlimited): first design classifier fitting in XC7S25CSGA225-1 and show synthesis report; otherwise board and architecture are free as long as image classification (G-6).
- **Class 2, ZERO7 Class:** ZERO7 board only, free task (not limited to image classification), Level 3 only (G-6).
- **Board:** ZERO7 by Gigafirm is a Raspberry Pi HAT on 40-pin GPIO header (G-3). Organizers lend Spartan-7 board "that can be connected to a Raspberry Pi 5" (G-6; JP: 「Raspberry Pi5に接続できるSpartan7 FPGAのボード」).
- **ZERO7 loan:** Indonesia via Prof. Trio Adiono, ITB (tadiono@itb.ac.id); Vietnam via Assoc. Prof. Lâm Đức Khải (khaild@uit.edu.vn); other countries via support@LSI-contest.com. Email subject: "Zero7 board Univ. name Your name" (G-2, G-6).
- **Judges' advice:** not only speed and area, but also ideas, originality, uniqueness; good presentation; "We definitely take your school grade into account"; "We like fun ideas. Please do something different from others." (G-2).
- **Participants:** see differences below.

Not yet announced, hence [UNKNOWN]: target classes, format of report and synthesis report, evaluation weighting, AI usage rules, and whether live hardware demo is conducted during presentation.

## Differences between Japanese and English pages (2026-11-16)

| Item | Japanese page | English page |
| --- | --- | --- |
| Team size | 「大学・高専生による4人以下のチーム」 (at most 4 persons) | "the team of 1-3 University or college students" |
| Evaluation items | Includes item 「仕様の部分変更など、柔軟に受け付けます」 (partial specification changes flexibly accepted) | That item is absent |
| Participant grade | 「大学院生、学部学生、高専生のレベルに応じて審査します」 | "We definitely take your school grade into account" |
| Loan contact | Only for students in Japan: support@LSI-contest.com | Vietnam, Indonesia, and other countries (see above) |

For teams from Indonesia, the English page applies until clarification; team size must be inquired with the organizers if members exceed three.

News 2026/11/10 mentions three ZERO7 documents: 導入資料 (setup guide), ユーザーマニュアル (user manual), and コネクションテーブル (connection table). The specification page only links two PDFs (setup guide and connection table). The guide itself writes "Refer to the ZERO7 User Manual" (slide 14) and mentions sample files `raspi-zer07_button.py`, `pi_button_receiver.v`, and `Zero7.xdc` that are "provided in the same folder as this manual". The user manual and those three sample files have not yet been found on the website.

## Changes since 2026-11-16 (checked 2026-11-23)

Details and status labels in `CORRESPONDENCE_2026-11.md`.

- [OFFICIAL, website] News 2026/11/19: the recognition targets of the Design Specification are four classes, cat, dog, deer and horse (§1 Task and §4 Overview of the CNN). They belong to the image classification task.
- [OFFICIAL, organizer response as relayed by the user] The project is Class 2 (ZERO7 Class), Level 3; Class 2 topic and evaluation method are free but ZERO7 must be used; the organizer validation images apply to Class 1, not Class 2; real-time camera input is not mandatory for Class 2; synthesis report for XC7S25CSGA225-1 and final report both due 31 Jan 2027; contest 5 Mar 2027, hybrid, 10 + 5 minutes.
- Pending organizer response: ZERO7 power without a Raspberry Pi; separate provision of `Zero7.xdc`; alternative or additional JTAG cables; synthesis report format; live demonstration procedure.
- [OFFICIAL, website, 2026-11-23] The ZERO7 documents section on both specification pages still links only the setup guide and the connection table; the 2026/11/10 news text now names only those two. No user manual or XDC file is linked, although the relayed organizer response says the user manual is published.

## Japanese terms used by organizers

| Japanese | Meaning |
| --- | --- |
| 設計仕様書 | design specification |
| 募集要項 | application guidelines (guidelines for applicants) |
| 審査のポイント | evaluation points |
| 設計課題 / 課題 | design task / task |
| 層数は任意 | number of layers is arbitrary |
| 論理合成・実装 | logic synthesis and implementation |
| 合成レポート | synthesis report |
| 指定チップ | specified chip |
| 必須要件 | mandatory requirements |
| 導入資料 | introductory materials (setup guide) |
| コネクションテーブル | connection table |
| 貸与 | loan |
| 指定画像検証データ | specified image validation data |
| カメラ実時間入力 | real-time camera input |
| 認識する対象（分類するクラス） | recognition target (classification classes) |
| 画像分類クラス / ZERO7クラス | Image Classification Class / ZERO7 Class |
| 初心者向け / 中級者向け / 上級者向け | beginner / intermediate / advanced |
| 発表会 | presentation session |

## Reading notes (2026-11-16)

| Source | What was read | Method | Notes |
| --- | --- | --- | --- |
| `index.html` (Japanese) | entire page | browser, page text | WebFetch misread this page (Shift_JIS) and produced several phrases absent from the page; WebFetch output discarded |
| `index_e.html` (English) | entire content via `GUIDE_LSI_2027_FINALE.pdf` pp. 1–2; direct check of team size item and links | PDF + browser | — |
| `shiyou_1.html` (Japanese) | entire page, §1–§5, and PDF links | browser | — |
| `shiyou_1e.html` (English) | entire content via `GUIDE_LSI_2027_FINALE.pdf` pp. 3–6; direct check of PDF links | PDF + browser | — |
| `ZERO7FPGA_Connection-table_261109_001.pdf` | 7 of 7 pages | PDF | — |
| `Initialize_20260618_EN.pdf` | 59 of 59 slides | PDF | SSH appendix mentioned in slide 6 is absent in this version; appendix only contains GPIO mapping (slide 59) |
| `Initialize_20260618.pdf` (Japanese) | not read | — | Text not readable via WebFetch (CID fonts); Japanese terms from this document not yet recorded |
| `A_Overview_LSI_2019.pdf`, `CNN_Example_2019.pdf`, `CNN_2019.zip` | read during 2026-11-09 session | visual | Not re-read on 2026-11-16 |
