/* Memeriksa muatan data yang dibangkitkan terhadap berkas sumbernya.
   Dijalankan dengan: node periksa_muatan.js  (dari folder final/web) */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const DIR = __dirname;
const sandal = { window: {} };
vm.createContext(sandal);
for (const nama of ["data.js", "label.js"]) {
  const kode = fs.readFileSync(path.join(DIR, nama), "utf8");
  vm.runInContext(kode, sandal, { filename: nama });
}
const D = sandal.window.DSS;
const L = sandal.window.DSS_LABEL;

let gagal = 0;
function periksa(nama, syarat, catatan) {
  if (syarat) {
    console.log(`  ok    ${nama}`);
  } else {
    gagal++;
    console.log(`  GAGAL ${nama}${catatan ? " :: " + catatan : ""}`);
  }
}

console.log("=== muatan data ===");
periksa("data.js memuat DSS", !!D);
periksa("label.js memuat DSS_LABEL", !!L);
periksa("jumlah baris sesuai jumlah baris korpus",
  L.baris.length === D.meta.jumlah_baris,
  `${L.baris.length} vs ${D.meta.jumlah_baris}`);

const I = {};
L.kolom.forEach((k, i) => { I[k] = i; });

const uid = L.baris.map((b) => b[I.uid]);
periksa("setiap baris punya uid", uid.every((u) => typeof u === "string" && u.length === 32));
periksa("uid tidak kembar", new Set(uid).size === uid.length,
  `${new Set(uid).size} unik dari ${uid.length}`);
periksa("panjang larik seragam", L.baris.every((b) => b.length === L.kolom.length));

const berlabel = L.baris.filter((b) => b[I.label]);
periksa("baris berlabel sesuai ringkasan",
  berlabel.length === D.meta.jumlah_label,
  `${berlabel.length} vs ${D.meta.jumlah_label}`);
periksa("baris tanpa label sesuai catatan audit",
  L.baris.length - berlabel.length === (D.audit.tanpa_anotasi || []).length);
periksa("baris tanpa label tidak punya ember",
  L.baris.filter((b) => !b[I.label]).every((b) => b[I.ember] === null));

const perEmber = {};
L.baris.forEach((b) => { if (b[I.ember]) perEmber[b[I.ember]] = (perEmber[b[I.ember]] || 0) + 1; });
periksa("sebaran ember cocok dengan audit",
  JSON.stringify(perEmber) === JSON.stringify(D.audit.per_ember),
  JSON.stringify(perEmber) + " vs " + JSON.stringify(D.audit.per_ember));

const perSentimen = {};
berlabel.forEach((b) => { perSentimen[b[I.label]] = (perSentimen[b[I.label]] || 0) + 1; });
function samakanTas(a, b) {
  const ka = Object.keys(a).sort(), kb = Object.keys(b).sort();
  return JSON.stringify(ka) === JSON.stringify(kb) && ka.every((k) => a[k] === b[k]);
}
periksa("sebaran sentimen cocok dengan audit",
  samakanTas(perSentimen, D.sentimen.seluruh),
  JSON.stringify(perSentimen) + " vs " + JSON.stringify(D.sentimen.seluruh));

console.log("=== penautan silang ===");
const uidSet = new Set(uid);
const auditUid = Object.keys(D.audit_per_baris);
periksa("setiap uid audit ada di daftar baris",
  auditUid.every((u) => uidSet.has(u)),
  auditUid.filter((u) => !uidSet.has(u)).slice(0, 3).join(", "));
periksa("jumlah baris beraudit sama dengan berkas audit",
  auditUid.length === D.audit.bertanda,
  `${auditUid.length} vs ${D.audit.bertanda}`);

const goldUid = Object.keys(D.gold_per_baris);
periksa("setiap uid gold ada di daftar baris",
  goldUid.every((u) => uidSet.has(u)),
  goldUid.filter((u) => !uidSet.has(u)).slice(0, 3).join(", "));
periksa("gold memuat seratus baris penilaian manusia",
  goldUid.filter((u) => D.gold_per_baris[u].manusia).length === 100);

const limeUid = Object.keys(D.xai.lime.per_uid || {});
periksa("setiap uid LIME ada di daftar baris", limeUid.every((u) => uidSet.has(u)));
periksa("LIME memuat tiga puluh baris", limeUid.length === 30, String(limeUid.length));

const atensiUid = Object.keys(D.xai_uid_atensi || {});
periksa("peta atensi berhasil ditautkan ke baris", atensiUid.length >= 6,
  `${atensiUid.length} dari 8 contoh`);
