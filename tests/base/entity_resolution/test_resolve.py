"""Tests for entity resolution logic."""

from src.base.entity_resolution.resolve import resolve_entities_from_records


def _make_raw_records():
    """Create minimal raw fact records for 3 known CIKs."""
    return [
        {"cik": 320193, "entity_name": "Apple Inc."},
        {"cik": 320193, "entity_name": "Apple Inc."},
        {"cik": 19617, "entity_name": "JPMORGAN CHASE & CO"},
        {"cik": 19617, "entity_name": "JPMORGAN CHASE & CO"},
        {"cik": 789019, "entity_name": "MICROSOFT CORPORATION"},
        {"cik": 789019, "entity_name": "MICROSOFT CORPORATION"},
    ]


def test_resolve_three_known_ciks():
    """3 known CIKs should produce 3 proposals with confidence 1.0."""
    records = _make_raw_records()
    proposals = resolve_entities_from_records(records)
    assert len(proposals) == 3
    for p in proposals:
        assert p["confidence"] == 1.0
        assert p["resolution_method"] == "exact_cik_match"
        assert p["status"] == "pending"


def test_resolve_mapping_ids_sequential():
    """Mapping IDs should be ER-001, ER-002, ER-003."""
    records = _make_raw_records()
    proposals = resolve_entities_from_records(records)
    ids = [p["mapping_id"] for p in proposals]
    assert ids == ["ER-001", "ER-002", "ER-003"]


def test_resolve_canonical_names():
    """Canonical names should match KNOWN_ENTITIES."""
    records = _make_raw_records()
    proposals = resolve_entities_from_records(records)
    names = {p["cik"]: p["canonical_name"] for p in proposals}
    assert names[19617] == "JPMorgan Chase & Co."
    assert names[320193] == "Apple Inc."
    assert names[789019] == "Microsoft Corporation"


def test_resolve_raw_entity_name_preserved():
    """Raw entity name should be the most common name from raw data."""
    records = _make_raw_records()
    proposals = resolve_entities_from_records(records)
    raw_names = {p["cik"]: p["raw_entity_name"] for p in proposals}
    assert raw_names[789019] == "MICROSOFT CORPORATION"
    assert raw_names[19617] == "JPMORGAN CHASE & CO"


def test_resolve_unknown_cik_low_confidence():
    """Unknown CIK should get confidence 0.5 and fuzzy method."""
    records = [
        {"cik": 99999, "entity_name": "UNKNOWN COMPANY INC"},
        {"cik": 99999, "entity_name": "UNKNOWN COMPANY INC"},
    ]
    proposals = resolve_entities_from_records(records)
    assert len(proposals) == 1
    assert proposals[0]["confidence"] == 0.5
    assert proposals[0]["resolution_method"] == "fuzzy_name_normalize"
    assert proposals[0]["canonical_name"] == "Unknown Company Inc"


def test_resolve_has_reasoning_and_evidence():
    """Every proposal should have reasoning and evidence fields."""
    records = _make_raw_records()
    proposals = resolve_entities_from_records(records)
    for p in proposals:
        assert "reasoning" in p
        assert "evidence" in p
        assert len(p["reasoning"]) > 0
        assert len(p["evidence"]) > 0


def test_resolve_metadata_fields():
    """Known entities should have ticker, sic_code, fiscal_year_end."""
    records = _make_raw_records()
    proposals = resolve_entities_from_records(records)
    apple = next(p for p in proposals if p["cik"] == 320193)
    assert apple["ticker"] == "AAPL"
    assert apple["sic_code"] == "3571"
    assert apple["fiscal_year_end"] == "0930"
