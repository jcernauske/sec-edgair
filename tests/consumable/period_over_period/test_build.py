"""Tests for consumable period-over-period growth build logic."""

import datetime

from src.consumable.period_over_period.build import build_period_over_period


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
        period_end_date = datetime.date(fiscal_year, 9, 30)
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
        "filed_date": datetime.date(fiscal_year, 11, 3),
        "companies_reporting": 20,
        "promoted_at": datetime.datetime.now(datetime.timezone.utc),
        "load_date": datetime.date.today(),
    }


# --- Basic YoY ---

def test_yoy_change_basic():
    """Revenue 100 -> 120 = yoy_change of 20."""
    cf = [
        _make_cf_row(val=100.0, fiscal_year=2022),
        _make_cf_row(val=120.0, fiscal_year=2023),
    ]

    results = build_period_over_period(company_financials=cf)

    yoy = [r for r in results if r["growth_type"] == "yoy_change"]
    assert len(yoy) == 1
    assert yoy[0]["growth_value"] == 20.0
    assert yoy[0]["current_val"] == 120.0
    assert yoy[0]["prior_val"] == 100.0
    assert yoy[0]["fiscal_year"] == 2023


def test_yoy_pct_change_basic():
    """Revenue 100 -> 120 = yoy_pct_change of 0.2 (20%)."""
    cf = [
        _make_cf_row(val=100.0, fiscal_year=2022),
        _make_cf_row(val=120.0, fiscal_year=2023),
    ]

    results = build_period_over_period(company_financials=cf)

    pct = [r for r in results if r["growth_type"] == "yoy_pct_change"]
    assert len(pct) == 1
    assert pct[0]["growth_value"] == 0.2
    assert pct[0]["current_val"] == 120.0
    assert pct[0]["prior_val"] == 100.0


# --- CAGR ---

def test_cagr_basic():
    """Revenue 100 in Y1, ~161.05 in Y6 = 5yr CAGR of ~10%."""
    cf = [
        _make_cf_row(val=100.0, fiscal_year=2018),
        _make_cf_row(val=161.051, fiscal_year=2023),
    ]

    results = build_period_over_period(company_financials=cf)

    cagr = [r for r in results if r["growth_type"] == "cagr_5yr"]
    assert len(cagr) == 1
    assert abs(cagr[0]["growth_value"] - 0.10) < 0.001
    assert cagr[0]["current_val"] == 161.051
    assert cagr[0]["base_val"] == 100.0
    assert cagr[0]["base_fiscal_year"] == 2018
    assert cagr[0]["prior_val"] is None


# --- Edge cases: zero prior ---

def test_zero_prior_no_pct():
    """prior_val=0 produces yoy_change but NOT yoy_pct_change."""
    cf = [
        _make_cf_row(val=0.0, fiscal_year=2022),
        _make_cf_row(val=100.0, fiscal_year=2023),
    ]

    results = build_period_over_period(company_financials=cf)

    yoy_change = [r for r in results if r["growth_type"] == "yoy_change"]
    yoy_pct = [r for r in results if r["growth_type"] == "yoy_pct_change"]

    assert len(yoy_change) == 1
    assert yoy_change[0]["growth_value"] == 100.0
    assert len(yoy_pct) == 0  # division by zero blocked


# --- Edge cases: sign changes ---

def test_sign_change_loss_to_profit():
    """Net Income -100 -> 200: yoy_change=300, yoy_pct_change=3.0 (300%)."""
    cf = [
        _make_cf_row(business_term_id="BT-023", business_term="Net Income",
                     val=-100.0, fiscal_year=2022),
        _make_cf_row(business_term_id="BT-023", business_term="Net Income",
                     val=200.0, fiscal_year=2023),
    ]

    results = build_period_over_period(company_financials=cf)

    yoy_change = [r for r in results if r["growth_type"] == "yoy_change"]
    yoy_pct = [r for r in results if r["growth_type"] == "yoy_pct_change"]

    assert len(yoy_change) == 1
    assert yoy_change[0]["growth_value"] == 300.0
    assert len(yoy_pct) == 1
    assert yoy_pct[0]["growth_value"] == 3.0  # (200 - (-100)) / abs(-100)


def test_sign_change_profit_to_loss():
    """Net Income 200 -> -100: yoy_change=-300, yoy_pct_change=-1.5 (-150%)."""
    cf = [
        _make_cf_row(business_term_id="BT-023", business_term="Net Income",
                     val=200.0, fiscal_year=2022),
        _make_cf_row(business_term_id="BT-023", business_term="Net Income",
                     val=-100.0, fiscal_year=2023),
    ]

    results = build_period_over_period(company_financials=cf)

    yoy_change = [r for r in results if r["growth_type"] == "yoy_change"]
    yoy_pct = [r for r in results if r["growth_type"] == "yoy_pct_change"]

    assert yoy_change[0]["growth_value"] == -300.0
    assert yoy_pct[0]["growth_value"] == -1.5


def test_deepening_loss():
    """Net Income -100 -> -150: yoy_change=-50, yoy_pct_change=-0.5 (-50%)."""
    cf = [
        _make_cf_row(business_term_id="BT-023", business_term="Net Income",
                     val=-100.0, fiscal_year=2022),
        _make_cf_row(business_term_id="BT-023", business_term="Net Income",
                     val=-150.0, fiscal_year=2023),
    ]

    results = build_period_over_period(company_financials=cf)

    yoy_change = [r for r in results if r["growth_type"] == "yoy_change"]
    yoy_pct = [r for r in results if r["growth_type"] == "yoy_pct_change"]

    assert yoy_change[0]["growth_value"] == -50.0
    assert yoy_pct[0]["growth_value"] == -0.5


