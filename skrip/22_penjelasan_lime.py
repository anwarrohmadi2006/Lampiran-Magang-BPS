# Analisis Sentimen Sensus Ekonomi 2026 dan Aplikasi Fasih BPS
# 22 Penjelasan LIME Model Final
#
# Kegunaan : Menghitung pengaruh token terhadap keputusan model pada tingkat satu teks
#            dengan perturbasi berulang, lalu meringkas token teratas tiap kelas.
# Masukan  : reports/modal/ablasi_jev/best_model dan data/processed/v3/dataset_jev_uji.csv
# Keluaran : final/lime/lime_top_tokens.png, lime_top_tokens.csv, dan contoh HTML tiap teks
# Rujukan  : Bab IV pada Gambar 4.6 serta Lampiran 4
#
# Menjalankan dari akar repositori:  py -3.13 analisis/22_penjelasan_lime.py
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# TensorFlow tidak dipakai penelitian ini dan pemasangannya di mesin ini rusak,
# sehingga pustaka transformers gagal ketika mencoba mengimpornya secara tidak
# sengaja melalui modul transformasi citra. Penetapan ini harus dilakukan
# sebelum transformers diimpor. Berkas lain pada folder ini sudah melakukannya;
# berkas ini sebelumnya terlewat sehingga gagal dijalankan.
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")

from scraper.dataset import read_rows  # noqa: E402

INSTALL_HINT = (
    "Dependensi XAI belum terpasang. Jalankan:\n"
    "  pip install torch transformers lime scikit-learn matplotlib pandas"
)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Explainable AI (LIME + attention rollout) untuk IndoBERT")
    p.add_argument("model_dir", help="folder model hasil train_indobert.py")
    p.add_argument("csv_path", help="CSV data (berlabel atau tidak)")
    p.add_argument("--text-col", default="text_clean")
    p.add_argument("--label-col", default="label")
    p.add_argument("--method", default="both", choices=["lime", "attention", "both"])
    p.add_argument("--n-samples", type=int, default=30, help="jumlah teks yang dijelaskan")
    p.add_argument("--select", default="all", choices=["all", "correct", "misclassified"])
    p.add_argument("--num-features", type=int, default=12, help="token teratas per kelas (LIME)")
    p.add_argument("--num-perturbations", type=int, default=600, help="num_samples LIME")
    p.add_argument("--batch-size", type=int, default=32,
                   help="jumlah teks per satu pengambilan keputusan model")
    p.add_argument("--html-n", type=int, default=5, help="jumlah HTML example LIME")
    p.add_argument("--max-len", type=int, default=128)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", default="reports/xai")
    return p.parse_args(argv)


def load_model(model_dir: str):
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir, output_attentions=True)
    model.eval()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    label_map_path = Path(model_dir) / "label_map.json"
    if label_map_path.exists():
        label2id = json.loads(label_map_path.read_text(encoding="utf-8"))
        id2label = {i: l for l, i in label2id.items()}
    else:
        id2label = {i: model.config.id2label[i] for i in sorted(model.config.id2label)}
        label2id = {v: k for k, v in id2label.items()}
    return tokenizer, model, device, label2id, id2label


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        import numpy as np
        import torch
    except ImportError as e:
        print(f"{INSTALL_HINT}\n\nDetail: {e}", file=sys.stderr)
        return 1

    tokenizer, model, device, label2id, id2label = load_model(args.model_dir)
    class_names = [id2label[i] for i in range(len(id2label))]

    rows = read_rows(args.csv_path)
    data = [
        {
            "uid": r.get("uid"),
            "source": r.get("source"),
            "text": (r.get(args.text_col) or "").strip(),
            "label": (r.get(args.label_col) or "").strip().lower(),
        }
        for r in rows
        if (r.get(args.text_col) or "").strip()
    ]
    if not data:
        print("tidak ada teks valid di CSV", file=sys.stderr)
        return 1

    def predict_proba(texts: list[str]):
        """Menghitung peluang kelas untuk sekumpulan teks.

        Teks diproses berkelompok, bukan sekaligus. LIME mengirimkan seluruh
        teks perturbasi dalam satu panggilan — ratusan teks sekaligus — dan
        karena model dimuat dengan keluaran atensi, satu tembakan sebesar itu
        menghabiskan memori GPU: pada T4 penjalanan berhenti dengan
        CUDA out of memory saat mencoba menyediakan 2,13 GiB.
        """
        keluaran = []
        daftar = list(texts)
        with torch.no_grad():
            for mulai in range(0, len(daftar), args.batch_size):
                potong = daftar[mulai : mulai + args.batch_size]
                enc = tokenizer(
                    potong,
                    padding=True,
                    truncation=True,
                    max_length=args.max_len,
                    return_tensors="pt",
                ).to(device)
                logits = model(**enc).logits
                keluaran.append(torch.softmax(logits, dim=-1).cpu())
        if not keluaran:
            return torch.zeros((0, 3)).numpy()
        return torch.cat(keluaran, dim=0).numpy()

    sample_texts = [d["text"] for d in data]
    all_probs = predict_proba(sample_texts)
    pred_ids = all_probs.argmax(axis=-1)
    for i, d in enumerate(data):
        d["pred"] = class_names[int(pred_ids[i])]
        d["confidence"] = float(all_probs[i].max())

    def matches(d) -> bool:
        if not d["label"]:
            return args.select == "all"
        if args.select == "correct":
            return d["label"] == d["pred"]
        if args.select == "misclassified":
            return d["label"] != d["pred"]
        return True

    pool = [d for d in data if matches(d)]
    random.Random(args.seed).shuffle(pool)
    picked = pool[: args.n_samples]

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"label kelas : {class_names}")
    print(f"dijelaskan  : {len(picked)} dari {len(data)} teks (select={args.select})")

    if args.method in ("lime", "both"):
        try:
            _run_lime(picked, predict_proba, class_names, args, out_dir)
        except ImportError as e:
            print(f"LIME gagal (import): {e}", file=sys.stderr)

    if args.method in ("attention", "both"):
        _run_attention(picked, tokenizer, model, device, class_names, args, out_dir)

    print(f"\noutput XAI -> {out_dir.resolve()}")
    return 0


