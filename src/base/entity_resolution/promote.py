"""Promote approved entity mappings to Iceberg tables.

Reads approved proposals from staging, writes to:
- base.entity_mappings — the canonical mapping table
- base.entity_resolution_audit — the decision audit trail
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


from src.infra.iceberg_setup import append_data, create_test_table, get_catalog, read_with_duckdb

from .schema import ENTITY_MAPPINGS_SCHEMA, ENTITY_RESOLUTION_AUDIT_SCHEMA
from .staging import archive_staging, read_staging


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
    """Promote approved mappings from staging to Iceberg tables.

    Returns a summary dict with counts and snapshot IDs.
    """
    proposals = read_staging(staging_path)
    approved = [p for p in proposals if p.get("status") == "approved"]

    if not approved:
        return {"promoted": 0, "message": "No approved mappings to promote"}

    catalog = get_catalog(warehouse_path, catalog_path)

    # Create tables if they don't exist
    mappings_table = create_test_table(catalog, "base", "entity_mappings", ENTITY_MAPPINGS_SCHEMA)
    audit_table = create_test_table(catalog, "base", "entity_resolution_audit", ENTITY_RESOLUTION_AUDIT_SCHEMA)

    now = datetime.now(timezone.utc)

    # Build mapping records (strip extra fields like reasoning/evidence)
    # Uniqueness check: skip CIKs that already have approved mappings
    existing_ciks = set()
    try:
        existing = read_with_duckdb(mappings_table)
        existing_ciks = {r["cik"] for r in existing if r.get("status") == "approved"}
    except Exception:
        pass  # Empty table or first run

    duplicates = [p for p in approved if p["cik"] in existing_ciks]
    approved = [p for p in approved if p["cik"] not in existing_ciks]

    if duplicates:
        dup_ciks = [str(p["cik"]) for p in duplicates]
        print(f"Skipping {len(duplicates)} duplicate CIK(s) already in entity_mappings: {', '.join(dup_ciks)}")

    if not approved:
        return {"promoted": 0, "skipped_duplicates": len(duplicates), "message": "All approved mappings already exist"}

    mapping_records = []
    audit_records = []

    for p in approved:
        mapping_records.append({
            "mapping_id": p["mapping_id"],
            "cik": p["cik"],
            "canonical_name": p["canonical_name"],
            "raw_entity_name": p["raw_entity_name"],
            "ticker": p.get("ticker"),
            "sic_code": p.get("sic_code"),
            "fiscal_year_end": p.get("fiscal_year_end"),
            "confidence": p["confidence"],
            "resolution_method": p["resolution_method"],
            "status": "approved",
            "resolved_by": p["resolved_by"],
            "approved_by": p.get("approved_by", "auto"),
            "resolved_at": _parse_ts(p["resolved_at"]),
            "approved_at": _parse_ts(p.get("approved_at")) or now,
        })

        # Proposal audit entry
        audit_records.append({
            "audit_id": str(uuid.uuid4()),
            "mapping_id": p["mapping_id"],
            "action": "proposed",
            "actor": p["resolved_by"],
            "reasoning": p.get("reasoning", "Entity resolution proposal"),
            "evidence": p.get("evidence", "{}"),
            "confidence_at_action": p["confidence"],
            "timestamp": _parse_ts(p["resolved_at"]),
        })

        # Approval audit entry
        audit_records.append({
            "audit_id": str(uuid.uuid4()),
            "mapping_id": p["mapping_id"],
            "action": "approved",
            "actor": p.get("approved_by", "auto"),
            "reasoning": f"Mapping {p['mapping_id']} approved for CIK {p['cik']}",
            "evidence": json.dumps({
                "confidence": p["confidence"],
                "resolution_method": p["resolution_method"],
            }),
            "confidence_at_action": p["confidence"],
            "timestamp": _parse_ts(p.get("approved_at")) or now,
        })

    mappings_snap = append_data(mappings_table, mapping_records)
    audit_snap = append_data(audit_table, audit_records)

    # Archive staging file if archive_dir provided and no pending remain
    archived = None
    if archive_dir:
        remaining = read_staging(staging_path)
        still_pending = [p for p in remaining if p.get("status") == "pending"]
        if not still_pending:
            archived = archive_staging(staging_path, archive_dir)

    return {
        "promoted": len(approved),
        "mappings_snapshot_id": mappings_snap,
        "audit_snapshot_id": audit_snap,
        "audit_entries": len(audit_records),
        "archived_to": str(archived) if archived else None,
    }
