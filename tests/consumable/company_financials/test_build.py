"""Tests for consumable company financials build logic."""

import datetime

from src.consumable.company_financials.build import build_company_financials


def _make_conformed_fact(
    cik: int = 320193,
    source_concept: str = "Assets",
    business_term_id: str = "BT-024",
    business_term: str = "Total Assets",
    financial_statement: str = "balance_sheet",
    category: str = "assets",
    unit: str = "USD",
    val: float = 352583000000.0,
    fiscal_year: int = 2023,
    fiscal_period: str = "FY",
    period_end_date: datetime.date | None = None,
    filed_date: datetime.date | None = None,
    accession_number: str = "0000-23-000001",
    entity_id: str = "ER-320193",
    canonical_name: str = "Apple Inc.",
    ticker: str = "AAPL",
    fiscal_year_end: str = "0930",
    calendar_year: int = 2023,
    calendar_quarter: int = 3,
    conformed_id: str = "CF-001",
    source_fact_id: str = "SF-001",
    competing_fact_count: int = 1,
    selection_reason: str = "primary_concept",
    promoted_at: datetime.datetime | None = None,
    load_date: datetime.date | None = None,
) -> dict:
    if period_end_date is None:
        period_end_date = datetime.date(2023, 9, 30)
    if filed_date is None:
        filed_date = datetime.date(2023, 11, 3)
    if promoted_at is None:
        promoted_at = datetime.datetime.now(datetime.timezone.utc)
    if load_date is None:
        load_date = datetime.date.today()
    return {
        "cik": cik,
        "entity_id": entity_id,
        "canonical_name": canonical_name,
        "ticker": ticker,
        "business_term_id": business_term_id,
        "business_term": business_term,
        "financial_statement": financial_statement,
        "category": category,
        "source_concept": source_concept,
        "val": val,
        "unit": unit,
        "fiscal_year": fiscal_year,
        "fiscal_period": fiscal_period,
        "fiscal_year_end": fiscal_year_end,
        "period_end_date": period_end_date,
        "calendar_year": calendar_year,
        "calendar_quarter": calendar_quarter,
        "accession_number": accession_number,
        "filed_date": filed_date,
        "conformed_id": conformed_id,
        "source_fact_id": source_fact_id,
        "competing_fact_count": competing_fact_count,
        "selection_reason": selection_reason,
        "promoted_at": promoted_at,
        "load_date": load_date,
    }


def _make_entity_mapping(
    cik: int = 320193,
    sic_code: str = "3571",
    fiscal_year_end: str = "0930",
) -> dict:
    return {
        "cik": cik,
        "sic_code": sic_code,
        "fiscal_year_end": fiscal_year_end,
    }


# --- Basic build ---

def test_basic_build():
    """2 companies, 2 terms: verify output grain and fields."""
    facts = [
        _make_conformed_fact(cik=320193, business_term_id="BT-024", source_concept="Assets", val=100.0),
        _make_conformed_fact(cik=320193, business_term_id="BT-022", source_concept="Revenues",
                   business_term="Revenue", financial_statement="income_statement",
                   category="revenue", val=200.0),
        _make_conformed_fact(cik=19617, business_term_id="BT-024", source_concept="Assets", val=300.0,
                   entity_id="ER-19617", canonical_name="JPMorgan Chase & Co.",
                   ticker="JPM", calendar_quarter=4, calendar_year=2023,
                   period_end_date=datetime.date(2023, 12, 31),
                   filed_date=datetime.date(2024, 2, 15)),
        _make_conformed_fact(cik=19617, business_term_id="BT-022", source_concept="Revenues",
                   business_term="Revenue", financial_statement="income_statement",
                   category="revenue", val=400.0,
                   entity_id="ER-19617", canonical_name="JPMorgan Chase & Co.",
                   ticker="JPM", calendar_quarter=4, calendar_year=2023,
                   period_end_date=datetime.date(2023, 12, 31),
                   filed_date=datetime.date(2024, 2, 15)),
    ]
    entity_mappings = [
        _make_entity_mapping(cik=320193, sic_code="3571"),
        _make_entity_mapping(cik=19617, sic_code="6020", fiscal_year_end="1231"),
    ]

    results = build_company_financials(conformed_facts=facts, entity_mappings=entity_mappings)

    assert len(results) == 4  # 2 companies x 2 terms

    # Check all expected fields are present
    expected_fields = {
        "record_id", "cik", "entity_id", "ticker", "canonical_name", "sector",
        "business_term_id", "business_term", "financial_statement", "category",
        "val", "unit", "source_concept", "fiscal_year", "fiscal_period",
        "fiscal_year_end", "period_end_date", "calendar_year", "calendar_quarter",
        "accession_number", "filed_date", "companies_reporting", "promoted_at",
        "load_date",
    }
    for r in results:
        assert set(r) == expected_fields


