"""Promote financial facts, fiscal calendar, and amendment tracking to Iceberg.

No staging/approval gate — the join is deterministic given already-approved
entity and concept mappings.
"""

from __future__ import annotations

import time
from pathlib import Path

from src.infra.dq_runner import validate_after_write
from pyiceberg.exceptions import NoSuchTableError

from src.infra.iceberg_setup import append_data, get_or_create_table, get_catalog, read_with_duckdb
from src.infra.lineage import emit_complete, emit_fail, emit_start

from .config import (
    AMENDMENT_TRACKING_TABLE,
    CATALOG_PATH,
    FINANCIAL_FACTS_TABLE,
    FISCAL_CALENDAR_TABLE,
    NAMESPACE,
    WAREHOUSE_PATH,
)
from .schema import (
    AMENDMENT_TRACKING_SCHEMA,
    FINANCIAL_FACTS_SCHEMA,
    FISCAL_CALENDAR_SCHEMA,
)


def promote_financial_facts(
    facts: list[dict],
    *,
    warehouse_path: str | Path | None = None,
    catalog_path: str | Path | None = None,
    validate: bool = False,
) -> dict:
    """Write financial facts to Iceberg table.

    Args:
        validate: If True, run DQ rules after write. Set False when calling
                  from promote_all (which validates once at the end).
    """
    run_id = emit_start(
        job_name="base.financial_facts",
        input_tables=["raw.xbrl_company_facts", "base.entity_mappings", "base.concept_mappings"],
        output_table="base.financial_facts",
        producer="src/base/financial_facts_model/promote.py",
    )
    start_time = time.monotonic()
    try:
        wh = Path(warehouse_path) if warehouse_path else WAREHOUSE_PATH
        cp = Path(catalog_path) if catalog_path else CATALOG_PATH

        if not facts:
            emit_complete(
                run_id=run_id, job_name="base.financial_facts",
                output_table="base.financial_facts",
                producer="src/base/financial_facts_model/promote.py",
                row_count=0, duration_ms=int((time.monotonic() - start_time) * 1000),
            )
            return {"table": f"{NAMESPACE}.{FINANCIAL_FACTS_TABLE}", "promoted": 0}

        catalog = get_catalog(wh, cp)
        table = get_or_create_table(catalog, NAMESPACE, FINANCIAL_FACTS_TABLE, FINANCIAL_FACTS_SCHEMA)

        # Uniqueness check: skip fact_ids that already exist
        existing_ids = set()
        try:
            existing = read_with_duckdb(table)
            existing_ids = {r["fact_id"] for r in existing}
        except NoSuchTableError:
            pass  # Table doesn't exist yet — first run

        original_count = len(facts)
        facts = [f for f in facts if f["fact_id"] not in existing_ids]
        skipped = original_count - len(facts)
        if skipped:
            print(f"Skipping {skipped} fact(s) already in financial_facts")

        if not facts:
            emit_complete(
                run_id=run_id, job_name="base.financial_facts",
                output_table="base.financial_facts",
                producer="src/base/financial_facts_model/promote.py",
                row_count=0, skipped_duplicates=skipped,
                duration_ms=int((time.monotonic() - start_time) * 1000),
            )
            return {"table": f"{NAMESPACE}.{FINANCIAL_FACTS_TABLE}", "promoted": 0, "skipped_duplicates": skipped}

        snapshot_id = append_data(table, facts)

        result = {
            "table": f"{NAMESPACE}.{FINANCIAL_FACTS_TABLE}",
            "promoted": len(facts),
            "skipped_duplicates": skipped,
            "snapshot_id": snapshot_id,
        }

        if validate:
            dq_result = validate_after_write("base-financial-facts-model", catalog=catalog)
            result["dq_run_id"] = dq_result["run_id"]
            result["dq_passed"] = dq_result["rules_passed"]
            result["dq_total"] = dq_result["rules_total"]

        emit_complete(
            run_id=run_id, job_name="base.financial_facts",
            output_table="base.financial_facts",
            producer="src/base/financial_facts_model/promote.py",
            snapshot_id=result.get("snapshot_id"),
            row_count=result.get("promoted", 0),
            skipped_duplicates=result.get("skipped_duplicates", 0),
            dq_passed=result.get("dq_passed"), dq_total=result.get("dq_total"),
            dq_p0_passed=result.get("dq_passed") == result.get("dq_total") if result.get("dq_total") else None,
            duration_ms=int((time.monotonic() - start_time) * 1000),
        )
        return result
    except Exception as e:
        emit_fail(
            run_id=run_id, job_name="base.financial_facts",
            output_table="base.financial_facts",
            producer="src/base/financial_facts_model/promote.py",
            error_message=str(e),
            duration_ms=int((time.monotonic() - start_time) * 1000),
        )
        raise