def _run_lime(picked, predict_proba, class_names, args, out_dir: Path) -> None:
    from lime.lime_text import LimeTextExplainer

    explainer = LimeTextExplainer(class_names=class_names, split_expression=r"\s+")
    per_class: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    detail_path = out_dir / "explanations_lime.csv"
    n_html = 0

    with detail_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["uid", "source", "text", "label_true", "label_pred", "confidence", "class", "token", "weight"])
        for d in picked:
            exp = explainer.explain_instance(
                d["text"],
                predict_proba,
                labels=list(range(len(class_names))),
                num_features=args.num_features,
                num_samples=args.num_perturbations,
            )
            for c, name in enumerate(class_names):
                for token, weight in exp.as_list(label=c):
                    w.writerow([
                        d["uid"], d["source"], d["text"], d["label"], d["pred"],
                        round(d["confidence"], 4), name, token, round(float(weight), 6),
                    ])
                    per_class[name][token].append(float(weight))
            if n_html < args.html_n:
                html_path = out_dir / f"lime_example_{n_html + 1}.html"
                html_path.write_text(exp.as_html(), encoding="utf-8")
                n_html += 1

    summary_path = out_dir / "lime_top_tokens.csv"
    with summary_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["class", "token", "mean_weight", "n_samples", "direction"])
        for name in class_names:
            ranked = sorted(per_class[name].items(), key=lambda kv: -abs(sum(kv[1]) / len(kv[1])))
            for token, weights in ranked[:20]:
                mean = sum(weights) / len(weights)
                w.writerow([name, token, round(mean, 6), len(weights), "positif" if mean > 0 else "negatif"])

    _plot_top_tokens(per_class, class_names, out_dir / "lime_top_tokens.png")
    print(f"LIME detail -> {detail_path}")
    print(f"LIME ringkas -> {summary_path}")


def _plot_top_tokens(per_class, class_names, out_path: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return

    ncols = len(class_names)
    fig, axes = plt.subplots(1, ncols, figsize=(5 * ncols, 5))
    if ncols == 1:
        axes = [axes]
    for ax, name in zip(axes, class_names):
        ranked = sorted(per_class[name].items(), key=lambda kv: -abs(sum(kv[1]) / len(kv[1])))[:15]
        tokens = [t for t, _ in ranked][::-1]
        weights = [sum(ws) / len(ws) for _, ws in ranked][::-1]
        colors = ["#2f855a" if w > 0 else "#c53030" for w in weights]
        ax.barh(tokens, weights, color=colors)
        ax.set_title(f"LIME - kelas {name}")
        ax.set_xlabel("bobot rata-rata (hijau=pendukung, merah=penentang)")
        ax.axvline(0, color="black", linewidth=0.8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def _attention_rollout(attentions, discard_ratio: float = 0.0):
    import torch

    result = torch.eye(attentions[0].size(-1), device=attentions[0].device)
    for attn in attentions:
        a = attn.mean(dim=1)[0]
        if discard_ratio > 0:
            flat = a.view(-1)
            n = int(flat.numel() * discard_ratio)
            if n > 0:
                thresh = flat.topk(n, largest=False).values.max()
                a = torch.where(a <= thresh, torch.zeros_like(a), a)
        a = a + torch.eye(a.size(-1), device=a.device)
        a = a / a.sum(dim=-1, keepdim=True)
        result = a @ result
    return result


def _run_attention(picked, tokenizer, model, device, class_names, args, out_dir: Path) -> None:
    import torch

    detail_path = out_dir / "explanations_attention.csv"
    per_class: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    with detail_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["uid", "source", "text", "label_pred", "confidence", "position", "token", "importance"])
        for d in picked:
            enc = tokenizer(
                d["text"], truncation=True, max_length=args.max_len, return_tensors="pt"
            ).to(device)
            with torch.no_grad():
                out = model(**enc)
            if not out.attentions:
                continue
            rollout = _attention_rollout(out.attentions)
            importance = rollout[0, 0].cpu().tolist()
            tokens = tokenizer.convert_ids_to_tokens(enc["input_ids"][0])
            for pos, (tok, imp) in enumerate(zip(tokens, importance)):
                if tok in tokenizer.all_special_tokens:
                    continue
                w.writerow([
                    d["uid"], d["source"], d["text"], d["pred"],
                    round(d["confidence"], 4), pos, tok, round(float(imp), 6),
                ])
                per_class[d["pred"]][tok].append(float(imp))

    summary_path = out_dir / "attention_top_tokens.csv"
    with summary_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["class", "token", "mean_importance", "n_samples"])
        for name in class_names:
            ranked = sorted(per_class[name].items(), key=lambda kv: -sum(kv[1]) / len(kv[1]))
            for token, vals in ranked[:20]:
                w.writerow([name, token, round(sum(vals) / len(vals), 6), len(vals)])
    print(f"attention detail -> {detail_path}")
    print(f"attention ringkas-> {summary_path}")


if __name__ == "__main__":
    raise SystemExit(main())
