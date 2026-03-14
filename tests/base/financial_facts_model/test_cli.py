"""Tests for financial facts model CLI."""

import datetime

from src.base.financial_facts_model.cli import main
from src.base.financial_facts_model.promote import (
    promote_amendment_tracking,
    promote_financial_facts,
    promote_fiscal_calendar,
)


def _seed_tables(tmp_path):
    """Seed all 3 tables with minimal data for status command."""
    warehouse = tmp_path / "iceberg_warehouse"
    catalog_db = tmp_path / "catalog.db"
    now = datetime.datetime.now(datetime.timezone.utc)

    promote_financial_facts(
        [{
            "fact_id": "f1", "entity_id": "ER-1", "cik": 1,
            "canonical_name": "Test", "ticker": None,
            "concept": "Assets", "cde_id": None, "canonical_cde": None,
            "financial_statement": "balance_sheet", "category": "assets",
            "tier": 1, "taxonomy": "us-gaap", "unit": "USD", "val": 1.0,
            "start_date": None, "end_date": datetime.date(2023, 12, 31),
            "fiscal_year": 2023, "fiscal_period": "FY",
            "fiscal_year_end": "1231",
            "calendar_year": 2023, "calendar_quarter": 4,
            "accession_number": "A1", "form": "10-K",
            "filed_date": datetime.date(2024, 2, 15),
            "is_amendment": False, "is_superseded": False,
            "superseded_by": None, "promoted_at": now,
            "load_date": now.date(),
        }],
        warehouse_path=warehouse,
        catalog_path=catalog_db,
    )

    promote_fiscal_calendar(
        [{
            "calendar_id": "c1", "cik": 1, "entity_id": "ER-1",
            "fiscal_year": 2023, "fiscal_period": "FY",
            "fiscal_year_end": "1231",
            "period_start": datetime.date(2023, 1, 1),
            "period_end": datetime.date(2023, 12, 31),
            "calendar_year": 2023, "calendar_quarter": 4,
            "duration_days": 364, "is_annual": True,
            "load_date": now.date(),
        }],
        warehouse_path=warehouse,
        catalog_path=catalog_db,
    )

    promote_amendment_tracking(
        [{
            "tracking_id": "t1", "cik": 1, "concept": "Assets",
            "unit": "USD", "start_date": None,
            "end_date": datetime.date(2023, 12, 31),
            "original_accession": "A1",
            "original_filed_date": datetime.date(2024, 2, 15),
            "original_val": 1000.0,
            "amendment_accession": "A2",
            "amendment_filed_date": datetime.date(2024, 5, 1),
            "amendment_val": 1050.0,
            "val_change": 50.0, "val_change_pct": 5.0,
            "amendment_form": "10-K/A", "detected_at": now,
            "load_date": now.date(),
        }],
        warehouse_path=warehouse,
        catalog_path=catalog_db,
    )

    return warehouse, catalog_db


def test_cli_status(tmp_path, capsys):
    """Status command should show row counts."""
    warehouse, catalog_db = _seed_tables(tmp_path)

    main(["--warehouse", str(warehouse), "--catalog", str(catalog_db), "status"])

    output = capsys.readouterr().out
    assert "Financial Facts: 1 rows" in output
    assert "Fiscal Calendar: 1 rows" in output
    assert "Amendment Tracking: 1 rows" in output


def test_cli_status_no_tables(tmp_path, capsys):
    """Status on empty warehouse shows 'not yet created'."""
    warehouse = tmp_path / "iceberg_warehouse"
    catalog_db = tmp_path / "catalog.db"

    main(["--warehouse", str(warehouse), "--catalog", str(catalog_db), "status"])

    output = capsys.readouterr().out
    assert "not yet created" in output


def test_cli_help(capsys):
    """CLI should accept --help without error."""
    import sys
    try:
        main(["--help"])
    except SystemExit as e:
        assert e.code == 0
