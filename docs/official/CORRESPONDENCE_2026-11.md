# Organizer correspondence and website check, November 2026

Recorded 2026-11-23. The original e-mails are not in the repository: sections 1–8 below are a faithful
record of the organizer responses **as relayed by the user** in the session of 2026-11-23, kept as
separate responses and not merged. If the original e-mails become available, archive them in this
folder (for example as PDF or `.eml`) and link them here; they then take precedence over this record.

Status labels used in this file:

- **CONFIRMED BY ORGANIZER** — organizer response, as relayed by the user.
- **PENDING ORGANIZER RESPONSE** — question asked, no answer yet.
- **OFFICIAL WEBSITE** — read directly on the organizer website on the date given.
- **USER-PROVIDED** — information from the user, not from the organizers.

## 1. Project classification — CONFIRMED BY ORGANIZER

- The SENTINEL project belongs to **Class 2 (ZERO7 Class)**.
- Class 2 has **Level 3 (Advanced) only**.
- Participants may choose any project topic and may define their own evaluation methods.
- The implementation **must use the ZERO7 board**. Topic freedom is not an exemption from this.

## 2. Class 2 scope, validation images and image classification — CONFIRMED BY ORGANIZER

- Class 2 is **not limited to image classification**.
- The validation images supplied by the organizers on the contest day are intended for **Class 1** and
  **do not apply to Class 2**.
- Each Class 2 team defines its own project topic and evaluation method, provided the implementation
  uses ZERO7.

Not confirmed and therefore not to be assumed: whether the 32 × 32 input size and the four-class task of
the general "Overview of the CNN" (section 9 below) apply to a Class 2 project at all.

## 3. Camera input for Class 2 — CONFIRMED BY ORGANIZER

- Real-time camera input is **not mandatory** for Class 2.
- Alternative input sources are permitted according to the project's requirements.
- The implementation must use ZERO7.

## 4. ZERO7 power supply without a Raspberry Pi — PENDING ORGANIZER RESPONSE

- Question: can ZERO7 operate without being connected to a Raspberry Pi, and is an alternative
  standalone power supply supported?
- Response: the committee needs to confirm the supported power supply methods and specifications before
  giving further instructions.
- Status: **not answered**. No standalone power method, connector or voltage is confirmed. Do not attempt
  or recommend an unverified power connection.

## 5. ZERO7 documentation and the official XDC file — partly CONFIRMED, partly PENDING

- CONFIRMED BY ORGANIZER (as relayed): ZERO7 technical documentation is published on
  <https://www.lsi-contest.com/shiyou_1e.html> and includes the ZERO7 Setup Guide, the ZERO7 User Manual
  and the FPGA Connection Table.
- CONFIRMED BY ORGANIZER (recommendation from the committee): confirm the required FPGA I/O voltage
  settings and other relevant constraints before programming the FPGA.
- PENDING ORGANIZER RESPONSE: whether the official `Zero7.xdc` can be provided separately.
- OFFICIAL WEBSITE, checked 2026-11-23 (English and Japanese specification pages): the "ZERO7 Documents"
  section links **only two PDFs**, the setup guide (`Initialize_20260618_EN.pdf` / `Initialize_20260618.pdf`)
  and the connection table (`ZERO7FPGA_Connection-table_261109_001.pdf`). **No User Manual and no XDC file
  are linked.** The English news item of 2026/11/10 now reads "ZERO7 documents (setup guide, connection
  table) have been published"; earlier records in this folder (2026-11-16) noted a news text that also
  named a user manual. This conflicts with the relayed response above and is open (see section 10).

## 6. JTAG cables — PENDING ORGANIZER RESPONSE

Asked by the user; no response yet. Recorded separately from sections 4 and 5.

1. Whether alternative JTAG or compatible programming/debugging cables can replace the
   **Digilent JTAG-HS2** for programming and debugging the FPGA on ZERO7 (asked because of the limited
   availability of JTAG-HS2 cables).
2. Whether the committee will provide additional Digilent JTAG-HS2 cables to participants who have not
   received one.
3. If so: whether participants can borrow or obtain them, the procedure for requesting them, and any
   limitations or conditions.

Not to be assumed: compatibility of any alternative cable with ZERO7, provision of additional cables, or
the existence of a borrowing procedure.

## 7. Synthesis report and final report — CONFIRMED BY ORGANIZER, format PENDING

- All teams must submit a synthesis report targeting **AMD Spartan-7 XC7S25CSGA225-1** (the chip on ZERO7).
- Class 2 deadlines: final report **31 January 2027**; synthesis report **31 January 2027**.
- The final report is **recommended** (not stated as mandatory) to include the hardware design,
  implementation details, and available testing or evaluation results.
- PENDING ORGANIZER RESPONSE: the exact synthesis report format and required contents; the committee will
  clarify once confirmed.

## 8. Final contest and demonstration — CONFIRMED BY ORGANIZER, demo procedure PENDING

- Final contest: **5 March 2027**, hybrid (on-site and online via Zoom).
- Each team: **10 minutes** presentation and **5 minutes** Q&A.
- PENDING ORGANIZER RESPONSE: requirements and procedure for a live hardware demonstration.
- Official website: <https://www.lsi-contest.com/index_e.html>.

## 9. Website change of 2026/11/19 — OFFICIAL WEBSITE

Read 2026-11-23 on `index_e.html` and `shiyou_1e.html` / `shiyou_1.html`:

- News item: "(2026/11/19) The recognition targets (four classes: cat, dog, deer, horse) have been added
  to the Design Specification."
- Design Specification §1 "Task" and §4 "Overview of the CNN": the CNN accepts 32 × 32 input images; any
  dataset may be used for training; the recognition targets are four classes, **cat, dog, deer and horse**;
  on the contest day classification is performed with photos prepared by the organizers.
- The Class 1 / Class 2 text of §5 is unchanged: Class 2 is "not limited to image classification".

How this combines with section 2: the four-class task and the organizer photos belong to the image
classification task of Class 1; for Class 2 they are not mandatory (section 2). A Class 2 team may still
choose CNN image classification as its topic and its own evaluation method.

## 10. Open conflicts and uncertainties

1. User Manual: relayed response says it is published (section 5); the website on 2026-11-23 links no
   user manual. Ask the committee for the direct link or file.
2. JTAG cable on hand: earlier team information (18 Nov 2026, photo) says the team uses a Digilent
   JTAG-HS2 Rev. A; the new question asks about cables for participants "who have not received one". Whether
   the team currently holds a working cable is not recorded here; confirm with the user.
3. Raspberry Pi: the project previously planned a Raspberry Pi 4 (ADR-022). USER-PROVIDED (2026-11-23): a
   Raspberry Pi 5 from the user's lecturer is expected to be available from about 3–4 January 2027. Whether
   a Raspberry Pi 4 is available before that is not recorded; confirm with the user.
