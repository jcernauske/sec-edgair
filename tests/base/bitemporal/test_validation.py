"""Tests for bitemporal temporal DQ validation rules."""

import datetime

from src.base.bitemporal.validation import (
    validate_filed_after_period,
    validate_no_future_filed_dates,
    validate_start_before_end,
    validate_superseded_by_exists,
    validate_supersession_order,
)


def _make_fact(**overrides) -> dict:
    defaults = {
        "cik": 320193,
        "concept": "Assets",
        "unit": "USD",
        "val": 1000.0,
        "start_date": datetime.date(2023, 1, 1),
        "end_date": datetime.date(2023, 12, 31),
        "filed_date": datetime.date(2024, 2, 15),
        "accession_number": "0000-23-000001",
        "is_superseded": False,
        "superseded_by": None,
    }
    defaults.update(overrides)
    return defaults


class TestNoFutureFiledDates:

    def test_pass_all_past(self):
        facts = [_make_fact(filed_date=datetime.date(2024, 2, 15))]
        result = validate_no_future_filed_dates(
            facts, reference_date=datetime.date(2025, 1, 1),
        )
        assert result["passed"] is True
        assert result["violations"] == 0

    def test_fail_future_date(self):
        facts = [_make_fact(filed_date=datetime.date(2030, 1, 1))]
        result = validate_no_future_filed_dates(
            facts, reference_date=datetime.date(2025, 1, 1),
        )
        assert result["passed"] is False
        assert result["violations"] == 1


class TestStartBeforeEnd:

    def test_pass_valid_range(self):
        facts = [_make_fact(
            start_date=datetime.date(2023, 1, 1),
            end_date=datetime.date(2023, 12, 31),
        )]
        result = validate_start_before_end(facts)
        assert result["passed"] is True

    def test_fail_start_equals_end(self):
        facts = [_make_fact(
            start_date=datetime.date(2023, 12, 31),
            end_date=datetime.date(2023, 12, 31),
        )]
        result = validate_start_before_end(facts)
        assert result["passed"] is False
        assert result["violations"] == 1


class TestSupersessionOrder:

    def test_pass_correct_order(self):
        facts = [
            _make_fact(
                filed_date=datetime.date(2024, 2, 15),
                accession_number="A1",
                is_superseded=True,
                superseded_by="A2",
            ),
            _make_fact(
                filed_date=datetime.date(2024, 5, 1),
                accession_number="A2",
                is_superseded=False,
            ),
        ]
        result = validate_supersession_order(facts)
        assert result["passed"] is True

    def test_fail_wrong_order(self):
        facts = [
            _make_fact(
                filed_date=datetime.date(2024, 5, 1),
                accession_number="A1",
                is_superseded=True,
                superseded_by="A2",
            ),
            _make_fact(
                filed_date=datetime.date(2024, 2, 15),
                accession_number="A2",
                is_superseded=False,
            ),
        ]
        result = validate_supersession_order(facts)
        assert result["passed"] is False
        assert result["violations"] == 1


class TestFiledAfterPeriod:

    def test_pass_filed_after_end(self):
        facts = [_make_fact(
            end_date=datetime.date(2023, 12, 31),
            filed_date=datetime.date(2024, 2, 15),
        )]
        result = validate_filed_after_period(facts)
        assert result["passed"] is True

    def test_fail_filed_before_end(self):
        # Single fact filed before period end — 0% pass rate < 99% threshold
        facts = [_make_fact(
            end_date=datetime.date(2024, 12, 31),
            filed_date=datetime.date(2024, 6, 15),
        )]
        result = validate_filed_after_period(facts)
        assert result["passed"] is False
        assert result["violations"] == 1


class TestSupersededByExists:

    def test_pass_reference_exists(self):
        facts = [
            _make_fact(accession_number="A1", is_superseded=True, superseded_by="A2"),
            _make_fact(accession_number="A2"),
        ]
        result = validate_superseded_by_exists(facts)
        assert result["passed"] is True

    def test_fail_reference_missing(self):
        facts = [
            _make_fact(accession_number="A1", is_superseded=True, superseded_by="A99"),
        ]
        result = validate_superseded_by_exists(facts)
        assert result["passed"] is False
        assert result["violations"] == 1
