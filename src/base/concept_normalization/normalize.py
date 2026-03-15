"""Generic tiered concept normalization engine.

Loads concept → business term mappings from JSON config files.
Works with any taxonomy — XBRL, CPT codes, meter types, etc.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from src.infra.iceberg_setup import get_catalog, read_with_duckdb

logger = logging.getLogger(__name__)


class ConceptNormalizer:
    """Generic tiered concept normalization engine.

    Loads concept → business term mappings from JSON config files.
    Works with any taxonomy — XBRL, CPT codes, meter types, etc.
    """

    def __init__(self, mappings_dir: Path | None = None):
        """Load mappings from all JSON files in mappings_dir.

        If mappings_dir is None or doesn't exist, operates in
        discovery mode — all concepts return as unmapped.
        """
        self._business_terms: dict[str, dict] = {}
        self._exact_mappings: dict[str, tuple[str, str, str]] = {}
        self._prefix_rules: list[tuple[str, str, str, str]] = []
        self._pattern_rules: list[tuple[str, str, str, str]] = []
        self._heuristic_categories: list[tuple[str, str, str]] = []
        self._source_mappings: list[str] = []
        self._unmapped_concepts: list[str] = []
        self._classify_counts: dict[str, int] = {
            "total": 0, "tier_1": 0, "tier_2_prefix": 0,
            "tier_2_pattern": 0, "tier_3": 0, "unmapped": 0,
        }

        if mappings_dir is None or not Path(mappings_dir).exists():
            if mappings_dir is not None:
                logger.info(
                    "No concept mappings found at %s. "
                    "Operating in discovery mode — all concepts will be unmapped.",
                    mappings_dir,
                )
            else:
                logger.info(
                    "No concept mappings found. "
                    "Operating in discovery mode — all concepts will be unmapped.",
                )
            return

        mappings_path = Path(mappings_dir)
        json_files = sorted(mappings_path.glob("*.json"))

        if not json_files:
            logger.info(
                "No concept mappings found in %s. "
                "Operating in discovery mode — all concepts will be unmapped.",
                mappings_dir,
            )
            return

        for json_file in json_files:
            self._load_mapping_file(json_file)

        logger.info(
            "Loaded concept mappings: %d exact, %d prefix, %d pattern, %d heuristic from %s",
            len(self._exact_mappings),
            len(self._prefix_rules),
            len(self._pattern_rules),
            len(self._heuristic_categories),
            [s for s in self._source_mappings],
        )

    def _load_mapping_file(self, path: Path) -> None:
        """Load a single mapping JSON file."""
        with open(path) as f:
            data = json.load(f)

        metadata = data.get("mapping_metadata", {})
        source_name = metadata.get("name", path.stem)
        self._source_mappings.append(source_name)

        # Business terms
        for bt_id, bt_data in data.get("business_terms", {}).items():
            self._business_terms[bt_id] = bt_data

        # Exact mappings: {concept: [bt_id, stmt, cat]}
        for concept, mapping in data.get("exact_mappings", {}).items():
            self._exact_mappings[concept] = (mapping[0], mapping[1], mapping[2])

        # Prefix rules: [{prefix, business_term_id, financial_statement, category}]
        for rule in data.get("prefix_rules", []):
            self._prefix_rules.append((
                rule["prefix"],
                rule["business_term_id"],
                rule["financial_statement"],
                rule["category"],
            ))

        # Pattern rules: [{pattern, business_term_id, financial_statement, category}]
        for rule in data.get("pattern_rules", []):
            self._pattern_rules.append((
                rule["pattern"],
                rule["business_term_id"],
                rule["financial_statement"],
                rule["category"],
            ))

        # Heuristic categories: {substring: {financial_statement, category}}
        for substring, heuristic in data.get("heuristic_categories", {}).items():
            self._heuristic_categories.append((
                substring,
                heuristic["financial_statement"],
                heuristic["category"],
            ))

    def classify(self, concept: str) -> dict:
        """Classify a concept through the tier hierarchy.

        Returns:
            {
                "business_term_id": "BT-024" | None,
                "business_term": "Revenue" | None,
                "financial_statement": "income_statement" | None,
                "category": "line_item" | None,
                "tier": 1 | 2 | 3 | "unmapped",
                "confidence": 1.0 | 0.7 | 0.6 | 0.3 | 0.0,
                "mapping_method": "exact_match" | "prefix_match" | "pattern_match" | "heuristic" | "unmapped",
                "source_mapping": "xbrl-us-gaap" | None
            }
        """
        self._classify_counts["total"] += 1
        source = self._source_mappings[0] if self._source_mappings else None

        # No mappings loaded → discovery mode
        if not self._exact_mappings and not self._prefix_rules and not self._pattern_rules:
            self._classify_counts["unmapped"] += 1
            self._unmapped_concepts.append(concept)
            return {
                "business_term_id": None,
                "business_term": None,
                "financial_statement": None,
                "category": None,
                "tier": "unmapped",
                "confidence": 0.0,
                "mapping_method": "unmapped",
                "source_mapping": None,
            }

        # Tier 1: Exact match
        if concept in self._exact_mappings:
            business_term_id, stmt, cat = self._exact_mappings[concept]
            bt_name = self._business_terms.get(business_term_id, {}).get("name")
            self._classify_counts["tier_1"] += 1
            return {
                "business_term_id": business_term_id,
                "business_term": bt_name,
                "financial_statement": stmt,
                "category": cat,
                "tier": 1,
                "confidence": 1.0,
                "mapping_method": "exact_match",
                "source_mapping": source,
            }

        # Tier 2: Prefix match (confidence 0.7)
        for prefix, business_term_id, stmt, cat in self._prefix_rules:
            if concept.startswith(prefix):
                bt_name = self._business_terms.get(business_term_id, {}).get("name")
                self._classify_counts["tier_2_prefix"] += 1
                return {
                    "business_term_id": business_term_id,
                    "business_term": bt_name,
                    "financial_statement": stmt,
                    "category": cat,
                    "tier": 2,
                    "confidence": 0.7,
                    "mapping_method": "prefix_match",
                    "source_mapping": source,
                }

        # Tier 2: Pattern match (confidence 0.6)
        for pattern, business_term_id, stmt, cat in self._pattern_rules:
            if re.match(pattern, concept):
                bt_name = self._business_terms.get(business_term_id, {}).get("name")
                self._classify_counts["tier_2_pattern"] += 1
                return {
                    "business_term_id": business_term_id,
                    "business_term": bt_name,
                    "financial_statement": stmt,
                    "category": cat,
                    "tier": 2,
                    "confidence": 0.6,
                    "mapping_method": "pattern_match",
                    "source_mapping": source,
                }

        # Tier 3: Unmapped — assign heuristic category
        stmt, cat = self._heuristic_category(concept)
        self._classify_counts["tier_3"] += 1
        return {
            "business_term_id": None,
            "business_term": None,
            "financial_statement": stmt,
            "category": cat,
            "tier": 3,
            "confidence": 0.0,
            "mapping_method": "unmapped",
            "source_mapping": source,
        }

    def _heuristic_category(self, concept: str) -> tuple[str, str]:
        """Assign a heuristic financial statement and category based on substrings."""
        for substring, stmt, cat in self._heuristic_categories:
            if substring in concept:
                return stmt, cat
        return "other", "uncategorized"

    def get_unmapped_concepts(self) -> list[str]:
        """Return all concepts that have been classified as unmapped."""
        return list(self._unmapped_concepts)

    def get_mapping_coverage(self) -> dict:
        """Return mapping coverage stats."""
        return dict(self._classify_counts)


# ---------------------------------------------------------------------------
# Module-level functions for backwards compatibility
# ---------------------------------------------------------------------------

# Default normalizer instance, lazily initialized
_default_normalizer: ConceptNormalizer | None = None


def _get_default_normalizer() -> ConceptNormalizer:
    """Get or create the default normalizer using domain manifest hints."""
    global _default_normalizer
    if _default_normalizer is None:
        from .config import get_concept_mappings_dir
        mappings_dir = get_concept_mappings_dir()
        _default_normalizer = ConceptNormalizer(mappings_dir)
    return _default_normalizer


def _classify_concept(concept: str) -> dict:
    """Classify a single concept using the default normalizer.

    Backwards-compatible wrapper. Returns the same dict shape as before
    (without source_mapping for compatibility).
    """
    normalizer = _get_default_normalizer()
    result = normalizer.classify(concept)

    # Map "unmapped" tier string back to int 3 for backwards compat
    if result["tier"] == "unmapped":
        result["tier"] = 3

    # Remove source_mapping for backwards compat
    result.pop("source_mapping", None)

    return result


def normalize_concepts(
    *,
    raw_warehouse_path: str | Path,
    catalog_path: str | Path,
) -> list[dict]:
    """Read raw.xbrl_company_facts and classify all us-gaap concepts."""
    catalog = get_catalog(raw_warehouse_path, catalog_path)
    table = catalog.load_table("raw.xbrl_company_facts")
    rows = read_with_duckdb(table)

    concept_stats = _compute_concept_stats(rows)
    return _build_proposals(concept_stats)


def normalize_concepts_from_records(records: list[dict]) -> list[dict]:
    """Classify concepts from raw fact records (for testing without Iceberg)."""
    concept_stats = _compute_concept_stats(records)
    return _build_proposals(concept_stats)


def _compute_concept_stats(rows: list[dict]) -> dict[str, dict]:
    """Compute per-concept statistics from raw fact rows."""
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
            "business_term": classification["business_term"],
            "business_term_id": classification["business_term_id"],
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
            f"{classification['business_term']} ({classification['business_term_id']}). "
            f"Appears in {stats['company_count']} companies, {stats['fact_count']} facts."
        )
    elif method == "prefix_match":
        return (
            f"Prefix match: '{concept}' starts with a known prefix for "
            f"{classification['business_term']} ({classification['business_term_id']}). "
            f"Appears in {stats['company_count']} companies, {stats['fact_count']} facts."
        )
    elif method == "pattern_match":
        return (
            f"Pattern match: '{concept}' matched regex for "
            f"{classification['business_term']} ({classification['business_term_id']}). "
            f"Appears in {stats['company_count']} companies, {stats['fact_count']} facts."
        )
    else:
        return (
            f"Unmapped: '{concept}' did not match any known business term. "
            f"Heuristic category: {classification['financial_statement']}/{classification['category']}. "
            f"Appears in {stats['company_count']} companies, {stats['fact_count']} facts."
        )


def compute_coverage(proposals: list[dict], fact_rows: list[dict] | None = None) -> dict:
    """Compute coverage statistics for a set of proposals."""
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
