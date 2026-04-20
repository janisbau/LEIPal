"""
Download GLEIF Golden Copy files (full + delta).

GLEIF API base: https://leidata.gleif.org/api/v1/
- Full file list:  GET /concatenated-files/lei2
- Delta file list: GET /concatenated-files/lei2delta  (24h rolling delta)

Each entry in the response looks like:
  {
    "id": 40879,
    "type": "lei2",
    "content_date": "2026-04-20 09:00:01",
    "record_count": 3284799,
    "file": "https://leidata.gleif.org/api/v1/concatenated-files/lei2/get/40879/zip",
    "filesize": 510665692,
    "signature": "https://..."
  }

Run this script directly:
    python -m app.pipeline.download --mode full
    python -m app.pipeline.download --mode delta
"""

import argparse
import logging
from pathlib import Path

import httpx
from tqdm import tqdm

from app.config import settings

log = logging.getLogger(__name__)

GLEIF_API_BASE = "https://leidata.gleif.org/api/v1"
FULL_ENDPOINT = f"{GLEIF_API_BASE}/concatenated-files/lei2"
DELTA_ENDPOINT = f"{GLEIF_API_BASE}/concatenated-files/lei2delta"


def _get_latest_entry(endpoint: str) -> dict:
    """Fetch the file list from an endpoint and return the most recent entry."""
    resp = httpx.get(endpoint, timeout=30)
    resp.raise_for_status()
    entries = resp.json().get("data", [])
    if not entries:
        raise RuntimeError(f"No files returned from {endpoint}")
    # Entries are ordered oldest→newest; last entry is most recent
    return entries[-1]


def _stream_download(url: str, dest: Path) -> None:
    """Stream a file from url to dest with a progress bar."""
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


def download_full() -> Path:
    """
    Download the latest full concatenated GLEIF golden copy.
    Returns the path to the downloaded ZIP file.
    """
    log.info("Fetching latest full file info from GLEIF …")
    entry = _get_latest_entry(FULL_ENDPOINT)

    file_id = entry["id"]
    download_url: str = entry["file"]
    content_date: str = entry["content_date"]
    record_count: int = entry.get("record_count", 0)

    # Use a predictable filename based on the file ID
    filename = f"lei2_full_{file_id}.zip"
    dest = settings.data_dir / "full" / filename

    log.info(
        "Latest full file: id=%s, date=%s, records=%s, size=%.1f MB",
        file_id,
        content_date,
        f"{record_count:,}",
        entry.get("filesize", 0) / 1_048_576,
    )

    if dest.exists():
        log.info("File already downloaded, skipping: %s", dest)
        return dest

    log.info("Downloading to %s …", dest)
    _stream_download(download_url, dest)
    log.info("Full file saved: %s", dest)
    return dest


def download_deltas() -> list[Path]:
    """
    Download all delta files not yet recorded in the watermark table.
    Returns a list of paths to downloaded delta ZIPs.
    """
    from app.database import SessionLocal
    from app.models import PipelineWatermark

    log.info("Fetching delta file list from GLEIF …")

    try:
        resp = httpx.get(DELTA_ENDPOINT, timeout=30)
        resp.raise_for_status()
        entries = resp.json().get("data", [])
    except httpx.HTTPStatusError as e:
        log.warning("Delta endpoint returned %s — may not be available yet", e.response.status_code)
        return []

    if not entries:
        log.info("No delta files available")
        return []

    with SessionLocal() as session:
        applied = {row.file_name for row in session.query(PipelineWatermark.file_name).all()}

    downloaded: list[Path] = []
    for entry in entries:
        file_id = entry["id"]
        filename = f"lei2_delta_{file_id}.zip"

        if filename in applied:
            log.info("Delta already applied, skipping: %s", filename)
            continue

        dest = settings.data_dir / "deltas" / filename
        if not dest.exists():
            log.info("Downloading delta %s …", filename)
            _stream_download(entry["file"], dest)

        downloaded.append(dest)

    log.info("Downloaded %d new delta file(s)", len(downloaded))
    return downloaded


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Download GLEIF golden copy files")
    parser.add_argument(
        "--mode",
        choices=["full", "delta"],
        required=True,
        help="'full' for initial load, 'delta' for incremental updates",
    )
    args = parser.parse_args()

    if args.mode == "full":
        download_full()
    else:
        download_deltas()
