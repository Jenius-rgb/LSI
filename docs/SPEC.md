# SPEC — SENTINEL v0.1 (pra-board)

Tanggal: 2026-11-09. Status: usulan awal. Setiap perubahan dilakukan lewat ADR di `docs/DECISIONS.md`.
Diperbarui 2026-11-16 lewat ADR-013 sampai ADR-020, sesudah panitia menerbitkan chip resmi dan dokumen ZERO7.
Bagian bertanda **(normatif)** wajib diikuti persis oleh golden model dan RTL.

---

## 0. Ringkasan

SENTINEL adalah akselerator CNN INT8 di Spartan-7 dengan **K lane MAC paralel**. Setiap lane menghitung satu output channel.

- Lane MAC berada di **domain clock cepat** yang dapat di-overclock per layer.
- Dua lane checksum menghitung C1 = Σ_k W_k ∗ X dan C2 = Σ_k k·W_k ∗ X. Lane ketiga, C3 = Σ_k k²·W_k ∗ X, bersifat opsional.
- Error satu lane dideteksi, dilokalisasi, lalu dikoreksi tepat. Error yang tidak bisa dikoreksi dihitung ulang di clock aman.
- **Governor hardware** memilih clock untuk setiap layer.
- Semua memori, kontrol, komparator, dan governor berada di **domain clock aman** yang lolos timing.

---

## 1. Parameter global (`config/*.yaml`)

| Nama | Default | Arti |
| --- | --- | --- |
| `K` | 8 | jumlah lane data (8 atau 16) |
| `R` | 2 | jumlah operand set yang dihasilkan domain aman per siklus `clk_safe` |
| `C3_EN` | 0 | lane checksum ketiga (parameter sintesis) |
| `LANE_IMPL` | `lut` | `lut`, `dsp_min` (register pipeline DSP minimal), atau `dsp_full` |
| `ACT_W` | 8 | lebar aktivasi, unsigned |
| `W_W` | 8 | lebar bobot, signed, nilai −127..127 |
| `ACC_W` | 32 | lebar akumulator lane data |
| `ACC_CS_W` | 48 | lebar akumulator lane checksum dan d1/d2/d3 |
| `N_LOG` | 256 | kapasitas log unit gagal per layer |
| `MODEL` | `s` | arsitektur CNN (`s` atau `xs`) |
| `N_CLASSES` | 10 | jumlah kelas (CIFAR-10 sebagai pengganti sementara) |
| `N_CLASSES_MAX` | 16 | batas atas kelas yang didukung hardware tanpa sintesis ulang (tabel layer dimuat saat runtime) |
| `IN_CH` | 3 | kanal input (RGB) |
| `INJ_EN` | 1 | logika fault injection ikut disintesis |

Varian resmi untuk ZERO7 dan laporan sintesis ada di `config/hw_zero7.yaml`: K = 8, R = 2, `C3_EN = 1`, `LANE_IMPL = lut`, model `s` (ADR-013).

---

## 2. Model CNN

[OFFICIAL] Input 32×32. Level 3 bebas.
[HISTORICAL] Spesifikasi kontes ke-23 memakai konvolusi, max pooling, aktivasi sigmoid/ReLU, dan fully connected.

### 2.1 Varian `s` (default; varian resmi untuk XC7S25CSGA225-1)

| Layer | Operasi | Output | Bobot | MAC |
| --- | --- | --- | --- | --- |
| conv1 | 3×3, 3→16, same, ReLU, maxpool 2×2 | 16×16×16 | 432 | 442.368 |
| conv2 | 3×3, 16→32, same, ReLU, maxpool 2×2 | 8×8×32 | 4.608 | 1.179.648 |
| conv3 | 3×3, 32→32, same, ReLU, maxpool 2×2 | 4×4×32 | 9.216 | 589.824 |
| fc | 512→N | N | 5.120 (N = 10) | 5.120 |
| **Total** | | | **19.376 + 90 bias** | **2.216.960** |

### 2.2 Varian `xs` (varian kecil, dipakai untuk regresi cepat)

| Layer | Operasi | Output | Bobot | MAC |
| --- | --- | --- | --- | --- |
| conv1 | 3×3, 3→8 | 16×16×8 | 216 | 221.184 |
| conv2 | 3×3, 8→16 | 8×8×16 | 1.152 | 294.912 |
| conv3 | 3×3, 16→16 | 4×4×16 | 2.304 | 147.456 |
| fc | 256→N | N | 2.560 | 2.560 |
| **Total** | | | **6.232 + 50 bias** | **666.112** |

