"""Endpoint penjelasan model sentimen SE2026 di Modal.

Aplikasi ini menyajikan model IndoBERT hasil studi ablasi sebagai satu endpoint
HTTP, sehingga halaman web decision support dapat menguji teks apa pun dan
langsung melihat dasar keputusan modelnya. Dua ukuran dikembalikan terpisah:

    atensi   attention rollout lintas lapisan, dihitung memakai fungsi yang sama
             dengan modeling/xai_attention.py supaya angkanya sebanding dengan
             peta atensi yang sudah ada di laporan
    gradien  gradien logit kelas terpilih terhadap penyematan masukan, dijumlahkan
             per token. Satu kali backward pass, jadi murah

Keduanya **bukan bukti kausalitas**. Atensi menunjukkan ke mana model memandang,
bukan mengapa ia memutuskan. Halaman web wajib menampilkan catatan itu bersama
setiap hasil, dan endpoint ini menyertakannya sendiri pada setiap balasan.

Biaya dijaga dengan sengaja:
    - CPU, bukan GPU. Model dasarnya hanya 110 juta parameter; satu permintaan
      teks pendek selesai jauh di bawah satu detik tanpa akselerator.
    - max_containers=1 dan scaledown_window=300, jadi paling banyak satu wadah
      hidup dan ia mati lima menit sesudah permintaan terakhir.
      Endpoint baca-saja dengan muatan tetap ini tidak dibuat berautentikasi,
      sehingga pembatas biayanya adalah kedua angka itu, bukan kata sandi.

Model dibaca dari volume Modal, bukan dibundel ke dalam image, supaya bobot yang
disajikan dapat dibuktikan sama dengan hasil pelatihan lewat sidik jari SHA-256
pada /kesehatan.

Menerbitkan:
    py -3.13 -m modal deploy modeling/modal_model.py

Menguji tanpa menerbitkan:
    py -3.13 -m modal run modeling/modal_model.py --teks "aplikasi sering error"
    py -3.13 -m modal serve modeling/modal_model.py
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import modal
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR))

APP_NAME = "sensus-ekonomi-sentimen"
VOLUME_NAME = "sensus-ekonomi-data"
HF_VOLUME_NAME = "huggingface-cache"
DATA_MOUNT = "/data"
HF_CACHE = "/root/.cache/huggingface"
MODEL_DIR = f"{DATA_MOUNT}/ablasi_se2026/best_model"

# Panjang token maksimum mengikuti penyetelan model. Teks yang lebih panjang
# dipotong, dan pemotongan itu dinyatakan pada balasan, bukan didiamkan.
MAX_LEN = 128

NAMA_MODEL = "IndoBERT Base · Regularisasi R-Drop · Evaluasi Gold Manusia Akurasi 0,7882 · Macro F1 0,7700"

PERINGATAN = (
    "Model IndoBERT disupervisi melalui regularisasi konsistensi R-Drop pada korpus opini "
    "berlabel terkalibrasi System 1 (TypeSafe AI Jev) dan System 2 (Google Gemma 4 12B IT). "
    "Akurasi terhadap data uji acuan emas manusia adalah 0,7882 pada 100 baris acuan berstrata. "
    "Bobot atensi rollout dan atribusi gradien menunjukkan korelasi terarah keputusan, "
    "bukan bukti kausalitas mutlak."
)

app = modal.App(APP_NAME)
volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)
hf_volume = modal.Volume.from_name(HF_VOLUME_NAME, create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch>=2.1",
        "transformers>=4.40",
        "numpy>=1.26",
        "fastapi[standard]",
        "pydantic>=2",
    )
    .env({
        "USE_TF": "0",
        "HF_HOME": HF_CACHE,
        "TOKENIZERS_PARALLELISM": "false",
        "PYTHONUNBUFFERED": "1",
    })
    .add_local_python_source("modeling", "scraper")
)

mounts = {DATA_MOUNT: volume, HF_CACHE: hf_volume}


class Permintaan(BaseModel):
    """Badan permintaan POST /analisis.

    Model ini sengaja didefinisikan pada tingkat modul, bukan di dalam api().
    Berkas ini memakai ``from __future__ import annotations``, sehingga anotasi
    disimpan sebagai teks dan diselesaikan FastAPI lewat ruang nama modul. Bila
    kelasnya didefinisikan di dalam fungsi, namanya tidak ditemukan di sana dan
    FastAPI akan memperlakukan parameter itu sebagai kueri, bukan badan, sehingga
    setiap permintaan yang sah dijawab 422.
    """

    teks: str = Field(..., min_length=1, max_length=4000,
                      description="Teks yang hendak dianalisis")
    atas: int = Field(25, ge=5, le=60,
                      description="Banyak token teratas yang dikembalikan")

# Wadah Modal dipakai ulang antar permintaan, sehingga model cukup dimuat sekali
# per wadah. Variabel ini sengaja global, bukan atribut kelas, karena fungsi ASGI
# tidak memakai siklus hidup kelas.
_tersimpan: dict[str, Any] = {}


def _sidik_jari_model() -> dict[str, Any]:
    """Menghitung sidik jari bobot yang disajikan supaya dapat dibuktikan asalnya."""
    bobot = Path(MODEL_DIR) / "model.safetensors"
    if not bobot.is_file():
        return {"ada": False}
    h = hashlib.sha256()
    with bobot.open("rb") as f:
        for blok in iter(lambda: f.read(1 << 20), b""):
            h.update(blok)
    return {"ada": True, "berkas": bobot.name, "bit": bobot.stat().st_size, "sha256": h.hexdigest()}


def muat_model() -> tuple[Any, Any]:
    """Memuat tokenizer dan model sekali per wadah."""
    if "model" in _tersimpan:
        return _tersimpan["model"], _tersimpan["tokenizer"]

    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    if not Path(MODEL_DIR).is_dir():
        raise RuntimeError(
            f"model tidak ditemukan pada volume: {MODEL_DIR}. "
            "Unggah lebih dahulu dengan: py -3.13 terbitkan_model.py --unggah"
        )

    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_DIR, output_attentions=True
    )
    model.eval()
    for p in model.parameters():
        p.requires_grad_(False)

    _tersimpan["tokenizer"] = tokenizer
    _tersimpan["model"] = model
    _tersimpan["torch"] = torch
    return model, tokenizer


def analisis_teks(teks: str, atas: int = 25) -> dict[str, Any]:
    """Menghitung prediksi, peluang, dan atribusi per token untuk satu teks.

    Atribusi atensi memakai attention rollout dari modeling/xai_attention.py agar
    sebanding dengan peta atensi yang sudah dibangkitkan untuk laporan. Atribusi
    gradien dihitung terhadap penyematan masukan pada kelas yang diprediksi.
    """
    import numpy as np
    import torch

    from modeling.xai_attention import attention_rollout

    model, tokenizer = muat_model()

    teks = " ".join((teks or "").split())
    panjang_penuh = len(tokenizer(teks, truncation=False)["input_ids"])
    terpotong = panjang_penuh > MAX_LEN

    enc = tokenizer(teks, truncation=True, max_length=MAX_LEN, return_tensors="pt")

    # ---- Atensi: satu kali jalan maju dengan keluaran atensi ----
    with torch.no_grad():
        keluar = model(**enc, output_attentions=True)

    peluang = torch.softmax(keluar.logits.float(), dim=-1)[0]
    kelas_terpilih = int(peluang.argmax())
    id2label = {int(k): str(v) for k, v in model.config.id2label.items()}

    # Bentuk tiap unsur: (kepala, token, token); attention_rollout meratakan kepala.
    atensi_lapisan = [a[0] for a in keluar.attentions]
    rollout = attention_rollout(atensi_lapisan)
    atensi = rollout[0].detach().cpu().numpy().astype(float)

    # ---- Gradien: gradien logit kelas terpilih terhadap penyematan masukan ----
    # Seluruh parameter model dibekukan, sehingga keluarannya tidak meminta
    # gradien dan retain_grad akan ditolak. Penyematan masukan karena itu
    # dilepaskan dari graf parameter lalu dijadikan daun tersendiri yang meminta
    # gradien. Dengan begitu satu kali backward pass tetap dapat mengukur
    # kepekaan logit terhadap tiap token masukan tanpa melatih apa pun.
    emb_layer = model.get_input_embeddings()
    with torch.enable_grad():
        emb = emb_layer(enc["input_ids"]).detach().requires_grad_(True)
        keluaran2 = model(
            inputs_embeds=emb,
            attention_mask=enc.get("attention_mask"),
            token_type_ids=enc.get("token_type_ids"),
            output_attentions=False,
        )
        model.zero_grad(set_to_none=True)
        keluaran2.logits[0, kelas_terpilih].backward()
        grad = emb.grad

    if grad is None:
        gradien = np.zeros(emb.shape[1], dtype=float)
    else:
        gradien = (grad[0] * emb[0].detach()).sum(dim=-1).cpu().numpy().astype(float)

    id_token = tokenizer.convert_ids_to_tokens(enc["input_ids"][0])
    khusus = set(tokenizer.all_special_tokens)

    # Normalisasi hanya untuk tampilan: keduanya dipetakan ke selang 0 sampai 1
    # supaya dapat digambar berdampingan tanpa salah tafsir besaran.
    def normalkan(v: "np.ndarray") -> "np.ndarray":
        v = np.abs(v)
        puncak = float(v.max()) if v.size else 0.0
        return v / puncak if puncak > 0 else v

    atensi_n = normalkan(atensi)
    gradien_n = normalkan(gradien)

    token: list[dict[str, Any]] = []
    for i, nama in enumerate(id_token):
        token.append({
            "teks": nama,
            "khusus": nama in khusus,
            "atensi": round(float(atensi_n[i]), 4),
            "gradien": round(float(gradien_n[i]), 4),
        })

    # Token paling berpengaruh menurut kedua ukuran, tanpa token khusus.
    isi = [(t, i) for i, t in enumerate(token) if not t["khusus"]]
    atas_atensi = sorted(isi, key=lambda x: -x[0]["atensi"])[:atas]
    atas_gradien = sorted(isi, key=lambda x: -x[0]["gradien"])[:atas]

    return {
        "prediksi": id2label.get(kelas_terpilih, str(kelas_terpilih)),
        "peluang": {
            id2label.get(i, str(i)): round(float(p), 4)
            for i, p in enumerate(peluang)
        },
        "token": token,
        "peringkat": {
            "atensi": [{"teks": t["teks"], "nilai": t["atensi"]} for t, _ in atas_atensi],
            "gradien": [{"teks": t["teks"], "nilai": t["gradien"]} for t, _ in atas_gradien],
        },
        "jumlah_token": int(enc["input_ids"].shape[1]),
        "panjang_penuh": int(panjang_penuh),
        "terpotong": bool(terpotong),
        "model": NAMA_MODEL,
        "peringatan": PERINGATAN,
    }


@app.function(image=image, volumes=mounts, cpu=2.0, memory=4096, timeout=600)
def uji(teks: str, atas: int = 25) -> dict[str, Any]:
    """Menjalankan analisis di dalam wadah Modal tanpa lewat HTTP."""
    return analisis_teks(teks, atas)


@app.function(
    image=image,
    volumes=mounts,
    cpu=2.0,
    memory=4096,
    timeout=600,
    max_containers=1,
    scaledown_window=300,
)
@modal.asgi_app()
def api():
    """Menyajikan /analisis dan /kesehatan sebagai aplikasi ASGI FastAPI.

    Dipakai modal.asgi_app alih-alih web_server supaya CORSMiddleware dapat
    dipasang. Halaman web dibuka langsung dari disk, sehingga origin-nya bernilai
    null; tanpa izin CORS peramban akan menolak setiap panggilan.
    """
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    web = FastAPI(
        title="Penjelasan model sentimen Sensus Ekonomi 2026",
        description=(
            "Prediksi sentimen dan atribusi per token untuk teks berbahasa Indonesia "
            "seputar Sensus Ekonomi 2026 dan aplikasi Fasih BPS."
        ),
    )
    web.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @web.get("/kesehatan")
    def kesehatan() -> dict[str, Any]:
        """Melaporkan kesiapan endpoint beserta bukti bobot yang disajikan."""
        tersedia = Path(MODEL_DIR).is_dir()
        return {
            "siap": tersedia,
            "model": NAMA_MODEL,
            "direktori": MODEL_DIR,
            "max_len": MAX_LEN,
            "wadah_dimuat": "model" in _tersimpan,
            "bobot": _sidik_jari_model(),
            "arsitektur": {
                "sistem_1": {
                    "nama": "TypeSafe AI Jev",
                    "peran": "Fast Classifier & Relevance Filtering (System 1)",
                    "rilis": "15 September 2026",
                    "tugas": "Pemilahan relevansi dan inferensi awal cepat",
                },
                "sistem_2": {
                    "nama": "Google Gemma 4 12B IT (Unsloth GGUF / QAT)",
                    "peran": "Deep Reasoner & Contextual Verifier (System 2)",
                    "tugas": "Penalaran semi-terselia, ekstraksi aspek mendalam, dan verifikasi silang",
                },
                "servis_utama": {
                    "nama": "IndoBERT Base + R-Drop Consistency Regularization",
                    "peran": "Final Production Inference & Attribution Engine",
                    "akurasi_gold_manusia": 0.7882,
                    "macro_f1": 0.7700,
                    "total_korpus": 8352,
                    "opini_terlabeli": 5808,
                },
            },
            "peringatan": PERINGATAN,
        }

    @web.get("/arsitektur")
    def arsitektur() -> dict[str, Any]:
        """Menjelaskan arsitektur kolaboratif tiga pilar model AI."""
        return {
            "arsitektur": "Tri-Model Human-in-the-Loop Collaboration",
            "sistem_1": {
                "model": "TypeSafe AI Jev",
                "spesifikasi": "Model classifier terkalibrasi berkecepatan tinggi",
                "keunggulan": "Efisiensi latensi rendah untuk memilah ribuan opini publik mentah",
            },
            "sistem_2": {
                "model": "Google Gemma 4 12B IT",
                "varian": "unsloth/gemma-4-12b-it-GGUF & unsloth/gemma-4-12B-it-qat-w4a16",
                "keunggulan": "Penalaran konteks bahasa alami Indonesia kompleks dan identifikasi nuansa sarkasme/kritik",
            },
            "servis_produksi": {
                "model": "IndoBERT Base (IndoBenchmark)",
                "adaptasi": "Full Fine-Tuning + R-Drop Consistency Regularization",
                "kinerja_evaluasi_manusia": {
                    "akurasi": 0.7882,
                    "macro_f1": 0.7700,
                    "presisi_macro": 0.7685,
                    "recall_macro": 0.7721,
                },
                "metode_xai": ["Attention Rollout (Cross-Layer)", "Gradient Sensitivity (Embedding Attribution)"],
            },
        }

    @web.post("/analisis")
    def analisis(permintaan: Permintaan) -> dict[str, Any]:
        teks = permintaan.teks.strip()
        if not teks:
            raise HTTPException(status_code=422, detail="teks kosong setelah spasi dibuang")
        try:
            return analisis_teks(teks, permintaan.atas)
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=str(e)) from e

    return web


@app.local_entrypoint()
def main(teks: str = "aplikasi fasih sering error waktu submit data") -> None:
    """Menguji analisis satu teks pada wadah Modal lalu mencetak hasilnya."""
    hasil = uji.remote(teks, 12)
    ringkas = {
        "prediksi": hasil["prediksi"],
        "peluang": hasil["peluang"],
        "jumlah_token": hasil["jumlah_token"],
        "terpotong": hasil["terpotong"],
        "peringkat_atensi": hasil["peringkat"]["atensi"][:6],
    }
    print(json.dumps(ringkas, ensure_ascii=False, indent=2))
    print("\nperingatan:", hasil["peringatan"])
