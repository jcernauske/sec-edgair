"""Promote amendment analysis to Iceberg with dedup guard.

Same pattern as other consumable promote modules: get_catalog, get_or_create_table,
check existing record_ids, append_data.
"""

from __future__ import annotations

import time
from pathlib import Path

from src.infra.iceberg_setup import append_data, filter_existing_records, get_or_create_table, get_catalog
from src.infra.lineage import emit_complete, emit_fail, emit_start

from .config import CATALOG_PATH, NAMESPACE, TABLE_NAME, WAREHOUSE_PATH
from .schema import AMENDMENT_ANALYSIS_SCHEMA


def promote_amendment_analysis(
    records: list[dict],
    *,
    warehouse_path: str | Path | None = None,
    catalog_path: str | Path | None = None,
) -> dict:
    """Write amendment analysis records to Iceberg table.

    Dedup guard: skips record_ids that already exist in the table.
    """
    run_id = emit_start(
        job_name="consumable.amendment_analysis",
        input_tables=["base.amendment_tracking", "base.conformed_facts"],
        output_table="consumable.amendment_analysis",
        producer="src/consumable/amendment_analysis/promote.py",
    )
    start_time = time.monotonic()
    try:
        wh = Path(warehouse_path) if warehouse_path else WAREHOUSE_PATH
        cp = Path(catalog_path) if catalog_path else CATALOG_PATH

        if not records:
            emit_complete(
                run_id=run_id, job_name="consumable.amendment_analysis",
                output_table="consumable.amendment_analysis",
                producer="src/consumable/amendment_analysis/promote.py",
                row_count=0, duration_ms=int((time.monotonic() - start_time) * 1000),
            )
            return {"table": f"{NAMESPACE}.{TABLE_NAME}", "promoted": 0}

        catalog = get_catalog(wh, cp)
        table = get_or_create_table(catalog, NAMESPACE, TABLE_NAME, AMENDMENT_ANALYSIS_SCHEMA)

        # Dedup via DuckDB anti-join (scalable — reads only record_id column)
        records, skipped = filter_existing_records(table, records)
        if skipped:
            print(f"Skipping {skipped} record(s) already in amendment_analysis")

        if not records:
            emit_complete(
                run_id=run_id, job_name="consumable.amendment_analysis",
                output_table="consumable.amendment_analysis",
                producer="src/consumable/amendment_analysis/promote.py",
                row_count=0, skipped_duplicates=skipped,
                duration_ms=int((time.monotonic() - start_time) * 1000),
            )
            return {
                "table": f"{NAMESPACE}.{TABLE_NAME}",
                "promoted": 0,
                "skipped_duplicates": skipped,
            }

        snapshot_id = append_data(table, records)

        result = {
            "table": f"{NAMESPACE}.{TABLE_NAME}",
            "promoted": len(records),
            "skipped_duplicates": skipped,
            "snapshot_id": snapshot_id,
        }

        emit_complete(
            run_id=run_id, job_name="consumable.amendment_analysis",
            output_table="consumable.amendment_analysis",
            producer="src/consumable/amendment_analysis/promote.py",
            snapshot_id=snapshot_id, row_count=len(records), skipped_duplicates=skipped,
            duration_ms=int((time.monotonic() - start_time) * 1000),
        )
        return result
    except Exception as e:
        emit_fail(
            run_id=run_id, job_name="consumable.amendment_analysis",
            output_table="consumable.amendment_analysis",
            producer="src/consumable/amendment_analysis/promote.py",
            error_message=str(e),
            duration_ms=int((time.monotonic() - start_time) * 1000),
        )
        raise
