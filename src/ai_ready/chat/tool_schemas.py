"""Tool definitions for the Claude API (Anthropic SDK format).

Defines the 7 tools as input_schema JSON Schema objects that Claude
uses to generate valid tool calls.
"""

from __future__ import annotations

TOOL_DEFINITIONS = [
    {
        "name": "get_company_metric",
        "description": (
            "Get a specific financial metric for a company. Use this when the user asks "
            "about a single metric for a single company (e.g., 'What was Apple's revenue in 2024?'). "
            "Returns the value with formatting, YoY change, sector rank, and anomaly flags."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Company ticker symbol (e.g., AAPL, MSFT, BA)",
                },
                "metric": {
                    "type": "string",
                    "description": (
                        "Financial metric name or business term ID. "
                        "Examples: 'Revenue', 'Net Income', 'Total Assets', 'BT-022', 'BT-023'"
                    ),
                },
                "fiscal_year": {
                    "type": "integer",
                    "description": "Fiscal year (e.g., 2024). If omitted, returns the latest available year.",
                },
                "fiscal_period": {
                    "type": "string",
                    "enum": ["FY", "Q1", "Q2", "Q3"],
                    "description": "Fiscal period. Default: FY (full year).",
                },
            },
            "required": ["ticker", "metric"],
        },
    },
    {
        "name": "get_company_profile",
        "description": (
            "Get a full financial profile for a company in a given fiscal year. "
            "Returns all metrics, all ratios, amendment summary, and anomaly flags. "
            "Use this when the user wants a broad overview (e.g., 'Tell me about Apple's FY2024 financials')."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Company ticker symbol",
                },
                "fiscal_year": {
                    "type": "integer",
                    "description": "Fiscal year. If omitted, returns the latest available year.",
                },
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "compare_companies",
        "description": (
            "Compare two companies on financial metrics side by side. "
            "Returns values for both companies, deltas, and a fiscal year alignment warning "
            "if their fiscal years end in different months. "
            "Use this when the user asks to compare two specific companies."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker_a": {
                    "type": "string",
                    "description": "First company ticker",
                },
                "ticker_b": {
                    "type": "string",
                    "description": "Second company ticker",
                },
                "fiscal_year": {
                    "type": "integer",
                    "description": "Fiscal year to compare. If omitted, uses the latest year where both have data.",
                },
                "metrics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Specific metrics to compare. If omitted, compares all shared metrics. "
                        "Examples: ['Revenue', 'Net Income', 'Net Margin']"
                    ),
                },
            },
            "required": ["ticker_a", "ticker_b"],
        },
    },
    {
        "name": "rank_companies",
        "description": (
            "Rank all companies (or a sector) by a specific metric. "
            "Use this when the user asks 'which company has the highest/lowest X?' "
            "or 'rank companies by Y'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "metric": {
                    "type": "string",
                    "description": (
                        "Metric to rank by. Can be a business term name, ID, ratio name, or ratio ID. "
                        "Examples: 'Revenue', 'Net Margin', 'Debt-to-Equity', 'RATIO-003'"
                    ),
                },
                "fiscal_year": {
                    "type": "integer",
                    "description": "Fiscal year. If omitted, uses the latest available.",
                },
                "sector": {
                    "type": "string",
                    "description": "Filter to a specific sector (e.g., 'Technology'). If omitted, ranks all companies.",
                },
                "top_n": {
                    "type": "integer",
                    "description": "Number of top companies to return. If omitted, returns all.",
                },
                "metric_source": {
                    "type": "string",
                    "enum": ["company_financials", "financial_ratios"],
                    "description": "Which table to query. Auto-detected if omitted.",
                },
            },
            "required": ["metric"],
        },
    },
    {
        "name": "get_company_trend",
        "description": (
            "Get a metric's trend over time for a company. "
            "Returns a time series with YoY changes, CAGR, and trend direction. "
            "Use this when the user asks 'how has X changed over time?' or 'show me the trend'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Company ticker symbol",
                },
                "metric": {
                    "type": "string",
                    "description": "Financial metric name or ID",
                },
                "start_year": {
                    "type": "integer",
                    "description": "Start of the time range. If omitted, uses earliest available.",
                },
                "end_year": {
                    "type": "integer",
                    "description": "End of the time range. If omitted, uses latest available.",
                },
            },
            "required": ["ticker", "metric"],
        },
    },
    {
        "name": "get_sector_summary",
        "description": (
            "Get a summary of a sector's financial performance. "
            "Returns the companies in the sector, averages, medians, leaders, and laggards. "
            "Use this when the user asks about a sector overall."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sector": {
                    "type": "string",
                    "description": (
                        "Sector name. Available sectors: Technology, Healthcare, Financials, "
                        "Consumer Staples, Consumer Discretionary, Energy, Industrials, "
                        "Communication Services"
                    ),
                },
                "fiscal_year": {
                    "type": "integer",
                    "description": "Fiscal year. If omitted, uses the latest available.",
                },
                "metric": {
                    "type": "string",
                    "description": (
                        "Specific metric to summarize. If omitted, summarizes Revenue, "
                        "Net Income, and Net Margin."
                    ),
                },
            },
            "required": ["sector"],
        },
    },
    {
        "name": "get_ratio",
        "description": (
            "Get a financial ratio with its component breakdown (numerator and denominator). "
            "Use this when the user asks about a specific ratio like 'What is Apple's debt-to-equity ratio?' "
            "Returns the ratio value, its components, sector rank, and anomaly flags."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Company ticker symbol",
                },
                "ratio": {
                    "type": "string",
                    "description": (
                        "Ratio name or ID. Available ratios: 'Gross Margin', 'Operating Margin', "
                        "'Net Margin', 'Debt-to-Equity', 'R&D Intensity', 'SGA Ratio', "
                        "'CapEx-to-Revenue', or RATIO-001 through RATIO-007"
                    ),
                },
                "fiscal_year": {
                    "type": "integer",
                    "description": "Fiscal year. If omitted, returns the latest available.",
                },
            },
            "required": ["ticker", "ratio"],
        },
    },
    {
        "name": "get_amendment_summary",
        "description": (
            "Get an amendment analysis summary for a company. "
            "Returns how many times a company restated or amended their SEC filings, "
            "what concepts changed, and the magnitude of changes. "
            "Use this when the user asks about restatements, amendments, or filing corrections."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Company ticker symbol (e.g., AAPL, MSFT, BA)",
                },
                "fiscal_year": {
                    "type": "integer",
                    "description": "Fiscal year. If omitted, returns the latest available year.",
                },
            },
            "required": ["ticker"],
        },
    },
]


def get_tool_definitions() -> list[dict]:
    """Return the tool definitions list for the Anthropic API."""
    return TOOL_DEFINITIONS
