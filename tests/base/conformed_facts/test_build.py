"""Tests for base.conformed_facts build logic."""

import datetime

from src.base.conformed_facts.build import build_conformed_facts


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
    fact_id: str = "FF-001",
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
        "fact_id": fact_id,
    }


def _make_entity_mapping(
    cik: int = 320193,
    fiscal_year_end: str = "0930",
) -> dict:
    return {
        "cik": cik,
        "fiscal_year_end": fiscal_year_end,
    }


# ---------------------------------------------------------------------------
# 1. Basic build
# ---------------------------------------------------------------------------

def test_basic_build():
    """2 companies, 2 business terms: verify output grain and fields."""
    facts = [
        _make_fact(cik=320193, business_term_id="BT-024", concept="Assets",
                   val=100.0, fact_id="FF-001"),
        _make_fact(cik=320193, business_term_id="BT-022", concept="Revenues",
                   business_term="Revenue", financial_statement="income_statement",
                   category="revenue", val=200.0, fact_id="FF-002"),
        _make_fact(cik=19617, business_term_id="BT-024", concept="Assets",
                   val=300.0, entity_id="ER-19617",
                   canonical_name="JPMorgan Chase & Co.", ticker="JPM",
                   calendar_quarter=4, calendar_year=2023,
                   end_date=datetime.date(2023, 12, 31),
                   filed_date=datetime.date(2024, 2, 15),
                   fact_id="FF-003"),
        _make_fact(cik=19617, business_term_id="BT-022", concept="Revenues",
                   business_term="Revenue", financial_statement="income_statement",
                   category="revenue", val=400.0, entity_id="ER-19617",
                   canonical_name="JPMorgan Chase & Co.", ticker="JPM",
                   calendar_quarter=4, calendar_year=2023,
                   end_date=datetime.date(2023, 12, 31),
                   filed_date=datetime.date(2024, 2, 15),
                   fact_id="FF-004"),
    ]
    entity_mappings = [
        _make_entity_mapping(cik=320193),
        _make_entity_mapping(cik=19617, fiscal_year_end="1231"),
    ]

    results = build_conformed_facts(facts=facts, entity_mappings=entity_mappings)

    assert len(results) == 4  # 2 companies x 2 terms

    expected_fields = {
        "conformed_id", "source_fact_id", "entity_id", "cik", "canonical_name",
        "ticker", "business_term_id", "business_term", "financial_statement",
        "category", "source_concept", "val", "unit", "fiscal_year",
        "fiscal_period", "fiscal_year_end", "period_end_date", "calendar_year",
        "calendar_quarter", "accession_number", "filed_date",
        "competing_fact_count", "selection_reason", "promoted_at", "load_date",
    }
    for r in results:
        assert set(r.keys()) == expected_fields, (
            f"Missing: {expected_fields - set(r.keys())}, "
            f"Extra: {set(r.keys()) - expected_fields}"
        )


# ---------------------------------------------------------------------------
# 2. Concept collision resolution -- primary preferred
# ---------------------------------------------------------------------------

def test_concept_collision_primary_preferred():
    """When multiple concepts map to the same BT, PRIMARY_CONCEPTS order wins."""
    facts = [
        _make_fact(concept="Revenues", val=100.0, business_term_id="BT-022",
                   business_term="Revenue", financial_statement="income_statement",
                   category="revenue", fact_id="FF-010"),
        _make_fact(concept="RevenueFromContractWithCustomerExcludingAssessedTax",
                   val=200.0, business_term_id="BT-022",
                   business_term="Revenue", financial_statement="income_statement",
                   category="revenue", accession_number="0000-23-000002",
                   fact_id="FF-011"),
        _make_fact(concept="SalesRevenueNet", val=300.0, business_term_id="BT-022",
                   business_term="Revenue", financial_statement="income_statement",
                   category="revenue", accession_number="0000-23-000003",
                   fact_id="FF-012"),
    ]
    entity_mappings = [_make_entity_mapping()]

    results = build_conformed_facts(facts=facts, entity_mappings=entity_mappings)

    assert len(results) == 1
    assert results[0]["source_concept"] == "Revenues"
    assert results[0]["val"] == 100.0
    assert results[0]["selection_reason"] == "primary_concept"


