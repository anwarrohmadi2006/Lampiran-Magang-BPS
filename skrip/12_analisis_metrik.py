# Analisis Sentimen Sensus Ekonomi 2026 dan Aplikasi Fasih BPS
# 12 Analisis Metrik Lengkap
#
# Kegunaan : Menghitung presisi, recall, F1, dan dukungan tiap kelas sentimen, akurasi, F1 macro,
#            matriks konfusi, pecahan per sumber, pecahan per panjang teks, dan bak kalibrasi
#            keyakinan untuk setiap sistem.
# Masukan  : final/gold_uji.csv dan berkas prediksi tiap sistem
# Keluaran : reports/analisis_metrik_lengkap.json
# Rujukan  : Bab IV pada tabel metrik per kelas
#
# Menjalankan dari akar repositori:  py -3.13 analisis/12_analisis_metrik.py
"""Metrik lengkap per kelas untuk seluruh sistem pada dua ronde gold manusia.

Menghitung, untuk setiap sistem: presisi, recall, F1, dan dukungan tiap kelas
sentimen; akurasi; F1 macro; matriks konfusi 3x3 plus jumlah tebakan di luar
kelas sentimen; pecahan per sumber; pecahan per panjang teks; dan bak kalibrasi
keyakinan untuk sistem yang menyertakan peluang tiap kelas.

Keluaran: reports/analisis_metrik_lengkap.json dan cetakan tabel ke layar.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
KELAS = ("negatif", "netral", "positif")
KELUARAN = ROOT / "reports" / "analisis_metrik_lengkap.json"

RONDE = {
    "ronde1": {
        "gold": "final/gold_manusia.csv",
        "teks": None,
        "sistem": {
            "Prompt v2 (Gemma)": "final/prediksi_prompt_v2.csv",
            "Prompt v4 (Gemma)": "final/prediksi_prompt_v4.csv",
            "Prompt v5 (Gemma)": "final/prediksi_prompt_v5.csv",
            "DeepSeek V4.1 Flash": "final/prediksi_deepseek.csv",
            "Jev v4b (prompt)": "reports/uji_jev_api_v4b_100.csv",
            "IndoBERT Jev (latih)": "reports/prediksi_model_jev_ronde1.csv",
            "IndoBERT Gemma (lama)": "reports/prediksi_model_gemma_ronde1.csv",
        },
    },
    "ronde3": {
        "gold": "data/processed/v3/gold_ronde3_manusia.csv",
        "teks": "data/processed/v3/gold_kandidat_ronde3.csv",
        "sistem": {
            "Prompt v2 (Gemma)": "reports/prediksi_v2_ronde3.csv",
            "Jev v4b (prompt)": "reports/uji_jev_v4b_ronde3.csv",
            "IndoBERT Jev (latih)": "reports/prediksi_model_jev_ronde3.csv",
            "IndoBERT Gemma (lama)": "reports/prediksi_model_gemma_ronde3.csv",
        },
    },
}


def baca(rel: str) -> list[dict]:
    with (ROOT / rel).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def panjang_bucket(teks: str) -> str:
    n = len((teks or "").strip())
    if n < 25:
        return "pendek (<25)"
    if n < 100:
        return "sedang (25-99)"
    return "panjang (>=100)"


def metrik(pasangan: list[tuple[str, str]]) -> dict:
    """pasangan: (manusia, tebakan) untuk baris bersentimen."""
    n = len(pasangan)
    benar = sum(1 for a, b in pasangan if a == b)
    per_kelas = {}
    f1s = []
    for k in KELAS:
        tp = sum(1 for a, b in pasangan if a == k and b == k)
        fp = sum(1 for a, b in pasangan if a != k and b == k)
        fn = sum(1 for a, b in pasangan if a == k and b != k)
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        f = 2 * p * r / (p + r) if p + r else 0.0
        f1s.append(f)
        per_kelas[k] = {
            "precision": round(p, 4), "recall": round(r, 4),
            "f1": round(f, 4), "support": tp + fn,
        }
    m = [[0] * len(KELAS) for _ in KELAS]
    idx = {k: i for i, k in enumerate(KELAS)}
    luar = Counter()
    for a, b in pasangan:
        if b in idx:
            m[idx[a]][idx[b]] += 1
        else:
            luar[b or "(kosong)"] += 1
    return {
        "n": n,
        "accuracy": round(benar / n, 4) if n else None,
        "macro_f1": round(sum(f1s) / len(f1s), 4) if n else None,
        "per_kelas": per_kelas,
        "confusion": {"labels": list(KELAS), "matrix": m},
        "di_luar_kelas": dict(luar),
    }


def main() -> int:
    hasil: dict = {}
    for nama_ronde, cfg in RONDE.items():
        gold = baca(cfg["gold"])
        teks_kandidat: dict[str, dict] = {}
        if cfg["teks"]:
            for r in baca(cfg["teks"]):
                teks_kandidat[(r.get("uid") or "").strip()] = r

        manusia: dict[str, str] = {}
        sumber: dict[str, str] = {}
        panjang: dict[str, str] = {}
        for r in gold:
            u = (r.get("uid") or "").strip()
            lab = (r.get("label_manusia") or "").strip().lower()
            if not u:
                continue
            manusia[u] = lab
            k = teks_kandidat.get(u, {})
            sumber[u] = r.get("source") or k.get("source") or "?"
            teks = r.get("text_clean") or r.get("text") or k.get("text_clean") or k.get("text") or ""
            panjang[u] = panjang_bucket(teks)
        h = [u for u in manusia if manusia[u] in KELAS]

        sistem_hasil: dict[str, dict] = {}
        for nama, rel in cfg["sistem"].items():
            pred = {(r.get("uid") or "").strip(): (r.get("label") or "").strip().lower()
                    for r in baca(rel)}
            uids = [u for u in h if u in pred]
            pasangan = [(manusia[u], pred[u]) for u in uids]
            m = metrik(pasangan)
            m["cakupan"] = f"{len(uids)}/{len(h)}"
            # pecahan per sumber
            per_sumber = {}
            for s in sorted({sumber[u] for u in uids}):
                isi = [(manusia[u], pred[u]) for u in uids if sumber[u] == s]
                per_sumber[s] = {"n": len(isi),
                                 "accuracy": round(sum(1 for a, b in isi if a == b) / len(isi), 4)}
            m["per_sumber"] = per_sumber
            # pecahan per panjang
            per_panjang = {}
            for p in sorted({panjang[u] for u in uids}):
                isi = [(manusia[u], pred[u]) for u in uids if panjang[u] == p]
                per_panjang[p] = {"n": len(isi),
                                  "accuracy": round(sum(1 for a, b in isi if a == b) / len(isi), 4)}
            m["per_panjang"] = per_panjang
            # kalibrasi bila ada peluang
            baris_penuh = baca(rel)
            kolom_p = [k for k in baris_penuh[0] if k.startswith("p_")]
            if kolom_p and len(kolom_p) >= 3 and all(kolom_p):
                bak = [(0.0, 0.5), (0.5, 0.7), (0.7, 0.9), (0.9, 1.01)]
                kalibrasi = []
                peta_p = {r["uid"]: r for r in baris_penuh if r.get("uid") in pred}
                for bawah, atas in bak:
                    isi = []
                    for u in uids:
                        r = peta_p.get(u, {})
                        try:
                            yakin = max(float(r.get(k) or 0) for k in kolom_p)
                        except ValueError:
                            continue
                        if bawah <= yakin < atas:
                            isi.append((manusia[u], pred[u]))
                    if isi:
                        kalibrasi.append({
                            "rentang": f"{bawah:.2f}-{atas:.2f}",
                            "n": len(isi),
                            "ketepatan": round(sum(1 for a, b in isi if a == b) / len(isi), 4),
                        })
                m["kalibrasi_keyakinan"] = kalibrasi
            sistem_hasil[nama] = m
        hasil[nama_ronde] = {
            "gold": cfg["gold"],
            "n_baris": len(manusia),
            "n_bersentimen": len(h),
            "sebaran_manusia": dict(Counter(manusia[u] for u in manusia)),
            "sistem": sistem_hasil,
        }

        print(f"\n================ {nama_ronde} (n bersentimen {len(h)}) ================")
        for s in sorted({u for u in manusia}):
            pass
        for nama, m in sistem_hasil.items():
            print(f"\n[{nama}] n={m['n']} akurasi={m['accuracy']:.4f} F1 macro={m['macro_f1']:.4f}")
            print("  kelas     presisi  recall  F1     dukung")
            for k in KELAS:
                pk = m["per_kelas"][k]
                print(f"  {k:8s}  {pk['precision']:.3f}    {pk['recall']:.3f}   {pk['f1']:.3f}  {pk['support']:4d}")
            print(f"  tebakan di luar kelas: {m['di_luar_kelas']}")
            print("  per sumber : " + "  ".join(f"{s}:{v['accuracy']:.3f}({v['n']})"
                                               for s, v in m["per_sumber"].items()))
            print("  per panjang: " + "  ".join(f"{p}:{v['accuracy']:.3f}({v['n']})"
                                               for p, v in m["per_panjang"].items()))
            if m.get("kalibrasi_keyakinan"):
                print("  kalibrasi  : " + "  ".join(f"{k['rentang']}:{k['ketepatan']:.3f}({k['n']})"
                                                    for k in m["kalibrasi_keyakinan"]))

    KELUARAN.write_text(json.dumps(hasil, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nringkasan -> {KELUARAN.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
