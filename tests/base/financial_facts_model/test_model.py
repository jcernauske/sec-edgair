"""Tests for financial facts model core logic."""

import datetime

from src.base.financial_facts_model.model import (
    _apply_supersession,
    _compute_fact_id,
    _is_amendment,
    build_financial_facts_from_records,
)


def _make_entity(cik: int = 320193) -> dict:
    return {
        "mapping_id": f"ER-{cik}",
        "cik": cik,
        "canonical_name": "Apple Inc.",
        "ticker": "AAPL",
        "fiscal_year_end": "0930",
    }


def _make_concept(concept: str = "Assets", business_term_id: str = "BT-024") -> dict:
    return {
        "concept": concept,
        "business_term_id": business_term_id,
        "business_term": "Total Assets",
        "financial_statement": "balance_sheet",
        "category": "assets",
        "tier": 1,
    }


def _make_raw_fact(
    cik: int = 320193,
    concept: str = "Assets",
    unit: str = "USD",
    val: float = 1000.0,
    start_date: str | None = "2023-01-01",
    end_date: str = "2023-12-31",
    accession_number: str = "0000-23-000001",
    form: str = "10-K",
    filed_date: str = "2024-02-15",
    fiscal_year: int = 2023,
    fiscal_period: str = "FY",
    taxonomy: str = "us-gaap",
) -> dict:
    return {
        "cik": cik,
        "concept": concept,
        "unit": unit,
        "val": val,
        "start_date": start_date,
        "end_date": end_date,
        "accession_number": accession_number,
        "form": form,
        "filed_date": filed_date,
        "fiscal_year": fiscal_year,
        "fiscal_period": fiscal_period,
        "taxonomy": taxonomy,
        "entity_name": "Apple Inc.",
    }


# --- Fact ID ---

def test_fact_id_deterministic():
    """Same grain produces same fact_id."""
    entities = [_make_entity()]
    concepts = [_make_concept()]
    facts1 = build_financial_facts_from_records(
        [_make_raw_fact()], entities, concepts,
    )
    facts2 = build_financial_facts_from_records(
        [_make_raw_fact()], entities, concepts,
    )
    assert facts1[0]["fact_id"] == facts2[0]["fact_id"]


def test_fact_id_differs_for_different_accession():
    """Different accession_number produces different fact_id."""
    entities = [_make_entity()]
    concepts = [_make_concept()]
    raw = [
        _make_raw_fact(accession_number="0000-23-000001"),
        _make_raw_fact(accession_number="0000-23-000002"),
    ]
    facts = build_financial_facts_from_records(raw, entities, concepts)
    assert facts[0]["fact_id"] != facts[1]["fact_id"]


# --- Join logic ---

def test_join_enriches_entity_fields():
    """Entity fields (canonical_name, ticker, entity_id) should be populated."""
    entities = [_make_entity()]
    concepts = [_make_concept()]
    facts = build_financial_facts_from_records(
        [_make_raw_fact()], entities, concepts,
    )

    assert len(facts) == 1
    f = facts[0]
    assert f["entity_id"] == "ER-320193"
    assert f["canonical_name"] == "Apple Inc."
    assert f["ticker"] == "AAPL"


def test_join_enriches_concept_fields():
    """Concept fields (business_term_id, business_term, tier, etc.) should be populated."""
    entities = [_make_entity()]
    concepts = [_make_concept("Assets", "BT-024")]
    facts = build_financial_facts_from_records(
        [_make_raw_fact(concept="Assets")], entities, concepts,
    )

    f = facts[0]
    assert f["business_term_id"] == "BT-024"
    assert f["business_term"] == "Total Assets"
    assert f["financial_statement"] == "balance_sheet"
    assert f["tier"] == 1


def test_join_unmapped_concept():
    """Facts with concepts not in concept_mappings get defaults."""
    entities = [_make_entity()]
    concepts = []  # No mappings
    facts = build_financial_facts_from_records(
        [_make_raw_fact(concept="UnknownConcept")], entities, concepts,
    )

    f = facts[0]
    assert f["business_term_id"] is None
    assert f["business_term"] is None
    assert f["financial_statement"] == "other"
    assert f["category"] == "uncategorized"
    assert f["tier"] == 3


def test_join_skips_unknown_entities():
    """Facts for CIKs not in entity_mappings are excluded."""
    entities = [_make_entity(320193)]
    concepts = [_make_concept()]
    raw = [
        _make_raw_fact(cik=320193),
        _make_raw_fact(cik=999999),
    ]
    facts = build_financial_facts_from_records(raw, entities, concepts)
    assert len(facts) == 1
    assert facts[0]["cik"] == 320193


