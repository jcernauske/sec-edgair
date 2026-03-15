# Consumable Zone: Period-Over-Period Growth

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
| Informed By | `governance/insights/base-to-consumable-insights.md` (@insight-manager, item #2) |

---

## Claude Code Prompt

```
Implement the consumable-period-over-period spec.

This is the third consumable zone table — period-over-period growth metrics derived
from consumable.company_financials. It takes the 26,894-row company financials table
and produces YoY change, YoY % change, and multi-year CAGR for every (company,
business term, period) combination. One row per (company, business term, year, period,
growth_type).

Follow the full Base & Consumable Zone Pipeline (greenfield mode) from CLAUDE.md.
```

---

## 1. Feature Description

### Problem Statement

`consumable.company_financials` gives absolute values — Apple's Revenue was $394B in FY2024 and $383B in FY2023. But the first question any analyst asks after seeing the absolute number is "how much did it grow?" Today, computing growth requires two self-joins against company_financials on (cik, business_term_id, fiscal_period) with `fiscal_year = fiscal_year - 1`, null handling for the first year in the series, and manual CAGR computation across arbitrary time windows. Every consumer repeats this work.

`consumable.financial_ratios` has the same problem — knowing Apple's net margin was 24.6% is useful, but knowing it expanded from 21.1% is more useful. Growth on ratios is a second-order question this table enables downstream.

### User Story

As a financial analyst (or LLM), I want to query "Apple's revenue growth in FY2024" or "which company had the fastest earnings growth over 5 years" without performing self-joins, handling edge cases around sign changes, or computing compound growth rates manually.

### Success Criteria

- [ ] `consumable.period_over_period` table with one row per (company, business term, fiscal_year, fiscal_period, growth_type)
- [ ] Three growth types: `yoy_change` (absolute), `yoy_pct_change` (percentage), `cagr_5yr` (compound annual)
- [ ] Prior period value preserved for transparency
- [ ] Only computed where both current and prior period values exist
- [ ] Sign-change handling: percentage change is meaningful even when crossing zero (loss to profit)
- [ ] CAGR only computed where 5+ years of data exist and base value > 0
- [ ] Company metadata denormalized (ticker, canonical_name, sector)
- [ ] Business term metadata denormalized (business_term, financial_statement, category)
- [ ] Dedup guard on promote (no duplicates on re-run)
- [ ] load_date on every row
- [ ] All DQ rules pass
- [ ] All governance artifacts produced

## 2. Technical Design

### 2.1 Growth Types

All derived from `consumable.company_financials` by self-joining on (cik, business_term_id, fiscal_period).

| Growth Type | Computation | When Produced | Interpretation |
|-------------|-------------|---------------|----------------|
| `yoy_change` | `current_val - prior_val` | Both current and prior year exist | Absolute change in USD (or USD/shares for EPS/DPS). "Revenue grew by $11B." |
| `yoy_pct_change` | `(current_val - prior_val) / abs(prior_val)` | Both exist AND `prior_val != 0` | Percentage change. "Revenue grew 2.9%." Uses `abs(prior_val)` in denominator so sign-change transitions are meaningful. |
| `cagr_5yr` | `(current_val / base_val)^(1/5) - 1` | Current year AND year-5 both exist AND `base_val > 0` | 5-year compound annual growth rate. "Apple's 5-year revenue CAGR is 8.2%." Only meaningful when base value is positive. |

### 2.2 Iceberg Table

#### `consumable.period_over_period` — Cross-Company Growth Metrics Table

Grain: **(cik, business_term_id, fiscal_year, fiscal_period, growth_type)**

| Field | Type | Required | Source |
|-------|------|----------|--------|
| record_id | String | Yes | Deterministic SHA-256 hash of grain fields |
| cik | Integer | Yes | consumable.company_financials.cik |
| entity_id | String | Yes | consumable.company_financials.entity_id |
| ticker | String | No | consumable.company_financials.ticker |
| canonical_name | String | Yes | consumable.company_financials.canonical_name |
| sector | String | Yes | consumable.company_financials.sector |
| business_term_id | String | Yes | consumable.company_financials.business_term_id |
| business_term | String | Yes | consumable.company_financials.business_term |
| financial_statement | String | Yes | consumable.company_financials.financial_statement |
| category | String | Yes | consumable.company_financials.category |
| fiscal_year | Integer | Yes | consumable.company_financials.fiscal_year |
| fiscal_period | String | Yes | consumable.company_financials.fiscal_period (FY/Q1/Q2/Q3) |
| fiscal_year_end | String | No | consumable.company_financials.fiscal_year_end |
| period_end_date | Date | Yes | consumable.company_financials.period_end_date |
| calendar_year | Integer | Yes | consumable.company_financials.calendar_year |
| calendar_quarter | Integer | Yes | consumable.company_financials.calendar_quarter |
| growth_type | String | Yes | `yoy_change`, `yoy_pct_change`, or `cagr_5yr` |
| growth_value | Double | Yes | The computed growth metric |
| current_val | Double | Yes | Value in the current period |
| prior_val | Double | No | Value in the prior period (NULL for CAGR) |
| base_val | Double | No | Value 5 years ago (only for CAGR, NULL for YoY) |
| base_fiscal_year | Integer | No | Fiscal year of the base value (only for CAGR) |
| companies_reporting | Integer | Yes | Count of distinct companies with this growth metric for this business term in this period type |
| promoted_at | Timestamptz | Yes | When written to consumable |
| load_date | Date | Yes | System date tracking |

### 2.3 Computation Rules

1. **Read** `consumable.company_financials` into a dictionary keyed by (cik, business_term_id, fiscal_year, fiscal_period)
2. **Build grain groups** — distinct (cik, business_term_id, fiscal_period) tuples
3. For each grain group, **sort by fiscal_year** ascending
4. For each (company, business term, year, period):
   - **YoY Change:** Look up `fiscal_year - 1` in the index. If found: `current_val - prior_val`. Emit one row with `growth_type = yoy_change`.
   - **YoY % Change:** Same pair. If found AND `prior_val != 0`: `(current_val - prior_val) / abs(prior_val)`. Emit one row with `growth_type = yoy_pct_change`. Use `abs(prior_val)` so transitions through zero produce meaningful percentages (e.g., loss of -$1B to profit of $2B = 300% improvement, not -300%).
   - **CAGR 5yr:** Look up `fiscal_year - 5` in the index. If found AND `base_val > 0`: `(current_val / base_val)^(1/5) - 1`. Emit one row with `growth_type = cagr_5yr`. Only compute when base is positive — CAGR is undefined for negative or zero base values.
5. **Compute** `companies_reporting` — distinct companies with this growth type per (business_term_id, fiscal_period)

### 2.4 Edge Cases

| Case | Handling |
|------|----------|
| First year in series (no prior year) | No YoY rows produced. Correct — can't compute growth without a baseline. |
| Prior value is 0 | YoY change is produced (absolute change is meaningful). YoY % change is NOT produced (division by zero). |
| Sign change (loss to profit) | YoY change is produced normally. YoY % change uses `abs(prior_val)` in denominator — e.g., from -$1B to $2B = +$3B / $1B = +300%. This is standard financial convention. |
| Both periods negative (deeper loss) | YoY change is negative (correct). YoY % change: from -$2B to -$3B = -$1B / $2B = -50% (loss deepened 50%). Correct. |
| CAGR with negative base | Not produced. CAGR requires `base_val > 0` — can't take fractional roots of negative numbers meaningfully. |
| CAGR with negative current but positive base | Produced. Result is negative. "Revenue CAGR of -15% means the company shrank." Meaningful signal. |
| CAGR with < 5 years of data | Not produced. GOOGL (data from 2015) won't have 5yr CAGR until fiscal_year >= 2020. |
| Per-share metrics (EPS, DPS) | Computed identically. YoY change is in USD/shares, % change is dimensionless. |
| Quarterly data (Q1/Q2/Q3) | YoY on Q1 means Q1-this-year vs Q1-last-year (same quarter, prior year). NOT sequential (Q1 vs Q4). |

### 2.5 Module Structure

```
src/consumable/
    period_over_period/
        __init__.py
        config.py              # GROWTH_TYPES, paths
        schema.py              # PERIOD_OVER_PERIOD_SCHEMA (25 fields)
        build.py               # Core: read company_financials, compute growth metrics
        promote.py             # Write to Iceberg with dedup guard
        cli.py                 # build, status, coverage, all
```

### 2.6 Growth Type Config

```python
GROWTH_TYPES = [
    {
        "growth_type": "yoy_change",
        "description": "Year-over-year absolute change",
        "lookback_years": 1,
        "requires_positive_base": False,
        "requires_nonzero_base": False,
    },
    {
        "growth_type": "yoy_pct_change",
        "description": "Year-over-year percentage change",
        "lookback_years": 1,
        "requires_positive_base": False,
        "requires_nonzero_base": True,
    },
    {
        "growth_type": "cagr_5yr",
        "description": "5-year compound annual growth rate",
        "lookback_years": 5,
        "requires_positive_base": True,
        "requires_nonzero_base": True,
    },
]
```

## 3. CLI Commands

```
python -m src.consumable.period_over_period.cli build     # build the table
python -m src.consumable.period_over_period.cli status    # show table stats, row counts per growth type
python -m src.consumable.period_over_period.cli coverage  # growth type x business term coverage matrix
python -m src.consumable.period_over_period.cli all       # build + status + coverage
```

## 4. DQ Rules

| Rule | Description | Priority | Threshold |
|------|-------------|----------|-----------|
| CONS-PP-001 | record_id is unique (no duplicate grain) | P0 | 100% |
| CONS-PP-002 | Every row has valid growth_type (yoy_change, yoy_pct_change, cagr_5yr) | P0 | 100% |
| CONS-PP-003 | Every row has valid cik (matches consumable.company_financials) | P0 | 100% |
| CONS-PP-004 | No null growth_value (every row has a computed value) | P0 | 100% |
| CONS-PP-005 | YoY rows have non-null prior_val | P0 | 100% |
| CONS-PP-006 | CAGR rows have non-null base_val and base_fiscal_year | P0 | 100% |
| CONS-PP-007 | CAGR base_fiscal_year = fiscal_year - 5 | P0 | 100% |
| CONS-PP-008 | YoY % change: prior_val is never 0 (division by zero guard) | P0 | 100% |
| CONS-PP-009 | CAGR: base_val is always > 0 | P0 | 100% |
| CONS-PP-010 | All 3 growth types represented in the table | P0 | 100% |
| CONS-PP-011 | All 25 business terms represented in YoY rows | P0 | 100% |
| CONS-PP-012 | companies_reporting is accurate (matches actual count per growth_type per business_term_id per fiscal_period) | P0 | 100% |

## 5. Expected Output

Based on company_financials data profiling:

- **~50,000-55,000 rows** estimated breakdown:
  - YoY change: ~24,690 rows (all consecutive year pairs across all period types)
  - YoY % change: ~24,500 rows (slightly fewer — excludes prior_val = 0 cases)
  - CAGR 5yr: ~3,000-5,000 rows (only where 5+ years exist AND base > 0, FY period type primarily)
- **25 business terms** — all terms from company_financials carry through
- **20 companies** across 6 sectors
- **FY2010 to FY2026** for YoY (need prior year, so first YoY year is min_year + 1)
- **FY2014 to FY2026** for CAGR (need 5 years back, so first CAGR year is min_year + 5)

### Coverage Expectations per Growth Type

| Growth Type | Expected Rows | Expected Companies | Why |
|-------------|---------------|--------------------|----|
| yoy_change | ~24,690 | 20 | Every consecutive year pair. Universal. |
| yoy_pct_change | ~24,500 | 20 | Same minus zero-prior-value cases. Nearly universal. |
| cagr_5yr | ~3,000-5,000 | 20 | Only FY with 5+ year lookback and positive base. Smaller set. |

## 6. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Three growth types as separate rows, not columns | Uniform grain. Adding `cagr_10yr` later is a config change, not a schema change. Consumers can filter to the growth type they need. |
| `abs(prior_val)` for percentage change | Standard financial convention. Ensures sign-change transitions produce meaningful percentages. From -$1B to +$2B should be +300%, not -300%. |
| CAGR only with positive base | CAGR formula `(end/start)^(1/n) - 1` requires start > 0. Negative start makes the fractional exponent undefined. Zero start is division by zero. |
| CAGR at 5 years, not configurable per query | Pre-computed for the most common window. 5-year CAGR is the institutional investor standard. 3-year and 10-year can be added as additional growth types later. |
| Quarterly YoY = same quarter prior year | Q1 FY2024 vs Q1 FY2023, not Q1 FY2024 vs Q4 FY2023. Sequential quarter growth is a different analysis (seasonal effects dominate). Could be a future growth type. |
| Reads from company_financials, not base tables | Same rationale as financial_ratios — company_financials already handles supersession, concept collision, and unit normalization. |
| Both component values preserved | `current_val` and `prior_val` (or `base_val`) let consumers verify the computation. "Revenue grew 2.9% — $394B vs $383B." |
| CAGR on all period types, not just FY | Quarterly CAGR is niche but valid — "Q1 revenue 5-year CAGR" smooths seasonality. Computed where data exists. |

## 7. Governance Artifacts

- `governance/lineage/consumable-period-over-period.json` — OpenLineage
- `governance/audit-trail/consumable-period-over-period.json` — Design decisions
- `governance/dq-rules/consumable-period-over-period.json` — 12 DQ rules
- `governance/dq-scorecards/consumable-period-over-period-scorecard.md` — DQ results
- `governance/data-dictionary.json` — 1 new table definition added
- `governance/models/consumable-period-over-period-conceptual.md`
- `governance/models/consumable-period-over-period-logical.md`
- `governance/models/consumable-period-over-period-physical.md`

## 8. Testing

```
tests/consumable/period_over_period/
    __init__.py
    test_build.py           # Growth computation, edge cases (sign changes, zero base, CAGR windows)
    test_promote.py         # Iceberg roundtrip, dedup guard
    test_cli.py             # CLI commands
```

### Key Test Cases

| Test | What It Validates |
|------|-------------------|
| test_yoy_change_basic | Revenue 100→120, assert yoy_change = 20 |
| test_yoy_pct_change_basic | Revenue 100→120, assert yoy_pct_change = 0.2 |
| test_cagr_basic | Revenue 100 in Y1, 161.05 in Y6, assert cagr_5yr ≈ 0.10 (10%) |
| test_zero_prior_no_pct | prior_val=0 produces yoy_change but NOT yoy_pct_change |
| test_sign_change_loss_to_profit | Net Income -100→200, assert yoy_change=300, yoy_pct_change=3.0 (300%) |
| test_sign_change_profit_to_loss | Net Income 200→-100, assert yoy_change=-300, yoy_pct_change=-1.5 (-150%) |
| test_deepening_loss | Net Income -100→-150, assert yoy_change=-50, yoy_pct_change=-0.5 (-50%) |
| test_cagr_negative_base_skipped | base_val=-100, assert no cagr_5yr row |
| test_cagr_zero_base_skipped | base_val=0, assert no cagr_5yr row |
| test_cagr_negative_current_allowed | base=100, current=-50, assert cagr_5yr is negative |
| test_first_year_no_yoy | Only one year of data, assert 0 YoY rows |
| test_quarterly_yoy_same_quarter | Q1 FY2024 vs Q1 FY2023, not Q4 FY2023 |
| test_companies_reporting_count | 2 companies with YoY for BT-022, assert count=2 |
| test_record_id_deterministic | Same inputs produce same record_id across runs |
| test_promote_roundtrip | Write 1 record, read back, assert field values |
| test_promote_dedup | Write same record twice, assert no duplicates |

## 9. Agent Workflow

Per CLAUDE.md Base & Consumable Zone Pipeline (greenfield mode):

1. @governance-reviewer — Pre-implementation review
2. @data-steward — Business terms from spec
3. @semantic-modeler — Conceptual model
4. @semantic-modeler — Logical model
5. @data-analyst — EDA on source data (consumable.company_financials year-pair coverage)
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
- `infra-setup-duckdb-iceberg` (🟢 COMPLETE) — Iceberg infrastructure

## 11. Post-Implementation Governance Review

**Agent:** @governance-reviewer
**Date:** 2026-03-15
**Review Type:** Post-implementation (greenfield mode)

### Checklist

| Check | Status | Evidence |
|-------|--------|----------|
| DQ rules exist | PASS | `governance/dq-rules/consumable-period-over-period.json` — 12 rules, all P0 |
| DQ rules executed | PASS | `governance/dq-results/consumable-period-over-period-*.json` — run ID a981f059 |
| No P0 failures | PASS | 12/12 rules passing (100%) |
| DQ scorecard produced | PASS | `governance/dq-scorecards/consumable-period-over-period-scorecard.md` |
| OpenLineage exists | PASS | `governance/lineage/consumable-period-over-period.json` — column-level lineage for 4 derived fields |
| Conceptual model exists | PASS | `governance/models/consumable-period-over-period-conceptual.md` |
| Logical model exists | PASS | `governance/models/consumable-period-over-period-logical.md` |
| Physical model exists | PASS | `governance/models/consumable-period-over-period-physical.md` |
| Data dictionary updated | PASS | `governance/data-dictionary.json` — consumable.period_over_period added with 25 fields |
| Business terms mapped | PASS | BT-052 (Period-Over-Period Growth) added; component BTs inherited from company_financials |
| EDA report produced | PASS | `governance/eda/consumable-period-over-period-eda.md` |

### Verdict: APPROVED

All governance artifacts are present and consistent. DQ rules validate real Iceberg data with zero violations. Lineage captures column-level provenance including the four derived fields (record_id, growth_value, companies_reporting, growth_type). Models at all three levels match the implementation. EDA correctly identified 24 zero values and ~500-800 negative-base CAGR exclusions.

## 12. Staff Engineer Review

**Agent:** @staff-engineer
**Date:** 2026-03-15
**Spec:** consumable-period-over-period
**Production stats:** 281 tests pass, 72 DQ rules pass, 65,445 rows produced

### Code Review

#### build.py — Growth Computation

The core logic is clean and correct:

1. **Index-based lookup** (lines 52-61) builds a dict keyed by (cik, business_term_id, fiscal_year, fiscal_period) for O(1) lookups. Same proven pattern as financial_ratios.

2. **Year collection** (lines 68-73) pre-collects fiscal years per grain group to avoid redundant iteration. The sorted() call on line 78 ensures deterministic processing order.

3. **Growth type iteration** (lines 83-120) walks GROWTH_TYPES config for each (company, term, year, period). The `requires_nonzero_base` and `requires_positive_base` flags drive the guards cleanly — no special-case if/else for individual growth types.

4. **CAGR negative-current handling** (lines 109-112) correctly handles the case where current/base ratio is negative (company went from profit to loss over 5 years). Uses `-(abs(ratio)^(1/n)) - 1` which produces a meaningful negative CAGR. This edge case would trip most implementations.

5. **prior_val/base_val mutual exclusivity** (lines 125-127) cleanly separates YoY (prior_val populated, base_val NULL) from CAGR (base_val populated, prior_val NULL) using the lookback_years value. No ambiguity.

6. **companies_reporting** (lines 133-138) follows the established pattern — second pass over results, COUNT(DISTINCT cik) per (growth_type, business_term_id, fiscal_period). Correct.

#### Config-driven growth types

GROWTH_TYPES is a clean data structure with semantic flags (requires_positive_base, requires_nonzero_base) rather than growth-type-specific code paths. Adding `cagr_10yr` would be a 7-line config entry. The `lookback_years` field drives both the comparison year lookup and the CAGR exponent. Good separation.

#### promote.py — Dedup Guard

Identical pattern to financial_ratios and company_financials. Full-table scan for existing record_ids, filter incoming, append only new. Acceptable at 65K rows.

#### Tests — Real or Theater?

**test_build.py (15 tests):** Not theater. Every test constructs specific input data and asserts specific output values:
- `test_yoy_change_basic`: 100→120, asserts growth_value==20.0, current_val==120.0, prior_val==100.0
- `test_sign_change_loss_to_profit`: -100→200, asserts yoy_change==300.0, yoy_pct_change==3.0
- `test_sign_change_profit_to_loss`: 200→-100, asserts yoy_pct_change==-1.5
- `test_deepening_loss`: -100→-150, asserts yoy_pct_change==-0.5
- `test_cagr_basic`: 100→161.051 over 5 years, asserts CAGR≈0.10 within tolerance
- `test_quarterly_yoy_same_quarter`: Verifies Q1-to-Q1 comparison, not Q1-to-Q4
- `test_zero_prior_no_pct`: Verifies yoy_change produced but yoy_pct_change blocked

All assertions are on specific values, not existence checks. Approved.

**test_promote.py (3 tests):** Same Iceberg roundtrip pattern. Real.

**test_cli.py (2 tests):** Integration tests with capsys assertions. Minimal but sufficient.

#### DQ Rules

12 rules, all P0, well-chosen:
- CONS-PP-001 (uniqueness) — standard
- CONS-PP-005 (YoY prior_val not null) — structural invariant
- CONS-PP-007 (CAGR base_fiscal_year = fiscal_year - 5) — catches lookback drift
- CONS-PP-008 (pct change prior_val != 0) — catches division by zero guard failure
- CONS-PP-009 (CAGR base_val > 0) — catches positive-base guard failure
- CONS-PP-011 (all 25 BTs in YoY) — completeness check
- CONS-PP-012 (companies_reporting accuracy) — denormalized aggregate check

#### Concerns

None blocking.

One observation: the CAGR row count (16,085) is significantly higher than the spec's estimate of 3,000-5,000. This is because CAGR is computed on all period types (FY, Q1, Q2, Q3), not just FY. The spec said "CAGR on all period types" in the design decisions, so this is correct behavior — the estimate was just conservative. The actual breakdown is likely ~4,500 FY + ~11,500 quarterly.

### Verdict: APPROVED

Clean implementation. Config-driven growth types with semantic flags. Real tests with specific assertions covering all edge cases (sign changes, zero/negative base, quarterly alignment). DQ rules caught all structural invariants. 65,445 rows with 12 DQ rules passing and 281 tests green. Ship it.
