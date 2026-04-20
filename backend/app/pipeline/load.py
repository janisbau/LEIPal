"""
Load parsed GLEIF data into PostgreSQL.

Full load: uses PostgreSQL COPY for maximum throughput (~100k rows/sec).
Delta load: upserts in batches using ON CONFLICT DO UPDATE.

Run directly:
    python -m app.pipeline.load --mode full --file ./data/full/lei2_full_40438.zip
    python -m app.pipeline.load --mode delta --file ./data/deltas/lei2_delta_XXXXX.zip
"""

import argparse
import csv
import logging
import tempfile
from pathlib import Path

import psycopg
from tqdm import tqdm

from app.config import settings
from app.pipeline.parse import stream_records

log = logging.getLogger(__name__)

DB_COLUMNS = [
    "lei",
    "legal_name",
    "jurisdiction",
    "entity_status",
    "entity_category",
    "managing_lou",
    "registration_status",
    "initial_registration_date",
    "last_update_date",
    "next_renewal_date",
]

UPSERT_SQL = """
    INSERT INTO lei_records (
        lei, legal_name, jurisdiction, entity_status, entity_category,
        managing_lou, registration_status, initial_registration_date,
        last_update_date, next_renewal_date, updated_at
    ) VALUES (
        %(lei)s, %(legal_name)s, %(jurisdiction)s, %(entity_status)s,
        %(entity_category)s, %(managing_lou)s, %(registration_status)s,
        %(initial_registration_date)s, %(last_update_date)s,
        %(next_renewal_date)s, NOW()
    )
    ON CONFLICT (lei) DO UPDATE SET
        legal_name               = EXCLUDED.legal_name,
        jurisdiction             = EXCLUDED.jurisdiction,
        entity_status            = EXCLUDED.entity_status,
        entity_category          = EXCLUDED.entity_category,
        managing_lou             = EXCLUDED.managing_lou,
        registration_status      = EXCLUDED.registration_status,
        initial_registration_date = EXCLUDED.initial_registration_date,
        last_update_date         = EXCLUDED.last_update_date,
        next_renewal_date        = EXCLUDED.next_renewal_date,
        updated_at               = NOW()
"""


def _get_raw_dsn() -> str:
    return settings.database_url.replace("postgresql+psycopg://", "postgresql://")


def load_full(zip_path: Path) -> int:
    """
    Bulk-load the full golden copy using PostgreSQL COPY.
    Streams the XML → writes a temp CSV → COPYs into Postgres.
    Truncates existing data first.
    """
    log.info("Streaming records from %s …", zip_path.name)

    # Stream XML → temp CSV (avoids loading 3M rows into RAM)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8"
    ) as tmp:
        tmp_path = Path(tmp.name)
        writer = csv.DictWriter(tmp, fieldnames=DB_COLUMNS, extrasaction="ignore")
        row_count = 0
        for row in tqdm(stream_records(zip_path), desc="Parsing XML", unit=" records"):
            writer.writerow({k: ("" if row.get(k) is None else row[k]) for k in DB_COLUMNS})
            row_count += 1

    log.info("Parsed %d records. Loading into PostgreSQL …", row_count)

    dsn = _get_raw_dsn()
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            # Stage into a temp table (no PK constraint) so duplicates in the
            # source data don't blow up COPY
            cur.execute("""
                CREATE TEMP TABLE lei_stage (
                    lei TEXT, legal_name TEXT, jurisdiction TEXT,
                    entity_status TEXT, entity_category TEXT,
                    managing_lou TEXT, registration_status TEXT,
                    initial_registration_date TEXT,
                    last_update_date TEXT, next_renewal_date TEXT
                )
            """)

            log.info("COPYing into staging table …")
            with open(tmp_path, "r", newline="", encoding="utf-8") as f:
                with cur.copy(
                    "COPY lei_stage (lei, legal_name, jurisdiction, entity_status, "
                    "entity_category, managing_lou, registration_status, "
                    "initial_registration_date, last_update_date, next_renewal_date) "
                    "FROM STDIN WITH (FORMAT CSV, NULL '')"
                ) as copy:
                    while data := f.read(65536):
                        copy.write(data)

            log.info("Deduplicating and inserting into lei_records …")
            cur.execute("TRUNCATE TABLE lei_records RESTART IDENTITY CASCADE")
            cur.execute("""
                INSERT INTO lei_records (
                    lei, legal_name, jurisdiction, entity_status, entity_category,
                    managing_lou, registration_status,
                    initial_registration_date, last_update_date, next_renewal_date
                )
                SELECT DISTINCT ON (lei)
                    lei, legal_name, jurisdiction, entity_status, entity_category,
                    managing_lou, registration_status,
                    NULLIF(initial_registration_date, '')::date,
                    NULLIF(last_update_date, '')::date,
                    NULLIF(next_renewal_date, '')::date
                FROM lei_stage
                WHERE lei IS NOT NULL AND lei <> ''
                ORDER BY lei, last_update_date DESC NULLS LAST
            """)
        conn.commit()

    tmp_path.unlink(missing_ok=True)
    log.info("Full load complete: %d records", row_count)
    _record_watermark(zip_path.name, row_count)
    _refresh_lous()
    return row_count