# --- Derived fields ---

def test_calendar_year_and_quarter():
    """calendar_year/quarter derived from end_date."""
    entities = [_make_entity()]
    concepts = [_make_concept()]
    facts = build_financial_facts_from_records(
        [_make_raw_fact(end_date="2023-09-30")], entities, concepts,
    )

    f = facts[0]
    assert f["calendar_year"] == 2023
    assert f["calendar_quarter"] == 3


def test_is_amendment_detection():
    """Forms ending in /A should set is_amendment=True."""
    assert _is_amendment("10-K/A") is True
    assert _is_amendment("10-Q/A") is True
    assert _is_amendment("10-K") is False
    assert _is_amendment("10-Q") is False


def test_amendment_flag_in_facts():
    """10-K/A filing should produce is_amendment=True."""
    entities = [_make_entity()]
    concepts = [_make_concept()]
    facts = build_financial_facts_from_records(
        [_make_raw_fact(form="10-K/A")], entities, concepts,
    )
    assert facts[0]["is_amendment"] is True


# --- Supersession ---

def test_supersession_single_filing():
    """Single filing for a grain → not superseded."""
    entities = [_make_entity()]
    concepts = [_make_concept()]
    facts = build_financial_facts_from_records(
        [_make_raw_fact()], entities, concepts,
    )
    assert facts[0]["is_superseded"] is False
    assert facts[0]["superseded_by"] is None


def test_supersession_amendment_supersedes_original():
    """Later filing supersedes earlier for same grain."""
    entities = [_make_entity()]
    concepts = [_make_concept()]
    raw = [
        _make_raw_fact(
            accession_number="0000-23-000001",
            filed_date="2024-02-15",
            form="10-K",
            val=1000.0,
        ),
        _make_raw_fact(
            accession_number="0000-23-000002",
            filed_date="2024-05-01",
            form="10-K/A",
            val=1050.0,
        ),
    ]
    facts = build_financial_facts_from_records(raw, entities, concepts)

    original = [f for f in facts if f["accession_number"] == "0000-23-000001"][0]
    amendment = [f for f in facts if f["accession_number"] == "0000-23-000002"][0]

    assert original["is_superseded"] is True
    assert original["superseded_by"] == "0000-23-000002"
    assert amendment["is_superseded"] is False
    assert amendment["superseded_by"] is None


def test_supersession_chain_three_filings():
    """Three filings for same grain: only latest is current."""
    entities = [_make_entity()]
    concepts = [_make_concept()]
    raw = [
        _make_raw_fact(accession_number="A1", filed_date="2024-02-15"),
        _make_raw_fact(accession_number="A2", filed_date="2024-05-01"),
        _make_raw_fact(accession_number="A3", filed_date="2024-08-01"),
    ]
    facts = build_financial_facts_from_records(raw, entities, concepts)

    by_accession = {f["accession_number"]: f for f in facts}
    assert by_accession["A1"]["is_superseded"] is True
    assert by_accession["A1"]["superseded_by"] == "A3"
    assert by_accession["A2"]["is_superseded"] is True
    assert by_accession["A2"]["superseded_by"] == "A3"
    assert by_accession["A3"]["is_superseded"] is False


def test_supersession_different_concepts_independent():
    """Different concepts for same CIK are independent grain groups."""
    entities = [_make_entity()]
    concepts = [
        _make_concept("Assets", "BT-024"),
        {"concept": "Revenue", "business_term_id": "BT-022", "business_term": "Revenue",
         "financial_statement": "income_statement", "category": "revenue", "tier": 1},
    ]
    raw = [
        _make_raw_fact(concept="Assets", accession_number="A1", filed_date="2024-02-15"),
        _make_raw_fact(concept="Assets", accession_number="A2", filed_date="2024-05-01"),
        _make_raw_fact(concept="Revenue", accession_number="A1", filed_date="2024-02-15"),
    ]
    facts = build_financial_facts_from_records(raw, entities, concepts)

    assets = [f for f in facts if f["concept"] == "Assets"]
    revenue = [f for f in facts if f["concept"] == "Revenue"]

    # Assets: A1 superseded by A2
    assert [f for f in assets if f["accession_number"] == "A1"][0]["is_superseded"] is True
    assert [f for f in assets if f["accession_number"] == "A2"][0]["is_superseded"] is False

    # Revenue: only one filing, not superseded
    assert revenue[0]["is_superseded"] is False
