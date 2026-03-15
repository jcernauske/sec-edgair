"""Tests for generic concept normalization engine."""

from pathlib import Path

from src.base.concept_normalization.normalize import (
    ConceptNormalizer,
    _classify_concept,
    compute_coverage,
    normalize_concepts_from_records,
)


# ---------------------------------------------------------------------------
# ConceptNormalizer class tests
# ---------------------------------------------------------------------------

def test_normalizer_loads_from_json(tmp_path):
    """ConceptNormalizer should load mappings from JSON files."""
    import json

    mappings = {
        "mapping_metadata": {"name": "test-mappings", "taxonomy": "test"},
        "business_terms": {
            "BT-001": {"name": "Test Term", "financial_statement": "balance_sheet", "category": "test"},
        },
        "exact_mappings": {
            "TestConcept": ["BT-001", "balance_sheet", "test"],
        },
        "prefix_rules": [],
        "pattern_rules": [],
        "heuristic_categories": {},
    }
    (tmp_path / "test.json").write_text(json.dumps(mappings))

    normalizer = ConceptNormalizer(tmp_path)
    result = normalizer.classify("TestConcept")
    assert result["tier"] == 1
    assert result["business_term_id"] == "BT-001"
    assert result["business_term"] == "Test Term"
    assert result["source_mapping"] == "test-mappings"


def test_normalizer_discovery_mode_no_dir():
    """When mappings_dir is None, all concepts are unmapped."""
    normalizer = ConceptNormalizer(None)
    result = normalizer.classify("AnyConcept")
    assert result["tier"] == "unmapped"
    assert result["confidence"] == 0.0
    assert result["mapping_method"] == "unmapped"
    assert result["source_mapping"] is None


def test_normalizer_discovery_mode_missing_dir(tmp_path):
    """When mappings_dir doesn't exist, all concepts are unmapped."""
    normalizer = ConceptNormalizer(tmp_path / "nonexistent")
    result = normalizer.classify("AnyConcept")
    assert result["tier"] == "unmapped"
    assert result["confidence"] == 0.0


def test_normalizer_discovery_mode_empty_dir(tmp_path):
    """When mappings_dir exists but has no JSON files, all concepts are unmapped."""
    normalizer = ConceptNormalizer(tmp_path)
    result = normalizer.classify("AnyConcept")
    assert result["tier"] == "unmapped"
    assert result["confidence"] == 0.0


def test_normalizer_tracks_unmapped_concepts():
    """get_unmapped_concepts should return all concepts classified as unmapped."""
    normalizer = ConceptNormalizer(None)
    normalizer.classify("Foo")
    normalizer.classify("Bar")
    assert normalizer.get_unmapped_concepts() == ["Foo", "Bar"]


def test_normalizer_mapping_coverage():
    """get_mapping_coverage should return classify counts."""
    normalizer = ConceptNormalizer(None)
    normalizer.classify("Foo")
    normalizer.classify("Bar")
    coverage = normalizer.get_mapping_coverage()
    assert coverage["total"] == 2
    assert coverage["unmapped"] == 2


def test_normalizer_with_real_xbrl_mappings():
    """ConceptNormalizer should load the actual XBRL mappings from domain/concept-mappings/."""
    mappings_dir = Path(__file__).resolve().parents[2] / "domain" / "concept-mappings"
    if not mappings_dir.exists():
        return  # Skip if not in full project context

    normalizer = ConceptNormalizer(mappings_dir)

    # Tier 1: exact match
    result = normalizer.classify("Revenues")
    assert result["tier"] == 1
    assert result["business_term_id"] == "BT-022"
    assert result["confidence"] == 1.0

    # Tier 2: prefix
    result = normalizer.classify("InventoryFinishedGoodsNetOfReserves")
    assert result["tier"] == 2
    assert result["business_term_id"] == "BT-031"
    assert result["confidence"] == 0.7

    # Tier 3: unmapped with heuristic
    result = normalizer.classify("LongTermDebtMaturitiesRepaymentsYear2")
    assert result["tier"] == 3
    assert result["financial_statement"] == "balance_sheet"
    assert result["category"] == "debt"


