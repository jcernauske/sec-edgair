"""Live bulk ZIP tests for SEC EDGAR XBRL Company Facts.

These tests download the full companyfacts.zip (~2-3 GB). Only run manually:
    pytest tests/raw/xbrl_company_facts/test_fetch_bulk.py -m network

Requires a valid User-Agent with real contact info.
"""

import pytest

from src.raw.xbrl_company_facts.fetch_bulk import fetch_bulk_company_facts

pytestmark = pytest.mark.network


def test_fetch_bulk_apple(tmp_path):
    """Download bulk ZIP and extract Apple (CIK 320193)."""
    results = fetch_bulk_company_facts(
        ciks=[320193],
        cache_dir=tmp_path / "bulk_cache",
        user_agent="SEC-EDGAIR your-email@example.com",
    )

    assert 320193 in results
    data = results[320193]
    assert data["cik"] == 320193
    assert data["entityName"] == "Apple Inc."
    assert "facts" in data


def test_fetch_bulk_multiple_ciks(tmp_path):
    """Extract multiple CIKs from bulk ZIP."""
    ciks = [320193, 789019]
    results = fetch_bulk_company_facts(
        ciks=ciks,
        cache_dir=tmp_path / "bulk_cache",
        user_agent="SEC-EDGAIR your-email@example.com",
    )

    assert len(results) == 2
    assert results[320193]["cik"] == 320193
    assert results[789019]["cik"] == 789019
    assert "facts" in results[320193]
    assert "facts" in results[789019]
