"""Tests for staging file management."""

import json

from src.base.entity_resolution.staging import (
    approve_proposals,
    archive_staging,
    get_pending,
    read_staging,
    reject_proposals,
    write_staging,
)


def _make_proposals():
    return [
        {
            "mapping_id": "ER-001",
            "cik": 320193,
            "canonical_name": "Apple Inc.",
            "raw_entity_name": "Apple Inc.",
            "confidence": 1.0,
            "resolution_method": "exact_cik_match",
            "status": "pending",
            "resolved_by": "@entity-resolver",
            "approved_by": None,
            "resolved_at": "2026-03-14T00:00:00+00:00",
            "approved_at": None,
        },
        {
            "mapping_id": "ER-002",
            "cik": 19617,
            "canonical_name": "JPMorgan Chase & Co.",
            "raw_entity_name": "JPMORGAN CHASE & CO",
            "confidence": 1.0,
            "resolution_method": "exact_cik_match",
            "status": "pending",
            "resolved_by": "@entity-resolver",
            "approved_by": None,
            "resolved_at": "2026-03-14T00:00:00+00:00",
            "approved_at": None,
        },
    ]


def test_write_and_read_staging(tmp_path):
    """Write proposals to staging and read back."""
    staging_file = tmp_path / "proposed-mappings.json"
    proposals = _make_proposals()
    write_staging(proposals, staging_file)

    loaded = read_staging(staging_file)
    assert len(loaded) == 2
    assert loaded[0]["mapping_id"] == "ER-001"


def test_read_staging_missing_file(tmp_path):
    """Reading from nonexistent file returns empty list."""
    staging_file = tmp_path / "does-not-exist.json"
    assert read_staging(staging_file) == []


def test_approve_all_proposals(tmp_path):
    """Approve all pending proposals."""
    staging_file = tmp_path / "proposed-mappings.json"
    write_staging(_make_proposals(), staging_file)

    approved = approve_proposals(staging_file)
    assert len(approved) == 2
    for a in approved:
        assert a["status"] == "approved"
        assert a["approved_by"] == "human:jeff"
        assert a["approved_at"] is not None


def test_approve_specific_proposals(tmp_path):
    """Approve only specific mapping IDs."""
    staging_file = tmp_path / "proposed-mappings.json"
    write_staging(_make_proposals(), staging_file)

    approved = approve_proposals(staging_file, ["ER-001"])
    assert len(approved) == 1
    assert approved[0]["mapping_id"] == "ER-001"

    # ER-002 should still be pending
    pending = get_pending(staging_file)
    assert len(pending) == 1
    assert pending[0]["mapping_id"] == "ER-002"


def test_reject_proposals(tmp_path):
    """Reject specific proposals with reason."""
    staging_file = tmp_path / "proposed-mappings.json"
    write_staging(_make_proposals(), staging_file)

    rejected = reject_proposals(staging_file, ["ER-002"], reason="Wrong entity")
    assert len(rejected) == 1
    assert rejected[0]["status"] == "rejected"
    assert rejected[0]["rejection_reason"] == "Wrong entity"

    # ER-001 should still be pending
    pending = get_pending(staging_file)
    assert len(pending) == 1


def test_approve_idempotent(tmp_path):
    """Approving already-approved proposals does nothing."""
    staging_file = tmp_path / "proposed-mappings.json"
    write_staging(_make_proposals(), staging_file)

    approve_proposals(staging_file)
    # Second approve should return empty
    second = approve_proposals(staging_file)
    assert len(second) == 0


def test_archive_staging(tmp_path):
    """Archive staging file to archive directory."""
    staging_file = tmp_path / "proposed-mappings.json"
    archive_dir = tmp_path / "archive"
    write_staging(_make_proposals(), staging_file)

    archived = archive_staging(staging_file, archive_dir)
    assert archived is not None
    assert archived.exists()
    assert not staging_file.exists()

    # Verify archive content
    data = json.loads(archived.read_text())
    assert len(data) == 2


def test_archive_missing_file(tmp_path):
    """Archiving nonexistent file returns None."""
    staging_file = tmp_path / "does-not-exist.json"
    archive_dir = tmp_path / "archive"
    assert archive_staging(staging_file, archive_dir) is None


def test_get_pending(tmp_path):
    """get_pending returns only pending proposals."""
    staging_file = tmp_path / "proposed-mappings.json"
    write_staging(_make_proposals(), staging_file)

    pending = get_pending(staging_file)
    assert len(pending) == 2

    approve_proposals(staging_file, ["ER-001"])
    pending = get_pending(staging_file)
    assert len(pending) == 1
    assert pending[0]["mapping_id"] == "ER-002"
