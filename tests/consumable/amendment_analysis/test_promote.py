"""Tests for promoting amendment analysis to Iceberg."""

import datetime

from src.consumable.amendment_analysis.promote import promote_amendment_analysis
from src.infra.iceberg_setup import get_catalog, read_with_duckdb


def _make_record(
    record_id: str = "abc123def456aa",
    cik: int = 320193,
    amendment_count: int = 150,
) -> dict:
    now = datetime.datetime.now(datetime.timezone.utc)
    return {
        "record_id": record_id,
        "cik": cik,
        "entity_id": "ER-002",
        "ticker": "AAPL",
        "canonical_name": "Apple Inc.",
        "sector": "Technology",
        "fiscal_year": 2023,
        "amendment_count": amendment_count,
        "distinct_concepts": 85,
        "distinct_filings": 12,
        "mean_abs_change": 553626344.12,
        "median_abs_change": 12500000.0,
        "max_abs_change": 5000000000.0,
        "mean_pct_change": 0.15,
        "median_pct_change": 0.08,
        "total_val_impact": 83043951618.0,
        "largest_concept": "Revenue",
        "largest_change": 5000000000.0,
        "days_to_amend_avg": 365.0,
        "days_to_amend_median": 340.0,
        "promoted_at": now,
        "load_date": now.date(),
    }


def test_promote_roundtrip(tmp_path):
    """Records should roundtrip through Iceberg."""
    warehouse = tmp_path / "iceberg_warehouse"
    catalog_db = tmp_path / "catalog.db"

    result = promote_amendment_analysis(
        [_make_record()],
        warehouse_path=warehouse,
        catalog_path=catalog_db,
    )

    assert result["promoted"] == 1
    assert "snapshot_id" in result

    catalog = get_catalog(warehouse, catalog_db)
    table = catalog.load_table("consumable.amendment_analysis")
    rows = read_with_duckdb(table)
    assert len(rows) == 1
    assert rows[0]["record_id"] == "abc123def456aa"
    assert rows[0]["cik"] == 320193
    assert rows[0]["amendment_count"] == 150
    assert rows[0]["largest_concept"] == "Revenue"


def test_promote_dedup(tmp_path):
    """Writing same records twice should not create duplicates."""
    warehouse = tmp_path / "iceberg_warehouse"
    catalog_db = tmp_path / "catalog.db"

    record = _make_record()

    result1 = promote_amendment_analysis(
        [record],
        warehouse_path=warehouse,
        catalog_path=catalog_db,
    )
    assert result1["promoted"] == 1

    result2 = promote_amendment_analysis(
        [record],
        warehouse_path=warehouse,
        catalog_path=catalog_db,
    )
    assert result2["promoted"] == 0
    assert result2["skipped_duplicates"] == 1

    catalog = get_catalog(warehouse, catalog_db)
    table = catalog.load_table("consumable.amendment_analysis")
    rows = read_with_duckdb(table)
    assert len(rows) == 1


def test_promote_empty(tmp_path):
    """Empty list returns promoted=0 without creating tables."""
    warehouse = tmp_path / "iceberg_warehouse"
    catalog_db = tmp_path / "catalog.db"

    result = promote_amendment_analysis(
        [],
        warehouse_path=warehouse,
        catalog_path=catalog_db,
    )
    assert result["promoted"] == 0


def test_promote_nullable_pct(tmp_path):
    """Records with null pct fields should roundtrip correctly."""
    warehouse = tmp_path / "iceberg_warehouse"
    catalog_db = tmp_path / "catalog.db"

    record = _make_record()
    record["mean_pct_change"] = None
    record["median_pct_change"] = None

    result = promote_amendment_analysis(
        [record],
        warehouse_path=warehouse,
        catalog_path=catalog_db,
    )

    assert result["promoted"] == 1

    catalog = get_catalog(warehouse, catalog_db)
    table = catalog.load_table("consumable.amendment_analysis")
    rows = read_with_duckdb(table)
    assert rows[0]["mean_pct_change"] is None
    assert rows[0]["median_pct_change"] is None
