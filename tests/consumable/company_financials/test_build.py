"""Tests for consumable company financials build logic."""

import datetime

from src.consumable.company_financials.build import build_company_financials


def _make_fact(
    cik: int = 320193,
    concept: str = "Assets",
    business_term_id: str = "BT-024",
    business_term: str = "Total Assets",
    financial_statement: str = "balance_sheet",
    category: str = "assets",
    tier: int = 1,
    unit: str = "USD",
    val: float = 352583000000.0,
    fiscal_year: int = 2023,
    fiscal_period: str = "FY",
    end_date: datetime.date | None = None,
    filed_date: datetime.date | None = None,
    accession_number: str = "0000-23-000001",
    is_superseded: bool = False,
    entity_id: str = "ER-320193",
    canonical_name: str = "Apple Inc.",
    ticker: str = "AAPL",
    fiscal_year_end: str = "0930",
    calendar_year: int = 2023,
    calendar_quarter: int = 3,
) -> dict:
    if end_date is None:
        end_date = datetime.date(2023, 9, 30)
    if filed_date is None:
        filed_date = datetime.date(2023, 11, 3)
    return {
        "cik": cik,
        "concept": concept,
        "business_term_id": business_term_id,
        "business_term": business_term,
        "financial_statement": financial_statement,
        "category": category,
        "tier": tier,
        "unit": unit,
        "val": val,
        "fiscal_year": fiscal_year,
        "fiscal_period": fiscal_period,
        "end_date": end_date,
        "filed_date": filed_date,
        "accession_number": accession_number,
        "is_superseded": is_superseded,
        "entity_id": entity_id,
        "canonical_name": canonical_name,
        "ticker": ticker,
        "fiscal_year_end": fiscal_year_end,
        "calendar_year": calendar_year,
        "calendar_quarter": calendar_quarter,
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
        _make_fact(cik=320193, business_term_id="BT-024", concept="Assets", val=100.0),
        _make_fact(cik=320193, business_term_id="BT-022", concept="Revenues",
                   business_term="Revenue", financial_statement="income_statement",
                   category="revenue", val=200.0),
        _make_fact(cik=19617, business_term_id="BT-024", concept="Assets", val=300.0,
                   entity_id="ER-19617", canonical_name="JPMorgan Chase & Co.",
                   ticker="JPM", calendar_quarter=4, calendar_year=2023,
                   end_date=datetime.date(2023, 12, 31),
                   filed_date=datetime.date(2024, 2, 15)),
        _make_fact(cik=19617, business_term_id="BT-022", concept="Revenues",
                   business_term="Revenue", financial_statement="income_statement",
                   category="revenue", val=400.0,
                   entity_id="ER-19617", canonical_name="JPMorgan Chase & Co.",
                   ticker="JPM", calendar_quarter=4, calendar_year=2023,
                   end_date=datetime.date(2023, 12, 31),
                   filed_date=datetime.date(2024, 2, 15)),
    ]
    entity_mappings = [
        _make_entity_mapping(cik=320193, sic_code="3571"),
        _make_entity_mapping(cik=19617, sic_code="6020", fiscal_year_end="1231"),
    ]

    results = build_company_financials(facts=facts, entity_mappings=entity_mappings)

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


# --- Concept collision resolution ---

def test_concept_collision_primary_preferred():
    """When multiple concepts map to the same BT, primary is selected."""
    facts = [
        _make_fact(concept="Revenues", val=100.0, business_term_id="BT-022",
                   business_term="Revenue", financial_statement="income_statement",
                   category="revenue"),
        _make_fact(concept="RevenueFromContractWithCustomerExcludingAssessedTax",
                   val=200.0, business_term_id="BT-022",
                   business_term="Revenue", financial_statement="income_statement",
                   category="revenue", accession_number="0000-23-000002"),
        _make_fact(concept="SalesRevenueNet", val=300.0, business_term_id="BT-022",
                   business_term="Revenue", financial_statement="income_statement",
                   category="revenue", accession_number="0000-23-000003"),
    ]
    entity_mappings = [_make_entity_mapping()]

    results = build_company_financials(facts=facts, entity_mappings=entity_mappings)

    assert len(results) == 1
    # "Revenues" is the first in PRIMARY_CONCEPTS for BT-022
    assert results[0]["source_concept"] == "Revenues"
    assert results[0]["val"] == 100.0


def test_concept_collision_fallback():
    """When no primary concept matches, fallback to highest tier + most common."""
    facts = [
        _make_fact(concept="SomeObscureRevenue", val=100.0, tier=2,
                   business_term_id="BT-022", business_term="Revenue",
                   financial_statement="income_statement", category="revenue"),
        _make_fact(concept="AnotherObscureRevenue", val=200.0, tier=3,
                   business_term_id="BT-022", business_term="Revenue",
                   financial_statement="income_statement", category="revenue",
                   accession_number="0000-23-000002"),
    ]
    entity_mappings = [_make_entity_mapping()]

    results = build_company_financials(facts=facts, entity_mappings=entity_mappings)

    assert len(results) == 1
    # Tier 2 is better than Tier 3 (lower number = better match)
    assert results[0]["source_concept"] == "SomeObscureRevenue"
    assert results[0]["val"] == 100.0


# --- Filtering ---

def test_superseded_filtered():
    """is_superseded=true facts are excluded."""
    facts = [
        _make_fact(is_superseded=True, val=100.0),
        _make_fact(is_superseded=False, val=200.0, accession_number="0000-23-000002"),
    ]
    entity_mappings = [_make_entity_mapping()]

    results = build_company_financials(facts=facts, entity_mappings=entity_mappings)

    assert len(results) == 1
    assert results[0]["val"] == 200.0


