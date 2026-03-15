"""Core build logic for consumable.company_financials.

Reads base.financial_facts and base.entity_mappings, applies filtering
(superseded, unmapped, unit), resolves concept collisions via primary
concept preference, computes derived fields, and returns one row per
(cik, business_term_id, fiscal_year, fiscal_period).
"""

from __future__ import annotations

import datetime
import hashlib
from pathlib import Path

from src.infra.iceberg_setup import get_catalog, read_with_duckdb

from .config import (
    CATALOG_PATH,
    LEGACY_CDE_TO_BT,
    PRIMARY_CONCEPTS,
    PRIMARY_UNIT,
    RECORD_ID_GRAIN,
    SIC_TO_SECTOR,
    WAREHOUSE_PATH,
)


def _compute_record_id(record: dict) -> str:
    """Deterministic SHA-256 hash of grain fields, truncated to 16 chars."""
    parts = []
    for field in RECORD_ID_GRAIN:
        v = record.get(field)
        parts.append(str(v) if v is not None else "")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _build_sic_lookup(entity_mappings: list[dict]) -> dict[int, str]:
    """Build CIK -> SIC code lookup from entity_mappings."""
    lookup: dict[int, str] = {}
    for em in entity_mappings:
        cik = em.get("cik")
        sic = em.get("sic_code")
        if cik is not None and sic is not None:
            lookup[cik] = sic
    return lookup


def _build_fiscal_year_end_lookup(entity_mappings: list[dict]) -> dict[int, str]:
    """Build CIK -> fiscal_year_end lookup from entity_mappings."""
    lookup: dict[int, str] = {}
    for em in entity_mappings:
        cik = em.get("cik")
        fye = em.get("fiscal_year_end")
        if cik is not None and fye is not None:
            lookup[cik] = fye
    return lookup


def _compute_concept_frequency(facts: list[dict]) -> dict[str, int]:
    """Count how many times each concept appears across the full dataset."""
    freq: dict[str, int] = {}
    for f in facts:
        concept = f.get("concept")
        if concept is not None:
            freq[concept] = freq.get(concept, 0) + 1
    return freq


