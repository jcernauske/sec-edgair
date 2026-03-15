"""Tests for the three-tier glossary loader.

Validates: registry loading, standard glossary loading, project glossary
composition, term search, tier filtering, and read-only enforcement.
"""

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from src.infra.glossary_loader import (
    ComposedGlossary,
    GlossaryRegistry,
    GlossaryTerm,
    find_matching_term,
    load_project_glossary,
    load_registry,
    load_standard_glossary,
)


# --- Fixtures ---


@pytest.fixture
def tmp_glossary_dir(tmp_path):
    """Create a temporary glossary registry structure."""
    standards_dir = tmp_path / "standards"
    standards_dir.mkdir()
    domains_dir = tmp_path / "domains"
    domains_dir.mkdir()

    # Write a test standard glossary
    test_standard = {
        "glossary_metadata": {
            "name": "test-standard",
            "tier": 1,
            "authority": "Test Authority",
            "version": "1.0",
            "description": "Test standard glossary",
            "term_count": 3,
        },
        "terms": [
            {
                "term_id": "ST-TEST-001",
                "term": "Widget",
                "definition": "A standard widget.",
                "source_reference": "Widget Spec v1",
                "synonyms": ["Gadget", "Thingamajig"],
                "category": "entity",
                "is_cde": True,
                "is_pii": False,
            },
            {
                "term_id": "ST-TEST-002",
                "term": "Widget ID",
                "definition": "Unique identifier for a widget.",
                "source_reference": "Widget Spec v1",
                "synonyms": ["WID"],
                "category": "identifier",
                "is_cde": True,
                "is_pii": False,
            },
            {
                "term_id": "ST-TEST-003",
                "term": "Widget Category",
                "definition": "Classification of widget type.",
                "source_reference": "Widget Spec v1",
                "synonyms": [],
                "category": "classification",
                "is_cde": False,
                "is_pii": False,
            },
        ],
    }

    with open(standards_dir / "test-standard.json", "w") as f:
        json.dump(test_standard, f)

    # Write a test domain glossary
    test_domain = {
        "glossary_metadata": {
            "name": "test-domain",
            "tier": 2,
            "authority": "Community",
            "version": "1.0",
            "description": "Test domain glossary",
            "term_count": 1,
        },
        "terms": [
            {
                "term_id": "DT-TEST-001",
                "term": "Widget Throughput",
                "definition": "Rate of widget processing per unit time.",
                "source_reference": None,
                "synonyms": ["Processing Rate"],
                "category": "metric",
                "is_cde": False,
                "is_pii": False,
            },
        ],
    }

    with open(domains_dir / "test-domain.json", "w") as f:
        json.dump(test_domain, f)

    # Write registry
    registry = {
        "standards": [
            {
                "name": "test-standard",
                "file": "standards/test-standard.json",
                "authority": "Test Authority",
                "term_count": 3,
                "description": "Test standard glossary",
            },
        ],
        "domains": [
            {
                "name": "test-domain",
                "file": "domains/test-domain.json",
                "term_count": 1,
                "description": "Test domain glossary",
            },
        ],
    }

    with open(tmp_path / "registry.yaml", "w") as f:
        yaml.dump(registry, f)

    return tmp_path


