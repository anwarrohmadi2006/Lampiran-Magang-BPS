# Analisis Sentimen Sensus Ekonomi 2026 dan Aplikasi Fasih BPS
# 01 Penyusunan Korpus
#
# Kegunaan : Mengumpulkan tanggapan dari tiga platform, menyaringnya dengan batas waktu dan
#            kata kunci, lalu memilah korpus menjadi ember opini, non-opini, dan karantina.
# Masukan  : data mentah hasil pengumpulan pada folder data/raw_v2
# Keluaran : data/processed/v3/korpus.csv beserta embernya dan reports/pipeline_SE2026.json
# Rujukan  : Bab III, sub-bab Metode Pengumpulan Data, serta Bab IV pada bagian cakupan korpus
#
# Menjalankan dari akar repositori:  py -3.13 analisis/01_penyusunan_korpus.py
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from scraper import keywords
from scraper import percakapan
from scraper.cleaning import clean_text, dedupe_texts, saring_bahasa
from scraper.schema import (
    PERIODE_AKHIR,
    PERIODE_MULAI,
    RAW_DIR,
    Record,
    in_range,
    parse_date_arg,
)

ALL_SOURCES = ["playstore", "reddit", "youtube", "threads", "twitter"]

FINAL_COLUMNS = [
    "uid",
    "source",
    "source_id",
    "text",
    "text_clean",
    "created_at",
    "author",
    "url",
    "score",
    "query",
    "label",
    "extra",
]


def collect_playstore(limit: int, since=None, until=None) -> list[Record]:
    from scraper import playstore

    return playstore.scrape(
        app_id="id.go.bpsfasih", target=limit, since=since, until=until
    )


def collect_reddit(limit: int, comments: int, since=None, until=None) -> list[Record]:
    from scraper import reddit

    return reddit.scrape(
        queries=keywords.DEFAULT_QUERIES,
        limit_per_query=limit,
        subreddits=keywords.REDDIT_SUBREDDITS,
        comments_per_post=comments,
        since=since,
        until=until,
    )


def collect_youtube(
    videos: int, comments: int, mode_topik: str = "longgar", since=None, until=None
) -> list[Record]:
    """Mengumpulkan komentar YouTube beserta penyaring topik.

    Jumlah video per kueri sebelumnya diturunkan dari parameter limit melalui
    rumus max(3, limit // 100), sehingga menaikkan target data justru
    memperlebar topik yang terjaring. Sekarang jumlah video ditetapkan
    tersendiri agar kedua hal itu tidak saling terikat.
    """
    from scraper import youtube

    return youtube.scrape(
        queries=keywords.YOUTUBE_QUERIES,
        channels=keywords.YOUTUBE_CHANNELS,
        videos_per_query=videos,
        max_comments=comments,
        mode_topik=mode_topik,
        since=since,
        until=until,
    )


def collect_threads(limit: int, backend: str, since=None, until=None) -> list[Record]:
    from scraper import threads_cli

    if backend in ("auto", "cli") and threads_cli.cli_available():
        return threads_cli.scrape(
            keywords=keywords.DEFAULT_QUERIES,
            limit=limit,
            out_csv=RAW_DIR / "threads_cli.csv",
            since=since,
            until=until,
        )
    if backend == "cli":
        raise RuntimeError(
            "backend=cli dipilih tapi CLI 'threads-scraper' tidak terpasang. "
            "pip install threads-comment-scraper && playwright install chromium"
        )
    from scraper import threads

    return threads.scrape(
        queries=keywords.DEFAULT_QUERIES[:6],
        accounts=keywords.THREADS_ACCOUNTS,
        max_posts=limit,
        since=since,
        until=until,
    )


def collect_twitter(limit: int, since=None, until=None) -> list[Record]:
    from scraper import twitter

    return twitter.scrape(
        queries=keywords.DEFAULT_QUERIES[:6],
        accounts=keywords.TWITTER_ACCOUNTS,
        max_tweets=limit,
        since=since,
        until=until,
    )


