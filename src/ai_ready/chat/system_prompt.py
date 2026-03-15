"""System prompt generation for the SEC EDGAIR financial chat agent.

The system prompt (~3,000 tokens) includes:
1. Company roster — 20 companies with ticker, name, sector, fiscal year end
2. Metric catalog — 25 business terms + 7 ratios with brief definitions
3. Known anomalies — Static list of known data quality issues
4. Interpretation guide — "Higher Net Margin = more profitable", etc.
5. Fiscal year alignment rules — Which companies have non-December FY ends
6. Scope declaration — Dataset coverage and limitations
7. Formatting instructions — Always cite specific numbers, always note fiscal year
"""

from __future__ import annotations

import logging

from src.ai_ready.tools.db import get_db
from src.consumable.financial_ratios.config import RATIO_DEFINITIONS

logger = logging.getLogger(__name__)

# Metric interpretation guide (static)
INTERPRETATION_GUIDE = """
## Interpretation Guide
- **Revenue**: Total top-line sales. Higher = larger business.
- **Net Income**: Bottom-line profit after all expenses and taxes. Higher = more profitable.
- **Total Assets**: Everything the company owns. Higher = larger balance sheet.
- **Total Liabilities**: Everything the company owes. Context matters — compare to assets.
- **Stockholders Equity**: Assets minus liabilities. Negative = owes more than it owns (e.g., Boeing).
- **Gross Margin**: (Gross Profit / Revenue). Higher = better cost control on products.
- **Operating Margin**: (Operating Income / Revenue). Higher = better operational efficiency.
- **Net Margin**: (Net Income / Revenue). Higher = more profit per dollar of revenue.
- **Debt-to-Equity**: (Total Liabilities / Stockholders Equity). > 1 means more debt than equity. Extreme values often reflect negative equity, not massive debt.
- **R&D Intensity**: (R&D Expense / Revenue). Higher = more investment in innovation.
- **EPS (Basic/Diluted)**: Earnings per share. Higher = more earnings allocated per share.
- **Operating Cash Flow**: Cash generated from operations. Positive = self-funding.
- **CapEx-to-Revenue**: Capital expenditure as fraction of revenue. Higher = more capital-intensive.
"""

# Known anomalies (static, updated when data changes)
KNOWN_ANOMALIES = """
## Known Data Quality Issues
- **Boeing (BA)**: Negative stockholders equity in multiple years. Debt-to-equity ratio is misleading — driven by negative denominator, not extreme debt.
- **Financial sector** (JPM, GS, BRK-B, V): Gross Margin and Operating Margin are not meaningful for financial institutions — different P&L structure.
- **Fiscal year misalignment**: Apple (Sep), Microsoft (Jun), Nike-style companies have non-December FY ends. Cross-company comparisons for the "same FY" cover different calendar periods.
- **Extreme YoY changes**: Some companies show >200% swings in individual metrics. Usually reflects M&A, accounting reclassification, or one-time events — not organic growth.
- **Negative revenue**: Rare data quality issues in source XBRL filings. Flag and exercise caution.
"""

FORMATTING_INSTRUCTIONS = """
## Response Guidelines
- Always cite specific numbers from tool results. Never guess or hallucinate values.
- Always note the fiscal year when citing data (e.g., "in FY2024").
- When comparing companies, check for fiscal year alignment warnings and mention them.
- Flag anomalies when they appear in tool results.
- Use the formatted values from tool results (e.g., "$394.3B" not "394328000000").
- When a metric is missing for a company, say so explicitly (e.g., "Boeing does not report Gross Profit").
- Sector averages are based on 2-5 companies in this dataset — note this limitation.
"""


def build_system_prompt() -> str:
    """Build the system prompt from real data and static context.

    Queries the DB to get the current company roster and metric catalog.
    Falls back to a minimal prompt if DB is unavailable.
    """
    try:
        return _build_from_data()
    except Exception as e:
        logger.warning("Failed to build system prompt from data: %s. Using minimal prompt.", e)
        return _build_minimal()


