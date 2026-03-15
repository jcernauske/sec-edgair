"""Configuration for consumable peer comparison pipeline."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Warehouse paths (shared consumable zone)
WAREHOUSE_PATH = PROJECT_ROOT / "data" / "consumable" / "iceberg_warehouse"
CATALOG_PATH = PROJECT_ROOT / "data" / "catalog" / "catalog.db"

# Table identifiers
NAMESPACE = "consumable"
TABLE_NAME = "peer_comparison"

# Grain fields for record_id hash
RECORD_ID_GRAIN = ("cik", "metric_id", "fiscal_year", "fiscal_period", "metric_source")

# Minimum companies in a sector group for peer comparison
MIN_PEER_COUNT = 2

# Agent identity
AGENT_ID = "@peer-comparison"
