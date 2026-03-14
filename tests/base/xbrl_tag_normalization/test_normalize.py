"""Tests for XBRL tag normalization core logic."""

from src.base.xbrl_tag_normalization.normalize import (
    _classify_concept,
    compute_coverage,
    normalize_concepts_from_records,
)


def _make_raw_records(concepts: list[str], cik: int = 320193) -> list[dict]:
    """Build fake raw fact records for testing."""
    return [
        {"cik": cik, "taxonomy": "us-gaap", "concept": c, "entity_name": "Test Corp"}
        for c in concepts
    ]


# --- Tier 1: Exact Match ---

def test_exact_match_revenue():
    """'Revenues' should exact-match to CDE-015 (Revenue)."""
    result = _classify_concept("Revenues")
    assert result["tier"] == 1
    assert result["confidence"] == 1.0
    assert result["cde_id"] == "CDE-015"
    assert result["canonical_cde"] == "Revenue"
    assert result["mapping_method"] == "exact_match"


def test_exact_match_assets():
    """'Assets' should exact-match to CDE-007."""
    result = _classify_concept("Assets")
    assert result["tier"] == 1
    assert result["cde_id"] == "CDE-007"
    assert result["canonical_cde"] == "Total Assets"


def test_exact_match_net_income():
    """'NetIncomeLoss' → CDE-019."""
    result = _classify_concept("NetIncomeLoss")
    assert result["tier"] == 1
    assert result["cde_id"] == "CDE-019"


def test_exact_match_eps_basic():
    """'EarningsPerShareBasic' → CDE-027."""
    result = _classify_concept("EarningsPerShareBasic")
    assert result["tier"] == 1
    assert result["cde_id"] == "CDE-027"


def test_exact_match_operating_cash_flow():
    """'NetCashProvidedByUsedInOperatingActivities' → CDE-023."""
    result = _classify_concept("NetCashProvidedByUsedInOperatingActivities")
    assert result["tier"] == 1
    assert result["cde_id"] == "CDE-023"


# --- Tier 2: Prefix Match ---

def test_prefix_match_revenue_variant():
    """'RevenueFromContractWithCustomerIncludingAssessedTax' should prefix-match."""
    result = _classify_concept("RevenueFromContractWithCustomerIncludingAssessedTax")
    assert result["tier"] == 2
    assert result["confidence"] == 0.7
    assert result["cde_id"] == "CDE-015"
    assert result["mapping_method"] == "prefix_match"


def test_prefix_match_inventory_variant():
    """'InventoryFinishedGoodsNetOfReserves' should prefix-match to CDE-012."""
    result = _classify_concept("InventoryFinishedGoodsNetOfReserves")
    assert result["tier"] == 2
    assert result["cde_id"] == "CDE-012"


def test_prefix_match_goodwill_impairment():
    """'GoodwillImpairmentLoss' should prefix-match to CDE-014."""
    result = _classify_concept("GoodwillImpairmentLoss")
    assert result["tier"] == 2
    assert result["cde_id"] == "CDE-014"


# --- Tier 3: Unmapped ---

def test_unmapped_concept():
    """Unknown concept → tier 3, confidence 0.0, no CDE."""
    result = _classify_concept("DeferredTaxAssetsOperatingLossCarryforwards")
    assert result["tier"] == 3
    assert result["confidence"] == 0.0
    assert result["cde_id"] is None
    assert result["canonical_cde"] is None
    assert result["mapping_method"] == "unmapped"


def test_unmapped_gets_heuristic_category():
    """Unmapped concepts should get heuristic category from substrings."""
    result = _classify_concept("LongTermDebtMaturitiesRepaymentsYear2")
    assert result["tier"] == 3
    assert result["financial_statement"] == "balance_sheet"
    assert result["category"] == "debt"


def test_unmapped_uncategorized():
    """Concept with no matching heuristic → other/uncategorized."""
    result = _classify_concept("SomeTotallyUnknownConcept")
    assert result["tier"] == 3
    assert result["financial_statement"] == "other"
    assert result["category"] == "uncategorized"


# --- Full Pipeline ---

def test_normalize_from_records_classifies_all():
    """All concepts in raw records should produce proposals."""
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


def test_normalize_assigns_mapping_ids():
    """Proposals should have sequential TN-NNNN IDs."""
    records = _make_raw_records(["Assets", "Revenues", "NetIncomeLoss"])
    proposals = normalize_concepts_from_records(records)

    ids = [p["mapping_id"] for p in proposals]
    # Sorted alphabetically: Assets, NetIncomeLoss, Revenues
    assert ids == ["TN-0001", "TN-0002", "TN-0003"]


def test_normalize_tier3_status_is_unmapped():
    """Tier 3 proposals should have status='unmapped', not 'pending'."""
    records = _make_raw_records(["DeferredTaxAssetsOperatingLossCarryforwards"])
    proposals = normalize_concepts_from_records(records)

    assert proposals[0]["status"] == "unmapped"


def test_normalize_tier1_status_is_pending():
    """Tier 1 proposals should have status='pending'."""
    records = _make_raw_records(["Assets"])
    proposals = normalize_concepts_from_records(records)

    assert proposals[0]["status"] == "pending"


def test_non_usgaap_concepts_excluded():
    """Non us-gaap taxonomy records should be excluded."""
    records = [
        {"cik": 1, "taxonomy": "us-gaap", "concept": "Assets", "entity_name": "X"},
        {"cik": 1, "taxonomy": "dei", "concept": "EntityRegistrantName", "entity_name": "X"},
    ]
    proposals = normalize_concepts_from_records(records)
    assert len(proposals) == 1
    assert proposals[0]["concept"] == "Assets"


# --- Coverage ---

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
    assert cov["tier_3_count"] == 2
    assert cov["mapped_concepts"] == 3
    assert cov["concept_coverage_pct"] == 60.0


def test_coverage_with_fact_rows():
    """Fact-level coverage should count facts covered by mapped concepts."""
    proposals = [
        {"concept": "Assets", "tier": 1},
        {"concept": "FooBar", "tier": 3},
    ]
    fact_rows = [
        {"taxonomy": "us-gaap", "concept": "Assets"},
        {"taxonomy": "us-gaap", "concept": "Assets"},
        {"taxonomy": "us-gaap", "concept": "Assets"},
        {"taxonomy": "us-gaap", "concept": "FooBar"},
        {"taxonomy": "dei", "concept": "EntityName"},  # excluded
    ]
    cov = compute_coverage(proposals, fact_rows)
    assert cov["total_facts"] == 4
    assert cov["covered_facts"] == 3
    assert cov["fact_coverage_pct"] == 75.0
