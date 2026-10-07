# Panduan Arsitektur dan Bobot Model IndoBERT

Berkas ini memuat spesifikasi teknis model klasifikasi sentimen IndoBERT yang dikembangkan pada program Kerja Praktik di Badan Pusat Statistik (BPS) Kabupaten Sukoharjo.

---

## 1. Arsitektur Model Dasar

Model dibangun di atas arsitektur model bahasa terlatih (pretrained language model) transformer dwiarah berbahasa Indonesia:
- **Model Fondasi**: `indobenchmark/indobert-base-p1`
- **Jumlah Lapisan Transformer**: 12 lapisan enkoder (*hidden layers*)
- **Dimensi Representasi Tersembunyi**: 768 dimensi (*hidden size*)
- **Kepala Perhatian Multi-Head**: 12 kepala atensi (*attention heads*)
- **Ukuran Kosakata (Vocabulary)**: 30.521 subkata (*subwords*)
- **Total Parameter**: ±124,5 Juta parameter
- **Jumlah Kelas Keluaran**: 3 kelas sentimen (`negatif`, `netral`, `positif`)

---

## 2. Konfigurasi Tokenizer & Konfigurasi Kepala Klasifikasi

Berkas konfigurasi berikut disertakan langsung di dalam folder ini:
- `config.json`: Konfigurasi arsitektur `BertForSequenceClassification`, parameter dropout (0.1), fungsi aktivasi gelu, dan pemetaan id label (`0: negatif`, `1: netral`, `2: positif`).
- `vocab.txt`: Kamus kosakata subkata IndoBERT.
- `tokenizer_config.json`: Konfigurasi token khusus (`[CLS]`, `[SEP]`, `[PAD]`, `[UNK]`, `[MASK]`).
- `special_tokens_map.json`: Pemetaan token penanda struktur urutan teks.

---

## 3. Strategi Pelatihan (R-Drop Consistency Regularization)

Model dilatih menggunakan strategi regularisasi konsistensi **R-Drop** (Fan et al., 2023) untuk mengatasi derau (*noise*) pada label semu (*pseudo-labels*):
1. **Fungsi Kerugian Gabungan**:
   $$\mathcal{L} = \mathcal{L}_{\text{CE}}(z^{(1)}, y) + \mathcal{L}_{\text{CE}}(z^{(2)}, y) + \frac{\alpha}{2} \left[ D_{\text{KL}}(P_1 \parallel P_2) + D_{\text{KL}}(P_2 \parallel P_1) \right]$$
2. **Hiperparameter Pelatihan**:
   - Bobot regularisasi R-Drop ($\alpha$): 0,7
   - *Learning Rate*: $2 \times 10^{-5}$ dengan AdamW optimizer
   - *Batch Size*: 32
   - Panjang token maksimum: 128 token
   - Penjadwal laju belajar: *Linear warmup with cosine decay* (warmup ratio: 0,1)
   - Jumlah epoch: 5 epoch (early stopping pada F1 makro validasi)

---

## 4. Cara Memuat Model di Python

Contoh kode untuk menginisialisasi tokenizer dan arsitektur model:

```python
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# 1. Memuat tokenizer dari direktori lokal
tokenizer = AutoTokenizer.from_pretrained("model_dan_prediksi")

# 2. Memuat model dari fondasi IndoBERT dengan kepala 3 kelas
model = AutoModelForSequenceClassification.from_pretrained(
    "indobenchmark/indobert-base-p1",
    num_labels=3,
    id2label={0: "negatif", 1: "netral", 2: "positif"},
    label2id={"negatif": 0, "netral": 1, "positif": 2}
)

# 3. Inferensi contoh kalimat
teks = "Petugas sensus ekonomi BPS datang dengan ramah dan penjelasan sangat jelas."
input_ids = tokenizer(teks, return_tensors="pt", truncation=True, max_length=128)

model.eval()
with torch.no_grad():
    keluaran = model(**input_ids)
    prediksi_id = torch.argmax(keluaran.logits, dim=1).item()
    probabilitas = torch.softmax(keluaran.logits, dim=1)[0]

print(f"Teks: {teks}")
print(f"Prediksi: {model.config.id2label[prediksi_id]}")
print(f"Probabilitas: Negatif: {probabilitas[0]:.4f}, Netral: {probabilitas[1]:.4f}, Positif: {probabilitas[2]:.4f}")
```