# --- Edge cases: CAGR ---

def test_cagr_negative_base_skipped():
    """CAGR with base_val=-100 is not produced."""
    cf = [
        _make_cf_row(val=-100.0, fiscal_year=2018),
        _make_cf_row(val=200.0, fiscal_year=2023),
    ]

    results = build_period_over_period(company_financials=cf)

    cagr = [r for r in results if r["growth_type"] == "cagr_5yr"]
    assert len(cagr) == 0


def test_cagr_zero_base_skipped():
    """CAGR with base_val=0 is not produced."""
    cf = [
        _make_cf_row(val=0.0, fiscal_year=2018),
        _make_cf_row(val=200.0, fiscal_year=2023),
    ]

    results = build_period_over_period(company_financials=cf)

    cagr = [r for r in results if r["growth_type"] == "cagr_5yr"]
    assert len(cagr) == 0


def test_cagr_negative_current_allowed():
    """CAGR with positive base and negative current is produced (negative growth)."""
    cf = [
        _make_cf_row(val=100.0, fiscal_year=2018),
        _make_cf_row(val=-50.0, fiscal_year=2023),
    ]

    results = build_period_over_period(company_financials=cf)

    cagr = [r for r in results if r["growth_type"] == "cagr_5yr"]
    assert len(cagr) == 1
    assert cagr[0]["growth_value"] < 0  # negative growth


# --- First year and quarterly ---

def test_first_year_no_yoy():
    """Only one year of data produces 0 YoY rows."""
    cf = [
        _make_cf_row(val=100.0, fiscal_year=2023),
    ]

    results = build_period_over_period(company_financials=cf)

    yoy = [r for r in results if r["growth_type"] in ("yoy_change", "yoy_pct_change")]
    assert len(yoy) == 0


def test_quarterly_yoy_same_quarter():
    """Q1 FY2024 vs Q1 FY2023, not vs Q4 FY2023."""
    cf = [
        _make_cf_row(val=50.0, fiscal_year=2023, fiscal_period="Q1"),
        _make_cf_row(val=100.0, fiscal_year=2023, fiscal_period="Q4"),
        _make_cf_row(val=60.0, fiscal_year=2024, fiscal_period="Q1"),
    ]

    results = build_period_over_period(company_financials=cf)

    # Q1 2024 should compare to Q1 2023 (val=50), not Q4 2023 (val=100)
    q1_yoy = [r for r in results if r["growth_type"] == "yoy_change"
              and r["fiscal_period"] == "Q1" and r["fiscal_year"] == 2024]
    assert len(q1_yoy) == 1
    assert q1_yoy[0]["growth_value"] == 10.0  # 60 - 50
    assert q1_yoy[0]["prior_val"] == 50.0


# --- companies_reporting ---

def test_companies_reporting_count():
    """companies_reporting counts distinct companies per (growth_type, bt_id, period)."""
    cf = [
        # Apple: Revenue 2022 and 2023
        _make_cf_row(cik=320193, val=383.0, fiscal_year=2022),
        _make_cf_row(cik=320193, val=394.0, fiscal_year=2023),
        # JPMorgan: Revenue 2022 and 2023
        _make_cf_row(cik=19617, val=120.0, fiscal_year=2022,
                     entity_id="ER-19617", canonical_name="JPMorgan", ticker="JPM",
                     sector="Financials"),
        _make_cf_row(cik=19617, val=128.0, fiscal_year=2023,
                     entity_id="ER-19617", canonical_name="JPMorgan", ticker="JPM",
                     sector="Financials"),
    ]

    results = build_period_over_period(company_financials=cf)

    yoy_change = [r for r in results if r["growth_type"] == "yoy_change"]
    assert len(yoy_change) == 2  # one per company
    for r in yoy_change:
        assert r["companies_reporting"] == 2


# --- record_id ---

def test_record_id_deterministic():
    """Same inputs produce the same record_id across runs."""
    cf = [
        _make_cf_row(val=100.0, fiscal_year=2022),
        _make_cf_row(val=120.0, fiscal_year=2023),
    ]

    results1 = build_period_over_period(company_financials=cf)
    results2 = build_period_over_period(company_financials=cf)

    r1_ids = {(r["growth_type"], r["fiscal_year"]): r["record_id"] for r in results1}
    r2_ids = {(r["growth_type"], r["fiscal_year"]): r["record_id"] for r in results2}

    for key in r1_ids:
        assert r1_ids[key] == r2_ids[key]
        assert len(r1_ids[key]) == 16  # truncated SHA-256


# --- Company metadata ---

def test_company_metadata_preserved():
    """Growth rows carry company metadata from source."""
    cf = [
        _make_cf_row(cik=320193, ticker="AAPL", canonical_name="Apple Inc.",
                     sector="Technology", val=100.0, fiscal_year=2022),
        _make_cf_row(cik=320193, ticker="AAPL", canonical_name="Apple Inc.",
                     sector="Technology", val=120.0, fiscal_year=2023),
    ]

    results = build_period_over_period(company_financials=cf)

    assert len(results) >= 1
    r = results[0]
    assert r["cik"] == 320193
    assert r["ticker"] == "AAPL"
    assert r["canonical_name"] == "Apple Inc."
    assert r["sector"] == "Technology"
    assert r["business_term_id"] == "BT-022"
    assert r["business_term"] == "Revenue"
