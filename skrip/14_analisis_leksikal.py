# Analisis Sentimen Sensus Ekonomi 2026 dan Aplikasi Fasih BPS
# 14 Analisis Leksikal dan Awan Kata
#
# Kegunaan : Menghitung kata pembeda tiap kelas dengan rasio log-odds, lalu menggambar awan kata
#            per kelas, baik pada korpus berlabel Jev maupun pada data uji manusia.
# Masukan  : data/processed/v3/dataset_jev.csv dan final/gold_uji.csv
# Keluaran : reports/analisis_leksikal.md dan delapan berkas awan kata di reports/gambar
# Rujukan  : Bab IV pada bagian analisis leksikal
#
# Menjalankan dari akar repositori:  py -3.13 analisis/14_analisis_leksikal.py
# -*- coding: utf-8 -*-
"""Analisis leksikal per kelas sentimen + awan kata (monokrom, latar putih).

Rujukan metode: Monroe, Colaresi & Quinn (2008), "Fightin' Words", Political
Analysis 16(4):372-403. Skor yang dipakai adalah log-odds ratio dengan prior
Dirichlet tak informatif (alpha_w = 0.01 untuk semua kata, alpha_0 = 0.01*|V|;
lihat bagian 3.3.2), rumus (16):

    delta_w = log( (y_w^A + a_w) / (n_A + a_0 - y_w^A - a_w) )
            - log( (y_w^B + a_w) / (n_B + a_0 - y_w^B - a_w) )

dengan varian (19) dan z = delta / sigma (22) sebagai ukuran signifikansi.

Skrip ini tidak ditulis ke dalam repo. Keluaran: reports\\gambar\\*.png dan
ringkasan teks di direktori scratchpad sesi.
"""
import csv, json, math, os, collections, re

BASE = r"C:\Users\user\Laporan Magang BPS"
SCRATCH = r"C:\Users\user\AppData\Local\Temp\commandcode\C--Users-user-Laporan-Magang-BPS\3c8d241c-0393-4026-bda3-1893ba0f5cde\scratchpad"
IMG = os.path.join(BASE, "reports", "gambar")
os.makedirs(IMG, exist_ok=True)
HCLS = ("negatif", "netral", "positif")
A0 = 0.01


