# Analisis Sentimen Sensus Ekonomi 2026 dan Aplikasi Fasih BPS
# 10 Kesepakatan Antar Penilai
#
# Kegunaan : Menghitung kesepakatan antar penilai data uji dengan Cohen's kappa pada dua
#            sudut pandang, yaitu seluruh kelas apa adanya dan hanya kelas sentimen setelah baris
#            tidak relevan dikeluarkan.
# Masukan  : final/gold_uji.csv, data/processed/gold_asisten_100.csv, dan label model
# Keluaran : final/kappa_gold.json dan reports/kappa_*.json
# Rujukan  : Bab IV pada bagian kesepakatan antar penilai
#
# Menjalankan dari akar repositori:  py -3.13 analisis/10_kappa_gold.py
"""Menghitung kesepakatan antar penilai gold dengan Cohen's kappa.

Dipakai untuk membandingkan label asisten dengan label manusia pada baris yang
sama. Dua sudut pandang dihitung terpisah: seluruh empat kelas apa adanya, dan
hanya kelas sentimen setelah baris tidak relevan dikeluarkan. Yang kedua penting
karena kesepakatan pada relevansi dan kesepakatan pada sentimen adalah dua
persoalan berbeda, dan menggabungkannya dapat menutupi masalah di salah satunya.

Kesepakatan pada putusan relevan dihitung tersendiri sebagai ukuran ketiga,
sebab seluruh kelas sangat tidak seimbang: hampir semua baris relevan, sehingga
kesepakatan mentahnya selalu tampak tinggi sementara kappanya mendekati nol.

Menjalankan:
    py -3.13 modeling/kappa_gold.py                 # seluruh pasangan tetap
    py -3.13 modeling/kappa_gold.py --semua         # sama, dan menulis JSON
    py -3.13 modeling/kappa_gold.py --a <berkas> --kolom-a <kolom> \
                                    --b <berkas> --kolom-b <kolom>
    py -3.13 modeling/kappa_gold.py --selftest
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AKAR = Path(__file__).resolve().parent.parent
SENTIMEN = ("negatif", "netral", "positif")
SEMUA = ("negatif", "netral", "positif", "tidak_relevan")

# Pasangan yang dihitung sekaligus oleh --semua. Setiap pasangan berpasangan
# lewat uid dan menunjuk berkas yang benar-benar ada; pasangan yang berkasnya
# tidak ditemukan dilewati dengan catatan, bukan digagalkan.
PASANGAN_TETAP = [
    {
        "id": "v2_vs_manusia",
        "nama": "Skema anotasi awal terhadap penilaian manusia",
        "a": "final/prediksi_prompt_v2.csv", "kolom_a": "label",
        "b": "final/gold_manusia.csv", "kolom_b": "label_manusia",
        "catatan": "Seratus baris gold ronde pertama yang ditarik berlapis dan "
                   "tersamar. Pasangan inilah yang menghasilkan akurasi 0,7391.",
    },
    {
        "id": "v4_vs_manusia",
        "nama": "Skema anotasi perbaikan terhadap penilaian manusia",
        "a": "final/prediksi_prompt_v4.csv", "kolom_a": "label",
        "b": "final/gold_manusia.csv", "kolom_b": "label_manusia",
        "catatan": "Kandidat pengganti yang tidak dipakai karena perbedaannya "
                   "terhadap skema awal belum nyata secara statistik.",
    },
    {
        "id": "v5_vs_manusia",
        "nama": "Skema anotasi bernalar terhadap penilaian manusia",
        "a": "final/prediksi_prompt_v5.csv", "kolom_a": "label",
        "b": "final/gold_manusia.csv", "kolom_b": "label_manusia",
        "catatan": "Skema yang menuntut penalaran ditulis sebelum sentimen ditetapkan.",
    },
    {
        "id": "deepseek_vs_manusia",
        "nama": "Anotator keluarga lain terhadap penilaian manusia",
        "a": "final/prediksi_deepseek.csv", "kolom_a": "label",
        "b": "final/gold_manusia.csv", "kolom_b": "label_manusia",
        "catatan": "Pembanding dari keluarga model berbeda, diuji pada gold yang sama.",
    },
    {
        "id": "model_vs_anotator2",
        "nama": "Usulan model terhadap penilai kedua pada ronde kedua",
        "a": "final/gold_kandidat_ronde2.csv", "kolom_a": "label_sementara",
        "b": "final/gold_anotator2_ronde2.csv", "kolom_b": "label",
        "catatan": "Seratus baris ini sengaja ditarik dari keyakinan model terendah, "
                   "sehingga memang baris tersulit. Angkanya tidak sebanding dengan "
                   "angka pada seratus baris acak berlapis.",
    },
]


def muat(path: Path, kolom: str) -> dict[str, str]:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        return {
            b["uid"]: (b.get(kolom) or "").strip().lower()
            for b in csv.DictReader(f)
            if b.get("uid") and (b.get(kolom) or "").strip()
        }


def kappa(pasangan: list[tuple[str, str]]) -> tuple[float, float, list[str]]:
    """Cohen's kappa atas daftar pasangan label. Mengembalikan kappa, kesepakatan, kelas."""
    kelas = sorted({a for a, _ in pasangan} | {b for _, b in pasangan})
    n = len(pasangan)
    if n == 0:
        return 0.0, 0.0, kelas
    setuju = sum(1 for a, b in pasangan if a == b)
    po = setuju / n
    ca = Counter(a for a, _ in pasangan)
    cb = Counter(b for _, b in pasangan)
    pe = sum((ca[k] / n) * (cb[k] / n) for k in kelas)
    # Bila seluruh label jatuh pada satu kelas, peluang kebetulan bernilai satu
    # sehingga pembaginya nol. Dalam keadaan itu kesepakatan sempurna dipandang
    # sepakat penuh, dan ketidaksepakatan mustahil terjadi.
    if pe >= 1.0:
        return (1.0 if po >= 1.0 else 0.0), po, kelas
    k = (po - pe) / (1 - pe)
    return k, po, kelas


