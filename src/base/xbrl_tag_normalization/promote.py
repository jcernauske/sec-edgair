"""Promote approved + unmapped concept mappings to Iceberg tables.

Reads proposals from staging, writes to:
- base.concept_mappings — the canonical mapping table
- base.tag_normalization_audit — the decision audit trail
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.base.entity_resolution.staging import archive_staging, read_staging
from src.infra.iceberg_setup import append_data, create_test_table, get_catalog

from .schema import CONCEPT_MAPPINGS_SCHEMA, TAG_NORMALIZATION_AUDIT_SCHEMA


def _parse_ts(value: str | datetime | None) -> datetime | None:
    """Parse an ISO timestamp string to datetime, or return as-is if already datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def promote_approved(
    *,
    staging_path: str | Path,
    warehouse_path: str | Path,
    catalog_path: str | Path,
    archive_dir: str | Path | None = None,
) -> dict:
    """Promote approved + unmapped mappings from staging to Iceberg tables.

    Tier 1+2 approved mappings and Tier 3 unmapped concepts are all written.
    Returns a summary dict with counts and snapshot IDs.
    """
    proposals = read_staging(staging_path)
    promotable = [
        p for p in proposals
        if p.get("status") in ("approved", "unmapped")
    ]

    if not promotable:
        return {"promoted": 0, "message": "No promotable mappings"}

    catalog = get_catalog(warehouse_path, catalog_path)

    mappings_table = create_test_table(catalog, "base", "concept_mappings", CONCEPT_MAPPINGS_SCHEMA)
    audit_table = create_test_table(catalog, "base", "tag_normalization_audit", TAG_NORMALIZATION_AUDIT_SCHEMA)

    now = datetime.now(timezone.utc)

    mapping_records = []
    audit_records = []

    for p in promotable:
        mapping_records.append({
            "mapping_id": p["mapping_id"],
            "concept": p["concept"],
            "canonical_cde": p.get("canonical_cde"),
            "cde_id": p.get("cde_id"),
            "financial_statement": p["financial_statement"],
            "category": p["category"],
            "tier": p["tier"],
            "confidence": p["confidence"],
            "mapping_method": p["mapping_method"],
            "status": p["status"],
            "mapped_by": p["mapped_by"],
            "mapped_at": _parse_ts(p["mapped_at"]),
        })

        action = "proposed" if p["status"] == "approved" else "classified_unmapped"
        audit_records.append({
            "audit_id": str(uuid.uuid4()),
            "mapping_id": p["mapping_id"],
            "action": action,
            "actor": p["mapped_by"],
            "reasoning": p.get("reasoning", "Tag normalization proposal"),
            "evidence": p.get("evidence", "{}"),
            "confidence_at_action": p["confidence"],
            "timestamp": _parse_ts(p["mapped_at"]),
        })

        if p["status"] == "approved":
            audit_records.append({
                "audit_id": str(uuid.uuid4()),
                "mapping_id": p["mapping_id"],
                "action": "approved",
                "actor": p.get("approved_by", "auto"),
                "reasoning": f"Mapping {p['mapping_id']} approved: {p['concept']} → {p.get('canonical_cde', 'N/A')}",
                "evidence": json.dumps({
                    "confidence": p["confidence"],
                    "mapping_method": p["mapping_method"],
                    "tier": p["tier"],
                }),
                "confidence_at_action": p["confidence"],
                "timestamp": _parse_ts(p.get("approved_at")) or now,
            })

    mappings_snap = append_data(mappings_table, mapping_records)
    audit_snap = append_data(audit_table, audit_records)

    archived = None
    if archive_dir:
        remaining = read_staging(staging_path)
        still_pending = [p for p in remaining if p.get("status") == "pending"]
        if not still_pending:
            archived = archive_staging(staging_path, archive_dir)

    return {
        "promoted": len(promotable),
        "approved_count": len([p for p in promotable if p["status"] == "approved"]),
        "unmapped_count": len([p for p in promotable if p["status"] == "unmapped"]),
        "mappings_snapshot_id": mappings_snap,
        "audit_snapshot_id": audit_snap,
        "audit_entries": len(audit_records),
        "archived_to": str(archived) if archived else None,
    }
