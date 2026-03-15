"""Tests for the domain manifest loader.

Validates: manifest parsing, source config loading, hints parsing,
missing manifest handling, and get_source lookup.
"""

import json
from pathlib import Path

import pytest
import yaml

from src.domain_loader import (
    DomainHints,
    DomainManifest,
    SourceConfig,
    get_source,
    load_manifest,
)


# --- Fixtures ---


@pytest.fixture
def minimal_manifest(tmp_path):
    """Create a minimal manifest with no hints."""
    source_config = {
        "name": "test_source",
        "namespace": "raw",
        "table": "test_data",
        "fetch": {
            "api": {
                "url_template": "https://example.com/data/{entity_id}.json",
                "rate_limit_seconds": 0.5,
            }
        },
        "entities": {1: "Entity A", 2: "Entity B"},
        "dedup_grain": ["id", "date"],
        "cache_dir": "data/raw/test_cache",
    }

    sources_dir = tmp_path / "sources"
    sources_dir.mkdir()
    with open(sources_dir / "test_source.yaml", "w") as f:
        yaml.dump(source_config, f)

    manifest = {
        "name": "test-domain",
        "version": "1.0",
        "description": "A test domain",
        "sources": [
            {
                "name": "test_source",
                "source_config": "sources/test_source.yaml",
                "fetcher": "sources/fetchers/test_fetcher.py",
                "flattener": "flatten/test_flattener.py",
            }
        ],
    }

    manifest_path = tmp_path / "manifest.yaml"
    with open(manifest_path, "w") as f:
        yaml.dump(manifest, f)

    return manifest_path


@pytest.fixture
def full_manifest(tmp_path):
    """Create a manifest with all hints populated."""
    source_config = {
        "name": "test_source",
        "namespace": "raw",
        "table": "test_data",
        "fetch": {"api": {"url_template": "https://example.com/{id}.json"}},
        "entities": {100: "Company X", 200: "Company Y"},
        "dedup_grain": ["id", "metric", "date"],
        "cache_dir": "data/raw/cache",
    }

    sources_dir = tmp_path / "sources"
    sources_dir.mkdir()
    with open(sources_dir / "test_source.yaml", "w") as f:
        yaml.dump(source_config, f)

    manifest = {
        "name": "test-with-hints",
        "version": "2.0",
        "description": "A test domain with hints",
        "sources": [
            {
                "name": "test_source",
                "source_config": "sources/test_source.yaml",
            }
        ],
        "hints": {
            "entity_id_field": "company_id",
            "time_field": "report_date",
            "glossary": {
                "inherit": ["standard:test-std", "domain:test-dom"],
            },
            "concept_mappings": "concept-mappings/",
            "metrics": "metrics/",
            "grouping_taxonomy": "taxonomy/groups.yaml",
            "anomaly_rules": "anomaly-rules/",
            "chat_context": "chat-context/prompt.md",
        },
    }

    manifest_path = tmp_path / "manifest.yaml"
    with open(manifest_path, "w") as f:
        yaml.dump(manifest, f)

    return manifest_path


# --- Manifest Loading ---


