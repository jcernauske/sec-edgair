"""Tests for promoting approved mappings to Iceberg."""

from src.base.entity_resolution.promote import promote_approved
from src.base.entity_resolution.staging import approve_proposals, write_staging
from src.infra.iceberg_setup import get_catalog, read_with_duckdb


def _make_approved_proposals():
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


def test_promote_writes_to_iceberg(tmp_path):
    """Approved mappings should be written to base.entity_mappings."""
    staging_file = tmp_path / "proposed-mappings.json"
    write_staging(_make_approved_proposals(), staging_file)
    approve_proposals(staging_file)

    warehouse = tmp_path / "iceberg_warehouse"
    catalog_db = tmp_path / "catalog.db"

    result = promote_approved(
        staging_path=staging_file,
        warehouse_path=warehouse,
        catalog_path=catalog_db,
    )

    assert result["promoted"] == 2
    assert result["mappings_snapshot_id"] > 0
    assert result["audit_snapshot_id"] > 0

    # Verify mappings readable via DuckDB
    catalog = get_catalog(warehouse, catalog_db)
    table = catalog.load_table("base.entity_mappings")
    rows = read_with_duckdb(table)
    assert len(rows) == 2

    ciks = {r["cik"] for r in rows}
    assert ciks == {320193, 19617}

    for row in rows:
        assert row["status"] == "approved"
        assert row["approved_by"] == "human:jeff"


def test_promote_creates_audit_entries(tmp_path):
    """Each approved mapping creates 2 audit entries (proposed + approved)."""
    staging_file = tmp_path / "proposed-mappings.json"
    write_staging(_make_approved_proposals(), staging_file)
    approve_proposals(staging_file)

    warehouse = tmp_path / "iceberg_warehouse"
    catalog_db = tmp_path / "catalog.db"

    result = promote_approved(
        staging_path=staging_file,
        warehouse_path=warehouse,
        catalog_path=catalog_db,
    )

    assert result["audit_entries"] == 4  # 2 proposed + 2 approved

    catalog = get_catalog(warehouse, catalog_db)
    table = catalog.load_table("base.entity_resolution_audit")
    rows = read_with_duckdb(table)
    assert len(rows) == 4

    actions = {r["action"] for r in rows}
    assert actions == {"proposed", "approved"}

    mapping_ids = {r["mapping_id"] for r in rows}
    assert mapping_ids == {"ER-001", "ER-002"}


def test_promote_no_approved_is_noop(tmp_path):
    """Promoting with no approved mappings returns early."""
    staging_file = tmp_path / "proposed-mappings.json"
    write_staging(_make_approved_proposals(), staging_file)
    # Don't approve — all still pending

    warehouse = tmp_path / "iceberg_warehouse"
    catalog_db = tmp_path / "catalog.db"

    result = promote_approved(
        staging_path=staging_file,
        warehouse_path=warehouse,
        catalog_path=catalog_db,
    )

    assert result["promoted"] == 0


def test_promote_archives_staging(tmp_path):
    """After promotion, staging file should be archived."""
    staging_file = tmp_path / "proposed-mappings.json"
    archive_dir = tmp_path / "archive"
    write_staging(_make_approved_proposals(), staging_file)
    approve_proposals(staging_file)

    warehouse = tmp_path / "iceberg_warehouse"
    catalog_db = tmp_path / "catalog.db"

    result = promote_approved(
        staging_path=staging_file,
        warehouse_path=warehouse,
        catalog_path=catalog_db,
        archive_dir=archive_dir,
    )

    assert result["archived_to"] is not None
    assert not staging_file.exists()


def test_promote_mapping_fields_complete(tmp_path):
    """All 14 fields should be present in promoted mappings."""
    staging_file = tmp_path / "proposed-mappings.json"
    write_staging(_make_approved_proposals(), staging_file)
    approve_proposals(staging_file)

    warehouse = tmp_path / "iceberg_warehouse"
    catalog_db = tmp_path / "catalog.db"

    promote_approved(
        staging_path=staging_file,
        warehouse_path=warehouse,
        catalog_path=catalog_db,
    )

    catalog = get_catalog(warehouse, catalog_db)
    table = catalog.load_table("base.entity_mappings")
    rows = read_with_duckdb(table)

    expected_fields = {
        "mapping_id", "cik", "canonical_name", "raw_entity_name",
        "ticker", "sic_code", "fiscal_year_end", "confidence",
        "resolution_method", "status", "resolved_by", "approved_by",
        "resolved_at", "approved_at",
    }
    assert set(rows[0].keys()) == expected_fields
