"""Build fiscal calendar dimension from observed periods in raw data.

Extracts distinct (cik, fiscal_year, fiscal_period) combinations from raw facts,
enriches with entity metadata, and computes calendar alignment fields.
"""

from __future__ import annotations

import datetime
import hashlib
from pathlib import Path

from src.infra.iceberg_setup import get_catalog, read_with_duckdb

from .config import CALENDAR_ID_GRAIN


def _compute_calendar_id(cik: int, fiscal_year: int, fiscal_period: str) -> str:
    """Deterministic hash of calendar grain fields."""
    key = f"{cik}|{fiscal_year}|{fiscal_period}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _calendar_quarter(d: datetime.date) -> int:
    """Return calendar quarter (1-4) from a date."""
    return (d.month - 1) // 3 + 1


def build_fiscal_calendar(
    *,
    raw_records: list[dict] | None = None,
    entity_mappings: list[dict] | None = None,
    warehouse_path: str | Path | None = None,
    catalog_path: str | Path | None = None,
) -> list[dict]:
    """Build fiscal calendar entries from raw facts + entity mappings.

    Can operate on in-memory records (for testing) or read from Iceberg tables.
    """
    if raw_records is None:
        catalog = get_catalog(warehouse_path, catalog_path)
        raw_table = catalog.load_table("raw.xbrl_company_facts")
        raw_records = read_with_duckdb(raw_table)

    if entity_mappings is None:
        catalog = get_catalog(warehouse_path, catalog_path)
        entity_table = catalog.load_table("base.entity_mappings")
        entity_mappings = read_with_duckdb(entity_table)

    entity_lookup = {e["cik"]: e for e in entity_mappings}

    # Group raw facts by (cik, fiscal_year, fiscal_period) to find period boundaries
    periods: dict[tuple, dict] = {}

    for r in raw_records:
        fy = r.get("fiscal_year")
        fp = r.get("fiscal_period")
        if fy is None or fp is None:
            continue

        key = (r["cik"], fy, fp)

        start = r.get("start_date")
        end = r.get("end_date")
        if end is None:
            continue

        # Normalize dates
        if isinstance(start, str):
            start = datetime.date.fromisoformat(start)
        if isinstance(end, str):
            end = datetime.date.fromisoformat(end)

        if key not in periods:
            periods[key] = {"start_dates": [], "end_dates": []}

        if start is not None:
            periods[key]["start_dates"].append(start)
        periods[key]["end_dates"].append(end)

    calendar_entries = []
    for (cik, fy, fp), data in sorted(periods.items()):
        entity = entity_lookup.get(cik)
        if entity is None:
            continue

        period_end = max(data["end_dates"])
        period_start = min(data["start_dates"]) if data["start_dates"] else None

        duration_days = None
        if period_start is not None:
            duration_days = (period_end - period_start).days

        calendar_entries.append({
            "calendar_id": _compute_calendar_id(cik, fy, fp),
            "cik": cik,
            "entity_id": entity["mapping_id"],
            "fiscal_year": fy,
            "fiscal_period": fp,
            "fiscal_year_end": entity.get("fiscal_year_end", "1231"),
            "period_start": period_start,
            "period_end": period_end,
            "calendar_year": period_end.year,
            "calendar_quarter": _calendar_quarter(period_end),
            "duration_days": duration_days,
            "is_annual": fp == "FY",
            "load_date": datetime.date.today(),
        })

    return calendar_entries


def build_fiscal_calendar_from_records(
    raw_records: list[dict],
    entity_mappings: list[dict],
) -> list[dict]:
    """Convenience wrapper for testing — takes records directly."""
    return build_fiscal_calendar(
        raw_records=raw_records,
        entity_mappings=entity_mappings,
    )
