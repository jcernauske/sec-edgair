# EDA Report: Period-Over-Period Growth

**Agent:** @data-analyst
**Date:** 2026-03-15
**Source:** consumable.company_financials (26,894 rows, 20 companies, 25 business terms)
**Spec:** docs/specs/consumable-period-over-period.md

## Source Data Profile

### Year-over-Year Pair Availability
| Period Type | YoY Pairs | Notes |
|-------------|-----------|-------|
| FY | 6,323 | Strongest coverage — all 20 companies have 10+ consecutive FY years |
| Q1 | 5,651 | Slightly fewer — some companies start Q1 data later |
| Q2 | 6,331 | Near-identical to FY |
| Q3 | 6,385 | Highest quarterly count |
| **Total** | **24,690** | Every pair produces a yoy_change row; most produce yoy_pct_change |

### CAGR 5-Year Window Availability (FY only)
| Company | CAGR Pairs | First CAGR Year | Notes |
|---------|-----------|-----------------|-------|
| Johnson & Johnson | 296 | 2014 | Most pairs (25 terms x ~12 years) |
| Boeing | 294 | 2014 | |
| Procter & Gamble | 282 | 2014 | |
| Pfizer | 281 | 2014 | |
| Alphabet | 130 | 2020 | Fewest — data starts 2015, so first 5yr CAGR is 2020 |
| **Total** | **4,569** | | Across all 20 companies |

### Zero Values (Block YoY % Change)
| Business Term | Zero Count | Impact |
|---------------|-----------|--------|
| BT-046 Dividends Per Share | 11 | Companies that didn't pay dividends in some years. Prior=0 blocks pct change. |
| BT-033 Goodwill | 7 | Companies with no acquisitions. Prior=0 blocks pct change. |
| BT-037 Income Tax Expense | 2 | Tax benefit years. Minor. |
| BT-038 R&D Expense | 2 | Minor. |
| BT-023 Net Income | 1 | Single breakeven year. |
| BT-045 EPS Diluted | 1 | Single breakeven year. |
| **Total** | **24** | <0.1% of rows — negligible impact |

**Threshold evidence:** 24 zero values across 26,894 rows. Expected to block ~24 yoy_pct_change rows. No threshold adjustment needed.

### Negative Values (Sign-Change Transitions)
| Business Term | Negative Count | Companies | Sign-Change Risk |
|---------------|---------------|-----------|-----------------|
| BT-041 Investing CF | 986 | 20 | **High** — investing CF is predominantly negative (cash outflow). Sign changes are routine. |
| BT-042 Financing CF | 801 | 20 | **High** — financing CF oscillates between positive and negative. |
| BT-036 Operating Income | 159 | 12 | **Medium** — operating losses in downturns (Boeing, Intel). |
| BT-047 Comprehensive Income | 131 | 15 | **Medium** — AOCI swings. |
| BT-023 Net Income | 89 | 13 | **Medium** — net losses across 13 companies. Boeing, Intel most frequent. |
| BT-022 Revenue | 2 | 2 | **Low** — Apple Q1 2017 data quality issue (already known from financial-ratios EDA). |

**Threshold evidence:** Sign changes are common and expected. The `abs(prior_val)` denominator approach handles these correctly. No special filtering needed — sign-change growth values are meaningful financial signals.

### CAGR Base Value Analysis
- CAGR requires `base_val > 0`. Negative base values block CAGR computation.
- Most negative values are in cash flow terms (BT-040, BT-041, BT-042) and income terms (BT-023, BT-036).
- Estimated ~500-800 CAGR pairs will be blocked by negative base values.
- Expected usable CAGR rows: ~3,800-4,100.

## Row Count Estimates

| Growth Type | Estimated Rows | Basis |
|-------------|---------------|-------|
| yoy_change | ~24,690 | All YoY pairs (every consecutive year pair) |
| yoy_pct_change | ~24,666 | YoY pairs minus ~24 zero-prior-value cases |
| cagr_5yr | ~3,800-4,100 | 4,569 FY pairs minus negative-base exclusions |
| **Total** | **~53,000-53,500** | |

## DQ Threshold Recommendations

All rules should be P0 at 100% threshold:
- No zero-denominator tolerance (pct change should never have prior_val=0)
- No null growth_value tolerance
- CAGR base_val must always be > 0
- All 3 growth types must be represented
- All 25 business terms must appear in YoY rows
- companies_reporting accuracy must be exact

## Anomalies Noted
1. **Apple Q1 2017 negative Revenue** (-$29M) — already flagged in financial-ratios EDA. Will produce unusual YoY values for that period. Not a pipeline bug — the source data has this anomaly.
2. **Boeing negative equity** — Stockholders Equity went negative in 2019+. CAGR will be blocked for those base years (correct behavior). YoY growth values will be large and meaningful.
3. **Dividends Per Share = 0** — AMZN, META, TSLA, GOOGL don't pay dividends. Some years show 0 (started paying then stopped). YoY pct change blocked for these transitions.
