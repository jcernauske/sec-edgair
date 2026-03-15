"""Configuration for XBRL Company Facts ingestion.

Loads values from domain/manifest.yaml via the domain loader.
Falls back to hardcoded defaults if the manifest doesn't exist,
ensuring backwards compatibility during the transition.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Try to load from domain manifest
_source_config = None
try:
    from src.domain_loader import get_source, load_manifest

    _manifest = load_manifest()
    _source_config = get_source(_manifest, "xbrl_company_facts")
except (FileNotFoundError, ImportError, KeyError):
    logger.debug("Domain manifest not available, using hardcoded defaults")


def _get_source_field(field: str, default):
    """Get a field from the source config, falling back to default."""
    if _source_config is None:
        return default
    return getattr(_source_config, field, default)


# Companies — CIK -> company name
DEFAULT_CIKS: dict[int, str] = (
    _source_config.entities if _source_config else {
        320193: "Apple Inc.",
        19617: "JPMorgan Chase & Co.",
        789019: "Microsoft Corp.",
        1018724: "Amazon.com Inc.",
        1652044: "Alphabet Inc.",
        1326801: "Meta Platforms Inc.",
        1318605: "Tesla Inc.",
        1067983: "Berkshire Hathaway Inc.",
        200406: "Johnson & Johnson",
        104169: "Walmart Inc.",
        34088: "Exxon Mobil Corp.",
        1403161: "Visa Inc.",
        731766: "UnitedHealth Group Inc.",
        80424: "Procter & Gamble Co.",
        21344: "Coca-Cola Co.",
        78003: "Pfizer Inc.",
        1065280: "Netflix Inc.",
        886982: "Goldman Sachs Group Inc.",
        12927: "Boeing Co.",
        50863: "Intel Corp.",
    }
)

# SEC EDGAR requires an identifying User-Agent.
USER_AGENT = os.environ.get("SEC_EDGAIR_USER_AGENT", "SEC-EDGAIR (no contact email set)")

# Rate limiting: SEC allows <=10 requests/second
_fetch_config = _source_config.fetch.get("api", {}) if _source_config else {}
RATE_LIMIT_SLEEP = _fetch_config.get("rate_limit_seconds", 0.1)

# Paths
JSON_CACHE_DIR = _source_config.cache_dir if _source_config else PROJECT_ROOT / "data" / "raw" / "json_cache"
WAREHOUSE_PATH = PROJECT_ROOT / "data" / "raw" / "iceberg_warehouse"
CATALOG_PATH = PROJECT_ROOT / "data" / "catalog" / "catalog.db"

# SEC EDGAR endpoints
_api_config = _source_config.fetch.get("api", {}) if _source_config else {}
_bulk_config = _source_config.fetch.get("bulk", {}) if _source_config else {}
API_URL_TEMPLATE = _api_config.get(
    "url_template",
    "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik_padded}.json",
)
BULK_ZIP_URL = _bulk_config.get(
    "url",
    "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip",
)
