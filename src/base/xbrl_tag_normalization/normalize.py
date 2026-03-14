"""Core XBRL tag normalization logic.

Reads raw.xbrl_company_facts, extracts distinct us-gaap concepts,
and classifies each into a tier with a CDE mapping.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from src.infra.iceberg_setup import get_catalog, read_with_duckdb

from .config import (
    CDE_DEFINITIONS,
    EXACT_MAPPINGS,
    HEURISTIC_CATEGORIES,
    PATTERN_RULES,
    PREFIX_RULES,
)


def _classify_concept(concept: str) -> dict:
    """Classify a single XBRL concept into a tier with CDE mapping.

    Returns a dict with: cde_id, canonical_cde, financial_statement,
    category, tier, confidence, mapping_method.
    """
    # Tier 1: Exact match
    if concept in EXACT_MAPPINGS:
        cde_id, stmt, cat = EXACT_MAPPINGS[concept]
        cde_name = CDE_DEFINITIONS[cde_id]["name"]
        return {
            "cde_id": cde_id,
            "canonical_cde": cde_name,
            "financial_statement": stmt,
            "category": cat,
            "tier": 1,
            "confidence": 1.0,
            "mapping_method": "exact_match",
        }

    # Tier 2: Prefix match (confidence 0.7)
    for prefix, cde_id, stmt, cat in PREFIX_RULES:
        if concept.startswith(prefix):
            cde_name = CDE_DEFINITIONS[cde_id]["name"]
            return {
                "cde_id": cde_id,
                "canonical_cde": cde_name,
                "financial_statement": stmt,
                "category": cat,
                "tier": 2,
                "confidence": 0.7,
                "mapping_method": "prefix_match",
            }

    # Tier 2: Pattern match (confidence 0.6)
    for pattern, cde_id, stmt, cat in PATTERN_RULES:
        if re.match(pattern, concept):
            cde_name = CDE_DEFINITIONS[cde_id]["name"]
            return {
                "cde_id": cde_id,
                "canonical_cde": cde_name,
                "financial_statement": stmt,
                "category": cat,
                "tier": 2,
                "confidence": 0.6,
                "mapping_method": "pattern_match",
            }

    # Tier 3: Unmapped — assign heuristic category
    stmt, cat = _heuristic_category(concept)
    return {
        "cde_id": None,
        "canonical_cde": None,
        "financial_statement": stmt,
        "category": cat,
        "tier": 3,
        "confidence": 0.0,
        "mapping_method": "unmapped",
    }


def _heuristic_category(concept: str) -> tuple[str, str]:
    """Assign a heuristic financial statement and category based on substrings."""
    for substring, stmt, cat in HEURISTIC_CATEGORIES:
        if substring in concept:
            return stmt, cat
    return "other", "uncategorized"


def normalize_concepts(
    *,
    raw_warehouse_path: str | Path,
    catalog_path: str | Path,
) -> list[dict]:
    """Read raw.xbrl_company_facts and classify all us-gaap concepts.

    Returns a list of proposal dicts ready for staging.
    """
    catalog = get_catalog(raw_warehouse_path, catalog_path)
    table = catalog.load_table("raw.xbrl_company_facts")
    rows = read_with_duckdb(table)

    # Extract distinct us-gaap concepts with fact counts
    concept_stats = _compute_concept_stats(rows)
    return _build_proposals(concept_stats)


def normalize_concepts_from_records(records: list[dict]) -> list[dict]:
    """Classify concepts from raw fact records (for testing without Iceberg).

    Same logic as normalize_concepts but takes records directly.
    """
    concept_stats = _compute_concept_stats(records)
    return _build_proposals(concept_stats)


def _compute_concept_stats(rows: list[dict]) -> dict[str, dict]:
    """Compute per-concept statistics from raw fact rows.

    Returns {concept: {"fact_count": N, "company_count": N, "companies": set}}.
    """
    stats: dict[str, dict] = {}
    for row in rows:
        taxonomy = row.get("taxonomy", "")
        if taxonomy != "us-gaap":
            continue
        concept = row["concept"]
        if concept not in stats:
            stats[concept] = {"fact_count": 0, "companies": set()}
        stats[concept]["fact_count"] += 1
        stats[concept]["companies"].add(row["cik"])

    # Convert sets to counts
    for concept in stats:
        stats[concept]["company_count"] = len(stats[concept]["companies"])
        del stats[concept]["companies"]

    return stats


def _build_proposals(concept_stats: dict[str, dict]) -> list[dict]:
    """Build mapping proposals from concept statistics."""
    now = datetime.now(timezone.utc)
    proposals = []

    for idx, concept in enumerate(sorted(concept_stats.keys()), start=1):
        mapping_id = f"TN-{idx:04d}"
        classification = _classify_concept(concept)
        stats = concept_stats[concept]

        status = "unmapped" if classification["tier"] == 3 else "pending"

        proposals.append({
            "mapping_id": mapping_id,
            "concept": concept,
            "canonical_cde": classification["canonical_cde"],
            "cde_id": classification["cde_id"],
            "financial_statement": classification["financial_statement"],
            "category": classification["category"],
            "tier": classification["tier"],
            "confidence": classification["confidence"],
            "mapping_method": classification["mapping_method"],
            "status": status,
            "mapped_by": "@tag-normalizer",
            "mapped_at": now.isoformat(),
            "reasoning": _build_reasoning(concept, classification, stats),
            "evidence": json.dumps({
                "concept": concept,
                "fact_count": stats["fact_count"],
                "company_count": stats["company_count"],
                "tier": classification["tier"],
                "mapping_method": classification["mapping_method"],
            }),
        })

    return proposals


def _build_reasoning(concept: str, classification: dict, stats: dict) -> str:
    """Build human-readable reasoning for a mapping."""
    method = classification["mapping_method"]
    if method == "exact_match":
        return (
            f"Exact match: '{concept}' directly mapped to "
            f"{classification['canonical_cde']} ({classification['cde_id']}). "
            f"Appears in {stats['company_count']} companies, {stats['fact_count']} facts."
        )
    elif method == "prefix_match":
        return (
            f"Prefix match: '{concept}' starts with a known prefix for "
            f"{classification['canonical_cde']} ({classification['cde_id']}). "
            f"Appears in {stats['company_count']} companies, {stats['fact_count']} facts."
        )
    elif method == "pattern_match":
        return (
            f"Pattern match: '{concept}' matched regex for "
            f"{classification['canonical_cde']} ({classification['cde_id']}). "
            f"Appears in {stats['company_count']} companies, {stats['fact_count']} facts."
        )
    else:
        return (
            f"Unmapped: '{concept}' did not match any known CDE. "
            f"Heuristic category: {classification['financial_statement']}/{classification['category']}. "
            f"Appears in {stats['company_count']} companies, {stats['fact_count']} facts."
        )


def compute_coverage(proposals: list[dict], fact_rows: list[dict] | None = None) -> dict:
    """Compute coverage statistics for a set of proposals.

    If fact_rows is provided, computes fact-level coverage.
    Otherwise, computes concept-level coverage only.
    """
    total = len(proposals)
    tier_counts = {1: 0, 2: 0, 3: 0}
    mapped = 0

    for p in proposals:
        tier = p["tier"]
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
        if tier in (1, 2):
            mapped += 1

    result = {
        "total_concepts": total,
        "tier_1_count": tier_counts[1],
        "tier_2_count": tier_counts[2],
        "tier_3_count": tier_counts[3],
        "mapped_concepts": mapped,
        "concept_coverage_pct": round(mapped / total * 100, 1) if total else 0.0,
    }

    # Fact-level coverage if rows provided
    if fact_rows is not None:
        mapped_concepts = {p["concept"] for p in proposals if p["tier"] in (1, 2)}
        total_facts = 0
        covered_facts = 0
        for row in fact_rows:
            if row.get("taxonomy") != "us-gaap":
                continue
            total_facts += 1
            if row["concept"] in mapped_concepts:
                covered_facts += 1
        result["total_facts"] = total_facts
        result["covered_facts"] = covered_facts
        result["fact_coverage_pct"] = round(covered_facts / total_facts * 100, 1) if total_facts else 0.0

    return result
