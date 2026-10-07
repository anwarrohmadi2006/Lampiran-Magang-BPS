from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import modal

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

APP_NAME = "sensus-ekonomi-gemma"

ASPECTS = [
    "pajak",
    "privasi_data",
    "hoaks",
    "manfaat",
    "teknis_aplikasi",
    "biaya_ekonomi",
    "petugas",
    "lainnya",
]

DEFAULT_SYSTEM = (
    "Anda anotator sentimen ahli Bahasa Indonesia untuk riset Sensus Ekonomi 2026 "
    "dan aplikasi Fasih BPS. Tugas: klasifikasikan opini menjadi positif, negatif, "
    "atau netral, lalu tentukan aspeknya. Jawab HANYA dengan satu objek JSON valid, "
    "tanpa teks lain, tanpa markdown."
)


def build_user_prompt(text: str, max_chars: int = 1500) -> str:
    snippet = " ".join((text or "").split())[:max_chars]
    return (
        "Balas dengan JSON: "
        '{"sentimen": "positif|negatif|netral", '
        f'"aspek": {json.dumps(ASPECTS)}, '
        '"keyakinan": 0.0-1.0, "alasan": "singkat"}\n\n'
        f'Teks: "{snippet}"'
    )


"""Penyaji Model Google Gemma 4 12B IT (System 2 Contextual Reasoner) di Modal.

Model ini bertindak sebagai System 2 LMM/LLM untuk penalaran semantik kompleks,
verifikasi multi-aspek, dan anotasi semi-terselia pada korpus Sensus Ekonomi 2026.
Mendukung format kuantisasi Unsloth QAT (w4a16) dan GGUF (unsloth/gemma-4-12b-it-GGUF).
"""

HF_OVERRIDES = {
    "vision_config": {
        "num_soft_tokens": 280,
        "model_patch_size": 48,
        "patch_size": 16,
        "mm_embed_dim": 3840,
        "mm_posemb_size": 1120,
        "pooling_kernel_size": 3,
    }
}

# Model acuan resmi Google Gemma 4 12B IT melalui optimasi Unsloth
GEMMA_QAT_MODEL = "unsloth/gemma-4-12B-it-qat-w4a16"
GEMMA_GGUF_MODEL = "unsloth/gemma-4-12b-it-GGUF"
MODEL_NAME = os.environ.get("GEMMA_MODEL", GEMMA_QAT_MODEL)
SERVED_NAME = os.environ.get("GEMMA_SERVED_NAME", "gemma-4-12b-qat")
GPU = os.environ.get("GEMMA_GPU", "L4")
MAX_MODEL_LEN = os.environ.get("GEMMA_MAX_MODEL_LEN", "8192")
GPU_UTIL = os.environ.get("GEMMA_GPU_UTIL", "0.92")
PORT = 8000

HF_CACHE = "/root/.cache/huggingface"
VLLM_CACHE = "/root/.cache/vllm"
DATA_MOUNT = "/data"
LABEL_DIR = "/data/labeled"
hf_cache_vol = modal.Volume.from_name("huggingface-cache", create_if_missing=True)
vllm_cache_vol = modal.Volume.from_name("vllm-cache", create_if_missing=True)
data_vol = modal.Volume.from_name("sensus-ekonomi-data", create_if_missing=True)

_hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
hf_secrets = (
    [modal.Secret.from_dict({"HF_TOKEN": _hf_token, "HUGGING_FACE_HUB_TOKEN": _hf_token})]
    if _hf_token
    else []
)

app = modal.App(APP_NAME)

vllm_image = (
    modal.Image.from_registry("nvidia/cuda:13.0.3-devel-ubuntu22.04", add_python="3.12")
    .entrypoint([])
    .pip_install(
        "vllm",
        "compressed-tensors",
        "huggingface_hub[hf_transfer]",
        "transformers",
        "accelerate",
    )
    .env(
        {
            "HF_XET_HIGH_PERFORMANCE": "1",
            "HF_HOME": HF_CACHE,
            "CUDA_HOME": "/usr/local/cuda",
            "VLLM_USE_FLASHINFER_SAMPLER": "0",
        }
    )
)


