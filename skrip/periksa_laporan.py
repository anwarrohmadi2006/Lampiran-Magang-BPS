"""Memeriksa mutu penulisan laporan KP terhadap kaidah yang dipakai pembimbing.

Pemeriksa ini menilai hal yang dapat diukur otomatis pada berkas .docx hasil
susunan: keberadaan em dash, kata penghubung yang membuka kalimat, rujukan
tabel dan gambar sebelum tampil, urutan penomoran, baris "Sumber:" yang
miring, singkatan pada judul kolom, istilah asing yang belum dimiringkan,
kalimat yang menggantung ke sub-bab lain, paragraf yang terlalu panjang, dan
kebersihan angka yang dilaporkan.

Setiap temuan dikurangi dari nilai awal 100 menurut bobotnya, sehingga hasil
pemeriksaan dapat dibandingkan antarputaran penyuntingan.

Menjalankan:
    py -3.13 periksa_laporan.py --laporan reports/laporan.docx
    py -3.13 periksa_laporan.py --laporan reports/laporan.docx --out reports/periksa_laporan.json
    py -3.13 periksa_laporan.py --selftest
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Istilah asing yang wajib dimiringkan pada naskah laporan.
ISTILAH_ASING = (
    "gold set", "pseudo-label", "prompt", "checkpoint", "dataset", "endpoint",
    "fine-tuning", "noise", "overfitting", "token", "recall",
)

# Singkatan yang tidak boleh dipakai pada judul kolom tabel.
SINGKATAN_TERLARANG = ("No", "SD", "SMP", "KV", "Min", "Maks", "dll", "dsb", "sda")

# Angka yang tidak boleh lagi muncul (peninggalan pengukuran lama) dan angka
# yang wajib muncul (hasil data uji tunggal).
ANGKA_USANG = ("0,7391", "0,7717", "0,7772", "0,8903", "0,9162", "0,8545")
ANGKA_WAJIB = ("0,7882", "0,8830", "0,7628", "0,7713", "0,7700")

KONJUNGSI_AWAL = ("Namun", "Dengan", "Sedangkan", "Jadi", "Sehingga", "Tetapi",
                  "Tapi", "Sementara", "Adapun")

FRASA_MENGGANTUNG = ("sub-bab berikutnya", "sub bab berikutnya", "sub-bab ini",
                     "pada bab berikutnya", "di sub-bab selanjutnya")

BOBOT = {
    "em_dash": 5,
    "konektor_awal": 5,
    "rujukan_sebelum_tampil": 5,
    "urutan_nomor": 5,
    "kalimat_menggantung": 3,
    "sumber_miring": 3,
    "singkatan_kolom": 3,
    "istilah_asing": 2,
    "angka_usang": 5,
    "angka_wajib": 5,
    "paragraf_panjang": 2,
    "judul_berawalan_dari": 5,
}

KETERANGAN_TABEL = re.compile(r"^(Tabel)\s+(\d+)\.(\d+)\b")
KETERANGAN_GAMBAR = re.compile(r"^(Gambar)\s+(\d+)\.(\d+)\b")
RUJUKAN = re.compile(r"\b(Tabel|Gambar)\s+(\d+)\.(\d+)\b")


def _teks_paragraf(doc) -> list[dict]:
    """Mengumpulkan paragraf beserta gaya dan penanda miring tiap potongannya."""
    hasil = []
    for p in doc.paragraphs:
        potongan = [{"teks": r.text, "miring": bool(r.italic)} for r in p.runs if r.text]
        hasil.append({
            "teks": "".join(x["teks"] for x in potongan),
            "potongan": potongan,
            "gaya": (p.style.name if p.style is not None else ""),
        })
    return hasil


def periksa(doc) -> dict:
    paragraf = _teks_paragraf(doc)
    temuan: dict[str, list[str]] = {k: [] for k in BOBOT}

    # Penanda wilayah: abstrak berbahasa Inggris memang tidak dimiringkan dan
    # abstrak lazimnya satu paragraf panjang, sehingga keduanya dikecualikan
    # dari aturan istilah asing dan aturan panjang paragraf.
    dalam_inggris = False
    dalam_abstrak = False
    penanda = []
    for p in paragraf:
        teks_ringkas = p["teks"].strip()
        if teks_ringkas == "ABSTRAK":
            dalam_abstrak = True
        elif teks_ringkas == "ABSTRACT":
            dalam_abstrak = True
            dalam_inggris = True
        elif teks_ringkas.startswith("DAFTAR ISI"):
            dalam_abstrak = False
            dalam_inggris = False
        penanda.append((dalam_inggris, dalam_abstrak))

    # 1 dan 2: em dash serta kata penghubung pada awal kalimat.
    for p in paragraf:
        if "—" in p["teks"]:
            temuan["em_dash"].append(p["teks"][:90])
        for cocok in re.finditer(
            r"(?:^|(?<=[.!?])\s)(" + "|".join(KONJUNGSI_AWAL) + r")\b", p["teks"]
        ):
            temuan["konektor_awal"].append(f"{cocok.group(1)}: {p['teks'][:80]}")

    # 3 dan 4: rujukan sebelum tampil serta urutan nomor keterangan.
    sudah_disebut: set[str] = set()
    nomor_terakhir: dict[tuple[str, str], int] = {}
    for p in paragraf:
        teks = p["teks"].strip()
        keterangan = KETERANGAN_TABEL.match(teks) or KETERANGAN_GAMBAR.match(teks)
        if keterangan:
            jenis, bab, nomor = keterangan.group(1), keterangan.group(2), int(keterangan.group(3))
            kunci = f"{jenis} {bab}.{nomor}"
            if kunci not in sudah_disebut:
                temuan["rujukan_sebelum_tampil"].append(kunci)
            sebelumnya = nomor_terakhir.get((jenis, bab), 0)
            if nomor != sebelumnya + 1:
                temuan["urutan_nomor"].append(f"{kunci} setelah {jenis} {bab}.{sebelumnya}")
            nomor_terakhir[(jenis, bab)] = nomor
        else:
            for cocok in RUJUKAN.finditer(teks):
                sudah_disebut.add(f"{cocok.group(1)} {cocok.group(2)}.{cocok.group(3)}")

    # 5: baris "Sumber:" tidak boleh miring dan baris lain setelahnya.
    for p in paragraf:
        if p["teks"].strip().startswith("Sumber:"):
            if any(x["miring"] for x in p["potongan"]):
                temuan["sumber_miring"].append(p["teks"][:80])

    # 6: singkatan pada judul kolom tabel.
    for t in doc.tables:
        if not t.rows:
            continue
        for sel in t.rows[0].cells:
            for kata in SINGKATAN_TERLARANG:
                if re.search(rf"\b{kata}\b", sel.text):
                    temuan["singkatan_kolom"].append(f"{kata} pada: {sel.text[:60]}")

    # 7: istilah asing yang belum dimiringkan, kecuali pada abstrak Inggris.
    # Pencocokan memakai batas kata, sama seperti penyunting pada
    # buat_laporan_docx.py, supaya kata di dalam nama berkas atau bentuk jamak
    # berbahasa Inggris tidak ikut tertandai.
    pola_istilah = re.compile(
        r"\b(" + "|".join(re.escape(i) for i in ISTILAH_ASING) + r")\b", re.IGNORECASE)
    for p, (inggris, _) in zip(paragraf, penanda):
        if inggris:
            continue
        for x in p["potongan"]:
            if x["miring"]:
                continue
            for cocok in pola_istilah.finditer(x["teks"]):
                temuan["istilah_asing"].append(
                    f"{cocok.group(0)} pada: {x['teks'][:70].strip()}")

    # 8 dan 9: kebersihan angka.
    seluruh = "\n".join(p["teks"] for p in paragraf)
    for angka in ANGKA_USANG:
        if angka in seluruh:
            temuan["angka_usang"].append(angka)
    for angka in ANGKA_WAJIB:
        if angka not in seluruh:
            temuan["angka_wajib"].append(angka)

    # 10: kalimat yang menggantung ke bagian lain.
    for p in paragraf:
        for frasa in FRASA_MENGGANTUNG:
            if frasa in p["teks"]:
                temuan["kalimat_menggantung"].append(f"{frasa}: {p['teks'][:80]}")

    # 11: paragraf terlalu panjang (di atas 180 kata), kecuali abstrak.
    for p, (_, abstrak) in zip(paragraf, penanda):
        if abstrak:
            continue
        jumlah = len(p["teks"].split())
        if jumlah > 180:
            temuan["paragraf_panjang"].append(f"{jumlah} kata: {p['teks'][:80]}")

    # 12: judul tidak berawalan kata "Dari".
    for p in paragraf:
        if p["gaya"].lower().startswith("title") or (
            p["teks"].isupper() and len(p["teks"].split()) > 6 and "SENTIMEN" in p["teks"]
        ):
            if p["teks"].strip().lower().startswith("dari "):
                temuan["judul_berawalan_dari"].append(p["teks"][:90])

    nilai = 100
    for kunci, bobot in BOBOT.items():
        nilai -= bobot * len(temuan[kunci])
    return {"temuan": temuan, "nilai": max(0, nilai)}


def cetak(hasil: dict) -> None:
    temuan = hasil["temuan"]
    print("=== pemeriksaan mutu penulisan laporan ===")
    for kunci, bobot in BOBOT.items():
        jumlah = len(temuan[kunci])
        tanda = "ok   " if jumlah == 0 else "TEMUAN"
        print(f"  {tanda} {kunci:26s} {jumlah:3d}  (bobot {bobot})")
    total = sum(len(v) for v in temuan.values())
    print(f"\nnilai: {hasil['nilai']} dari 100 (total temuan {total})")
    for kunci in BOBOT:
        if temuan[kunci]:
            print(f"\n--- {kunci} ---")
            for t in temuan[kunci][:12]:
                print(f"   {t}")
            if len(temuan[kunci]) > 12:
                print(f"   ... dan {len(temuan[kunci]) - 12} lagi")


def _selftest() -> int:
    from docx import Document

    doc = Document()
    doc.add_paragraph("Namun kepatuhan format belum tentu menjamin kebenaran substansi.")
    doc.add_paragraph("Kalimat ini memuat em dash — yang terlarang.")
    doc.add_paragraph("Pembahasan lanjutannya ada pada sub-bab berikutnya.")
    doc.add_paragraph("Tabel 4.1 Hasil Penyaringan")
    doc.add_paragraph("Tabel 4.3 Hasil Pelabelan")
    doc.add_paragraph("Angka lama 0,7391 tidak boleh muncul.")
    t = doc.add_table(rows=2, cols=2)
    t.rows[0].cells[0].text = "No"
    t.rows[0].cells[1].text = "Tahap"
    t.rows[1].cells[0].text = "1"
    t.rows[1].cells[1].text = "Awal"

    hasil = periksa(doc)
    temuan = hasil["temuan"]
    assert len(temuan["em_dash"]) == 1, temuan["em_dash"]
    assert len(temuan["konektor_awal"]) == 1, temuan["konektor_awal"]
    assert "Tabel 4.1" in temuan["rujukan_sebelum_tampil"]
    assert any("Tabel 4.3" in x for x in temuan["urutan_nomor"])
    assert "0,7391" in temuan["angka_usang"]
    assert any("No" in x for x in temuan["singkatan_kolom"])
    assert temuan["kalimat_menggantung"], temuan["kalimat_menggantung"]
    assert hasil["nilai"] < 100
    print("selftest periksa_laporan ok")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--laporan", default=None, help="berkas .docx yang diperiksa")
    p.add_argument("--out", default=None, help="berkas JSON keluaran")
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args(argv)

    if args.selftest:
        return _selftest()

    if not args.laporan:
        print("beri --laporan berkas .docx", file=sys.stderr)
        return 1
    berkas = Path(args.laporan)
    if not berkas.is_file():
        print(f"berkas tidak ada: {berkas}", file=sys.stderr)
        return 1

    from docx import Document

    hasil = periksa(Document(str(berkas)))
    hasil["laporan"] = str(berkas)
    hasil["diperiksa"] = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    cetak(hasil)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(hasil, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nringkasan -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