def saring_topik_threads(records: list[Record]) -> list[Record]:
    """Membuang rekaman Threads yang tidak menyebut Sensus Ekonomi 2026.

    Pencarian Threads cocok sebagian, sehingga kueri "sensus ekonomi" juga
    mengembalikan unggahan tentang ekonomi umum bahkan politik, lengkap dengan
    seluruh komentarnya. Audit 15 September 2026 menemukan 131 dari 394 baris
    (33,2 persen) sama sekali tidak menyebut sensus ekonomi.

    Pemeriksaan dilakukan pada teks rekaman sekaligus teks unggahan induknya,
    karena banyak komentar baru bermakna setelah dibaca bersama konteksnya.
    Rekaman dari sumber lain tidak disentuh.
    """
    hasil: list[Record] = []
    for r in records:
        if r.source != "threads":
            hasil.append(r)
            continue
        induk = (r.extra or {}).get("post_text")
        if keywords.teks_bertopik(r.text, induk):
            hasil.append(r)
    return hasil


def load_raw_jsonl(directory: Path) -> list[Record]:
    records: list[Record] = []
    for path in sorted(directory.glob("*.jsonl")):
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                extra = row.get("extra")
                if isinstance(extra, str):
                    try:
                        extra = json.loads(extra)
                    except json.JSONDecodeError:
                        extra = {}
                records.append(
                    Record(
                        source=row.get("source", "unknown"),
                        source_id=str(row.get("source_id")),
                        text=row.get("text") or "",
                        created_at=row.get("created_at"),
                        author=row.get("author"),
                        url=row.get("url"),
                        score=row.get("score"),
                        lang=row.get("lang"),
                        query=row.get("query"),
                        extra=extra or {},
                    )
                )
    return records


def to_final_rows(records: list[Record], apply_clean: bool = True) -> list[dict]:
    rows: list[dict] = []
    for r in records:
        d = r.to_dict()
        if apply_clean:
            d["text_clean"] = clean_text(d.get("text") or "")
        else:
            d["text_clean"] = d.get("text") or ""
        d["label"] = ""
        d["extra"] = json.dumps(d.get("extra") or {}, ensure_ascii=False)
        rows.append({k: d.get(k) for k in FINAL_COLUMNS})
    return rows


