"""Live API tests for SEC EDGAR XBRL Company Facts fetcher.

These tests hit the real SEC EDGAR API. Only run manually:
    pytest tests/raw/xbrl_company_facts/test_fetch_api.py -m network

Requires a valid User-Agent with real contact info.
"""

import pytest

from src.raw.xbrl_company_facts.fetch_api import fetch_company_facts

pytestmark = pytest.mark.network


@pytest.fixture
def live_cache_dir(tmp_path):
    return tmp_path / "live_cache"


def test_fetch_apple_from_api(live_cache_dir):
    """Fetch Apple (CIK 320193) Company Facts from SEC EDGAR."""
    data = fetch_company_facts(
        cik=320193,
        cache_dir=live_cache_dir,
        user_agent="SEC-EDGAIR your-email@example.com",
    )

    assert data["cik"] == 320193
    assert data["entityName"] == "Apple Inc."
    assert "facts" in data
    assert "us-gaap" in data["facts"]
    assert len(data["facts"]["us-gaap"]) > 100


def test_fetch_caches_response(live_cache_dir):
    """Second fetch should use cache, not hit API."""
    data1 = fetch_company_facts(320193, live_cache_dir, "SEC-EDGAIR your-email@example.com")
    data2 = fetch_company_facts(320193, live_cache_dir, "SEC-EDGAIR your-email@example.com")

    assert data1["cik"] == data2["cik"]
    assert (live_cache_dir / "CIK0000320193.json").exists()