Angka di atas dihitung manual. `model/arch_report.py` wajib menghitung ulang dari config, dan hasil skrip itulah acuannya.

---

## 3. Aritmetika integer (normatif)

`model/golden.py` mengimplementasikan bagian ini persis, memakai NumPy int64. RTL harus bit-exact dengan golden model.

### 3.1 Representasi

- **Aktivasi** `a`: uint8 [0, 255], termasuk piksel input mentah. Nilai real = a · S_a.
- **Bobot** `w`: int8 [−127, 127]. Nilai −128 tidak dipakai.
- **Bias** `b`: int32, dengan skala S_in · S_w.
- Urutan tensor (C, H, W). Flatten sebelum FC: i = c·H·W + y·W + x.

### 3.2 Konvolusi

Stride 1, kernel 3×3, padding "same" dengan nol:

```
acc[o,y,x] = Σ_{c=0..Cin-1} Σ_{i=0..2} Σ_{j=0..2}  w[o,c,i,j] · a[c, y+i-1, x+j-1]
```

Nilai a di luar batas dianggap 0. Ini cross-correlation, sama dengan `torch.nn.Conv2d(padding=1)`, tanpa membalik kernel.

### 3.3 Post-processing conv

```
v = acc + b[o]
q = (v · M + 2^(n-1)) >> n        # geser kanan aritmetika; jika n = 0, tanpa suku pembulatan
y = min(max(q, 0), 255)           # sekaligus berfungsi sebagai ReLU
```

M adalah uint16 (1..65535) dan n bernilai 0..31, per layer. Skala per-channel boleh dipakai lewat ADR.

### 3.4 MaxPool

MaxPool 2×2 dengan stride 2, diterapkan pada y (uint8). Requant monoton naik (M > 0), jadi pooling setelah requant memberi hasil yang sama dengan pooling sebelum requant.

### 3.5 Fully connected dan argmax

```
z[o] = Σ_i w[o,i] · a[i] + b[o]   # int32, tanpa requant
```

Kelas adalah **indeks o terkecil** yang memiliki z maksimum.

### 3.6 Batas bit

Skrip ekspor wajib menghitung batas terburuk |acc| untuk setiap layer, lalu memastikan dengan assert:

- |acc| ≤ 2^(ACC_W−1) − 1,
- |S_c| (akumulator checksum) ≤ 2^(ACC_CS_W−1) − 1,
- |v · M| tidak overflow pada lebar yang dipakai RTL.

---

## 4. Training dan kuantisasi

- **Dataset sementara**: CIFAR-10 (torchvision). Input dinormalisasi x/255 saja, tanpa mean/std, supaya input integer sama dengan piksel mentah.
- **BatchNorm** boleh dipakai saat training, tetapi harus di-fold ke bobot dan bias sebelum kuantisasi.
- **Kuantisasi**:
  1. Mulai dengan PTQ: kalibrasi dengan 1.000 gambar train, S_out = persentil 99,99 aktivasi dibagi 255.
  2. Jika akurasi model integer turun lebih dari 2 poin persentase dari float, coba QAT (fake-quant dengan STE) atau skala per-channel. Catat keputusannya di ADR.
- **Pemilihan M dan n**: n diambil sebesar mungkin sehingga M = round(rasio · 2^n) ≤ 65535, dengan rasio = S_in·S_w / S_out.
- **Output ekspor** (`model/export.py`):
  - `build/weights/<model>.bin` dan `manifest.json`, dengan urutan byte persis sama dengan memori RTL,
  - file `.mem` untuk `$readmemh` di simulasi,
  - parameter requant per layer,
  - laporan akurasi float dibanding integer di `results/model/`.
- **Kelas target** dari panitia belum diumumkan [UNKNOWN]. Training wajib mendukung dataset folder (format ImageFolder) dan N_CLASSES bebas, sehingga melatih ulang untuk kelas lain cukup dengan mengganti konfigurasi dataset. Bobot baru dimuat lewat SPI tanpa sintesis ulang, selama arsitektur konvolusinya sama dan N_CLASSES ≤ N_CLASSES_MAX.

---

## 5. Dataflow dan jadwal

### 5.1 Pemetaan lane

Lane k (k = 1..K) menghitung output channel o = g·K + (k−1) untuk grup g. Jika Cout bukan kelipatan K, lane sisa memakai bobot nol.

### 5.2 Output-stationary

Untuk setiap unit hitung, lane mengakumulasi selama T siklus:

- conv: T = Cin · 9,
- FC: T = N_in.

