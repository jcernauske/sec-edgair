"""Configuration for consumable financial ratios pipeline."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Warehouse paths (shared with company_financials — same consumable zone)
WAREHOUSE_PATH = PROJECT_ROOT / "data" / "consumable" / "iceberg_warehouse"
CATALOG_PATH = PROJECT_ROOT / "data" / "catalog" / "catalog.db"

# Table identifiers
NAMESPACE = "consumable"
TABLE_NAME = "financial_ratios"

# Grain fields for record_id hash
RECORD_ID_GRAIN = ("cik", "ratio_id", "fiscal_year", "fiscal_period")

# Agent identity
AGENT_ID = "@financial-ratios"

# ---------------------------------------------------------------------------
# Ratio definitions: each ratio is a numerator/denominator pair of business terms
# ---------------------------------------------------------------------------

RATIO_DEFINITIONS = [
    {
        "ratio_id": "RATIO-001",
        "ratio_name": "Gross Margin",
        "numerator_bt_id": "BT-035",
        "denominator_bt_id": "BT-022",
        "abs_numerator": False,
    },
    {
        "ratio_id": "RATIO-002",
        "ratio_name": "Operating Margin",
        "numerator_bt_id": "BT-036",
        "denominator_bt_id": "BT-022",
        "abs_numerator": False,
    },
    {
        "ratio_id": "RATIO-003",
        "ratio_name": "Net Margin",
        "numerator_bt_id": "BT-023",
        "denominator_bt_id": "BT-022",
        "abs_numerator": False,
    },
    {
        "ratio_id": "RATIO-004",
        "ratio_name": "Debt-to-Equity",
        "numerator_bt_id": "BT-027",
        "denominator_bt_id": "BT-028",
        "abs_numerator": False,
    },
    {
        "ratio_id": "RATIO-005",
        "ratio_name": "R&D Intensity",
        "numerator_bt_id": "BT-038",
        "denominator_bt_id": "BT-022",
        "abs_numerator": False,
    },
    {
        "ratio_id": "RATIO-006",
        "ratio_name": "SGA Ratio",
        "numerator_bt_id": "BT-039",
        "denominator_bt_id": "BT-022",
        "abs_numerator": False,
    },
    {
        "ratio_id": "RATIO-007",
        "ratio_name": "CapEx-to-Revenue",
        "numerator_bt_id": "BT-043",
        "denominator_bt_id": "BT-022",
        "abs_numerator": True,
    },
]

# Quick lookup: ratio_id -> definition
RATIO_BY_ID = {r["ratio_id"]: r for r in RATIO_DEFINITIONS}
