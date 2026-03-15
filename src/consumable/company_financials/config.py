"""Configuration for consumable company financials pipeline.

Business logic (collision resolution, unit filtering, supersession) now lives
in the base zone (src/base/conformed_facts/). This config retains only
presentation-layer settings and PRIMARY_UNIT (used by AI-Ready formatting).
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Warehouse paths
WAREHOUSE_PATH = PROJECT_ROOT / "data" / "consumable" / "iceberg_warehouse"
CATALOG_PATH = PROJECT_ROOT / "data" / "catalog" / "catalog.db"

# Table identifiers
NAMESPACE = "consumable"
TABLE_NAME = "company_financials"

# Grain fields for record_id hash
RECORD_ID_GRAIN = ("cik", "business_term_id", "fiscal_year", "fiscal_period")

# Agent identity
AGENT_ID = "@company-financials"

# ---------------------------------------------------------------------------
# Primary Unit: expected measurement unit per business term category
# USD for dollar amounts, USD/shares for per-share values
# Retained here because AI-Ready formatting (financial_tools.py) references it.
# Authoritative source: governance/conformation/concept-priority-rules.json
# ---------------------------------------------------------------------------

PRIMARY_UNIT: dict[str, str] = {
    # Balance Sheet
    "BT-024": "USD",
    "BT-027": "USD",
    "BT-028": "USD",
    "BT-029": "USD",
    "BT-030": "USD",
    "BT-031": "USD",
    "BT-032": "USD",
    "BT-033": "USD",
    # Income Statement
    "BT-022": "USD",
    "BT-034": "USD",
    "BT-035": "USD",
    "BT-036": "USD",
    "BT-023": "USD",
    "BT-037": "USD",
    "BT-038": "USD",
    "BT-039": "USD",
    # Cash Flow
    "BT-040": "USD",
    "BT-041": "USD",
    "BT-042": "USD",
    "BT-043": "USD",
    # Per-Share
    "BT-044": "USD/shares",
    "BT-045": "USD/shares",
    "BT-046": "USD/shares",
    # Other
    "BT-047": "USD",
    "BT-048": "USD",
}
