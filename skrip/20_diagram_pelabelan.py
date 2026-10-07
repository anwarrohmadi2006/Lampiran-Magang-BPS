# Analisis Sentimen Sensus Ekonomi 2026 dan Aplikasi Fasih BPS
# 20 Diagram Pipeline Utama dan Pipeline Ablation (Hulu ke Hilir dengan Preprocessing)
#
# Kegunaan : Menggambar bagan pipeline komprehensif hulu ke hilir, mulai dari
#            pengumpulan data mentah, tahapan preprocessing berlapis, dua pipeline
#            pelabelan (utama dan ablation), pelatihan IndoBERT, evaluasi pada gold set
#            manusia, uji signifikansi statistik McNemar, hingga penjelasan model.
# Masukan  : tanpa masukan data eksternal, konfigurasi terintegrasi di dalam skrip
# Keluaran : reports/diagram_alur_pelabelan.png, .svg, dan .html
# Rujukan  : Bab III Gambar 3.4 dan Sub-bab 3.4

from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"

GELAP = "#2f4f6f"
REDUP = "#6b7a8d"
TERANG = "#f4f6f9"
AKS_BIRU = "#1d4ed8"


def kotak(ax, x, y, lebar, tinggi, teks, *, kepala=False, ukuran=10.0,
          putus=False, latar=None, warna_teks_khusus=None, tebal_garis=1.1):
    muka = latar if latar else (GELAP if kepala else TERANG)
    warna_teks = warna_teks_khusus if warna_teks_khusus else ("white" if kepala else "#1f2a37")
    tepi = GELAP if kepala else REDUP
    ax.add_patch(FancyBboxPatch(
        (x - lebar / 2, y - tinggi / 2), lebar, tinggi,
        boxstyle="round,pad=0.06,rounding_size=0.12",
        linewidth=tebal_garis, edgecolor=tepi, facecolor=muka, zorder=2,
        linestyle=(0, (4, 3)) if putus else "-"))
    ax.text(x, y, teks, ha="center", va="center", fontsize=ukuran,
            color=warna_teks, zorder=3, linespacing=1.4)


def panah(ax, x1, y1, x2, y2, *, gaya="-", warna=GELAP, lebar=1.3):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=12,
        linewidth=lebar, color=warna, linestyle=gaya, zorder=1,
        shrinkA=1, shrinkB=1))


