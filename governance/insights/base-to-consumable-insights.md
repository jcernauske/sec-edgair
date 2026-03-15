# Insight Report: Base Zone → Consumable Zone

**Date:** 2026-03-14
**Agent:** @insight-manager
**Source Tables:** base.financial_facts, base.entity_mappings, base.concept_mappings, base.fiscal_calendar, base.amendment_tracking
**Companies:** 20
**Facts:** 547,398 total (283,025 current / non-superseded)
**Time Range:** FY2009 to FY2026 (end_date: 2006-06-30 to 2026-03-11)

## Executive Summary

We have 283K current financial facts across 20 large-cap US companies spanning 17 years, with 25 canonical business terms already mapped. The data is clean (42 DQ rules, all passing) and temporally rich (amendment tracking, supersession, bitemporal queries). The highest-value next step is a **cross-company financial comparison table** — 12 of our 25 business terms have coverage across all 20 companies with annual data back to 2009, which means we can build Apple-vs-Microsoft-vs-Amazon revenue comparisons *today* with no new data. After that, **computed financial ratios** and **period-over-period growth** are one derivation away from what we already have. External data (stock prices) would unlock valuation ratios (P/E, price-to-book) — the single highest-value enrichment opportunity.

## Data Products — Ranked

### Tier 1: High Value, High Feasibility (build from existing data only)

| # | Data Product | Description | Source Tables | Why It Matters |
|---|-------------|-------------|---------------|----------------|
| 1 | **Company Financial Comparison** | Denormalized table: one row per (company, business term, fiscal_year, fiscal_period) with current value. Filter `is_superseded=false`, pivot on business_term. Simple SELECT with WHERE clause on existing data. | base.financial_facts | **The core use case.** "Show me Apple vs Microsoft revenue over time" is the question everyone asks first. 12 business terms have all-20-company coverage. This table makes it a one-liner. |
| 2 | **Period-Over-Period Growth** | For each (company, business term, period), compute YoY change and % change by joining the same business term across consecutive fiscal years. | base.financial_facts, base.fiscal_calendar | Revenue growth, earnings growth, asset growth — the #1 thing analysts look at after absolute values. Pure derivation from existing data, no external sources needed. |
| 3 | **Financial Ratios (Internal)** | Computed ratios using only existing business terms: gross margin (BT-035/BT-022), operating margin (BT-036/BT-022), net margin (BT-023/BT-022), debt-to-equity (BT-027/BT-028), current ratio (requires current assets — not a business term yet), R&D intensity (BT-038/BT-022), SGA ratio (BT-039/BT-022), capex-to-revenue (BT-043/BT-022). | base.financial_facts | Ratios enable comparative analysis ("who's the most profitable?") without needing to normalize for company size. 7 ratios are computable today from existing business terms. |
| 4 | **Amendment Impact Analysis** | Summarize amendment_tracking: which companies amend most? Which metrics change most? Average magnitude of restatements. | base.amendment_tracking, base.financial_facts | Unique insight not available from standard financial data providers. "Berkshire rarely restates; Boeing restates often" is genuinely interesting intelligence about corporate reporting quality. |

### Tier 2: High Value, Moderate Effort (requires external data or new business terms)

| # | Data Product | Description | Source Tables | Key Dependency | Why It Matters |
|---|-------------|-------------|---------------|----------------|----------------|
| 5 | **Valuation Ratios** | P/E ratio (price / EPS), price-to-book (market cap / equity), price-to-sales (market cap / revenue), dividend yield (DPS / price). | base.financial_facts + **stock price data** | External: daily stock prices (Yahoo Finance, Alpha Vantage, or FRED) | The most-asked financial questions involve valuation. We have the E, the B, the S, and the D — we just need the P. |
| 6 | **Industry Peer Comparison** | Group companies by SIC sector, compute sector averages/medians for each business term, rank each company within its sector. | base.financial_facts, base.entity_mappings (sic_code) | SIC-to-sector mapping (we have SIC codes for all 20 companies) | "Is Apple's margin good?" only makes sense relative to peers. We already have SIC codes — just need a SIC-to-sector-name lookup. |
| 7 | **Cash Flow Quality Score** | Ratio of operating cash flow to net income (>1.0 = high quality earnings), free cash flow (OCF - CapEx), FCF yield when combined with stock prices. | base.financial_facts (BT-040, BT-023, BT-043) | Minor: free cash flow is a derived business term not yet defined | Cash flow quality distinguishes real earnings from accounting earnings. Enron's net income looked great; its cash flow didn't. |
| 8 | **Balance Sheet Health Index** | Composite score from debt-to-equity, current ratio, interest coverage. Flags companies trending toward distress. | base.financial_facts | Needs: current assets business term, interest expense business term (currently unmapped Tier 3 concepts) | Early warning system for financial distress. Boeing's deteriorating balance sheet is a story this data can tell. |

