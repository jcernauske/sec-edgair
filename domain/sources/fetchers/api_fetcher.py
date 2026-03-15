"""Per-company API fetcher for SEC EDGAR XBRL Company Facts.

Downloads JSON for a single CIK, caches to disk, respects rate limits.

This is the domain pack version — config values are passed as arguments,
not imported from a hardcoded Python config module.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import httpx


def _cache_path(cik: int, cache_dir: Path) -> Path:
    return cache_dir / f"CIK{cik:010d}.json"


def fetch_company_facts(
    cik: int,
    cache_dir: Path,
    user_agent: str,
    url_template: str = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik_padded}.json",
    rate_limit_sleep: float = 0.1,
) -> dict:
    """Fetch Company Facts JSON for a single CIK.

    Returns cached data if available. Otherwise fetches from SEC EDGAR,
    caches the response, and sleeps to respect rate limits.

    Raises httpx.HTTPStatusError on 403/429 or other HTTP errors.
    """
    cache_file = _cache_path(cik, cache_dir)

    if cache_file.exists():
        return json.loads(cache_file.read_text())

    cache_dir.mkdir(parents=True, exist_ok=True)

    url = url_template.format(cik_padded=f"{cik:010d}")
    response = httpx.get(
        url,
        headers={"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"},
        timeout=30.0,
        follow_redirects=True,
    )
    response.raise_for_status()

    data = response.json()
    cache_file.write_text(json.dumps(data))

    time.sleep(rate_limit_sleep)
    return data
