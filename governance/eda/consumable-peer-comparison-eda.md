# EDA Report: Consumable Peer Comparison
**Date:** 2026-03-15
**Agent:** @data-analyst
**Sources:** consumable.company_financials (26,894 rows), consumable.financial_ratios (6,544 rows)
**Target:** consumable.peer_comparison

## 1. Source Data Profile

### consumable.company_financials
- **Row count:** 26,894
- **Companies:** 20 (across 8 sectors)
- **Business terms:** 25 (BT-022 through BT-048)
- **Fiscal periods:** FY, Q1, Q2, Q3
- **Fiscal year range:** 2009-2026

### consumable.financial_ratios
- **Row count:** 6,544
- **Companies:** 20
- **Ratios:** 7 (RATIO-001 through RATIO-007)
- **Fiscal periods:** FY, Q1, Q2, Q3
- **Fiscal year range:** 2009-2026

## 2. Sector Distribution

| Sector | Companies | Eligible for Peer Comparison |
|--------|-----------|------------------------------|
| Technology | 5 | Yes |
| Financials | 4 | Yes |
| Healthcare | 3 | Yes |
| Consumer Staples | 3 | Yes |
| Consumer Discretionary | 2 | Yes |
| Communication Services | 1 | No (single company) |
| Energy | 1 | No (single company) |
| Industrials | 1 | No (single company) |

**Eligible sectors:** 5 (17 companies)
**Excluded sectors:** 3 (3 companies: NFLX, XOM, BA)

## 3. Peer Comparison Row Estimates

### From company_financials
- Total groups (sector, metric_id, fiscal_year, fiscal_period): varies
- Groups with 2+ companies: majority of groups in 5 eligible sectors
- **Eligible rows:** 21,642

### From financial_ratios
- Total groups (sector, ratio_id, fiscal_year, fiscal_period): varies
- Groups with 2+ companies: majority of groups in 5 eligible sectors
- **Eligible rows:** 4,917

### Total estimated peer_comparison rows: 26,559

## 4. Metric Coverage by Sector

### company_financials metrics
- All 25 business terms appear across eligible sectors
- Coverage varies: Revenue (BT-022) has all 17 eligible companies; R&D Expense (BT-038) is absent for some financial sector companies
- Not every company reports every metric in every period

### financial_ratios metrics
- All 7 ratios appear across eligible sectors
- Coverage varies by ratio: Net Margin available for most companies; Gross Margin missing for financial sector companies
- Same coverage patterns as the underlying company_financials data

## 5. Edge Cases Identified

| Edge Case | Count | Impact |
|-----------|-------|--------|
| Single-company sectors | 3 sectors (Energy, Industrials, Communication Services) | Excluded -- no peer comparison rows |
| Tied values possible | Yes (especially for near-zero metrics) | Dense ranking handles this correctly |
| Negative values | Present in Net Income, Operating Income, Cash Flows | Ranked normally -- least negative is higher |
| Missing metrics per company | Financial sector companies lack Gross Profit, R&D | Excluded from those metric groups; peer_count reflects actual participants |

## 6. DQ Threshold Evidence

| Threshold | Evidence |
|-----------|----------|
| record_id uniqueness | Grain is 5-field compound key; hash collision probability negligible at ~26.5K rows |
| metric_source validity | Only two possible values produced by build logic |
| sector_rank range | Dense ranking guarantees 1 <= rank <= peer_count |
| sector_percentile range | Formula guarantees 0.0 <= percentile <= 1.0 for peer_count >= 2 |
| peer_count >= 2 | Build logic skips groups below MIN_PEER_COUNT threshold |
| Rank 1 = percentile 1.0 | Formula: (peer_count - 1) / (peer_count - 1) = 1.0 always |
| No single-company sectors | Energy (XOM), Industrials (BA), Communication Services (NFLX) all have 1 company |
| peer_count accuracy | Build logic counts distinct CIKs per group |

## 7. Recommendations for DQ Rules

1. **P0 Uniqueness:** record_id must be unique (no duplicate grain)
2. **P0 Validity:** metric_source must be 'company_financials' or 'financial_ratios'
3. **P0 Referential Integrity:** Every cik must exist in source tables
4. **P0 Completeness:** No null metric_value, sector_rank, sector_avg, sector_median, sector_percentile
5. **P0 Range:** sector_rank between 1 and peer_count inclusive
6. **P0 Range:** sector_percentile between 0.0 and 1.0 inclusive
7. **P0 Threshold:** peer_count >= 2 for every row
8. **P0 Consistency:** Rank 1 must have percentile 1.0
9. **P0 Exclusion:** No rows from Energy, Industrials, or Communication Services
10. **P0 Accuracy:** peer_count matches actual distinct CIKs per group