periksa("setiap uid atensi ada di daftar baris", atensiUid.every((u) => uidSet.has(u)));
const bertvizUid = Object.keys(D.xai_uid_bertviz || {});
periksa("setiap uid BertViz ada di daftar baris", bertvizUid.every((u) => uidSet.has(u)));
periksa("BertViz memuat tiga baris", bertvizUid.length === 3, String(bertvizUid.length));

console.log("=== kelengkapan naratif ===");
periksa("keputusan terbaca", (D.keputusan || []).length >= 20, String((D.keputusan || []).length));
periksa("keterbatasan terbaca", (D.keterbatasan || []).length >= 5, String((D.keterbatasan || []).length));
periksa("temuan terbaca", (D.temuan || []).length >= 3, String((D.temuan || []).length));
periksa("alur memuat delapan tahap", (D.alur || []).length === 8);
periksa("klaim boleh dan tidak boleh terisi",
  D.klaim.boleh.length > 0 && D.klaim.tidak.length > 0);
periksa("kurva pertukaran memuat empat sistem", (D.gold.kurva || []).length === 4);
periksa("ablasi memuat enam skenario", (D.ablasi.skenario || []).length === 6);
periksa("berkas manifest terbaca", (D.berkas || []).length > 0);
periksa("gambar LIME tersedia untuk kelas", Object.keys(
  (D.xai.lime.top || []).reduce((a, t) => { a[t.class] = 1; return a; }, {})).length >= 3);

console.log("=== matriks konfusi dan metrik turunan ===");

/* Angka pada halaman diturunkan dari matriksnya. Bila turunan itu tidak lagi
   cocok dengan yang dilaporkan berkas evaluasi, berarti salah satunya berubah
   dan halaman akan menyajikan dua angka yang berbeda untuk hal yang sama. */
function dekat(a, b, toleransi = 0.002) {
  return typeof a === "number" && typeof b === "number" && Math.abs(a - b) <= toleransi;
}
function periksaMatriks(nama, metrik, laporan, kunciLaporan) {
  const cocok = dekat(metrik.macro.f1, laporan.f1_macro)
    && dekat(metrik.akurasi, laporan.accuracy);
  periksa(`metrik turunan ${nama} cocok dengan ${kunciLaporan}`, cocok,
    cocok ? "" : `turunan akurasi ${metrik.akurasi} / F1 ${metrik.macro.f1} lawan ` +
      `laporan ${laporan.accuracy} / ${laporan.f1_macro}`);
}

const ablasi = D.ablasi.skenario || [];
periksa("setiap skenario punya metrik turunan",
  ablasi.length === 6 && ablasi.every((s) => s.metrik && s.metrik.per_kelas.length === 3),
  `${ablasi.filter((s) => s.metrik).length} dari ${ablasi.length}`);
periksa("setiap skenario punya matriks 3x3",
  ablasi.every((s) => s.matriks && s.matriks.length === 3
    && s.matriks.every((r) => r.length === 3)));

const laporanAblasi = require(path.join(DIR, "..", "hasil_ablasi.json"));
for (const s of ablasi) {
  const asli = laporanAblasi.variants[s.id];
  periksaMatriks("ablasi " + s.id, s.metrik, asli, "hasil_ablasi.json");
}

const sistem = D.gold.sistem || [];
periksa("setiap sistem gold punya metrik turunan",
  sistem.length === 4 && sistem.every((s) => s.metrik && s.metrik.per_kelas.length === 3));
periksa("setiap sistem gold punya matriks",
  sistem.every((s) => s.matriks && s.matriks.length === 3 && s.matriks[0].length === 4),
  "kolom seharusnya empat termasuk tidak relevan");
periksa("dukungan gold sepuluh kelas sesuai sebaran",
  sistem.every((s) => s.metrik.total === D.gold.n),
  `${sistem.map((s) => s.metrik.total).join(", ")} lawan ${D.gold.n}`);

const laporanGold = require(path.join(DIR, "..", "evaluasi_gold.json"));
for (const s of sistem) {
  periksaMatriks("gold " + s.id, s.metrik, laporanGold.sistem[s.id], "evaluasi_gold.json");
}

/* Jumlah baris pada matriks harus sama dengan jumlah baris gold yang terpakai,
   dan jumlah baris yang dinilai di luar kelas sentimen harus delapan. */
