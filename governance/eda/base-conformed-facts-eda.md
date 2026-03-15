## EDA Report: base.conformed_facts (Source Data Profile)
**Source:** `base.financial_facts` (Iceberg table)
**Date:** 2026-03-15
**Agent:** @data-analyst
**Record Count:** 547,398 (source); 28,849 expected output grains
**Field Count:** 29 (source table)

### Key Findings

- **Source table is large but heavily filtered:** Of 547,398 rows in `base.financial_facts`, only 75,460 survive the filtering pipeline (supersession + mapping + FY + unit), and collision resolution reduces those to 28,849 unique grains.
- **49.3% of facts are superseded** — nearly half the table represents prior versions of facts replaced by later filings. This is the largest single filter.
- **70.1% of facts are unmapped** — 383,499 rows have NULL `business_term_id`, representing XBRL concepts not in the 25 mapped business terms. This is expected; the project maps only 25 core financial terms from ~3,000 distinct concepts.
- **Null fiscal year is 0%** — every row has a fiscal year, so this filter is a no-op. The `_derive_fiscal_year()` logic in the model catches all cases.
- **Collisions are pervasive:** 49.0% of grains (14,137 of 28,849) have more than one competing fact. This is not edge-case behavior — it is the norm, especially for income statement and comprehensive income terms.
- **BT-047 (Comprehensive Income) is extreme:** Up to 114 competing facts per grain due to dozens of OCI sub-concepts all mapping to the same business term. 99.4% of BT-047 grains have collisions.
- **Primary concept resolution handles 96% of collisions:** Of 14,137 collision grains, 13,492 (95.4%) are resolved by the PRIMARY_CONCEPTS priority list. Only 645 (4.6%) fall through to tier/frequency fallback.
- **Spec's expected row count is stale:** The spec says ~26,894 rows (matching an older `consumable.company_financials` build). Current data produces 28,849 grains. The spec should be updated.
- **All 20 companies and all 25 business terms are represented**, though coverage varies significantly by company (financial companies like JPMorgan and Goldman Sachs are missing 7-8 terms that don't apply to their business model).
- **Legacy CDE-XXX IDs still present in source:** The `LEGACY_CDE_TO_BT` normalization is still required at read time. All business_term_ids in the Iceberg table use the old CDE-XXX format.
- **21.8% of filtered values are negative** — expected for income statement items (losses), cash flow items (outflows), and per-share items (net losses per share). Not an anomaly.

### Filtering Pipeline Summary

| Step | Action | Rows Remaining | Rows Removed |
|------|--------|----------------|--------------|
| 0 | Source table | 547,398 | — |
| 1 | Legacy ID normalization (CDE→BT) | 547,398 | 0 (in-place) |
| 2 | `is_superseded = false` | 277,436 | 269,962 (49.3%) |
| 3 | `business_term_id IS NOT NULL` | ~75,930* | ~201,506 (unmapped) |
| 4 | `fiscal_year IS NOT NULL` | 75,930 | 0 (no nulls) |
| 5 | Unit matches PRIMARY_UNIT | 75,460 | 470 wrong-unit |
| 6 | Collision resolution (one per grain) | 28,849 | 46,611 (losing concepts) |

*Steps 2-4 applied together; 75,930 is the combined result of non-superseded + mapped + non-null FY.

### Section 1: Total Facts

- **Total rows:** 547,398
- **Fields:** 29 columns including fact_id, entity_id, cik, canonical_name, ticker, concept, business_term_id, business_term, financial_statement, category, tier, taxonomy, unit, val, start_date, end_date, fiscal_year, fiscal_period, fiscal_year_end, calendar_year, calendar_quarter, accession_number, form, filed_date, is_amendment, is_superseded, superseded_by, promoted_at, load_date

### Section 2: Superseded Facts

| Metric | Count | Percentage |
|--------|-------|------------|
| Superseded (`is_superseded = true`) | 269,962 | 49.32% |
| Not superseded | 277,436 | 50.68% |

Nearly half the table is superseded. This is expected — companies file amendments (10-K/A, 10-Q/A) and quarterly filings include restated prior-period figures, all of which create supersession chains.

### Section 3: Unmapped Facts

| Metric | Count | Percentage |
|--------|-------|------------|
| Unmapped (`business_term_id IS NULL`) | 383,499 | 70.06% |
| Mapped | 163,899 | 29.94% |

**Distinct unmapped concepts:** 2,947

Top 10 unmapped concepts (candidates for future business term mapping):

| Concept | Count |
|---------|-------|
| WeightedAverageNumberOfSharesOutstandingBasic | 3,745 |
| WeightedAverageNumberOfDilutedSharesOutstanding | 3,576 |
| InterestExpense | 2,949 |
| ShareBasedCompensation | 2,901 |
| AccumulatedOtherComprehensiveIncomeLossNetOfTax | 2,871 |
| IncomeLossFromContinuingOperationsBeforeIncomeTaxes... | 2,500 |
| PaymentsForRepurchaseOfCommonStock | 2,436 |
| ProfitLoss | 2,314 |
| AssetsCurrent | 2,283 |
| LiabilitiesCurrent | 2,283 |

### Section 4: Null Fiscal Year

| Metric | Count | Percentage |
|--------|-------|------------|
| Null fiscal_year | 0 | 0.00% |

The `_derive_fiscal_year()` function in `model.py` computes fiscal year from `end_date` for every row — there are no nulls. This filter step is technically a no-op but should remain as a defensive guard.

### Section 5: Unit Distribution

**Business terms with multiple units in source data:**

| Business Term | Units Present | Primary Unit |
|---------------|--------------|--------------|
| BT-022 (Revenue) | Rate, USD, pure | USD |
| BT-044 (EPS Basic) | USD/shares, pure | USD/shares |
| BT-045 (EPS Diluted) | USD/shares, pure | USD/shares |
| BT-046 (Dividends/Share) | USD, USD/shares, pure | USD/shares |

**Unit distribution (active, mapped facts):**

| Unit | Count | Percentage |
|------|-------|------------|
| USD | 71,163 | 93.8% |
| USD/shares | 4,732 | 6.2% |
| pure | 25 | 0.03% |
| Rate | 10 | 0.01% |

**470 rows removed by unit filtering** — mostly `pure` and `Rate` unit rows for revenue/EPS concepts that use non-standard units in some XBRL taxonomies.

### Section 6: Collision Frequency

After all filtering, **28,849 unique grains** exist at the (cik, business_term_id, fiscal_year, fiscal_period) level.

| Metric | Count | Percentage |
|--------|-------|------------|
| Single-fact grains (no collision) | 14,712 | 51.0% |
| Collision grains (>1 fact) | 14,137 | 49.0% |
| **Max collision size** | **114** | — |

**Collision size distribution:**

| Facts per Grain | Grains | Percentage | Cumulative % |
|-----------------|--------|------------|-------------|
| 1 | 14,712 | 51.00% | 51.00% |
| 2 | 8,030 | 27.83% | 78.83% |
| 3 | 1,927 | 6.68% | 85.51% |
| 4 | 1,543 | 5.35% | 90.86% |
| 5 | 509 | 1.76% | 92.62% |
| 6 | 538 | 1.86% | 94.49% |
| 7-10 | 677 | 2.35% | 96.83% |
| 11-20 | 592 | 2.05% | 98.89% |
| 21-50 | 273 | 0.95% | 99.83% |
| 51-114 | 48 | 0.17% | 100.00% |

**Key insight:** 78.8% of grains have 1-2 facts. The long tail (>10 facts per grain) is driven almost entirely by BT-047 (Comprehensive Income), which has dozens of OCI sub-concepts mapped to it.

### Section 7: Collision Stats by Business Term

| BT ID | Term | Total Grains | Collisions | Collision % | Max Size |
|-------|------|-------------|------------|-------------|----------|
| BT-022 | Revenue | 1,329 | 1,158 | 87.1% | 16 |
| BT-023 | Net Income | 1,329 | 1,056 | 79.5% | 13 |
| BT-024 | Assets | 1,298 | 17 | 1.3% | 4 |
| BT-027 | Liabilities | 1,309 | 978 | 74.7% | 5 |
| BT-028 | Stockholders Equity | 1,273 | 514 | 40.4% | 5 |
| BT-029 | Cash & Equivalents | 1,411 | 1,328 | 94.1% | 9 |
| BT-030 | Accounts Receivable | 931 | 71 | 7.6% | 4 |
| BT-031 | Inventory | 902 | 656 | 72.7% | 9 |
| BT-032 | PP&E | 1,175 | 597 | 50.8% | 6 |
| BT-033 | Goodwill | 1,116 | 540 | 48.4% | 5 |
| BT-034 | Cost of Revenue | 1,018 | 559 | 54.9% | 6 |
| BT-035 | Gross Profit | 480 | 168 | 35.0% | 3 |
| BT-036 | Operating Income | 1,156 | 992 | 85.8% | 8 |
| BT-037 | Income Tax | 1,390 | 1,252 | 90.1% | 13 |
| BT-038 | R&D Expense | 704 | 379 | 53.8% | 5 |
| BT-039 | SG&A Expense | 1,173 | 587 | 50.0% | 3 |
| BT-040 | Operating Cash Flow | 1,271 | 107 | 8.4% | 2 |
| BT-041 | Investing Cash Flow | 1,271 | 107 | 8.4% | 2 |
| BT-042 | Financing Cash Flow | 1,271 | 107 | 8.4% | 2 |
| BT-043 | CapEx | 1,231 | 223 | 18.1% | 4 |
| BT-044 | EPS Basic | 1,167 | 465 | 39.8% | 4 |
| BT-045 | EPS Diluted | 1,135 | 432 | 38.1% | 4 |
| BT-046 | Dividends/Share | 877 | 472 | 53.8% | 7 |
| BT-047 | Comprehensive Income | 1,338 | 1,330 | **99.4%** | **114** |
| BT-048 | Retained Earnings | 1,294 | 42 | 3.2% | 4 |

**Patterns:**
- **Low collision:** Balance sheet totals (BT-024 Assets 1.3%, BT-048 Retained Earnings 3.2%) — these are top-level XBRL concepts that rarely have alternatives.
- **Medium collision:** Cash flow statement items (~8.4%) — standardized concepts with few alternatives.
- **High collision:** Income statement items (BT-022 Revenue 87.1%, BT-036 Operating Income 85.8%, BT-037 Tax 90.1%) — many XBRL concept synonyms.
- **Extreme collision:** BT-047 Comprehensive Income (99.4%, max 114) — this term attracts all OCI sub-components, which is a mapping breadth issue.

### Section 8: Collision Resolution Outcomes

| Resolution Path | Grains | Percentage of All Grains |
|----------------|--------|--------------------------|
| sole_candidate | 14,712 | 51.00% |
| primary_concept | 13,492 | 46.77% |
| tier_frequency_fallback | 645 | 2.24% |

**Primary concept wins are dominated by:**

| Winning Concept | Times Won | Business Term |
|----------------|-----------|---------------|
| IncomeTaxExpenseBenefit | 1,240 | BT-037 |
| ComprehensiveIncomeNetOfTax | 1,226 | BT-047 |
| CashAndCashEquivalentsAtCarryingValue | 1,204 | BT-029 |
| NetIncomeLoss | 1,029 | BT-023 |
| Liabilities | 978 | BT-027 |
| OperatingIncomeLoss | 882 | BT-036 |
| Revenues | 612 | BT-022 |

**Tier/frequency fallback wins (645 grains):**

| Fallback Winner | Times Won |
|----------------|-----------|
| ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost | 110 |
| OtherNonoperatingIncomeExpense | 93 |
| OtherComprehensiveIncomeLossNetOfTax | 82 |
| SalesRevenueGoodsNet | 72 |
| InventoryForLongTermContractsOrPrograms | 61 |
| PropertyPlantAndEquipmentAndFinanceLeaseRightOfUseAssetAfterAccumulatedDepreciationAndAmortization | 46 |
| InventoryPartsAndComponentsNetOfReserves | 36 |
| NetIncomeLossAttributableToNoncontrollingInterest | 24 |

The fallback path handles industry-specific variants (e.g., Boeing's `InventoryForLongTermContractsOrPrograms` instead of `InventoryNet`, or R&D expense variants that exclude acquired in-process costs).

### Section 9: Expected Output Row Count

| Metric | Count |
|--------|-------|
| Expected `base.conformed_facts` rows | 28,849 |
| Current `consumable.company_financials` rows | 28,849 |
| Spec's stated expected count | ~26,894 |

**Discrepancy:** The spec says ~26,894 rows but both the EDA pipeline simulation and the current consumable table produce 28,849 rows. The spec's number appears to be from an earlier data load. The spec should be updated to ~28,849.

### Section 10: Companies and Terms Coverage

**20 distinct CIKs** (all in scope):

| Company | CIK | Terms Covered | Missing Terms |
|---------|-----|---------------|---------------|
| Apple Inc. | 320193 | 25/25 | — |
| Microsoft Corporation | 789019 | 25/25 | — |
| Intel Corporation | 50863 | 25/25 | — |
| Johnson & Johnson | 200406 | 25/25 | — |
| The Boeing Company | 12927 | 25/25 | — |
| Alphabet Inc. | 1652044 | 24/25 | BT-035 |
| The Coca-Cola Company | 21344 | 24/25 | BT-038 |
| Pfizer Inc. | 78003 | 24/25 | BT-035 |
| Procter & Gamble Company | 80424 | 24/25 | BT-035 |
| Tesla Inc. | 1318605 | 24/25 | BT-046 |
| Meta Platforms Inc. | 1326801 | 23/25 | BT-031, BT-035 |
| Exxon Mobil Corporation | 34088 | 23/25 | BT-034, BT-035 |
| Walmart Inc. | 104169 | 23/25 | BT-035, BT-038 |
| UnitedHealth Group | 731766 | 23/25 | BT-035, BT-038 |
| Amazon.com Inc. | 1018724 | 23/25 | BT-038, BT-046 |
| Netflix Inc. | 1065280 | 21/25 | BT-030, BT-031, BT-033, BT-046 |
| Visa Inc. | 1403161 | 19/25 | BT-031, BT-034, BT-035, BT-038, BT-044, BT-045 |
| The Goldman Sachs Group | 886982 | 18/25 | BT-030, BT-031, BT-034, BT-035, BT-036, BT-038, BT-039 |
| JPMorgan Chase & Co. | 19617 | 17/25 | BT-030, BT-031, BT-034, BT-035, BT-036, BT-038, BT-039, BT-043 |
| Berkshire Hathaway Inc. | 1067983 | 17/25 | BT-030, BT-032, BT-034, BT-035, BT-038, BT-039, BT-045, BT-046 |

**Missing term patterns:**
- **BT-035 (Gross Profit):** Missing from 11 companies — many use different reporting structures (especially financials, energy, healthcare).
- **BT-038 (R&D Expense):** Missing from 7 companies — consumer staples, financials, and energy companies may not report R&D separately.
- **BT-031 (Inventory):** Missing from 5 companies — service/tech/financial companies without physical inventory.
- **Financial sector (JPMorgan, Goldman, Berkshire):** Missing 7-8 terms because banks use different financial statement structures (no COGS, no gross profit, no SG&A, etc.).

**Grains per business_term_id:**

| BT ID | Grains | Notes |
|-------|--------|-------|
| BT-029 (Cash) | 1,411 | Highest — balance sheet item reported every quarter |
| BT-037 (Tax) | 1,390 | |
| BT-047 (Comp Income) | 1,338 | |
| BT-022 (Revenue) | 1,329 | |
| BT-023 (Net Income) | 1,329 | |
| BT-027 (Liabilities) | 1,309 | |
| BT-024 (Assets) | 1,298 | |
| BT-048 (Retained Earnings) | 1,294 | |
| BT-040/041/042 (Cash Flows) | 1,271 each | |
| BT-043 (CapEx) | 1,231 | |
| BT-032 (PP&E) | 1,175 | |
| BT-039 (SG&A) | 1,173 | |
| BT-036 (Operating Income) | 1,156 | |
| BT-044 (EPS Basic) | 1,167 | |
| BT-045 (EPS Diluted) | 1,135 | |
| BT-033 (Goodwill) | 1,116 | |
| BT-034 (COGS) | 1,018 | |
| BT-030 (AR) | 931 | Lower — not all companies report AR separately |
| BT-031 (Inventory) | 902 | |
| BT-046 (Dividends/Share) | 877 | Not all companies pay dividends |
| BT-038 (R&D) | 704 | Lowest of IS items — sector-dependent |
| BT-035 (Gross Profit) | 480 | Lowest — many companies don't use GrossProfit concept |

### Section 11: Edge Cases

#### Values

| Observation | Count | Percentage |
|-------------|-------|------------|
| Zero values | 1,519 | 2.01% |
| Negative values | 16,460 | 21.81% |
| NULL values | 0 | 0.00% |

**Value distribution (filtered set, 75,460 rows):**

| Percentile | Value |
|------------|-------|
| Min | -$312,447,000,000 |
| p1 | -$13,450,000,000 |
| p25 | $0.61 |
| p50 | $638,000,000 |
| p75 | $9,344,000,000 |
| p99 | $450,526,000,000 |
| Max | $4,560,205,000,000 |

- **p25 = $0.61** indicates per-share values (EPS, dividends) at the low end
- **Negative values are expected:** Operating losses (Tesla early years), net cash outflows (investing/financing activities), tax benefits, etc.
- **Max $4.56T** is Berkshire Hathaway or JPMorgan total assets — reasonable for the largest financial institutions

#### Fiscal Period Distribution

| Period | Count | Percentage |
|--------|-------|------------|
| Q3 | 22,337 | 29.60% |
| Q2 | 21,793 | 28.88% |
| FY | 18,407 | 24.39% |
| Q1 | 12,923 | 17.13% |

**Q1 underrepresentation:** Q1 has noticeably fewer facts (17.1%) than Q2/Q3 (28-30%). This is because many Q1 filings only report the current quarter, while Q2/Q3 filings include cumulative YTD figures that expand the fact count. FY being 24.4% is expected — annual filings include all duration-based facts.

#### Fiscal Year Range

| Metric | Value |
|--------|-------|
| Earliest | 2006 |
| Latest | 2026 |
| Peak years | 2023-2024 (~4,750 facts each) |
| Earliest sparse | 2006 (25 facts), 2007 (344 facts) |
| Current year | 2026 (478 facts — partial year) |

Ramp-up from 2006-2010 reflects XBRL adoption becoming mandatory for large filers.

#### Duplicate Fact IDs

**0 duplicate fact_ids** in the filtered set — the deterministic SHA-256 hashing produces unique identifiers.

### Section 12: Anomalies

| Field/Pattern | Type | Count | Severity | Details |
|---------------|------|-------|----------|---------|
| BT-047 max collision 114 | Mapping breadth | ~50 grains with >50 competing facts | Low | OCI sub-concepts all map to BT-047; collision resolution correctly picks `ComprehensiveIncomeNetOfTax` via primary list |
| 470 wrong-unit facts surviving to step 5 | Data quality | 470 | Low | Revenue tagged as `pure` or `Rate` (10 facts); EPS tagged as `pure` (25 facts); Dividends tagged as `USD` instead of `USD/shares` |
| BT-035 only 480 grains | Coverage gap | 480 vs ~1,300 average | Info | `GrossProfit` is the only mapped concept; many companies report gross margin differently or not at all |
| Q1 underrepresentation (17.1%) | Temporal skew | 12,923 vs ~21,000 avg | Info | Expected behavior from XBRL quarterly filing patterns |
| 2006 has only 25 facts | Temporal edge | 25 | Info | Pre-XBRL mandate; likely partial/voluntary filers only |
| Tier 2 facts dominate collisions | Resolution quality | 36,895 tier-2 vs 23,853 tier-1 in collision groups | Info | Many competing facts are tier-2 (alternatives); tier-1 concepts in PRIMARY_CONCEPTS list correctly win |

### Edge Cases for DQ Thresholds

| Observation | Count | Percentage | Recommendation |
|-------------|-------|------------|----------------|
| Expected output row count | 28,849 | — | P0: Row count between 25,000-35,000 (allow for data growth) |
| Unique grain (cik, bt, fy, fp) | 28,849 unique | 100% | P0: Zero duplicates at grain level |
| All 20 companies present | 20/20 | 100% | P0: Exactly 20 distinct CIKs |
| All 25 BTs present | 25/25 | 100% | P0: All 25 business_term_ids represented |
| selection_reason distribution | 51%/47%/2% | — | P1: sole_candidate >= 40%, primary_concept >= 30%, tier_frequency_fallback <= 10% |
| competing_fact_count >= 1 | 28,849 | 100% | P0: No rows with competing_fact_count < 1 |
| source_fact_id referential integrity | — | — | P0: Every source_fact_id must exist in base.financial_facts |
| val consistency | — | — | P1: val in conformed_facts matches val in financial_facts for source_fact_id |
| Zero values | 1,519 | 2.01% | P2: Zero values <= 5% (some zeros are legitimate) |
| Negative values | 16,460 | 21.81% | Info only — expected for losses/outflows; do NOT flag |
| NULL val | 0 | 0% | P0: No NULL values in val column |
| Fiscal year coverage | 2006-2026 | — | P1: Min fiscal_year <= 2010, max fiscal_year >= current_year - 1 |
| Per-company minimum terms | 17/25 (Berkshire, JPMorgan) | 68% | P2: Every company has >= 15 business terms |
| BT-035 low coverage | 480 grains | 1.7% of total | Info: expected; not a data quality issue |

### Cross-Field Analysis

1. **selection_reason vs competing_fact_count:** When `competing_fact_count = 1`, `selection_reason` must be `sole_candidate`. When `competing_fact_count > 1`, it must be `primary_concept` or `tier_frequency_fallback`. These are structurally coupled.

2. **Business term vs unit:** After unit filtering, every BT-044/BT-045/BT-046 row must have `unit = 'USD/shares'` and all other BTs must have `unit = 'USD'`. This is enforced by the filtering logic but should be validated post-write.

3. **Financial sector missing terms:** JPMorgan (17/25), Goldman Sachs (18/25), and Berkshire (17/25) consistently miss the same terms (COGS, Gross Profit, SG&A, AR, Inventory, R&D). This is structurally correct — banks don't have these line items.

4. **Fiscal period vs start_date:** FY rows have ~350-366 day durations; quarterly rows have ~88-93 day durations. The `_derive_fiscal_period()` function handles this, but conformed_facts does not carry start_date (by design — the grain is fiscal period, not date range).
