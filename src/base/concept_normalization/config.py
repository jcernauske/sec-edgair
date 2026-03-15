"""Configuration for concept normalization pipeline.

Reads mapping paths from the domain manifest instead of hardcoding
XBRL-specific mappings. The mappings themselves live in JSON files
under domain/concept-mappings/.
"""

from __future__ import annotations

import logging
from pathlib import Path

from src.config import PROJECT_ROOT, REQUIRE_HUMAN_APPROVAL  # noqa: F401 — re-exported

logger = logging.getLogger(__name__)

# Confidence threshold — mappings below this ALWAYS require human approval
CONFIDENCE_FLOOR = 0.7

# Paths (relative to project root)
WAREHOUSE_PATH = PROJECT_ROOT / "data" / "base" / "iceberg_warehouse"
CATALOG_PATH = PROJECT_ROOT / "data" / "catalog" / "catalog.db"
STAGING_DIR = PROJECT_ROOT / "governance" / "tag-normalization"
STAGING_FILE = STAGING_DIR / "proposed-mappings.json"
ARCHIVE_DIR = STAGING_DIR / "archive"


def get_concept_mappings_dir() -> Path | None:
    """Get the concept mappings directory from the domain manifest.

    Returns None if the manifest doesn't exist or doesn't specify
    a concept_mappings path — the normalizer will operate in discovery mode.
    """
    try:
        from src.domain_loader import load_manifest
        manifest = load_manifest()
        return manifest.hints.concept_mappings
    except (FileNotFoundError, Exception) as e:
        logger.info("No domain manifest or concept_mappings hint: %s", e)
        return None