Setiap siklus, semua lane menerima satu **operand set**: {a (1 byte, broadcast), w_1..w_K, wc1, wc2, (wc3)}.

### 5.3 Urutan loop conv

```
for g in groups:
  for window in pool_windows (raster):
    for (dy,dx) in [(0,0),(0,1),(1,0),(1,1)]:
      for c, i, j:  (Cin × 3 × 3)
```

- **Unit hitung** = satu posisi output × satu grup.
- **Unit recompute** = satu jendela pool × satu grup, terdiri dari 4 unit hitung.
- Untuk FC, unit hitung dan unit recompute sama-sama satu grup.

### 5.4 Model siklus

```
siklus_ideal = Σ_conv (H_out · W_out · G · Cin · 9) + Σ_fc (G · N_in)
```

H_out·W_out dihitung sebelum pooling. Untuk varian `s` dengan K = 8: 277.504 siklus, sekitar 2,78 ms di 100 MHz. Simulasi wajib melaporkan siklus nyata dan selisihnya terhadap model ini. Targetnya overhead ≤ 10%.

---

## 6. Checksum (normatif)

### 6.1 Bobot checksum, dihitung on-the-fly

Bobot checksum dihitung di **domain aman**, dari K bobot yang sama yang dikirim ke lane data:

```
wc1 = Σ_{k=1..K} w_k        wc2 = Σ k · w_k        wc3 = Σ k² · w_k
```

| K | max \|wc1\| | max \|wc2\| | max \|wc3\| |
| --- | --- | --- | --- |
| 8 | 1.016 (11 bit signed) | 4.572 (14 bit) | 25.908 (16 bit) |
| 16 | 2.032 (12 bit) | 17.272 (16 bit) | 189.992 (19 bit) |

Lane checksum c menghitung S_c = Σ_t wc_c(t) · a(t).

Tanpa error, berlaku identitas berikut, dengan Y_k akumulator lane k sebelum bias:

- S1 = Σ Y_k,
- S2 = Σ k·Y_k,
- S3 = Σ k²·Y_k.

Identitas ini eksak dalam aritmetika integer selama tidak ada overflow, yang dijamin oleh §3.6.

**Alasan dihitung on-the-fly**: tidak butuh BRAM tambahan, dan domain aman lolos timing sehingga wc selalu benar. Bobot lane data yang rusak setelah keluar dari domain aman tetap terdeteksi.

### 6.2 Keputusan komparator

Diimplementasikan di `model/checker.py`, dan RTL harus identik:

```
def check(Y, S1, S2, S3, mode, c3_en, trust_csum_lane):
    # Y[1..K] = akumulator lane data; S1, S2, S3 = akumulator lane checksum
    d1 = sum(Y[k] for k in 1..K) - S1
    d2 = sum(k * Y[k] for k in 1..K) - S2
    d3 = (sum(k*k * Y[k] for k in 1..K) - S3) if c3_en else 0

    if mode == UNPROTECTED:
        return NONE, Y
    if mode == DETECT_C1_RECOMPUTE:          # baseline ala Marty dkk.
        return (RECOMPUTE if d1 != 0 else CLEAN), Y

    # mode == CORRECT (SENTINEL)
    if d1 == 0 and d2 == 0 and d3 == 0:
        return CLEAN, Y
    if d1 != 0:
        for j in 1..K:
            if d2 == j * d1 and (not c3_en or d3 == j*j * d1):
                Y[j] = Y[j] - d1
                return CORRECTED(j), Y
    if trust_csum_lane:
        if d1 != 0 and d2 == 0 and d3 == 0:           return CSUM_LANE(1), Y
        if d1 == 0 and d2 != 0 and d3 == 0:           return CSUM_LANE(2), Y
        if c3_en and d1 == 0 and d2 == 0 and d3 != 0: return CSUM_LANE(3), Y
    return RECOMPUTE, Y
```

- Bobot lane dimulai dari 1, bukan 0. Dengan bobot 0, error di lane C1 akan salah dikira error di lane data.
- Default `trust_csum_lane = 0` (konservatif). Tanpa C3, kasus d2 = 0 juga bisa berasal dari error multi-lane yang saling meniadakan. Contoh: +2 di lane 1 dan −1 di lane 2 memberi d1 = 1 dan d2 = 0.

### 6.3 Pencarian j

Boleh sekuensial (K siklus, mengakumulasi d1) atau kombinasional. Pembagi tidak boleh dipakai. Hasilnya harus identik dengan pseudo-code di atas, dan latensinya didokumentasikan.

