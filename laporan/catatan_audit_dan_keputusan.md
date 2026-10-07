# Audit Label dan Strategi Perbaikan — Sentimen Sensus Ekonomi 2026

Disusun: 15 September 2026
Lingkup: 9.677 baris berlabel (`data/processed/dataset_se2026_labeled.csv`), lima konektor scraper, dan rencana pemanfaatan `microsoft/SkillOpt`.

---

## 1. Ringkasan eksekutif

Kesimpulan utama: **format pelabelan patuh, tetapi substansinya cacat karena anotator tidak diberi konteks.**

Beberapa hal yang saya temukan dan putuskan:

- Seluruh 9.677 baris berhasil diurai (`parse_ok` benar semua, tidak ada alasan kosong). Masalahnya bukan pada format JSON, melainkan pada penilaian yang dilakukan tanpa keterangan asal teks.
- **2.222 komentar YouTube (27,9%) adalah balasan** yang dinilai tanpa teks induknya, padahal konteks itu ada di kolom `extra` namun tidak pernah dikirim ke anotator.
- **Kelas netral berubah menjadi tempat penampungan.** Teks di bawah 25 karakter menempati 38,8% kelas netral, sementara teks panjang hanya 29,3%. Sapaan seperti "Hadir", "Me..", "gooooo", dan nama tanpa makna masuk ke kelas itu dengan keyakinan 0,5.
- **Kontaminasi topik terkonfirmasi.** 21 komentar berbahasa Vietnam dari video "THE VIETNAMESE AI RACE" masuk ke korpus, beberapa di antaranya dilabeli dengan keyakinan hanya 0,10. Ada pula 115 komentar dari video "Utang Akan Semakin Mahal" dan 4 komentar dari video Sakernas.
- **Bintang Google Play tidak layak dijadikan acuan otomatis.** 90 ulasan bintang lima dilabeli negatif dan 11 ulasan bintang satu dilabeli positif. Pemeriksaan manual menunjukkan label teksnya justru yang benar; bintangnya yang tidak dapat dipercaya.
- Angka kinerja ablasi sebelumnya (**akurasi 0,8769 dan F1 macro 0,8669**) adalah **tingkat kesesuaian terhadap anotator Gemma**, bukan akurasi sejati. Angka itu belum boleh dikutip sebagai kualitas model.

---

## 2. Cara audit dilakukan

Tiga pemeriksaan dijalankan terhadap korpus yang sudah dilabeli:

1. **Rekapitulasi struktural** per sumber: jumlah baris, sebaran label, rata-rata keyakinan, jumlah keyakinan di bawah 0,6, serta kegagalan penguraian.
2. **Uji kontradiksi eksternal** antara bintang ulasan Google Play dan label sentimen, sebagai satu-satunya sinyal objektif yang tersedia.
3. **Penelusuran asal YouTube** melalui kolom `extra` untuk mengukur keterkaitan topik video, keberadaan balasan, dan panjang teks.

---

## 3. Temuan audit label

### 3.1 Sebaran dan keyakinan

| Sumber | Jumlah | Rata keyakinan | Keyakinan < 0,6 | Negatif | Netral | Positif |
|---|---:|---:|---:|---:|---:|---:|
| Google Play | 1.348 | 0,944 | 9 | 1.016 | 104 | 228 |
| Threads | 378 | 0,867 | 3 | 192 | 148 | 38 |
| YouTube | 7.951 | 0,892 | 172 | 3.710 | 2.715 | 1.526 |

Ketidakseimbangan kelas cukup tajam. Kelas positif hanya 1.792 baris (18,5%), sedangkan negatif mencapai 4.918 baris (50,8%). Hal ini menjelaskan mengapa pembobotan kelas dan label smoothing pada skenario `full_rdrop` memberi perolehan terbesar pada F1 macro.

### 3.2 Bintang Play Store bertentangan dengan label teks

| Pola | Jumlah |
|---|---:|
| Bintang 5 tetapi dilabeli negatif | 90 |
| Bintang 1 tetapi dilabeli positif | 11 |

Contoh yang saya periksa satu per satu:

- `1 bintang` — "aplikasi hebat mempermudah pekerjaan" → **positif**. Label teks benar, bintang tidak masuk akal.
- `5 bintang` — "masih blm stabil" → **negatif**. Label teks benar, pengulas memberi lima bintang sambil mengeluh.
- `5 bintang` — "kadang suka eror" → **negatif**. Pola yang sama.

**Kesimpulan:** anotator LLM menilai isi teks dengan baik pada kasus-kasus ini. Yang tidak dapat dipercaya adalah bintangnya. Perilaku memberi bintang tinggi sambil mengeluh lazim di Google Play Indonesia.

### 3.3 Kelas netral menampung sampah

Contoh nyata dari korpus:

| Teks | Label | Keyakinan |
|---|---|---:|
| "Hadir 😂" | netral | 0,50 |
| "Me.. 😂" | netral | 0,50 |
| "gooooo" | netral | 0,50 |
| "AGITPRAYOGA" | netral | 0,50 |
| "on proses ka" | netral | 0,80 |
| "Ini mirror bukan sih" | netral | 0,80 |
| "tidak satu pun?" | netral | 0,80 |

Tidak satu pun dari teks di atas menyampaikan sentimen. Semuanya memakai kuota kelas netral, sehingga kelas itu kehilangan makna analitisnya.

### 3.4 Balasan dinilai tanpa konteks

Sebanyak 2.222 komentar YouTube (27,9%) adalah balasan. Contoh:

- "usaha pertanian tidak dicakup di SE ka, sudah dicakup di sensus pertanian (ST)" → netral
- "Koreksi Kategori A masuk juga" → netral
- "didata ka @azahraes8370" → netral

Ketiganya adalah percakapan teknis antara petugas pendata dan warga. Menilainya sebagai "netral" secara taksonomi dapat dibenarkan, tetapi maknanya sebagai opini publik hampir nol. Padahal kolom `extra` menyimpan `parent`, `video_title`, dan `channel` — konteks itu tersedia tetapi tidak pernah dipakai.

### 3.5 Kontaminasi topik dan bahasa

| Temuan | Jumlah | Bukti |
|---|---:|---|
| Komentar berbahasa Vietnam | 21 | Semuanya dari video "THE VIETNAMESE AI RACE"; beberapa berkeyakinan 0,10 |
| Komentar dari video "Utang Akan Semakin Mahal" | 115 | Topik utang negara, bukan sensus |
| Komentar dari video Sakernas | 4 | Program statistik berbeda |
| Komentar dari judul tanpa kata kunci sensus/BPS | 435 (batas atas) | Sebagian sebenarnya relevan, hanya berjudul bahasa Inggris |

Batas bawah kontaminasi yang terkonfirmasi adalah **140 baris (1,4%)**; batas atasnya **435 baris (4,5%)**.

### 3.6 Teks panjang dan ringkas berperilaku berbeda

| Kelompok | Jumlah | Netral | Negatif | Positif |
|---|---:|---:|---:|---:|
| Teks < 25 karakter | 1.385 | 38,8% | 31,0% | 30,2% |
| Teks ≥ 25 karakter | 8.292 | 29,3% | 54,1% | 16,6% |

Teks pendek tersebar hampir rata, sedangkan teks panjang sangat condong ke negatif. Ini menandakan teks pendek memang tidak membawa sinyal, bukan bahwa sentimen publik berimbang.

---

## 4. Temuan audit scraper

Sepuluh cacat yang saya temukan pada kode pengambilan data, diurutkan menurut dampaknya:

1. **Sapuan kanal tanpa penyaring topik** — `scraper/youtube.py::channel_videos` mengambil seluruh video kanal `@BPSStatistics` tanpa memeriksa judul. Inilah pintu masuk video AI Vietnam, utang negara, dan Sakernas. Ini penyebab kontaminasi terbesar.
2. **Konteks induk tidak disimpan** — `extra.parent` hanya memuat identitas induk, bukan teksnya. Akibatnya 27,9% balasan tidak dapat direkonstruksi konteksnya, bahkan setelah data mentah tersedia.
3. **Stempel waktu Google Play tidak deterministik** — `scraper/playstore.py::_to_utc` memanggil `parse_dt` terlebih dahulu; fungsi itu sudah menempelkan `tzinfo=UTC` pada datetime tanpa zona. Cabang `if isinstance(value, datetime) and value.tzinfo is None` lalu memanggil `value.astimezone(timezone.utc)`, yang menafsirkan datetime tanpa zona sebagai waktu lokal mesin. Hasilnya bergeser mengikuti zona waktu host: di Modal (UTC) tidak bergeser, di mesin WIB bergeser tujuh jam.
4. **Tidak ada penyaring bahasa** — komentar Vietnam lolos tanpa hambatan sampai ke tahap pelabelan.
5. **Bahasa komentar tertukar dengan bahasa video** — `youtube.py` menyetel `lang=meta.get("lang")` yang berasal dari video, bukan dari komentar.
6. **Teks Threads tercampur** — `scraper/threads.py` mengambil `inner_text` dari seluruh elemen `article`, sehingga teks unggahan, balasan, dan label antarmuka bergabung menjadi satu baris.
7. **Kata kunci hanya berbahasa Indonesia** — `scraper/keywords.py` tidak memuat padanan Inggris, sehingga video resmi BPS berbahasa Inggris hanya terjaring lewat jalur sapuan kanal yang justru tidak terfilter.
8. **Pemetaan kata yang tidak berguna** — `scraper/cleaning.py` memuat banyak entri yang memetakan kata ke dirinya sendiri, misalnya "ubah", "pajak", "sensus", "responden", "gratis".
9. **Partikel wacana dibuang** — `replace_slang` menghapus "sih", "deh", "dong", "kok", "ya" yang justru membawa nuansa penilaian.
10. **Pelebaran topik mengikuti limit** — `pipeline_SE2026.py::collect_youtube` memakai `videos_per_query=max(3, limit // 100)`, sehingga menaikkan target data justru memperlebar topik yang terjaring.

---

## 5. Keputusan

| Kode | Keputusan | Alasan |
|---|---|---|
| D1 | Memperlakukan label saat ini sebagai **label lemah**, bukan kebenaran | Semua angka kinerja mengukur kesesuaian terhadap anotator |
| D2 | **Menolak** bintang Google Play sebagai acuan otomatis | 101 kasus bertentangan; label teks terbukti lebih benar |
| D3 | Menyusun **gold set** manusia ±300 baris berlapis sebagai satu-satunya sumber skor validasi | Tanpa acuan, tidak ada cara mengukur perbaikan |
| D4 | Menambahkan kelas **`tidak_relevan`** dan memisahkan `tipe` teks | Memisahkan penilaian relevansi dari penilaian sentimen |
| D5 | Memperketat definisi netral dan mewajibkan kolom **bukti** serta **bahasa** | Menghentikan netral sebagai tempat penampungan |
| D6 | Mewajibkan konteks pada balasan; bila tidak tersedia, keyakinan diturunkan | 27,9% baris saat ini dinilai tanpa induk |
| D7 | Memperbaiki scraper sebelum menambah data | Menambah data tanpa perbaikan hanya memperbanyak derau |
| D8 | Memakai **SkillOpt setelah** gold set tersedia | SkillOpt butuh rollout berskor untuk gerbang validasi |

---

## 6. Prompt v2 — anotasi sadar konteks

Prompt ini sudah saya tanamkan pada `scraper/labeling.py` sebagai `SYSTEM_PROMPT_V2`, `build_user_prompt_v2`, dan `parse_label_v2`, lengkap dengan self-check yang lolos.

### 6.1 Prompt sistem

```
Anda anotator sentimen bahasa Indonesia untuk riset Sensus Ekonomi 2026 dan aplikasi Fasih BPS.
Anda menerima sebuah teks beserta keterangan asalnya. Tugas Anda menetapkan relevansi, sentimen,
tipe teks, aspek, dan bukti pemicu.

Ikuti aturan berikut secara berurutan.
1. Periksa relevansi lebih dahulu. Bila teks tidak membicarakan Sensus Ekonomi 2026, aplikasi
   Fasih BPS, petugas pendata, pelaksanaan pendataan, atau tanggapan atas hal tersebut, tetapkan
   sentimen "tidak_relevan". Contohnya percakapan tentang utang negara, kecerdasan buatan, atau
   program statistik lain seperti Sakernas.
2. Periksa kebermaknaan. Bila teks hanya berupa sapaan, penanda kehadiran, nama, atau stiker tanpa
   penilaian, tetapkan tipe "sapaan" dan sentimen "netral" dengan keyakinan paling tinggi 0,5.
   Jangan memaksakan sentimen pada teks semacam itu.
3. Gunakan "netral" hanya untuk pernyataan faktual, pertanyaan murni, atau laporan keadaan yang
   tidak memuat penilaian positif maupun negatif. Netral bukan tempat penampungan bagi teks yang
   sulit dinilai; bila teks sulit dinilai, turunkan keyakinan dan jelaskan sebabnya.
4. Baca konteks. Teks yang berupa balasan wajib dinilai bersama teks induknya. Panggilan "ka" atau
   "kak" menandakan percakapan dengan petugas, bukan penilaian terhadap layanan. Bila teks induk
   tidak tersedia, nyatakan keterbatasan itu pada kolom alasan dan turunkan keyakinan.
5. Perlakukan bahasa daerah dan campur kode sebagai teks yang sah. Sebutkan bahasanya, misalnya
   Sunda, Jawa, atau Melayu. Teks berbahasa asing yang tidak berkaitan dengan topik tetap ditandai
   "tidak_relevan".
6. Abaikan bintang ulasan pada Google Play. Nilai hanya isi teksnya, karena banyak pengulas memberi
   lima bintang sambil menyampaikan keluhan.
7. Perhitungkan negasi, perbandingan, dan sarkasme. Kalimat "malah tambah parah" bersentimen negatif
   meskipun memuat kata bermakna positif.
8. Sertakan kolom bukti berisi potongan pendek teks yang menjadi dasar penilaian, dan kolom alasan
   berisi satu kalimat penalaran.
Jawab HANYA dengan satu objek JSON valid, tanpa markdown, tanpa teks tambahan.
```

### 6.2 Kerangka permintaan pengguna

