"""Core build logic for consumable.peer_comparison.

Reads consumable.company_financials and consumable.financial_ratios, normalizes
both into a common structure, groups by (sector, metric_id, fiscal_year,
fiscal_period, metric_source), and computes dense rank, sector avg, sector
median, and percentile for each company within its sector group.
"""

from __future__ import annotations

import datetime
import hashlib
from pathlib import Path

from src.infra.iceberg_setup import get_catalog, read_with_duckdb

from .config import (
    CATALOG_PATH,
    MIN_PEER_COUNT,
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
    """Compute median of a sorted list of values."""
    n = len(values)
    if n == 0:
        return 0.0
    mid = n // 2
    if n % 2 == 1:
        return values[mid]
    return (values[mid - 1] + values[mid]) / 2.0


def _dense_rank(values: list[float], target: float) -> int:
    """Compute dense rank (1 = highest value). Ties get same rank.

    Values are ranked descending. Distinct sorted values determine rank positions.
    """
    distinct_sorted = sorted(set(values), reverse=True)
    for rank, val in enumerate(distinct_sorted, start=1):
        if val == target:
            return rank
    return len(distinct_sorted)


def _normalize_company_financials(rows: list[dict]) -> list[dict]:
    """Normalize company_financials rows into the common peer comparison structure."""
    normalized = []
    for r in rows:
        normalized.append({
            "cik": r.get("cik"),
            "entity_id": r.get("entity_id", ""),
            "ticker": r.get("ticker"),
            "canonical_name": r.get("canonical_name", ""),
            "sector": r.get("sector", ""),
            "metric_source": "company_financials",
            "metric_id": r.get("business_term_id", ""),
            "metric_name": r.get("business_term", ""),
            "metric_value": float(r.get("val", 0)),
            "fiscal_year": r.get("fiscal_year"),
            "fiscal_period": r.get("fiscal_period", ""),
            "fiscal_year_end": r.get("fiscal_year_end"),
            "period_end_date": r.get("period_end_date"),
            "calendar_year": r.get("calendar_year", 0),
            "calendar_quarter": r.get("calendar_quarter", 0),
        })
    return normalized


def _normalize_financial_ratios(rows: list[dict]) -> list[dict]:
    """Normalize financial_ratios rows into the common peer comparison structure."""
    normalized = []
    for r in rows:
        normalized.append({
            "cik": r.get("cik"),
            "entity_id": r.get("entity_id", ""),
            "ticker": r.get("ticker"),
            "canonical_name": r.get("canonical_name", ""),
            "sector": r.get("sector", ""),
            "metric_source": "financial_ratios",
            "metric_id": r.get("ratio_id", ""),
            "metric_name": r.get("ratio_name", ""),
            "metric_value": float(r.get("ratio_value", 0)),
            "fiscal_year": r.get("fiscal_year"),
            "fiscal_period": r.get("fiscal_period", ""),
            "fiscal_year_end": r.get("fiscal_year_end"),
            "period_end_date": r.get("period_end_date"),
            "calendar_year": r.get("calendar_year", 0),
            "calendar_quarter": r.get("calendar_quarter", 0),
        })
    return normalized


def build_peer_comparison(
    *,
    company_financials: list[dict] | None = None,
    financial_ratios: list[dict] | None = None,
    warehouse_path: str | Path | None = None,
    catalog_path: str | Path | None = None,
    min_peer_count: int = MIN_PEER_COUNT,
) -> list[dict]:
    """Build the consumable.peer_comparison table.

    Accepts source data as parameters for testability.
    When not provided, reads from Iceberg tables.
    """
    wh = Path(warehouse_path) if warehouse_path else WAREHOUSE_PATH
    cp = Path(catalog_path) if catalog_path else CATALOG_PATH

    if company_financials is None or financial_ratios is None:
        catalog = get_catalog(wh, cp)

    if company_financials is None:
        cf_table = catalog.load_table("consumable.company_financials")
        company_financials = read_with_duckdb(cf_table)

    if financial_ratios is None:
        fr_table = catalog.load_table("consumable.financial_ratios")
        financial_ratios = read_with_duckdb(fr_table)

    # Normalize both sources
    normalized = _normalize_company_financials(company_financials)
    normalized.extend(_normalize_financial_ratios(financial_ratios))

    # Group by (sector, metric_id, fiscal_year, fiscal_period, metric_source)
    groups: dict[tuple, list[dict]] = {}
    for row in normalized:
        group_key = (
            row["sector"],
            row["metric_id"],
            row["fiscal_year"],
            row["fiscal_period"],
            row["metric_source"],
        )
        groups.setdefault(group_key, []).append(row)

    now = datetime.datetime.now(datetime.timezone.utc)
    today = now.date()
    results: list[dict] = []

    for group_key, members in groups.items():
        # Deduplicate by CIK within a group (shouldn't happen, but safety)
        seen_ciks: dict[int, dict] = {}
        for m in members:
            cik = m["cik"]
            if cik not in seen_ciks:
                seen_ciks[cik] = m

        unique_members = list(seen_ciks.values())
        peer_count = len(unique_members)

        # Skip single-company groups
        if peer_count < min_peer_count:
            continue

        # Compute sector statistics
        values = [m["metric_value"] for m in unique_members]
        sector_avg = sum(values) / len(values)
        sorted_values = sorted(values)
        sector_median = _compute_median(sorted_values)

        for member in unique_members:
            rank = _dense_rank(values, member["metric_value"])

            # Percentile: (peer_count - rank) / (peer_count - 1)
            if peer_count > 1:
                percentile = (peer_count - rank) / (peer_count - 1)
            else:
                percentile = 1.0

            record = {
                "cik": member["cik"],
                "entity_id": member["entity_id"],
                "ticker": member["ticker"],
                "canonical_name": member["canonical_name"],
                "sector": member["sector"],
                "metric_source": member["metric_source"],
                "metric_id": member["metric_id"],
                "metric_name": member["metric_name"],
                "metric_value": member["metric_value"],
                "sector_rank": rank,
                "sector_avg": sector_avg,
                "sector_median": sector_median,
                "sector_percentile": percentile,
                "peer_count": peer_count,
                "fiscal_year": member["fiscal_year"],
                "fiscal_period": member["fiscal_period"],
                "fiscal_year_end": member["fiscal_year_end"],
                "period_end_date": member["period_end_date"],
                "calendar_year": member["calendar_year"],
                "calendar_quarter": member["calendar_quarter"],
                "promoted_at": now,
                "load_date": today,
            }
            record["record_id"] = _compute_record_id(record)
            results.append(record)

    return results
