"""Integration tests for the DB module.

Tests that Iceberg tables can be loaded into DuckDB.
"""

import pytest

from src.ai_ready.tools.db import get_db, get_table_row_counts, reset_db


@pytest.fixture(autouse=True)
def _reset():
    """Reset DB between tests."""
    reset_db()
    yield
    reset_db()


class TestDbConnection:
    """Tests for DB connection and table loading."""

    def test_get_db_returns_connection(self):
        con = get_db()
        assert con is not None

    def test_tables_loaded(self):
        counts = get_table_row_counts()
        assert "company_financials" in counts
        assert "financial_ratios" in counts
        assert "period_over_period" in counts
        assert "peer_comparison" in counts
        assert "amendment_analysis" in counts

    def test_company_financials_has_rows(self):
        counts = get_table_row_counts()
        assert counts["company_financials"] > 0, "company_financials should have data"

    def test_financial_ratios_has_rows(self):
        counts = get_table_row_counts()
        assert counts["financial_ratios"] > 0, "financial_ratios should have data"

    def test_can_query_company_financials(self):
        con = get_db()
        result = con.execute(
            "SELECT COUNT(DISTINCT ticker) FROM company_financials"
        ).fetchone()
        assert result[0] >= 15, f"Expected at least 15 companies, got {result[0]}"

    def test_can_query_with_filter(self):
        con = get_db()
        result = con.execute(
            "SELECT val FROM company_financials WHERE ticker = 'AAPL' AND business_term_id = 'BT-022' AND fiscal_period = 'FY' ORDER BY fiscal_year DESC LIMIT 1"
        ).fetchone()
        assert result is not None, "Should find Apple revenue data"
        assert result[0] > 0, "Apple revenue should be positive"

    def test_get_db_caches(self):
        """Calling get_db() twice should return the same connection."""
        con1 = get_db()
        con2 = get_db()
        assert con1 is con2
