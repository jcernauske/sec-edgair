"""Core build logic for consumable.amendment_analysis.

Reads base.amendment_tracking and base.conformed_facts,
aggregates amendment patterns per (cik, fiscal_year), and returns
one summary row per company per fiscal year.
"""

from __future__ import annotations

import datetime
import hashlib
import statistics
from pathlib import Path

from src.infra.iceberg_setup import get_catalog, read_with_duckdb

from ..shared import build_sector_lookup
from .config import (
    BASE_WAREHOUSE_PATH,
    CATALOG_PATH,
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


def _compute_median(values: list[float]) -> float:
    """Compute median of a list of numeric values."""
    if not values:
        return 0.0
    return statistics.median(values)


def build_amendment_analysis(
    *,
    amendment_tracking: list[dict] | None = None,
    conformed_facts: list[dict] | None = None,
    warehouse_path: str | Path | None = None,
    catalog_path: str | Path | None = None,
    base_warehouse_path: str | Path | None = None,
    entity_mappings: list[dict] | None = None,
    # Legacy parameter for backward compatibility with tests
    company_financials: list[dict] | None = None,
) -> list[dict]:
    """Build the consumable.amendment_analysis table.

    Reads base.amendment_tracking and base.conformed_facts for company metadata.
    Accepts data as parameters for testability.
    """
    cp = Path(catalog_path) if catalog_path else CATALOG_PATH
    bwh = Path(base_warehouse_path) if base_warehouse_path else BASE_WAREHOUSE_PATH

    if amendment_tracking is None:
        base_catalog = get_catalog(bwh, cp)
        at_table = base_catalog.load_table("base.amendment_tracking")
        amendment_tracking = read_with_duckdb(at_table)

    # Support legacy parameter name
    if conformed_facts is None and company_financials is not None:
        conformed_facts = company_financials

    if conformed_facts is None:
        base_catalog = get_catalog(bwh, cp)
        cf_table = base_catalog.load_table("base.conformed_facts")
        conformed_facts = read_with_duckdb(cf_table)

    # Build sector lookup
    sector_lookup = build_sector_lookup(
        entity_mappings=entity_mappings,
        warehouse_path=str(bwh),
        catalog_path=str(cp),
    )

    # Build company metadata lookup from conformed_facts: cik -> {entity_id, ticker, canonical_name}
    company_meta: dict[int, dict] = {}
    for row in conformed_facts:
        cik = row.get("cik")
        if cik is not None and cik not in company_meta:
            company_meta[cik] = {
                "entity_id": row.get("entity_id", ""),
                "ticker": row.get("ticker"),
                "canonical_name": row.get("canonical_name", ""),
            }

    # Group amendments by (cik, fiscal_year)
    groups: dict[tuple[int, int], list[dict]] = {}
    for row in amendment_tracking:
        cik = row.get("cik")
        end_date = row.get("end_date")
        if cik is None or end_date is None:
            continue

        # Derive fiscal_year from end_date
        if isinstance(end_date, str):
            end_date = datetime.date.fromisoformat(end_date)
        fiscal_year = end_date.year

        key = (cik, fiscal_year)
        groups.setdefault(key, []).append(row)

    now = datetime.datetime.now(datetime.timezone.utc)
    today = now.date()
    results: list[dict] = []

    for (cik, fiscal_year), amendments in groups.items():
        # Skip companies not in conformed_facts
        meta = company_meta.get(cik)
        if meta is None:
            continue

        sector = sector_lookup.get(cik, "Unknown")

        # Compute aggregates
        amendment_count = len(amendments)

        concepts = set()
        filings = set()
        abs_changes: list[float] = []
        abs_pct_changes: list[float] = []
        days_to_amend_values: list[float] = []

        # Track largest concept
        largest_abs = -1.0
        largest_concept = ""

        for a in amendments:
            concept = a.get("concept", "")
            concepts.add(concept)

            amendment_accession = a.get("amendment_accession", "")
            filings.add(amendment_accession)

            val_change = a.get("val_change")
            if val_change is not None:
                abs_val = abs(float(val_change))
                abs_changes.append(abs_val)
                if abs_val > largest_abs:
                    largest_abs = abs_val
                    largest_concept = concept

            val_change_pct = a.get("val_change_pct")
            if val_change_pct is not None:
                abs_pct_changes.append(abs(float(val_change_pct)))

            # Days to amend
            amend_date = a.get("amendment_filed_date")
            orig_date = a.get("original_filed_date")
            if amend_date is not None and orig_date is not None:
                if isinstance(amend_date, str):
                    amend_date = datetime.date.fromisoformat(amend_date)
                if isinstance(orig_date, str):
                    orig_date = datetime.date.fromisoformat(orig_date)
                days = (amend_date - orig_date).days
                days_to_amend_values.append(float(days))

        # Compute stats
        mean_abs = sum(abs_changes) / len(abs_changes) if abs_changes else 0.0
        median_abs = _compute_median(abs_changes)
        max_abs = max(abs_changes) if abs_changes else 0.0
        total_impact = sum(abs_changes)

        mean_pct = (
            sum(abs_pct_changes) / len(abs_pct_changes)
            if abs_pct_changes
            else None
        )
        median_pct = _compute_median(abs_pct_changes) if abs_pct_changes else None

        days_avg = (
            sum(days_to_amend_values) / len(days_to_amend_values)
            if days_to_amend_values
            else 0.0
        )
        days_median = _compute_median(days_to_amend_values) if days_to_amend_values else 0.0

        record = {
            "cik": cik,
            "entity_id": meta["entity_id"],
            "ticker": meta["ticker"],
            "canonical_name": meta["canonical_name"],
            "sector": sector,
            "fiscal_year": fiscal_year,
            "amendment_count": amendment_count,
            "distinct_concepts": len(concepts),
            "distinct_filings": len(filings),
            "mean_abs_change": mean_abs,
            "median_abs_change": median_abs,
            "max_abs_change": max_abs,
            "mean_pct_change": mean_pct,
            "median_pct_change": median_pct,
            "total_val_impact": total_impact,
            "largest_concept": largest_concept,
            "largest_change": largest_abs,
            "days_to_amend_avg": days_avg,
            "days_to_amend_median": days_median,
            "promoted_at": now,
            "load_date": today,
        }
        record["record_id"] = _compute_record_id(record)
        results.append(record)

    # Sort for deterministic output
    results.sort(key=lambda r: (r["cik"], r["fiscal_year"]))

    return results
