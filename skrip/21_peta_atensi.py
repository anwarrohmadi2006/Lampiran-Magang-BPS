# Analisis Sentimen Sensus Ekonomi 2026 dan Aplikasi Fasih BPS
# 21 Peta Atensi Model Final
#
# Kegunaan : Menghitung profil atensi tiap lapisan, skor attention rollout, dan matriks
#            atensi penuh untuk sejumlah teks contoh dari model terbaik.
# Masukan  : reports/modal/ablasi_jev/best_model dan data/processed/v3/dataset_jev_uji.csv
# Keluaran : final/atensi/attention_*.png, attention_matrix.png, attention_summary.json, attention_gallery.html
# Rujukan  : Bab IV pada Gambar 4.5 serta Lampiran 4
#
# Menjalankan dari akar repositori:  py -3.13 analisis/21_peta_atensi.py
"""Penjelasan model berbasis peta atensi untuk IndoBERT Sensus Ekonomi 2026.

Modul ini menghasilkan peta panas (heatmap) yang mudah dibaca manusia untuk
menjawab pertanyaan "token mana yang diperhatikan model ketika menetapkan
sentimen?". Dua sudut pandang yang disajikan yaitu:

    1. Profil atensi token klasifikasi terhadap setiap token masukan pada tiap
       lapisan, sehingga terlihat lapisan mana yang mulai menangkap isyarat.
    2. Attention rollout yang merambatkan atensi lintas lapisan menjadi satu
       skor kepentingan per token.

Selain itu, modul ini menggambar matriks atensi penuh antar token untuk satu
lapisan terpilih, sehingga pola hubungan antar kata dapat diamati langsung.

Rujukan:
    - AttentionViz (arXiv:2305.03210, 2023)            -> visualisasi atensi global
    - Survei XAI (arXiv:2501.09967, 2025)              -> taksonomi metode penjelasan
    - Survei XAI untuk LLM (arXiv:2506.21812, 2025)    -> praktik penjelasan model bahasa

Catatan: peta atensi menunjukkan korelasi, bukan bukti kausalitas. Penjelasan
ini harus dibaca bersama metrik kinerja dan pemeriksaan manual.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault("USE_TF", "0")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraper.dataset import read_rows  # noqa: E402


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Peta atensi IndoBERT untuk sentimen SE2026")
    p.add_argument("model_dir", help="folder model hasil pelatihan")
    p.add_argument("csv_path", help="CSV berlabel untuk mengambil contoh teks")
    p.add_argument("--text-col", default="text_clean")
    p.add_argument("--label-col", default="label")
    p.add_argument("--n-samples", type=int, default=8)
    p.add_argument("--select", default="all", choices=["all", "correct", "misclassified"])
    p.add_argument("--layer", type=int, default=-1, help="lapisan untuk matriks atensi penuh")
    p.add_argument("--max-len", type=int, default=64)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", default="reports/xai_attention")
    return p.parse_args(argv)


def attention_rollout(attentions) -> Any:
    """Merambatkan atensi lintas lapisan menjadi skor kepentingan per token.

    Setiap unsur `attentions` berbentuk (kepala, token, token), sehingga
    perataan dilakukan pada dimensi kepala. Selanjutnya matriks atensi ditambah
    matriks identitas agar token tetap memperhatikan dirinya sendiri, lalu
    dinormalkan dan dikalikan berurutan antar lapisan.
    """
    import torch

    size = attentions[0].size(-1)
    result = torch.eye(size)
    for attn in attentions:
        a = attn.mean(dim=0).cpu()
        a = a + torch.eye(a.size(-1))
        a = a / a.sum(dim=-1, keepdim=True)
        result = a @ result
    return result


def analyse_sample(model, tokenizer, text: str, max_len: int, layer: int = -1) -> dict[str, Any]:
    """Menghitung peta atensi, prediksi, dan skor kepentingan untuk satu teks."""
    import torch

    device = next(model.parameters()).device
    enc = tokenizer(text, truncation=True, max_length=max_len, return_tensors="pt")
    enc = {k: v.to(device) for k, v in enc.items()}
    with torch.no_grad():
        out = model(**enc)

    probs = torch.softmax(out.logits.float(), dim=-1)[0]
    pred_id = int(probs.argmax())
    id2label = {int(k): v for k, v in model.config.id2label.items()}

    tokens = tokenizer.convert_ids_to_tokens(enc["input_ids"][0])
    attentions = [a[0] for a in out.attentions]  # (lapisan, kepala, token, token)

    # Profil atensi token klasifikasi: rata-rata seluruh kepala per lapisan.
    cls_profile = torch.stack([a.mean(dim=0)[0] for a in attentions]).cpu().numpy()

    # Matriks atensi penuh untuk lapisan terpilih, dirata-ratakan antar kepala.
    layer_idx = layer if layer >= 0 else len(attentions) + layer
    layer_idx = max(0, min(layer_idx, len(attentions) - 1))
    full_matrix = attentions[layer_idx].mean(dim=0).cpu().numpy()

    # Attention rollout menghasilkan satu skor kepentingan per token.
    rollout = attention_rollout(attentions)
    importance = rollout[0].cpu().numpy().tolist()

    return {
        "text": text,
        "tokens": tokens,
        "pred": id2label.get(pred_id, str(pred_id)),
        "confidence": round(float(probs.max()), 4),
        "probabilities": {id2label.get(i, str(i)): round(float(p), 4) for i, p in enumerate(probs)},
        "cls_profile": cls_profile.tolist(),
        "full_matrix": full_matrix.tolist(),
        "importance": [round(float(v), 6) for v in importance],
        "layer_used": layer_idx,
    }


def plot_sample(sample: dict[str, Any], path: Path) -> None:
    """Menggambar dua panel: profil atensi per lapisan dan skor kepentingan token."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    tokens = sample["tokens"]
    profile = np.array(sample["cls_profile"])
    importance = np.array(sample["importance"])

    fig, axes = plt.subplots(2, 1, figsize=(max(8, len(tokens) * 0.34), 7.2))

    im = axes[0].imshow(profile, aspect="auto", cmap="viridis")
    axes[0].set_yticks(range(profile.shape[0]))
    axes[0].set_yticklabels([f"L{i}" for i in range(profile.shape[0])], fontsize=7)
    axes[0].set_xticks(range(len(tokens)))
    axes[0].set_xticklabels(tokens, rotation=90, fontsize=7)
    axes[0].set_title(
        f"Profil atensi token klasifikasi per lapisan (prediksi: {sample['pred']} "
        f"dengan keyakinan {sample['confidence']:.3f})",
        fontsize=10,
    )
    fig.colorbar(im, ax=axes[0], fraction=0.02, pad=0.01, label="bobot atensi")

    colors = ["#2b6cb0" if t not in ("[CLS]", "[SEP]") else "#a0aec0" for t in tokens]
    axes[1].bar(range(len(tokens)), importance, color=colors)
    axes[1].set_xticks(range(len(tokens)))
    axes[1].set_xticklabels(tokens, rotation=90, fontsize=7)
    axes[1].set_title("Skor kepentingan token hasil attention rollout", fontsize=10)
    axes[1].set_ylabel("kepentingan")

    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_full_matrix(sample: dict[str, Any], path: Path) -> None:
    """Menggambar matriks atensi penuh antar pasangan token pada lapisan terpilih."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    tokens = sample["tokens"]
    matrix = np.array(sample["full_matrix"])
    fig, ax = plt.subplots(figsize=(max(7, len(tokens) * 0.3), max(6, len(tokens) * 0.28)))
    im = ax.imshow(matrix, cmap="magma")
    ax.set_xticks(range(len(tokens)))
    ax.set_xticklabels(tokens, rotation=90, fontsize=7)
    ax.set_yticks(range(len(tokens)))
    ax.set_yticklabels(tokens, fontsize=7)
    ax.set_title(f"Matriks atensi penuh lapisan {sample['layer_used']}", fontsize=10)
    ax.set_xlabel("token tujuan")
    ax.set_ylabel("token sumber")
    fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02, label="bobot atensi")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def write_gallery(samples: list[dict[str, Any]], out_dir: Path, meta: dict[str, Any]) -> None:
    """Menyusun galeri HTML agar penjelasan model mudah dibaca dan dibagikan."""
    rows = []
    for i, s in enumerate(samples, 1):
        prob = " · ".join(f"{k}: {v:.3f}" for k, v in s["probabilities"].items())
        paired = sorted(zip(s["tokens"], s["importance"]), key=lambda kv: -kv[1])[:10]
        top = ", ".join(f"{t} ({v:.4f})" for t, v in paired)
        rows.append(
            f"""<section>
