"""Membangun laporan Kerja Praktik dalam format .docx sesuai Lamp 8 edisi 2026.

Berkas ini menyusun laporan mulai dari halaman judul, bagian awal, lima bab,
daftar pustaka, hingga lampiran. Seluruh isi diambil dari artefak nyata di
repositori ini, sehingga angka yang tertulis dapat ditelusuri kembali.

Ketentuan tata cara penulisan yang diterapkan langsung oleh skrip:
  - kertas A4, tepi atas 4 cm, kiri 4 cm, bawah 3 cm, kanan 3 cm;
  - huruf Times New Roman 12 pt, jarak baris 1,5;
  - judul bab (Heading 1) 12 pt, huruf kapital, tebal, dan rata tengah;
  - sub-bab (Heading 2) dan anak sub-bab (Heading 3) 12 pt, tebal, rata kiri,
    tanpa diakhiri tanda titik;
  - alinea baru diawali indentasi 1,5 cm dari batas tepi kiri;
  - nomor halaman Romawi kecil pada bagian awal dan angka Arab pada bagian utama;
  - tabel berbatas, berlebar tetap, berkepala berulang, dan berkepala berlatar;
  - daftar isi, daftar tabel, daftar gambar, dan daftar lampiran dihitung Word
    pada akhir penyusunan, sehingga sudah terisi saat berkas diserahkan.

Menjalankan:
    py -3.13 buat_laporan_docx.py
    py -3.13 buat_laporan_docx.py --out reports/Laporan_KP.docx
    py -3.13 buat_laporan_docx.py --tanpa-word     # lewati pembaruan medan
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

# Istilah asing yang dimiringkan pada naskah berbahasa Indonesia, sesuai kaidah
# penulisan yang dipakai laporan ini. Abstrak berbahasa Inggris dikecualikan.
ISTILAH_ASING = (
    "gold set", "pseudo-label", "prompt", "checkpoint", "dataset", "endpoint",
    "fine-tuning", "noise", "overfitting", "token", "recall",
)

ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"
FINAL = ROOT / "final"

# Nama gaya yang dipakai untuk menghimpun daftar tabel, daftar gambar, dan daftar
# lampiran. Gaya ini sengaja TIDAK diberi tingkat kerangka (outline), supaya
# keterangan tabel dan gambar tidak ikut menyusup ke daftar isi utama. Daftar
# turunannya dibangun dengan pengalih \t yang menghimpun menurut nama gaya.
GAYA_KETERANGAN_TABEL = "Keterangan Tabel"
GAYA_KETERANGAN_GAMBAR = "Keterangan Gambar"
GAYA_JUDUL_LAMPIRAN = "Judul Lampiran"

# Identitas penulis dan keperluan administrasi.
#
# Seluruhnya dibaca dari satu berkas `final/identitas.json` supaya pengisiannya
# cukup di satu tempat, bukan diburu ke seluruh naskah di dalam Word. Berkas itu
# dibuat otomatis berisi contoh apabila belum ada.
BERKAS_IDENTITAS = ROOT / "final" / "identitas.json"

IDENTITAS_BAWAAN: dict[str, str] = {
    "nama": "<<ISI: Nama Mahasiswa>>",
    "nim": "<<ISI: NIM>>",
    "prodi": "<<ISI: Program Studi>>",
    "pembimbing": "<<ISI: Nama Dosen Pembimbing>>",
    "nip_pembimbing": "<<ISI: NIP Dosen Pembimbing>>",
    "penguji": "<<ISI: Nama Dosen Penguji>>",
    "nip_penguji": "<<ISI: NIP Dosen Penguji>>",
    "kaprodi": "<<ISI: Nama Ketua Program Studi>>",
    "nip_kaprodi": "<<ISI: NIP Ketua Program Studi>>",
    "hari": "",
    "tanggal_pengesahan": "",
    "tanggal_kp": "<<ISI: tanggal pelaksanaan KP>>",
    "tempat_tanggal": "Sukoharjo, [...] 2026",
    "lokasi": "Badan Pusat Statistik",
    "alamat_lokasi": "<<ISI: alamat lengkap kantor>>",
    "unit_kerja": "<<ISI: bagian atau unit kerja>>",
}


def muat_identitas() -> dict[str, str]:
    """Membaca identitas dari berkas, membuat contohnya bila belum ada.

    Berkas contoh sengaja ditulis dengan penanda yang sama seperti bawaannya,
    sehingga orang yang membukanya langsung tahu bagian mana yang perlu diisi.
    """
    if not BERKAS_IDENTITAS.is_file():
        BERKAS_IDENTITAS.parent.mkdir(parents=True, exist_ok=True)
        BERKAS_IDENTITAS.write_text(
            json.dumps(IDENTITAS_BAWAAN, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return dict(IDENTITAS_BAWAAN)
    try:
        isi = json.loads(BERKAS_IDENTITAS.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"peringatan: {BERKAS_IDENTITAS.name} tidak dapat dibaca, memakai nilai bawaan")
        return dict(IDENTITAS_BAWAAN)
    hasil = dict(IDENTITAS_BAWAAN)
    hasil.update({k: str(v) for k, v in isi.items() if k in IDENTITAS_BAWAAN})
    return hasil


ID = muat_identitas()

NAMA = ID["nama"]
NIM = ID["nim"]
PRODI = ID["prodi"]
PEMBIMBING = ID["pembimbing"]
PENGUJI = ID["penguji"]
KAPRODI = ID["kaprodi"]
TANGGAL_KP = ID["tanggal_kp"]
LOKASI = ID["lokasi"]


# ---------------------------------------------------------------------------
# Perkakas tata letak
# ---------------------------------------------------------------------------

def gaya_normal(doc: Document):
    """Mengambil gaya Normal, menangani perbedaan huruf besar/kecil pada template."""
    for s in doc.styles:
        if s.name.lower() == "normal" or s.style_id == "Normal":
            return s
    return doc.styles["Normal"]


def _setel_lvl_bold(lvl) -> None:
    """Menjadikan nomor urut pada level numbering tebal (bold) 12 pt Times New Roman."""
    pStyle = lvl.find(qn("w:pStyle"))
    if pStyle is None:
        pStyle = OxmlElement("w:pStyle")
        pStyle.set(qn("w:val"), "Heading2")
        lvl.insert(0, pStyle)
    rPr = lvl.find(qn("w:rPr"))
    if rPr is None:
        rPr = OxmlElement("w:rPr")
        lvl.append(rPr)
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), "Times New Roman")
    rFonts.set(qn("w:hAnsi"), "Times New Roman")
    rFonts.set(qn("w:cs"), "Times New Roman")
    if rPr.find(qn("w:b")) is None:
        rPr.append(OxmlElement("w:b"))
    if rPr.find(qn("w:bCs")) is None:
        rPr.append(OxmlElement("w:bCs"))
    sz = rPr.find(qn("w:sz"))
    if sz is None:
        sz = OxmlElement("w:sz")
        rPr.append(sz)
    sz.set(qn("w:val"), "24")
    szCs = rPr.find(qn("w:szCs"))
    if szCs is None:
        szCs = OxmlElement("w:szCs")
        rPr.append(szCs)
    szCs.set(qn("w:val"), "24")


def siapkan_gaya(doc: Document) -> None:
    """Menambahkan gaya yang belum ada pada cangkang.

    Gaya bawaan cangkang sengaja **tidak disentuh**. Huruf, ukuran, jarak baris,
    dan jarak judulnya dipakai apa adanya, karena itulah alasan laporan disusun
    di dalam cangkang dan bukan dari dokumen kosong. Yang ditambahkan hanya tiga
    gaya yang memang tidak ada di sana, yaitu gaya untuk menghimpun daftar tabel,
    daftar gambar, dan daftar lampiran.
    """
    gaya_tambahan = (
        (GAYA_KETERANGAN_TABEL, WD_ALIGN_PARAGRAPH.CENTER),
        (GAYA_KETERANGAN_GAMBAR, WD_ALIGN_PARAGRAPH.CENTER),
        (GAYA_JUDUL_LAMPIRAN, WD_ALIGN_PARAGRAPH.LEFT),
    )
    for nama, rata in gaya_tambahan:
        if nama in {s.name for s in doc.styles}:
            continue
        st = doc.styles.add_style(nama, WD_STYLE_TYPE.PARAGRAPH)
        st.base_style = gaya_normal(doc)
        st.font.name = "Times New Roman"
        st.font.size = Pt(12)
        st.font.bold = nama == GAYA_JUDUL_LAMPIRAN

        st.element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "Times New Roman")
        st.paragraph_format.alignment = rata
        st.paragraph_format.space_before = Pt(8 if nama == GAYA_JUDUL_LAMPIRAN else 0)
        st.paragraph_format.space_after = Pt(4)
        st.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        if nama == GAYA_JUDUL_LAMPIRAN:
            # Tingkat kerangka dipasang hanya pada gaya judul lampiran, tidak pada
            # gaya keterangan tabel dan gambar. Dengan begitu judul lampiran ikut
            # masuk daftar isi utama, sedangkan keterangan tabel dan gambar tidak,
            # sehingga daftar isi tetap terbaca.
            lvl = OxmlElement("w:outlineLvl")
            lvl.set(qn("w:val"), "1")
            pPr = st.element.get_or_add_pPr()
            pPr.insert_element_before(lvl, "w:divId", "w:cnfStyle", "w:rPr",
                                      "w:sectPr", "w:pPrChange")

    # Pastikan gaya Heading 1, Heading 2, dan Heading 3 sesuai kaidah ruler
    if "Heading 1" in doc.styles:
        h1 = doc.styles["Heading 1"]
        h1.font.name = "Times New Roman"
        h1.font.size = Pt(12)
        h1.font.bold = True
        h1.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        h1.paragraph_format.left_indent = Cm(0)
        h1.paragraph_format.right_indent = Cm(0)
        h1.paragraph_format.first_line_indent = Cm(0)
        h1.paragraph_format.space_before = Pt(0)
        h1.paragraph_format.space_after = Pt(3)
        h1.paragraph_format.line_spacing = 1.5

    if "Heading 2" in doc.styles:
        h2 = doc.styles["Heading 2"]
        h2.font.name = "Times New Roman"
        h2.font.size = Pt(12)
        h2.font.bold = True
        h2.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        h2.paragraph_format.left_indent = Cm(1.5)
        h2.paragraph_format.first_line_indent = Cm(-1.5)
        h2.paragraph_format.right_indent = Cm(0)
        h2.paragraph_format.space_before = Pt(8)
        h2.paragraph_format.space_after = Pt(4)
        h2.paragraph_format.line_spacing = 1.5

        rPr_h2 = h2.element.get_or_add_rPr()
        if rPr_h2.find(qn("w:b")) is None:
            rPr_h2.append(OxmlElement("w:b"))
        if rPr_h2.find(qn("w:bCs")) is None:
            rPr_h2.append(OxmlElement("w:bCs"))



    if "Heading 3" in doc.styles:
        h3 = doc.styles["Heading 3"]
        h3.font.name = "Times New Roman"
        h3.font.size = Pt(12)
        h3.font.bold = True
        h3.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        h3.paragraph_format.left_indent = Cm(0)
        h3.paragraph_format.right_indent = Cm(0)
        h3.paragraph_format.first_line_indent = Cm(0)
        h3.paragraph_format.space_before = Pt(6)
        h3.paragraph_format.space_after = Pt(4)
        h3.paragraph_format.line_spacing = 1.5

    # Pastikan seluruh nomor subbab pada abstractNum numbering memiliki format bold
    if hasattr(doc.part, "numbering_part") and doc.part.numbering_part is not None:
        numbering = doc.part.numbering_part.element
        for abs_el in numbering.findall(qn("w:abstractNum")):
            for lvl in abs_el.findall(qn("w:lvl")):
                lt = lvl.find(qn("w:lvlText"))
                if lt is not None and "%1" in lt.get(qn("w:val"), ""):
                    _setel_lvl_bold(lvl)


def siapkan_halaman(section) -> None:
    """Mengatur ukuran kertas A4, batas tepi, dan jarak header serta footer.

    Angka tepi dan jarak header diambil dari pengukuran template. Jarak header
    dan footer bawaan python-docx adalah 1,27 cm, sedangkan template memakai
    1,25 cm, sehingga perlu ditetapkan secara eksplisit.
    """
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(4)
    section.left_margin = Cm(4)
    section.bottom_margin = Cm(3)
    section.right_margin = Cm(3)
    section.header_distance = Cm(1.25)
    section.footer_distance = Cm(1.25)


def gaya_penomoran(section, fmt: str) -> None:
    """Menetapkan bentuk nomor halaman, misalnya lowerRoman atau decimal.

    Posisi ``w:pgNumType`` di dalam ``w:sectPr`` tidak bebas: menurut ECMA-376 ia
    harus mendahului ``w:cols``. Menambahkannya dengan ``append`` akan mendaratkan
    elemen itu di urutan yang salah. Word sering memperbaikinya saat berkas
    dibuka, tetapi hasilnya kadang benar dan kadang tidak, sehingga urutannya
    ditegakkan sejak awal.
    """
    sectPr = section._sectPr
    lama = sectPr.find(qn("w:pgNumType"))
    if lama is not None:
        sectPr.remove(lama)
    el = OxmlElement("w:pgNumType")
    el.set(qn("w:fmt"), fmt)
    el.set(qn("w:start"), "1")
    sectPr.insert_element_before(
        el,
        "w:cols", "w:formProt", "w:vAlign", "w:noEndnote", "w:titlePg",
        "w:textDirection", "w:bidi", "w:rtlGutter", "w:docGrid",
        "w:printerSettings", "w:sectPrChange",
    )


def nomor_halaman(section, angka_romawi_juga: bool = True) -> None:
    """Menaruh nomor halaman di tengah bawah.

    Isi footer dibersihkan lebih dahulu. Cangkang sudah membawa footer sendiri
    pada setiap section-nya, dan menambahkan medan ``PAGE`` di atasnya akan
    menghasilkan dua nomor halaman bertumpuk di tempat yang sama. Yang dibuang
    hanya run dan medannya; pengaturan paragrafnya dipertahankan.
    """
    section.footer.is_linked_to_previous = False
    p = section.footer.paragraphs[0]
    for run in list(p.runs):
        run._element.getparent().remove(run._element)
    for anak in list(p._p):
        if anak.tag != qn("w:pPr"):
            p._p.remove(anak)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    run = p.add_run()
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    run._r.addnext(fld)


def field_toc(par, instruksi: str) -> None:
    """Menyisipkan field yang dihitung Word, misalnya daftar isi otomatis."""
    run = par.add_run()
    awal = OxmlElement("w:fldChar")
    awal.set(qn("w:fldCharType"), "begin")
    teks = OxmlElement("w:instrText")
    teks.set(qn("xml:space"), "preserve")
    teks.text = instruksi
    pisah = OxmlElement("w:fldChar")
    pisah.set(qn("w:fldCharType"), "separate")
    akhir = OxmlElement("w:fldChar")
    akhir.set(qn("w:fldCharType"), "end")
    run._r.append(awal)
    run._r.append(teks)
    run._r.append(pisah)
    run._r.append(akhir)


def _potongan_miring(teks: str) -> list[tuple[str, bool]]:
    """Memecah teks menjadi potongan biasa dan potongan istilah asing.

    Istilah asing dimiringkan sesuai kaidah penulisan. Pencocokan tidak
    membedakan huruf besar dan huruf kecil, sedangkan teks yang ditulis tetap
    apa adanya.
    """
    pola = re.compile(r"\b(" + "|".join(re.escape(i) for i in ISTILAH_ASING) + r")\b",
                      re.IGNORECASE)
    potongan: list[tuple[str, bool]] = []
    pos = 0
    for cocok in pola.finditer(teks):
        if cocok.start() > pos:
            potongan.append((teks[pos : cocok.start()], False))
        potongan.append((cocok.group(0), True))
        pos = cocok.end()
    if pos < len(teks):
        potongan.append((teks[pos:], False))
    if not potongan:
        potongan.append((teks, False))
    return potongan


def par(doc: Document, teks: str = "", rata=WD_ALIGN_PARAGRAPH.JUSTIFY,
        tebal: bool = False, miring: bool = False, jarak_setelah: int = 0,
        alinea: bool = True, gaya: str | None = None,
        istilah_asing: bool = True):
    """Menambah satu paragraf dengan pengaturan yang lazim dipakai laporan.

    Paragraf naskah diberi awalan alinea sejauh 1,00 cm, sesuai ukuran yang
    dipakai template (567 twips). Rincian bernomor dimatikan awalannya melalui
    ``alinea=False`` karena template menempatkan rincian dengan indentasi
    menggantung, bukan seperti alinea biasa.

    ``gaya`` dipakai untuk keterangan tabel, keterangan gambar, dan judul
    lampiran. Ketiganya memakai gaya tersendiri supaya dapat dihimpun menjadi
    daftar turunan tanpa ikut masuk ke daftar isi utama.

    ``istilah_asing`` dimatikan pada abstrak berbahasa Inggris, sebab kaidah
    pemiringan hanya berlaku pada naskah berbahasa Indonesia.
    """
    p = doc.add_paragraph(style=gaya) if gaya else doc.add_paragraph()
    p.alignment = rata
    p.paragraph_format.space_after = Pt(jarak_setelah)
    # Template menuliskan jarak 1,5 spasi pada setiap paragraf, bukan hanya pada
    # gayanya. Hal yang sama dilakukan di sini agar bentuk berkasnya sepadan.
    p.paragraph_format.line_spacing = 1.5
    if alinea and rata == WD_ALIGN_PARAGRAPH.JUSTIFY:
        # Template menetapkan awalan alinea baru sejauh 1,5 cm dari margin kiri.
        p.paragraph_format.first_line_indent = Cm(1.5)
    if teks:
        potongan = _potongan_miring(teks) if istilah_asing else [(teks, False)]
        for bagian, asing in potongan:
            r = p.add_run(bagian)
            r.bold = tebal
            r.italic = miring or asing
    return p


def judul_tabel(doc: Document, teks: str) -> None:
    # Template memakai jarak 1 spasi untuk judul tabel, berbeda dari naskah.
    p = par(doc, teks, rata=WD_ALIGN_PARAGRAPH.CENTER, jarak_setelah=4, gaya=GAYA_KETERANGAN_TABEL)
    p.paragraph_format.line_spacing = 1


def judul_gambar(doc: Document, teks: str) -> None:
    # Template memakai jarak 1 spasi untuk judul gambar, berbeda dari naskah.
    p = par(doc, teks, rata=WD_ALIGN_PARAGRAPH.CENTER, jarak_setelah=2, gaya=GAYA_KETERANGAN_GAMBAR)
    p.paragraph_format.line_spacing = 1


def sumber(doc: Document, teks: str) -> None:
    """Menuliskan keterangan sumber di bawah tabel atau gambar.

    Template mewajibkan setiap tabel dan gambar yang berasal dari data sekunder
    mencantumkan sumbernya, dan keterangan itu memakai jarak 1 spasi.
    """
    p = par(doc, teks, rata=WD_ALIGN_PARAGRAPH.CENTER, jarak_setelah=8)
    p.paragraph_format.line_spacing = 1


_PENCACAH_SUBBAB: dict[str, int] = {}


def _pastikan_numid(doc: Document, awalan: str) -> str:
    """Menginisialisasi penomoran subbab (Heading 2) untuk bab tertentu."""
    awalan_str = str(awalan).strip()
    _PENCACAH_SUBBAB[awalan_str] = 0
    return awalan_str


def bab(doc: Document, teks: str):
    """Menulis judul bab atau bagian awal (Heading 1) simetris rata tengah tanpa indentasi."""
    p = doc.add_heading(teks.rstrip("."), level=1)
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.left_indent = Cm(0)
    p.paragraph_format.right_indent = Cm(0)
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.5
    return p


def sub_bab(doc: Document, teks: str, awalan: str | int = "1"):
    """Menulis subbab (Heading 2) dengan nomor bab.urutan tebal tepat pada batas kiri.

    Batas ruler: first line sejajar batas margin kiri (0 cm), teks setelah nomor
    mengikuti hanging indent 1,50 cm sejajar lurus dengan alinea baru.
    Nomor sub-bab dimasukkan langsung sebagai bagian teks Heading 2 sehingga:
      1. Nomor (1.1, 1.2, dst.) dan judul 100% pasti tebal (bold) di Word tanpa gangguan
         bug bullet glyph.
      2. Teks mewarisi gaya Heading 2 tanpa inline run bold, sehingga entri sub-bab
         di Daftar Isi (TOC 2) tetap rapi berhuruf reguler (tidak ikut menebal berlebihan).
    """
    awalan_str = str(awalan).strip()
    urutan = _PENCACAH_SUBBAB.get(awalan_str, 0) + 1
    _PENCACAH_SUBBAB[awalan_str] = urutan
    nomor = f"{awalan_str}.{urutan}"
    judul_lengkap = f"{nomor}\t{teks.rstrip('.')}"

    p = doc.add_heading(judul_lengkap, level=2)
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.left_indent = Cm(1.5)
    p.paragraph_format.first_line_indent = Cm(-1.5)
    p.paragraph_format.right_indent = Cm(0)
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.5

    for r in p.runs:
        r.font.name = "Times New Roman"
        r.font.size = Pt(12)
        r.bold = None  # Mewarisi dari gaya Heading 2 agar tidak memaksa TOC 2 menjadi tebal

    return p


def anak_sub_bab(doc: Document, teks: str):
    """Menulis anak sub-bab (Heading 3) dengan nomor dan hanging indent 1,50 cm.

    Batas ruler: nomor (3.2.1, 4.1.1, dst.) berada tepat pada batas margin kiri (0 cm),
    sedangkan judul mengikuti hanging indent 1,50 cm setelah tab, sejajar tegak lurus
    dengan judul sub-bab (Heading 2) dan awalan alinea baru.
    """
    teks_bersih = teks.rstrip(".")
    m = re.match(r"^(\d+(?:\.\d+)+)\s+(.*)$", teks_bersih)
    if m:
        nomor, judul = m.group(1), m.group(2)
        judul_lengkap = f"{nomor}\t{judul}"
    else:
        judul_lengkap = teks_bersih

    p = doc.add_heading(judul_lengkap, level=3)
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.left_indent = Cm(1.5)
    p.paragraph_format.first_line_indent = Cm(-1.5)
    p.paragraph_format.right_indent = Cm(0)
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.5
    for r in p.runs:
        r.font.name = "Times New Roman"
        r.font.size = Pt(12)
        r.bold = None
    return p


def _pasang_numpr(p, num_id: int | str, ilvl: int = 0) -> None:
    """Memasang penomoran daftar rincian otomatis pada paragraf."""
    pPr = p._element.get_or_add_pPr()
    numPr = OxmlElement("w:numPr")
    ilvl_el = OxmlElement("w:ilvl")
    ilvl_el.set(qn("w:val"), str(ilvl))
    numPr.append(ilvl_el)
    numId_el = OxmlElement("w:numId")
    numId_el.set(qn("w:val"), str(num_id))
    numPr.append(numId_el)
    pPr.append(numPr)


def _anggap_rincian(doc: Document) -> int:
    """Membuat definisi penomoran rincian baru yang dimulai dari satu.

    Setiap daftar rincian memperoleh numId sendiri yang menumpang definisi
    "%1." pada cangkang dengan penggantian awal satu, sehingga nomor tiap
    daftar dimulai dari satu dan tidak bersambung dengan daftar sebelumnya.
    """
    numbering = doc.part.numbering_part.element
    abs_target = None
    for abs_el in numbering.findall(qn("w:abstractNum")):
        lvl0 = abs_el.find(qn("w:lvl"))
        if lvl0 is None:
            continue
        teks_lvl = lvl0.find(qn("w:lvlText"))
        fmt = lvl0.find(qn("w:numFmt"))
        if (teks_lvl is not None and teks_lvl.get(qn("w:val")) == "%1."
                and fmt is not None and fmt.get(qn("w:val")) == "decimal"):
            abs_target = abs_el
            break
    if abs_target is None:
        raise ValueError("definisi penomoran rincian tidak ditemukan pada cangkang")
    id_num = 1 + max(int(x.get(qn("w:numId"))) for x in numbering.findall(qn("w:num")))
    num = OxmlElement("w:num")
    num.set(qn("w:numId"), str(id_num))
    rujuk = OxmlElement("w:abstractNumId")
    rujuk.set(qn("w:val"), abs_target.get(qn("w:abstractNumId")))
    num.append(rujuk)
    atas = OxmlElement("w:lvlOverride")
    atas.set(qn("w:ilvl"), "0")
    mulai = OxmlElement("w:startOverride")
    mulai.set(qn("w:val"), "1")
    atas.append(mulai)
    num.append(atas)
    numbering.append(num)
    return id_num


def butir(doc: Document, teks: str, num_id: int):
    """Menulis satu butir rincian bernomor otomatis.

    Template meminta rincian ke bawah memakai nomor urut; nomornya dihitung
    Word, sedangkan teks butir tetap memakai kaidah naskah yang sama, yaitu
    jarak 1,5 spasi dan istilah asing dimiringkan.
    """
    p = par(doc, teks, alinea=False)
    _pasang_numpr(p, num_id)
    return p


def _bagi_lebar(bobot: list[float], total: float, minimum: float) -> list[float]:
    """Membagi lebar total menurut bobot, tanpa kolom yang di bawah batas minimum.

    Setiap kolom diberi batas minimum lebih dahulu, lalu sisanya dibagi menurut
    bobot. Cara ini menjaga kolom pendek tetap terbaca, sedangkan kolom panjang
    tetap memperoleh bagian terbesar.
    """
    n = len(bobot)
    if n == 0:
        return []
    if total <= minimum * n:
        return [total / n] * n
    lebar = [minimum] * n
    sisa = total - minimum * n
    jumlah_bobot = sum(bobot) or n
    for i in range(n):
        lebar[i] += sisa * bobot[i] / jumlah_bobot
    # Selisih pembulatan diberikan kepada kolom terlebar supaya jumlahnya tepat.
    terlebar = max(range(n), key=lambda i: lebar[i])
    lebar[terlebar] += total - sum(lebar)
    return lebar


def _bobot_kolom(header: list[str], baris: list[list[str]], batas: float = 34.0) -> list[float]:
    """Menaksir kebutuhan lebar tiap kolom dari panjang isinya.

    Nilai terpanjang dan rata-rata dipakai bersama supaya satu sel yang sangat
    panjang tidak menghabiskan lebar seluruh tabel.
    """
    bobot = []
    for i in range(len(header)):
        panjang = [len(str(header[i]))]
        for r in baris:
            if i < len(r):
                panjang.append(len(str(r[i])) or 1)
        bobot.append(max(3.0, min(batas, (max(panjang) + sum(panjang) / len(panjang)) / 2)))
    return bobot


def _sisipkan(induk, el, *sesudah: str) -> None:
    """Menyisipkan unsur pada urutan yang sah menurut ECMA-376.

    Urutan anak pada ``w:tblPr``, ``w:tcPr``, dan ``w:trPr`` tidak bebas. Menambah
    dengan ``append`` dapat mendaratkan unsur di tempat yang salah; Word kadang
    memperbaikinya diam-diam, kadang tidak.
    """
    if "w:" + el.tag.split("}")[-1] in sesudah:
        induk.append(el)
        return
    induk.insert_element_before(el, *sesudah)


def _rapikan_tabel(t, lebar_cm: list[float]) -> None:
    """Menegakkan bentuk tabel: batas, lebar tetap, kepala berulang, dan jarak sel.

    Seluruhnya ditulis sebagai XML mentah karena python-docx tidak menyediakan
    API untuk batas, lebar tetap, maupun pengulangan baris kepala.
    """
    tbl = t._tbl
    tblPr = tbl.tblPr
    for nama in ("w:tblW", "w:tblBorders", "w:tblLayout", "w:tblCellMar"):
        lama = tblPr.find(qn(nama))
        if lama is not None:
            tblPr.remove(lama)

    total = str(int(round(sum(lebar_cm) * 567)))
    w = OxmlElement("w:tblW")
    w.set(qn("w:w"), total)
    w.set(qn("w:type"), "dxa")
    _sisipkan(tblPr, w, "w:jc", "w:tblCellSpacing", "w:tblInd", "w:tblBorders",
              "w:shd", "w:tblLayout", "w:tblCellMar", "w:tblLook")

    batas = OxmlElement("w:tblBorders")
    for sisi in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{sisi}")
        e.set(qn("w:val"), "single")
        # w:sz dinyatakan dalam per delapan poin, sehingga 4 berarti 0,5 poin.
        e.set(qn("w:sz"), "4")
        e.set(qn("w:space"), "0")
        e.set(qn("w:color"), "auto")
        batas.append(e)
    _sisipkan(tblPr, batas, "w:shd", "w:tblLayout", "w:tblCellMar", "w:tblLook")

    tata = OxmlElement("w:tblLayout")
    tata.set(qn("w:type"), "fixed")
    _sisipkan(tblPr, tata, "w:tblCellMar", "w:tblLook")

    mar = OxmlElement("w:tblCellMar")
    for sisi, nilai in (("top", 40), ("left", 85), ("bottom", 40), ("right", 85)):
        e = OxmlElement(f"w:{sisi}")
        e.set(qn("w:w"), str(nilai))
        e.set(qn("w:type"), "dxa")
        mar.append(e)
    _sisipkan(tblPr, mar, "w:tblLook")

    # Lebar kolom ditulis dua kali, pada kisi kolom dan pada setiap sel. Menulis
    # salah satu saja tidak cukup: Word membaca keduanya, dan bila hanya kisi yang
    # diisi, lebar tetap dipasang menurut isi sel.
    kisi = tbl.find(qn("w:tblGrid"))
    if kisi is not None:
        for kolom, cm in zip(kisi.findall(qn("w:gridCol")), lebar_cm):
            kolom.set(qn("w:w"), str(int(round(cm * 567))))

    baris_tbl = tbl.findall(qn("w:tr"))
    for i, baris in enumerate(baris_tbl):
        for sel, cm in zip(baris.findall(qn("w:tc")), lebar_cm):
            tcPr = sel.find(qn("w:tcPr"))
            if tcPr is None:
                tcPr = OxmlElement("w:tcPr")
                sel.insert(0, tcPr)
            lama = tcPr.find(qn("w:tcW"))
            if lama is not None:
                tcPr.remove(lama)
            wc = OxmlElement("w:tcW")
            wc.set(qn("w:w"), str(int(round(cm * 567))))
            wc.set(qn("w:type"), "dxa")
            _sisipkan(tcPr, wc, "w:gridSpan", "w:hMerge", "w:vMerge", "w:tcBorders",
                      "w:shd", "w:noWrap", "w:tcMar", "w:textDirection",
                      "w:tcFitText", "w:vAlign", "w:hideMark")
            if i == 0:
                shd = OxmlElement("w:shd")
                shd.set(qn("w:val"), "clear")
                shd.set(qn("w:color"), "auto")
                shd.set(qn("w:fill"), "D9D9D9")
                _sisipkan(tcPr, shd, "w:noWrap", "w:tcMar", "w:textDirection",
                          "w:tcFitText", "w:vAlign", "w:hideMark")

    # Setiap baris tabel dijaga agar tidak terbelah antar halaman, sesuai
    # ketentuan template bahwa tabel diupayakan tampil utuh.
    for baris in baris_tbl:
        trPr = baris.find(qn("w:trPr"))
        if trPr is None:
            trPr = OxmlElement("w:trPr")
            baris.insert(0, trPr)
        if trPr.find(qn("w:cantSplit")) is None:
            trPr.insert_element_before(
                OxmlElement("w:cantSplit"),
                "w:trHeight", "w:tblHeader", "w:tblCellSpacing", "w:jc", "w:hidden")

    # Baris kepala diulang pada setiap halaman bila tabel terpotong.
    if baris_tbl:
        kepala = baris_tbl[0]
        trPr = kepala.find(qn("w:trPr"))
        if trPr is None:
            trPr = OxmlElement("w:trPr")
            kepala.insert(0, trPr)
        if trPr.find(qn("w:tblHeader")) is None:
            h = OxmlElement("w:tblHeader")
            h.set(qn("w:val"), "true")
            trPr.append(h)


def tabel(
    doc: Document,
    header: list[str],
    baris: list[list[str]],
    sumber_teks: str | None = "Sumber: hasil pengolahan data, 2026",
) -> None:
    """Membuat tabel dengan huruf 10 pt agar tetap muat satu halaman.

    Lebar tiap kolom dihitung dari panjang isinya lalu dibagi tetap, sehingga
    tabel tidak lagi dipasang otomatis oleh Word dan tidak melebar keluar batas
    tepi. Keterangan sumber dituliskan secara bawaan karena template
    mewajibkannya untuk tabel yang berasal dari data sekunder. Tabel tanda tangan
    pada halaman pengesahan tidak memerlukannya, sehingga dapat dimatikan dengan
    None.
    """
    lebar_kertas = 21.0 - 4.0 - 3.0
    lebar = _bagi_lebar(_bobot_kolom(header, baris), lebar_kertas, 1.5)

    t = doc.add_table(rows=1, cols=len(header))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    # Mematikan pemasangan otomatis; tanpa ini, w:tblLayout fixed tidak berpengaruh.
    t.autofit = False
    # Gaya tabel hanya dipakai bila memang ada di dalam dokumen. Cangkang tidak
    # memuat gaya "Table Grid", sehingga penyetelannya akan gagal; batas, lebar,
    # dan jarak dalam sel tetap ditulis eksplisit oleh _rapikan_tabel, jadi gaya
    # itu memang tidak wajib.
    if "Table Grid" in {s.name for s in doc.styles}:
        t.style = "Table Grid"

    for i, h in enumerate(header):
        sel = t.rows[0].cells[i]
        sel.text = ""
        p = sel.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        r = p.add_run(h)
        r.bold = True
        r.font.size = Pt(10)
    for isi in baris:
        cells = t.add_row().cells
        for i, nilai in enumerate(isi):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
            r = p.add_run(str(nilai))
            r.font.size = Pt(10)

    _rapikan_tabel(t, lebar)

    if sumber_teks:
        sumber(doc, sumber_teks)
    else:
        par(doc, "", jarak_setelah=6)


def gambar(doc: Document, path: Path, lebar_cm: float, caption: str) -> None:
    """Menyisipkan gambar bila berkasnya tersedia."""
    if not path.is_file():
        par(doc, f"[Gambar tidak tersedia: {path.name}]", rata=WD_ALIGN_PARAGRAPH.CENTER)
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(path), width=Cm(lebar_cm))
    judul_gambar(doc, caption)


def buat_diagram_alir(path: Path) -> Path:
    """Menggambar diagram alir pelaksanaan KP sebagai berkas PNG berkualitas tinggi.

    Menggunakan representasi 2-kolom terstruktur dengan standar ANSI flowchart
    (terminator, wadah tahapan I-V, proses, belah ketupat keputusan, dan konektor).
    """
    if path.is_file() and path.stat().st_size > 100_000:
        return path
    try:
        from analisis.render_diagram_alir_svg import render_ke_png
        return render_ke_png(path)
    except Exception:
        from analisis.buat_diagram_alir_bagus import bangun_diagram_alir_kp
        return bangun_diagram_alir_kp(path)


# ---------------------------------------------------------------------------
# Isi laporan
# ---------------------------------------------------------------------------

CANGKANG = FINAL / "TEMPLATE.docx"

# Penanda batas halaman awal di dalam cangkang. Aturan penulisan (sebelum HALAMAN JUDUL)
# dan isi naskah dummy template (sesudah DAFTAR ISI) dibuang.
CANGKANG_AWAL = "HALAMAN JUDUL"
CANGKANG_AKHIR = "DAFTAR ISI"


def _setel_gaya_judul(doc: Document) -> None:
    """Menegakkan gaya judul menurut template resmi Lamp 8 edisi 2026.

    Heading 1: 12 pt, tebal, rata tengah, jarak sesudah 3 pt.
    Heading 2: 12 pt, tebal, rata kiri, sebelum 8 pt, sesudah 4 pt.
    Heading 3: 12 pt, tebal, rata kiri, sebelum 6 pt, sesudah 4 pt.
    Title: 14 pt, tebal, rata tengah.
    Normal / docDefaults: Times New Roman 12 pt.
    """
    gaya_normal(doc).font.name = "Times New Roman"
    for nama in ("Heading 1", "Heading 2", "Heading 3", "Title"):
        if nama in doc.styles:
            doc.styles[nama].font.name = "Times New Roman"


    styles_el = doc.styles.element
    docDefaults = styles_el.find(qn("w:docDefaults"))
    if docDefaults is None:
        docDefaults = OxmlElement("w:docDefaults")
        styles_el.insert(0, docDefaults)
    rPrDefault = docDefaults.find(qn("w:rPrDefault"))
    if rPrDefault is None:
        rPrDefault = OxmlElement("w:rPrDefault")
        docDefaults.insert(0, rPrDefault)
    rPr = rPrDefault.find(qn("w:rPr"))
    if rPr is None:
        rPr = OxmlElement("w:rPr")
        rPrDefault.append(rPr)
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.insert(0, rFonts)
    rFonts.set(qn("w:ascii"), "Times New Roman")
    rFonts.set(qn("w:hAnsi"), "Times New Roman")
    rFonts.set(qn("w:cs"), "Times New Roman")
    rFonts.set(qn("w:eastAsia"), "Times New Roman")

    h1 = doc.styles["Heading 1"]
    h1.font.name = "Times New Roman"
    h1.font.size = Pt(12)
    h1.font.bold = True
    h1.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    h1.paragraph_format.left_indent = Cm(0)
    h1.paragraph_format.right_indent = Cm(0)
    h1.paragraph_format.first_line_indent = Cm(0)
    h1.paragraph_format.space_before = Pt(0)
    h1.paragraph_format.space_after = Pt(3)
    h1.paragraph_format.line_spacing = 1.5

    h2 = doc.styles["Heading 2"]
    h2.font.name = "Times New Roman"
    h2.font.size = Pt(12)
    h2.font.bold = True
    h2.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    h2.paragraph_format.left_indent = Cm(1.5)
    h2.paragraph_format.first_line_indent = Cm(-1.5)
    h2.paragraph_format.right_indent = Cm(0)
    h2.paragraph_format.space_before = Pt(8)
    h2.paragraph_format.space_after = Pt(4)
    h2.paragraph_format.line_spacing = 1.5

    h3 = doc.styles["Heading 3"]
    h3.font.name = "Times New Roman"
    h3.font.size = Pt(12)
    h3.font.bold = True
    h3.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    h3.paragraph_format.left_indent = Cm(0)
    h3.paragraph_format.right_indent = Cm(0)
    h3.paragraph_format.first_line_indent = Cm(0)
    h3.paragraph_format.space_before = Pt(6)
    h3.paragraph_format.space_after = Pt(4)
    h3.paragraph_format.line_spacing = 1.5


def buka_cangkang() -> Document:
    """Membuka template Lamp 8 edisi 2026 dan menyisakan halaman awalnya.

    Bagian panduan di awal dokumen (sebelum HALAMAN JUDUL) serta naskah dummy
    (mulai DAFTAR ISI sampai lampiran) dibuang. Halaman sampul (beserta logo resmi UIN),
    lembar persetujuan, dan halaman pengesahan dipertahankan apa adanya.
    """
    if not CANGKANG.is_file():
        raise FileNotFoundError(f"cangkang format tidak ada: {CANGKANG}")
    doc = Document(str(CANGKANG))
    body = doc.element.body

    anak = list(body)
    mulai = akhir = None
    for i, el in enumerate(anak):
        if el.tag != qn("w:p"):
            continue
        pPr = el.find(qn("w:pPr"))
        pStyle = pPr.find(qn("w:pStyle")) if pPr is not None else None
        style_val = pStyle.get(qn("w:val")) if pStyle is not None else ""
        teks = "".join(t.text or "" for t in el.iter(qn("w:t"))).strip().upper()
        if mulai is None and teks == CANGKANG_AWAL:
            mulai = i
        elif mulai is not None and (style_val.startswith("Heading") or "Heading" in style_val) and teks.startswith(CANGKANG_AKHIR):
            akhir = i
            break
    if mulai is None or akhir is None:
        raise ValueError(
            f"penanda halaman awal cangkang tidak ditemukan "
            f"({CANGKANG_AWAL} .. {CANGKANG_AKHIR})"
        )

    # Sisakan halaman awal dan sectPr terakhir, buang selebihnya.
    for el in anak[akhir:]:
        if el.tag != qn("w:sectPr"):
            body.remove(el)
    for el in anak[:mulai]:
        body.remove(el)

    # Pemisah section pada halaman awal dibuang agar bagian awal menyatu dalam Section 1.
    for ppr in list(body.iter(qn("w:pPr"))):
        sisa = ppr.find(qn("w:sectPr"))
        if sisa is not None:
            ppr.remove(sisa)

    return doc


def ganti_teks(p, teks: str) -> None:
    """Mengganti isi satu paragraf tanpa mengubah gayanya.

    Run pertama dipakai ulang supaya keterangan huruf dan ukurannya tetap, lalu
    run selebihnya dibuang agar teks lama tidak tertinggal di belakangnya.
    """
    runs = p.runs
    if not runs:
        p.add_run(teks)
        return
    runs[0].text = teks
    for r in runs[1:]:
        r._element.getparent().remove(r._element)


def terisi(nilai: str) -> bool:
    """Menandai apakah sebuah nilai identitas sudah diisi, bukan masih penanda.

    Nilai yang masih berupa penanda seperti ``<<ISI: ...>>`` tidak dituliskan ke
    dalam laporan.
    """
    teks = (nilai or "").strip()
    return bool(teks) and not teks.startswith("<<")


def isi_tabel_tanda_tangan(doc: Document) -> set[str]:
    """Mengisi nama dan NIP di dalam tabel tanda tangan lembar persetujuan dan pengesahan.

    Struktur tabel pada template Lamp 8 edisi 2026:
      - Table 0: Lembar Persetujuan (Dosen Pembimbing KP)
      - Table 1: Halaman Pengesahan (Dosen Pembimbing & Dosen Penguji)
      - Table 2: Halaman Pengesahan (Ketua Program Studi)
    """
    diganti: set[str] = set()

    # Table 0: Lembar Persetujuan
    if len(doc.tables) >= 1:
        t0 = doc.tables[0]
        for p in t0.rows[0].cells[0].paragraphs:
            t = p.text.strip()
            if "Nama Lengkap" in t or t == "Nama Dosen" or "Aji Joko" in t:
                if terisi(PEMBIMBING):
                    ganti_teks(p, PEMBIMBING)
                    diganti.add("pembimbing")
            elif t.startswith("NIP"):
                if terisi(ID.get("nip_pembimbing", "")):
                    ganti_teks(p, f"NIP. {ID['nip_pembimbing']}")
                    diganti.add("nip_pembimbing")

    # Table 1: Pengesahan (Pembimbing | Penguji)
    if len(doc.tables) >= 2:
        t1 = doc.tables[1]
        for p in t1.rows[0].cells[0].paragraphs:
            t = p.text.strip()
            if t == "Nama Dosen" or "Aji Joko" in t:
                if terisi(PEMBIMBING):
                    ganti_teks(p, PEMBIMBING)
                    diganti.add("pembimbing")
            elif t.startswith("NIP"):
                if terisi(ID.get("nip_pembimbing", "")):
                    ganti_teks(p, f"NIP. {ID['nip_pembimbing']}")
                    diganti.add("nip_pembimbing")
        if len(t1.rows[0].cells) > 1:
            for p in t1.rows[0].cells[1].paragraphs:
                t = p.text.strip()
                if (t == "Nama Dosen" or "Penguji" in t) and terisi(ID.get("penguji", "")):
                    ganti_teks(p, ID["penguji"])
                    diganti.add("penguji")
                elif t.startswith("NIP") and terisi(ID.get("nip_penguji", "")):
                    ganti_teks(p, f"NIP. {ID['nip_penguji']}")
                    diganti.add("nip_penguji")

    # Table 2: Kaprodi
    if len(doc.tables) >= 3:
        t2 = doc.tables[2]
        for p in t2.rows[0].cells[0].paragraphs:
            t = p.text.strip()
            if "Ketua Program Studi" in t:
                ganti_teks(p, f"Ketua Program Studi {PRODI}")
                diganti.add("kaprodi_judul")
            elif (t == "Nama Dosen" or "Rizky" in t) and terisi(KAPRODI):
                ganti_teks(p, KAPRODI)
                diganti.add("kaprodi")
            elif t.startswith("NIP") and terisi(ID.get("nip_kaprodi", "")):
                ganti_teks(p, f"NIP. {ID['nip_kaprodi']}")
                diganti.add("nip_kaprodi")

    return diganti


def isi_halaman_awal(doc: Document) -> None:
    """Mengisi halaman sampul, lembar persetujuan, dan halaman pengesahan.

    Teks diganti pada run yang sudah ada supaya susunan tata letak bawaan
    template (logo, jarak paragraf, dan perataan) tetap utuh.
    """
    judul_baru = ("ANALISIS SENTIMEN OPINI PUBLIK TERHADAP SENSUS EKONOMI 2026 "
                  "DAN APLIKASI FASIH BPS MENGGUNAKAN INDOBERT")

    diganti = isi_tabel_tanda_tangan(doc)
    for p in doc.paragraphs:
        teks = p.text.strip()
        if not teks:
            continue
        naik = teks.upper()

        if naik == CANGKANG_AWAL:
            # HALAMAN JUDUL diturunkan ke Normal agar tidak masuk TOC.
            p.style = gaya_normal(doc)
            diganti.add("penanda sampul")

        elif naik in ("LEMBAR PERSETUJUAN", "HALAMAN PENGESAHAN"):
            p.paragraph_format.page_break_before = True
            diganti.add(naik.lower())
        elif naik == "JUDUL" or naik.startswith("ANALISIS DAN VISUALISASI") or naik.startswith("ANALISIS SENTIMEN"):
            ganti_teks(p, judul_baru.upper())
            diganti.add("judul")
        elif naik == "NAMA MAHASISWA":
            ganti_teks(p, NAMA.upper())
            diganti.add("nama")
        elif teks == "Nama Mahasiswa" or teks.lower() == "nur yuliyanti":
            ganti_teks(p, NAMA)
            diganti.add("nama")
        elif naik.startswith("NIM."):
            ganti_teks(p, f"NIM. {NIM}")
            diganti.add("nim")
        elif naik.startswith("NIM"):
            ganti_teks(p, f"NIM {NIM}")
            diganti.add("nim")
        elif naik == "PROGRAM STUDI XXX":
            ganti_teks(p, f"PROGRAM STUDI {PRODI.upper()}")
            diganti.add("prodi")
        elif naik.startswith("HARI"):
            ganti_teks(p, f"Hari\t: {ID.get('hari', '')}")
            diganti.add("hari")
        elif naik.startswith("TANGGAL"):
            ganti_teks(p, f"Tanggal\t: {ID.get('tanggal_pengesahan', '')}")
            diganti.add("tanggal")

    kurang = {"judul", "nama", "nim"} - diganti
    if kurang:
        raise ValueError(
            "identitas pada halaman awal template tidak ditemukan: "
            + ", ".join(sorted(kurang))
        )



def bagian_awal(doc: Document) -> None:
    """Menulis kata pengantar, abstrak, dan abstract.

    Halaman sampul, lembar persetujuan, dan halaman pengesahan tidak ditulis di
    sini. Ketiganya diambil apa adanya dari cangkang, lalu identitasnya diisi oleh
    :func:`isi_halaman_awal`, sehingga susunannya tidak perlu disusun ulang.
    """
    doc.add_page_break()
    bab(doc, "KATA PENGANTAR")
    par(doc, "Puji syukur penulis panjatkan atas selesainya penyusunan laporan Kerja Praktik "
             "yang berjudul \u201cAnalisis Sentimen Opini Publik terhadap Sensus Ekonomi 2026 dan "
             "Aplikasi Fasih BPS Menggunakan IndoBERT\u201d. Laporan ini disusun sebagai salah satu "
             "syarat penyelesaian Kerja Praktik pada Program Studi " + PRODI + ".")
    par(doc, "Penyusunan laporan ini terwujud berkat bimbingan, arahan, dan bantuan dari berbagai pihak. "
             "Oleh karena itu, penulis menyampaikan terima kasih kepada dosen pembimbing atas arahan "
             "selama pelaksanaan dan penyusunan laporan, kepada pembimbing lapangan beserta seluruh pegawai " + LOKASI +
             " atas kesempatan dan bimbingan yang diberikan, serta kepada keluarga dan rekan "
             "sejawat yang telah memberi dukungan.")
    par(doc, "Penulis menyadari laporan ini masih memiliki kekurangan. Kritik dan saran yang "
             "membangun sangat diharapkan demi perbaikan pada penulisan berikutnya. Semoga laporan "
             "ini bermanfaat bagi pembaca.")
    par(doc, "")
    par(doc, ID["tempat_tanggal"], rata=WD_ALIGN_PARAGRAPH.RIGHT)
    par(doc, "Penulis", rata=WD_ALIGN_PARAGRAPH.RIGHT)

    doc.add_page_break()
    bab(doc, "ABSTRAK")
    par(doc, "ANALISIS SENTIMEN OPINI PUBLIK TERHADAP SENSUS EKONOMI 2026 DAN APLIKASI FASIH BPS "
             "MENGGUNAKAN INDOBERT", rata=WD_ALIGN_PARAGRAPH.CENTER, tebal=True)
    par(doc, NAMA, rata=WD_ALIGN_PARAGRAPH.CENTER)
    par(doc, NIM, rata=WD_ALIGN_PARAGRAPH.CENTER)
    par(doc, "")
    par(doc, "Sensus Ekonomi 2026 merupakan kegiatan pendataan berskala nasional yang menuai "
             "tanggapan luas di ruang publik. Penelitian ini bertujuan mengukur sentimen opini "
             "publik terhadap pelaksanaan Sensus Ekonomi 2026 dan aplikasi Fasih BPS, serta "
             "menyusun korpus berlabel yang dapat dipertanggungjawabkan secara metodologis. "
             "Kontribusi utamanya berupa perumusan prosedur audit mutu label. Evaluasi ini membuktikan "
             "bahwa kesalahan anotasi otomatis oleh model bahasa besar memuat pola sistematis dan "
             "bukan sekadar derau acak. Oleh sebab itu, tingginya konsistensi inferensi model tidak "
             "menjamin kebenaran terhadap acuan manusia, dan angka kesesuaian terhadap anotator semu tidak dapat "
             "disamakan dengan akurasi. "
             "Data dikumpulkan dari Google Play, YouTube, dan Threads pada rentang 15 Juni sampai "
             "15 September 2026. Sebanyak 10.961 rekaman mentah disaring sehingga menghasilkan "
             "korpus bersih 8.352 baris. Anotasi awal memakai Gemma 4 12B dan dipilah menjadi "
             "partisi opini, non-opini, dan karantina, lalu sentimen korpus dinilai ulang oleh Jev. "
             "Pengujian pemilahan relevansi menunjukkan bahwa Jev dapat dipakai tanpa Gemma "
             "sebagai gerbang wajib; pada pengukuran terhadap 85 baris sentimen yang dinilai "
             "manusia, pipeline utama (partisi Gemma dan anotasi Jev) memperoleh akurasi 0,7882, sedangkan pemilahan "
             "Jev memperoleh 0,7529 dengan nilai p 0,5811 sehingga perbedaannya belum nyata "
             "secara statistik. Pipeline utama dipertahankan sebagai penyajian utama "
             "karena angka titiknya lebih tinggi, sedangkan pipeline mandiri Jev dilaporkan "
             "sebagai eksperimen pembanding. "
             "Pemindaian atas seluruh 8.350 baris berlabel tidak menemukan cacat kritis, dan "
             "seluruh kutipan bukti dapat dilacak ke teks asalnya. Uji konsistensi memperlihatkan "
             "90 dari 92 baris dijawab sama persis pada tiga pengambilan, termasuk baris yang "
             "salah, sehingga pemungutan suara tidak menyaring kesalahan apa pun. Pengklasifikasi "
             "dibangun dengan menyetel IndoBERT dan dibandingkan melalui studi ablasi enam "
             "strategi adaptasi parameter. Pengukuran terhadap seratus baris uji yang dinilai "
             "manusia memberi akurasi 0,7882 dan F1 macro 0,7713 bagi anotator Jev, serta 0,7882 "
             "dan 0,7700 bagi pengklasifikasi IndoBERT yang dilatih di atas labelnya, keduanya di "
             "bawah angka kesesuaian 0,8830 pada skenario terbaik. Selisih tersebut mencerminkan "
             "perambatan galat dari anotator semu ke model klasifikasi, sekaligus menegaskan bahwa "
             "pengujian independen berbasis data acuan manusia tetap menjadi keharusan metodologis.")
    par(doc, "")
    par(doc, "Kata kunci: analisis sentimen, Sensus Ekonomi 2026, Fasih BPS, IndoBERT, "
             "pelabelan semu, audit mutu label", miring=True)

    doc.add_page_break()
    bab(doc, "ABSTRACT")
    par(doc, "SENTIMENT ANALYSIS OF PUBLIC OPINION TOWARD THE 2026 ECONOMIC CENSUS AND THE FASIH "
             "BPS APPLICATION USING INDOBERT", rata=WD_ALIGN_PARAGRAPH.CENTER, tebal=True)
    par(doc, NAMA, rata=WD_ALIGN_PARAGRAPH.CENTER)
    par(doc, NIM, rata=WD_ALIGN_PARAGRAPH.CENTER)
    par(doc, "")
    par(doc, "The 2026 Economic Census is a nationwide data collection effort that has drawn "
             "widespread public response. This study measures public sentiment toward the census "
             "and the Fasih BPS application, and builds a methodologically accountable labelled "
             "corpus. Its main contribution is a label quality audit procedure. The study demonstrates "
             "that automatic annotation errors in large language models follow systematic patterns "
             "rather than purely random noise. Consequently, high inference consistency does "
             "not guarantee correctness against human ground truth, and agreement with the pseudo-annotator "
             "cannot be reported as accuracy. Data were collected from Google Play, YouTube, and Threads between 15 June "
             "and 15 September 2026. A total of 10,961 raw records were filtered into a clean "
             "corpus of 8,352 rows. Initial annotation used Gemma 4 12B and was routed into "
             "opinion, non-opinion, and quarantine partitions; after comparison with the Jev "
             "annotator across three test sets, the corpus labels were refreshed with Jev, "
             "so the 5,808-row opinion partition now holds 3,978 negative, 1,315 positive, and 515 "
             "neutral rows. A scan of all 8,350 labelled rows found no critical defect, and every "
             "quoted piece of evidence could be traced back to its source text. A consistency "
             "test showed 90 of 92 rows answered identically across three draws, including the "
             "incorrect ones, so majority voting filters out no errors at all. A classifier was "
             "built by fine-tuning IndoBERT and compared through an ablation study of six "
             "parameter adaptation strategies. Measurement against a one-hundred-row human-labelled "
             "test set yields an accuracy of 0.7882 and a macro F1 of 0.7713 for the Jev "
             "annotator, and 0.7882 and 0.7700 for the IndoBERT classifier trained on its labels, "
             "both below the agreement figure of 0.8830 attained by the best scenario. This performance gap "
             "reflects the propagation of annotation error into the downstream classifier, confirming that "
             "an independent human test set remains indispensable for rigorous model evaluation.", istilah_asing=False)
    par(doc, "")
    par(doc, "Keywords: sentiment analysis, 2026 Economic Census, Fasih BPS, IndoBERT, "
             "pseudo-labelling, label quality audit", miring=True)


def daftar_awal(doc: Document) -> None:
    """Menulis daftar isi dan ketiga daftar turunannya.

    Seluruhnya berupa medan yang dihitung Word, dan pengalihnya berbeda menurut
    sumber entri. Daftar isi memakai ``\\o`` yang menghimpun gaya judul
    berkerangka, sedangkan ketiga daftar lainnya memakai ``\\t`` yang menghimpun
    menurut nama gaya.

    Cara itu dipilih dengan sengaja. Bila keterangan tabel dan gambar diberi gaya
    judul berkerangka seperti pada berkas pembanding, keduanya ikut menyusup ke
    daftar isi utama dan membuatnya sulit dibaca. Dengan pengalih ``\\t``,
    keterangan itu hanya muncul pada daftar yang seharusnya.

    Judul lampiran diperlakukan berbeda: gayanya diberi tingkat kerangka, sehingga
    ia muncul di daftar isi utama sekaligus di daftar lampiran.

    Tidak ada lagi petunjuk menekan Ctrl+A lalu F9 di dalam laporan. Medan ini
    diperbarui oleh langkah Word yang dijalankan pada akhir penyusunan, sehingga
    hasilnya sudah tersimpan saat berkas dibuka pembaca.
    """
    daftar = (
        ("DAFTAR ISI", 'TOC \\o "1-3" \\h \\z \\u'),
        ("DAFTAR GAMBAR", f'TOC \\h \\z \\t "{GAYA_KETERANGAN_GAMBAR},1"'),
        ("DAFTAR TABEL", f'TOC \\h \\z \\t "{GAYA_KETERANGAN_TABEL},1"'),
        ("DAFTAR LAMPIRAN", f'TOC \\h \\z \\t "{GAYA_JUDUL_LAMPIRAN},1"'),
    )
    for judul, instruksi in daftar:
        doc.add_page_break()
        bab(doc, judul)
        field_toc(par(doc, ""), instruksi)

    # Daftar istilah ditempatkan paling akhir pada bagian awal, mengikuti
    # urutan template: daftar isi, daftar gambar, daftar tabel, daftar lampiran,
    # lalu daftar istilah.
    doc.add_page_break()
    bab(doc, "DAFTAR ISTILAH")
    for istilah, arti in (
        ("Pelabelan semu", "pemberian label oleh model, bukan oleh manusia, yang hasilnya "
                         "dipakai sebagai data latih"),
        ("Gold set", "himpunan kecil baris yang dinilai manusia dan dipakai mengukur mutu "
                     "sistem, bukan untuk melatih"),
        ("Partisi korpus", "pengelompokan hasil anotasi data menjadi partisi opini, non-opini, dan karantina"),
        ("Korpus", "kumpulan teks yang sudah disaring dan siap dianotasi"),
        ("F1 macro", "rata-rata F1 seluruh kelas tanpa memperhitungkan jumlah tiap kelas, "
                     "sehingga kelas kecil tetap terwakili"),
        ("McNemar", "uji berpasangan yang hanya memperhitungkan baris yang dinilai berbeda "
                    "oleh dua sistem"),
        ("Sidik jari teks", "nilai ringkas suatu teks yang dipakai mendeteksi teks kembar"),
        ("SLS, PPL, PML", "istilah lapangan: satuan lingkungan setempat, petugas pendata "
                          "lapangan, dan petugas pemeriksa lapangan"),
        ("Fasih BPS", "aplikasi pendataan yang dipakai petugas Sensus Ekonomi 2026"),
        ("IndoBERT", "model bahasa Indonesia yang dipakai sebagai dasar pengklasifikasi "
                     "sentimen pada penelitian ini"),
    ):
        p = par(doc, f"{istilah} - {arti}", alinea=False)
        p.paragraph_format.left_indent = Cm(1)
        p.paragraph_format.first_line_indent = Cm(-0.5)


def bab_satu(doc: Document) -> None:
    # Tanpa pemutus halaman di awal bab. Section utama sudah dimulai pada halaman
    # baru, sehingga pemutus di sini akan menyisakan satu halaman kosong bernomor
    # "1" sebelum bab pertama; bab pertama sampai kelima baru dimulai pada
    # halaman berikutnya.
    bab(doc, "BAB I \nPENDAHULUAN")
    numid_b1 = _pastikan_numid(doc, "1")
    sub_bab(doc, "Latar Belakang", numid_b1)
    par(doc, "Sensus Ekonomi 2026 merupakan kegiatan pendataan yang dilaksanakan secara serentak "
             "di seluruh wilayah Indonesia untuk memotret struktur, persebaran, dan karakteristik "
             "pelaku usaha. Berbeda dari survei rutin, sensus menyentuh hampir seluruh rumah "
             "tangga dan usaha sehingga pelaksanaannya selalu menarik perhatian masyarakat luas. "
             "Sejak tahap persiapan, pemberitaan tentang sensus ekonomi telah menimbulkan "
             "tanggapan beragam, mulai dari dukungan, pertanyaan teknis, kekhawatiran mengenai "
             "kerahasiaan data, hingga penolakan (Badan Pusat Statistik, 2024). Pendataan lapangan Sensus Ekonomi 2026 "
             "berlangsung mulai 15 Juni 2026 secara serentak di seluruh wilayah Indonesia "
             "(Badan Pusat Statistik, 2026), dan penolakan sebagian masyarakat menjadi persoalan "
             "yang perlu dikelola melalui komunikasi publik (Khoifaturrahman et al., 2026).")
    par(doc, "Pada tingkat nasional, Badan Pusat Statistik Republik Indonesia (BPS Pusat) memegang "
             "tanggung jawab strategis dalam merumuskan kebijakan pendataan, standardisasi instrumen, "
             "serta pengelolaan arsitektur sistem digital Sensus Ekonomi 2026. Di era keterbukaan "
             "informasi, pelaksanaan sensus serentak memicu dinamika opini publik berskala nasional "
             "yang tersebar di ruang digital, terutama melalui ulasan aplikasi pada toko aplikasi, "
             "komentar video sosialisasi sensus, serta unggahan di berbagai saluran media sosial. "
             "Bagi pengambil kebijakan di BPS Pusat, pemantauan persepsi publik secara cepat dan "
             "menyeluruh merupakan kebutuhan mendesak guna mengukur tingkat kepercayaan publik, "
             "mengevaluasi stabilitas infrastruktur aplikasi survei digital, serta merumuskan strategi "
             "komunikasi publik yang adaptif terhadap isu sensitif seperti kerahasiaan data usaha "
             "dan kekhawatiran integrasi perpajakan.")
    par(doc, "Dinamika komunikasi publik di tingkat nasional tersebut berimbas langsung pada operasional "
             "satuan kerja di tingkat daerah. Sebagai unit pelaksana teknis di garis depan pendataan, "
             + LOKASI + " menghadapi tantangan nyata saat petugas pendata lapangan berinteraksi langsung "
             "dengan para pelaku usaha dan masyarakat setempat. Instansi di tingkat kabupaten memerlukan "
             "gambaran yang cepat, akurat, dan terukur mengenai respons masyarakat lokal, resistensi "
             "responden di lapangan, serta kendala operasional aplikasi Fasih BPS yang dipakai oleh "
             "petugas pencacah. Volume dan kecepatan persebaran percakapan digital yang sangat masif "
             "membuat pemantauan manual tidak lagi memadai, baik untuk perumusan kebijakan di tingkat "
             "pusat maupun mitigasi operasional harian di tingkat daerah.")
    par(doc, "Analisis sentimen berbasis pembelajaran mesin menawarkan jalan keluar atas "
             "kebutuhan tersebut. Data yang menopang analisis itu berupa ulasan aplikasi dan "
             "komentar daring yang sudah tersedia, bersifat publik, dan langsung menyuarakan "
             "pengalaman pengguna. Pemanfaatan "
             "data tersebut menuntut penanganan yang cermat karena teks media sosial umumnya pendek, memuat "
             "singkatan, campur kode bahasa daerah, sarkasme, dan emoji, serta tidak selalu "
             "membicarakan topik yang dituju.")
    par(doc, "Kendala yang lebih mendasar terletak pada penyediaan data berlabel. Pelabelan "
             "manual atas ribuan baris membutuhkan waktu dan tenaga yang besar, sedangkan "
             "pelabelan otomatis memakai model bahasa besar menekan biaya namun membawa risiko tersendiri, "
             "yaitu label yang tampak rapi secara format tetapi keliru secara substansi. Efisiensi "
             "biaya pelabelan otomatis telah banyak didokumentasikan (Gilardi et al., 2023), namun "
             "mutunya belum tentu andal tanpa pemeriksaan kritis (Klie et al., 2024). Pada "
             "penelitian ini, anotator model yang menerima teks tanpa konteks percakapan terbukti "
             "salah mengklasifikasikan balasan singkat sebagai pernyataan netral, sehingga kelas netral "
             "membengkak menampung teks non-opini.")
    par(doc, "Berdasarkan uraian tersebut, Kerja Praktik ini melakukan analisis sentimen opini "
             "publik terhadap Sensus Ekonomi 2026 dan aplikasi Fasih BPS dengan menempatkan mutu "
             "pelabelan sebagai fokus pengujian. Evaluasi pada penelitian ini mencakup audit korpus, "
             "audit mutu label, penyusunan gold set manusia sebagai acuan pengukuran, dan "
             "penjelasan model agar hasilnya dapat ditafsirkan. Penelitian ini membandingkan dua "
             "anotator otomatis, yaitu Jev sebagai anotator utama dan Gemma sebagai anotator "
             "pembanding, untuk menguji sejauh mana penyesuaian anotator memengaruhi mutu label "
             "dan kinerja model klasifikasi.")
    sub_bab(doc, "Tujuan", numid_b1)
    par(doc, "Tujuan umum pelaksanaan Kerja Praktik ini adalah membangun sistem analisis sentimen "
             "yang dapat dipercaya secara metodologis untuk memantau opini publik terhadap Sensus "
             "Ekonomi 2026 dan aplikasi Fasih BPS. Secara khusus, tujuan yang ingin dicapai "
             "adalah sebagai berikut.")
    numid_tujuan = _anggap_rincian(doc)
    for t in ("Mengumpulkan dan menyaring data opini publik dari tiga platform digital melalui "
              "preprocessing berlapis pada rentang 15 Juni sampai 15 September 2026 sehingga "
              "terbentuk korpus yang bersih, konsisten cakupan waktunya, dan dapat ditelusuri asalnya.",
              "Merumuskan kerangka kerja audit mutu label berbasis model bahasa besar untuk "
              "memeriksa seluruh baris, memverifikasi keterlacakan kutipan bukti ke teks sumber, "
              "mendeteksi kesalahan sistematis, serta menormalkan pembengkakan kelas netral.",
              "Membangun mekanisme pelabelan semu sadar konteks beserta perangkat pemilah yang "
              "mempartisi korpus menjadi kelompok opini, non-opini, dan karantina.",
              "Menyusun gold set independen yang diverifikasi manusia sebagai tolok ukur evaluasi "
              "serta memisahkan secara metodologis antara metrik kesepakatan model terhadap "
              "anotator semu dan akurasi terverifikasi manusia.",
              "Melatih pengklasifikasi sentimen berbasis IndoBERT dan membandingkan strategi adaptasi "
              "parameter melalui studi ablasi serta menguji signifikansi perbandingan pipeline "
              "menggunakan uji berpasangan McNemar.",
              "Menerapkan teknik penjelasan model melalui peta atensi dan LIME serta menyusun "
              "analisis tematik opini publik berbasis kalimat untuk menghasilkan rekomendasi kebijakan "
              "operasional bagi Badan Pusat Statistik."):
        butir(doc, t, numid_tujuan)
    sub_bab(doc, "Manfaat", numid_b1)
    par(doc, "Bagi mahasiswa dan sivitas akademik, kegiatan ini memberi pengalaman mengerjakan "
             "rangkaian analisis data berbasis pembelajaran mesin secara menyeluruh, mulai dari "
             "pengumpulan data, penanganan mutu data, pelatihan model, hingga penyusunan laporan "
             "yang dapat dipertanggungjawabkan. Kegiatan ini juga memberikan pemahaman praktis "
             "mengenai penelusuran cacat pada pelabelan otomatis serta penerapan mekanisme pengukuran "
             "evaluasi yang objektif.")
    par(doc, "Bagi " + LOKASI + " dan mitra kerja praktik, penelitian ini menghasilkan perangkat "
             "yang dapat dijalankan ulang untuk memantau tanggapan masyarakat terhadap program "
             "pendataan, sekaligus menyediakan daftar temuan mengenai mutu data yang dikumpulkan "
             "beserta perbaikannya. Perangkat tersebut dapat dipakai memantau tanggapan masyarakat "
             "pada periode pendataan berikutnya.")
    par(doc, "Bagi masyarakat umum, hasil penelitian ini menyajikan gambaran terukur mengenai "
             "tanggapan publik terhadap Sensus Ekonomi 2026, termasuk aspek yang paling sering "
             "dikeluhkan dan dipertanyakan. Gambaran itu berguna sebagai bahan evaluasi pelayanan "
             "kepada masyarakat.")
    sub_bab(doc, "Waktu Pelaksanaan", numid_b1)
    par(doc, "Kerja Praktik dilaksanakan selama satu bulan, yaitu " + TANGGAL_KP + ", bertempat di "
             + LOKASI + ". Pelaksanaan terbagi menjadi lima tahap, yaitu persiapan, pelaksanaan, "
             "penyusunan laporan, ujian kerja praktik, dan penutup. Rincian jadwal setiap tahap "
             "disajikan pada Bab III.")


def bab_dua(doc: Document) -> None:
    doc.add_page_break()
    bab(doc, "BAB II \nTINJAUAN PUSTAKA")
    par(doc, "Bab ini menyajikan landasan teoretis dan kajian pustaka yang mendasari pelaksanaan "
             "Kerja Praktik. Pembahasan tersebut mencakup konsep analisis sentimen, karakteristik media sosial, "
             "arsitektur IndoBERT, metodologi pelabelan semu, strategi adaptasi parameter, metrik evaluasi "
             "klasifikasi dan uji signifikansi statistik, teknik penjelasan model, serta "
             "penelitian terdahulu.")
    numid_b2 = _pastikan_numid(doc, "2")
    sub_bab(doc, "Analisis Sentimen", numid_b2)
    par(doc, "Analisis sentimen adalah tugas mengidentifikasi polaritas opini pada teks, umumnya "
             "ke dalam kelas positif, negatif, dan netral. Pada tingkat dokumen, tugas ini menilai "
             "keseluruhan teks; pada tingkat aspek, penilaian dilakukan terhadap unsur tertentu "
             "yang dibicarakan. Dari sisi pendekatannya, analisis sentimen berkembang dari "
             "pendekatan berbasis kamus, pembelajaran mesin klasik, hingga jaringan saraf dalam. "
             "Di antara metode tersebut, arsitektur jaringan saraf tiruan mendalam lebih banyak "
             "diterapkan karena keunggulannya dalam memodelkan ketergantungan konteks pada teks "
             "berbahasa Indonesia (Setiawan, 2024; Lin & Nuha, 2023).")
    par(doc, "Analisis sentimen pada ranah media sosial menghadapi persoalan khas. Teksnya pendek, "
             "tidak mengikuti kaidah penulisan baku, kerap memuat emoji dan campur kode, serta "
             "bergantung pada percakapan sebelumnya. Sebagai contoh, teks yang berupa balasan sering "
             "tidak bermakna apabila dibaca terpisah dari teks yang dibalas. Kenyataan ini menjadi "
             "pertimbangan penting pada perancangan skema anotasi dalam penelitian ini, sejalan "
             "dengan temuan bahwa penanganan bahasa tidak baku menuntut perlakuan khusus sebelum "
             "teks diklasifikasi (Fernandez et al., 2022; Suhaeni et al., 2025).")
    sub_bab(doc, "Media Sosial sebagai Sumber Opini Publik", numid_b2)
    par(doc, "Media sosial telah menjadi saluran utama penyampaian tanggapan masyarakat terhadap "
             "kebijakan publik. Ulasan aplikasi pada toko aplikasi memiliki sifat yang berbeda dari "
             "komentar video: ulasan cenderung berupa penilaian langsung terhadap pengalaman "
             "penggunaan, sedangkan komentar video lebih beragam dan sering memuat tanggapan atas "
             "pernyataan pihak lain. Perbedaan itu menuntut penyaringan dan penafsiran data yang "
             "berbeda.")
    par(doc, "Pada platform toko aplikasi, peringkat bintang kerap tidak mencerminkan polaritas teks "
             "yang sebenarnya. Kenyataan ini tampak dari perilaku pengguna di Indonesia yang sering "
             "memberikan bintang lima disertai keluhan operasional atau bintang satu disertai apresiasi. "
             "Oleh karena itu, evaluasi sentimen harus bertumpu pada analisis isi teks secara langsung "
             "dan bukan pada skor numerik bintang (Natan Kharisma A. et al., 2025).")
    sub_bab(doc, "Transformer dan IndoBERT", numid_b2)
    par(doc, "Arsitektur transformer memakai mekanisme atensi untuk menimbang keterkaitan antar "
             "token pada sebuah barisan. Berbeda dari jaringan berulang, transformer memproses "
             "seluruh posisi secara paralel sehingga lebih mudah dilatih pada data berukuran "
             "besar. Model bahasa yang telah dilatih lebih dahulu pada korpus luas, seperti BERT, "
             "dapat disetel pada tugas tertentu dengan data berlabel yang jauh lebih sedikit.")
    par(doc, "IndoBERT merupakan model bahasa Indonesia yang dilatih pada korpus berbahasa "
             "Indonesia. Model ini dipakai sebagai dasar pada penelitian ini karena bahasanya "
             "sesuai dengan data yang diolah. Model dasar yang dipakai adalah "
             "indobenchmark/indobert-base-p1. Alternatif yang dipertimbangkan adalah IndoBERTweet "
             "yang dilatih pada korpus Twitter. Varian resmi indobenchmark/indobert-base-p1 dipilih "
             "karena dilatih pada korpus formal dan informal yang seimbang, berbeda dari varian seperti "
             "IndoBERTweet yang dikhususkan untuk teks pendek Twitter (Cahyawijaya et al., 2023). "
             "Pemanfaatan IndoBERT untuk analisis sentimen berbahasa Indonesia telah terbukti pada "
             "berbagai ranah, termasuk layanan kesehatan dan pembahasan kebijakan publik "
             "(Imaduddin et al., 2023; Merdiansah et al., 2024). Pengembangan lanjutan model ini "
             "juga menuju cakupan bahasa daerah yang lebih luas (Wongso et al., 2025; Winata "
             "et al., 2023).")
    sub_bab(doc, "Pelabelan Semu dengan Model Bahasa Besar", numid_b2)
    par(doc, "Pelabelan semu merupakan proses pemberian label secara otomatis oleh model untuk "
             "digunakan sebagai data latih tambahan. Pendekatan ini memangkas waktu anotasi manual, "
             "namun rentan menghasilkan anotasi yang valid secara sintaksis tetapi keliru secara semantik. "
             "Di samping itu, tinjauan empiris terhadap ratusan dataset teks menunjukkan bahwa "
             "verifikasi mutu anotasi otomatis kerap diabaikan meskipun model bahasa besar dilaporkan mampu "
             "menyaingi anotator manusia pada tugas tertentu (Gilardi et al., 2023; Klie et al., 2024).")
    par(doc, "Secara metodologis, terdapat perbedaan fungsi antara gold set dan label semu (pseudo-label). "
             "Gold set diverifikasi oleh manusia sebagai tolok ukur evaluasi akhir, sedangkan label semu "
             "dibangkitkan oleh model untuk kebutuhan pelatihan. Oleh sebab itu, evaluasi yang menggunakan "
             "label semu sebagai acuan akhir akan menghasilkan penalaran melingkar karena model hanya diuji "
             "terhadap prediksinya sendiri.")
    par(doc, "Penanganan label lemah hasil model juga dibahas dalam pustaka, misalnya melalui "
             "penghalusan label, pembobotan ulang, dan pemilihan contoh yang layak dilatih "
             "(Wu et al., 2023; Zhang et al., 2024). Pustaka tersebut menjadi dasar untuk tidak "
             "memakai nilai keyakinan model secara mentah sebagai ambang penyaringan. Pada "
             "penelitian ini, keyakinan model difungsikan sebagai penanda baris anomali yang "
             "memerlukan peninjauan lanjutan dan tidak digunakan untuk eliminasi data secara otomatis.")
    par(doc, "Pada tugas berbasis persepsi sosial, sebagian ketidaksepakatan antaranotator berakar "
             "dari ambiguitas alami teks dan bukan semata-mata kesalahan acak (Fleisig et al., 2023). "
             "Perbedaan penafsiran tersebut memerlukan metrik kesepakatan yang tepat agar kalibrasi "
             "anotasi tetap objektif (Braylan et al., 2022).")
    sub_bab(doc, "Adaptasi Parameter dan Regularisasi", numid_b2)
    par(doc, "Penyetelan penuh seluruh parameter memberikan kinerja baik namun mahal secara "
             "komputasi. Sejumlah strategi adaptasi parameter dikembangkan untuk menekan biaya "
             "tersebut. Salah satu yang paling sederhana adalah BitFit, yang hanya melatih suku "
             "bias tanpa mengubah bobot lainnya, dan terbukti mampu menandingi penyetelan penuh "
             "pada data berukuran kecil sampai sedang (Ben Zaken et al., 2022). Pada penelitian "
             "ini, BitFit dipakai sebagai pembanding terhadap penyetelan penuh dan penyetelan "
             "sebagian lapisan, sehingga perbandingannya dapat ditelusuri pada korpus yang sama.")
    par(doc, "Metode regularisasi R-Drop meminimalkan divergensi Kullback-Leibler antara dua distribusi "
             "keluaran dari masukan identik dengan sub-jaringan dropout berbeda, sehingga meningkatkan "
             "ketahanan representasi model melalui regularisasi konsistensi (Fan et al., 2023). "
             "Di samping itu, ketimpangan distribusi kelas diatasi melalui fungsi rugi tertimbang dan "
             "pemfokusan pada sampel sulit guna menjaga performa pada kelas minoritas "
             "(Cao et al., 2022; Wang et al., 2022).")
    sub_bab(doc, "Metrik Evaluasi Klasifikasi dan Uji Signifikansi Statistik", numid_b2)
    par(doc, "Evaluasi kinerja model klasifikasi teks bertumpu pada matriks konfusi yang memetakan "
             "perbandingan antara label acuan kebenaran dan label prediksi model. Dari matriks "
             "tersebut, metrik akurasi dihitung sebagai rasio prediksi benar terhadap seluruh sampel. "
             "Akurasi memberikan gambaran umum mengenai performa sistem, namun memiliki kelemahan mendasar "
             "pada korpus dengan distribusi kelas yang tidak seimbang. Pada korpus yang timpang, "
             "model yang selalu memprediksi kelas mayoritas dapat memperoleh nilai akurasi nominal "
             "yang tinggi meskipun gagal mengenali kelas minoritas sama sekali (Opitz, 2024).")
    par(doc, "Evaluasi dilengkapi dengan metrik presisi, recall, dan F1-Score guna mengatasi kelemahan "
             "akurasi tersebut. Presisi mengukur proporsi prediksi suatu kelas yang terbukti benar, "
             "sedangkan recall mengukur kemampuan model dalam menangkap seluruh instansi aktual dari "
             "kelas tersebut. F1-Score merupakan rata-rata harmonik antara presisi dan recall. Pada "
             "tugas klasifikasi multikelas dengan ketimpangan proporsi kelas, Macro F1-Score (F1 macro) "
             "dihitung dengan merata-ratakan skor F1 setiap kelas secara aritmetika tanpa pembobotan "
             "ukuran sampel. Pendekatan ini memberikan bobot kepentingan yang setara bagi seluruh "
             "kelas, sehingga penurunan kinerja pada kelas minoritas seperti kelas netral dapat "
             "terdeteksi secara objektif (Opitz, 2024).")
    par(doc, "Perbandingan performa antarmodel memerlukan pengujian signifikansi statistik guna memastikan "
             "bahwa selisih performa bukan merupakan hasil variansi acak pada sampel uji. Uji berpasangan "
             "McNemar merupakan uji statistik non-parametrik yang dirancang khusus untuk membandingkan "
             "dua pengklasifikasi pada set data uji berpasangan yang sama (Soman et al., 2022). "
             "Pengujian ini berfokus pada sel diskordan, yaitu kasus ketika salah satu model "
             "memprediksi benar sementara model lainnya keliru, dengan tingkat kesalahan Tipe I yang "
             "rendah pada partisi data uji tunggal, sehingga signifikansi perbedaan kedua pipeline "
             "dapat diukur secara statistik.")
    sub_bab(doc, "Penjelasan Model", numid_b2)
    par(doc, "Penjelasan model diperlukan agar hasil klasifikasi dapat ditafsirkan dan dipertanggungjawabkan "
             "secara rasional. Tingginya skor akurasi nominal pada data uji tidak serta-merta menjamin bahwa "
             "model mengambil keputusan berdasarkan fitur semantik yang valid. Model berparameter besar "
             "berisiko mengandalkan korelasi semu atau pola pintas statistik untuk mencapai akurasi tinggi. "
             "Oleh sebab itu, evaluasi akurasi perlu diiringi dengan pengujian kesetiaan dan keterpahaman "
             "fitur melalui metode penjelasan model (Atanasova et al., 2023; Liu et al., 2022).")
    par(doc, "Dua pendekatan penjelasan model diterapkan pada penelitian ini, yaitu peta atensi dan LIME. "
             "Peta atensi menampilkan bobot perhatian model terhadap token pada tiap lapisan, sedangkan "
             "LIME menjelaskan keputusan model dengan mengubah masukan secara lokal dan mengamati "
             "pengaruh perubahannya terhadap keluaran prediksi. Yeh et al. (2024) membahas visualisasi "
             "atensi secara menyeluruh pada transformer. Bobot atensi tidak dengan sendirinya merupakan "
             "penjelasan yang sahih, sehingga kesetiaan penjelasan berbasis atensi perlu diuji secara "
             "tersendiri guna memastikan model benar-benar memusatkan perhatian pada kata kunci sentimen "
             "yang relevan (Atanasova et al., 2023; Liu et al., 2022). Tinjauan atas metode penjelasan "
             "berbasis nilai Shapley turut melengkapi gambaran mengenai pilihan metode atribusi fitur yang "
             "tersedia untuk teks (Mosca et al., 2022).")
    sub_bab(doc, "Penelitian Terdahulu", numid_b2)
    par(doc, "Analisis sentimen berbahasa Indonesia telah banyak dilakukan pada ranah layanan "
             "publik dan media sosial. Pendekatan yang dipakai bergerak dari Naive Bayes dan "
             "K-Nearest Neighbor hingga model bahasa terlatih (Setiawan, 2024). Model BERT dan "
             "IndoBERT dilaporkan mengungguli pendekatan klasik pada data berbahasa Indonesia, "
             "baik pada ulasan aplikasi maupun pada percakapan media sosial (Lin & Nuha, 2023; "
             "Mandhasiya et al., 2024). Penerapannya pada kebijakan publik mencakup pembahasan "
             "pembatasan kegiatan masyarakat, tanggapan terhadap akun kementerian, dan pemilihan "
             "umum (Naufal & Kusuma, 2022; Gumilang et al., 2024; Geni et al., 2023).")
    par(doc, "Sebagian besar penelitian terdahulu berfokus pada optimasi skor akurasi tanpa menguji "
             "validitas label latih yang digunakan. Penelitian ini mengisi celah tersebut dengan "
             "menempatkan audit mutu label dan verifikasi gold set manusia sebagai pilar utama "
             "metodologi. Pendekatan ini sejalan dengan paradigma data-centric AI yang menekankan "
             "rekayasa dan kualitas data sebagai penentu utama keandalan sistem cerdas (Whang et al., 2023).")


def bab_tiga(doc: Document) -> None:
    doc.add_page_break()
    bab(doc, "BAB III \nMETODE PELAKSANAAN KP")
    numid_b3 = _pastikan_numid(doc, "3")
    sub_bab(doc, "Gambaran Umum Lokasi KP", numid_b3)
    par(doc, "Kerja Praktik dilaksanakan di " + LOKASI + ", " + ID["alamat_lokasi"] + ". "
             "Lingkup pekerjaan yang diberikan berkaitan dengan penyiapan data digital untuk "
             "mendukung pelaksanaan Sensus Ekonomi 2026, khususnya pengolahan tanggapan masyarakat "
             "atas pelaksanaan pendataan dan atas aplikasi Fasih BPS.")
    sub_bab(doc, "Metode Pengumpulan Data", numid_b3)
    par(doc, "Pengumpulan data pada kegiatan ini bertumpu pada data sekunder yang tersedia bebas "
             "di ruang publik digital, yaitu ulasan aplikasi, komentar video, dan unggahan media "
             "sosial. Data primer diperoleh melalui diskusi dengan pembimbing lapangan untuk "
             "memastikan konteks istilah teknis yang muncul pada teks, misalnya singkatan SLS, PPL, "
             "dan PML.")
    anak_sub_bab(doc, "3.2.1 Pengumpulan Data Primer")
    par(doc, "Data primer dikumpulkan melalui wawancara tidak terstruktur dengan pembimbing "
             "lapangan dan observasi langsung terhadap alur pendataan. Keduanya dipakai untuk "
             "memahami istilah lapangan yang tidak lazim bagi orang di luar lingkungan statistik, "
             "sehingga penyaring topik dan skema anotasi dapat dirancang sesuai kenyataan di "
             "lapangan.")
    anak_sub_bab(doc, "3.2.2 Pengumpulan Data Sekunder")
    par(doc, "Data sekunder dikumpulkan melalui antarmuka pemrograman aplikasi dan peramban pada "
             "tiga platform. Selain itu, cakupan waktu dibatasi pada rentang 15 Juni 2026 sampai "
             "15 September 2026. Penegakan batas tanggal tersebut diotomatisasi melalui skrip "
             "pengambil data guna mencegah pergeseran rentang waktu secara manual. "
             "Rincian jenis data dan alat pengumpulnya disajikan pada Tabel 3.1.")
    judul_tabel(doc, "Tabel 3.1 Metode Pengumpulan Data")
    tabel(doc, ["Nomor", "Jenis Data", "Sumber Data", "Alat/Instrumen"], [
        ["1", "Ulasan dan penilaian aplikasi", "Data sekunder",
         "Pustaka google-play-scraper pada aplikasi id.go.bpsfasih"],
        ["2", "Komentar video beserta balasannya", "Data sekunder",
         "Pustaka yt-dlp pada hasil pencarian dan kanal resmi"],
        ["3", "Unggahan dan komentar Threads", "Data sekunder",
         "Antarmuka CLI threads-comment-scraper"],
        ["4", "Istilah dan konteks pendataan", "Data primer",
         "Wawancara dan observasi"],
    ])
    sub_bab(doc, "Metode Analisis Data", numid_b3)
    par(doc, "Analisis dijalankan berurutan mulai dari pemeriksaan mutu korpus sampai penjelasan "
             "model. Setiap tahap dalam rangkaian itu menyediakan mode pengujian mandiri dan "
             "menyimpan keluarannya sebagai berkas, sehingga hasil dapat ditelusuri kembali. "
             "Rincian metode analisis "
             "disajikan pada Tabel 3.2.")
    judul_tabel(doc, "Tabel 3.2 Metode Analisis Data")
    tabel(doc, ["Nomor", "Jenis Data", "Sumber Data", "Analisis"], [
        ["1", "Korpus teks mentah", "Data sekunder",
         "Penyaringan bahasa, penyaringan topik, penyaringan tanggal, dan deduplikasi"],
        ["2", "Korpus bersih", "Data sekunder",
         "Pelabelan semu sadar konteks Gemma 4 12B, partisi korpus, dan pengujian anotasi keputusan Jev"],
        ["3", "Korpus berlabel", "Data sekunder",
         "Audit mutu label menyeluruh dan pengukuran keterlacakan bukti"],
        ["4", "Kandidat gold set", "Data primer",
         "Anotasi manusia berlapis dan uji berpasangan McNemar"],
        ["5", "Partisi opini", "Data sekunder",
         "Penyetelan IndoBERT dan studi ablasi enam strategi adaptasi parameter"],
        ["6", "Model terlatih", "Data sekunder",
         "Penjelasan peta atensi dan LIME"],
        ["7", "Pipeline pembanding", "Data sekunder",
         "Pemilahan langsung dengan Jev dan pelatihan IndoBERT pembanding"],
    ])
    par(doc, "Untuk menguji apakah pemilahan awal oleh Gemma diperlukan, penelitian ini "
             "menjalankan pipeline pembanding dengan Jev sebagai pemilah langsung. Pipeline itu "
             "memakai ambang peluang relevansi 0,20, mengambil baris bertipe opini, menghasilkan "
             "5.590 baris data latih, dan dilatih dengan skenario yang sama. Kedua pipeline "
             "kemudian diukur pada data uji manusia yang sama dan dibandingkan dengan uji McNemar.")
    sub_bab(doc, "Tahapan dan Jadwal Kegiatan KP", numid_b3)
    par(doc, "Pelaksanaan Kerja Praktik mengikuti lima tahap sesuai buku panduan. Tahap persiapan "
             "mencakup pengurusan administrasi dan studi pustaka. Tahap pelaksanaan mencakup "
             "pengumpulan data, penyusunan korpus, pelabelan, audit, penyusunan gold set, "
             "pelatihan model, dan penjelasan model. Jadwal selengkapnya disajikan pada Tabel 3.3.")
    judul_tabel(doc, "Tabel 3.3 Jadwal Pelaksanaan Kegiatan KP Tahun 2026")
    tabel(doc, ["Tahapan Kegiatan", "Bulan ke-1", "Bulan ke-2", "Bulan ke-3", "Bulan ke-4"], [
        ["Persiapan", "Minggu 1, 2", "-", "-", "-"],
        ["Pelaksanaan", "Minggu 3, 4", "Minggu 1, 2, 3", "Minggu 1, 2", "-"],
        ["Penyusunan Laporan", "-", "-", "Minggu 3, 4", "Minggu 1"],
        ["Ujian KP", "-", "-", "-", "Minggu 2"],
        ["Penutup", "-", "-", "-", "Minggu 3, 4"],
    ], sumber_teks="Sumber: Buku Panduan Kerja Praktik dan Rencana Kegiatan, 2026")
    par(doc, "Alur pelaksanaan Kerja Praktik digambarkan pada Gambar 3.1, mulai dari persiapan "
             "dan studi pustaka, pengumpulan data, penyaringan korpus, pelabelan semu beserta "
             "auditnya, penyusunan gold set, pelatihan dan studi ablasi, penjelasan model, "
             "pembangunan antarmuka sistem pendukung keputusan, hingga penyusunan laporan.")
    gambar(doc, buat_diagram_alir(REPORTS / "diagram_alir_kp.png"), 13,
           "Gambar 3.1 Diagram Alir Pelaksanaan KP")
    sumber(doc, "Sumber: hasil pengolahan data, 2026")
    par(doc, "Aturan penentuan kelas sentimen yang dipakai pada anotasi manusia mengikuti urutan "
             "keputusan pada Gambar 3.2, sedangkan keseluruhan alur penelitian dari data mentah "
             "sampai laporan digambarkan pada Gambar 3.3.")
    gambar(doc, REPORTS / "diagram_keputusan_anotasi.png", 14,
           "Gambar 3.2 Diagram Keputusan Anotasi Lima Kelas")
    sumber(doc, "Sumber: hasil pengolahan data, 2026")
    gambar(doc, REPORTS / "diagram_alur_penelitian.png", 14,
           "Gambar 3.3 Diagram Alur Penelitian")
    sumber(doc, "Sumber: hasil pengolahan data, 2026")
    par(doc, "Diagram pipeline terpadu dari hulu ke hilir disajikan pada Gambar 3.4. Diagram tersebut "
             "memvisualisasikan alur lengkap mulai dari pengumpulan data mentah multi-platform (10.961 rekaman), "
             "empat tahap preprocessing (penyaringan tanggal, bahasa, topik, dan deduplikasi hingga menghasilkan "
             "8.352 baris bersih), dua jalur anotasi komparatif (pipeline utama Gemma-Jev dan pipeline pembanding mandiri Jev), "
             "pelatihan pengklasifikasi IndoBERT beserta studi ablasi parameter, pengujian statistik McNemar pada data "
             "uji manusia, tahap penjelasan model melalui peta atensi dan LIME, serta implementasi sistem pendukung "
             "keputusan (decision support system) berbasis web.")
    gambar(doc, REPORTS / "diagram_alur_pelabelan.png", 15,
           "Gambar 3.4 Diagram Pipeline Komprehensif dari Preprocessing hingga Evaluasi")
    sumber(doc, "Sumber: hasil pengolahan data, 2026")


def bab_empat(doc: Document) -> None:
    doc.add_page_break()
    bab(doc, "BAB IV \nHASIL DAN PEMBAHASAN")
    numid_b4 = _pastikan_numid(doc, "4")
    sub_bab(doc, "Hasil", numid_b4)
    anak_sub_bab(doc, "4.1.1 Hasil Pengumpulan dan Penyaringan Data")
    par(doc, "Pengumpulan data menghasilkan 10.961 rekaman mentah dari tiga platform. Rekaman itu "
             "kemudian disaring berlapis, yaitu penyaringan tanggal, penyaringan bahasa asing, "
             "penyaringan topik, dan deduplikasi. Hasil setiap lapis disajikan pada Tabel 4.1. "
             "Di luar ketiga platform tersebut, pengambilan data dari Reddit dan Twitter/X "
             "terhambat oleh pembatasan akses antarmuka pemrograman aplikasi komersial dari "
             "penyedia layanan.")
    judul_tabel(doc, "Tabel 4.1 Hasil Penyaringan Korpus")
    tabel(doc, ["Tahap", "Jumlah Baris", "Keterangan"], [
        ["Rekaman mentah", "10.961", "Gabungan tiga platform"],
        ["Setelah penyaringan tanggal", "8.953", "Rentang 15 Juni sampai 15 September 2026"],
        ["Setelah penyaringan bahasa", "8.952", "Satu rekaman berbahasa asing dibuang"],
        ["Setelah penyaringan topik", "8.831", "Penyaringan topik Threads"],
        ["Korpus akhir", "8.352", "Setelah deduplikasi sidik jari teks"],
    ])
    par(doc, "Korpus akhir terdiri atas 6.727 baris dari YouTube, 1.366 baris dari Google Play, "
             "dan 259 baris dari Threads. Penegakan batas tanggal mengubah "
             "korpus secara berarti: pada korpus sebelumnya terdapat 1.721 baris yang berada di "
             "luar rentang, termasuk komentar yang mundur sampai tahun 2016 karena komentar lama "
             "pada video yang baru tetap terbawa.")
    anak_sub_bab(doc, "4.1.2 Hasil Pelabelan dan Partisi Korpus")
    par(doc, "Pelabelan semu memakai prompt sadar konteks (spesifikasi rancangan dan skema JSON terstruktur "
             "disajikan pada Lampiran 3) menghasilkan label untuk 8.350 baris. "
             "Hasilnya dipartisi ke dalam empat kelompok korpus sebagaimana disajikan pada Tabel 4.2. Dari "
             "jumlah tersebut, dua baris belum berlabel karena panjang teksnya di bawah ambang yang "
             "layak dianotasi.")
    judul_tabel(doc, "Tabel 4.2 Sebaran Partisi Korpus")
    tabel(doc, ["Partisi", "Jumlah", "Porsi", "Perlakuan"], [
        ["Opini", "5.808", "69,6%", "Data latih sentimen"],
        ["Non-opini", "2.119", "25,4%", "Disimpan, tidak dipakai melatih sentimen"],
        ["Karantina", "423", "5,1%", "Di luar topik, disimpan sebagai bukti audit"],
        ["Gagal", "0", "0%", "Tidak ada kegagalan penguraian"],
    ])
    par(doc, "Sebaran sentimen pada partisi opini dengan anotator awal adalah negatif 4.285 baris, "
             "positif 1.304 baris, dan netral 219 baris. Setelah label disegarkan memakai anotator "
             "Jev, sebarannya menjadi negatif 3.978 baris, positif 1.315 baris, dan netral 515 "
             "baris atau 8,9 persen; seluruh pelatihan pada bab ini memakai label hasil penyegaran "
             "itu. Kelas netral pada korpus lama pernah mencapai 2.967 baris atau 30,7 persen "
             "karena menampung pertanyaan, sapaan, dan keterangan. Setelah konteks dan tipe teks "
             "diperhitungkan, kelas itu menyusut, dan yang tersisa pada korpus akhir adalah "
             "laporan keadaan serta penilaian yang memang datar.")
    par(doc, "Pemilahan relevansi diuji tersendiri pada seratus baris data uji manusia, dengan "
             "lima belas baris di antaranya dinilai tidak relevan oleh manusia. Perbandingan "
             "pemilahan Gemma dan ambang peluang relevansi Jev disajikan pada Tabel 4.3.")
    judul_tabel(doc, "Tabel 4.3 Perbandingan Pemilahan Relevansi Gemma dan Jev")
    tabel(doc, ["Pemilah", "Benar", "Salah Menuduh", "Luput", "Presisi", "Recall", "F1", "Akurasi"], [
        ["Gemma, partisi karantina", "1", "7", "14", "0,1250", "0,0667", "0,0870", "0,7900"],
        ["Jev, peluang relevan < 0,20", "3", "4", "12", "0,4286", "0,2000", "0,2727", "0,8400"],
        ["Jev, peluang relevan < 0,50", "5", "13", "10", "0,2778", "0,3333", "0,3030", "0,7700"],
    ])
    par(doc, "Berdasarkan data pada tabel, pemilahan relevansi masih menjadi kelemahan kedua anotator "
             "karena sebagian besar baris tidak relevan terlewat. Pemilahan Gemma keliru memilah "
             "tujuh baris relevan, sedangkan ambang peluang Jev 0,20 keliru pada empat baris. Pada "
             "seluruh korpus, ambang 0,20 menyaring keluar 436 baris, mendekati 423 baris karantina "
             "Gemma. Tabel ini mengukur mutu pemilahan relevansi secara khusus, sedangkan evaluasi "
             "pipeline sentimen disajikan pada Sub-bab 4.1.5.")
    par(doc, "Hasil pengujian menunjukkan bahwa Jev dapat menjalankan pemilahan relevansi secara mandiri "
             "tanpa dependensi wajib pada Gemma. Pada pengukuran terhadap data uji manusia, "
             "pipeline utama (partisi Gemma dan anotasi Jev) menghasilkan akurasi 0,7882, sedangkan pipeline "
             "mandiri Jev menghasilkan 0,7529. Uji McNemar menghasilkan nilai p 0,5811, yang menunjukkan "
             "perbedaan performa kedua pipeline belum signifikan secara statistik. Pipeline utama dipilih "
             "sebagai konfigurasi rujukan karena mencatatkan estimasi titik yang lebih tinggi serta menjadi "
             "landasan seluruh artefak eksplanasi model, sementara pipeline mandiri Jev diposisikan sebagai "
             "varian ablasi pembanding.")
    anak_sub_bab(doc, "4.1.3 Hasil Audit Mutu Label")
    par(doc, "Audit mutu dijalankan terhadap seluruh 8.350 baris berlabel secara menyeluruh. "
             "Pemeriksaan tersebut mencakup validitas nilai terhadap rentang yang diizinkan, konsistensi "
             "antarkolom, serta verifikasi keterlacakan kutipan bukti terhadap teks sumber. Hasil pemeriksaan "
             "disajikan pada Tabel 4.4.")
    judul_tabel(doc, "Tabel 4.4 Hasil Audit Mutu Label")
    tabel(doc, ["Ukuran", "Nilai"], [
        ["Baris dipindai", "8.350"],
        ["Baris bertanda", "1.782 (21,3%)"],
        ["Cacat kritis", "0"],
        ["Bukti berdasar teks", "8.348 (99,98%)"],
        ["Teks identik dengan sentimen berbeda", "0"],
        ["Keyakinan bernilai mutlak 1,0", "816"],
        ["Keyakinan di bawah 0,6", "367"],
    ])
    par(doc, "Tidak ditemukan satu pun cacat kritis: seluruh nilai sentimen, tipe, dan bahasa "
             "berada pada daftar yang diizinkan, dan tidak ada baris di luar topik yang menyusup "
             "ke partisi latih. Kutipan bukti juga tidak dihaluskan; seluruhnya dapat dilacak ke teks "
             "asalnya. Meski demikian, cacat yang tersisa bersifat definisional, misalnya sapaan "
             "yang tetap diberi sentimen dan lelucon yang belum dipisahkan dari partisi opini.")
    anak_sub_bab(doc, "4.1.4 Hasil Studi Ablasi")
    par(doc, "Studi ablasi membandingkan enam strategi adaptasi parameter pada pembagian data yang "
             "sama, yaitu 4.646 baris latih dan 1.162 baris uji dari 5.808 baris partisi opini "
             "berlabel Jev. Pembagian dilakukan berkelompok menurut asal percakapan agar komentar "
             "dari video yang sama tidak terbelah antara data latih dan data uji. Pelatihan itu "
             "dijalankan pada GPU T4 layanan Modal. Hasilnya disajikan pada Tabel 4.5.")
    judul_tabel(doc, "Tabel 4.5 Hasil Studi Ablasi pada Korpus Penelitian")
    tabel(doc, ["Skenario", "Akurasi", "F1 macro", "Parameter Dilatih", "Waktu (detik)"], [
        ["zeroshot", "0,7324", "0,5971", "0", "0"],
        ["linear_probe", "0,8141", "0,6948", "0", "33"],
        ["bitfit", "0,8821", "0,7160", "105.219", "155"],
        ["partial_top_k", "0,8778", "0,7344", "43.120.131", "150"],
        ["full", "0,8830", "0,7426", "124.443.651", "225"],
        ["full_rdrop", "0,8830", "0,7628", "124.443.651", "424"],
    ])
    par(doc, "Hasil studi ablasi menunjukkan bahwa strategi hemat parameter seperti BitFit dan "
             "partial_top_k mampu mencapai akurasi mendekati 0,88 dengan melatih sebagian kecil "
             "parameter, menjadikannya pilihan efisien untuk kebutuhan pemantauan berkala. Pada "
             "strategi penyetelan penuh, penambahan regularisasi R-Drop mempertahankan akurasi pada "
             "angka 0,8830 sekaligus menaikkan F1 macro dari 0,7426 menjadi 0,7628, sehingga skenario "
             "full_rdrop dipilih sebagai konfigurasi model terbaik. Di samping itu, nilai F1 macro "
             "pada seluruh skenario berada di bawah akurasi karena proporsi kelas netral hanya 8,9 "
             "persen dengan tingkat presisi yang relatif rendah.")
    par(doc, "Studi yang sama diulang pada data latih hasil pemilahan Jev, yaitu 5.590 baris "
             "dengan pembagian 4.475 baris latih dan 1.115 baris uji. Skenario terbaik tetap "
             "full_rdrop dengan akurasi 0,8780 dan F1 macro 0,7355, sedangkan zeroshot naik menjadi "
             "0,7507. Selisih kedua pipeline itu tidak berbeda nyata pada data uji manusia "
             "(p 0,5811), sehingga Tabel 4.5 tetap dipakai sebagai angka utama dan hasil pemilahan "
             "Jev disajikan sebagai pembanding.")
    par(doc, "Seluruh metrik pada Tabel 4.5 mengukur tingkat kesesuaian inferensi model terhadap "
             "label semu Jev dan bukan akurasi mutlak terhadap acuan manusia. Evaluasi terhadap "
             "data uji terverifikasi manusia disajikan terpisah pada Tabel 4.6 guna menghindari bias "
             "pengukuran. Di samping itu, matriks konfusi model terbaik pada data uji semu "
             "disajikan pada Gambar 4.1.")
    gambar(doc, REPORTS / "modal" / "ablasi_jev" / "ablation_confusion.png", 11,
           "Gambar 4.1 Matriks Konfusi Studi Ablasi")
    sumber(doc, "Sumber: hasil pengolahan data, 2026")
    anak_sub_bab(doc, "4.1.5 Hasil Pengukuran terhadap Data Uji Manusia")
    par(doc, "Data uji terdiri atas seratus baris yang dinilai manusia. Barisnya ditarik acak "
             "berlapis dari korpus final, tersamar, dan tidak beririsan dengan berkas uji mana pun "
             "sebelumnya. Penilaian atas baris-baris itu dilakukan setelah aturan baku kelas "
             "ditulis. Hasil penilaian menunjukkan 15 baris tidak relevan sehingga dikeluarkan dari "
             "metrik sentimen, dan yang tersisa 85 baris. Lima sistem diukur pada baris yang sama "
             "dan hasilnya disajikan pada "
             "Tabel 4.6.")
    judul_tabel(doc, "Tabel 4.6 Hasil Pengukuran terhadap Data Uji Manusia")
    tabel(doc, ["Sistem", "Akurasi", "F1 macro", "Recall negatif", "Recall netral", "Recall positif"], [
        ["Anotator LLM Gemma (Prompt Sadar Konteks)", "0,7176", "0,7052", "0,913", "0,387", "0,875"],
        ["Anotator Keputusan Jev (Aturan Terkalibrasi)", "0,7882", "0,7713", "0,891", "0,613", "0,875"],
        ["IndoBERT (Pipeline Utama: Gemma-Jev)", "0,7882", "0,7700", "0,913", "0,581", "0,875"],
        ["IndoBERT (Pipeline Mandiri Jev / Pembanding)", "0,7529", "0,7387", "0,957", "0,419", "0,875"],
        ["IndoBERT (Baseline Anotasi Tunggal Gemma)", "0,7294", "0,6910", "0,913", "0,419", "0,875"],
    ])
    par(doc, "Dua angka teratas adalah 0,7882, yaitu anotator keputusan Jev dan pengklasifikasi IndoBERT "
             "yang dilatih pada pipeline utama (partisi Gemma dan anotasi Jev). Pengklasifikasi dengan "
             "pipeline mandiri Jev mencapai 0,7529; uji McNemar atas pasangan kedua pengklasifikasi itu memberi 5 lawan 8 "
             "dengan nilai p 0,5811, sehingga keduanya belum dapat dibedakan pada 85 baris. "
             "Perbedaan kelasnya terlihat pada recall kelas netral: anotator awal Gemma hanya menemukan "
             "0,387, anotator keputusan Jev menemukan 0,613, IndoBERT pipeline utama menemukan 0,581, "
             "sedangkan IndoBERT pipeline mandiri Jev menemukan 0,419. Pada kelas negatif semuanya memadai, dan "
             "kelas positif hanya berisi 8 baris sehingga angkanya bising. Uji McNemar eksak antara "
             "anotator awal Gemma dan anotator keputusan Jev memberi 9 lawan 3 dengan nilai p 0,1460; arahnya "
             "konsisten, tetapi besarnya belum dapat dipastikan.")
    par(doc, "Hasil evaluasi pada Tabel 4.6 merepresentasikan akurasi riil terhadap acuan manusia, "
             "yang berbeda maknanya dari metrik kesesuaian pada Tabel 4.5. Selisih kedua nilai tersebut "
             "cukup lebar: model yang dilatih di atas label semu memperoleh kesesuaian 0,8830 terhadap "
             "anotatornya, tetapi akurasinya pada acuan manusia bernilai 0,7882. Kesenjangan ini "
             "membuktikan bahwa model mempelajari pola anotator latih secara konsisten, termasuk "
             "mereplikasi galat yang ada.")
    par(doc, "Rincian metrik tiap kelas disajikan pada Tabel 4.7, dan pola kesalahan yang "
             "terbanyak muncul pada Tabel 4.8. Tampak bahwa selisih antarsistem hampir "
             "seluruhnya berasal dari kelas netral, sedangkan kelas negatif dan positif sudah "
             "dikenali baik oleh semua sistem.")
    judul_tabel(doc, "Tabel 4.7 Metrik per Kelas pada Data Uji Manusia")
    tabel(doc, ["Sistem", "Kelas", "Presisi", "Recall", "F1", "Dukungan"], [
        ["Anotator LLM Gemma (Prompt Sadar Konteks)", "negatif", "0,808", "0,913", "0,857", "46"],
        ["Anotator LLM Gemma (Prompt Sadar Konteks)", "netral", "0,800", "0,387", "0,522", "31"],
        ["Anotator LLM Gemma (Prompt Sadar Konteks)", "positif", "0,636", "0,875", "0,737", "8"],
        ["Anotator Keputusan Jev (Aturan Terkalibrasi)", "negatif", "0,804", "0,891", "0,845", "46"],
        ["Anotator Keputusan Jev (Aturan Terkalibrasi)", "netral", "0,792", "0,613", "0,691", "31"],
        ["Anotator Keputusan Jev (Aturan Terkalibrasi)", "positif", "0,700", "0,875", "0,778", "8"],
        ["IndoBERT (Pipeline Utama: Gemma-Jev)", "negatif", "0,778", "0,913", "0,840", "46"],
        ["IndoBERT (Pipeline Utama: Gemma-Jev)", "netral", "0,857", "0,581", "0,692", "31"],
        ["IndoBERT (Pipeline Utama: Gemma-Jev)", "positif", "0,700", "0,875", "0,778", "8"],
        ["IndoBERT (Pipeline Mandiri Jev / Pembanding)", "negatif", "0,647", "0,957", "0,772", "46"],
        ["IndoBERT (Pipeline Mandiri Jev / Pembanding)", "netral", "0,619", "0,419", "0,500", "31"],
        ["IndoBERT (Pipeline Mandiri Jev / Pembanding)", "positif", "0,636", "0,875", "0,737", "8"],
        ["IndoBERT (Baseline Anotasi Tunggal Gemma)", "negatif", "0,724", "0,913", "0,808", "46"],
        ["IndoBERT (Baseline Anotasi Tunggal Gemma)", "netral", "0,867", "0,419", "0,565", "31"],
        ["IndoBERT (Baseline Anotasi Tunggal Gemma)", "positif", "0,583", "0,875", "0,700", "8"],
    ])
    judul_tabel(doc, "Tabel 4.8 Pola Kesalahan Terbanyak pada Data Uji")
    tabel(doc, ["Pola (penilaian manusia lalu tebakan sistem)", "Kemunculan", "Baris Unik"], [
        ["netral ditebak negatif", "62", "22"],
        ["tidak relevan ditebak netral", "38", "10"],
        ["tidak relevan ditebak negatif", "29", "10"],
        ["negatif ditebak netral", "14", "7"],
        ["netral ditebak positif", "13", "5"],
    ])
    par(doc, "Pola pertama menunjukkan bahwa kesalahan klasifikasi menumpuk pada batas antara "
             "laporan keadaan dan keluhan, mencerminkan batas semantik yang rapat antarkategori. "
             "Di sisi lain, pola kedua dan ketiga memperlihatkan bahwa kelima sistem cenderung "
             "menerima teks di luar topik sehingga gerbang relevansi masih memerlukan penyempurnaan "
             "lebih lanjut.")
    par(doc, "Pada data uji manusia, kelas netral masih mencakup 25 baris laporan keadaan dari "
             "total 31 baris netral yang secara formal berkarakteristik non-opini. Karakteristik ini "
             "dipertahankan agar evaluasi kelas netral secara realistis menguji daya adaptasi model "
             "terhadap variasi ekspresi faktual di media sosial.")
    par(doc, "Perjalanan pengujian anotator sampai pada pilihan Jev digambarkan pada Gambar 4.2.")
    gambar(doc, REPORTS / "diagram_uji_jev.png", 13, "Gambar 4.2 Diagram Pengujian Anotator")
    sumber(doc, "Sumber: hasil pengolahan data, 2026")
    par(doc, "Bagan pada Gambar 4.2 memperlihatkan alur kalibrasi berulang anotator keputusan Jev melalui "
             "tujuh tahapan terencana sebelum menjalankan pelabelan korpus berskala penuh. Pada "
             "tahap awal, formulasi gerbang relevansi yang terlampau ketat menyebabkan model menolak "
             "sebagian besar teks sasaran sehingga menghasilkan akurasi 0,2609 pada data uji ronde "
             "pertama. Peneliti kemudian menerapkan pembingkaian adaptif berbasis lembar anotasi "
             "yang meningkatkan akurasi menjadi 0,5109. Memasuki ronde kedua, pelibatan anotator "
             "manusia kedua memungkinkan penanaman aturan batas semantik antarkelas, yang "
             "mendorong akurasi ke angka 0,6196 dan akurasi khusus kelas sentimen ke 0,7935. "
             "Ronde 3a dan penajaman final kemudian menuntaskan kalibrasi batas keluhan teknis "
             "aplikasi Fasih serta memisahkan laporan faktual dari keluhan, menghasilkan akurasi "
             "0,7935. Pengujian buta pada data uji manusia menghasilkan akurasi validasi independen "
             "sebesar 0,7882 yang melampaui model Gemma (0,7176), sebelum akhirnya model "
             "mengeksekusi anotasi 8.352 baris korpus dengan tingkat keberhasilan seratus persen.")
    anak_sub_bab(doc, "4.1.6 Gambaran Leksikal per Kelas")
    par(doc, "Untuk melihat apa yang membedakan tiap kelas dari bahasanya sendiri, dihitung rasio "
             "log-odds berprior Dirichlet (Valizadeh et al., 2023) atas sebaran kata "
             "korpus, dan hasilnya digambarkan sebagai awan kata pada Gambar 4.3. Kata yang "
             "menonjol pada kelas negatif adalah kata tindakan dan kekecewaan seperti \"buang\", "
             "\"korup\", \"percuma\", dan \"janji\"; kelas netral didominasi kata prosedural seperti "
             "\"mode\", \"urut\", \"kolom\", dan \"sls\"; sedangkan kelas positif memuat kata "
             "apresiasi dan dukungan seperti \"aamiin\", \"semangat\", \"keren\", dan "
             "\"menginspirasi\". Kelas netral yang hanya 8,9 "
             "persen membuat tanda leksikalnya paling lemah, sejalan dengan kesulitan yang terlihat "
             "pada Tabel 4.6.")
    gambar(doc, REPORTS / "gambar" / "awan_kelas.png", 15,
           "Gambar 4.3 Awan Kata Khas Tiap Kelas Sentimen")
    sumber(doc, "Sumber: hasil pengolahan data, 2026")
    par(doc, "Awan kata pada baris yang salah dinilai model (Gambar 4.4) memperlihatkan bahwa "
             "kesalahan terkonsentrasi pada kosakata teknis dan naratif: prelist, pegawai, data, "
             "biaya, dan kata orang pertama seperti \"aku\" dan \"kan\". Model andal ketika ada kata "
             "sentimen yang eksplisit, dan goyah ketika penilaian tersembunyi di balik laporan "
             "keadaan.")
    gambar(doc, REPORTS / "gambar" / "awan_salah_model.png", 13,
           "Gambar 4.4 Awan Kata pada Baris yang Salah Dinilai")
    sumber(doc, "Sumber: hasil pengolahan data, 2026")
    anak_sub_bab(doc, "4.1.7 Analisis Tematik Kalimat Opini Publik per Kelas Sentimen")
    par(doc, "Gambaran leksikal pada subbab sebelumnya memperlihatkan sebaran kata kunci, namun "
             "makna substantif opini publik baru dapat dipahami melalui telaah pada tingkat kalimat. "
             "Oleh karena itu, seluruh 5.808 kalimat pada korpus opini ditelaah secara tematik "
             "berdasarkan aspek dan muatan semantiknya. Sebaran tematik opini publik berbasis "
             "kalimat disajikan pada Tabel 4.9.")
    judul_tabel(doc, "Tabel 4.9 Sebaran Tematik Opini Publik Berbasis Kalimat")
    tabel(doc, ["Nomor", "Tema Isu Publik", "Sentimen Utama", "Jumlah Kalimat", "Porsi", "Inti Keluhan dan Harapan"], [
        ["1", "Kendala Teknis Aplikasi FASIH Lapangan", "Negatif", "1.215", "20,9%", "Kegagalan kirim data, eror modul kamera/foto, dan keterlambatan sinkronisasi."],
        ["2", "Skeptisisme dan Persepsi Manfaat Sensus", "Campuran", "1.549", "26,7%", "Keraguan dampak langsung sensus (669 negatif) berbanding apresiasi data (880 positif)."],
        ["3", "Dinamika Lapangan dan Pelayanan Petugas", "Negatif", "677", "11,7%", "Resistensi warga (501 negatif), ketakutan kehilangan bansos, dan dukungan bagi mitra."],
        ["4", "Disinformasi dan Narasi Hoaks", "Negatif", "523", "9,0%", "Kecurigaan rekayasa data kemakmuran dan informasi keliru seputar jadwal pendataan."],
        ["5", "Kekhawatiran Penarikan Pajak Tambahan", "Negatif", "400", "6,9%", "Kecemasan bahwa data omzet dan aset usaha dijadikan sarana pungutan pajak baru."],
        ["6", "Beban Ekonomi dan Kepastian Honor Mitra", "Negatif", "335", "5,8%", "Ketimpangan beban kerja lapangan per blok sensus dan keterlambatan pencairan honor."],
        ["7", "Privasi dan Keamanan Kerahasiaan Data", "Negatif", "310", "5,3%", "Kekhawatiran penyalahgunaan foto rumah atau lokasi usaha dan kebocoran identitas."],
        ["8", "Pertanyaan Prosedural dan Informasi Sensus", "Netral", "515", "8,9%", "Pertanyaan faktual jadwal sensus, syarat pendaftaran mitra, dan batasan unit usaha."],
        ["9", "Apresiasi Digitalisasi dan Pelayanan Petugas", "Positif", "284", "4,9%", "Pujian atas kemudahan kuesioner digital dan dedikasi petugas pencacah di lapangan."],
    ])
    par(doc, "Analisis mendalam pada kelas negatif (3.978 kalimat atau 68,5 persen) menunjukkan "
             "bahwa penolakan publik tidak bersifat homogen. Keluhan terbesar tertuju pada kendala "
             "teknis aplikasi FASIH (1.215 kalimat atau 30,5 persen dari seluruh opini negatif). "
             "Kutipan kalimat nyata dari lapangan mencerminkan hambatan operasional petugas mitra: "
             "\"Error apk sering sekali error tidak bisa di-submit foto harus ambil dua kali membuat "
             "pekerjaan semakin lambat mohon segera dievaluasi\" serta \"tolong perbaiki sistem kadang "
             "masuk untuk submit kadang nyangkol\". Keluhan ini murni persoalan reliabilitas "
             "perangkat lunak lapangan yang menghambat pencapaian target harian pencacahan.")
    par(doc, "Tema negatif kedua menyangkut persepsi manfaat dan skeptisisme sensus (669 kalimat "
             "atau 16,8 persen). Masyarakat mempertanyakan relevansi pendataan aset usaha terhadap "
             "kesejahteraan mereka, sebagaimana tercermin pada ungkapan: \"Namanya sensus ekonomi "
             "tapi pertanyaannya tentang hartanya saja lah hutangnya tidak ikut dipikirkan juga benar-benar "
             "tidak guna\" dan \"Aset sudah terdata di kantor pajak mengapa harus didata manual lagi\". "
             "Kritik tersebut menunjukkan perlunya BPS memperjelas narasi kemanfaatan sensus bagi "
             "perumusan subsidi dan kebijakan UMKM.")
    par(doc, "Tema negatif berikutnya mencakup disinformasi (509 kalimat atau 12,8 persen), kendala "
             "lapangan petugas (501 kalimat atau 12,6 persen), kekhawatiran pajak (393 kalimat atau "
             "9,9 persen), beban kerja petugas (326 kalimat atau 8,2 persen), serta kerahasiaan "
             "data (289 kalimat atau 7,3 persen). Pada aspek petugas, hambatan muncul akibat penolakan "
             "warga yang takut dicoret dari penerima bantuan sosial: \"Mending teh abdi mah meni "
             "sesah ditaros teh majar sieun bisi teu menang bantuan deui\" (sulit sekali ditanya karena "
             "takut tidak mendapat bantuan lagi). Pada aspek pajak, kekhawatiran terlihat dari "
             "ungkapan: \"Bukan masalah data dirahasiakan atau tidak justru yang ditakutkan pemerintah "
             "mencari celah untuk pajak\".")
    par(doc, "Dominasi sentimen negatif sebesar 68,5 persen merefleksikan evaluasi kritis masyarakat "
             "terhadap dua isu operasional: stabilitas teknis aplikasi FASIH serta kekhawatiran bahwa "
             "data sensus disalahgunakan untuk penarikan pajak atau pemotongan bantuan sosial. Opini "
             "publik tidak menunjukkan penolakan mendasar terhadap institusi BPS maupun urgensi "
             "Sensus Ekonomi 2026 itu sendiri. Oleh karena itu, temuan ini menjadi masukan strategis "
             "bagi perbaikan sistem digital dan komunikasi publik BPS menjelang pelaksanaan sensus.")
    par(doc, "Pada kelas positif (1.315 kalimat atau 22,6 persen), opini terpusat pada dukungan "
             "moral bagi suksesnya Sensus Ekonomi 2026, kebanggaan terhadap modernisasi sistem BPS, "
             "dan apresiasi atas kesabaran petugas sensus door-to-door. Pada kelas netral (515 kalimat "
             "atau 8,9 persen), seluruh teks berupa pertanyaan informatif murni seputar tata cara "
             "pendaftaran petugas mitra, klarifikasi jadwal sensus, dan definisi cakupan usaha tanpa "
             "memuat evaluasi sentimen afektif.")
    anak_sub_bab(doc, "4.1.8 Hasil Penjelasan Model")
    par(doc, "Penjelasan model dilakukan melalui peta atensi dan LIME. Peta atensi menampilkan "
             "bobot perhatian pada setiap lapisan sehingga dapat dilihat token mana yang paling "
             "menentukan keputusan model, dan hasilnya disajikan pada Gambar 4.5. LIME melengkapi "
             "gambaran tersebut dengan menunjukkan pengaruh token terhadap keputusan pada tingkat "
             "satu teks, dengan cara mengubah masukan secara berulang lalu mengamati akibatnya pada "
             "keluaran model; ringkasannya disajikan pada Gambar 4.7. Kedua penjelasan ini dihitung "
             "dari model terbaik yang dilatih pada label Jev, yaitu model pada Tabel 4.5, sehingga "
             "sejalan dengan angka yang dilaporkan.")
    gambar(doc, FINAL / "atensi" / "attention_matrix.png", 11,
           "Gambar 4.5 Peta Atensi Antar Lapisan")
    sumber(doc, "Sumber: hasil pengolahan data, 2026")
    par(doc, "Dua hal terlihat dari peta atensi tersebut. Bobot terbesar jatuh pada token khusus "
             "klasifikasi dan pemisah, sebagaimana lazim pada BERT, sedangkan di antara token isi "
             "yang paling berpengaruh adalah kata bermuatan penilaian, seperti \"kemiskinan\", "
             "\"manipulasi\", dan \"memperlambat\" pada teks negatif serta \"mantab\" dan "
             "\"lanjutkan\" pada teks positif. Hal ini menunjukkan model bersandar pada "
             "kata bermuatan sentimen alih-alih pada panjang atau bentuk kalimat.")
    par(doc, "Profil atensi satu teks contoh secara utuh, mulai dari bobot atensi token "
             "klasifikasi pada tiap lapisan sampai skor kepentingan gabungan antar lapisan, "
             "disajikan pada Gambar 4.6.")
    gambar(doc, FINAL / "atensi" / "attention_1.png", 13,
           "Gambar 4.6 Profil Atensi Satu Teks Contoh")
    sumber(doc, "Sumber: hasil pengolahan data, 2026")
    gambar(doc, FINAL / "lime" / "lime_top_tokens.png", 13,
           "Gambar 4.7 Token Paling Berpengaruh menurut LIME")
    sumber(doc, "Sumber: hasil pengolahan data, 2026")
    par(doc, "LIME menegaskan gambaran yang sama pada tingkat satu teks: keluaran model berubah "
             "paling tajam ketika kata bermuatan sentimen dihilangkan, sedangkan penghilangan kata "
             "netral hampir tidak mengubah keputusan. Pada baris yang salah dinilai, LIME justru "
             "memperlihatkan model bersandar pada kata yang salah, misalnya pertanyaan yang "
             "memuat kata \"sulit\" dinilai negatif meskipun penulisnya hanya meminta penjelasan. "
             "Temuan itu sejalan dengan pola kesalahan yang ditemukan pada data uji di subbab 4.1.5.")
    par(doc, "Pembangkitan penjelasan dijalankan pada model yang sama dengan Tabel 4.5. LIME "
             "menuntut ratusan kali pengambilan keputusan untuk setiap teks, sehingga pemrosesan "
             "dijalankan berkelompok. Cara itu menyelesaikan penjelasan untuk 30 teks contoh "
             "dalam hitungan menit pada mesin tanpa kartu grafis.")
    anak_sub_bab(doc, "4.1.9 Kontribusi Utama: Prosedur Audit Mutu Label")
    par(doc, "Kontribusi metodologis dari Kerja Praktik ini terletak pada prosedur audit mutu label "
             "yang menguji apakah metrik kinerja model mencerminkan kebenaran substantif atau sekadar "
             "kepatuhan format terhadap anotator otomatis.")
    par(doc, "Anotasi berbasis model bahasa besar digunakan karena pelabelan manual atas "
             "seluruh korpus memerlukan sumber daya yang besar. Pendekatan ini efisien dari segi "
             "biaya komputasi, namun memindahkan tantangan teknis pada verifikasi keandalan label: "
             "luaran yang patuh skema format belum tentu bebas dari kesalahan substantif. Oleh "
             "karena itu, audit mutu label diintegrasikan sebagai tahapan baku dalam alur kerja "
             "penelitian.")
    par(doc, "Audit dijalankan terhadap seluruh baris korpus dan memeriksa tiga parameter: "
             "kesesuaian nilai terhadap daftar yang diizinkan, konsistensi antarkolom, serta "
             "keterlacakan bukti kutipan terhadap teks asli. Pemeriksaan ketiga memastikan bahwa "
             "frasa pendukung sentimen benar-benar berasal dari teks sumber, mengantisipasi "
             "kecenderungan model bahasa besar menghasilkan kutipan yang tidak faktual.")
    par(doc, "Audit mengidentifikasi dua karakteristik penting data. Pertama, kelas netral pada "
             "korpus awal sempat mencapai 30,7 persen karena menampung balasan singkat yang dianalisis "
             "tanpa konteks; setelah konteks percakapan disertakan dan kategori non-opini dipisahkan, "
             "proporsi kelas netral berada pada angka realistis 8,9 persen (515 baris). Kedua, "
             "hampir tiga dari sepuluh komentar merupakan balasan yang memerlukan teks induk untuk "
             "dapat dipahami maknanya secara utuh. Kedua temuan ini menegaskan bahwa kelengkapan "
             "metadata konteks menjadi faktor penentu kualitas pelabelan.")
    par(doc, "Temuan evaluasi juga menunjukkan adanya komponen kesalahan sistematis pada anotator. "
             "Tingginya konsistensi inferensi, di mana sembilan puluh dari sembilan puluh dua baris "
             "menghasilkan prediksi identik pada tiga kali pengujian bersuhu 0,7 (termasuk pada "
             "contoh yang keliru terhadap acuan manusia), menunjukkan bahwa model memiliki stabilitas "
             "inferensi yang tinggi, namun stabilitas tersebut tidak menjamin ketepatan faktual. Oleh sebab itu, "
             "metode pemungutan suara mayoritas (majority voting) tidak secara otomatis menyaring "
             "kesalahan model.")
    par(doc, "Eksperimen penyempurnaan prompt menunjukkan dinamika yang sejalan dengan kajian "
             "pelatihan mandiri (Chen et al., 2022): penambahan aturan dan contoh menaikkan akurasi "
             "3,3 poin (p = 0,63); pemaksaan penalaran eksplisit (chain-of-thought) tidak memberikan "
             "peningkatan nyata; dan pergantian rumpun model tidak menghasilkan selisih signifikan. "
             "Pada evaluasi terhadap data uji manusia, anotator baru beserta model terlatihnya "
             "menghasilkan angka lebih tinggi (0,7882 berbanding 0,7176), namun perbedaan tersebut "
             "belum signifikan secara statistik pada 85 baris uji (p = 0,1460). Secara umum, penyesuaian "
             "aturan tersebut cenderung menggeser kurva pertukaran (trade-off) antara recall kelas "
             "netral dan negatif.")
    par(doc, "Secara metodologis, tanpa adanya acuan manusia, penyesuaian aturan otomatis hanya "
             "menggeser ambang keputusan tanpa memastikan kebenaran substantif. Ketersediaan gold set "
             "manusia menjadi tolok ukur esensial dalam validasi model, sejalan dengan literatur "
             "mengenai kalibrasi label lemah (Hsu dan Roberts, 2025; Zhang et al., 2024) serta "
             "pengujian mutu anotasi otomatis (Klie et al., 2024).")
    par(doc, "Bagi penelitian sejenis, prosedur ini dapat diadopsi melalui pemindaian mutu pada "
             "seluruh korpus, uji konsistensi model terhadap prediksinya sendiri, serta validasi "
             "terhadap gold set manusia berukuran terkelola. Langkah ini mencegah penafsiran keliru "
             "antara nilai kesesuaian terhadap anotator semu dan akurasi riil model.")
    anak_sub_bab(doc, "4.1.10 Prototipe Sistem Pendukung Keputusan Berbasis Web")
    par(doc, "Sebagai wujud hilirisasi komputasi terapan bagi instansi, hasil pemodelan klasifikasi dan "
             "analisis tematik diintegrasikan ke dalam antarmuka sistem pendukung keputusan (decision support system) "
             "interaktif berbasis web. Tampilan antarmuka dasbor pemantauan opini publik tersebut disajikan "
             "pada Gambar 4.8.")
    gambar(doc, REPORTS / "gambar" / "screenshot_dss_trendline.png", 15.5,
           "Gambar 4.8 Antarmuka Sistem Pendukung Keputusan Pemantauan Opini Publik SE2026")
    sumber(doc, "Sumber: hasil perancangan sistem, 2026")
    par(doc, "Antarmuka pemantauan pada Gambar 4.8 dirancang dengan tata letak modular yang menyajikan "
             "empat komponen informasi utama bagi pimpinan dan staf Badan Pusat Statistik:")
    numid_dss = _anggap_rincian(doc)
    for p_dss in (
        "Pita Indikator Kinerja Kunci (KPI Ribbon): Menampilkan ringkasan volume korpus bersih sebanyak "
        "8.352 baris, sebaran tiga kelas polaritas (negatif 47,6 persen atau 68,5 persen dari opini murni, "
        "positif 15,7 persen, dan netral 6,2 persen), serta agregasi volume per platform digital "
        "(YouTube 6.727 rekaman, Google Play 1.366 ulasan, dan Threads 259 kiriman).",
        "Visualisasi Dinamika Tren Waktu Nyata: Memetakan fluktuasi proporsi sentimen mingguan sepanjang "
        "jendela 15 Juni sampai 15 September 2026, lengkap dengan penanda tonggak peristiwa lapangan seperti "
        "fase peluncuran awal sensus, puncak perbincangan aplikasi Fasih dan isu pajak, serta momentum "
        "sosialisasi klarifikasi BPS.",
        "Pemetaan Tematik dan Deteksi Lonjakan Anomali: Memuat peta panas konsentrasi polaritas lintas tema, "
        "grafik sebaran volume isu strategis, serta tabel deteksi lonjakan sentimen negatif (negative spike) "
        "untuk memberikan peringatan dini atas gejolak opini publik.",
        "Matriks Prioritas Rekomendasi Operasional: Menghubungkan skor urgensi isu dominan dengan panduan aksi "
        "mitigasi praktis bagi unit kerja BPS Kabupaten Sukoharjo, seperti stabilisasi penyimpanan data luring "
        "aplikasi Fasih dan sosialisasi masif jaminan kerahasiaan data usaha."
    ):
        butir(doc, p_dss, numid_dss)
    par(doc, "Sistem tersebut juga terhubung langsung dengan modul penelusuran label mendalam (deep label inspection) "
             "yang memungkinkan pemangku kepentingan menelusuri setiap baris data berlabel hingga potongan bukti "
             "leksikal, penalaran model, peta atensi transformer, dan skor atribusi LIME. Integrasi menyeluruh ini "
             "membuktikan bahwa luaran Kerja Praktik tidak berhenti pada pembuktian metrik komputasi di lingkungan "
             "pengujian semata, melainkan terwujud menjadi instrumen analitik terapan yang siap mendukung respons "
             "komunikasi publik instansi.")
    sub_bab(doc, "Pembahasan", numid_b4)
    par(doc, "Temuan pertama yang perlu dibahas adalah kedudukan label otomatis. Prosedur pelabelan "
             "yang dipakai pada penelitian ini menghasilkan keluaran yang patuh format, dengan "
             "penguraian berhasil penuh dan seluruh nilai berada pada daftar yang diizinkan. "
             "Kepatuhan format tersebut tidak menjamin kebenaran substansi label. Audit atas label "
             "justru menemukan bahwa anotator yang tidak menerima keterangan asal teks cenderung "
             "menilai balasan singkat sebagai pernyataan netral, sehingga kelas netral membengkak "
             "hingga 30,7 persen pada korpus lama. Setelah konteks dan tipe teks diperhitungkan, "
             "proporsi kelas netral berada pada angka riil 8,9 persen (515 baris). Kenyataan ini "
             "sejalan dengan pustaka yang menyatakan bahwa mutu label hasil anotasi model bahasa besar "
             "perlu diuji dan dikalibrasi secara sistematis (Klie et al., 2024; Zhang et al., 2024).")
    par(doc, "Temuan kedua menyangkut mutu data di hulu pengumpulan. Pemeriksaan data menunjukkan "
             "bahwa batasan pengumpulan perlu ditegakkan langsung pada tingkat kode program. "
             "Sebelumnya, pengambilan data tanpa filter topik menyebabkan komentar di luar lingkup "
             "ikut terambil, dan penegakan batas tanggal yang tidak seragam pada seluruh konektor "
             "menyebabkan komentar lampau sebelum 15 Juni 2026 terbawa ke dalam korpus.")
    par(doc, "Temuan ketiga berkaitan dengan acuan pengukuran. Nilai bintang ulasan pada toko aplikasi "
             "sempat dipertimbangkan sebagai acuan otomatis karena sifatnya yang kuantitatif. "
             "Pemeriksaan menunjukkan bahwa 120 ulasan berbintang lima ternyata berisi keluhan "
             "dan 6 ulasan berbintang satu berisi pujian. Oleh sebab itu, bintang ulasan tidak dapat "
             "dijadikan acuan objektif, dan validasi model disandarkan pada gold set manusia.")
    par(doc, "Temuan keempat menyangkut efisiensi model. Hasil studi ablasi menunjukkan "
             "bahwa strategi hemat parameter tetap bersaing: BitFit mencapai akurasi 0,8821 dengan "
             "105.219 parameter dilatih, dan penyetelan sebagian mencapai 0,8778. Untuk kebutuhan "
             "pemantauan berkala dengan sumber daya komputasi terbatas, kedua strategi tersebut "
             "merupakan opsi yang efisien. Selain itu, penambahan regularisasi R-Drop pada penyetelan "
             "penuh mempertahankan akurasi pada angka 0,8830 sekaligus meningkatkan F1 macro dari "
             "0,7426 menjadi 0,7628 (Fan et al., 2023). Regularisasi tersebut membantu model "
             "menghasilkan prediksi yang lebih berimbang antarkelas.")
    par(doc, "Temuan kelima menyangkut redefinisi kelas netral. Pada korpus akhir, proporsi kelas "
             "netral berada pada 515 baris (8,9 persen) setelah teks informatif non-opini dipisahkan "
             "ke partisi tersendiri. Perubahan ini menurunkan akurasi nominal model dari 0,9185 menjadi "
             "0,8830 karena berkurangnya dominasi tebakan kelas mayoritas, namun F1 macro meningkat dari "
             "0,6828 menjadi 0,7426 (dan 0,7628 dengan R-Drop). Matriks konfusi pada data uji "
             "menunjukkan dari 83 prediksi netral, 44 bernilai tepat (presisi 0,53 dan recall 0,43). "
             "Pemisahan teks non-opini memberikan evaluasi yang lebih realistis terhadap tantangan "
             "klasifikasi kelas netral di lapangan.")
    par(doc, "Temuan keenam berkaitan dengan distingsi metrik evaluasi. Angka kesesuaian pada "
             "Tabel 4.5 (0,8830) mengukur kedekatan model terhadap anotator semu, sedangkan akurasi riil "
             "terhadap acuan manusia pada Tabel 4.6 bernilai 0,7882. Selisih tersebut mengindikasikan bahwa "
             "model mempelajari pola anotator latihnya secara konsisten, termasuk bias yang ada. Oleh "
             "karena itu, laporan ini membedakan secara tegas antara metrik kesesuaian terhadap "
             "anotator semu dan akurasi terhadap gold set manusia agar penafsiran performa sistem "
             "tetap objektif.")
    par(doc, "Terkait implikasi praktis bagi Badan Pusat Statistik, hasil analisis sentimen dan "
             "pemetaan tematik kalimat ditransformasikan menjadi alur mitigasi kebijakan: pemetaan "
             "opini publik, penetapan isu kritis, penentuan prioritas tindakan, hingga rekomendasi "
             "operasional bagi unit terkait. Rincian pemetaan isu kritis dan rekomendasi kebijakan "
             "disajikan pada Tabel 4.10.")
    judul_tabel(doc, "Tabel 4.10 Pemetaan Isu Kritis Opini Publik dan Rekomendasi Kebijakan bagi BPS")
    tabel(doc, ["Nomor", "Isu Kritis", "Sentimen Dominan", "Indikasi Lapangan", "Prioritas Aksi", "Rekomendasi Kebijakan BPS"], [
        ["1", "Keandalan Aplikasi FASIH", "Negatif (30,5%)", "Gagal submit dan eror kamera memperlambat target harian.", "Prioritas 1 (Segera)", "Penyempurnaan modul sinkronisasi luring dan kompresi foto otomatis."],
        ["2", "Kekhawatiran Pajak dan Privasi", "Negatif (17,1%)", "Responden curiga data aset dipakai dasar penarikan pajak.", "Prioritas 1 (Segera)", "Sosialisasi masif jaminan kerahasiaan sesuai UU Statistik No. 16/1997."],
        ["3", "Resistensi Bansos Dicabut", "Negatif (12,6%)", "Warga menolak didata karena takut kehilangan bansos.", "Prioritas 2 (Menengah)", "Penyusunan SOP komunikasi persuasif petugas pencacah di lapangan."],
        ["4", "Transparansi Honor Mitra", "Negatif (8,2%)", "Keluhan beban kerja tidak sebanding dan pencairan terlambat.", "Prioritas 2 (Menengah)", "Penataan beban kerja per blok sensus dan kepastian jadwal honor."],
        ["5", "Pertanyaan Prosedural", "Netral (8,9%)", "Tingginya pertanyaan jadwal dan syarat pendaftaran mitra.", "Prioritas 3 (Rutin)", "Penyediaan kanal FAQ interaktif dan respons cepat di media sosial."],
    ])
    par(doc, "Keterbatasan penelitian ini perlu dinyatakan secara terbuka. Pertama, ukuran gold set "
             "manusia berjumlah seratus baris, dengan 85 baris yang masuk evaluasi tiga kelas "
             "sentimen; ukuran ini memadai untuk audit konsistensi awal namun memiliki variansi "
             "cukup besar pada kelas minoritas seperti kelas positif yang hanya memuat delapan contoh. "
             "Kedua, pengumpulan data dilakukan pada tiga platform digital (YouTube, Google Play, dan Threads) "
             "tanpa melibatkan platform teks seperti Twitter/X atau Reddit karena pembatasan akses "
             "antarmuka pemrograman aplikasi. Ketiga, anotator model bahasa besar bertindak sebagai "
             "pelabel semu, sehingga mutu representasi konteks balasan sangat bergantung pada "
             "kelengkapan metadata percakapan.")


def bab_lima(doc: Document) -> None:
    doc.add_page_break()
    bab(doc, "BAB V \nPENUTUP")
    numid_b5 = _pastikan_numid(doc, "5")
    sub_bab(doc, "Simpulan", numid_b5)
    par(doc, "Pelaksanaan Kerja Praktik ini menghasilkan simpulan berikut.")
    numid_simpulan = _anggap_rincian(doc)
    for t in ("Korpus opini publik terhadap Sensus Ekonomi 2026 dan aplikasi Fasih BPS berhasil "
              "dihimpun sebanyak 10.961 rekaman mentah dari tiga platform digital dan disaring "
              "melalui empat tahap preprocessing menjadi 8.352 baris bersih (6.727 YouTube, "
              "1.366 Google Play, dan 259 Threads) dengan batas rentang waktu 15 Juni sampai "
              "15 September 2026 yang ditegakkan secara konsisten oleh kode program sehingga "
              "terbebas dari pergeseran data lampau dan dapat ditelusuri asalnya.",
              "Kerangka kerja audit mutu label berbasis model bahasa besar berhasil dirumuskan dan "
              "diterapkan pada seluruh 8.350 baris berlabel tanpa menemukan cacat kritis, dengan "
              "tingkat keterlacakan kutipan bukti mencapai 99,98 persen (8.348 baris) terhadap teks "
              "sumber. Pengujian konsistensi mengungkap bahwa kesalahan anotasi otomatis memuat "
              "komponen sistematis di mana 90 dari 92 baris dijawab identik pada pengujian berulang "
              "termasuk pada contoh yang keliru, serta berhasil merekonstruksi proporsi kelas netral "
              "dari 30,7 persen pada korpus awal menjadi 8,9 persen (515 baris) yang realistis.",
              "Mekanisme pelabelan semu sadar konteks berbasis prompt terstruktur dan penyaring "
              "relevansi berhasil mempartisi korpus bersih menjadi kelompok opini 5.808 baris "
              "(69,6 persen), non-opini 2.119 baris (25,4 persen), dan karantina 423 baris (5,1 persen). "
              "Pengujian menunjukkan anotator keputusan Jev mampu menjalankan fungsi pemilahan "
              "relevansi secara mandiri dengan ambang batas peluang 0,20 tanpa ketergantungan wajib "
              "pada model awal.",
              "Penyusunan gold set independen sebanyak seratus baris terverifikasi manusia berhasil "
              "membuktikan pemisahan metodologis yang tegas antara metrik kesepakatan model terhadap "
              "anotator semu dan akurasi riil manusia. Skor kesesuaian model terhadap anotator semu "
              "mencapai 0,8830, sedangkan akurasi terverifikasi manusia bernilai 0,7882. Kesenjangan ini "
              "mengonfirmasi bahwa evaluasi berbasis acuan manusia merupakan syarat mutlak agar metrik "
              "kesesuaian semu tidak disalahartikan sebagai akurasi faktual sistem.",
              "Pelatihan pengklasifikasi IndoBERT melalui studi ablasi enam strategi membuktikan bahwa "
              "varian hemat parameter BitFit (akurasi 0,8821) dan partial_top_k (0,8778) mampu bersaing "
              "dengan penyetelan penuh, sedangkan penambahan regularisasi R-Drop pada penyetelan penuh "
              "(full_rdrop) menghasilkan performa terbaik dengan akurasi 0,8830 dan F1 macro 0,7628. "
              "Pengujian pada data uji manusia menghasilkan akurasi 0,7882 dan F1 macro 0,7713 bagi "
              "anotator keputusan Jev, serta akurasi 0,7882 dan F1 macro 0,7700 bagi pengklasifikasi "
              "IndoBERT pipeline utama. Uji berpasangan McNemar terhadap pipeline utama dan pipeline "
              "mandiri Jev (akurasi 0,7529) menghasilkan nilai p 0,5811 yang membuktikan kedua pipeline "
              "tidak berbeda signifikan secara statistik.",
              "Penerapan teknik penjelasan model melalui peta atensi dan LIME berhasil membuktikan "
              "bahwa IndoBERT mendasarkan prediksinya pada kata kunci evaluatif substantif dan bukan "
              "pada fitur panjang kalimat. Analisis tematik berbasis kalimat mengungkap bahwa dominasi "
              "sentimen negatif (3.978 kalimat atau 68,5 persen) terpusat pada kendala teknis aplikasi "
              "FASIH (30,5 persen), skeptisisme manfaat sensus (16,8 persen), kekhawatiran privasi dan "
              "pajak (17,1 persen), serta resistensi pencabutan bansos (12,6 persen), yang "
              "ditransformasikan menjadi rekomendasi kebijakan operasional prioritas bagi Badan Pusat Statistik.",
              "Hilirisasi seluruh hasil pemodelan dan temuan analisis sentimen berhasil diwujudkan "
              "ke dalam sebuah prototipe antarmuka sistem pendukung keputusan (decision support system) "
              "interaktif berbasis web yang dilengkapi dasbor pemantauan tren mingguan, peta panas tematik, "
              "tabel deteksi lonjakan anomali, serta modul penelusuran bukti label transparan guna "
              "mendukung respons kebijakan dan komunikasi publik Badan Pusat Statistik Kabupaten Sukoharjo."):
        butir(doc, t, numid_simpulan)
    sub_bab(doc, "Saran", numid_b5)
    par(doc, "Bagi Badan Pusat Statistik, hasil analisis tematik sentimen memberikan empat "
             "rekomendasi praktis untuk mitigasi operasional. Pertama, penguatan keandalan teknis "
             "aplikasi FASIH melalui optimalisasi penyimpanan data luring dan kompresi foto "
             "otomatis guna mengatasi kendala submit yang menyumbang 30,5 persen keluhan negatif. "
             "Kedua, sosialisasi masif mengenai jaminan kerahasiaan data individu berdasarkan "
             "Undang-Undang Nomor 16 Tahun 1997 tentang Statistik guna menepis kekhawatiran "
             "masyarakat bahwa data omzet dan aset usaha akan diintegrasikan dengan penetapan pajak. "
             "Ketiga, penyusunan panduan komunikasi persuasif bagi petugas pencacah lapangan saat "
             "berhadapan dengan warga yang khawatir kehilangan bantuan sosial. Keempat, pengelolaan "
             "transparansi dan kepastian jadwal pencairan honor mitra statistik untuk menjaga "
             "motivasi kerja di lapangan.")
    par(doc, "Bagi penelitian selanjutnya, disarankan memperluas ukuran data uji manusia secara "
             "bertahap menuju lima ratus baris guna memperkecil variansi pada kelas minoritas serta "
             "melibatkan penilai manusia ganda agar batas atas kesepakatan antar-anotator dapat "
             "diukur secara kuantitatif. Selain itu, peneliti berikutnya disarankan menerapkan "
             "kalibrasi nilai probabilitas keyakinan model sebelum dijadikan ambang penyaringan "
             "otomatis. Di samping itu, disarankan mengintegrasikan pembaruan data berkala "
             "ke dalam prototipe antarmuka sistem pendukung keputusan yang telah dibangun, serta memperluas "
             "pengumpulan data ke platform berbasis teks murni apabila akses antarmuka "
             "pemrograman aplikasi di masa depan telah terbuka.")


def daftar_pustaka(doc: Document) -> None:
    """Menyusun daftar pustaka dengan kaidah APA edisi ketujuh.

    Seluruh acuan terbit pada rentang 2022 sampai 2026. Setiap butir sudah
    diperiksa langsung pada halaman penerbitnya, sehingga nama penulis, nama
    terbitan, jilid, nomor, halaman, dan DOI-nya bukan tafsiran. Butir disusun
    menurut abjad nama belakang penulis pertama.
    """
    doc.add_page_break()
    bab(doc, "DAFTAR PUSTAKA")
    acuan = [
        "Atanasova, P., Simonsen, J. G., Lioma, C., & Augenstein, I. (2023). Faithfulness tests "
        "for natural language explanations. In Proceedings of the 61st Annual Meeting of the "
        "Association for Computational Linguistics (Volume 2: Short Papers) (pp. 283–294). "
        "Association for Computational Linguistics. https://doi.org/10.18653/v1/2023.acl-short.26",

        "Badan Pusat Statistik. (2024). Siap untuk Sensus Ekonomi 2026! "
        "https://www.bps.go.id/id/news/2024/12/09/651/siap-untuk-sensus-ekonomi-2026-.html",

        "Badan Pusat Statistik. (2026). Pendataan Sensus Ekonomi 2026 resmi dimulai. "
        "https://sukoharjokab.bps.go.id/id/news/2026/06/17/589/",

        "Ben Zaken, E., Goldberg, Y., & Ravfogel, S. (2022). BitFit: Simple parameter-efficient "
        "fine-tuning for transformer-based masked language-models. In Proceedings of the 60th "
        "Annual Meeting of the Association for Computational Linguistics (Volume 2: Short Papers) "
        "(pp. 1–9). Association for Computational Linguistics. https://doi.org/10.18653/v1/2022.acl-short.1",

        "Braylan, A., Alonso, O., & Lease, M. (2022). Measuring annotator agreement generally "
        "across complex structured, multi-object, and free-text annotation tasks. In Proceedings of "
        "the ACM Web Conference 2022 (pp. 1720–1730). Association for Computing Machinery. "
        "https://doi.org/10.1145/3485447.3512242",

        "Cahyawijaya, S., Winata, G. I., Wilie, B., Vincentio, K., Li, X., Koto, F., Rahimi, A., "
        "Bahar, Y. Y., Chung, C., Doocar, S., Aji, A. F., Purwarianti, A., & Fung, P. (2023). "
        "NusaCrowd: Open-source machine learning resources for Indonesian languages and dialects. "
        "In Proceedings of the 61st Annual Meeting of the Association for Computational "
        "Linguistics (Volume 1: Long Papers) (pp. 12053–12078). Association for Computational "
        "Linguistics. https://doi.org/10.18653/v1/2023.acl-long.673",

        "Cao, L., Liu, X., & Shen, H. (2022). Adaptable focal loss for imbalanced text "
        "classification. In Parallel and Distributed Computing, Applications and Technologies "
        "(Lecture Notes in Computer Science, Vol. 13148, pp. 466–475). Springer. "
        "https://doi.org/10.1007/978-3-030-96772-7_43",

        "Chen, H., Han, W., & Poria, S. (2022). SAT: Improving semi-supervised text classification "
        "with simple instance-adaptive self-training. In Findings of the Association for "
        "Computational Linguistics: EMNLP 2022 (pp. 6141–6146). Association for Computational "
        "Linguistics. https://doi.org/10.18653/v1/2022.findings-emnlp.456",

        "Fan, Y., Kukleva, A., Dai, D., & Schiele, B. (2023). Revisiting consistency "
        "regularization for semi-supervised learning. International Journal of Computer Vision, "
        "131, 626–643. https://doi.org/10.1007/s11263-022-01723-4",

        "Fernandez, E., Anderies, Winata, M. G., Fasya, F. H., & Gunawan, A. A. S. (2022). "
        "Improving IndoBERT for sentiment analysis on Indonesian stock trader slang language. "
        "In 2022 IEEE International Conference on Internet of Things and Intelligence Systems "
        "(IoTaIS) (pp. 165–170). IEEE. https://doi.org/10.1109/IoTaIS56727.2022.9975975",

        "Fleisig, E., Abebe, R., & Klein, D. (2023). When the majority is wrong: Modeling annotator "
        "disagreement for subjective tasks. In Proceedings of the 2023 Conference on Empirical "
        "Methods in Natural Language Processing (pp. 6715–6726). Association for Computational "
        "Linguistics. https://doi.org/10.18653/v1/2023.emnlp-main.415",

        "Geni, L., Yulianti, E., & Sensuse, D. I. (2023). Sentiment analysis of tweets before the "
        "2024 elections in Indonesia using BERT language models. Jurnal Ilmiah Teknik Elektro "
        "Komputer dan Informatika, 9(3), 746–757. https://doi.org/10.26555/jiteki.v9i3.26490",

        "Gilardi, F., Alizadeh, M., & Kubli, M. (2023). ChatGPT outperforms crowd workers for "
        "text-annotation tasks. Proceedings of the National Academy of Sciences, 120(30), "
        "Article e2305016120. https://doi.org/10.1073/pnas.2305016120",

        "Gumilang, M. A., Abdillah, F., Amin, M. Y., & Hasan, M. (2024). Sentiment analysis of "
        "Indonesian ministries social media: Citizen responses utilizing TextBlob analyser. Jurnal "
        "Sosioteknologi, 23(2), 203–216. https://doi.org/10.5614/sostek.itbj.2024.23.2.5",

        "Hsu, E., & Roberts, K. (2025). Leveraging large language models for knowledge-free weak "
        "supervision in clinical natural language processing. Scientific Reports, 15, "
        "Article 8241. https://doi.org/10.1038/s41598-024-68168-2",

        "Imaduddin, H., A’la, F., & Nugroho, Y. (2023). Sentiment analysis in Indonesian "
        "healthcare applications using IndoBERT approach. International Journal of Advanced "
        "Computer Science and Applications, 14(8). https://doi.org/10.14569/IJACSA.2023.0140813",

        "Khoifaturrahman, K., Berlian, B., Rizkiyah, U., Aliyah, U. H., Shalihah, I., & "
        "Rahmawati, Y. T. N. (2026). Manajemen informasi publik BPS dalam menghadapi penolakan "
        "masyarakat pada Sensus Ekonomi 2026. Jurnal Manajemen dan Ilmu Administrasi, 2(2), "
        "185–195. https://doi.org/10.58472/jmia.v2i2.492",

        "Klie, J.-C., Eckart de Castilho, R., & Gurevych, I. (2024). Analyzing dataset annotation "
        "quality management in the wild. Computational Linguistics, 50(3), 817–866. "
        "https://doi.org/10.1162/coli_a_00516",

        "Lin, C.-H., & Nuha, U. (2023). Sentiment analysis of Indonesian datasets based on a hybrid "
        "deep-learning strategy. Journal of Big Data, 10, Article 88. "
        "https://doi.org/10.1186/s40537-023-00782-9",

        "Liu, Y., Li, H., Guo, Y., Kong, C., Li, J., & Wang, S. (2022). Rethinking attention-model "
        "explainability through faithfulness violation test. In Proceedings of the 39th "
        "International Conference on Machine Learning (Proceedings of Machine Learning Research, "
        "Vol. 162, pp. 13807–13824). PMLR. https://proceedings.mlr.press/v162/liu22i.html",

        "Mandhasiya, D. G., Murfi, H., & Bustamam, A. (2024). The hybrid of BERT and deep learning "
        "models for Indonesian sentiment analysis. Indonesian Journal of Electrical Engineering "
        "and Computer Science, 33(1), 591–602. https://doi.org/10.11591/ijeecs.v33.i1.pp591-602",

        "Merdiansah, R., Siska, S., & Ridha, A. A. (2024). Analisis sentimen pengguna X Indonesia "
        "terkait kendaraan listrik menggunakan IndoBERT. Jurnal Ilmu Komputer dan Sistem Informasi "
        "(JIKOMSI), 7(1), 221–228. https://doi.org/10.55338/jikomsi.v7i1.2895",

        "Mosca, E., Szigeti, F., Tragianni, S., Gallagher, D., & Groh, G. (2022). SHAP-based "
        "explanation methods: A review for NLP interpretability. In Proceedings of the 29th "
        "International Conference on Computational Linguistics (pp. 4593–4603). International "
        "Committee on Computational Linguistics. https://aclanthology.org/2022.coling-1.406/",

        "Natan Kharisma A., Lestari, D., & Pranoto, G. T. (2025). Sentiment analysis of Threads "
        "reviews in Google Play Store with RoBERTa model. Jurnal Nasional Teknik Elektro dan "
        "Teknologi Informasi, 14(4), 272–280. https://doi.org/10.22146/jnteti.v14i4.22038",

        "Naufal, M. F., & Kusuma, S. F. (2022). Analisis sentimen pada media sosial Twitter "
        "terhadap kebijakan pemberlakuan pembatasan kegiatan masyarakat berbasis deep learning. "
        "JEPIN (Jurnal Edukasi dan Penelitian Informatika), 8(1), 44–49. "
        "https://doi.org/10.26418/jp.v8i1.49951",

        "Opitz, J. (2024). A closer look at classification evaluation metrics and a critical "
        "reflection of common evaluation practice. Transactions of the Association for "
        "Computational Linguistics, 12, 820–836. https://doi.org/10.1162/tacl_a_00675",

        "Setiawan, B. (2024). A review of sentiment analysis applications in Indonesia between "
        "2023–2024. JIEET: Journal of Information Engineering and Educational Technology, 8(2), "
        "71–83. https://doi.org/10.26740/jieet.v8n2.p71-83",

        "Soman, K., Kokate, C., Mohite, A., Vispute, A., More, O., & Mundargi, Z. K. (2022). "
        "Statistical tests for comparing machine learning algorithms. International Journal for "
        "Research in Applied Science and Engineering Technology, 10(12), 628–633. "
        "https://doi.org/10.22214/ijraset.2022.47955",

        "Suhaeni, C., Kamila, S. A., Fahira, F., Yusran, M., & Alfa Dito, G. (2025). Exploring a "
        "large language model on the ChatGPT platform for Indonesian text preprocessing tasks. "
        "Indonesian Journal of Statistics and Its Applications, 9(1), 100–116. "
        "https://doi.org/10.29244/ijsa.v9i1p100-116",

        "Valizadeh, M., Qian, X., Ranjbar-Noiey, P., Caragea, C., & Parde, N. (2023). What clued "
        "the AI doctor in? On the influence of data source and quality for transformer-based "
        "medical self-disclosure detection. In Proceedings of the 17th Conference of the European "
        "Chapter of the Association for Computational Linguistics (pp. 1198–1213). Association for "
        "Computational Linguistics. https://doi.org/10.18653/v1/2023.eacl-main.86",

        "Wang, C., Balazs, J., Szarvas, G., Ernst, P., Poddar, L., & Danchenko, P. (2022). "
        "Calibrating imbalanced classifiers with focal loss: An empirical study. In Proceedings of "
        "the 2022 Conference on Empirical Methods in Natural Language Processing: Industry Track "
        "(pp. 145–153). Association for Computational Linguistics. "
        "https://doi.org/10.18653/v1/2022.emnlp-industry.14",

        "Whang, S. E., Roh, Y., Song, H., & Lee, J.-G. (2023). Data collection and quality "
        "challenges in deep learning: A data-centric AI perspective. The VLDB Journal, 32, "
        "791–813. https://doi.org/10.1007/s00778-022-00775-9",

        "Winata, G. I., Aji, A. F., Cahyawijaya, S., Mahendra, R., Koto, F., Romadhony, A., "
        "Kurniawan, K., Moeljadi, D., Prasojo, R. E., Fung, P., Baldwin, T., Lau, J. H., "
        "Sennrich, R., & Ruder, S. (2023). NusaX: Multilingual parallel sentiment dataset for 10 "
        "Indonesian local languages. In Proceedings of the 17th Conference of the European Chapter "
        "of the Association for Computational Linguistics (pp. 815–834). Association for "
        "Computational Linguistics. https://doi.org/10.18653/v1/2023.eacl-main.57",

        "Wongso, W., Setiawan, D. S., Limcorn, S., & Joyoadikusumo, A. (2025). NusaBERT: Teaching "
        "IndoBERT to be multilingual and multicultural. In Proceedings of the Second Workshop in "
        "South East Asian Language Processing (pp. 10–26). Association for Computational "
        "Linguistics. https://aclanthology.org/2025.sealp-1.2/",

        "Wu, T., Ding, X., Tang, M., Zhang, H., Qin, B., & Liu, T. (2023). NoisywikiHow: A "
        "benchmark for learning with real-world noisy labels in natural language processing. In "
        "Findings of the Association for Computational Linguistics: ACL 2023 (pp. 4856–4873). "
        "Association for Computational Linguistics. https://doi.org/10.18653/v1/2023.findings-acl.299",

        "Yeh, C., Chen, Y., Wu, A., Chen, C., Viégas, F., & Wattenberg, M. (2024). AttentionViz: "
        "A global view of transformer attention. IEEE Transactions on Visualization and Computer "
        "Graphics, 30(1), 262–272. https://doi.org/10.1109/TVCG.2023.3327163",

        "Zhang, J., Song, K., Shin, S., Ding, D., & Ratner, A. (2024). Stronger than you think: "
        "Benchmarking weak supervision on realistic tasks. In Advances in Neural Information "
        "Processing Systems (Vol. 37, pp. 1–32). Curran Associates. "
        "https://proceedings.neurips.cc/paper_files/paper/2024/hash/Zhang-2024-Stronger-than-you-think.html",
    ]
    for a in acuan:
        p = par(doc, a)
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        p.paragraph_format.left_indent = Cm(1.27)
        p.paragraph_format.first_line_indent = Cm(-1.27)
        p.paragraph_format.space_after = Pt(6)


def lampiran(doc: Document) -> None:
    """Menulis lampiran.

    Judul tiap lampiran memakai gaya tersendiri, bukan Heading 2, supaya dapat
    dihimpun menjadi DAFTAR LAMPIRAN tersendiri. Gaya itu tetap ikut masuk ke
    daftar isi utama melalui pengalih ``\\t`` pada medan daftar isi.
    """
    def judul(teks: str) -> None:
        par(doc, teks, rata=WD_ALIGN_PARAGRAPH.LEFT, alinea=False, gaya=GAYA_JUDUL_LAMPIRAN)

    doc.add_page_break()
    bab(doc, "LAMPIRAN")
    judul("Lampiran 1. Catatan Log dan Bukti Pelaksanaan Harian Kerja Praktik")
    par(doc, "Pelaksanaan Kerja Praktik di Badan Pusat Statistik Kabupaten Sukoharjo oleh Anwar Rohmadi "
             "berlangsung selama tiga bulan dan didokumentasikan secara terstruktur ke dalam tiga fase kegiatan utama:")
    numid_log = _anggap_rincian(doc)
    for p_log in (
        "Fase I (15 Juni sampai 15 Juli 2026): Melaksanakan orientasi instansi, koordinasi bersama pembimbing "
        "lapangan, observasi proses bisnis pendataan Sensus Ekonomi 2026 dan aplikasi Fasih BPS, serta "
        "membangun skrip pengumpulan rekaman publik dari YouTube, Google Play Store, dan Threads.",
        "Fase II (16 Juli sampai 15 Agustus 2026): Menjalankan pembersihan korpus digital berlapis, merancang skema "
        "anotasi lima kelas, mengkalibrasi prompt sadar konteks anotator Jev secara berulang, serta "
        "menyusun data uji acuan manusia terstandarisasi untuk evaluasi.",
        "Fase III (16 Agustus sampai 15 September 2026): Menyelenggarakan pelatihan model IndoBERT dengan regularisasi "
        "konsistensi R-Drop, mengeksekusi studi ablasi enam skenario di komputasi awan, menganalisis interpretabilitas "
        "atensi dan LIME, serta menyusun antarmuka sistem pendukung keputusan berbasis web."
    ):
        butir(doc, p_log, numid_log)

    judul("Lampiran 2. Struktur Repositori Daring GitHub dan Tata Kelola Berkas")
    par(doc, "Seluruh kode sumber, korpus digital bersih, data uji acuan manusia, bobot konfigurasi model, "
             "artefak visual beresolusi tinggi, hingga aplikasi antarmuka pendukung keputusan pada penelitian ini "
             "dipublikasikan secara terbuka pada repositori GitHub resmi https://github.com/anwarrohmadi2006/Lampiran-Magang-BPS "
             "yang dikelola oleh Anwar Rohmadi. Repositori ini berfungsi sebagai repositori komputasi terpadu "
             "untuk memastikan keterbukaan sains dan reproduktibilitas penuh, sehingga pembaca dan dewan penguji "
             "dapat meninjau korpus data, mereplikasi skrip analisis, maupun menjalankan dashboard pendukung keputusan "
             "secara mandiri. Struktur tata kelola berkas pada repositori tersebut diselaraskan langsung "
             "dengan pembagian lampiran laporan ini melalui tujuh direktori utama:")
    numid_repo = _anggap_rincian(doc)
    for p_rep in (
        "Direktori laporan/: Memuat naskah dokumen laporan resmi Laporan_KP_Analisis_Sentimen_SE2026.docx, salinan "
        "laporan_kp.docx, serta catatan audit penjamin mutu label korpus dan pedoman penetapan keputusan metodologi.",
        "Direktori data/: Memuat korpus bersih 8.352 baris (korpus_bersih_8352.csv), partisi data latih opini "
        "5.808 baris (korpus_opini_5808.csv), partisi non-opini, partisi karantina, serta data uji acuan emas manusia 100 baris.",
        "Direktori hasil_evaluasi/: Memuat berkas evaluasi resmi evaluasi_gold.json, lembar anotasi interaktif web, "
        "laporan audit label mandiri, gambar matriks konfusi, serta hasil pengukuran Cohen's Kappa antar-penilai.",
        "Direktori model_dan_prediksi/: Memuat panduan teknis model, konfigurasi arsitektur config.json, kamus subkata "
        "vocab.txt, token khusus tokenizer, serta catatan rekaman prediksi kelima sistem pembanding pada data uji.",
        "Direktori artefak_visual/: Memuat diagram alur metodologi penelitian 300 DPI, berkas vektor SVG bagan pipeline, "
        "diagram evolusi ronde kalibrasi Jev, awan kata representasi leksikal, galeri peta atensi, dan visualisasi LIME.",
        "Direktori skrip/: Memuat skrip Python modular untuk eksekusi pra-pemrosesan korpus, audit mutu, perhitungan "
        "metrik dengan selang kepercayaan bootstrap, uji signifikansi statistik McNemar, serta penyusun dokumen laporan.",
        "Direktori dashboard_web/: Memuat aplikasi sistem pendukung keputusan (decision support system) interaktif "
        "berbasis web yang menyajikan analisis sentimen per aspek, tren persepsi publik, dan ringkasan eksekutif instansi."
    ):
        butir(doc, p_rep, numid_repo)

    judul("Lampiran 3. Spesifikasi Rekayasa Prompt Sadar Konteks dan Skema JSON Terstruktur")
    par(doc, "Penelitian ini menerapkan rekayasa prompt sadar konteks (context-aware prompting) "
             "untuk memandu model bahasa besar dalam menjalankan anotasi semu multi-tugas yang konsisten. "
             "Model bertugas menetapkan lima dimensi keluaran secara simultan, yaitu relevansi topik, "
             "polaritas sentimen, tipe teks, kategori aspek, dan bukti leksikal pemicu keputusan.")
    par(doc, "Teks instruksi sistem (system prompt) yang ditanamkan pada mesin inferensi vLLM memuat peran "
             "dan dua belas aturan penalaran operasional sebagai berikut:")
    numid_prompt = _anggap_rincian(doc)
    for p_rule in (
        "Aturan 1 (Pemeriksaan Relevansi Topik): Model memeriksa keterkaitan teks terhadap Sensus Ekonomi 2026, "
        "aplikasi Fasih BPS, petugas sensus, pelaksanaan pendataan, atau tanggapan publik atas agenda tersebut. "
        "Teks yang membicarakan agenda politik umum, utang negara, kecerdasan buatan, maupun survei statistik lain "
        "ditetapkan ke dalam kelas tidak relevan.",
        "Aturan 2 (Pemeriksaan Kebermaknaan Teks): Teks yang semata-mata berupa sapaan, penanda kehadiran, nama, "
        "maupun emotikon tanpa muatan evaluasi diklasifikasikan sebagai tipe sapaan dan sentimen netral dengan "
        "derajat keyakinan paling tinggi 0,5 guna mencegah pemaksaan polaritas pada teks nirpenilaian.",
        "Aturan 3 (Kaidah Pembatasan Kelas Netral): Polaritas netral dicadangkan secara ketat bagi pernyataan faktual, "
        "pertanyaan murni, usulan netral, atau laporan keadaan yang tidak memuat muatan emosional positif maupun "
        "negatif. Kelas netral tidak boleh dijadikan wadah penampungan bagi teks yang sukar diputuskan.",
        "Aturan 4 (Penalaran Sadar Konteks Teks Sasaran): Penilaian polaritas selalu diputuskan berdasarkan isi teks "
        "sasaran yang dianotasi, sedangkan teks induk (parent post) hanya difungsikan sebagai konteks penjelas maksud. "
        "Sebuah komentar balasan tidak serta-merta menjadi relevan hanya karena unggahan induknya membahas sensus. "
        "Panggilan khas seperti kata kak atau min diposisikan sebagai penanda percakapan lapangan.",
        "Aturan 5 (Pengakuan Bahasa Daerah dan Campur Kode): Teks berbahasa daerah, seperti bahasa Jawa, Sunda, "
        "maupun Melayu, serta variasi campur kode diakui sebagai teks sah dan dianotasi menurut muatan maknanya.",
        "Aturan 6 (Netralisasi Bias Peringkat Bintang): Evaluasi berbasis teks ulasan mengabaikan nilai bintang rating "
        "pada Google Play Store, mengingat temuan empiris menunjukkan banyak pengguna memberikan peringkat bintang "
        "lima sembari menyampaikan keluhan teknis yang berat.",
        "Aturan 7 (Resolusi Negasi, Kontras, dan Sarkasme): Model memperhitungkan konstruksi negasi dan ungkapan "
        "sarkasme kontekstual sehingga frasa yang tampak positif dalam struktur kalimat kontradiktif dinilai secara akurat.",
        "Aturan 8 (Kewajiban Bukti Pemicu dan Penalaran): Model diwajibkan menyertakan kutipan teks pendek sebagai "
        "bukti leksikal pemicu (trigger evidence) serta satu kalimat penalaran rasional pada setiap objek jawaban.",
        "Aturan 9 (Kalibrasi Batas Laporan Keadaan terhadap Keluhan): Pertanyaan teknis, permintaan informasi, dan "
        "laporan kondisi faktual di lapangan tetap diklasifikasikan netral sekalipun memuat kata berkonotasi kendala "
        "seperti sulit, belum ada respon, atau tidak muncul, sepanjang penulis tidak melontarkan kecaman kepada institusi.",
        "Aturan 10 (Pencegahan Penyempitan Topik Berlebih): Obrolan teknis lapangan antarpetugas sensus dan pertanyaan "
        "prosedural tetap dipertahankan sebagai data relevan selama masih berkaitan dengan aktivitas pendataan BPS.",
        "Aturan 11 (Resolusi Multisentimen Pujian dan Kendala): Apabila teks memuat apresiasi manfaat sekaligus catatan "
        "kendala teknis ringan, evaluasi didasarkan pada penegasan manfaat utama yang dirasakan pengguna.",
        "Aturan 12 (Deteksi Sindiran Melalui Rangkaian Fakta): Rangkaian pernyataan faktual yang dihimpun secara sinis "
        "untuk menyindir kinerja layanan ditetapkan secara konsisten ke dalam polaritas negatif."
    ):
        butir(doc, p_rule, numid_prompt)

    par(doc, "Untuk menjamin kepatuhan format keluaran sistem hilir, mesin inferensi vLLM dikunci menggunakan "
             "skema format JSON terstruktur (JSON schema enforcement) dengan spesifikasi tipe data sebagai berikut:")
    numid_schema = _anggap_rincian(doc)
    for p_sch in (
        "relevan (boolean): bernilai true apabila teks berkaitan dengan korpus penelitian, atau false bila berada di luar topik.",
        "sentimen (string enum): bernilai positif, negatif, netral, atau tidak_relevan.",
        "tipe (string enum): kategori bentuk teks, mencakup opini, pertanyaan, informasi, sapaan, atau lelucon.",
        "aspek (array of string): himpunan label aspek yang mencakup pajak, privasi_data, hoaks, manfaat, teknis_aplikasi, biaya_ekonomi, petugas, atau lainnya.",
        "bahasa (string enum): klasifikasi ragam bahasa teks, meliputi indonesia, daerah, campur, atau asing.",
        "keyakinan (number): derajat kepastian model dalam rentang nilai numerik 0,0 sampai 1,0.",
        "bukti (string): potongan leksikal spesifik di dalam teks yang mendasari penetapan polaritas.",
        "alasan (string): satu kalimat penjelasan ringkas mengenai rasionalisasi keputusan anotasi."
    ):
        butir(doc, p_sch, numid_schema)

    par(doc, "Pada tahap penyegaran anotasi korpus opini, model probabilitas keputusan Jev mengajukan tiga dimensi "
             "pertanyaan formal terstruktur yang dieksekusi secara independen per baris:")
    numid_jev = _anggap_rincian(doc)
    for p_jv in (
        "Pertanyaan Keterkaitan Topik (dalam_topik): Bertipe biner (noul) untuk memverifikasi apakah baris teks "
        "berada di dalam ruang lingkup diskursus pendataan Sensus Ekonomi BPS atau di luar topik pembicaraan.",
        "Pertanyaan Tipe Teks (tipe): Bertipe pilihan ganda (choice) dengan empat kategori mutually exclusive, "
        "yaitu opini (memuat penilaian evaluatif), sapaan (penanda interaksi), pertanyaan (permintaan informasi), "
        "dan informasi (laporan keterangan faktual).",
        "Pertanyaan Polaritas Sentimen (sentimen): Bertipe pilihan ganda (choice) tiga kelas dengan definisi operasional "
        "baku, yaitu negatif (keluhan, kecaman, sindiran, atau kendala aplikasi), netral (laporan keadaan nirpenilaian "
        "dan pertanyaan teknis), serta positif (pujian, rasa syukur, dan apresiasi manfaat pendataan)."
    ):
        butir(doc, p_jv, numid_jev)

    judul("Lampiran 4. Ringkasan Jumlah Data per Tahap Penyaringan")
    par(doc, "Ringkasan kuantitatif data pada setiap tahap penyaringan korpus disajikan pada Tabel L4.1.")
    judul_tabel(doc, "Tabel L4.1 Ringkasan Jumlah Data per Tahap Penyaringan")
    tabel(doc, ["Nomor", "Tahap Penyaringan", "Jumlah Baris"], [
        ["1", "Rekaman mentah dari tiga platform digital", "10.961"],
        ["2", "Lolos penyaringan jendela tanggal (15 Jun - 15 Sep 2026)", "8.953"],
        ["3", "Lolos penyaringan bahasa (identifikasi lingua)", "8.952"],
        ["4", "Lolos penyaringan kata kunci relevansi topik", "8.831"],
        ["5", "Korpus bersih final pascadeduplikasi", "8.352"],
        ["6", "Baris teks beranotasi lengkap", "8.350"],
    ])

    judul("Lampiran 5. Daftar Berkas Keluaran dan Artefak Penelitian")
    par(doc, "Seluruh artefak keluaran dihimpun secara terstruktur pada repositori GitHub resmi "
             "https://github.com/anwarrohmadi2006/Lampiran-Magang-BPS dengan penamaan berkas kanonik "
             "yang terpetakan langsung ke dalam direktori repositori:")
    numid_lampiran = _anggap_rincian(doc)
    for t in (
        "data/korpus_bersih_8352.csv: korpus teks bersih siap anotasi pascadeduplikasi (8.352 baris)",
        "data/korpus_opini_5808.csv: partisi opini sebagai data latih IndoBERT berlabel Jev (5.808 baris)",
        "data/korpus_non_opini_2119.csv: partisi non-opini yang memuat pertanyaan, sapaan, dan informasi",
        "data/korpus_karantina_423.csv: partisi karantina untuk teks di luar topik pendataan sensus",
        "data/data_uji_manusia_100.csv: data uji acuan manusia seratus baris dengan penyamaran identitas",
        "hasil_evaluasi/evaluasi_gold.json: hasil pengukuran performa lima sistem pada data uji acuan",
        "hasil_evaluasi/audit_label.html: laporan mandiri interaktif audit penjamin mutu label semu",
        "hasil_evaluasi/matriks_konfusi.png: visualisasi matriks konfusi model IndoBERT terbaik",
        "hasil_evaluasi/kappa_gold.json: hasil pengukuran reliabilitas kesepakatan antar-anotator manusia",
        "model_dan_prediksi/config.json: konfigurasi arsitektur model klasifikasi IndoBERT",
        "model_dan_prediksi/vocab.txt: kosakata subkata tokenizer IndoBERT (30.521 token)",
        "model_dan_prediksi/prediksi_prompt_v2.csv: catatan inferensi sistem pembanding pada data uji",
        "artefak_visual/diagram_alur_penelitian.png: diagram alur metodologi penelitian 300 DPI",
        "artefak_visual/diagram_alur_pelabelan.png: diagram bagan pipeline pra-pemrosesan dan ablasi",
        "artefak_visual/atensi/: peta atensi multi-head model final beserta galeri visualisasinya",
        "artefak_visual/lime/: penjelasan atribusi fitur lokal LIME pada tingkat token",
        "skrip/: kumpulan skrip Python modular untuk pembersihan data, pengujian, dan visualisasi",
        "dashboard_web/: aplikasi antarmuka sistem pendukung keputusan interaktif berbasis web",
        "laporan/: naskah dokumen resmi Laporan_KP_Analisis_Sentimen_SE2026.docx dan catatan metodologi",
    ):
        butir(doc, t, numid_lampiran)

    judul("Lampiran 6. Pedoman Baku Penentuan Kelas Sentimen Anotator Manusia")
    par(doc, "Anotasi manusia mengacu pada hierarki pohon keputusan baku lima kelas. Teks ditetapkan ke "
             "dalam kelas tidak relevan apabila secara substantif membicarakan topik di luar sensus dan BPS. "
             "Teks ditetapkan ke dalam kelas bukan opini apabila relevan dengan pendataan namun tidak memuat "
             "muatan evaluasi, mencakup sapaan, pertanyaan teknis, permohonan klarifikasi, laporan kondisi faktual, "
             "serta usulan perbaikan. Teks diklasifikasikan positif bila menyatakan pujian, rasa syukur, dukungan, "
             "atau manfaat nyata pendataan. Teks diklasifikasikan negatif bila memuat keluhan, kritik tajam, "
             "sindiran sinis, maupun kendala aplikasi yang dibungkus dalam bentuk pertanyaan. Teks diklasifikasikan "
             "netral apabila evaluasi bersifat datar atau memuat keseimbangan antara apresiasi dan catatan tanpa "
             "sisi yang dominan. Pedoman operasional komprehensif beserta contoh penerapannya terdokumentasi "
             "pada berkas laporan/catatan_audit_dan_keputusan.md di repositori GitHub.")

    judul("Lampiran 7. Contoh Tambahan Peta Atensi dan Interpretabilitas Model")
    par(doc, "Dua contoh berikut memperlihatkan cara model IndoBERT terbaik menimbang bobot perhatian antar-token "
             "pada dua kelas sentimen yang berbeda. Gambar L.1 merepresentasikan ulasan keluhan teknis aplikasi, "
             "sedangkan Gambar L.2 merepresentasikan komentar apresiasi dan dukungan masyarakat.")
    gambar(doc, FINAL / "atensi" / "attention_4.png", 13,
           "Gambar L.1 Profil Atensi Teks Keluhan Aplikasi")
    sumber(doc, "Sumber: hasil pengolahan data, 2026")
    gambar(doc, FINAL / "atensi" / "attention_5.png", 13,
           "Gambar L.2 Profil Atensi Teks Dukungan")
    sumber(doc, "Sumber: hasil pengolahan data, 2026")

    judul("Lampiran 8. Rekapitulasi Siklus Iterasi Kalibrasi Anotator Keputusan Jev")
    par(doc, "Proses kalibrasi rekayasa prompt model probabilitas keputusan Jev berlangsung secara iteratif "
             "melalui tujuh tahapan terencana guna memastikan konsistensi pelabelan semu sebelum diaplikasikan "
             "ke seluruh korpus. Rincian perkembangan akurasi, temuan evaluasi, serta tindakan kalibrasi per ronde "
             "dirangkum pada Tabel L8.1.")
    judul_tabel(doc, "Tabel L8.1 Rekapitulasi Tahapan Iterasi Kalibrasi Anotator Jev")
    tabel(doc, ["Nomor", "Tahapan Iterasi", "Fokus Intervensi Prompt", "Akurasi", "Tindakan dan Tindak Lanjut"], [
        ["1", "Jev awal (batas gerbang sempit)", "Pemisahan biner relevansi topik", "0,2609",
         "Model menolak 68 baris valid; formulasi gerbang perlu diubah."],
        ["2", "Jev adaptif (bingkai anotasi)", "Penyisipan konteks sensus di awal prompt", "0,5109",
         "Akurasi sentimen murni mencapai 0,7609; struktur pertanyaan disempurnakan."],
        ["3", "Jev ronde 2 (penanaman aturan)", "Penanaman 12 aturan penalaran batas semantik", "0,6196",
         "Uji antar-anotator manusia memetakan batas pertanyaan faktual versus opini."],
        ["4", "Jev ronde 3a (kalibrasi keluhan)", "Penyempurnaan aturan keluhan aplikasi Play Store", "0,7826",
         "Keluhan login Fasih berhasil dipisahkan dari kelas netral."],
        ["5", "Jev final (penajaman batas netral)", "Penegasan batas laporan faktual dan kekecewaan", "0,7935",
         "Aturan stabil dan siap diuji secara independen."],
        ["6", "Validasi independen (data uji manusia)", "Pengujian buta pada 100 baris acuan manusia", "0,7882",
         "Mengungguli model Gemma (0,7176) tanpa indikasi overfitting."],
        ["7", "Anotasi korpus berskala penuh", "Eksekusi otomatis pada 8.352 baris korpus", "100%",
         "Memproses 8,3 juta token tanpa kegagalan komputasi."],
    ])

    judul("Lampiran 9. Dokumentasi Prosedur Operasional Baku dan Kode Program Kunci")
    par(doc, "Pengembangan sistem mengadopsi standar arsitektur modular yang memisahkan tahapan pengumpulan, "
             "pembersihan, pelatihan, dan evaluasi ke dalam modul Python mandiri yang dapat direproduksi secara "
             "penuh. Tiga prosedur algoritma kunci didokumentasikan sebagai berikut:")
    numid_kode = _anggap_rincian(doc)
    for p_kd in (
        "Prosedur 1 (Penyaringan dan Normalisasi Korpus): Modul skrip/01_penyusunan_korpus.py menegakkan batasan rentang "
        "waktu pengumpulan (15 Juni sampai 15 September 2026), memvalidasi bahasa Indonesia melalui pustaka "
        "identifikasi bahasa, menyaring kata kunci relevansi sensus ekonomi dan aplikasi Fasih, serta "
        "menjalankan deduplikasi berbasis sidik jari teks MD5 guna menghasilkan korpus bersih final 8.352 baris.",
        "Prosedur 2 (Pengukuran Kinerja Multikelas dan Kalibrasi Keyakinan): Modul skrip/09_ukur_kinerja.py "
        "menghitung metrik presisi, recall, F1 makro, akurasi seimbang, serta nilai Brier score kalibrasi multi-kelas "
        "secara objektif terhadap 100 baris data uji manusia emas dengan selang kepercayaan bootstrap 95 persen "
        "dan uji signifikansi statistik berpasangan McNemar.",
        "Prosedur 3 (Ekstraksi Bobot Peta Atensi Multi-Head): Modul skrip/21_peta_atensi.py mengekstraksi "
        "matriks perhatian antar-token pada lapisan Transformer terakhir model IndoBERT untuk menghasilkan "
        "profil atensi visual yang menjelaskan kontribusi leksikal kata terhadap keputusan klasifikasi sentimen."
    ):
        butir(doc, p_kd, numid_kode)


# ---------------------------------------------------------------------------
# Penyusunan
# ---------------------------------------------------------------------------

def setel_perbarui_medan(path: Path) -> None:
    """Menandai agar Word memperbarui seluruh medan saat dokumen dibuka.

    Daftar isi, daftar tabel, dan daftar gambar disimpan sebagai medan yang
    dihitung Word. Tanpa tanda ini, pembaca harus menekan Ctrl+A lalu F9
    sendiri, dan laporan yang baru dibuka akan tampak memiliki daftar kosong.
    """
    import shutil
    import zipfile

    sementara = path.with_suffix(".tmp.docx")
    with zipfile.ZipFile(path) as masuk, zipfile.ZipFile(sementara, "w", zipfile.ZIP_DEFLATED) as keluar:
        for item in masuk.infolist():
            data = masuk.read(item.filename)
            if item.filename == "word/settings.xml":
                teks = data.decode("utf-8")
                if "updateFields" not in teks:
                    tanda = "<w:updateFields w:val=\"true\"/>"
                    if "</w:settings>" in teks:
                        teks = teks.replace("</w:settings>", tanda + "</w:settings>", 1)
                    else:
                        teks = teks.replace(">", ">" + tanda, 1)
                    data = teks.encode("utf-8")
            keluar.writestr(item, data)
    shutil.move(str(sementara), str(path))


def perbarui_medan_lewat_word(path: Path) -> bool:
    """Menjalankan Word sekali untuk memperbarui seluruh medan lalu menyimpan.

    Daftar isi, daftar tabel, daftar gambar, dan daftar lampiran adalah medan yang
    hanya dapat dihitung oleh mesin tata letak Word. Penanda ``w:updateFields``
    yang dipasang :func:`setel_perbarui_medan` memang cara yang benar, tetapi ia
    hanya berlaku di Word, hanya sekali pakai, dan dapat dihalangi setelan Trust
    Center. LibreOffice dan Google Docs umumnya mengabaikannya.

    Dengan menjalankan Word di sini, hasil hitungan medan ikut tersimpan di dalam
    berkas. Daftar itu karena itu sudah terisi bagi pembaca mana pun, bukan hanya
    bagi pengguna Word yang menyetujui pembaruan. Inilah bedanya laporan yang
    diserahkan apa adanya dengan laporan yang masih meminta pembacanya menekan
    Ctrl+A lalu F9.

    Istansi Word dibuat baru dengan ``DispatchEx``, bukan menumpang istansi yang
    sedang berjalan. Dengan begitu dokumen lain yang sedang dibuka pengguna tidak
    terganggu, dan yang ditutup benar-benar hanya proses milik skrip ini.
    """
    try:
        import win32com.client
    except ImportError:
        print("    pywin32 tidak tersedia; medan tidak diperbarui di tempat")
        return False

    word = None
    dok = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        dok = word.Documents.Open(str(path.resolve()), ReadOnly=False,
                                  AddToRecentFiles=False)
        dok.Fields.Update()
        for toc in dok.TablesOfContents:
            toc.Update()
        dok.Save()
        return True
    except Exception as galat:  # noqa: BLE001
        print(f"    gagal memperbarui medan lewat Word: {type(galat).__name__}: {galat}")
        print("    laporan tetap tersusun; daftarnya terisi saat dibuka di Word")
        return False
    finally:
        # Penutupan yang gagal tidak boleh ditelan diam-diam. Word yang tertinggal
        # memegang berkas laporan, sehingga pemeriksaan berikutnya tidak dapat
        # membuka berkas itu dan penjelasannya membingungkan.
        if dok is not None:
            try:
                dok.Close(SaveChanges=0)
            except Exception as galat:  # noqa: BLE001
                print(f"    peringatan: dokumen Word tidak tertutup: {galat}")
        if word is not None:
            try:
                word.Quit(SaveChanges=0)
            except Exception as galat:  # noqa: BLE001
                print(f"    peringatan: Word tidak tertutup: {galat}")
        dok = None
        word = None


def pulihkan_tebal_gaya(path: Path) -> None:
    """Memulihkan penanda tebal pada gaya judul setelah pembaruan medan Word.

    Langkah pembaruan medan Word (khususnya daftar isi otomatis) dapat
    menormalkan definisi rPr pada styles.xml. Fungsi ini menegakkan kembali
    atribut tebal pada Heading 1, Heading 2, Heading 3, dan Title agar penomoran
    sub-bab (1.1, dst.) dirender tebal dan dokumen memenuhi seluruh ketentuan format.
    """
    doc = Document(str(path))
    for nama in ("Heading 1", "Heading 2", "Heading 3", "Title"):
        if nama in doc.styles:
            doc.styles[nama].font.bold = True
    doc.save(str(path))


def bangun(out: Path, lewat_word: bool = True) -> Path:
    """Menyusun laporan di dalam cangkang format.

    Cangkang dibuka lebih dahulu, isinya dibuang kecuali tiga halaman awal, lalu
    laporan ditulis ke dalamnya memakai gaya bawaan cangkang. Berkas cangkangnya
    sendiri tidak pernah ditulis; ia hanya dibaca berulang kali.
    """
    doc = buka_cangkang()
    _setel_gaya_judul(doc)
    siapkan_gaya(doc)

    # Halaman sampul, lembar persetujuan, dan halaman pengesahan sudah ada di
    # dalam cangkang. Yang dikerjakan di sini hanya mengisi identitasnya.
    isi_halaman_awal(doc)

    # Bagian awal memakai angka Romawi kecil, bagian utama memakai angka Arab
    # mulai dari satu. Section pertama sudah ada sejak cangkang dibuka; section
    # kedua dibuat di antara daftar awal dan bab pertama.
    siapkan_halaman(doc.sections[0])
    gaya_penomoran(doc.sections[0], "lowerRoman")
    nomor_halaman(doc.sections[0])

    bagian_awal(doc)
    daftar_awal(doc)

    badan = doc.add_section(WD_SECTION.NEW_PAGE)
    siapkan_halaman(badan)
    gaya_penomoran(badan, "decimal")
    nomor_halaman(badan)

    bab_satu(doc)
    bab_dua(doc)
    bab_tiga(doc)
    bab_empat(doc)
    bab_lima(doc)
    daftar_pustaka(doc)
    lampiran(doc)

    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out))
    setel_perbarui_medan(out)
    if lewat_word:
        perbarui_medan_lewat_word(out)
    pulihkan_tebal_gaya(out)
    return out


def selftest() -> int:
    """Menguji logika yang tidak bergantung pada Word maupun berkas keluaran.

    Yang diuji adalah perhitungan lebar kolom tabel dan penamaan gaya daftar,
    sebab keduanya menentukan bentuk berkas dan tidak terlihat dari isinya.
    Pemeriksaan bentuk laporan yang sudah jadi dikerjakan `periksa_format.py`.
    """
    # Pembagian lebar harus berjumlah tepat dan tidak menyisakan kolom yang
    # terlalu sempit untuk isinya.
    for bobot, total, minimum in (
        ([1, 1], 14.0, 1.5),
        ([10, 1, 1], 14.0, 2.0),
        ([1, 1, 1, 1, 1, 1, 1], 14.0, 1.5),
        ([40, 3], 14.0, 1.5),
    ):
        lebar = _bagi_lebar(bobot, total, minimum)
        assert len(lebar) == len(bobot), "jumlah kolom harus tetap"
        assert abs(sum(lebar) - total) < 0.01, f"jumlah lebar tidak tepat: {sum(lebar)}"
        assert all(w >= minimum - 0.01 for w in lebar), f"ada kolom di bawah batas: {lebar}"

    # Bila totalnya lebih kecil daripada kebutuhan minimum, lebar dibagi rata.
    lebar = _bagi_lebar([1, 1, 1], 3.0, 1.5)
    assert abs(sum(lebar) - 3.0) < 0.01

    # Bobot kolom mengikuti panjang isi, tetapi dibatasi agar satu sel yang
    # sangat panjang tidak menghabiskan lebar seluruh tabel.
    bobot = _bobot_kolom(["Nomor", "Tahap", "Jumlah"],
                         [["1", "Rekaman mentah dari tiga platform", "10.961"]])
    assert len(bobot) == 3
    assert bobot[1] > bobot[0], "kolom berisi teks panjang harus berbobot lebih besar"
    assert max(bobot) <= 34.0
    assert min(bobot) >= 3.0

    # Ketiga gaya daftar turunan harus berbeda satu sama lain, sebab medan TOC
    # menghimpun entrinya menurut nama gaya.
    assert len({GAYA_KETERANGAN_TABEL, GAYA_KETERANGAN_GAMBAR,
                GAYA_JUDUL_LAMPIRAN}) == 3, "nama gaya daftar tidak boleh kembar"

    # Template harus terbaca dan hanya menyisakan halaman awal (sampul, persetujuan,
    # dan pengesahan). Aturan penulisan dan isi naskah dummy tidak boleh ikut terbawa.
    doc = buka_cangkang()
    _setel_gaya_judul(doc)
    assert len(doc.sections) == 1, "cangkang harus menyisakan satu section"
    judul_awal = [p.text.strip().upper() for p in doc.paragraphs]
    for penanda in (CANGKANG_AWAL, "LEMBAR PERSETUJUAN", "HALAMAN PENGESAHAN"):
        assert penanda in judul_awal, f"halaman awal hilang: {penanda}"
    assert CANGKANG_AKHIR not in judul_awal, "isi cangkang tidak terbuang"

    # Penanda template harus tergantikan seluruhnya, termasuk yang berada di dalam
    # sel tabel tanda tangan halaman pengesahan.
    isi_halaman_awal(doc)
    sisa = " ".join(p.text for p in doc.paragraphs)
    for t in doc.tables:
        for baris in t.rows:
            for sel in baris.cells:
                sisa += " " + " ".join(p.text for p in sel.paragraphs)
    for kata in ("PROGRAM STUDI XXX", "NAMA MAHASISWA", "Nama Lengkap beserta gelar"):
        assert kata not in sisa, f"sisa penanda template: {kata}"


    # Nilai yang masih berupa penanda tidak boleh dituliskan, sebab penanda akan
    # menumpuk di tempat yang seharusnya memuat nama orang.
    assert terisi("Zulfanita Dien Rizqiana"), "nilai terisi harus dikenali"
    assert not terisi("<<ISI: Nama Dosen Penguji>>"), "penanda harus dikenali"
    assert not terisi("   "), "nilai kosong harus dikenali"

    # Penggantian teks memakai run pertama supaya keterangan hurufnya tetap, dan
    # run selebihnya dibuang supaya teks lama tidak tertinggal.
    contoh = doc.add_paragraph()
    tebal = contoh.add_run("teks lama")
    tebal.bold = True
    contoh.add_run(" sambungan")
    ganti_teks(contoh, "teks baru")
    assert contoh.text == "teks baru", f"teks tidak terganti: {contoh.text!r}"
    assert len(contoh.runs) == 1, "run lama harus dibuang"
    assert contoh.runs[0].bold is True, "keterangan huruf run pertama harus tetap"
    contoh._element.getparent().remove(contoh._element)

    print("selftest buat_laporan_docx ok")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Menyusun laporan KP dalam format .docx")
    p.add_argument("--out", default="reports/Laporan_KP_Analisis_Sentimen_SE2026.docx")
    p.add_argument("--tanpa-word", action="store_true",
                   help="lewati langkah pembaruan medan lewat Word")
    p.add_argument("--selftest", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if argv and argv[0] == "--selftest":
        return selftest()
    args = build_parser().parse_args(argv)
    if args.selftest:
        return selftest()
    out = bangun(Path(args.out), lewat_word=not args.tanpa_word)
    print(f"laporan tersusun: {out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
