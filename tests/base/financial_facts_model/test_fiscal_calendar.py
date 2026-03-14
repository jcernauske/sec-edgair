"""Tests for fiscal calendar dimension builder."""

import datetime

from src.base.financial_facts_model.fiscal_calendar import (
    _calendar_quarter,
    _compute_calendar_id,
    build_fiscal_calendar_from_records,
)


def _make_entity(cik: int = 320193, fiscal_year_end: str = "0930") -> dict:
    return {
        "mapping_id": f"ER-{cik}",
        "cik": cik,
        "canonical_name": "Test Corp",
        "ticker": "TEST",
        "fiscal_year_end": fiscal_year_end,
    }


def _make_raw_fact(
    cik: int = 320193,
    fiscal_year: int = 2023,
    fiscal_period: str = "FY",
    start_date: str | None = "2022-10-01",
    end_date: str = "2023-09-30",
) -> dict:
    return {
        "cik": cik,
        "fiscal_year": fiscal_year,
        "fiscal_period": fiscal_period,
        "start_date": start_date,
        "end_date": end_date,
        "concept": "Revenue",
        "taxonomy": "us-gaap",
        "unit": "USD",
        "val": 1000.0,
    }


# --- Calendar quarter ---

def test_calendar_quarter_q1():
    assert _calendar_quarter(datetime.date(2023, 3, 31)) == 1


def test_calendar_quarter_q2():
    assert _calendar_quarter(datetime.date(2023, 6, 30)) == 2


def test_calendar_quarter_q3():
    assert _calendar_quarter(datetime.date(2023, 9, 30)) == 3


def test_calendar_quarter_q4():
    assert _calendar_quarter(datetime.date(2023, 12, 31)) == 4


# --- Calendar ID determinism ---

def test_calendar_id_deterministic():
    """Same inputs produce same ID."""
    id1 = _compute_calendar_id(320193, 2023, "FY")
    id2 = _compute_calendar_id(320193, 2023, "FY")
    assert id1 == id2


def test_calendar_id_different_inputs():
    """Different inputs produce different IDs."""
    id1 = _compute_calendar_id(320193, 2023, "FY")
    id2 = _compute_calendar_id(320193, 2023, "Q1")
    assert id1 != id2


# --- Build fiscal calendar ---

def test_build_calendar_basic():
    """Single company, single period produces one entry."""
    entities = [_make_entity(320193, "0930")]
    facts = [_make_raw_fact(320193, 2023, "FY", "2022-10-01", "2023-09-30")]

    result = build_fiscal_calendar_from_records(facts, entities)

    assert len(result) == 1
    entry = result[0]
    assert entry["cik"] == 320193
    assert entry["fiscal_year"] == 2023
    assert entry["fiscal_period"] == "FY"
    assert entry["fiscal_year_end"] == "0930"
    assert entry["period_start"] == datetime.date(2022, 10, 1)
    assert entry["period_end"] == datetime.date(2023, 9, 30)
    assert entry["calendar_year"] == 2023
    assert entry["calendar_quarter"] == 3  # Sept → Q3
    assert entry["is_annual"] is True
    assert entry["duration_days"] == 364


def test_build_calendar_january_fiscal_year_end():
    """Walmart-style 0131 fiscal year end."""
    entities = [_make_entity(104169, "0131")]
    facts = [_make_raw_fact(104169, 2024, "FY", "2023-02-01", "2024-01-31")]

    result = build_fiscal_calendar_from_records(facts, entities)

    assert len(result) == 1
    entry = result[0]
    assert entry["fiscal_year_end"] == "0131"
    assert entry["calendar_year"] == 2024
    assert entry["calendar_quarter"] == 1  # Jan → Q1


def test_build_calendar_june_fiscal_year_end():
    """Microsoft-style 0630 fiscal year end."""
    entities = [_make_entity(789019, "0630")]
    facts = [_make_raw_fact(789019, 2023, "FY", "2022-07-01", "2023-06-30")]

    result = build_fiscal_calendar_from_records(facts, entities)

    entry = result[0]
    assert entry["fiscal_year_end"] == "0630"
    assert entry["calendar_quarter"] == 2  # June → Q2


def test_build_calendar_quarterly_periods():
    """Multiple quarters for same company."""
    entities = [_make_entity(320193, "1231")]
    facts = [
        _make_raw_fact(320193, 2023, "Q1", "2023-01-01", "2023-03-31"),
        _make_raw_fact(320193, 2023, "Q2", "2023-04-01", "2023-06-30"),
        _make_raw_fact(320193, 2023, "Q3", "2023-07-01", "2023-09-30"),
        _make_raw_fact(320193, 2023, "Q4", "2023-10-01", "2023-12-31"),
        _make_raw_fact(320193, 2023, "FY", "2023-01-01", "2023-12-31"),
    ]

    result = build_fiscal_calendar_from_records(facts, entities)

    assert len(result) == 5
    periods = {r["fiscal_period"] for r in result}
    assert periods == {"Q1", "Q2", "Q3", "Q4", "FY"}
    annual = [r for r in result if r["is_annual"]][0]
    assert annual["duration_days"] == 364


def test_build_calendar_instant_facts_no_start_date():
    """Balance sheet facts have no start_date — period_start should be None."""
    entities = [_make_entity(320193, "1231")]
    facts = [_make_raw_fact(320193, 2023, "FY", None, "2023-12-31")]

    result = build_fiscal_calendar_from_records(facts, entities)

    assert len(result) == 1
    assert result[0]["period_start"] is None
    assert result[0]["duration_days"] is None


def test_build_calendar_skips_unknown_entities():
    """Facts for entities not in entity_mappings are skipped."""
    entities = [_make_entity(320193, "0930")]
    facts = [
        _make_raw_fact(320193, 2023, "FY", "2022-10-01", "2023-09-30"),
        _make_raw_fact(999999, 2023, "FY", "2023-01-01", "2023-12-31"),
    ]

    result = build_fiscal_calendar_from_records(facts, entities)

    assert len(result) == 1
    assert result[0]["cik"] == 320193


def test_build_calendar_multiple_facts_same_period():
    """Multiple facts for same period should merge to widest boundaries."""
    entities = [_make_entity(320193, "1231")]
    facts = [
        _make_raw_fact(320193, 2023, "FY", "2023-01-01", "2023-12-31"),
        _make_raw_fact(320193, 2023, "FY", "2023-01-15", "2023-12-31"),
        _make_raw_fact(320193, 2023, "FY", None, "2023-12-31"),
    ]

    result = build_fiscal_calendar_from_records(facts, entities)

    assert len(result) == 1
    # Earliest start_date from facts that have one
    assert result[0]["period_start"] == datetime.date(2023, 1, 1)
    assert result[0]["period_end"] == datetime.date(2023, 12, 31)