# --- record_id ---

def test_record_id_deterministic():
    """Same inputs produce the same record_id."""
    facts = [_make_conformed_fact()]
    entity_mappings = [_make_entity_mapping()]

    results1 = build_company_financials(conformed_facts=facts, entity_mappings=entity_mappings)
    results2 = build_company_financials(conformed_facts=facts, entity_mappings=entity_mappings)

    assert results1[0]["record_id"] == results2[0]["record_id"]
    assert len(results1[0]["record_id"]) == 16  # truncated SHA-256


# --- Sector mapping ---

def test_sector_mapping():
    """SIC code maps to the correct sector."""
    facts = [
        _make_conformed_fact(cik=320193),  # Apple — SIC 3571 -> Technology
        _make_conformed_fact(cik=19617, entity_id="ER-19617",
                   canonical_name="JPMorgan Chase & Co.", ticker="JPM",
                   accession_number="0000-23-000002",
                   period_end_date=datetime.date(2023, 12, 31),
                   filed_date=datetime.date(2024, 2, 15),
                   calendar_year=2023, calendar_quarter=4),
    ]
    entity_mappings = [
        _make_entity_mapping(cik=320193, sic_code="3571"),   # Technology
        _make_entity_mapping(cik=19617, sic_code="6020", fiscal_year_end="1231"),  # Financials
    ]

    results = build_company_financials(conformed_facts=facts, entity_mappings=entity_mappings)

    by_cik = {r["cik"]: r for r in results}
    assert by_cik[320193]["sector"] == "Technology"
    assert by_cik[19617]["sector"] == "Financials"


# --- companies_reporting ---

def test_companies_reporting_count():
    """companies_reporting counts distinct CIKs per (business_term_id, fiscal_period)."""
    facts = [
        _make_conformed_fact(cik=320193, business_term_id="BT-024", fiscal_period="FY"),
        _make_conformed_fact(cik=19617, business_term_id="BT-024", fiscal_period="FY",
                   entity_id="ER-19617", canonical_name="JPMorgan",
                   ticker="JPM", accession_number="0000-23-000002",
                   period_end_date=datetime.date(2023, 12, 31),
                   filed_date=datetime.date(2024, 2, 15),
                   calendar_year=2023, calendar_quarter=4),
        _make_conformed_fact(cik=320193, business_term_id="BT-022", source_concept="Revenues",
                   business_term="Revenue", financial_statement="income_statement",
                   category="revenue", fiscal_period="FY",
                   accession_number="0000-23-000003"),
    ]
    entity_mappings = [
        _make_entity_mapping(cik=320193, sic_code="3571"),
        _make_entity_mapping(cik=19617, sic_code="6020", fiscal_year_end="1231"),
    ]

    results = build_company_financials(conformed_facts=facts, entity_mappings=entity_mappings)

    by_bt = {}
    for r in results:
        by_bt.setdefault(r["business_term_id"], []).append(r)

    # BT-024 FY: 2 companies (Apple + JPMorgan)
    for r in by_bt["BT-024"]:
        assert r["companies_reporting"] == 2

    # BT-022 FY: 1 company (Apple only)
    for r in by_bt["BT-022"]:
        assert r["companies_reporting"] == 1
