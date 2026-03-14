"""Temporal query helpers for base.financial_facts.

All functions operate on list[dict] for testability without Iceberg infrastructure.
"""

from __future__ import annotations

import datetime

from .config import SUPERSESSION_GRAIN


def current_facts(
    facts: list[dict],
    *,
    cik: int | None = None,
    concept: str | None = None,
    cde_id: str | None = None,
) -> list[dict]:
    """Return non-superseded facts, optionally filtered by cik/concept/cde_id."""
    result = [f for f in facts if not f.get("is_superseded", False)]

    if cik is not None:
        result = [f for f in result if f.get("cik") == cik]
    if concept is not None:
        result = [f for f in result if f.get("concept") == concept]
    if cde_id is not None:
        result = [f for f in result if f.get("cde_id") == cde_id]

    return result


def as_known_on(
    facts: list[dict],
    as_of_date: datetime.date | str,
) -> list[dict]:
    """Return facts as known on a specific date.

    Re-computes supersession within the filed_date window:
    1. Filter to filed_date <= as_of_date
    2. Group by SUPERSESSION_GRAIN
    3. Within each group, keep only the record with max(filed_date)
    """
    if isinstance(as_of_date, str):
        as_of_date = datetime.date.fromisoformat(as_of_date)

    # Filter to facts filed on or before as_of_date
    filtered = []
    for f in facts:
        filed = f.get("filed_date")
        if filed is None:
            continue
        if isinstance(filed, str):
            filed = datetime.date.fromisoformat(filed)
        if filed <= as_of_date:
            filtered.append(f)

    # Group by supersession grain
    groups: dict[tuple, list[dict]] = {}
    for f in filtered:
        key = tuple(f.get(field) for field in SUPERSESSION_GRAIN)
        groups.setdefault(key, []).append(f)

    # Keep latest filed_date per group
    result = []
    for group in groups.values():
        latest = max(group, key=lambda x: x.get("filed_date", datetime.date.min))
        result.append(latest)

    return result


def fact_history(
    facts: list[dict],
    cik: int,
    concept: str,
    start_date: datetime.date | str,
    end_date: datetime.date | str,
    unit: str = "USD",
) -> list[dict]:
    """All versions of a fact across amendments, sorted by filed_date.

    Returns all facts matching the grain (cik, concept, unit, start_date, end_date),
    including superseded versions, ordered chronologically by filed_date.
    """
    if isinstance(start_date, str):
        start_date = datetime.date.fromisoformat(start_date)
    if isinstance(end_date, str):
        end_date = datetime.date.fromisoformat(end_date)

    matches = []
    for f in facts:
        if f.get("cik") != cik or f.get("concept") != concept or f.get("unit") != unit:
            continue

        f_start = f.get("start_date")
        f_end = f.get("end_date")
        if isinstance(f_start, str):
            f_start = datetime.date.fromisoformat(f_start)
        if isinstance(f_end, str):
            f_end = datetime.date.fromisoformat(f_end)

        if f_start == start_date and f_end == end_date:
            matches.append(f)

    matches.sort(key=lambda x: x.get("filed_date", datetime.date.min))
    return matches


def compare_periods(
    facts: list[dict],
    cik: int,
    concept: str,
    period1_end: datetime.date | str,
    period2_end: datetime.date | str,
    unit: str = "USD",
) -> dict | None:
    """Compare current value of a fact across two periods.

    Returns dict with period1_val, period2_val, change, pct_change,
    or None if either period is missing.
    """
    if isinstance(period1_end, str):
        period1_end = datetime.date.fromisoformat(period1_end)
    if isinstance(period2_end, str):
        period2_end = datetime.date.fromisoformat(period2_end)

    current = current_facts(facts, cik=cik, concept=concept)

    val1 = None
    val2 = None

    for f in current:
        if f.get("unit") != unit:
            continue

        f_end = f.get("end_date")
        if isinstance(f_end, str):
            f_end = datetime.date.fromisoformat(f_end)

        if f_end == period1_end:
            val1 = f.get("val")
        elif f_end == period2_end:
            val2 = f.get("val")

    if val1 is None or val2 is None:
        return None

    change = val2 - val1
    pct_change = (change / val1 * 100) if val1 != 0 else None

    return {
        "cik": cik,
        "concept": concept,
        "unit": unit,
        "period1_end": period1_end,
        "period2_end": period2_end,
        "period1_val": val1,
        "period2_val": val2,
        "change": change,
        "pct_change": round(pct_change, 2) if pct_change is not None else None,
    }


def facts_at_snapshot(
    table,
    snapshot_id: int,
    *,
    cik: int | None = None,
    concept: str | None = None,
) -> list[dict]:
    """Read facts from a specific Iceberg snapshot (system time travel).

    Unlike as_known_on (which uses filed_date/valid time), this uses
    Iceberg's snapshot mechanism (transaction/system time).
    """
    from src.infra.iceberg_setup import read_with_duckdb

    records = read_with_duckdb(table, snapshot_id=snapshot_id)

    if cik is not None:
        records = [r for r in records if r.get("cik") == cik]
    if concept is not None:
        records = [r for r in records if r.get("concept") == concept]

    return records
