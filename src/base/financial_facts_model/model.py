"""Core financial facts model: join raw + entity + concept mappings.

Joins raw XBRL facts with entity_mappings (for company metadata) and
concept_mappings (for business term/tier/category), computes derived fields
(calendar alignment, amendment detection, supersession), and produces
the base.financial_facts table.
"""

from __future__ import annotations

import datetime
import hashlib
from pathlib import Path

from src.infra.iceberg_setup import get_catalog, read_with_duckdb

from .config import FACT_ID_GRAIN, SUPERSESSION_GRAIN


def _compute_fact_id(record: dict) -> str:
    """Deterministic hash of grain fields."""
    parts = []
    for field in FACT_ID_GRAIN:
        v = record.get(field)
        parts.append(str(v) if v is not None else "")
    key = "|".join(parts)
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _calendar_quarter(d: datetime.date) -> int:
    """Return calendar quarter (1-4) from a date."""
    return (d.month - 1) // 3 + 1


def _derive_fiscal_year(end_date: datetime.date, fiscal_year_end_mmdd: str | None) -> int:
    """Derive fiscal year from end_date and company's fiscal year end.

    The XBRL 'fy' field reflects the filing year, not the reporting year.
    We must derive the actual fiscal year from end_date instead.

    For December FY companies: FY = end_date.year
    For non-December: FY = end_date.year if end_date.month <= FY end month,
                      else end_date.year + 1
    """
    if not fiscal_year_end_mmdd:
        return end_date.year

    fy_end_month = int(fiscal_year_end_mmdd[:2])

    if fy_end_month == 12:
        return end_date.year

    # Non-December FY: if end_date is after the FY end month,
    # it belongs to the NEXT fiscal year
    if end_date.month > fy_end_month:
        return end_date.year + 1
    else:
        return end_date.year


def _derive_fiscal_period(
    start_date: datetime.date | None,
    end_date: datetime.date,
    xbrl_fp: str | None,
) -> str:
    """Derive fiscal period from duration, falling back to XBRL fp.

    XBRL fp is unreliable (some quarterly data tagged as FY).
    Use duration to disambiguate:
      ~360-366 days = FY
      ~180-185 days = cumulative (Q2 or Q3 YTD) — use xbrl_fp
      ~270-275 days = cumulative (Q3 YTD) — use xbrl_fp
      ~88-93 days = single quarter — use xbrl_fp
    """
    if start_date is None:
        # Instant/balance sheet items — no duration. Trust XBRL fp.
        return xbrl_fp or "FY"

    duration = (end_date - start_date).days

    if duration >= 350:
        return "FY"

    # For sub-annual periods, trust the XBRL fp since it correctly
    # identifies Q1/Q2/Q3 even when fy is wrong
    return xbrl_fp or "FY"


def _is_amendment(form: str) -> bool:
    """Check if the form type indicates an amendment."""
    return form.endswith("/A") if form else False


def _apply_supersession(facts: list[dict]) -> list[dict]:
    """Mark superseded facts within each grain group.

    For each (cik, concept, unit, start_date, end_date) group:
    - Sort by filed_date ASC
    - Latest filed_date → is_superseded=False (current)
    - All earlier → is_superseded=True, superseded_by=latest.accession_number
    """
    groups: dict[tuple, list[dict]] = {}

    for f in facts:
        key = tuple(f.get(field) for field in SUPERSESSION_GRAIN)
        groups.setdefault(key, []).append(f)

    for group in groups.values():
        if len(group) == 1:
            group[0]["is_superseded"] = False
            group[0]["superseded_by"] = None
            continue

        group.sort(key=lambda x: x["filed_date"])
        latest = group[-1]

        for f in group[:-1]:
            f["is_superseded"] = True
            f["superseded_by"] = latest["accession_number"]

        latest["is_superseded"] = False
        latest["superseded_by"] = None

    return facts


