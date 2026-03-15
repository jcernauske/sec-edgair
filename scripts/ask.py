"""Direct tool query runner — no API key needed.

Usage: PYTHONPATH=. uv run python scripts/ask.py <tool> [args...]

Examples:
  PYTHONPATH=. uv run python scripts/ask.py metric AAPL Revenue 2024
  PYTHONPATH=. uv run python scripts/ask.py profile AAPL 2024
  PYTHONPATH=. uv run python scripts/ask.py compare AAPL MSFT 2024
  PYTHONPATH=. uv run python scripts/ask.py rank "Net Margin" 2024
  PYTHONPATH=. uv run python scripts/ask.py trend AAPL Revenue
  PYTHONPATH=. uv run python scripts/ask.py sector Technology 2024
  PYTHONPATH=. uv run python scripts/ask.py ratio AAPL "Net Margin" 2024
"""
import json
import sys

from src.ai_ready.tools.financial_tools import (
    get_company_metric,
    get_company_profile,
    compare_companies,
    rank_companies,
    get_company_trend,
    get_sector_summary,
    get_ratio,
)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    tool = sys.argv[1]
    args = sys.argv[2:]

    if tool == "metric" and len(args) >= 2:
        result = get_company_metric(args[0], args[1], fiscal_year=int(args[2]) if len(args) > 2 else None)
    elif tool == "profile" and len(args) >= 1:
        result = get_company_profile(args[0], fiscal_year=int(args[1]) if len(args) > 1 else None)
    elif tool == "compare" and len(args) >= 2:
        result = compare_companies(args[0], args[1], fiscal_year=int(args[2]) if len(args) > 2 else None)
    elif tool == "rank" and len(args) >= 1:
        result = rank_companies(args[0], fiscal_year=int(args[1]) if len(args) > 1 else None)
    elif tool == "trend" and len(args) >= 2:
        result = get_company_trend(args[0], args[1])
    elif tool == "sector" and len(args) >= 1:
        result = get_sector_summary(args[0], fiscal_year=int(args[1]) if len(args) > 1 else None)
    elif tool == "ratio" and len(args) >= 2:
        result = get_ratio(args[0], args[1], fiscal_year=int(args[2]) if len(args) > 2 else None)
    else:
        print(__doc__)
        sys.exit(1)

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
