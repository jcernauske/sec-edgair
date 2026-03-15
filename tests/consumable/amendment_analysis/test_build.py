"""Tests for consumable amendment analysis build logic."""

import datetime

from src.consumable.amendment_analysis.build import build_amendment_analysis


def _make_at_row(
    cik: int = 320193,
    concept: str = "Revenue",
    val_change: float = 1000.0,
    val_change_pct: float | None = 0.05,
    end_date: datetime.date | None = None,
    original_filed_date: datetime.date | None = None,
    amendment_filed_date: datetime.date | None = None,
    amendment_accession: str = "0001-23-000001",
) -> dict:
    """Create an amendment_tracking row for testing."""
    if end_date is None:
        end_date = datetime.date(2023, 12, 31)
    if original_filed_date is None:
        original_filed_date = datetime.date(2024, 2, 15)
    if amendment_filed_date is None:
        amendment_filed_date = datetime.date(2024, 8, 15)
    return {
        "tracking_id": f"test-{cik}-{concept}-{end_date}",
        "cik": cik,
        "concept": concept,
        "unit": "USD",
        "start_date": None,
        "end_date": end_date,
        "original_accession": "0001-23-000000",
        "original_filed_date": original_filed_date,
        "original_val": 20000.0,
        "amendment_accession": amendment_accession,
        "amendment_filed_date": amendment_filed_date,
        "amendment_val": 21000.0,
        "val_change": val_change,
        "val_change_pct": val_change_pct,
        "amendment_form": "10-K",
        "detected_at": datetime.datetime.now(datetime.timezone.utc),
        "load_date": datetime.date.today(),
    }


def _make_cf_row(
    cik: int = 320193,
    entity_id: str = "ER-002",
    ticker: str = "AAPL",
    canonical_name: str = "Apple Inc.",
    sector: str = "Technology",
) -> dict:
    """Create a company_financials row for metadata lookup."""
    return {
        "record_id": f"cf-test-{cik}",
        "cik": cik,
        "entity_id": entity_id,
        "ticker": ticker,
        "canonical_name": canonical_name,
        "sector": sector,
        "business_term_id": "BT-022",
        "business_term": "Revenue",
        "val": 394328000000.0,
        "fiscal_year": 2023,
        "fiscal_period": "FY",
    }


# --- Basic aggregation ---

def test_basic_aggregation():
    """3 amendments for 1 company/year, assert amendment_count=3."""
    at = [
        _make_at_row(concept="Revenue", val_change=100.0),
        _make_at_row(concept="NetIncome", val_change=200.0),
        _make_at_row(concept="Revenue", val_change=300.0, amendment_accession="0001-23-000002"),
    ]
    cf = [_make_cf_row()]

    results = build_amendment_analysis(amendment_tracking=at, company_financials=cf)

    assert len(results) == 1
    r = results[0]
    assert r["amendment_count"] == 3
    assert r["cik"] == 320193
    assert r["fiscal_year"] == 2023


def test_distinct_concepts():
    """3 amendments for 2 distinct concepts, assert distinct_concepts=2."""
    at = [
        _make_at_row(concept="Revenue", val_change=100.0),
        _make_at_row(concept="NetIncome", val_change=200.0),
        _make_at_row(concept="Revenue", val_change=300.0, amendment_accession="0001-23-000002"),
    ]
    cf = [_make_cf_row()]

    results = build_amendment_analysis(amendment_tracking=at, company_financials=cf)

    assert results[0]["distinct_concepts"] == 2


def test_mean_abs_change():
    """Known values, assert exact mean."""
    at = [
        _make_at_row(val_change=100.0),
        _make_at_row(val_change=-200.0, amendment_accession="0001-23-000002"),
        _make_at_row(val_change=300.0, amendment_accession="0001-23-000003"),
    ]
    cf = [_make_cf_row()]

    results = build_amendment_analysis(amendment_tracking=at, company_financials=cf)

    # ABS values: 100, 200, 300 -> mean = 200
    assert results[0]["mean_abs_change"] == 200.0


def test_median_abs_change_odd():
    """3 values, assert middle value."""
    at = [
        _make_at_row(val_change=100.0),
        _make_at_row(val_change=-500.0, amendment_accession="0001-23-000002"),
        _make_at_row(val_change=300.0, amendment_accession="0001-23-000003"),
    ]
    cf = [_make_cf_row()]

    results = build_amendment_analysis(amendment_tracking=at, company_financials=cf)

    # ABS values sorted: 100, 300, 500 -> median = 300
    assert results[0]["median_abs_change"] == 300.0


def test_median_abs_change_even():
    """2 values, assert average of both."""
    at = [
        _make_at_row(val_change=100.0),
        _make_at_row(val_change=-300.0, amendment_accession="0001-23-000002"),
    ]
    cf = [_make_cf_row()]

    results = build_amendment_analysis(amendment_tracking=at, company_financials=cf)

    # ABS values: 100, 300 -> median = (100 + 300) / 2 = 200
    assert results[0]["median_abs_change"] == 200.0


def test_max_abs_change():
    """Assert largest absolute change."""
    at = [
        _make_at_row(val_change=100.0),
        _make_at_row(val_change=-500.0, amendment_accession="0001-23-000002"),
        _make_at_row(val_change=300.0, amendment_accession="0001-23-000003"),
    ]
    cf = [_make_cf_row()]

    results = build_amendment_analysis(amendment_tracking=at, company_financials=cf)

    assert results[0]["max_abs_change"] == 500.0


