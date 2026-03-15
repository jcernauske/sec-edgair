"""Anomaly flag rules computed at query time.

Flags are generated from known rules, not stored in Iceberg. Each rule
checks a condition and returns a human-readable flag string when triggered.
"""

from __future__ import annotations

import datetime


def check_anomalies(
    *,
    ticker: str | None = None,
    metric: str | None = None,
    value: float | None = None,
    yoy_pct: float | None = None,
    sector: str | None = None,
    ratio_name: str | None = None,
    net_margin: float | None = None,
) -> list[str]:
    """Check a data point against known anomaly rules.

    Returns a list of flag strings for any triggered rules. Empty list = no anomalies.
    """
    flags: list[str] = []

    if value is None:
        return flags

    # Rule 1: Extreme YoY change (|yoy_pct| > 2.0 = 200%)
    if yoy_pct is not None and abs(yoy_pct) > 2.0:
        pct_display = f"{abs(yoy_pct) * 100:.0f}"
        flags.append(
            f"Unusually large year-over-year change ({pct_display}%). "
            f"May reflect M&A, reclassification, or one-time event."
        )

    # Rule 2: Negative stockholders equity (Boeing-specific known issue)
    if (
        ticker == "BA"
        and metric is not None
        and "stockholders equity" in metric.lower()
        and value < 0
    ):
        flags.append(
            "Negative stockholders equity. Debt-to-equity ratio reflects "
            "negative equity denominator, not extreme debt."
        )

    # Rule 3: Extreme D/E ratio (> 50x)
    if ratio_name is not None and "debt" in ratio_name.lower() and "equity" in ratio_name.lower():
        if abs(value) > 50:
            flags.append(
                f"Extreme leverage ratio ({value:.1f}x) driven by near-zero "
                f"or negative equity denominator."
            )

    # Rule 4: Negative revenue
    if metric is not None and "revenue" in metric.lower() and value < 0:
        flags.append(
            "Data quality anomaly in source XBRL filing. Exercise caution."
        )

    # Rule 5: Pre-profitability (Net Margin < -1.0 = -100%)
    if net_margin is not None and net_margin < -1.0:
        flags.append(
            "Pre-profitability period. Operating losses exceeded revenue."
        )

    # Rule 6: Financial sector missing ratios
    if (
        sector == "Financials"
        and metric is not None
        and any(m in metric.lower() for m in ["gross margin", "operating margin"])
    ):
        flags.append(
            "Financial institutions use different P&L structures. "
            "This metric is not applicable."
        )

    return flags


def check_fiscal_alignment(
    ticker_a: str,
    fy_end_a: str | None,
    ticker_b: str,
    fy_end_b: str | None,
) -> str | None:
    """Check if two companies have misaligned fiscal year ends.

    Returns a warning string if fiscal year ends differ by more than 30 days,
    or None if aligned (or data is missing).
    """
    if fy_end_a is None or fy_end_b is None:
        return None

    # fiscal_year_end is typically "MMDD" format (e.g., "0930" for Sep 30)
    try:
        # Parse MMDD format
        if len(fy_end_a) == 4 and len(fy_end_b) == 4:
            month_a, day_a = int(fy_end_a[:2]), int(fy_end_a[2:])
            month_b, day_b = int(fy_end_b[:2]), int(fy_end_b[2:])

            # Use a reference year to compute day difference
            date_a = datetime.date(2024, month_a, min(day_a, 28))
            date_b = datetime.date(2024, month_b, min(day_b, 28))

            diff_days = abs((date_a - date_b).days)

            # Handle wrap-around (e.g., Jan vs Dec)
            if diff_days > 182:
                diff_days = 365 - diff_days

            if diff_days > 30:
                end_a_str = date_a.strftime("%b %d")
                end_b_str = date_b.strftime("%b %d")
                return (
                    f"Fiscal year ends differ: {ticker_a} ({end_a_str}) vs "
                    f"{ticker_b} ({end_b_str}). Comparison covers different "
                    f"calendar periods."
                )
    except (ValueError, TypeError):
        pass

    return None
