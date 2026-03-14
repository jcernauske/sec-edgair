"""Tests for the data profiler on raw.xbrl_company_facts.

Uses a temporary Iceberg table with fixture data to verify profiling logic
without requiring the full 104K-row live dataset.
"""

import json
import shutil
from pathlib import Path

import pytest

from src.raw.xbrl_company_facts.ingest import ingest_company_facts
from src.raw.xbrl_company_facts.profile import profile_table, format_profile_report

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "CIK0000320193_sample.json"


@pytest.fixture
def profiled_workspace(tmp_path):
    """Ingest fixture data and return workspace paths for profiling."""
    cache_dir = tmp_path / "json_cache"
    cache_dir.mkdir()
    shutil.copy(FIXTURE_PATH, cache_dir / "CIK0000320193.json")

    warehouse = tmp_path / "iceberg_warehouse"
    catalog = tmp_path / "catalog.db"

    ingest_company_facts(
        ciks={320193: "Apple Inc."},
        method="api",
        cache_dir=cache_dir,
        warehouse_path=warehouse,
        catalog_path=catalog,
        user_agent="test-agent",
    )

    return {"warehouse": warehouse, "catalog": catalog}


def test_profile_returns_expected_structure(profiled_workspace):
    """Profile output has total_rows, field_count, cik_counts, and fields."""
    profile = profile_table(
        warehouse_path=profiled_workspace["warehouse"],
        catalog_path=profiled_workspace["catalog"],
    )

    assert profile["total_rows"] == 9
    assert profile["field_count"] == 19
    assert "320193" in profile["cik_counts"]
    assert profile["cik_counts"]["320193"] == 9
    assert len(profile["fields"]) == 19


def test_profile_all_19_fields_present(profiled_workspace):
    """Every schema field appears in the profile."""
    expected = {
        "cik", "entity_name", "taxonomy", "concept", "label", "description",
        "unit", "start_date", "end_date", "val", "accession_number",
        "fiscal_year", "fiscal_period", "form", "filed_date", "frame",
        "ingested_at", "source_url", "source_method",
    }
    profile = profile_table(
        warehouse_path=profiled_workspace["warehouse"],
        catalog_path=profiled_workspace["catalog"],
    )
    assert set(profile["fields"]) == expected


def test_profile_null_rates_correct(profiled_workspace):
    """Nullable fields show correct null rates from fixture data."""
    profile = profile_table(
        warehouse_path=profiled_workspace["warehouse"],
        catalog_path=profiled_workspace["catalog"],
    )

    # Required fields should have 0 nulls
    assert profile["fields"]["cik"]["null_count"] == 0
    assert profile["fields"]["end_date"]["null_count"] == 0
    assert profile["fields"]["val"]["null_count"] == 0

    # start_date should have nulls (instant facts)
    assert profile["fields"]["start_date"]["null_count"] > 0

    # frame should have nulls
    assert profile["fields"]["frame"]["null_count"] > 0


def test_profile_cardinality(profiled_workspace):
    """Cardinality checks on known fixture data."""
    profile = profile_table(
        warehouse_path=profiled_workspace["warehouse"],
        catalog_path=profiled_workspace["catalog"],
    )

    # Only 1 CIK in fixture
    assert profile["fields"]["cik"]["distinct_count"] == 1

    # 2 taxonomies in fixture (us-gaap, dei)
    assert profile["fields"]["taxonomy"]["distinct_count"] == 2

    # source_method is always "api"
    assert profile["fields"]["source_method"]["distinct_count"] == 1


def test_format_report_produces_markdown(profiled_workspace):
    """format_profile_report produces valid markdown with expected sections."""
    profile = profile_table(
        warehouse_path=profiled_workspace["warehouse"],
        catalog_path=profiled_workspace["catalog"],
    )
    report = format_profile_report(profile)

    assert "## Data Profile: raw.xbrl_company_facts" in report
    assert "Record Count:" in report
    assert "Field Count:" in report
    assert "### Row Counts by CIK" in report
    assert "### Field Profiles" in report
    assert "#### cik" in report
    assert "#### val" in report
