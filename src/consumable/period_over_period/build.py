"""Core build logic for consumable.period_over_period.

Reads base.conformed_facts, computes YoY change, YoY % change, and
5-year CAGR for every (company, business term, year, period) combination.
Returns one row per (company, business term, year, period, growth_type).
"""

from __future__ import annotations

import datetime
import hashlib
from pathlib import Path

from src.infra.iceberg_setup import get_catalog, read_with_duckdb

from ..shared import build_sector_lookup
from .config import (
    CATALOG_PATH,
    GROWTH_TYPES,
    RECORD_ID_GRAIN,
    WAREHOUSE_PATH,
)


# Base zone warehouse
BASE_WAREHOUSE_PATH = Path(__file__).resolve().parents[3] / "data" / "raw" / "iceberg_warehouse"


def _compute_record_id(record: dict) -> str:
    """Deterministic SHA-256 hash of grain fields, truncated to 16 chars."""
    parts = []
    for field in RECORD_ID_GRAIN:
        v = record.get(field)
        parts.append(str(v) if v is not None else "")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def build_period_over_period(
    *,
    conformed_facts: list[dict] | None = None,
    entity_mappings: list[dict] | None = None,
    warehouse_path: str | Path | None = None,
    catalog_path: str | Path | None = None,
    # Legacy parameter for backward compatibility with tests
    company_financials: list[dict] | None = None,
) -> list[dict]:
    """Build the consumable.period_over_period table.

    Reads base.conformed_facts directly. Accepts data as parameters
    for testability.
    """
    cp = Path(catalog_path) if catalog_path else CATALOG_PATH
    base_wh = BASE_WAREHOUSE_PATH

    # Support legacy parameter name
    if conformed_facts is None and company_financials is not None:
        conformed_facts = company_financials

    if conformed_facts is None:
        catalog = get_catalog(base_wh, cp)
        cf_table = catalog.load_table("base.conformed_facts")
        conformed_facts = read_with_duckdb(cf_table)

    # Build sector lookup
    sector_lookup = build_sector_lookup(
        entity_mappings=entity_mappings,
        warehouse_path=str(base_wh),
        catalog_path=str(cp),
    )

    # Index by (cik, business_term_id, fiscal_year, fiscal_period) for O(1) lookup
    cf_index: dict[tuple, dict] = {}
    for row in conformed_facts:
        key = (
            row.get("cik"),
            row.get("business_term_id"),
            row.get("fiscal_year"),
            row.get("fiscal_period"),
        )
        cf_index[key] = row

    # Collect fiscal years per (cik, business_term_id, fiscal_period) group
    years_by_group: dict[tuple, set[int]] = {}
    for row in conformed_facts:
        group_key = (
            row.get("cik"),
            row.get("business_term_id"),
            row.get("fiscal_period"),
        )
        fy = row.get("fiscal_year")
        if fy is not None:
            years_by_group.setdefault(group_key, set()).add(fy)

    now = datetime.datetime.now(datetime.timezone.utc)
    today = now.date()
    results: list[dict] = []

    for (cik, bt_id, fp), years in years_by_group.items():
        sector = sector_lookup.get(cik, "Unknown")

        for fy in sorted(years):
            current_key = (cik, bt_id, fy, fp)
            current_row = cf_index.get(current_key)
            if current_row is None:
                continue

            current_val = current_row.get("val")
            if current_val is None:
                continue

            for growth_def in GROWTH_TYPES:
                gt = growth_def["growth_type"]
                lookback = growth_def["lookback_years"]

                # Look up comparison period
                comp_key = (cik, bt_id, fy - lookback, fp)
                comp_row = cf_index.get(comp_key)
                if comp_row is None:
                    continue

                comp_val = comp_row.get("val")
                if comp_val is None:
                    continue

                # Check nonzero base requirement
                if growth_def["requires_nonzero_base"] and comp_val == 0:
                    continue

                # Check positive base requirement
                if growth_def["requires_positive_base"] and comp_val <= 0:
                    continue

                # Compute growth value
                if gt == "yoy_change":
                    growth_value = current_val - comp_val
                elif gt == "yoy_pct_change":
                    growth_value = (current_val - comp_val) / abs(comp_val)
                elif gt == "cagr_5yr":
                    ratio = current_val / comp_val
                    if ratio <= 0:
                        growth_value = -(abs(ratio) ** (1.0 / lookback)) - 1
                    else:
                        growth_value = ratio ** (1.0 / lookback) - 1
                else:
                    continue

                record = {
                    "cik": cik,
                    "entity_id": current_row.get("entity_id", ""),
                    "ticker": current_row.get("ticker"),
                    "canonical_name": current_row.get("canonical_name", ""),
                    "sector": sector,
                    "business_term_id": bt_id,
                    "business_term": current_row.get("business_term", ""),
                    "financial_statement": current_row.get("financial_statement", ""),
                    "category": current_row.get("category", ""),
                    "fiscal_year": fy,
                    "fiscal_period": fp,
                    "fiscal_year_end": current_row.get("fiscal_year_end"),
                    "period_end_date": current_row.get("period_end_date"),
                    "calendar_year": current_row.get("calendar_year", 0),
                    "calendar_quarter": current_row.get("calendar_quarter", 0),
                    "growth_type": gt,
                    "growth_value": growth_value,
                    "current_val": float(current_val),
                    "prior_val": float(comp_val) if lookback == 1 else None,
                    "base_val": float(comp_val) if lookback > 1 else None,
                    "base_fiscal_year": fy - lookback if lookback > 1 else None,
                    "companies_reporting": 0,  # placeholder — computed below
                    "promoted_at": now,
                    "load_date": today,
                }
                record["record_id"] = _compute_record_id(record)
                results.append(record)

    # Compute companies_reporting per (growth_type, business_term_id, fiscal_period)
    reporting_counts: dict[tuple, set] = {}
    for r in results:
        key = (r["growth_type"], r["business_term_id"], r["fiscal_period"])
        reporting_counts.setdefault(key, set()).add(r["cik"])

    for r in results:
        key = (r["growth_type"], r["business_term_id"], r["fiscal_period"])
        r["companies_reporting"] = len(reporting_counts.get(key, set()))

    return results
