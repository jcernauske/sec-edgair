"""Promote period-over-period growth to Iceberg with dedup guard.

Same pattern as financial_ratios promote: get_catalog, create_test_table,
check existing record_ids, append_data.
"""

from __future__ import annotations

from pathlib import Path

from src.infra.iceberg_setup import append_data, create_test_table, get_catalog, read_with_duckdb

from .config import CATALOG_PATH, NAMESPACE, TABLE_NAME, WAREHOUSE_PATH
from .schema import PERIOD_OVER_PERIOD_SCHEMA


def promote_period_over_period(
    records: list[dict],
    *,
    warehouse_path: str | Path | None = None,
    catalog_path: str | Path | None = None,
) -> dict:
    """Write period-over-period growth records to Iceberg table.

    Dedup guard: skips record_ids that already exist in the table.
    """
    wh = Path(warehouse_path) if warehouse_path else WAREHOUSE_PATH
    cp = Path(catalog_path) if catalog_path else CATALOG_PATH

    if not records:
        return {"table": f"{NAMESPACE}.{TABLE_NAME}", "promoted": 0}

    catalog = get_catalog(wh, cp)
    table = create_test_table(catalog, NAMESPACE, TABLE_NAME, PERIOD_OVER_PERIOD_SCHEMA)

    # Uniqueness check: skip record_ids that already exist
    existing_ids: set[str] = set()
    try:
        existing = read_with_duckdb(table)
        existing_ids = {r["record_id"] for r in existing}
    except Exception:
        pass

    original_count = len(records)
    records = [r for r in records if r["record_id"] not in existing_ids]
    skipped = original_count - len(records)
    if skipped:
        print(f"Skipping {skipped} record(s) already in period_over_period")

    if not records:
        return {
            "table": f"{NAMESPACE}.{TABLE_NAME}",
            "promoted": 0,
            "skipped_duplicates": skipped,
        }

    snapshot_id = append_data(table, records)

    return {
        "table": f"{NAMESPACE}.{TABLE_NAME}",
        "promoted": len(records),
        "skipped_duplicates": skipped,
        "snapshot_id": snapshot_id,
    }
