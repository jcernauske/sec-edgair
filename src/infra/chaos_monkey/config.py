"""Chaos Monkey configuration.

All chaos monkey settings live here. The kill switch is checked at runtime
by safety.py — this module only defines the values.
"""

from pathlib import Path

from src.config import PROJECT_ROOT

# ---------------------------------------------------------------------------
# Kill switch (Layer 1) — must also be True in src/config.py
# ---------------------------------------------------------------------------
# Layer 2 is the SEC_EDGAIR_ENV environment variable (checked at runtime)
# Layer 3 is output path validation (checked at runtime)

# ---------------------------------------------------------------------------
# Injection settings
# ---------------------------------------------------------------------------
DEFAULT_INJECTION_RATE = 0.07  # 7% of source rows
MIN_INJECTION_RATE = 0.05
MAX_INJECTION_RATE = 0.10

# Minimum corruptions per dimension to guarantee full coverage
MIN_PER_DIMENSION = 5

# ---------------------------------------------------------------------------
# DQ dimensions — the 10 dimensions every run must violate
# ---------------------------------------------------------------------------
DQ_DIMENSIONS = [
    "completeness",
    "validity",
    "uniqueness",
    "consistency",
    "accuracy",
    "reasonableness",
    "freshness",
    "volume",
    "referential_integrity",
    "coverage",
]

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SHADOW_WAREHOUSE_PATH = PROJECT_ROOT / "data" / "shadow" / "iceberg_warehouse"
SHADOW_CATALOG_PATH = PROJECT_ROOT / "data" / "shadow" / "catalog" / "catalog.db"
CHAOS_MANIFESTS_DIR = PROJECT_ROOT / "governance" / "chaos-manifests"

# Source data paths (read-only for the monkey)
SOURCE_WAREHOUSE_PATH = PROJECT_ROOT / "data" / "raw" / "iceberg_warehouse"
SOURCE_CATALOG_PATH = PROJECT_ROOT / "data" / "catalog" / "catalog.db"