def test_normalizer_prefix_match(tmp_path):
    """Prefix rules should match concepts starting with the prefix."""
    import json

    mappings = {
        "mapping_metadata": {"name": "test"},
        "business_terms": {"BT-001": {"name": "Revenue", "financial_statement": "is", "category": "rev"}},
        "exact_mappings": {},
        "prefix_rules": [
            {"prefix": "Revenue", "business_term_id": "BT-001", "financial_statement": "income_statement", "category": "revenue"},
        ],
        "pattern_rules": [],
        "heuristic_categories": {},
    }
    (tmp_path / "test.json").write_text(json.dumps(mappings))

    normalizer = ConceptNormalizer(tmp_path)
    result = normalizer.classify("RevenueFromContractWithCustomer")
    assert result["tier"] == 2
    assert result["confidence"] == 0.7
    assert result["mapping_method"] == "prefix_match"


def test_normalizer_pattern_match(tmp_path):
    """Pattern rules should match concepts via regex."""
    import json

    mappings = {
        "mapping_metadata": {"name": "test"},
        "business_terms": {"BT-001": {"name": "Net Income", "financial_statement": "is", "category": "ni"}},
        "exact_mappings": {},
        "prefix_rules": [],
        "pattern_rules": [
            {"pattern": "(?i).*NetIncome.*", "business_term_id": "BT-001", "financial_statement": "income_statement", "category": "net_income"},
        ],
        "heuristic_categories": {},
    }
    (tmp_path / "test.json").write_text(json.dumps(mappings))

    normalizer = ConceptNormalizer(tmp_path)
    result = normalizer.classify("ConsolidatedNetIncomeLoss")
    assert result["tier"] == 2
    assert result["confidence"] == 0.6
    assert result["mapping_method"] == "pattern_match"


# ---------------------------------------------------------------------------
# Backwards-compatible module-level function tests
# ---------------------------------------------------------------------------

def _make_raw_records(concepts: list[str], cik: int = 320193) -> list[dict]:
    """Build fake raw fact records for testing."""
    return [
        {"cik": cik, "taxonomy": "us-gaap", "concept": c, "entity_name": "Test Corp"}
        for c in concepts
    ]


def test_classify_concept_exact_match():
    """_classify_concept should exact-match 'Revenues' to BT-022."""
    result = _classify_concept("Revenues")
    assert result["tier"] == 1
    assert result["confidence"] == 1.0
    assert result["business_term_id"] == "BT-022"
    assert result["mapping_method"] == "exact_match"


def test_classify_concept_prefix_match():
    """_classify_concept should prefix-match revenue variant."""
    result = _classify_concept("RevenueFromContractWithCustomerIncludingAssessedTax")
    assert result["tier"] == 2
    assert result["confidence"] == 0.7
    assert result["business_term_id"] == "BT-022"


def test_classify_concept_unmapped():
    """_classify_concept should return tier 3 for unknown concepts."""
    result = _classify_concept("DeferredTaxAssetsOperatingLossCarryforwards")
    assert result["tier"] == 3
    assert result["confidence"] == 0.0
    assert result["business_term_id"] is None


def test_normalize_from_records():
    """normalize_concepts_from_records should classify all concepts."""
    records = _make_raw_records([
        "Revenues", "Assets", "NetIncomeLoss",
        "InventoryFinishedGoodsNetOfReserves",
        "DeferredTaxAssetsOperatingLossCarryforwards",
    ])
    proposals = normalize_concepts_from_records(records)

    assert len(proposals) == 5
    tiers = {p["concept"]: p["tier"] for p in proposals}
    assert tiers["Revenues"] == 1
    assert tiers["Assets"] == 1
    assert tiers["InventoryFinishedGoodsNetOfReserves"] == 2
    assert tiers["DeferredTaxAssetsOperatingLossCarryforwards"] == 3


def test_coverage_computation():
    """Coverage should report tier counts and percentages."""
    proposals = [
        {"concept": "A", "tier": 1},
        {"concept": "B", "tier": 1},
        {"concept": "C", "tier": 2},
        {"concept": "D", "tier": 3},
        {"concept": "E", "tier": 3},
    ]
    cov = compute_coverage(proposals)
    assert cov["total_concepts"] == 5
    assert cov["tier_1_count"] == 2
    assert cov["tier_2_count"] == 1
    assert cov["mapped_concepts"] == 3
    assert cov["concept_coverage_pct"] == 60.0
