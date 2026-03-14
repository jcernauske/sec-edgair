"""Unit tests for XBRL Company Facts flattening logic.

Uses fixture JSON — no network, no Iceberg.
Tests all edge cases: missing start, missing frame, missing description,
zero val, fractional val, multiple units, multiple taxonomies.
"""

import json
from pathlib import Path

from src.raw.xbrl_company_facts.flatten import flatten_company_facts

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "CIK0000320193_sample.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text())


def test_flatten_returns_correct_row_count():
    """Fixture has 9 fact observations across all concepts and taxonomies."""
    data = _load_fixture()
    rows = flatten_company_facts(data)
    assert len(rows) == 9


def test_flatten_all_rows_have_required_fields():
    """Every row must have the non-nullable fields set by the flattener."""
    required_non_null = {
        "cik", "entity_name", "taxonomy", "concept", "unit",
        "end_date", "val", "accession_number",
        "form", "filed_date",
    }
    # These fields must be present as keys but may be None
    nullable_present = {"label", "description", "start_date", "frame", "fiscal_year", "fiscal_period"}
    data = _load_fixture()
    rows = flatten_company_facts(data)
    for row in rows:
        for field in required_non_null:
            assert field in row, f"Missing required field: {field}"
            assert row[field] is not None, f"Required field is None: {field}"
        for field in nullable_present:
            assert field in row, f"Missing nullable field key: {field}"


def test_flatten_cik_and_entity_name_consistent():
    """All rows should have the same CIK and entity name."""
    data = _load_fixture()
    rows = flatten_company_facts(data)
    for row in rows:
        assert row["cik"] == 320193
        assert row["entity_name"] == "Apple Inc."


def test_flatten_missing_start_date():
    """Instant facts (balance sheet items) have no start date."""
    data = _load_fixture()
    rows = flatten_company_facts(data)
    # Assets is an instant fact — no start date
    assets_rows = [r for r in rows if r["concept"] == "Assets"]
    assert len(assets_rows) == 1
    assert assets_rows[0]["start_date"] is None


def test_flatten_present_start_date():
    """Duration facts (income statement items) have a start date."""
    data = _load_fixture()
    rows = flatten_company_facts(data)
    revenue_rows = [r for r in rows if r["concept"] == "Revenue"]
    assert len(revenue_rows) == 2
    for row in revenue_rows:
        assert row["start_date"] is not None


def test_flatten_missing_frame():
    """Some facts lack a frame identifier."""
    data = _load_fixture()
    rows = flatten_company_facts(data)
    # GoodwillImpairmentLoss has no frame
    gw_rows = [r for r in rows if r["concept"] == "GoodwillImpairmentLoss"]
    assert len(gw_rows) == 1
    assert gw_rows[0]["frame"] is None


def test_flatten_missing_description():
    """GoodwillImpairmentLoss has description=null in fixture."""
    data = _load_fixture()
    rows = flatten_company_facts(data)
    gw_rows = [r for r in rows if r["concept"] == "GoodwillImpairmentLoss"]
    assert gw_rows[0]["description"] is None


def test_flatten_zero_val():
    """val=0 is legitimate (e.g., no goodwill impairment)."""
    data = _load_fixture()
    rows = flatten_company_facts(data)
    gw_rows = [r for r in rows if r["concept"] == "GoodwillImpairmentLoss"]
    assert gw_rows[0]["val"] == 0.0


def test_flatten_fractional_val():
    """EPS has a fractional value (6.16)."""
    data = _load_fixture()
    rows = flatten_company_facts(data)
    eps_rows = [r for r in rows if r["concept"] == "EarningsPerShareBasic"]
    assert len(eps_rows) == 1
    assert eps_rows[0]["val"] == 6.16


def test_flatten_large_integer_val():
    """Revenue is a large integer stored as float."""
    data = _load_fixture()
    rows = flatten_company_facts(data)
    revenue_fy = [
        r for r in rows
        if r["concept"] == "Revenue" and r["fiscal_period"] == "FY"
    ]
    assert len(revenue_fy) == 1
    assert revenue_fy[0]["val"] == 383285000000.0


def test_flatten_multiple_units():
    """EPS uses USD/shares unit, shares outstanding uses shares."""
    data = _load_fixture()
    rows = flatten_company_facts(data)
    eps_rows = [r for r in rows if r["concept"] == "EarningsPerShareBasic"]
    assert eps_rows[0]["unit"] == "USD/shares"
    shares_rows = [r for r in rows if r["concept"] == "CommonStockSharesOutstanding"]
    assert shares_rows[0]["unit"] == "shares"


def test_flatten_multiple_taxonomies():
    """Fixture has both us-gaap and dei taxonomies."""
    data = _load_fixture()
    rows = flatten_company_facts(data)
    taxonomies = {r["taxonomy"] for r in rows}
    assert "us-gaap" in taxonomies
    assert "dei" in taxonomies


def test_flatten_accession_number_format():
    """Accession numbers should be non-empty strings."""
    data = _load_fixture()
    rows = flatten_company_facts(data)
    for row in rows:
        assert isinstance(row["accession_number"], str)
        assert len(row["accession_number"]) > 0


def test_flatten_does_not_add_pipeline_metadata():
    """Flattener does NOT add ingested_at, source_url, source_method."""
    data = _load_fixture()
    rows = flatten_company_facts(data)
    for row in rows:
        assert "ingested_at" not in row
        assert "source_url" not in row
        assert "source_method" not in row


def test_flatten_duplicate_facts_across_periods():
    """NetIncomeLoss appears for two different periods — both are kept."""
    data = _load_fixture()
    rows = flatten_company_facts(data)
    ni_rows = [r for r in rows if r["concept"] == "NetIncomeLoss"]
    assert len(ni_rows) == 2
    end_dates = {r["end_date"] for r in ni_rows}
    assert len(end_dates) == 2
