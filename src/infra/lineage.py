"""Runtime lineage event emitter.

Emits OpenLineage-compatible START/COMPLETE/FAIL events to the
governance.lineage_events Iceberg table. Every promote function
calls these to create a runtime audit trail.

Usage:
    from src.infra.lineage import emit_start, emit_complete, emit_fail

CLI:
    python -m src.infra.lineage status          # Latest event per job
    python -m src.infra.lineage generate-docs   # Update governance/lineage/*.json
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
from pyiceberg.schema import Schema
from pyiceberg.types import (
    BooleanType,
    IntegerType,
    LongType,
    NestedField,
    StringType,
    TimestamptzType,
)

from src.config import CATALOG_PATH, PROJECT_ROOT
from src.infra.iceberg_setup import get_catalog, get_or_create_table

logger = logging.getLogger(__name__)

# Governance warehouse (separate from zone warehouses)
GOVERNANCE_WAREHOUSE = PROJECT_ROOT / "data" / "governance" / "iceberg_warehouse"

LINEAGE_EVENTS_SCHEMA = Schema(
    NestedField(field_id=1, name="event_id", field_type=StringType(), required=True),
    NestedField(field_id=2, name="run_id", field_type=StringType(), required=True),
    NestedField(field_id=3, name="event_type", field_type=StringType(), required=True),
    NestedField(field_id=4, name="job_name", field_type=StringType(), required=True),
    NestedField(field_id=5, name="job_namespace", field_type=StringType(), required=True),
    NestedField(field_id=6, name="producer", field_type=StringType(), required=True),
    NestedField(field_id=7, name="input_tables", field_type=StringType(), required=True),
    NestedField(field_id=8, name="output_table", field_type=StringType(), required=True),
    NestedField(field_id=9, name="output_snapshot_id", field_type=LongType(), required=False),
    NestedField(field_id=10, name="row_count", field_type=IntegerType(), required=False),
    NestedField(field_id=11, name="skipped_duplicates", field_type=IntegerType(), required=False),
    NestedField(field_id=12, name="dq_rules_passed", field_type=IntegerType(), required=False),
    NestedField(field_id=13, name="dq_rules_total", field_type=IntegerType(), required=False),
    NestedField(field_id=14, name="dq_p0_passed", field_type=BooleanType(), required=False),
    NestedField(field_id=15, name="duration_ms", field_type=IntegerType(), required=False),
    NestedField(field_id=16, name="error_message", field_type=StringType(), required=False),
    NestedField(field_id=17, name="event_time", field_type=TimestamptzType(), required=True),
)


def _get_lineage_table():
    """Lazily create and return the governance.lineage_events table."""
    catalog = get_catalog(GOVERNANCE_WAREHOUSE, CATALOG_PATH)
    return get_or_create_table(catalog, "governance", "lineage_events", LINEAGE_EVENTS_SCHEMA)


def _write_event(record: dict) -> None:
    """Write a single event record to the lineage_events table."""
    table = _get_lineage_table()
    from pyiceberg.io.pyarrow import schema_to_pyarrow

    arrow_schema = schema_to_pyarrow(table.schema())
    columns = {}
    for field in table.schema().fields:
        columns[field.name] = [record.get(field.name)]
    arrow_table = pa.table(columns, schema=arrow_schema)
    table.append(arrow_table)


def emit_start(
    job_name: str,
    input_tables: list[str],
    output_table: str,
    producer: str,
) -> str:
    """Emit a START event. Returns run_id for pairing with COMPLETE/FAIL.

    Fault-tolerant: logs a warning and returns run_id even if write fails.
    """
    run_id = str(uuid.uuid4())
    try:
        _write_event({
            "event_id": str(uuid.uuid4()),
            "run_id": run_id,
            "event_type": "START",
            "job_name": job_name,
            "job_namespace": "sec-edgair",
            "producer": producer,
            "input_tables": json.dumps(input_tables),
            "output_table": output_table,
            "output_snapshot_id": None,
            "row_count": None,
            "skipped_duplicates": None,
            "dq_rules_passed": None,
            "dq_rules_total": None,
            "dq_p0_passed": None,
            "duration_ms": None,
            "error_message": None,
            "event_time": datetime.now(timezone.utc),
        })
        logger.debug("Lineage START emitted for %s (run_id=%s)", job_name, run_id)
    except Exception:
        logger.warning("Failed to emit lineage START for %s", job_name, exc_info=True)
    return run_id


def emit_complete(
    run_id: str,
    job_name: str,
    output_table: str,
    producer: str,
    snapshot_id: int | None = None,
    row_count: int | None = None,
    skipped_duplicates: int | None = None,
    dq_passed: int | None = None,
    dq_total: int | None = None,
    dq_p0_passed: bool | None = None,
    duration_ms: int | None = None,
) -> None:
    """Emit a COMPLETE event. Fault-tolerant: logs warning on failure."""
    try:
        _write_event({
            "event_id": str(uuid.uuid4()),
            "run_id": run_id,
            "event_type": "COMPLETE",
            "job_name": job_name,
            "job_namespace": "sec-edgair",
            "producer": producer,
            "input_tables": "[]",  # inputs captured in START
            "output_table": output_table,
            "output_snapshot_id": snapshot_id,
            "row_count": row_count,
            "skipped_duplicates": skipped_duplicates,
            "dq_rules_passed": dq_passed,
            "dq_rules_total": dq_total,
            "dq_p0_passed": dq_p0_passed,
            "duration_ms": duration_ms,
            "error_message": None,
            "event_time": datetime.now(timezone.utc),
        })
        logger.debug("Lineage COMPLETE emitted for %s (run_id=%s)", job_name, run_id)
    except Exception:
        logger.warning("Failed to emit lineage COMPLETE for %s", job_name, exc_info=True)


def emit_fail(
    run_id: str,
    job_name: str,
    output_table: str,
    producer: str,
    error_message: str,
    duration_ms: int | None = None,
) -> None:
    """Emit a FAIL event. Fault-tolerant: logs warning on failure."""
    try:
        _write_event({
            "event_id": str(uuid.uuid4()),
            "run_id": run_id,
            "event_type": "FAIL",
            "job_name": job_name,
            "job_namespace": "sec-edgair",
            "producer": producer,
            "input_tables": "[]",
            "output_table": output_table,
            "output_snapshot_id": None,
            "row_count": None,
            "skipped_duplicates": None,
            "dq_rules_passed": None,
            "dq_rules_total": None,
            "dq_p0_passed": None,
            "duration_ms": duration_ms,
            "error_message": error_message[:4000] if error_message else None,
            "event_time": datetime.now(timezone.utc),
        })
        logger.debug("Lineage FAIL emitted for %s (run_id=%s)", job_name, run_id)
    except Exception:
        logger.warning("Failed to emit lineage FAIL for %s", job_name, exc_info=True)


# ---------------------------------------------------------------------------
# CLI: status + generate-docs
# ---------------------------------------------------------------------------

def _read_all_events() -> list[dict]:
    """Read all lineage events from the Iceberg table."""
    import duckdb

    try:
        table = _get_lineage_table()
        arrow_table = table.scan().to_arrow()
        if arrow_table.num_rows == 0:
            return []
        con = duckdb.connect()
        rows = con.sql("SELECT * FROM arrow_table ORDER BY event_time DESC").fetchall()
        columns = [f.name for f in table.schema().fields]
        return [dict(zip(columns, row)) for row in rows]
    except Exception:
        logger.warning("Could not read lineage events", exc_info=True)
        return []


def cmd_status() -> None:
    """Show the latest event per job_name."""
    import duckdb

    try:
        table = _get_lineage_table()
        arrow_table = table.scan().to_arrow()
    except Exception as e:
        print(f"No lineage events table found: {e}")
        return

    if arrow_table.num_rows == 0:
        print("No lineage events recorded yet.")
        return

    con = duckdb.connect()
    rows = con.sql("""
        WITH ranked AS (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY job_name ORDER BY event_time DESC) AS rn
            FROM arrow_table
            WHERE event_type IN ('COMPLETE', 'FAIL')
        )
        SELECT job_name, event_time, row_count, duration_ms, event_type, error_message
        FROM ranked
        WHERE rn = 1
        ORDER BY job_name
    """).fetchall()

    if not rows:
        print("No COMPLETE or FAIL events recorded yet.")
        return

    # Print formatted table
    print(f"{'Job':<40} {'Last Run':<22} {'Rows':>8} {'Duration':>10} {'Status':<10}")
    print("-" * 94)
    for row in rows:
        job_name, event_time, row_count, duration_ms, event_type, error_msg = row
        time_str = event_time.strftime("%Y-%m-%d %H:%M:%S") if event_time else "N/A"
        rows_str = str(row_count) if row_count is not None else "N/A"
        dur_str = f"{duration_ms}ms" if duration_ms is not None else "N/A"
        status = event_type
        if event_type == "FAIL" and error_msg:
            status = f"FAIL: {error_msg[:30]}"
        print(f"{job_name:<40} {time_str:<22} {rows_str:>8} {dur_str:>10} {status:<10}")


def cmd_generate_docs() -> None:
    """Update governance/lineage/*.json files with runtime data from lineage events."""
    import duckdb

    try:
        table = _get_lineage_table()
        arrow_table = table.scan().to_arrow()
    except Exception as e:
        print(f"No lineage events table found: {e}")
        return

    if arrow_table.num_rows == 0:
        print("No lineage events to generate docs from.")
        return

    con = duckdb.connect()
    # Get latest COMPLETE event per job
    rows = con.sql("""
        WITH ranked AS (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY job_name ORDER BY event_time DESC) AS rn
            FROM arrow_table
            WHERE event_type = 'COMPLETE'
        )
        SELECT job_name, event_time, row_count, output_snapshot_id, duration_ms,
               dq_rules_passed, dq_rules_total, dq_p0_passed, run_id
        FROM ranked
        WHERE rn = 1
    """).fetchall()

    if not rows:
        print("No COMPLETE events found.")
        return

    # Map job_name to lineage JSON filename
    job_to_file = {
        "base.conformed_facts": "base-conformed-facts.json",
        "base.financial_facts": "base-financial-facts-model.json",
        "base.fiscal_calendar": "base-financial-facts-model.json",
        "base.amendment_tracking": "base-financial-facts-model.json",
        "base.entity_mappings": "base-entity-resolution.json",
        "base.concept_mappings": "base-tag-normalization.json",
        "consumable.company_financials": "consumable-company-financials.json",
        "consumable.financial_ratios": "consumable-financial-ratios.json",
        "consumable.period_over_period": "consumable-period-over-period.json",
        "consumable.peer_comparison": "consumable-peer-comparison.json",
        "consumable.amendment_analysis": "consumable-amendment-analysis.json",
    }

    lineage_dir = PROJECT_ROOT / "governance" / "lineage"
    updated = 0

    for row in rows:
        job_name, event_time, row_count, snapshot_id, duration_ms, \
            dq_passed, dq_total, dq_p0_passed, run_id = row

        filename = job_to_file.get(job_name)
        if not filename:
            logger.debug("No lineage doc mapping for job %s", job_name)
            continue

        filepath = lineage_dir / filename
        if not filepath.exists():
            logger.debug("Lineage doc not found: %s", filepath)
            continue

        try:
            doc = json.loads(filepath.read_text())
        except (json.JSONDecodeError, OSError):
            logger.warning("Could not parse %s", filepath)
            continue

        # Update the run facets with runtime data
        if isinstance(doc, list) and len(doc) > 0:
            entry = doc[0]
        else:
            entry = doc

        if "run" not in entry:
            entry["run"] = {"runId": run_id}

        run_facets = entry["run"].setdefault("facets", {})
        time_str = event_time.strftime("%Y-%m-%dT%H:%M:%SZ") if event_time else None
        run_facets["secEdgair_runtimeLineage"] = {
            "lastRunId": run_id,
            "lastEventTime": time_str,
            "rowCount": row_count,
            "snapshotId": snapshot_id,
            "durationMs": duration_ms,
            "dqRulesPassed": dq_passed,
            "dqRulesTotal": dq_total,
            "dqP0Passed": dq_p0_passed,
        }

        # Update the top-level eventTime to match runtime
        if time_str:
            entry["eventTime"] = time_str

        filepath.write_text(json.dumps(doc, indent=2) + "\n")
        updated += 1
        print(f"  Updated {filepath.name} with runtime data from {job_name}")

    print(f"\nUpdated {updated} lineage doc(s).")


def main() -> None:
    """CLI entry point."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.infra.lineage <command>")
        print("Commands:")
        print("  status         Show latest event per job")
        print("  generate-docs  Update governance/lineage/*.json from runtime data")
        sys.exit(1)

    command = sys.argv[1]
    if command == "status":
        cmd_status()
    elif command == "generate-docs":
        cmd_generate_docs()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
