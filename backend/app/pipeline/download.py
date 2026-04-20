"""
Download GLEIF Golden Copy files (full + delta).

Full files:   https://leidata.gleif.org/api/v1/concatenated-files/lei2
              Returns JSON list; each entry has an `id` and `file` (ZIP URL).
              ZIP contains one XML file in LEI-CDF v3.1 format.

Delta files:  https://goldencopy.gleif.org/api/v2/golden-copies/publishes/lei2/latest.xml
              Add ?delta=<type> where type is one of:
                IntraDay  — changes in last ~8 hours   (published 3x/day)
                LastDay   — changes in last 24 hours   (recommended for daily runs)
                LastWeek  — changes in last 7 days
                LastMonth — changes in last 31 days
              Returns a ZIP containing one XML file in LEI-CDF v3.1 format.
              The ZIP filename (from Content-Disposition) is used as the watermark key.

Run this script directly:
    python -m app.pipeline.download --mode full
    python -m app.pipeline.download --mode delta
    python -m app.pipeline.download --mode delta --delta-type LastWeek
"""

import argparse
import logging
import re
from pathlib import Path

import httpx
from tqdm import tqdm

from app.config import settings

log = logging.getLogger(__name__)

GLEIF_API_BASE = "https://leidata.gleif.org/api/v1"
FULL_ENDPOINT = f"{GLEIF_API_BASE}/concatenated-files/lei2"

GOLDENCOPY_BASE = "https://goldencopy.gleif.org/api/v2/golden-copies/publishes/lei2"
DELTA_TYPES = ["IntraDay", "LastDay", "LastWeek", "LastMonth"]


def _stream_download(url: str, dest: Path) -> None:
    """Stream a file from url to dest with a progress bar. Follows redirects."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream("GET", url, timeout=None, follow_redirects=True) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        with open(dest, "wb") as f, tqdm(
            total=total, unit="B", unit_scale=True, desc=dest.name
        ) as bar:
            for chunk in resp.iter_bytes(chunk_size=1024 * 256):
                f.write(chunk)
                bar.update(len(chunk))


def _get_delta_filename(url: str, delta_type: str) -> tuple[str, str]:
    """
    Resolve the final URL after redirect and derive a stable filename from it.
    Returns (filename, resolved_url).

    The resolved URL looks like:
      .../2026/04/20/1216828/20260420-1600-gleif-goldencopy-lei2-last-day.xml.zip
    We use the basename of that URL as the watermark key.
    """
    try:
        resp = httpx.head(url, timeout=30, follow_redirects=True)
        resolved_url = str(resp.url)
        filename = resolved_url.split("/")[-1]
        if filename.endswith(".zip"):
            return filename, resolved_url
    except Exception:
        pass
    # Fallback
    return f"lei2_delta_{delta_type}.zip", url


def download_full() -> Path:
    """
    Download the latest full concatenated GLEIF golden copy.
    Skips download if the file already exists locally.
    Returns the path to the downloaded ZIP.
    """
    log.info("Fetching latest full file info from GLEIF …")
    resp = httpx.get(FULL_ENDPOINT, timeout=30)
    resp.raise_for_status()
    entries = resp.json().get("data", [])
    if not entries:
        raise RuntimeError("No full files returned from GLEIF API")

    entry = entries[-1]  # most recent
    file_id = entry["id"]
    download_url: str = entry["file"]
    content_date: str = entry["content_date"]
    record_count: int = entry.get("record_count", 0)
    size_mb = entry.get("filesize", 0) / 1_048_576

    filename = f"lei2_full_{file_id}.zip"
    dest = settings.data_dir / "full" / filename

    log.info(
        "Latest full file: id=%s  date=%s  records=%s  size=%.0f MB",
        file_id, content_date, f"{record_count:,}", size_mb,
    )

    if dest.exists():
        log.info("Already downloaded, skipping: %s", dest)
        return dest

    _stream_download(download_url, dest)
    log.info("Saved: %s", dest)
    return dest


def download_deltas(delta_type: str = "LastDay") -> list[Path]:
    """
    Download the latest delta file of the given type, unless already applied.

    delta_type: IntraDay | LastDay | LastWeek | LastMonth
    Returns a list with the downloaded path (empty if already applied or nothing new).
    """
    if delta_type not in DELTA_TYPES:
        raise ValueError(f"delta_type must be one of {DELTA_TYPES}")

    from app.database import SessionLocal
    from app.models import PipelineWatermark

    url = f"{GOLDENCOPY_BASE}/latest.xml?delta={delta_type}"
    log.info("Checking latest %s delta …", delta_type)

    # Resolve redirect to get the real filename (includes date+time in the name)
    filename, resolved_url = _get_delta_filename(url, delta_type)
    dest = settings.data_dir / "deltas" / filename

    log.info("Latest delta file: %s", filename)

    with SessionLocal() as session:
        from sqlalchemy import select
        already_applied = session.scalar(
            select(PipelineWatermark).where(PipelineWatermark.file_name == filename)
        )

    if already_applied:
        log.info("Delta already applied, skipping: %s", filename)
        return []

    if dest.exists():
        log.info("Already downloaded (not yet applied): %s", dest)
        return [dest]

    log.info("Downloading → %s …", dest)
    _stream_download(url, dest)
    log.info("Saved: %s", dest)
    return [dest]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Download GLEIF golden copy files")
    parser.add_argument(
        "--mode", choices=["full", "delta"], required=True,
        help="'full' for initial load, 'delta' for incremental update",
    )
    parser.add_argument(
        "--delta-type", default="LastDay", choices=DELTA_TYPES,
        help="Which delta window to download (default: LastDay)",
    )
    args = parser.parse_args()

    if args.mode == "full":
        download_full()
    else:
        paths = download_deltas(args.delta_type)
        if paths:
            print(f"\nDownloaded: {paths[0]}")
            print("Now run: poetry run python -m app.pipeline.load --mode delta --file", paths[0])
