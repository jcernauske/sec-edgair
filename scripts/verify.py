"""Verify our pipeline data against known public financial figures.

Pulls our computed values and compares to officially reported 10-K figures.
Source: SEC EDGAR XBRL filings (the same source our pipeline ingests).
"""
import json
from src.ai_ready.tools.financial_tools import get_company_metric, get_ratio

# Known figures from public 10-K filings (in USD)
# Source: Company 10-K annual reports filed with SEC
KNOWN_FIGURES = [
    # ===== APPLE (FY ends Sep) =====
    {"ticker": "AAPL", "metric": "Revenue", "fy": 2024, "expected": 391_035_000_000, "source": "Apple 10-K FY2024"},
    {"ticker": "AAPL", "metric": "Net Income", "fy": 2024, "expected": 93_736_000_000, "source": "Apple 10-K FY2024"},
    {"ticker": "AAPL", "metric": "Revenue", "fy": 2023, "expected": 383_285_000_000, "source": "Apple 10-K FY2023"},
    {"ticker": "AAPL", "metric": "Net Income", "fy": 2023, "expected": 96_995_000_000, "source": "Apple 10-K FY2023"},
    {"ticker": "AAPL", "metric": "Total Assets", "fy": 2023, "expected": 352_583_000_000, "source": "Apple 10-K FY2023"},
    {"ticker": "AAPL", "metric": "Earnings Per Share Diluted", "fy": 2023, "expected": 6.13, "source": "Apple 10-K FY2023"},
    {"ticker": "AAPL", "metric": "Operating Cash Flow", "fy": 2023, "expected": 110_543_000_000, "source": "Apple 10-K FY2023"},

    # ===== MICROSOFT (FY ends Jun) =====
    {"ticker": "MSFT", "metric": "Revenue", "fy": 2024, "expected": 245_122_000_000, "source": "Microsoft 10-K FY2024"},
    {"ticker": "MSFT", "metric": "Net Income", "fy": 2024, "expected": 88_136_000_000, "source": "Microsoft 10-K FY2024"},
    {"ticker": "MSFT", "metric": "Operating Income", "fy": 2024, "expected": 109_433_000_000, "source": "Microsoft 10-K FY2024"},
    {"ticker": "MSFT", "metric": "Total Assets", "fy": 2024, "expected": 512_163_000_000, "source": "Microsoft 10-K FY2024"},
    {"ticker": "MSFT", "metric": "Earnings Per Share Diluted", "fy": 2024, "expected": 11.80, "source": "Microsoft 10-K FY2024"},

    # ===== AMAZON (FY ends Dec) =====
    {"ticker": "AMZN", "metric": "Revenue", "fy": 2023, "expected": 574_785_000_000, "source": "Amazon 10-K FY2023"},
    {"ticker": "AMZN", "metric": "Net Income", "fy": 2023, "expected": 30_425_000_000, "source": "Amazon 10-K FY2023"},
    {"ticker": "AMZN", "metric": "Total Assets", "fy": 2023, "expected": 527_854_000_000, "source": "Amazon 10-K FY2023"},
    {"ticker": "AMZN", "metric": "Operating Cash Flow", "fy": 2023, "expected": 84_946_000_000, "source": "Amazon 10-K FY2023"},

    # ===== ALPHABET/GOOGLE (FY ends Dec) =====
    {"ticker": "GOOGL", "metric": "Revenue", "fy": 2023, "expected": 307_394_000_000, "source": "Alphabet 10-K FY2023"},
    {"ticker": "GOOGL", "metric": "Net Income", "fy": 2023, "expected": 73_795_000_000, "source": "Alphabet 10-K FY2023"},
    {"ticker": "GOOGL", "metric": "Operating Income", "fy": 2023, "expected": 84_293_000_000, "source": "Alphabet 10-K FY2023"},
    {"ticker": "GOOGL", "metric": "Total Assets", "fy": 2023, "expected": 402_392_000_000, "source": "Alphabet 10-K FY2023"},

    # ===== META (FY ends Dec) =====
    {"ticker": "META", "metric": "Revenue", "fy": 2023, "expected": 134_902_000_000, "source": "Meta 10-K FY2023"},
    {"ticker": "META", "metric": "Net Income", "fy": 2023, "expected": 39_098_000_000, "source": "Meta 10-K FY2023"},
    {"ticker": "META", "metric": "Total Assets", "fy": 2023, "expected": 229_623_000_000, "source": "Meta 10-K FY2023"},

    # ===== TESLA (FY ends Dec) =====
    {"ticker": "TSLA", "metric": "Revenue", "fy": 2023, "expected": 96_773_000_000, "source": "Tesla 10-K FY2023"},
    {"ticker": "TSLA", "metric": "Net Income", "fy": 2023, "expected": 14_997_000_000, "source": "Tesla 10-K FY2023"},
    {"ticker": "TSLA", "metric": "Total Assets", "fy": 2023, "expected": 106_618_000_000, "source": "Tesla 10-K FY2023"},
    {"ticker": "TSLA", "metric": "Capital Expenditures", "fy": 2023, "expected": 8_877_000_000, "source": "Tesla 10-K FY2023"},

    # ===== JPMORGAN (FY ends Dec) =====
    {"ticker": "JPM", "metric": "Revenue", "fy": 2023, "expected": 158_104_000_000, "source": "JPM 10-K FY2023"},
    {"ticker": "JPM", "metric": "Net Income", "fy": 2023, "expected": 49_552_000_000, "source": "JPM 10-K FY2023"},
    {"ticker": "JPM", "metric": "Total Assets", "fy": 2023, "expected": 3_875_393_000_000, "source": "JPM 10-K FY2023"},

    # ===== BOEING (FY ends Dec) — negative equity =====
    {"ticker": "BA", "metric": "Revenue", "fy": 2023, "expected": 77_794_000_000, "source": "Boeing 10-K FY2023"},
    {"ticker": "BA", "metric": "Net Income", "fy": 2023, "expected": -2_222_000_000, "source": "Boeing 10-K FY2023"},
    {"ticker": "BA", "metric": "Total Stockholders Equity", "fy": 2023, "expected": -17_233_000_000, "source": "Boeing 10-K FY2023"},
    {"ticker": "BA", "metric": "Operating Cash Flow", "fy": 2023, "expected": 5_960_000_000, "source": "Boeing 10-K FY2023"},

    # ===== WALMART (FY ends Jan 31) — tricky FY alignment =====
    {"ticker": "WMT", "metric": "Revenue", "fy": 2024, "expected": 648_125_000_000, "source": "Walmart 10-K FY2024 (ends Jan 31, 2024)"},
    {"ticker": "WMT", "metric": "Net Income", "fy": 2024, "expected": 15_511_000_000, "source": "Walmart 10-K FY2024"},
    {"ticker": "WMT", "metric": "Total Assets", "fy": 2024, "expected": 252_399_000_000, "source": "Walmart 10-K FY2024"},

    # ===== VISA (FY ends Sep) =====
    {"ticker": "V", "metric": "Revenue", "fy": 2023, "expected": 32_653_000_000, "source": "Visa 10-K FY2023 (ends Sep 30, 2023)"},
    {"ticker": "V", "metric": "Net Income", "fy": 2023, "expected": 17_273_000_000, "source": "Visa 10-K FY2023"},

    # ===== COCA-COLA (FY ends Dec) =====
    {"ticker": "KO", "metric": "Revenue", "fy": 2023, "expected": 45_754_000_000, "source": "Coca-Cola 10-K FY2023"},
    {"ticker": "KO", "metric": "Net Income", "fy": 2023, "expected": 10_714_000_000, "source": "Coca-Cola 10-K FY2023"},

    # ===== PROCTER & GAMBLE (FY ends Jun) =====
    {"ticker": "PG", "metric": "Revenue", "fy": 2024, "expected": 84_039_000_000, "source": "P&G 10-K FY2024 (ends Jun 30, 2024)"},
    {"ticker": "PG", "metric": "Net Income", "fy": 2024, "expected": 14_993_000_000, "source": "P&G 10-K FY2024"},

    # ===== NETFLIX (FY ends Dec) =====
    {"ticker": "NFLX", "metric": "Revenue", "fy": 2023, "expected": 33_723_000_000, "source": "Netflix 10-K FY2023"},
    {"ticker": "NFLX", "metric": "Net Income", "fy": 2023, "expected": 5_408_000_000, "source": "Netflix 10-K FY2023"},

    # ===== INTEL (FY ends Dec) =====
    {"ticker": "INTC", "metric": "Revenue", "fy": 2023, "expected": 54_228_000_000, "source": "Intel 10-K FY2023"},
    {"ticker": "INTC", "metric": "Net Income", "fy": 2023, "expected": 1_689_000_000, "source": "Intel 10-K FY2023"},

    # ===== EXXON MOBIL (FY ends Dec) =====
    {"ticker": "XOM", "metric": "Revenue", "fy": 2023, "expected": 344_582_000_000, "source": "Exxon 10-K FY2023"},
    {"ticker": "XOM", "metric": "Net Income", "fy": 2023, "expected": 36_010_000_000, "source": "Exxon 10-K FY2023"},

    # ===== UNITEDHEALTH (FY ends Dec) =====
    {"ticker": "UNH", "metric": "Revenue", "fy": 2023, "expected": 371_622_000_000, "source": "UNH 10-K FY2023"},
    {"ticker": "UNH", "metric": "Net Income", "fy": 2023, "expected": 22_381_000_000, "source": "UNH 10-K FY2023"},

    # ===== PFIZER (FY ends Dec) =====
    {"ticker": "PFE", "metric": "Revenue", "fy": 2023, "expected": 58_496_000_000, "source": "Pfizer 10-K FY2023"},
    {"ticker": "PFE", "metric": "Net Income", "fy": 2023, "expected": 2_119_000_000, "source": "Pfizer 10-K FY2023"},

    # ===== JOHNSON & JOHNSON (FY ends Dec) =====
    {"ticker": "JNJ", "metric": "Revenue", "fy": 2023, "expected": 85_159_000_000, "source": "J&J 10-K FY2023"},
    {"ticker": "JNJ", "metric": "Net Income", "fy": 2023, "expected": 35_153_000_000, "source": "J&J 10-K FY2023"},

    # ===== GOLDMAN SACHS (FY ends Dec) =====
    {"ticker": "GS", "metric": "Revenue", "fy": 2023, "expected": 46_254_000_000, "source": "GS 10-K FY2023"},
    {"ticker": "GS", "metric": "Net Income", "fy": 2023, "expected": 8_516_000_000, "source": "GS 10-K FY2023"},
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