# ---------------------------------------------------------------------------
# 3. Concept collision resolution -- tier/frequency fallback
# ---------------------------------------------------------------------------

def test_concept_collision_tier_frequency_fallback():
    """When no primary concept matches, fall back to best tier + most common."""
    facts = [
        _make_fact(concept="SomeObscureRevenue", val=100.0, tier=2,
                   business_term_id="BT-022", business_term="Revenue",
                   financial_statement="income_statement", category="revenue",
                   fact_id="FF-020"),
        _make_fact(concept="AnotherObscureRevenue", val=200.0, tier=3,
                   business_term_id="BT-022", business_term="Revenue",
                   financial_statement="income_statement", category="revenue",
                   accession_number="0000-23-000002", fact_id="FF-021"),
    ]
    entity_mappings = [_make_entity_mapping()]

    results = build_conformed_facts(facts=facts, entity_mappings=entity_mappings)

    assert len(results) == 1
    # Tier 2 beats tier 3 (lower = better)
    assert results[0]["source_concept"] == "SomeObscureRevenue"
    assert results[0]["val"] == 100.0
    assert results[0]["selection_reason"] == "tier_frequency_fallback"


# ---------------------------------------------------------------------------
# 4. Supersession filtering
# ---------------------------------------------------------------------------

def test_superseded_filtered():
    """is_superseded=True facts are excluded."""
    facts = [
        _make_fact(is_superseded=True, val=100.0, fact_id="FF-030"),
        _make_fact(is_superseded=False, val=200.0,
                   accession_number="0000-23-000002", fact_id="FF-031"),
    ]
    entity_mappings = [_make_entity_mapping()]

    results = build_conformed_facts(facts=facts, entity_mappings=entity_mappings)

    assert len(results) == 1
    assert results[0]["val"] == 200.0


# ---------------------------------------------------------------------------
# 5. Unmapped filtering
# ---------------------------------------------------------------------------

def test_unmapped_filtered():
    """business_term_id=None facts are excluded."""
    facts = [
        _make_fact(business_term_id=None, val=100.0, fact_id="FF-040"),
        _make_fact(business_term_id="BT-024", val=200.0,
                   accession_number="0000-23-000002", fact_id="FF-041"),
    ]
    entity_mappings = [_make_entity_mapping()]

    results = build_conformed_facts(facts=facts, entity_mappings=entity_mappings)

    assert len(results) == 1
    assert results[0]["val"] == 200.0


# ---------------------------------------------------------------------------
# 6. Unit filtering
# ---------------------------------------------------------------------------

def test_unit_filtering():
    """Only PRIMARY_UNIT-matching unit is kept per BT."""
    facts = [
        # BT-024 (Total Assets) expects USD
        _make_fact(business_term_id="BT-024", unit="USD", val=100.0,
                   fact_id="FF-050"),
        _make_fact(business_term_id="BT-024", unit="shares", val=999.0,
                   accession_number="0000-23-000002", fact_id="FF-051"),
        # BT-044 (EPS Basic) expects USD/shares
        _make_fact(business_term_id="BT-044", concept="EarningsPerShareBasic",
                   business_term="Earnings Per Share Basic",
                   financial_statement="per_share", category="eps",
                   unit="USD/shares", val=6.42,
                   accession_number="0000-23-000003", fact_id="FF-052"),
        _make_fact(business_term_id="BT-044", concept="EarningsPerShareBasic",
                   business_term="Earnings Per Share Basic",
                   financial_statement="per_share", category="eps",
                   unit="USD", val=9999.0,
                   accession_number="0000-23-000004", fact_id="FF-053"),
    ]
    entity_mappings = [_make_entity_mapping()]

    results = build_conformed_facts(facts=facts, entity_mappings=entity_mappings)

    by_bt = {r["business_term_id"]: r for r in results}
    assert by_bt["BT-024"]["unit"] == "USD"
    assert by_bt["BT-024"]["val"] == 100.0
    assert by_bt["BT-044"]["unit"] == "USD/shares"
    assert by_bt["BT-044"]["val"] == 6.42