### Tier 3: Exploratory / Future

| # | Data Product | Description | Dependency | Why It Matters |
|---|-------------|-------------|------------|----------------|
| 9 | **Earnings Quality Composite** | Multi-signal score: accruals ratio, revenue recognition patterns, amendment frequency, supersession history | Requires research-grade computation + domain expertise | Institutional investor-level analysis. Publishable research. |
| 10 | **Macro Correlation Analysis** | Correlate company financials with GDP, CPI, interest rates, sector indices | External: FRED API (Federal Reserve Economic Data) | Contextualizes company performance. "Revenue grew 5% but GDP grew 3% — so real outperformance was 2%." |
| 11 | **SEC Filing Timeliness** | Days between period_end and filed_date. Late filers may signal operational issues. | Already in base.financial_facts (filed_date - end_date) | Regulatory intelligence. Late filings often precede bad news. |
| 12 | **Natural Language Financial Summaries** | LLM-generated company profiles: "Apple's revenue grew 8% YoY to $394B in FY2024, with operating margins expanding to 30%..." | Requires Consumable zone + AI-Ready zone pipeline | The end goal for LLM consumption. But needs the numbers computed first. |

## Cross-Company Coverage Matrix

### Universal Business Terms (all 20 companies report these annually)

| BT | Metric | FY Facts | Min Year | Max Year | Quality |
|-----|--------|----------|----------|----------|---------|
| BT-047 | Comprehensive Income | 5,010 | 2009 | 2026 | Excellent — highest fact count |
| BT-037 | Income Tax Expense | 2,240 | 2009 | 2026 | Excellent |
| BT-022 | Revenue | 1,804 | 2009 | 2026 | Excellent — the #1 comparison metric |
| BT-023 | Net Income | 1,325 | 2009 | 2026 | Excellent |
| BT-029 | Cash & Equivalents | 1,042 | 2009 | 2026 | Excellent |
| BT-027 | Total Liabilities | 604 | 2009 | 2026 | Excellent |
| BT-028 | Total Stockholders Equity | 509 | 2009 | 2026 | Excellent |
| BT-048 | Retained Earnings | 372 | 2009 | 2026 | Good |
| BT-024 | Total Assets | 349 | 2009 | 2026 | Good |
| BT-042 | Financing Cash Flow | 344 | 2009 | 2026 | Good |
| BT-041 | Investing Cash Flow | 344 | 2009 | 2026 | Good |
| BT-040 | Operating Cash Flow | 344 | 2009 | 2026 | Good |

### Near-Universal Business Terms (18-19 companies)

| BT | Metric | Companies | Missing | Notes |
|-----|--------|-----------|---------|-------|
| BT-044 | EPS Basic | 19 | BRK.A (no split-adjusted EPS) | |
| BT-032 | PP&E | 19 | One company | |
| BT-033 | Goodwill | 19 | One company (likely no acquisitions) | |
| BT-043 | Capital Expenditures | 19 | | |
| BT-036 | Operating Income | 18 | JPM, GS (banks use different P&L structure) | Financial sector gap |
| BT-045 | EPS Diluted | 18 | | |

### Partial Business Terms (9-17 companies)

| BT | Metric | Companies | Why Partial |
|-----|--------|-----------|-------------|
| BT-039 | SG&A Expense | 17 | Some companies report OpEx differently |
| BT-046 | Dividends Per Share | 16 | AMZN, META, TSLA, GOOGL don't pay dividends (or didn't historically) |
| BT-030 | Accounts Receivable | 16 | Financial companies report differently |
| BT-031 | Inventory | 15 | Service/tech companies may not report |
| BT-034 | Cost of Revenue | 15 | Financial companies don't have "cost of revenue" |
| BT-038 | R&D Expense | 12 | Non-tech companies don't break out R&D |
| BT-035 | Gross Profit | 9 | Many companies don't report gross profit as a line item |

