"""Unit tests for anomaly checker.

Pure unit tests — no Iceberg or DB required.
"""

from src.ai_ready.tools.anomaly_checker import check_anomalies, check_fiscal_alignment


class TestCheckAnomalies:
    """Tests for check_anomalies."""

    def test_no_anomalies_normal_values(self):
        flags = check_anomalies(
            ticker="AAPL", metric="Revenue", value=394_000_000_000,
            yoy_pct=0.08, sector="Technology",
        )
        assert flags == []

    def test_extreme_yoy_positive(self):
        flags = check_anomalies(
            ticker="AAPL", metric="Revenue", value=100_000_000,
            yoy_pct=3.5,
        )
        assert len(flags) == 1
        assert "Unusually large year-over-year change" in flags[0]
        assert "350%" in flags[0]

    def test_extreme_yoy_negative(self):
        flags = check_anomalies(
            ticker="AAPL", metric="Revenue", value=100_000_000,
            yoy_pct=-2.5,
        )
        assert len(flags) == 1
        assert "Unusually large year-over-year change" in flags[0]

    def test_yoy_exactly_200_not_triggered(self):
        """200% exactly should not trigger (> 2.0, not >=)."""
        flags = check_anomalies(
            ticker="AAPL", metric="Revenue", value=100_000_000,
            yoy_pct=2.0,
        )
        assert flags == []

    def test_boeing_negative_equity(self):
        flags = check_anomalies(
            ticker="BA", metric="Stockholders Equity", value=-5_000_000_000,
        )
        assert len(flags) == 1
        assert "Negative stockholders equity" in flags[0]

    def test_any_company_negative_equity_flagged(self):
        """Any company with negative equity should be flagged, not just Boeing."""
        flags = check_anomalies(
            ticker="AAPL", metric="Stockholders Equity", value=-5_000_000_000,
        )
        assert len(flags) == 1
        assert "Negative stockholders equity" in flags[0]

    def test_positive_equity_no_flag(self):
        flags = check_anomalies(
            ticker="AAPL", metric="Stockholders Equity", value=50_000_000_000,
        )
        assert not any("Negative stockholders equity" in f for f in flags)

    def test_extreme_debt_to_equity(self):
        flags = check_anomalies(
            ticker="BA", metric="Debt-to-Equity", value=75.0,
            ratio_name="Debt-to-Equity",
        )
        assert any("Extreme leverage ratio" in f for f in flags)

    def test_normal_debt_to_equity_no_flag(self):
        flags = check_anomalies(
            ticker="AAPL", metric="Debt-to-Equity", value=1.5,
            ratio_name="Debt-to-Equity",
        )
        assert not any("Extreme leverage ratio" in f for f in flags)

    def test_negative_revenue(self):
        flags = check_anomalies(
            ticker="XYZ", metric="Revenue", value=-100_000,
        )
        assert any("Data quality anomaly" in f for f in flags)

    def test_pre_profitability(self):
        flags = check_anomalies(
            ticker="TSLA", metric="Net Income", value=-500_000_000,
            net_margin=-1.5,
        )
        assert any("Pre-profitability" in f for f in flags)

    def test_financial_sector_gross_margin(self):
        flags = check_anomalies(
            ticker="JPM", metric="Gross Margin", value=0.5,
            sector="Financials",
        )
        assert any("Financial institutions" in f for f in flags)

    def test_financial_sector_operating_margin(self):
        flags = check_anomalies(
            ticker="GS", metric="Operating Margin", value=0.3,
            sector="Financials",
        )
        assert any("Financial institutions" in f for f in flags)

    def test_none_value_returns_empty(self):
        flags = check_anomalies(ticker="AAPL", metric="Revenue", value=None)
        assert flags == []

    def test_multiple_flags(self):
        """Any company with negative equity AND extreme YoY should get both flags."""
        flags = check_anomalies(
            ticker="BA",
            metric="Stockholders Equity",
            value=-5_000_000_000,
            yoy_pct=3.0,
        )
        assert len(flags) >= 2


class TestCheckFiscalAlignment:
    """Tests for check_fiscal_alignment."""

    def test_aligned_december(self):
        result = check_fiscal_alignment("AAPL", "1231", "MSFT", "1231")
        assert result is None

    def test_misaligned_apple_microsoft(self):
        # Apple ends Sep (0930), Microsoft ends Jun (0630) — should warn
        result = check_fiscal_alignment("AAPL", "0928", "MSFT", "0630")
        assert result is not None
        assert "AAPL" in result
        assert "MSFT" in result
        assert "Fiscal year ends differ" in result

    def test_close_enough_no_warning(self):
        # Same month — within 30 days
        result = check_fiscal_alignment("A", "1231", "B", "1228")
        assert result is None

    def test_none_fy_end(self):
        result = check_fiscal_alignment("AAPL", None, "MSFT", "0630")
        assert result is None

    def test_both_none(self):
        result = check_fiscal_alignment("A", None, "B", None)
        assert result is None
