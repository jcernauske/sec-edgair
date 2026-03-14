"""Integration tests: fixture JSON → flatten → Iceberg write → DuckDB read back.

No network required. Uses a temporary directory for the Iceberg warehouse.
"""

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from src.infra.iceberg_setup import get_snapshots, read_with_duckdb
from src.raw.xbrl_company_facts.ingest import ingest_company_facts

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "CIK0000320193_sample.json"


@pytest.fixture
def tmp_workspace(tmp_path):
    """Set up a temporary workspace with cached fixture JSON."""
    cache_dir = tmp_path / "json_cache"
    cache_dir.mkdir()
    # Pre-populate cache so no network is needed
    shutil.copy(FIXTURE_PATH, cache_dir / "CIK0000320193.json")

    warehouse = tmp_path / "iceberg_warehouse"
    catalog = tmp_path / "catalog.db"

    return {
        "cache_dir": cache_dir,
        "warehouse": warehouse,
        "catalog": catalog,
    }


def test_ingest_single_company(tmp_workspace):
    """Ingest Apple fixture and verify row count matches flattener output."""
    ciks = {320193: "Apple Inc."}
    results = ingest_company_facts(
        ciks=ciks,
        method="api",
        cache_dir=tmp_workspace["cache_dir"],
        warehouse_path=tmp_workspace["warehouse"],
        catalog_path=tmp_workspace["catalog"],
        user_agent="test-agent",
    )

    assert 320193 in results
    assert results[320193]["rows"] == 9
    assert results[320193]["snapshot_id"] > 0


def test_ingest_creates_iceberg_table(tmp_workspace):
    """Verify the Iceberg table exists and is readable via DuckDB."""
    from src.infra.iceberg_setup import get_catalog

    ciks = {320193: "Apple Inc."}
    ingest_company_facts(
        ciks=ciks,
        method="api",
        cache_dir=tmp_workspace["cache_dir"],
        warehouse_path=tmp_workspace["warehouse"],
        catalog_path=tmp_workspace["catalog"],
        user_agent="test-agent",
    )

    catalog = get_catalog(tmp_workspace["warehouse"], tmp_workspace["catalog"])
    table = catalog.load_table("raw.xbrl_company_facts")
    rows = read_with_duckdb(table)
    assert len(rows) == 9


def test_ingest_all_19_columns_present(tmp_workspace):
    """Verify all 20 schema columns are present in the output."""
    from src.infra.iceberg_setup import get_catalog

    expected_columns = {
        "cik", "entity_name", "taxonomy", "concept", "label", "description",
        "unit", "start_date", "end_date", "val", "accession_number",
        "fiscal_year", "fiscal_period", "form", "filed_date", "frame",
        "ingested_at", "source_url", "source_method", "load_date",
    }

    ciks = {320193: "Apple Inc."}
    ingest_company_facts(
        ciks=ciks,
        method="api",
        cache_dir=tmp_workspace["cache_dir"],
        warehouse_path=tmp_workspace["warehouse"],
        catalog_path=tmp_workspace["catalog"],
        user_agent="test-agent",
    )

    catalog = get_catalog(tmp_workspace["warehouse"], tmp_workspace["catalog"])
    table = catalog.load_table("raw.xbrl_company_facts")
    rows = read_with_duckdb(table)
    assert len(rows) > 0
    actual_columns = set(rows[0].keys())
    assert actual_columns == expected_columns


def test_ingest_pipeline_metadata_populated(tmp_workspace):
    """Verify ingested_at, source_url, source_method are populated."""
    from src.infra.iceberg_setup import get_catalog

    ciks = {320193: "Apple Inc."}
    ingest_company_facts(
        ciks=ciks,
        method="api",
        cache_dir=tmp_workspace["cache_dir"],
        warehouse_path=tmp_workspace["warehouse"],
        catalog_path=tmp_workspace["catalog"],
        user_agent="test-agent",
    )

    catalog = get_catalog(tmp_workspace["warehouse"], tmp_workspace["catalog"])
    table = catalog.load_table("raw.xbrl_company_facts")
    rows = read_with_duckdb(table)

    for row in rows:
        assert row["ingested_at"] is not None
        assert "320193" in row["source_url"]
        assert row["source_method"] == "api"


def test_ingest_one_snapshot_per_company(tmp_workspace):
    """Each company creates exactly one snapshot."""
    from src.infra.iceberg_setup import get_catalog

    # Create a second fixture for a fake company
    fixture_data = json.loads(FIXTURE_PATH.read_text())
    fixture_data["cik"] = 99999
    fixture_data["entityName"] = "Test Corp."
    (tmp_workspace["cache_dir"] / "CIK0000099999.json").write_text(
        json.dumps(fixture_data)
    )

    ciks = {320193: "Apple Inc.", 99999: "Test Corp."}
    ingest_company_facts(
        ciks=ciks,
        method="api",
        cache_dir=tmp_workspace["cache_dir"],
        warehouse_path=tmp_workspace["warehouse"],
        catalog_path=tmp_workspace["catalog"],
        user_agent="test-agent",
    )

    catalog = get_catalog(tmp_workspace["warehouse"], tmp_workspace["catalog"])
    table = catalog.load_table("raw.xbrl_company_facts")
    snapshots = get_snapshots(table)
    assert len(snapshots) == 2


def test_ingest_snapshot_isolation(tmp_workspace):
    """First snapshot has only company 1 data, second has both."""
    from src.infra.iceberg_setup import get_catalog

    fixture_data = json.loads(FIXTURE_PATH.read_text())
    fixture_data["cik"] = 99999
    fixture_data["entityName"] = "Test Corp."
    (tmp_workspace["cache_dir"] / "CIK0000099999.json").write_text(
        json.dumps(fixture_data)
    )

    ciks = {320193: "Apple Inc.", 99999: "Test Corp."}
    results = ingest_company_facts(
        ciks=ciks,
        method="api",
        cache_dir=tmp_workspace["cache_dir"],
        warehouse_path=tmp_workspace["warehouse"],
        catalog_path=tmp_workspace["catalog"],
        user_agent="test-agent",
    )

    catalog = get_catalog(tmp_workspace["warehouse"], tmp_workspace["catalog"])
    table = catalog.load_table("raw.xbrl_company_facts")

    # Snapshot 1 should have only Apple's 9 rows
    snap1_id = results[320193]["snapshot_id"]
    snap1_rows = read_with_duckdb(table, snapshot_id=snap1_id)
    assert len(snap1_rows) == 9
    assert all(r["cik"] == 320193 for r in snap1_rows)

    # Current state (after snapshot 2) should have 18 rows
    all_rows = read_with_duckdb(table)
    assert len(all_rows) == 18


def test_ingest_invalid_method(tmp_workspace):
    """Unknown method should raise ValueError."""
    with pytest.raises(ValueError, match="Unknown method"):
        ingest_company_facts(
            ciks={320193: "Apple Inc."},
            method="invalid",
            cache_dir=tmp_workspace["cache_dir"],
            warehouse_path=tmp_workspace["warehouse"],
            catalog_path=tmp_workspace["catalog"],
            user_agent="test-agent",
        )
