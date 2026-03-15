"""Backwards-compatibility shim — re-exports from src.base.concept_normalization.config."""

from src.base.concept_normalization.config import *  # noqa: F401, F403
from src.base.concept_normalization.config import (  # noqa: F401 — explicit re-exports
    ARCHIVE_DIR,
    CATALOG_PATH,
    CONFIDENCE_FLOOR,
    REQUIRE_HUMAN_APPROVAL,
    STAGING_DIR,
    STAGING_FILE,
    WAREHOUSE_PATH,
    get_concept_mappings_dir,
)

# Re-export the old Python-dict mappings for any code that still imports them directly.
# These are now loaded from JSON at runtime, but we provide them here for backwards compat.
from src.base.concept_normalization.normalize import _get_default_normalizer as _get_norm


def _lazy_mappings():
    n = _get_norm()
    return n._exact_mappings, n._prefix_rules, n._pattern_rules, n._heuristic_categories, n._business_terms


# Lazy properties would break direct imports, so we provide the constants
# by loading them once on import. This is acceptable since the JSON is small.
_n = _get_norm()
BUSINESS_TERM_DEFINITIONS = {
    bt_id: {
        "name": bt.get("name", ""),
        "category": bt.get("financial_statement", ""),
        "subcategory": bt.get("category", ""),
        "definition": "",
    }
    for bt_id, bt in _n._business_terms.items()
}
EXACT_MAPPINGS = dict(_n._exact_mappings)
PREFIX_RULES = list(_n._prefix_rules)
PATTERN_RULES = list(_n._pattern_rules)
HEURISTIC_CATEGORIES = list(_n._heuristic_categories)
