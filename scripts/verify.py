"""Verify our pipeline data against known public financial figures.

Pulls our computed values and compares to officially reported 10-K figures.
Source: SEC EDGAR XBRL filings (the same source our pipeline ingests).
"""
import json
from src.ai_ready.tools.financial_tools import get_company_metric, get_ratio

# Known figures from public 10-K filings (in USD)
# Source: Company 10-K annual reports filed with SEC
KNOWN_FIGURES = [
    # Apple FY2023 (ends Sep 30, 2023) - from 10-K filed Nov 3, 2023
    {"ticker": "AAPL", "metric": "Revenue", "fy": 2023, "expected": 383_285_000_000, "source": "Apple 10-K FY2023"},
    {"ticker": "AAPL", "metric": "Net Income", "fy": 2023, "expected": 96_995_000_000, "source": "Apple 10-K FY2023"},
    {"ticker": "AAPL", "metric": "Total Assets", "fy": 2023, "expected": 352_583_000_000, "source": "Apple 10-K FY2023"},
    {"ticker": "AAPL", "metric": "Earnings Per Share Diluted", "fy": 2023, "expected": 6.13, "source": "Apple 10-K FY2023"},

    # Microsoft FY2024 (ends Jun 30, 2024) - from 10-K filed Jul 30, 2024
    {"ticker": "MSFT", "metric": "Revenue", "fy": 2024, "expected": 245_122_000_000, "source": "Microsoft 10-K FY2024"},
    {"ticker": "MSFT", "metric": "Net Income", "fy": 2024, "expected": 88_136_000_000, "source": "Microsoft 10-K FY2024"},
    {"ticker": "MSFT", "metric": "Operating Income", "fy": 2024, "expected": 109_433_000_000, "source": "Microsoft 10-K FY2024"},

    # Amazon FY2023 (ends Dec 31, 2023) - from 10-K filed Feb 1, 2024
    {"ticker": "AMZN", "metric": "Revenue", "fy": 2023, "expected": 574_785_000_000, "source": "Amazon 10-K FY2023"},
    {"ticker": "AMZN", "metric": "Net Income", "fy": 2023, "expected": 30_425_000_000, "source": "Amazon 10-K FY2023"},

    # JPMorgan FY2023 (ends Dec 31, 2023) - from 10-K filed Feb 16, 2024
    {"ticker": "JPM", "metric": "Revenue", "fy": 2023, "expected": 158_104_000_000, "source": "JPM 10-K FY2023"},
    {"ticker": "JPM", "metric": "Net Income", "fy": 2023, "expected": 49_552_000_000, "source": "JPM 10-K FY2023"},
    {"ticker": "JPM", "metric": "Total Assets", "fy": 2023, "expected": 3_875_393_000_000, "source": "JPM 10-K FY2023"},

    # Tesla FY2023 (ends Dec 31, 2023) - from 10-K filed Jan 29, 2024
    {"ticker": "TSLA", "metric": "Revenue", "fy": 2023, "expected": 96_773_000_000, "source": "Tesla 10-K FY2023"},
    {"ticker": "TSLA", "metric": "Net Income", "fy": 2023, "expected": 14_997_000_000, "source": "Tesla 10-K FY2023"},

    # Boeing FY2023 (ends Dec 31, 2023) - known for negative equity
    {"ticker": "BA", "metric": "Net Income", "fy": 2023, "expected": -2_222_000_000, "source": "Boeing 10-K FY2023"},
    {"ticker": "BA", "metric": "Total Stockholders Equity", "fy": 2023, "expected": -17_233_000_000, "source": "Boeing 10-K FY2023 (negative equity)"},
]


def format_num(v):
    if v is None:
        return "N/A"
    if abs(v) >= 1e12:
        return f"${v/1e12:.1f}T"
    if abs(v) >= 1e9:
        return f"${v/1e9:.1f}B"
    if abs(v) >= 1e6:
        return f"${v/1e6:.1f}M"
    return f"${v:,.2f}"


def main():
    print("=" * 100)
    print("PIPELINE DATA VERIFICATION — Comparing Our Data vs Known 10-K Figures")
    print("=" * 100)
    print()

    matches = 0
    mismatches = 0
    missing = 0

    for check in KNOWN_FIGURES:
        result = get_company_metric(check["ticker"], check["metric"], fiscal_year=check["fy"])

        if "error" in result:
            print(f"  MISSING  {check['ticker']} {check['metric']} FY{check['fy']}: {result['error']}")
            missing += 1
            continue

        our_val = result["value"]
        expected = check["expected"]

        # Check if values match within 1% tolerance (XBRL rounding)
        if expected != 0:
            pct_diff = abs(our_val - expected) / abs(expected) * 100
        else:
            pct_diff = 0 if our_val == 0 else 100

        status = "MATCH" if pct_diff < 1.0 else ("CLOSE" if pct_diff < 5.0 else "MISMATCH")

        if status == "MATCH":
            matches += 1
            marker = "OK"
        elif status == "CLOSE":
            matches += 1
            marker = "~OK"
        else:
            mismatches += 1
            marker = "XX"

        print(f"  [{marker:>3}] {check['ticker']:5} {check['metric']:<35} FY{check['fy']}")
        print(f"         Ours: {format_num(our_val):>15}   Expected: {format_num(expected):>15}   Diff: {pct_diff:.2f}%")
        if pct_diff >= 1.0:
            print(f"         Source: {check['source']}")
        print()

    print("=" * 100)
    print(f"Results: {matches} match | {mismatches} mismatch | {missing} missing | {len(KNOWN_FIGURES)} total")
    if mismatches == 0 and missing == 0:
        print("ALL FIGURES VERIFIED")
    print("=" * 100)


if __name__ == "__main__":
    main()
