"""Tests for consumable company financials CLI."""

import datetime

from src.consumable.company_financials.cli import main
from src.consumable.company_financials.promote import promote_company_financials


def _seed_table(tmp_path):
    """Seed company_financials with minimal data for CLI tests."""
    warehouse = tmp_path / "iceberg_warehouse"
    catalog_db = tmp_path / "catalog.db"
    now = datetime.datetime.now(datetime.timezone.utc)

    promote_company_financials(
        [{
            "record_id": "r1",
            "cik": 320193,
            "entity_id": "ER-320193",
            "ticker": "AAPL",
            "canonical_name": "Apple Inc.",
            "sector": "Technology",
            "business_term_id": "BT-024",
            "business_term": "Total Assets",
            "financial_statement": "balance_sheet",
            "category": "assets",
            "val": 352583000000.0,
            "unit": "USD",
            "source_concept": "Assets",
            "fiscal_year": 2023,
            "fiscal_period": "FY",
            "fiscal_year_end": "0930",
            "period_end_date": datetime.date(2023, 9, 30),
            "calendar_year": 2023,
            "calendar_quarter": 3,
            "accession_number": "0000320193-23-000106",
            "filed_date": datetime.date(2023, 11, 3),
            "companies_reporting": 20,
            "promoted_at": now,
            "load_date": now.date(),
        }],
        warehouse_path=warehouse,
        catalog_path=catalog_db,
    )

    return warehouse, catalog_db


def test_status_with_data(tmp_path, capsys):
    """Status command should show row counts when data exists."""
    warehouse, catalog_db = _seed_table(tmp_path)

    main(["--warehouse", str(warehouse), "--catalog", str(catalog_db), "status"])

    output = capsys.readouterr().out
    assert "Company Financials: 1 rows" in output
    assert "Companies: 1" in output
    assert "Business terms: 1" in output


def test_status_empty(tmp_path, capsys):
    """Status on empty warehouse shows 'not yet created'."""
    warehouse = tmp_path / "iceberg_warehouse"
    catalog_db = tmp_path / "catalog.db"

    main(["--warehouse", str(warehouse), "--catalog", str(catalog_db), "status"])

    output = capsys.readouterr().out
    assert "not yet created" in output
