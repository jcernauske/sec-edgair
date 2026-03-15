"""Backwards-compatibility shim — imports from src.base.concept_normalization.

This module is deprecated. Use src.base.concept_normalization instead.
"""

from src.base.concept_normalization import (  # noqa: F401
    ConceptNormalizer,
    compute_coverage,
    normalize_concepts,
    normalize_concepts_from_records,
)
