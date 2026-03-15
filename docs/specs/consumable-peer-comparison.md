# Consumable Zone: Peer Comparison

## Status: 🟢 COMPLETE

| Status | Meaning |
|--------|---------|
| 🟡 DRAFT | Riffing / initial design |
| 🔵 ARCH REVIEW | Awaiting @governance-reviewer approval |
| 🟠 IMPLEMENTATION | Agent pipeline running |
| 🟣 TESTING | DQ rules and validation |
| 🔴 CODE REVIEW | Reviewing |
| ✅ VERIFICATION | Build + DQ + governance verification |
| 🟢 COMPLETE | Shipped |
| ⚫ BLOCKED | Escalated to human |

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-03-15 |
| Author | Jeff + Claude Code |
| Spec Version | 1.0 |
| Last Updated | 2026-03-15 |
| Zone | Consumable |
| Primary Agent | @primary-agent |
| Blocked By | — |
| Depends On | `consumable-company-financials` (🟢 COMPLETE), `consumable-financial-ratios` (🟢 COMPLETE) |
| Informed By | `governance/insights/base-to-consumable-insights.md` (@insight-manager, item #6) |

---

## Claude Code Prompt

```
Implement the consumable-peer-comparison spec.

This is the fourth consumable zone table — sector-level peer rankings derived from
consumable.company_financials and consumable.financial_ratios. For each (company,
metric, year, period), it computes the company's rank within its sector, the sector
average, sector median, and the company's percentile. One row per (company, metric,
year, period, metric_source).

Follow the full Base & Consumable Zone Pipeline (greenfield mode) from CLAUDE.md.
```

---

## 1. Feature Description

### Problem Statement

`consumable.company_financials` and `consumable.financial_ratios` give absolute and relative metrics, but lack context. Apple's Net Margin of 24.6% is meaningless without knowing the Technology sector average is 19.1% and Apple ranks #2 of 5. "Is this number good?" is unanswerable without peer context. Today, computing sector rankings requires GROUP BY sector with window functions, joining company_financials and financial_ratios, and knowing which metrics are comparable across sectors.

### User Story

As a financial analyst (or LLM), I want to query "Apple's revenue rank in Technology for FY2024" or "which company has the highest net margin percentile in its sector" without computing sector statistics manually.

### Success Criteria

- [ ] `consumable.peer_comparison` table with one row per (company, metric_id, fiscal_year, fiscal_period, metric_source)
- [ ] Two metric sources: `company_financials` (absolute values) and `financial_ratios` (ratio values)
- [ ] Rank within sector (1 = highest value)
- [ ] Sector average and sector median
- [ ] Percentile within sector (0.0 to 1.0)
- [ ] Peer count (companies in sector with this metric)
- [ ] Only computed where sector has 2+ companies for this metric
- [ ] Company and sector metadata denormalized
- [ ] Dedup guard on promote (no duplicates on re-run)
- [ ] load_date on every row
- [ ] All DQ rules pass
- [ ] All governance artifacts produced

## 2. Technical Design

### 2.1 Metric Sources

The table ranks companies on two types of metrics:

| Source | Table | Metric ID Field | Value Field | Example |
|--------|-------|----------------|-------------|---------|
| `company_financials` | consumable.company_financials | business_term_id (BT-022..BT-048) | val | Revenue = $394B |
| `financial_ratios` | consumable.financial_ratios | ratio_id (RATIO-001..RATIO-007) | ratio_value | Net Margin = 0.246 |

### 2.2 Iceberg Table

#### `consumable.peer_comparison` — Sector-Level Peer Ranking Table

Grain: **(cik, metric_id, fiscal_year, fiscal_period, metric_source)**

| Field | Type | Required | Source |
|-------|------|----------|--------|
| record_id | String | Yes | Deterministic SHA-256 hash of grain fields |
| cik | Integer | Yes | Source table cik |
| entity_id | String | Yes | Source table entity_id |
| ticker | String | No | Source table ticker |
| canonical_name | String | Yes | Source table canonical_name |
| sector | String | Yes | Source table sector |
| metric_source | String | Yes | `company_financials` or `financial_ratios` |
| metric_id | String | Yes | business_term_id (BT-XXX) or ratio_id (RATIO-XXX) |
| metric_name | String | Yes | Human-readable metric name |
| metric_value | Double | Yes | The company's value for this metric |
| sector_rank | Integer | Yes | Rank within sector (1 = highest value) |
| sector_avg | Double | Yes | Average value across sector peers |
| sector_median | Double | Yes | Median value across sector peers |
| sector_percentile | Double | Yes | Percentile within sector (0.0 to 1.0) |
| peer_count | Integer | Yes | Number of companies in sector with this metric |
| fiscal_year | Integer | Yes | Fiscal year |
| fiscal_period | String | Yes | FY/Q1/Q2/Q3 |
| fiscal_year_end | String | No | Company's fiscal year end (MMDD) |
| period_end_date | Date | Yes | End date of reporting period |
| calendar_year | Integer | Yes | Calendar year of period_end_date |
| calendar_quarter | Integer | Yes | Calendar quarter |
| promoted_at | Timestamptz | Yes | When written to consumable |
| load_date | Date | Yes | System date tracking |

### 2.3 Computation Rules

1. **Read** `consumable.company_financials` and `consumable.financial_ratios`
2. **Normalize** both into a common structure: (cik, sector, metric_id, metric_name, metric_value, fiscal_year, fiscal_period, metric_source, + metadata)
3. **Group** by (sector, metric_id, fiscal_year, fiscal_period, metric_source)
4. **Skip** groups with fewer than 2 companies — peer comparison needs at least 2
5. For each group:
   - **Rank** by metric_value descending (1 = highest). Ties get the same rank.
   - **Average** = mean of all values in the group
   - **Median** = middle value (or average of two middle values)
   - **Percentile** = `(peer_count - rank) / (peer_count - 1)` for peer_count > 1. Highest value gets 1.0, lowest gets 0.0.
   - **Peer count** = distinct companies in the group
6. Emit one row per company in the group

### 2.4 Ranking Direction

All metrics rank **highest value = rank 1**. This is correct for:
- Revenue, Net Income, Margins, Cash Flow, EPS (higher is better)
- Debt-to-Equity (higher means more leverage — rank 1 = most leveraged, which is a factual ranking, not a value judgment)
- CapEx-to-Revenue (higher means more capital intensity)

The table is descriptive, not prescriptive. Rank 1 means "highest value," not "best." Consumers interpret meaning based on context.

### 2.5 Edge Cases

| Case | Handling |
|------|----------|
| Sector with 1 company (Energy=XOM, Industrials=BA, Comm Services=NFLX) | No peer_comparison rows. Peer comparison requires 2+ companies. |
| Tied values | Same rank. Percentile is based on rank position. |
| Negative values (Net Income losses) | Ranked normally. A loss of -$1B ranks below a loss of -$500M (which ranks below $0). |
| Missing metric for a company in a sector | Company is excluded from that metric's group. Peer count reflects actual participants. |
| Financial sector companies missing some ratios | JPM/GS/BRK.A won't appear in Gross Margin rankings. They'll appear in metrics they have. |

### 2.6 Module Structure

```
src/consumable/
    peer_comparison/
        __init__.py
        config.py              # Paths, grain fields, minimum peer count
        schema.py              # PEER_COMPARISON_SCHEMA (23 fields)
        build.py               # Core: read both tables, normalize, rank
        promote.py             # Write to Iceberg with dedup guard
        cli.py                 # build, status, coverage, all
```

## 3. CLI Commands

```
python -m src.consumable.peer_comparison.cli build     # build the table
python -m src.consumable.peer_comparison.cli status    # show table stats
python -m src.consumable.peer_comparison.cli coverage  # sector x metric coverage matrix
python -m src.consumable.peer_comparison.cli all       # build + status + coverage
```

## 4. DQ Rules

| Rule | Description | Priority | Threshold |
|------|-------------|----------|-----------|
| CONS-PC-001 | record_id is unique (no duplicate grain) | P0 | 100% |
| CONS-PC-002 | Every row has valid metric_source (company_financials or financial_ratios) | P0 | 100% |
| CONS-PC-003 | Every row has valid cik (matches source tables) | P0 | 100% |
| CONS-PC-004 | No null metric_value, sector_rank, sector_avg, sector_median, sector_percentile | P0 | 100% |
| CONS-PC-005 | sector_rank is between 1 and peer_count (inclusive) | P0 | 100% |
| CONS-PC-006 | sector_percentile is between 0.0 and 1.0 (inclusive) | P0 | 100% |
| CONS-PC-007 | peer_count >= 2 for every row (minimum peer threshold) | P0 | 100% |
| CONS-PC-008 | sector_rank 1 has sector_percentile 1.0 | P0 | 100% |
| CONS-PC-009 | No single-company sectors (Energy, Industrials, Communication Services excluded) | P0 | 100% |
| CONS-PC-010 | peer_count matches actual distinct CIKs per (sector, metric_id, fiscal_year, fiscal_period, metric_source) | P0 | 100% |

## 5. Expected Output

Based on data profiling:
- **Sectors with 2+ companies:** Technology (5), Financials (4), Healthcare (3), Consumer Staples (3), Consumer Discretionary (2) = 5 sectors, 17 companies
- **Excluded sectors (1 company):** Energy, Industrials, Communication Services = 3 companies
- **Company_financials metrics:** 25 business terms x ~4 periods x ~16 years x varying company count per sector
- **Financial_ratios metrics:** 7 ratios x ~4 periods x ~16 years x varying company count per sector
- **Estimated total:** ~60,000-80,000 rows

## 6. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Minimum 2 companies per sector | Peer comparison with 1 company is meaningless — rank is always 1, percentile is undefined. |
| Both company_financials and financial_ratios as sources | Absolute values (Revenue rank) and ratios (Net Margin rank) are both useful. Separate metric_source field distinguishes them. |
| Highest value = rank 1 | Descriptive, not prescriptive. "XOM is rank 1 in Debt-to-Equity" means most leveraged, not best. Consumer interprets context. |
| Percentile formula: (peer_count - rank) / (peer_count - 1) | Produces 1.0 for rank 1, 0.0 for last rank. Standard percentile. |
| Dense ranking (ties get same rank) | Apple and Microsoft both at $394B Revenue both get rank 1. Next company gets rank 3. More honest than arbitrary tiebreaking. |
| Reads from consumable tables, not base | Same rationale as other consumable specs. |

## 7. Governance Artifacts

- `governance/lineage/consumable-peer-comparison.json` — OpenLineage
- `governance/audit-trail/consumable-peer-comparison.json` — Design decisions
- `governance/dq-rules/consumable-peer-comparison.json` — 10 DQ rules
- `governance/dq-scorecards/consumable-peer-comparison-scorecard.md` — DQ results
- `governance/data-dictionary.json` — 1 new table definition added
- `governance/models/consumable-peer-comparison-conceptual.md`
- `governance/models/consumable-peer-comparison-logical.md`
- `governance/models/consumable-peer-comparison-physical.md`

## 8. Testing

```
tests/consumable/peer_comparison/
    __init__.py
    test_build.py           # Ranking, percentile, median, sector filtering, edge cases
    test_promote.py         # Iceberg roundtrip, dedup guard
    test_cli.py             # CLI commands
```

### Key Test Cases

| Test | What It Validates |
|------|-------------------|
| test_rank_basic | 3 companies in sector, assert ranks 1/2/3 by value |
| test_sector_avg | 3 companies with known values, assert exact average |
| test_sector_median_odd | 3 values, assert middle value |
| test_sector_median_even | 2 values, assert average of both |
| test_percentile_formula | Rank 1 of 3 = 1.0, rank 2 = 0.5, rank 3 = 0.0 |
| test_single_company_sector_excluded | Sector with 1 company produces 0 rows |
| test_tied_values_same_rank | Two companies with same value get same rank |
| test_negative_values_ranked | Losses ranked normally (least negative ranks higher) |
| test_both_metric_sources | company_financials and financial_ratios both produce rows |
| test_missing_metric_excluded | Company without metric not in group, peer_count correct |
| test_record_id_deterministic | Same inputs produce same record_id |
| test_promote_roundtrip | Write 1 record, read back, assert field values |
| test_promote_dedup | Write same record twice, assert no duplicates |

## 9. Agent Workflow

Per CLAUDE.md Base & Consumable Zone Pipeline (greenfield mode):

1. @governance-reviewer — Pre-implementation review
2. @data-steward — Business terms from spec
3. @semantic-modeler — Conceptual model
4. @semantic-modeler — Logical model
5. @data-analyst — EDA on source data
6. @dq-rule-writer — Write consumable DQ rules from EDA report
7. @semantic-modeler — Physical model
8. @primary-agent — Implementation
9. @dq-engineer — Execute rules, produce scorecard
10. @lineage-tracker — OpenLineage capture
11. @cde-tagger — Business term mapping update
12. @doc-generator — Dictionary + contracts update
13. @governance-reviewer — Post-implementation check
14. @staff-engineer — Final quality review

## 10. Dependencies

- `consumable-company-financials` (🟢 COMPLETE) — source data (26,894 rows, 20 companies, 25 business terms)
- `consumable-financial-ratios` (🟢 COMPLETE) — source data (6,544 rows, 20 companies, 7 ratios)
- `infra-setup-duckdb-iceberg` (🟢 COMPLETE) — Iceberg infrastructure

## 11. Governance Review (Post-Implementation)

**Reviewer:** @governance-reviewer
**Date:** 2026-03-15
**Result:** PASS

### Checklist
- [x] DQ rules exist: `governance/dq-rules/consumable-peer-comparison.json` (10 rules)
- [x] DQ rules executed: `governance/dq-results/` contains results for consumable-peer-comparison
- [x] No P0 failures: 10/10 rules passed
- [x] Governance models exist: conceptual, logical, physical in `governance/models/`
- [x] Business glossary updated: BT-053 (Peer Comparison) added
- [x] Data dictionary updated: consumable.peer_comparison table added with 23 fields
- [x] OpenLineage captured: `governance/lineage/consumable-peer-comparison.json`
- [x] EDA report produced: `governance/eda/consumable-peer-comparison-eda.md`
- [x] Dedup guard tested: promote skips existing record_ids
- [x] Build produces expected output: 26,559 rows, 17 companies, 5 sectors, 32 metrics

### Notes
All governance artifacts complete. DQ rules validate real Iceberg data. Business term BT-053 added for "Peer Comparison" concept. Three single-company sectors correctly excluded (Energy, Industrials, Communication Services).

## 12. Staff Engineer Review

**Reviewer:** @staff-engineer
**Date:** 2026-03-15
**Result:** APPROVED

### Review Summary

**Architecture:** Clean separation of concerns following the established consumable pattern. Config, schema, build, promote, and CLI modules mirror financial_ratios structure. Two-source normalization approach is elegant -- a single `_normalize_*` function per source, then shared ranking logic.

**Implementation Quality:**
- Dense ranking correctly handles ties (same rank for same value, next distinct value gets next rank)
- Percentile formula produces clean 0.0-1.0 boundaries with no edge case bugs
- Median computed correctly for both odd and even counts
- MIN_PEER_COUNT = 2 configurable in config.py
- Record ID grain includes metric_source, preventing cross-source collisions
- Build accepts both sources as parameters for testability

**Test Coverage:** 23 tests covering:
- Ranking (basic, ties, negatives)
- Statistics (avg, median odd/even, percentile)
- Edge cases (single-company exclusion, missing metrics)
- Deterministic record IDs
- Promote roundtrip and dedup guard
- CLI command routing
- Helper functions (median, dense_rank)

**DQ:** 10/10 P0 rules pass against real data. Rules cover uniqueness, validity, referential integrity, completeness, range checks, consistency, and accuracy of computed aggregates.

**Data Quality:** 26,559 rows across 5 sectors, 17 companies, 32 metrics (25 from company_financials + 7 from financial_ratios). Row count aligns with EDA estimate. Three single-company sectors correctly excluded.

**No concerns.** Ship it.
