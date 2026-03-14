"""Configuration for entity resolution pipeline."""

from pathlib import Path

from src.config import REQUIRE_HUMAN_APPROVAL  # noqa: F401 — re-exported for local imports

# Confidence threshold — mappings below this ALWAYS require human approval
# regardless of the REQUIRE_HUMAN_APPROVAL toggle
CONFIDENCE_FLOOR = 0.7

# Known companies — CIK → metadata for initial resolution
# These are exact CIK matches from SEC EDGAR with confidence 1.0
KNOWN_ENTITIES: dict[int, dict] = {
    320193: {
        "canonical_name": "Apple Inc.",
        "ticker": "AAPL",
        "sic_code": "3571",
        "fiscal_year_end": "0930",
    },
    19617: {
        "canonical_name": "JPMorgan Chase & Co.",
        "ticker": "JPM",
        "sic_code": "6020",
        "fiscal_year_end": "1231",
    },
    789019: {
        "canonical_name": "Microsoft Corporation",
        "ticker": "MSFT",
        "sic_code": "7372",
        "fiscal_year_end": "0630",
    },
    1018724: {
        "canonical_name": "Amazon.com Inc.",
        "ticker": "AMZN",
        "sic_code": "5961",
        "fiscal_year_end": "1231",
    },
    1652044: {
        "canonical_name": "Alphabet Inc.",
        "ticker": "GOOGL",
        "sic_code": "7372",
        "fiscal_year_end": "1231",
    },
    1326801: {
        "canonical_name": "Meta Platforms Inc.",
        "ticker": "META",
        "sic_code": "7370",
        "fiscal_year_end": "1231",
    },
    1318605: {
        "canonical_name": "Tesla Inc.",
        "ticker": "TSLA",
        "sic_code": "3711",
        "fiscal_year_end": "1231",
    },
    1067983: {
        "canonical_name": "Berkshire Hathaway Inc.",
        "ticker": "BRK.A",
        "sic_code": "6331",
        "fiscal_year_end": "1231",
    },
    200406: {
        "canonical_name": "Johnson & Johnson",
        "ticker": "JNJ",
        "sic_code": "2834",
        "fiscal_year_end": "1231",
    },
    104169: {
        "canonical_name": "Walmart Inc.",
        "ticker": "WMT",
        "sic_code": "5331",
        "fiscal_year_end": "0131",
    },
    34088: {
        "canonical_name": "Exxon Mobil Corporation",
        "ticker": "XOM",
        "sic_code": "2911",
        "fiscal_year_end": "1231",
    },
    1403161: {
        "canonical_name": "Visa Inc.",
        "ticker": "V",
        "sic_code": "7389",
        "fiscal_year_end": "0930",
    },
    731766: {
        "canonical_name": "UnitedHealth Group Incorporated",
        "ticker": "UNH",
        "sic_code": "6324",
        "fiscal_year_end": "1231",
    },
    80424: {
        "canonical_name": "Procter & Gamble Company",
        "ticker": "PG",
        "sic_code": "2841",
        "fiscal_year_end": "0630",
    },
    21344: {
        "canonical_name": "The Coca-Cola Company",
        "ticker": "KO",
        "sic_code": "2086",
        "fiscal_year_end": "1231",
    },
    78003: {
        "canonical_name": "Pfizer Inc.",
        "ticker": "PFE",
        "sic_code": "2834",
        "fiscal_year_end": "1231",
    },
    1065280: {
        "canonical_name": "Netflix Inc.",
        "ticker": "NFLX",
        "sic_code": "7841",
        "fiscal_year_end": "1231",
    },
    886982: {
        "canonical_name": "The Goldman Sachs Group Inc.",
        "ticker": "GS",
        "sic_code": "6211",
        "fiscal_year_end": "1231",
    },
    12927: {
        "canonical_name": "The Boeing Company",
        "ticker": "BA",
        "sic_code": "3721",
        "fiscal_year_end": "1231",
    },
    50863: {
        "canonical_name": "Intel Corporation",
        "ticker": "INTC",
        "sic_code": "3674",
        "fiscal_year_end": "1231",
    },
}

# Paths (relative to project root)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
WAREHOUSE_PATH = PROJECT_ROOT / "data" / "base" / "iceberg_warehouse"
CATALOG_PATH = PROJECT_ROOT / "data" / "catalog" / "catalog.db"
STAGING_DIR = PROJECT_ROOT / "governance" / "entity-resolution"
STAGING_FILE = STAGING_DIR / "proposed-mappings.json"
ARCHIVE_DIR = STAGING_DIR / "archive"
