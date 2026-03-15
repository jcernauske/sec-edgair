"""Tests for financial ratios CLI commands."""

import datetime

from src.consumable.financial_ratios.cli import cmd_status
from src.consumable.financial_ratios.promote import promote_financial_ratios
from src.infra.iceberg_setup import get_catalog, read_with_duckdb


def _make_record(
    record_id: str = "abc123def456",
    ratio_id: str = "RATIO-003",
    ratio_name: str = "Net Margin",
) -> dict:
    now = datetime.datetime.now(datetime.timezone.utc)
    return {
        "record_id": record_id,
        "cik": 320193,
        "entity_id": "ER-320193",
        "ticker": "AAPL",
        "canonical_name": "Apple Inc.",
        "sector": "Technology",
        "ratio_id": ratio_id,
        "ratio_name": ratio_name,
        "ratio_value": 0.246,
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


def test_status_with_data(tmp_path, capsys):
    """cmd_status prints row count and ratio info when table exists."""
    warehouse = tmp_path / "iceberg_warehouse"
    catalog_db = tmp_path / "catalog.db"

    promote_financial_ratios(
        [_make_record()],
        warehouse_path=warehouse,
        catalog_path=catalog_db,
    )

    import argparse
    args = argparse.Namespace(
        warehouse=str(warehouse),
        catalog=str(catalog_db),
    )
    cmd_status(args)

    captured = capsys.readouterr()
    assert "1 rows" in captured.out
    assert "Ratios: 1" in captured.out


def test_status_no_table(tmp_path, capsys):
    """cmd_status prints not yet created when table missing."""
    warehouse = tmp_path / "iceberg_warehouse"
    catalog_db = tmp_path / "catalog.db"

    import argparse
    args = argparse.Namespace(
        warehouse=str(warehouse),
        catalog=str(catalog_db),
    )
    cmd_status(args)

    captured = capsys.readouterr()
    assert "not yet created" in captured.out