### 6.4 Koreksi

Y_j ← Y_j − d1 dihitung dalam ACC_CS_W bit, lalu dipotong ke ACC_W dengan assert bahwa tidak terjadi overflow.

### 6.5 Cakupan dan batasan

Bagian ini wajib ditulis jujur di laporan.

- **Checksum melindungi perhitungan MAC, bukan input.** Error pada aktivasi a yang di-broadcast ke semua lane setelah keluar dari domain aman tidak terdeteksi. Mitigasinya ada tiga:
  - jalur operand di domain cepat dibuat pendek dan diberi register tambahan (§7.4),
  - bit paritas operand (opsional),
  - pengukuran SDC (silent data corruption) end-to-end terhadap golden model di setiap eksperimen.
- **Error multi-lane** dapat lolos atau salah dikoreksi. Lajunya diukur di M3 dan M9.

---

## 7. Domain clock dan CDC

### 7.1 `clk_safe`

Berisi BRAM, kontrol, SPI, generator operand beserta wc, komparator dan korektor, post-processing, pooling, governor, dan counter. Wajib lolos timing (WNS ≥ 0) di f_safe.

### 7.2 `clk_fast`

Berisi lane data, lane checksum, register holding hasil, serializer hasil, sisi baca FIFO operand, dan sisi tulis FIFO hasil.

`clk_fast = BUFGCTRL(clk_safe, clk_turbo)`.

### 7.3 FIFO asinkron

Wrapper `cdc_fifo` punya dua implementasi:

- `xpm_fifo_async` untuk Vivado (lihat UG953),
- model behavioral dengan pointer Gray-code untuk simulasi portabel.

Dua FIFO yang dipakai:

- **FIFO operand**: lebar tulis R × set, lebar baca 1 × set. Alternatifnya R FIFO paralel yang dibaca bergantian.
- **FIFO hasil**: hasil satu unit diserialisasi menjadi K + 2 (+1) kata selebar ACC_CS_W bit. Syaratnya K + 3 ≤ T. Untuk conv1, T = 27.

Akumulator lane punya register holding, supaya unit berikutnya bisa langsung mulai selama hasil unit sebelumnya diserialisasi.

### 7.4 Prinsip jalur kritis

Di domain cepat, jalur MAC dan akumulator harus menjadi jalur kritis. Semua jalur non-MAC (operand dari FIFO ke lane, kontrol, serializer) diberi register tambahan sampai slack-nya minimal 30% lebih besar dari jalur MAC terburuk. Ini diverifikasi di laporan timing Vivado (M11).

### 7.5 Suplai operand

Syaratnya R · f_safe ≥ f_turbo_max. Siklus ketika FIFO operand kosong dihitung oleh counter `STARVE_CYCLES`.

### 7.6 Pembangkit clock (wrapper `clk_gen`)

**Implementasi Xilinx:**

- **MMCM1** menghasilkan `clk_safe` dari F_IN.
- **MMCM2** menghasilkan `clk_turbo` dari F_IN, dengan frekuensi yang bisa diubah lewat dynamic reconfiguration.
- **BUFGCTRL** (UG472) memilih clock untuk `clk_fast`.

**Rekonfigurasi MMCM2:**

- Pilihan utama: Clocking Wizard dengan dynamic reconfiguration via AXI4-Lite (PG065), memakai master AXI-Lite sederhana.
- Alternatif: DRP langsung sesuai XAPP888.
- Pilihan dicatat lewat ADR.
- Rencana B: MMCM2 dengan beberapa CLKOUT tetap ditambah mux, tanpa rekonfigurasi.

**Tabel frekuensi turbo** dibangkitkan `tools/gen_mmcm_table.py` dari F_IN dan batas datasheet. Batas VCO, PFD, dan input untuk speed grade yang dipakai diambil dari DS189, dengan nilai dan halamannya dicantumkan. F_IN = 20 MHz di pin B13 [OFFICIAL] (ADR-015). Batas DS189 belum diverifikasi; sampai datasheet tersedia, setelan MMCM dicek dengan DRC Vivado.

**Implementasi simulasi:** clock behavioral dengan periode yang bisa diubah, dan model mux bebas glitch.

### 7.7 Protokol perpindahan clock (normatif)

1. `sel` hanya berubah saat domain cepat idle: di antara layer, atau sebelum dan sesudah recompute pass.
2. Sebelum rekonfigurasi MMCM2: set `sel = safe` dan tunggu konfirmasi perpindahan. Baru setelah itu rekonfigurasi, lalu tunggu `LOCKED = 1`. Setelah itu `sel = turbo` boleh dipakai lagi.
3. Rekonfigurasi hanya dilakukan di antara gambar.

