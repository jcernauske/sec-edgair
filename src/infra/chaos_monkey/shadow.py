"""Shadow zone management — copy real data, inject corruptions, never touch originals.

The shadow zone is a complete copy of the raw Iceberg warehouse where
corrupted data gets mixed with clean data. The real raw tables are NEVER modified.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

import pyarrow as pa
from pyiceberg.io.pyarrow import schema_to_pyarrow
from pyiceberg.schema import Schema
from pyiceberg.types import NestedField

from src.infra.chaos_monkey.config import (
    SHADOW_CATALOG_PATH,
    SHADOW_WAREHOUSE_PATH,
    SOURCE_CATALOG_PATH,
    SOURCE_WAREHOUSE_PATH,
)
from src.infra.chaos_monkey.injector import InjectionPlan
from src.infra.iceberg_setup import append_data, get_catalog, get_or_create_table
from src.raw.xbrl_company_facts.schema import XBRL_COMPANY_FACTS_SCHEMA

logger = logging.getLogger(__name__)


def setup_shadow_zone() -> None:
    """Create a fresh shadow zone by copying the real raw warehouse.

    Wipes any existing shadow zone first to ensure a clean slate.
    """
    # Clean slate
    if SHADOW_WAREHOUSE_PATH.exists():
        shutil.rmtree(SHADOW_WAREHOUSE_PATH)
    if SHADOW_CATALOG_PATH.exists():
        SHADOW_CATALOG_PATH.unlink()

    SHADOW_WAREHOUSE_PATH.mkdir(parents=True, exist_ok=True)
    SHADOW_CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Shadow zone created at %s", SHADOW_WAREHOUSE_PATH)


def _relaxed_schema() -> Schema:
    """Return the raw schema with ALL fields nullable.

    The real schema has required=True on many fields, which Iceberg enforces
    at the Parquet level. The shadow zone needs nullable fields so the chaos
    monkey can inject nulls to test completeness DQ rules.
    """
    return Schema(
        *(
            NestedField(
                field_id=f.field_id,
                name=f.name,
                field_type=f.field_type,
                required=False,  # Everything nullable in shadow zone
            )
            for f in XBRL_COMPANY_FACTS_SCHEMA.fields
        )
    )


def copy_real_data_to_shadow() -> tuple[int, list[dict]]:
    """Copy all rows from real raw.xbrl_company_facts into the shadow zone.

    Returns (row_count, rows) — the clean data that was copied.
    """
    # Read from real catalog
    real_catalog = get_catalog(SOURCE_WAREHOUSE_PATH, SOURCE_CATALOG_PATH)
    real_table = real_catalog.load_table("raw.xbrl_company_facts")
    arrow_table = real_table.scan().to_arrow()
    rows = arrow_table.to_pylist()
    row_count = len(rows)

    logger.info("Read %d rows from real raw.xbrl_company_facts", row_count)

    # Write to shadow catalog — use relaxed (all-nullable) schema so the
    # chaos monkey can inject nulls into required fields
    shadow_catalog = get_catalog(SHADOW_WAREHOUSE_PATH, SHADOW_CATALOG_PATH)
    shadow_table = get_or_create_table(
        shadow_catalog, "raw", "xbrl_company_facts", _relaxed_schema()
    )

    if rows:
        append_data(shadow_table, rows)
        logger.info("Copied %d clean rows to shadow zone", row_count)

    return row_count, rows


def inject_corruptions_to_shadow(plan: InjectionPlan) -> int:
    """Append corrupted rows to the shadow zone table.

    Returns the snapshot ID of the injection write.
    """
    shadow_catalog = get_catalog(SHADOW_WAREHOUSE_PATH, SHADOW_CATALOG_PATH)
    shadow_table = shadow_catalog.load_table("raw.xbrl_company_facts")

    if plan.corrupted_rows:
        snapshot_id = append_data(shadow_table, plan.corrupted_rows)
        logger.info(
            "Injected %d corrupted rows into shadow zone (snapshot %d)",
            len(plan.corrupted_rows),
            snapshot_id,
        )
        return snapshot_id

    return 0


def teardown_shadow_zone() -> None:
    """Remove the shadow zone entirely."""
    if SHADOW_WAREHOUSE_PATH.exists():
        shutil.rmtree(SHADOW_WAREHOUSE_PATH)
    if SHADOW_CATALOG_PATH.exists():
        SHADOW_CATALOG_PATH.unlink()
    # Clean up parent dirs if empty
    shadow_root = SHADOW_WAREHOUSE_PATH.parent
    if shadow_root.exists() and not any(shadow_root.iterdir()):
        shadow_root.rmdir()
    logger.info("Shadow zone cleaned up")