def _vllm_command() -> list[str]:
    cmd = [
        "vllm",
        "serve",
        MODEL_NAME,
        "--served-model-name",
        SERVED_NAME,
        "--host",
        "0.0.0.0",
        "--port",
        str(PORT),
        "--max-model-len",
        MAX_MODEL_LEN,
        "--gpu-memory-utilization",
        GPU_UTIL,
        "--limit-mm-per-prompt",
        '{"image": 0, "video": 0, "audio": 0}',
        "--hf-overrides",
        json.dumps(HF_OVERRIDES),
        "--trust-remote-code",
    ]
    if os.environ.get("GEMMA_FAST_BOOT", "1") != "0":
        cmd += ["--enforce-eager"]
    extra = os.environ.get("VLLM_EXTRA_ARGS", "").strip()
    if extra:
        cmd += extra.split()
    return cmd


@app.function(
    image=vllm_image,
    gpu=GPU,
    volumes={HF_CACHE: hf_cache_vol, VLLM_CACHE: vllm_cache_vol},
    secrets=hf_secrets,
    timeout=24 * 3600,
    scaledown_window=15 * 60,
)
@modal.concurrent(max_inputs=32)
@modal.web_server(port=PORT, startup_timeout=20 * 60)
def serve() -> None:
    print("menjalankan:", " ".join(_vllm_command()), flush=True)
    subprocess.Popen(_vllm_command())


@app.function(
    image=vllm_image,
    gpu=GPU,
    volumes={HF_CACHE: hf_cache_vol, VLLM_CACHE: vllm_cache_vol},
    secrets=hf_secrets,
    timeout=2 * 3600,
)
def label_batch(
    texts: list[str],
    system_prompt: str = DEFAULT_SYSTEM,
    max_tokens: int = 160,
    temperature: float = 0.0,
) -> list[str]:
    from vllm import LLM, SamplingParams

    llm = LLM(
        model=MODEL_NAME,
        max_model_len=int(MAX_MODEL_LEN),
        gpu_memory_utilization=float(GPU_UTIL),
        limit_mm_per_prompt={"image": 0, "video": 0, "audio": 0},
        hf_overrides=HF_OVERRIDES,
        enforce_eager=os.environ.get("GEMMA_FAST_BOOT", "1") != "0",
        trust_remote_code=True,
    )
    try:
        hf_cache_vol.commit()
    except Exception:
        pass
    params = SamplingParams(temperature=temperature, max_tokens=max_tokens)
    conversations = [
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": build_user_prompt(t)},
        ]
        for t in texts
    ]
    outputs = llm.chat(conversations, sampling_params=params, use_tqdm=True)
    return [o.outputs[0].text for o in outputs]


@app.function(
    image=vllm_image,
    gpu=GPU,
    volumes={HF_CACHE: hf_cache_vol, VLLM_CACHE: vllm_cache_vol},
    secrets=hf_secrets,
    timeout=1800,
)
def health() -> dict[str, Any]:
    return {
        "model": MODEL_NAME,
        "served_name": SERVED_NAME,
        "gpu": GPU,
        "max_model_len": MAX_MODEL_LEN,
        "hf_token": bool(_hf_token),
    }


def _parse_label(raw: str) -> dict[str, Any]:
    import re

    text = (raw or "").strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    obj: Any = None
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                obj = json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                obj = None
    if not isinstance(obj, dict):
        return {"sentimen": "", "aspek": [], "keyakinan": 0.0, "alasan": "", "parse_ok": False}

    aliases = {
        "positive": "positif", "positif": "positif",
        "negative": "negatif", "negatif": "negatif",
        "neutral": "netral", "netral": "netral",
    }
    sent = aliases.get(str(obj.get("sentimen") or obj.get("label") or "").strip().lower(), "")

    aspects = obj.get("aspek") or obj.get("aspect") or []
    if isinstance(aspects, str):
        aspects = [aspects]
    clean_aspects: list[str] = []
    for a in aspects if isinstance(aspects, list) else []:
        key = str(a).strip().lower().replace(" ", "_")
        if key in ASPECTS and key not in clean_aspects:
            clean_aspects.append(key)

    try:
        conf = float(obj.get("keyakinan", obj.get("confidence", 0.0)))
    except (TypeError, ValueError):
        conf = 0.0

    return {
        "sentimen": sent,
        "aspek": clean_aspects,
        "keyakinan": max(0.0, min(1.0, conf)),
        "alasan": str(obj.get("alasan") or obj.get("reason") or "")[:300],
        "parse_ok": bool(sent),
    }


