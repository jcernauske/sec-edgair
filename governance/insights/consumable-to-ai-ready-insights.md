# Insight Report: Consumable Zone → AI-Ready Zone

**Date:** 2026-03-15
**Agent:** @insight-manager
**Source Tables:** consumable.company_financials, consumable.financial_ratios, consumable.period_over_period, consumable.peer_comparison, consumable.amendment_analysis
**Companies:** 20
**Consumable Rows:** 125,814 total (26,894 + 6,545 + 65,445 + 26,559 + 371)
**Base Rows Referenced:** 547,398 financial_facts + 239,127 amendment_tracking
**Business Terms:** 54 in glossary (25 financial metrics + 7 ratios + derived concepts)
**Time Range:** FY2009 to FY2026 (18 fiscal years)

## Executive Summary

We have 125,814 consumable rows across 5 tables, covering 20 large-cap US companies with 25 financial metrics, 7 computed ratios, 3 growth types, sector peer rankings, and amendment pattern analysis. The data is clean (52 DQ rules across consumable tables, all passing) and analytically rich. However, it is **structurally hostile to LLM consumption**: answering "summarize Apple's financial health" requires 5 separate table queries across 118 columns, fiscal year alignment math, and knowledge of which numbers need caveats. The AI-Ready zone must solve three problems: (1) pre-join the 5 tables into company-centric documents, (2) attach natural language context and anomaly flags to every data point, and (3) provide narrative templates that let an LLM generate human-readable financial summaries without hallucinating numbers. The highest-value product is a **Company Financial Profile** -- a single JSON document per company per year that an LLM can consume in one read. After that, **comparison-ready data packs** and **financial narrative templates** close the gap between structured data and natural language answers.

## Data Products -- Ranked

### Tier 1: High Value, High Feasibility (build from existing consumable data only)

| # | Data Product | Description | Source Tables | Why It Matters |
|---|-------------|-------------|---------------|----------------|
| 1 | **Company Financial Profile** | Single JSON document per (company, fiscal_year): all 25 metrics with values + YoY growth + 5yr CAGR, all 7 ratios, peer ranks/percentiles, amendment quality score, company metadata (sector, FY end, description), anomaly flags, fiscal alignment warnings. One document = one LLM context window load. | All 5 consumable tables | **The core AI-Ready product.** An LLM answering "tell me about Apple's FY2024 financials" should load ONE document, not run 5 queries. This eliminates 80% of the join complexity at query time. Estimated ~340 documents (20 companies x 17 years). |
| 2 | **Company Comparison Pack** | Pre-computed comparison JSON for every company pair within a sector: side-by-side metrics, ratio differences, rank gaps, growth rate differences, fiscal alignment warnings. For N companies in a sector, produce N*(N-1)/2 pairwise comparisons per year. | company_financials, financial_ratios, period_over_period, peer_comparison | "How does Apple compare to Microsoft?" is the #2 most common financial question after "tell me about company X." Pre-computing pairwise comparisons means the LLM gets a ready-made answer. Technology sector alone produces 10 pairs per year. |
| 3 | **Financial Narrative Templates** | Pre-generated natural language summaries per company per year using template engine (not LLM-generated). "Apple reported revenue of $394.3B in FY2024, up 7.8% year-over-year. Net margin was 25.3%, ranking #1 in the Technology sector (sector avg: 19.1%). R&D intensity was 7.8% of revenue, below sector median of 12.1%." | All 5 consumable tables | LLMs are good at reasoning but bad at arithmetic. Pre-generating the factual narrative eliminates hallucination risk on numbers. The LLM's job becomes synthesis and interpretation, not data retrieval and formatting. |
| 4 | **Anomaly & Caveat Registry** | Pre-attached flags on data points that need caveats: >2 sigma YoY changes (NFLX FY2019 revenue +497%), negative equity (Boeing FY2019+), extreme leverage (Boeing D/E 346x), fiscal year misalignment warnings, amendment-affected values, data quality notes (Apple Q1 2017 negative revenue). Each flag has a severity, a human-readable explanation, and a suggested caveat sentence. | All 5 consumable tables | **Prevents LLM hallucination by omission.** Without anomaly flags, an LLM might say "Boeing's debt-to-equity is 346x" without noting this is due to negative equity, not extreme debt. The caveat registry turns every unusual number into a number + explanation. |
| 5 | **Metric Definition & Context Registry** | Machine-readable definitions for all 25 business terms + 7 ratios: what it measures, typical range for this sector, how to interpret high/low values, which companies don't report it and why, related metrics. Derived from business-glossary.json + EDA reports. | business-glossary.json, EDA reports | LLMs need context to interpret numbers. "R&D Intensity of 0.078" is meaningless without knowing the tech sector average is 0.12, non-tech companies don't report it, and higher generally means more innovation investment. This registry provides that grounding. |

