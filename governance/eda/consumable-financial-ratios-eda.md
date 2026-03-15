# EDA Report: Financial Ratios Source Data

**Date:** 2026-03-14
**Agent:** @data-analyst
**Source:** consumable.company_financials (26,894 rows)
**Spec:** consumable-financial-ratios

## Executive Summary

Profiled the 14 business terms that serve as numerators and denominators for the 7 planned financial ratios. Key findings: all 7 ratios are computable from existing data, coverage ranges from 9 to 20 companies, and one data quality edge case (negative Revenue for Apple Q1 2017) requires handling.

## Component Coverage Analysis

### Revenue (BT-022) — Denominator for 6 of 7 ratios

| Metric | Value |
|--------|-------|
| Companies | 20 |
| Total rows | 1,166 (FY+quarterly) |
| Min value | -$29M (Apple Q1 2017 — anomaly) |
| Max value | ~$611B (Walmart FY2024) |
| Negative values | 1 row (Apple Q1 2017) |

**Finding:** One negative Revenue value exists (Apple Q1 2017, -$29M). This is likely a data quality issue in the source XBRL — possibly a quarterly adjustment or misreported concept. CapEx-to-Revenue computation must handle this (negative denominator would produce negative ratio despite abs(numerator)).

### Gross Profit (BT-035) — Numerator for Gross Margin

| Metric | Value |
|--------|-------|
| Companies | 9 |
| Missing | JPM, GS, BRK.A (financials), AMZN, WMT, XOM, BA, INTC, V, UNH, NFLX |

**Finding:** Only 9 of 20 companies report Gross Profit as a separate line item. Banks and many other companies use a different P&L structure. This is expected and documented in the insight report.

### Operating Income (BT-036) — Numerator for Operating Margin

| Metric | Value |
|--------|-------|
| Companies | 18 |
| Missing | JPM, GS (banks use different P&L structure) |

### Net Income (BT-023) — Numerator for Net Margin

| Metric | Value |
|--------|-------|
| Companies | 20 |
| Negative values | Multiple (expected — operating losses for some companies in some periods) |

### Total Liabilities (BT-027) — Numerator for Debt-to-Equity

| Metric | Value |
|--------|-------|
| Companies | 20 |
| All positive | Yes |

### Stockholders Equity (BT-028) — Denominator for Debt-to-Equity

| Metric | Value |
|--------|-------|
| Companies | 20 |
| Negative values | Yes — Boeing has negative stockholders equity in recent years |

**Finding:** Boeing's negative equity is real (accumulated losses exceed paid-in capital). Debt-to-Equity will be negative for Boeing in those periods. This is a meaningful signal, not a data error.

### R&D Expense (BT-038) — Numerator for R&D Intensity

| Metric | Value |
|--------|-------|
| Companies | 12 |
| Missing | KO, PG, WMT, XOM, JPM, GS, BRK.A, V (non-R&D-intensive sectors) |

### SG&A Expense (BT-039) — Numerator for SGA Ratio

| Metric | Value |
|--------|-------|
| Companies | 17 |
| Missing | Some companies report operating expenses differently |

### Capital Expenditures (BT-043) — Numerator for CapEx-to-Revenue

| Metric | Value |
|--------|-------|
| Companies | 19 |
| All negative | Nearly all (cash outflow convention) |

**Finding:** CapEx is reported as a negative number (cash outflow). Must take abs() before dividing by Revenue.

## Ratio Feasibility Summary

| Ratio | Numerator | Denominator | Companies | Feasible |
|-------|-----------|-------------|-----------|----------|
| Gross Margin | BT-035 (9) | BT-022 (20) | 9 | Yes |
| Operating Margin | BT-036 (18) | BT-022 (20) | 18 | Yes |
| Net Margin | BT-023 (20) | BT-022 (20) | 20 | Yes |
| Debt-to-Equity | BT-027 (20) | BT-028 (20) | 20 | Yes |
| R&D Intensity | BT-038 (12) | BT-022 (20) | 12 | Yes |
| SGA Ratio | BT-039 (17) | BT-022 (20) | 17 | Yes |
| CapEx-to-Revenue | BT-043 (19) | BT-022 (20) | 19 | Yes |

## Edge Cases Requiring Build Logic

1. **Zero denominator:** Revenue = 0 should produce no ratio (unlikely but guard needed)
2. **Negative denominator with abs_numerator:** Revenue = -$29M with abs(CapEx) produces negative ratio — skip these rows
3. **Negative equity:** Boeing's negative stockholders equity produces negative Debt-to-Equity — allow (meaningful signal)
4. **Missing components:** Companies without Gross Profit, R&D, etc. simply don't get those ratio rows — honest coverage

## DQ Rule Recommendations

- Uniqueness on record_id (grain hash)
- Valid ratio_id enumeration (RATIO-001 through RATIO-007)
- Referential integrity on CIK (must exist in company_financials)
- No null ratio_value
- No zero denominator_val
- Correct numerator/denominator BT-ID pairing per ratio definition
- Accurate companies_reporting counts
- All 7 ratios represented
- CapEx-to-Revenue (RATIO-007) always non-negative
- Revenue-denominator consistency for margin ratios