# ---------------------------------------------------------------------------
# 7. Null fiscal year filtering
# ---------------------------------------------------------------------------

def test_null_fiscal_year_excluded():
    """Rows with fiscal_year=None are excluded."""
    facts = [
        _make_fact(fiscal_year=None, val=100.0, fact_id="FF-060"),
        _make_fact(fiscal_year=2023, val=200.0,
                   accession_number="0000-23-000002", fact_id="FF-061"),
    ]
    entity_mappings = [_make_entity_mapping()]

    results = build_conformed_facts(facts=facts, entity_mappings=entity_mappings)

    assert len(results) == 1
    assert results[0]["val"] == 200.0


# ---------------------------------------------------------------------------
# 8. conformed_id is deterministic
# ---------------------------------------------------------------------------

def test_conformed_id_deterministic():
    """Same inputs produce the same conformed_id."""
    facts = [_make_fact()]
    entity_mappings = [_make_entity_mapping()]

    results1 = build_conformed_facts(facts=facts, entity_mappings=entity_mappings)
    results2 = build_conformed_facts(facts=facts, entity_mappings=entity_mappings)

    assert results1[0]["conformed_id"] == results2[0]["conformed_id"]
    assert len(results1[0]["conformed_id"]) == 16  # truncated SHA-256


# ---------------------------------------------------------------------------
# 9. source_fact_id preserved
# ---------------------------------------------------------------------------

def test_source_fact_id_preserved():
    """The winning fact's fact_id is carried through as source_fact_id."""
    facts = [_make_fact(fact_id="FF-UNIQUE-99")]
    entity_mappings = [_make_entity_mapping()]

    results = build_conformed_facts(facts=facts, entity_mappings=entity_mappings)

    assert len(results) == 1
    assert results[0]["source_fact_id"] == "FF-UNIQUE-99"


def test_source_fact_id_from_collision_winner():
    """In a collision, the winning fact's fact_id is preserved."""
    facts = [
        _make_fact(concept="Revenues", val=100.0, business_term_id="BT-022",
                   business_term="Revenue", financial_statement="income_statement",
                   category="revenue", fact_id="FF-WINNER"),
        _make_fact(concept="SalesRevenueNet", val=300.0, business_term_id="BT-022",
                   business_term="Revenue", financial_statement="income_statement",
                   category="revenue", accession_number="0000-23-000002",
                   fact_id="FF-LOSER"),
    ]
    entity_mappings = [_make_entity_mapping()]

    results = build_conformed_facts(facts=facts, entity_mappings=entity_mappings)

    assert len(results) == 1
    assert results[0]["source_fact_id"] == "FF-WINNER"


# ---------------------------------------------------------------------------
# 10. competing_fact_count accurate
# ---------------------------------------------------------------------------

def test_competing_fact_count_sole_candidate():
    """Sole candidate has competing_fact_count=1."""
    facts = [_make_fact(fact_id="FF-080")]
    entity_mappings = [_make_entity_mapping()]

    results = build_conformed_facts(facts=facts, entity_mappings=entity_mappings)

    assert len(results) == 1
    assert results[0]["competing_fact_count"] == 1


def test_competing_fact_count_collision():
    """Collision group reports the actual count of competing facts."""
    facts = [
        _make_fact(concept="Revenues", val=100.0, business_term_id="BT-022",
                   business_term="Revenue", financial_statement="income_statement",
                   category="revenue", fact_id="FF-090"),
        _make_fact(concept="RevenueFromContractWithCustomerExcludingAssessedTax",
                   val=200.0, business_term_id="BT-022",
                   business_term="Revenue", financial_statement="income_statement",
                   category="revenue", accession_number="0000-23-000002",
                   fact_id="FF-091"),
        _make_fact(concept="SalesRevenueNet", val=300.0, business_term_id="BT-022",
                   business_term="Revenue", financial_statement="income_statement",
                   category="revenue", accession_number="0000-23-000003",
                   fact_id="FF-092"),
    ]
    entity_mappings = [_make_entity_mapping()]

    results = build_conformed_facts(facts=facts, entity_mappings=entity_mappings)

    assert len(results) == 1
    assert results[0]["competing_fact_count"] == 3


