"""Configuration for consumable period-over-period growth pipeline."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Warehouse paths (shared with company_financials — same consumable zone)
WAREHOUSE_PATH = PROJECT_ROOT / "data" / "consumable" / "iceberg_warehouse"
CATALOG_PATH = PROJECT_ROOT / "data" / "catalog" / "catalog.db"

# Table identifiers
NAMESPACE = "consumable"
TABLE_NAME = "period_over_period"

# Grain fields for record_id hash
RECORD_ID_GRAIN = ("cik", "business_term_id", "fiscal_year", "fiscal_period", "growth_type")

# Agent identity
AGENT_ID = "@period-over-period"

# ---------------------------------------------------------------------------
# Growth type definitions
# ---------------------------------------------------------------------------

GROWTH_TYPES = [
    {
        "growth_type": "yoy_change",
        "description": "Year-over-year absolute change",
        "lookback_years": 1,
        "requires_positive_base": False,
        "requires_nonzero_base": False,
    },
    {
        "growth_type": "yoy_pct_change",
        "description": "Year-over-year percentage change",
        "lookback_years": 1,
        "requires_positive_base": False,
        "requires_nonzero_base": True,
    },
    {
        "growth_type": "cagr_5yr",
        "description": "5-year compound annual growth rate",
        "lookback_years": 5,
        "requires_positive_base": True,
        "requires_nonzero_base": True,
    },
]

# Quick lookup
GROWTH_BY_TYPE = {g["growth_type"]: g for g in GROWTH_TYPES}