def promote_fiscal_calendar(
    entries: list[dict],
    *,
    warehouse_path: str | Path | None = None,
    catalog_path: str | Path | None = None,
    validate: bool = False,
) -> dict:
    """Write fiscal calendar entries to Iceberg table."""
    run_id = emit_start(
        job_name="base.fiscal_calendar",
        input_tables=["base.financial_facts"],
        output_table="base.fiscal_calendar",
        producer="src/base/financial_facts_model/promote.py",
    )
    start_time = time.monotonic()
    try:
        wh = Path(warehouse_path) if warehouse_path else WAREHOUSE_PATH
        cp = Path(catalog_path) if catalog_path else CATALOG_PATH

        if not entries:
            emit_complete(
                run_id=run_id, job_name="base.fiscal_calendar",
                output_table="base.fiscal_calendar",
                producer="src/base/financial_facts_model/promote.py",
                row_count=0, duration_ms=int((time.monotonic() - start_time) * 1000),
            )
            return {"table": f"{NAMESPACE}.{FISCAL_CALENDAR_TABLE}", "promoted": 0}

        catalog = get_catalog(wh, cp)
        table = get_or_create_table(catalog, NAMESPACE, FISCAL_CALENDAR_TABLE, FISCAL_CALENDAR_SCHEMA)

        # Uniqueness check: skip calendar_ids that already exist
        existing_ids = set()
        try:
            existing = read_with_duckdb(table)
            existing_ids = {r["calendar_id"] for r in existing}
        except NoSuchTableError:
            pass  # Table doesn't exist yet — first run

        original_count = len(entries)
        entries = [e for e in entries if e["calendar_id"] not in existing_ids]
        skipped = original_count - len(entries)
        if skipped:
            print(f"Skipping {skipped} entry(ies) already in fiscal_calendar")

        if not entries:
            emit_complete(
                run_id=run_id, job_name="base.fiscal_calendar",
                output_table="base.fiscal_calendar",
                producer="src/base/financial_facts_model/promote.py",
                row_count=0, skipped_duplicates=skipped,
                duration_ms=int((time.monotonic() - start_time) * 1000),
            )
            return {"table": f"{NAMESPACE}.{FISCAL_CALENDAR_TABLE}", "promoted": 0, "skipped_duplicates": skipped}

        snapshot_id = append_data(table, entries)

        result = {
            "table": f"{NAMESPACE}.{FISCAL_CALENDAR_TABLE}",
            "promoted": len(entries),
            "skipped_duplicates": skipped,
            "snapshot_id": snapshot_id,
        }

        if validate:
            dq_result = validate_after_write("base-financial-facts-model", catalog=catalog)
            result["dq_run_id"] = dq_result["run_id"]
            result["dq_passed"] = dq_result["rules_passed"]
            result["dq_total"] = dq_result["rules_total"]

        emit_complete(
            run_id=run_id, job_name="base.fiscal_calendar",
            output_table="base.fiscal_calendar",
            producer="src/base/financial_facts_model/promote.py",
            snapshot_id=result.get("snapshot_id"),
            row_count=result.get("promoted", 0),
            skipped_duplicates=result.get("skipped_duplicates", 0),
            dq_passed=result.get("dq_passed"), dq_total=result.get("dq_total"),
            dq_p0_passed=result.get("dq_passed") == result.get("dq_total") if result.get("dq_total") else None,
            duration_ms=int((time.monotonic() - start_time) * 1000),
        )
        return result
    except Exception as e:
        emit_fail(
            run_id=run_id, job_name="base.fiscal_calendar",
            output_table="base.fiscal_calendar",
            producer="src/base/financial_facts_model/promote.py",
            error_message=str(e),
            duration_ms=int((time.monotonic() - start_time) * 1000),
        )
        raise


