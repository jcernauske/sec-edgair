# Consumable Zone: Financial Ratios

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
| Created | 2026-03-14 |
| Author | Jeff + Claude Code |
| Spec Version | 1.0 |
| Last Updated | 2026-03-14 |
| Zone | Consumable |
| Primary Agent | @primary-agent |
| Blocked By | — |
| Depends On | `consumable-company-financials` (🟢 COMPLETE) |
| Informed By | `governance/insights/base-to-consumable-insights.md` (@insight-manager) |

---

## Claude Code Prompt

```
Implement the consumable-financial-ratios spec.

This is the second consumable zone table — computed financial ratios derived from
consumable.company_financials. It takes the 26,894-row company financials table and
produces ratios like gross margin, operating margin, net margin, debt-to-equity,
R&D intensity, SGA ratio, and capex-to-revenue. One row per (company, ratio, year, period).

Follow the full Base & Consumable Zone Pipeline (greenfield mode) from CLAUDE.md.
```

---

## 1. Feature Description

### Problem Statement

`consumable.company_financials` gives absolute financial values — Revenue of $394B, Net Income of $97B. But absolute values are useless for cross-company comparison because a $394B Apple is not comparable to a $33B Netflix. Ratios normalize for size: Apple's 24.6% net margin vs Netflix's 18.3% net margin is a meaningful comparison. Today, computing any ratio requires two separate queries against company_financials, manual alignment on (cik, fiscal_year, fiscal_period), null handling for missing components, and knowledge of which business terms to divide.

### User Story

As a financial analyst (or LLM), I want a single table where I can query "Apple's operating margin in FY2024" or "compare debt-to-equity across all 20 companies for FY2023" without knowing which business terms to divide or which companies have the required components.

### Success Criteria

- [ ] `consumable.financial_ratios` table with one row per (company, ratio, fiscal_year, fiscal_period)
- [ ] 7 ratios computed from existing business terms
- [ ] Numerator and denominator values preserved for transparency
- [ ] Only computed where both numerator and denominator exist and denominator != 0
- [ ] Company metadata denormalized (ticker, canonical_name, sector)
- [ ] Coverage count per ratio (how many companies have this ratio)
- [ ] Dedup guard on promote (no duplicates on re-run)
- [ ] load_date on every row
- [ ] All DQ rules pass
- [ ] All governance artifacts produced

## 2. Technical Design

### 2.1 Ratios

All ratios are derived from `consumable.company_financials` by joining on (cik, fiscal_year, fiscal_period).

| Ratio ID | Ratio Name | Numerator (BT) | Denominator (BT) | Coverage | Interpretation |
|----------|-----------|-----------------|-------------------|----------|----------------|
| RATIO-001 | Gross Margin | BT-035 Gross Profit | BT-022 Revenue | 9 companies | % of revenue retained after COGS. Higher = better pricing power. |
| RATIO-002 | Operating Margin | BT-036 Operating Income | BT-022 Revenue | 18 companies | % of revenue retained after operating expenses. Core profitability. |
| RATIO-003 | Net Margin | BT-023 Net Income | BT-022 Revenue | 20 companies | % of revenue that becomes profit. Bottom-line efficiency. |
| RATIO-004 | Debt-to-Equity | BT-027 Total Liabilities | BT-028 Stockholders Equity | 20 companies | Financial leverage. >1.0 means more debt than equity. |
| RATIO-005 | R&D Intensity | BT-038 R&D Expense | BT-022 Revenue | 12 companies | % of revenue spent on R&D. Innovation investment signal. |
| RATIO-006 | SGA Ratio | BT-039 SG&A Expense | BT-022 Revenue | 17 companies | % of revenue spent on SG&A. Operational efficiency signal. |
| RATIO-007 | CapEx-to-Revenue | BT-043 Capital Expenditures | BT-022 Revenue | 19 companies | % of revenue reinvested in fixed assets. Capital intensity signal. |

### 2.2 Iceberg Table

#### `consumable.financial_ratios` — Cross-Company Financial Ratio Comparison Table

Grain: **(cik, ratio_id, fiscal_year, fiscal_period)**