### 7.8 Constraint

- `clk_safe` dan `clk_fast` adalah clock group asinkron.
- Dua clock di keluaran BUFGCTRL bersifat physically exclusive.
- Constraint XPM diterapkan otomatis.
- Untuk OOC: `create_clock` pada port clock dengan periode target.

---

## 8. Mode operasi (register `CTRL.MODE`)

| Nilai | Nama | Perilaku |
| --- | --- | --- |
| 0 | `UNPROTECTED` | tanpa cek, hasil dipakai apa adanya |
| 1 | `DETECT_C1_RECOMPUTE` | baseline ala Marty dkk.: d1 ≠ 0 → recompute |
| 2 | `CORRECT` | SENTINEL, sesuai §6.2 |

Ketiganya ada di bitstream yang sama supaya perbandingan E4 adil. Untuk perbandingan area, buat varian sintesis tanpa C2.

---

## 9. Recompute

1. Selama layer berjalan di turbo, unit recompute yang berstatus RECOMPUTE dicatat di log (kapasitas N_LOG).
2. Setelah layer selesai: `sel = safe` (§7.7). Semua unit di log dihitung ulang, lalu outputnya ditulis ulang setelah post-processing dan pooling. Layer berikutnya baru mulai setelah itu.
3. Komparator tetap aktif selama recompute pass. Jika hasil di clock aman tetap tidak CLEAN, set flag `FATAL`, karena itu tanda bug atau error yang bukan timing.
4. Jika log penuh, seluruh layer diulang di clock aman dan counter `LOG_OVF` bertambah.

---

## 10. Governor (normatif awal)

Model referensinya `model/governor.py`.

**State**: level L (indeks tabel frekuensi turbo), `turbo_en[l]` per layer, `cool[l]`, dan `clean_streak`.

**Parameter (register)**: `N_UP`, `COOLDOWN`, `CORR_HI`, `L_MIN`, `L_MAX`, `AUTO`.

**Di akhir setiap gambar:**

```
any_fail = False
for l in layers:
    if fails[l] > 0:
        turbo_en[l] = 0; cool[l] = COOLDOWN; any_fail = True
    elif not turbo_en[l]:
        if cool[l] > 0: cool[l] -= 1
        if cool[l] == 0: turbo_en[l] = 1
corr = sum(corrected[l] for l in layers)
if any_fail or corr > CORR_HI:
    L = max(L - 1, L_MIN); clean_streak = 0
else:
    clean_streak += 1
    if clean_streak >= N_UP:
        L = min(L + 1, L_MAX); clean_streak = 0
```

- Perubahan L berarti MMCM2 direkonfigurasi sesuai §7.7 sebelum gambar berikutnya.
- **Mode manual** (`AUTO = 0`): L dan `turbo_en` ditulis oleh host. Mode ini dipakai untuk sapuan E1.
- RTL governor harus menghasilkan trajektori state yang identik dengan model Python untuk urutan event yang sama.
- Kebijakan boleh diperbaiki lewat ADR, asalkan model Python dan RTL diperbarui bersamaan.

---

## 11. Fault injection

### 11.1 Hardware

Dapat disintesis, aktif jika `INJ_EN = 1`. Ada dua slot injeksi, INJ0 dan INJ1. Setiap slot punya field:

- `LAYER`,
- `UNIT` (indeks unit hitung di dalam layer, atau ANY),
- `LANE` (1..K untuk lane data; K+1..K+3 untuk lane checksum),
- `MASK` (ACC_CS_W bit),
- `ONESHOT`.

Efeknya: register holding pada lane terpilih di-XOR dengan MASK (dipotong ke lebar lane) saat unitnya cocok. Injeksi ini melewati FIFO, serializer, dan komparator, sama seperti error timing sungguhan.

### 11.2 Semantik di model Python

Semantik injeksi sama persis di `model/checker.py`, sehingga outcome RTL bisa diprediksi.

### 11.3 Model error timing sintetis

`model/fault_model.py` hanya untuk pengembangan, dan hasilnya selalu berlabel `[SYNTHETIC]`.

