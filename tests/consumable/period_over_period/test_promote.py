"""Tests for promoting period-over-period growth to Iceberg."""

import datetime

from src.consumable.period_over_period.promote import promote_period_over_period
from src.infra.iceberg_setup import get_catalog, read_with_duckdb


def _make_record(
    record_id: str = "abc123def456pp",
    cik: int = 320193,
    growth_value: float = 0.029,
) -> dict:
    now = datetime.datetime.now(datetime.timezone.utc)
    return {
        "record_id": record_id,
        "cik": cik,
        "entity_id": "ER-320193",
        "ticker": "AAPL",
        "canonical_name": "Apple Inc.",
        "sector": "Technology",
        "business_term_id": "BT-022",
        "business_term": "Revenue",
        "financial_statement": "income_statement",
        "category": "revenue",
        "fiscal_year": 2024,
        "fiscal_period": "FY",
        "fiscal_year_end": "0930",
        "period_end_date": datetime.date(2024, 9, 28),
        "calendar_year": 2024,
        "calendar_quarter": 3,
        "growth_type": "yoy_pct_change",
        "growth_value": growth_value,
        "current_val": 394328000000.0,
        "prior_val": 383285000000.0,
        "base_val": None,
        "base_fiscal_year": None,
        "companies_reporting": 20,
        "promoted_at": now,
        "load_date": now.date(),
    }


def test_promote_roundtrip(tmp_path):
    """Records should roundtrip through Iceberg."""
    warehouse = tmp_path / "iceberg_warehouse"
    catalog_db = tmp_path / "catalog.db"

    result = promote_period_over_period(
        [_make_record()],
        warehouse_path=warehouse,
        catalog_path=catalog_db,
    )

    assert result["promoted"] == 1
    assert "snapshot_id" in result

    catalog = get_catalog(warehouse, catalog_db)
    table = catalog.load_table("consumable.period_over_period")
    rows = read_with_duckdb(table)
    assert len(rows) == 1
    assert rows[0]["record_id"] == "abc123def456pp"
    assert rows[0]["cik"] == 320193
    assert rows[0]["growth_type"] == "yoy_pct_change"
    assert rows[0]["business_term_id"] == "BT-022"


def test_promote_dedup(tmp_path):
    """Writing same records twice should not create duplicates."""
    warehouse = tmp_path / "iceberg_warehouse"
    catalog_db = tmp_path / "catalog.db"

    record = _make_record()

    result1 = promote_period_over_period(
        [record],
        warehouse_path=warehouse,
        catalog_path=catalog_db,
    )
    assert result1["promoted"] == 1

    result2 = promote_period_over_period(
        [record],
        warehouse_path=warehouse,
        catalog_path=catalog_db,
    )
    assert result2["promoted"] == 0
    assert result2["skipped_duplicates"] == 1

    catalog = get_catalog(warehouse, catalog_db)
    table = catalog.load_table("consumable.period_over_period")
    rows = read_with_duckdb(table)
    assert len(rows) == 1


def test_promote_empty(tmp_path):
    """Empty list returns promoted=0 without creating tables."""
    warehouse = tmp_path / "iceberg_warehouse"
    catalog_db = tmp_path / "catalog.db"

    result = promote_period_over_period(
        [],
        warehouse_path=warehouse,
        catalog_path=catalog_db,
    )
    assert result["promoted"] == 0