class TestLoadManifest:
    """Tests for loading the domain manifest."""

    def test_load_real_manifest(self):
        """Load the actual project manifest."""
        manifest = load_manifest()
        assert isinstance(manifest, DomainManifest)
        assert manifest.name == "sec-edgar"
        assert manifest.version == "1.0"
        assert len(manifest.sources) == 1
        assert manifest.sources[0].name == "xbrl_company_facts"

    def test_load_minimal_manifest(self, minimal_manifest):
        """Load a manifest with no hints block."""
        manifest = load_manifest(minimal_manifest)
        assert manifest.name == "test-domain"
        assert manifest.version == "1.0"
        assert len(manifest.sources) == 1

        # Hints should all be None/empty
        assert manifest.hints.entity_id_field is None
        assert manifest.hints.time_field is None
        assert manifest.hints.glossary_inherit == []
        assert manifest.hints.concept_mappings is None

    def test_load_full_manifest(self, full_manifest):
        """Load a manifest with all hints populated."""
        manifest = load_manifest(full_manifest)
        assert manifest.name == "test-with-hints"
        assert manifest.hints.entity_id_field == "company_id"
        assert manifest.hints.time_field == "report_date"
        assert manifest.hints.glossary_inherit == ["standard:test-std", "domain:test-dom"]
        assert manifest.hints.concept_mappings is not None
        assert manifest.hints.metrics is not None

    def test_missing_manifest_raises(self, tmp_path):
        """Missing manifest file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Domain manifest not found"):
            load_manifest(tmp_path / "nonexistent.yaml")

    def test_missing_source_config_raises(self, tmp_path):
        """Missing source config file raises FileNotFoundError."""
        manifest = {
            "name": "broken",
            "version": "1.0",
            "sources": [
                {"name": "bad", "source_config": "sources/nonexistent.yaml"}
            ],
        }
        manifest_path = tmp_path / "manifest.yaml"
        with open(manifest_path, "w") as f:
            yaml.dump(manifest, f)

        with pytest.raises(FileNotFoundError, match="Source config not found"):
            load_manifest(manifest_path)


# --- Source Config ---


class TestSourceConfig:
    """Tests for source configuration loading."""

    def test_real_source_has_entities(self):
        """Real SEC EDGAR source has 20 entities."""
        manifest = load_manifest()
        source = manifest.sources[0]
        assert len(source.entities) == 20
        assert 320193 in source.entities  # Apple
        assert source.entities[320193] == "Apple Inc."

    def test_real_source_has_dedup_grain(self):
        """Real source has 5-field dedup grain."""
        manifest = load_manifest()
        source = manifest.sources[0]
        assert source.dedup_grain == ["cik", "accession_number", "concept", "unit", "end_date"]

    def test_real_source_has_fetch_config(self):
        """Real source has API and bulk fetch configs."""
        manifest = load_manifest()
        source = manifest.sources[0]
        assert "api" in source.fetch
        assert "bulk" in source.fetch
        assert "url_template" in source.fetch["api"]

    def test_source_full_table_name(self):
        """Source config provides full table name."""
        manifest = load_manifest()
        source = manifest.sources[0]
        assert source.full_table_name == "raw.xbrl_company_facts"

    def test_source_cache_dir_resolved(self):
        """Cache dir is resolved to absolute path."""
        manifest = load_manifest()
        source = manifest.sources[0]
        assert source.cache_dir.is_absolute()
        assert str(source.cache_dir).endswith("data/raw/json_cache")

    def test_source_fetcher_path(self):
        """Source config stores fetcher path."""
        manifest = load_manifest()
        source = manifest.sources[0]
        assert source.fetcher_path == "domain/sources/fetchers/api_fetcher.py"

    def test_source_flattener_path(self):
        """Source config stores flattener path."""
        manifest = load_manifest()
        source = manifest.sources[0]
        assert source.flattener_path == "domain/flatten/xbrl_flattener.py"

    def test_fixture_source_config(self, minimal_manifest):
        """Load source config from fixture manifest."""
        manifest = load_manifest(minimal_manifest)
        source = manifest.sources[0]
        assert source.name == "test_source"
        assert source.namespace == "raw"
        assert source.table == "test_data"
        assert len(source.entities) == 2
        assert source.dedup_grain == ["id", "date"]


# --- Get Source ---


class TestGetSource:
    """Tests for source lookup by name."""

    def test_get_existing_source(self):
        """Get source by name from real manifest."""
        manifest = load_manifest()
        source = get_source(manifest, "xbrl_company_facts")
        assert source.name == "xbrl_company_facts"

    def test_get_nonexistent_source_raises(self):
        """Unknown source name raises KeyError."""
        manifest = load_manifest()
        with pytest.raises(KeyError, match="not found in manifest"):
            get_source(manifest, "nonexistent_source")


# --- Hints ---


class TestDomainHints:
    """Tests for optional hints parsing."""

    def test_real_manifest_has_hints(self):
        """Real manifest has SEC EDGAR hints."""
        manifest = load_manifest()
        assert manifest.hints.entity_id_field == "cik"
        assert manifest.hints.time_field == "end_date"

    def test_real_manifest_glossary_inherit(self):
        """Real manifest inherits from xbrl and sec-edgar glossaries."""
        manifest = load_manifest()
        assert "standard:xbrl-us-gaap" in manifest.hints.glossary_inherit
        assert "standard:sec-edgar" in manifest.hints.glossary_inherit

    def test_no_hints_all_none(self, minimal_manifest):
        """Manifest without hints block has all-None hints."""
        manifest = load_manifest(minimal_manifest)
        hints = manifest.hints
        assert hints.entity_id_field is None
        assert hints.time_field is None
        assert hints.glossary_inherit == []
        assert hints.concept_mappings is None
        assert hints.metrics is None
        assert hints.grouping_taxonomy is None
        assert hints.anomaly_rules is None
        assert hints.chat_context is None

    def test_hints_paths_resolved(self, full_manifest):
        """Hint paths are resolved relative to project root."""
        manifest = load_manifest(full_manifest)
        assert manifest.hints.concept_mappings is not None
        assert manifest.hints.concept_mappings.is_absolute()


# --- Backwards Compatibility ---


class TestBackwardsCompatibility:
    """Tests that existing config.py still works after manifest integration."""

    def test_config_module_loads(self):
        """The raw config module still imports without error."""
        from src.raw.xbrl_company_facts.config import (
            API_URL_TEMPLATE,
            BULK_ZIP_URL,
            CATALOG_PATH,
            DEFAULT_CIKS,
            JSON_CACHE_DIR,
            RATE_LIMIT_SLEEP,
            USER_AGENT,
            WAREHOUSE_PATH,
        )
        # All values should be populated
        assert DEFAULT_CIKS is not None
        assert len(DEFAULT_CIKS) == 20
        assert API_URL_TEMPLATE is not None
        assert BULK_ZIP_URL is not None
        assert JSON_CACHE_DIR is not None
        assert WAREHOUSE_PATH is not None
        assert CATALOG_PATH is not None
        assert RATE_LIMIT_SLEEP > 0
        assert USER_AGENT is not None

    def test_config_values_match_manifest(self):
        """Config values loaded from manifest match YAML source of truth."""
        from src.raw.xbrl_company_facts.config import DEFAULT_CIKS, RATE_LIMIT_SLEEP

        manifest = load_manifest()
        source = get_source(manifest, "xbrl_company_facts")

        # Entities should match
        assert len(DEFAULT_CIKS) == len(source.entities)
        assert 320193 in DEFAULT_CIKS  # Apple

        # Rate limit should match
        api_config = source.fetch.get("api", {})
        assert RATE_LIMIT_SLEEP == api_config.get("rate_limit_seconds", 0.1)
