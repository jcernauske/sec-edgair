# Base Zone: Fiscal Year Derivation Fix

## Status: 🟢 COMPLETE

| Status | Meaning |
|--------|---------|
| 🟡 DRAFT | Riffing / initial design |
| 🟢 COMPLETE | Shipped |

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-03-15 |
| Author | Jeff + Claude Code |
| Spec Version | 1.0 |
| Last Updated | 2026-03-15 |
| Zone | Base (with cascade to Consumable + AI-Ready) |
| Primary Agent | @primary-agent |
| Blocked By | — |
| Depends On | — |

---

## Claude Code Prompt

```
Fix the fiscal year derivation bug in the base zone pipeline.

The XBRL `fy` field reflects the FILING fiscal year (when the 10-K was filed),
not the REPORTING fiscal year (what period the data covers). Apple's FY2025 10-K
includes comparative data for FY2024 and FY2023, and all three rows get fy=2025.

The fix: derive fiscal_year from end_date, not from the XBRL frame's fy field.
Then rebuild all downstream tables.
```

---

## 1. The Bug

### What's Wrong

The `fiscal_year` field in `base.financial_facts` is derived from the XBRL filing's `fy` (frame fiscal year) field. This field indicates **which 10-K filing the data came from**, not **which fiscal year the data describes**.

Example — Apple's FY2025 10-K (filed Oct 2025) contains comparative data:

| XBRL fy | end_date | val | What it actually is |
|---------|----------|-----|-------------------|
| 2025 | 2025-09-27 | $416.2B | FY2025 Revenue |
| 2025 | 2024-09-28 | $391.0B | FY2024 Revenue (comparative) |
| 2025 | 2023-09-30 | $383.3B | FY2023 Revenue (comparative) |

Our pipeline assigns `fiscal_year=2025` to all three rows from the FY2025 filing. After supersession filtering, the latest filing wins, so our "FY2023" row gets the value from the FY2023 filing ($365.8B from end_date 2021-09-25) instead of the correct FY2023 comparative value ($383.3B from end_date 2023-09-30).

### Impact

- **Every fiscal_year value in the pipeline is potentially wrong** — offset varies by company and filing
- Verified mismatches against known 10-K figures: Apple Revenue off by 4.6%, Tesla Revenue off by 44%, Amazon Revenue off by 18%
- All downstream consumable tables inherit the wrong fiscal_year
- YoY growth calculations compare wrong year pairs
- CAGR calculations use wrong base years
- Peer comparison ranks are comparing different actual periods

### Root Cause

In `src/base/financial_facts_model/build.py` (or wherever fiscal_year is assigned), the pipeline uses the XBRL frame's `fy` field. SEC EDGAR XBRL data includes the `fy` field in the frame identifier (e.g., `CY2023Q4I`), but this reflects the filing context, not the period end.

## 2. The Fix

### Derive fiscal_year from end_date

For each fact row, compute fiscal_year based on `end_date` and the company's `fiscal_year_end` (MMDD from entity_mappings):

```python
def derive_fiscal_year(end_date: date, fiscal_year_end_mmdd: str) -> int:
    """Derive the fiscal year from the period end date.

    For December FY companies: FY = end_date.year
    For non-December FY companies: FY = end_date.year if end_date month >= FY end month,
                                   else end_date.year + 1 for companies where FY spans calendar years

    Examples:
      Apple (FY ends Sep): end_date 2024-09-28 -> FY2024
      Apple (FY ends Sep): end_date 2024-06-29 -> FY2024 (Q3 of Apple's FY2024)
      Walmart (FY ends Jan): end_date 2024-01-31 -> FY2024
      Microsoft (FY ends Jun): end_date 2024-06-30 -> FY2024
    """
    fy_end_month = int(fiscal_year_end_mmdd[:2])

    if fy_end_month == 12:
        # December FY: fiscal_year = calendar year of end_date
        return end_date.year

    # Non-December FY: the fiscal year is the year containing the FY end
    # If end_date is after the FY end month, it belongs to FY = end_date.year + 1
    # If end_date is at or before the FY end month, it belongs to FY = end_date.year
    if end_date.month > fy_end_month:
        return end_date.year + 1
    else:
        return end_date.year
```

### Rebuild Cascade

After fixing fiscal_year in base.financial_facts:

1. **Rebuild base.financial_facts** — new fiscal_year values
2. **Rebuild base.fiscal_calendar** — derived from financial_facts
3. **Rebuild base.amendment_tracking** — references fiscal periods
4. **Rebuild all 5 consumable tables** — all derived from base
5. **Re-run all 92 DQ rules** — verify everything still passes
6. **Re-run verification script** — confirm figures match known 10-K values

### What Does NOT Change

- `end_date` — stays the same (this is correct in the source data)
- `val` — stays the same (the values are correct, just assigned to wrong years)
- `concept` — stays the same
- Schema — no new fields, no field removals
- DQ rules — same rules, re-executed against corrected data

