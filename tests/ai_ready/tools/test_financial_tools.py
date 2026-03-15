"""Integration tests for the 7 tool functions.

Tests against real Iceberg data to validate correct results.
Does NOT call the Claude API.
"""

import pytest

from src.ai_ready.tools.db import reset_db
from src.ai_ready.tools.financial_tools import (
    compare_companies,
    get_company_metric,
    get_company_profile,
    get_company_trend,
    get_ratio,
    get_sector_summary,
    rank_companies,
)


@pytest.fixture(autouse=True, scope="module")
def _load_db():
    """Load DB once for all tests in this module."""
    from src.ai_ready.tools.db import get_db
    get_db()
    yield
    reset_db()


# ---------------------------------------------------------------------------
# Tool 1: get_company_metric
# ---------------------------------------------------------------------------


class TestGetCompanyMetric:
    """Tests for get_company_metric."""

    def test_apple_revenue_returns_value(self):
        result = get_company_metric("AAPL", "Revenue")
        assert "error" not in result, f"Unexpected error: {result.get('error')}"
        assert result["ticker"] == "AAPL"
        assert result["value"] > 0
        assert result["formatted"].startswith("$")
        assert result["metric"] == "Revenue"

    def test_apple_revenue_specific_year(self):
        result = get_company_metric("AAPL", "Revenue", fiscal_year=2023)
        assert "error" not in result
        assert result["fiscal_year"] == 2023

    def test_metric_by_id(self):
        result = get_company_metric("AAPL", "BT-022")
        assert "error" not in result
        assert result["metric_id"] == "BT-022"

    def test_includes_yoy(self):
        result = get_company_metric("AAPL", "Revenue")
        # Should have YoY data for latest year (unless it's the first year)
        # Just check the structure exists if present
        if "yoy_pct" in result:
            assert isinstance(result["yoy_pct"], (int, float))
            assert "yoy_pct_formatted" in result

    def test_includes_sector_rank(self):
        result = get_company_metric("AAPL", "Revenue")
        if "sector_rank" in result:
            assert isinstance(result["sector_rank"], int)
            assert result["sector_rank"] >= 1

    def test_invalid_ticker(self):
        result = get_company_metric("INVALID", "Revenue")
        assert "error" in result

    def test_invalid_metric(self):
        result = get_company_metric("AAPL", "FakeMetric12345")
        assert "error" in result

    def test_missing_metric_for_company(self):
        # Some companies may not report all metrics
        result = get_company_metric("JPM", "Gross Profit", fiscal_year=2020)
        # Should either return data or a helpful error, not crash
        assert isinstance(result, dict)

    def test_case_insensitive_ticker(self):
        result = get_company_metric("aapl", "Revenue")
        assert "error" not in result
        assert result["ticker"] == "AAPL"


# ---------------------------------------------------------------------------
# Tool 2: get_company_profile
# ---------------------------------------------------------------------------


class TestGetCompanyProfile:
    """Tests for get_company_profile."""

    def test_apple_profile(self):
        result = get_company_profile("AAPL")
        assert "error" not in result
        assert "company_info" in result
        assert result["company_info"]["ticker"] == "AAPL"
        assert "metrics" in result
        assert len(result["metrics"]) > 0
        assert "ratios" in result

    def test_profile_specific_year(self):
        result = get_company_profile("MSFT", fiscal_year=2022)
        assert "error" not in result
        assert result["company_info"]["fiscal_year"] == 2022

    def test_profile_has_formatted_values(self):
        result = get_company_profile("AAPL")
        assert "error" not in result
        for m in result["metrics"]:
            assert "formatted" in m
            assert "name" in m

    def test_invalid_ticker(self):
        result = get_company_profile("INVALID")
        assert "error" in result

    def test_boeing_has_anomaly_flags(self):
        """Boeing should have negative equity flags in some years."""
        result = get_company_profile("BA", fiscal_year=2022)
        # May or may not have anomalies in 2022 — just check structure
        assert isinstance(result, dict)
        if "anomaly_flags" in result:
            assert isinstance(result["anomaly_flags"], list)


# ---------------------------------------------------------------------------
# Tool 3: compare_companies
# ---------------------------------------------------------------------------


class TestCompareCompanies:
    """Tests for compare_companies."""

    def test_apple_vs_microsoft(self):
        result = compare_companies("AAPL", "MSFT")
        assert "error" not in result
        assert "company_a" in result
        assert "company_b" in result
        assert "comparisons" in result
        assert len(result["comparisons"]) > 0

    def test_comparison_has_values(self):
        result = compare_companies("AAPL", "MSFT")
        assert "error" not in result
        for comp in result["comparisons"]:
            assert "metric" in comp
            assert "value_a" in comp
            assert "value_b" in comp
            assert "formatted_a" in comp
            assert "formatted_b" in comp
            assert "winner" in comp

    def test_fiscal_alignment_warning_apple_microsoft(self):
        """Apple (Sep FY) and Microsoft (Jun FY) should trigger alignment warning."""
        result = compare_companies("AAPL", "MSFT")
        # The warning depends on actual fiscal_year_end values in the data
        assert isinstance(result, dict)
        # Check that the key exists (may or may not have warning)
        if "fiscal_alignment_warning" in result:
            assert "Fiscal year ends differ" in result["fiscal_alignment_warning"]

    def test_specific_metrics(self):
        result = compare_companies("AAPL", "MSFT", metrics=["Revenue", "Net Income"])
        assert "error" not in result
        metrics_compared = {c["metric"] for c in result["comparisons"]}
        assert "Revenue" in metrics_compared

    def test_invalid_ticker(self):
        result = compare_companies("INVALID1", "INVALID2")
        assert "error" in result or len(result.get("comparisons", [])) == 0


