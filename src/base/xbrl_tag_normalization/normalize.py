"""Backwards-compatibility shim — re-exports from src.base.concept_normalization.normalize."""

from src.base.concept_normalization.normalize import (  # noqa: F401
    ConceptNormalizer,
    _build_proposals,
    _build_reasoning,
    _classify_concept,
    _compute_concept_stats,
    compute_coverage,
    normalize_concepts,
    normalize_concepts_from_records,
)