- Setiap lane punya f_onset_k yang deterministik dari seed.
- Efek layer: f_onset_kl = f_onset_k · (1 + γ · s_l), dengan s_l = sparsity aktivasi input layer l. Ini asumsi H3; γ boleh 0.
- Probabilitas error: p(f) = 0 jika f ≤ f_onset_kl, selain itu min(1, ((f − f_onset_kl)/Δ)^α).
- Keputusan error deterministik: error terjadi jika hash(seed, image_id, layer, unit, lane, f) < p(f). Ini meniru H2.
- Nilai error: XOR satu bit, dipilih dengan bias ke MSB dari rentang bit yang aktif pada nilai akumulator yang benar. Ini meniru temuan Chamberlin dkk. (2024) bahwa bit atas gagal lebih dulu.
- Semua parameter dicatat di metadata hasil.

---

## 12. Antarmuka host (SPI)

### 12.1 Fisik

- SPI mode 0 (CPOL = 0, CPHA = 0), MSB first, CS aktif rendah.
- FPGA bertindak sebagai slave dengan oversampling di `clk_safe` (sinkronizer 2-FF).
- Dijamin bekerja untuk f_SCLK ≤ f_safe / 8.
- Pin: SPI0 Raspberry Pi dengan CE0, yaitu SCLK A8, MOSI A6, MISO A7, CS D9 [OFFICIAL]. Sinyal selesai `irq_done` di RP_GPIO25, pin C9 (ADR-016).
- Level tegangan belum tertulis di dokumen resmi [UNKNOWN]; lihat `board/BOARD_INFO.md`.

### 12.2 Perintah

| Byte | Format | Fungsi |
| --- | --- | --- |
| `0x02` WRITE | `[0x02][A23:16][A15:8][A7:0][data…]` | tulis, alamat byte auto-increment |
| `0x03` READ | `[0x03][A23:16][A15:8][A7:0][dummy]` lalu data keluar di MISO | baca, auto-increment |
| `0x9F` ID | 8 byte keluar | `"SNTL"`, versi major, versi minor, K, flags |

### 12.3 Peta alamat

Alamat byte, 24-bit. Sumber kebenarannya `spec/regmap.yaml`.

| Rentang | Isi |
| --- | --- |
| `0x000000–0x000FFF` | register 32-bit little-endian |
| `0x010000–` | memori bobot |
| `0x020000–` | bias, parameter requant, tabel layer |
| `0x030000–` | IMG0 (3.072 B) |
| `0x034000–` | IMG1 |
| `0x040000–` | logit (int32 × N) |
| `0x050000–` | log event (opsional) |

### 12.4 Register awal

Boleh ditambah. Nama final ada di YAML.

- `ID`, `VERSION`
- `CTRL`: `START`, `SOFT_RESET`, `MODE[1:0]`, `C3_EN`, `TRUST_CSUM_LANE`, `IMG_SEL`
- `STATUS`: `BUSY`, `DONE`, `FATAL`, `LOG_OVF`, `MMCM2_LOCKED`, `FAST_IS_TURBO`
- `RESULT_CLASS`, `CYCLES_TOTAL`, `CYCLES_RECOMPUTE`, `STARVE_CYCLES`
- `GOV_CTRL` (`AUTO`, `LEVEL`, `TURBO_MASK` manual), `GOV_PARAM` (`N_UP`, `COOLDOWN`, `CORR_HI`, `L_MIN`, `L_MAX`), `GOV_STATE`
- `CLK_CTRL` dan `CLK_STATUS` untuk rekonfigurasi
- `INJ0_*`, `INJ1_*`
- Counter per layer: `UNITS`, `CLEAN`, `CORRECTED`, `CSUM_LANE`, `RECOMPUTE`, `FATAL`
- Counter koreksi per lane, dan `LANE_STATUS` (untuk LED)
- `TEMP`: kode suhu dari XADC (ADR-018)

### 12.5 Format gambar

32×32×3 uint8, urutan (C, H, W), sama dengan golden model. Ping-pong: host menulis IMG(1−sel) selagi engine memproses IMG(sel).

### 12.6 Ko-simulasi protokol

Driver Python dapat menulis log byte transaksi. Testbench memutar ulang log itu ke SPI slave RTL, lalu membandingkan responsnya dengan ekspektasi driver.

---

## 13. Verifikasi

### 13.1 Oracle

Golden model integer (`model/golden.py`), checker model, dan governor model.

### 13.2 Vektor

Dibangkitkan dengan seed tetap ke `build/vectors/`. Tidak di-commit; `run.py gen` membangkitkannya ulang.

### 13.3 Tingkat verifikasi

- **L0 (pytest)**:
  - requant: pembulatan di .5, nilai negatif, saturasi 255, n = 0,
  - padding, flatten, argmax ketika ada nilai sama,
  - tabel keputusan checker lengkap ditambah property test,
  - batas bit.
