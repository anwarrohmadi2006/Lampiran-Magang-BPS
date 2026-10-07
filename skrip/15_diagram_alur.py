# Analisis Sentimen Sensus Ekonomi 2026 dan Aplikasi Fasih BPS
# 15 Diagram Alur Penelitian
#
# Kegunaan : Menggambar tiga diagram alur dari kode dengan palet redup tanpa hiasan, yaitu alur
#            penelitian ujung ke ujung, urutan keputusan anotasi, dan perjalanan pengujian Jev.
# Masukan  : tanpa masukan data, seluruh isi diagram ditulis di dalam kode
# Keluaran : reports/diagram_alur_penelitian.png, diagram_keputusan_anotasi.png, diagram_uji_jev.png
# Rujukan  : Bab III pada diagram alir penelitian, serta Bab IV pada diagram pengujian Jev
#
# Menjalankan dari akar repositori:  py -3.13 analisis/15_diagram_alur.py
"""Menggambar tiga diagram alur untuk laporan, dari kode, dengan gaya yang sama
seperti diagram alir yang sudah ada: kotak membulat, palet redup, tanpa hiasan.

Diagram yang dihasilkan:
    reports/diagram_alur_penelitian.png      alur penelitian ujung ke ujung
    reports/diagram_keputusan_anotasi.png    urutan keputusan lima pilihan
    reports/diagram_uji_jev.png              perjalanan pengujian Jev
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"

GELAP = "#2f4f6f"
SEDANG = "#6b7a8d"
ISIAN = "#f4f6f9"
ISIAN_SOROT = "#e4ebf2"
TULISAN = "#1a1a1a"


def kotak(ax, x, y, teks, lebar=7.4, tinggi=0.62, sorot=False, ukuran=9.0, terminator=False):
    style = f"round,pad={tinggi*0.45}" if terminator else "round,pad=0.06"
    ax.add_patch(FancyBboxPatch((x, y), lebar, tinggi,
                                boxstyle=style,
                                linewidth=1.2,
                                edgecolor="#059669" if terminator else (GELAP if sorot else SEDANG),
                                facecolor="#ECFDF5" if terminator else (ISIAN_SOROT if sorot else ISIAN)))
    ax.text(x + lebar / 2, y + tinggi / 2, teks, ha="center", va="center",
            fontsize=ukuran, color="#065F46" if terminator else TULISAN,
            fontweight="bold" if terminator or sorot else "normal",
            linespacing=1.35)


def panah(ax, x1, y1, x2, y2, warna=SEDANG, gaya="-|>"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=gaya,
                                 mutation_scale=12, linewidth=1.1, color=warna))


def belah_ketupat(ax, x, y, teks, lebar=3.3, tinggi=0.95, ukuran=8.4):
    ax.add_patch(Polygon([(x, y + tinggi), (x + lebar, y), (x, y - tinggi), (x - lebar, y)],
                         closed=True, linewidth=1.2, edgecolor=GELAP, facecolor=ISIAN_SOROT))
    ax.text(x, y, teks, ha="center", va="center", fontsize=ukuran, color=TULISAN,
            fontweight="bold", linespacing=1.3)


def diagram_penelitian(path: Path) -> Path:
    tahap = [
        "Mulai",
        "Pengumpulan data tiga platform (10.961 rekaman)",
        "Penyaringan tanggal, bahasa, topik, dan deduplikasi",
        "Korpus final 8.352 baris pada jendela 15 Juni sampai 15 September 2026",
        "Anotasi semu dan partisi tiga kelompok korpus",
        "Audit mutu label menyeluruh (nol cacat kritis)",
        "Penyusunan data uji manusia (100 baris, tersamar)",
        "Pengukuran lima sistem terhadap data uji manusia",
        "Anotasi sentimen korpus dengan model keputusan terkalibrasi",
        "Pelatihan IndoBERT dan studi ablasi enam skenario",
        "Penjelasan model: peta atensi multi-head dan LIME",
        "Penyusunan laporan Kerja Praktik dan web pendukung keputusan",
        "Selesai",
    ]
    catatan = {
        4: "Anotator LLM Gemma (Prompt Sadar Konteks)",
        8: "Anotator Keputusan Jev (8.352 baris)",
        9: "Partisi opini berlabel Jev (5.808 baris)",
        10: "Model IndoBERT terbaik (Full R-Drop)",
    }
    tinggi, lebar, jarak = 0.66, 7.4, 1.05
    fig, ax = plt.subplots(figsize=(9.8, 0.68 * len(tahap) + 1.2))
    for i, t in enumerate(tahap):
        y = (len(tahap) - i) * jarak
        is_term = i in (0, len(tahap) - 1)
        kotak(ax, 0.4, y, t, lebar=lebar, tinggi=tinggi,
              sorot=is_term, terminator=is_term)
        if i:
            panah(ax, 0.4 + lebar / 2, y + tinggi + 0.35, 0.4 + lebar / 2, y + tinggi + 0.04)
        if i in catatan:
            ax.text(0.4 + lebar + 0.30, y + tinggi / 2, catatan[i], ha="left", va="center",
                    fontsize=7.8, color=SEDANG, style="italic")
    ax.set_xlim(0, lebar + 3.8)
    ax.set_ylim(0.2, (len(tahap) + 1.3) * jarak)
    ax.axis("off")
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def diagram_keputusan(path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(9.4, 6.6))
    x0 = 0.0

    kotak(ax, x0 - 2.4, 6.0, "Teks beserta konteks asalnya", lebar=4.8, tinggi=0.62)
    panah(ax, x0, 6.0, x0, 5.85)

    belah_ketupat(ax, x0, 4.85, "Membahas hal lain?")
    panah(ax, x0 + 3.3, 4.85, x0 + 4.6, 4.85)
    ax.text(x0 + 3.7, 5.10, "Ya", fontsize=8.5, fontweight="bold", color="#059669")
    kotak(ax, x0 + 4.6, 4.54, "Tidak relevan", lebar=3.4, tinggi=0.62, ukuran=8.6)
    ax.text(x0 + 6.3, 4.30, "politik, program lain, obrolan\nyang tak berkaitan",
            ha="center", va="top", fontsize=7.4, color=SEDANG, style="italic")

    ax.text(x0 - 0.45, 3.65, "Tidak", fontsize=8.5, fontweight="bold", color=GELAP, ha="right")
    panah(ax, x0, 3.85, x0, 3.58)

    belah_ketupat(ax, x0, 2.60, "Ada penilaian terhadap\ntopiknya?")
    panah(ax, x0 + 3.3, 2.60, x0 + 4.6, 2.60)
    ax.text(x0 + 3.7, 2.85, "Tidak", fontsize=8.5, fontweight="bold", color=GELAP)
    kotak(ax, x0 + 4.6, 2.29, "Bukan opini", lebar=3.4, tinggi=0.62, ukuran=8.6)
    ax.text(x0 + 6.3, 2.05, "sapaan, pertanyaan, minta\nbantuan, laporan keadaan,\nusulan walau mengkritik",
            ha="center", va="top", fontsize=7.4, color=SEDANG, style="italic")

    ax.text(x0 - 0.35, 1.35, "Ya", fontsize=8.5, fontweight="bold", color="#059669", ha="right")
    panah(ax, x0, 1.62, x0, 1.28)
    kotak(ax, x0 - 1.6, 0.65, "Arah penilaian", lebar=3.2, tinggi=0.62, ukuran=8.6)

    kotak(ax, x0 - 6.0, -0.65, "Positif", lebar=2.6, tinggi=0.60, ukuran=8.8)
    kotak(ax, x0 - 1.3, -0.65, "Negatif", lebar=2.6, tinggi=0.60, ukuran=8.8)
    kotak(ax, x0 + 3.4, -0.65, "Netral", lebar=2.6, tinggi=0.60, ukuran=8.8)
    panah(ax, x0, 0.65, x0 - 4.7, -0.03)
    panah(ax, x0, 0.65, x0, -0.03)
    panah(ax, x0, 0.65, x0 + 4.7, -0.03)
    ax.text(x0 - 5.7, -0.90, "pujian, syukur,\nmanfaat", ha="center", va="top",
            fontsize=7.4, color=SEDANG, style="italic")
    ax.text(x0 - 1.0, -0.85, "keluhan, kritik, sindiran;\ntermasuk keluhan aplikasi\nyang dibungkus pertanyaan",
            ha="center", va="top", fontsize=7.4, color=SEDANG, style="italic")
    ax.text(x0 + 4.1, -0.85, "datar atau campuran\ntanpa sisi dominan", ha="center", va="top",
            fontsize=7.4, color=SEDANG, style="italic")

    ax.text(x0, -2.4, "Saat ragu: ada kata yang menilai topiknya? Tidak ada berarti Bukan opini. "
                      "Penulis mengeluh? Negatif.",
            ha="center", va="top", fontsize=8.0, color=GELAP, fontweight="bold")

    ax.set_xlim(x0 - 7.0, x0 + 8.4)
    ax.set_ylim(-3.0, 7.2)
    ax.axis("off")
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def diagram_uji_jev(path: Path) -> Path:
    """Menggambar bagan evolusi kalibrasi berulang anotator keputusan Jev.

    Bagan ini merekam jejak empiris pengembangan prompt terkalibrasi melalui
    tujuh tahapan sistematis (Ronde 1 sampai Anotasi Korpus Penuh):
    1. Jev awal (batas gerbang sempit): Akurasi 0,2609 akibat penolakan biner berlebih.
    2. Jev adaptif (bingkai lembar anotasi): Akurasi melonjak ke 0,5109 dengan konteks sensus.
    3. Jev ronde 2 (penanaman aturan batas): Akurasi 0,6196 (sentimen 0,7935) berbasis uji antar-anotator.
    4. Jev ronde 3a (kalibrasi keluhan teknis): Akurasi 0,7826 setelah menyempurnakan aturan Fasih Play Store.
    5. Jev final (penajaman batas netral): Akurasi 0,7935 menstabilkan diferensiasi fakta vs keluhan.
    6. Validasi independen (data uji manusia): Akurasi 0,7882 mengungguli baseline Gemma 0,7176 secara buta.
    7. Anotasi korpus penuh: Eksekusi 8.352 baris korpus (8,3 juta token) tuntas seratus persen.

    Parameter:
        path (Path): Jalur berkas gambar keluaran (.png).

    Mengembalikan:
        Path: Jalur berkas gambar yang berhasil disimpan.
    """
    tahap = [
        ("Jev awal, batas gerbang sempit", "akurasi 0,2609 pada gold set ronde 1"),
        ("Jev adaptif, pembingkaian lembar anotasi", "akurasi 0,5109"),
        ("Jev ronde 2, penanaman aturan batas kelas", "akurasi 0,6196; kelas sentimen 0,7935"),
        ("Jev ronde 3a, kalibrasi aturan keluhan teknis", "akurasi 0,7826"),
        ("Jev final, penajaman batas netral dan keluhan", "akurasi 0,7935"),
        ("Validasi independen pada data uji manusia", "akurasi 0,7882 lawan Gemma 0,7176"),
        ("Anotasi korpus berskala penuh (8.352 baris)", "keberhasilan 100%, 8,3 juta token"),
    ]
    tinggi, lebar, jarak = 0.66, 7.4, 1.06
    fig, ax = plt.subplots(figsize=(10.0, 0.68 * len(tahap) + 1.2))
    for i, (judul, catatan) in enumerate(tahap):
        y = (len(tahap) - i) * jarak
        kotak(ax, 0.4, y, judul, lebar=lebar, tinggi=tinggi, sorot=i >= 5)
        if i:
            panah(ax, 0.4 + lebar / 2, y + tinggi + 0.36, 0.4 + lebar / 2, y + tinggi + 0.04)
        ax.text(0.4 + lebar + 0.30, y + tinggi / 2, catatan, ha="left", va="center",
                fontsize=7.8, color=SEDANG, style="italic")
    ax.set_xlim(0, lebar + 4.8)
    ax.set_ylim(0.2, (len(tahap) + 1.3) * jarak)
    ax.axis("off")
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


if __name__ == "__main__":
    for fungsi, nama in ((diagram_penelitian, "diagram_alur_penelitian.png"),
                         (diagram_keputusan, "diagram_keputusan_anotasi.png"),
                         (diagram_uji_jev, "diagram_uji_jev.png")):
        hasil = fungsi(REPORTS / nama)
        print(f"{nama}: {hasil.stat().st_size:,} bit")