### Tier 2: High Value, Moderate Effort (requires new computation or external data)

| # | Data Product | Description | Source Tables | Key Dependency | Why It Matters |
|---|-------------|-------------|---------------|----------------|----------------|
| 6 | **Calendar-Year Aligned Comparisons** | Re-aggregate quarterly data into calendar years (Jan-Dec) for companies with non-December fiscal year ends (AAPL/V=Sep, MSFT/PG=Jun, WMT=Jan). Enables true apples-to-apples temporal comparison. | company_financials (quarterly rows) | Quarterly data must be available for Q1-Q4 calendar quarters. 5 of 20 companies need realignment. | When an LLM compares "FY2024 Revenue" across Apple (ends Sep) and Microsoft (ends Jun), it's comparing periods 3-6 months apart. Calendar-year alignment makes cross-company time comparisons honest. |
| 7 | **Sector Summary Documents** | Aggregate sector-level profiles: sector revenue, average margins, growth leaders, peer rankings, sector trends over time. One document per sector per year. | company_financials, financial_ratios, peer_comparison | Requires sectors with 2+ companies (5 of 8 sectors qualify). 3 single-company sectors (Energy, Industrials, Communication Services) get company-as-sector profiles. | Sector context is essential for answering "is this metric good or bad?" A 25% net margin means different things in Technology vs Consumer Staples. Sector summaries provide the baseline. |
| 8 | **Time Series Trend Documents** | Per (company, metric): full time series as a structured array with annotations at inflection points. "Apple Revenue: $170B(2015) -> $394B(2024), inflection at FY2020 (+33% jump, iPhone 12 cycle), 5yr CAGR 11.5%." Inflection = >2 sigma deviation from trailing average growth. | company_financials, period_over_period | Requires inflection point detection algorithm (statistical, not complex). | LLMs answer trend questions poorly from raw numbers. Pre-identifying inflection points and attaching them to the time series gives the LLM a narrative skeleton. "Revenue growth accelerated in FY2020" is more useful than "Revenue was $274B in FY2020 and $260B in FY2019." |
| 9 | **Financial Health Score** | Composite score per company per year: weighted combination of profitability (net margin percentile), leverage (D/E percentile inverse), growth (revenue CAGR percentile), amendment quality (inverse amendment rate). Score 0-100. | financial_ratios, period_over_period, peer_comparison, amendment_analysis | Requires weighting methodology -- simple equal weights or configurable. | Enables "rank companies by overall financial health" without the LLM doing multi-factor analysis. Reduces a 25-metric company to a single comparable score. Useful but opinionated -- the weights are editorial. |

### Tier 3: Exploratory / Future

