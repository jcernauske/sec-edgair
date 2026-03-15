"""Configuration for consumable amendment analysis pipeline."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Warehouse paths (shared consumable zone)
WAREHOUSE_PATH = PROJECT_ROOT / "data" / "consumable" / "iceberg_warehouse"
CATALOG_PATH = PROJECT_ROOT / "data" / "catalog" / "catalog.db"

# Base zone warehouse (for reading amendment_tracking)
BASE_WAREHOUSE_PATH = PROJECT_ROOT / "data" / "base" / "iceberg_warehouse"

# Table identifiers
NAMESPACE = "consumable"
TABLE_NAME = "amendment_analysis"

# Grain fields for record_id hash
RECORD_ID_GRAIN = ("cik", "fiscal_year")

# Agent identity
AGENT_ID = "@amendment-analysis"
