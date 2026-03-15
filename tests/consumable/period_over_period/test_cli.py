"""Tests for period-over-period CLI commands."""

import datetime

from src.consumable.period_over_period.cli import main
from src.consumable.period_over_period.promote import promote_period_over_period


def _make_record(record_id: str = "cli-test-001", growth_type: str = "yoy_change") -> dict:
    now = datetime.datetime.now(datetime.timezone.utc)
    return {
        "record_id": record_id,
        "cik": 320193,
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
        "growth_type": growth_type,
        "growth_value": 11043000000.0 if growth_type == "yoy_change" else 0.029,
        "current_val": 394328000000.0,
        "prior_val": 383285000000.0 if growth_type != "cagr_5yr" else None,
        "base_val": 260174000000.0 if growth_type == "cagr_5yr" else None,
        "base_fiscal_year": 2019 if growth_type == "cagr_5yr" else None,
        "companies_reporting": 20,
        "promoted_at": now,
        "load_date": now.date(),
    }


def test_status_with_data(tmp_path, capsys):
    """Status command shows table stats."""
    warehouse = tmp_path / "iceberg_warehouse"
    catalog_db = tmp_path / "catalog.db"

    promote_period_over_period(
        [_make_record()],
        warehouse_path=warehouse,
        catalog_path=catalog_db,
    )

    main(["--warehouse", str(warehouse), "--catalog", str(catalog_db), "status"])

    captured = capsys.readouterr()
    assert "Period-Over-Period: 1 rows" in captured.out
    assert "Companies: 1" in captured.out


def test_coverage_with_data(tmp_path, capsys):
    """Coverage command shows growth type x business term matrix."""
    warehouse = tmp_path / "iceberg_warehouse"
    catalog_db = tmp_path / "catalog.db"

    promote_period_over_period(
        [_make_record(record_id="cov-001", growth_type="yoy_change"),
         _make_record(record_id="cov-002", growth_type="yoy_pct_change")],
        warehouse_path=warehouse,
        catalog_path=catalog_db,
    )

    main(["--warehouse", str(warehouse), "--catalog", str(catalog_db), "coverage"])

    captured = capsys.readouterr()
    assert "yoy_change" in captured.out
    assert "yoy_pct_change" in captured.out
