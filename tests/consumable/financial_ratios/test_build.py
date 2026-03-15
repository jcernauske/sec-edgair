"""Tests for consumable financial ratios build logic."""

import datetime

from src.consumable.financial_ratios.build import build_financial_ratios


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


# --- Basic ratio computation ---

def test_net_margin_computation():
    """Net Margin = Net Income / Revenue."""
    cf = [
        _make_cf_row(business_term_id="BT-022", business_term="Revenue", val=1000.0),
        _make_cf_row(business_term_id="BT-023", business_term="Net Income", val=250.0),
    ]

    results = build_financial_ratios(company_financials=cf)

    net_margin = [r for r in results if r["ratio_id"] == "RATIO-003"]
    assert len(net_margin) == 1
    assert net_margin[0]["ratio_value"] == 0.25
    assert net_margin[0]["numerator_val"] == 250.0
    assert net_margin[0]["denominator_val"] == 1000.0
    assert net_margin[0]["numerator_bt_id"] == "BT-023"
    assert net_margin[0]["denominator_bt_id"] == "BT-022"


def test_gross_margin_computation():
    """Gross Margin = Gross Profit / Revenue."""
    cf = [
        _make_cf_row(business_term_id="BT-022", business_term="Revenue", val=500.0),
        _make_cf_row(business_term_id="BT-035", business_term="Gross Profit", val=215.0),
    ]

    results = build_financial_ratios(company_financials=cf)

    gross_margin = [r for r in results if r["ratio_id"] == "RATIO-001"]
    assert len(gross_margin) == 1
    assert gross_margin[0]["ratio_value"] == 0.43


def test_debt_to_equity_computation():
    """Debt-to-Equity = Total Liabilities / Stockholders Equity."""
    cf = [
        _make_cf_row(business_term_id="BT-027", business_term="Total Liabilities", val=300000.0),
        _make_cf_row(business_term_id="BT-028", business_term="Stockholders Equity", val=100000.0),
    ]

    results = build_financial_ratios(company_financials=cf)

    dte = [r for r in results if r["ratio_id"] == "RATIO-004"]
    assert len(dte) == 1
    assert dte[0]["ratio_value"] == 3.0


# --- Edge cases ---

def test_zero_denominator_skipped():
    """Revenue = 0 should produce no ratio rows."""
    cf = [
        _make_cf_row(business_term_id="BT-022", business_term="Revenue", val=0.0),
        _make_cf_row(business_term_id="BT-023", business_term="Net Income", val=250.0),
    ]

    results = build_financial_ratios(company_financials=cf)

    # No margin ratios should be produced (all use BT-022 as denominator)
    margin_ratios = [r for r in results if r["denominator_bt_id"] == "BT-022"]
    assert len(margin_ratios) == 0


def test_negative_equity():
    """Negative stockholders equity produces negative debt-to-equity."""
    cf = [
        _make_cf_row(business_term_id="BT-027", business_term="Total Liabilities", val=150000.0),
        _make_cf_row(business_term_id="BT-028", business_term="Stockholders Equity", val=-50000.0),
    ]

    results = build_financial_ratios(company_financials=cf)

    dte = [r for r in results if r["ratio_id"] == "RATIO-004"]
    assert len(dte) == 1
    assert dte[0]["ratio_value"] == -3.0


def test_capex_abs_applied():
    """CapEx (negative cash outflow) is abs'd before dividing by Revenue."""
    cf = [
        _make_cf_row(business_term_id="BT-022", business_term="Revenue", val=1000.0),
        _make_cf_row(business_term_id="BT-043", business_term="Capital Expenditures", val=-100.0),
    ]

    results = build_financial_ratios(company_financials=cf)

    capex = [r for r in results if r["ratio_id"] == "RATIO-007"]
    assert len(capex) == 1
    assert capex[0]["ratio_value"] == 0.1  # abs(-100) / 1000
    assert capex[0]["numerator_val"] == -100.0  # original value preserved


def test_capex_negative_revenue_skipped():
    """CapEx-to-Revenue skipped when Revenue is negative (data quality issue)."""
    cf = [
        _make_cf_row(business_term_id="BT-022", business_term="Revenue", val=-29000000.0),
        _make_cf_row(business_term_id="BT-043", business_term="Capital Expenditures", val=3612000000.0),
    ]

    results = build_financial_ratios(company_financials=cf)

    capex = [r for r in results if r["ratio_id"] == "RATIO-007"]
    assert len(capex) == 0  # negative Revenue makes the ratio meaningless


def test_missing_component_skipped():
    """Company without R&D produces no R&D Intensity row."""
    cf = [
        _make_cf_row(business_term_id="BT-022", business_term="Revenue", val=1000.0),
        # No BT-038 (R&D) row
    ]

    results = build_financial_ratios(company_financials=cf)

    rd = [r for r in results if r["ratio_id"] == "RATIO-005"]
    assert len(rd) == 0


# --- companies_reporting ---

