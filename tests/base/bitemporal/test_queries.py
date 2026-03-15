"""Tests for bitemporal query helpers."""

import datetime

from src.base.bitemporal.queries import (
    as_known_on,
    compare_periods,
    current_facts,
    fact_history,
)


def _make_fact(
    cik: int = 320193,
    concept: str = "Assets",
    unit: str = "USD",
    val: float = 1000.0,
    start_date: str = "2023-01-01",
    end_date: str = "2023-12-31",
    filed_date: str = "2024-02-15",
    accession_number: str = "0000-23-000001",
    is_superseded: bool = False,
    superseded_by: str | None = None,
    business_term_id: str | None = "BT-024",
    canonical_name: str = "Apple Inc.",
) -> dict:
    return {
        "cik": cik,
        "concept": concept,
        "unit": unit,
        "val": val,
        "start_date": datetime.date.fromisoformat(start_date),
        "end_date": datetime.date.fromisoformat(end_date),
        "filed_date": datetime.date.fromisoformat(filed_date),
        "accession_number": accession_number,
        "is_superseded": is_superseded,
        "superseded_by": superseded_by,
        "business_term_id": business_term_id,
        "canonical_name": canonical_name,
    }


# --- current_facts ---

class TestCurrentFacts:

    def test_excludes_superseded(self):
        facts = [
            _make_fact(is_superseded=True, superseded_by="A2"),
            _make_fact(accession_number="A2", is_superseded=False),
        ]
        result = current_facts(facts)
        assert len(result) == 1
        assert result[0]["accession_number"] == "A2"

    def test_filter_by_cik(self):
        facts = [
            _make_fact(cik=320193),
            _make_fact(cik=789019, canonical_name="Microsoft"),
        ]
        result = current_facts(facts, cik=320193)
        assert len(result) == 1
        assert result[0]["cik"] == 320193

    def test_filter_by_concept(self):
        facts = [
            _make_fact(concept="Assets"),
            _make_fact(concept="Revenue"),
        ]
        result = current_facts(facts, concept="Assets")
        assert len(result) == 1
        assert result[0]["concept"] == "Assets"

    def test_filter_by_business_term_id(self):
        facts = [
            _make_fact(business_term_id="BT-024"),
            _make_fact(business_term_id="BT-022"),
        ]
        result = current_facts(facts, business_term_id="BT-024")
        assert len(result) == 1
        assert result[0]["business_term_id"] == "BT-024"

    def test_no_filters_returns_all_current(self):
        facts = [
            _make_fact(concept="Assets"),
            _make_fact(concept="Revenue"),
            _make_fact(concept="Old", is_superseded=True),
        ]
        result = current_facts(facts)
        assert len(result) == 2


# --- as_known_on ---

class TestAsKnownOn:

    def test_before_amendment(self):
        """Before amendment filed, original is 'current'."""
        facts = [
            _make_fact(
                val=1000.0,
                filed_date="2024-02-15",
                accession_number="A1",
                is_superseded=True,
                superseded_by="A2",
            ),
            _make_fact(
                val=1050.0,
                filed_date="2024-05-01",
                accession_number="A2",
                is_superseded=False,
            ),
        ]
        # Before amendment: only A1 is known
        result = as_known_on(facts, datetime.date(2024, 3, 1))
        assert len(result) == 1
        assert result[0]["val"] == 1000.0

    def test_after_amendment(self):
        """After amendment filed, amendment is 'current'."""
        facts = [
            _make_fact(
                val=1000.0,
                filed_date="2024-02-15",
                accession_number="A1",
                is_superseded=True,
                superseded_by="A2",
            ),
            _make_fact(
                val=1050.0,
                filed_date="2024-05-01",
                accession_number="A2",
                is_superseded=False,
            ),
        ]
        result = as_known_on(facts, datetime.date(2024, 6, 1))
        assert len(result) == 1
        assert result[0]["val"] == 1050.0

    def test_string_date_accepted(self):
        """as_known_on accepts string dates."""
        facts = [_make_fact(filed_date="2024-02-15")]
        result = as_known_on(facts, "2024-12-31")
        assert len(result) == 1


# --- fact_history ---

class TestFactHistory:

    def test_returns_all_versions_sorted(self):
        facts = [
            _make_fact(val=1000.0, filed_date="2024-02-15", accession_number="A1"),
            _make_fact(val=1050.0, filed_date="2024-05-01", accession_number="A2"),
            _make_fact(val=1100.0, filed_date="2024-08-01", accession_number="A3"),
        ]
        result = fact_history(
            facts, 320193, "Assets",
            "2023-01-01", "2023-12-31",
        )
        assert len(result) == 3
        assert result[0]["val"] == 1000.0
        assert result[1]["val"] == 1050.0
        assert result[2]["val"] == 1100.0

    def test_filters_by_grain(self):
        facts = [
            _make_fact(concept="Assets", val=1000.0),
            _make_fact(concept="Revenue", val=500.0),
        ]
        result = fact_history(
            facts, 320193, "Assets",
            "2023-01-01", "2023-12-31",
        )
        assert len(result) == 1
        assert result[0]["concept"] == "Assets"


# --- compare_periods ---

class TestComparePeriods:

    def test_basic_comparison(self):
        facts = [
            _make_fact(val=1000.0, end_date="2022-12-31"),
            _make_fact(val=1200.0, end_date="2023-12-31"),
        ]
        result = compare_periods(
            facts, 320193, "Assets",
            "2022-12-31", "2023-12-31",
        )
        assert result is not None
        assert result["period1_val"] == 1000.0
        assert result["period2_val"] == 1200.0
        assert result["change"] == 200.0
        assert result["pct_change"] == 20.0

    def test_missing_period_returns_none(self):
        facts = [
            _make_fact(val=1000.0, end_date="2022-12-31"),
        ]
        result = compare_periods(
            facts, 320193, "Assets",
            "2022-12-31", "2023-12-31",
        )
        assert result is None