periksa("jumlah baris di luar kelas sentimen sesuai catatan audit",
  sistem.every((s) => (s.di_luar || []).reduce((a, d) => a + d.jumlah, 0) === 8),
  sistem.map((s) => (s.di_luar || []).reduce((a, d) => a + d.jumlah, 0)).join(", "));

/* Metrik tidak boleh saling bertentangan: akurasi seimbang adalah rata-rata
   recall, dan presisi serta recall harus berada di antara nol dan satu. */
periksa("akurasi seimbang sama dengan rata-rata recall",
  sistem.concat(ablasi).every((s) => {
    const rata = s.metrik.per_kelas.reduce((a, p) => a + p.recall, 0) / s.metrik.per_kelas.length;
    return Math.abs(rata - s.metrik.akurasi_seimbang) < 0.002;
  }));
periksa("seluruh presisi, recall, dan F1 berada pada rentang nol sampai satu",
  sistem.concat(ablasi).every((s) => s.metrik.per_kelas.every((p) =>
    p.presisi >= 0 && p.presisi <= 1 && p.recall >= 0 && p.recall <= 1
    && p.f1 >= 0 && p.f1 <= 1 && p.spesifisitas >= 0 && p.spesifisitas <= 1)));
periksa("jumlah benar pada matriks sama dengan diagonalnya",
  sistem.concat(ablasi).every((s) => {
    const diagonal = s.matriks.reduce((a, r, i) => a + (r[i] || 0), 0);
    return diagonal === s.metrik.benar;
  }));

console.log("=== gambar yang dirujuk ===");
/* Daftar berkas manifest sengaja dilewati: isinya jalur berkas penelitian,
   bukan aset yang dipakai halaman ini. */
const semuaGambar = [];
function jelajah(n, jalur) {
  if (jalur === "berkas") return;
  if (Array.isArray(n)) return n.forEach((v) => jelajah(v, jalur));
  if (n && typeof n === "object") {
    return Object.keys(n).forEach((k) => jelajah(n[k], k));
  }
  if (typeof n === "string" && /\.png$/.test(n)) semuaGambar.push(n);
}
jelajah(D, "");
const unikGambar = [...new Set(semuaGambar)];
let gambarHilang = 0;
for (const g of unikGambar) {
  const relatif = g.indexOf("aset/") === 0 ? g.slice(5) : g;
  const jalur = path.join(DIR, "aset", relatif);
  if (!fs.existsSync(jalur) && !fs.existsSync(path.join(DIR, "aset", "bertviz", relatif))) {
    gambarHilang++;
    console.log("  hilang:", g);
  }
}
periksa("seluruh gambar yang dirujuk ada di folder aset", gambarHilang === 0,
  `${unikGambar.length} dirujuk`);

console.log("=== leksikon dan deret turunan ===");
const leksikon = D.leksikon || {};
periksa("leksikon memuat tiga kelas sentimen",
  ["negatif", "netral", "positif"].every((k) => Array.isArray(leksikon[k]) && leksikon[k].length),
  Object.keys(leksikon).join(", "));
periksa("setiap butir leksikon berbentuk pasangan kata dan bobot",
  Object.keys(leksikon).every((k) => leksikon[k].every((t) =>
    Array.isArray(t) && typeof t[0] === "string" && typeof t[1] === "number")));
periksa("hanya token penyokong kelas yang disimpan",
  Object.keys(leksikon).every((k) => leksikon[k].every((t) => t[1] > 0)));
periksa("leksikon urut menurun",
  Object.keys(leksikon).every((k) => leksikon[k].every((t, i, a) =>
    i === 0 || a[i - 1][1] >= t[1])));

const deret = D.deret || {};
periksa("deret bulanan terisi", !!(deret.bulanan && deret.bulanan.bulan.length));
periksa("setiap bulan pada deret hanya memuat sumber yang dikenal",
  Object.keys(deret.bulanan.nilai).every((b) =>
    Object.keys(deret.bulanan.nilai[b]).every((s) => deret.bulanan.sumber.indexOf(s) >= 0)));
periksa("silang sumber dan sentimen terisi", Object.keys(deret.sumber_sentimen || {}).length > 0);
periksa("silang aspek dan sentimen terisi", Object.keys(deret.aspek_sentimen || {}).length > 0);
periksa("silang tipe dan sentimen terisi", Object.keys(deret.tipe_sentimen || {}).length > 0);
periksa("panjang teks terukur untuk ketiga kelas",
  ["negatif", "netral", "positif"].every((k) => (deret.panjang_kelas || {})[k]));