def _build_from_data() -> str:
    """Build the full system prompt by querying real data."""
    con = get_db()

    # 1. Company roster
    company_rows = con.execute(
        """SELECT DISTINCT ticker, canonical_name, sector, fiscal_year_end
           FROM company_financials
           WHERE fiscal_period = 'FY'
           ORDER BY ticker"""
    ).fetchall()

    company_lines = []
    non_dec_fy = []
    for ticker, name, sector, fy_end in company_rows:
        company_lines.append(f"- {ticker}: {name} | {sector} | FY ends {fy_end or 'N/A'}")
        if fy_end and not fy_end.startswith("12"):
            non_dec_fy.append(f"  - {ticker} ({name}): FY ends {fy_end}")

    company_roster = "\n".join(company_lines) if company_lines else "No companies loaded."

    # 2. Metric catalog
    metric_rows = con.execute(
        """SELECT DISTINCT business_term_id, business_term
           FROM company_financials
           ORDER BY business_term_id"""
    ).fetchall()

    metric_lines = [f"- {bt_id}: {bt_name}" for bt_id, bt_name in metric_rows]
    metric_catalog = "\n".join(metric_lines) if metric_lines else "No metrics loaded."

    # 3. Ratio catalog
    ratio_lines = [
        f"- {r['ratio_id']}: {r['ratio_name']} = {r['numerator_bt_id']} / {r['denominator_bt_id']}"
        for r in RATIO_DEFINITIONS
    ]
    ratio_catalog = "\n".join(ratio_lines)

    # 4. Fiscal year info
    fy_range_row = con.execute(
        "SELECT MIN(fiscal_year), MAX(fiscal_year) FROM company_financials WHERE fiscal_period = 'FY'"
    ).fetchone()
    min_fy = fy_range_row[0] if fy_range_row else "?"
    max_fy = fy_range_row[1] if fy_range_row else "?"

    row_count = con.execute("SELECT COUNT(*) FROM company_financials").fetchone()
    total_rows = row_count[0] if row_count else "?"

    # 5. Non-December FY companies
    fy_alignment = "\n".join(non_dec_fy) if non_dec_fy else "  All companies have December fiscal year ends."

    prompt = f"""You are a financial data analyst with access to SEC EDGAR financial data for {len(company_rows)} large-cap US companies spanning FY{min_fy}-{max_fy} ({total_rows:,} data points across 5 tables).

You answer questions by calling tool functions that query real Iceberg data. Never guess or fabricate numbers — always use the tools.

## Company Roster
{company_roster}

## Financial Metrics ({len(metric_rows)} business terms)
{metric_catalog}

## Financial Ratios (7 computed ratios)
{ratio_catalog}

{INTERPRETATION_GUIDE}

{KNOWN_ANOMALIES}

## Fiscal Year Alignment
Companies with non-December fiscal year ends (comparisons cover different calendar periods):
{fy_alignment}

## Scope & Limitations
- This dataset covers {len(company_rows)} large-cap US companies from FY{min_fy}-{max_fy}.
- Sector averages are based on 2-5 companies per sector — NOT representative of full sectors.
- Data comes from SEC EDGAR XBRL filings. Some filings have data quality issues (amendments, reclassifications).
- All values are in USD unless noted otherwise.
- Amendment analysis data is available — you can check if companies restated or amended their SEC filings, which concepts changed, and the magnitude of changes.

{FORMATTING_INSTRUCTIONS}"""

    return prompt


def _build_minimal() -> str:
    """Minimal fallback prompt when DB is unavailable."""
    return f"""You are a financial data analyst with access to SEC EDGAR financial data.
You answer questions by calling tool functions that query real data. Never guess or fabricate numbers.

{INTERPRETATION_GUIDE}

{KNOWN_ANOMALIES}

{FORMATTING_INSTRUCTIONS}"""