def promote_amendment_tracking(
    entries: list[dict],
    *,
    warehouse_path: str | Path | None = None,
    catalog_path: str | Path | None = None,
    validate: bool = False,
) -> dict:
    """Write amendment tracking entries to Iceberg table."""
    run_id = emit_start(
        job_name="base.amendment_tracking",
        input_tables=["base.financial_facts"],
        output_table="base.amendment_tracking",
        producer="src/base/financial_facts_model/promote.py",
    )
    start_time = time.monotonic()
    try:
        wh = Path(warehouse_path) if warehouse_path else WAREHOUSE_PATH
        cp = Path(catalog_path) if catalog_path else CATALOG_PATH

        if not entries:
            emit_complete(
                run_id=run_id, job_name="base.amendment_tracking",
                output_table="base.amendment_tracking",
                producer="src/base/financial_facts_model/promote.py",
                row_count=0, duration_ms=int((time.monotonic() - start_time) * 1000),
            )
            return {"table": f"{NAMESPACE}.{AMENDMENT_TRACKING_TABLE}", "promoted": 0}

        catalog = get_catalog(wh, cp)
        table = get_or_create_table(catalog, NAMESPACE, AMENDMENT_TRACKING_TABLE, AMENDMENT_TRACKING_SCHEMA)

        # Uniqueness check: skip amendment pairs that already exist
        # tracking_id is a UUID generated fresh each run, so dedup on the grain instead
        existing_pairs = set()
        try:
            existing = read_with_duckdb(table)
            existing_pairs = {
                (r["cik"], r["concept"], r["unit"], str(r.get("end_date", "")),
                 r["original_accession"], r["amendment_accession"])
                for r in existing
            }
        except NoSuchTableError:
            pass  # Table doesn't exist yet — first run

        def _pair_key(e: dict) -> tuple:
            return (e["cik"], e["concept"], e["unit"], str(e.get("end_date", "")),
                    e["original_accession"], e["amendment_accession"])

        original_count = len(entries)
        entries = [e for e in entries if _pair_key(e) not in existing_pairs]
        skipped = original_count - len(entries)
        if skipped:
            print(f"Skipping {skipped} entry(ies) already in amendment_tracking")

        if not entries:
            emit_complete(
                run_id=run_id, job_name="base.amendment_tracking",
                output_table="base.amendment_tracking",
                producer="src/base/financial_facts_model/promote.py",
                row_count=0, skipped_duplicates=skipped,
                duration_ms=int((time.monotonic() - start_time) * 1000),
            )
            return {"table": f"{NAMESPACE}.{AMENDMENT_TRACKING_TABLE}", "promoted": 0, "skipped_duplicates": skipped}

        snapshot_id = append_data(table, entries)

        result = {
            "table": f"{NAMESPACE}.{AMENDMENT_TRACKING_TABLE}",
            "promoted": len(entries),
            "skipped_duplicates": skipped,
            "snapshot_id": snapshot_id,
        }

        if validate:
            dq_result = validate_after_write("base-financial-facts-model", catalog=catalog)
            result["dq_run_id"] = dq_result["run_id"]
            result["dq_passed"] = dq_result["rules_passed"]
            result["dq_total"] = dq_result["rules_total"]

        emit_complete(
            run_id=run_id, job_name="base.amendment_tracking",
            output_table="base.amendment_tracking",
            producer="src/base/financial_facts_model/promote.py",
            snapshot_id=result.get("snapshot_id"),
            row_count=result.get("promoted", 0),
            skipped_duplicates=result.get("skipped_duplicates", 0),
            dq_passed=result.get("dq_passed"), dq_total=result.get("dq_total"),
            dq_p0_passed=result.get("dq_passed") == result.get("dq_total") if result.get("dq_total") else None,
            duration_ms=int((time.monotonic() - start_time) * 1000),
        )
        return result
    except Exception as e:
        emit_fail(
            run_id=run_id, job_name="base.amendment_tracking",
            output_table="base.amendment_tracking",
            producer="src/base/financial_facts_model/promote.py",
            error_message=str(e),
            duration_ms=int((time.monotonic() - start_time) * 1000),
        )
        raise
