"""Configuration for base.conformed_facts pipeline.

Reads collision resolution rules from the governance artifact
(governance/conformation/concept-priority-rules.json) rather than
hardcoding them in Python. Falls back to empty dicts if the file
is missing (should never happen in a properly configured environment).
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Warehouse paths
WAREHOUSE_PATH = PROJECT_ROOT / "data" / "base" / "iceberg_warehouse"
CATALOG_PATH = PROJECT_ROOT / "data" / "catalog" / "catalog.db"

# Table identifiers
NAMESPACE = "base"
TABLE_NAME = "conformed_facts"

# Source tables
FINANCIAL_FACTS_TABLE = "base.financial_facts"
ENTITY_MAPPINGS_TABLE = "base.entity_mappings"

# Grain fields for conformed_id hash
CONFORMED_ID_GRAIN = ("cik", "business_term_id", "fiscal_year", "fiscal_period")

# Agent identity
AGENT_ID = "@conformed-facts"

# ---------------------------------------------------------------------------
# Load concept collision resolution rules from governance artifact
# ---------------------------------------------------------------------------

_RULES_PATH = PROJECT_ROOT / "governance" / "conformation" / "concept-priority-rules.json"


def _load_rules() -> dict:
    """Load concept-priority-rules.json and extract PRIMARY_CONCEPTS and PRIMARY_UNIT."""
    if not _RULES_PATH.exists():
        return {}
    with open(_RULES_PATH) as f:
        return json.load(f)


_RULES_DATA = _load_rules()
_RULES = _RULES_DATA.get("rules", {})

PRIMARY_CONCEPTS: dict[str, list[str]] = {
    bt_id: rule["primary_concepts"]
    for bt_id, rule in _RULES.items()
}

PRIMARY_UNIT: dict[str, str] = {
    bt_id: rule["primary_unit"]
    for bt_id, rule in _RULES.items()
}

# ---------------------------------------------------------------------------
# Legacy ID translation: CDE-XXX -> BT-XXX
# Existing Iceberg data still contains CDE-XXX values from before the
# governance model alignment refactor. This mapping normalizes them on read.
# Safe to remove once base tables are rebuilt from raw.
# ---------------------------------------------------------------------------

LEGACY_CDE_TO_BT: dict[str, str] = {
    "CDE-007": "BT-024", "CDE-008": "BT-027", "CDE-009": "BT-028",
    "CDE-010": "BT-029", "CDE-011": "BT-030", "CDE-012": "BT-031",
    "CDE-013": "BT-032", "CDE-014": "BT-033", "CDE-015": "BT-022",
    "CDE-016": "BT-034", "CDE-017": "BT-035", "CDE-018": "BT-036",
    "CDE-019": "BT-023", "CDE-020": "BT-037", "CDE-021": "BT-038",
    "CDE-022": "BT-039", "CDE-023": "BT-040", "CDE-024": "BT-041",
    "CDE-025": "BT-042", "CDE-026": "BT-043", "CDE-027": "BT-044",
    "CDE-028": "BT-045", "CDE-029": "BT-046", "CDE-030": "BT-047",
    "CDE-031": "BT-048",
}
