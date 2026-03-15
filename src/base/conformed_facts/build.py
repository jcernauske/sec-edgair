"""Core build logic for base.conformed_facts.

Reads base.financial_facts and base.entity_mappings, applies supersession
filtering, null BT filtering, null FY filtering, unit filtering, concept
collision resolution, and produces conformed facts with source_fact_id
lineage and selection_reason metadata.

One row per (cik, business_term_id, fiscal_year, fiscal_period).
"""

from __future__ import annotations

import datetime
import hashlib
import logging
from pathlib import Path

from src.infra.iceberg_setup import get_catalog, read_with_duckdb

from .config import (
    CATALOG_PATH,
    CONFORMED_ID_GRAIN,
    LEGACY_CDE_TO_BT,
    PRIMARY_CONCEPTS,
    PRIMARY_UNIT,
    WAREHOUSE_PATH,
)

logger = logging.getLogger(__name__)


def _compute_conformed_id(record: dict) -> str:
    """Deterministic SHA-256 hash of grain fields, truncated to 16 chars."""
    parts = []
    for field in CONFORMED_ID_GRAIN:
        v = record.get(field)
        parts.append(str(v) if v is not None else "")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


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
    """Count how many times each concept appears across the filtered dataset."""
    freq: dict[str, int] = {}
    for f in facts:
        concept = f.get("concept")
        if concept is not None:
            freq[concept] = freq.get(concept, 0) + 1
    return freq


def _select_concept(
    bt_id: str,
    group_facts: list[dict],
    concept_freq: dict[str, int],
) -> tuple[dict | None, str]:
    """Select the best fact from a collision group using primary concept preference.

    Returns (selected_fact, selection_reason).

    1. If only one fact in group: return it with "sole_candidate".
    2. Walk PRIMARY_CONCEPTS for this business_term_id -- pick the first concept
       that has a fact in the group. Reason: "primary_concept".
    3. If no primary concept found, pick by highest tier, then most common concept.
       Reason: "tier_frequency_fallback".
    """
    if not group_facts:
        return None, ""

    if len(group_facts) == 1:
        return group_facts[0], "sole_candidate"

    primary_list = PRIMARY_CONCEPTS.get(bt_id, [])

    # Try primary concepts in order
    for preferred_concept in primary_list:
        for f in group_facts:
            if f.get("concept") == preferred_concept:
                return f, "primary_concept"

    # Fallback: lowest tier first (tier 1 = best), then most common concept
    sorted_facts = sorted(
        group_facts,
        key=lambda f: (f.get("tier", 3), -concept_freq.get(f.get("concept", ""), 0)),
    )
    return sorted_facts[0], "tier_frequency_fallback"


def build_conformed_facts(
    *,
    facts: list[dict] | None = None,
    entity_mappings: list[dict] | None = None,
    warehouse_path: str | Path | None = None,
    catalog_path: str | Path | None = None,
) -> list[dict]:
    """Build the base.conformed_facts table.

    Accepts facts and entity_mappings as parameters for testability.
    When not provided, reads from Iceberg tables.
    """
    wh = Path(warehouse_path) if warehouse_path else WAREHOUSE_PATH
    cp = Path(catalog_path) if catalog_path else CATALOG_PATH

    if facts is None:
        catalog = get_catalog(wh, cp)
        facts_table = catalog.load_table("base.financial_facts")
        facts = read_with_duckdb(facts_table)
        logger.info("Read %d facts from base.financial_facts", len(facts))

    if entity_mappings is None:
        catalog = get_catalog(wh, cp)
        em_table = catalog.load_table("base.entity_mappings")
        entity_mappings = read_with_duckdb(em_table)
        logger.info("Read %d entity mappings", len(entity_mappings))

    fye_lookup = _build_fiscal_year_end_lookup(entity_mappings)

    # Step 0: Normalize legacy CDE-XXX IDs to BT-XXX
    legacy_count = 0
    for f in facts:
        bt_id = f.get("business_term_id")
        if bt_id and bt_id in LEGACY_CDE_TO_BT:
            f["business_term_id"] = LEGACY_CDE_TO_BT[bt_id]
            legacy_count += 1
    if legacy_count:
        logger.info("Normalized %d legacy CDE-XXX IDs to BT-XXX", legacy_count)

    # Step 1: Filter -- is_superseded=false, business_term_id IS NOT NULL,
    # fiscal_year IS NOT NULL
    filtered = [
        f for f in facts
        if not f.get("is_superseded")
        and f.get("business_term_id") is not None
        and f.get("fiscal_year") is not None
    ]
    logger.info(
        "After supersession/mapping/FY filter: %d rows (removed %d)",
        len(filtered), len(facts) - len(filtered),
    )

    # Step 2: Filter to primary unit per business term
    unit_filtered = []
    for f in filtered:
        bt_id = f.get("business_term_id")
        expected_unit = PRIMARY_UNIT.get(bt_id)
        if expected_unit is None:
            # Unknown business term -- skip
            continue
        if f.get("unit") == expected_unit:
            unit_filtered.append(f)

    logger.info(
        "After unit filter: %d rows (removed %d)",
        len(unit_filtered), len(filtered) - len(unit_filtered),
    )

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

    logger.info("Unique grains: %d", len(groups))

    # Precompute concept frequency for fallback tiebreaking
    concept_freq = _compute_concept_frequency(unit_filtered)

    # Step 4: Resolve concept collisions -- one value per group
    now = datetime.datetime.now(datetime.timezone.utc)
    today = now.date()
    results: list[dict] = []

    for (cik, bt_id, fy, fp), group_facts in groups.items():
        selected, selection_reason = _select_concept(bt_id, group_facts, concept_freq)
        if selected is None:
            continue

        # Normalize dates
        end_date = selected.get("end_date")
        if isinstance(end_date, str):
            end_date = datetime.date.fromisoformat(end_date)

        filed_date = selected.get("filed_date")
        if isinstance(filed_date, str):
            filed_date = datetime.date.fromisoformat(filed_date)

        record = {
            "source_fact_id": selected.get("fact_id", ""),
            "entity_id": selected.get("entity_id", ""),
            "cik": cik,
            "canonical_name": selected.get("canonical_name", ""),
            "ticker": selected.get("ticker"),
            "business_term_id": bt_id,
            "business_term": selected.get("business_term", ""),
            "financial_statement": selected.get("financial_statement", ""),
            "category": selected.get("category", ""),
            "source_concept": selected.get("concept", ""),
            "val": float(selected.get("val", 0)),
            "unit": selected.get("unit", ""),
            "fiscal_year": fy,
            "fiscal_period": fp,
            "fiscal_year_end": fye_lookup.get(cik),
            "period_end_date": end_date,
            "calendar_year": selected.get("calendar_year", 0),
            "calendar_quarter": selected.get("calendar_quarter", 0),
            "accession_number": selected.get("accession_number", ""),
            "filed_date": filed_date,
            "competing_fact_count": len(group_facts),
            "selection_reason": selection_reason,
            "promoted_at": now,
            "load_date": today,
        }
        record["conformed_id"] = _compute_conformed_id(record)
        results.append(record)

    # Log resolution stats
    sole = sum(1 for r in results if r["selection_reason"] == "sole_candidate")
    primary = sum(1 for r in results if r["selection_reason"] == "primary_concept")
    fallback = sum(1 for r in results if r["selection_reason"] == "tier_frequency_fallback")
    logger.info(
        "Collision resolution: %d sole_candidate, %d primary_concept, %d tier_frequency_fallback",
        sole, primary, fallback,
    )
    logger.info("Built %d conformed facts", len(results))

    return results