@pytest.fixture
def tmp_project_glossary(tmp_path):
    """Create a temporary project glossary with tier metadata."""
    glossary = {
        "glossary_metadata": {
            "version": "3.0",
            "term_count": 4,
            "inherited_from": [
                {"glossary": "test-standard", "tier": 1, "terms_inherited": 2},
            ],
        },
        "terms": [
            {
                "term_id": "BT-001",
                "term": "Widget",
                "definition": "A standard widget.",
                "source": "test-standard",
                "source_tier": 1,
                "upstream_term_id": "ST-TEST-001",
                "read_only": True,
                "category": "entity",
                "synonyms": ["Gadget"],
                "related_terms": ["BT-002"],
                "is_cde": True,
                "is_pii": False,
                "status": "approved",
            },
            {
                "term_id": "BT-002",
                "term": "Widget ID",
                "definition": "Unique identifier for a widget.",
                "source": "test-standard",
                "source_tier": 1,
                "upstream_term_id": "ST-TEST-002",
                "read_only": True,
                "category": "identifier",
                "synonyms": ["WID"],
                "related_terms": [],
                "is_cde": True,
                "is_pii": False,
                "status": "approved",
            },
            {
                "term_id": "BT-003",
                "term": "Pipeline Run ID",
                "definition": "Unique identifier for a pipeline execution.",
                "source": "project-specific",
                "source_tier": 3,
                "upstream_term_id": None,
                "read_only": False,
                "category": "pipeline",
                "synonyms": ["Run ID"],
                "related_terms": [],
                "is_cde": False,
                "is_pii": False,
                "status": "approved",
            },
            {
                "term_id": "BT-004",
                "term": "Quality Score",
                "definition": "Aggregate DQ pass rate for a dataset.",
                "source": "project-specific",
                "source_tier": 3,
                "upstream_term_id": None,
                "read_only": False,
                "category": "pipeline",
                "synonyms": [],
                "related_terms": [],
                "is_cde": False,
                "is_pii": False,
                "status": "proposed",
            },
        ],
    }

    path = tmp_path / "business-glossary.json"
    with open(path, "w") as f:
        json.dump(glossary, f)

    return path


# --- Registry Tests ---


class TestLoadRegistry:
    """Tests for registry loading."""

    def test_load_real_registry(self):
        """Load the actual project registry."""
        registry = load_registry()
        assert isinstance(registry, GlossaryRegistry)
        assert len(registry.standards) >= 2
        names = [s["name"] for s in registry.standards]
        assert "sec-edgar" in names
        assert "xbrl-us-gaap" in names

    def test_missing_registry_returns_empty(self, tmp_path):
        """Missing registry file returns empty registry, not an error."""
        import src.infra.glossary_loader as gl

        original = gl.REGISTRY_PATH
        gl.REGISTRY_PATH = tmp_path / "nonexistent.yaml"
        try:
            registry = load_registry()
            assert registry.standards == []
            assert registry.domains == []
        finally:
            gl.REGISTRY_PATH = original

    def test_list_available(self):
        """Registry lists all available glossary names."""
        registry = load_registry()
        available = registry.list_available()
        assert "sec-edgar" in available
        assert "xbrl-us-gaap" in available

    def test_get_glossary_path(self):
        """Registry resolves glossary name to file path."""
        registry = load_registry()
        path = registry.get_glossary_path("sec-edgar")
        assert path is not None
        assert path.exists()
        assert path.name == "sec-edgar.json"

    def test_get_nonexistent_glossary_path(self):
        """Unknown glossary name returns None."""
        registry = load_registry()
        assert registry.get_glossary_path("nonexistent") is None


# --- Standard Glossary Loading ---


class TestLoadStandardGlossary:
    """Tests for loading individual standard glossaries."""

    def test_load_sec_edgar(self):
        """Load the SEC EDGAR standard glossary."""
        terms = load_standard_glossary("sec-edgar")
        assert len(terms) == 7
        assert all(isinstance(t, GlossaryTerm) for t in terms)
        assert all(t.source_tier == 1 for t in terms)
        assert all(t.read_only for t in terms)

    def test_load_xbrl_us_gaap(self):
        """Load the XBRL US-GAAP standard glossary."""
        terms = load_standard_glossary("xbrl-us-gaap")
        assert len(terms) == 29
        assert all(t.source == "xbrl-us-gaap" for t in terms)

    def test_load_nonexistent_returns_empty(self):
        """Missing glossary returns empty list, not error."""
        terms = load_standard_glossary("nonexistent")
        assert terms == []

    def test_standard_terms_have_upstream_ids(self):
        """Standard glossary terms have ST-prefixed IDs."""
        terms = load_standard_glossary("sec-edgar")
        for term in terms:
            assert term.term_id.startswith("ST-SEC-")

    def test_xbrl_terms_have_upstream_ids(self):
        """XBRL glossary terms have ST-XBRL-prefixed IDs."""
        terms = load_standard_glossary("xbrl-us-gaap")
        for term in terms:
            assert term.term_id.startswith("ST-XBRL-")


# --- Project Glossary Loading ---