## 3. Verification Plan

After the fix, re-run the verification script. Expected results:

| Company | Metric | FY | Expected | Should Match? |
|---------|--------|-----|----------|--------------|
| AAPL | Revenue | 2023 | $383.3B | Yes — from comparative data in FY2025 filing |
| AAPL | Net Income | 2023 | $97.0B | Yes |
| TSLA | Revenue | 2023 | $96.8B | Yes — was off by 44% |
| AMZN | Revenue | 2023 | $574.8B | Yes — was off by 18% |
| MSFT | Revenue | 2024 | $245.1B | Yes — was picking wrong concept |
| BA | Net Income | 2023 | -$2.2B | Yes — was off by 89% |

## 4. Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Rebuild drops existing Iceberg data | Existing data is deterministically reproducible from raw zone. No data loss risk. |
| DQ rules might fail after rebuild | Expected — some rules depend on specific row counts or year ranges. Fix rules if needed. |
| Fiscal year derivation edge cases | Unit test every company's FY end pattern (Sep, Jun, Jan, Dec) against known years. |
| Calendar_year and calendar_quarter also wrong | These are derived from end_date directly, not from fiscal_year. Should already be correct. Verify. |

## 5. Implementation Order

1. Write and test `derive_fiscal_year()` function with unit tests for all FY-end patterns
2. Update base.financial_facts build to use new derivation
3. Rebuild base zone tables
4. Rebuild all consumable tables
5. Re-run all 92 DQ rules
6. Run verification script
7. If all pass: commit, push

## 6. Results

### Verification: 15/16 match (was 5/16 before fix)

| Company | Metric | FY | Before Fix | After Fix | Status |
|---------|--------|-----|-----------|-----------|--------|
| AAPL | Revenue | 2023 | $365.8B (4.6% off) | $383.3B (0.00%) | FIXED |
| AAPL | Net Income | 2023 | $94.7B (2.4% off) | $97.0B (0.00%) | FIXED |
| AAPL | Total Assets | 2023 | $352.8B (0.05%) | $352.6B (0.00%) | OK |
| AAPL | EPS Diluted | 2023 | $5.61 (8.5% off) | $6.13 (0.00%) | FIXED |
| MSFT | Revenue | 2024 | $275.0B (12.2% off) | $245.1B (0.00%) | FIXED |
| MSFT | Net Income | 2024 | MISSING | $88.1B (0.00%) | FIXED |
| MSFT | Operating Income | 2024 | MISSING | $109.4B (0.00%) | FIXED |
| AMZN | Revenue | 2023 | $469.8B (18.3% off) | $574.8B (0.00%) | FIXED |
| AMZN | Net Income | 2023 | $33.4B (9.7% off) | $4.3B (85.9% off) | KNOWN ISSUE |
| JPM | Revenue | 2023 | $121.6B (23.1% off) | $158.1B (0.00%) | FIXED |
| JPM | Net Income | 2023 | $48.3B (2.5% off) | $49.6B (0.00%) | FIXED |
| JPM | Total Assets | 2023 | $3.7T (3.4% off) | $3.9T (0.00%) | FIXED |
| TSLA | Revenue | 2023 | $53.8B (44.4% off) | $96.8B (0.00%) | FIXED |
| TSLA | Net Income | 2023 | $5.5B (63.2% off) | $15.0B (0.00%) | FIXED |
| BA | Net Income | 2023 | ($4.2B) (89.1% off) | ($2.2B) (0.00%) | FIXED |
| BA | Stockholders Equity | 2023 | ($15.9B) (7.8% off) | ($17.2B) (0.00%) | FIXED |

### Known Remaining Issue: Amazon Net Income

Amazon's XBRL filings include trailing-twelve-month (TTM) values in quarterly 10-Q filings. These TTM values have 364-day durations and are tagged as FY by SEC EDGAR. Our fiscal_period derivation correctly identifies them as FY (duration >= 350 days), but the concept collision resolution in `consumable.company_financials` picks the TTM ending March 2023 ($4.3B) instead of the calendar year FY2023 (Jan-Dec, $30.4B).

**Root cause:** When multiple FY rows exist for the same (cik, business_term, fiscal_year), the concept collision resolution should prefer the row whose start_date aligns with the company's actual fiscal year start. For Amazon (Dec FY), the correct FY row has start_date near Jan 1.

**Fix:** A separate spec (`base-ttm-disambiguation`) should add start_date alignment to concept collision resolution. This affects companies that file 10-Qs with TTM income statement data.

## 7. Changes Made

### Files Modified
| File | What Changed |
|------|-------------|
| `src/base/financial_facts_model/model.py` | Added `_derive_fiscal_year()` and `_derive_fiscal_period()` functions; replaced XBRL fy/fp with derived values |
| `src/base/financial_facts_model/fiscal_calendar.py` | Updated to use same `_derive_fiscal_year()` and `_derive_fiscal_period()` instead of raw XBRL fy/fp |