| Field | Type | Required | Source |
|-------|------|----------|--------|
| record_id | String | Yes | Deterministic SHA-256 hash of grain fields |
| cik | Integer | Yes | consumable.company_financials.cik |
| entity_id | String | Yes | consumable.company_financials.entity_id |
| ticker | String | No | consumable.company_financials.ticker |
| canonical_name | String | Yes | consumable.company_financials.canonical_name |
| sector | String | Yes | consumable.company_financials.sector |
| ratio_id | String | Yes | RATIO-001 through RATIO-007 |
| ratio_name | String | Yes | Human-readable name (e.g., "Gross Margin") |
| ratio_value | Double | Yes | numerator_val / denominator_val |
| numerator_bt_id | String | Yes | Business term ID of the numerator |
| numerator_bt_name | String | Yes | Business term name of the numerator |
| numerator_val | Double | Yes | Value of the numerator component |
| denominator_bt_id | String | Yes | Business term ID of the denominator |
| denominator_bt_name | String | Yes | Business term name of the denominator |
| denominator_val | Double | Yes | Value of the denominator component |
| fiscal_year | Integer | Yes | consumable.company_financials.fiscal_year |
| fiscal_period | String | Yes | consumable.company_financials.fiscal_period (FY/Q1/Q2/Q3) |
| fiscal_year_end | String | No | consumable.company_financials.fiscal_year_end |
| period_end_date | Date | Yes | consumable.company_financials.period_end_date |
| calendar_year | Integer | Yes | consumable.company_financials.calendar_year |
| calendar_quarter | Integer | Yes | consumable.company_financials.calendar_quarter |
| companies_reporting | Integer | Yes | Count of distinct companies with this ratio in this period type |
| promoted_at | Timestamptz | Yes | When written to consumable |
| load_date | Date | Yes | System date tracking |

### 2.3 Computation Rules