@app.function(
    image=vllm_image,
    gpu=GPU,
    volumes={HF_CACHE: hf_cache_vol, VLLM_CACHE: vllm_cache_vol, DATA_MOUNT: data_vol},
    secrets=hf_secrets,
    timeout=6 * 3600,
)
def label_dataset(
    csv_text: str,
    batch_size: int = 512,
    max_chars: int = 800,
    max_tokens: int = 160,
    text_col: str = "text_clean",
    out_name: str = "dataset_se2026_labeled.csv",
    system_prompt: str = DEFAULT_SYSTEM,
) -> dict[str, Any]:
    import csv
    import io
    import os

    from vllm import LLM, SamplingParams

    os.makedirs(LABEL_DIR, exist_ok=True)
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    items = [(i, r) for i, r in enumerate(rows) if (r.get(text_col) or "").strip()]

    progress: dict[str, Any] = {
        "status": "loading_model",
        "total": len(items),
        "done": 0,
        "ok": 0,
        "fail": 0,
        "by_label": {},
        "started_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
    }

    def write_progress() -> None:
        with open(f"{LABEL_DIR}/progress.json", "w", encoding="utf-8") as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
        data_vol.commit()

    write_progress()

    llm = LLM(
        model=MODEL_NAME,
        max_model_len=int(MAX_MODEL_LEN),
        gpu_memory_utilization=float(GPU_UTIL),
        limit_mm_per_prompt={"image": 0, "video": 0, "audio": 0},
        hf_overrides=HF_OVERRIDES,
        enforce_eager=os.environ.get("GEMMA_FAST_BOOT", "1") != "0",
        trust_remote_code=True,
    )
    params = SamplingParams(temperature=0.0, max_tokens=max_tokens)
    progress["status"] = "labeling"
    progress["model_loaded"] = True
    write_progress()

    results: dict[int, dict[str, Any]] = {}
    ckpt_path = f"{LABEL_DIR}/checkpoint.jsonl"
    with open(ckpt_path, "a", encoding="utf-8") as ckpt:
        for start in range(0, len(items), max(1, batch_size)):
            chunk = items[start : start + max(1, batch_size)]
            conversations = [
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": build_user_prompt(r.get(text_col) or "", max_chars)},
                ]
                for _, r in chunk
            ]
            outputs = llm.chat(conversations, sampling_params=params, use_tqdm=False)
            for (idx, row), out in zip(chunk, outputs):
                parsed = _parse_label(out.outputs[0].text)
                results[idx] = parsed
                ckpt.write(json.dumps({"idx": idx, "uid": row.get("uid"), "raw": out.outputs[0].text, **parsed}, ensure_ascii=False) + "\n")
                progress["done"] += 1
                if parsed["parse_ok"]:
                    progress["ok"] += 1
                    label = parsed["sentimen"]
                    progress["by_label"][label] = progress["by_label"].get(label, 0) + 1
                else:
                    progress["fail"] += 1
            ckpt.flush()
            write_progress()

    extra_cols = ["label", "aspek", "label_confidence", "label_reason", "label_parse_ok", "label_source"]
    for idx, row in enumerate(rows):
        parsed = results.get(idx)
        if parsed:
            row["label"] = parsed["sentimen"]
            row["aspek"] = "|".join(parsed["aspek"])
            row["label_confidence"] = round(parsed["keyakinan"], 4)
            row["label_reason"] = parsed["alasan"]
            row["label_parse_ok"] = parsed["parse_ok"]
            row["label_source"] = "gemma-4-12b-qat-unsloth"
        else:
            for col in extra_cols:
                row.setdefault(col, "")

    fieldnames: list[str] = []
    for row in rows:
        for k in row:
            if k not in fieldnames:
                fieldnames.append(k)
    for col in extra_cols:
        if col not in fieldnames:
            fieldnames.append(col)

    out_path = f"{LABEL_DIR}/{out_name}"
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    progress["status"] = "done"
    progress["output"] = out_path
    progress["finished_at"] = __import__("datetime").datetime.now().isoformat(timespec="seconds")
    write_progress()
    return progress


status_image = modal.Image.debian_slim(python_version="3.12")


@app.function(image=status_image, volumes={DATA_MOUNT: data_vol}, timeout=120)
def label_status() -> dict[str, Any]:
    path = f"{LABEL_DIR}/progress.json"
    if not os.path.exists(path):
        return {"status": "not_started"}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@app.local_entrypoint()
def main(action: str = "health", text: str = "Sensus ekonomi 2026 malah bikin takut kena pajak") -> None:
    if action == "health":
        print(health.remote())
    elif action == "test":
        print(label_batch.remote([text]))
    elif action == "status":
        print(json.dumps(label_status.remote(), ensure_ascii=False, indent=2))
    else:
        print(f"aksi tidak dikenal: {action} (pakai: health|test|status)")