- **L1 (TB unit RTL)**: lane (setiap `LANE_IMPL`), lane array, generator operand dan wc, checker, post-processing, pooling, `cdc_fifo` (rasio clock acak), SPI slave.
- **L2**: satu layer conv dibandingkan dengan golden.
- **L3**: engine satu clock; logit dan kelas bit-exact untuk ≥ 200 gambar.
- **L4**: sistem dengan SPI dan dua domain clock (rasio f_fast/f_safe ∈ {1,0; 1,3; 1,7; 2,0}), ditambah injeksi.
- **L5**: governor, ≥ 50 skenario dibandingkan dengan model Python.

### 13.4 Kasus sudut wajib

- Cin = 3,
- grup dengan lane berbobot nol,
- nilai ekstrem (a = 255, w = ±127),
- gambar nol,
- saturasi,
- nilai sama di pooling dan di argmax,
- log penuh,
- jalur FATAL.

### 13.5 Simulator

- **Icarus**: simulator utama, portabel.
- **xsim**: referensi, untuk XPM dan unisim.
- **Verilator**: lint wajib jika tersedia; simulasi cepat opsional.

---

## 14. Alur FPGA tanpa board (OOC)

- **`fpga/ooc.tcl`** menjalankan:
  - `synth_design -mode out_of_context`, lalu opt, place, route,
  - `report_utilization -hierarchical`, `report_timing_summary`,
  - `report_timing -max_paths 20` per clock,
  - `report_power` (diberi label estimasi vectorless).
- **Part**: target resmi `xc7s25csga225-1` (ADR-013). Matriks M11 untuk part lain dan speed grade −2 hanya data pembanding.
- **`fpga/synth_official.tcl`** (ADR-014) mengimplementasikan desain lengkap `top_board` dengan `board/zero7.xdc` dan menyimpan laporan resmi di `results/vivado/official/`.
- **Varian**: K ∈ {8, 16}, `LANE_IMPL` ∈ {lut, dsp_min, dsp_full}, `C3_EN` ∈ {0, 1}.
- **Analisis wajib**:
  - Fmax STA domain cepat untuk setiap varian, dan Fmax domain aman,
  - 20 jalur kritis domain cepat harus jalur MAC,
  - gap slack antara jalur MAC dan non-MAC (§7.4),
  - kecocokan resource per part (BRAM36, DSP, LUT, FF).
- **`tools/fit_report.py`** mengestimasi kebutuhan BRAM dan DSP dari config sebelum Vivado dijalankan. Di XC7S25 modul `engine` varian `s` dengan K = 8 memakai 14 dari 45 block RAM [VIVADO-STA].
- Semua angka diberi label `[VIVADO-STA]`. STA bersifat konservatif; frekuensi gagal yang nyata hanya bisa diukur di board.
- Jika Vivado tidak tersedia di lingkungan ini: buat skrip dan instruksi, tandai "perlu dijalankan user", lalu simpan laporan yang dikirim balik oleh user ke `fpga/reports/`.

---

## 15. Perangkat lunak Raspberry Pi dan harness eksperimen

- **Paket `sw/sentinel/`**:
  - `regmap.py` (hasil generate), `driver.py`,
  - transport: `SpidevTransport` (untuk board) dan `LogTransport` (untuk ko-simulasi),
  - backend: `HwBackend` dan `MockBackend`. MockBackend memakai golden, checker, governor, dan fault model sintetis, dengan API yang sama dengan HwBackend.
- **`camera.py`** (picamera2 atau OpenCV) dan **`preprocess.py`** (center-crop → resize 32×32 dengan INTER_AREA → RGB uint8 (C, H, W)). Fungsi yang sama dipakai untuk data kamera saat fine-tuning.
- **Dashboard** (web ringan atau jendela OpenCV) menampilkan kamera, kelas, FPS, frekuensi turbo, layer yang turbo, counter, dan peta lane. Bisa dijalankan dengan MockBackend di PC.
- **Mode validasi** [OFFICIAL: data validasi diberikan pada hari lomba lewat kamera, kartu SD, dll.]: baca semua gambar di sebuah folder, klasifikasi, lalu laporkan akurasi (jika label tersedia), latensi per gambar, dan FPS. Waktu komputasi FPGA (dari `CYCLES_TOTAL`) dan waktu end-to-end dilaporkan terpisah.
- **Mode kamera** [OFFICIAL: input kamera real-time]: klasifikasi terus-menerus dan tampilkan kecepatan pengenalan.
- **Eksperimen** `sw/sentinel/experiments/e1.py` sampai `e8.py`. Output ke `results/<backend>/<exp>/<timestamp>/`:
  - `data.csv`,
  - `metadata.json`: git hash, config, backend, bitstream id, versi alat, parameter fault model.