class TestLoadProjectGlossary:
    """Tests for loading the composed project glossary."""

    def test_load_real_project_glossary(self):
        """Load the actual project glossary."""
        glossary = load_project_glossary()
        assert isinstance(glossary, ComposedGlossary)
        assert len(glossary.terms) == 54
        assert glossary.version == "3.0"

    def test_inherited_from_metadata(self):
        """Project glossary tracks which shared glossaries it inherits from."""
        glossary = load_project_glossary()
        assert len(glossary.inherited_from) == 2
        names = [i["glossary"] for i in glossary.inherited_from]
        assert "sec-edgar" in names
        assert "xbrl-us-gaap" in names

    def test_tier_distribution(self):
        """Project glossary has correct tier distribution."""
        glossary = load_project_glossary()
        tier1 = glossary.get_by_tier(1)
        tier3 = glossary.get_by_tier(3)
        assert len(tier1) == 36  # 7 sec-edgar + 29 xbrl-taxonomy
        assert len(tier3) == 18  # project-specific

    def test_read_only_terms(self):
        """Inherited terms are marked read-only."""
        glossary = load_project_glossary()
        read_only = glossary.get_read_only()
        assert len(read_only) == 36
        for term in read_only:
            assert term.source_tier == 1
            assert term.upstream_term_id is not None

    def test_project_terms_not_read_only(self):
        """Project-specific terms are not read-only."""
        glossary = load_project_glossary()
        project_terms = glossary.get_project_terms()
        assert len(project_terms) == 18
        for term in project_terms:
            assert not term.read_only
            assert term.upstream_term_id is None

    def test_get_term_by_id(self):
        """Look up a specific term by ID."""
        glossary = load_project_glossary()
        term = glossary.get_term("BT-001")
        assert term is not None
        assert term.term == "Central Index Key (CIK)"
        assert term.source_tier == 1
        assert term.read_only

    def test_get_nonexistent_term(self):
        """Missing term returns None."""
        glossary = load_project_glossary()
        assert glossary.get_term("BT-999") is None

    def test_missing_glossary_returns_empty(self, tmp_path):
        """Missing glossary file returns empty composed glossary."""
        glossary = load_project_glossary(tmp_path / "nonexistent.json")
        assert len(glossary.terms) == 0
        assert glossary.version == "0.0"

    def test_load_from_fixture(self, tmp_project_glossary):
        """Load a fixture-based project glossary."""
        glossary = load_project_glossary(tmp_project_glossary)
        assert len(glossary.terms) == 4
        assert len(glossary.get_by_tier(1)) == 2
        assert len(glossary.get_by_tier(3)) == 2


# --- Search ---


class TestSearch:
    """Tests for term search functionality."""

    def test_search_by_name(self):
        """Search finds terms by name substring."""
        glossary = load_project_glossary()
        results = glossary.search("Revenue")
        assert len(results) >= 1
        assert any(t.term == "Revenue" for t in results)

    def test_search_by_synonym(self):
        """Search finds terms by synonym."""
        glossary = load_project_glossary()
        results = glossary.search("CIK")
        assert len(results) >= 1

    def test_search_case_insensitive(self):
        """Search is case-insensitive."""
        glossary = load_project_glossary()
        results_upper = glossary.search("REVENUE")
        results_lower = glossary.search("revenue")
        assert len(results_upper) == len(results_lower)

    def test_search_no_results(self):
        """Search returns empty list for no matches."""
        glossary = load_project_glossary()
        results = glossary.search("zzzznonexistent")
        assert results == []


# --- Find Matching Term (Link-First API) ---


class TestFindMatchingTerm:
    """Tests for the link-first term lookup used by @data-steward."""

    def test_find_known_term(self):
        """Find a term that exists in the project glossary."""
        term = find_matching_term("Revenue")
        assert term is not None
        assert term.term == "Revenue"

    def test_find_by_synonym(self):
        """Find a term by its synonym."""
        term = find_matching_term("CIK")
        assert term is not None

    def test_find_returns_none_for_unknown(self):
        """Return None for a term that doesn't exist anywhere."""
        term = find_matching_term("QuantumFluxCapacitor")
        assert term is None