```
Platform: komentar video YouTube
Waktu unggah: 2026-08-01T10:00:00
Judul video: Sensus Ekonomi 2026 Resmi Dimulai | Fokus
Kanal: BPS Statistics
Teks yang dibalas: "Apakah sekolah negeri didata?"
Catatan: teks ini merupakan balasan, tetapi teks induk tidak tersedia sehingga penilaian
dilakukan secara terbatas.

Teks yang dianotasi: "didata ka @azahraes8370"

Balas dengan JSON seperti contoh berikut, lalu sesuaikan isinya:
{"relevan": true, "sentimen": "negatif", "tipe": "opini", "aspek": ["teknis_aplikasi"],
 "bahasa": "indonesia", "keyakinan": 0.9, "bukti": "sering error",
 "alasan": "Mengeluhkan gangguan teknis berulang."}
```

### 6.3 Perubahan skema keluaran

| Kolom | Versi 1 | Versi 2 |
|---|---|---|
| `sentimen` | positif, negatif, netral | ditambah **tidak_relevan** |
| `tipe` | tidak ada | **opini, pertanyaan, informasi, sapaan, lelucon** |
| `bahasa` | tidak ada | **indonesia, daerah, campur, asing** |
| `bukti` | tidak ada | potongan teks pemicu |
| `keyakinan` | ada | tetap, tetapi dibatasi 0,5 untuk tipe sapaan |

### 6.4 Cara menjalankan

```powershell
# uji prompt tanpa memanggil model
py -3.13 modeling/autolabel.py data/processed/dataset_se2026_ready.csv --dry-run

# pelabelan ulang penuh memakai endpoint vLLM Gemma di Modal
py -3.13 modeling/autolabel.py data/processed/dataset_se2026_ready.csv --mode endpoint
```

Saat ini `modeling/autolabel.py` masih memanggil `build_user_prompt` versi 1. Untuk beralih, ganti pemanggilan itu menjadi `build_user_prompt_v2(row)` dan `parse_label_v2(raw)`, lalu sesuaikan `EXTRA_COLUMNS` agar memuat kolom baru.

---

## 7. Pemanfaatan microsoft/SkillOpt

### 7.1 Apa itu SkillOpt

SkillOpt adalah pengoptimal ruang teks yang **melatih dokumen skill berbahasa alami** untuk agen LLM yang bobotnya dibekukan. Ia memakai istilah pelatihan jaringan saraf — epoch, ukuran batch, laju pembelajaran, gerbang validasi — tetapi yang berubah hanyalah berkas Markdown. Alurnya: rollout → refleksi → agregasi → seleksi → pembaruan → evaluasi. Sebuah model pengoptimal mengubah rollout yang sudah dinilai menjadi suntingan tambah/hapus/ganti yang dibatasi, dan suntingan hanya diterima bila skor validasi naik secara ketat. Luarannya `best_skill.md` berukuran 300–2.000 token. Lisensi MIT, Python 3.10+, paper arXiv:2605.23904.

### 7.2 Apakah dapat dipakai di sini

**Dapat, tetapi belum bisa dijalankan sekarang.** Kesesuaiannya tinggi: prompt pelabelan kita tepat berperan sebagai dokumen skill, dan model Gemma yang membeku tepat berperan sebagai target yang tidak dilatih.

Yang menghambat adalah **skor validasi**. Gerbang SkillOpt hanya menerima suntingan bila skor naik pada himpunan validasi, dan kita belum punya himpunan itu. Bintang Play Store sudah terbukti tidak layak (lihat 3.2), sedangkan label Gemma saat ini adalah objek yang justru ingin diperbaiki, sehingga tidak dapat dipakai menilai dirinya sendiri.

### 7.3 Rencana lima langkah

