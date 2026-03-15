"""Generic concept normalization engine.

Loads concept → business term mappings from JSON config files.
Works with any taxonomy — XBRL, CPT codes, meter types, etc.
"""

from .normalize import (
    ConceptNormalizer,
    compute_coverage,
    normalize_concepts,
    normalize_concepts_from_records,
)

__all__ = [
    "ConceptNormalizer",
    "compute_coverage",
    "normalize_concepts",
    "normalize_concepts_from_records",
]