def rd(rel):
    with open(os.path.join(BASE, rel), encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


# --------------------------------------------------------------- 1. tokenisasi
STOP_ID = """
ada adalah adanya agar akan akibat ala andai antar antara apa apabila apakah atas atau
bagi bahwa bahwasanya bahkan banyak baru begitu bila bilamana boleh buat bukan dalam dan
dapat dari daripada demi demikian dengan dimana engkau guna hal hanya hanyalah ialah ini
itu jika jikalau kalau kala kami kamu kau ketika kita kok lah lain lalu lantas lho maka
manakala melainkan memang mengapa mesti meski meskipun mungkin namun nya oleh olehnya pada
paling pun sampai sana sini saja saat serta saya sebagai sebab sebanyak sebenarnya secara
sudah supaya tersebut terhadap tetapi tiap untuk yang walau walaupun yaitu yakni maupun
juga sehingga telah masih harus bisa ingin sekedar sih deh dong yah yuk ayo mari nah eh
hmm hehe wkwk wkwkwk tsb dll dsb kepada menjadi adalah nya tuh mah
""".split()

# kata fungsi bahasa Inggris (korpus campur kode)
STOP_EN = """
the of with on in at by to for from and or but if you your are is was were be been am
this that these those have has had not no so too very just all any some more most then
than there here about after before over under again only also into during while when
which who whom whose what why how can could will would should shall may might must do
does did done
""".split()

# nama berkas emoji/shortcode yang ikut terbersihkan oleh praproses korpus
NOISE = """
face faces beaming tears joy smiling smile smiley grin grinning laughing laughing_face
loudly crying cry sob scream sweat folded hands hand clapping clap thumbs palms praying
raise raised raising together biceps flexed muscle sparkles sparkle glowing star stars
popper party tada hundred points tone skin light medium dark trophy medal first second
third place cake gift crown kiss wink blush sunglasses nerd confused worried angry rage
weary tired rolling floor eyes eye mouth nose steam devil ghost alien robot poop fire
rocket boom collision dizzy zap bulb bell check cross warn warning wave ok palms up
thumbs_up red blue green yellow orange purple brown black white heart hearts broken
trophy_2 open fresh
""".split()

TOKEN_RE = re.compile(r"[^a-z\s]+")
WS_RE = re.compile(r"\s+")
STOP = set(STOP_ID) | set(STOP_EN) | set(NOISE)


def tokenize(text):
    t = TOKEN_RE.sub(" ", (text or "").lower())
    return [w for w in WS_RE.split(t) if len(w) >= 3 and w not in STOP]


# ------------------------------------------------- 2. skor log-odds + z (Monroe)
def logodds(counts_a, n_a, counts_b, n_b, vocab, a0=A0):
    """delta (log-odds ratio, prior Dirichlet a0=0.01) dan z = delta/sigma."""
    a0sum = a0 * len(vocab)
    res = {}
    for w in vocab:
        ya, yb = counts_a.get(w, 0), counts_b.get(w, 0)
        da = math.log((ya + a0) / (n_a + a0sum - ya - a0))
        db = math.log((yb + a0) / (n_b + a0sum - yb - a0))
        delta = da - db
        var = (1.0 / (ya + a0)) + (1.0 / (n_a + a0sum - ya - a0)) \
            + (1.0 / (yb + a0)) + (1.0 / (n_b + a0sum - yb - a0))
        res[w] = (delta, delta / math.sqrt(var), ya, yb, ya + yb)
    return res


def top_words(docs_by_group, groups, min_total, topn=40):
    cnt = {g: collections.Counter() for g in groups}
    for g in groups:
        for toks in docs_by_group[g]:
            cnt[g].update(toks)
    n = {g: sum(cnt[g].values()) for g in groups}
    vocab = set().union(*[set(c) for c in cnt.values()])
    out = {}
    for g in groups:
        rest = collections.Counter()
        for o in groups:
            if o != g:
                rest.update(cnt[o])
        lo = logodds(cnt[g], n[g], rest, sum(n[o] for o in groups if o != g), vocab)
        rows = [(w, d, z, ya, yb, tot) for w, (d, z, ya, yb, tot) in lo.items() if tot >= min_total]
        # urutkan menurun menurut skor; seri diputuskan alfabetis agar dapat direproduksi
        rows.sort(key=lambda r: (-r[1], -r[2], r[0]))
        out[g] = rows[:topn]
    return out, cnt, n


# ------------------------------------------------------------------ 3. muat data
labels_jev = {r["uid"]: r["sentimen_jev"] for r in rd(r"data\processed\v3\labels_jev.csv")}
korpus = {r["uid"]: r["text_clean"] for r in rd(r"final\korpus_opini.csv")}

korpus_docs = {lab: [] for lab in HCLS}
for uid, lab in labels_jev.items():
    if uid in korpus and lab in korpus_docs:
        korpus_docs[lab].append(tokenize(korpus[uid]))
n_korpus = sum(len(v) for v in korpus_docs.values())

gold1 = rd(r"final\gold_manusia.csv")
gold3_lab = rd(r"data\processed\v3\gold_ronde3_manusia.csv")
gold3_txt = {r["uid"]: r["text_clean"] for r in rd(r"data\processed\v3\gold_kandidat_ronde3.csv")}

human_rows = [(1, r["uid"], r["text_clean"], r["label_manusia"]) for r in gold1]
human_rows += [(3, r["uid"], gold3_txt.get(r["uid"], ""), r["label_manusia"]) for r in gold3_lab]

human_docs = {lab: [] for lab in HCLS}
human_n = collections.Counter()
for ronde, uid, txt, lab in human_rows:
    human_n[lab] += 1
    if lab in human_docs:
        human_docs[lab].append(tokenize(txt))

pred1 = {r["uid"]: r["label"] for r in rd(r"reports\prediksi_model_jev_ronde1.csv")}
pred3 = {r["uid"]: r["label"] for r in rd(r"reports\prediksi_model_jev_ronde3.csv")}

salah_docs, benar_docs, salah_rows, benar_rows, tr_rows = [], [], [], [], []
for ronde, uid, txt, lab in human_rows:
    if lab not in HCLS:
        tr_rows.append((ronde, uid, lab))
        continue
    pred = (pred1 if ronde == 1 else pred3).get(uid)
    if pred is None:
        continue
    (benar_docs if pred == lab else salah_docs).append(tokenize(txt))
    (benar_rows if pred == lab else salah_rows).append((ronde, uid, lab, pred))

err_by_group = {"salah": salah_docs, "benar": benar_docs}

# --------------------------------------------------------------- 4. hitung skor
# ambang frekuensi minimum: 10 token pada korpus (5808 dokumen) dan 3 token pada
# himpunan kecil (200 baris gold / 35 baris salah) agar kata langka tidak mendominasi
kor_top, kor_cnt, kor_n = top_words(korpus_docs, HCLS, min_total=10)
hum_top, hum_cnt, hum_n_tok = top_words(human_docs, HCLS, min_total=3)
err_top, err_cnt, err_n = top_words(err_by_group, ("salah", "benar"), min_total=3)

# --------------------------------------------------------------- 5. awan kata
from wordcloud import WordCloud

COLOR = {"negatif": "#b03a2e", "netral": "#b7791f", "positif": "#2f855a", "salah": "#6b7a8d"}
FP = r"C:\Windows\Fonts\arial.ttf"
if not os.path.exists(FP):
    FP = None


def cloud(path, rows, color, seed=42):
    freq = {w: round(d, 4) for w, d, z, ya, yb, tot in rows if d > 0}
    if len(freq) < 3:
        print("SKIP", path)
        return None
    wc = WordCloud(width=1800, height=1100, background_color="white", mode="RGB",
                   font_path=FP, max_words=len(freq), prefer_horizontal=0.9,
                   relative_scaling=0.0, max_font_size=200, min_font_size=12,
                   margin=8, collocations=False, random_state=seed,
                   color_func=lambda *a, **k: color)
    wc.generate_from_frequencies(freq)
    wc.to_file(path)
    # word_count sebenarnya yang tergambar
    return path, len(wc.layout_)


made = []
plan = [
    ("awan_negatif_korpus.png", kor_top["negatif"], COLOR["negatif"]),
    ("awan_netral_korpus.png", kor_top["netral"], COLOR["netral"]),
    ("awan_positif_korpus.png", kor_top["positif"], COLOR["positif"]),
    ("awan_negatif_manusia.png", hum_top["negatif"], COLOR["negatif"]),
    ("awan_netral_manusia.png", hum_top["netral"], COLOR["netral"]),
    ("awan_positif_manusia.png", hum_top["positif"], COLOR["positif"]),
    ("awan_salah_model.png", err_top["salah"], COLOR["salah"]),
    ("awan_benar_model.png", err_top["benar"], COLOR["salah"]),
]
for name, rows, col in plan:
    r = cloud(os.path.join(IMG, name), rows, col)
    if r:
        made.append(r)

# ------------------------------------------------------------------ 6. ringkasan
def ser(rows):
    return [[w, round(d, 3), round(z, 2), ya, yb, tot] for w, d, z, ya, yb, tot in rows]


# matriks kesalahan (manusia -> prediksi) dan contoh teks per kelas
conf = collections.Counter()
by_round = collections.Counter()
for ronde, uid, lab, pred in salah_rows:
    conf["%s->%s" % (lab, pred)] += 1
    by_round[ronde] += 1
tot_h = collections.Counter()
for ronde, uid, txt, lab in human_rows:
    if lab in HCLS:
        tot_h[lab] += 1

kor_raw = {r["uid"]: (r.get("text") or "") for r in rd(r"final\korpus_opini.csv")}
gold_raw = {r["uid"]: (r.get("text") or "") for r in gold1}
gold_raw.update({r["uid"]: (r.get("text") or "") for r in rd(r"data\processed\v3\gold_kandidat_ronde3.csv")})


def contoh(pool, label_pick, n=4, lo=40, hi=220):
    out = []
    for uid, raw in pool.items():
        lab = label_pick(uid)
        if lab is None:
            continue
        t = " ".join((raw or "").split())
        if lo <= len(t) <= hi:
            out.append((lab, uid, t))
    out.sort(key=lambda x: len(x[2]))
    per = collections.defaultdict(list)
    for lab, uid, t in out:
        if len(per[lab]) < n:
            per[lab].append(t)
    return {k: v for k, v in per.items()}


cont_kor = contoh(kor_raw, lambda u: labels_jev.get(u))
cont_hum = contoh(gold_raw, lambda u: next((l for r, uu, tt, l in human_rows if uu == u and l in HCLS), None))

summary = {
    "n_korpus": n_korpus,
    "korpus_dok": {g: len(korpus_docs[g]) for g in HCLS},
    "korpus_token": {g: kor_n[g] for g in HCLS},
    "korpus_vokab": {g: len(kor_cnt[g]) for g in HCLS},
    "manusia_dok": dict(human_n),
    "manusia_token": {g: hum_n_tok[g] for g in HCLS},
    "model_salah": len(salah_docs), "model_benar": len(benar_docs),
    "model_tidak_relevan": len(tr_rows),
    "konfusi": dict(conf), "salah_per_ronde": {str(k): v for k, v in by_round.items()},
    "dok_kelas_manusia": dict(tot_h),
    "kor_top": {g: ser(kor_top[g]) for g in HCLS},
    "hum_top": {g: ser(hum_top[g]) for g in HCLS},
    "err_top": {g: ser(err_top[g]) for g in ("salah", "benar")},
    "gambar": [p for p, _ in made],
    "gambar_kata": {os.path.basename(p): n for p, n in made},
    "salah_rows": [list(map(str, r)) for r in sorted(salah_rows)],
    "contoh_korpus": cont_kor,
    "contoh_manusia": cont_hum,
}
with open(os.path.join(SCRATCH, "hasil_leksikal.json"), "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=1)

L = []
L.append("KORPUS Jev: %d dok (neg %d / net %d / pos %d)" % (
    n_korpus, len(korpus_docs["negatif"]), len(korpus_docs["netral"]), len(korpus_docs["positif"])))
L.append("  token: %s" % {g: kor_n[g] for g in HCLS})
L.append("MANUSIA: %s  dokumen 3 kelas = %d" % (dict(human_n), sum(human_n[g] for g in HCLS)))
L.append("MODEL: salah %d | benar %d | tidak_relevan %d" % (len(salah_docs), len(benar_docs), len(tr_rows)))
L.append("")
for src, tops in (("KORPUS JEV (label Jev)", kor_top),
                  ("MANUSIA GABUNGAN (ronde 1 + 3)", hum_top),
                  ("MODEL JE V: BARIS SALAH vs BENAR", err_top)):
    L.append("=" * 78)
    L.append(src)
    for g, rows in tops.items():
        nsig = sum(1 for r in rows if abs(r[2]) >= 1.96)
        L.append("-- %s: %d kata (z>=1.96: %d)" % (g, len(rows), nsig))
        for i, (w, d, z, ya, yb, tot) in enumerate(rows, 1):
            L.append("  %2d. %-16s delta=%6.3f  z=%7.2f  nA=%4d nB=%4d" % (i, w, d, z, ya, yb))
        L.append("")
L.append("GAMBAR:")
for p, n in made:
    L.append("  %s (%d kata tergambar)" % (os.path.basename(p), n))
L.append("")
L.append("KONFUSI (manusia -> prediksi): %s ; per ronde %s" % (dict(conf), dict(by_round)))
L.append("DOKUMEN 3 KELAS MANUSIA: %s" % dict(tot_h))
L.append("")
L.append("CONTOH KORPUS:")
for g in HCLS:
    for t in cont_kor.get(g, []):
        L.append("  [%s] %s" % (g, t))
L.append("CONTOH GOLD MANUSIA:")
for g in HCLS:
    for t in cont_hum.get(g, []):
        L.append("  [%s] %s" % (g, t))
L.append("")
L.append("DAFTAR BARIS SALAH MODEL:")
for ronde, uid, lab, pred in sorted(salah_rows):
    L.append("  r%d %s manusia=%s pred=%s" % (ronde, uid[:10], lab, pred))
with open(os.path.join(SCRATCH, "hasil_leksikal.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(L))
print("\n".join(L[:6]))
print("gambar:", len(made))
print("SELESAI")
