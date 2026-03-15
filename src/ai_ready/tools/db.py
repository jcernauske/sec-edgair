"""DuckDB connection and Iceberg table loading for AI-Ready tools.

Loads all 5 consumable Iceberg tables into an in-memory DuckDB instance
via PyIceberg scan -> Arrow -> DuckDB register. Data is cached for the
lifetime of the process (~125K rows fits easily in memory).
"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from src.infra.iceberg_setup import get_catalog

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
WAREHOUSE_PATH = PROJECT_ROOT / "data" / "consumable" / "iceberg_warehouse"
CATALOG_PATH = PROJECT_ROOT / "data" / "catalog" / "catalog.db"

# Tables to load into DuckDB
CONSUMABLE_TABLES = [
    "company_financials",
    "financial_ratios",
    "period_over_period",
    "peer_comparison",
    "amendment_analysis",
]

_db: duckdb.DuckDBPyConnection | None = None
_arrow_tables: dict = {}  # Keep Arrow table references alive for DuckDB


def get_db() -> duckdb.DuckDBPyConnection:
    """Return a cached DuckDB connection with all consumable tables registered.

    Tables are loaded once via PyIceberg scan -> Arrow and registered as
    views in DuckDB for efficient SQL querying.
    """
    global _db, _arrow_tables

    if _db is not None:
        return _db

    catalog = get_catalog(WAREHOUSE_PATH, CATALOG_PATH)
    con = duckdb.connect()

    for table_name in CONSUMABLE_TABLES:
        identifier = f"consumable.{table_name}"
        try:
            iceberg_table = catalog.load_table(identifier)
            arrow_table = iceberg_table.scan().to_arrow()
            # Store reference to keep Arrow table alive
            _arrow_tables[table_name] = arrow_table
            con.register(table_name, arrow_table)
            row_count = len(arrow_table)
            logger.info("Loaded %s: %d rows", table_name, row_count)
        except Exception:
            logger.warning("Failed to load table %s — it may not exist yet", identifier)

    _db = con
    return _db


def reset_db() -> None:
    """Reset the cached DB connection. Used in testing."""
    global _db, _arrow_tables
    if _db is not None:
        _db.close()
    _db = None
    _arrow_tables = {}


def get_table_row_counts() -> dict[str, int]:
    """Return row counts for all loaded tables."""
    con = get_db()
    counts = {}
    for table_name in CONSUMABLE_TABLES:
        try:
            result = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
            counts[table_name] = result[0] if result else 0
        except Exception:
            counts[table_name] = 0
    return counts