## External Data Opportunities

| External Source | Join Strategy | What It Unlocks | Effort | Priority |
|----------------|--------------|-----------------|--------|----------|
| **Yahoo Finance / Alpha Vantage** (daily stock prices) | Join on (ticker, date) — we have tickers for all 20 companies. Use fiscal_calendar.period_end as the date for point-in-time pricing. | P/E ratio, P/B ratio, P/S ratio, dividend yield, market cap, total return. **This is the single highest-value external data source.** | Medium — free API, rate-limited. ~20 tickers x ~17 years of daily data. | **#1 Priority** |
| **FRED API** (Federal Reserve Economic Data) | Join on (date) for macro indicators: GDP, CPI, Fed Funds Rate, 10Y Treasury, unemployment. | Macro-adjusted analysis: "Revenue grew 5% vs 3% GDP = 2% real growth." Sector rotation signals. | Low — free, well-documented REST API, no rate limits. | #2 |
| **SEC EDGAR Company Filings Index** (full filing metadata) | Join on (cik, accession_number). We already have both. | Filing page counts, exhibit counts, XBRL validation errors, filing time-of-day. Operational intelligence about corporate reporting. | Low — already using SEC EDGAR API. | #3 |
| **SIC-to-GICS Sector Mapping** | Lookup on sic_code — we have SIC codes for all 20 companies. | Industry classification for peer grouping. GICS is the standard institutional investors use. | Trivial — static mapping table, ~80 rows. | #3 |
| **S&P 500 Index Constituents** (historical) | Join on (ticker, date). | Track when companies entered/exited the index. Survivorship bias awareness. | Low-Medium — Wikipedia has historical data. | #4 |

## Coverage Gaps & Risks

| Gap | Impact | Mitigation |
|-----|--------|------------|
| **Only 20 companies** | Can't do broad market analysis. Results are large-cap biased. | Acknowledge limitation. These 20 cover ~30% of S&P 500 market cap. Expanding to 100+ companies is a future Raw Zone spec. |
| **Financial sector P&L structure** | JPM, GS, BRK.A use different income statement structure — no "Cost of Revenue" or "Operating Income" in the traditional sense. | Treat financial companies as a separate peer group. Consider bank-specific business terms (Net Interest Income, Provision for Credit Losses) in future business term expansion. |
| **Gross Profit only 9 companies** | Can't compute gross margin for all companies. | Use operating margin (18 companies) as the primary profitability metric. Gross margin is a Tier 2 analysis. |
| **No current assets/liabilities split** | Can't compute current ratio (a key liquidity metric). | Would need business term expansion (current assets, current liabilities). These XBRL tags exist in Tier 3 unmapped concepts. |
| **Fiscal year misalignment** | Apple (Sep), Microsoft (Jun), Walmart (Jan), PG (Jun) vs. most companies (Dec). Cross-company comparison for a "year" is actually comparing different calendar periods. | The consumable layer should offer both fiscal-year and calendar-year views. Calendar-year view uses quarterly data (Q1+Q2+Q3+Q4) realigned to Jan-Dec. Flag the alignment method on every comparison. |
| **Supersession ratio is 48.3%** | Almost half of all facts are superseded. Consumers MUST filter `is_superseded=false` or they'll double-count. | The consumable layer should ONLY expose current (non-superseded) facts by default. Superseded data is base-zone-only. |

## AI-Ready Considerations

1. **Pre-computed comparisons are essential.** An LLM shouldn't have to scan 283K facts to answer "what was Apple's revenue in 2024?" The consumable table should be queryable with a simple WHERE clause.

2. **Natural language metadata per row.** Each consumable row should carry enough context for an LLM to generate a meaningful sentence: company name, metric name, period, value, unit, and ideally YoY change.

3. **Fiscal year alignment annotations.** When comparing Apple (Sep FY) to Microsoft (Jun FY) for "2024", the LLM needs to know these aren't the same calendar period. The consumable table should include `fiscal_year_end_mmdd` and `period_end_date`.

