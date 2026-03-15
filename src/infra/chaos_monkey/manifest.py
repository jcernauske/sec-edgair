"""Chaos manifest writer and reader.

Produces timestamped JSON manifests recording every corruption the monkey
injected, for later reconciliation against DQ results.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.infra.chaos_monkey.config import CHAOS_MANIFESTS_DIR, DQ_DIMENSIONS
from src.infra.chaos_monkey.injector import InjectionPlan


def write_manifest(
    plan: InjectionPlan,
    source_table: str,
    source_row_count: int,
    injection_rate: float,
    run_id: str | None = None,
) -> Path:
    """Write the chaos manifest to governance/chaos-manifests/.

    Returns the path to the written manifest file.
    """
    now = datetime.now(timezone.utc)
    if run_id is None:
        run_id = f"chaos-{now.strftime('%Y-%m-%d-%H-%M-%S')}"

    manifest = {
        "run_id": run_id,
        "timestamp": now.isoformat(),
        "environment": "dev",
        "source_table": source_table,
        "source_row_count": source_row_count,
        "injected_row_count": len(plan.corrupted_rows),
        "injection_rate": injection_rate,
        "dimension_coverage": plan.dimension_coverage,
        "injections": [
            {
                "corruption_id": c.corruption_id,
                "dimension": c.dimension,
                "strategy": c.strategy,
                "description": c.description,
                "field": c.field_name,
                "original_value": c.original_value,
                "corrupted_value": c.corrupted_value,
                "row_identifier": c.row_identifier,
                "expected_detection": c.expected_detection,
            }
            for c in plan.corruptions
        ],
    }

    CHAOS_MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"chaos-manifest-{now.strftime('%Y-%m-%d-%H-%M-%S')}.json"
    path = CHAOS_MANIFESTS_DIR / filename
    path.write_text(json.dumps(manifest, indent=2, default=str))
    return path


def read_manifest(path: Path) -> dict:
    """Read a chaos manifest from disk."""
    return json.loads(path.read_text())


def get_latest_manifest() -> Path | None:
    """Return the path to the most recent chaos manifest, or None."""
    CHAOS_MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
    manifests = sorted(CHAOS_MANIFESTS_DIR.glob("chaos-manifest-*.json"))
    return manifests[-1] if manifests else None
