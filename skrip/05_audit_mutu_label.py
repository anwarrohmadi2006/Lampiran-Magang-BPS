# Analisis Sentimen Sensus Ekonomi 2026 dan Aplikasi Fasih BPS
# 05 Audit Mutu Label
#
# Kegunaan : Memindai seluruh baris korpus untuk menguji apakah label otomatis bertentangan
#            dengan aturan promptnya sendiri dan apakah bukti yang dikutip benar-benar berasal dari
#            teks. Pemeriksaan berlaku untuk setiap baris, bukan contoh acak.
# Masukan  : data/processed/v3 beserta berkas label
# Keluaran : reports/audit_label.json dan reports/audit_label.html
# Rujukan  : Bab IV pada bagian audit mutu label, yaitu kontribusi utama penelitian
#
# Menjalankan dari akar repositori:  py -3.13 analisis/05_audit_mutu_label.py
"""Pemindai mutu label semu hasil prompt v2 pada seluruh korpus.

Gold set manusia belum ada, sehingga "benar" tidak dapat diukur terhadap
kebenaran. Yang dapat diukur adalah **konsistensi internal** dan **kedasaran
bukti**: apakah label yang diberikan Gemma bertentangan dengan aturan promptnya
sendiri, dan apakah potongan bukti yang dikutip benar-benar berasal dari teks.
Kedua hal itu memberi batas bawah jumlah baris yang pasti bermasalah, sekaligus
batas atas mutu label yang boleh diklaim.

Pemeriksaan dijalankan pada **setiap baris**, bukan pada contoh acak, karena
cacat label yang jarang justru yang paling berbahaya bila lolos ke data latih.

Jalankan:
    py -3.13 modeling/audit_label.py
    py -3.13 modeling/audit_label.py --contoh 5
    py -3.13 modeling/audit_label.py --selftest
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraper import keywords  # noqa: E402
from scraper.labeling import ASPECTS, BAHASA, SENTIMEN_V2, TIPE_TEKS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"

BUCKET_FILES = {
    "opini": "korpus_opinion.csv",
    "non_opini": "korpus_non_opini.csv",
    "karantina": "karantina_tidak_relevan.csv",
}

KEPARAHAN = ["kritis", "tinggi", "sedang", "rendah"]

DIAKRITIK_ASING = re.compile(r"[\u00C0-\u024F\u1E00-\u1EFF]")


# ---------------------------------------------------------------------------
# Pembacaan dan normalisasi
# ---------------------------------------------------------------------------

def normalisasi(teks: str | None) -> str:
    """Menyeragamkan teks agar perbandingan kutipan tidak terganggu tanda baca."""
    t = unicodedata.normalize("NFKC", teks or "").lower()
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def extra_teks(extra: Any) -> tuple[str, str]:
    """Mengambil teks induk dan judul video dari kolom extra."""
    if isinstance(extra, str):
        try:
            extra = json.loads(extra or "{}")
        except json.JSONDecodeError:
            extra = {}
    if not isinstance(extra, dict):
        extra = {}
    induk = extra.get("parent_text") or extra.get("post_text") or extra.get("quote") or ""
    judul = extra.get("video_title") or extra.get("title") or ""
    return str(induk), str(judul)


def baca_ember(path: Path, ember: str) -> list[dict[str, Any]]:
    """Membaca satu berkas ember beserta kolom extra yang sudah diurai."""
    baris: list[dict[str, Any]] = []
    if not path.is_file():
        return baris
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            induk, judul = extra_teks(r.get("extra"))
            try:
                keyakinan = float(r.get("label_confidence") or 0.0)
            except ValueError:
                keyakinan = 0.0
            try:
                bintang = float(r.get("score")) if r.get("score") not in (None, "") else None
            except ValueError:
                bintang = None
            baris.append({
                "uid": (r.get("uid") or "").strip(),
                "ember": ember,
                "source": (r.get("source") or "").strip(),
                "text": r.get("text") or "",
                "text_clean": r.get("text_clean") or "",
                "sentimen": (r.get("label") or "").strip(),
                "tipe": (r.get("tipe") or "").strip(),
                "bahasa": (r.get("bahasa") or "").strip(),
                "keyakinan": keyakinan,
                "aspek": [a for a in (r.get("aspek") or "").replace(";", ",").split(",") if a.strip()],
                "bukti": (r.get("label_bukti") or "").strip(),
                "alasan": (r.get("label_reason") or "").strip(),
                "induk": induk,
                "judul": judul,
                "bintang": bintang,
            })
    return baris


def tumpang_tindih_kata(bukti: str, teks: str) -> float:
    """Menghitung porsi kata bukti yang muncul pada teks."""
    kata_bukti = normalisasi(bukti).split()
    if not kata_bukti:
        return 0.0
    himpunan = set(normalisasi(teks).split())
    if not himpunan:
        return 0.0
    return sum(1 for k in kata_bukti if k in himpunan) / len(kata_bukti)


# ---------------------------------------------------------------------------
# Pemeriksaan
# ---------------------------------------------------------------------------

def periksa_baris(r: dict[str, Any]) -> list[str]:
    """Mengembalikan daftar kode temuan untuk satu baris label."""
    temuan: list[str] = []
    sentimen, tipe, bahasa = r["sentimen"], r["tipe"], r["bahasa"]
    bukti, keyakinan = r["bukti"], r["keyakinan"]
    teks_gabung = f"{r['text']} {r['induk']}"

    if sentimen not in SENTIMEN_V2:
        temuan.append("sentimen_tidak_sah")
    if tipe not in TIPE_TEKS:
        temuan.append("tipe_tidak_sah")
    if bahasa not in BAHASA:
        temuan.append("bahasa_tidak_sah")
    if not 0.0 <= keyakinan <= 1.0:
        temuan.append("keyakinan_luar_rentang")

    if not bukti:
        temuan.append("bukti_kosong")
    elif normalisasi(bukti) not in normalisasi(r["text"]) and normalisasi(bukti) not in normalisasi(r["induk"]):
        if tumpang_tindih_kata(bukti, teks_gabung) < 0.6:
            temuan.append("bukti_tidak_berdasar")
        else:
            temuan.append("bukti_parafrase")
    if not r["alasan"]:
        temuan.append("alasan_kosong")

    if r["ember"] == "opini" and not r["aspek"]:
        temuan.append("aspek_kosong")
    if r["ember"] != "karantina" and sentimen == "tidak_relevan":
        temuan.append("tidak_relevan_di_luar_karantina")

    if tipe == "sapaan" and sentimen in ("positif", "negatif"):
        temuan.append("sapaan_bersentimen")
    if tipe == "sapaan" and keyakinan > 0.5:
        temuan.append("sapaan_keyakinan_tinggi")
    if tipe == "sapaan" and r["aspek"]:
        temuan.append("sapaan_beraspek")

    if r["ember"] == "karantina" and keywords.teks_bertopik(r["text"], r["induk"]):
        temuan.append("karantina_bertopik")

    if r["ember"] == "opini" and len(r["text_clean"].strip()) < 10:
        temuan.append("opini_teks_pendek")

    if keyakinan and keyakinan < 0.6:
        temuan.append("keyakinan_rendah")
    if keyakinan >= 0.999:
        temuan.append("keyakinan_mutlak")

    if r["ember"] in ("opini", "non_opini") and bahasa == "asing":
        temuan.append("asing_tapi_relevan")
    if DIAKRITIK_ASING.search(r["text_clean"]):
        temuan.append("aksara_asing")

    if r["source"] == "playstore" and r["bintang"] is not None:
        if r["bintang"] >= 5 and sentimen == "negatif":
            temuan.append("bintang5_negatif")
        if r["bintang"] <= 1 and sentimen == "positif":
            temuan.append("bintang1_positif")
    return temuan


def temuan_duplikat(baris: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Mencari teks yang identik namun diberi sentimen berbeda."""
    peta: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for r in baris:
        if r["ember"] not in ("opini", "non_opini") or not r["sentimen"]:
            continue
        kunci = normalisasi(r["text_clean"])
        if len(kunci) < 8:
            continue
        peta[kunci][r["sentimen"]].append(r["uid"])
    return {
        kunci: {s: u for s, u in isi.items()}
        for kunci, isi in peta.items()
        if len(isi) > 1
    }