| # | Data Product | Description | Dependency | Why It Matters |
|---|-------------|-------------|------------|----------------|
| 10 | **Embedding-Ready Financial Vectors** | Dense vector representation per (company, year): 25 metrics + 7 ratios + 3 growth types normalized to z-scores within sector. Enables similarity search ("find companies similar to Apple"). | Requires embedding infrastructure (vector DB or simple cosine similarity). | Enables semantic financial search. "What company is most similar to Netflix?" is answerable without domain expertise. Future use: RAG retrieval by financial similarity. |
| 11 | **Question-Answer Training Pairs** | Pre-generated Q&A pairs from the data: "Q: What was Apple's revenue in FY2024? A: $394.3B, up 7.8% YoY." One pair per (company, metric, year). ~6,800 pairs from FY data alone. | Requires template engine (same as #3). | Fine-tuning data for domain-specific LLM. Also useful as few-shot examples in prompts. |
| 12 | **Multi-Year Narrative Arcs** | 5-year story arcs per company: "Tesla's journey from unprofitable startup (FY2012 net margin -132%) to profitable automaker (FY2024 net margin 15.4%), with revenue growing from $413M to $96B (5yr CAGR 47.3%)." | Requires narrative generation (template or LLM-assisted). | The ultimate AI-Ready product. But it requires all Tier 1 products as inputs. Future spec after the foundation is built. |
| 13 | **Valuation Ratios (External Data)** | P/E, P/B, P/S, dividend yield, market cap. Requires stock price data (Yahoo Finance API, join on ticker + date). | Raw zone expansion: `raw-ingest-stock-prices` spec. | Valuation is the #1 missing analysis category. We have all the fundamental data; we just lack the market price. This unlocks the most-asked financial questions ("is Apple overvalued?"). |

## Cross-Company Coverage Matrix

### Consumable Zone Aggregate Coverage

| Table | Rows | Companies | Metrics/Ratios | Year Range | DQ Rules | DQ Status |
|-------|------|-----------|---------------|------------|----------|-----------|
| company_financials | 26,894 | 20 | 25 business terms | 2009-2026 | 8 | 8/8 PASS |
| financial_ratios | 6,545 | 20 | 7 ratios | 2009-2026 | 10 | 10/10 PASS |
| period_over_period | 65,445 | 20 | 25 BTs x 3 growth types | 2010-2026 | 12 | 12/12 PASS |
| peer_comparison | 26,559 | 17 (5 sectors) | 32 metrics | 2009-2026 | 10 | 10/10 PASS |
| amendment_analysis | 371 | 20 | 16 aggregate stats | 2006-2025 | 10 | 10/10 PASS |
| **TOTAL** | **125,814** | **20** | **61 distinct columns** | **2006-2026** | **50** | **50/50 PASS** |

### Company Data Richness (FY rows across all tables)

| Ticker | Company | CF | FR | PoP | PC | AA | Total FY | Notes |
|--------|---------|------|------|------|------|------|----------|-------|
| JNJ | Johnson & Johnson | 421 | 118 | 1,052 | 505 | 19 | 2,115 | Most complete |
| BA | Boeing | 419 | 119 | 1,054 | 0 | 19 | 1,611 | No peer comparison (solo sector) |
| PFE | Pfizer | 402 | 101 | 1,005 | 503 | 19 | 2,030 | |
| INTC | Intel | 395 | 119 | 984 | 509 | 19 | 2,026 | |
| AAPL | Apple | 374 | 107 | 861 | 479 | 20 | 1,841 | Sep FY-end |
| GOOGL | Alphabet | 246 | 66 | 558 | 312 | 14 | 1,196 | Fewest years (data from 2015) |
| BRK.A | Berkshire | 244 | 57 | 588 | 277 | 19 | 1,185 | Fewest BTs (no EPS, limited ratios) |

### Business Term Coverage for AI-Ready Profile

| Coverage Tier | Business Terms | Company Count | AI-Ready Implication |
|---------------|---------------|---------------|---------------------|
| Universal (20/20) | Revenue, Net Income, Total Assets, Total Liabilities, Stockholders Equity, Cash, Income Tax, OCF, ICF, FCF, Comprehensive Income, Retained Earnings | 20 | Always present in every company profile. LLM can rely on these. |
| Near-Universal (18-19) | PP&E, Goodwill, CapEx, EPS Basic, Operating Income, EPS Diluted | 18-19 | Present for most companies. Profile should note when missing and why. |
| Partial (9-17) | SG&A, DPS, Accounts Receivable, Inventory, Cost of Revenue, R&D, Gross Profit | 9-17 | Missing for valid reasons (sector structure). Profile MUST explain absence. |

## External Data Opportunities

| External Source | Join Key | What It Unlocks | Effort | Priority |
|----------------|----------|-----------------|--------|----------|
| **Yahoo Finance** (daily stock prices) | (ticker, date) -- use period_end_date for point-in-time pricing | P/E ratio, P/B ratio, P/S ratio, dividend yield, market cap, total return. Market cap enables "company size" context that sector alone doesn't provide. | Medium -- API rate limits, 20 tickers x 17 years daily data. | **#1** -- Valuation is the largest gap in the current data. |
| **Company descriptions** (SEC EDGAR company page, Wikipedia) | (cik) or (ticker) | Static company context: what the company does, key products, founding year, headquarters, number of employees. Essential for LLM grounding. | Low -- 20 companies, manual or one-time scrape. Static data. | **#2** -- Every AI-Ready profile needs a "who is this company" paragraph. |
| **SIC-to-GICS Sector Mapping** (refined) | (sic_code) | More granular industry classification. Current SIC mapping puts Visa in "Financials" alongside JPMorgan, which is a stretch for peer comparison. GICS sub-industries would enable better grouping. | Trivial -- static lookup table, ~80 rows. | **#3** |
| **FRED API** (Federal Reserve Economic Data) | (date) | GDP, CPI, Fed Funds Rate, 10Y Treasury. Macro context: "Revenue grew 5% vs 3% GDP = 2% real outperformance." | Low -- free API, well-documented. | **#4** |
| **S&P 500 constituent history** | (ticker, date) | Index membership timeline. Context for LLM: "TSLA joined S&P 500 in Dec 2020." | Low-Medium -- publicly available. | **#5** |

## Coverage Gaps & Risks

| Gap | Impact on AI-Ready | Mitigation |
|-----|-------------------|------------|
| **Only 20 companies** | LLM cannot answer "what's the industry average?" for broad market. Our "sector average" is based on 2-5 companies. | Declare scope explicitly in every profile: "Based on 20 large-cap US companies. Sector averages from N=2-5, not representative of full sector." |
| **3 single-company sectors** | Boeing (Industrials), Netflix (Comm Services), Exxon (Energy) have no peer comparison data. LLM gets rank/percentile for 17 companies but not these 3. | Include in profile with explicit "no sector peers in dataset" flag. Consider cross-sector comparisons (e.g., Boeing vs all 20) as an alternative. |
| **Fiscal year misalignment** | 5 companies (AAPL, MSFT, PG, V, WMT) have non-December fiscal year ends. "FY2024" means different calendar periods. | **Critical for AI-Ready.** Every comparison must include fiscal year end dates. Profile documents must include a "temporal alignment warning" when comparing across FY-end types. Calendar-year-aligned views (Tier 2, product #6) would solve this properly. |
| **Financial sector P&L structure** | JPM, GS, BRK.A lack Operating Income, Cost of Revenue, Gross Profit. Their profiles have missing ratio rows. | Profile documents must explain: "Financial institutions use different P&L structures. Operating Margin and Gross Margin are not applicable." |
| **No stock price / valuation data** | Cannot answer "is Apple overvalued?" or "what's the P/E ratio?" -- the #1 most-asked financial question category. | Acknowledge in profile. Recommend raw-ingest-stock-prices as highest-priority Raw Zone expansion. |
| **Extreme outliers in amendment data** | Goldman Sachs FY2013 shows a $42.6 trillion max amendment change (share count units, not dollars). These are real but misleading without unit context. | Anomaly registry must distinguish magnitude outliers caused by unit differences (share counts vs dollars) from genuine financial anomalies. |
| **Boeing negative equity** | D/E ratio of 346x is real but requires context (accumulated losses exceeding paid-in capital). Without caveat, an LLM might interpret this as extreme debt. | Anomaly flag: "Negative stockholders equity. Debt-to-equity ratio reflects negative equity denominator, not extreme debt level." |

## AI-Ready Considerations

### 1. Optimal Data Shape: JSON Documents, Not Tables

The consumable zone is table-shaped (rows and columns). LLMs work best with **document-shaped** data -- a self-contained JSON blob that has everything needed to answer questions about one entity in one time period. The AI-Ready zone should produce:

```json
{
  "company": {
    "ticker": "AAPL",
    "name": "Apple Inc.",
    "sector": "Technology",
    "fiscal_year_end": "September 30",
    "description": "Consumer electronics, software, and services company..."
  },
  "period": {
    "fiscal_year": 2024,
    "fiscal_period": "FY",
    "period_end_date": "2024-09-28",
    "calendar_year_note": "Apple's FY2024 ends Sep 2024; compare with caution to Dec-FY companies"
  },
  "financials": {
    "revenue": {
      "value": 394328000000,
      "formatted": "$394.3B",
      "unit": "USD",
      "yoy_change": 28709000000,
      "yoy_pct": 0.078,
      "cagr_5yr": 0.115,
      "sector_rank": 1,
      "sector_percentile": 1.0,
      "sector_avg": 198500000000,
      "companies_reporting": 20,
      "anomaly_flags": []
    },
    "net_income": { "..." : "..." },
    "...": "..."
  },
  "ratios": {
    "net_margin": {
      "value": 0.253,
      "formatted": "25.3%",
      "sector_rank": 1,
      "sector_avg": 0.191,
      "yoy_change_pp": 0.012,
      "anomaly_flags": []
    },
    "...": "..."
  },
  "amendment_quality": {
    "amendment_count": 429,
    "avg_change_magnitude": 15200000,
    "avg_days_to_amend": 315,
    "quality_signal": "normal"
  },
  "narrative": "Apple reported revenue of $394.3B in FY2024, up 7.8% YoY (5yr CAGR: 11.5%). Net margin was 25.3%, ranking #1 in Technology..."
}
```

This shape means an LLM loads ONE document to answer any question about Apple FY2024. No joins, no unit conversion, no fiscal alignment math.

### 2. Pre-Computed Aggregations That Reduce LLM Work

| Aggregation | Why Pre-Compute | Current State |
|-------------|-----------------|---------------|
| Formatted values ("$394.3B") | LLMs struggle with raw numbers (394328000000). Pre-formatting eliminates unit conversion errors. | Not computed. company_financials stores raw doubles. |
| Sector rank + percentile per metric | Already computed in peer_comparison. | Done. Needs to be denormalized into profile. |
| YoY growth + CAGR per metric | Already computed in period_over_period. | Done. Needs to be denormalized into profile. |
| Ratio trends (margin expansion/contraction) | LLM needs "margins are expanding" not "margin was 0.246 in 2023 and 0.253 in 2024." | Not computed. Needs period_over_period on ratios, or compute in AI-Ready. |
| Fiscal year alignment warnings | 5 companies need "this FY ends in Jun/Sep/Jan, not Dec" warning on every cross-company comparison. | fiscal_year_end column exists but no warning text. |
| Missing metric explanations | "Gross Profit not reported: financial institutions use different P&L structure." | Not computed. Needs metric_definition x company_sector logic. |

### 3. Anomaly Flags: What Needs a Caveat

Based on real data analysis, these data points require pre-attached caveats:

| Anomaly Type | Count | Examples | Suggested Caveat |
|-------------|-------|---------|-----------------|
| Revenue >100% YoY growth | 5 instances | NFLX FY2019 (+497%), TSLA FY2015 (+387%), MSFT FY2011 (+325%) | "Unusually large revenue change. May reflect M&A activity, segment reclassification, or accounting change rather than organic growth." |
| Negative stockholders equity | ~8 instances | Boeing FY2019-2024 | "Negative equity indicates accumulated losses exceed paid-in capital. Debt-to-equity ratio should be interpreted with caution." |
| Extreme D/E ratio (>50x) | 3 instances | Boeing FY2019 (346x), FY2017 (110x), FY2018 (68x) | "Extreme leverage ratio driven by near-zero or negative equity denominator." |
| Negative net margin >100% | 3 instances | TSLA FY2012 (-132%), FY2013 (-125%), FY2014 (-96%) | "Pre-profitability company. Operating losses exceeded revenue." |
| Apple Q1 2017 negative revenue | 1 instance | -$29M | "Data quality anomaly in source XBRL filing. Do not use for trend analysis." |
| High net income volatility | 5 companies | META (749% std dev), BRK.A (493%), BA (449%) | "Highly volatile earnings. Single-year comparisons may be misleading. Use 5yr CAGR for trend." |
| Amendment magnitude outliers (unit mismatch) | ~5 instances | GS FY2013 $42.6T (share counts, not dollars) | "Large amendment magnitude reflects non-dollar unit (share counts). Not a financial restatement." |

### 4. Fiscal Year Alignment: The Hidden Comparison Trap

This is the single most dangerous source of LLM error. When an LLM compares "FY2024" across companies:

| Company | FY2024 Period End | Months Off from Dec 2024 |
|---------|------------------|-------------------------|
| 15 companies | Dec 2024 | 0 (aligned) |
| AAPL, V | Sep 2024 | 3 months earlier |
| MSFT, PG | Jun 2024 | 6 months earlier |
| WMT | Jan 2025 | 1 month later |

**AI-Ready requirement:** Every cross-company comparison must include period_end_date for both companies. If they differ by >1 month, attach a temporal alignment warning: "Apple's FY2024 (ending Sep 28, 2024) vs Microsoft's FY2024 (ending Jun 30, 2024) cover different 12-month periods. For calendar-year-aligned comparison, use quarterly roll-up data."

### 5. What An LLM Needs That We Don't Have

| Missing Context | Source | Importance | Notes |
|----------------|--------|-----------|-------|
| Company description ("what does Apple do?") | SEC EDGAR / Wikipedia | Critical | LLMs know this from training data, but explicit context prevents hallucination and ensures consistency. |
| Metric definitions ("what is Operating Cash Flow?") | Business glossary + domain knowledge | High | LLMs know definitions broadly, but sector-specific nuance matters. "Operating Cash Flow for banks includes different items than for tech companies." |
| Typical metric ranges per sector | Derived from peer_comparison stats | High | "Net margin of 25% is excellent for Tech (sector avg 19%), but expected for Financials (sector avg 30%)." |
| Historical context / narrative | Not available without LLM generation | Medium | "Boeing's financial deterioration began with the 737 MAX crisis in FY2019." We have the numbers but not the story. Template-based narrative (#3) partially addresses this. |
| Industry/macro context | FRED API / external | Medium | "Revenue grew 8% in a year when GDP grew 3%." Relative outperformance matters. |

### 6. Recommended Document Types for AI-Ready Zone

| Document Type | Grain | Estimated Count | Use Case |
|--------------|-------|-----------------|----------|
| Company Financial Profile | (company, fiscal_year) | ~340 | "Tell me about Apple FY2024" |
| Company Comparison Pack | (company_a, company_b, fiscal_year) | ~800 (pairwise in 5 sectors) | "Compare Apple vs Microsoft FY2024" |
| Sector Summary | (sector, fiscal_year) | ~130 (8 sectors x 17 years) | "How is the Technology sector performing?" |
| Financial Narrative | (company, fiscal_year) | ~340 | Pre-written factual summary for LLM to build on |
| Metric Context Card | (metric_id) | ~32 | "What is Net Margin and how should I interpret it?" |
| Anomaly Report | (company, fiscal_year, metric) | ~50-100 | Attached caveats for unusual data points |

## Recommended Spec Order

Based on value, feasibility, and dependencies:

1. **`ai-ready-company-profiles`** -- The foundation. Pre-joins all 5 consumable tables into one JSON document per (company, fiscal_year). Includes formatted values, all ratios, growth metrics, peer ranks, amendment stats, anomaly flags, and fiscal alignment warnings. Grain: (ticker, fiscal_year). ~340 documents.
   - Depends on: all 5 consumable tables (complete)
   - Unlocks: products #2, #3, #8, #9, #11, #12

2. **`ai-ready-metric-context`** -- Metric definition and interpretation registry. One document per metric (25 BTs + 7 ratios = 32 documents). Includes: definition, typical ranges by sector, which companies don't report it and why, related metrics, interpretation guidance.
   - Depends on: business-glossary.json, peer_comparison (for sector ranges), company_financials (for coverage)
   - Unlocks: products #3, #5

3. **`ai-ready-anomaly-registry`** -- Pre-computed anomaly flags for every data point that needs a caveat. Statistical detection (>2 sigma YoY change), known data quality issues (Apple Q1 2017), structural anomalies (negative equity), and fiscal alignment warnings. One registry document with all flags, queryable by (company, metric, year).
   - Depends on: company_financials, period_over_period, financial_ratios
   - Unlocks: products #1, #3, #4

4. **`ai-ready-financial-narratives`** -- Template-generated natural language summaries per (company, fiscal_year). Pure template fill from profile data -- no LLM generation. Templates for: one-sentence summary, one-paragraph overview, full financial review, comparison sentence.
   - Depends on: ai-ready-company-profiles (#1), ai-ready-metric-context (#2), ai-ready-anomaly-registry (#3)
   - Unlocks: products #11, #12

5. **`ai-ready-comparison-packs`** -- Pairwise company comparison documents for intra-sector peers. Pre-computed side-by-side with delta analysis and fiscal alignment warnings.
   - Depends on: ai-ready-company-profiles (#1)
   - Unlocks: product #2

6. **`ai-ready-sector-summaries`** -- Sector-level aggregate profiles: sector revenue, average/median ratios, growth leaders, trend direction. One document per (sector, fiscal_year).
   - Depends on: ai-ready-company-profiles (#1), peer_comparison
   - Unlocks: product #7

7. **`ai-ready-embeddings`** (future) -- Vector representations for similarity search. Depends on all above being stable.
   - Depends on: ai-ready-company-profiles (#1), vector infrastructure
   - Unlocks: product #10

## Appendix: Questions Answerable Today vs After AI-Ready

| Question | Today (Consumable) | After AI-Ready |
|----------|-------------------|----------------|
| "What was Apple's revenue in FY2024?" | 1 SQL query against company_financials | Read profile.financials.revenue.formatted |
| "How does Apple's margin compare to Microsoft's?" | 3 queries: FR for both + PC for ranks | Read 2 profiles, comparison already computed |
| "Is Boeing's financial health deteriorating?" | 5+ queries across all tables, manual analysis | Read profile.narrative + anomaly flags |
| "Which tech company grew fastest over 5 years?" | 1 query against period_over_period with filter | Read sector summary, already ranked |
| "What's unusual about TSLA's early years?" | Multiple queries + manual anomaly detection | Read anomaly registry for TSLA FY2012-2014 |
| "Summarize Apple's FY2024 in one paragraph" | Not possible without LLM doing 5 queries + formatting | Read narrative template, LLM enhances |
| "What is Net Margin and is 25% good?" | Not answerable from data alone | Read metric context card for RATIO-003 |
| "Compare all tech companies on profitability" | Complex multi-join query | Read sector summary + 10 comparison packs |

## Appendix: Total Governance Artifact Count

As of consumable zone completion:

| Artifact Type | Count | Location |
|--------------|-------|----------|
| DQ Rules | 52 (consumable) + 42 (base) + 10 (raw) = 104 total | governance/dq-rules/ |
| DQ Scorecards | 12 | governance/dq-scorecards/ |
| EDA Reports | 7 | governance/eda/ |
| OpenLineage Files | 5 (consumable) + 5 (base) = 10+ | governance/lineage/ |
| Data Models | 15 (5 specs x 3 levels) consumable + 9 base = 24 | governance/models/ |
| Business Terms | 54 | governance/business-glossary.json |
| Insight Reports | 2 (this is the second) | governance/insights/ |
| Session Logs | 30+ | docs/sessions/ |
