"""Promote financial facts, fiscal calendar, and amendment tracking to Iceberg.

No staging/approval gate — the join is deterministic given already-approved
entity and concept mappings.
"""

from __future__ import annotations

from pathlib import Path

from src.infra.iceberg_setup import append_data, create_test_table, get_catalog

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
) -> dict:
    """Write financial facts to Iceberg table."""
    wh = Path(warehouse_path) if warehouse_path else WAREHOUSE_PATH
    cp = Path(catalog_path) if catalog_path else CATALOG_PATH

    if not facts:
        return {"table": f"{NAMESPACE}.{FINANCIAL_FACTS_TABLE}", "promoted": 0}

    catalog = get_catalog(wh, cp)
    table = create_test_table(catalog, NAMESPACE, FINANCIAL_FACTS_TABLE, FINANCIAL_FACTS_SCHEMA)
    snapshot_id = append_data(table, facts)

    return {
        "table": f"{NAMESPACE}.{FINANCIAL_FACTS_TABLE}",
        "promoted": len(facts),
        "snapshot_id": snapshot_id,
    }


def promote_fiscal_calendar(
    entries: list[dict],
    *,
    warehouse_path: str | Path | None = None,
    catalog_path: str | Path | None = None,
) -> dict:
    """Write fiscal calendar entries to Iceberg table."""
    wh = Path(warehouse_path) if warehouse_path else WAREHOUSE_PATH
    cp = Path(catalog_path) if catalog_path else CATALOG_PATH

    if not entries:
        return {"table": f"{NAMESPACE}.{FISCAL_CALENDAR_TABLE}", "promoted": 0}

    catalog = get_catalog(wh, cp)
    table = create_test_table(catalog, NAMESPACE, FISCAL_CALENDAR_TABLE, FISCAL_CALENDAR_SCHEMA)
    snapshot_id = append_data(table, entries)

    return {
        "table": f"{NAMESPACE}.{FISCAL_CALENDAR_TABLE}",
        "promoted": len(entries),
        "snapshot_id": snapshot_id,
    }


def promote_amendment_tracking(
    entries: list[dict],
    *,
    warehouse_path: str | Path | None = None,
    catalog_path: str | Path | None = None,
) -> dict:
    """Write amendment tracking entries to Iceberg table."""
    wh = Path(warehouse_path) if warehouse_path else WAREHOUSE_PATH
    cp = Path(catalog_path) if catalog_path else CATALOG_PATH

    if not entries:
        return {"table": f"{NAMESPACE}.{AMENDMENT_TRACKING_TABLE}", "promoted": 0}

    catalog = get_catalog(wh, cp)
    table = create_test_table(catalog, NAMESPACE, AMENDMENT_TRACKING_TABLE, AMENDMENT_TRACKING_SCHEMA)
    snapshot_id = append_data(table, entries)

    return {
        "table": f"{NAMESPACE}.{AMENDMENT_TRACKING_TABLE}",
        "promoted": len(entries),
        "snapshot_id": snapshot_id,
    }