def write_final(rows: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FINAL_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Pipeline 1-klik: scrape multisumber -> clean -> CSV siap IndoBERT"
    )
    p.add_argument("--sources", default="all", help=f"all atau subset dari {ALL_SOURCES} (koma)")
    p.add_argument("--limit", type=int, default=2000, help="target data per sumber sosmed")
    p.add_argument("--comments", type=int, default=200, help="komentar per post/video")
    p.add_argument(
        "--videos-per-query",
        type=int,
        default=8,
        help="jumlah video per kueri atau per kanal YouTube",
    )
    p.add_argument(
        "--mode-topik",
        default="longgar",
        choices=["longgar", "ketat"],
        help="longgar hanya membuang topik di luar lingkup; ketat menuntut kata kunci topik pada judul",
    )
    p.add_argument(
        "--saring-bahasa",
        action="store_true",
        help="membuang rekaman berbahasa asing sebelum penulisan",
    )
    p.add_argument(
        "--tanpa-saring-topik-threads",
        action="store_true",
        help="mematikan penyaring topik Threads, yang secara bawaan aktif",
    )
    p.add_argument("--threads-backend", default="auto", choices=["auto", "cli", "playwright"])
    p.add_argument("--out", default="data/processed/dataset_se2026_ready_v2.csv")
    p.add_argument("--raw-dir", default=str(RAW_DIR))
    p.add_argument("--dry-run", action="store_true", help="lewati scraping, pakai JSONL yang ada")
    p.add_argument(
        "--since",
        default=PERIODE_MULAI,
        help=f"batas awal tanggal; bawaan {PERIODE_MULAI}",
    )
    p.add_argument(
        "--until",
        default=PERIODE_AKHIR,
        help=f"batas akhir tanggal, inklusif sepanjang hari; bawaan {PERIODE_AKHIR}",
    )
    p.add_argument("--no-clean", action="store_true")
    p.add_argument("--keep-raw", action="store_true", help="simpan JSONL mentah per sumber")
    p.add_argument(
        "--tanpa-rantai",
        action="store_true",
        help="jangan sisipkan rantai percakapan ke extra rekaman",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    raw_dir = Path(args.raw_dir)
    sources = ALL_SOURCES if args.sources == "all" else [s.strip() for s in args.sources.split(",")]

    since = parse_date_arg(args.since)
    until = parse_date_arg(args.until)
    if until is not None and args.until and len(args.until.strip()) <= 10:
        until = until.replace(hour=23, minute=59, second=59)

    if args.dry_run:
        records = load_raw_jsonl(raw_dir)
        print(f"[dry-run] {len(records)} record dari {raw_dir}")
    else:
        records = []
        collectors = {
            "playstore": lambda: collect_playstore(args.limit, since, until),
            "reddit": lambda: collect_reddit(args.limit, args.comments, since, until),
            "youtube": lambda: collect_youtube(
                args.videos_per_query, args.comments, args.mode_topik, since, until
            ),
            "threads": lambda: collect_threads(
                args.limit, args.threads_backend, since, until
            ),
            "twitter": lambda: collect_twitter(args.limit, since, until),
        }
        for src in sources:
            if src not in collectors:
                print(f"[skip] sumber tidak dikenal: {src}", file=sys.stderr)
                continue
            print(f"[{src}] scraping ...", flush=True)
            try:
                got = collectors[src]()
            except Exception as e:  # noqa: BLE001
                print(f"[{src}] GAGAL: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
                continue
            print(f"[{src}] {len(got)} baris", flush=True)
            records.extend(got)

        if args.keep_raw:
            from scraper.schema import write_records

            seen_names: set[str] = set()
            for r in records:
                if r.source in seen_names:
                    continue
                seen_names.add(r.source)
                part = [x for x in records if x.source == r.source]
                write_records(part, name=r.source, out_dir=raw_dir, skip_existing=False)

    if not args.tanpa_rantai:
        peta_rantai = percakapan.bangun_rantai(records)
        jumlah_rantai = percakapan.sisipkan_rantai(records, peta_rantai)
        print(
            f"rantai percakapan: {jumlah_rantai} rekaman punya leluhur "
            f"({len(peta_rantai)} id berantai)"
        )

    if since or until:
        before_range = len(records)
        records = [r for r in records if in_range(r.created_at, since, until)]
        print(f"filter tanggal {args.since or '-'} .. {args.until or '-'}: {before_range} -> {len(records)}")

    if args.saring_bahasa:
        sebelum_bahasa = len(records)
        records = saring_bahasa(records)
        print(f"filter bahasa asing: {sebelum_bahasa} -> {len(records)}")

    if not args.tanpa_saring_topik_threads:
        sebelum_topik = len(records)
        records = saring_topik_threads(records)
        print(f"filter topik Threads: {sebelum_topik} -> {len(records)}")

    rows = to_final_rows(records, apply_clean=not args.no_clean)
    before = len(rows)
    rows = dedupe_texts([r for r in rows if r["text_clean"].strip()])
    rows = sorted(rows, key=lambda r: (r["source"], r["created_at"] or ""))

    out_path = Path(args.out)
    write_final(rows, out_path)

    per_source: dict[str, int] = {}
    for r in rows:
        per_source[r["source"]] = per_source.get(r["source"], 0) + 1

    print("\n=== ringkasan pipeline ===")
    print(f"total sebelum dedup : {before}")
    print(f"total siap IndoBERT : {len(rows)}")
    for src, n in sorted(per_source.items()):
        print(f"  {src:10s} {n}")
    print(f"output              : {out_path.resolve()}")
    print("kolom 'label' masih kosong -> isi manual/weak-label sebelum fine-tuning.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
