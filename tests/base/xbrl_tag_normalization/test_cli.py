"""Tests for the XBRL tag normalization CLI."""

from src.base.entity_resolution.staging import read_staging, write_staging
from src.base.xbrl_tag_normalization.cli import main


def _make_proposals():
    return [
        {
            "mapping_id": "TN-0001",
            "concept": "Assets",
            "business_term": "Total Assets",
            "business_term_id": "BT-024",
            "financial_statement": "balance_sheet",
            "category": "assets",
            "tier": 1,
            "confidence": 1.0,
            "mapping_method": "exact_match",
            "status": "pending",
            "mapped_by": "@tag-normalizer",
            "mapped_at": "2026-03-14T00:00:00+00:00",
            "reasoning": "Exact match",
            "evidence": "{}",
        },
        {
            "mapping_id": "TN-0002",
            "concept": "Revenues",
            "business_term": "Revenue",
            "business_term_id": "BT-022",
            "financial_statement": "income_statement",
            "category": "revenue",
            "tier": 1,
            "confidence": 1.0,
            "mapping_method": "exact_match",
            "status": "pending",
            "mapped_by": "@tag-normalizer",
            "mapped_at": "2026-03-14T00:00:00+00:00",
            "reasoning": "Exact match",
            "evidence": "{}",
        },
    ]


def test_cli_status_shows_pending(tmp_path, capsys):
    """CLI status command should display pending proposals."""
    staging_file = tmp_path / "proposed-mappings.json"
    write_staging(_make_proposals(), staging_file)

    main(["--staging", str(staging_file), "status"])

    output = capsys.readouterr().out
    assert "TN-0001" in output
    assert "TN-0002" in output
    assert "Assets" in output
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


def test_cli_reject(tmp_path, capsys):
    """CLI reject marks proposals as rejected with reason."""
    staging_file = tmp_path / "proposed-mappings.json"
    write_staging(_make_proposals(), staging_file)

    main([
        "--staging", str(staging_file),
        "reject", "TN-0002", "--reason", "Wrong CDE mapping",
    ])

    output = capsys.readouterr().out
    assert "Rejected 1" in output

    data = read_staging(staging_file)
    tn002 = next(p for p in data if p["mapping_id"] == "TN-0002")
    assert tn002["status"] == "rejected"
    assert tn002["rejection_reason"] == "Wrong CDE mapping"
