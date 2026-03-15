"""Configuration for XBRL Company Facts ingestion."""

import os
from pathlib import Path

# Companies — CIK → company name
DEFAULT_CIKS: dict[int, str] = {
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

# SEC EDGAR requires an identifying User-Agent.
# Set SEC_EDGAIR_USER_AGENT in .env or environment (e.g. "SEC-EDGAIR you@example.com")
USER_AGENT = os.environ.get("SEC_EDGAIR_USER_AGENT", "SEC-EDGAIR (no contact email set)")

# Rate limiting: SEC allows ≤10 requests/second
RATE_LIMIT_SLEEP = 0.1

# Paths (relative to project root)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
JSON_CACHE_DIR = PROJECT_ROOT / "data" / "raw" / "json_cache"
WAREHOUSE_PATH = PROJECT_ROOT / "data" / "raw" / "iceberg_warehouse"
CATALOG_PATH = PROJECT_ROOT / "data" / "catalog" / "catalog.db"

# SEC EDGAR endpoints
API_URL_TEMPLATE = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik_padded}.json"
BULK_ZIP_URL = "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip"
