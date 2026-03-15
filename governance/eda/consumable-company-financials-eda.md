## EDA Report: Consumable Company Financials Source Data
**Source:** base.financial_facts (filtered), base.entity_mappings, base.concept_mappings
**Date:** 2026-03-14
**Agent:** @data-analyst
**Spec:** docs/specs/consumable-company-financials.md
**Upstream Reference:** governance/insights/base-to-consumable-insights.md

### Scope

This EDA profiles the source data that will feed `consumable.company_financials`. The consumable table applies three filters to base.financial_facts before any transformation:
1. `is_superseded = false` (keep only current facts)
2. `business_term_id IS NOT NULL` (keep only mapped business terms, Tier 1+2)
3. Unit filtering (USD for dollar amounts, USD/shares for per-share)

### Key Numbers for DQ Thresholds

| Metric | Value | Source |
|--------|-------|--------|
| Total base.financial_facts rows | 547,398 | base-zone-eda.md |
| Current (non-superseded) rows | 283,025 (51.7%) | base-zone-eda.md |
| Rows with business_term_id | 163,899 (29.9%) | Complement of 70.1% NULL rate |
| Current + mapped rows (pre-collision) | ~84,800 (est.) | 283,025 x 29.9% |
| Expected output rows (post-collision) | ~27,000 | Spec estimate: 20 companies x 25 terms x ~54 periods avg |
| Business terms in scope | 25 | BT-022 to BT-048 |
| Companies in scope | 20 | All entity_mappings entries |
| Fiscal period types | 4 | FY, Q1, Q2, Q3 |
| Year range | FY2009 to FY2026 | ~17 years |

### Concept Collision Analysis

**34.3% of (company, business_term_id, fiscal_year, fiscal_period) groups have 2+ XBRL concepts mapping to the same business term.** This is the primary complexity the consumable table resolves.

| Collision Category | Detail |
|-------------------|--------|
| Worst offender | BT-047 (Comprehensive Income): up to 51 sub-component concepts per period |
| High collision terms | BT-028 (Stockholders Equity), BT-029 (Cash & Equivalents), BT-022 (Revenue) |
| Low collision terms | BT-033 (Goodwill), BT-032 (PP&E) -- typically one dominant concept |

**Resolution strategy:** Primary concept preference (spec Section 2.2). Walk an ordered list of preferred XBRL concepts per business term; pick the first match. Fallback: highest tier, then most facts across the dataset.

**DQ implication:** After collision resolution, every (cik, business_term_id, fiscal_year, fiscal_period) must have exactly one row. CONS-CF-001 (record_id uniqueness) enforces this at 100%.

### Unit Distribution

| Category | Business Terms | Primary Unit | Other Units Present |
|----------|---------------|-------------|-------------------|
| Balance Sheet | BT-024, BT-027 to BT-033 | USD | Some facts in other currencies (filtered out) |
| Income Statement | BT-022, BT-023, BT-034 to BT-039 | USD | Minor non-USD entries |
| Cash Flow | BT-040 to BT-043 | USD | Minimal variation |
| Per-Share | BT-044 to BT-046 | USD/shares | No alternatives expected |
| Other | BT-047, BT-048 | USD | Some currency variants |

**DQ implication:** CONS-CF-005 validates that every row has the correct unit for its business term category. After unit filtering, this should be 100%.

### Coverage Matrix

#### Universal Coverage (all 20 companies, annual data)
12 business terms have coverage across all 20 companies:

| BT | Metric | FY Fact Count | Quality |
|----|--------|--------------|---------|
| BT-047 | Comprehensive Income | 5,010 | Highest volume |
| BT-037 | Income Tax Expense | 2,240 | High |
| BT-022 | Revenue | 1,804 | Core comparison metric |
| BT-023 | Net Income | 1,325 | High |
| BT-029 | Cash & Equivalents | 1,042 | High |
| BT-027 | Total Liabilities | 604 | Good |
| BT-028 | Stockholders Equity | 509 | Good |
| BT-048 | Retained Earnings | 372 | Good |
| BT-024 | Total Assets | 349 | Good |
| BT-042 | Financing Cash Flow | 344 | Good |
| BT-041 | Investing Cash Flow | 344 | Good |
| BT-040 | Operating Cash Flow | 344 | Good |

#### Near-Universal Coverage (18-19 companies)
| BT | Metric | Companies | Missing |
|----|--------|-----------|---------|
| BT-044 | EPS Basic | 19 | BRK.A |
| BT-032 | PP&E | 19 | 1 company |
| BT-033 | Goodwill | 19 | 1 company |
| BT-043 | Capital Expenditures | 19 | 1 company |
| BT-036 | Operating Income | 18 | JPM, GS (bank P&L structure) |
| BT-045 | EPS Diluted | 18 | 2 companies |

#### Partial Coverage (9-17 companies)
| BT | Metric | Companies | Why Partial |
|----|--------|-----------|-------------|
| BT-039 | SG&A Expense | 17 | OpEx reporting differences |
| BT-046 | Dividends Per Share | 16 | Non-dividend payers |
| BT-030 | Accounts Receivable | 16 | Financial sector differences |
| BT-031 | Inventory | 15 | Service/tech companies |
| BT-034 | Cost of Revenue | 15 | Financial sector |
| BT-038 | R&D Expense | 12 | Non-tech companies |
| BT-035 | Gross Profit | 9 | Many don't report as line item |

**DQ implication:**
- CONS-CF-007 (all 25 business terms represented): should pass -- all 25 terms have at least 9 companies
- CONS-CF-008 (all 20 companies represented): should pass -- all 20 companies report at least the 12 universal terms
- CONS-CF-006 (companies_reporting accuracy): the count varies from 9 to 20 per business term per period type

### Sector Distribution

SIC-to-sector mapping produces 6 sectors across the 20 companies:

| Sector | Companies | Count |
|--------|-----------|-------|
| Technology | AAPL, INTC, META, MSFT, GOOGL | 5 |
| Financials | JPM, GS, BRK.A, V | 4 |
| Healthcare | PFE, JNJ, UNH | 3 |
| Consumer Staples | KO, PG, WMT | 3 |
| Consumer Discretionary | AMZN, TSLA | 2 |
| Energy | XOM | 1 |
| Industrials | BA | 1 |
| Communication Services | NFLX | 1 |

**Note:** 8 sectors, not 6 as stated in the spec estimate. The spec's "6 sectors" appears to be an undercount.

### Recommendations for @dq-rule-writer

1. **CONS-CF-001 (uniqueness):** 100% threshold. After collision resolution, duplicates indicate a bug in the resolution engine.
2. **CONS-CF-002 (valid business_term_id):** 100% threshold. Every row must reference a known business term from concept_mappings.
3. **CONS-CF-003 (valid cik):** 100% threshold. Every row must reference a known company from entity_mappings.
4. **CONS-CF-004 (no null val):** 100% threshold. The entire point of the table is to have values.
5. **CONS-CF-005 (unit consistency):** 100% threshold. Unit filtering is applied during build -- mismatches indicate a build bug.
6. **CONS-CF-006 (companies_reporting accuracy):** 100% threshold. The count is computed from the same data -- discrepancies indicate a computation bug.
7. **CONS-CF-007 (25 business terms):** 100% threshold. All 25 terms have at least 9 companies in the source data.
8. **CONS-CF-008 (20 companies):** 100% threshold. All 20 companies have at least the 12 universal terms.
