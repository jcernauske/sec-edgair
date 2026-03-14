"""Tests for amendment detection and tracking."""

import datetime

from src.base.financial_facts_model.amendments import detect_amendments


def _make_fact(
    cik: int = 320193,
    concept: str = "Assets",
    unit: str = "USD",
    start_date: str | None = "2023-01-01",
    end_date: str = "2023-12-31",
    accession_number: str = "0000-23-000001",
    form: str = "10-K",
    filed_date: str = "2024-02-15",
    val: float = 1000.0,
) -> dict:
    return {
        "cik": cik,
        "concept": concept,
        "unit": unit,
        "start_date": datetime.date.fromisoformat(start_date) if start_date else None,
        "end_date": datetime.date.fromisoformat(end_date),
        "accession_number": accession_number,
        "form": form,
        "filed_date": datetime.date.fromisoformat(filed_date),
        "val": val,
    }


def test_no_amendments_single_filing():
    """Single filing per grain produces no tracking entries."""
    facts = [_make_fact()]
    result = detect_amendments(facts)
    assert len(result) == 0


def test_amendment_detected():
    """Two filings for same grain produces one tracking entry."""
    facts = [
        _make_fact(accession_number="A1", filed_date="2024-02-15", val=1000.0, form="10-K"),
        _make_fact(accession_number="A2", filed_date="2024-05-01", val=1050.0, form="10-K/A"),
    ]
    result = detect_amendments(facts)

    assert len(result) == 1
    entry = result[0]
    assert entry["original_accession"] == "A1"
    assert entry["amendment_accession"] == "A2"
    assert entry["original_val"] == 1000.0
    assert entry["amendment_val"] == 1050.0
    assert entry["val_change"] == 50.0
    assert entry["val_change_pct"] == 5.0
    assert entry["amendment_form"] == "10-K/A"


def test_amendment_val_change_pct_zero_original():
    """Zero original value → val_change_pct is None."""
    facts = [
        _make_fact(accession_number="A1", filed_date="2024-02-15", val=0.0),
        _make_fact(accession_number="A2", filed_date="2024-05-01", val=100.0),
    ]
    result = detect_amendments(facts)

    assert result[0]["val_change_pct"] is None
    assert result[0]["val_change"] == 100.0


def test_amendment_chain_three_filings():
    """Three filings → two tracking entries (each original paired with latest)."""
    facts = [
        _make_fact(accession_number="A1", filed_date="2024-02-15", val=1000.0),
        _make_fact(accession_number="A2", filed_date="2024-05-01", val=1050.0),
        _make_fact(accession_number="A3", filed_date="2024-08-01", val=1100.0),
    ]
    result = detect_amendments(facts)

    assert len(result) == 2
    accessions = [(r["original_accession"], r["amendment_accession"]) for r in result]
    assert ("A1", "A3") in accessions
    assert ("A2", "A3") in accessions


def test_amendment_different_concepts_independent():
    """Different concepts don't create cross-concept amendments."""
    facts = [
        _make_fact(concept="Assets", accession_number="A1", filed_date="2024-02-15"),
        _make_fact(concept="Revenue", accession_number="A2", filed_date="2024-05-01"),
    ]
    result = detect_amendments(facts)
    assert len(result) == 0


def test_amendment_tracking_has_required_fields():
    """All required fields should be present in tracking entries."""
    facts = [
        _make_fact(accession_number="A1", filed_date="2024-02-15", val=1000.0),
        _make_fact(accession_number="A2", filed_date="2024-05-01", val=1050.0),
    ]
    result = detect_amendments(facts)

    entry = result[0]
    required = {
        "tracking_id", "cik", "concept", "unit", "end_date",
        "original_accession", "original_filed_date", "original_val",
        "amendment_accession", "amendment_filed_date", "amendment_val",
        "val_change", "amendment_form", "detected_at",
    }
    assert required.issubset(set(entry.keys()))