periksa("bak kalibrasi memuat lima selang", (deret.kalibrasi || []).length === 5);
periksa("selang kalibrasi tidak tumpang tindih",
  (deret.kalibrasi || []).every((b, i, a) => i === 0 || a[i - 1].atas <= b.bawah));
periksa("jumlah baris pada bak kalibrasi tidak melebihi baris gold",
  (deret.kalibrasi || []).reduce((s, b) => s + b.n, 0) <= 100);

console.log("=== kesepakatan antar penilai ===");
if (D.kappa) {
  periksa("kappa memuat pasangan penilai", (D.kappa.pasangan || []).length > 0);
  periksa("setiap pasangan memuat kappa seluruh kelas",
    D.kappa.pasangan.every((p) => p.semua_kelas && typeof p.semua_kelas.kappa === "number"));
  periksa("setiap pasangan punya matriks seukuran kelasnya",
    D.kappa.pasangan.every((p) => p.semua_kelas.matriks.length === p.semua_kelas.kelas.length));
  periksa("nilai kappa berada pada rentang yang mungkin",
    D.kappa.pasangan.every((p) => p.semua_kelas.kappa >= -1 && p.semua_kelas.kappa <= 1));
} else {
  periksa("berkas kappa belum dihitung, sehingga bloknya tidak ditampilkan", true);
}

console.log("=== berkas antarmuka ===");
const berkasWajib = ["index.html", "gaya.css", "app.js", "periksa_muatan.js"];
for (const nama of berkasWajib) {
  periksa(nama + " ada", fs.existsSync(path.join(DIR, nama)));
}
const adaKonfigurasi = fs.existsSync(path.join(DIR, "konfigurasi.js"));
periksa("konfigurasi.js ditulis terbitkan_model.py bila endpoint sudah terbit", true,
  adaKonfigurasi ? "ada" : "belum ada");
if (adaKonfigurasi) {
  const konf = fs.readFileSync(path.join(DIR, "konfigurasi.js"), "utf8");
  periksa("konfigurasi.js tidak memakai em-dash", !konf.includes("\u2014"));
}

console.log("=== tanda pisah panjang ===");
/* Tanda pisah panjang tidak dipakai sama sekali pada teks yang kita tulis.
   Kutipan korpus pada label.js dikecualikan: teks aslinya harus tetap apa
   adanya, termasuk tanda baca yang dipakai penulisnya. */
const ADA_PISAH = /[\u2014\u2013]/;
const pisahKutipan = [];
function jelajahPisah(n, jalur) {
  if (Array.isArray(n)) return n.forEach((v, i) => jelajahPisah(v, jalur + "[" + i + "]"));
  if (n && typeof n === "object") {
    return Object.keys(n).forEach((k) => jelajahPisah(n[k], jalur ? jalur + "." + k : k));
  }
  if (typeof n === "string" && ADA_PISAH.test(n)) pisahKutipan.push(jalur.replace(/\[\d+\]/g, "[]"));
}
jelajahPisah(D, "");
periksa("teks yang kita tulis pada data.js bebas tanda pisah panjang",
  pisahKutipan.length === 0, [...new Set(pisahKutipan)].slice(0, 5).join(", "));

const app = fs.readFileSync(path.join(DIR, "app.js"), "utf8");
const html = fs.readFileSync(path.join(DIR, "index.html"), "utf8");
/* Sintaks app.js diuji lebih dahulu: berkas dengan galat sintaks tidak akan
   memasang satu pun pengendali, sehingga halaman tampak kosong tanpa pesan. */
try {
  new vm.Script(app, { filename: "app.js" });
  periksa("app.js lolos pemeriksaan sintaks", true);
} catch (e) {
  periksa("app.js lolos pemeriksaan sintaks", false, e.message);
}
periksa("app.js tidak memakai em-dash", !app.includes("\u2014"));
periksa("index.html tidak memakai em-dash", !html.includes("\u2014"));
periksa("app.js membaca DSS dan DSS_LABEL",
  app.includes("window.DSS ") || app.includes("window.DSS ||"), true);
for (const kunci of ["gold_per_baris", "audit_per_baris", "xai_uid_atensi", "xai_uid_bertviz"]) {
  periksa("app.js memakai " + kunci, app.includes(kunci));
}

console.log("");
if (gagal) {
  console.log(`${gagal} pemeriksaan gagal`);
  process.exit(1);
}
console.log("seluruh pemeriksaan muatan data lulus");