1. **Bangun gold set.** Ambil 300 baris secara berlapis menurut sumber, panjang teks, dan level keyakinan. Dua anotator manusia menilai secara terpisah; hitung kesepakatan (Cohen's kappa). Target kappa di atas 0,6. Sisihkan 150 baris sebagai validasi dan 150 baris sebagai uji.
2. **Siapkan adapter benchmark.** SkillOpt memerlukan paket `skillopt/envs/<nama>/` berisi pemuat data, fungsi rollout berskor, dan konfigurasi YAML. Acuan paling sederhana adalah `skillopt/envs/searchqa/`.
3. **Sambungkan backend.** Endpoint vLLM Gemma di Modal sudah mengikuti protokol OpenAI Chat Completions, sehingga cukup memakai backend `openai_compatible` tanpa menambah kode.
4. **Jalankan pelatihan skill.** Dokumen awal adalah `SYSTEM_PROMPT_V2`. Skor rollout adalah F1 macro pada himpunan validasi gold.
5. **Evaluasi dan bekukan.** Bandingkan `best_skill.md` terhadap prompt v1 dan v2 secara polos pada himpunan uji gold. Simpan hasilnya sebagai `reports/labeling_skill_hasil.md`.

### 7.4 Perkiraan manfaat

SkillOpt melaporkan kenaikan rata-rata 23,5 poin pada mode obrolan langsung untuk GPT-5.5, tetapi angka itu berasal dari tugas agen, bukan anotasi sentimen berbahasa Indonesia. Kenaikan di kasus kita kemungkinan jauh lebih kecil, karena prompt v2 sudah menutup tiga cacat terbesar. Manfaat terbesarnya justru pada **penemuan aturan yang tidak terpikirkan manusia** dari kesalahan berulang pada gold set.

---

## 8. Perbaikan scraper yang diusulkan

Urutan pengerjaan mengikuti rasio manfaat terhadap usaha:

| Prioritas | Berkas | Perbaikan |
|---|---|---|
| Tinggi | `scraper/youtube.py` | Menyaring video kanal berdasarkan kata kunci judul sebelum mengambil komentar |
| Tinggi | `scraper/youtube.py` | Menyimpan teks induk, bukan hanya identitasnya, agar balasan dapat dinilai berkonteks |
| Tinggi | `scraper/playstore.py` | Menghapus `_to_utc`; menyerahkan seluruh konversi ke `to_iso` agar stempel waktu tidak bergantung zona waktu host |
| Tinggi | Seluruh konektor | Menambahkan penyaring bahasa sebelum menyimpan rekaman |
| Sedang | `scraper/threads.py` | Mengambil teks dari elemen isi unggahan saja, bukan seluruh `article` |
| Sedang | `scraper/keywords.py` | Menambahkan padanan Inggris: "economic census", "census 2026", "BPS Statistics" |
| Sedang | `pipeline_SE2026.py` | Memisahkan batas jumlah video dari parameter `limit` |
| Rendah | `scraper/cleaning.py` | Menghapus pemetaan yang memetakan kata ke dirinya sendiri |
| Rendah | `scraper/cleaning.py` | Mempertahankan partikel wacana alih-alih membuangnya |

---

## 9. Dampak terhadap hasil studi ablasi

Studi ablasi sebelumnya menghasilkan urutan yang wajar dan tetap berlaku: model hemat parameter bersaing (BitFit 0,8490 dengan 0,08% parameter), penyetelan sebagian hampir memadai (partial_top_k 0,8609), dan R-Drop menambah perolehan (0,8769).

Namun tafsirnya perlu disesuaikan. Selama prompt v1 masih dipakai, angka-angka itu mengukur **seberapa setia model meniru anotator Gemma**, termasuk meniru kesalahannya. Dua akibat praktis:

1. Kebocoran near-duplikat 1,03% pada himpunan uji masih berada di atas ambang yang dapat diterima, sehingga angka tersebut belum layak dikutip sebagai hasil akhir.
2. Selama kelas netral memuat sampah, metrik F1 macro pada kelas itu tidak bermakna. Perbaikan prompt v2 diperkirakan mengubah sebaran kelas secara berarti, sehingga ablasi perlu dijalankan ulang setelah pelabelan ulang.

---

## 10. Langkah lanjut yang saya sarankan

1. Terapkan perbaikan prioritas tinggi pada scraper, lalu ambil ulang data dengan penyaring topik dan bahasa.
2. Jalankan pelabelan ulang memakai prompt v2.
3. Bentuk gold set 300 baris dan hitung kesepakatan antar anotator.
4. Jalankan ulang studi ablasi di Modal T4 dengan label baru, lalu bandingkan secara adil terhadap hasil lama.
5. Setelah gold set terbentuk, jalankan SkillOpt untuk mengoptimalkan prompt pelabelan terhadap skor validasi gold.

Tanpa langkah 3, seluruh angka tetap mengukur kesesuaian, bukan kualitas. Itu keputusan yang menurut saya paling menentukan.

---

## 11. Protokol untuk gold set yang hanya berisi 100 baris

### 11.1 Gold set dan pseudo-label adalah dua hal berbeda

Kerancuan istilah ini perlu diluruskan lebih dahulu, karena keduanya berperan berlawanan:

| | Gold set | Pseudo-label |
|---|---|---|
| Sumber | Verifikasi manusia | Keluaran model |
| Jumlah | 100 baris | ±9.577 baris sisanya |
| Peran | **Mengukur** | **Melatih** |
| Boleh dipakai untuk evaluasi | Ya | Tidak, karena melingkar |
| Boleh masuk data latih | Tidak | Ya |

Jadi seratus baris itu bukan pengganti pseudo-label, melainkan **pengawas** bagi pseudo-label. Model dilatih memakai pseudo-label, lalu kualitas prompt yang menghasilkan pseudo-label itu dinilai pada seratus baris gold.

### 11.2 Apa yang dapat dan tidak dapat diukur dengan 100 baris

Dengan seratus baris, selang kepercayaan 95% untuk akurasi selebar **±6 hingga 10 poin**. Artinya:

- **Dapat dideteksi:** perbaikan besar, misalnya prompt v2 menaikkan akurasi dari 0,72 ke 0,85. Selisih tiga belas poin itu jauh melampaui lebar selang.
- **Tidak dapat dideteksi:** selisih kecil, misalnya selisih ablasi 0,8769 melawan 0,8669 yang hanya 1,1 poin. Selisih itu berada jauh di dalam derau.

Demonstrasi nyata dari perangkat yang baru dibuat, memakai dua sistem sintetis berukuran seratus baris:

```
[predA] akurasi 0.8800 (selang 95%: 0.8019 - 0.9300, lebar 12.8 poin)
[predB] akurasi 0.8500 (selang 95%: 0.7672 - 0.9069, lebar 14.0 poin)
predA vs predB: pasangan berbeda 10 vs 13, p = 0.6776 -> belum berbeda nyata
```

Dua sistem berselisih tiga poin pun tidak terbukti berbeda pada seratus baris. Kesimpulan praktisnya: **jangan memakai seratus baris untuk mengejar selisih satu sampai tiga poin.** Selisih sekecil itu baru layak diuji setelah gold set melewati angka 500.

Sebaliknya, jumlah baris yang dibutuhkan untuk mencapai galat baku tertentu adalah:

| Galat yang diinginkan | Jumlah baris |
|---|---:|
| 10 poin | 97 |
| 5 poin | 385 |
| 3 poin | 1.068 |
| 2 poin | 2.401 |

### 11.3 Kunci yang membuat 100 baris tetap berguna: perbandingan berpasangan

Membandingkan dua angka akurasi secara langsung memang tidak peka pada seratus baris. Namun bila kedua sistem diuji pada **baris yang sama persis** dan hanya pasangan yang berbeda pendapat yang dihitung, kepekaannya naik berlipat. Uji McNemar eksak inilah yang dipakai perangkat baru, bukan sekadar membandingkan dua nilai agregat.

### 11.4 Protokol lima ronde

1. **Ronde 0 — rapikan seratus baris yang ada.** Periksa apakah sebarannya berlapis. Seratus baris yang seluruhnya berasal dari YouTube kelas negatif hampir tidak berguna. Jalankan `sample` bila perlu menyusun ulang.
2. **Ronde 1 — ukur prompt lama.** Jalankan prompt v1 pada seratus baris, catat akurasi beserta selangnya. Inilah titik acuan.
3. **Ronde 2 — ukur prompt v2, bandingkan berpasangan.** Jalankan `eval` dengan dua berkas prediksi sekaligus. Yang dibaca bukan selisih akurasi, melainkan nilai p McNemar.
4. **Ronde 3 — pseudo-label dan tambah gold secara aktif.** Labeli seluruh korpus memakai prompt terbaik, latih model, lalu jalankan `mine` untuk memilih seratus baris yang paling meragukan. Baris itulah yang diminta diverifikasi manusia.
5. **Ronde 4 — ulangi sampai gold mencapai ±500 baris.** Pada titik itu selisih tiga poin mulai terukur, dan SkillOpt sudah layak dijalankan dengan gerbang validasi yang berarti.

### 11.5 Aturan pengaman

- Gold set **tidak pernah** masuk ke data latih. Pelanggaran aturan ini membuat evaluasi tidak bermakna sama sekali.
- Evaluasi **tidak pernah** memakai pseudo-label sebagai kebenaran.
- Setiap laporan wajib menyertakan selang kepercayaan, bukan angka tunggal.
- Pseudo-label hanya diterima bila model yakin **dan** konsisten pada beberapa kali pengambilan dengan suhu berbeda. Label yang tidak konsisten lebih baik dibuang daripada dipaksakan.
- Perubahan sebaran kelas wajib dicatat, sebab penambahan kelas `tidak_relevan` akan mengubah komposisi korpus secara berarti.

### 11.6 Perangkat yang sudah tersedia

`modeling/gold_eval.py` menyediakan empat perintah, seluruhnya sudah diuji:

```powershell
# 1. menarik kandidat verifikasi secara berlapis
py -3.13 modeling/gold_eval.py sample --csv data/processed/dataset_se2026_ready_v2.csv --n 100 --skema seimbang --lapis konteks --blind --out data/processed/gold_100_v2.csv

# 2. menghasilkan lembar anotasi HTML untuk dinilai manusia
py -3.13 modeling/gold_eval.py sheet --gold data/processed/gold_100_v2.csv --out reports/lembar_anotasi_v2.html

# 3. mengukur dan membandingkan sistem secara berpasangan
py -3.13 modeling/gold_eval.py eval --gold gold_manusia.csv --pred prompt_v1.csv prompt_v2.csv

# 4. memilih kandidat ronde verifikasi berikutnya
py -3.13 modeling/gold_eval.py mine --csv data/processed/dataset_se2026_ready_v2.csv --gold gold_manusia.csv --n 100

# memeriksa kebenaran perhitungan statistiknya
py -3.13 modeling/gold_eval.py --selftest
```

Seluruh contoh di atas menunjuk `dataset_se2026_ready_v2.csv`, bukan korpus lama. Setelah pengambilan ulang pada seksi 14, korpus lama tidak dipakai lagi dan tidak boleh dicampur dengan yang baru.

Perintah `sheet` menghasilkan satu berkas HTML mandiri. Lembar itu menampilkan setiap teks beserta konteks asalnya, menyediakan lima tombol penilaian, menyimpan jawaban secara otomatis pada penyimpanan lokal peramban, dan menyediakan tombol ekspor CSV. Berkas hasil ekspor langsung dapat dipakai sebagai argumen `--gold` pada perintah `eval`, sehingga tidak perlu menyunting CSV secara manual.

### 11.7 Cara memilih seratus baris

Jawaban singkatnya: **bukan saya yang memilih, dan bukan acak polos pula.** Yang berjalan secara acak adalah pemilihan anggotanya; yang saya tentukan hanyalah lapisannya.

Tiga cara yang mungkin, beserta akibatnya pada seratus baris:

| Cara | Sifat | Akibat |
|---|---|---|
| Acak polos | Tidak memihak | YouTube 82, Play Store 14, Threads 4; negatif 51, netral 31, positif 18 |
| Dipilih manual | Memihak | Baris yang menarik perhatian cenderung terpilih, sehingga angkanya terlalu pesimistis |
| Acak berlapis | Tidak memihak sekaligus terkendali | Setiap sel sumber kali label memperoleh porsi yang sudah ditentukan |

Angka acak polos di atas berasal dari komposisi korpus: YouTube 82,2%, Google Play 13,9%, Threads 3,9%; label negatif 50,8%, netral 30,7%, positif 18,5%. Dengan acak polos, Threads hanya kebagian sekitar empat baris dan kelas positif sekitar delapan belas, sehingga keduanya tidak dapat disimpulkan apa pun.

Memilih manual justru lebih berbahaya. Orang cenderung memilih baris yang aneh atau meragukan, sehingga yang terukur bukan potret korpus melainkan potret kasus tersulit. Akurasinya akan tampak terlalu rendah dan tidak dapat dibandingkan antar ronde.

Rekomendasi saya: **skema seimbang sembilan sel.** Setiap sel sumber kali label memperoleh sebelas baris, dipilih acak dari dalam selnya. Hasilnya seperti ini, dan sudah saya jalankan:

| Sumber | Negatif | Netral | Positif | Jumlah |
|---|---:|---:|---:|---:|
| YouTube | 11 | 12 | 11 | 34 |
| Google Play | 11 | 11 | 11 | 33 |
| Threads | 11 | 11 | 11 | 33 |
| **Jumlah** | **33** | **34** | **33** | **100** |

Alasannya begini. Tujuan utama gold set ini adalah membandingkan dua prompt, bukan menghitung akurasi korpus secara persis. Uji McNemar hanya memedulikan pasangan yang berbeda pendapat pada baris yang sama, sehingga komposisi sampel sama sekali tidak mempengaruhi kesimpulan perbandingan. F1 macro pun sudah memberi bobot setara pada setiap kelas. Dengan kata lain, sampel seimbang justru lebih tepat untuk keperluan ini, bukan sekadar lebih rapi.

Satu catatan pelaporan: ketika angkanya keluar, sebutkan bahwa sampel disusun seimbang. Jangan menyebutkannya sebagai perkiraan akurasi korpus, karena komposisinya memang sengaja tidak mengikuti korpus.

**Anotasi wajib tersamar.** Kolom usulan model harus disembunyikan dari anotator, sebab melihat dugaan mesin membuat orang cenderung membenarkannya. Perintah `sample` menuliskan kolom `label_usulan` secara bawaan, jadi tambahkan `--blind` supaya kolom itu tidak ikut tertulis.

Pada ronde berikutnya aturan pemilihan berubah. Baris tidak lagi diambil acak, melainkan diambil dari yang paling meragukan melalui perintah `mine`.

```powershell
# seratus baris awal, seimbang lima sel, tersamar
py -3.13 modeling/gold_eval.py sample --csv data/processed/dataset_se2026_ready_v2.csv \
    --n 100 --skema seimbang --lapis konteks --blind --out data/processed/gold_100_v2.csv
```

Catatan: uraian pada pasal ini mula-mula disusun untuk korpus lama. Setelah pengambilan ulang, pelapisan memakai `--lapis konteks` karena korpus baru belum berlabel. Rinciannya ada pada seksi 14.8.

### 11.8 Jawaban singkat

Seratus baris **cukup** untuk mengetahui apakah prompt v2 jauh lebih baik daripada prompt v1, dan cukup untuk memulai lingkaran penambahan label secara aktif. Seratus baris **tidak cukup** untuk memutuskan selisih satu sampai tiga poin antar skenario ablasi. Karena itu, jangan menunggu gold set besar untuk mulai; mulailah dari seratus baris yang ada, lalu tumbuhkan melalui ronde penambahan di atas.

---

## 12. Penanganan baris yang tidak relevan

### 12.1 Keputusan pokok

**`tidak_relevan` bukan kelas keempat, melainkan gerbang penyaring.** Sentimen tetap tiga kelas. Baris di luar topik tidak dilatih sebagai kelas tersendiri, melainkan dikeluarkan dari korpus dan disimpan terpisah.

Alasannya tiga. Pertama, menambahkan kelas keempat mencampur dua urusan berbeda: urusan topik dan urusan polaritas. Kedua, isi kelas itu hampir seluruhnya berasal dari cacat scraper yang seharusnya dibereskan di sumbernya, bukan diakomodasi di model. Ketiga, bila dilatih, model berisiko menolak komentar sah yang kebetulan berbentuk tidak biasa.

### 12.2 Dua sumbu yang selama ini tercampur

Audit menemukan kelas "netral" versi pertama menampung tiga hal sekaligus. Setelah dipisahkan, ternyata ada dua sumbu yang berbeda, bukan satu:

| Sumbu | Pertanyaan | Nilai |
|---|---|---|
| Relevansi | Apakah teks membahas sensus ekonomi atau Fasih BPS? | relevan, tidak relevan |
| Keopinian | Apakah teks memuat penilaian? | opini, bukan opini |

Teks bisa relevan tetapi bukan opini, contohnya percakapan teknis "usaha pertanian tidak dicakup di SE ka". Teks itu bukan sampah, tetapi juga bukan sentimen. Versi pertama membuang keduanya ke dalam netral.

### 12.3 Empat ember keluaran

Modul `modeling/pseudo_label.py` memilah hasil anotasi menjadi empat ember:

| Ember | Isi | Perlakuan |
|---|---|---|
| `opini` | Relevan dan memuat penilaian | **Inti korpus.** Menjadi data latih sentimen |
| `non_opini` | Relevan tetapi hanya sapaan, pertanyaan, atau keterangan | Disimpan tetapi tidak dipakai melatih sentimen |
| `karantina` | Di luar topik | Dikeluarkan dari korpus, disimpan sebagai bukti audit scraper |
| `gagal` | Penguraian JSON gagal | Diperiksa ulang, tidak dipakai |

Berkas keluarannya `korpus_opinion.csv`, `korpus_non_opini.csv`, `karantina_tidak_relevan.csv`, dan `gagal_anotasi.csv`, seluruhnya di `data/processed/`.

### 12.4 Mengapa baris di luar topik tidak langsung dibuang

Justru karena jumlahnya bermakna. Karantina berfungsi sebagai alat ukur mutu scraper:

- Bila karantina berisi puluhan baris berbahasa Vietnam dari satu video, itu bukti bahwa sapuan kanal tanpa penyaring topik memang bermasalah.
- Bila setelah perbaikan scraper jumlah karantina turun mendekati nol, perbaikannya terbukti berhasil.
- Bila jumlah karantina justru besar dan tetap besar, itu tanda harus berhenti menambah data dan membereskan pengambilan data lebih dahulu.

Membuangnya tanpa mencatat sama dengan menghapus bukti.

### 12.5 Kapan justru perlu klasifikasi relevansi tersendiri

Ada satu keadaan yang membenarkan dibuatnya pengklasifikasi relevansi terpisah: **saat model dipakai di produksi** dan masukannya datang dari luar kendali kita, misalnya bila Fasih BPS ingin menyaring aduan warga secara otomatis. Pada keadaan itu, model perlu kemampuan menolak masukan di luar topik.

Namun pengklasifikasi itu harus berdiri sendiri sebagai model biner relevan atau tidak, **bukan** ditambahkan sebagai kelas keempat pada model sentimen. Dua tugas berbeda sebaiknya tidak dipaksakan pada satu kepala klasifikasi.

Untuk keperluan riset saat ini, gerbang penyaring pada tahap anotasi sudah memadai dan lebih murah.

### 12.6 Perangkat yang tersedia

```powershell
# melihat susunan permintaan anotasi tanpa memanggil model
py -3.13 modeling/pseudo_label.py data/processed/dataset_se2026_ready.csv --mode dry-run --limit 1

# menjalankan anotasi ulang memakai endpoint vLLM Gemma di Modal
py -3.13 modeling/pseudo_label.py data/processed/dataset_se2026_ready.csv --mode endpoint

# memilah ulang hasil yang sudah ada tanpa memanggil model lagi
py -3.13 modeling/pseudo_label.py data/processed/dataset_se2026_ready.csv --route-only

# memeriksa kebenaran logika pemilahan
py -3.13 modeling/pseudo_label.py --selftest
```

Anotasi bersifat dapat dilanjutkan. Hasil disimpan bertahap ke `data/processed/labels_v2_checkpoint.jsonl`, sehingga menjalankan ulang perintah yang sama akan melanjutkan dari baris terakhir alih-alih mengulang dari awal.

### 12.7 Satu peringatan

Berkas keluaran modul ini adalah **label semu**. Evaluasi tetap hanya boleh memakai gold set manusia. Jangan pernah menjalankan `gold_eval.py eval` dengan berkas `korpus_opinion.csv` sebagai acuan, karena itu melingkar.

---

## 13. Perbaikan kode pengambilan data

### 13.1 Ringkasan perubahan

| # | Cacat | Perbaikan | Berkas | Status |
|---|---|---|---|---|
| 1 | Sapuan kanal tanpa penyaring topik | Ditambahkan penyaring judul dua mode | `scraper/youtube.py`, `scraper/keywords.py` | Selesai |
| 2 | Teks induk tidak disimpan pada balasan | Ditambahkan kolom `parent_text` melalui peta identitas | `scraper/youtube.py` | Selesai |
| 3 | Stempel waktu Play Store tidak deterministik | Fungsi `_to_utc` dihapus | `scraper/playstore.py` | Selesai |
| 4 | Tidak ada penyaring bahasa | Ditambahkan deteksi Vietnam dan aksara lain | `scraper/cleaning.py` | Selesai |
| 5 | Teks Threads tercampur label antarmuka | Ditambahkan pembersihan baris dan batas panjang | `scraper/threads.py` | Selesai |
| 6 | Kata kunci hanya berbahasa Indonesia | Ditambahkan kueri berbahasa Inggris | `scraper/keywords.py` | Selesai |
| 7 | Pelebaran topik mengikuti `limit` | Jumlah video dipisahkan menjadi parameter tersendiri | `pipeline_SE2026.py` | Selesai |
| 8 | Pemetaan kata yang tidak berguna | Sembilan entri mati dibuang | `scraper/cleaning.py` | Selesai |
| 9 | Partikel wacana dibuang | Enam partikel dipertahankan | `scraper/cleaning.py` | Selesai |
| 10 | Bahasa komentar tertukar dengan bahasa video | Kolom `lang` dikosongkan, bahasa video disimpan di `video_lang` | `scraper/youtube.py` | Selesai |

### 13.2 Penyaring topik dua mode

Penyaring dibangun dengan dua mode agar tidak membuang data yang sah:

- **longgar** (bawaan) membuang judul yang memuat topik di luar lingkup, seperti Sakernas, Susenas, pemutakhiran, utang, inflasi, dan kecerdasan buatan. Video tutorial resmi yang judulnya tidak memuat kata kunci tetap lolos.
- **ketat** menuntut kata kunci topik hadir pada judul, sehingga lebih bersih tetapi berisiko membuang video yang sebenarnya relevan.

Mode longgar dipilih sebagai bawaan karena banyak materi resmi BPS berjudul bahasa Inggris tanpa kata "sensus", misalnya "EFFICIENT TREATMENT & USE FOR 1 HOUSE WITH 2 FAMILIES". Membuangnya berarti kehilangan ratusan komentar yang sah.

Konsekuensinya, mode longgar masih meloloskan video yang judulnya tidak informatif, seperti "The Struggle Behind the Aceh Tamiang Data". Karena itu gerbang relevansi pada prompt v2 tetap diperlukan dan tidak digantikan oleh penyaring ini. Penyaring memperkecil kontaminasi di hulu, gerbang anotasi membersihkan sisanya di hilir.

### 13.3 Bukti pengujian

Seluruh self-test lolos:

```
selftest keywords ok
selftest cleaning ok
selftest labeling v2 ok
selftest gold_eval ok
selftest pseudo_label ok
import semua modul ok
```

Penyaring topik diuji memakai sepuluh judul inti korpus yang wajib lolos dan empat judul kontaminasi yang wajib dibuang, seluruhnya diambil dari hasil audit.

Penyaring bahasa diuji pada data mentah sungguhan:

```
[dry-run] 12927 record
filter bahasa asing: 12927 -> 12903
```

Dua puluh empat rekaman dibuang, konsisten dengan dua puluh satu komentar Vietnam yang ditemukan audit ditambah beberapa rekaman beraksara lain.

### 13.4 Yang belum dapat diverifikasi

Perbaikan pada `scraper/threads.py` **belum teruji pada halaman sungguhan**. Pengambilan data Threads memerlukan peramban dan sesi masuk, sedangkan halaman pencariannya menampilkan dinding masuk ketika tidak ada sesi. Yang dapat dipastikan hanyalah logika pembersihan baris dan batas panjangnya berjalan tanpa galat. Perilaku pemilihan elemen tetap perlu diperiksa pada penjalanan langsung berikutnya.

### 13.5 Dampak yang perlu diperhatikan

Perubahan pada `scraper/cleaning.py` mengubah keluaran `clean_text`, sehingga kolom `text_clean` pada penjalanan berikutnya tidak akan identik dengan korpus lama. Dua akibatnya:

1. Sidik jari teks berubah, sehingga `dedupe_texts` akan menganggap baris lama dan baru sebagai teks yang berbeda. Pengambilan ulang data sebaiknya dimulai dari direktori mentah yang bersih.
2. Pembobotan model ikut berubah karena fitur masukannya berbeda. Hasil studi ablasi sebelumnya **tidak dapat dibandingkan langsung** dengan hasil setelah perbaikan.

Karena itu, pengambilan ulang data sebaiknya dijadwalkan bersamaan dengan pelabelan ulang memakai prompt v2, bukan dijalankan sebagian-sebagian.

---

## 14. Pelaksanaan pengambilan ulang data

### 14.1 Perintah yang dijalankan

Pengambilan ulang dilakukan pada 15 September 2026 ke direktori mentah yang baru, `data/raw_v2`, agar tidak bercampur dengan korpus lama.

```powershell
# 1. Google Play, satu kali jalan
py -3.13 pipeline_SE2026.py --sources playstore --keep-raw --raw-dir data/raw_v2 --out data/processed/_sementara.csv

# 2. YouTube, dua ronde bertahap dan dapat dilanjutkan
py -3.13 ambil_ulang_youtube.py --videos-per-query 20 --comments 200 --raw-dir data/raw_v2
py -3.13 ambil_ulang_youtube.py --videos-per-query 60 --comments 200 --raw-dir data/raw_v2 --log reports/ambil_ulang_youtube_ronde2.log

# 3. Menyusun korpus bersih dari data mentah
py -3.13 pipeline_SE2026.py --dry-run --raw-dir data/raw_v2 --saring-bahasa --out data/processed/dataset_se2026_ready_v2.csv
```

### 14.2 Hasil

| Tahap | Baris | Durasi |
|---|---:|---:|
| Google Play | 2.000 mentah | ± 20 detik |
| YouTube ronde pertama | 4.539 komentar | 707 detik |
| YouTube ronde kedua | 4.026 komentar | 1.781 detik |
| Threads melalui CLI | 396 komentar | 18 detik |
| Korpus akhir | **10.192 baris bersih** | — |

Perbandingan dengan korpus lama:

| | Korpus lama | Korpus baru |
|---|---:|---:|
| Total baris | 9.677 | **10.192** |
| Google Play | 1.348 | **1.608** |
| YouTube | 7.951 | **8.190** |
| Threads | 378 | **394** |
| Video unik | 243 | **265** |
| Balasan YouTube | 2.222 (27,9%) | 2.615 (31,9%) |
| **Balasan dengan konteks induk** | **0 (0,0%)** | **2.615 (100%)** |

Korpus baru lebih besar pada setiap sumber sekaligus lebih bersih. Yang paling menentukan adalah baris terakhir: seluruh balasan kini membawa teks induknya, sedangkan sebelumnya tidak satu pun.

### 14.3 Bukti bahwa penyaring topik bekerja di hulu

Penyaring bahasa kali ini nyaris tidak membuang apa pun:

```
[dry-run] 10565 record
filter bahasa asing: 10565 -> 10563
```

Hanya dua rekaman. Bandingkan dengan pengujian pada data mentah lama yang membuang dua puluh empat rekaman. Artinya video kecerdasan buatan Vietnam itu sudah tersaring lebih dahulu oleh penyaring topik, sehingga penyaring bahasa tidak lagi menemukan sasaran. Kedua lapis pertahanan bekerja sebagaimana dirancang: lapis pertama menahan di hulu, lapis kedua menjadi jaring pengaman.

### 14.4 Sisa kontaminasi yang perlu diketahui

Enam belas dari 265 judul video lolos pada mode longgar tetapi gagal pada mode ketat. Contohnya:

- "A Year of Impact for the Red and White Cabinet"
- "Gubernur BI Turut Sampaikan Selamat Hari Statistik Nasional 2025"
- "We Are Waiting for You at Politeknik Statistika STIS"
- "Barista Podcast Episode 3 - Generic Statistical Business Process Model (GSBPM)"
- "How to Overcome Fluency Problems"

Sebagian masih berkaitan dengan BPS, sebagian tidak. Karena itu gerbang relevansi pada prompt v2 tetap wajib dijalankan. Penyaring topik tidak dimaksudkan menggantikannya, melainkan mengurangi beban di hulu.

### 14.5 Threads

Pengambilan Threads berhasil memakai backend CLI `threads-comment-scraper` yang tersedia pada mesin ini, dan menghasilkan 394 baris. Kendala halaman pencarian yang sebelumnya menampilkan dinding masuk tidak terulang, karena jalur CLI tidak melewati peramban melalui kode kita.

Satu catatan penting: ukuran berkas keluaran Threads identik dengan hasil pengambilan sebelumnya, yaitu 314.322 bita. Hal itu menandakan CLI tersebut mengembalikan himpunan data yang sama, sehingga pengambilan ulang tidak menambah komentar baru untuk sumber ini. Penyaringan dan pembersihan tetap berlaku, tetapi volume Threads praktis tidak bertambah.

### 14.6 Berkas keluaran

| Berkas | Isi |
|---|---|
| `data/raw_v2/` | 40 berkas mentah (20 JSONL dan 20 CSV) dari Play Store, YouTube, dan Threads, seluruhnya 14,3 MB |
| `data/processed/dataset_se2026_ready_v2.csv` | 10.192 baris siap dianotasi ulang |
| `reports/ambil_ulang_youtube.log` | catatan ronde pertama |
| `reports/ambil_ulang_youtube_ronde2.log` | catatan ronde kedua |
| `ambil_ulang_youtube.py` | penggerak bertahap yang dapat dilanjutkan |

### 14.7 Langkah berikutnya

Korpus `dataset_se2026_ready_v2.csv` masih memiliki kolom `label` kosong. Isinya perlu dianotasi memakai prompt v2 melalui `pseudo_label.py`, yang akan sekaligus memilahnya menjadi ember opini, non-opini, dan karantina.

Perlu ditegaskan bahwa korpus lama **tidak boleh dicampur** dengan yang baru, karena perbedaan keluaran `clean_text` membuat sidik jari teks dan fitur masukan berbeda. Hasil studi ablasi lama hanya berlaku untuk korpus lama.

### 14.8 Gold set untuk korpus baru

Setelah korpus diganti, lembar anotasi yang lama menjadi tidak berlaku. Lembar itu dibuat dari korpus lama, sehingga melabelinya berarti menghabiskan usaha pada data yang akan ditinggalkan.

**Korpus baru harus berdiri sendiri, tanpa satu pun tautan ke korpus lama.** Alasannya metodologis: kedua korpus memakai keluaran `clean_text` yang berbeda, sehingga `text_clean`, sidik jari teks, dan fitur masukan tidak sebanding. Menarik label dari korpus lama akan mencampurkan dua definisi teks yang berbeda ke dalam satu penilaian.

Karena itu, penarikan kandidat tidak boleh bergantung pada label sama sekali. Perintah `sample` diberi opsi `--lapis konteks`, yang melapis menurut **sumber, status balasan, dan panjang teks**. Ketiganya tersedia pada korpus yang belum berlabel, sehingga korpus baru dapat dipakai langsung tanpa perantara.

```powershell
py -3.13 modeling/gold_eval.py sample --csv data/processed/dataset_se2026_ready_v2.csv \
    --n 100 --skema seimbang --lapis konteks --blind --out data/processed/gold_100_v2.csv

py -3.13 modeling/gold_eval.py sheet --gold data/processed/gold_100_v2.csv \
    --out reports/lembar_anotasi_v2.html
```

Sebaran hasilnya:

| Sel | Jumlah |
|---|---:|
| Play Store, komentar utama | 20 |
| Threads, komentar utama | 20 |
| Threads, balasan | 20 |
| YouTube, komentar utama | 20 |
| YouTube, balasan | 20 |
| **Jumlah** | **100** |

Penandaan balasan menyesuaikan tiap platform: YouTube menandainya melalui kolom `parent`, sedangkan Threads melalui kolom `type`. Keduanya diperiksa agar pelapisan tetap sahih.

Berkas kandidat yang dihasilkan **sama sekali tidak memuat kolom label**: kolomnya hanya `uid, source, text, text_clean, created_at, url, konteks, label_manusia, catatan`. Dengan begitu tidak ada jalan bagi label lama untuk masuk, sengaja maupun tidak.

Artefak gold yang berasal dari korpus lama sudah dihapus agar tidak menimbulkan kekeliruan: `gold_100.csv`, `gold_kandidat.csv`, `gold_kandidat_seimbang.csv`, `gold_kandidat_ronde2.csv`, dan `lembar_anotasi.html`.

Rantai korpus baru kini bersih dari hulu ke hilir:

```
data/raw_v2/  ->  dataset_se2026_ready_v2.csv  ->  gold_100_v2.csv  ->  lembar_anotasi_v2.html
```

Tidak satu pun dari empat berkas itu membaca data dari `data/raw/` atau `dataset_se2026_labeled.csv`.

Lembar anotasi versi baru juga menampilkan konteks yang lebih lengkap: selain judul video dan kanal, baris yang berbentuk balasan kini menampilkan teks yang dibalas, berkat perbaikan `parent_text` pada tahap pengambilan data.

---

## 15. Penyaring topik untuk Threads

### 15.1 Masalah yang ditemukan

Pemeriksaan lanjutan menemukan bahwa data Threads memuat percakapan yang sama sekali tidak membahas Sensus Ekonomi 2026. Bukan sekadar pembicaraan ekonomi umum, melainkan **politik**: perdebatan tentang peristiwa 1998, tuduhan hoaks, dan provokasi.

| Temuan pada 394 baris Threads | Jumlah | Porsi |
|---|---:|---:|
| Mengandung penanda sensus | 259 | 65,7% |
| Hanya membahas ekonomi umum | 4 | 1,0% |
| **Tanpa penanda sensus sama sekali** | **131** | **33,2%** |

### 15.2 Sebabnya

Pencarian Threads melakukan **pencocokan sebagian**. Kueri "sensus ekonomi" tidak menuntut frasa itu hadir utuh, sehingga unggahan yang hanya memuat kata "ekonomi" ikut dikembalikan. Setelah unggahan tertangkap, antarmuka CLI menarik **seluruh komentarnya**, sehingga satu unggahan yang meleset membawa puluhan komentar yang meleset pula.

Perilaku itu berbeda dari YouTube, yang memakai pencarian berbasis kueri dan kanal resmi sehingga lebih mudah disaring melalui judul video.

### 15.3 Perbaikan

Penyaring dibangun pada tingkat **teks**, bukan judul, karena Threads tidak memiliki judul. Rekaman dipertahankan bila teksnya **atau teks unggahan induknya** memuat penanda topik:

```
sensus, se2026, fasih, pencacah, pendata, didata, didatangi, mendata,
blok sensus, kuesioner, responden, petugas, pengawas, mitra bps,
bps, badan pusat statistik, sls, ppl, pml
```

Pemeriksaan pada **kedua teks sekaligus** itu penting. Banyak komentar lapangan sangat pendek dan baru bermakna setelah dibaca bersama unggahan induknya, misalnya "Jadikan nomer bangunan terakhir kak" atau "Serius tadi pagi WA grup disuruh nambah usaha".

Penyaring diletakkan di tahap penyusunan korpus, **bukan** di tahap pengambilan data. Tujuannya agar berkas mentah tetap utuh dan dapat ditelusuri, sedangkan penyaringan dapat diulang bila polanya diperbaiki. Perilaku ini sejalan dengan perlakuan karantina pada seksi 12.

### 15.4 Hasil

```
filter topik Threads: 10959 -> 10838
```

| Sebelum | Sesudah |
|---:|---:|
| 394 baris | **275 baris** |

Seratus sembilan belas baris dibuang, persis seperti perkiraan pengujian pola. Setelah penyaringan, **tidak ada lagi baris Threads yang hanya membahas ekonomi umum**, dan 259 dari 275 baris (94,2 persen) menyebut penanda sensus secara eksplisit.

Enam belas baris sisanya sempat ditandai tanpa penanda oleh pemeriksaan awal, tetapi setelah diperiksa ternyata **relevan**: baris-baris itu memakai jargon lapangan seperti "prelist", "turlap", "assignment", "uji petik", dan "SLS". Penyaring justru benar karena menangkapnya melalui kata `sls`, `ppl`, `didata`, dan `didatangi`. Hal ini menunjukkan bahwa penanda harus mencakup istilah kerja petugas, bukan hanya nama program.

### 15.5 Cara mematikan

Penyaring aktif secara bawaan. Untuk melihat korpus tanpa penyaring:

```powershell
py -3.13 pipeline_SE2026.py --dry-run --raw-dir data/raw_v2 --saring-bahasa --tanpa-saring-topik-threads
```

### 15.6 Dampak pada korpus

Korpus baru turun dari 10.192 menjadi **10.073 baris** (Google Play 1.608, Threads 275, YouTube 8.190). Kandidat gold dan lembar anotasi sudah ditarik ulang dari korpus ini, sehingga keduanya bebas dari percakapan politik yang terbawa sebelumnya.

Perlu dicatat bahwa penyaring ini bersifat leksikal, sehingga masih mungkin meloloskan percakapan di luar topik yang kebetulan memuat kata penanda. Gerbang relevansi pada prompt v2 tetap menjadi lapis kedua yang menangkap sisanya.

---

## 16. Pemindaian menyeluruh korpus

### 16.1 Cara pemindaian

Seluruh 10.073 baris korpus dipindai memakai `modeling/audit_korpus.py`. Berbeda dari `validate_dataset.py` yang menitikberatkan duplikasi dan kebocoran pembagian data, modul ini menitikberatkan **mutu isi dan kesesuaian topik**.

```powershell
py -3.13 modeling/audit_korpus.py data/processed/dataset_se2026_ready_v2.csv --contoh 3
```

Pemeriksaan yang dijalankan pada setiap baris:

| Pemeriksaan | Arti | Keparahan |
|---|---|---|
| `teks_kosong` | teks bersih habis sama sekali | kritis |
| `bahasa_asing` | memakai aksara atau diakritik di luar Indonesia | kritis |
| `luar_topik` | video asal atau unggahan induk tidak membahas sensus | tinggi |
| `banyak_dibuang` | lebih dari 70% teks asli terbuang saat dibersihkan | tinggi |
| `topik_lemah` | judul video lolos penyaring longgar tetapi tanpa kata kunci | sedang |
| `terlalu_pendek` | teks bersih di bawah sepuluh aksara | sedang |
| `duplikat` | teks bersih persis sama dengan baris lain | sedang |
| `nyaris_duplikat` | mirip dengan baris lain melewati ambang kemiripan | rendah |

Tingkat keparahan dipakai untuk **mengurutkan peninjauan**, bukan membuang otomatis. Keputusan akhir tetap pada manusia, dan seluruh baris bertanda tersedia pada `data/processed/karantina_scan.csv`.

### 16.2 Hasil

| Tingkat | Jumlah |
|---|---:|
| Bersih | **9.068 (90,0%)** |
| Rendah | 327 |
| Sedang | 668 |
| Tinggi | 10 |
| Kritis | **0** |

| Temuan | Jumlah |
|---|---:|
| `topik_lemah` | 397 |
| `nyaris_duplikat` | 380 |
| `terlalu_pendek` | 286 |
| `banyak_dibuang` | 10 |
| `luar_topik` | **0** |
| `bahasa_asing` | **0** |
| `teks_kosong` | **0** |

Tiga temuan bernilai nol itu penting. Tidak ada lagi baris di luar topik, tidak ada bahasa asing, dan tidak ada teks yang hancur. Ketiganya adalah hasil kerja penyaring pada seksi 13 dan 15.

Per sumber:

| Sumber | Total | Bertanda | Rincian |
|---|---:|---:|---|
| Google Play | 1.608 | 173 | nyaris duplikat 62, terlalu pendek 111 |
| Threads | 275 | 3 | nyaris duplikat 3 |
| YouTube | 8.190 | 897 | topik lemah 397, nyaris duplikat 315, terlalu pendek 175, banyak dibuang 10 |

### 16.3 Bug yang ditemukan pemindaian: huruf hias Unicode

Pemindaian menemukan tiga baris berkategori kritis yang teksnya kosong. Setelah diperiksa, penyebabnya bukan data yang buruk, melainkan **cacat pada kode pembersih**.

Sebagian pengguna menulis dengan huruf hias Unicode. Contoh nyata dari korpus:

```
𝙎𝙚𝙣𝙨𝙪𝙨 𝙚𝙠𝙤𝙣𝙤𝙢𝙞 𝙠𝙖𝙡𝙞𝙖𝙣 𝙢𝙖𝙪 𝙩𝙪𝙧𝙪𝙣 𝙠𝙚 𝙟𝙖𝙡𝙖𝙣, 𝙜𝙢𝙣 𝙥𝙚𝙣𝙙𝙚𝙧𝙞𝙩𝙖𝙖𝙣 𝙧𝙖𝙠𝙮𝙖𝙩...
```

Huruf-huruf itu berada di blok Unicode Mathematical Alphanumeric Symbols. Penyaring non-alfanumerik `[^a-zA-Z0-9 \n]` membuangnya seluruhnya, sehingga teks bersih menjadi kosong. Isi komentarnya **hilang tanpa jejak**, padahal aslinya berbunyi "Sensus ekonomi kalian mau turun ke jalan...".

Perbaikannya adalah menyeragamkan bentuk huruf lebih dahulu memakai normalisasi NFKC sebelum penyaringan:

```python
t = unicodedata.normalize("NFKC", text)
```

NFKC memetakan huruf hias ke padanan ASCII-nya, sehingga isi teks terselamatkan. Hasilnya langsung terlihat: temuan `teks_kosong` turun dari **3 menjadi 0**, dan kategori kritis hilang seluruhnya.

Cacat ini tidak akan pernah terlihat dari pemeriksaan statistik biasa. Ia hanya muncul karena seluruh baris dipindai satu per satu.

### 16.4 Memahami temuan `topik_lemah`

Tiga ratus sembilan puluh tujuh baris berada pada video yang judulnya lolos penyaring longgar tetapi tidak memuat kata kunci topik. Setelah diperiksa, kelompok ini **bercampur dua hal yang berbeda**:

- Relevan tetapi berjudul tidak lazim, misalnya "tata cara pengisian L2". L2 adalah formulir sensus, jadi komentarnya sah meskipun judulnya tidak memuat kata "sensus".
- Benar-benar di luar lingkup, misalnya "Indonesia Full Sequence of Accounts (FSA)" dan "Sri Soelistyowati Pulang Ngantor – Bongkar Penghitungan Pertumbuhan Ekonomi!".

Karena itu temuan ini berstatus **sedang**, bukan tinggi. Ia menandai wilayah yang perlu ditinjau, bukan kesalahan yang pasti. Yang menentukan tetap gerbang relevansi pada tahap anotasi.

### 16.5 Temuan yang tidak perlu dikhawatirkan

`nyaris_duplikat` sebanyak 380 baris dan `terlalu_pendek` sebanyak 286 baris tampak besar, tetapi keduanya wajar:

- Teks pendek seperti "good luck", "bisa lah", dan "apk TAI" memang berasal dari ulasan singkat. Sebagian tetap membawa sentimen, sebagian tidak.
- Kemiripan tinggi lazim pada ulasan aplikasi, misalnya "aplikasi keren" yang muncul berkali-kali dari pengguna berbeda.

Keduanya bukan tanda data rusak, melainkan sifat alami korpus media sosial.

### 16.6 Berkas keluaran

| Berkas | Isi |
|---|---|
| `data/processed/karantina_scan.csv` | 1.005 baris bertanda beserta tingkat keparahan dan alasannya |
| `reports/scan_korpus.json` | ringkasan lengkap per sumber, per temuan, dan per tingkat |
| `modeling/audit_korpus.py` | alat pemindai yang dapat dijalankan ulang |

Setelah pemindaian ini, korpus disusun ulang dan kandidat gold ditarik ulang, sehingga `dataset_se2026_ready_v2.csv`, `gold_100_v2.csv`, dan `lembar_anotasi_v2.html` semuanya mencerminkan keadaan terbaru.

---

## 17. Pelabelan ulang memakai prompt v2

### 17.1 Endpoint Gemma ditemukan tanpa perlu token HF

Kendala yang selama ini menghambat ternyata tidak ada. App `sensus-ekonomi-gemma` sudah ter-deploy sejak 15 September 2026, dan alamat endpoint-nya dapat dibaca langsung dari Modal:

```
https://anwarrohmadi111--sensus-ekonomi-gemma-serve.modal.run/v1
```

Model yang dilayani adalah `gemma-4-12b-qat` dengan panjang konteks 8.192 token. Cold start memakan 118 detik, dan setelah itu peladen tetap hangat selama 15 menit tanpa permintaan. **Token Hugging Face tidak diperlukan** karena rahasia sudah tertanam pada deployment yang berjalan.

### 17.2 Dua bug yang ditemukan uji coba

Uji coba sepuluh baris mengungkap dua cacat yang tidak akan terlihat tanpa menjalankan alurnya sungguhan.

**Bug pertama: prompt v2 tidak menyebutkan nilai yang sah.**

Prompt versi pertama memuat daftar aspek dan sentimen yang diizinkan. Ketika saya menulis v2, daftar itu hilang dan hanya digantikan satu contoh JSON. Akibatnya model mengarang nilai di luar daftar:

| Kolom | Nilai yang dikarang model |
|---|---|
| aspek | `fungsionalitas_aplikasi`, `pembaruan_aplikasi`, `pelaksanaan_pendataan`, `performa_aplikasi`, `stabilitas_server`, `efisiensi_waktu` |
| tipe | `harapan` |
| bahasa | `inggris` |

Pengurai kita membuang nilai yang tidak dikenal, sehingga **kolom aspek hampir seluruhnya kosong**. Datanya masuk, tetapi informasinya hilang di tahap penguraian.

Perbaikannya adalah mencantumkan seluruh nilai yang diizinkan pada prompt sistem.

**Bug kedua: `guided_json` diabaikan oleh vLLM versi ini.**

Kode lama meminta penegakan skema melalui `extra_body={"guided_json": ...}`. Untuk menguji apakah penegakan itu benar-benar berjalan, saya memberi skema yang **sengaja mustahil**: teks ujinya jelas negatif, tetapi enum sentimen hanya mengizinkan `positif`. Bila penegakan aktif, keluarannya wajib `positif`.

| Cara pemanggilan | Keluaran | Kesimpulan |
|---|---|---|
| tanpa penegakan | negatif | patokan |
| `guided_json` | negatif | **tidak ditegakkan** |
| `response_format` | positif | ditegakkan |
| `structured_outputs` | positif | ditegakkan |

Jadi parameter yang kita pakai selama ini tidak melakukan apa pun, dan keluaran hanya menuruti prompt. Perbaikannya adalah beralih ke `response_format` dengan skema JSON, yang sekaligus merupakan bentuk standar OpenAI sehingga lebih mudah dipindahkan ke peladen lain. Tersedia juga `--skema-mode` untuk memilih cara lain bila diperlukan.

### 17.3 Hasil setelah perbaikan

| | Sebelum perbaikan (10 baris) | Sesudah perbaikan (15 baris) |
|---|---:|---:|
| `tipe` sah | 9 | **15** |
| `bahasa` sah | 9 | **15** |
| `aspek` terisi | hampir nol | **15** |

Ketiga kolom kini terisi penuh dan seluruh nilainya berada di dalam daftar yang diizinkan.

Contoh keluaran yang sehat:

```json
{"relevan": true, "sentimen": "negatif", "tipe": "opini",
 "aspek": ["teknis_aplikasi"], "bahasa": "indonesia", "keyakinan": 0.95,
 "bukti": "gk bisa submit", "alasan": "Pengguna melaporkan kegagalan pengiriman data."}
```

### 17.4 Perintah pelabelan penuh

```powershell
py -3.13 modeling/pseudo_label.py data/processed/dataset_se2026_ready_v2.csv \
    --mode endpoint \
    --base-url https://anwarrohmadi111--sensus-ekonomi-gemma-serve.modal.run/v1 \
    --concurrency 12 \
    --checkpoint data/processed/labels_v2_checkpoint.jsonl \
    --out-dir data/processed \
    --summary reports/pseudo_label_summary.json
```

Anotasi bersifat dapat dilanjutkan melalui checkpoint, sehingga penjalanan yang terputus tidak mengulang dari awal.

### 17.5 Pelajaran dari kejadian ini

Dua bug ini memenuhi satu pola yang sama: **kode yang tampak benar tetapi tidak melakukan apa yang kita kira**. Pada kasus pertama, prompt terlihat lengkap karena ada contoh JSON, padahal daftar nilainya hilang. Pada kasus kedua, parameter penegakan skema terlihat meyakinkan, padahal diabaikan oleh pustakanya.

Keduanya hanya terlihat dengan menjalankan satu permintaan sungguhan lalu memeriksa keluarannya satu per satu. Pemeriksaan statistik tidak akan menangkapnya, karena secara format keluaran tetap JSON yang sah.

---

## 18. Prompt v3 dan hasil uji A/B

### 18.1 Apa yang ditambahkan

Prompt v3 disusun memakai pola dari skill `prompt-engineering-patterns` (wshobson/agents, 21.400 pemasangan, lolos tiga audit keamanan). Dari delapan praktik terbaik pada skill itu, dua yang belum terpenuhi adalah **"tunjukkan, jangan jelaskan"** dan **"pembuatan versi prompt sebagai kode"**.

Prompt v2 hanya memuat satu contoh JSON. Prompt v3 menambahkan **enam contoh anotasi** yang diambil dari kasus nyata hasil audit, sengaja dipilih untuk mewakili kasus batas yang paling sering salah:

1. Balasan pendek berupa pertanyaan teknis → `pertanyaan`, bukan `netral`
2. Penanda kehadiran → `sapaan` dengan keyakinan 0,5
3. Percakapan politik → `tidak_relevan`
4. Ulasan bintang lima yang isinya keluhan → `negatif`, bintang diabaikan
5. Keluhan berbahasa Sunda → `daerah`
6. Ulasan bintang satu yang isinya pujian → `positif`, bintang diabaikan

Contoh keempat dan keenam dipilih khusus karena bintang Google Play sempat menyesatkan kita. Prompt v2 hanya **memberi tahu** untuk mengabaikan bintang; v3 **menunjukkannya**.

Prompt v2 dipertahankan tanpa perubahan agar keduanya dapat dibandingkan secara adil. Pilihan versi tersedia melalui `--prompt-versi v2|v3`.

### 18.2 Hasil uji A/B

Kedua versi dijalankan pada tiga puluh baris yang sama:

| Ukuran | Hasil |
|---|---:|
| Beda sentimen | 2 dari 30 (tingkat kesepakatan 93,3%) |
| Beda tipe | 1 dari 30 |
| Beda bahasa | 0 dari 30 |
| Keyakinan rata-rata v2 | 0,873 |
| Keyakinan rata-rata v3 | 0,862 |
| Aspek terisi v2 | 29 dari 30 |
| Aspek terisi v3 | 27 dari 30 |

Dua perbedaan sentimennya:

| Teks | v2 | v3 |
|---|---|---|
| "kerjaan aparat desa dsb d limpahkan ke tad pln" | `negatif` | `tidak_relevan` |
| "good luck" | `tidak_relevan` | `netral` |

Pada baris pertama v2 tampak lebih tepat, sebab teks itu memang membahas pekerjaan pendataan. Pada baris kedua keduanya dapat dibenarkan, meskipun jawaban yang paling sesuai sebenarnya `sapaan`.

### 18.3 Kesimpulan yang jujur

**v3 tidak menunjukkan perbaikan yang terukur, dan pada satu ukuran justru sedikit lebih lemah.** Tiga puluh baris terlalu sedikit untuk menyimpulkan apa pun secara pasti, tetapi tidak ada bukti yang membenarkan penggantian.

Biayanya juga nyata: v3 menambah sekitar 550 token pada setiap permintaan, atau sekitar 5,5 juta token untuk seluruh korpus. Pada model yang dihosting sendiri itu berarti waktu GPU tambahan.

Karena itu **korpus tetap memakai keluaran v2**, dan v3 disimpan untuk diuji dengan cara yang benar.

Menarik bahwa skill itu sendiri memperingatkan hal ini pada bagian *Common Pitfalls*: **"Over-engineering: Starting with complex prompts before trying simple ones."** Saya menambah enam contoh tanpa lebih dahulu memastikan bahwa kurangnya contoh memang penyebab kesalahan. Itu keliru menurut ukuran skill itu sendiri.

### 18.4 Langkah yang benar

Perbandingan sesungguhnya hanya dapat dilakukan pada **gold set**, bukan pada tiga puluh baris tanpa acuan. Setelah seratus baris terisi label manusia:

```powershell
# v2 dan v3 dijalankan pada seratus baris gold yang sama, lalu dibandingkan
py -3.13 modeling/gold_eval.py eval --gold gold_manusia.csv --pred prediksi_v2.csv prediksi_v3.csv
```

Yang dibaca adalah nilai p McNemar, bukan selisih akurasi. Bila v3 menang secara nyata, korpus dilabeli ulang dengan v3. Bila tidak, v2 dipertahankan dan v3 dihapus.

### 18.5 Keadaan korpus saat ini

Pelabelan penuh memakai v2 sudah selesai untuk seluruh 10.071 baris, dan hasilnya dipilah menjadi empat ember:

| Ember | Jumlah | Porsi |
|---|---:|---:|
| `opini` | **6.476** | 64,3% |
| `non_opini` | 3.143 | 31,2% |
| `karantina` | 452 | 4,5% |
| `gagal` | 0 | 0% |

Sebaran sentimen pada ember opini: negatif 4.614, positif 1.599, **netral hanya 263**.

Angka terakhir itu layak dicermati. Pada korpus lama kelas netral mencapai 2.967 baris atau 30,7 persen. Setelah kelas netral dipisahkan dari pertanyaan, sapaan, dan keterangan, sisanya hanya **263 baris atau 4,1 persen**. Ini menegaskan dugaan dari audit seksi 3.3: kelas netral pada korpus lama bukanlah kelas sentimen, melainkan tempat penampungan.

Temuan lain: 3.143 baris `non_opini` terdiri atas 1.773 pertanyaan, 914 keterangan, 591 sapaan, dan sisanya lelucon. Seluruh baris itu sebelumnya masuk data latih sentimen dan mengotori kelas netral.

---

## 19. Audit mutu label semu v2 pada seluruh 10.071 baris

### 19.1 Batas yang harus diakui lebih dahulu

Pertanyaan "apakah label Gemma benar semua" **belum dapat dijawab** dalam arti sebenarnya, karena kebenaran hanya dapat diukur terhadap acuan manusia, dan gold set itu belum terisi. Yang dapat diukur adalah dua hal yang memberi batas: **konsistensi internal** label terhadap aturan prompt v2 sendiri, serta **kedasaran bukti** alias apakah potongan `bukti` yang dikutip benar-benar berasal dari teks asalnya.

Keduanya dijalankan pada **setiap baris**, bukan pada contoh acak, sebab cacat label yang jarang justru yang paling berbahaya bila lolos ke data latih. Perangkatnya `modeling/audit_label.py` (self-test lolos) dan keluarannya `reports/audit_label_v2.json`, `reports/audit_label_v2.html`, serta `data/processed/karantina_label_v2.csv`.

### 19.2 Hasil ringkas

| Ukuran | Nilai |
|---|---:|
| Baris dipindai | 10.071 |
| Baris bertanda | **2.073 (20,6%)** |
| Bukti yang benar-benar berdasar teks | **100,0%** |
| Teks identik dengan sentimen berbeda | **0** |
| Baris tanpa anotasi | 2 |

| Keparahan | Jumlah |
|---|---:|
| Kritis | **0** |
| Tinggi | 327 |
| Sedang | 312 |
| Rendah | 1.434 |

### 19.3 Yang terbukti sehat

Tiga hal ini penting dan tidak boleh tenggelam oleh angka temuan yang terlihat besar:

1. **Tidak ada satu pun cacat kritis.** Seluruh nilai `sentimen`, `tipe`, dan `bahasa` berada di dalam daftar yang diizinkan, seluruh `keyakinan` berada pada rentang 0–1, dan tidak ada baris `tidak_relevan` yang menyusup ke ember latih. Penguraian JSON 100 persen bersih.
2. **Bukti tidak dihalusinasi.** Setiap kutipan `bukti` dapat dilacak ke teks asalnya. Tiga ratus lima puluh delapan di antaranya berupa parafrase ringan — misalnya teks "rewel sangat" dikutip sebagai "rewel banget" — tetapi intinya sama dan tidak ada yang dikarang.
3. **Model benar-benar menilai teks, bukan bintang.** Terdapat 140 ulasan bintang lima yang dilabeli negatif dan 7 ulasan bintang satu yang dilabeli positif. Itu bukan kesalahan, melainkan bukti bahwa perintah aturan 6 dipatuhi: bintang memang tidak dipercaya sejak audit pertama.

### 19.4 Cacat yang nyata

| Temuan | Jumlah | Catatan |
|---|---:|---|
| `sapaan_bersentimen` | 165 | Sapaan diberi sentimen positif/negatif, melanggar aturan 2 yang menuntut netral. Mayoritas berupa emoji "thumbs up" yang diterjemahkan model menjadi teks lalu dilabeli positif dengan keyakinan 0,5. |
| `sapaan_beraspek` | 230 | Sapaan yang tetap diberi aspek, padahal aturan 2 meminta aspek dikosongkan. |
| `karantina_bertopik` | 87 | Baris dikarantina padahal teks atau teks induknya memuat penanda topik. Sebagian wajar (sapaan "terimakasih pak" pada unggahan bertopik), tetapi sebagian mencurigakan — contohnya "yang sekolah masih belum paham mana ada di sls" yang menyebut SLS dan justru dibuang. |
| `opini_teks_pendek` | 149 | Teks di bawah sepuluh aksara di ember latih, seperti "apk tai", "bgus", dan "jos jos". Sebagian tetap membawa sentimen, sebagian tidak. |
| `asing_tapi_relevan` | 18 | Teks berbahasa Inggris yang tetap dimasukkan sebagai opini, misalnya "very excellent" dan "the best". Dapat dibenarkan karena membahas aplikasinya langsung. |
| `aspek_kosong` | 6 | Seluruhnya berjenis `lelucon` tanpa aspek, isinya "wkwkwk" dan "lol". |
| `bukti_kosong` | 2 | Dua baris di karantina tanpa kolom bukti. |
| Tanpa anotasi | 2 | Uid berakhir `...a1b1c` (Play Store, teks "ok") dan `...398f6` (YouTube, teks "up"), keduanya di bawah ambang panjang teks sehingga tidak pernah dikirim ke anotator. |

Satu cacat rancangan yang terungkap dari pemindaian ini **tidak terlihat dari hitungan temuan**: jenis `lelucon` tidak dimasukkan ke `TIPE_NON_OPINI` pada `modeling/pseudo_label.py`, sehingga **97 baris lelucon masuk ke ember opini** dan ikut menjadi data latih sentimen. Isinya bercampur: "melatih kesabaran petugas sensus hahah" memang membawa nada negatif, tetapi "wkwkwk samaan qt" dan "hahaa iya pasti" tidak membawa sentimen apa pun.

### 19.5 Kalibrasi keyakinan

Sebaran keyakinan menumpuk pada 0,8–0,9, dengan **882 baris bernilai mutlak 1,0** dan **500 baris di bawah 0,6**. Model terlalu yakin pada sebagian besar baris. Akibat praktisnya: keyakinan mentah **tidak boleh** dipakai sebagai ambang penyaringan sebelum dikalibrasi, sebab ambang apa pun akan membuang baris yang sebenarnya mudah dengan dalih keraguan yang salah tempat.

### 19.6 Kesimpulan yang jujur

**Label v2 tidak "benar semua".** Satu dari lima baris membawa satu atau lebih temuan. Namun tidak ada satu pun cacat kritis, tidak ada bukti yang dikarang, dan tidak ada label yang saling bertentangan untuk teks yang sama.

Cacat yang tersisa hampir seluruhnya bersifat **definisional**, bukan faktual: soal bagaimana sapaan dan lelucon seharusnya diperlakukan, bukan soal salah menilai positif menjadi negatif. Pertanyaan yang paling menentukan — apakah kelas `netral` sekarang benar-benar netral — **belum dapat dijawab** dan tetap menunggu gold set manusia.

### 19.7 Keputusan lanjutan

| Kode | Keputusan | Alasan |
|---|---|---|
| D9 | Mempertahankan v2 sebagai label semu dan **tidak mengklaim akurasi apa pun** darinya | Konsistensi internal baik, tetapi kebenaran masih tanpa acuan |
| D10 | **Tidak** memakai `label_confidence` mentah sebagai gerbang penyaringan | Terlalu banyak nilai mutlak; perlu kalibrasi lebih dahulu |
| D11 | Meninjau ulang perlakuan `sapaan` dan `lelucon` sebelum melatih ulang | 165 sapaan bersentimen dan 97 lelucon ikut masuk ember latih |
| D12 | Memasukkan 262 baris itu (165 sapaan + 97 lelucon) ke daftar wajib nilai saat gold set bertambah | Batas keputusan yang paling tidak pasti berada di wilayah itu |

---

## 20. Pengukuran pertama terhadap gold set manusia

### 20.1 Gold set terisi

Seratus kandidat pada `data/processed/v3/gold_100.csv` telah dinilai manusia dan hasilnya disatukan ke `data/processed/v3/gold_manusia.csv`. Seluruhnya terisi, tanpa satu pun baris kosong.

| Kelas menurut manusia | Jumlah |
|---|---:|
| negatif | 41 |
| netral | 35 |
| positif | 16 |
| tidak_relevan | 8 |

Perlu dicatat sejak awal: pilihan **"Bukan opini" tidak sekali pun dipakai**, sedangkan "Tidak relevan" dipakai delapan kali. Setelah diperiksa, enam dari delapan baris itu sebenarnya bukan teks di luar topik, melainkan percakapan lapangan yang tidak memuat penilaian, misalnya "disinkronkan lagi ka" dan "cara bertanya nya". Artinya anotator memahami "tidak relevan" sebagai "tidak dapat dinilai sentimennya", bukan sebagai "di luar topik". Perbedaan tafsir ini perlu dijelaskan pada ronde anotasi berikutnya, karena mempengaruhi angka.

### 20.2 Akurasi sebenarnya prompt v2

Delapan baris `tidak_relevan` dikeluarkan dari metrik sentimen, sehingga yang diukur 92 baris.

| Ukuran | Nilai |
|---|---:|
| Akurasi | **0,7391** |
| Selang kepercayaan 95% | 0,6411 – 0,8180 |
| F1 macro | 0,5684 |
| Recall negatif | 0,902 (41 baris) |
| Recall netral | **0,571** (35 baris) |
| Recall positif | 0,688 (16 baris) |

Angka ini penting karena menegaskan apa yang sudah diperingatkan berulang kali: angka kesesuaian 0,8656 yang selama ini dilaporkan **bukan akurasi**, melainkan tingkat kesetiaan meniru anotator Gemma. Selisihnya dua belas koma enam poin. Prompt v2 yang sama, dijalankan ulang pada seratus baris gold, menghasilkan prediksi yang identik dengan label korpus pada seluruh seratus baris, sehingga kedua angka memang mengukur hal yang berbeda dan bukan akibat ketidakstabilan model.

### 20.3 Pola kesalahan

Dari 92 baris, 24 baris berbeda pendapat. Sebaran arahnya:

| Pola | Jumlah |
|---|---:|
| gold netral, dinilai negatif | **10** |
| gold tidak_relevan, dinilai netral | 6 |
| gold negatif, dikarantina | 3 |
| gold netral, dikarantina | 3 |
| gold positif, dinilai negatif | 3 |
| gold netral, dinilai positif | 2 |
| gold positif, dinilai netral | 1 |
| gold negatif, dinilai netral | 1 |

Kesalahan terbesar adalah **teks netral yang dipaksa negatif**. Contohnya "bagaimana mau melihat kembali foto foto lantai dan atap rumah yang sudah di aploud ya mohon penjelasan pak" dinilai negatif, padahal itu permintaan penjelasan. Begitu pula "dapet laporan dari group rt saja tau tau sudah didepan komplek rumah" yang hanya melaporkan keadaan. Polanya jelas: kehadiran kata bermuatan negatif seperti "sulit", "tidak ada yang jujur", atau "no respon" langsung disimpulkan sebagai keluhan, padahal penulisnya hanya bertanya atau melaporkan.

Kesalahan kedua adalah **gerbang relevansi yang terlalu agresif**, yaitu tujuh baris sah dikarantina, termasuk sindiran "bulan pertama nyensus isu pajak naik bulan kedua desil naik bulan ketiga gajian tidak turun turun" yang jelas membahas sensus.

Kesalahan ketiga adalah **ulasan campuran** yang dibaca negatif karena menyebut kata teknis negatif, misalnya "sangat membantu dalam proses pendataan hanya banyak error dan galat".

### 20.4 Prompt v4

Prompt v4 disusun untuk menyerang ketiga pola itu, dengan menambahkan empat aturan dan enam contoh yang diambil langsung dari kesalahan di atas:

- Aturan 9 memisahkan keluhan dari sekadar laporan, sehingga pertanyaan murni dan laporan keadaan tetap netral meski memuat kata bermuatan negatif.
- Aturan 10 melarang menyempitkan topik secara berlebihan, sehingga percakapan teknis singkat tetap relevan.
- Aturan 11 mengatur ulasan campuran.
- Aturan 12 mengatur sindiran beruntun.

Prompt v2 dan v3 tidak diubah agar perbandingan tetap adil. Pemilihan versi tersedia melalui `--prompt-versi v2|v3|v4`, dan bawaannya tetap v2 sampai ada versi yang terbukti lebih baik.

### 20.5 Hasil perbandingan

Kedua prompt dijalankan pada seratus baris gold yang sama, dengan model dan suhu yang sama.

| Ukuran | v2 | v4 |
|---|---:|---:|
| Akurasi | 0,7391 | **0,7717** |
| Selang kepercayaan 95% | 0,6411 – 0,8180 | 0,6761 – 0,8456 |
| F1 macro | 0,5684 | **0,5829** |
| Recall negatif | 0,902 | 0,829 |
| Recall netral | 0,571 | **0,743** |
| Recall positif | 0,688 | 0,688 |

Prompt v4 mengubah 19 dari 100 prediksi. Sebelas di antaranya adalah perubahan dari negatif ke netral, tepat sasaran pada kesalahan terbesar.

Uji McNemar eksak atas pasangan yang berbeda pendapat menghasilkan 10 lawan 7 dengan **p = 0,6291**, sehingga **perbedaannya belum nyata secara statistik**. Kesimpulan yang jujur: v4 bergerak ke arah yang benar dan memperbaiki kelemahan yang paling jelas, tetapi seratus baris belum cukup untuk membuktikannya. Recall netral naik tujuh belas poin, namun recall negatif justru turun tujuh poin, dan pada sampel sekecil ini perubahan-perubahan itu masih dapat berasal dari derau.

### 20.6 Keputusan lanjutan

| Kode | Keputusan | Alasan |
|---|---|---|
| D13 | **Korpus tetap memakai v2**; v4 disimpan tetapi belum dipakai | Perbedaan belum nyata secara statistik (p = 0,6291) |
| D14 | Menjalankan `gold_eval.py mine` untuk menarik seratus baris gold ronde kedua | Selisih tiga poin baru terukur setelah gold melewati angka lima ratus |
| D15 | Menjelaskan arti "tidak relevan" dan "bukan opini" pada lembar anotasi ronde berikutnya | Anotator tidak sekali pun memakai "bukan opini", sehingga kedua kategori tercampur |
| D16 | Menjadikan `0,7391` sebagai angka acuan tunggal menggantikan `0,8656` | Angka lama mengukur kesesuaian, bukan akurasi |

### 20.7 Berkas keluaran

| Berkas | Isi |
|---|---|
| `data/processed/v3/gold_manusia.csv` | Seratus baris gold beserta penilaian manusia |
| `data/processed/v3/prediksi_eval_v2.csv` dan `prediksi_eval_v4.csv` | Prediksi kedua prompt pada baris yang sama |
| `reports/gold_eval_v2_vs_v4.json` | Ringkasan pengukuran dan uji McNemar |
| `reports/eval_v2_summary.json` dan `reports/eval_v4_summary.json` | Ringkasan tiap penjalanan anotasi |

Seluruh prediksi dihasilkan dengan model `unsloth/gemma-4-12B-it-qat-w4a16` yang disajikan vLLM di Modal sebagai `gemma-4-12b-qat`.

---

## 21. Uji hipotesis penalaran: apakah model perlu menalar lebih dahulu?

### 21.1 Pertanyaan yang diuji

Setelah prompt v4 hanya menang tipis, muncul dugaan bahwa persoalannya bukan pada isi aturan melainkan pada **urutan pengambilan keputusan**: model menetapkan sentimen lebih dahulu, baru menyusun alasan yang membenarkannya. Bila benar, memaksa model menalar lebih dahulu seharusnya memperbaiki hasil tanpa mengubah aturannya sama sekali.

### 21.2 Cara menguji

Penegakan keluaran vLLM mengikuti **urutan properti pada skema JSON**. Sifat itu dipakai sebagai alat uji: skema versi 5 memindahkan `alasan` dan `bukti` ke depan, sedangkan `sentimen` dan `keyakinan` dipindahkan ke belakang. Model karena itu wajib menuliskan penalarannya sebelum boleh menetapkan sentimen. Isi aturannya sendiri tidak diubah dari v4, hanya ditambah satu aturan agar penalaran ditulis lebih dahulu. Batas token dinaikkan dari 220 menjadi 500 untuk memberi ruang penalaran.

### 21.3 Hasil

| Ukuran | v2 | v4 | v5 |
|---|---:|---:|---:|
| Akurasi | 0,7391 | **0,7717** | 0,7609 |
| Selang kepercayaan 95% | 0,64–0,82 | 0,68–0,85 | 0,66–0,84 |
| F1 macro | 0,5684 | **0,5829** | 0,5686 |
| Recall negatif | **0,902** | 0,829 | 0,805 |
| Recall netral | 0,571 | 0,743 | **0,800** |
| Recall positif | **0,688** | 0,688 | 0,562 |

Uji McNemar:

| Pasangan | Pasangan berbeda | p | Kesimpulan |
|---|---:|---:|---|
| v2 vs v4 | 10 vs 7 | 0,6291 | belum berbeda nyata |
| v2 vs v5 | 13 vs 11 | 0,8388 | belum berbeda nyata |
| v4 vs v5 | 3 vs 4 | 1,0000 | belum berbeda nyata |

### 21.4 Tafsiran

**Hipotesis penalaran terbantahkan dengan bukti ini.** Memaksa model menalar lebih dahulu tidak memperbaiki hasil; akurasinya justru sedikit lebih rendah daripada v4 (0,7609 melawan 0,7717) dan perbandingan langsung antara keduanya menghasilkan p = 1,0000, artinya keduanya praktis tidak dapat dibedakan.

Yang lebih penting, arah pergeserannya menjelaskan sebabnya. Penalarannya mendorong model semakin jauh ke kelas netral: recall netral naik dari 0,743 menjadi 0,800, tetapi recall positif jatuh dari 0,688 menjadi 0,562 dan recall negatif turun dari 0,829 menjadi 0,805. Gejalanya sudah terlihat pada uji kecil sebelum penjalanan penuh, ketika keluhan "tolong aplikasinya ngefreze" dinilai netral dengan alasan "hanya laporan keadaan".

Dengan kata lain, penalaran tidak membuat model lebih tepat menempatkan garis, melainkan hanya **menggeser garis itu ke arah lain**. Model menalar dengan baik menuju kesimpulan yang salah, sebab yang keliru sejak awal adalah di mana batas antara laporan dan keluhan diletakkan.

Kesimpulan praktisnya penting bagi arah pekerjaan berikutnya: hambatan utama bukanlah kemampuan menalar model, melainkan **ketidakjelasan definisi batas antar kelas**. Menambah aturan, menambah contoh, dan menambah penalaran semuanya hanya menggeser garis tanpa menyelesaikan persoalan. Yang benar-benar menyelesaikannya adalah acuan manusia yang lebih banyak, supaya garis itu dapat ditempatkan berdasarkan bukti, bukan berdasarkan tafsiran perancang prompt.

### 21.5 Keputusan lanjutan

| Kode | Keputusan | Alasan |
|---|---|---|
| D17 | **Tidak** beralih ke skema bernalar; v5 tidak dipakai | p = 1,0000 melawan v4, dengan biaya token lebih dari dua kali lipat |
| D18 | Menempatkan **penambahan gold set** sebagai pekerjaan utama berikutnya, bukan penambahan aturan prompt | Tiga versi prompt menghasilkan perbedaan yang tidak nyata; batas kelasnya belum terdefinisi dengan cukup |
| D19 | Mempertahankan v4 sebagai kandidat terkuat, korpus tetap memakai v2 | Konsisten dengan D13 |

### 21.6 Berkas keluaran

| Berkas | Isi |
|---|---|
| `data/processed/v3/prediksi_eval_v5.csv` | Prediksi skema bernalar pada seratus baris gold |
| `reports/eval_v5_summary.json` | Ringkasan penjalanan anotasi versi 5 |
| `reports/gold_eval_v2_v4_v5.json` | Perbandingan tiga sistem beserta uji McNemar |

---

## 22. Uji konsistensi diri: apakah kesalahan model berupa derau atau berupa bias?

### 22.1 Pertanyaan yang diuji

Aturan pengaman yang dipegang sejak awal berbunyi: label semu hanya diterima bila model **yakin dan konsisten** pada beberapa kali pengambilan dengan suhu berbeda. Aturan itu berguna hanya bila kesalahan model memang berupa derau acak, yaitu bila ketidakkonsistenan menandai baris yang cenderung salah. Bila kesalahannya justru sistematis, aturan itu justru membuang waktu sekaligus memberi rasa aman yang keliru.

### 22.2 Cara menguji

Prompt v4 dijalankan **tiga kali** pada seratus baris gold yang sama dengan suhu 0,7, sehingga setiap baris memperoleh tiga jawaban bebas. Ketiganya dibandingkan dengan penilaian manusia, lalu akurasi dipisahkan antara baris yang ketiga jawabannya sepakat dan baris yang terbelah.

### 22.3 Hasil

| Ukuran | Nilai |
|---|---:|
| Baris yang tiga jawabannya sepakat | **90 dari 92** |
| Baris yang jawabannya terbelah | 2 dari 92 |
| Akurasi pada baris sepakat | 0,7667 (69/90) |
| Akurasi pada baris terbelah | 0,5000 (1/2) |
| Akurasi suara terbanyak | 0,7609 |
| Akurasi v4 sekali jalan pada suhu 0 | 0,7717 |

### 22.4 Tafsiran

**Model ini nyaris selalu sepakat dengan dirinya sendiri, dan tetap salah.** Sembilan puluh dari sembilan puluh dua baris menghasilkan jawaban yang persis sama pada tiga pengambilan bersuhu 0,7.

Akibatnya jelas dan penting: **kesalahannya bukan derau, melainkan bias.** Pengambilan berulang dan pemungutan suara tidak memperbaiki apa pun; akurasi suara terbanyak 0,7609 praktis sama dengan sekali jalan 0,7717. Yang lebih mengkhawatirkan, aturan pengaman "label hanya diterima bila konsisten" akan **meloloskan 90 baris tanpa menyaring satu pun kesalahan yang berarti**, karena baris yang salah pun dijawab dengan yakin dan seragam.

Temuan ini melengkapi dua hasil sebelumnya menjadi satu kesimpulan utuh:

| Cara memperbaiki | Hasil |
|---|---|
| Menambah aturan dan contoh (v4) | naik 3,3 poin, p = 0,63 — belum nyata |
| Memaksa menalar lebih dahulu (v5) | turun 1,1 poin, p = 1,00 melawan v4 |
| Mengambil suara terbanyak tiga kali | turun 1,1 poin, tanpa manfaat |

Ketiganya gagal karena sebab yang sama: garis batas antar kelas belum terdefinisi dengan cukup, sehingga setiap usaha menambah kecerdasan hanya menggeser garis itu ke arah lain tanpa membuatnya lebih benar. Selama acuan manusia masih seratus baris, tidak ada cara mengetahui ke arah mana garis seharusnya diletakkan.

### 22.5 Keputusan lanjutan

| Kode | Keputusan | Alasan |
|---|---|---|
| D20 | Mencabut aturan "label hanya diterima bila konsisten pada beberapa pengambilan" sebagai penyaring | Terbukti tidak menyaring apa pun: 90 dari 92 baris konsisten, termasuk yang salah |
| D21 | Memindahkan seluruh daya kerja berikutnya ke penambahan gold set manusia | Tiga upaya perbaikan berbasis model gagal dengan pola yang sama |
| D22 | Tidak menguji model anotator lain pada tahap ini | Kekeliruan terbukti sistematis pada batas kelas, bukan kekurangan kemampuan model; mengganti model juga akan mengubah dua hal sekaligus sehingga hasilnya tidak dapat ditafsirkan |

### 22.6 Berkas keluaran

| Berkas | Isi |
|---|---|
| `data/processed/v3/konsist_1.jsonl` sampai `konsist_3.jsonl` | Tiga kali anotasi pada suhu 0,7 |
| `reports/konsist_1.json` sampai `konsist_3.json` | Ringkasan tiap pengambilan |
| `data/processed/v3/konsist_1/` sampai `konsist_3/` | Ember korpus hasil tiap pengambilan |

---

## 23. Uji anotator dari keluarga model lain

### 23.1 Pertanyaan yang diuji

Dua uji sebelumnya mengubah prompt dan cara menalar, tetapi tetap memakai model yang sama. Muncul pertanyaan yang belum terjawab: apakah anotator **dari keluarga model yang berbeda** menghasilkan penilaian yang lebih dekat ke manusia?

### 23.2 Cara menguji

Seratus baris yang sama diberikan kepada **DeepSeek V4.1 Flash** dalam keadaan tersamar: yang diberikan hanya `uid`, platform, konteks asal, dan teks, tanpa label mana pun. Model diminta menalar sendiri lalu menetapkan satu dari empat label yang sama. Hasilnya diukur dengan alat dan gold set yang sama seperti sebelumnya, sehingga perbandingannya setara.

Pekerjaan dibagi menjadi empat bagian berisi dua puluh lima baris agar tiap bagian dapat ditelusuri, lalu digabung dan diperiksa: seluruh seratus uid cocok, tidak ada label di luar daftar yang diizinkan.

### 23.3 Hasil

| Sistem | Akurasi | F1 macro | Recall negatif | Recall netral | Recall positif |
|---|---:|---:|---:|---:|---:|
| v2 — Gemma, prompt v2 | 0,7391 | 0,5684 | **0,902** | 0,571 | **0,688** |
| v4 — Gemma, prompt v4 | **0,7717** | **0,5829** | 0,829 | 0,743 | **0,688** |
| v5 — Gemma, menalar lebih dahulu | 0,7609 | 0,5686 | 0,805 | 0,800 | 0,562 |
| **DeepSeek V4.1 Flash** | 0,7609 | 0,5604 | 0,732 | **0,886** | 0,562 |

Uji McNemar terhadap DeepSeek:

| Pasangan | Pasangan berbeda | p | Kesimpulan |
|---|---:|---:|---|
| v2 vs DeepSeek | 15 vs 13 | 0,8506 | belum berbeda nyata |
| v4 vs DeepSeek | 8 vs 9 | 1,0000 | belum berbeda nyata |
| v5 vs DeepSeek | 10 vs 10 | 1,0000 | belum berbeda nyata |

### 23.4 Tafsiran

**Mengganti model tidak memperbaiki apa pun.** DeepSeek memperoleh akurasi 0,7609, persis sama dengan v5 dan di bawah v4. Tidak satu pun perbandingan berpasangan yang berbeda nyata.

Yang jauh lebih penting daripada angkanya adalah **bentuk** hasilnya. Keempat sistem berdiri pada kurva pertukaran yang sama:

| Sistem | Recall negatif | Recall netral |
|---|---:|---:|
| v2 | 0,902 | 0,571 |
| v4 | 0,829 | 0,743 |
| v5 | 0,805 | 0,800 |
| DeepSeek | 0,732 | 0,886 |

Setiap tambahan kepekaan terhadap kelas netral selalu dibayar dengan hilangnya kepekaan terhadap kelas negatif, dengan kemiringan yang hampir sama. Artinya keempat sistem **tidak berbeda dalam hal seberapa baik mereka menilai**, melainkan hanya **berbeda dalam hal di mana mereka meletakkan garis batas**. Model yang berbeda keluarga, dilatih berbeda, dengan cara menalar yang berbeda, semuanya menempatkan garis di titik yang bergeser sepanjang satu kurva yang sama.

Kenyataan itu menutup jalan penyelesaian dari sisi model. Selama garisnya belum ditentukan oleh acuan manusia, model apa pun hanya akan memilih satu titik pada kurva itu, dan tidak ada alasan untuk menganggap satu titik lebih benar daripada titik lain.

### 23.5 Keputusan lanjutan

| Kode | Keputusan | Alasan |
|---|---|---|
| D23 | Menghentikan seluruh upaya perbaikan melalui penggantian model atau penambahan aturan prompt | Empat sistem dari dua keluarga model menghasilkan perbedaan yang tidak nyata dan bergerak pada satu kurva pertukaran yang sama |
| D24 | Memakai v4 sebagai anotator bila kelak korpus dilabeli ulang | Akurasi tertinggi (0,7717) dengan F1 macro tertinggi, dan tetap memakai peladen sendiri |
| D25 | Menempatkan penambahan gold set manusia sebagai satu-satunya jalan penyelesaian | Hanya acuan manusialah yang dapat menentukan letak garis batas yang benar |

### 23.6 Keterbatasan yang perlu dinyatakan

Pengujian ini dijalankan melalui jalur agen, bukan melalui `modeling/pseudo_label.py`, sehingga hasilnya berupa pengukuran sekali jalan dan belum dapat diulang otomatis seperti ketiga sistem lainnya. Angka DeepSeek karena itu sah untuk perbandingan, tetapi belum menjadi bagian dari rantai perangkat yang dapat dijalankan ulang.

### 23.7 Berkas keluaran

| Berkas | Isi |
|---|---|
| `data/processed/v3/prediksi_deepseek.csv` | Seratus prediksi DeepSeek atas baris gold |
| `reports/gold_eval_deepseek.json` | Perbandingan empat sistem beserta uji McNemar |

---

## 24. Pelatihan pada GPU Kaggle dan cacat pembagian data yang ditemukan

### 24.1 Sebab berpindah dari Modal

Modal menolak menjalankan fungsi GPU baru pada akun ini dengan pesan "Please add a payment method to use T4 GPU functions", dan hal yang sama terjadi pada akun kedua yang diuji. Karena Colab CLI hanya mendukung Linux dan macOS, jalur yang dipakai adalah **Kaggle**, yang menyediakan 30 jam GPU per minggu tanpa kartu kredit dan CLI-nya berupa paket Python sehingga berjalan langsung di Windows.

Perangkatnya `kirim_kaggle.py`: kode dan korpus dikemas menjadi satu himpunan data, sebuah kernel ber-GPU dikirim dan dijalankan, lalu keluarannya ditarik kembali ke `reports/kaggle/`.

### 24.2 Cacat yang ditemukan sebelum pelatihan berjalan

Kecurigaan muncul dari satu angka yang janggal: kernel melaporkan himpunan uji hanya **272 dari 5.808 baris**, padahal pembagiannya seharusnya seperlima. Penelusuran menemukan sebabnya.

Ember korpus yang ditulis `modeling/pseudo_label.py` **tidak memuat kolom `source_id`**, padahal korpus lama memuatnya. Akibatnya `derive_group` kehilangan identitas asal rekaman dan jatuh ke cadangan terakhir, yaitu pasangan sumber dan kueri. Seluruh **1.295 ulasan Play Store** karena itu menjadi satu grup tunggal bernama `playstore:fasih`.

Karena pembagian data dilakukan berkelompok (`StratifiedGroupKFold`), satu grup raksasa yang mencakup 22,3 persen korpus membuat ukuran lipatan menjadi sangat timpang: hanya 272 baris yang jatuh ke himpunan uji, dan 200 grup unik tidak lagi mewakili struktur korpus.

Setelah kolom `source_id` ditambahkan dan ember ditulis ulang, keadaannya menjadi:

| Ukuran | Sebelum | Sesudah |
|---|---:|---:|
| Grup unik | 200 | **1.494** |
| Grup terbesar | 1.295 baris | **166 baris** |
| Baris uji | 272 (4,7%) | **1.313 (22,6%)** |

Cacat ini tidak akan terlihat dari pemeriksaan statistik biasa. Ia hanya muncul karena angka hasil diperiksa terhadap kewajaran, bukan diterima apa adanya.

### 24.3 Hasil studi ablasi pada korpus v3

Dijalankan pada GPU Kaggle, korpus 5.808 baris opini dengan pembagian 4.495 latih dan 1.313 uji.

| Skenario | Akurasi | F1 macro | F1 weighted | Parameter dilatih | Waktu (detik) |
|---|---:|---:|---:|---:|---:|
| zeroshot | 0,7609 | 0,5458 | 0,8119 | 0 | 0 |
| linear_probe | 0,8545 | 0,6277 | 0,8719 | 0 | 41 |
| bitfit | **0,9185** | 0,6228 | 0,9067 | 105.219 | 128 |
| partial_top_k | 0,9162 | 0,6316 | 0,9087 | 43.120.131 | 122 |
| full | **0,9185** | 0,6828 | **0,9153** | 124.443.651 | 160 |
| full_rdrop | 0,8903 | **0,7079** | 0,9044 | 124.443.651 | 289 |

### 24.4 Tafsiran

**F1 macro jatuh jauh dibandingkan korpus lama**: dari 0,8669 menjadi 0,7079 pada skenario yang sama. Akurasinya justru naik, dari 0,8769 menjadi 0,9185 pada skenario `full`. Penurunan itu bukan kemunduran model, melainkan akibat kelas netral yang kini benar-benar netral.

Pada korpus lama, kelas netral mencapai 30,7 persen dan isinya sebagian besar pertanyaan serta sapaan yang mudah dikenali, sehingga F1 macro tampak tinggi. Pada korpus v3, kelas netral tinggal 219 baris (3,8 persen) dan isinya pernyataan yang memang tidak memuat penilaian, sehingga jauh lebih sulit dipisahkan.

Matriks konfusi model terbaik memperlihatkan persoalannya dengan jelas. Dari 109 baris yang diprediksi netral, hanya 28 yang benar, sedangkan 66 sebenarnya negatif dan 15 sebenarnya positif. Recall netralnya memadai (28 dari 43, atau 0,651), tetapi presisinya rendah (0,257). Justru presisi itulah yang menekan F1 macro, bukan kemampuan model mengenali kelas negatif yang tetap di atas 0,9.

Ada pula temuan yang berlawanan dengan dugaan umum: **R-Drop menurunkan akurasi tetapi menaikkan F1 macro**. Model `full` lebih akurat (0,9185) sedangkan `full_rdrop` lebih berimbang (F1 macro 0,7079). Karena pemilihan model terbaik memakai F1 macro, `full_rdrop` yang terpilih.

### 24.5 Keputusan lanjutan

| Kode | Keputusan | Alasan |
|---|---|---|
| D26 | Memakai Kaggle sebagai jalur pelatihan selama Modal terkunci | Berhasil tanpa biaya dan tanpa kartu kredit, 30 jam GPU per minggu |
| D27 | Menjadikan `source_id` kolom wajib pada seluruh berkas ember | Kelalaian ini sempat merusak pembagian data secara diam-diam |
| D28 | Melaporkan F1 macro kelas netral secara terpisah pada laporan akhir | Angka agregat menyembunyikan presisi kelas netral yang hanya 0,257 |
| D29 | Tidak membandingkan angka v3 dengan angka korpus lama secara langsung | Keduanya memakai korpus dan pembagian data yang berbeda |

### 24.6 Berkas keluaran

| Berkas | Isi |
|---|---|
| `kirim_kaggle.py` | Pengirim himpunan data dan kernel ke Kaggle |
| `reports/kaggle/ablasi-se2026.log` | Catatan penjalanan kernel |
| `reports/kaggle/ablasi_se2026/ablation_report.md` | Laporan ablasi korpus v3 |
| `reports/kaggle/ablasi_se2026/best_model/` | Bobot model terbaik (`full_rdrop`) |
| `reports/kaggle/ablasi_se2026/ablation_confusion.png` | Matriks konfusi |

---

## 25. Pemeriksaan menyeluruh dan koreksi angka F1 macro

### 25.1 Cara pemeriksaan

Seluruh pekerjaan ditelusuri ulang dari hulu ke hilir oleh delapan pemeriksa terpisah, masing-masing pada satu bidang: rantai korpus dan rentang tanggal, pelabelan dan versi prompt, audit mutu label, gold set dan evaluasinya, hasil pelatihan, laporan docx, kesehatan kode, serta keterlacakan git dan jurnal. Setiap pemeriksa bekerja hanya dengan membaca dan menghitung, tanpa mengubah apa pun.

### 25.2 Cacat yang ditemukan: F1 macro terbagi empat kelas

Pemeriksaan atas gold set menemukan bahwa **nilai F1 macro yang selama ini dilaporkan keliru**. Fungsi `macro_f1` pada `modeling/gold_eval.py` menyimpulkan daftar kelas dari gabungan label acuan **dan** label prediksi. Karena delapan baris diprediksi `tidak_relevan` sementara kelas itu sudah dikeluarkan dari acuan, kelas tersebut masuk sebagai kelas keempat yang seluruh nilai F1-nya nol. Rata-rata karena itu terbagi empat, bukan tiga.

Akibatnya F1 macro terdeflasi sekitar seperempat, dan angka yang salah itu sempat masuk ke dokumen.

| Sistem | F1 macro tercatat (keliru) | F1 macro benar | Akurasi |
|---|---:|---:|---:|
| Prompt v2 | 0,5684 | **0,7579** | 0,7391 |
| Prompt v4 | 0,5829 | **0,7772** | 0,7717 |
| Prompt v5 (menalar lebih dahulu) | 0,5686 | **0,7581** | 0,7609 |
| DeepSeek V4.1 Flash | 0,5604 | **0,7472** | 0,7609 |

Akurasi dan recall per kelas tidak terpengaruh, dan kesimpulan pada seksi 20, 21, dan 23 tidak berubah. Bahkan dengan angka yang benar, kedudukan prompt v4 semakin kuat: ia unggul pada akurasi **dan** F1 macro sekaligus.

Perbaikannya dilakukan pada `modeling/gold_eval.py`: daftar kelas kini wajib diberikan oleh pemanggil melalui `--kelas-sentimen`, dan sebuah uji baru ditambahkan pada `--selftest` untuk mengunci perilaku itu agar tidak terulang.

### 25.3 Cacat lain yang ditemukan dan diperbaiki

| Cacat | Perbaikan |
|---|---|
| Ember korpus kehilangan kolom `source_id` sehingga pembagian data timpang (uji hanya 272 baris) | Kolom ditambahkan pada `KOLOM_EMBER` dan ember ditulis ulang; uji menjadi 1.313 baris |
| Perintah `mine` pada `gold_eval.py` tidak menyertakan konteks asal teks | Kolom `konteks` ditambahkan |
| Laporan docx memuat sejumlah angka basi, gambar tanpa rujukan, dan tabel tanpa keterangan sumber | Angka disegarkan, rujukan gambar ditambahkan, keterangan sumber dicantumkan pada seluruh tabel dan gambar |
| Laporan docx masih menyatakan gold set belum terisi | Diganti dengan hasil pengukuran yang sebenarnya |

### 25.4 Catatan tentang letak angka audit

Perlu ditegaskan bahwa **seksi 19 pada dokumen ini adalah audit korpus v2** (10.071 baris dipindai, 2.073 baris bertanda), sedangkan **audit korpus v3** yang dipakai pada laporan KP berjumlah 8.350 baris dipindai dan 1.782 baris bertanda. Angka v3 tersimpan pada `reports/audit_label_v3.json` dan `reports/audit_label_v3.html`, serta telah dipindahkan ke dalam laporan docx. Keduanya sah, tetapi merujuk korpus yang berbeda dan tidak boleh dicampur.

`data/processed/labels_checkpoint.jsonl` pada korpus v3 juga masih menyimpan 1.734 entri sisa dari penjalanan sebelumnya. Entri itu tidak menghasilkan baris ember karena pemilahan berjalan mengikuti baris korpus, tetapi cekpoin tersebut tidak bersih dan sebaiknya disaring bila kelak dipakai lagi.

### 25.5 Yang dinyatakan belum beres

| Hal | Keadaan |
|---|---|
| Nilai F1 macro pada `reports/gold_eval_*.json` | Sudah diperbaiki dan dihitung ulang |
| Angka pada laporan docx | Sudah disegarkan; 26 penanda identitas masih perlu diisi pengguna |
| Tabel dan gambar docx | Sudah diberi rujukan dan keterangan sumber |
| `README.md` | Menyimpang jauh dari keadaan nyata dan perlu diperbarui |
| Keterlacakan | Satu commit awal belum mencakup era korpus v3, Kaggle, dan laporan docx |
| Ronde kedua gold set | Kandidat sudah ditarik dan anotator kedua sudah menilai, tetapi anotasi manusia belum ada sehingga kappa belum dapat dihitung |
| Bobot model pada `reports/kaggle/` | Belum dikecualikan dari git sehingga berisiko ikut ter-commit |
| Transkrip sesi pada `reports/sesi/` | Sudah ter-commit dan menjadi kanal yang mungkin memuat kredensial; perlu penyaring |

### 25.6 Berkas keluaran

| Berkas | Isi |
|---|---|
| `modeling/gold_eval.py` | Perbaikan `macro_f1` beserta uji penguncinya |
| `reports/gold_eval_v2.json`, `gold_eval_v2_vs_v4.json`, `gold_eval_v2_v4_v5.json`, `gold_eval_deepseek.json` | Seluruhnya dihitung ulang dengan F1 macro yang benar |