def build_company_financials(
    *,
    facts: list[dict] | None = None,
    entity_mappings: list[dict] | None = None,
    warehouse_path: str | Path | None = None,
    catalog_path: str | Path | None = None,
) -> list[dict]:
    """Build the consumable.company_financials table.

    Accepts facts and entity_mappings as parameters for testability.
    When not provided, reads from Iceberg tables.
    """
    if facts is None:
        wh = Path(warehouse_path) if warehouse_path else WAREHOUSE_PATH
        cp = Path(catalog_path) if catalog_path else CATALOG_PATH
        catalog = get_catalog(wh, cp)
        facts_table = catalog.load_table("base.financial_facts")
        facts = read_with_duckdb(facts_table)

    if entity_mappings is None:
        wh = Path(warehouse_path) if warehouse_path else WAREHOUSE_PATH
        cp = Path(catalog_path) if catalog_path else CATALOG_PATH
        catalog = get_catalog(wh, cp)
        em_table = catalog.load_table("base.entity_mappings")
        entity_mappings = read_with_duckdb(em_table)

    sic_lookup = _build_sic_lookup(entity_mappings)
    fye_lookup = _build_fiscal_year_end_lookup(entity_mappings)

    # Step 0: Normalize legacy CDE-XXX IDs to BT-XXX
    # Existing Iceberg data may still have CDE-XXX values from before the
    # governance model alignment refactor. Translate on read.
    for f in facts:
        bt_id = f.get("business_term_id")
        if bt_id and bt_id in LEGACY_CDE_TO_BT:
            f["business_term_id"] = LEGACY_CDE_TO_BT[bt_id]

    # Step 1: Filter — is_superseded=false, business_term_id IS NOT NULL,
    # fiscal_year IS NOT NULL
    filtered = [
        f for f in facts
        if not f.get("is_superseded")
        and f.get("business_term_id") is not None
        and f.get("fiscal_year") is not None
    ]

    # Step 2: Filter to primary unit per business term
    unit_filtered = []
    for f in filtered:
        bt_id = f.get("business_term_id")
        expected_unit = PRIMARY_UNIT.get(bt_id)
        if expected_unit is None:
            # Unknown business term — skip
            continue
        if f.get("unit") == expected_unit:
            unit_filtered.append(f)

    # Step 3: Group by grain (cik, business_term_id, fiscal_year, fiscal_period)
    groups: dict[tuple, list[dict]] = {}
    for f in unit_filtered:
        key = (
            f.get("cik"),
            f.get("business_term_id"),
            f.get("fiscal_year"),
            f.get("fiscal_period"),
        )
        groups.setdefault(key, []).append(f)

    # Precompute concept frequency for fallback tiebreaking
    concept_freq = _compute_concept_frequency(unit_filtered)

    # Step 4: Resolve concept collisions — one value per group
    now = datetime.datetime.now(datetime.timezone.utc)
    today = now.date()
    results: list[dict] = []

    for (cik, bt_id, fy, fp), group_facts in groups.items():
        selected = _select_concept(bt_id, group_facts, concept_freq)
        if selected is None:
            continue

        sic_code = sic_lookup.get(cik, "")
        sector = SIC_TO_SECTOR.get(sic_code, "Unknown")

        # Normalize period_end_date
        end_date = selected.get("end_date")
        if isinstance(end_date, str):
            end_date = datetime.date.fromisoformat(end_date)

        filed_date = selected.get("filed_date")
        if isinstance(filed_date, str):
            filed_date = datetime.date.fromisoformat(filed_date)

        record = {
            "cik": cik,
            "entity_id": selected.get("entity_id", ""),
            "ticker": selected.get("ticker"),
            "canonical_name": selected.get("canonical_name", ""),
            "sector": sector,
            "business_term_id": bt_id,
            "business_term": selected.get("business_term", ""),
            "financial_statement": selected.get("financial_statement", ""),
            "category": selected.get("category", ""),
            "val": float(selected.get("val", 0)),
            "unit": selected.get("unit", ""),
            "source_concept": selected.get("concept", ""),
            "fiscal_year": fy,
            "fiscal_period": fp,
            "fiscal_year_end": fye_lookup.get(cik),
            "period_end_date": end_date,
            "calendar_year": selected.get("calendar_year", 0),
            "calendar_quarter": selected.get("calendar_quarter", 0),
            "accession_number": selected.get("accession_number", ""),
            "filed_date": filed_date,
            "companies_reporting": 0,  # placeholder — computed below
            "promoted_at": now,
            "load_date": today,
        }
        record["record_id"] = _compute_record_id(record)
        results.append(record)

    # Step 5: Compute companies_reporting per (business_term_id, fiscal_period)
    reporting_counts: dict[tuple, set] = {}
    for r in results:
        key = (r["business_term_id"], r["fiscal_period"])
        reporting_counts.setdefault(key, set()).add(r["cik"])

    for r in results:
        key = (r["business_term_id"], r["fiscal_period"])
        r["companies_reporting"] = len(reporting_counts.get(key, set()))

    return results


def _select_concept(
    bt_id: str,
    group_facts: list[dict],
    concept_freq: dict[str, int],
) -> dict | None:
    """Select the best fact from a collision group using primary concept preference.

    1. Walk PRIMARY_CONCEPTS for this business_term_id — pick the first concept
       that has a fact in the group.
    2. If no primary concept found, pick by highest tier, then most common concept.
    """
    if not group_facts:
        return None

    primary_list = PRIMARY_CONCEPTS.get(bt_id, [])

    # Try primary concepts in order
    for preferred_concept in primary_list:
        for f in group_facts:
            if f.get("concept") == preferred_concept:
                return f

    # Fallback: lowest tier first (tier 1 = best), then most common concept
    sorted_facts = sorted(
        group_facts,
        key=lambda f: (f.get("tier", 3), -concept_freq.get(f.get("concept", ""), 0)),
    )
    return sorted_facts[0]