def test_pct_change_null_excluded():
    """2 amendments, 1 with null pct, assert mean uses only non-null."""
    at = [
        _make_at_row(val_change=100.0, val_change_pct=0.10),
        _make_at_row(val_change=200.0, val_change_pct=None, amendment_accession="0001-23-000002"),
    ]
    cf = [_make_cf_row()]

    results = build_amendment_analysis(amendment_tracking=at, company_financials=cf)

    # Only 1 non-null pct: 0.10 -> mean = 0.10
    assert results[0]["mean_pct_change"] == 0.10
    assert results[0]["median_pct_change"] == 0.10


def test_all_pct_null():
    """All amendments have null pct, mean and median are None."""
    at = [
        _make_at_row(val_change=100.0, val_change_pct=None),
        _make_at_row(val_change=200.0, val_change_pct=None, amendment_accession="0001-23-000002"),
    ]
    cf = [_make_cf_row()]

    results = build_amendment_analysis(amendment_tracking=at, company_financials=cf)

    assert results[0]["mean_pct_change"] is None
    assert results[0]["median_pct_change"] is None


def test_total_val_impact():
    """Sum of absolute changes."""
    at = [
        _make_at_row(val_change=100.0),
        _make_at_row(val_change=-200.0, amendment_accession="0001-23-000002"),
        _make_at_row(val_change=300.0, amendment_accession="0001-23-000003"),
    ]
    cf = [_make_cf_row()]

    results = build_amendment_analysis(amendment_tracking=at, company_financials=cf)

    # ABS values: 100 + 200 + 300 = 600
    assert results[0]["total_val_impact"] == 600.0


def test_largest_concept():
    """Concept with biggest change is captured."""
    at = [
        _make_at_row(concept="SmallConcept", val_change=10.0),
        _make_at_row(concept="BigConcept", val_change=-999.0, amendment_accession="0001-23-000002"),
        _make_at_row(concept="MediumConcept", val_change=500.0, amendment_accession="0001-23-000003"),
    ]
    cf = [_make_cf_row()]

    results = build_amendment_analysis(amendment_tracking=at, company_financials=cf)

    assert results[0]["largest_concept"] == "BigConcept"
    assert results[0]["largest_change"] == 999.0


def test_days_to_amend():
    """Known dates, assert correct day counts."""
    at = [
        _make_at_row(
            original_filed_date=datetime.date(2024, 1, 1),
            amendment_filed_date=datetime.date(2024, 7, 1),
        ),
        _make_at_row(
            original_filed_date=datetime.date(2024, 1, 1),
            amendment_filed_date=datetime.date(2024, 4, 1),
            amendment_accession="0001-23-000002",
        ),
    ]
    cf = [_make_cf_row()]

    results = build_amendment_analysis(amendment_tracking=at, company_financials=cf)

    # Days: 182 (Jan 1 to Jul 1), 91 (Jan 1 to Apr 1)
    # Avg: (182 + 91) / 2 = 136.5
    # Median: (91 + 182) / 2 = 136.5
    assert results[0]["days_to_amend_avg"] == 136.5
    assert results[0]["days_to_amend_median"] == 136.5


def test_no_amendments_no_row():
    """Company with 0 amendments in a year produces no row."""
    at = []  # no amendments
    cf = [_make_cf_row()]

    results = build_amendment_analysis(amendment_tracking=at, company_financials=cf)

    assert len(results) == 0


def test_record_id_deterministic():
    """Same inputs produce same record_id across runs."""
    at = [_make_at_row()]
    cf = [_make_cf_row()]

    results1 = build_amendment_analysis(amendment_tracking=at, company_financials=cf)
    results2 = build_amendment_analysis(amendment_tracking=at, company_financials=cf)

    assert results1[0]["record_id"] == results2[0]["record_id"]
    assert len(results1[0]["record_id"]) == 16


def test_multiple_fiscal_years():
    """Amendments in 2022 and 2023 produce 2 rows."""
    at = [
        _make_at_row(end_date=datetime.date(2022, 12, 31), val_change=100.0),
        _make_at_row(end_date=datetime.date(2023, 12, 31), val_change=200.0, amendment_accession="0001-23-000002"),
    ]
    cf = [_make_cf_row()]

    results = build_amendment_analysis(amendment_tracking=at, company_financials=cf)

    assert len(results) == 2
    years = {r["fiscal_year"] for r in results}
    assert years == {2022, 2023}


def test_company_metadata_preserved():
    """Company metadata is correctly populated from company_financials."""
    at = [_make_at_row()]
    cf = [_make_cf_row(ticker="AAPL", canonical_name="Apple Inc.", sector="Technology")]

    results = build_amendment_analysis(amendment_tracking=at, company_financials=cf)

    r = results[0]
    assert r["ticker"] == "AAPL"
    assert r["canonical_name"] == "Apple Inc."
    assert r["sector"] == "Technology"
    assert r["entity_id"] == "ER-002"


def test_company_not_in_financials_skipped():
    """Amendments for a company not in company_financials are skipped."""
    at = [_make_at_row(cik=99999)]  # Unknown CIK
    cf = [_make_cf_row(cik=320193)]

    results = build_amendment_analysis(amendment_tracking=at, company_financials=cf)

    assert len(results) == 0


def test_distinct_filings():
    """Distinct filings count uses amendment_accession."""
    at = [
        _make_at_row(amendment_accession="filing-A", val_change=100.0),
        _make_at_row(amendment_accession="filing-A", val_change=200.0, concept="NetIncome"),
        _make_at_row(amendment_accession="filing-B", val_change=300.0, concept="Assets"),
    ]
    cf = [_make_cf_row()]

    results = build_amendment_analysis(amendment_tracking=at, company_financials=cf)

    assert results[0]["distinct_filings"] == 2