def _apply_ttm_dedup(facts: list[dict]) -> list[dict]:
    """Mark trailing-twelve-month duplicates as superseded.

    XBRL quarterly filings often include TTM (trailing twelve month) values
    tagged as FY. These have ~365-day durations but start on non-standard dates
    (e.g., Apr 1 for a Dec-FY company). When multiple non-superseded FY rows
    exist for the same (cik, concept, unit, fiscal_year) with different
    start_dates, prefer the one whose end_date month matches the company's
    fiscal_year_end month.
    """
    # Group non-superseded FY facts by (cik, concept, unit, fiscal_year)
    groups: dict[tuple, list[dict]] = {}
    for f in facts:
        if f.get("is_superseded") or f.get("fiscal_period") != "FY":
            continue
        if f.get("start_date") is None:
            continue
        key = (f["cik"], f["concept"], f["unit"], f["fiscal_year"])
        groups.setdefault(key, []).append(f)

    for group in groups.values():
        if len(group) <= 1:
            continue

        # Check if they have different start_dates (TTM vs true annual)
        starts = {f["start_date"] for f in group}
        if len(starts) <= 1:
            continue

        # Prefer the row whose end_date month matches fiscal_year_end
        fy_end = group[0].get("fiscal_year_end")
        if not fy_end:
            continue

        fy_end_month = int(fy_end[:2])

        best = None
        for f in group:
            end = f["end_date"]
            if isinstance(end, str):
                end = datetime.date.fromisoformat(end)
            if end.month == fy_end_month or (fy_end_month == 12 and end.month == 12):
                best = f
                break

        if best is None:
            # No exact month match — pick the one with latest end_date
            # (most likely the true annual filing)
            best = max(group, key=lambda f: f["end_date"])

        # Mark all others as superseded (TTM dedup, not filing supersession)
        for f in group:
            if f is not best:
                f["is_superseded"] = True
                f["superseded_by"] = best.get("accession_number")

    return facts


def build_financial_facts(
    *,
    raw_records: list[dict] | None = None,
    entity_mappings: list[dict] | None = None,
    concept_mappings: list[dict] | None = None,
    warehouse_path: str | Path | None = None,
    catalog_path: str | Path | None = None,
) -> list[dict]:
    """Build financial facts by joining raw + entity + concept data.

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

    if concept_mappings is None:
        catalog = get_catalog(warehouse_path, catalog_path)
        concept_table = catalog.load_table("base.concept_mappings")
        concept_mappings = read_with_duckdb(concept_table)

    entity_lookup = {e["cik"]: e for e in entity_mappings}
    concept_lookup = {c["concept"]: c for c in concept_mappings}

    now = datetime.datetime.now(datetime.timezone.utc)
    facts = []

    for r in raw_records:
        entity = entity_lookup.get(r["cik"])
        if entity is None:
            continue

        concept = concept_lookup.get(r["concept"])

        # Normalize dates
        end_date = r.get("end_date")
        start_date = r.get("start_date")
        filed_date = r.get("filed_date")

        if isinstance(end_date, str):
            end_date = datetime.date.fromisoformat(end_date)
        if isinstance(start_date, str):
            start_date = datetime.date.fromisoformat(start_date)
        if isinstance(filed_date, str):
            filed_date = datetime.date.fromisoformat(filed_date)

        if end_date is None:
            continue

        form = r.get("form", "")

        fact = {
            "entity_id": entity["mapping_id"],
            "cik": r["cik"],
            "canonical_name": entity["canonical_name"],
            "ticker": entity.get("ticker"),
            "concept": r["concept"],
            "business_term_id": concept["business_term_id"] if concept else None,
            "business_term": concept["business_term"] if concept else None,
            "financial_statement": concept["financial_statement"] if concept else "other",
            "category": concept["category"] if concept else "uncategorized",
            "tier": concept["tier"] if concept else 3,
            "taxonomy": r.get("taxonomy", "us-gaap"),
            "unit": r["unit"],
            "val": float(r["val"]),
            "start_date": start_date,
            "end_date": end_date,
            "fiscal_year": _derive_fiscal_year(end_date, entity.get("fiscal_year_end")),
            "fiscal_period": _derive_fiscal_period(start_date, end_date, r.get("fiscal_period")),
            "fiscal_year_end": entity.get("fiscal_year_end"),
            "calendar_year": end_date.year,
            "calendar_quarter": _calendar_quarter(end_date),
            "accession_number": r["accession_number"],
            "form": form,
            "filed_date": filed_date,
            "is_amendment": _is_amendment(form),
            "promoted_at": now,
            "load_date": now.date(),
        }

        fact["fact_id"] = _compute_fact_id(fact)
        facts.append(fact)

    _apply_supersession(facts)
    _apply_ttm_dedup(facts)

    return facts


def build_financial_facts_from_records(
    raw_records: list[dict],
    entity_mappings: list[dict],
    concept_mappings: list[dict],
) -> list[dict]:
    """Convenience wrapper for testing — takes records directly."""
    return build_financial_facts(
        raw_records=raw_records,
        entity_mappings=entity_mappings,
        concept_mappings=concept_mappings,
    )
