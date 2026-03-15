"""Tests for consumable peer comparison build logic."""

import datetime

from src.consumable.peer_comparison.build import (
    build_peer_comparison,
    _compute_median,
    _dense_rank,
)


def _make_cf_row(
    cik: int = 320193,
    business_term_id: str = "BT-022",
    business_term: str = "Revenue",
    val: float = 394328000000.0,
    fiscal_year: int = 2023,
    fiscal_period: str = "FY",
    entity_id: str = "ER-320193",
    ticker: str = "AAPL",
    canonical_name: str = "Apple Inc.",
    sector: str = "Technology",
    fiscal_year_end: str = "0930",
    period_end_date: datetime.date | None = None,
    calendar_year: int = 2023,
    calendar_quarter: int = 3,
) -> dict:
    """Create a company_financials row for testing."""
    if period_end_date is None:
        period_end_date = datetime.date(2023, 9, 30)
    return {
        "record_id": f"test-{cik}-{business_term_id}-{fiscal_year}-{fiscal_period}",
        "cik": cik,
        "entity_id": entity_id,
        "ticker": ticker,
        "canonical_name": canonical_name,
        "sector": sector,
        "business_term_id": business_term_id,
        "business_term": business_term,
        "financial_statement": "income_statement",
        "category": "revenue",
        "val": val,
        "unit": "USD",
        "source_concept": "TestConcept",
        "fiscal_year": fiscal_year,
        "fiscal_period": fiscal_period,
        "fiscal_year_end": fiscal_year_end,
        "period_end_date": period_end_date,
        "calendar_year": calendar_year,
        "calendar_quarter": calendar_quarter,
        "accession_number": "0000-23-000001",
        "filed_date": datetime.date(2023, 11, 3),
        "companies_reporting": 20,
        "promoted_at": datetime.datetime.now(datetime.timezone.utc),
        "load_date": datetime.date.today(),
    }


def _make_fr_row(
    cik: int = 320193,
    ratio_id: str = "RATIO-003",
    ratio_name: str = "Net Margin",
    ratio_value: float = 0.246,
    fiscal_year: int = 2023,
    fiscal_period: str = "FY",
    entity_id: str = "ER-320193",
    ticker: str = "AAPL",
    canonical_name: str = "Apple Inc.",
    sector: str = "Technology",
    fiscal_year_end: str = "0930",
    period_end_date: datetime.date | None = None,
    calendar_year: int = 2023,
    calendar_quarter: int = 3,
) -> dict:
    """Create a financial_ratios row for testing."""
    if period_end_date is None:
        period_end_date = datetime.date(2023, 9, 30)
    return {
        "record_id": f"test-{cik}-{ratio_id}-{fiscal_year}-{fiscal_period}",
        "cik": cik,
        "entity_id": entity_id,
        "ticker": ticker,
        "canonical_name": canonical_name,
        "sector": sector,
        "ratio_id": ratio_id,
        "ratio_name": ratio_name,
        "ratio_value": ratio_value,
        "numerator_bt_id": "BT-023",
        "numerator_bt_name": "Net Income",
        "numerator_val": 97000000000.0,
        "denominator_bt_id": "BT-022",
        "denominator_bt_name": "Revenue",
        "denominator_val": 394000000000.0,
        "fiscal_year": fiscal_year,
        "fiscal_period": fiscal_period,
        "fiscal_year_end": fiscal_year_end,
        "period_end_date": period_end_date,
        "calendar_year": calendar_year,
        "calendar_quarter": calendar_quarter,
        "companies_reporting": 20,
        "promoted_at": datetime.datetime.now(datetime.timezone.utc),
        "load_date": datetime.date.today(),
    }


# --- Ranking tests ---

def test_rank_basic():
    """3 companies in sector, assert ranks 1/2/3 by value."""
    cf = [
        _make_cf_row(cik=1, canonical_name="Co A", val=300.0, sector="Tech",
                     entity_id="ER-1", ticker="A"),
        _make_cf_row(cik=2, canonical_name="Co B", val=200.0, sector="Tech",
                     entity_id="ER-2", ticker="B"),
        _make_cf_row(cik=3, canonical_name="Co C", val=100.0, sector="Tech",
                     entity_id="ER-3", ticker="C"),
    ]

    results = build_peer_comparison(company_financials=cf, financial_ratios=[])

    by_cik = {r["cik"]: r for r in results}
    assert by_cik[1]["sector_rank"] == 1
    assert by_cik[2]["sector_rank"] == 2
    assert by_cik[3]["sector_rank"] == 3