- **Plot** di `sw/sentinel/plots/` membaca CSV. Jika backend = mock, watermark "SYNTHETIC — NOT MEASURED" wajib ada.
- Setiap hasil HW dibandingkan per gambar dengan golden model (kolom `logits_match`). Setiap ketidakcocokan dihitung sebagai SDC.

---

## 16. Eksperimen

| ID | Pertanyaan | Kriteria berhasil [PROPOSAL] | Sebelum board |
| --- | --- | --- | --- |
| E1 | Atlas error (sapuan frekuensi, langkah 5 MHz); menguji H1 | ≥ 90% kejadian error di 3 frekuensi error terendah hanya mengenai satu lane | skrip diuji dengan mock |
| E2 | Apakah error deterministik? (H2) | ≥ 95% pengulangan memberi pola error identik | skrip diuji dengan mock |
| E3 | Onset error per layer (H3) | layer dalam mulai error ≥ 10% lebih tinggi dari layer 1 | skrip diuji dengan mock |
| E4 | Tiga mode: throughput dan akurasi terhadap frekuensi | throughput bit-exact maksimum mode 2 ≥ 1,2× mode 1 dan ≥ 1,4× baseline yang lolos timing | skrip diuji dengan mock |
| E5 | Fault injection: cakupan dan salah koreksi | 100% error satu lane terkoreksi; laju dua lane dilaporkan | **[SIM] penuh** (Python dan RTL) |
| E6 | Governor dan suhu | frekuensi mengikuti suhu tanpa hasil salah | skrip diuji dengan mock |
| E7 | Bit-exact di set validasi | 100% kelas dan logit identik | [SIM] di RTL |
| E8 | Biaya: resource, daya, keuntungan bersih | keuntungan bersih positif | **[VIVADO-STA]** |

Hipotesis H1–H3 bisa saja salah. Hasil negatif yang diukur dengan jujur tetap dilaporkan.

---

## 17. Struktur repo

```
sentinel/
  CLAUDE.md  STATUS.md  README.md  requirements.txt
  config/              model_s.yaml, model_xs.yaml, hw_default.yaml
  spec/                regmap.yaml
  model/               arch.py, arch_report.py, train.py, quant.py, golden.py, export.py,
                       checker.py, governor.py, fault_model.py, campaign.py
  rtl/                 lane_*.v, lane_array.v, operand_gen.v, lane_checker.v, postproc.v, pool.v,
                       engine.v, spi_slave.v, regfile.v, governor.v, top_core.v
  rtl/gen/             hasil generate regmap (jangan diedit)
  rtl/platform/sim/    clk_gen_sim.v, cdc_fifo_sim.v, ...
  rtl/platform/xilinx/ clk_gen_xilinx.v, cdc_fifo_xpm.v, ...
  tb/                  testbench
  fpga/                ooc.tcl, run_matrix.py, constraints/, reports/
  board/               BOARD_INFO.md, BRINGUP.md, xdc/ (diisi di fase board)
  sw/sentinel/         driver, backend, camera, preprocess, dashboard, experiments/, plots/
  tests/               pytest
  tools/               run.py, check_env.py, gen_regmap.py, gen_mmcm_table.py, fit_report.py
  results/             model/, sim/, mock/, hw/
  docs/                SPEC.md, DECISIONS.md, PRIOR_ART.md, ENVIRONMENT.md, ARCHITECTURE.md,
                       VERIFICATION.md, RESULTS_SIM.md, AI_USAGE.md, THIRD_PARTY.md,
                       REPORT_DRAFT.md, SLIDES_OUTLINE.md, official/
  build/               (tidak di-commit)
```

---

## 18. Item yang terblokir oleh board

Sudah terjawab oleh dokumen resmi 10 Nov 2026: part number, package, speed grade, pin, F_IN, dan cara programming lewat JTAG (`board/BOARD_INFO.md`).

- `Zero7.xdc` resmi, tegangan VCCO, dan standar I/O tiap bank.
- Kecepatan SPI yang nyata, polaritas tombol, jumlah LED WS2812B per rantai, dan boot dari flash QSPI.
- Metode pengukuran daya.
- Semua hasil `[HW]`: E1–E4, E6, dan E7 di board.
