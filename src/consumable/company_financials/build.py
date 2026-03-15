"""Core build logic for consumable.company_financials.

Reads base.conformed_facts (pre-resolved, one fact per grain) and
base.entity_mappings, adds sector derivation and companies_reporting
aggregate. This is a thin presentation layer — all business logic
(collision resolution, unit filtering, supersession) lives in the
base zone's conformed_facts module.
"""

from __future__ import annotations

import datetime
import hashlib
from pathlib import Path

from src.infra.iceberg_setup import get_catalog, read_with_duckdb

from ..shared import build_sector_lookup
from .config import (
    CATALOG_PATH,
    RECORD_ID_GRAIN,
    WAREHOUSE_PATH,
)


# Base zone warehouse (conformed_facts lives in the base warehouse)
BASE_WAREHOUSE_PATH = Path(__file__).resolve().parents[3] / "data" / "raw" / "iceberg_warehouse"


def _compute_record_id(record: dict) -> str:
    """Deterministic SHA-256 hash of grain fields, truncated to 16 chars."""
    parts = []
    for field in RECORD_ID_GRAIN:
        v = record.get(field)
        parts.append(str(v) if v is not None else "")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def build_company_financials(
    *,
    conformed_facts: list[dict] | None = None,
    entity_mappings: list[dict] | None = None,
    warehouse_path: str | Path | None = None,
    catalog_path: str | Path | None = None,
) -> list[dict]:
    """Build the consumable.company_financials table.

    Reads base.conformed_facts (all business logic already applied)
    and adds sector derivation + companies_reporting aggregate.

    Accepts data as parameters for testability.
    When not provided, reads from Iceberg tables.
    """
    cp = Path(catalog_path) if catalog_path else CATALOG_PATH
    base_wh = BASE_WAREHOUSE_PATH

    if conformed_facts is None:
        catalog = get_catalog(base_wh, cp)
        cf_table = catalog.load_table("base.conformed_facts")
        conformed_facts = read_with_duckdb(cf_table)

    # Build sector lookup from entity_mappings
    sector_lookup = build_sector_lookup(
        entity_mappings=entity_mappings,
        warehouse_path=str(base_wh),
        catalog_path=str(cp),
    )

    now = datetime.datetime.now(datetime.timezone.utc)
    today = now.date()
    results: list[dict] = []

    for fact in conformed_facts:
        cik = fact.get("cik")
        sector = sector_lookup.get(cik, "Unknown")

        # Normalize dates
        period_end_date = fact.get("period_end_date")
        if isinstance(period_end_date, str):
            period_end_date = datetime.date.fromisoformat(period_end_date)

        filed_date = fact.get("filed_date")
        if isinstance(filed_date, str):
            filed_date = datetime.date.fromisoformat(filed_date)

        record = {
            "cik": cik,
            "entity_id": fact.get("entity_id", ""),
            "ticker": fact.get("ticker"),
            "canonical_name": fact.get("canonical_name", ""),
            "sector": sector,
            "business_term_id": fact.get("business_term_id", ""),
            "business_term": fact.get("business_term", ""),
            "financial_statement": fact.get("financial_statement", ""),
            "category": fact.get("category", ""),
            "val": float(fact.get("val", 0)),
            "unit": fact.get("unit", ""),
            "source_concept": fact.get("source_concept", ""),
            "fiscal_year": fact.get("fiscal_year"),
            "fiscal_period": fact.get("fiscal_period"),
            "fiscal_year_end": fact.get("fiscal_year_end"),
            "period_end_date": period_end_date,
            "calendar_year": fact.get("calendar_year", 0),
            "calendar_quarter": fact.get("calendar_quarter", 0),
            "accession_number": fact.get("accession_number", ""),
            "filed_date": filed_date,
            "companies_reporting": 0,  # placeholder — computed below
            "promoted_at": now,
            "load_date": today,
        }
        record["record_id"] = _compute_record_id(record)
        results.append(record)

    # Compute companies_reporting per (business_term_id, fiscal_period)
    reporting_counts: dict[tuple, set] = {}
    for r in results:
        key = (r["business_term_id"], r["fiscal_period"])
        reporting_counts.setdefault(key, set()).add(r["cik"])

    for r in results:
        key = (r["business_term_id"], r["fiscal_period"])
        r["companies_reporting"] = len(reporting_counts.get(key, set()))

    return results