1. **Read** `consumable.company_financials` into a DataFrame
2. **Pivot** by (cik, fiscal_year, fiscal_period) so each business term's val is accessible as a column
3. For each ratio definition, **join** numerator and denominator on (cik, fiscal_year, fiscal_period)
4. **Skip** rows where numerator is NULL, denominator is NULL, or denominator is 0
5. **Compute** `ratio_value = numerator_val / denominator_val`
6. **Special case — CapEx-to-Revenue (RATIO-007):** CapEx (BT-043 PaymentsToAcquirePropertyPlantAndEquipment) is reported as a negative number in cash flow statements (it's a cash outflow). Take the absolute value before dividing: `ratio_value = abs(numerator_val) / denominator_val`
7. **Preserve** both component values and their business term IDs for full transparency
8. **Compute** `companies_reporting` — distinct companies with this ratio per period type

### 2.4 Edge Cases

| Case | Handling |
|------|----------|
| Denominator is 0 | Skip — no ratio row produced. Revenue = 0 is theoretically possible but shouldn't exist in practice for operating companies. |
| Denominator is negative | Compute normally. Negative equity (BT-028) is real — Boeing had negative stockholders' equity. Debt-to-equity will be negative, which is meaningful. |
| Numerator is negative | Compute normally. Negative net income = negative net margin. Meaningful signal. |
| CapEx is negative | Take absolute value (it's a cash outflow convention). Result is always positive. |
| Both components missing | No row produced. This is correct — can't compute a ratio without both parts. |
| Only one period type has data | Compute for the periods available. Some companies may have FY but not quarterly for certain metrics. |
| Financial sector companies (JPM, GS, BRK.A) | Some ratios won't apply — banks don't have "Cost of Revenue" (no Gross Margin) or traditional "Operating Income." These companies simply won't have those ratio rows. |

### 2.5 Module Structure

```
src/consumable/
    financial_ratios/
        __init__.py
        config.py              # RATIO_DEFINITIONS, paths
        schema.py              # FINANCIAL_RATIOS_SCHEMA (24 fields)
        build.py               # Core: read company_financials, compute ratios
        promote.py             # Write to Iceberg with dedup guard
        cli.py                 # build, status, coverage, all
```

### 2.6 Ratio Definitions Config

```python
RATIO_DEFINITIONS = [
    {
        "ratio_id": "RATIO-001",
        "ratio_name": "Gross Margin",
        "numerator_bt_id": "BT-035",
        "denominator_bt_id": "BT-022",
        "abs_numerator": False,
    },
    {
        "ratio_id": "RATIO-002",
        "ratio_name": "Operating Margin",
        "numerator_bt_id": "BT-036",
        "denominator_bt_id": "BT-022",
        "abs_numerator": False,
    },
    {
        "ratio_id": "RATIO-003",
        "ratio_name": "Net Margin",
        "numerator_bt_id": "BT-023",
        "denominator_bt_id": "BT-022",
        "abs_numerator": False,
    },
    {
        "ratio_id": "RATIO-004",
        "ratio_name": "Debt-to-Equity",
        "numerator_bt_id": "BT-027",
        "denominator_bt_id": "BT-028",
        "abs_numerator": False,
    },
    {
        "ratio_id": "RATIO-005",
        "ratio_name": "R&D Intensity",
        "numerator_bt_id": "BT-038",
        "denominator_bt_id": "BT-022",
        "abs_numerator": False,
    },
    {
        "ratio_id": "RATIO-006",
        "ratio_name": "SGA Ratio",
        "numerator_bt_id": "BT-039",
        "denominator_bt_id": "BT-022",
        "abs_numerator": False,
    },
    {
        "ratio_id": "RATIO-007",
        "ratio_name": "CapEx-to-Revenue",
        "numerator_bt_id": "BT-043",
        "denominator_bt_id": "BT-022",
        "abs_numerator": True,
    },
]
```

## 3. CLI Commands

```
python -m src.consumable.financial_ratios.cli build     # build the table
python -m src.consumable.financial_ratios.cli status    # show table stats, row counts per ratio
python -m src.consumable.financial_ratios.cli coverage  # ratio x company coverage matrix
python -m src.consumable.financial_ratios.cli all       # build + status + coverage
```

## 4. DQ Rules

| Rule | Description | Priority | Threshold |
|------|-------------|----------|-----------|
| CONS-FR-001 | record_id is unique (no duplicate grain) | P0 | 100% |
| CONS-FR-002 | Every row has valid ratio_id (RATIO-001 through RATIO-007) | P0 | 100% |
| CONS-FR-003 | Every row has valid cik (matches consumable.company_financials) | P0 | 100% |
| CONS-FR-004 | No null ratio_value (every row has a computed value) | P0 | 100% |
| CONS-FR-005 | denominator_val is never 0 (division by zero guard) | P0 | 100% |
| CONS-FR-006 | Numerator and denominator business term IDs match the ratio definition | P0 | 100% |
| CONS-FR-007 | companies_reporting is accurate (matches actual count per ratio per period type) | P0 | 100% |
| CONS-FR-008 | All 7 ratios represented in the table | P0 | 100% |
| CONS-FR-009 | CapEx-to-Revenue (RATIO-007) ratio_value is always >= 0 (abs applied) | P0 | 100% |
| CONS-FR-010 | Margin ratios (RATIO-001, 002, 003, 005, 006, 007) use Revenue (BT-022) as denominator | P0 | 100% |

## 5. Expected Output

Based on company_financials coverage data:
- **~15,000-20,000 rows** (estimated: variable coverage per ratio x ~4 period types x ~17 years)
- **7 ratios**, coverage ranging from 9 companies (Gross Margin) to 20 companies (Net Margin, Debt-to-Equity)
- **20 companies** across 6 sectors (though not all companies will have all ratios)
- **FY2009 to FY2026** range (matching company_financials)

### Coverage Expectations per Ratio

| Ratio | Expected Companies | Why |
|-------|--------------------|-----|
| Gross Margin | ~9 | Only 9 companies report Gross Profit as a line item |
| Operating Margin | ~18 | JPM, GS don't have traditional Operating Income |
| Net Margin | ~20 | Universal — all companies have Net Income and Revenue |
| Debt-to-Equity | ~20 | Universal — all companies have Liabilities and Equity |
| R&D Intensity | ~12 | Only tech/pharma companies break out R&D |
| SGA Ratio | ~17 | Some companies report OpEx differently |
| CapEx-to-Revenue | ~19 | Nearly universal — one company missing CapEx data |

## 6. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Reads from consumable.company_financials, not base tables | The company_financials table already handles concept collision resolution, supersession filtering, and unit normalization. Ratios get clean inputs. |
| Numerator and denominator values preserved | Full transparency. A consumer can verify that Gross Margin = 0.43 came from Gross Profit $170B / Revenue $394B, not a magic number. |
| No ratio produced when either component is missing | Honest coverage. If a company doesn't report Gross Profit, it doesn't get a Gross Margin row. No imputation, no estimation. |
| Abs(CapEx) before dividing | CapEx is negative in cash flow statements (outflow convention). The ratio should be positive — "5% of revenue is reinvested in fixed assets." |
| Negative denominators allowed (equity) | Boeing had negative stockholders' equity. A negative debt-to-equity ratio is a meaningful signal, not an error. |
| RATIO_DEFINITIONS as config, not code | Adding new ratios is a config change + spec update, not a code change. Each ratio is a simple {numerator_bt, denominator_bt, abs_flag} tuple. |
| companies_reporting per ratio, not per business term | "Gross Margin is available for 9 companies" is more useful than "Gross Profit is available for 9" when you're looking at ratios. |

## 7. Governance Artifacts

- `governance/lineage/consumable-financial-ratios.json` — OpenLineage
- `governance/audit-trail/consumable-financial-ratios.json` — Design decisions
- `governance/dq-rules/consumable-financial-ratios.json` — 10 DQ rules
- `governance/dq-scorecards/consumable-financial-ratios-scorecard.md` — DQ results
- `governance/data-dictionary.json` — 1 new table definition added
- `governance/models/consumable-financial-ratios-conceptual.md`
- `governance/models/consumable-financial-ratios-logical.md`
- `governance/models/consumable-financial-ratios-physical.md`

## 8. Testing

```
tests/consumable/financial_ratios/
    __init__.py
    test_build.py           # Ratio computation, edge cases (zero denom, negative equity, abs capex)
    test_promote.py         # Iceberg roundtrip, dedup guard
    test_cli.py             # CLI commands
```

### Key Test Cases

| Test | What It Validates |
|------|-------------------|
| test_ratio_computation_basic | Given known numerator/denominator values, assert exact ratio |
| test_zero_denominator_skipped | Revenue=0 produces no ratio row |
| test_negative_equity | Negative stockholders equity produces negative debt-to-equity |
| test_capex_abs_applied | Negative CapEx value produces positive CapEx-to-Revenue |
| test_missing_component_skipped | Company without R&D produces no R&D Intensity row |
| test_companies_reporting_count | 2 companies with Net Margin, 1 with Gross Margin — assert correct counts |
| test_record_id_deterministic | Same inputs produce same record_id across runs |
| test_promote_roundtrip | Write 1 record, read back, assert field values |
| test_promote_dedup | Write same record twice, assert no duplicates |

## 9. Agent Workflow

Per CLAUDE.md Base & Consumable Zone Pipeline (greenfield mode):

1. @governance-reviewer — Pre-implementation review
2. @data-steward — Business terms from spec
3. @semantic-modeler — Conceptual model
4. @semantic-modeler — Logical model
5. @data-analyst — EDA on source data (consumable.company_financials ratio components)
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
**Date:** 2026-03-14
**Review Type:** Post-implementation (greenfield mode)

### Checklist

| Check | Status | Evidence |
|-------|--------|----------|
| DQ rules exist | PASS | `governance/dq-rules/consumable-financial-ratios.json` — 10 rules, all P0 |
| DQ rules executed | PASS | `governance/dq-results/consumable-financial-ratios-*.json` — run ID d5713894 |
| No P0 failures | PASS | 10/10 rules passing (100%) |
| DQ scorecard produced | PASS | `governance/dq-scorecards/consumable-financial-ratios-scorecard.md` |
| OpenLineage exists | PASS | `governance/lineage/consumable-financial-ratios.json` — column-level lineage for 4 derived fields |
| Conceptual model exists | PASS | `governance/models/consumable-financial-ratios-conceptual.md` |
| Logical model exists | PASS | `governance/models/consumable-financial-ratios-logical.md` |
| Physical model exists | PASS | `governance/models/consumable-financial-ratios-physical.md` |
| Data dictionary updated | PASS | `governance/data-dictionary.json` — consumable.financial_ratios added with 24 fields |
| Business terms mapped | PASS | BT-051 (Financial Ratio) added; component BTs inherited from company_financials |
| EDA report produced | PASS | `governance/eda/consumable-financial-ratios-eda.md` |

### Verdict: APPROVED

All governance artifacts are present and consistent. DQ rules validate real Iceberg data with zero violations. Lineage captures column-level provenance including derived ratio_value computation. Models at all three levels match the implementation. One data quality finding (Apple Q1 2017 negative Revenue) was identified during EDA and handled in the build logic.

## 12. Staff Engineer Review

**Agent:** @staff-engineer
**Date:** 2026-03-14
**Spec:** consumable-financial-ratios
**Production stats:** 261 tests pass, 60 DQ rules pass, 6,544 rows produced

### Code Review

#### build.py — Ratio Computation

The core logic is clean and correct:

1. **Index-based lookup** (lines 54-63) builds a dict keyed by (cik, fiscal_year, fiscal_period, business_term_id) for O(1) lookups. This is the right approach for joining numerator/denominator pairs — avoids N^2 scanning.

2. **Grain group collection** (lines 66-71) uses a set of (cik, fy, fp) tuples, then iterates RATIO_DEFINITIONS inside the loop. Each ratio definition is independent — if the numerator/denominator pair exists in the index, compute it; otherwise skip. Simple, correct, and the coverage naturally reflects data availability.

3. **CapEx abs handling** (line 97) correctly applies `abs()` only to the numerator when `abs_numerator=True`, while preserving the original value in `numerator_val` (line 105). Consumers can see that CapEx was -$100M and the ratio used $100M.

4. **Negative denominator guard** (lines 94-95) was added after the first DQ run caught Apple Q1 2017 with Revenue = -$29M. The guard correctly only applies when `abs_numerator=True` — negative equity for Debt-to-Equity (RATIO-004) is allowed because it's meaningful. This is exactly the right scoping.

5. **companies_reporting** (lines 113-118) follows the same pattern as company_financials — second pass over results, COUNT(DISTINCT cik) per (ratio_id, fiscal_period). Correct.

#### Config-driven ratio definitions

RATIO_DEFINITIONS is a clean data structure — each ratio is a {ratio_id, ratio_name, numerator_bt_id, denominator_bt_id, abs_numerator} tuple. Adding RATIO-008 (e.g., Free Cash Flow Margin) would be a 5-line config entry, not a code change. The `abs_numerator` flag is the only special-case behavior. Good separation.

#### promote.py — Dedup Guard

Identical pattern to company_financials promote. Full-table scan for existing record_ids, filter incoming, append only new. Acceptable at 6.5K rows.

#### Tests — Real or Theater?

**test_build.py (12 tests):** Not theater. Every test constructs specific input, asserts specific output:
- `test_net_margin_computation`: Known values (250/1000), asserts ratio_value == 0.25 AND both component values AND both BT IDs
- `test_zero_denominator_skipped`: Revenue=0, asserts 0 margin ratios produced
- `test_negative_equity`: Liabilities=150K, Equity=-50K, asserts D/E == -3.0
- `test_capex_abs_applied`: CapEx=-100, Revenue=1000, asserts ratio=0.1 AND numerator_val=-100 (original preserved)
- `test_capex_negative_revenue_skipped`: Revenue=-29M, asserts 0 CapEx ratio rows
- `test_multiple_ratios_from_revenue`: 6 components provided, asserts exactly 6 revenue-based ratios with specific values (0.4, 0.2, 0.1, 0.15, 0.08, 0.05)

All assertions are on specific values, not existence checks. Approved.

**test_promote.py (3 tests):** Same Iceberg roundtrip pattern as company_financials. Real.

**test_cli.py (2 tests):** Integration tests with capsys assertions on stdout. Minimal but sufficient.

#### DQ Rules

10 rules, all P0, well-chosen:
- CONS-FR-001 (uniqueness) — standard
- CONS-FR-002 (valid ratio_id) — checks against enumeration
- CONS-FR-005 (no zero denominator) — catches the guard
- CONS-FR-006 (correct BT pairing per ratio) — this is excellent, catches config drift
- CONS-FR-009 (CapEx always >= 0) — caught the negative Revenue bug on first run
- CONS-FR-010 (margin ratios use Revenue) — structural invariant check

The DQ rules catching the negative Revenue issue in production data on the first run is exactly how this pipeline is supposed to work.

#### Concerns

None blocking. The code is simple (build.py is 120 lines), well-structured, and the config-driven approach keeps the ratio definitions cleanly separated from computation logic.

### Verdict: APPROVED

Clean implementation. Config-driven ratio definitions. Real tests with specific assertions. DQ rules caught a real data quality issue (negative Revenue) on first run. 6,544 rows with 10 DQ rules passing and 261 tests green. Ship it.
