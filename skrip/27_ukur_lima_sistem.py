# Analisis Sentimen Sensus Ekonomi 2026 dan Aplikasi Fasih BPS
# 27 Pengukuran Lima Sistem
#
# Kegunaan : Mengukur lima sistem pada satu data uji manusia sekaligus, yaitu
#            prompt Gemma v2, anotator Jev v4b, IndoBERT pada label Jev dengan
#            pemilahan Gemma (pipeline lama), IndoBERT pada label Jev dengan
#            pemilahan Jev (pipeline langsung), dan IndoBERT pada label Gemma
#            (pembanding). Hasilnya menggantikan final/evaluasi_uji.json.
# Masukan  : final/gold_uji.csv dan berkas prediksi tiap sistem
# Keluaran : final/evaluasi_uji.json (diperbarui) dan cetakan ringkasan
# Rujukan  : Bab IV Tabel 4.6; Bab V Simpulan
#
# Menjalankan dari akar repositori:  py -3.13 analisis/27_ukur_lima_sistem.py
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "final"
GOLD = FINAL / "gold_uji.csv"
KELUARAN = FINAL / "evaluasi_uji.json"

SISTEM: list[tuple[str, str]] = [
    ("prediksi_uji_prompt_v2.csv", ""),
    ("prediksi_uji_jev_v4b.csv", ""),
    ("prediksi_uji_indobert_jev.csv", ""),
    ("prediksi_uji_indobert_gemma.csv", ""),
    ("prediksi_uji_indobert_jevlangsung.csv",
     "reports/prediksi_model_jev_langsung_ronde3.csv"),
]


def main() -> int:
    # Salin prediksi sistem baru dari folder kerja ke folder final bila perlu.
    for nama, asal in SISTEM:
        tujuan = FINAL / nama
        if not asal or tujuan.is_file():
            continue
        sumber = ROOT / asal
        if not sumber.is_file():
            print(f"peringatan: prediksi sistem baru belum ada: {asal}")
            return 1
        shutil.copy2(sumber, tujuan)
        print(f"disalin: final/{nama} <- {asal}")

    ada = [str(FINAL / nama) for nama, _ in SISTEM if (FINAL / nama).is_file()]
    if len(ada) < 5:
        print(f"peringatan: hanya {len(ada)} dari 5 berkas prediksi tersedia")
        return 1

    perintah = [
        sys.executable, str(ROOT / "modeling" / "gold_eval.py"), "eval",
        "--gold", str(GOLD), "--pred", *ada, "--out", str(KELUARAN),
    ]
    proses = subprocess.run(perintah, cwd=str(ROOT))
    if proses.returncode:
        return proses.returncode

    hasil = json.loads(KELUARAN.read_text(encoding="utf-8-sig"))
    print(f"\nbaris dinilai : {hasil.get('gold_n')}")
    for nama, m in (hasil.get("sistem") or {}).items():
        if isinstance(m, dict):
            print(f"  {nama:28s} akurasi={m.get('accuracy')} "
                  f"F1 macro={m.get('f1_macro')}")

    # Rincian per kelas untuk seluruh sistem, sekaligus baris siap tempel untuk
    # tabel rincian per kelas pada laporan.
    import csv as _csv

    kelas = ["negatif", "netral", "positif"]
    with GOLD.open(encoding="utf-8-sig", newline="") as f:
        manusia = {r["uid"]: (r.get("label_manusia") or "").strip().lower()
                   for r in _csv.DictReader(f)}
    rincian: dict = {}
    for nama, _ in SISTEM:
        berkas = FINAL / nama
        if not berkas.is_file():
            continue
        with berkas.open(encoding="utf-8-sig", newline="") as f:
            tebak = {r["uid"]: (r.get("label") or "").strip().lower()
                     for r in _csv.DictReader(f) if r.get("uid")}
        baris = {}
        for k in kelas:
            tp = fp = fn = 0
            for uid, benar in manusia.items():
                t = tebak.get(uid, "")
                if t not in kelas:
                    continue
                if benar == k and t == k:
                    tp += 1
                elif t == k and benar != k:
                    fp += 1
                elif benar == k and t != k:
                    fn += 1
            p = tp / (tp + fp) if tp + fp else 0.0
            rr = tp / (tp + fn) if tp + fn else 0.0
            f1 = 2 * p * rr / (p + rr) if p + rr else 0.0
            baris[k] = {"presisi": round(p, 3), "recall": round(rr, 3),
                        "f1": round(f1, 3), "dukungan": tp + fn}
        rincian[nama] = baris
    (ROOT / "reports" / "metrik_per_kelas_lima_sistem.json").write_text(
        json.dumps(rincian, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nbaris tabel per kelas untuk sistem baru (siap tempel):")
    for k in kelas:
        b = rincian.get("prediksi_uji_indobert_jevlangsung.csv", {}).get(k)
        if b:
            print(f'        ["IndoBERT pada label Jev (pemilahan Jev)", "{k}", '
                  f'"{b["presisi"]:.3f}".replace(".", ","), '
                  f'"{b["recall"]:.3f}".replace(".", ","), '
                  f'"{b["f1"]:.3f}".replace(".", ","), "{b["dukungan"]}"],')
    for nama, baris in rincian.items():
        print(f"  {nama:34s} " + "; ".join(
            f"{k}: F1={v['f1']:.3f}" for k, v in baris.items()))

    catatan = FINAL / "catatan_uji.md"
    if catatan.is_file():
        teks = catatan.read_text(encoding="utf-8")
        tanda = "## Sistem kelima"
        if tanda not in teks:
            tambahan = (
                f"\n{tanda}\n\n"
                "Sejak pipeline Jev langsung dijalankan, pengukuran memuat lima sistem: "
                "prompt Gemma v2, anotator Jev v4b, IndoBERT dengan pemilahan Gemma, "
                "IndoBERT dengan pemilahan Jev, dan IndoBERT pembanding berlabel Gemma. "
                "Berkasnya adalah `prediksi_uji_indobert_jevlangsung.csv`, dan seluruh "
                "angkanya dihitung ulang oleh `analisis/27_ukur_lima_sistem.py`.\n"
            )
            catatan.write_text(teks + tambahan, encoding="utf-8")
            print("catatan_uji.md diperbarui")
    print("evaluasi     : final/evaluasi_uji.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
