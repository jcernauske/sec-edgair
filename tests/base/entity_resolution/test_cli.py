"""Tests for the entity resolution CLI."""

import json
from unittest.mock import patch

from src.base.entity_resolution.cli import main
from src.base.entity_resolution.staging import read_staging, write_staging


def _make_proposals():
    return [
        {
            "mapping_id": "ER-001",
            "cik": 320193,
            "canonical_name": "Apple Inc.",
            "raw_entity_name": "Apple Inc.",
            "ticker": "AAPL",
            "sic_code": "3571",
            "fiscal_year_end": "0930",
            "confidence": 1.0,
            "resolution_method": "exact_cik_match",
            "status": "pending",
            "resolved_by": "@entity-resolver",
            "approved_by": None,
            "resolved_at": "2026-03-14T00:00:00+00:00",
            "approved_at": None,
            "reasoning": "CIK 320193 exact match",
            "evidence": '{"source": "KNOWN_ENTITIES"}',
        },
        {
            "mapping_id": "ER-002",
            "cik": 19617,
            "canonical_name": "JPMorgan Chase & Co.",
            "raw_entity_name": "JPMORGAN CHASE & CO",
            "ticker": "JPM",
            "sic_code": "6020",
            "fiscal_year_end": "1231",
            "confidence": 1.0,
            "resolution_method": "exact_cik_match",
            "status": "pending",
            "resolved_by": "@entity-resolver",
            "approved_by": None,
            "resolved_at": "2026-03-14T00:00:00+00:00",
            "approved_at": None,
            "reasoning": "CIK 19617 exact match",
            "evidence": '{"source": "KNOWN_ENTITIES"}',
        },
    ]


def test_cli_status_shows_pending(tmp_path, capsys):
    """CLI status command should display pending proposals."""
    staging_file = tmp_path / "proposed-mappings.json"
    write_staging(_make_proposals(), staging_file)

    main(["--staging", str(staging_file), "status"])

    output = capsys.readouterr().out
    assert "ER-001" in output
    assert "ER-002" in output
    assert "Apple Inc." in output
    assert "2 pending" in output


def test_cli_status_no_pending(tmp_path, capsys):
    """CLI status with no pending should say so."""
    staging_file = tmp_path / "no-proposals.json"
    main(["--staging", str(staging_file), "status"])

    output = capsys.readouterr().out
    assert "No pending" in output


def test_cli_approve_all(tmp_path, capsys):
    """CLI approve without IDs approves all."""
    staging_file = tmp_path / "proposed-mappings.json"
    warehouse = tmp_path / "warehouse"
    catalog = tmp_path / "catalog.db"
    write_staging(_make_proposals(), staging_file)

    main([
        "--staging", str(staging_file),
        "--warehouse", str(warehouse),
        "--catalog", str(catalog),
        "approve",
    ])

    output = capsys.readouterr().out
    assert "Approved 2" in output
    assert "Promoted 2" in output


def test_cli_approve_specific(tmp_path, capsys):
    """CLI approve with specific IDs approves only those."""
    staging_file = tmp_path / "proposed-mappings.json"
    warehouse = tmp_path / "warehouse"
    catalog = tmp_path / "catalog.db"
    write_staging(_make_proposals(), staging_file)

    main([
        "--staging", str(staging_file),
        "--warehouse", str(warehouse),
        "--catalog", str(catalog),
        "approve", "ER-001",
    ])

    output = capsys.readouterr().out
    assert "Approved 1" in output

    # ER-002 still pending
    data = read_staging(staging_file)
    er002 = next(p for p in data if p["mapping_id"] == "ER-002")
    assert er002["status"] == "pending"


def test_cli_reject(tmp_path, capsys):
    """CLI reject marks proposals as rejected with reason."""
    staging_file = tmp_path / "proposed-mappings.json"
    write_staging(_make_proposals(), staging_file)

    main([
        "--staging", str(staging_file),
        "reject", "ER-002", "--reason", "Wrong entity",
    ])

    output = capsys.readouterr().out
    assert "Rejected 1" in output

    data = read_staging(staging_file)
    er002 = next(p for p in data if p["mapping_id"] == "ER-002")
    assert er002["status"] == "rejected"
    assert er002["rejection_reason"] == "Wrong entity"
