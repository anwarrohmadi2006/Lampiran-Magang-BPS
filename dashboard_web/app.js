/* ==========================================================================
   Penelusuran Label SE2026 - logika antarmuka
   --------------------------------------------------------------------------
   Seluruh isi halaman dibangun dari dua berkas data yang dibangkitkan
   buat_web_dss.py: data.js (angka, tabel, keputusan) dan label.js (seluruh
   baris label). Tidak ada permintaan jaringan sama sekali, sehingga berkasnya
   dapat dibuka langsung dari disk.
   ========================================================================== */
(function () {
  "use strict";

  var D = window.DSS || {};
  var L = window.DSS_LABEL || { kolom: [], baris: [] };

  /* ------------------------------------------------------------------------
     Ikon: berkas resmi dari paket @phosphor-icons/core, digambar sebaris
     supaya tidak ada permintaan jaringan dan tidak ada gambar tangan sendiri.
     ------------------------------------------------------------------------ */
  var IKON = {
    cari: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor"><path d="M229.66,218.34l-50.07-50.06a88.11,88.11,0,1,0-11.31,11.31l50.06,50.07a8,8,0,0,0,11.32-11.32ZM40,112a72,72,0,1,1,72,72A72.08,72.08,0,0,1,40,112Z"/></svg>',
    tutup: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor"><path d="M205.66,194.34a8,8,0,0,1-11.32,11.32L128,139.31,61.66,205.66a8,8,0,0,1-11.32-11.32L116.69,128,50.34,61.66A8,8,0,0,1,61.66,50.34L128,116.69l66.34-66.35a8,8,0,0,1,11.32,11.32L139.31,128Z"/></svg>',
    terang: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor"><path d="M120,40V16a8,8,0,0,1,16,0V40a8,8,0,0,1-16,0Zm72,88a64,64,0,1,1-64-64A64.07,64.07,0,0,1,192,128Zm-16,0a48,48,0,1,0-48,48A48.05,48.05,0,0,0,176,128ZM58.34,69.66A8,8,0,0,0,69.66,58.34l-16-16A8,8,0,0,0,42.34,53.66Zm0,116.68-16,16a8,8,0,0,0,11.32,11.32l16-16a8,8,0,0,0-11.32-11.32ZM192,72a8,8,0,0,0,5.66-2.34l16-16a8,8,0,0,0-11.32-11.32l-16,16A8,8,0,0,0,192,72Zm5.66,114.34a8,8,0,0,0-11.32,11.32l16,16a8,8,0,0,0,11.32-11.32ZM48,128a8,8,0,0,0-8-8H16a8,8,0,0,0,0,16H40A8,8,0,0,0,48,128Zm80,80a8,8,0,0,0-8,8v24a8,8,0,0,0,16,0V216A8,8,0,0,0,128,208Zm112-88H216a8,8,0,0,0,0,16h24a8,8,0,0,0,0-16Z"/></svg>',
    gelap: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor"><path d="M233.54,142.23a8,8,0,0,0-8-2,88.08,88.08,0,0,1-109.8-109.8,8,8,0,0,0-10-10,104.84,104.84,0,0,0-52.91,37A104,104,0,0,0,136,224a103.09,103.09,0,0,0,62.52-20.88,104.84,104.84,0,0,0,37-52.91A8,8,0,0,0,233.54,142.23ZM188.9,190.34A88,88,0,0,1,65.66,67.11a89,89,0,0,1,31.4-26A106,106,0,0,0,96,56,104.11,104.11,0,0,0,200,160a106,106,0,0,0,14.92-1.06A89,89,0,0,1,188.9,190.34Z"/></svg>',
    luar: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor"><path d="M224,104a8,8,0,0,1-16,0V59.32l-66.33,66.34a8,8,0,0,1-11.32-11.32L196.68,48H152a8,8,0,0,1,0-16h64a8,8,0,0,1,8,8Zm-40,24a8,8,0,0,0-8,8v72H48V80h72a8,8,0,0,0,0-16H48A16,16,0,0,0,32,80V208a16,16,0,0,0,16,16H176a16,16,0,0,0,16-16V136A8,8,0,0,0,184,128Z"/></svg>',
    centang: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor"><path d="M229.66,77.66l-128,128a8,8,0,0,1-11.32,0l-56-56a8,8,0,0,1,11.32-11.32L96,188.69,218.34,66.34a8,8,0,0,1,11.32,11.32Z"/></svg>',
    awas: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor"><path d="M128,24A104,104,0,1,0,232,128,104.11,104.11,0,0,0,128,24Zm0,192a88,88,0,1,1,88-88A88.1,88.1,0,0,1,128,216Zm-8-80V80a8,8,0,0,1,16,0v56a8,8,0,0,1-16,0Zm20,36a12,12,0,1,1-12-12A12,12,0,0,0,140,172Z"/></svg>'
  };

  /* Arti setiap temuan audit, supaya pembaca tidak perlu menebak dari namanya. */
  var ARTI_TEMUAN = {
    keyakinan_mutlak: "Model menyatakan keyakinan 1,0 secara mutlak. Keyakinan seperti ini tidak terkalibrasi, jadi jangan dipakai sebagai ambang penyaringan.",
    keyakinan_rendah: "Keyakinan di bawah 0,6. Baris ini paling layak diperiksa manusia lebih dahulu.",
    bukti_parafrase: "Kutipan bukti bukan salinan harfiah dari teks, melainkan parafrase. Bukti yang diparafrase lebih sulit diperiksa.",
    sapaan_beraspek: "Teksnya sapaan, tetapi diberi aspek. Sapaan tidak memuat penilaian, sehingga aspek di situ menyesatkan.",
    sapaan_bersentimen: "Teksnya sapaan, tetapi diberi sentimen. Ini sisa kebiasaan kelas netral lama yang menampung sapaan.",
    opini_teks_pendek: "Baris opini dengan teks sangat pendek, sehingga dasar penilaiannya tipis.",
    bintang5_negatif: "Ulasan berbintang lima, tetapi isi teksnya negatif. Bukti bahwa bintang tidak dapat dipakai sebagai acuan otomatis.",
    bintang1_positif: "Ulasan berbintang satu, tetapi isi teksnya positif.",
    sapaan_keyakinan_tinggi: "Sapaan yang diberi keyakinan tinggi, padahal tidak ada dasar penilaian di dalamnya.",
    karantina_bertopik: "Baris dikarantina meskipun teksnya menyebut topik sensus. Kandidat salah tolak gerbang.",
    asing_tapi_relevan: "Teks berbahasa asing tetapi tetap relevan, sehingga penyaring bahasa perlu ditinjau.",
    aspek_kosong: "Aspek tidak terisi padahal barisnya opini.",
    bukti_kosong: "Kutipan bukti kosong, sehingga labelnya tidak dapat diperiksa."
  };

  var ARTI_KEPARAHAN = {
    kritis: "Menghalangi pemakaian, harus dibetulkan lebih dahulu.",
    tinggi: "Mempengaruhi mutu label secara nyata.",
    sedang: "Perlu ditinjau, tetapi tidak mengubah tafsiran angka.",
    rendah: "Catatan kebersihan data."
  };

  var SUMBER = { youtube: "YouTube", playstore: "Google Play", threads: "Threads" };
  var KELAS_HURUF = { negatif: "Negatif", netral: "Netral", positif: "Positif", tidak_relevan: "Tidak relevan" };

  /* ------------------------------------------------------------------------
     Perkakas kecil
     ------------------------------------------------------------------------ */
  function $(sel, akar) { return (akar || document).querySelector(sel); }

  /* Nama unsur yang termasuk ruang nama SVG. Unsur di luar daftar ini dibuat
     sebagai unsur HTML biasa. Tanpa pemisahan ini, bagan SVG hanya akan menjadi
     unsur tak dikenal yang tidak digambar peramban. */
  var UNSUR_SVG = {
    svg: 1, g: 1, line: 1, circle: 1, polyline: 1, polygon: 1,
    path: 1, rect: 1, text: 1, title: 1, defs: 1
  };

  function h(tag, sifat, isi) {
    var n = UNSUR_SVG[tag]
      ? document.createElementNS("http://www.w3.org/2000/svg", tag)
      : document.createElement(tag);
    if (sifat) {
      Object.keys(sifat).forEach(function (k) {
        var v = sifat[k];
        if (v === null || v === undefined || v === false) return;
        if (k === "class") n.setAttribute("class", v);
        else if (k === "html") n.innerHTML = v;
        /* "teks" dan "text" sama-sama menjadi isi unsur, bukan atribut, sebab
           unsur <text> pada SVG memakai isi untuk menampilkan tulisan. */
        else if (k === "teks" || k === "text") n.textContent = v;
        else if (k === "dataset") Object.keys(v).forEach(function (d) { n.dataset[d] = v[d]; });
        else if (k.slice(0, 2) === "on") n.addEventListener(k.slice(2), v);
        else n.setAttribute(k, v === true ? "" : v);
      });
    }
    if (isi) {
      (Array.isArray(isi) ? isi : [isi]).forEach(function (a) {
        if (a === null || a === undefined || a === false) return;
        n.appendChild(typeof a === "string" ? document.createTextNode(a) : a);
      });
    }
    return n;
  }

  function kosongkan(n) { while (n.firstChild) n.removeChild(n.firstChild); }

  function angka(n, desimal) {
    if (n === null || n === undefined || n === "") return "-";
    if (typeof n !== "number") return String(n);
    return n.toLocaleString("id-ID", {
      minimumFractionDigits: desimal === undefined ? 0 : desimal,
      maximumFractionDigits: desimal === undefined ? 0 : desimal
    });
  }

  function persen(n, desimal) {
    if (typeof n !== "number") return "-";
    return (n * 100).toLocaleString("id-ID", {
      minimumFractionDigits: desimal === undefined ? 1 : desimal,
      maximumFractionDigits: desimal === undefined ? 1 : desimal
    }) + "%";
  }

  function ikon(nama) { return h("span", { class: "ikon", html: IKON[nama] || "" }); }

  function penanda(kelas, teks) { return h("span", { class: "penanda " + kelas, teks: teks }); }

  function blok(judul, keterangan, isi) {
    return h("section", { class: "blok" }, [
      judul ? h("h3", { teks: judul }) : null,
      keterangan ? h("p", { class: "ket", teks: keterangan }) : null
    ].concat(isi || []));
  }

  function tabel(kepala, baris, opsi) {
    opsi = opsi || {};
    var thead = h("thead", null, h("tr", null, kepala.map(function (k) {
      return h("th", { class: k[1] === "angka" ? "angka" : null, teks: k[0] });
    })));
    var tbody = h("tbody", null, baris.map(function (r) {
      var tr = h("tr", { class: r.kelas || null }, r.sel.map(function (s, i) {
        var isi = s && typeof s === "object" && s.nodeType ? s : h("td", {
          class: kepala[i] && kepala[i][1] === "angka" ? "angka" : null
        }, typeof s === "string" || typeof s === "number" ? String(s) : s);
        return isi;
      }));
      return tr;
    }));
    var t = h("table", { class: "data" }, [thead, tbody]);
    var bungkus = h("div", { class: "bungkus-tabel" }, t);
    if (opsi.catatan) bungkus.insertBefore(h("p", { class: "ket", style: "padding:12px 16px 0", teks: opsi.catatan }), t);
    return bungkus;
  }

  function batangToken(daftar, opsi) {
    opsi = opsi || {};
    var maks = daftar.reduce(function (m, d) { return Math.max(m, Math.abs(d[1])); }, 0) || 1;
    return h("div", { class: "batang" }, daftar.slice(0, opsi.batas || 10).map(function (d) {
      var lebar = Math.max(1.5, (Math.abs(d[1]) / maks) * 100);
      return h("div", { class: "batang-baris" }, [
        h("span", { class: "tok", title: d[0], teks: d[0] }),
        h("span", { class: "nil", teks: (d[1] > 0 ? "+" : "") + d[1].toFixed(4) }),
        h("span", { class: "batang-rel" }, h("i", {
          class: opsi.warna === "aksen" ? "a" : (d[1] < 0 ? "n" : "p"),
          style: "width:" + lebar + "%"
        }))
      ]);
    }));
  }

  /* ------------------------------------------------------------------------
     Tema: satu tema untuk seluruh halaman, bawaan mengikuti sistem
     ------------------------------------------------------------------------ */
  function initTema() {
    var tombol = $("#tombol-tema");
    var ikonTema = $("#ikon-tema");
    var teksTema = $(".tema-teks", tombol);
    var dipilih = null;
    try { dipilih = localStorage.getItem("dss-tema"); } catch (e) { dipilih = null; }
    var sistemGelap = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;

    function pasang(tema) {
      var gelap = tema === "gelap";
      document.documentElement.dataset.tema = gelap ? "gelap" : "terang";
      tombol.setAttribute("aria-pressed", gelap ? "true" : "false");
      teksTema.textContent = gelap ? "Terang" : "Gelap";
      kosongkan(ikonTema);
      ikonTema.appendChild(h("span", { class: "ikon", html: gelap ? IKON.terang : IKON.gelap }));
    }

    pasang(dipilih || (sistemGelap ? "gelap" : "terang"));

    tombol.addEventListener("click", function () {
      var baru = document.documentElement.dataset.tema === "gelap" ? "terang" : "gelap";
      pasang(baru);
      try { localStorage.setItem("dss-tema", baru); } catch (e) { /* diabaikan */ }
    });
  }

  /* ------------------------------------------------------------------------
     Navigasi bagian
     ------------------------------------------------------------------------ */
  var PANEL = ["ringkasan", "alur", "label", "mutu", "model", "banding", "keputusan"];
  var sudahDigambar = {};
  var sedangBuka = false;

  function initTab() {
    var tombol = Array.prototype.slice.call(document.querySelectorAll(".tab-tombol"));
    tombol.forEach(function (t) {
      t.addEventListener("click", function () { buka(t.dataset.panel); });
    });
    document.addEventListener("keydown", function (e) {
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
      var aktif = document.activeElement;
      if (!aktif || !aktif.classList.contains("tab-tombol")) return;
      var i = tombol.indexOf(aktif);
      var tujuan = e.key === "ArrowRight" ? (i + 1) % tombol.length : (i - 1 + tombol.length) % tombol.length;
      tombol[tujuan].focus();
    });
    /* Bagian dapat ditautkan langsung lewat alamat, misalnya index.html#label,
       sehingga satu temuan dapat dikirim ke orang lain tanpa petunjuk menekan. */
    window.addEventListener("hashchange", function () {
      if (sedangBuka) { sedangBuka = false; return; }
      buka((location.hash || "").replace("#", ""));
    });
  }

  function buka(nama) {
    if (PANEL.indexOf(nama) < 0) nama = "ringkasan";
    if (location.hash !== "#" + nama) {
      /* Alamat disamakan dengan bagian yang sedang dibuka, tanpa memicu
         pemrosesan ulang lewat peristiwa hashchange. */
      sedangBuka = true;
      location.hash = nama;
    }
    PANEL.forEach(function (p) {
      var bagian = $("#panel-" + p);
      bagian.hidden = p !== nama;
    });
    Array.prototype.forEach.call(document.querySelectorAll(".tab-tombol"), function (t) {
      if (t.dataset.panel === nama) t.setAttribute("aria-current", "page");
      else t.removeAttribute("aria-current");
    });
    if (!sudahDigambar[nama]) {
      sudahDigambar[nama] = true;
      var peta = {
        ringkasan: gambarRingkasan, alur: gambarAlur, label: gambarPenelusuran,
        mutu: gambarMutu, model: gambarModel, banding: gambarBanding, keputusan: gambarKeputusan
      };
      try {
        peta[nama]();
      } catch (galat) {
        /* Bila satu bagian gagal digambar, pesannya dinyatakan di tempat,
           bukan dibiarkan menjadi halaman kosong tanpa penjelasan. */
        var panel = $("#panel-" + nama);
        panel.appendChild(h("p", { class: "catatan-kosong" },
          "Bagian ini gagal digambar: " + galat.message));
        if (window.console && console.error) console.error(galat);
      }
    }
    window.scrollTo({ top: 0, behavior: "instant" in window ? "instant" : "auto" });
  }

  /* ------------------------------------------------------------------------
     Panel 1: Ringkasan
     ------------------------------------------------------------------------ */
  function gambarRingkasan() {
    var p = $("#panel-ringkasan");
    kosongkan(p);

    p.appendChild(h("div", { class: "pembuka" }, [
      h("h1", { id: "judul-ringkasan", teks: "Setiap label bisa ditelusuri sampai buktinya." }),
      h("p", { class: "masuk", teks: "Delapan ribu tiga ratus lima puluh dua baris data publik tentang Sensus Ekonomi 2026 dan aplikasi Fasih BPS, dari panen data sampai penjelasan model." }),
      h("div", { class: "pembuka-kendali" }, [
        h("button", { class: "tombol tombol-utama", type: "button", onclick: function () { buka("label"); } }, "Telusuri label"),
        h("button", { class: "tombol tombol-samar", type: "button", onclick: function () { buka("alur"); } }, "Lihat alur penelitian")
      ])
    ]));

    var deret = h("div", { class: "deret-ukuran" }, (D.kpi || []).map(function (k) {
      return h("div", { class: "ukuran" + (k.sorot ? " sorot" : "") }, [
        h("div", { class: "nama", teks: k.label }),
        h("div", { class: "nilai", teks: typeof k.nilai === "number" ? angka(k.nilai, k.nilai < 1 ? 4 : 0) : k.nilai }),
        h("div", { class: "ket", teks: k.catatan })
      ]);
    }));
    p.appendChild(deret);

    p.appendChild(h("div", { class: "konteks-ringkas", "aria-label": "Konteks data" }, [
      h("span", { teks: "8.352 baris korpus" }),
      h("span", { teks: "5.808 opini berlabel" }),
      h("span", { teks: "3 sumber: YouTube, Google Play, Threads" }),
      h("span", { teks: "XAI: LIME + peta atensi + BertViz" })
    ]));

    p.appendChild(h("div", { class: "dss-teaser" }, [
      h("div", null, [
        h("strong", { teks: "Lanjut ke Dasbor Tren & DSS" }),
        h("p", { teks: "Lihat tren sentimen per periode, distribusi platform, topik utama, anomali, dan matriks prioritas respons. Dasbor ini membaca data riil dari berkas DSS yang sama." })
      ]),
      h("a", { class: "tombol tombol-utama", href: "dss_trendline.html", teks: "Buka dasbor ↗" })
    ]));

    var klaim = D.klaim || { boleh: [], tidak: [] };
    p.appendChild(blok("Yang boleh dan tidak boleh diklaim", "Bagian ini yang paling sering ditanyakan penguji. Seluruh angka pada halaman ini harus dibaca bersama batas ini.",
      h("div", { class: "klaim" }, [
        h("div", { class: "klaim-kolom ya" }, [
          h("h4", null, [ikon("centang"), "Boleh diklaim"]),
          h("ul", null, klaim.boleh.map(function (k) {
            return h("li", null, [h("strong", { teks: k.teks }), h("span", { teks: k.dasar })]);
          }))
        ]),
        h("div", { class: "klaim-kolom tidak" }, [
          h("h4", null, [ikon("awas"), "Tidak boleh diklaim"]),
          h("ul", null, klaim.tidak.map(function (k) {
            return h("li", null, [h("strong", { teks: k.teks }), h("span", { teks: k.dasar })]);
          }))
        ])
      ])));

    p.appendChild(gambarKurva());

    var temuan = D.temuan || [];
    if (temuan.length) {
      p.appendChild(blok("Temuan yang mengubah arah pekerjaan", "Kelima hal ini ditemukan lewat audit, bukan direncanakan sejak awal.",
        h("div", { class: "grid-dua" }, temuan.map(function (t, i) {
          return h("div", { class: "kotak" }, [
            h("h4", { teks: "Temuan " + (i + 1) }),
            h("p", { teks: t })
          ]);
        }))));
    }
  }

  /* Kurva pertukaran: kepekaan kelas netral selalu dibayar dengan kepekaan
     kelas negatif. Digambar dari angka evaluasi gold, bukan hiasan. */
  function gambarKurva() {
    var titik = (D.gold && D.gold.kurva) || [];
    if (!titik.length) return h("div");

    var L_ = 62, R_ = 18, T_ = 20, B_ = 44;
    var w = 560, ht = 300;
    var xs = titik.map(function (t) { return t.negatif; });
    var ys = titik.map(function (t) { return t.netral; });
    var x0 = Math.min.apply(null, xs) - 0.06, x1 = Math.max.apply(null, xs) + 0.04;
    var y0 = Math.min.apply(null, ys) - 0.08, y1 = Math.max.apply(null, ys) + 0.06;

    function px(v) { return L_ + ((v - x0) / (x1 - x0)) * (w - L_ - R_); }
    function py(v) { return ht - B_ - ((v - y0) / (y1 - y0)) * (ht - T_ - B_); }

    var anak = [];
    for (var g = 0; g <= 4; g++) {
      var ny = y0 + ((y1 - y0) * g) / 4;
      var nx = x0 + ((x1 - x0) * g) / 4;
      anak.push(h("line", { class: "kisi", x1: L_, x2: w - R_, y1: py(ny), y2: py(ny) }));
      anak.push(h("text", { class: "tanda-sumbu", x: L_ - 9, y: py(ny) + 3.5, "text-anchor": "end", text: ny.toFixed(2) }));
      /* Label mendatar dijangkarkan menjauhi tepi: yang pertama mulai dari garis
         sumbu, yang terakhir berakhir di situ, sehingga tidak ada yang keluar
         dari kotak bagan maupun bertabrakan dengan label sumbu tegak. */
      var jangkarX = g === 0 ? "start" : (g === 4 ? "end" : "middle");
      anak.push(h("text", { class: "tanda-sumbu", x: px(nx), y: ht - B_ + 16, "text-anchor": jangkarX, text: nx.toFixed(2) }));
    }
    anak.push(h("line", { class: "sumbu", x1: L_, x2: w - R_, y1: ht - B_, y2: ht - B_ }));
    anak.push(h("line", { class: "sumbu", x1: L_, x2: L_, y1: T_, y2: ht - B_ }));

    var urut = titik.slice().sort(function (a, b) { return a.negatif - b.negatif; });
    anak.push(h("polyline", {
      class: "jejak",
      points: urut.map(function (t) { return px(t.negatif) + "," + py(t.netral); }).join(" ")
    }));

    titik.forEach(function (t) {
      anak.push(h("circle", { class: "titik", cx: px(t.negatif), cy: py(t.netral), r: 4.5 }));
      /* Label ditaruh di kanan titik, kecuali bila akan keluar dari kotak bagan;
         dalam hal itu label dipindah ke kiri titik. */
      var lebarTaksir = (t.sistem || "").length * 6.2 + 12;
      var keluar = px(t.negatif) + 9 + lebarTaksir > w - R_;
      var xLabel = keluar ? px(t.negatif) - 9 : px(t.negatif) + 9;
      var jangkar = keluar ? "end" : "start";
      anak.push(h("text", {
        class: "label-titik", x: xLabel, y: py(t.netral) - 3, "text-anchor": jangkar,
        text: t.sistem
      }));
      anak.push(h("text", {
        class: "nilai-titik", x: xLabel, y: py(t.netral) + 9, "text-anchor": jangkar,
        text: t.negatif.toFixed(3) + " / " + t.netral.toFixed(3)
      }));
    });

    anak.push(h("text", { class: "judul-sumbu", x: L_ + (w - L_ - R_) / 2, y: ht - 6, "text-anchor": "middle", text: "Kepekaan kelas negatif (recall)" }));
    anak.push(h("text", {
      class: "judul-sumbu", x: 14, y: T_ + (ht - T_ - B_) / 2, "text-anchor": "middle",
      transform: "rotate(-90 14 " + (T_ + (ht - T_ - B_) / 2) + ")",
      text: "Kepekaan kelas netral (recall)"
    }));

    return blok("Kurva pertukaran antar skema anotasi",
      "Empat sistem dari dua keluarga model menempati satu kurva yang sama. Tidak ada yang lebih baik, hanya berbeda letak garisnya. Inilah bukti bahwa yang bermasalah adalah definisi batas antar kelas, bukan kemampuan model.",
      h("div", { class: "kurva-bungkus" }, [
        h("svg", { class: "kurva", viewBox: "0 0 " + w + " " + ht, role: "img", "aria-label": "Sebaran kepekaan kelas negatif dan netral untuk empat skema anotasi" }, anak),
        h("div", { class: "legenda" }, [
          h("span", null, "Kurva putus-putus menunjukkan arah pergeseran: menambah kepekaan netral selalu mengurangi kepekaan negatif.")
        ])
      ]));
  }

  /* ------------------------------------------------------------------------
     Panel 2: Alur
     ------------------------------------------------------------------------ */
  function gambarAlur() {
    var p = $("#panel-alur");
    kosongkan(p);

    p.appendChild(h("div", { class: "judul-panel" }, [
      h("h2", { id: "judul-alur", teks: "Alur penelitian, hulu ke hilir" }),
      h("p", { class: "keterangan-panel", teks: "Delapan tahap berurutan. Setiap tahap menyimpan keluarannya, sehingga penjalanan dapat dilanjutkan dari tahap terakhir yang berhasil." })
    ]));

    p.appendChild(h("div", { class: "alur" }, (D.alur || []).map(function (t, i) {
      return h("article", { class: "tahap" }, [
        h("div", { class: "tahap-no", teks: String(i + 1).padStart(2, "0") }),
        h("div", { class: "tahap-isi" }, [
          h("h4", { teks: t.nama }),
          h("p", { class: "ringkas", teks: t.ringkas }),
          h("ul", null, (t.rinci || []).map(function (r) { return h("li", { teks: r }); }))
        ]),
        h("div", { class: "tahap-sisi" }, [
          h("div", { class: "tahap-angka" }, (t.angka || []).map(function (a) {
            return h("span", { class: "pil" }, [a.label + ": ", h("b", { teks: a.nilai })]);
          })),
          t.catatan ? h("p", { class: "tahap-catatan", teks: t.catatan }) : null
        ])
      ]);
    })));

    p.appendChild(blok("Penyaringan berlapis", "Empat lapis diterapkan berurutan, dan jumlah pada setiap lapis dicatat supaya kehilangan data dapat dipertanggungjawabkan.",
      tabel(
        [["Lapis", ""], ["Sebelum", "angka"], ["Sesudah", "angka"], ["Yang dibuang", "angka"]],
        (D.saring || []).map(function (s) {
          return {
            sel: [
              s.tahap,
              s.sebelum === null ? "titik awal" : angka(s.sebelum),
              angka(s.sesudah),
              s.sebelum === null ? "-" : angka(s.sebelum - s.sesudah)
            ]
          };
        })
      )));

    p.appendChild(blok("Sumber data", "Dua platform tidak menghasilkan data karena pembatasan akses dari penyedianya, bukan karena kegagalan kode.",
      tabel(
        [["Platform", ""], ["Baris korpus", "angka"], ["Teranotasi", "angka"], ["Catatan", ""]],
        (D.sumber || []).map(function (s) {
          return { sel: [s.nama, angka(s.jumlah), angka(s.teranotasi), h("span", { class: "kecil", teks: s.catatan })] };
        })
      )));

    p.appendChild(blok("Pemilahan ember", "Tidak relevan sengaja bukan kelas keempat pada model sentimen, melainkan gerbang penyaring.",
      tabel(
        [["Ember", ""], ["Baris", "angka"], ["Perlakuan", ""]],
        (D.ember || []).map(function (e) {
          return { sel: [h("span", { class: "mono", teks: e.nama }), angka(e.jumlah), e.perlakuan] };
        })
      )));

    p.appendChild(gambarBulanan());
  }

  /* ------------------------------------------------------------------------
     Panel 3: Penelusuran label
     ------------------------------------------------------------------------ */
  var FILTER = { cari: "", ember: "", sumber: "", label: "", tipe: "", bertanda: false, gold: false, bertentangan: false };
  var INDEKS = {};
  var barisSaring = [];
  var terpilih = null;

  function indeksKolom() {
    (L.kolom || []).forEach(function (k, i) { INDEKS[k] = i; });
  }

  function ambil(baris, kunci) { return baris[INDEKS[kunci]]; }

  function cocok(baris) {
    if (FILTER.ember && ambil(baris, "ember") !== FILTER.ember) return false;
    if (FILTER.sumber && ambil(baris, "sumber") !== FILTER.sumber) return false;
    if (FILTER.label && ambil(baris, "label") !== FILTER.label) return false;
    if (FILTER.tipe && ambil(baris, "tipe") !== FILTER.tipe) return false;
    var uid = ambil(baris, "uid");
    if (FILTER.bertanda && !(D.audit_per_baris || {})[uid]) return false;
    if (FILTER.gold && !(D.gold_per_baris || {})[uid]) return false;
    if (FILTER.bertentangan) {
      /* Baris yang leksikonnya lebih banyak menyokong kelas lain daripada kelas
         yang diberikan. Inilah baris yang paling perlu diperiksa manusia lebih
         dahulu, karena labelnya tidak didukung kata-katanya sendiri. */
      var d = hitungDukungan()[uid];
      if (!d || d.n < 2 || d.selisih <= 0) return false;
    }
    if (FILTER.cari) {
      var q = FILTER.cari.toLowerCase();
      var gabung = [
        ambil(baris, "teks"), ambil(baris, "bukti"), ambil(baris, "alasan"),
        ambil(baris, "konteks"), ambil(baris, "induk"), uid
      ].join(" ").toLowerCase();
      if (gabung.indexOf(q) < 0) return false;
    }
    return true;
  }

  var TINGGI_BARIS = 62;
  var JENDELA_AKHIR = -1;

  function gambarPenelusuran() {
    var p = $("#panel-label");
    kosongkan(p);

    p.appendChild(h("div", { class: "judul-panel" }, [
      h("h2", { id: "judul-label", teks: "Penelusuran label" }),
      h("p", { class: "keterangan-panel", teks: "Seluruh " + angka((L.baris || []).length) + " baris berlabel ada di sini, bukan contoh pilihan. Buka satu baris untuk melihat teks asalnya, kutipan bukti, alasan model, temuan audit, penilaian manusia, dan penjelasan model bila tersedia." })
    ]));

    var input = h("input", { type: "search", id: "saring-cari", placeholder: "Cari teks, bukti, alasan, atau uid", autocomplete: "off" });
    var pilihan = function (id, label, opsi) {
      return h("div", { class: "kolom-saring" }, [
        h("label", { for: id, teks: label }),
        h("select", { id: id }, opsi.map(function (o) {
          return h("option", { value: o[0], teks: o[1] });
        }))
      ]);
    };

    var sumberTersedia = [];
    var tipeTersedia = [];
    var lihatSumber = {};
    var lihatTipe = {};
    (L.baris || []).forEach(function (b) {
      var s = ambil(b, "sumber");
      if (s && !lihatSumber[s]) { lihatSumber[s] = true; sumberTersedia.push(s); }
      var t = ambil(b, "tipe");
      if (t && !lihatTipe[t]) { lihatTipe[t] = true; tipeTersedia.push(t); }
    });
    sumberTersedia.sort();
    tipeTersedia.sort();

    var saring = h("div", { class: "saring" }, [
      h("div", { class: "kolom-saring cari" }, [
        h("label", { for: "saring-cari", teks: "Cari" }),
        ikon("cari"),
        input
      ]),
      pilihan("saring-ember", "Ember", [["", "Semua ember"]].concat(
        (D.ember || []).map(function (e) { return [e.nama, e.nama + " (" + angka(e.jumlah) + ")"]; }))),
      pilihan("saring-sumber", "Sumber", [["", "Semua sumber"]].concat(
        sumberTersedia.map(function (s) { return [s, SUMBER[s] || s]; }))),
      pilihan("saring-label", "Label", [["", "Semua label"]].concat(
        ["negatif", "netral", "positif", "tidak_relevan"].map(function (k) { return [k, KELAS_HURUF[k]]; }))),
      pilihan("saring-tipe", "Tipe teks", [["", "Semua tipe"]].concat(
        tipeTersedia.map(function (t) { return [t, t]; }))),
      h("div", { class: "sakelar" }, [
        h("label", null, [
          h("input", { type: "checkbox", id: "saring-bertanda" }), "Bertanda audit"
        ]),
        h("label", null, [
          h("input", { type: "checkbox", id: "saring-gold" }), "Di gold set"
        ]),
        h("label", { title: "Baris yang kata-katanya lebih banyak menyokong kelas lain daripada label yang diberikan" }, [
          h("input", { type: "checkbox", id: "saring-bertentangan" }), "Leksikon menentang"
        ])
      ])
    ]);

    var hitung = h("span", { id: "hitung-label" });
    var cepat = h("span", { class: "cepat" }, [
      h("button", { class: "tombol tombol-samar tombol-kecil", type: "button", onclick: function () { aturCepat("bertentangan"); } }, "Leksikon menentang label"),
      h("button", { class: "tombol tombol-samar tombol-kecil", type: "button", onclick: function () { aturCepat("keyakinan"); } }, "Keyakinan di bawah 0,6"),
      h("button", { class: "tombol tombol-samar tombol-kecil", type: "button", onclick: function () { aturCepat("karantina"); } }, "Karantina"),
      h("button", { class: "tombol tombol-samar tombol-kecil", type: "button", onclick: function () { aturCepat("netral"); } }, "Kelas netral"),
      h("button", { class: "tombol tombol-samar tombol-kecil", type: "button", onclick: function () { aturCepat("reset"); } }, "Bersihkan")
    ]);

    var bar = h("div", { class: "bar-penelusur" }, [hitung, cepat]);

    var daftar = h("div", { class: "daftar", id: "daftar-label", tabindex: "0" },
      h("div", { class: "daftar-penuh", id: "daftar-penuh" }));

    p.appendChild(h("div", { class: "penelusur" }, [
      saring,
      bar,
      h("div", { class: "daftar-bungkus" }, daftar)
    ]));

    function aturCepat(jenis) {
      FILTER.cari = "";
      input.value = "";
      FILTER.ember = ""; FILTER.sumber = ""; FILTER.label = ""; FILTER.tipe = "";
      FILTER.bertanda = false; FILTER.gold = false; FILTER.bertentangan = false;
      $("#saring-ember").value = ""; $("#saring-sumber").value = "";
      $("#saring-label").value = ""; $("#saring-tipe").value = "";
      $("#saring-bertanda").checked = false; $("#saring-gold").checked = false;
      $("#saring-bertentangan").checked = false;
      terapkanTambahan(null);
      if (jenis === "keyakinan") {
        terapkanTambahan(function (b) { var y = ambil(b, "yak"); return typeof y === "number" && y < 0.6; });
      } else if (jenis === "karantina") FILTER.ember = "karantina";
      else if (jenis === "netral") FILTER.label = "netral";
      else if (jenis === "bertentangan") FILTER.bertentangan = true;
      if (jenis === "karantina") $("#saring-ember").value = "karantina";
      if (jenis === "netral") $("#saring-label").value = "netral";
      if (jenis === "bertentangan") $("#saring-bertentangan").checked = true;
      terapkan();
    }

    input.addEventListener("input", function () {
      FILTER.cari = input.value.trim();
      terapkan();
    });
    [["saring-ember", "ember"], ["saring-sumber", "sumber"], ["saring-label", "label"], ["saring-tipe", "tipe"]]
      .forEach(function (pasang) {
        $("#" + pasang[0]).addEventListener("change", function (e) {
          FILTER[pasang[1]] = e.target.value; terapkan();
        });
      });
    $("#saring-bertanda").addEventListener("change", function (e) { FILTER.bertanda = e.target.checked; terapkan(); });
    $("#saring-gold").addEventListener("change", function (e) { FILTER.gold = e.target.checked; terapkan(); });
    $("#saring-bertentangan").addEventListener("change", function (e) { FILTER.bertentangan = e.target.checked; terapkan(); });

    daftar.addEventListener("scroll", function () { gambarJendela(); });

    terapkan();
    window.addEventListener("resize", gambarJendela);
  }

  var TAMBAHAN = null;
  function terapkanTambahan(fn) { TAMBAHAN = fn; }

  function terapkan() {
    var semua = L.baris || [];
    barisSaring = [];
    for (var i = 0; i < semua.length; i++) {
      if (!cocok(semua[i])) continue;
      if (TAMBAHAN && !TAMBAHAN(semua[i])) continue;
      barisSaring.push(i);
    }
    $("#hitung-label").innerHTML = "Menampilkan <b>" + angka(barisSaring.length) + "</b> dari <b>" +
      angka(semua.length) + "</b> baris";
    var penuh = $("#daftar-penuh");
    kosongkan(penuh);
    if (!barisSaring.length) {
      penuh.style.height = "auto";
      JENDELA_AKHIR = -1;
      penuh.appendChild(h("div", { class: "kosong", teks: "Tidak ada baris yang cocok dengan saringan ini." }));
      return;
    }
    penuh.style.height = (barisSaring.length * TINGGI_BARIS) + "px";
    $("#daftar-label").scrollTop = 0;
    JENDELA_AKHIR = -1;
    gambarJendela();
  }

  /* Daftar digambar bertingkap: hanya baris yang terlihat yang masuk ke DOM,
     sehingga delapan ribu baris tetap ringan digulir. */
  function gambarJendela() {
    var daftar = $("#daftar-label");
    var penuh = $("#daftar-penuh");
    if (!daftar || !penuh || !barisSaring.length) return;
    var mulai = Math.max(0, Math.floor(daftar.scrollTop / TINGGI_BARIS) - 4);
    var muat = Math.ceil(daftar.clientHeight / TINGGI_BARIS) + 8;
    var akhir = Math.min(barisSaring.length, mulai + muat);
    if (mulai === JENDELA_AKHIR && penuh.childElementCount === akhir - mulai) return;
    JENDELA_AKHIR = mulai;
    kosongkan(penuh);
    for (var i = mulai; i < akhir; i++) {
      penuh.appendChild(barisElemen(barisSaring[i], i));
    }
  }

  function barisElemen(indeksBaris, posisi) {
    var b = (L.baris || [])[indeksBaris];
    var uid = ambil(b, "uid");
    var label = ambil(b, "label");
    var sumber = ambil(b, "sumber");
    var yak = ambil(b, "yak");
    var audit = (D.audit_per_baris || {})[uid];
    var gold = (D.gold_per_baris || {})[uid];
    var lime = ((D.xai || {}).lime || {}).per_uid || {};
    var punyaXai = !!lime[uid] || (D.xai_uid_atensi || {})[uid] || (D.xai_uid_bertviz || {})[uid];

    var tanda = h("span", { class: "tanda" }, [
      audit ? h("span", { class: "titik audit", title: "Bertanda audit: " + (audit.temuan || []).length + " temuan" }) : null,
      gold ? h("span", { class: "titik gold", title: "Ada penilaian gold manusia" }) : null,
      punyaXai ? h("span", { class: "titik xai", title: "Ada penjelasan model" }) : null
    ]);

    return h("button", {
      class: "baris-label",
      type: "button",
      style: "top:" + (posisi * TINGGI_BARIS) + "px",
      "aria-current": terpilih === uid ? "true" : "false",
      dataset: { uid: uid },
      onclick: function () { bukaLaci(uid, b); }
    }, [
      h("span", { class: "meta kolom-sumber" }, [
        penanda(label || "netral2", KELAS_HURUF[label] || "belum teranotasi"),
        h("span", { class: "mono", teks: SUMBER[sumber] || sumber || "" })
      ]),
      h("span", { class: "teks", teks: ambil(b, "teks") || "" }),
      h("span", { class: "ya", teks: typeof yak === "number" ? yak.toFixed(2) : "-" }),
      tanda
    ]);
  }

  /* ------------------------------------------------------------------------
     Laci rincian baris: inti penelusuran dan penjelasan
     ------------------------------------------------------------------------ */
  function normalkanDenganPeta(s) {
    var keluar = "", peta = [], renggang = false;
    for (var i = 0; i < s.length; i++) {
      var c = s.charAt(i);
      if (/\s/.test(c)) {
        if (renggang) continue;
        renggang = true;
        keluar += " ";
        peta.push(i);
      } else {
        renggang = false;
        keluar += c.toLowerCase();
        peta.push(i);
      }
    }
    return { teks: keluar, peta: peta };
  }

  /* Menyisipkan penanda pada kutipan bukti di dalam teks asalnya. Kalau kutipan
     tidak ditemukan harfiah, hal itu dinyatakan apa adanya, bukan disembunyikan,
     karena justru itu temuan auditnya. */
  function sorotBukti(teks, bukti) {
    if (!teks || !bukti) return { html: null, status: "kosong" };
    var a = normalkanDenganPeta(teks);
    var b = normalkanDenganPeta(bukti).teks.replace(/^\s+|\s+$/g, "");
    if (!b) return { html: null, status: "kosong" };
    var pos = a.teks.indexOf(b);
    if (pos < 0) return { html: null, status: "parafrase" };
    var mulaiAsli = a.peta[pos];
    var akhirAsli = a.peta[pos + b.length - 1] + 1;
    var potongan = teks.slice(mulaiAsli, akhirAsli);
    return {
      html: esc(teks.slice(0, mulaiAsli)) + "<mark>" + esc(potongan) + "</mark>" + esc(teks.slice(akhirAsli)),
      status: "harfiah"
    };
  }

  function esc(s) {
    return String(s === null || s === undefined ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  /* ------------------------------------------------------------------------
     Petunjuk leksikal untuk seluruh baris
     ------------------------------------------------------------------------
     Bobot per token dihitung buat_web_dss.py dari sebaran kata di korpus memakai
     rasio log-odds berprior Dirichlet, bukan dari atensi model. Karena itu ia
     berlaku untuk keseluruhan 8.352 baris, termasuk baris yang tidak punya peta
     atensi sama sekali. Karena itu pula ia tidak boleh dibaca sebagai penjelasan
     model, dan laci menampilkan keduanya secara terpisah.
     ------------------------------------------------------------------------ */
  var LEKSIKON = D.leksikon || {};
  var KELAS_SENTIMEN = ["negatif", "netral", "positif"];
  var PETA_LEKSIKON = null;
  var DUKUNGAN = null;

  function petaLeksikon() {
    if (PETA_LEKSIKON) return PETA_LEKSIKON;
    PETA_LEKSIKON = {};
    Object.keys(LEKSIKON).forEach(function (k) {
      var p = {};
      (LEKSIKON[k] || []).forEach(function (t) { p[t[0]] = t[1]; });
      PETA_LEKSIKON[k] = p;
    });
    return PETA_LEKSIKON;
  }

  function tokenTeks(s) {
    var m = String(s || "").toLowerCase().match(/[a-z0-9]+/g);
    if (!m) return [];
    var keluar = [];
    for (var i = 0; i < m.length; i++) if (m[i].length >= 3) keluar.push(m[i]);
    return keluar;
  }

  /* Memisahkan token baris menjadi yang menyokong labelnya dan yang menyokong
     kelas lain. Yang kedua itulah yang membuat sebuah label patut dicurigai. */
  function dukunganSatu(label, teks) {
    var peta = petaLeksikon();
    if (KELAS_SENTIMEN.indexOf(label) < 0) return { sokong: null, lawan: null, selisih: null, n: 0 };
    var unik = {}, sokong = [], lawan = [];
    tokenTeks(teks).forEach(function (t) {
      if (unik[t]) return;
      unik[t] = true;
      var zSendiri = peta[label] ? peta[label][t] : undefined;
      var zLain = 0;
      KELAS_SENTIMEN.forEach(function (lain) {
        if (lain !== label && peta[lain] && peta[lain][t] !== undefined) {
          zLain = Math.max(zLain, peta[lain][t]);
        }
      });
      if (zSendiri !== undefined && zSendiri >= zLain) sokong.push(zSendiri);
      else if (zLain > 0) lawan.push(zLain);
    });
    function rata(a) { return a.length ? a.reduce(function (x, y) { return x + y; }, 0) / a.length : 0; }
    var rSokong = rata(sokong), rLawan = rata(lawan);
    return {
      sokong: rSokong,
      lawan: rLawan,
      selisih: rLawan - rSokong,
      n: sokong.length + lawan.length,
      sokongAwal: sokong.length,
      lawanAwal: lawan.length
    };
  }

  /* Skor seluruh baris dihitung sekali lalu disimpan, sebab saringan memintanya
     untuk delapan ribu baris sekaligus. */
  function hitungDukungan() {
    if (DUKUNGAN) return DUKUNGAN;
    DUKUNGAN = {};
    (L.baris || []).forEach(function (b) {
      var label = ambil(b, "label");
      if (KELAS_SENTIMEN.indexOf(label) < 0) return;
      var d = dukunganSatu(label, ambil(b, "bersih") || ambil(b, "teks"));
      if (d.n) DUKUNGAN[ambil(b, "uid")] = d;
    });
    return DUKUNGAN;
  }

  /* Menyorot sekaligus: bentang bukti memakai warna aksen, token pendukung
     memakai warna kelas positif, dan token penentang memakai warna kelas
     negatif. Ketiganya dapat bertumpuk, sehingga penandanya disusun berlapis. */
  function sorotGabungan(teks, bukti, label) {
    var s = String(teks || "");
    if (!s) return { html: null, status: "kosong", adaLeksikal: false };

    var peta = petaLeksikon();
    var petaDukung = peta[label] || {};
    var petaLawan = {};
    KELAS_SENTIMEN.forEach(function (lain) {
      if (lain !== label) {
        Object.keys(peta[lain] || {}).forEach(function (t) {
          petaLawan[t] = Math.max(petaLawan[t] || 0, peta[lain][t]);
        });
      }
    });

    var kelas = {};
    var adaLeksikal = false;
    var pola = /[A-Za-z0-9]+/g;
    var m;
    while ((m = pola.exec(s)) !== null) {
      var kata = m[0].toLowerCase();
      if (kata.length < 3) continue;
      var zD = petaDukung[kata];
      var zL = petaLawan[kata];
      var tanda = null;
      if (zD !== undefined && (zL === undefined || zD >= zL)) tanda = "dukung";
      else if (zL !== undefined) tanda = "lawan";
      if (!tanda) continue;
      for (var i = m.index; i < m.index + m[0].length; i++) kelas[i] = tanda;
      adaLeksikal = true;
    }

    var status = bukti ? "parafrase" : "kosong";
    var bentang = null;
    if (bukti) {
      var a = normalkanDenganPeta(s);
      var b = normalkanDenganPeta(bukti).teks.replace(/^\s+|\s+$/g, "");
      if (b) {
        var pos = a.teks.indexOf(b);
        if (pos >= 0) {
          bentang = [a.peta[pos], a.peta[pos + b.length - 1] + 1];
          status = "harfiah";
        }
      }
    }

    var potongan = [];
    var n = s.length, j = 0;
    while (j < n) {
      var diBukti = !!(bentang && j >= bentang[0] && j < bentang[1]);
      var kls = kelas[j];
      var k = j;
      while (k < n) {
        var db = !!(bentang && k >= bentang[0] && k < bentang[1]);
        if (db !== diBukti || kelas[k] !== kls) break;
        k++;
      }
      potongan.push({ teks: s.slice(j, k), bukti: diBukti, kls: kls });
      j = k;
    }

    var html = potongan.map(function (p) {
      var isi = esc(p.teks);
      if (p.kls) isi = '<mark class="' + p.kls + '">' + isi + "</mark>";
      if (p.bukti) isi = "<mark>" + isi + "</mark>";
      return isi;
    }).join("");

    return { html: html, status: status, adaLeksikal: adaLeksikal };
  }

  function bukaLaci(uid, b) {
    terpilih = uid;
    var laci = $("#laci"), tabir = $("#tabir");
    $("#laci-uid").textContent = uid;
    var sumber = ambil(b, "sumber");
    $("#laci-judul").textContent = "Baris " + (SUMBER[sumber] || sumber || "tanpa sumber");

    var isi = $("#laci-isi");
    kosongkan(isi);

    var label = ambil(b, "label");
    var yak = ambil(b, "yak");

    /* 1. Teks asal dengan bukti dan petunjuk leksikal ditandai */
    var teks = ambil(b, "teks") || "";
    var bukti = ambil(b, "bukti");
    var bersih = ambil(b, "bersih") || "";
    var hasil = sorotGabungan(teks, bukti, label);
    var statusBukti = hasil.status;
    if (statusBukti === "parafrase" && bersih && bersih !== teks) {
      var hasil2 = sorotGabungan(bersih, bukti, label);
      if (hasil2.status === "harfiah") { hasil = hasil2; statusBukti = "bersih"; }
    }

    var keteranganBukti = {
      harfiah: null,
      bersih: "Kutipan cocok setelah teks dibersihkan, bukan pada teks mentahnya.",
      parafrase: "Kutipan bukti tidak ditemukan harfiah di dalam teks. Model memparafrase buktinya, sehingga kutipan itu tidak dapat diperiksa langsung.",
      kosong: "Bukti tidak diisi pada baris ini."
    }[statusBukti];

    isi.appendChild(h("div", { class: "bagian-laci" }, [
      h("h3", { teks: "Teks asal" }),
      hasil.html ? h("p", { class: "teks-asli", html: hasil.html })
        : h("p", { class: "teks-asli", teks: teks }),
      hasil.adaLeksikal ? h("div", { class: "kunci-warna", style: "margin-top:12px" }, [
        h("span", null, [h("i", { class: "bukti" }), "kutipan bukti"]),
        h("span", null, [h("i", { class: "dukung" }), "kata penyokong label ini"]),
        h("span", null, [h("i", { class: "lawan" }), "kata penyokong kelas lain"])
      ]) : null,
      keteranganBukti ? h("p", { class: "tahap-catatan", style: "margin-top:10px", teks: keteranganBukti }) : null,
      teks && teks !== bersih && bersih ? h("p", { class: "kecil", style: "margin-top:8px;color:var(--tinta-samar);font-size:12px", teks: "Teks setelah pembersihan: " + bersih }) : null
    ]));

    /* 1b. Petunjuk leksikal. Berlaku untuk setiap baris, termasuk yang tidak
       punya peta atensi, dan dinyatakan terpisah dari penjelasan model. */
    var dukung = dukunganSatu(label, bersih || teks);
    if (dukung.n && KELAS_SENTIMEN.indexOf(label) >= 0) {
      var rinciLeksikal = [];
      var petaLabel = petaLeksikon()[label] || {};
      var petaLain = {};
      KELAS_SENTIMEN.forEach(function (lain) {
        if (lain !== label) {
          Object.keys(petaLeksikon()[lain] || {}).forEach(function (t) {
            petaLain[t] = Math.max(petaLain[t] || 0, petaLeksikon()[lain][t]);
          });
        }
      });
      var unikL = {};
      tokenTeks(bersih || teks).forEach(function (t) {
        if (unikL[t]) return;
        unikL[t] = true;
        var zD = petaLabel[t];
        var zL = petaLain[t];
        if (zD !== undefined && (zL === undefined || zD >= zL)) rinciLeksikal.push([t, zD]);
        else if (zL !== undefined) rinciLeksikal.push([t, -zL]);
      });
      rinciLeksikal.sort(function (x, y) { return Math.abs(y[1]) - Math.abs(x[1]); });

      var pihak = dukung.selisih > 0
        ? "Leksikon lebih banyak menyokong kelas lain daripada kelas yang diberikan."
        : "Leksikon menyokong kelas yang diberikan.";
      isi.appendChild(h("div", { class: "bagian-laci" }, [
        h("h3", { teks: "Petunjuk leksikal" }),
        h("p", { class: "ket", style: "margin-bottom:10px", teks: "Bobot ini berasal dari sebaran kata di korpus, bukan dari atensi model. Karena itu ia berlaku untuk seluruh baris, termasuk yang tidak punya peta atensi. Batang ke kanan menyokong label baris ini, ke kiri menyokong kelas lain." }),
        h("div", { class: "leksikal" }, rinciLeksikal.slice(0, 10).map(function (d) {
          var maksL = Math.max(Math.abs(d[1]), 0.001);
          return h("div", { class: "leksikal-baris" }, [
            h("span", { class: "tok", title: d[0], teks: d[0] }),
            h("span", { class: "nil", teks: (d[1] > 0 ? "+" : "") + d[1].toFixed(2) }),
            h("span", { class: "leksikal-rel" }, h("i", {
              class: d[1] > 0 ? "p" : "n",
              style: "width:" + Math.max(3, (Math.abs(d[1]) / maksL) * 100) + "%"
            }))
          ]);
        })),
        h("p", { class: "tahap-catatan", style: "margin-top:12px", teks: pihak +
          " Rata-rata penyokong " + dukung.sokong.toFixed(2) + " dari " + dukung.sokongAwal +
          " kata, penentang " + dukung.lawan.toFixed(2) + " dari " + dukung.lawanAwal + " kata." })
      ]));
    }


    /* 2. Konteks percakapan */
    var konteks = ambil(b, "konteks");
    var induk = ambil(b, "induk");
    if (konteks || induk) {
      isi.appendChild(h("div", { class: "bagian-laci" }, [
        h("h3", { teks: "Konteks percakapan" }),
        konteks ? h("div", { class: "konteks" }, [h("span", { class: "nama", teks: sumber === "threads" ? "Unggahan induk" : "Judul video" }), konteks]) : null,
        induk ? h("div", { class: "konteks", style: "margin-top:8px" }, [h("span", { class: "nama", teks: "Teks yang dibalas" }), induk]) : null
      ]));
    }

    /* 3. Label model */
    isi.appendChild(h("div", { class: "bagian-laci" }, [
      h("h3", { teks: "Label model" }),
      h("div", { class: "petak-kunci" }, [
        h("div", null, [h("div", { class: "k", teks: "Sentimen" }), h("div", { class: "v" }, penanda(label === "tidak_relevan" ? "tidak_relevan" : (label || "netral2"), KELAS_HURUF[label] || label || "belum"))]),
        h("div", null, [h("div", { class: "k", teks: "Keyakinan" }), h("div", { class: "v mono", teks: typeof yak === "number" ? yak.toFixed(2) : "-" })]),
        h("div", null, [h("div", { class: "k", teks: "Tipe teks" }), h("div", { class: "v", teks: ambil(b, "tipe") || "-" })]),
        h("div", null, [h("div", { class: "k", teks: "Aspek" }), h("div", { class: "v", teks: (ambil(b, "aspek") || "-").split("|").join(", ") })]),
        h("div", null, [h("div", { class: "k", teks: "Bahasa" }), h("div", { class: "v", teks: ambil(b, "bahasa") || "-" })]),
        h("div", null, [h("div", { class: "k", teks: "Ember" }), h("div", { class: "v", teks: ambil(b, "ember") || "belum teranotasi" })])
      ]),
      h("div", { class: "kutipan", style: "margin-top:12px" }, [
        h("div", null, [h("span", { class: "label", teks: "Bukti" }), h("p", { class: "isi", teks: bukti || "tidak diisi" })]),
        h("div", null, [h("span", { class: "label", teks: "Alasan" }), h("p", { class: "isi", teks: ambil(b, "alasan") || "tidak diisi" })])
      ])
    ]));

    /* 4. Temuan audit */
    var audit = (D.audit_per_baris || {})[uid];
    if (audit) {
      isi.appendChild(h("div", { class: "bagian-laci" }, [
        h("h3", { teks: "Temuan audit" }),
        h("p", { class: "ket", style: "margin-bottom:10px", teks: "Keparahan " + audit.keparahan + ". " + (ARTI_KEPARAHAN[audit.keparahan] || "") }),
        h("div", { class: "kutipan" }, (audit.temuan || []).map(function (t) {
          return h("div", null, [
            h("span", { class: "label", teks: t }),
            h("p", { class: "isi", teks: ARTI_TEMUAN[t] || "Temuan ini belum punya keterangan." })
          ]);
        }))
      ]));
    }

    /* 5. Penilaian manusia dan perbandingan sistem */
    var gold = (D.gold_per_baris || {})[uid];
    if (gold) {
      var kepala = [["Penilai", ""], ["Label", ""]];
      var barisan = [];
      if (gold.manusia) barisan.push({ sel: ["Manusia (gold ronde pertama)", penanda(gold.manusia, KELAS_HURUF[gold.manusia] || gold.manusia)], kelas: "sorot" });
      if (gold.asisten) barisan.push({ sel: ["Penilai kedua (asisten)", penanda(gold.asisten, KELAS_HURUF[gold.asisten] || gold.asisten)] });
      if (gold.ronde2_anotator2) barisan.push({ sel: ["Anotator kedua ronde dua", penanda(gold.ronde2_anotator2, KELAS_HURUF[gold.ronde2_anotator2] || gold.ronde2_anotator2)] });
      if (gold.ronde2_sementara) barisan.push({ sel: ["Usulan model ronde dua", penanda(gold.ronde2_sementara, KELAS_HURUF[gold.ronde2_sementara] || gold.ronde2_sementara)] });
      [["v2", "Skema anotasi awal"], ["v4", "Skema anotasi perbaikan"], ["v5", "Skema anotasi bernalar"], ["deepseek", "Anotator keluarga lain"]]
        .forEach(function (s) {
          if (gold[s[0]]) barisan.push({ sel: [s[1], penanda(gold[s[0]], KELAS_HURUF[gold[s[0]]] || gold[s[0]])] });
        });

      var tambahanLaci = [];
      if (gold.catatan) tambahanLaci.push(h("p", { class: "ket", style: "margin-top:8px", teks: "Catatan manusia: " + gold.catatan }));
      if (gold.alasan_asisten) tambahanLaci.push(h("p", { class: "ket", style: "margin-top:6px", teks: "Alasan penilai kedua: " + gold.alasan_asisten }));
      if (gold.konteks_gold) tambahanLaci.push(h("p", { class: "ket", style: "margin-top:6px", teks: "Konteks pada lembar anotasi: " + gold.konteks_gold }));

      tambahanLaci.unshift(tabel(kepala, barisan));
      isi.appendChild(h("div", { class: "bagian-laci" }, [
        h("h3", { teks: "Penilaian manusia dan perbandingan" })
      ].concat(tambahanLaci)));
    }

    /* 6. Penjelasan model */
    var lime = (((D.xai || {}).lime || {}).per_uid || {})[uid];
    var atensiPeta = D.xai_uid_atensi || {};
    var atensi = atensiPeta[uid];
    var bertviz = (D.xai_uid_bertviz || {})[uid];
    if (lime || atensi || bertviz) {
      var isiXai = [];
      if (lime) {
        isiXai.push(h("p", { class: "ket", teks: "LIME mengubah masukan secara lokal lalu mengamati akibatnya pada keluaran model. Batang ke kanan mendorong kelas tersebut, ke kiri menahannya." }));
        Object.keys(lime.kelas).forEach(function (kelas) {
          isiXai.push(h("h4", { style: "margin:14px 0 6px;font-size:12.5px", teks: "Kelas " + (KELAS_HURUF[kelas] || kelas) + " terhadap kelas lainnya" }));
          isiXai.push(batangToken(lime.kelas[kelas], { batas: 8 }));
        });
        isiXai.push(h("p", { class: "ket", style: "margin-top:10px", teks: "Dugaan model " + lime.dugaan + " dengan keyakinan " + (lime.yak || 0).toFixed(4) + " pada baris ini." }));
      }
      if (atensi) {
        isiXai.push(h("h4", { style: "margin:16px 0 6px;font-size:12.5px", teks: "Token terpenting menurut atensi" }));
        isiXai.push(batangToken(atensi.token.map(function (t) { return [t[0], t[1]]; }), { batas: 10, warna: "aksen" }));
        isiXai.push(h("p", { class: "ket", style: "margin-top:8px", teks: "Bobot atensi bukan kausalitas. Kepala [CLS] dan [SEP] rutin muncul di puncak karena cara normalisasi, bukan karena model memutuskan dari situ." }));
      }
      if (bertviz) {
        var berkasBertviz = "aset/bertviz/" + bertviz.berkas_png;
        isiXai.push(h("h4", { style: "margin:16px 0 6px;font-size:12.5px", teks: "Kisi kepala atensi (BertViz)" }));
        isiXai.push(h("a", { href: berkasBertviz, target: "_blank", rel: "noopener", style: "display:inline-block" },
          h("img", { src: berkasBertviz, alt: "Kisi kepala atensi untuk baris ini", style: "width:100%;border:1px solid var(--garis);border-radius:var(--r-kendali)" })));
        isiXai.push(h("p", { class: "ket", style: "margin-top:8px", teks: "Tampilan ini memperlihatkan bahwa kepala atensi berspesialisasi. Kata yang tampak penting hanya penting di sebagian kepala, bukan di seluruh model." }));
      }
      isi.appendChild(h("div", { class: "bagian-laci" }, [h("h3", { teks: "Penjelasan model (XAI)" })].concat(isiXai)));
    }

    /* 7. Asal dan tautan */
    var tautan = ambil(b, "tautan");
    var bintang = ambil(b, "bintang");
    isi.appendChild(h("div", { class: "bagian-laci" }, [
      h("h3", { teks: "Asal rekaman" }),
      h("div", { class: "petak-kunci" }, [
        h("div", null, [h("div", { class: "k", teks: "Waktu" }), h("div", { class: "v mono", teks: ambil(b, "waktu") || "-" })]),
        h("div", null, [h("div", { class: "k", teks: "Bintang ulasan" }), h("div", { class: "v mono", teks: bintang === null || bintang === undefined ? "tidak berlaku" : String(bintang) })]),
        h("div", { style: "grid-column:1/-1" }, [
          h("div", { class: "k", teks: "Tautan sumber" }),
          tautan ? h("a", { href: tautan, target: "_blank", rel: "noopener", class: "v" }, [
            ikon("luar"), " buka sumber"
          ]) : h("div", { class: "v", teks: "tidak tersedia" })
        ])
      ])
    ]));

    laci.hidden = false;
    tabir.hidden = false;
    requestAnimationFrame(function () {
      laci.classList.add("tampak");
      tabir.classList.add("tampak");
    });
    $("#tombol-tutup").focus();
  }

  function tutupLaci() {
    var laci = $("#laci"), tabir = $("#tabir");
    laci.classList.remove("tampak");
    tabir.classList.remove("tampak");
    window.setTimeout(function () { laci.hidden = true; tabir.hidden = true; }, 220);
    terpilih = null;
    Array.prototype.forEach.call(document.querySelectorAll(".baris-label"), function (b) {
      b.removeAttribute("aria-current");
    });
  }

  /* ------------------------------------------------------------------------
     Deret bulanan dan silang tabulasi
     ------------------------------------------------------------------------
     Deret digambar sebagai kelipatan kecil, satu panel per sumber, masing-masing
     dengan skala sendiri. Skala bersama sengaja dihindari: YouTube memuat enam
     ribu baris sementara Threads dua ratus, sehingga pada skala bersama dua
     sumber terakhir akan rata menjadi garis nol yang tidak terbaca.
     ------------------------------------------------------------------------ */
  function gambarBulanan() {
    var der = (D.deret || {}).bulanan;
    if (!der || !der.bulan || !der.bulan.length) return h("div");

    var panel = der.sumber.map(function (sumber) {
      var nilai = der.bulan.map(function (b) {
        return ((der.nilai[b] || {})[sumber]) || 0;
      });
      var puncak = Math.max.apply(null, nilai.concat([1]));
      var w = 150, ht = 96, bawah = 20, atas = 18, kiri = 4, kanan = 4;
      var lebarSel = (w - kiri - kanan) / der.bulan.length;

      var anak = [];
      der.bulan.forEach(function (b, i) {
        var v = nilai[i];
        var tinggi = v ? Math.max(2, (v / puncak) * (ht - bawah - atas)) : 0;
        var x = kiri + i * lebarSel + lebarSel * 0.16;
        var lebar = lebarSel * 0.68;
        if (tinggi) {
          anak.push(h("rect", { class: "semua", x: x, y: ht - bawah - tinggi, width: lebar, height: tinggi, rx: 2 }));
        } else {
          anak.push(h("line", { class: "kisi", x1: x, x2: x + lebar, y1: ht - bawah, y2: ht - bawah }));
        }
        anak.push(h("text", { class: "tanda", x: x + lebar / 2, y: ht - bawah - tinggi - 4, "text-anchor": "middle", text: angka(v) }));
        anak.push(h("text", { class: "tanda", x: x + lebar / 2, y: ht - 6, "text-anchor": "middle", text: b.slice(5) }));
      });
      anak.push(h("line", { class: "sumbu", x1: kiri, x2: w - kanan, y1: ht - bawah, y2: ht - bawah }));

      return h("figure", { class: "gambar-kartu" }, [
        h("div", { style: "padding:12px 14px 0" }, [
          h("b", { style: "font-size:13px", teks: SUMBER[sumber] || sumber }),
          h("div", { class: "ket", style: "font-size:11.5px;color:var(--tinta-samar)", teks: "tertinggi " + angka(puncak) + " baris" })
        ]),
        h("svg", { class: "bulanan", viewBox: "0 0 " + w + " " + ht, role: "img",
                   "aria-label": "Jumlah baris per bulan untuk " + (SUMBER[sumber] || sumber) }, anak)
      ]);
    });

    return blok("Sebaran waktu korpus", "Jumlah baris tiap bulan menurut sumbernya. Setiap panel memakai skala sendiri, jadi tinggi batang antar panel tidak dapat dibandingkan; angkanya tercetak di atas tiap batang.",
      h("div", { class: "petak-gambar" }, panel));
  }

  function gambarKomposisi(judul, keterangan, data, ubahNama) {
    var kunci = Object.keys(data || {});
    if (!kunci.length) return h("div");
    var kelas = ["negatif", "netral", "positif"];
    return blok(judul, keterangan,
      h("div", { class: "komposisi" }, kunci.map(function (k) {
        var isi = data[k] || {};
        var jumlah = kelas.reduce(function (a, c) { return a + (isi[c] || 0); }, 0) || 1;
        return h("div", { class: "komposisi-baris" }, [
          h("span", { class: "nama", title: k, teks: ubahNama ? ubahNama(k) : k }),
          h("div", { class: "komposisi-rel" }, kelas.map(function (c) {
            var v = isi[c] || 0;
            if (!v) return null;
            return h("i", {
              class: c,
              style: "width:" + ((v / jumlah) * 100) + "%",
              title: KELAS_HURUF[c] + ": " + angka(v)
            });
          })),
          h("span", { class: "komposisi-nilai", teks: angka(jumlah) })
        ]);
      })));
  }

  function gambarKalibrasi() {
    var bak = (D.deret || {}).kalibrasi || [];
    if (!bak.length || !bak.some(function (b) { return b.n; })) return h("div");
    var terpakai = bak.filter(function (b) { return b.n > 0; });
    if (!terpakai.length) return h("div");

    /* Kalibrasi yang baik berarti ketepatan naik seiring keyakinan. Temuan yang
       dilaporkan di sini bukan sekadar gambarnya, melainkan ada atau tidaknya
       kenaikan itu, sehingga pembaca tidak perlu menyimpulkannya sendiri. */
    var turun = null;
    for (var i = 1; i < terpakai.length; i++) {
      if ((terpakai[i].tepat || 0) < (terpakai[i - 1].tepat || 0)) {
        turun = { bawah: terpakai[i - 1], atas: terpakai[i] };
        break;
      }
    }

    var catatan = turun
      ? "Ketepatannya tidak naik seiring keyakinan. Selang " + turun.atas.batas +
        " justru lebih rendah (" + persen(turun.atas.tepat, 1) + " dari " + angka(turun.atas.n) +
        " baris) daripada selang " + turun.bawah.batas + " (" + persen(turun.bawah.tepat, 1) +
        " dari " + angka(turun.bawah.n) + " baris). Karena itu keyakinan model tidak dapat dipakai sebagai jaminan kebenaran."
      : "Ketepatannya naik seiring keyakinan pada rentang yang terisi. Jumlah barisnya kecil, sehingga ini petunjuk arah, bukan ukuran tetap.";

    return blok("Apakah keyakinan model dapat dipercaya",
      "Diuji pada baris gold yang punya penilaian manusia. Bila keyakinan terkalibrasi, batang akan berakhir tepat di tengah selang keyakinannya dan bergerak naik dari kiri ke kanan. Angka di kanan adalah ketepatan pada selang itu beserta jumlah barisnya.",
      h("div", null, [
        h("div", { class: "kalibrasi" }, terpakai.map(function (b) {
          return h("div", { class: "kalibrasi-baris" }, [
            h("span", { class: "mono", style: "font-size:12px", teks: b.batas }),
            h("span", { class: "kalibrasi-rel" }, h("i", {
              style: "width:" + Math.max(2, (b.tepat || 0) * 100) + "%"
            })),
            h("span", { class: "kalibrasi-nilai", teks: persen(b.tepat, 1) + " dari " + angka(b.n) })
          ]);
        })),
        h("p", { class: "tahap-catatan", style: "margin-top:14px", teks: catatan })
      ]));
  }

  function tabelKappa() {
    var k = D.kappa;
    if (!k || !k.pasangan || !k.pasangan.length) return h("div");

    var baris = k.pasangan.map(function (p) {
      var s = p.semua_kelas || {};
      var se = p.sentimen || {};
      var rel = p.relevansi || {};
      return {
        kelas: p.id === "model_vs_anotator2" ? "sorot" : null,
        sel: [
          h("div", null, [h("div", { style: "font-size:13px", teks: p.nama }),
                          h("div", { class: "kecil", style: "font-family:var(--mono)", teks: p.id })]),
          angka(p.irisan),
          h("span", { class: "mono", teks: angka(s.kappa, 4) }),
          h("span", { class: "tafsir", teks: s.tafsir || "" }),
          angka(se.kappa, 4),
          angka(rel.kappa, 4)
        ]
      };
    });

    var isi = [tabel(
      [["Pasangan penilai", ""], ["Baris", "angka"], ["Kappa semua kelas", "angka"], ["Tafsir", ""],
       ["Kappa sentimen", "angka"], ["Kappa relevansi", "angka"]],
      baris,
      { catatan: k.catatan }
    )];

    var penting = k.pasangan.filter(function (p) { return p.id === "model_vs_anotator2"; })[0];
    if (penting && penting.beda_terbanyak && penting.beda_terbanyak.length) {
      isi.push(h("div", { class: "grid-dua", style: "margin-top:18px" }, [
        h("div", { class: "kotak" }, [
          h("h4", { teks: "Di mana kedua penilai paling sering berbeda" }),
          h("div", { class: "leksikal" }, penting.beda_terbanyak.map(function (d) {
            return h("div", { class: "leksikal-baris" }, [
              h("span", { class: "tok", teks: (KELAS_HURUF[d.a] || d.a) + " jadi " + (KELAS_HURUF[d.b] || d.b) }),
              h("span", { class: "nil", teks: String(d.jumlah) }),
              h("span", { class: "leksikal-rel" }, h("i", {
                class: "n", style: "width:" + Math.round((d.jumlah / penting.beda_terbanyak[0].jumlah) * 100) + "%"
              }))
            ]);
          }))
        ]),
        h("div", { class: "kotak" }, [
          h("h4", { teks: "Cara membacanya" }),
          h("p", { teks: penting.catatan }),
          h("p", { style: "margin-top:10px", teks: "Selisihnya terpusat pada satu hal: penilai kedua menandai " +
            angka((penting.semua_kelas.sebaran_b || {}).netral || 0) + " baris sebagai netral, sedangkan model hanya " +
            angka((penting.semua_kelas.sebaran_a || {}).netral || 0) + ". Pada putusan relevan, keduanya sepakat penuh." })
        ])
      ]));
    }
    return blok("Kesepakatan antar penilai",
      "Cohen's kappa mengoreksi kesepakatan yang terjadi karena kebetulan, sehingga angkanya selalu lebih rendah daripada kesepakatan mentah. Skala tafsirnya: di bawah 0,21 sedikit, 0,21 sampai 0,40 cukup, 0,41 sampai 0,60 sedang, 0,61 sampai 0,80 kuat.",
      h("div", null, isi));
  }

  /* ------------------------------------------------------------------------
     Panel 4: Mutu label
     ------------------------------------------------------------------------ */
  function gambarMutu() {
    var p = $("#panel-mutu");
    kosongkan(p);
    var a = D.audit || {};

    p.appendChild(h("div", { class: "judul-panel" }, [
      h("h2", { id: "judul-mutu", teks: "Mutu label" }),
      h("p", { class: "keterangan-panel", teks: "Pemindaian dijalankan pada setiap baris, bukan pada contoh acak, karena cacat label yang jarang justru yang paling berbahaya." })
    ]));

    p.appendChild(h("div", { class: "deret-ukuran" }, [
      h("div", { class: "ukuran" }, [h("div", { class: "nama", teks: "Baris dipindai" }), h("div", { class: "nilai", teks: angka(a.total) }), h("div", { class: "ket", teks: "seluruh baris berlabel" })]),
      h("div", { class: "ukuran" }, [h("div", { class: "nama", teks: "Baris bertanda" }), h("div", { class: "nilai", teks: angka(a.bertanda) }), h("div", { class: "ket", teks: persen(a.porsi_bertanda) + " dari seluruh baris" })]),
      h("div", { class: "ukuran" }, [h("div", { class: "nama", teks: "Cacat kritis" }), h("div", { class: "nilai", teks: angka((a.keparahan || {}).kritis || 0) }), h("div", { class: "ket", teks: "tidak ada yang menghalangi pemakaian" })]),
      h("div", { class: "ukuran" }, [h("div", { class: "nama", teks: "Bukti berdasar teks" }), h("div", { class: "nilai", teks: angka(a.bukti_berdasar) }), h("div", { class: "ket", teks: persen(a.porsi_bukti_berdasar, 2) + " dari baris berlabel" })]),
      h("div", { class: "ukuran" }, [h("div", { class: "nama", teks: "Teks identik, sentimen berbeda" }), h("div", { class: "nilai", teks: angka(a.teks_identik_beda_sentimen) }), h("div", { class: "ket", teks: "tidak ada label yang saling bertentangan" })]),
      h("div", { class: "ukuran" }, [h("div", { class: "nama", teks: "Belum teranotasi" }), h("div", { class: "nilai", teks: angka((a.tanpa_anotasi || []).length) }), h("div", { class: "ket", teks: "teks di bawah ambang panjang" })])
    ]));

    var keparahan = a.keparahan || {};
    var temuan = a.temuan || {};
    var urutTemuan = Object.keys(temuan).sort(function (x, y) { return temuan[y] - temuan[x]; });

    p.appendChild(blok("Temuan audit menurut jenisnya", "Setiap jenis temuan disertai artinya, supaya angkanya dapat ditafsirkan tanpa membuka kode.",
      h("div", { class: "grid-dua" }, [
        h("div", { class: "bungkus-tabel" }, tabel(
          [["Keparahan", ""], ["Jumlah", "angka"], ["Artinya", ""]],
          ["kritis", "tinggi", "sedang", "rendah"].map(function (k) {
            return {
              kelas: k === "kritis" ? "sorot" : null,
              sel: [h("span", { class: "mono", teks: k }), angka(keparahan[k] || 0), h("span", { class: "kecil", teks: ARTI_KEPARAHAN[k] })]
            };
          })
        )),
        h("div", { class: "bungkus-tabel" }, tabel(
          [["Jenis temuan", ""], ["Jumlah", "angka"], ["Artinya", ""]],
          urutTemuan.map(function (t) {
            return { sel: [h("span", { class: "mono", teks: t }), angka(temuan[t]), h("span", { class: "kecil", teks: ARTI_TEMUAN[t] || "" })] };
          })
        ))
      ])));

    var key = a.keyakinan || {};
    var deretKey = [
      { nama: "Rata-rata", nilai: key.rata },
      { nama: "Median", nilai: key.median },
      { nama: "Terendah", nilai: key.min }
    ];
    p.appendChild(blok("Keyakinan model tidak terkalibrasi", "Jangan memakai nilai keyakinan mentah sebagai ambang penyaringan. Sebaran di bawah ini yang menjadi alasannya.",
      h("div", { class: "grid-dua" }, [
        h("div", { class: "kotak" }, [
          h("h4", { teks: "Sebaran keyakinan" }),
          h("div", { class: "petak-kunci" }, deretKey.map(function (d) {
            return h("div", null, [h("div", { class: "k", teks: d.nama }), h("div", { class: "v mono", teks: typeof d.nilai === "number" ? d.nilai.toFixed(4) : "-" })]);
          }).concat([
            h("div", null, [h("div", { class: "k", teks: "Bernilai mutlak 1,0" }), h("div", { class: "v mono", teks: angka(key.mutlak_1_0) })]),
            h("div", null, [h("div", { class: "k", teks: "Di bawah 0,6" }), h("div", { class: "v mono", teks: angka(key.di_bawah_0_6) })])
          ]))
        ]),
        h("div", { class: "kotak" }, [
          h("h4", { teks: "Kesalahan berupa bias, bukan derau" }),
          h("p", { teks: "Pada tiga pengambilan dengan suhu 0,7, model menjawab sama persis untuk 90 dari 92 baris, termasuk baris yang salah. Karena itu pemungutan suara tidak menyaring kesalahan apa pun, dan aturan yang mensyaratkan label konsisten tidak menolong." })
        ])
      ])));

    var bintang = a.bintang || {};
    var kontradiksi = [
      ["5bintang_negatif", "Bintang lima berisi negatif"],
      ["1bintang_positif", "Bintang satu berisi positif"],
      ["3bintang_negatif", "Bintang tiga berisi negatif"],
      ["5bintang_positif", "Bintang lima berisi positif"],
      ["1bintang_negatif", "Bintang satu berisi negatif"]
    ].filter(function (k) { return bintang[k[0]] !== undefined; });

    p.appendChild(blok("Bintang Google Play tidak dapat dipakai sebagai acuan", "Pemeriksaan manual menunjukkan label teksnya justru yang benar, bintangnya yang tidak dapat dipercaya.",
      tabel(
        [["Pasangan bintang dan label", ""], ["Jumlah", "angka"]],
        kontradiksi.map(function (k) { return { sel: [k[1], angka(bintang[k[0]])], kelas: k[0].indexOf("5bintang_negatif") === 0 || k[0].indexOf("1bintang_positif") === 0 ? "sorot" : null }; })
      )));

    var der = D.deret || {};
    p.appendChild(gambarKomposisi("Sentimen menurut sumber data",
      "Setiap batang mewakili seluruh baris sumber itu, dibagi menurut kelas sentimennya. Angka di kanan adalah jumlah barisnya.",
      der.sumber_sentimen, function (k) { return SUMBER[k] || k; }));

    p.appendChild(gambarKomposisi("Sentimen menurut aspek",
      "Satu baris dapat memuat lebih dari satu aspek, sehingga jumlah pada kolom ini melebihi jumlah baris korpus.",
      der.aspek_sentimen));

    p.appendChild(gambarKomposisi("Sentimen menurut tipe teks",
      "Tipe teks ditetapkan anotator bersama sentimennya. Sapaan dan pertanyaan seharusnya tidak memuat penilaian, sehingga sebaran pada keduanya menarik untuk diperiksa.",
      der.tipe_sentimen));

    p.appendChild(gambarKalibrasi());

    var panjang = der.panjang_kelas || {};
    var kunciPanjang = Object.keys(panjang).filter(function (k) { return panjang[k].n; });
    if (kunciPanjang.length) {
      p.appendChild(blok("Panjang teks menurut kelas", "Diukur pada teks yang sudah dibersihkan. Kelas netral pada korpus ini berisi teks yang jauh lebih pendek, dan itulah salah satu sebabnya kelas itu sulit dikenali.",
        tabel(
          [["Kelas", ""], ["P25", "angka"], ["Median", "angka"], ["P75", "angka"], ["Rata-rata", "angka"], ["Terpanjang", "angka"]],
          kunciPanjang.map(function (k) {
            var d = panjang[k];
            return { sel: [penanda(k, KELAS_HURUF[k] || k), angka(d.p25), angka(d.median), angka(d.p75), angka(d.rata, 1), angka(d.maks)] };
          })
        )));
    }
  }

  /* ------------------------------------------------------------------------
     Panel 5: Model
     ------------------------------------------------------------------------
     Blok uji model adalah satu-satunya bagian halaman yang memanggil jaringan.
     Alamatnya dibaca dari konfigurasi.js yang ditulis terbitkan_model.py. Bila
     berkas itu kosong atau endpoint tidak terjangkau, hanya blok ini yang
     menampilkan keadaan galat; seluruh halaman tetap bekerja luring.
     ------------------------------------------------------------------------ */
  var KONFIG = window.DSS_KONFIG || {};
  var CONTOH_UJI = [
    "aplikasi fasih sering error waktu submit data",
    "petugas sensus datang kerumah saya sangat sopan dan sabar",
    "kapan sensus ekonomi 2026 dimulai ya"
  ];

  function batangPeluang(peluang, terpilih) {
    var urut = KELAS_SENTIMEN.slice().sort(function (a, b) {
      return (peluang[b] || 0) - (peluang[a] || 0);
    });
    var maks = Math.max.apply(null, KELAS_SENTIMEN.map(function (k) { return peluang[k] || 0; }).concat([0.001]));
    return h("div", { class: "peluang" }, urut.map(function (k) {
      var v = peluang[k] || 0;
      return h("div", { class: "peluang-baris" + (k === terpilih ? " unggul" : "") }, [
        penanda(k, KELAS_HURUF[k] || k),
        h("span", { class: "nilai", teks: v.toFixed(4) }),
        h("span", { class: "peluang-rel" }, h("i", {
          class: "b-" + k,
          style: "width:" + Math.max(2, (v / maks) * 100) + "%;background:var(--" + (k === "negatif" ? "neg" : k === "netral" ? "net" : "pos") + ")"
        }))
      ]);
    }));
  }

  function gambarUjiModel() {
    var endpoint = (KONFIG.endpoint || "").replace(/\/+$/, "");
    var kotak = h("div", { class: "uji-kotak", hidden: true });
    var hitung = h("span", { class: "uji-hitung", teks: "" });
    var tombol = h("button", {
      class: "tombol tombol-utama", type: "button",
      onclick: function () { kirim(); }
    }, "Analisis");

    var input = h("textarea", {
      class: "uji-masukan", id: "uji-teks", rows: 3,
      placeholder: "Tempel atau tulis teks berbahasa Indonesia tentang Sensus Ekonomi 2026 atau aplikasi Fasih BPS",
      onkeydown: function (e) {
        if ((e.ctrlKey || e.metaKey) && e.key === "Enter") { e.preventDefault(); kirim(); }
      }
    });

    var contoh = h("div", { class: "uji-contoh" }, [h("span", { class: "nama", teks: "Contoh:" })].concat(
      CONTOH_UJI.map(function (t) {
        return h("button", { type: "button", title: t, onclick: function () { input.value = t; kirim(); } }, t);
      })));

    function tampilkan(isi) {
      kosongkan(kotak);
      kotak.hidden = false;
      kotak.appendChild(isi);
    }

    function tampilkanGalat(judul, rinci) {
      tampilkan(h("div", { class: "uji-galat" }, [
        h("b", { teks: judul }),
        h("span", { teks: rinci })
      ]));
    }

    function kirim() {
      var teks = (input.value || "").trim();
      if (!teks) {
        tampilkanGalat("Teks masih kosong.", "Tulis atau tempel teks lebih dahulu, lalu tekan Analisis.");
        return;
      }
      if (!endpoint) {
        tampilkanGalat("Endpoint belum diterbitkan.",
          "Jalankan py -3.13 terbitkan_model.py, lalu bangun ulang halaman dengan py -3.13 buat_web_dss.py.");
        return;
      }

      tombol.disabled = true;
      hitung.textContent = "mengirim";
      tampilkan(h("div", { class: "kerangka" }, [
        h("span"), h("span"), h("span"), h("span")
      ]));

      /* Permintaan pertama setelah wadah Modal tidur harus memuat bobot model,
         sehingga batas waktunya dibuat longgar dan keadaannya diberitahukan. */
      var pengawas = typeof AbortController !== "undefined" ? new AbortController() : null;
      var jam = pengawas ? window.setTimeout(function () { pengawas.abort(); }, 180000) : null;

      var mulai = Date.now();
      fetch(endpoint + "/analisis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ teks: teks, atas: 20 }),
        signal: pengawas ? pengawas.signal : undefined
      }).then(function (r) {
        return r.text().then(function (teksBadan) {
          if (!r.ok) {
            var pesan = teksBadan;
            try { pesan = JSON.parse(teksBadan).detail || teksBadan; } catch (e) { /* dibiarkan */ }
            throw new Error("HTTP " + r.status + ": " + String(pesan).slice(0, 200));
          }
          return JSON.parse(teksBadan);
        });
      }).then(function (hasil) {
        if (jam) window.clearTimeout(jam);
        var detik = ((Date.now() - mulai) / 1000).toFixed(1).replace(".", ",");
        var isi = [];

        isi.push(h("div", { class: "petak-kunci" }, [
          h("div", null, [h("div", { class: "k" , teks: "Dugaan model" }), h("div", { class: "v" }, penanda(hasil.prediksi, KELAS_HURUF[hasil.prediksi] || hasil.prediksi))]),
          h("div", null, [h("div", { class: "k", teks: "Panjang token" }), h("div", { class: "v mono", teks: angka(hasil.jumlah_token) + (hasil.terpotong ? " dari " + angka(hasil.panjang_penuh) : "") })]),
          h("div", null, [h("div", { class: "k", teks: "Waktu jawab" }), h("div", { class: "v mono", teks: detik + " detik" })]),
          h("div", null, [h("div", { class: "k", teks: "Model" }), h("div", { class: "v mono", teks: hasil.model || "-" })])
        ]));

        isi.push(batangPeluang(hasil.peluang || {}, hasil.prediksi));

        if (hasil.terpotong) {
          isi.push(h("p", { class: "tahap-catatan", teks: "Teks melebihi batas " + angka(hasil.jumlah_token) + " token yang dipakai saat pelatihan, sehingga sisa teksnya tidak ikut dinilai." }));
        }

        var peringkat = hasil.peringkat || {};
        if ((peringkat.atensi || []).length || (peringkat.gradien || []).length) {
          var grid = [];
          if ((peringkat.atensi || []).length) {
            grid.push(h("div", { class: "kotak" }, [
              h("h4", { teks: "Token terpenting menurut atensi" }),
              batangToken(peringkat.atensi.map(function (t) { return [t.teks, t.nilai]; }), { batas: 12, warna: "aksen" })
            ]));
          }
          if ((peringkat.gradien || []).length) {
            grid.push(h("div", { class: "kotak" }, [
              h("h4", { teks: "Token terpenting menurut gradien" }),
              batangToken(peringkat.gradien.map(function (t) { return [t.teks, t.nilai]; }), { batas: 12, warna: "aksen" })
            ]));
          }
          isi.push(h("div", { class: "grid-dua" }, grid));
          isi.push(h("p", { class: "ket", teks: "Dua ukuran ini dihitung dengan cara yang berbeda dan tidak selalu sepakat. Atensi menunjukkan ke mana model memandang; gradien menunjukkan seberapa peka logit kelas terpilih terhadap token itu. Keduanya korelasi, bukan sebab-akibat." }));
        }

        /* Catatan server selalu ditampilkan, tidak bisa disembunyikan, karena
           inilah batas tafsir yang paling mudah dilewatkan pembaca. */
        if (hasil.peringatan) {
          isi.push(h("p", { class: "uji-catatan" }, [h("b", { teks: "Batas tafsir. " }), hasil.peringatan]));
        }

        tampilkan(h("div", null, isi));
        hitung.textContent = "selesai dalam " + detik + " detik";
      }).catch(function (galat) {
        if (jam) window.clearTimeout(jam);
        var pesan = String(galat && galat.message ? galat.message : galat);
        if (galat && galat.name === "AbortError") {
          tampilkanGalat("Permintaan melewati batas waktu.",
            "Wadah Modal kemungkinan sedang memuat bobot model. Coba tekan Analisis sekali lagi.");
        } else if (pesan.indexOf("HTTP ") === 0) {
          tampilkanGalat("Endpoint menolak permintaan.", pesan);
        } else {
          tampilkanGalat("Endpoint tidak terjangkau.",
            "Periksa sambungan jaringan. Seluruh bagian lain halaman ini tetap bekerja tanpa sambungan. Sebab: " + pesan);
        }
        hitung.textContent = "gagal";
      }).then(function () {
        tombol.disabled = false;
      });
    }

    var kepala = h("div", { class: "uji-kepala" }, [
      h("h4", { teks: "Uji model secara langsung" }),
      h("span", { class: "capaian", teks: endpoint ? endpoint : "endpoint belum diterbitkan" })
    ]);

    if (!endpoint) {
      input.disabled = true;
      tombol.disabled = true;
    }

    return h("section", { class: "blok" }, [
      h("h3", { teks: "Coba sendiri" }),
      h("p", { class: "ket", teks: "Model yang sama dengan yang dilaporkan berjalan di Modal dan dapat diuji dengan teks apa pun. Permintaan pertama setelah beberapa menit menganggur akan lebih lambat karena wadahnya harus memuat bobot lebih dahulu." }),
      h("div", { class: "uji" }, [
        kepala,
        h("div", { class: "uji-badan" }, [
          contoh,
          input,
          h("div", { class: "uji-kendali" }, [tombol, hitung]),
          endpoint
            ? h("p", { class: "ket", teks: "Tekan Ctrl dan Enter untuk menganalisis tanpa memindahkan tangan dari papan ketik." })
            : h("p", { class: "tahap-catatan", teks: "Endpoint belum diterbitkan, sehingga kotak teksnya dimatikan. Jalankan py -3.13 terbitkan_model.py lebih dahulu, lalu bangun ulang halaman dengan py -3.13 buat_web_dss.py." }),
          kotak
        ])
      ])
    ]);
  }

  /* ------------------------------------------------------------------------
     Tabel metrik klasifikasi
     ------------------------------------------------------------------------
     Seluruh angkanya dihitung buat_web_dss.py dari matriks konfusi yang sama,
     lalu disajikan di sini tanpa diketik ulang. Karena itu angka pada matriks,
     rincian per kelas, dan ringkasan tidak mungkin saling bertentangan.
     ------------------------------------------------------------------------ */

  function selMatriks(nilai, maks, diagonal) {
    return h("td", {
      class: "sel" + (diagonal ? " diag" : "") + (nilai === 0 ? " nol" : ""),
      style: "--muat:" + Math.round((nilai / maks) * 55) + "%",
      teks: angka(nilai)
    });
  }

  function tabelMatriks(matriks, label, judul, keterangan) {
    if (!matriks || !matriks.length) return null;
    var maks = 1;
    matriks.forEach(function (r) {
      r.forEach(function (v) { if (v > maks) maks = v; });
    });

    var kepala = h("tr", null, [h("th", { class: "sudut", teks: "Sebenarnya ↓" })].concat(
      label.map(function (k) { return h("th", { teks: KELAS_HURUF[k] || k }); })
    ).concat([h("th", { teks: "Jumlah" })]));

    var badan = matriks.map(function (r, i) {
      var jumlah = r.reduce(function (a, b) { return a + b; }, 0);
      return h("tr", null, [h("td", { class: "nama", teks: KELAS_HURUF[label[i]] || label[i] })].concat(
        r.map(function (v, j) { return selMatriks(v, maks, i === j); })
      ).concat([h("td", { class: "jumlah", teks: angka(jumlah) })]));
    });

    var kaki = h("tr", null, [h("td", { class: "nama", teks: "Jumlah dugaan" })].concat(
      label.map(function (_, j) {
        return h("td", { class: "jumlah", teks: angka(matriks.reduce(function (a, r) { return a + r[j]; }, 0)) });
      })
    ).concat([h("td", { class: "jumlah", teks: angka(matriks.reduce(function (a, r) {
      return a + r.reduce(function (x, y) { return x + y; }, 0);
    }, 0)) })]));

    return h("figure", { class: "matriks-kartu" }, [
      h("figcaption", null, [
        h("b", { teks: judul }),
        keterangan || "Baris adalah kelas sebenarnya, kolom adalah kelas dugaan. Sel tebal pada diagonal adalah yang dinilai benar."
      ]),
      h("div", { class: "matriks-bungkus" }, h("table", { class: "matriks" }, [
        h("thead", null, kepala),
        h("tbody", null, badan),
        h("tfoot", null, kaki)
      ]))
    ]);
  }

  function tabelPerKelas(barisKelas) {
    if (!barisKelas || !barisKelas.length) return null;
    return tabel(
      [["Sistem", ""], ["Kelas", ""], ["Dukungan", "angka"], ["Diprediksi", "angka"],
       ["Presisi", "angka"], ["Recall", "angka"], ["F1", "angka"], ["Spesifisitas", "angka"]],
      barisKelas.map(function (b) {
        return {
          kelas: b.sorot ? "sorot" : null,
          sel: [
            h("span", { class: "mono kecil", teks: b.sistem || "" }),
            penanda(b.kelas, KELAS_HURUF[b.kelas] || b.kelas),
            angka(b.dukungan), angka(b.diprediksi),
            angka(b.presisi, 4), angka(b.recall, 4), angka(b.f1, 4), angka(b.spesifisitas, 4)
          ]
        };
      })
    );
  }

  function tabelRingkas(barisSistem, adaSelang) {
    var kepala = [["Sistem", ""], ["Akurasi", "angka"]];
    if (adaSelang) kepala.push(["Selang 95%", ""]);
    kepala = kepala.concat([
      ["Akurasi seimbang", "angka"], ["Presisi macro", "angka"], ["Recall macro", "angka"],
      ["F1 macro", "angka"], ["F1 terbobot", "angka"], ["MCC", "angka"], ["Kappa", "angka"]
    ]);
    return tabel(kepala, barisSistem.map(function (b) {
      var m = b.metrik;
      var sel = [
        b.nama,
        angka(m.akurasi, 4)
      ];
      if (adaSelang) {
        sel.push(h("span", { class: "mono kecil", teks: (b.ci || []).map(function (c) { return c.toFixed(3); }).join(" sampai ") }));
      }
      sel = sel.concat([
        angka(m.akurasi_seimbang, 4),
        angka(m.macro.presisi, 4), angka(m.macro.recall, 4), angka(m.macro.f1, 4),
        angka(m.terbobot.f1, 4), angka(m.mcc, 4), angka(m.kappa, 4)
      ]);
      return { kelas: b.sorot ? "sorot" : null, sel: sel };
    }));
  }

  function artiMetrik() {
    return h("div", { class: "kotak", style: "margin-top:14px" }, [
      h("h4", { teks: "Cara membaca metriknya" }),
      h("ul", null, [
        h("li", null, "Akurasi: bagian baris yang dinilai benar dari seluruh baris."),
        h("li", null, "Akurasi seimbang: rata-rata recall tiap kelas, sehingga tiap kelas berbobot sama tanpa memandang jumlah barisnya."),
        h("li", null, "Presisi: dari semua baris yang ditebak sebagai kelas itu, berapa bagian yang benar. Menjawab seberapa sering tebakan itu tepat."),
        h("li", null, "Recall: dari semua baris yang sebenarnya kelas itu, berapa bagian yang tertangkap. Menjawab seberapa banyak yang terlewat."),
        h("li", null, "F1: keseimbangan presisi dan recall pada satu kelas."),
        h("li", null, "Macro: rata-rata angka tiap kelas tanpa membobot jumlah barisnya. Inilah yang dipakai memilih model, karena kelas netral hanya 3,8% sehingga tidak boleh ditenggelamkan kelas mayoritas."),
        h("li", null, "Terbobot: rata-rata yang dibobot jumlah baris. Angkanya akan mendekati akurasi, dan itu sebabnya tidak dipakai memilih model."),
        h("li", null, "Spesifisitas: dari semua baris yang bukan kelas itu, berapa bagian yang benar ditolak."),
        h("li", null, "MCC: korelasi antara label sebenarnya dan label dugaan, bernilai 1 bila sempurna, 0 bila setara tebakan acak."),
        h("li", null, "Kappa: kesesuaian setelah peluang kebetulan dikeluarkan.")
      ])
    ]);
  }

  function gambarModel() {
    var p = $("#panel-model");
    kosongkan(p);
    var ab = D.ablasi || {};
    var meta = ab.meta || {};
    var skenario = ab.skenario || [];

    p.appendChild(h("div", { class: "judul-panel" }, [
      h("h2", { id: "judul-model", teks: "Model dan penjelasannya" }),
      h("p", { class: "keterangan-panel", teks: "Enam strategi adaptasi parameter dibandingkan pada pembagian data yang sama. Pemilihan model terbaik memakai F1 macro karena kelasnya sangat tidak seimbang." })
    ]));

    p.appendChild(gambarUjiModel());

    p.appendChild(h("div", { class: "kotak", style: "margin-bottom:22px" }, [
      h("h4", { teks: "Resep pelatihan" }),
      h("div", { class: "petak-kunci" }, [
        h("div", null, [h("div", { class: "k", teks: "Model dasar" }), h("div", { class: "v mono", teks: meta.model_name || "-" })]),
        h("div", null, [h("div", { class: "k", teks: "Data" }), h("div", { class: "v mono", teks: angka(meta.train_rows) + " latih / " + angka(meta.test_rows) + " uji" })]),
        h("div", null, [h("div", { class: "k", teks: "Epoch dan panjang token" }), h("div", { class: "v mono", teks: (meta.epochs || "-") + " epoch, " + (meta.max_len || "-") + " token" })]),
        h("div", null, [h("div", { class: "k", teks: "Presisi dan benih" }), h("div", { class: "v mono", teks: (meta.amp_dtype || "-") + ", benih " + (meta.seed || "-") })])
      ]),
      h("p", { class: "ket", style: "margin-top:14px", teks: "Pembagian data dilakukan berkelompok, bukan acak per baris, supaya komentar dari video yang sama tidak terbelah antara data latih dan data uji." })
    ]));

    p.appendChild(blok("Ringkasan metrik seluruh skenario",
      "Seluruh angka pada tabel ini mengukur kesesuaian terhadap anotator Gemma, bukan akurasi sebenarnya. Angka sebenarnya ada pada panel Perbandingan.",
      tabelRingkas(skenario.map(function (s) {
        return {
          nama: h("span", { class: "mono", teks: s.id }),
          metrik: s.metrik,
          sorot: s.id === "full_rdrop"
        };
      }).filter(function (b) { return b.metrik; }), false)));

    p.appendChild(blok("Biaya pelatihan",
      "Harga yang dibayar tiap skenario. R-Drop menuntut dua kali komputasi karena setiap teks dilewatkan dua kali dengan dropout berbeda.",
      tabel(
        [["Skenario", ""], ["Parameter dilatih", "angka"], ["Waktu (detik)", "angka"]],
        skenario.map(function (s) {
          return {
            kelas: s.id === "full_rdrop" ? "sorot" : null,
            sel: [
              h("span", { class: "mono", teks: s.id }),
              angka(s.params || 0) + (s.probe ? " (+ probe " + angka(s.probe) + ")" : ""),
              angka(s.detik, 1)
            ]
          };
        }),
        { catatan: "Baris yang disorot adalah model yang dipakai untuk penjelasan, dipilih karena F1 macro tertinggi meskipun akurasinya bukan yang tertinggi." }
      )));

    var barisKelas = [];
    skenario.forEach(function (s) {
      if (!s.metrik) return;
      s.metrik.per_kelas.forEach(function (c, i) {
        barisKelas.push({
          sistem: i === 0 ? s.id : "",
          kelas: c.kelas, dukungan: c.dukungan, diprediksi: c.diprediksi,
          presisi: c.presisi, recall: c.recall, f1: c.f1, spesifisitas: c.spesifisitas,
          sorot: s.id === "full_rdrop" && i === 0
        });
      });
    });
    p.appendChild(blok("Rincian per kelas",
      "Presisi, recall, dan F1 dihitung dari matriks yang sama seperti pada tabel ringkasan di atasnya. Dukungan adalah jumlah baris sebenarnya, diprediksi adalah jumlah baris yang ditebak sebagai kelas itu.",
      tabelPerKelas(barisKelas)));

    var adaMatriks = skenario.filter(function (s) { return s.metrik && s.kelas; });
    if (adaMatriks.length) {
      p.appendChild(blok("Matriks konfusi tiap skenario",
        "Warna sel mengikuti besarnya angka pada matriks yang sama, jadi tiap matriks dibandingkan dengan dirinya sendiri, bukan dengan matriks lain.",
        h("div", { class: "petak-matriks" }, adaMatriks.map(function (s) {
          return tabelMatriks(s.matriks, s.kelas, "Skenario " + s.id,
            "Akurasi " + angka(s.metrik.akurasi, 4) + ", F1 macro " + angka(s.metrik.macro.f1, 4) +
            ". Model ini " + (s.dilatih ? "dilatih" : "dipakai tanpa pelatihan") + ".");
        }))));
    }

    p.appendChild(artiMetrik());

    var rd = skenario.filter(function (s) { return s.id === "full_rdrop"; })[0];
    var full = skenario.filter(function (s) { return s.id === "full"; })[0];
    if (rd && rd.matriks && full && full.matriks) {
      var idxNetral = (rd.kelas || []).indexOf("netral");
      p.appendChild(blok("Pertukaran yang disengaja: R-Drop", "Netral hanya 219 baris (3,8%), sehingga model yang selalu menebak negatif pun sudah memperoleh akurasi 73,8%. Karena itu akurasi tinggi belum tentu berarti model menjadi lebih pintar.",
        h("div", { class: "grid-dua" }, [
          h("div", { class: "kotak" }, [
            h("h4", { teks: "Kelas netral yang benar" }),
            h("div", { class: "petak-kunci" }, [
              h("div", null, [h("div", { class: "k", teks: "Penyetelan penuh" }), h("div", { class: "v mono", teks: String(full.matriks[1][idxNetral]) + " dari " + String(full.matriks[1].reduce(function (a, b) { return a + b; }, 0)) })]),
              h("div", null, [h("div", { class: "k", teks: "Penyetelan penuh dengan R-Drop" }), h("div", { class: "v mono", teks: String(rd.matriks[1][idxNetral]) + " dari " + String(rd.matriks[1].reduce(function (a, b) { return a + b; }, 0)) })])
            ]),
            h("p", { class: "ket", style: "margin-top:12px", teks: "R-Drop menukar 2,8 poin akurasi demi kelas netral, dan itu sebabnya F1 macro naik dari " + angka(full.f1, 4) + " menjadi " + angka(rd.f1, 4) + "." })
          ]),
          h("div", { class: "kotak" }, [
            h("h4", { teks: "Cara kerjanya" }),
            h("p", { teks: "Model melewati dua kali dropout berbeda pada teks yang sama, lalu kedua jawabannya dituntut serupa." }),
            h("p", { class: "mono", style: "margin-top:10px;font-size:12px;background:var(--latar-turun);padding:10px 12px;border-radius:8px", teks: "L = 1/2 (CE(p1, y) + CE(p2, y)) + alpha x KL(p1 || p2)" }),
            h("p", { class: "ket", style: "margin-top:10px", teks: "Suku kedua itulah kuncinya. Kalau dropout pertama bilang negatif 95% dan kedua netral 60%, model dihukum berat. Satu-satunya cara lolos adalah melunakkan keyakinan, dan begitu lunak, kelas netral punya ruang untuk menang. Harganya dua kali komputasi." })
          ])
        ])));
    }

    p.appendChild(blok("Matriks konfusi model terbaik", "Gambar ini dihasilkan langsung oleh tahap pelatihan, bukan digambar ulang.",
      h("div", { class: "petak-gambar" }, [
        kartuGambar("aset/matriks_konfusi.png", "Matriks konfusi enam skenario", "Baris adalah kelas sebenarnya, kolom adalah kelas dugaan.")
      ])));

    var xai = D.xai || {};
    var atensi = (xai.atensi || {}).contoh || [];
    if (atensi.length) {
      p.appendChild(blok("Peta atensi", "Bobot perhatian model terhadap setiap token. Angka ini menunjukkan korelasi atensi, bukan bukti kausalitas.",
        h("div", { class: "petak-gambar" }, atensi.slice(0, 8).map(function (s, i) {
          return kartuGambar("aset/atensi/attention_" + (i + 1) + ".png",
            "Contoh " + (i + 1) + ": " + (s.pred || ""),
            (typeof s.confidence === "number" ? "Keyakinan " + s.confidence.toFixed(3) + ". " : "") + '"' + (s.text || "").slice(0, 90) + '"');
        }).concat([
          kartuGambar("aset/atensi/attention_matrix.png", "Pola atensi antar-lapisan", "Memperlihatkan lapisan mana yang paling banyak menahan perhatian.")
        ]))));
    }

    var limeTop = (xai.lime || {}).top || [];
    var perKelas = {};
    limeTop.forEach(function (t) {
      (perKelas[t.class] = perKelas[t.class] || []).push([t.token, parseFloat(t.mean_weight)]);
    });
    if (Object.keys(perKelas).length) {
      p.appendChild(blok("LIME: token yang paling menggerakkan keputusan", "Diurutkan dari rata-rata bobot terbesar pada seluruh teks yang dijelaskan. Nilai positif mendorong kelas tersebut, nilai negatif menahannya.",
        h("div", { class: "grid-dua" }, Object.keys(perKelas).map(function (kelas) {
          return h("div", { class: "kotak" }, [
            h("h4", null, penanda(kelas === "tidak_relevan" ? "tidak_relevan" : kelas, KELAS_HURUF[kelas] || kelas)),
            batangToken(perKelas[kelas].slice().sort(function (a, b) { return Math.abs(b[1]) - Math.abs(a[1]); }), { batas: 10 })
          ]);
        }).concat([
          kartuGambar("aset/lime/lime_top_tokens.png", "Ringkasan token terpenting", "Gambar asli dari tahap penjelasan model.")
        ]))));
    }

    var bert = (xai.bertviz || {}).contoh || [];
    if (bert.length) {
      p.appendChild(blok("Kisi kepala atensi (BertViz)", "Yang tidak dimiliki alat lain: seluruh kepala atensi pada satu lapisan sekaligus, sehingga terlihat bahwa kepala-kepala itu berspesialisasi.",
        h("div", { class: "petak-gambar" }, bert.map(function (c) {
          return kartuGambar("aset/bertviz/" + c.berkas_png, "Contoh " + c.indeks + ": " + c.prediksi,
            "Acuan " + c.label_acuan + ", keyakinan " + (c.keyakinan || 0).toFixed(4) + ". " + c.jumlah_token + " token.");
        }))));
    }
  }

  function kartuGambar(sumber, judul, keterangan) {
    return h("figure", { class: "gambar-kartu" }, [
      h("img", { src: sumber, alt: judul, loading: "lazy" }),
      h("figcaption", null, [h("b", { teks: judul }), keterangan])
    ]);
  }

  /* ------------------------------------------------------------------------
     Panel 6: Perbandingan
     ------------------------------------------------------------------------ */
  function gambarBanding() {
    var p = $("#panel-banding");
    kosongkan(p);
    var g = D.gold || {};
    var sistem = g.sistem || [];

    p.appendChild(h("div", { class: "judul-panel" }, [
      h("h2", { id: "judul-banding", teks: "Perbandingan dan pengukuran" }),
      h("p", { class: "keterangan-panel", teks: "Seratus baris gold dinilai manusia secara berlapis dan tersamar. Delapan baris dinilai tidak relevan sehingga metrik sentimen diukur pada " + angka(g.n) + " baris." })
    ]));

    p.appendChild(blok("Pengukuran terhadap gold manusia",
      "Selang 95% selebar 6 sampai 10 poin, sehingga selisih di bawah tiga poin belum dapat dipisahkan dari derau. Pengukuran ini hanya memakai baris yang dinilai manusia, bukan label model.",
      tabelRingkas(sistem.map(function (s) {
        return {
          nama: s.nama, metrik: s.metrik, ci: s.ci,
          sorot: s.id === "prediksi_eval_v2"
        };
      }).filter(function (b) { return b.metrik; }), true)));

    var barisKelasGold = [];
    sistem.forEach(function (s) {
      if (!s.metrik) return;
      s.metrik.per_kelas.forEach(function (c, i) {
        barisKelasGold.push({
          sistem: i === 0 ? s.nama : "",
          kelas: c.kelas, dukungan: c.dukungan, diprediksi: c.diprediksi,
          presisi: c.presisi, recall: c.recall, f1: c.f1, spesifisitas: c.spesifisitas,
          sorot: s.id === "prediksi_eval_v2" && i === 0
        });
      });
    });
    p.appendChild(blok("Rincian per kelas terhadap gold manusia",
      "Dukungan adalah jumlah baris gold pada kelas itu, seluruhnya " + angka(g.n) + " baris setelah delapan baris tidak relevan dikeluarkan. Kolom diprediksi menunjukkan berapa kali sistem menebak kelas itu.",
      tabelPerKelas(barisKelasGold)));

    var adaMatriksGold = sistem.filter(function (s) { return s.metrik && s.label_matriks; });
    if (adaMatriksGold.length) {
      var luar = (adaMatriksGold[0].di_luar || []).map(function (d) {
        return angka(d.jumlah) + " sebagai " + (KELAS_HURUF[d.dugaan] || d.dugaan);
      }).join(", ");
      p.appendChild(blok("Matriks konfusi terhadap gold manusia",
        "Barisnya penilaian manusia, kolomnya tebakan sistem. Kolom tidak relevan tidak dihitung sebagai tebakan pada kelas sentimen mana pun, tetapi barisnya tetap terhitung sebagai tidak dikenali dengan benar. Dari delapan baris gold yang manusia nilai tidak relevan, sistem ini menebak " + luar + ".",
        h("div", { class: "petak-matriks" }, adaMatriksGold.map(function (s) {
          return tabelMatriks(s.matriks, s.label_matriks, s.nama,
            "Akurasi " + angka(s.metrik.akurasi, 4) + ", F1 macro " + angka(s.metrik.macro.f1, 4) +
            ", kappa " + angka(s.metrik.kappa, 4) + ".");
        }))));
    }

    p.appendChild(artiMetrik());

    p.appendChild(tabelKappa());

    p.appendChild(blok("Uji McNemar berpasangan", "Perbandingan dilakukan atas pasangan yang berbeda pendapat pada baris yang sama, bukan dengan membandingkan dua angka akurasi.",
      tabel(
        [["Sistem A", ""], ["Sistem B", ""], ["A salah, B benar", "angka"], ["B salah, A benar", "angka"], ["Nilai p", "angka"], ["Tafsiran", ""]],
        (g.mcnemar || []).map(function (m) {
          return {
            sel: [
              m.a, m.b,
              angka(m.a_salah_b_benar), angka(m.b_salah_a_benar),
              angka(m.p_value, 4),
              h("span", { class: "kecil", teks: m.p_value < 0.05 ? "berbeda nyata" : "belum berbeda nyata" })
            ]
          };
        })
      )));

    var pemb = g.pembanding || {};
    if (pemb.pseudocode) {
      var ps = pemb.pseudocode;
      p.appendChild(blok("Uji metode pseudocode", "Metode dari kajian eksternal diterapkan sebagai modul tersendiri lalu diuji pada data yang sama. Klaim kenaikan 7 sampai 16 poin F1 tidak tereplikasi.",
        h("div", { class: "grid-dua" }, [
          h("div", { class: "kotak" }, [
            h("h4", { teks: "Hasil pada 100 baris yang sama" }),
            h("div", { class: "petak-kunci" }, [
              h("div", null, [h("div", { class: "k", teks: "Akurasi" }), h("div", { class: "v mono", teks: angka(ps.akurasi, 4) })]),
              h("div", null, [h("div", { class: "k", teks: "F1 macro" }), h("div", { class: "v mono", teks: angka(ps.f1_macro, 4) })]),
              h("div", null, [h("div", { class: "k", teks: "Gagal urai" }), h("div", { class: "v mono", teks: angka(ps.gagal_urai) })]),
              h("div", null, [h("div", { class: "k", teks: "Presisi gerbang" }), h("div", { class: "v mono", teks: angka(ps.gerbang_presisi, 3) })]),
              h("div", null, [h("div", { class: "k", teks: "Recall gerbang" }), h("div", { class: "v mono", teks: angka(ps.gerbang_recall, 3) })]),
              h("div", null, [h("div", { class: "k", teks: "Model" }), h("div", { class: "v mono", teks: ps.model })]),
            ])
          ]),
          h("div", { class: "kotak" }, [
            h("h4", { teks: "Temuan terpentingnya" }),
            h("p", { teks: "Dua prompt yang sama sekali berbeda, satu bahasa alami dengan dua belas contoh dan satu pseudocode tanpa contoh, menghasilkan bias asimetris yang sama persis: tidak pernah salah menerima, tetapi salah menolak sekitar 35 persen." }),
            h("p", { style: "margin-top:10px", teks: "Artinya sumber biasnya bukan pada prompt. Prompt dapat diganti sekreatif apa pun dan hasilnya akan sama, karena biasnya ada pada model atau pada definisinya." })
          ])
        ])));
    }

    if (pemb.indobert) {
      var ib = pemb.indobert;
      var barisIb = [];
      ["judul", "tetap"].forEach(function (mode) {
        if (ib[mode]) {
          barisIb.push({
            sel: [
              mode === "judul" ? "Konteks judul unggahan" : "Konteks topik tetap",
              angka(ib[mode].akurasi, 4),
              angka(ib[mode].f1_macro, 4),
              angka(ib[mode].jumlah_relevan) + " dari " + angka(ib[mode].n)
            ]
          });
        }
      });
      p.appendChild(blok("Uji anotator dari model terbuka lain", "Dua model IndoBERT sadar konteks dari publikasi independen diuji pada gold yang sama. Keduanya kalah dari model penelitian ini.",
        h("div", { class: "grid-dua" }, [
          h("div", { class: "bungkus-tabel" }, tabel(
            [["Bentuk konteks", ""], ["Akurasi", "angka"], ["F1 macro", "angka"], ["Baris dianggap relevan", ""]],
            barisIb
          )),
          h("div", { class: "kotak" }, [
            h("h4", { teks: "Yang justru menguatkan argumen penelitian" }),
            h("p", { teks: "Pada model relevansi itu, delapan dari delapan baris yang dinilai tidak relevan oleh manusia juga ditolaknya. Ia sepakat penuh pada kasus yang jelas, tetapi jauh lebih ketat pada kasus batas." }),
            h("p", { style: "margin-top:10px", teks: "Dua kejujuran yang harus ikut dibaca: label latih kedua model itu berasal dari GPT-4o-mini, bukan manusia, sehingga ia mewarisi definisi satu model bahasa besar. Konteks latihnya juga bersih sedangkan konteks penelitian ini berantakan, jadi sebagian kelemahannya adalah model itu bekerja di luar sebaran latihnya." })
          ])
        ])));
    }

    var eks = g.eksperimen;
    if (eks && eks.sistem) {
      p.appendChild(blok("Eksperimen yang dihentikan, dan mengapa", "Rantai percakapan dan gerbang relevansi dua tahap pernah dicoba penuh, lalu dihentikan karena hasilnya tidak membaik. Jejaknya sengaja disimpan.",
        h("div", { class: "bungkus-tabel" }, tabel(
          [["Sistem", ""], ["Akurasi", "angka"], ["F1 macro", "angka"]],
          eks.sistem.map(function (s) {
            return { sel: [s.nama.replace("prediksi_", ""), angka(s.akurasi, 4), angka(s.f1, 4)] };
          }),
          { catatan: (eks.mcnemar || []).map(function (m) { return m.a + " lawan " + m.b + ": p = " + angka(m.p_value, 4); }).join(" · ") }
        ))));
    }
  }

  /* ------------------------------------------------------------------------
     Panel 7: Keputusan
     ------------------------------------------------------------------------ */
  function gambarKeputusan() {
    var p = $("#panel-keputusan");
    kosongkan(p);

    p.appendChild(h("div", { class: "judul-panel" }, [
      h("h2", { id: "judul-keputusan", teks: "Keputusan dan batas" }),
      h("p", { class: "keterangan-panel", teks: "Setiap temuan audit menghasilkan keputusan yang dicatat, bukan sekadar diperbaiki diam-diam. Daftar ini yang membuat pekerjaan dapat dipertanggungjawabkan." })
    ]));

    var kep = D.keputusan || [];
    if (kep.length) {
      p.appendChild(blok("Catatan keputusan", angka(kep.length) + " butir keputusan beserta alasannya, disalin dari catatan audit.",
        h("div", { class: "daftar-keputusan" }, kep.map(function (k) {
          return h("div", { class: "keputusan-baris" }, [
            h("div", { class: "kode", teks: k.kode }),
            h("div", null, [h("div", { class: "isi", teks: k.keputusan }), h("div", { class: "alasan", teks: k.alasan })])
          ]);
        }))));
    }

    var batas = D.keterbatasan || [];
    if (batas.length) {
      p.appendChild(blok("Keterbatasan yang harus ikut dibaca", "Diambil dari bagian yang tidak boleh diklaim pada README penelitian.",
        h("div", { class: "grid-dua" }, batas.map(function (b, i) {
          return h("div", { class: "kotak" }, [h("h4", { teks: "Keterbatasan " + (i + 1) }), h("p", { teks: b })]);
        }))));
    }

    var terbuka = D.terbuka || [];
    if (terbuka.length) {
      p.appendChild(blok("Yang masih terbuka", "Pekerjaan ini dinyatakan lengkap apa adanya. Butir di bawah adalah perbaikan, bukan syarat agar hasilnya dapat diserahkan.",
        h("div", { class: "daftar-terbuka" }, terbuka.map(function (t) {
          return h("div", { class: "terbuka-baris" }, [ikon("awas"), h("span", { teks: t })]);
        }))));
    }

    var berkas = D.berkas || [];
    if (berkas.length) {
      p.appendChild(blok("Berkas keluaran penelitian", "Seluruh berkas hasil ada di folder final, dan kesamaannya dengan berkas kerja dibuktikan dengan sidik jari SHA-256.",
        tabel(
          [["Berkas", ""], ["Ukuran (bit)", "angka"], ["Baris", "angka"], ["Berasal dari", ""]],
          berkas.map(function (b) {
            return { sel: [h("span", { class: "mono", teks: b.nama }), angka(b.ukuran), b.baris ? angka(b.baris) : "-", h("span", { class: "kecil", teks: b.asal || "" })] };
          })
        )));
    }
  }

  /* ------------------------------------------------------------------------
     Titik masuk
     ------------------------------------------------------------------------ */
  function mulai() {
    indeksKolom();
    initTema();
    initTab();

    var tabir = $("#tabir");
    tabir.addEventListener("click", tutupLaci);
    $("#tombol-tutup").addEventListener("click", tutupLaci);
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !$("#laci").hidden) tutupLaci();
    });

    $("#kaki-keterangan").textContent =
      "Data dibangkitkan " + (D.meta && D.meta.dibuat ? D.meta.dibuat : "") +
      " dari " + angka(D.meta && D.meta.jumlah_label) + " baris berlabel. Sumber label: " +
      ((D.meta && D.meta.sumber_label) || "-") + ".";

    var capaian = $("#kaki-capaian");
    if (capaian) {
      var endpoint = ((KONFIG.endpoint) || "").replace(/\/+$/, "");
      capaian.textContent = endpoint
        ? "Uji model langsung memanggil " + endpoint + " (diterbitkan " + (KONFIG.diterbitkan || "tidak diketahui") + "). Seluruh bagian lain bekerja tanpa sambungan."
        : "Endpoint uji model belum diterbitkan. Halaman tetap bekerja penuh tanpa sambungan; jalankan py -3.13 terbitkan_model.py untuk menyalakan blok uji model.";
    }

    buka((location.hash || "").replace("#", ""));
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mulai);
  else mulai();
})();