def test_sector_avg():
    """3 companies with known values, assert exact average."""
    cf = [
        _make_cf_row(cik=1, val=300.0, sector="Tech", entity_id="ER-1", ticker="A",
                     canonical_name="Co A"),
        _make_cf_row(cik=2, val=200.0, sector="Tech", entity_id="ER-2", ticker="B",
                     canonical_name="Co B"),
        _make_cf_row(cik=3, val=100.0, sector="Tech", entity_id="ER-3", ticker="C",
                     canonical_name="Co C"),
    ]

    results = build_peer_comparison(company_financials=cf, financial_ratios=[])

    # All rows should have same sector_avg
    for r in results:
        assert r["sector_avg"] == 200.0  # (300 + 200 + 100) / 3


def test_sector_median_odd():
    """3 values, assert middle value."""
    cf = [
        _make_cf_row(cik=1, val=300.0, sector="Tech", entity_id="ER-1", ticker="A",
                     canonical_name="Co A"),
        _make_cf_row(cik=2, val=200.0, sector="Tech", entity_id="ER-2", ticker="B",
                     canonical_name="Co B"),
        _make_cf_row(cik=3, val=100.0, sector="Tech", entity_id="ER-3", ticker="C",
                     canonical_name="Co C"),
    ]

    results = build_peer_comparison(company_financials=cf, financial_ratios=[])

    for r in results:
        assert r["sector_median"] == 200.0


def test_sector_median_even():
    """2 values, assert average of both."""
    cf = [
        _make_cf_row(cik=1, val=300.0, sector="Tech", entity_id="ER-1", ticker="A",
                     canonical_name="Co A"),
        _make_cf_row(cik=2, val=100.0, sector="Tech", entity_id="ER-2", ticker="B",
                     canonical_name="Co B"),
    ]

    results = build_peer_comparison(company_financials=cf, financial_ratios=[])

    for r in results:
        assert r["sector_median"] == 200.0  # (100 + 300) / 2


def test_percentile_formula():
    """Rank 1 of 3 = 1.0, rank 2 = 0.5, rank 3 = 0.0."""
    cf = [
        _make_cf_row(cik=1, val=300.0, sector="Tech", entity_id="ER-1", ticker="A",
                     canonical_name="Co A"),
        _make_cf_row(cik=2, val=200.0, sector="Tech", entity_id="ER-2", ticker="B",
                     canonical_name="Co B"),
        _make_cf_row(cik=3, val=100.0, sector="Tech", entity_id="ER-3", ticker="C",
                     canonical_name="Co C"),
    ]

    results = build_peer_comparison(company_financials=cf, financial_ratios=[])

    by_cik = {r["cik"]: r for r in results}
    assert by_cik[1]["sector_percentile"] == 1.0
    assert by_cik[2]["sector_percentile"] == 0.5
    assert by_cik[3]["sector_percentile"] == 0.0


def test_single_company_sector_excluded():
    """Sector with 1 company produces 0 rows."""
    cf = [
        _make_cf_row(cik=1, val=300.0, sector="Energy", entity_id="ER-1", ticker="A",
                     canonical_name="Co A"),
    ]

    results = build_peer_comparison(company_financials=cf, financial_ratios=[])

    assert len(results) == 0


def test_tied_values_same_rank():
    """Two companies with same value get same rank."""
    cf = [
        _make_cf_row(cik=1, val=300.0, sector="Tech", entity_id="ER-1", ticker="A",
                     canonical_name="Co A"),
        _make_cf_row(cik=2, val=300.0, sector="Tech", entity_id="ER-2", ticker="B",
                     canonical_name="Co B"),
        _make_cf_row(cik=3, val=100.0, sector="Tech", entity_id="ER-3", ticker="C",
                     canonical_name="Co C"),
    ]

    results = build_peer_comparison(company_financials=cf, financial_ratios=[])

    by_cik = {r["cik"]: r for r in results}
    assert by_cik[1]["sector_rank"] == 1
    assert by_cik[2]["sector_rank"] == 1
    assert by_cik[3]["sector_rank"] == 2  # dense ranking: next distinct value


