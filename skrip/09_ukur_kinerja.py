# Analisis Sentimen Sensus Ekonomi 2026 dan Aplikasi Fasih BPS
# 09 Pengukuran Kinerja
#
# Kegunaan : Mengukur satu atau beberapa sistem terhadap data uji manusia, lengkap dengan
#            selang kepercayaan Wilson, selang bootstrap untuk F1 macro, dan uji McNemar eksak.
#            Perintah sample, eval, dan mine memakai data uji yang sama.
# Masukan  : final/gold_uji.csv dan berkas prediksi tiap sistem
# Keluaran : final/evaluasi_uji.json dan reports/gold_eval_*.json
# Rujukan  : Bab III, sub-bab Metode Analisis Data, serta Bab IV bagian kinerja lima sistem
#
# Menjalankan dari akar repositori:  py -3.13 analisis/09_ukur_kinerja.py
"""Perangkat evaluasi gold set kecil dan pertambahan label secara aktif.

Modul ini menjawab satu masalah praktis: gold set hanya berisi 100 baris,
sehingga perlu cara mengukur yang jujur dan cara menumbuhkan gold set tanpa
biaya anotasi besar.

Tiga perintah tersedia:

    sample  Menarik kandidat berlapis dari korpus untuk diverifikasi manusia.
    eval    Mengukur satu atau beberapa sistem terhadap gold set, lengkap dengan
            selang kepercayaan Wilson, selang bootstrap untuk F1 macro, dan uji
            McNemar eksak untuk perbandingan berpasangan.
    mine    Memeringkat baris yang paling layak diverifikasi pada ronde
            berikutnya berdasarkan keraguan model.

Prinsip yang dipegang:
    - Gold set hanya dipakai untuk mengukur dan tidak boleh masuk ke data latih.
    - Evaluasi tidak pernah dilakukan terhadap pseudo-label, karena itu melingkar.
    - Perbandingan antar sistem selalu berpasangan pada baris yang sama, sebab
      dengan seratus baris hanya uji berpasangan yang cukup peka.

Rujukan metodologis: ensembling dan pemilihan model berbasis validasi
(arXiv:2410.19889) serta kalibrasi label lemah hasil LLM (arXiv:2505.19675).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraper.dataset import read_rows  # noqa: E402

LABEL_ORDER = ["negatif", "netral", "positif"]


# ---------------------------------------------------------------------------
# Statistik dasar, ditulis sendiri agar tidak menambah ketergantungan
# ---------------------------------------------------------------------------

def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Menghitung selang kepercayaan Wilson untuk sebuah proporsi.

    Selang Wilson dipilih karena tetap masuk akal pada proporsi ekstrem dan
    pada jumlah contoh kecil, keadaan yang biasa ditemui pada gold set seratus
    baris.
    """
    if n <= 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def macro_f1(
    y_true: list[str],
    y_pred: list[str],
    labels: list[str] | None = None,
) -> float:
    """Menghitung F1 macro tanpa bantuan pustaka luar.

    Daftar kelas wajib diberikan pada pemakaian yang sesungguhnya. Bila kelas
    disimpulkan dari gabungan label kebenaran dan label prediksi, kelas yang
    diprediksi tetapi tidak pernah muncul pada acuan akan ikut terhitung
    sebagai kelas bernilai nol dan menekan rata-ratanya. Hal itu benar-benar
    terjadi pada pengukuran 16 September 2026: delapan baris diprediksi
    `tidak_relevan`, padahal kelas itu sudah dikeluarkan dari acuan, sehingga
    F1 macro terbagi empat dan nilainya terdeflasi sekitar seperempat.
    """
    daftar = labels if labels is not None else sorted(set(y_true) | set(y_pred))
    daftar = [lab for lab in daftar if lab]
    nilai: list[float] = []
    for lab in daftar:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == lab and p == lab)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != lab and p == lab)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == lab and p != lab)
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        nilai.append(2 * prec * rec / (prec + rec) if (prec + rec) else 0.0)
    return sum(nilai) / len(nilai) if nilai else 0.0