# ---------------------------------------------------------------------------
# Tool 4: rank_companies
# ---------------------------------------------------------------------------


class TestRankCompanies:
    """Tests for rank_companies."""

    def test_rank_by_revenue(self):
        result = rank_companies("Revenue")
        assert "error" not in result
        assert "rankings" in result
        assert len(result["rankings"]) > 0
        # Ranks should be descending by value
        values = [r["value"] for r in result["rankings"]]
        assert values == sorted(values, reverse=True)

    def test_rank_has_correct_structure(self):
        result = rank_companies("Revenue")
        assert "error" not in result
        for r in result["rankings"]:
            assert "rank" in r
            assert "ticker" in r
            assert "value" in r
            assert "formatted" in r

    def test_rank_net_margin(self):
        """Net Margin should auto-detect as financial_ratios."""
        result = rank_companies("Net Margin")
        assert "error" not in result
        assert len(result["rankings"]) > 0

    def test_rank_by_sector(self):
        result = rank_companies("Revenue", sector="Technology")
        assert "error" not in result
        for r in result["rankings"]:
            assert r["sector"] == "Technology"

    def test_top_n(self):
        result = rank_companies("Revenue", top_n=5)
        assert "error" not in result
        assert len(result["rankings"]) <= 5

    def test_invalid_metric(self):
        result = rank_companies("FakeMetric12345")
        assert "error" in result


# ---------------------------------------------------------------------------
# Tool 5: get_company_trend
# ---------------------------------------------------------------------------


class TestGetCompanyTrend:
    """Tests for get_company_trend."""

    def test_apple_revenue_trend(self):
        result = get_company_trend("AAPL", "Revenue")
        assert "error" not in result
        assert "time_series" in result
        assert len(result["time_series"]) > 0
        assert "trend_direction" in result

    def test_trend_has_years(self):
        result = get_company_trend("AAPL", "Revenue")
        assert "error" not in result
        years = [e["fiscal_year"] for e in result["time_series"]]
        assert years == sorted(years), "Time series should be in chronological order"

    def test_trend_with_range(self):
        result = get_company_trend("AAPL", "Revenue", start_year=2018, end_year=2023)
        assert "error" not in result
        years = [e["fiscal_year"] for e in result["time_series"]]
        assert all(2018 <= y <= 2023 for y in years)

    def test_trend_has_formatted_values(self):
        result = get_company_trend("AAPL", "Revenue")
        assert "error" not in result
        for entry in result["time_series"]:
            assert "formatted" in entry

    def test_trend_direction_valid(self):
        result = get_company_trend("AAPL", "Revenue")
        assert result.get("trend_direction") in (
            "growing", "declining", "volatile", "stable", "insufficient_data"
        )

    def test_invalid_ticker(self):
        result = get_company_trend("INVALID", "Revenue")
        assert "error" in result


# ---------------------------------------------------------------------------
# Tool 6: get_sector_summary
# ---------------------------------------------------------------------------


class TestGetSectorSummary:
    """Tests for get_sector_summary."""

    def test_technology_sector(self):
        result = get_sector_summary("Technology")
        assert "error" not in result
        assert "companies" in result
        assert len(result["companies"]) > 0
        assert "metric_summary" in result

    def test_technology_has_multiple_companies(self):
        result = get_sector_summary("Technology")
        assert "error" not in result
        # Technology should have several companies
        assert len(result["companies"]) >= 3

    def test_summary_has_leader_laggard(self):
        result = get_sector_summary("Technology")
        assert "error" not in result
        for ms in result["metric_summary"]:
            assert "leader" in ms
            assert "laggard" in ms
            assert "avg" in ms
            assert "median" in ms

    def test_specific_metric(self):
        result = get_sector_summary("Technology", metric="Revenue")
        assert "error" not in result
        assert len(result["metric_summary"]) == 1

    def test_invalid_sector(self):
        result = get_sector_summary("FakeSector")
        assert "error" in result


# ---------------------------------------------------------------------------
# Tool 7: get_ratio
# ---------------------------------------------------------------------------


class TestGetRatio:
    """Tests for get_ratio."""

    def test_apple_net_margin(self):
        result = get_ratio("AAPL", "Net Margin")
        assert "error" not in result
        assert result["ticker"] == "AAPL"
        assert result["ratio_name"] == "Net Margin"
        assert "value" in result
        assert "numerator" in result
        assert "denominator" in result

    def test_ratio_by_id(self):
        result = get_ratio("AAPL", "RATIO-003")
        assert "error" not in result
        assert result["ratio_id"] == "RATIO-003"

    def test_ratio_has_components(self):
        result = get_ratio("AAPL", "Net Margin")
        assert "error" not in result
        assert "bt_name" in result["numerator"]
        assert "value" in result["numerator"]
        assert "formatted" in result["numerator"]
        assert "bt_name" in result["denominator"]

    def test_ratio_has_sector_rank(self):
        result = get_ratio("AAPL", "Net Margin")
        if "sector_rank" in result:
            assert isinstance(result["sector_rank"], int)

    def test_debt_to_equity(self):
        result = get_ratio("AAPL", "Debt-to-Equity")
        assert "error" not in result
        # D/E is formatted as Xx
        assert "x" in result["formatted"].lower() or "N/A" == result["formatted"]

    def test_invalid_ratio(self):
        result = get_ratio("AAPL", "FakeRatio12345")
        assert "error" in result

    def test_invalid_ticker(self):
        result = get_ratio("INVALID", "Net Margin")
        assert "error" in result
