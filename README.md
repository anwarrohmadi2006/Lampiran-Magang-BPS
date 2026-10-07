# Lampiran Kerja Praktik: Analisis Sentimen Publik terhadap Sensus Ekonomi 2026 dan Aplikasi Fasih BPS

[![Python 3.13](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-ee4c2c.svg)](https://pytorch.org/)
[![Hugging Face](https://img.shields.io/badge/Hugging%20Face-Transformers-yellow.svg)](https://huggingface.co/)
[![Akurasi Uji](https://img.shields.io/badge/Akurasi%20Data%20Uji-0%2C7882-success.svg)](#hasil-evaluasi)
[![Macro F1](https://img.shields.io/badge/Macro%20F1-0%2C7713-brightgreen.svg)](#hasil-evaluasi)
[![Linter Score](https://img.shields.io/badge/Linter%20Mutu%20Laporan-100%2F100-success.svg)](#pemeriksaan-mutu-laporan)
[![Lisensi MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Repositori ini memuat seluruh artefak teknis, korpus digital, set data uji acuan manusia (*human gold standard*), catatan kalibrasi *prompt*, skrip pemodelan *deep learning*, visualisasi interpretabilitas (*attention map* & LIME), serta berkas naskah laporan resmi pelaksanaan **Kerja Praktik di Badan Pusat Statistik (BPS) Kabupaten Sukoharjo**.

---

## 📌 Ringkasan Eksekutif

Sensus Ekonomi 2026 (SE2026) merupakan agenda pendataan statistik nasional sepuluh tahunan yang diselenggarakan oleh Badan Pusat Statistik Republik Indonesia untuk memetakan struktur perekonomian non-pertanian. Pelaksanaan sensus mengadopsi moda *Computer-Assisted Personal Interviewing* (CAPI) berbasis aplikasi **Fasih BPS** (versi *mobile* Android untuk pencacahan lapangan dan versi *web* untuk manajemen pengawasan).

Peralihan moda digital ini memicu dinamika opini publik di media sosial, mulai dari kekhawatiran privasi data, prasangka integrasi data terhadap beban pajak, hingga kendala teknis aplikasi Fasih seperti kegagalan otentikasi akun, pembaruan aplikasi yang lambat, dan pengiriman dokumen cacah.

Penelitian terapan ini mengembangkan sistem analisis sentimen cerdas hulu ke hilir dengan capaian operasional:
1. **Pengumpulan Korpus Multi-Platform**: Menghimpun 10.961 rekaman publik dari YouTube, Google Play Store, dan Threads pada jendela waktu 15 Juni sampai 15 September 2026, yang disaring secara bertahap menghasilkan **8.352 baris korpus bersih** (partisi opini 5.808 baris, non-opini 2.119 baris, karantina 423 baris).
2. **Supervisi Lemah Berbantuan LLM (*Human-in-the-Loop*)**: Menerapkan model probabilitas keputusan Jev dengan rekayasa *prompt* sadar konteks (*context-aware prompt*) 12 aturan penalaran operasional yang dikalibrasi melalui tujuh tahapan iteratif, menghasilkan akurasi **0,7882** pada data uji acuan manusia dan mengungguli *baseline* Gemma (0,7176).
3. **Fine-Tuning IndoBERT dengan R-Drop**: Melatih model `indobenchmark/indobert-base-p1` dengan regularisasi konsistensi *R-Drop* (*consistency regularization*) untuk meredam derau label semu (*pseudo-label noise*), membukukan akurasi **0,7882** dan F1 makro **0,7700** pada data uji manusia.
4. **Keterjelangan Model (Explainable AI)**: Membedah dasar keputusan model melalui ekstraksi bobot *multi-head attention rollout* dan atribusi lokal *Local Interpretable Model-agnostic Explanations* (LIME).
5. **Dashboard Decision Support System (DSS)**: Menyediakan antarmuka analitik interaktif berbasis web untuk visualisasi sentimen per aspek, tren temporal, dan rekomendasi mitigasi risiko komunikasi publik instansi.

---

## 📂 Struktur Repositori

Proyek ini dirancang mengikuti kaidah rekayasa perangkat lunak standar industri (*clean architecture*) yang memisahkan data, artefak evaluasi, skrip reproduksi, dan pelaporan:

```text
Lampiran Magang BPS/
│
├── README.md                           <- Dokumentasi resmi proyek (EYD baku & panduan teknis)
├── requirements.txt                    <- Daftar pustaka dependensi Python
├── .gitignore                          <- Konfigurasi pengabaian git (binari besar & cache)
│
├── laporan/                            <- Naskah Laporan Magang resmi & catatan audit
│   ├── Laporan_KP_Analisis_Sentimen_SE2026.docx  <- Dokumen laporan utama hasil susunan otomatis
│   ├── laporan_kp.docx                           <- Salinan kanonik laporan final siap cetak/uji
│   └── catatan_audit_dan_keputusan.md            <- Log komprehensif audit label & putusan metodologi
│
├── data/                               <- Korpus digital & set data uji manusia
│   ├── korpus_bersih_8352.csv          <- Korpus final siap anotasi pascadeduplikasi (8.352 baris)
│   ├── korpus_opini_5808.csv           <- Partisi opini berlabel Jev data latih IndoBERT (5.808 baris)
│   ├── korpus_non_opini_2119.csv       <- Partisi non-opini (pertanyaan, sapaan, informasi)
│   ├── korpus_karantina_423.csv        <- Partisi teks di luar topik sensus & BPS
│   ├── data_uji_manusia_100.csv        <- Data uji manusia emas tersamar (100 baris acuan tunggal)
│   ├── data_uji_ronde1_kandidat.csv    <- Sampel 100 baris kandidat kalibrasi ronde 1
│   ├── data_uji_ronde2_kandidat.csv    <- Sampel 100 baris kandidat kalibrasi ronde 2
│   ├── data_uji_anotator2_ronde2.csv   <- Anotasi independen manusia kedua untuk Cohen's Kappa
│   └── ringkasan_korpus.json           <- Statistik agregat sebaran korpus digital
│
├── hasil_evaluasi/                     <- Pengukuran performa, audit mutu, & studi ablasi
│   ├── evaluasi_gold.json              <- Hasil pengukuran resmi lima sistem pada data uji manusia
│   ├── audit_label.html                <- Laporan mandiri interaktif audit penjamin mutu label semu
│   ├── audit_label.json                <- Ringkasan metrik temuan audit label semu (nol cacat kritis)
│   ├── lembar_anotasi.html             <- Lembar kerja anotasi interaktif manusia ronde 1
│   ├── lembar_anotasi_ronde2.html      <- Lembar kerja anotasi interaktif manusia ronde 2
│   ├── matriks_konfusi.png             <- Visualisasi matriks konfusi model IndoBERT terbaik
│   ├── kappa_gold.json                 <- Nilai kesepakatan antar-anotator (Cohen's Kappa)
│   ├── hasil_ablasi.json               <- Catatan numerik enam skenario studi ablasi IndoBERT
│   └── laporan_ablasi.md               <- Laporan analisis perbandingan enam skenario ablasi
│
├── model_dan_prediksi/                 <- Konfigurasi model IndoBERT & rekaman inferensi
│   ├── panduan_bobot_model.md          <- Panduan teknis arsitektur model dan pemuatan bobot
│   ├── config.json                     <- Konfigurasi model BertForSequenceClassification
│   ├── tokenizer_config.json           <- Konfigurasi tokenizer IndoBERT
│   ├── vocab.txt                       <- Kosakata subkata tokenizer (30.521 token)
│   ├── special_tokens_map.json         <- Pemetaan token struktur Transformer
│   ├── prediksi_prompt_v2.csv          <- Prediksi baseline Gemma prompt v2 pada data uji
│   ├── prediksi_prompt_v4.csv          <- Prediksi baseline Gemma prompt v4 pada data uji
│   ├── prediksi_prompt_v5.csv          <- Prediksi baseline Gemma prompt v5 pada data uji
│   ├── prediksi_deepseek.csv           <- Prediksi baseline DeepSeek pada data uji
│   └── prediksi_uji_indobert_jevlangsung.csv <- Prediksi IndoBERT pipeline pembanding
│
├── artefak_visual/                     <- Diagram metodologi & grafik interpretabilitas
│   ├── diagram_alur_penelitian.png     <- Diagram alir ujung ke ujung metodologi penelitian
│   ├── diagram_alur_pelabelan.png      <- Diagram bagan dua pipeline pelabelan & preprocessing
│   ├── diagram_alur_pelabelan.svg      <- Format vektor SVG bagan pipeline
│   ├── diagram_alur_pelabelan.html     <- Halaman web interaktif pembesaran bagan pipeline
│   ├── diagram_keputusan_anotasi.png   <- Pohon keputusan klasifikasi lima kelas anotator
│   ├── diagram_uji_jev.png             <- Diagram evolusi tujuh tahap kalibrasi ronde Jev
│   ├── awan_kata_kelas.png             <- Awan kata leksikal per kelas (Dirichlet prior log-odds)
│   ├── awan_kata_salah.png             <- Awan kata leksikal pada baris kekeliruan prediksi
│   ├── atensi/                         <- Galeri 12 visualisasi matriks atensi multi-head
│   └── lime/                           <- Galeri 8 visualisasi atribusi lokal token LIME
│
├── skrip/                              <- Skrip eksekusi analisis & kompilasi laporan
│   ├── 01_penyusunan_korpus.py         <- Pembersihan data, penyaringan berlapis, & pemilahan partisi
│   ├── 05_audit_mutu_label.py          <- Audit mutu label semu korpus berskala penuh
│   ├── 09_ukur_kinerja.py              <- Pengukuran presisi, recall, F1, bootstrap CI, & McNemar
│   ├── 10_kappa_gold.py                <- Perhitungan Cohen's Kappa antar penilai manusia
│   ├── 12_analisis_metrik.py           <- Analisis metrik per kelas, platform, & kalibrasi Brier
│   ├── 14_analisis_leksikal.py         <- Analisis kata pembeda Dirichlet prior & visualisasi awan kata
│   ├── 15_diagram_alur.py              <- Pembangkit seluruh diagram alir resmi laporan (300 DPI)
│   ├── 20_diagram_pelabelan.py         <- Pembangkit diagram bagan pipeline preprocessing & ablation
│   ├── 21_peta_atensi.py               <- Ekstraksi bobot perhatian Transformer IndoBERT
│   ├── 22_penjelasan_lime.py           <- Pengekstraksian penjelasan lokal berbasis LIME
│   ├── 27_ukur_lima_sistem.py          <- Pengukuran komparatif lima sistem pada data uji tunggal
│   ├── buat_laporan_docx.py            <- Penyusun dokumen laporan resmi format .docx otomatis
│   └── periksa_laporan.py              <- Pemeriksa mutu otomatis naskah laporan (skor 100/100)
│
└── dashboard_web/                      <- Sistem Pendukung Keputusan (DSS) berbasis web mandiri
    ├── index.html                      <- Halaman beranda antarmuka DSS BPS Sukoharjo
    ├── style.css                       <- Lembar gaya tampilan visual
    ├── app.js                          <- Logika pemfilteran aspek, kata kunci, & visualisasi
    └── ...                             <- Aset pendukung dasbor analitik
```

---

## 🔬 Siklus Iterasi Kalibrasi Anotator (*Human-in-the-Loop Rounds*)

Dalam rekayasa *weak supervision*, anotasi otomatis tidak dilepas tanpa verifikasi bertahap. Sistem melewati tujuh fase kalibrasi terukur:

```text
[Ronde 1 Awal: 0,2609] ──► [Ronde 1 Adaptif: 0,5109] ──► [Ronde 2: 0,6196 / Sentimen 0,7935]
                                                                      │
[Anotasi Penuh 8.352 Baris] ◄── [Validasi Buta Manusia: 0,7882] ◄── [Ronde 3a & Final: 0,7935]
```

| Tahapan Iterasi | Fokus Intervensi *Prompt* | Akurasi *Gold* | Evaluasi & Tindak Lanjut |
|---|---|:---:|---|
| **1. Jev Awal** (Gerbang Sempit) | Pemisahan biner keterkaitan topik sensus | `0,2609` | Model menolak 68 baris valid karena teks medsos pendek dan slang; formulasi gerbang perlu diubah. |
| **2. Jev Adaptif** (Bingkai Lembar Anotasi) | Penyisipan konteks sensus di awal instruksi *prompt* | `0,5109` | Akurasi khusus sub-tugas sentimen melonjak ke 0,7609; struktur pertanyaan disempurnakan. |
| **3. Jev Ronde 2** (Penanaman Aturan Batas) | Penanaman 12 aturan penalaran operasional batas semantik | `0,6196` *(sentimen `0,7935`)* | Uji kesepakatan dua anotator manusia memetakan batas pertanyaan faktual versus keluhan. |
| **4. Jev Ronde 3a** (Kalibrasi Keluhan Teknis) | Penyempurnaan aturan keluhan aplikasi Google Play Store | `0,7826` | Kendala *login* Fasih yang dibungkus nada santun/tanya berhasil dipisahkan dari kelas netral. |
| **5. Jev Final** (Penajaman Batas Netral) | Penegasan pemisah laporan kondisi faktual dan kekecewaan | `0,7935` | Aturan semantik stabil dan siap diuji secara independen tanpa campur tangan peneliti. |
| **6. Validasi Independen** (Data Uji Manusia) | Pengujian buta (*blind test*) pada 100 baris acuan manusia | **`0,7882`** | Mengungguli model *baseline* Gemma (0,7176); model terbukti terkalibrasi tanpa *overfitting*. |
| **7. Anotasi Korpus Penuh** | Eksekusi inferensi otomatis 8.352 baris korpus | **`100% tuntas`** | Berhasil memproses 8,3 juta token dengan tingkat kegagalan 0% (*zero failure*). |

---

## 📊 Kinerja Model & Hasil Eksperimen

Pengujian dilakukan secara objektif pada **data uji manusia tunggal (100 baris acuan berstrata tersamar)** yang belum pernah dilihat oleh sistem selama proses kalibrasi *prompt* maupun pelatihan IndoBERT.

### 1. Perbandingan Kinerja Lima Sistem

| Sistem Klasifikasi | Akurasi | Macro F1 | Recall Negatif | Recall Netral | Recall Positif |
|---|:---:|:---:|:---:|:---:|:---:|
| **Anotator Keputusan Jev (Aturan Terkalibrasi)** | **0,7882** | **0,7713** | 0,891 | **0,613** | **0,875** |
| **IndoBERT (Pipeline Utama: Gemma-Jev)** | **0,7882** | **0,7700** | **0,913** | 0,581 | **0,875** |
| IndoBERT (Pipeline Mandiri Jev) | 0,7529 | 0,7387 | **0,957** | 0,419 | **0,875** |
| LLM Gemma 4 12B (Prompt v2) | 0,7176 | 0,6954 | 0,804 | 0,581 | 0,750 |
| Model Pembanding DeepSeek | 0,6941 | 0,6682 | 0,848 | 0,452 | 0,750 |

> **Uji Signifikansi Statistik McNemar**: Perbandingan berpasangan antara IndoBERT pipeline utama dan pipeline mandiri Jev menghasilkan nilai $p = 0,5811$ ($> 0,05$), membuktikan kedua jalur mencapai performa statistik yang setara, dengan pipeline utama unggul pada daya tangkap kelas netral (0,581 vs 0,419).

### 2. Metrik Rinci per Kelas Model IndoBERT Terbaik

| Kelas Sentimen | Presisi | Recall | F1-Score | Jumlah Dukungan (*Support*) |
|---|:---:|:---:|:---:|:---:|
| **Negatif** | 0,778 | 0,913 | 0,840 | 46 baris |
| **Netral** | 0,857 | 0,581 | 0,692 | 31 baris |
| **Positif** | 0,700 | 0,875 | 0,778 | 8 baris |
| **Rata-Rata Makro** | **0,778** | **0,790** | **0,7700** | 85 baris evaluasi |

---

## 📈 Keterjelangan Model (Explainable AI)

Untuk memastikan bahwa model klasifikasi tidak menjadi "kotak hitam" (*black box*), penelitian menerapkan dua pendekatan interpretabilitas:

1. **Peta Atensi Multi-Head (*Attention Rollout*)**:
   - Memvisualisasikan bobot perhatian antar-token pada lapisan transformer terakhir.
   - Pada teks keluhan Fasih, atensi terdistribusi kuat ke kata kendala fungsional seperti *"sulit"*, *"login"*, *"gagal"*, dan *"eror"*.
   - Pada komentar positif, atensi terkonsentrasi pada kata apresiatif seperti *"semangat"*, *"membantu"*, *"akurat"*, dan *"sukses"*.
   - Seluruh galeri peta atensi tersimpan pada folder `artefak_visual/atensi/`.
2. **Atribusi Fitur Lokal LIME (*Local Interpretable Model-agnostic Explanations*)**:
   - Menghitung kontribusi leksikal setiap kata terhadap pergeseran probabilitas logit kelas prediksi.
   - Membuktikan bahwa model IndoBERT mengambil keputusan berdasarkan semantik kata kunci kontekstual, bukan bias panjang kalimat atau nama platform.
   - Laporan visual LIME tersimpan pada folder `artefak_visual/lime/`.

---

## 🚀 Panduan Menjalankan & Replikasi

### 1. Kebutuhan Sistem
- Sistem Operasi: Windows 10/11, Linux (Ubuntu 22.04+), atau macOS.
- Python: Versi 3.10 sampai 3.13.

### 2. Pemasangan Lingkungan Virtual

```bash
# Kloning atau unduh repositori
git clone https://github.com/anwarrohmadi2006/Lampiran-Magang-BPS.git
cd Lampiran-Magang-BPS

# Buat lingkungan virtual Python
python -m venv venv

# Aktivasi lingkungan virtual
# Pada Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Pada Linux / macOS:
source venv/bin/activate

# Pasang pustaka dependensi
pip install -r requirements.txt
```

### 3. Menjalankan Pengukuran Kinerja Model

```bash
# Mengukur kinerja prediksi model pada data uji manusia emas
python skrip/09_ukur_kinerja.py eval \
    --gold data/data_uji_manusia_100.csv \
    --prediksi model_dan_prediksi/prediksi_prompt_v2.csv \
    --nama "Gemma Prompt v2"
```

### 4. Menghasilkan Ulang Seluruh Diagram Alur (300 DPI)

```bash
# Menghasilkan diagram alur penelitian, keputusan anotasi, dan diagram kalibrasi Jev
python skrip/15_diagram_alur.py

# Menghasilkan bagan arsitektur pipeline preprocessing & ablation
python skrip/20_diagram_pelabelan.py
```

### 5. Memeriksa Kepatuhan Format & Mutu Laporan (Linter 100/100)

```bash
# Menjalankan linter otomatis penjamin mutu penulisan laporan
python skrip/periksa_laporan.py --laporan laporan/Laporan_KP_Analisis_Sentimen_SE2026.docx
```

---

## 📑 Pemeriksaan Mutu Laporan

Dokumen laporan resmi [`laporan/Laporan_KP_Analisis_Sentimen_SE2026.docx`](laporan/Laporan_KP_Analisis_Sentimen_SE2026.docx) disusun secara terprogram menggunakan skrip otomatis [`skrip/buat_laporan_docx.py`](skrip/buat_laporan_docx.py) dan telah diaudit melalui linter ketat [`skrip/periksa_laporan.py`](skrip/periksa_laporan.py) dengan **nilai sempurna 100 dari 100 (total temuan 0)**:

```text
=== pemeriksaan mutu penulisan laporan ===
  ok    em_dash                      0  (bobot 5)
  ok    konektor_awal                0  (bobot 5)
  ok    rujukan_sebelum_tampil       0  (bobot 5)
  ok    urutan_nomor                 0  (bobot 5)
  ok    kalimat_menggantung          0  (bobot 3)
  ok    sumber_miring                0  (bobot 3)
  ok    singkatan_kolom              0  (bobot 3)
  ok    istilah_asing                0  (bobot 2)
  ok    angka_usang                  0  (bobot 5)
  ok    angka_wajib                  0  (bobot 5)
  ok    paragraf_panjang             0  (bobot 2)
  ok    judul_berawalan_dari         0  (bobot 5)

nilai: 100 dari 100 (total temuan 0)
```

Seluruh 37 acuan pada Daftar Pustaka diterbitkan secara ketat pada rentang tahun **2022 sampai 2026**, mengikuti format APA edisi ketujuh, dan bersesuaian satu banding satu (*exact match*) dengan seluruh sitasi dalam teks.

---

## 👥 Kontributor & Ucapan Terima Kasih

- **Pelaksana Kerja Praktik**: Tim Mahasiswa Kerja Praktik
- **Instansi Penyelenggara**: [Badan Pusat Statistik Kabupaten Sukoharjo](https://sukoharjokab.bps.go.id/)
- **Periode Pelaksanaan**: 15 Juni 2026 – 15 September 2026

Penulis menyampaikan apresiasi dan terima kasih yang mendalam kepada seluruh jajaran pimpinan, pembimbing lapangan, dan staf seksi statistik BPS Kabupaten Sukoharjo atas arahan teknis, dukungan data, serta wawasan operasional lapangan selama pelaksanaan kegiatan Kerja Praktik.

---

## 📄 Lisensi

Repositori dan seluruh kode sumber dirilis di bawah lisensi [MIT License](LICENSE). Korpus publik dan data hasil pengolahan ditujukan untuk keperluan penelitian akademis, pengembangan ilmu pengetahuan, dan evaluasi kebijakan pelayanan publik.