def bootstrap_macro_f1(
    y_true: list[str],
    y_pred: list[str],
    iters: int = 2000,
    seed: int = 42,
    labels: list[str] | None = None,
) -> tuple[float, float, float]:
    """Mengukur sebaran F1 macro melalui penyampelan ulang berpasangan."""
    rng = random.Random(seed)
    n = len(y_true)
    if n == 0:
        return (0.0, 0.0, 0.0)
    nilai: list[float] = []
    for _ in range(iters):
        idx = [rng.randrange(n) for _ in range(n)]
        nilai.append(
            macro_f1([y_true[i] for i in idx], [y_pred[i] for i in idx], labels=labels)
        )
    nilai.sort()
    return (nilai[len(nilai) // 2], nilai[int(0.025 * iters)], nilai[int(0.975 * iters)])


def mcnemar_exact(b: int, c: int) -> float:
    """Uji McNemar eksak dua sisi untuk perbandingan dua sistem berpasangan.

    Hanya pasangan yang berbeda pendapat yang dihitung, yaitu b dan c. Nilai
    peluang dihitung langsung dari sebaran binomial sehingga tetap sahih pada
    jumlah contoh kecil.
    """
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    ekor = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return min(1.0, 2 * ekor)


def kebutuhan_contoh(p: float, margin: float, z: float = 1.96) -> int:
    """Menghitung jumlah contoh yang dibutuhkan untuk mencapai galat baku tertentu."""
    if margin <= 0:
        return 0
    return math.ceil(z * z * p * (1 - p) / (margin * margin))


# ---------------------------------------------------------------------------
# Pembacaan berkas
# ---------------------------------------------------------------------------

def baca_pasangan(path: Path, uid_col: str, label_col: str) -> dict[str, str]:
    """Membaca berkas CSV menjadi peta uid menuju label."""
    hasil: dict[str, str] = {}
    for r in read_rows(path):
        uid = (r.get(uid_col) or "").strip()
        lab = (r.get(label_col) or "").strip().lower()
        if uid and lab:
            hasil[uid] = lab
    return hasil


def baca_meta(path: Path) -> dict[str, dict[str, Any]]:
    """Membaca berkas CSV menjadi peta uid menuju seluruh kolomnya."""
    return {(r.get("uid") or "").strip(): r for r in read_rows(path) if (r.get("uid") or "").strip()}


def _konteks(row: dict[str, Any]) -> str:
    """Merangkum keterangan asal teks agar anotator manusia menilai dengan konteks.

    Tanpa rangkuman ini, anotator hanya melihat potongan teks tanpa tahu ia
    berasal dari video apa dan apakah ia sebuah balasan.
    """
    extra = row.get("extra")
    if isinstance(extra, str):
        try:
            extra = json.loads(extra)
        except json.JSONDecodeError:
            extra = {}
    extra = extra if isinstance(extra, dict) else {}
    bagian: list[str] = []
    if extra.get("video_title"):
        bagian.append(f"video: {extra['video_title']}")
    if extra.get("channel"):
        bagian.append(f"kanal: {extra['channel']}")
    if extra.get("app_version"):
        bagian.append(f"versi aplikasi: {extra['app_version']}")
    induk = extra.get("parent")
    if induk not in (None, "", "root"):
        teks_induk = " ".join(str(extra.get("parent_text") or "").split())[:160]
        if teks_induk:
            bagian.append(f'balasan atas: "{teks_induk}"')
        else:
            bagian.append("balasan, teks induk tidak tersedia")
    elif (row.get("source") or "") == "youtube":
        bagian.append("komentar utama")
    return " \u00b7 ".join(bagian)


# ---------------------------------------------------------------------------
# Perintah sample: menarik kandidat berlapis
# ---------------------------------------------------------------------------

def perintah_sample(args: argparse.Namespace) -> int:
    """Menarik kandidat verifikasi manusia secara berlapis.

    Lapisan dibentuk dari gabungan sumber, label sementara, dan sel panjang
    teks, sehingga seratus baris yang terpilih mewakili wilayah keputusan yang
    berbeda alih-alih didominasi kelas terbesar.
    """
    rows = read_rows(args.csv)
    if not rows:
        print("berkas kosong", file=sys.stderr)
        return 1

    # Dua cara pelapisan tersedia.
    #
    # "kelas" menuntut korpus sudah berlabel dan menyeimbangkan kelas sentimen.
    # "konteks" tidak menuntut label sama sekali; yang diseimbangkan adalah
    # sumber, status balasan, dan panjang teks. Cara kedua inilah yang dipakai
    # pada korpus hasil pengambilan ulang, supaya penarikan kandidat tidak
    # bergantung pada korpus lain yang memakai pembersihan teks berbeda.
    ember_rinci: dict[tuple, list[dict]] = defaultdict(list)
    ember_kasar: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        sumber = r.get("source") or "?"
        panjang = len((r.get("text_clean") or r.get("text") or "").strip())
        sel = "pendek" if panjang < 25 else ("sedang" if panjang < 100 else "panjang")
        if args.lapis == "kelas":
            kunci = (sumber, (r.get(args.label_col) or "?").strip().lower())
        else:
            extra = r.get("extra")
            if isinstance(extra, str):
                try:
                    extra = json.loads(extra)
                except json.JSONDecodeError:
                    extra = {}
            extra = extra if isinstance(extra, dict) else {}
            # YouTube menandai balasan melalui kolom parent, sedangkan Threads
            # melalui kolom type. Keduanya diperiksa agar pelapisan tetap sahih.
            jenis = str(extra.get("type") or "").strip().lower()
            balasan = "balasan" if (
                extra.get("parent") not in (None, "", "root") or jenis == "reply"
            ) else "utama"
            kunci = (sumber, balasan)
        r["_sel"] = kunci
        ember_kasar[kunci].append(r)
        ember_rinci[(kunci[0], kunci[1], sel)].append(r)

    rng = random.Random(args.seed)
    pilih: list[dict] = []

    if args.skema == "seimbang":
        # Bagi rata setiap sel sumber kali label, lalu acak di dalam sel.
        # Cara ini menjaga setiap kelas dan setiap sumber tetap terwakili,
        # sehingga kekeliruan per kelompok dapat terlihat.
        kunci = sorted(k for k, v in ember_kasar.items() if v)
        per_sel = max(1, args.n // max(1, len(kunci)))
        for k in kunci:
            isi = list(ember_kasar[k])
            rng.shuffle(isi)
            pilih.extend(isi[:per_sel])
        sisa = args.n - len(pilih)
        if sisa > 0:
            terpakai = {r.get("uid") for r in pilih}
            cadangan = [r for r in rows if r.get("uid") not in terpakai]
            rng.shuffle(cadangan)
            pilih.extend(cadangan[:sisa])
    else:
        # Bagi proporsional terhadap ukuran setiap sel rinci.
        total = sum(len(v) for v in ember_rinci.values())
        for kunci, isi in ember_rinci.items():
            kuota = max(1, round(args.n * len(isi) / total))
            isi = list(isi)
            rng.shuffle(isi)
            pilih.extend(isi[:kuota])

    rng.shuffle(pilih)
    pilih = pilih[: args.n]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    kolom = ["uid", "source", "text", "text_clean", "created_at", "url", "konteks"]
    if not args.blind:
        kolom.append("label_usulan")
    kolom += ["label_manusia", "catatan"]

    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=kolom, extrasaction="ignore")
        w.writeheader()
        for r in pilih:
            baris = {
                "uid": r.get("uid"),
                "source": r.get("source"),
                "text": r.get("text"),
                "text_clean": r.get("text_clean"),
                "created_at": r.get("created_at"),
                "url": r.get("url"),
                "konteks": _konteks(r),
                "label_usulan": r.get(args.label_col) if args.lapis == "kelas" else "",
                "label_manusia": "",
                "catatan": "",
            }
            if args.blind:
                baris.pop("label_usulan")
            w.writerow(baris)

    print(f"skema             : {args.skema}{' dan tersamar' if args.blind else ''}")
    print(f"sel rinci         : {len(ember_rinci)}")
    print(f"sel sumber x kunci: {len(ember_kasar)}")
    print(f"kandidat terpilih : {len(pilih)} dari {len(rows)}")
    sebaran = Counter(p.get("_sel") or ("?", "?") for p in pilih)
    for k, v in sorted(sebaran.items(), key=lambda x: -x[1]):
        print(f"   {k[0]:10s} {k[1]:8s} {v}")
    if args.blind:
        print("Usulan model disembunyikan sehingga anotator menilai tanpa terpengaruh.")
    else:
        print("Perhatian: kolom label_usulan ikut tertulis sehingga anotator dapat terpengaruh.")
        print("Tambahkan --blind untuk menyembunyikannya.")
    print(f"keluaran          : {out.resolve()}")
    print("Isi kolom label_manusia secara manual, lalu jalankan perintah eval.")
    return 0


# ---------------------------------------------------------------------------
# Perintah eval: mengukur sistem terhadap gold set
# ---------------------------------------------------------------------------

def perintah_eval(args: argparse.Namespace) -> int:
    """Mengukur satu atau beberapa sistem terhadap gold set berukuran kecil.

    Setiap sistem diukur pada himpunan baris yang sama, lalu dibandingkan
    secara berpasangan memakai uji McNemar. Cara ini jauh lebih peka daripada
    membandingkan dua nilai akurasi secara langsung.
    """
    gold_semua = baca_pasangan(Path(args.gold), args.uid_col, args.label_human_col)
    if not gold_semua:
        print("gold set kosong atau kolom label manusia belum diisi", file=sys.stderr)
        return 1

    kelas = {k.strip().lower() for k in args.kelas_sentimen.split(",") if k.strip()}
    kelas_urut = sorted(kelas)
    di_luar = Counter(l for l in gold_semua.values() if l not in kelas)
    gold = {u: l for u, l in gold_semua.items() if l in kelas}
    if not gold:
        print("tidak ada baris gold yang tergolong kelas sentimen", file=sys.stderr)
        return 1

    sistem: dict[str, dict[str, str]] = {}
    for path in args.pred:
        p = Path(path)
        sistem[p.stem] = baca_pasangan(p, args.uid_col, args.label_col)

    sebaran = Counter(gold.values())
    print(f"gold set         : {len(gold_semua)} baris")
    if di_luar:
        print(f"di luar sentimen : {sum(di_luar.values())} baris {dict(di_luar)} "
              "(dikeluarkan dari metrik, dilaporkan terpisah)")
    print(f"dinilai sentimen : {len(gold)} baris")
    print("sebaran kelas gold:", dict(sebaran))
    ambang = min(sebaran.values())
    if ambang < 15:
        print(f"peringatan: kelas terkecil hanya {ambang} baris, "
              "sehingga F1 kelas tersebut sangat bising.")

    ringkasan: dict[str, Any] = {
        "gold_n": len(gold),
        "gold_dist": dict(sebaran),
        "di_luar_kelas_sentimen": dict(di_luar),
        "sistem": {},
    }
    benar_urut: dict[str, list[bool]] = {}
    uids = [u for u in gold if all(u in sistem[s] for s in sistem)]

    for nama, prediksi in sistem.items():
        pasangan = [(u, gold[u], prediksi[u]) for u in uids]
        y_true = [t for _, t, _ in pasangan]
        y_pred = [p for _, _, p in pasangan]
        k = sum(1 for t, p in zip(y_true, y_pred) if t == p)
        n = len(pasangan)
        lo, hi = wilson_ci(k, n)
        med, blo, bhi = bootstrap_macro_f1(y_true, y_pred, labels=kelas_urut)
        benar_urut[nama] = [t == p for t, p in zip(y_true, y_pred)]

        per_kelas: dict[str, Any] = {}
        for lab in kelas_urut:
            idx = [i for i, t in enumerate(y_true) if t == lab]
            if idx:
                kk = sum(1 for i in idx if y_pred[i] == lab)
                clo, chi = wilson_ci(kk, len(idx))
                per_kelas[lab] = {
                    "n": len(idx),
                    "recall": round(kk / len(idx), 4),
                    "recall_ci": [round(clo, 4), round(chi, 4)],
                }

        ringkasan["sistem"][nama] = {
            "n": n,
            "accuracy": round(k / n, 4),
            "accuracy_ci95": [round(lo, 4), round(hi, 4)],
            "f1_macro": round(macro_f1(y_true, y_pred, labels=kelas_urut), 4),
            "f1_macro_bootstrap": [round(blo, 4), round(med, 4), round(bhi, 4)],
            "per_kelas": per_kelas,
        }
        print(f"\n[{nama}] n={n}")
        print(f"   akurasi   : {k / n:.4f}  (selang 95%: {lo:.4f} - {hi:.4f}, "
              f"lebar {100 * (hi - lo):.1f} poin)")
        print(f"   F1 macro  : {macro_f1(y_true, y_pred, labels=kelas_urut):.4f}  "
              f"(bootstrap 95%: {blo:.4f} - {bhi:.4f})")
        for lab, info in sorted(per_kelas.items()):
            print(f"   {lab:9s} : recall {info['recall']:.3f} pada {info['n']} baris")

    nama_sistem = list(benar_urut)
    if len(nama_sistem) >= 2:
        print("\n=== perbandingan berpasangan (McNemar eksak) ===")
        for i in range(len(nama_sistem)):
            for j in range(i + 1, len(nama_sistem)):
                a, b = nama_sistem[i], nama_sistem[j]
                salah_a = sum(1 for x, y in zip(benar_urut[a], benar_urut[b]) if not x and y)
                salah_b = sum(1 for x, y in zip(benar_urut[a], benar_urut[b]) if x and not y)
                p = mcnemar_exact(salah_a, salah_b)
                ringkasan.setdefault("mcnemar", []).append(
                    {"a": a, "b": b, "a_salah_b_benar": salah_a,
                     "b_salah_a_benar": salah_b, "p_value": round(p, 4)}
                )
                tanda = "berbeda nyata" if p < 0.05 else "belum berbeda nyata"
                print(f"   {a} vs {b}: pasangan berbeda {salah_a} vs {salah_b}, "
                      f"p = {p:.4f} -> {tanda}")

    print("\n=== berapa contoh yang dibutuhkan ===")
    for margin in (0.10, 0.05, 0.03, 0.02):
        n_butuh = kebutuhan_contoh(0.5, margin)
        print(f"   galat {margin * 100:.0f} poin pada kasus terburuk: {n_butuh} baris")
    print("   Catatan: uji berpasangan McNemar jauh lebih peka daripada angka di atas, "
          "sehingga seratus baris tetap dapat mendeteksi selisih besar.")

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(
            json.dumps(ringkasan, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\nringkasan -> {Path(args.out).resolve()}")
    return 0


# ---------------------------------------------------------------------------
# Perintah mine: memilih kandidat ronde berikutnya
# ---------------------------------------------------------------------------

def perintah_mine(args: argparse.Namespace) -> int:
    """Memeringkat baris yang paling layak diverifikasi pada ronde berikutnya.

    Baris dengan keyakinan rendah, teks sangat pendek, atau prediksi yang
    bertentangan dengan label sementara diberi nilai keraguan tertinggi. Dengan
    begitu, penambahan gold set mengarah ke wilayah yang benar-benar sulit.
    """
    rows = read_rows(args.csv)
    gold = baca_pasangan(Path(args.gold), args.uid_col, args.label_human_col) if args.gold else {}
    if gold:
        rows = [r for r in rows if (r.get("uid") or "") not in gold]

    def keraguan(r: dict) -> float:
        try:
            keyakinan = float(r.get(args.confidence_col) or 0.0)
        except ValueError:
            keyakinan = 0.0
        panjang = len((r.get("text_clean") or r.get("text") or "").strip())
        nilai = 1.0 - keyakinan
        if panjang < 25:
            nilai += 0.35
        if panjang > 200:
            nilai += 0.10
        if (r.get("source") or "") == "threads":
            nilai += 0.05
        return nilai

    rows.sort(key=keraguan, reverse=True)

    # Jaga keragaman: batasi jumlah per kombinasi sumber dan label.
    kuota: Counter = Counter()
    batas = max(1, args.n // 6)
    pilih: list[dict] = []
    for r in rows:
        kunci = (r.get("source") or "?", (r.get(args.label_col) or "?").strip().lower())
        if kuota[kunci] >= batas:
            continue
        kuota[kunci] += 1
        pilih.append(r)
        if len(pilih) >= args.n:
            break

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    # Kolom konteks disertakan karena tanpa keterangan asal teks, anotator
    # menilai balasan singkat tanpa teks induknya. Kelalaian itu terbukti
    # menjadi cacat terbesar pada audit ronde pertama, sehingga kandidat ronde
    # berikutnya wajib membawa konteks yang sama seperti perintah sample.
    kolom = ["uid", "source", "text", "created_at", "url", "konteks",
             "label_sementara", "keyakinan", "label_manusia", "catatan"]
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=kolom, extrasaction="ignore")
        w.writeheader()
        for r in pilih:
            w.writerow({
                "uid": r.get("uid"),
                "source": r.get("source"),
                "text": r.get("text"),
                "created_at": r.get("created_at"),
                "url": r.get("url"),
                "konteks": r.get("konteks") or _konteks(r),
                "label_sementara": r.get(args.label_col),
                "keyakinan": r.get(args.confidence_col),
                "label_manusia": "",
                "catatan": "",
            })

    print(f"kandidat tanpa gold : {len(rows)}")
    print(f"terpilih untuk ronde berikutnya: {len(pilih)}")
    for k, v in sorted(kuota.items(), key=lambda x: -x[1]):
        print(f"   {k[0]:10s} {k[1]:8s} {v}")
    print(f"keluaran            : {out.resolve()}")
    return 0


# ---------------------------------------------------------------------------
# Perintah sheet: lembar anotasi manusia
# ---------------------------------------------------------------------------

LEMBAR_HTML = """<!doctype html>
<html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Lembar Anotasi Gold Set - Sensus Ekonomi 2026</title>
<style>
:root{--bg:#f7fafc;--card:#fff;--line:#e2e8f0;--fg:#1a202c;--dim:#718096;--acc:#2b6cb0;
--neg:#c53030;--neu:#b7791f;--pos:#2f855a;--irr:#4a5568;--non:#553c9a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 system-ui,Segoe UI,sans-serif}
header{position:sticky;top:0;z-index:5;background:#1a365d;color:#fff;padding:13px 20px;
box-shadow:0 2px 8px rgba(0,0,0,.15)}
h1{margin:0 0 5px;font-size:16px}
.hint{font-size:12px;opacity:.88;max-width:900px}
.bar{height:7px;background:#2c5282;border-radius:4px;overflow:hidden;margin-top:8px;max-width:900px}
.bar i{display:block;height:100%;background:#48bb78;width:0;transition:width .15s}
main{max-width:900px;margin:0 auto;padding:16px 20px 100px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:13px 16px;margin:13px 0}
.card.done{opacity:.62}
.meta{color:var(--dim);font-size:12px;margin-bottom:5px}
.meta a{color:var(--acc)}
.txt{font-size:15px;background:#f7fafc;border-left:3px solid var(--acc);padding:9px 12px;
border-radius:4px;white-space:pre-wrap;word-break:break-word}
.opsi{display:flex;flex-wrap:wrap;gap:7px;margin-top:10px}
button{border:1px solid var(--line);background:#fff;color:var(--fg);border-radius:7px;
padding:7px 13px;font-size:13px;cursor:pointer;font-family:inherit}
button:hover{border-color:var(--acc)}
button.on{color:#fff;border-color:transparent}
button.on[data-v="negatif"]{background:var(--neg)}
button.on[data-v="netral"]{background:var(--neu)}
button.on[data-v="positif"]{background:var(--pos)}
button.on[data-v="tidak_relevan"]{background:var(--irr)}
button.on[data-v="bukan_opini"]{background:var(--non)}
textarea{width:100%;margin-top:9px;border:1px solid var(--line);border-radius:7px;
padding:7px;font:inherit;font-size:13px;resize:vertical}
footer{position:fixed;bottom:0;left:0;right:0;background:#fff;border-top:1px solid var(--line);
padding:11px 20px;display:flex;gap:14px;align-items:center;justify-content:center;flex-wrap:wrap}
footer .hint{color:var(--dim)}
#ekspor{background:var(--acc);color:#fff;border-color:transparent;font-weight:600}
</style></head><body>
<header>
<h1>Lembar Anotasi Gold Set &mdash; Sentimen Sensus Ekonomi 2026</h1>
<div class="hint">Pilih <b>Negatif, Netral,</b> atau <b>Positif</b> bila teks memuat penilaian.
Pilih <b>Tidak relevan</b> bila teks di luar topik sensus ekonomi atau Fasih BPS.
Pilih <b>Bukan opini</b> bila teks relevan tetapi hanya sapaan, pertanyaan, atau keterangan.
Usulan model sengaja tidak ditampilkan agar penilaian tidak terpengaruh.
Jawaban tersimpan otomatis di peramban ini.</div>
<div class="bar"><i id="bar"></i></div>
<div class="hint" id="prog">0 dari 0</div>
</header>
<main id="list"></main>
<footer>
<label class="hint"><input type="checkbox" id="sembunyi"> sembunyikan yang sudah dinilai</label>
<button id="ekspor">Ekspor CSV</button>
<button id="reset">Hapus semua jawaban</button>
</footer>
<script>
const ITEMS = __ITEMS__;
const KEY = "se2026_gold_v1";
const PILIHAN = [["negatif","Negatif"],["netral","Netral"],["positif","Positif"],
                 ["tidak_relevan","Tidak relevan"],["bukan_opini","Bukan opini"]];
let simpan = {};
try { simpan = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { simpan = {}; }

function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
    return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];
  });
}
function simpanKe() { localStorage.setItem(KEY, JSON.stringify(simpan)); }

function render() {
  const list = document.getElementById("list");
  const sembunyi = document.getElementById("sembunyi").checked;
  list.innerHTML = "";
  let dinilai = 0;

  ITEMS.forEach(function (it, i) {
    const v = simpan[it.uid] || {};
    if (v.label) dinilai++;
    if (sembunyi && v.label) return;

    const card = document.createElement("div");
    card.className = "card" + (v.label ? " done" : "");
    const tautan = it.url ? ' &middot; <a href="' + esc(it.url) + '" target="_blank" rel="noopener">buka sumber</a>' : "";
    card.innerHTML =
      '<div class="meta">#' + (i + 1) + " &middot; " + esc(it.source) +
      " &middot; " + esc(it.created_at || "") + tautan + "</div>" +
      (it.konteks ? '<div class="meta">' + esc(it.konteks) + "</div>" : "") +
      '<div class="txt"></div><div class="opsi"></div>' +
      '<textarea rows="1" placeholder="catatan (opsional)"></textarea>';
    card.querySelector(".txt").textContent = it.text || "";

    const opsi = card.querySelector(".opsi");
    PILIHAN.forEach(function (pasangan) {
      const b = document.createElement("button");
      b.textContent = pasangan[1];
      b.dataset.v = pasangan[0];
      if (v.label === pasangan[0]) b.className = "on";
      b.onclick = function () {
        const kini = simpan[it.uid] || {};
        if (kini.label === pasangan[0]) { delete kini.label; }
        else { kini.label = pasangan[0]; }
        simpan[it.uid] = kini;
        simpanKe();
        render();
      };
      opsi.appendChild(b);
    });

    const ta = card.querySelector("textarea");
    ta.value = v.catatan || "";
    ta.oninput = function () {
      const kini = simpan[it.uid] || {};
      kini.catatan = ta.value;
      simpan[it.uid] = kini;
      simpanKe();
    };
    list.appendChild(card);
  });

  document.getElementById("prog").textContent = dinilai + " dari " + ITEMS.length + " dinilai";
  document.getElementById("bar").style.width = (ITEMS.length ? 100 * dinilai / ITEMS.length : 0) + "%";
}

document.getElementById("ekspor").onclick = function () {
  const baris = [["uid", "label_manusia", "catatan"]];
  ITEMS.forEach(function (it) {
    const v = simpan[it.uid] || {};
    baris.push([it.uid, v.label || "", String(v.catatan || "").replace(/[\\r\\n]+/g, " ")]);
  });
  const isi = baris.map(function (r) {
    return r.map(function (x) { return '"' + String(x).replace(/"/g, '""') + '"'; }).join(",");
  }).join("\\r\\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob(["\\ufeff" + isi], { type: "text/csv;charset=utf-8" }));
  a.download = "gold_manusia.csv";
  a.click();
};

document.getElementById("reset").onclick = function () {
  if (confirm("Hapus seluruh jawaban pada peramban ini?")) {
    simpan = {};
    simpanKe();
    render();
  }
};
document.getElementById("sembunyi").onchange = render;
render();
</script></body></html>
"""


def perintah_sheet(args: argparse.Namespace) -> int:
    """Menghasilkan lembar anotasi HTML mandiri dari berkas kandidat gold.

    Lembar ini dibuat agar penilaian seratus baris tidak perlu dilakukan dengan
    menyunting CSV. Jawaban tersimpan pada penyimpanan lokal peramban, sehingga
    pekerjaan tidak hilang saat halaman ditutup, dan dapat diekspor menjadi CSV
    yang langsung dapat dibaca perintah eval.
    """
    rows = read_rows(Path(args.gold))
    if not rows:
        print("berkas kandidat kosong", file=sys.stderr)
        return 1

    items = []
    for r in rows:
        items.append({
            "uid": (r.get("uid") or "").strip(),
            "source": r.get("source") or "",
            "text": r.get("text") or r.get("text_clean") or "",
            "created_at": (r.get("created_at") or "")[:16].replace("T", " "),
            "url": r.get("url") or "",
            "konteks": r.get("konteks") or _konteks(r),
        })

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(LEMBAR_HTML.replace("__ITEMS__", json.dumps(items, ensure_ascii=False)),
                   encoding="utf-8")

    print(f"baris pada lembar : {len(items)}")
    print(f"berkas            : {out.resolve()}")
    print("Buka di peramban, nilai setiap baris, lalu tekan Ekspor CSV.")
    print("Berkas hasil ekspor langsung dapat dipakai perintah eval sebagai --gold.")
    return 0


# ---------------------------------------------------------------------------
# Antarmuka baris perintah
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Evaluasi gold set kecil dan pertambahan label secara aktif"
    )
    sub = p.add_subparsers(dest="perintah", required=True)

    s = sub.add_parser("sample", help="menarik kandidat berlapis untuk diverifikasi manusia")
    s.add_argument("--csv", required=True)
    s.add_argument("--label-col", default="label")
    s.add_argument("--n", type=int, default=100)
    s.add_argument(
        "--skema",
        default="proporsional",
        choices=["proporsional", "seimbang"],
        help="proporsional mengikuti ukuran korpus; seimbang membagi rata setiap sel sumber kali label",
    )
    s.add_argument(
        "--blind",
        action="store_true",
        help="menyembunyikan usulan model agar anotator manusia tidak terpengaruh",
    )
    s.add_argument("--seed", type=int, default=42)
    s.add_argument("--uid-col", default="uid")
    s.add_argument(
        "--lapis",
        default="kelas",
        choices=["kelas", "konteks"],
        help="kelas menuntut korpus berlabel; konteks melapis menurut sumber, "
             "status balasan, dan panjang teks tanpa memerlukan label",
    )
    s.add_argument("--out", default="data/processed/gold_kandidat.csv")
    s.set_defaults(func=perintah_sample)

    e = sub.add_parser("eval", help="mengukur sistem terhadap gold set")
    e.add_argument("--gold", required=True)
    e.add_argument("--pred", nargs="+", required=True, help="satu atau beberapa berkas prediksi")
    e.add_argument("--label-col", default="label", help="nama kolom prediksi pada berkas prediksi")
    e.add_argument("--label-human-col", default="label_manusia")
    e.add_argument("--uid-col", default="uid")
    e.add_argument(
        "--kelas-sentimen",
        default="negatif,netral,positif",
        help="kelas gold yang dinilai sebagai sentimen; sisanya dilaporkan terpisah",
    )
    e.add_argument("--out", default="reports/gold_eval.json")
    e.set_defaults(func=perintah_eval)

    m = sub.add_parser("mine", help="memeringkat kandidat ronde verifikasi berikutnya")
    m.add_argument("--csv", required=True)
    m.add_argument("--gold", default=None)
    m.add_argument("--label-col", default="label")
    m.add_argument("--confidence-col", default="label_confidence")
    m.add_argument("--label-human-col", default="label_manusia")
    m.add_argument("--uid-col", default="uid")
    m.add_argument("--n", type=int, default=100)
    m.add_argument("--out", default="data/processed/gold_kandidat_ronde2.csv")
    m.set_defaults(func=perintah_mine)

    h = sub.add_parser("sheet", help="menghasilkan lembar anotasi HTML untuk penilaian manusia")
    h.add_argument("--gold", required=True, help="berkas kandidat hasil perintah sample atau mine")
    h.add_argument("--out", default="reports/lembar_anotasi.html")
    h.set_defaults(func=perintah_sheet)
    return p


def selftest() -> int:
    lo, hi = wilson_ci(87, 100)
    assert 0.78 < lo < 0.80 and 0.92 < hi < 0.94, (lo, hi)

    yt = ["a", "a", "b", "b"]
    yp = ["a", "b", "b", "b"]
    assert abs(macro_f1(yt, yp) - 0.7333333333) < 1e-6, macro_f1(yt, yp)

    # Kelas yang diprediksi tetapi tidak termasuk daftar penilaian tidak boleh
    # ikut menekan rata-rata. Inilah cacat yang membuat F1 macro terbagi empat
    # pada pengukuran 16 September 2026.
    yt2 = ["negatif", "netral", "positif", "negatif"]
    yp2 = ["negatif", "netral", "positif", "tidak_relevan"]
    tiga = macro_f1(yt2, yp2, labels=["negatif", "netral", "positif"])
    empat = macro_f1(yt2, yp2)
    assert abs(tiga - 0.8888888888) < 1e-6, tiga
    assert abs(empat - 0.6666666666) < 1e-6, empat
    assert tiga > empat, (tiga, empat)

    assert mcnemar_exact(0, 0) == 1.0
    assert mcnemar_exact(10, 0) < 0.01, mcnemar_exact(10, 0)
    assert mcnemar_exact(3, 2) > 0.5

    med, blo, bhi = bootstrap_macro_f1(yt * 10, yp * 10, iters=200)
    assert blo <= med <= bhi

    assert kebutuhan_contoh(0.5, 0.10) == 97
    print("selftest gold_eval ok")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if argv and argv[0] == "--selftest":
        return selftest()
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
