"""Bulk ZIP downloader for SEC EDGAR XBRL Company Facts.

Downloads the full companyfacts.zip (~2-3 GB) and selectively extracts
only the requested CIK files. Caches extracted JSON alongside API-fetched files.

This is the domain pack version — config values are passed as arguments,
not imported from a hardcoded Python config module.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import httpx


def _zip_cache_path(cache_dir: Path) -> Path:
    return cache_dir / "companyfacts.zip"


def _cik_filename(cik: int) -> str:
    return f"CIK{cik:010d}.json"


def fetch_bulk_company_facts(
    ciks: list[int],
    cache_dir: Path,
    user_agent: str,
    bulk_url: str = "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip",
) -> dict[int, dict]:
    """Download bulk ZIP and extract only the requested CIKs.

    Returns {cik: parsed_json} for each requested CIK found in the ZIP.
    Caches extracted JSON files in cache_dir for future use.

    Raises httpx.HTTPStatusError on download failure.
    Raises KeyError if a requested CIK is not found in the ZIP.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    zip_path = _zip_cache_path(cache_dir)

    # Check which CIKs are already cached
    needed_ciks = []
    results: dict[int, dict] = {}
    for cik in ciks:
        cached = cache_dir / _cik_filename(cik)
        if cached.exists():
            results[cik] = json.loads(cached.read_text())
        else:
            needed_ciks.append(cik)

    if not needed_ciks:
        return results

    # Download ZIP if not cached
    if not zip_path.exists():
        _download_bulk_zip(zip_path, user_agent, bulk_url)

    # Selectively extract only needed CIKs
    with zipfile.ZipFile(zip_path) as zf:
        for cik in needed_ciks:
            filename = _cik_filename(cik)
            try:
                raw_bytes = zf.read(filename)
            except KeyError:
                raise KeyError(
                    f"CIK {cik} ({filename}) not found in bulk ZIP. "
                    f"Available files: {len(zf.namelist())}"
                )

            data = json.loads(raw_bytes)
            # Cache extracted JSON
            (cache_dir / filename).write_text(json.dumps(data))
            results[cik] = data

    return results


def _download_bulk_zip(zip_path: Path, user_agent: str, bulk_url: str) -> None:
    """Stream-download the bulk ZIP to disk."""
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream(
        "GET",
        bulk_url,
        headers={"User-Agent": user_agent},
        timeout=600.0,
        follow_redirects=True,
    ) as response:
        response.raise_for_status()
        with open(zip_path, "wb") as f:
            for chunk in response.iter_bytes(chunk_size=8192):
                f.write(chunk)
