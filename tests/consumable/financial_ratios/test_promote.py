"""Tests for promoting financial ratios to Iceberg."""

import datetime

from src.consumable.financial_ratios.promote import promote_financial_ratios
from src.infra.iceberg_setup import get_catalog, read_with_duckdb


def _make_record(
    record_id: str = "abc123def456",
    cik: int = 320193,
    ratio_value: float = 0.246,
) -> dict:
    now = datetime.datetime.now(datetime.timezone.utc)
    return {
        "record_id": record_id,
        "cik": cik,
        "entity_id": "ER-320193",
        "ticker": "AAPL",
        "canonical_name": "Apple Inc.",
        "sector": "Technology",
        "ratio_id": "RATIO-003",
        "ratio_name": "Net Margin",
        "ratio_value": ratio_value,
        "numerator_bt_id": "BT-023",
        "numerator_bt_name": "Net Income",
        "numerator_val": 96995000000.0,
        "denominator_bt_id": "BT-022",
        "denominator_bt_name": "Revenue",
        "denominator_val": 394328000000.0,
        "fiscal_year": 2023,
        "fiscal_period": "FY",
        "fiscal_year_end": "0930",
        "period_end_date": datetime.date(2023, 9, 30),
        "calendar_year": 2023,
        "calendar_quarter": 3,
        "companies_reporting": 20,
        "promoted_at": now,
        "load_date": now.date(),
    }


def test_promote_roundtrip(tmp_path):
    """Records should roundtrip through Iceberg."""
    warehouse = tmp_path / "iceberg_warehouse"
    catalog_db = tmp_path / "catalog.db"

    result = promote_financial_ratios(
        [_make_record()],
        warehouse_path=warehouse,
        catalog_path=catalog_db,
    )

    assert result["promoted"] == 1
    assert "snapshot_id" in result

    catalog = get_catalog(warehouse, catalog_db)
    table = catalog.load_table("consumable.financial_ratios")
    rows = read_with_duckdb(table)
    assert len(rows) == 1
    assert rows[0]["record_id"] == "abc123def456"
    assert rows[0]["cik"] == 320193
    assert rows[0]["ratio_id"] == "RATIO-003"
    assert rows[0]["ratio_name"] == "Net Margin"


def test_promote_dedup(tmp_path):
    """Writing same records twice should not create duplicates."""
    warehouse = tmp_path / "iceberg_warehouse"
    catalog_db = tmp_path / "catalog.db"

    record = _make_record()

    result1 = promote_financial_ratios(
        [record],
        warehouse_path=warehouse,
        catalog_path=catalog_db,
    )
    assert result1["promoted"] == 1

    result2 = promote_financial_ratios(
        [record],
        warehouse_path=warehouse,
        catalog_path=catalog_db,
    )
    assert result2["promoted"] == 0
    assert result2["skipped_duplicates"] == 1

    catalog = get_catalog(warehouse, catalog_db)
    table = catalog.load_table("consumable.financial_ratios")
    rows = read_with_duckdb(table)
    assert len(rows) == 1


def test_promote_empty(tmp_path):
    """Empty list returns promoted=0 without creating tables."""
    warehouse = tmp_path / "iceberg_warehouse"
    catalog_db = tmp_path / "catalog.db"

    result = promote_financial_ratios(
        [],
        warehouse_path=warehouse,
        catalog_path=catalog_db,
    )
    assert result["promoted"] == 0
