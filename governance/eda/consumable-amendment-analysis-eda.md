# EDA Report: Amendment Analysis Source Data

**Date:** 2026-03-15
**Agent:** @data-analyst
**Source:** base.amendment_tracking (239,127 rows) + consumable.company_financials (20 companies)
**Spec:** consumable-amendment-analysis

## Executive Summary

Profiled base.amendment_tracking (239,127 rows across 20 companies) to inform the consumable.amendment_analysis aggregation. Key findings: all 20 companies have amendments, fiscal years span 2006-2025, val_change_pct has 4,661 null values (1.9%), and days_to_amend ranges from small corrections filed within days to restatements filed years later.

## Source Data Profile

### Volume
| Metric | Value |
|--------|-------|
| Total rows | 239,127 |
| Distinct companies (CIK) | 20 |
| Distinct XBRL concepts | 2,688 |
| Distinct amendment filings | 1,267 |
| Fiscal year range | 2006 - 2025 |

### Per-Company Distribution
| Company (CIK) | Ticker | Count | Share |
|---------------|--------|-------|-------|
| 19617 | JPM | 21,317 | 8.9% |
| 886982 | GS | 15,850 | 6.6% |
| 12927 | BA | 15,278 | 6.4% |
| 21344 | KO | 14,465 | 6.0% |
| 789019 | MSFT | 13,798 | 5.8% |
| 78003 | PFE | 13,061 | 5.5% |
| 80424 | PG | 12,889 | 5.4% |
| 50863 | INTC | 12,165 | 5.1% |
| 104169 | WMT | 12,155 | 5.1% |
| 731766 | UNH | 12,098 | 5.1% |
| 200406 | JNJ | 11,937 | 5.0% |
| 320193 | AAPL | 11,563 | 4.8% |
| 1318605 | TSLA | 10,466 | 4.4% |
| 1018724 | AMZN | 10,222 | 4.3% |
| 1065280 | NFLX | 9,734 | 4.1% |
| 34088 | XOM | 9,584 | 4.0% |
| 1403161 | V | 9,450 | 4.0% |
| 1652044 | GOOGL | 8,430 | 3.5% |
| 1067983 | BRK.A | 7,488 | 3.1% |
| 1326801 | META | 7,177 | 3.0% |

### Fiscal Year Distribution (from end_date)
| Fiscal Year | Count |
|-------------|-------|
| 2006 | 2 |
| 2007 | 118 |
| 2008 | 2,269 |
| 2009 | 7,518 |
| 2010 | 12,613 |
| 2011 | 13,900 |
| 2012 | 14,878 |
| 2013 | 15,310 |
| 2014 | 16,036 |
| 2015 | 15,751 |
| 2016 | 14,961 |
| 2017 | 15,791 |
| 2018 | 15,858 |
| 2019 | 15,828 |
| 2020 | 15,161 |
| 2021 | 15,382 |
| 2022 | 15,903 |
| 2023 | 16,949 |
| 2024 | 14,167 |
| 2025 | 732 |

**Finding:** Fiscal year 2006 has only 2 rows and 2025 has 732 rows -- these are edges. The bulk of the data is 2008-2024 with 13K-17K rows per year.

### Magnitude Analysis
| Metric | Value |
|--------|-------|
| AVG(ABS(val_change)) | $553,626,344 |
| val_change_pct non-null | 234,466 (98.1%) |
| val_change_pct null | 4,661 (1.9%) |

**Finding:** 4,661 rows (1.9%) have null val_change_pct. These occur when original_val is 0. The mean_pct_change and median_pct_change fields must be nullable.

### Days-to-Amend Analysis
| Metric | Value |
|--------|-------|
| Date type | amendment_filed_date - original_filed_date yields BIGINT (days) |
| Sample values | 573, 478, 370, 374, 367 days |
| Min amendment_filed_date | 2009-10-21 |
| Max amendment_filed_date | 2026-03-13 |
| Min original_filed_date | 2009-07-22 |
| Max original_filed_date | 2025-12-03 |

**Finding:** Days-to-amend is always positive (amendments filed after originals). Values range from near-zero to multi-year gaps.

## Expected Output

- **Estimated rows:** ~340 (20 companies x ~17 years)
- **All 20 companies** are represented in amendment_tracking
- **Company metadata join:** All 20 CIKs exist in both amendment_tracking and company_financials

## DQ Rule Recommendations

- Uniqueness on record_id (grain hash)
- Referential integrity on CIK (must exist in company_financials)
- No null amendment_count
- amendment_count > 0 (only years with amendments produce rows)
- Non-negative magnitude stats (mean_abs_change, median_abs_change >= 0)
- max_abs_change >= median_abs_change
- distinct_concepts <= amendment_count
- All 20 companies represented
- total_val_impact >= max_abs_change