def load_delta(zip_path: Path, batch_size: int = 5_000) -> int:
    """
    Apply a delta file using batched upserts.
    """
    log.info("Applying delta: %s", zip_path.name)
    dsn = _get_raw_dsn()
    row_count = 0
    batch: list[dict] = []

    with psycopg.connect(dsn) as conn:
        for row in tqdm(stream_records(zip_path), desc="Applying delta", unit=" records"):
            batch.append(row)
            if len(batch) >= batch_size:
                with conn.cursor() as cur:
                    cur.executemany(UPSERT_SQL, batch)
                conn.commit()
                row_count += len(batch)
                batch.clear()

        if batch:
            with conn.cursor() as cur:
                cur.executemany(UPSERT_SQL, batch)
            conn.commit()
            row_count += len(batch)

    log.info("Delta applied: %d records upserted", row_count)
    _record_watermark(zip_path.name, row_count)
    _refresh_lous()
    return row_count


def _record_watermark(file_name: str, record_count: int) -> None:
    from sqlalchemy import select
    from app.database import SessionLocal
    from app.models import PipelineWatermark

    with SessionLocal() as session:
        exists = session.scalar(
            select(PipelineWatermark).where(PipelineWatermark.file_name == file_name)
        )
        if exists is None:
            session.add(PipelineWatermark(file_name=file_name, record_count=record_count))
            session.commit()


def _refresh_lous() -> None:
    """Rebuild the lous table from the managing_lou field in lei_records."""
    sql = """
        INSERT INTO lous (lou_lei, lou_name, country, status)
        SELECT DISTINCT ON (r.managing_lou)
            r.managing_lou           AS lou_lei,
            lou.legal_name           AS lou_name,
            LEFT(lou.jurisdiction, 2) AS country,
            lou.entity_status        AS status
        FROM lei_records r
        LEFT JOIN lei_records lou ON lou.lei = r.managing_lou
        WHERE r.managing_lou IS NOT NULL
        ON CONFLICT (lou_lei) DO UPDATE SET
            lou_name = EXCLUDED.lou_name,
            country  = EXCLUDED.country,
            status   = EXCLUDED.status
    """
    with psycopg.connect(_get_raw_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    log.info("LOU table refreshed")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Load GLEIF data into PostgreSQL")
    parser.add_argument("--mode", choices=["full", "delta"], required=True)
    parser.add_argument("--file", required=True, help="Path to the ZIP file to load")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        raise SystemExit(f"File not found: {path}")

    if args.mode == "full":
        count = load_full(path)
    else:
        count = load_delta(path)
    print(f"\nDone. Records processed: {count:,}")
