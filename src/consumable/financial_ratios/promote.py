"""Promote financial ratios to Iceberg with dedup guard.

Same pattern as company_financials promote: get_catalog, get_or_create_table,
check existing record_ids, append_data.
"""

from __future__ import annotations

from pathlib import Path

from src.infra.iceberg_setup import append_data, filter_existing_records, get_or_create_table, get_catalog

from .config import CATALOG_PATH, NAMESPACE, TABLE_NAME, WAREHOUSE_PATH
from .schema import FINANCIAL_RATIOS_SCHEMA


def promote_financial_ratios(
    records: list[dict],
    *,
    warehouse_path: str | Path | None = None,
    catalog_path: str | Path | None = None,
) -> dict:
    """Write financial ratio records to Iceberg table.

    Dedup guard: skips record_ids that already exist in the table.
    """
    wh = Path(warehouse_path) if warehouse_path else WAREHOUSE_PATH
    cp = Path(catalog_path) if catalog_path else CATALOG_PATH

    if not records:
        return {"table": f"{NAMESPACE}.{TABLE_NAME}", "promoted": 0}

    catalog = get_catalog(wh, cp)
    table = get_or_create_table(catalog, NAMESPACE, TABLE_NAME, FINANCIAL_RATIOS_SCHEMA)

    # Dedup via DuckDB anti-join (scalable — reads only record_id column)
    records, skipped = filter_existing_records(table, records)
    if skipped:
        print(f"Skipping {skipped} record(s) already in financial_ratios")

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
