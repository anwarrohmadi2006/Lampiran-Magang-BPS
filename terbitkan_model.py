"""Menerbitkan endpoint penjelasan model ke Modal lalu menyambungkannya ke web.

Skrip ini melakukan seluruh rangkaian penerbitan dalam satu perintah:

    1. memeriksa perkakas Modal, keadaan login, dan kelengkapan model lokal
    2. mengunggah bobot model ke volume Modal (sekali saja)
    3. menerbitkan aplikasi modeling/modal_model.py
    4. menunggu endpoint hidup, lalu membuktikan sidik jari bobot yang disajikan
    5. menuliskan alamat endpoint ke web/konfigurasi.js

Halaman web tetap berfungsi penuh tanpa jaringan. Alamat pada konfigurasi itu
hanya menyalakan satu blok tambahan, yaitu uji model secara langsung.

Menjalankan:
    py -3.13 terbitkan_model.py                # periksa, terbitkan, tulis konfigurasi
    py -3.13 terbitkan_model.py --unggah       # unggah ulang bobot lebih dahulu
    py -3.13 terbitkan_model.py --periksa      # hanya memeriksa keadaan
    py -3.13 terbitkan_model.py --lewati-unggah
    py -3.13 terbitkan_model.py --selftest
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AKAR = Path(__file__).resolve().parent
PY = sys.executable

APP_NAME = "sensus-ekonomi-sentimen"
FUNGSI_ASGI = "api"
VOLUME = "sensus-ekonomi-data"
TUJUAN_VOLUME = "ablasi_se2026/best_model"

# Dua salinan bobot yang sah. Yang pertama adalah salinan definitif pada folder
# final, yang kedua berkas kerja asli dari Kaggle. Keduanya diperiksa sama.
KANDIDAT_MODEL = [
    AKAR / "final" / "model",
    AKAR / "reports" / "kaggle" / "ablasi_se2026" / "best_model",
]

BERKAS_MODEL = ["config.json", "model.safetensors", "tokenizer.json", "tokenizer_config.json"]
KONFIGURASI_WEB = AKAR / "dashboard_web" / "konfigurasi.js"
DAFTAR_KONFIGURASI_WEB = [
    AKAR / "dashboard_web" / "konfigurasi.js",
    AKAR / "web" / "konfigurasi.js",
    Path(r"c:\Users\user\Lampiran Magang BPS\dashboard_web\konfigurasi.js"),
]
APLIKASI_MODAL = AKAR / "modeling" / "modal_model.py"


# ---------------------------------------------------------------------------
# Perkakas
# ---------------------------------------------------------------------------

def jalankan(perintah: list[str], timeout: int = 3600) -> tuple[int, str]:
    """Menjalankan perintah dan mengembalikan kode keluar beserta seluruh keluarannya.

    PYTHONIOENCODING dipaksa UTF-8 karena perkakas Modal mencetak bilah kemajuan
    berkarakter kotak. Pada konsol Windows yang memakai codepage lama, cetakan itu
    melempar UnicodeEncodeError dan penerbitan berhenti sebelum dimulai.
    """
    lingkungan = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    proses = subprocess.run(
        perintah, cwd=str(AKAR), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout, env=lingkungan,
    )
    return proses.returncode, (proses.stdout or "") + (proses.stderr or "")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for blok in iter(lambda: f.read(1 << 20), b""):
            h.update(blok)
    return h.hexdigest()


def modal(*args: str, timeout: int = 3600) -> tuple[int, str]:
    return jalankan([PY, "-m", "modal", *args], timeout=timeout)


def folder_model() -> Path | None:
    """Memilih salinan bobot yang lengkap, mengutamakan salinan definitif."""
    for kandidat in KANDIDAT_MODEL:
        if kandidat.is_dir() and all((kandidat / b).is_file() for b in BERKAS_MODEL):
            return kandidat
    return None


def profil_modal() -> str | None:
    kode, keluaran = modal("profile", "current", timeout=120)
    if kode != 0:
        return None
    nama = keluaran.strip().splitlines()[-1].strip()
    return nama or None


def alamat_endpoint(profil: str) -> str:
    return f"https://{profil}--{APP_NAME}-{FUNGSI_ASGI}.modal.run"


# ---------------------------------------------------------------------------
# Pemeriksaan
# ---------------------------------------------------------------------------

def periksa(verbose: bool = True) -> dict:
    """Memeriksa perkakas, login, bobot lokal, dan keberadaan berkas aplikasi."""
    hasil: dict = {"siap": True, "catatan": []}

    kode, keluaran = modal("--version", timeout=120)
    hasil["modal"] = keluaran.strip().splitlines()[-1] if kode == 0 else None
    if kode != 0:
        hasil["siap"] = False
        hasil["catatan"].append(
            "perkakas Modal belum terpasang untuk py -3.13. Pasang dengan: "
            "py -3.13 -m pip install modal"
        )

    profil = profil_modal()
    hasil["profil"] = profil
    if not profil:
        hasil["siap"] = False
        hasil["catatan"].append(
            "belum login ke Modal. Jalankan lebih dahulu: py -3.13 -m modal token new"
        )

    berkas = folder_model()
    hasil["folder_model"] = str(berkas) if berkas else None
    if berkas is None:
        hasil["siap"] = False
        hasil["catatan"].append(
            "bobot model tidak lengkap. Dicari pada: "
            + ", ".join(str(k) for k in KANDIDAT_MODEL)
        )
    else:
        bobot = berkas / "model.safetensors"
        hasil["bobot_bit"] = bobot.stat().st_size
        hasil["bobot_sha256"] = sha256(bobot)

    if not APLIKASI_MODAL.is_file():
        hasil["siap"] = False
        hasil["catatan"].append(f"berkas aplikasi tidak ada: {APLIKASI_MODAL}")

    if verbose:
        print("=== pemeriksaan ===")
        print(f"  perkakas Modal : {hasil.get('modal') or 'TIDAK ADA'}")
        print(f"  profil         : {hasil.get('profil') or 'BELUM LOGIN'}")
        print(f"  bobot model    : {hasil.get('folder_model') or 'TIDAK LENGKAP'}")
        if hasil.get("bobot_bit"):
            print(f"  ukuran bobot   : {hasil['bobot_bit']:,} bit")
            print(f"  sidik jari     : {hasil['bobot_sha256']}")
        for c in hasil["catatan"]:
            print(f"  catatan        : {c}")
        print(f"  keadaan        : {'siap' if hasil['siap'] else 'BELUM SIAP'}")
    return hasil


# ---------------------------------------------------------------------------
# Tahapan penerbitan
# ---------------------------------------------------------------------------

def unggah(berkas: Path) -> int:
    """Mengunggah bobot model ke volume Modal, menimpa salinan lama."""
    print(f"\n[unggah] {berkas} -> {VOLUME}:{TUJUAN_VOLUME}")
    print("         berkas sekitar 475 MB; unggahan ini hanya perlu sekali")
    kode, keluaran = modal("volume", "put", VOLUME, str(berkas), TUJUAN_VOLUME, "--force")
    print("         " + "\n         ".join(keluaran.strip().splitlines()[-6:]))
    return kode


def terbitkan() -> tuple[int, str | None]:
    """Menerbitkan aplikasi dan mengembalikan alamat endpoint bila terbaca."""
    print("\n[terbitkan] membangun image dan menerbitkan aplikasi")
    print("            pembangunan pertama memakan beberapa menit karena torch")
    kode, keluaran = modal("deploy", str(APLIKASI_MODAL.relative_to(AKAR)))
    print("            " + "\n            ".join(keluaran.strip().splitlines()[-8:]))
    if kode != 0:
        return kode, None
    cocok = re.findall(r"https://[A-Za-z0-9_.-]+\.modal\.run", keluaran)
    return 0, (cocok[-1].rstrip("/") if cocok else None)


def ambil_json(url: str, timeout: int = 60) -> tuple[int, dict | None]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return 0, None


def tunggu_hidup(alamat: str, batas_detik: int = 600) -> dict | None:
    """Menunggu /kesehatan menjawab siap, lalu mengembalikan laporannya."""
    print(f"\n[menunggu] {alamat}/kesehatan")
    mulai = time.time()
    percobaan = 0
    while time.time() - mulai < batas_detik:
        percobaan += 1
        kode, isi = ambil_json(f"{alamat}/kesehatan", timeout=30)
        if kode == 200 and isi:
            if isi.get("siap"):
                print(f"           siap setelah {time.time() - mulai:.0f} detik "
                      f"({percobaan} percobaan)")
                return isi
            print("           endpoint menjawab, tetapi model belum ada pada volume")
            return isi
        print(f"           percobaan {percobaan}: belum siap ({kode or 'tidak terjangkau'})")
        time.sleep(10)
    print(f"           belum siap setelah {batas_detik} detik")
    return None


def uji_prediksi(alamat: str, teks: str) -> dict | None:
    """Menembak satu teks ke /analisis untuk membuktikan endpoint benar-benar bekerja."""
    muatan = json.dumps({"teks": teks, "atas": 8}).encode("utf-8")
    permintaan = urllib.request.Request(
        f"{alamat}/analisis", data=muatan,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(permintaan, timeout=180) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # Badan galat ikut dicetak: tanpa itu, satu-satunya petunjuk yang tersisa
        # adalah kode status, dan penyebabnya harus ditebak.
        badan = e.read().decode("utf-8", "replace")
        print(f"           gagal menguji prediksi: HTTP {e.code}")
        print(f"           badan: {badan[:400]}")
        return None
    except Exception as e:  # noqa: BLE001
        print(f"           gagal menguji prediksi: {type(e).__name__}: {e}")
        return None


def tulis_konfigurasi(alamat: str, catatan: str = "") -> None:
    """Menuliskan alamat endpoint ke berkas konfigurasi antarmuka web."""
    isi = (
        "/* Alamat endpoint penjelasan model di Modal.\n"
        "   Berkas ini ditulis otomatis oleh terbitkan_model.py; jangan disunting\n"
        "   dengan tangan karena penjalanan berikutnya akan menimpanya.\n"
        "   Mengosongkan endpoint membuat halaman tetap berfungsi penuh, hanya\n"
        "   tanpa blok uji model secara langsung. */\n"
        "window.DSS_KONFIG = "
        + json.dumps({
            "endpoint": alamat,
            "aplikasi": APP_NAME,
            "diterbitkan": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z"),
            "catatan": catatan,
        }, ensure_ascii=False, indent=2)
        + ";\n"
    )
    for target in DAFTAR_KONFIGURASI_WEB:
        try:
            if target.parent.is_dir() or target == KONFIGURASI_WEB:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(isi, encoding="utf-8")
                print(f"[konfigurasi] berhasil ditulis ke: {target}")
        except Exception as e:
            print(f"[konfigurasi] lewati {target}: {e}")
    print(f"              endpoint aktif: {alamat or '(kosong)'}")


def selftest() -> int:
    assert APP_NAME and FUNGSI_ASGI and VOLUME and TUJUAN_VOLUME
    assert not APP_NAME.startswith("--") and " " not in APP_NAME
    assert len(BERKAS_MODEL) == 4 and "model.safetensors" in BERKAS_MODEL
    assert len(KANDIDAT_MODEL) >= 2, "perlu salinan cadangan bila satu hilang"
    assert KONFIGURASI_WEB.name == "konfigurasi.js"
    assert alamat_endpoint("contoh") == f"https://contoh--{APP_NAME}-{FUNGSI_ASGI}.modal.run"
    assert re.findall(r"https://[A-Za-z0-9_.-]+\.modal\.run",
                      "lihat https://a--b-c.modal.run/ ya") == ["https://a--b-c.modal.run"]
    print("selftest terbitkan_model ok")
    return 0


# ---------------------------------------------------------------------------
# Titik masuk
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Menerbitkan endpoint penjelasan model ke Modal")
    p.add_argument("--periksa", action="store_true", help="hanya memeriksa keadaan")
    p.add_argument("--unggah", action="store_true", help="unggah ulang bobot ke volume")
    p.add_argument("--lewati-unggah", action="store_true", help="jangan menyentuh volume")
    p.add_argument("--teks-uji", default="aplikasi fasih sering error waktu submit data",
                   help="teks contoh untuk membuktikan endpoint bekerja")
    p.add_argument("--selftest", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if argv and argv[0] == "--selftest":
        return selftest()

    args = build_parser().parse_args(argv)
    if args.selftest:
        return selftest()

    hasil = periksa()
    if not hasil["siap"]:
        print("\npenerbitan dibatalkan sampai pemeriksaan di atas beres.")
        return 1
    if args.periksa:
        return 0

    if args.unggah:
        kode = unggah(folder_model())
        if kode != 0:
            print("\nunggahan gagal; penerbitan dihentikan.")
            return 1
    elif args.lewati_unggah:
        print("\n[unggah] dilewati atas permintaan")
    else:
        print("\n[unggah] dilewati; volume dianggap sudah memuat bobot yang sama")
        print("         pakai --unggah bila bobot lokal berubah")

    kode, alamat = terbitkan()
    if kode != 0:
        return 1

    profil = hasil.get("profil")
    if not alamat and profil:
        alamat = alamat_endpoint(profil)
        print(f"\n[alamat] dibentuk dari nama profil: {alamat}")
    if not alamat:
        print("\nalamat endpoint tidak dapat ditentukan; konfigurasi web tidak ditulis.")
        return 1

    laporan = tunggu_hidup(alamat)
    catatan = ""
    if laporan is None:
        catatan = "endpoint belum menjawab saat penerbitan selesai"
    elif not laporan.get("siap"):
        catatan = "endpoint menjawab, tetapi bobot model belum ada pada volume"

    if laporan and laporan.get("bobot", {}).get("sha256"):
        jarak = ""
        if laporan["bobot"]["sha256"] != hasil.get("bobot_sha256"):
            jarak = "  <-- BERBEDA dari bobot lokal"
        print(f"\n[bobot] disajikan : {laporan['bobot']['sha256']}")
        print(f"        lokal      : {hasil.get('bobot_sha256')}{jarak}")

    if laporan and laporan.get("siap"):
        hasil_uji = uji_prediksi(alamat, args.teks_uji)
        if hasil_uji:
            print(f"\n[uji] \"{args.teks_uji}\"")
            print(f"      prediksi {hasil_uji['prediksi']} "
                  f"dengan peluang {hasil_uji['peluang']}")
            print(f"      token teratas menurut atensi: "
                  + ", ".join(t["teks"] for t in hasil_uji["peringkat"]["atensi"][:5]))

    tulis_konfigurasi(alamat, catatan)
    print("\n[susun ulang] jalankan py -3.13 buat_web_dss.py agar halaman memakai endpoint ini")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
