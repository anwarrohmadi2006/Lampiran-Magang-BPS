# Laporan Studi Ablasi IndoBERT - Sentimen Sensus Ekonomi 2026

Jumlah data berlabel: 5808 baris (latih 4646, uji 1162).
Model dasar: `indobenchmark/indobert-base-p1`, panjang token maksimum 128, epoch 3.0, presisi bf16.

| Skenario | Akurasi | F1 macro | F1 weighted | Parameter dilatih | Waktu (detik) |
|---|---:|---:|---:|---:|---:|
| zeroshot | 0.7324 | 0.5971 | 0.7630 | 0 | 0.0 |
| linear_probe | 0.8141 | 0.6948 | 0.8256 | 0 | 32.5 |
| bitfit | 0.8821 | 0.7160 | 0.8654 | 105.219 | 155.0 |
| partial_top_k | 0.8778 | 0.7344 | 0.8672 | 43.120.131 | 149.7 |
| full | 0.8830 | 0.7426 | 0.8726 | 124.443.651 | 225.2 |
| full_rdrop | 0.8830 | 0.7628 | 0.8792 | 124.443.651 | 424.4 |

Catatan: seluruh angka mengukur kesesuaian terhadap label lemah hasil anotasi Gemma 4 12B, bukan terhadap kebenaran yang diverifikasi manusia.