def gambar() -> None:
    fig, ax = plt.subplots(figsize=(16, 14.5))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 15)
    ax.axis("off")

    # 1. HULU: Data mentah
    kotak(ax, 8, 14.3, 10.2, 0.76,
          "PENGUMPULAN DATA MENTAH TIGA PLATFORM DIGITAL\n"
          "10.961 rekaman (YouTube 8.784 · Google Play Store 1.831 · Threads 346)",
          kepala=True, ukuran=10.5)

    # 2. TAHAP PREPROCESSING BERLAPIS (Header kontainer & 4 box horizontal)
    kotak(ax, 8, 13.48, 14.8, 0.44,
          "TAHAP PREPROCESSING BERLAPIS (PENYARINGAN KORPUS)",
          latar="#e2e8f0", warna_teks_khusus="#1e293b", ukuran=9.5)

    kotak(ax, 2.3, 12.55, 3.25, 0.85,
          "1. Filter Rentang Waktu\n15 Jun – 15 Sep 2026\n(sisa: 8.953 rekaman)",
          ukuran=9.0)
    kotak(ax, 6.1, 12.55, 3.25, 0.85,
          "2. Filter Bahasa Asing\nEliminasi non-Indonesia\n(sisa: 8.952 rekaman)",
          ukuran=9.0)
    kotak(ax, 9.9, 12.55, 3.25, 0.85,
          "3. Filter Relevansi Topik\nPenyaringan Threads\n(sisa: 8.831 rekaman)",
          ukuran=9.0)
    kotak(ax, 13.7, 12.55, 3.25, 0.85,
          "4. Deduplikasi Teks\nSidik Jari MD5 Ringkas\n(sisa: 8.352 baris)",
          ukuran=9.0)

    # Panah alur preprocessing
    panah(ax, 8, 13.92, 8, 13.7)
    panah(ax, 2.3, 13.26, 2.3, 12.98)
    panah(ax, 3.93, 12.55, 4.47, 12.55)
    panah(ax, 7.73, 12.55, 8.27, 12.55)
    panah(ax, 11.53, 12.55, 12.07, 12.55)

    # 3. KORPUS BERSIH SIAP ANOTASI
    kotak(ax, 8, 11.28, 9.4, 0.76,
          "KORPUS TEKS BERSIH SIAP ANOTASI\n"
          "8.352 baris (YouTube 6.727 · Google Play 1.366 · Threads 259)",
          kepala=True, ukuran=10.5)
    panah(ax, 13.7, 12.12, 10.5, 11.66)
    panah(ax, 2.3, 12.12, 5.5, 11.66)

    # 4. KEPALA DUA PIPELINE
    kotak(ax, 4, 10.22, 7.0, 0.58, "PIPELINE UTAMA (GEMMA-JEV)", kepala=True, ukuran=10.5)
    kotak(ax, 12, 10.22, 7.0, 0.58, "PIPELINE PEMBANDING (ABLATION JEV)", kepala=True, ukuran=10.5)

    # 5. JALUR UTAMA (Kiri)
    kotak(ax, 4, 9.28, 7.0, 0.8,
          "Pemilah Relevansi: LLM Gemma 4 12B\n"
          "partisi opini: 5.808 · non-opini: 2.119 · karantina: 423")
    kotak(ax, 4, 8.22, 7.0, 0.8,
          "Anotator Sentimen: Model Keputusan Jev\n"
          "negatif: 3.978 · positif: 1.315 · netral: 515 (8,9%)")
    kotak(ax, 4, 7.22, 7.0, 0.65, "Data Latih Sentimen: 5.808 baris")
    kotak(ax, 4, 6.32, 7.0, 0.65, "Pelatihan IndoBERT · Skenario Penuh (R-Drop)")

    # 6. JALUR ABLATION (Kanan)
    kotak(ax, 12, 9.28, 7.0, 0.8,
          "Pemilah Relevansi: Model Keputusan Jev\n"
          "ambang peluang 0,20 · dipilah keluar: 436 baris", putus=True)
    kotak(ax, 12, 8.22, 7.0, 0.8,
          "Anotator Sentimen: Model Keputusan Jev\n"
          "negatif: 3.814 · positif: 1.413 · netral: 363", putus=True)
    kotak(ax, 12, 7.22, 7.0, 0.65, "Data Latih Sentimen: 5.590 baris", putus=True)
    kotak(ax, 12, 6.32, 7.0, 0.65, "Pelatihan IndoBERT · Skenario Penuh (R-Drop)", putus=True)

    # 7. TITIK TEMU EVALUASI: DATA UJI MANUSIA
    kotak(ax, 8, 5.22, 11.2, 0.72,
          "DATA UJI MANUSIA (GOLD SET INDEPENDEN)\n"
          "100 baris acuan manusia · 85 baris tersentimen", ukuran=10.5)

    # 8. HASIL KINERJA
    kotak(ax, 4.4, 4.18, 6.2, 0.74,
          "Pipeline Utama (Rujukan)\n"
          "Akurasi: 0,7882 · F1 Macro: 0,7700")
    kotak(ax, 11.6, 4.18, 6.2, 0.74,
          "Pipeline Pembanding (Ablasi)\n"
          "Akurasi: 0,7529 · F1 Macro: 0,7387", putus=True)

    # 9. UJI BERPASANGAN MCNEMAR
    kotak(ax, 8, 3.16, 12.6, 0.64,
          "Uji Berpasangan McNemar (Dietterich, 1998)\n"
          "p = 0,5811 · Perbedaan kinerja kedua pipeline belum signifikan secara statistik")

    # 10. MODUL EKSPLANASI & REKOMENDASI BPS
    kotak(ax, 8, 2.14, 12.6, 0.74,
          "Eksplanasi Model (Explainable AI) & Rekomendasi Kebijakan Operasional BPS\n"
          "Peta Atensi Multi-Head · Perturbasi LIME · Analisis Tematik Kalimat 4 Isu Strategis",
          latar="#e0f2fe", warna_teks_khusus="#0369a1")

    # Keterangan penjelas di bawah diagram
    ax.text(8, 0.95,
            "Alur komprehensif dari hulu ke hilir: data mentah disaring bertahap melalui empat tahap preprocessing,\n"
            "dianotasi melalui dua pipeline berbeda, dilatih dengan IndoBERT, dievaluasi secara independen terhadap gold set manusia,\n"
            "serta diverifikasi melalui uji signifikansi statistik McNemar dan modul penjelasan model (Explainable AI).",
            ha="center", va="center", fontsize=9.5, color="#1f2a37", linespacing=1.45)

    # Hubungan panah dari Korpus Bersih ke Dua Pipeline
    panah(ax, 6.4, 10.9, 4, 10.51)
    panah(ax, 9.6, 10.9, 12, 10.51)

    # Panah vertikal jalur utama dan jalur ablation
    for x in (4, 12):
        warna = GELAP if x == 4 else REDUP
        gaya = "-" if x == 4 else (0, (4, 3))
        panah(ax, x, 9.93, x, 9.68, warna=warna, gaya=gaya)
        panah(ax, x, 8.88, x, 8.62, warna=warna, gaya=gaya)
        panah(ax, x, 7.82, x, 7.55, warna=warna, gaya=gaya)
        panah(ax, x, 6.89, x, 6.65, warna=warna, gaya=gaya)
        panah(ax, x, 5.99, x, 5.58, warna=warna, gaya=gaya)

    panah(ax, 4.4, 4.86, 4.4, 4.55)
    panah(ax, 11.6, 4.86, 11.6, 4.55)
    panah(ax, 4.4, 3.81, 6.2, 3.48)
    panah(ax, 11.6, 3.81, 9.8, 3.48)
    panah(ax, 8, 2.84, 8, 2.51)

    fig.tight_layout()
    REPORTS.mkdir(exist_ok=True)
    fig.savefig(REPORTS / "diagram_alur_pelabelan.png", dpi=300, bbox_inches="tight",
                facecolor="white")
    fig.savefig(REPORTS / "diagram_alur_pelabelan.svg", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("diagram:", (REPORTS / "diagram_alur_pelabelan.png").name)


def halaman_html() -> None:
    """Menulis halaman mandiri berisi diagram vektor."""
    svg = (REPORTS / "diagram_alur_pelabelan.svg").read_text(encoding="utf-8")
    svg = svg[svg.find("<svg"):]
    html = f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Diagram Pipeline Utama dan Pipeline Ablation Komprehensif</title>
<style>
  :root {{ --biru:#2f4f6f; --redup:#6b7a8d; --terang:#f4f6f9; --tinta:#1f2a37; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font:15px/1.6 "Segoe UI",system-ui,sans-serif; color:var(--tinta);
         background:#ffffff; }}
  main {{ max-width:1240px; margin:0 auto; padding:28px 20px 60px; }}
  h1 {{ font-size:21px; color:var(--biru); margin:0 0 6px; }}
  p.keterangan {{ color:var(--redup); margin:0 0 18px; }}
  figure {{ margin:0; padding:14px; border:1px solid var(--redup); border-radius:10px;
            background:var(--terang); overflow:auto; }}
  figure svg {{ width:100%; height:auto; background:#ffffff; }}
  figcaption {{ margin-top:12px; font-size:13px; color:var(--redup); }}
  ul {{ margin:16px 0 0; padding-left:20px; }}
  li {{ margin:5px 0; }}
  code {{ background:var(--terang); border:1px solid var(--redup); border-radius:4px;
          padding:1px 5px; font-size:13px; }}
</style>
</head>
<body>
<main>
  <h1>Pipeline Komprehensif: Preprocessing, Pelabelan, Pelatihan, hingga Evaluasi</h1>
  <p class="keterangan">Gambar 3.4 pada laporan Kerja Praktik. Diagram dibangkitkan dari kode
     <code>analisis/20_diagram_pelabelan.py</code>, memetakan alur hulu ke hilir secara utuh.</p>
  <figure>
    {svg}
    <figcaption>Sumber: hasil pengolahan data, 2026.</figcaption>
  </figure>
  <ul>
    <li>Tahap Preprocessing menyaring 10.961 rekaman mentah secara bertahap (tanggal, bahasa, topik, deduplikasi) hingga menghasilkan 8.352 baris korpus bersih.</li>
    <li>Pipeline utama memakai Gemma sebagai pemilah relevansi (5.808 opini) dan Jev sebagai anotator sentimen.</li>
    <li>Pipeline ablation memakai Jev sebagai pemilah langsung (ambang peluang 0,20) menghasilkan 5.590 opini latih.</li>
    <li>Keduanya dilatih pada IndoBERT dan diukur terhadap acuan gold set manusia yang sama: 0,7882 berbanding 0,7529, dengan uji berpasangan McNemar p = 0,5811 (perbedaan belum nyata secara statistik).</li>
    <li>Hasil akhir diverifikasi melalui teknik penjelasan model (peta atensi dan LIME) serta rekomendasi tematik bagi BPS.</li>
  </ul>
</main>
</body>
</html>
"""
    (REPORTS / "diagram_alur_pelabelan.html").write_text(html, encoding="utf-8")
    print("halaman:", (REPORTS / "diagram_alur_pelabelan.html").name)


if __name__ == "__main__":
    gambar()
    halaman_html()