def matriks(pasangan: list[tuple[str, str]], kelas: list[str]) -> list[list[int]]:
    idx = {k: i for i, k in enumerate(kelas)}
    m = [[0] * len(kelas) for _ in kelas]
    for a, b in pasangan:
        if a in idx and b in idx:
            m[idx[a]][idx[b]] += 1
    return m


def tafsir(k: float) -> str:
    if k < 0:
        return "lebih buruk daripada kebetulan"
    if k < 0.21:
        return "sedikit"
    if k < 0.41:
        return "cukup"
    if k < 0.61:
        return "sedang"
    if k < 0.81:
        return "kuat"
    return "hampir sempurna"


def ringkas_pasangan(pasangan: list[tuple[str, str]]) -> dict:
    """Menghitung ketiga sudut pandang kesepakatan untuk satu pasangan label."""
    hasil: dict = {}

    k, po, kelas = kappa(pasangan)
    hasil["semua_kelas"] = {
        "n": len(pasangan),
        "kesepakatan": round(po, 4),
        "kappa": round(k, 4),
        "tafsir": tafsir(k),
        "kelas": kelas,
        "matriks": matriks(pasangan, kelas),
        "sebaran_a": dict(Counter(a for a, _ in pasangan)),
        "sebaran_b": dict(Counter(b for _, b in pasangan)),
    }

    saring = [(x, y) for x, y in pasangan if x in SENTIMEN and y in SENTIMEN]
    if len(saring) >= 10:
        k2, po2, kelas2 = kappa(saring)
        hasil["sentimen"] = {
            "n": len(saring),
            "kesepakatan": round(po2, 4),
            "kappa": round(k2, 4),
            "tafsir": tafsir(k2),
            "kelas": kelas2,
            "matriks": matriks(saring, kelas2),
        }

    rel_a = [a != "tidak_relevan" for a, _ in pasangan]
    rel_b = [b != "tidak_relevan" for _, b in pasangan]
    k3, po3, _ = kappa([(str(x), str(y)) for x, y in zip(rel_a, rel_b)])
    tp = sum(1 for x, y in zip(rel_a, rel_b) if x and y)
    fp = sum(1 for x, y in zip(rel_a, rel_b) if not x and y)
    fn = sum(1 for x, y in zip(rel_a, rel_b) if x and not y)
    hasil["relevansi"] = {
        "n": len(pasangan),
        "kesepakatan": round(po3, 4),
        "kappa": round(k3, 4),
        "tafsir": tafsir(k3),
        "presisi": round(tp / (tp + fp), 4) if tp + fp else None,
        "recall": round(tp / (tp + fn), 4) if tp + fn else None,
    }

    beda = Counter((a, b) for a, b in pasangan if a != b)
    hasil["beda_terbanyak"] = [
        {"a": x, "b": y, "jumlah": n} for (x, y), n in beda.most_common(8)
    ]
    return hasil