def rangkum(baris: list[dict[str, Any]], tanpa_anotasi: list[str]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Menyusun ringkasan lengkap dari hasil pemeriksaan seluruh baris."""
    per_temuan: Counter[str] = Counter()
    per_keparahan: Counter[str] = Counter()
    bertanda: list[dict[str, Any]] = []

    for r in baris:
        temuan = periksa_baris(r)
        r["temuan"] = temuan
        if not temuan:
            continue
        per_temuan.update(temuan)
        tingkat = next((k for k in KEPARAHAN if any(_keparahan(t) == k for t in temuan)), "rendah")
        r["keparahan"] = tingkat
        per_keparahan[tingkat] += 1
        bertanda.append(r)

    keyakinan = [r["keyakinan"] for r in baris if r["keyakinan"] > 0]
    keyakinan.sort()
    duplikat = temuan_duplikat(baris)

    def sebaran(kunci: str) -> dict[str, int]:
        return dict(Counter(r[kunci] for r in baris).most_common())

    bintang = Counter()
    for r in baris:
        if r["source"] == "playstore" and r["bintang"] is not None:
            bintang[f"{int(r['bintang'])}bintang_{r['sentimen']}"] += 1

    grounded = sum(1 for r in baris if r["bukti"] and "bukti_tidak_berdasar" not in r["temuan"])
    return {
        "total_baris": len(baris),
        "tanpa_anotasi": tanpa_anotasi,
        "per_ember": sebaran("ember"),
        "per_source": sebaran("source"),
        "per_sentimen": sebaran("sentimen"),
        "per_tipe": sebaran("tipe"),
        "per_bahasa": sebaran("bahasa"),
        "keyakinan": {
            "rata": round(sum(keyakinan) / len(keyakinan), 4) if keyakinan else 0.0,
            "median": keyakinan[len(keyakinan) // 2] if keyakinan else 0.0,
            "min": keyakinan[0] if keyakinan else 0.0,
            "max": keyakinan[-1] if keyakinan else 0.0,
            "di_bawah_0_6": sum(1 for k in keyakinan if k < 0.6),
            "mutlak_1_0": sum(1 for k in keyakinan if k >= 0.999),
        },
        "bukti_berdasar": grounded,
        "porsi_bukti_berdasar": round(grounded / len(baris), 4) if baris else 0.0,
        "teks_identik_beda_sentimen": len(duplikat),
        "contoh_duplikat": [
            {"teks": k[:120], "label": v} for k, v in list(duplikat.items())[:10]
        ],
        "per_temuan": dict(per_temuan.most_common()),
        "per_keparahan": {k: per_keparahan.get(k, 0) for k in KEPARAHAN},
        "baris_bertanda": len(bertanda),
        "porsi_bertanda": round(len(bertanda) / len(baris), 4) if baris else 0.0,
        "bintang": dict(bintang.most_common()),
    }, bertanda


def _keparahan(kode: str) -> str:
    """Menetapkan tingkat keparahan untuk setiap jenis temuan."""
    if kode in {
        "sentimen_tidak_sah", "tipe_tidak_sah", "bahasa_tidak_sah",
        "keyakinan_luar_rentang", "tidak_relevan_di_luar_karantina",
    }:
        return "kritis"
    if kode in {
        "bukti_tidak_berdasar", "sapaan_bersentimen", "asing_tapi_relevan",
        "aksara_asing", "opini_teks_pendek",
    }:
        return "tinggi"
    if kode in {
        "bukti_kosong", "aspek_kosong", "sapaan_keyakinan_tinggi",
        "sapaan_beraspek", "karantina_bertopik", "bintang5_negatif", "bintang1_positif",
    }:
        return "sedang"
    return "rendah"


# ---------------------------------------------------------------------------
# Keluaran
# ---------------------------------------------------------------------------

CSS = """
body { margin: 0; padding: 24px; background: #f4f5f7; color: #1c1e21;
  font: 14px/1.55 "Segoe UI", system-ui, sans-serif; }
h1 { font-size: 20px; margin: 0 0 4px; }
h2 { font-size: 15px; margin: 26px 0 8px; text-transform: uppercase;
  letter-spacing: .06em; color: #5b6470; }
.sub { color: #5b6470; margin: 0 0 18px; }
table { border-collapse: collapse; width: 100%; background: #fff;
  border: 1px solid #e2e5ea; margin-bottom: 6px; }
th, td { text-align: left; padding: 7px 10px; border-bottom: 1px solid #eceef1; font-size: 13px; }
th { background: #f7f8fa; }
td.n { text-align: right; font-variant-numeric: tabular-nums; }
.kritis { color: #a3220f; font-weight: 600; }
.tinggi { color: #b4600a; font-weight: 600; }
.sedang { color: #7a6a10; }
.rendah { color: #5b6470; }
.angka { font-size: 26px; font-weight: 600; }
"""


def render_html(ringkas: dict[str, Any], berkas: dict[str, str]) -> str:
    """Membangun laporan HTML mandiri dari ringkasan audit."""
    def tabel(judul: str, isi: dict[str, Any], kelas_kunci: str = "") -> str:
        baris = "".join(
            f'<tr><td class="{kelas_kunci}">{k}</td><td class="n">{v}</td></tr>'
            for k, v in isi.items()
        )
        return f"<h2>{judul}</h2><table><tbody>{baris}</tbody></table>"

    temuan = "".join(
        f'<tr><td class="{_keparahan(k)}">{k}</td>'
        f'<td class="{_keparahan(k)}">{_keparahan(k)}</td><td class="n">{v}</td></tr>'
        for k, v in ringkas["per_temuan"].items()
    )
    duplikat = "".join(
        f'<tr><td>{d["teks"]}</td><td>{json.dumps(d["label"], ensure_ascii=False)}</td></tr>'
        for d in ringkas["contoh_duplikat"]
    )
    return (
        "<!doctype html>\n<html lang=\"id\">\n<head><meta charset=\"utf-8\">\n"
        "<title>Audit label semu v2</title>\n"
        f"<style>{CSS}</style></head>\n<body>\n"
        "<h1>Audit label semu prompt v2</h1>\n"
        f'<p class="sub">sumber: {", ".join(berkas.values())} &middot; '
        f'{ringkas["total_baris"]} baris dipindai</p>\n'
        f'<p class="angka">{ringkas["baris_bertanda"]} baris bertanda '
        f'({ringkas["porsi_bertanda"] * 100:.1f}%) &middot; '
        f'bukti berdasar {ringkas["porsi_bukti_berdasar"] * 100:.1f}%</p>\n'
        + tabel("Temuan", {k: f"{v}" for k, v in ringkas["per_temuan"].items()})
        + tabel("Keparahan", ringkas["per_keparahan"], "kritis")
        + tabel("Ember", ringkas["per_ember"])
        + tabel("Sentimen", ringkas["per_sentimen"])
        + tabel("Tipe", ringkas["per_tipe"])
        + tabel("Bahasa", ringkas["per_bahasa"])
        + tabel("Keyakinan", {k: str(v) for k, v in ringkas["keyakinan"].items()})
        + f"<h2>Teks identik dengan sentimen berbeda ({ringkas['teks_identik_beda_sentimen']})</h2>"
        + f"<table><tbody>{duplikat}</tbody></table>"
        + "</body></html>\n"
    )


def perintah_audit(args: argparse.Namespace) -> int:
    basis = Path(args.dir)
    baris: list[dict[str, Any]] = []
    for ember, nama in BUCKET_FILES.items():
        bagian = baca_ember(basis / nama, ember)
        print(f"{ember:10s} {len(bagian):6d} baris  ({nama})")
        baris.extend(bagian)

    terdaftar = {r["uid"] for r in baris}
    tanpa_anotasi: list[str] = []
    kandidat = sorted(basis.glob("dataset_se2026_ready*.csv"))
    sumber_path = kandidat[0] if kandidat else None
    if sumber_path is not None:
        with sumber_path.open("r", encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                if (r.get("uid") or "").strip() not in terdaftar:
                    tanpa_anotasi.append((r.get("uid") or "").strip())

    ringkas, bertanda = rangkum(baris, tanpa_anotasi)

    out_json = Path(args.out)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(ringkas, ensure_ascii=False, indent=2), encoding="utf-8")

    out_csv = Path(args.out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["uid", "ember", "keparahan", "temuan", "source", "sentimen", "tipe",
                    "bahasa", "keyakinan", "bukti", "text_clean"])
        for r in bertanda:
            w.writerow([r["uid"], r["ember"], r["keparahan"], ";".join(r["temuan"]), r["source"],
                        r["sentimen"], r["tipe"], r["bahasa"], r["keyakinan"], r["bukti"],
                        r["text_clean"]])

    out_html = Path(args.out_html)
    out_html.write_text(render_html(ringkas, BUCKET_FILES), encoding="utf-8")

    print("\n=== ringkasan audit label ===")
    print(f"total dipindai      : {ringkas['total_baris']}")
    print(f"baris bertanda      : {ringkas['baris_bertanda']} ({ringkas['porsi_bertanda']*100:.1f}%)")
    print(f"bukti berdasar      : {ringkas['porsi_bukti_berdasar']*100:.1f}%")
    print(f"teks identik beda   : {ringkas['teks_identik_beda_sentimen']}")
    print(f"tanpa anotasi       : {len(tanpa_anotasi)}")
    print("per keparahan       : " + ", ".join(f"{k}={v}" for k, v in ringkas["per_keparahan"].items()))
    print("\ntemuan terbanyak:")
    for k, v in list(ringkas["per_temuan"].items())[:18]:
        print(f"  {k:28s} {v}")
    print(f"\nberkas: {out_json.name}, {out_csv.name}, {out_html.name}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Memindai mutu label semu prompt v2 pada seluruh korpus")
    p.add_argument("--dir", default="data/processed", help="folder berisi ember korpus dan berkas siap label")
    p.add_argument("--out", default="reports/audit_label_v2.json")
    p.add_argument("--out-csv", default="data/processed/karantina_label_v2.csv")
    p.add_argument("--out-html", default="reports/audit_label_v2.html")
    return p


def selftest() -> int:
    dasar = {
        "uid": "x", "ember": "opini", "source": "youtube", "text": "aplikasi ini sering error",
        "text_clean": "aplikasi ini sering error", "sentimen": "negatif", "tipe": "opini",
        "bahasa": "indonesia", "keyakinan": 0.9, "aspek": ["teknis_aplikasi"],
        "bukti": "sering error", "alasan": "keluhan", "induk": "", "judul": "", "bintang": None,
    }
    assert periksa_baris(dasar) == [], periksa_baris(dasar)

    a = dict(dasar, bukti="aplikasi keren", keyakinan=0.99, tipe="sapaan", sentimen="positif",
             aspek=[], ember="non_opini")
    t = periksa_baris(a)
    assert "bukti_tidak_berdasar" in t and "sapaan_bersentimen" in t and "sapaan_keyakinan_tinggi" in t, t

    b = dict(dasar, sentimen="tidak_relevan", ember="opini")
    assert "tidak_relevan_di_luar_karantina" in periksa_baris(b)

    c = dict(dasar, ember="karantina", text="utang negara makin mahal", text_clean="utang negara makin mahal",
             sentimen="tidak_relevan", tipe="informasi", aspek=[])
    assert "karantina_bertopik" not in periksa_baris(c)

    assert normalisasi("Kerjaan  Aparat!") == "kerjaan aparat"
    assert round(tumpang_tindih_kata("sering error", "aplikasi ini sering error"), 3) == 1.0
    assert tumpang_tindih_kata("zzz qqq", "aplikasi ini") == 0.0
    assert _keparahan("sentimen_tidak_sah") == "kritis"
    assert _keparahan("keyakinan_rendah") == "rendah"

    ringkas, _ = rangkum([dasar], [])
    assert ringkas["per_sentimen"] == {"negatif": 1}, ringkas["per_sentimen"]
    assert ringkas["porsi_bukti_berdasar"] == 1.0, ringkas

    print("selftest audit_label ok")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if argv and argv[0] == "--selftest":
        return selftest()
    args = build_parser().parse_args(argv)
    return perintah_audit(args)


if __name__ == "__main__":
    raise SystemExit(main())