<h3>Contoh {i} — prediksi <span class="tag">{s['pred']}</span> (keyakinan {s['confidence']:.3f})</h3>
<p class="text">{s['text'][:400]}</p>
<p class="meta">Probabilitas kelas: {prob}</p>
<p class="meta">Label acuan (anotasi lemah): {s.get('label_true') or '-'}</p>
<img src="attention_{i}.png" alt="peta atensi contoh {i}">
<p class="meta">Sepuluh token paling berpengaruh: {top}</p>
</section>"""
        )

    html = f"""<!doctype html>
<html lang="id"><head><meta charset="utf-8">
<title>Peta Atensi IndoBERT - Sentimen Sensus Ekonomi 2026</title>
<style>
body{{font-family:system-ui,Segoe UI,sans-serif;margin:0;background:#f7fafc;color:#1a202c}}
header{{background:#1a365d;color:#fff;padding:22px 26px}}
header h1{{margin:0 0 6px;font-size:20px}}
header p{{margin:0;opacity:.85;font-size:13px}}
main{{max-width:1000px;margin:0 auto;padding:20px 26px 60px}}
section{{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:16px 18px;margin:18px 0}}
h3{{margin:0 0 8px;font-size:15px}}
.tag{{background:#2b6cb0;color:#fff;border-radius:5px;padding:1px 8px;font-size:12px}}
.text{{background:#f7fafc;border-left:3px solid #2b6cb0;padding:9px 11px;border-radius:4px;font-size:13px}}
.meta{{color:#4a5568;font-size:12px;margin:5px 0}}
img{{width:100%;border:1px solid #e2e8f0;border-radius:6px;margin-top:8px}}
</style></head><body>
<header>
<h1>Peta Atensi IndoBERT — Analisis Sentimen Sensus Ekonomi 2026</h1>
<p>Model {meta['model_name']} · {meta['n_samples']} contoh · panjang token maksimum {meta['max_len']}</p>
</header>
<main>
<p class="meta">Peta panas di bawah menunjukkan bobot atensi token klasifikasi terhadap
setiap token masukan pada tiap lapisan (panel atas) serta skor kepentingan token
hasil attention rollout (panel bawah). Warna terang menandakan atensi besar.</p>
{''.join(rows)}
</main></body></html>"""
    (out_dir / "attention_gallery.html").write_text(html, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(args.model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model_dir, output_attentions=True
    ).to(device)
    model.eval()

    rows = read_rows(args.csv_path)
    data: list[dict[str, Any]] = []
    for r in rows:
        text = (r.get(args.text_col) or "").strip()
        if text:
            data.append({"text": text, "label": (r.get(args.label_col) or "").strip().lower()})

    random.Random(args.seed).shuffle(data)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    picked: list[dict[str, Any]] = []
    for item in data:
        if len(picked) >= args.n_samples:
            break
        sample = analyse_sample(model, tokenizer, item["text"], args.max_len, args.layer)
        if args.select == "correct" and sample["pred"] != item["label"]:
            continue
        if args.select == "misclassified" and (not item["label"] or sample["pred"] == item["label"]):
            continue
        sample["label_true"] = item["label"]
        picked.append(sample)

    for i, sample in enumerate(picked, 1):
        plot_sample(sample, out_dir / f"attention_{i}.png")
        if i == 1:
            plot_full_matrix(sample, out_dir / "attention_matrix.png")

    with (out_dir / "attention_top_tokens.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["contoh", "prediksi", "keyakinan", "peringkat", "token", "kepentingan"])
        for i, sample in enumerate(picked, 1):
            ranked = sorted(zip(sample["tokens"], sample["importance"]), key=lambda kv: -kv[1])[:15]
            for rank, (token, value) in enumerate(ranked, 1):
                writer.writerow([i, sample["pred"], sample["confidence"], rank, token, round(value, 6)])

    meta = {
        "model_name": args.model_dir,
        "csv_path": args.csv_path,
        "n_samples": len(picked),
        "max_len": args.max_len,
        "select": args.select,
    }
    (out_dir / "attention_summary.json").write_text(
        json.dumps(
            {
                "metadata": meta,
                "samples": [
                    {
                        "text": s["text"][:300],
                        "pred": s["pred"],
                        "confidence": s["confidence"],
                        "label_true": s.get("label_true"),
                        "top_tokens": sorted(
                            zip(s["tokens"], s["importance"]), key=lambda kv: -kv[1]
                        )[:10],
                    }
                    for s in picked
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    write_gallery(picked, out_dir, meta)

    print(f"jumlah contoh    : {len(picked)}")
    print(f"galeri HTML      : {out_dir / 'attention_gallery.html'}")
    print(f"ringkasan JSON   : {out_dir / 'attention_summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
