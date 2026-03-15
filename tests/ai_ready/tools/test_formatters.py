"""Unit tests for number formatting.

These are pure unit tests — no Iceberg or DB required.
"""

import pytest

from src.ai_ready.tools.formatters import (
    format_currency,
    format_per_share,
    format_percentage,
    format_ratio,
    format_value,
    format_yoy_pct,
)


class TestFormatCurrency:
    """Tests for format_currency."""

    def test_trillions(self):
        assert format_currency(1_200_000_000_000) == "$1.2T"

    def test_billions(self):
        assert format_currency(394_328_000_000) == "$394.3B"

    def test_billions_small(self):
        assert format_currency(1_500_000_000) == "$1.5B"

    def test_millions(self):
        assert format_currency(97_000_000) == "$97.0M"

    def test_thousands(self):
        assert format_currency(6_500) == "$6.5K"

    def test_small(self):
        assert format_currency(3.50) == "$3.50"

    def test_negative_billions(self):
        assert format_currency(-1_200_000_000) == "($1.2B)"

    def test_negative_millions(self):
        assert format_currency(-97_000_000) == "($97.0M)"

    def test_zero(self):
        assert format_currency(0) == "$0.00"

    def test_none(self):
        assert format_currency(None) == "N/A"


class TestFormatPercentage:
    """Tests for format_percentage."""

    def test_positive(self):
        assert format_percentage(0.253) == "25.3%"

    def test_negative(self):
        assert format_percentage(-0.15) == "(15.0%)"

    def test_small(self):
        assert format_percentage(0.008) == "0.8%"

    def test_large(self):
        assert format_percentage(1.5) == "150.0%"

    def test_zero(self):
        assert format_percentage(0.0) == "0.0%"

    def test_none(self):
        assert format_percentage(None) == "N/A"


class TestFormatPerShare:
    """Tests for format_per_share."""

    def test_positive(self):
        assert format_per_share(6.42) == "$6.42"

    def test_negative(self):
        assert format_per_share(-1.25) == "($1.25)"

    def test_zero(self):
        assert format_per_share(0) == "$0.00"

    def test_none(self):
        assert format_per_share(None) == "N/A"


class TestFormatRatio:
    """Tests for format_ratio."""

    def test_positive(self):
        assert format_ratio(2.5) == "2.5x"

    def test_negative(self):
        assert format_ratio(-3.2) == "(3.2x)"

    def test_none(self):
        assert format_ratio(None) == "N/A"


class TestFormatYoyPct:
    """Tests for format_yoy_pct."""

    def test_positive(self):
        assert format_yoy_pct(0.078) == "+7.8%"

    def test_negative(self):
        assert format_yoy_pct(-0.12) == "-12.0%"

    def test_zero(self):
        assert format_yoy_pct(0.0) == "0.0%"

    def test_none(self):
        assert format_yoy_pct(None) == "N/A"


class TestFormatValue:
    """Tests for format_value with unit detection."""

    def test_usd(self):
        assert format_value(394_328_000_000, unit="USD") == "$394.3B"

    def test_usd_per_share(self):
        assert format_value(6.42, unit="USD/shares") == "$6.42"

    def test_ratio(self):
        assert format_value(2.5, unit="ratio") == "2.5x"

    def test_percentage(self):
        assert format_value(0.253, unit="percentage") == "25.3%"

    def test_auto_large_value(self):
        # No unit specified, large value -> currency
        assert format_value(5_000_000_000) == "$5.0B"

    def test_auto_small_decimal(self):
        # No unit specified, small decimal -> percentage
        assert format_value(0.15) == "15.0%"

    def test_none(self):
        assert format_value(None) == "N/A"