def _selftest() -> int:
    assert abs(kappa([("a", "a"), ("b", "b")])[0] - 1.0) < 1e-9
    k, po, _ = kappa([("a", "b"), ("b", "a")])
    assert k < 0 and abs(po) < 1e-9
    k2, po2, _ = kappa([("a", "a"), ("a", "b"), ("b", "b"), ("b", "a")])
    assert abs(po2 - 0.5) < 1e-9
    assert abs(k2) < 1e-9
    assert kappa([])[0] == 0.0
    k3, _, _ = kappa([("x", "x")] * 5)
    assert abs(k3 - 1.0) < 1e-9
    assert tafsir(0.75) == "kuat"
    assert tafsir(0.1) == "sedikit"

    r = ringkas_pasangan(
        [("negatif", "negatif"), ("netral", "netral"), ("positif", "positif")]
        + [("positif", "netral")] * 7
        + [("tidak_relevan", "tidak_relevan")]
    )
    assert r["semua_kelas"]["n"] == 11
    assert r["sentimen"]["n"] == 10, "baris tidak relevan dikeluarkan dari blok sentimen"
    assert r["relevansi"]["kappa"] == 1.0, "tidak ada yang menolak, jadi sepakat penuh"
    assert r["relevansi"]["presisi"] == 1.0 and r["relevansi"]["recall"] == 1.0
    assert r["beda_terbanyak"][0] == {"a": "positif", "b": "netral", "jumlah": 7}
    assert all({"a", "b", "jumlah"} <= set(b) for b in r["beda_terbanyak"])
    assert len(PASANGAN_TETAP) >= 5
    assert len({p["id"] for p in PASANGAN_TETAP}) == len(PASANGAN_TETAP), "id harus unik"
    print("selftest kappa_gold ok")
    return 0


