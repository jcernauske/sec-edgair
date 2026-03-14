"""Configuration for base financial facts model pipeline."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Warehouse paths
WAREHOUSE_PATH = PROJECT_ROOT / "data" / "base" / "iceberg_warehouse"
RAW_WAREHOUSE_PATH = PROJECT_ROOT / "data" / "raw" / "iceberg_warehouse"
CATALOG_PATH = PROJECT_ROOT / "data" / "catalog" / "catalog.db"

# Table identifiers
NAMESPACE = "base"
FINANCIAL_FACTS_TABLE = "financial_facts"
FISCAL_CALENDAR_TABLE = "fiscal_calendar"
AMENDMENT_TRACKING_TABLE = "amendment_tracking"

# Source tables
RAW_TABLE = "raw.xbrl_company_facts"
ENTITY_MAPPINGS_TABLE = "base.entity_mappings"
CONCEPT_MAPPINGS_TABLE = "base.concept_mappings"

# Grain fields for supersession grouping
SUPERSESSION_GRAIN = ("cik", "concept", "unit", "start_date", "end_date")

# Grain fields for fact_id hash
FACT_ID_GRAIN = ("cik", "concept", "unit", "start_date", "end_date", "accession_number")

# Grain fields for calendar_id hash
CALENDAR_ID_GRAIN = ("cik", "fiscal_year", "fiscal_period")

# Agent identity
AGENT_ID = "@financial-facts-model"