def test_negative_values_ranked():
    """Losses ranked normally (least negative ranks higher)."""
    cf = [
        _make_cf_row(cik=1, val=-100.0, sector="Tech", entity_id="ER-1", ticker="A",
                     canonical_name="Co A", business_term_id="BT-023",
                     business_term="Net Income"),
        _make_cf_row(cik=2, val=-500.0, sector="Tech", entity_id="ER-2", ticker="B",
                     canonical_name="Co B", business_term_id="BT-023",
                     business_term="Net Income"),
        _make_cf_row(cik=3, val=200.0, sector="Tech", entity_id="ER-3", ticker="C",
                     canonical_name="Co C", business_term_id="BT-023",
                     business_term="Net Income"),
    ]

    results = build_peer_comparison(company_financials=cf, financial_ratios=[])

    by_cik = {r["cik"]: r for r in results}
    assert by_cik[3]["sector_rank"] == 1  # 200 highest
    assert by_cik[1]["sector_rank"] == 2  # -100 second
    assert by_cik[2]["sector_rank"] == 3  # -500 lowest


def test_both_metric_sources():
    """company_financials and financial_ratios both produce rows."""
    cf = [
        _make_cf_row(cik=1, val=300.0, sector="Tech", entity_id="ER-1", ticker="A",
                     canonical_name="Co A"),
        _make_cf_row(cik=2, val=200.0, sector="Tech", entity_id="ER-2", ticker="B",
                     canonical_name="Co B"),
    ]
    fr = [
        _make_fr_row(cik=1, ratio_value=0.3, sector="Tech", entity_id="ER-1",
                     ticker="A", canonical_name="Co A"),
        _make_fr_row(cik=2, ratio_value=0.2, sector="Tech", entity_id="ER-2",
                     ticker="B", canonical_name="Co B"),
    ]

    results = build_peer_comparison(company_financials=cf, financial_ratios=fr)

    cf_rows = [r for r in results if r["metric_source"] == "company_financials"]
    fr_rows = [r for r in results if r["metric_source"] == "financial_ratios"]
    assert len(cf_rows) == 2
    assert len(fr_rows) == 2


def test_missing_metric_excluded():
    """Company without metric not in group, peer_count correct."""
    cf = [
        _make_cf_row(cik=1, val=300.0, sector="Tech", entity_id="ER-1", ticker="A",
                     canonical_name="Co A", business_term_id="BT-022"),
        _make_cf_row(cik=2, val=200.0, sector="Tech", entity_id="ER-2", ticker="B",
                     canonical_name="Co B", business_term_id="BT-022"),
        # Only cik=1 has BT-023
        _make_cf_row(cik=1, val=75.0, sector="Tech", entity_id="ER-1", ticker="A",
                     canonical_name="Co A", business_term_id="BT-023",
                     business_term="Net Income"),
    ]

    results = build_peer_comparison(company_financials=cf, financial_ratios=[])

    bt022_rows = [r for r in results if r["metric_id"] == "BT-022"]
    bt023_rows = [r for r in results if r["metric_id"] == "BT-023"]

    assert len(bt022_rows) == 2
    assert bt022_rows[0]["peer_count"] == 2

    # BT-023 has only 1 company, so excluded (min 2)
    assert len(bt023_rows) == 0


def test_record_id_deterministic():
    """Same inputs produce the same record_id across runs."""
    cf = [
        _make_cf_row(cik=1, val=300.0, sector="Tech", entity_id="ER-1", ticker="A",
                     canonical_name="Co A"),
        _make_cf_row(cik=2, val=200.0, sector="Tech", entity_id="ER-2", ticker="B",
                     canonical_name="Co B"),
    ]

    results1 = build_peer_comparison(company_financials=cf, financial_ratios=[])
    results2 = build_peer_comparison(company_financials=cf, financial_ratios=[])

    r1_ids = {r["cik"]: r["record_id"] for r in results1}
    r2_ids = {r["cik"]: r["record_id"] for r in results2}

    for cik in r1_ids:
        assert r1_ids[cik] == r2_ids[cik]
        assert len(r1_ids[cik]) == 16  # truncated SHA-256


# --- Helper function tests ---

def test_compute_median_odd():
    assert _compute_median([1.0, 2.0, 3.0]) == 2.0


def test_compute_median_even():
    assert _compute_median([1.0, 3.0]) == 2.0


def test_compute_median_empty():
    assert _compute_median([]) == 0.0


def test_dense_rank_basic():
    """Highest value gets rank 1."""
    values = [300.0, 200.0, 100.0]
    assert _dense_rank(values, 300.0) == 1
    assert _dense_rank(values, 200.0) == 2
    assert _dense_rank(values, 100.0) == 3


def test_dense_rank_ties():
    """Tied values get the same rank."""
    values = [300.0, 300.0, 100.0]
    assert _dense_rank(values, 300.0) == 1
    assert _dense_rank(values, 100.0) == 2