def test_companies_reporting_count():
    """companies_reporting counts distinct companies per (ratio_id, fiscal_period)."""
    cf = [
        # Apple: Revenue + Net Income
        _make_cf_row(cik=320193, business_term_id="BT-022", business_term="Revenue", val=394.0),
        _make_cf_row(cik=320193, business_term_id="BT-023", business_term="Net Income", val=97.0),
        # JPMorgan: Revenue + Net Income
        _make_cf_row(cik=19617, business_term_id="BT-022", business_term="Revenue", val=128.0,
                     entity_id="ER-19617", canonical_name="JPMorgan", ticker="JPM",
                     sector="Financials"),
        _make_cf_row(cik=19617, business_term_id="BT-023", business_term="Net Income", val=36.0,
                     entity_id="ER-19617", canonical_name="JPMorgan", ticker="JPM",
                     sector="Financials"),
        # Apple only: Gross Profit (JPMorgan doesn't have it)
        _make_cf_row(cik=320193, business_term_id="BT-035", business_term="Gross Profit", val=170.0),
    ]

    results = build_financial_ratios(company_financials=cf)

    net_margins = [r for r in results if r["ratio_id"] == "RATIO-003"]
    gross_margins = [r for r in results if r["ratio_id"] == "RATIO-001"]

    # Net Margin: 2 companies
    assert len(net_margins) == 2
    for r in net_margins:
        assert r["companies_reporting"] == 2

    # Gross Margin: 1 company (Apple only)
    assert len(gross_margins) == 1
    assert gross_margins[0]["companies_reporting"] == 1


# --- record_id ---

def test_record_id_deterministic():
    """Same inputs produce the same record_id across runs."""
    cf = [
        _make_cf_row(business_term_id="BT-022", business_term="Revenue", val=1000.0),
        _make_cf_row(business_term_id="BT-023", business_term="Net Income", val=250.0),
    ]

    results1 = build_financial_ratios(company_financials=cf)
    results2 = build_financial_ratios(company_financials=cf)

    r1_ids = {r["ratio_id"]: r["record_id"] for r in results1}
    r2_ids = {r["ratio_id"]: r["record_id"] for r in results2}

    for ratio_id in r1_ids:
        assert r1_ids[ratio_id] == r2_ids[ratio_id]
        assert len(r1_ids[ratio_id]) == 16  # truncated SHA-256


# --- Multiple ratios from same inputs ---

def test_multiple_ratios_from_revenue():
    """A company with Revenue + multiple metrics produces multiple ratio rows."""
    cf = [
        _make_cf_row(business_term_id="BT-022", business_term="Revenue", val=1000.0),
        _make_cf_row(business_term_id="BT-023", business_term="Net Income", val=100.0),
        _make_cf_row(business_term_id="BT-035", business_term="Gross Profit", val=400.0),
        _make_cf_row(business_term_id="BT-036", business_term="Operating Income", val=200.0),
        _make_cf_row(business_term_id="BT-038", business_term="R&D Expense", val=150.0),
        _make_cf_row(business_term_id="BT-039", business_term="SG&A Expense", val=80.0),
        _make_cf_row(business_term_id="BT-043", business_term="Capital Expenditures", val=-50.0),
    ]

    results = build_financial_ratios(company_financials=cf)

    ratio_ids = {r["ratio_id"] for r in results}
    # Should have 6 ratios (all revenue-based: 001, 002, 003, 005, 006, 007)
    # No RATIO-004 (Debt-to-Equity) because BT-027/BT-028 not provided
    assert ratio_ids == {"RATIO-001", "RATIO-002", "RATIO-003", "RATIO-005", "RATIO-006", "RATIO-007"}

    by_ratio = {r["ratio_id"]: r for r in results}
    assert by_ratio["RATIO-001"]["ratio_value"] == 0.4   # 400/1000
    assert by_ratio["RATIO-002"]["ratio_value"] == 0.2   # 200/1000
    assert by_ratio["RATIO-003"]["ratio_value"] == 0.1   # 100/1000
    assert by_ratio["RATIO-005"]["ratio_value"] == 0.15  # 150/1000
    assert by_ratio["RATIO-006"]["ratio_value"] == 0.08  # 80/1000
    assert by_ratio["RATIO-007"]["ratio_value"] == 0.05  # abs(-50)/1000


# --- Company metadata ---

def test_company_metadata_preserved():
    """Ratio rows carry company metadata from source."""
    cf = [
        _make_cf_row(cik=320193, ticker="AAPL", canonical_name="Apple Inc.",
                     sector="Technology", business_term_id="BT-022",
                     business_term="Revenue", val=394.0),
        _make_cf_row(cik=320193, ticker="AAPL", canonical_name="Apple Inc.",
                     sector="Technology", business_term_id="BT-023",
                     business_term="Net Income", val=97.0),
    ]

    results = build_financial_ratios(company_financials=cf)

    assert len(results) >= 1
    r = results[0]
    assert r["cik"] == 320193
    assert r["ticker"] == "AAPL"
    assert r["canonical_name"] == "Apple Inc."
    assert r["sector"] == "Technology"
