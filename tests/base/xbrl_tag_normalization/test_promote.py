"""Tests for promoting tag normalization mappings to Iceberg."""

from src.base.entity_resolution.staging import approve_proposals, write_staging
from src.base.xbrl_tag_normalization.promote import promote_approved
from src.infra.iceberg_setup import get_catalog, read_with_duckdb


def _make_proposals():
    """Mixed proposals: 2 tier 1 (pending) + 1 tier 3 (unmapped)."""
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
            "reasoning": "Exact match: Assets → Total Assets",
            "evidence": '{"concept": "Assets", "fact_count": 2919}',
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
            "reasoning": "Exact match: Revenues → Revenue",
            "evidence": '{"concept": "Revenues", "fact_count": 2637}',
        },
        {
            "mapping_id": "TN-0003",
            "concept": "DeferredTaxAssetsOther",
            "business_term": None,
            "business_term_id": None,
            "financial_statement": "income_statement",
            "category": "tax",
            "tier": 3,
            "confidence": 0.0,
            "mapping_method": "unmapped",
            "status": "unmapped",
            "mapped_by": "@tag-normalizer",
            "mapped_at": "2026-03-14T00:00:00+00:00",
            "reasoning": "Unmapped: DeferredTaxAssetsOther",
            "evidence": '{"concept": "DeferredTaxAssetsOther"}',
        },
    ]


def test_promote_writes_approved_and_unmapped(tmp_path):
    """Both approved and unmapped proposals should be written to Iceberg."""
    staging_file = tmp_path / "proposed-mappings.json"
    write_staging(_make_proposals(), staging_file)
    # Approve the pending ones
    approve_proposals(staging_file)

    warehouse = tmp_path / "iceberg_warehouse"
    catalog_db = tmp_path / "catalog.db"

    result = promote_approved(
        staging_path=staging_file,
        warehouse_path=warehouse,
        catalog_path=catalog_db,
    )

    assert result["promoted"] == 3
    assert result["approved_count"] == 2
    assert result["unmapped_count"] == 1

    catalog = get_catalog(warehouse, catalog_db)
    table = catalog.load_table("base.concept_mappings")
    rows = read_with_duckdb(table)
    assert len(rows) == 3

    concepts = {r["concept"] for r in rows}
    assert concepts == {"Assets", "Revenues", "DeferredTaxAssetsOther"}


def test_promote_creates_audit_entries(tmp_path):
    """Approved get 2 entries (proposed + approved), unmapped get 1 (classified_unmapped)."""
    staging_file = tmp_path / "proposed-mappings.json"
    write_staging(_make_proposals(), staging_file)
    approve_proposals(staging_file)

    warehouse = tmp_path / "iceberg_warehouse"
    catalog_db = tmp_path / "catalog.db"

    result = promote_approved(
        staging_path=staging_file,
        warehouse_path=warehouse,
        catalog_path=catalog_db,
    )

    # 2 approved × 2 entries + 1 unmapped × 1 entry = 5
    assert result["audit_entries"] == 5

    catalog = get_catalog(warehouse, catalog_db)
    table = catalog.load_table("base.tag_normalization_audit")
    rows = read_with_duckdb(table)
    assert len(rows) == 5

    actions = [r["action"] for r in rows]
    assert actions.count("proposed") == 2
    assert actions.count("approved") == 2
    assert actions.count("classified_unmapped") == 1


def test_promote_no_promotable_is_noop(tmp_path):
    """Promoting with no approved/unmapped returns early."""
    staging_file = tmp_path / "proposed-mappings.json"
    # Only pending proposals, not approved
    proposals = [p for p in _make_proposals() if p["status"] == "pending"]
    write_staging(proposals, staging_file)

    warehouse = tmp_path / "iceberg_warehouse"
    catalog_db = tmp_path / "catalog.db"

    result = promote_approved(
        staging_path=staging_file,
        warehouse_path=warehouse,
        catalog_path=catalog_db,
    )

    assert result["promoted"] == 0


def test_promote_mapping_fields_complete(tmp_path):
    """All 12 fields should be present in promoted mappings."""
    staging_file = tmp_path / "proposed-mappings.json"
    write_staging(_make_proposals(), staging_file)
    approve_proposals(staging_file)

    warehouse = tmp_path / "iceberg_warehouse"
    catalog_db = tmp_path / "catalog.db"

    promote_approved(
        staging_path=staging_file,
        warehouse_path=warehouse,
        catalog_path=catalog_db,
    )

    catalog = get_catalog(warehouse, catalog_db)
    table = catalog.load_table("base.concept_mappings")
    rows = read_with_duckdb(table)

    expected_fields = {
        "mapping_id", "concept", "business_term", "business_term_id",
        "financial_statement", "category", "tier", "confidence",
        "mapping_method", "status", "mapped_by", "mapped_at", "load_date",
    }
    assert set(rows[0].keys()) == expected_fields


def test_promote_archives_staging(tmp_path):
    """After promotion with no pending left, staging file should be archived."""
    staging_file = tmp_path / "proposed-mappings.json"
    archive_dir = tmp_path / "archive"
    write_staging(_make_proposals(), staging_file)
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
