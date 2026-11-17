# Reading notes: K. K. Parhi, *VLSI Digital Signal Processing Systems: Design and Implementation* (Wiley, 1999)

Purpose: find techniques that can speed up or harden SENTINEL (task C of PROMPT_PARHI_KAMERA_TANPA_PI).

Rules kept here:
- The book PDF is never committed (`.gitignore`); these notes summarise in our own words with chapter and
  page references, and quote no long passages.
- A chapter is marked read only after every one of its pages has been read. Pages that could not be read
  are listed in the chapter note.
- In the report, cite the book as: K. K. Parhi, *VLSI Digital Signal Processing Systems: Design and
  Implementation*, Wiley, 1999. (Year to confirm against the title page of a licensed copy.)

How the pages are read: the copy is a 791-page scan without a text layer (tiff2pdf). Text comes from the
Windows OCR engine run locally on each rendered page (`build/parhi/ocr/page-NNN.txt`, not committed);
equations, figures and tables are checked visually on the rendered page, because OCR loses them.

Scripts (Windows PowerShell 5.1, built-in Windows APIs only, nothing downloaded):

```
powershell -File tools/parhi/ocr_pdf.ps1 -Pdf "<path to the book PDF>" -OutDir build/parhi/ocr
powershell -File tools/parhi/render_pages.ps1 -Pdf "<path to the book PDF>" -OutDir build/parhi/pages -Pages 65,66
```

The file name of the copy used contains square brackets, so the scripts take the path literally (no
`Resolve-Path`). OCR of all 791 pages takes several minutes; existing page files are skipped.

Labels: book facts carry a page reference ("p. N" = printed page; the PDF page is given per chapter).
Statements about SENTINEL are [INFERENCE] unless they point to a file or result in this repository.

## Progress

| Chapter | Title (from the table of contents) | PDF pages | Status | Note |
| --- | --- | --- | --- | --- |
| Front matter | Contents, Preface | 1–17 | contents read (OCR) | chapter titles below |
| 1 | Introduction to Digital Signal Processing Systems | 18–59 | read 17 Nov 2026 | [CH01.md](CH01.md); no failed pages |
| 2 | Iteration Bound | 60–79 | read 17 Nov 2026 | [CH02.md](CH02.md); PDF 79 repeats book p. 60, book p. 62 missing from the scan |
| 3 | Pipelining and Parallel Processing | 80–106 | read 17 Nov 2026 | [CH03.md](CH03.md); no failed pages |
| 4 | Retiming | 107–134 | read 17 Nov 2026 | [CH04.md](CH04.md); book p. 90 not in the scan (book page = PDF − 16 from here) |
| 5 | Unfolding | 135–164 | read 17 Nov 2026 | [CH05.md](CH05.md); no failed pages |
| 6 | Folding | 165–203 | read 17 Nov 2026 | [CH06.md](CH06.md); no failed pages |
| 7 | Systolic Architecture Design | 204–241 | read 17 Nov 2026 | [CH07.md](CH07.md); book p. 188 not in the scan (book page = PDF − 15 from here) |
| 8 | Fast Convolution | 242–268 | read 17 Nov 2026 | [CH08.md](CH08.md); no failed pages |
| 9 | Algorithmic Strength Reduction in Filters and Transforms | 269–325 | read 17 Nov 2026 | [CH09.md](CH09.md); book p. 254 not in the scan (book page = PDF − 14 from here) |
| 10 | Pipelined and Parallel Recursive and Adaptive Filters | 326–388 | read 17 Nov 2026 | [CH10.md](CH10.md); book p. 312 not in the scan (book page = PDF − 13 from here) |
| 11 | Scaling and Roundoff Noise | 389–431 | not read | |
| 12 | Digital Lattice Filter Structures | 432–487 | not read | |
| 13 | Bit-Level Arithmetic Architectures | 488–539 | not read | |
| 14 | Redundant Arithmetic | 540–568 | not read | |
| 15 | Numerical Strength Reduction | 569–600 | not read | |
| 16 | Synchronous, Wave, and Asynchronous Pipelines | 601–654 | not read | |
| 17 | Low-Power Design | 655–704 | not read | |
| 18 | Programmable Digital Signal Processors | 705–725 | not read | |
| A–G | Appendices: shortest paths, scheduling and allocation, Euclidean GCD, Schur polynomials, fast adders and multipliers, bit-serial scheduling, FIR coefficient quantization | 726–784 | not read | |

Chapter titles 3–18 and the appendices are taken from the OCR of the contents pages (PDF pages 5–10);
title 13 is to be confirmed (titles 1, 2 and 7–10 confirmed from their first pages) from their first pages (the OCR of those contents lines
was incomplete). PDF page ranges come from the first section heading of each chapter ("N.1 INTRODUCTION") in the OCR text; the index is on PDF pages 785–791. Appendix A starts on 726, B 732, C 752, D 756, E 761, F 771, G 778.