def perintah_semua(out: str) -> int:
    """Menghitung seluruh pasangan tetap lalu menuliskan hasilnya sebagai JSON."""
    keluaran = {
        "dihitung": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z"),
        "catatan": "Cohen's kappa tidak mengoreksi ketidakseimbangan kelas sepihak, "
                   "sehingga tafsirnya harus dibaca bersama sebaran labelnya.",
        "pasangan": [],
        "dilewati": [],
    }

    for p in PASANGAN_TETAP:
        a = muat(AKAR / p["a"], p["kolom_a"])
        b = muat(AKAR / p["b"], p["kolom_b"])
        sama = sorted(set(a) & set(b))
        if len(sama) < 10:
            keluaran["dilewati"].append({
                "id": p["id"],
                "alasan": f"hanya {len(sama)} baris beririsan, terlalu sedikit untuk dihitung",
                "a": p["a"], "b": p["b"],
            })
            print(f"  dilewati {p['id']:22s} irisan {len(sama)} baris")
            continue

        pasangan = [(a[u], b[u]) for u in sama]
        isi = ringkas_pasangan(pasangan)
        isi.update({
            "id": p["id"], "nama": p["nama"], "catatan": p.get("catatan", ""),
            "a": {"berkas": p["a"], "kolom": p["kolom_a"], "baris": len(a)},
            "b": {"berkas": p["b"], "kolom": p["kolom_b"], "baris": len(b)},
            "irisan": len(sama),
        })
        keluaran["pasangan"].append(isi)
        s = isi["semua_kelas"]
        print(f"  {p['id']:22s} n={len(sama):4d} kappa={s['kappa']:.4f} ({s['tafsir']})")

    tujuan = AKAR / out
    tujuan.parent.mkdir(parents=True, exist_ok=True)
    tujuan.write_text(json.dumps(keluaran, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{len(keluaran['pasangan'])} pasangan dihitung, "
          f"{len(keluaran['dilewati'])} dilewati")
    print(f"keluaran: {tujuan}")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if argv and argv[0] == "--selftest":
        return _selftest()

    p = argparse.ArgumentParser(description="Menghitung kesepakatan antar penilai gold")
    p.add_argument("--a", default="data/processed/gold_asisten_100.csv", help="penilai pertama")
    p.add_argument("--kolom-a", default="label_asisten")
    p.add_argument("--b", default="final/gold_manusia_ronde3.csv", help="penilai kedua")
    p.add_argument("--kolom-b", default="label")
    p.add_argument("--semua", action="store_true",
                   help="menghitung seluruh pasangan tetap lalu menulis JSON")
    p.add_argument("--out", default="final/kappa_gold.json",
                   help="berkas keluaran JSON, atau kosongkan untuk tidak menulis")
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args(argv)

    if args.selftest:
        return _selftest()
    if args.semua:
        return perintah_semua(args.out)

    a = muat(AKAR / args.a, args.kolom_a)
    b = muat(AKAR / args.b, args.kolom_b)
    print(f"penilai A {args.a}: {len(a)} baris")
    print(f"penilai B {args.b}: {len(b)} baris")
    if not a or not b:
        print("\nsalah satu berkas belum ada atau kosong; belum ada yang dapat dihitung.")
        return 0

    sama = sorted(set(a) & set(b))
    print(f"baris yang dinilai keduanya: {len(sama)}")
    if len(sama) < 10:
        print("terlalu sedikit untuk dihitung.")
        return 0

    pasangan = [(a[u], b[u]) for u in sama]
    isi = ringkas_pasangan(pasangan)

    for nama, kunci in (("seluruh kelas apa adanya", "semua_kelas"),
                        ("hanya sentimen, baris tidak relevan dikeluarkan", "sentimen")):
        blok = isi.get(kunci)
        if not blok:
            continue
        print(f"\n=== {nama} (n={blok['n']}) ===")
        print(f"kesepakatan {blok['kesepakatan']:.4f} | kappa {blok['kappa']:.4f} ({blok['tafsir']})")
        for baris, kelas in zip(blok["matriks"], blok["kelas"]):
            print(f"   {kelas[:14]:>14s} " + " ".join(f"{v:5d}" for v in baris))

    rel = isi["relevansi"]
    print(f"\n=== hanya putusan relevan atau tidak (n={rel['n']}) ===")
    print(f"kesepakatan {rel['kesepakatan']:.4f} | kappa {rel['kappa']:.4f} ({rel['tafsir']})")
    print(f"presisi {rel['presisi']:.3f} | recall {rel['recall']:.3f}")

    print("\n--- baris yang paling sering berbeda ---")
    if not isi["beda_terbanyak"]:
        print("   tidak ada")
    for d in isi["beda_terbanyak"]:
        print(f"   A={d['a']:14s} B={d['b']:14s} : {d['jumlah']}")

    if args.out:
        tujuan = AKAR / args.out
        tujuan.parent.mkdir(parents=True, exist_ok=True)
        tujuan.write_text(json.dumps({
            "dihitung": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z"),
            "pasangan": [dict(isi, id="manual", nama="pasangan manual",
                              a={"berkas": args.a, "kolom": args.kolom_a, "baris": len(a)},
                              b={"berkas": args.b, "kolom": args.kolom_b, "baris": len(b)},
                              irisan=len(sama), catatan="")],
            "dilewati": [],
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nkeluaran: {tujuan}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
