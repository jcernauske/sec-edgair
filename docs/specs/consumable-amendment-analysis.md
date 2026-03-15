# Consumable Zone: Amendment Analysis

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
| Depends On | `consumable-company-financials` (🟢 COMPLETE) |
| Informed By | `governance/insights/base-to-consumable-insights.md` (@insight-manager, item #4) |

---

## Claude Code Prompt

```
Implement the consumable-amendment-analysis spec.

This is the fifth consumable zone table — amendment/restatement pattern analysis
derived from base.amendment_tracking and enriched with company metadata from
consumable.company_financials. Summarizes amendment frequency, magnitude, and
patterns per company per fiscal year. One row per (company, fiscal_year).

Follow the full Base & Consumable Zone Pipeline (greenfield mode) from CLAUDE.md.
```

---

## 1. Feature Description

### Problem Statement

`base.amendment_tracking` has 239,127 rows tracking every value change across all 20 companies over 17 years. But it's raw — one row per amended fact. The first question an analyst asks is "which companies amend most?" followed by "how big are the restatements?" and "is this company's amendment rate getting worse?" Today, answering these requires aggregating 239K rows with GROUP BY, computing medians, counting distinct concepts, and joining to entity metadata. The insight report flagged this as "genuinely interesting intelligence about corporate reporting quality."

### User Story

As a financial analyst (or LLM), I want to query "Boeing's amendment rate in FY2023" or "which company had the largest median restatement magnitude" without aggregating raw amendment tracking data.

### Success Criteria

- [x] `consumable.amendment_analysis` table with one row per (company, fiscal_year)
- [x] Amendment count, distinct concepts amended, distinct filings amended
- [x] Magnitude stats: mean, median, max absolute change; mean and median percentage change
- [x] Company metadata denormalized (ticker, canonical_name, sector)
- [x] Dedup guard on promote (no duplicates on re-run)
- [x] load_date on every row
- [x] All DQ rules pass
- [x] All governance artifacts produced

## 2. Technical Design

### 2.1 Iceberg Table

#### `consumable.amendment_analysis` — Company Amendment Pattern Summary

Grain: **(cik, fiscal_year)**

| Field | Type | Required | Source |
|-------|------|----------|--------|
| record_id | String | Yes | Deterministic SHA-256 hash of grain fields |
| cik | Integer | Yes | base.amendment_tracking.cik |
| entity_id | String | Yes | consumable.company_financials.entity_id |
| ticker | String | No | consumable.company_financials.ticker |
| canonical_name | String | Yes | consumable.company_financials.canonical_name |
| sector | String | Yes | consumable.company_financials.sector |
| fiscal_year | Integer | Yes | Derived from amendment_tracking.end_date |
| amendment_count | Integer | Yes | COUNT(*) of amendments for this company/year |
| distinct_concepts | Integer | Yes | COUNT(DISTINCT concept) amended |
| distinct_filings | Integer | Yes | COUNT(DISTINCT amendment_accession) |
| mean_abs_change | Double | Yes | AVG(ABS(val_change)) |
| median_abs_change | Double | Yes | MEDIAN(ABS(val_change)) |
| max_abs_change | Double | Yes | MAX(ABS(val_change)) |
| mean_pct_change | Double | No | AVG(ABS(val_change_pct)) where val_change_pct is not null |
| median_pct_change | Double | No | MEDIAN(ABS(val_change_pct)) where val_change_pct is not null |
| total_val_impact | Double | Yes | SUM(ABS(val_change)) — total dollar magnitude of all amendments |
| largest_concept | String | Yes | Concept with the largest single ABS(val_change) in this year |
| largest_change | Double | Yes | The largest single ABS(val_change) value |
| days_to_amend_avg | Double | Yes | AVG(amendment_filed_date - original_filed_date) in days |
| days_to_amend_median | Double | Yes | MEDIAN(amendment_filed_date - original_filed_date) in days |
| promoted_at | Timestamptz | Yes | When written to consumable |
| load_date | Date | Yes | System date tracking |

### 2.2 Computation Rules

1. **Read** `base.amendment_tracking` — 239K rows of individual amendments
2. **Read** `consumable.company_financials` — for company metadata (ticker, canonical_name, sector, entity_id). Use one row per cik for metadata lookup.
3. **Derive fiscal_year** from `end_date` field in amendment_tracking (the period being amended)
4. **Group** by (cik, fiscal_year)
5. For each group:
   - **amendment_count** = COUNT(*)
   - **distinct_concepts** = COUNT(DISTINCT concept)
   - **distinct_filings** = COUNT(DISTINCT amendment_accession)
   - **mean_abs_change** = AVG(ABS(val_change))
   - **median_abs_change** = MEDIAN(ABS(val_change))
   - **max_abs_change** = MAX(ABS(val_change))
   - **mean_pct_change** = AVG(ABS(val_change_pct)) where not null
   - **median_pct_change** = MEDIAN(ABS(val_change_pct)) where not null
   - **total_val_impact** = SUM(ABS(val_change))
   - **largest_concept** = concept with MAX(ABS(val_change))
   - **largest_change** = MAX(ABS(val_change))
   - **days_to_amend_avg** = AVG(amendment_filed_date - original_filed_date)
   - **days_to_amend_median** = MEDIAN(amendment_filed_date - original_filed_date)
6. **Join** company metadata from company_financials

### 2.3 Fiscal Year Derivation

Amendment tracking has `end_date` (the period end being amended) but not `fiscal_year`. Derive fiscal_year from the calendar year of `end_date`. This is an approximation — companies with non-December fiscal year ends may have slight misalignment, but it's sufficient for trend analysis.

### 2.4 Edge Cases

| Case | Handling |
|------|----------|
| val_change_pct is null | Some amendments have val_change but null val_change_pct (original was 0). mean_pct_change and median_pct_change exclude nulls. Fields are nullable. |
| Company with 0 amendments in a year | No row produced. Only years with amendments appear. |
| Multiple amendments to same concept in same year | All counted. amendment_count reflects total, distinct_concepts reflects unique concepts. |
| Negative val_change | ABS applied for magnitude stats. The sign indicates direction but magnitude stats should always be positive. |
| Company not in company_financials | Shouldn't happen — same 20 companies. If it did, skip (no metadata). |

### 2.5 Module Structure

```
src/consumable/
    amendment_analysis/
        __init__.py
        config.py              # Paths, grain fields
        schema.py              # AMENDMENT_ANALYSIS_SCHEMA (22 fields)
        build.py               # Core: read amendment_tracking, aggregate, join metadata
        promote.py             # Write to Iceberg with dedup guard
        cli.py                 # build, status, all
```

## 3. CLI Commands

```
python -m src.consumable.amendment_analysis.cli build     # build the table
python -m src.consumable.amendment_analysis.cli status    # show table stats
python -m src.consumable.amendment_analysis.cli all       # build + status
```

## 4. DQ Rules

| Rule | Description | Priority | Threshold |
|------|-------------|----------|-----------|
| CONS-AA-001 | record_id is unique (no duplicate grain) | P0 | 100% |
| CONS-AA-002 | Every row has valid cik (matches consumable.company_financials) | P0 | 100% |
| CONS-AA-003 | No null amendment_count (every row has a count) | P0 | 100% |
| CONS-AA-004 | amendment_count > 0 (no zero-amendment rows) | P0 | 100% |
| CONS-AA-005 | mean_abs_change >= 0 (magnitude is non-negative) | P0 | 100% |
| CONS-AA-006 | median_abs_change >= 0 (magnitude is non-negative) | P0 | 100% |
| CONS-AA-007 | max_abs_change >= median_abs_change (max is at least as large) | P0 | 100% |
| CONS-AA-008 | distinct_concepts <= amendment_count (can't have more distinct concepts than amendments) | P0 | 100% |
| CONS-AA-009 | All 20 companies represented in the table | P0 | 100% |
| CONS-AA-010 | total_val_impact >= max_abs_change (total is at least as large as max) | P0 | 100% |

## 5. Expected Output

Based on amendment_tracking profiling:
- **239,127 amendments** across 20 companies
- **~20 companies x ~17 years = ~340 rows** (much smaller than other consumable tables — this is a summary)
- All 20 companies have amendment data
- Top amenders: JPM (21K), Goldman Sachs (16K), Boeing (15K), Coca-Cola (14K)

## 6. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| One row per (company, fiscal_year) | Annual summary is the natural grain. Quarterly breakdown adds complexity without proportional value. |
| ABS() for all magnitude stats | Amendments can increase or decrease values. Magnitude stats (mean, median, max) should reflect size, not direction. |
| Percentage change excludes nulls | val_change_pct is null when original_val is 0. Can't compute percentage change from zero. |
| days_to_amend computed | Time between original and amendment filings. Long delays may signal operational issues. |
| largest_concept captured | The single concept with the biggest restatement. "Boeing's largest amendment in FY2023 was to Operating Income" tells a story. |
| Fiscal year from end_date | Approximate but sufficient. The period being amended is more meaningful than the filing date. |
| Reads from base.amendment_tracking, not raw | Amendment tracking already has the val_change and val_change_pct computed. |

## 7. Governance Artifacts

- `governance/lineage/consumable-amendment-analysis.json` — OpenLineage
- `governance/audit-trail/consumable-amendment-analysis.json` — Design decisions
- `governance/dq-rules/consumable-amendment-analysis.json` — 10 DQ rules
- `governance/dq-scorecards/consumable-amendment-analysis-scorecard.md` — DQ results
- `governance/data-dictionary.json` — 1 new table definition added
- `governance/models/consumable-amendment-analysis-conceptual.md`
- `governance/models/consumable-amendment-analysis-logical.md`
- `governance/models/consumable-amendment-analysis-physical.md`

## 8. Testing

```
tests/consumable/amendment_analysis/
    __init__.py
    test_build.py           # Aggregation, magnitude stats, edge cases
    test_promote.py         # Iceberg roundtrip, dedup guard
    test_cli.py             # CLI commands
```

### Key Test Cases

| Test | What It Validates |
|------|-------------------|
| test_basic_aggregation | 3 amendments for 1 company/year, assert amendment_count=3 |
| test_distinct_concepts | 3 amendments for 2 distinct concepts, assert distinct_concepts=2 |
| test_mean_abs_change | Known values, assert exact mean |
| test_median_abs_change_odd | 3 values, assert middle value |
| test_median_abs_change_even | 2 values, assert average of both |
| test_max_abs_change | Assert largest absolute change |
| test_pct_change_null_excluded | 2 amendments, 1 with null pct, assert mean uses only non-null |
| test_total_val_impact | Sum of absolute changes |
| test_largest_concept | Concept with biggest change is captured |
| test_days_to_amend | Known dates, assert correct day counts |
| test_no_amendments_no_row | Company with 0 amendments in a year produces no row |
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

- `consumable-company-financials` (🟢 COMPLETE) — company metadata (ticker, canonical_name, sector)
- `base-financial-facts-model` (🟢 COMPLETE) — base.amendment_tracking source data (239,127 rows)
- `infra-setup-duckdb-iceberg` (🟢 COMPLETE) — Iceberg infrastructure

## 11. Governance Review (Post-Implementation)

**Agent:** @governance-reviewer
**Date:** 2026-03-15

### Checklist
- [x] DQ rules exist: `governance/dq-rules/consumable-amendment-analysis.json` (10 rules)
- [x] DQ rules executed: `governance/dq-results/` contains timestamped results
- [x] No P0 failures: All 10 rules PASS
- [x] DQ scorecard generated: `governance/dq-scorecards/consumable-amendment-analysis-scorecard.md`
- [x] Lineage captured: `governance/lineage/consumable-amendment-analysis.json`
- [x] Business term added: BT-054 "Amendment Analysis" in `governance/business-glossary.json`
- [x] Data dictionary updated: `consumable.amendment_analysis` table added to `governance/data-dictionary.json`
- [x] Models produced: conceptual, logical, physical in `governance/models/`
- [x] EDA report: `governance/eda/consumable-amendment-analysis-eda.md`
- [x] Tests pass: 22/22 tests pass
- [x] Table populated: 371 rows, 20 companies, fiscal years 2006-2025
- [x] Total amendments summarized: 239,127 (matches source count)

### Verdict: APPROVED

## 12. Staff Engineer Review

**Agent:** @staff-engineer
**Date:** 2026-03-15

### Review Summary
- **Implementation quality:** Clean aggregation logic with proper ABS() on all magnitude stats, nullable pct fields, deterministic record_id, and median computation using Python statistics module.
- **Test coverage:** 22 tests covering aggregation, distinct counts, mean/median/max, pct null handling, total impact, largest concept, days to amend, edge cases (no amendments, unknown CIK), record_id determinism, Iceberg roundtrip, dedup guard, and nullable pct roundtrip.
- **Real data validation:** 371 rows produced from 239,127 source amendments. All 20 companies represented. DQ: 10/10 rules pass.
- **Governance completeness:** All artifacts produced — EDA report, 3 data models, DQ rules + scorecard, OpenLineage, business glossary update, data dictionary update.

### Verdict: APPROVED — spec marked COMPLETE