def test_unmapped_filtered():
    """business_term_id=None facts are excluded."""
    facts = [
        _make_fact(business_term_id=None, val=100.0),
        _make_fact(business_term_id="BT-024", val=200.0,
                   accession_number="0000-23-000002"),
    ]
    entity_mappings = [_make_entity_mapping()]

    results = build_company_financials(facts=facts, entity_mappings=entity_mappings)

    assert len(results) == 1
    assert results[0]["val"] == 200.0


def test_unit_filtering():
    """Only primary unit is kept per business term."""
    facts = [
        # BT-024 (Total Assets) expects USD
        _make_fact(business_term_id="BT-024", unit="USD", val=100.0),
        _make_fact(business_term_id="BT-024", unit="shares", val=999.0,
                   accession_number="0000-23-000002"),
        # BT-044 (EPS Basic) expects USD/shares
        _make_fact(business_term_id="BT-044", concept="EarningsPerShareBasic",
                   business_term="Earnings Per Share Basic",
                   financial_statement="per_share", category="eps",
                   unit="USD/shares", val=6.42,
                   accession_number="0000-23-000003"),
        _make_fact(business_term_id="BT-044", concept="EarningsPerShareBasic",
                   business_term="Earnings Per Share Basic",
                   financial_statement="per_share", category="eps",
                   unit="USD", val=9999.0,
                   accession_number="0000-23-000004"),
    ]
    entity_mappings = [_make_entity_mapping()]

    results = build_company_financials(facts=facts, entity_mappings=entity_mappings)

    by_bt = {r["business_term_id"]: r for r in results}
    assert by_bt["BT-024"]["unit"] == "USD"
    assert by_bt["BT-024"]["val"] == 100.0
    assert by_bt["BT-044"]["unit"] == "USD/shares"
    assert by_bt["BT-044"]["val"] == 6.42


# --- record_id ---

def test_record_id_deterministic():
    """Same inputs produce the same record_id."""
    facts = [_make_fact()]
    entity_mappings = [_make_entity_mapping()]

    results1 = build_company_financials(facts=facts, entity_mappings=entity_mappings)
    results2 = build_company_financials(facts=facts, entity_mappings=entity_mappings)

    assert results1[0]["record_id"] == results2[0]["record_id"]
    assert len(results1[0]["record_id"]) == 16  # truncated SHA-256


# --- Sector mapping ---

def test_sector_mapping():
    """SIC code maps to the correct sector."""
    facts = [
        _make_fact(cik=320193),  # Apple — SIC 3571 → Technology
        _make_fact(cik=19617, entity_id="ER-19617",
                   canonical_name="JPMorgan Chase & Co.", ticker="JPM",
                   accession_number="0000-23-000002",
                   end_date=datetime.date(2023, 12, 31),
                   filed_date=datetime.date(2024, 2, 15),
                   calendar_year=2023, calendar_quarter=4),
    ]
    entity_mappings = [
        _make_entity_mapping(cik=320193, sic_code="3571"),   # Technology
        _make_entity_mapping(cik=19617, sic_code="6020", fiscal_year_end="1231"),  # Financials
    ]

    results = build_company_financials(facts=facts, entity_mappings=entity_mappings)

    by_cik = {r["cik"]: r for r in results}
    assert by_cik[320193]["sector"] == "Technology"
    assert by_cik[19617]["sector"] == "Financials"


# --- companies_reporting ---

def test_companies_reporting_count():
    """companies_reporting counts distinct CIKs per (business_term_id, fiscal_period)."""
    facts = [
        _make_fact(cik=320193, business_term_id="BT-024", fiscal_period="FY"),
        _make_fact(cik=19617, business_term_id="BT-024", fiscal_period="FY",
                   entity_id="ER-19617", canonical_name="JPMorgan",
                   ticker="JPM", accession_number="0000-23-000002",
                   end_date=datetime.date(2023, 12, 31),
                   filed_date=datetime.date(2024, 2, 15),
                   calendar_year=2023, calendar_quarter=4),
        _make_fact(cik=320193, business_term_id="BT-022", concept="Revenues",
                   business_term="Revenue", financial_statement="income_statement",
                   category="revenue", fiscal_period="FY",
                   accession_number="0000-23-000003"),
    ]
    entity_mappings = [
        _make_entity_mapping(cik=320193, sic_code="3571"),
        _make_entity_mapping(cik=19617, sic_code="6020", fiscal_year_end="1231"),
    ]

    results = build_company_financials(facts=facts, entity_mappings=entity_mappings)

    by_bt = {}
    for r in results:
        by_bt.setdefault(r["business_term_id"], []).append(r)

    # BT-024 FY: 2 companies (Apple + JPMorgan)
    for r in by_bt["BT-024"]:
        assert r["companies_reporting"] == 2

    # BT-022 FY: 1 company (Apple only)
    for r in by_bt["BT-022"]:
        assert r["companies_reporting"] == 1


# --- Null fiscal year ---

def test_null_fiscal_year_excluded():
    """Rows with fiscal_year=None are excluded."""
    facts = [
        _make_fact(fiscal_year=None, val=100.0),
        _make_fact(fiscal_year=2023, val=200.0, accession_number="0000-23-000002"),
    ]
    entity_mappings = [_make_entity_mapping()]

    results = build_company_financials(facts=facts, entity_mappings=entity_mappings)

    assert len(results) == 1
    assert results[0]["val"] == 200.0
