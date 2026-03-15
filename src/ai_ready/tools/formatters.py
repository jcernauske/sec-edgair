"""Number formatting for financial data.

All tool responses include both raw values and formatted strings:
  >= 1 trillion  -> $X.XT
  >= 1 billion   -> $X.XB
  >= 1 million   -> $X.XM
  >= 1 thousand  -> $X.XK
  < 1 thousand   -> $X.XX
  Ratios/margins -> X.X%
  Per-share      -> $X.XX
  Negative       -> ($X.XB)
"""

from __future__ import annotations


def format_currency(value: float | None) -> str:
    """Format a USD value with appropriate scale suffix.

    Returns formatted string like "$394.3B", "($1.2B)", "$97.0M".
    Negative values use parentheses: ($X.XB).
    """
    if value is None:
        return "N/A"

    negative = value < 0
    abs_val = abs(value)

    if abs_val >= 1_000_000_000_000:
        formatted = f"${abs_val / 1_000_000_000_000:.1f}T"
    elif abs_val >= 1_000_000_000:
        formatted = f"${abs_val / 1_000_000_000:.1f}B"
    elif abs_val >= 1_000_000:
        formatted = f"${abs_val / 1_000_000:.1f}M"
    elif abs_val >= 1_000:
        formatted = f"${abs_val / 1_000:.1f}K"
    else:
        formatted = f"${abs_val:.2f}"

    if negative:
        # Strip the $ and wrap in parens with $
        return f"({formatted})"

    return formatted


def format_percentage(value: float | None) -> str:
    """Format a ratio/margin value as a percentage.

    Input is a decimal ratio (0.253 -> "25.3%").
    """
    if value is None:
        return "N/A"

    pct = value * 100
    if pct < 0:
        return f"({abs(pct):.1f}%)"
    return f"{pct:.1f}%"


def format_per_share(value: float | None) -> str:
    """Format a per-share value.

    Returns "$X.XX" or "($X.XX)" for negative.
    """
    if value is None:
        return "N/A"

    if value < 0:
        return f"(${abs(value):.2f})"
    return f"${value:.2f}"


def format_ratio(value: float | None) -> str:
    """Format a raw ratio (not percentage-based).

    Used for ratios like Debt-to-Equity where the value is a multiplier, not a percentage.
    Returns "X.Xx" format.
    """
    if value is None:
        return "N/A"

    if value < 0:
        return f"({abs(value):.1f}x)"
    return f"{value:.1f}x"


def format_yoy_pct(value: float | None) -> str:
    """Format a year-over-year percentage change.

    Input is a decimal (0.078 -> "+7.8%").
    """
    if value is None:
        return "N/A"

    pct = value * 100
    sign = "+" if pct > 0 else ""
    return f"{sign}{pct:.1f}%"


def format_value(value: float | None, unit: str | None = None, metric_type: str | None = None) -> str:
    """Format a value based on its unit or metric type.

    Args:
        value: The numeric value to format.
        unit: The unit from the data (e.g., "USD", "USD/shares", "ratio", "percentage").
        metric_type: Optional type hint ("currency", "per_share", "ratio", "percentage").

    Returns:
        Formatted string appropriate for the value type.
    """
    if value is None:
        return "N/A"

    # Determine format from unit
    if unit == "USD/shares" or metric_type == "per_share":
        return format_per_share(value)
    elif unit == "ratio" or metric_type == "ratio":
        return format_ratio(value)
    elif unit == "percentage" or metric_type == "percentage":
        return format_percentage(value)
    elif unit == "USD" or metric_type == "currency":
        return format_currency(value)

    # Default: try currency for large values, raw for small
    if abs(value) >= 1000:
        return format_currency(value)
    elif abs(value) < 1 and abs(value) > 0:
        # Likely a ratio
        return format_percentage(value)
    else:
        return f"{value:,.2f}"
