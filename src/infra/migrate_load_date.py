"""One-time migration: add load_date column to all Iceberg tables and backfill.

Iceberg supports schema evolution — adding a column is non-destructive.
Existing rows get load_date backfilled from their nearest timestamp column.

Usage:
    python -m src.infra.migrate_load_date
"""

from __future__ import annotations

import datetime

import pyarrow as pa
from pyiceberg.io.pyarrow import schema_to_pyarrow
from pyiceberg.schema import Schema
from pyiceberg.types import DateType, NestedField

from src.infra.iceberg_setup import get_catalog, read_with_duckdb
from src.config import CATALOG_PATH, WAREHOUSE_PATH


def _add_load_date_column(table, next_field_id: int) -> None:
    """Add load_date column to an Iceberg table via schema evolution."""
    existing_names = {f.name for f in table.schema().fields}
    if "load_date" in existing_names:
        print(f"  load_date already exists, skipping schema evolution")
        return

    with table.update_schema() as update:
        update.add_column("load_date", DateType())


def _backfill_table(table, timestamp_column: str, fallback_date: datetime.date) -> int:
    """Read all rows, set load_date from timestamp column, overwrite table."""
    rows = read_with_duckdb(table)
    if not rows:
        print(f"  empty table, nothing to backfill")
        return 0

    # Check if already backfilled
    if all(r.get("load_date") is not None for r in rows):
        print(f"  all {len(rows)} rows already have load_date")
        return 0

    for r in rows:
        if r.get("load_date") is None:
            ts = r.get(timestamp_column)
            if ts is not None and hasattr(ts, "date"):
                r["load_date"] = ts.date()
            elif isinstance(ts, datetime.date):
                r["load_date"] = ts
            else:
                r["load_date"] = fallback_date

    # Overwrite with backfilled data
    arrow_schema = schema_to_pyarrow(table.schema())
    columns = {}
    for field in table.schema().fields:
        columns[field.name] = [r.get(field.name) for r in rows]
    arrow_table = pa.table(columns, schema=arrow_schema)
    table.overwrite(arrow_table)

    return len(rows)


TABLES = [
    ("raw.xbrl_company_facts", "ingested_at"),
    ("base.entity_mappings", "approved_at"),
    ("base.entity_resolution_audit", "timestamp"),
    ("base.concept_mappings", "mapped_at"),
    ("base.tag_normalization_audit", "timestamp"),
    ("base.financial_facts", "promoted_at"),
    ("base.fiscal_calendar", None),  # No timestamp — use fallback
    ("base.amendment_tracking", "detected_at"),
]


def main() -> None:
    catalog = get_catalog(WAREHOUSE_PATH, CATALOG_PATH)
    today = datetime.date.today()

    for table_id, ts_column in TABLES:
        print(f"\n--- {table_id} ---")
        try:
            table = catalog.load_table(table_id)
        except Exception as e:
            print(f"  table not found: {e}")
            continue

        # Get the next field_id
        max_id = max(f.field_id for f in table.schema().fields)
        _add_load_date_column(table, max_id + 1)

        # Reload table after schema change
        table = catalog.load_table(table_id)

        ts_col = ts_column or "none"
        count = _backfill_table(table, ts_col if ts_column else "", today)
        print(f"  backfilled {count} rows (timestamp source: {ts_col})")

    print("\nMigration complete.")


if __name__ == "__main__":
    main()
