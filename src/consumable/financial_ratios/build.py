"""Core build logic for consumable.financial_ratios.

Reads consumable.company_financials, computes 7 financial ratios by joining
numerator and denominator business terms on (cik, fiscal_year, fiscal_period),
and returns one row per (company, ratio, year, period).
"""

from __future__ import annotations

import datetime
import hashlib
from pathlib import Path

from src.infra.iceberg_setup import get_catalog, read_with_duckdb

from .config import (
    CATALOG_PATH,
    RATIO_DEFINITIONS,
    RECORD_ID_GRAIN,
    WAREHOUSE_PATH,
)


def _compute_record_id(record: dict) -> str:
    """Deterministic SHA-256 hash of grain fields, truncated to 16 chars."""
    parts = []
    for field in RECORD_ID_GRAIN:
        v = record.get(field)
        parts.append(str(v) if v is not None else "")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def build_financial_ratios(
    *,
    company_financials: list[dict] | None = None,
    warehouse_path: str | Path | None = None,
    catalog_path: str | Path | None = None,
) -> list[dict]:
    """Build the consumable.financial_ratios table.

    Accepts company_financials as parameter for testability.
    When not provided, reads from Iceberg table.
    """
    if company_financials is None:
        wh = Path(warehouse_path) if warehouse_path else WAREHOUSE_PATH
        cp = Path(catalog_path) if catalog_path else CATALOG_PATH
        catalog = get_catalog(wh, cp)
        cf_table = catalog.load_table("consumable.company_financials")
        company_financials = read_with_duckdb(cf_table)

    # Index company_financials by (cik, fiscal_year, fiscal_period, business_term_id)
    # for fast lookup of numerator/denominator pairs
    cf_index: dict[tuple, dict] = {}
    for row in company_financials:
        key = (
            row.get("cik"),
            row.get("fiscal_year"),
            row.get("fiscal_period"),
            row.get("business_term_id"),
        )
        cf_index[key] = row

    # Collect unique (cik, fiscal_year, fiscal_period) groups
    grain_groups: set[tuple] = set()
    for row in company_financials:
        grain_groups.add((
            row.get("cik"),
            row.get("fiscal_year"),
            row.get("fiscal_period"),
        ))

    now = datetime.datetime.now(datetime.timezone.utc)
    today = now.date()
    results: list[dict] = []

    for cik, fy, fp in grain_groups:
        for ratio_def in RATIO_DEFINITIONS:
            num_key = (cik, fy, fp, ratio_def["numerator_bt_id"])
            den_key = (cik, fy, fp, ratio_def["denominator_bt_id"])

            num_row = cf_index.get(num_key)
            den_row = cf_index.get(den_key)

            # Skip if either component is missing
            if num_row is None or den_row is None:
                continue

            num_val = num_row.get("val")
            den_val = den_row.get("val")

            # Skip if values are None or denominator is 0
            if num_val is None or den_val is None or den_val == 0:
                continue

            # When abs_numerator is True (CapEx), also skip negative denominators.
            # Negative Revenue makes CapEx-to-Revenue meaningless (data quality issue).
            if ratio_def["abs_numerator"] and den_val < 0:
                continue

            # Apply abs to numerator if configured (CapEx)
            effective_num = abs(num_val) if ratio_def["abs_numerator"] else num_val
            ratio_value = effective_num / den_val

            # Use denominator row for temporal fields (both rows share the same period)
            record = {
                "cik": cik,
                "entity_id": den_row.get("entity_id", ""),
                "ticker": den_row.get("ticker"),
                "canonical_name": den_row.get("canonical_name", ""),
                "sector": den_row.get("sector", ""),
                "ratio_id": ratio_def["ratio_id"],
                "ratio_name": ratio_def["ratio_name"],
                "ratio_value": ratio_value,
                "numerator_bt_id": ratio_def["numerator_bt_id"],
                "numerator_bt_name": num_row.get("business_term", ""),
                "numerator_val": float(num_val),
                "denominator_bt_id": ratio_def["denominator_bt_id"],
                "denominator_bt_name": den_row.get("business_term", ""),
                "denominator_val": float(den_val),
                "fiscal_year": fy,
                "fiscal_period": fp,
                "fiscal_year_end": den_row.get("fiscal_year_end"),
                "period_end_date": den_row.get("period_end_date"),
                "calendar_year": den_row.get("calendar_year", 0),
                "calendar_quarter": den_row.get("calendar_quarter", 0),
                "companies_reporting": 0,  # placeholder — computed below
                "promoted_at": now,
                "load_date": today,
            }
            record["record_id"] = _compute_record_id(record)
            results.append(record)

    # Compute companies_reporting per (ratio_id, fiscal_period)
    reporting_counts: dict[tuple, set] = {}
    for r in results:
        key = (r["ratio_id"], r["fiscal_period"])
        reporting_counts.setdefault(key, set()).add(r["cik"])

    for r in results:
        key = (r["ratio_id"], r["fiscal_period"])
        r["companies_reporting"] = len(reporting_counts.get(key, set()))

    return results
