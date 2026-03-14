"""Tests for promoting all 3 tables to Iceberg."""

import datetime

from src.base.financial_facts_model.promote import (
    promote_amendment_tracking,
    promote_financial_facts,
    promote_fiscal_calendar,
)
from src.infra.iceberg_setup import get_catalog, read_with_duckdb


def _make_fact_record() -> dict:
    return {
        "fact_id": "abc123",
        "entity_id": "ER-320193",
        "cik": 320193,
        "canonical_name": "Apple Inc.",
        "ticker": "AAPL",
        "concept": "Assets",
        "cde_id": "CDE-007",
        "canonical_cde": "Total Assets",
        "financial_statement": "balance_sheet",
        "category": "assets",
        "tier": 1,
        "taxonomy": "us-gaap",
        "unit": "USD",
        "val": 352583000000.0,
        "start_date": None,
        "end_date": datetime.date(2023, 9, 30),
        "fiscal_year": 2023,
        "fiscal_period": "FY",
        "fiscal_year_end": "0930",
        "calendar_year": 2023,
        "calendar_quarter": 3,
        "accession_number": "0000320193-23-000106",
        "form": "10-K",
        "filed_date": datetime.date(2023, 11, 3),
        "is_amendment": False,
        "is_superseded": False,
        "superseded_by": None,
        "promoted_at": datetime.datetime.now(datetime.timezone.utc),
    }


def _make_calendar_record() -> dict:
    return {
        "calendar_id": "cal123",
        "cik": 320193,
        "entity_id": "ER-320193",
        "fiscal_year": 2023,
        "fiscal_period": "FY",
        "fiscal_year_end": "0930",
        "period_start": datetime.date(2022, 10, 1),
        "period_end": datetime.date(2023, 9, 30),
        "calendar_year": 2023,
        "calendar_quarter": 3,
        "duration_days": 364,
        "is_annual": True,
    }


def _make_amendment_record() -> dict:
    return {
        "tracking_id": "track123",
        "cik": 320193,
        "concept": "Assets",
        "unit": "USD",
        "start_date": None,
        "end_date": datetime.date(2023, 9, 30),
        "original_accession": "0000-23-000001",
        "original_filed_date": datetime.date(2023, 11, 3),
        "original_val": 1000.0,
        "amendment_accession": "0000-23-000002",
        "amendment_filed_date": datetime.date(2024, 2, 15),
        "amendment_val": 1050.0,
        "val_change": 50.0,
        "val_change_pct": 5.0,
        "amendment_form": "10-K/A",
        "detected_at": datetime.datetime.now(datetime.timezone.utc),
    }


def test_promote_financial_facts(tmp_path):
    """Financial facts should roundtrip through Iceberg."""
    warehouse = tmp_path / "iceberg_warehouse"
    catalog_db = tmp_path / "catalog.db"

    result = promote_financial_facts(
        [_make_fact_record()],
        warehouse_path=warehouse,
        catalog_path=catalog_db,
    )

    assert result["promoted"] == 1
    assert "snapshot_id" in result

    catalog = get_catalog(warehouse, catalog_db)
    table = catalog.load_table("base.financial_facts")
    rows = read_with_duckdb(table)
    assert len(rows) == 1
    assert rows[0]["fact_id"] == "abc123"
    assert rows[0]["cik"] == 320193


def test_promote_fiscal_calendar(tmp_path):
    """Fiscal calendar should roundtrip through Iceberg."""
    warehouse = tmp_path / "iceberg_warehouse"
    catalog_db = tmp_path / "catalog.db"

    result = promote_fiscal_calendar(
        [_make_calendar_record()],
        warehouse_path=warehouse,
        catalog_path=catalog_db,
    )

    assert result["promoted"] == 1

    catalog = get_catalog(warehouse, catalog_db)
    table = catalog.load_table("base.fiscal_calendar")
    rows = read_with_duckdb(table)
    assert len(rows) == 1
    assert rows[0]["calendar_id"] == "cal123"
    assert rows[0]["is_annual"] is True


def test_promote_amendment_tracking(tmp_path):
    """Amendment tracking should roundtrip through Iceberg."""
    warehouse = tmp_path / "iceberg_warehouse"
    catalog_db = tmp_path / "catalog.db"

    result = promote_amendment_tracking(
        [_make_amendment_record()],
        warehouse_path=warehouse,
        catalog_path=catalog_db,
    )

    assert result["promoted"] == 1

    catalog = get_catalog(warehouse, catalog_db)
    table = catalog.load_table("base.amendment_tracking")
    rows = read_with_duckdb(table)
    assert len(rows) == 1
    assert rows[0]["tracking_id"] == "track123"
    assert rows[0]["val_change"] == 50.0


def test_promote_empty_list_is_noop(tmp_path):
    """Empty list should return promoted=0 without creating tables."""
    warehouse = tmp_path / "iceberg_warehouse"
    catalog_db = tmp_path / "catalog.db"

    result = promote_financial_facts(
        [],
        warehouse_path=warehouse,
        catalog_path=catalog_db,
    )
    assert result["promoted"] == 0


def test_promote_multiple_facts(tmp_path):
    """Multiple facts should all be written."""
    warehouse = tmp_path / "iceberg_warehouse"
    catalog_db = tmp_path / "catalog.db"

    facts = []
    for i in range(3):
        f = _make_fact_record()
        f["fact_id"] = f"fact-{i}"
        f["accession_number"] = f"0000-23-{i:06d}"
        facts.append(f)

    result = promote_financial_facts(
        facts,
        warehouse_path=warehouse,
        catalog_path=catalog_db,
    )

    assert result["promoted"] == 3

    catalog = get_catalog(warehouse, catalog_db)
    table = catalog.load_table("base.financial_facts")
    rows = read_with_duckdb(table)
    assert len(rows) == 3
