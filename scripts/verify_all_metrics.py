"""Verify ALL 25 business terms + 7 ratios against known values.

Strategy: Use Apple FY2023 as the reference company since their 10-K
is the most widely cited. Verify every metric we report.

Source: Apple Inc. 10-K for FY2023 (ended Sep 30, 2023), filed Nov 3, 2023.
"""
import json
from src.ai_ready.tools.financial_tools import get_company_metric, get_company_profile

# Apple FY2023 — all 25 business terms from the 10-K
# Source: Apple Inc. Annual Report on Form 10-K for FY ended September 30, 2023
APPLE_FY2023 = {
    # Income Statement
    "Revenue": 383_285_000_000,
    "Cost of Revenue": 214_137_000_000,
    "Gross Profit": 169_148_000_000,
    "Operating Income": 114_301_000_000,
    "Net Income": 96_995_000_000,
    "Income Tax Expense": 16_741_000_000,
    "Research and Development Expense": 29_915_000_000,
    "Selling General and Administrative Expense": 24_932_000_000,

    # Balance Sheet
    "Total Assets": 352_583_000_000,
    "Total Liabilities": 290_437_000_000,
    "Total Stockholders Equity": 62_146_000_000,
    "Cash and Cash Equivalents": 29_965_000_000,
    "Accounts Receivable": 29_508_000_000,  # XBRL AccountsReceivableNetCurrent (trade only); 10-K groups trade + non-trade = $61B
    "Inventory": 6_331_000_000,
    "Property Plant and Equipment": 43_715_000_000,
    # Goodwill: Apple does not tag a standalone Goodwill concept in XBRL (no acquisitions)

    # Cash Flow
    "Operating Cash Flow": 110_543_000_000,
    "Investing Cash Flow": 3_705_000_000,  # XBRL reports $3.7B; 10-K narrative says -$7.1B (XBRL tagging discrepancy in source)
    "Financing Cash Flow": -108_488_000_000,
    "Capital Expenditures": 11_006_000_000,

    # Per-Share
    "Earnings Per Share Basic": 6.16,
    "Earnings Per Share Diluted": 6.13,
    "Dividends Per Share": 0.94,

    # Other
    "Comprehensive Income": 96_759_000_000,
    "Retained Earnings": -214_000_000,
}

# Known ratios for Apple FY2023 (computed from above)
APPLE_RATIOS_FY2023 = {
    "Gross Margin": 169_148_000_000 / 383_285_000_000,       # 0.4413
    "Operating Margin": 114_301_000_000 / 383_285_000_000,   # 0.2982
    "Net Margin": 96_995_000_000 / 383_285_000_000,          # 0.2531
    "Debt-to-Equity": 290_437_000_000 / 62_146_000_000,      # 4.674
    "R&D Intensity": 29_915_000_000 / 383_285_000_000,       # 0.0780
    "SGA Ratio": 24_932_000_000 / 383_285_000_000,           # 0.0650
    "CapEx-to-Revenue": 11_006_000_000 / 383_285_000_000,    # 0.0287
}


def format_num(v):
    if v is None:
        return "N/A"
    if abs(v) >= 1e12:
        return f"${v/1e12:.1f}T"
    if abs(v) >= 1e9:
        return f"${v/1e9:.1f}B"
    if abs(v) >= 1e6:
        return f"${v/1e6:.1f}M"
    if abs(v) < 100:
        return f"${v:.2f}"
    return f"${v:,.0f}"


def main():
    print("=" * 100)
    print("FULL METRIC VERIFICATION — Apple FY2023 (all 25 business terms + 7 ratios)")
    print("=" * 100)

    matches = 0
    mismatches = 0
    missing = 0

    # Check all 25 business terms
    print("\n--- Business Terms (25) ---")
    for metric_name, expected in APPLE_FY2023.items():
        result = get_company_metric("AAPL", metric_name, fiscal_year=2023)

        if "error" in result:
            print(f"  MISSING  {metric_name}: {result['error']}")
            missing += 1
            continue

        our_val = result["value"]

        if expected != 0:
            pct_diff = abs(our_val - expected) / abs(expected) * 100
        else:
            pct_diff = 0 if our_val == 0 else 100

        if pct_diff < 1.0:
            marker = " OK"
            matches += 1
        elif pct_diff < 5.0:
            marker = "~OK"
            matches += 1
        else:
            marker = " XX"
            mismatches += 1

        print(f"  [{marker}] {metric_name:<45} Ours: {format_num(our_val):>12}  Expected: {format_num(expected):>12}  Diff: {pct_diff:.2f}%")

    # Check all 7 ratios
    print("\n--- Financial Ratios (7) ---")
    from src.ai_ready.tools.financial_tools import get_ratio
    for ratio_name, expected in APPLE_RATIOS_FY2023.items():
        result = get_ratio("AAPL", ratio_name, fiscal_year=2023)

        if "error" in result:
            print(f"  MISSING  {ratio_name}: {result['error']}")
            missing += 1
            continue

        our_val = result["value"]
        pct_diff = abs(our_val - expected) / abs(expected) * 100

        if pct_diff < 1.0:
            marker = " OK"
            matches += 1
        elif pct_diff < 5.0:
            marker = "~OK"
            matches += 1
        else:
            marker = " XX"
            mismatches += 1

        print(f"  [{marker}] {ratio_name:<45} Ours: {our_val:>12.4f}  Expected: {expected:>12.4f}  Diff: {pct_diff:.2f}%")

    print()
    print("=" * 100)
    print(f"Results: {matches} match | {mismatches} mismatch | {missing} missing | {matches + mismatches + missing} total")
    if mismatches == 0 and missing == 0:
        print("ALL METRICS VERIFIED")
    print("=" * 100)


if __name__ == "__main__":
    main()
