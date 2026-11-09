# Prior Art dan Batas Klaim

Diperiksa 2026-11-09. Untuk sebagian besar karya, yang dibaca baru abstrak atau halaman ringkasannya, bukan teks lengkap. Kolom "Dibaca" mencatat sedalam apa.

| Karya | Platform | Yang dilakukan | Yang tidak dilakukan | Dibaca |
| --- | --- | --- | --- | --- |
| Marty, Yuki & Derrien, "Enabling Overclocking through Algorithm-Level Error Detection" (FPT 2018); versi jurnal "Safe Overclocking for CNN Accelerators through Algorithm-Level Error Detection" (IEEE, 2020). Kode: https://github.com/ThibautMarty/conv-hls-overclocking · HAL: https://inria.hal.science/hal-03094811 | ZC706 | Checksum mendeteksi error per tile output. Frekuensi diatur software di ARM lewat MMCM (Clocking Wizard, dynamic reconfiguration). Throughput naik sekitar 68–77%. | Tidak ada lokalisasi atau koreksi yang dijelaskan. Kontrol ada di CPU. | README repo dan ringkasan; teks lengkap belum (HAL memblokir bot) |
| Jiang, Yu, Chen & Ha, "AOS: An Automated Overclocking System for High-Performance CNN Accelerator Through Timing Delay Measurement on FPGA", IEEE TCAD 2023. https://unnc.globalimpact.cn/en/publications/aos-an-automated-overclocking-system-for-high-performance-cnn-acc/ | ZCU104 | Monitor delay timing di FPGA. Controller di CPU memilih frekuensi tiap iterasi. 657 FPS di 436 MHz, 1,41×. | Tanpa checksum, sehingga tidak ada jaminan bit-exact per gambar. | Abstrak |
| "Training for 'Unstable' CNN Accelerator: A Case Study on FPGA", arXiv 1812.01689 (2018). https://arxiv.org/pdf/1812.01689 | KCU1500 | Overclock 19–26%, lalu melatih ulang jaringan dengan accelerator di dalam loop. | Error ditoleransi, bukan diperbaiki. | Ringkasan |
| Chamberlin dkk., "Understanding Timing Error Characteristics from Overclocked Systolic Multiply–Accumulate Arrays in FPGAs", JLPEA 14(1):4, 2024. https://www.mdpi.com/2079-9268/14/1/4 | Zybo Z7-20 | Array MAC 2×2: error deterministik dan bergantung data, bit atas gagal lebih dulu. Error baru muncul di 315 MHz, padahal estimasi STA sekitar 168 MHz. | Bukan CNN. Tidak ada deteksi atau koreksi. | Sebagian besar teks |
| Gao dkk., "Detect and Replace: Efficient Soft Error Protection of FPGA-Based CNN Accelerators", IEEE TVLSI 33(1), 2024. https://api.openalex.org/works/doi:10.1109%2FTVLSI.2024.3443834 | Zynq-7000 | Proteksi soft error pada array PE, sekitar 1,3× kompleksitas. Menyebut bahwa skema coding sudah bisa mendeteksi dan mengoreksi error output PE. | Fokus soft error (radiasi), bukan overclocking. | Abstrak |
| Zhao dkk., "FT-CNN: Algorithm-Based Fault Tolerance for Convolutional Neural Networks", IEEE TPDS 2021. https://arxiv.org/abs/2003.12203 | CPU/GPU | Skema checksum ABFT untuk berbagai implementasi konvolusi, overhead 4–8%. | Bukan FPGA, bukan error timing. | Abstrak |
| Zhang dkk., "ThUnderVolt: Enabling Aggressive Voltage Underscaling and Timing Error Resilience for Energy Efficient DNN Accelerators", arXiv 1802.03806 (2018). https://arxiv.org/abs/1802.03806 | Simulasi ASIC mirip TPU | Menurunkan tegangan sampai error timing muncul; hemat energi 34–57%. | Bukan FPGA nyata. | Abstrak |
| Huang & Abraham, "Algorithm-Based Fault Tolerance for Matrix Operations", IEEE Trans. Computers, 1984 | Teori | Asal-usul ABFT dan checksum baris/kolom. | — | Belum dibuka; verifikasi detail sitasi |

## Wajib dibaca sebelum menulis klaim orisinalitas

1. "Squeezing the Last MHz for CNN Acceleration on FPGAs" (baru ditemukan judulnya).
2. Marty dkk., "Algorithm Level Timing Speculation for Convolutional Neural Network Accelerators" (versi awal; HAL hal-01811231).
3. Teks lengkap Marty dkk. 2020, terutama bagian penanganan error dan pemilihan frekuensi.

Kalau salah satunya sudah melakukan koreksi error timing, atau pemilihan clock per layer, sesuaikan klaim di bawah.

## Klaim yang boleh ditulis (jika datanya ada)

- Atlas error timing untuk CNN sungguhan di FPGA kelas kecil (Spartan-7), per frekuensi, layer, lane, dan bit.
- Koreksi error satu lane tanpa jeda, dibandingkan langsung dengan deteksi-lalu-ulang ala Marty dkk. pada desain dan board yang sama.
- Pemilihan clock per layer dengan governor yang seluruhnya di dalam FPGA, tanpa CPU.

## Klaim yang tidak boleh ditulis

- "Pertama" atau "baru" untuk ABFT, dual checksum, atau overclocking CNN. Semuanya sudah ada.
- Apa pun tentang perilaku error timing yang hanya berasal dari simulasi atau model sintetis.