# ---------------------------------------------------------------------------
# 11. selection_reason correct
# ---------------------------------------------------------------------------

def test_selection_reason_sole_candidate():
    """Single fact in group gets selection_reason='sole_candidate'."""
    facts = [_make_fact(fact_id="FF-100")]
    entity_mappings = [_make_entity_mapping()]

    results = build_conformed_facts(facts=facts, entity_mappings=entity_mappings)

    assert results[0]["selection_reason"] == "sole_candidate"


def test_selection_reason_primary_concept():
    """Primary concept match gets selection_reason='primary_concept'."""
    facts = [
        _make_fact(concept="Revenues", val=100.0, business_term_id="BT-022",
                   business_term="Revenue", financial_statement="income_statement",
                   category="revenue", fact_id="FF-110"),
        _make_fact(concept="SalesRevenueNet", val=200.0, business_term_id="BT-022",
                   business_term="Revenue", financial_statement="income_statement",
                   category="revenue", accession_number="0000-23-000002",
                   fact_id="FF-111"),
    ]
    entity_mappings = [_make_entity_mapping()]

    results = build_conformed_facts(facts=facts, entity_mappings=entity_mappings)

    assert results[0]["selection_reason"] == "primary_concept"


def test_selection_reason_tier_frequency_fallback():
    """Non-primary collision gets selection_reason='tier_frequency_fallback'."""
    facts = [
        _make_fact(concept="ObscureRevenueA", val=100.0, tier=1,
                   business_term_id="BT-022", business_term="Revenue",
                   financial_statement="income_statement", category="revenue",
                   fact_id="FF-120"),
        _make_fact(concept="ObscureRevenueB", val=200.0, tier=2,
                   business_term_id="BT-022", business_term="Revenue",
                   financial_statement="income_statement", category="revenue",
                   accession_number="0000-23-000002", fact_id="FF-121"),
    ]
    entity_mappings = [_make_entity_mapping()]

    results = build_conformed_facts(facts=facts, entity_mappings=entity_mappings)

    assert results[0]["selection_reason"] == "tier_frequency_fallback"


# ---------------------------------------------------------------------------
# 12. Legacy CDE-XXX normalization
# ---------------------------------------------------------------------------

def test_legacy_cde_normalization():
    """CDE-XXX IDs in input are translated to BT-XXX before processing."""
    facts = [
        # CDE-007 maps to BT-024 (Total Assets) per LEGACY_CDE_TO_BT
        _make_fact(business_term_id="CDE-007", concept="Assets",
                   business_term="Total Assets", val=500.0, fact_id="FF-130"),
    ]
    entity_mappings = [_make_entity_mapping()]

    results = build_conformed_facts(facts=facts, entity_mappings=entity_mappings)

    assert len(results) == 1
    assert results[0]["business_term_id"] == "BT-024"
    assert results[0]["val"] == 500.0


def test_legacy_cde_normalization_mixed():
    """Mix of CDE-XXX and BT-XXX IDs both work correctly."""
    facts = [
        # CDE-015 maps to BT-022 (Revenue)
        _make_fact(business_term_id="CDE-015", concept="Revenues",
                   business_term="Revenue", financial_statement="income_statement",
                   category="revenue", val=100.0, fact_id="FF-140"),
        # BT-024 is already correct
        _make_fact(business_term_id="BT-024", concept="Assets",
                   val=200.0, accession_number="0000-23-000002",
                   fact_id="FF-141"),
    ]
    entity_mappings = [_make_entity_mapping()]

    results = build_conformed_facts(facts=facts, entity_mappings=entity_mappings)

    by_bt = {r["business_term_id"]: r for r in results}
    assert "BT-022" in by_bt
    assert "BT-024" in by_bt
    assert by_bt["BT-022"]["val"] == 100.0
    assert by_bt["BT-024"]["val"] == 200.0