4. **Pre-aggregated time series.** Rather than making the LLM aggregate, store the 5-year and 10-year CAGR for each (company, business term). "Apple's 5-year revenue CAGR is 8.2%" is more useful than raw annual numbers.

5. **Anomaly flags.** Mark data points that are unusual: >2σ YoY change, negative values for typically positive metrics, amendment-affected values. LLMs should know when a number needs a caveat.

6. **Company context blobs.** A JSON field per company with sector, market cap range, fiscal year end, number of employees, key products. LLMs need this for grounding.

## Recommended Spec Order

Based on value, feasibility, and dependencies:

1. **`consumable-company-financials`** — The core denormalized comparison table. One row per (company, business term, fiscal_year, fiscal_period). Current facts only. This is the foundation everything else builds on.
   - Depends on: nothing new (uses existing base tables)
   - Unlocks: products #2, #3, #4, #6, #7

2. **`consumable-financial-ratios`** — Computed ratios (margins, returns, leverage). Derived from the company financials table.
   - Depends on: `consumable-company-financials`
   - Unlocks: products #6, #8

3. **`consumable-period-over-period`** — YoY growth, sequential growth, CAGR. Time-series analysis layer.
   - Depends on: `consumable-company-financials`
   - Unlocks: products #9, #12

4. **`consumable-peer-comparison`** — Sector grouping, peer ranks, percentiles. Requires SIC-to-sector mapping.
   - Depends on: `consumable-company-financials`, `consumable-financial-ratios`
   - Unlocks: product #6

5. **`raw-ingest-stock-prices`** (Raw Zone expansion) — Daily stock prices for all 20 tickers. New raw data source.
   - Depends on: external API (Yahoo Finance or Alpha Vantage)
   - Unlocks: products #5 (valuation ratios)

6. **`consumable-amendment-analysis`** — Amendment frequency, magnitude, and patterns per company.
   - Depends on: nothing new (uses base.amendment_tracking)
   - Unlocks: product #4

## Appendix: Company Roster

| Ticker | Company | SIC | Sector | FY End | Current Facts | Years |
|--------|---------|-----|--------|--------|---------------|-------|
| JPM | JPMorgan Chase & Co. | 6020 | Financial | Dec | 24,717 | 17 |
| GS | The Goldman Sachs Group Inc. | 6211 | Financial | Dec | 19,910 | 17 |
| PFE | Pfizer Inc. | 2834 | Healthcare | Dec | 17,339 | 17 |
| BA | The Boeing Company | 3721 | Industrials | Dec | 17,154 | 17 |
| KO | The Coca-Cola Company | 2086 | Consumer Staples | Dec | 16,868 | 17 |
| MSFT | Microsoft Corporation | 7372 | Technology | Jun | 15,957 | 17 |
| AMZN | Amazon.com Inc. | 5961 | Consumer Discretionary | Dec | 15,764 | 17 |
| UNH | UnitedHealth Group Incorporated | 6324 | Healthcare | Dec | 15,303 | 17 |
| INTC | Intel Corporation | 3674 | Technology | Dec | 14,633 | 17 |
| JNJ | Johnson & Johnson | 2834 | Healthcare | Dec | 13,998 | 17 |
| V | Visa Inc. | 7389 | Financial | Sep | 12,523 | 18 |
| TSLA | Tesla Inc. | 3711 | Consumer Discretionary | Dec | 12,154 | 15 |
| AAPL | Apple Inc. | 3571 | Technology | Sep | 12,154 | 18 |
| NFLX | Netflix Inc. | 7841 | Communication | Dec | 11,921 | 17 |
| PG | Procter & Gamble Company | 2841 | Consumer Staples | Jun | 11,511 | 18 |
| WMT | Walmart Inc. | 5331 | Consumer Staples | Jan | 11,478 | 17 |
| GOOGL | Alphabet Inc. | 7372 | Technology | Dec | 10,639 | 11 |
| XOM | Exxon Mobil Corporation | 2911 | Energy | Dec | 9,929 | 17 |
| META | Meta Platforms Inc. | 7370 | Technology | Dec | 9,603 | 14 |
| BRK.A | Berkshire Hathaway Inc. | 6331 | Financial | Dec | 9,470 | 17 |
