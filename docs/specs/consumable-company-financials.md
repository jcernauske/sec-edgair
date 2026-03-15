# Consumable Zone: Company Financials

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
| Depends On | `base-financial-facts-model` (🟢 COMPLETE), `base-entity-resolution` (🟢 COMPLETE), `base-xbrl-tag-normalization` (🟢 COMPLETE) |
| Informed By | `governance/insights/base-to-consumable-insights.md` (@insight-manager) |

---

## Claude Code Prompt

```
Implement the consumable-company-financials spec.

This is the first consumable zone table — the foundation that all other consumable
data products build on. It takes the 547K-row base.financial_facts table and produces
a clean, one-row-per-(company, metric, period) comparison table that makes cross-company
financial analysis a one-liner.

Follow the full Base & Consumable Zone Pipeline (greenfield mode) from CLAUDE.md.
```

---

## 1. Feature Description

### Problem Statement

`base.financial_facts` has 547K rows with 28 fields. 48.3% are superseded. 70.1% have no business term mapping (Tier 3 unmapped concepts). Multiple XBRL concepts can map to the same business term for the same company/period (34.3% of business term groups have 2+ concepts — Comprehensive Income has up to 51 sub-component concepts per period). Consumers must filter superseded rows, filter to mapped business terms, resolve concept collisions, and handle fiscal year misalignment — all before asking a single analytical question.

### User Story

As a financial analyst (or LLM), I want a single table where I can query "Apple's revenue in FY2024" or "compare net income across all 20 companies for FY2023" without knowing anything about XBRL concepts, supersession, or fiscal calendar alignment.

### Success Criteria

- [ ] `consumable.company_financials` table with one row per (company, business term, fiscal_year, fiscal_period)
- [ ] Only current facts (is_superseded=false)
- [ ] Only mapped business terms (Tier 1+2, business_term_id IS NOT NULL)
- [ ] Concept collision resolved via primary concept preference per business term
- [ ] Unit filtered to primary unit per business term (USD for dollar amounts, USD/shares for per-share)
- [ ] Company metadata denormalized (ticker, canonical_name, sector, fiscal_year_end)
- [ ] Business term metadata denormalized (business_term, financial_statement, category)
- [ ] Both fiscal year and calendar year fields for temporal alignment
- [ ] Dedup guard on promote (no duplicates on re-run)
- [ ] load_date on every row
- [ ] All DQ rules pass
- [ ] All governance artifacts produced

## 2. Technical Design

### 2.1 Iceberg Table

#### `consumable.company_financials` — Cross-Company Financial Comparison Table

Grain: **(cik, business_term_id, fiscal_year, fiscal_period)**

| Field | Type | Required | Source |
|-------|------|----------|--------|
| record_id | String | Yes | Deterministic SHA-256 hash of grain fields |
| cik | Integer | Yes | base.financial_facts.cik |
| entity_id | String | Yes | base.financial_facts.entity_id |
| ticker | String | No | base.financial_facts.ticker |
| canonical_name | String | Yes | base.financial_facts.canonical_name |
| sector | String | Yes | SIC-to-sector mapping from entity_mappings.sic_code |
| business_term_id | String | Yes | base.financial_facts.business_term_id |
| business_term | String | Yes | base.financial_facts.business_term |
| financial_statement | String | Yes | base.financial_facts.financial_statement |
| category | String | Yes | base.financial_facts.category |
| val | Double | Yes | base.financial_facts.val (from primary concept) |
| unit | String | Yes | base.financial_facts.unit |
| source_concept | String | Yes | The XBRL concept selected by the priority engine |
| fiscal_year | Integer | Yes | base.financial_facts.fiscal_year |
| fiscal_period | String | Yes | base.financial_facts.fiscal_period (FY/Q1/Q2/Q3) |
| fiscal_year_end | String | No | base.entity_mappings.fiscal_year_end (MMDD) |
| period_end_date | Date | Yes | base.financial_facts.end_date |
| calendar_year | Integer | Yes | base.financial_facts.calendar_year |
| calendar_quarter | Integer | Yes | base.financial_facts.calendar_quarter |
| accession_number | String | Yes | Source filing accession number |
| filed_date | Date | Yes | base.financial_facts.filed_date |
| companies_reporting | Integer | Yes | Count of distinct companies with this business term in this period type |
| promoted_at | Timestamptz | Yes | When written to consumable |
| load_date | Date | Yes | System date tracking |

### 2.2 Concept Collision Resolution

34.3% of (company, business term, period) groups have multiple XBRL concepts mapping to the same business term. The consumable table needs exactly ONE value per group.

#### Strategy: Primary Concept Preference

For each business term, define an ordered list of **preferred concepts** — the top-level rollup, not sub-components. The engine selects the first match found for each (company, business term, period):

```python
PRIMARY_CONCEPTS = {
    "BT-024": ["Assets"],                                              # Total Assets
    "BT-027": ["Liabilities"],                                         # Total Liabilities
    "BT-028": ["StockholdersEquity",
                "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "BT-029": ["CashAndCashEquivalentsAtCarryingValue",
                "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"],
    "BT-030": ["AccountsReceivableNetCurrent"],                        # Accounts Receivable
    "BT-031": ["InventoryNet"],                                        # Inventory
    "BT-032": ["PropertyPlantAndEquipmentNet"],                        # PP&E
    "BT-033": ["Goodwill"],                                            # Goodwill
    "BT-022": ["Revenues",
                "RevenueFromContractWithCustomerExcludingAssessedTax",
                "SalesRevenueNet"],                                     # Revenue
    "BT-034": ["CostOfRevenue",
                "CostOfGoodsAndServicesSold",
                "CostOfGoodsSold"],                                     # Cost of Revenue
    "BT-035": ["GrossProfit"],                                         # Gross Profit
    "BT-036": ["OperatingIncomeLoss"],                                 # Operating Income
    "BT-023": ["NetIncomeLoss"],                                       # Net Income
    "BT-037": ["IncomeTaxExpenseBenefit"],                             # Income Tax Expense
    "BT-038": ["ResearchAndDevelopmentExpense"],                       # R&D
    "BT-039": ["SellingGeneralAndAdministrativeExpense",
                "GeneralAndAdministrativeExpense"],                     # SG&A
    "BT-040": ["NetCashProvidedByUsedInOperatingActivities"],          # Operating CF
    "BT-041": ["NetCashProvidedByUsedInInvestingActivities"],          # Investing CF
    "BT-042": ["NetCashProvidedByUsedInFinancingActivities"],          # Financing CF
    "BT-043": ["PaymentsToAcquirePropertyPlantAndEquipment"],          # CapEx
    "BT-044": ["EarningsPerShareBasic"],                               # EPS Basic
    "BT-045": ["EarningsPerShareDiluted"],                             # EPS Diluted
    "BT-046": ["CommonStockDividendsPerShareDeclared",
                "CommonStockDividendsPerShareCashPaid"],                # DPS
    "BT-047": ["ComprehensiveIncomeNetOfTax"],                         # Comprehensive Income
    "BT-048": ["RetainedEarningsAccumulatedDeficit"],                  # Retained Earnings
}
```

**Algorithm:**
1. Filter base.financial_facts to `is_superseded=false AND business_term_id IS NOT NULL`
2. For each (cik, business_term_id, fiscal_year, fiscal_period), find all matching facts
3. Filter to primary unit (USD for dollar amounts, USD/shares for per-share terms)
4. Walk the PRIMARY_CONCEPTS list for this business term — pick the first concept that has a fact in this group
5. If no primary concept found, pick the concept with the highest tier, then by most facts across the full dataset
6. Record `source_concept` — which XBRL concept was selected (audit trail)

### 2.3 Unit Filtering

| Category | Primary Unit | Rationale |
|-------------|-------------|-----------|
| Balance Sheet (BT-024, BT-027 to BT-033) | USD | Dollar amounts |
| Income Statement (BT-022, BT-023, BT-034 to BT-039) | USD | Dollar amounts |
| Cash Flow (BT-040 to BT-043) | USD | Dollar amounts |
| Per-Share (BT-044 to BT-046) | USD/shares | Per-share values |
| Other (BT-047, BT-048) | USD | Dollar amounts |

### 2.4 SIC-to-Sector Mapping

Static mapping from SIC codes to human-readable sectors. Derived from the 20 companies we have:

```python
SIC_TO_SECTOR = {
    "2086": "Consumer Staples",   # Coca-Cola
    "2834": "Healthcare",         # Pfizer, J&J
    "2841": "Consumer Staples",   # P&G
    "2911": "Energy",             # Exxon
    "3571": "Technology",         # Apple
    "3674": "Technology",         # Intel
    "3711": "Consumer Discretionary",  # Tesla
    "3721": "Industrials",        # Boeing
    "5331": "Consumer Staples",   # Walmart
    "5961": "Consumer Discretionary",  # Amazon
    "6020": "Financials",         # JPMorgan
    "6211": "Financials",         # Goldman Sachs
    "6324": "Healthcare",         # UnitedHealth
    "6331": "Financials",         # Berkshire
    "7370": "Technology",         # Meta
    "7372": "Technology",         # Microsoft, Alphabet
    "7389": "Financials",         # Visa
    "7841": "Communication Services", # Netflix
}
```

### 2.5 Companies Reporting Count

Each row includes `companies_reporting` — how many of the 20 companies have this business term for this fiscal_period type (FY, Q1, Q2, Q3). This lets consumers immediately see coverage. "Revenue has 20 companies reporting FY; Gross Profit has 9."

### 2.6 Module Structure

```
src/consumable/
    __init__.py
    company_financials/
        __init__.py
        config.py              # PRIMARY_CONCEPTS, SIC_TO_SECTOR, unit mapping, paths
        schema.py              # COMPANY_FINANCIALS_SCHEMA (23 fields)
        build.py               # Core: read base facts, resolve collisions, compute derived fields
        promote.py             # Write to Iceberg with dedup guard
        cli.py                 # build, status, coverage, all
```

### 2.7 No Staging/Approval Gate for Data

The consumable table is a deterministic transformation of already-approved base data. No human judgment needed for the data itself. The data modeling gates (business terms, conceptual/logical/physical models) still apply per the pipeline.

## 3. CLI Commands

```
python -m src.consumable.company_financials.cli build     # build the table
python -m src.consumable.company_financials.cli status    # show table stats, row counts
python -m src.consumable.company_financials.cli coverage  # business term x company coverage matrix
python -m src.consumable.company_financials.cli all       # build + status + coverage
```

## 4. DQ Rules

| Rule | Description | Threshold |
|------|-------------|-----------|
| CONS-CF-001 | record_id is unique (no duplicate grain) | 100% |
| CONS-CF-002 | Every row has valid business_term_id (matches business glossary) | 100% |
| CONS-CF-003 | Every row has valid cik (matches entity_mappings) | 100% |
| CONS-CF-004 | No null val (every row has a value) | 100% |
| CONS-CF-005 | Unit matches expected unit for business term category | 100% |
| CONS-CF-006 | companies_reporting is accurate (matches actual count) | 100% |
| CONS-CF-007 | All 25 business terms represented in the table | 100% |
| CONS-CF-008 | All 20 companies represented in the table | 100% |

## 5. Expected Output

Based on the insight report data:
- **~27,000 rows** (estimated: 20 companies x 25 business terms x ~4 periods x ~17 years, minus gaps)
- **25 business terms**, 12 with all-20-company coverage, 13 partial
- **20 companies** across 6 sectors
- **FY2009 to FY2026** range

## 6. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| One row per (company, business term, year, period) | The natural grain for cross-company comparison. Eliminates concept-level complexity. |
| Primary concept preference, not aggregation | We pick ONE value, not SUM or AVG. Revenue is Revenue, not the sum of Revenue + RevenueFromContracts + SalesRevenueNet. |
| source_concept field preserved | Audit trail — consumers can see which XBRL concept was selected and why. |
| Unit filtering, not unit aggregation | USD and USD/shares are different things. Don't mix them. |
| SIC-to-sector as static mapping | Only 20 companies. A dynamic mapping is over-engineering. |
| companies_reporting per row | Immediate coverage signal. "This business term has 9 companies" vs "this one has 20" without a second query. |
| Consumable defaults to current facts only | is_superseded=false. Historical/amended data is a base zone concern. Consumable is clean. |
| Both fiscal and calendar year fields | Apple FY2024 ends Sep 2024. Microsoft FY2024 ends Jun 2024. Calendar year fields enable apples-to-apples comparison. |

## 7. Governance Artifacts

- `governance/lineage/consumable-company-financials.json` — OpenLineage
- `governance/audit-trail/consumable-company-financials.json` — Design decisions
- `governance/dq-rules/consumable-company-financials.json` — 8 DQ rules
- `governance/dq-scorecards/consumable-company-financials-scorecard.md` — DQ results
- `governance/data-dictionary.json` — 1 new table definition added
- `governance/models/consumable-company-financials-conceptual.md`
- `governance/models/consumable-company-financials-logical.md`
- `governance/models/consumable-company-financials-physical.md`

## 8. Testing

```
tests/consumable/company_financials/
    __init__.py
    test_build.py           # Collision resolution, unit filtering, sector mapping
    test_promote.py         # Iceberg roundtrip, dedup guard
    test_cli.py             # CLI commands
```

## 9. Agent Workflow

Per CLAUDE.md Base & Consumable Zone Pipeline (greenfield mode):

1. @governance-reviewer — Pre-implementation review
2. @data-steward — Business terms from spec
3. @semantic-modeler — Conceptual model
4. @semantic-modeler — Logical model
5. @data-analyst — EDA on source data (base.financial_facts filtered to current + mapped business terms)
6. @dq-rule-writer — Write consumable DQ rules from EDA report
7. @semantic-modeler — Physical model
8. @primary-agent — Implementation
9. @dq-engineer — Execute rules, produce scorecard
10. @lineage-tracker — OpenLineage capture
11. @cde-tagger — business term mapping update
12. @doc-generator — Dictionary + contracts update
13. @governance-reviewer — Post-implementation check
14. @staff-engineer — Final quality review

## 11. Post-Implementation Governance Review

**Agent:** @governance-reviewer
**Date:** 2026-03-15
**Review Type:** Post-implementation (greenfield mode)

### Checklist

| Check | Status | Evidence |
|-------|--------|----------|
| DQ rules exist | PASS | `governance/dq-rules/consumable-company-financials.json` — 8 rules, all P0 |
| DQ rules executed | PASS | `governance/dq-results/consumable-company-financials-20260315T034333Z.json` — run ID f3e7c245 |
| No P0 failures | PASS | 8/8 rules passing (100%) |
| DQ scorecard produced | PASS | `governance/dq-scorecards/consumable-company-financials-scorecard.md` |
| OpenLineage exists | PASS | `governance/lineage/consumable-company-financials.json` — column-level lineage for 4 derived fields |
| Conceptual model exists | PASS | `governance/models/consumable-company-financials-conceptual.md` |
| Logical model exists | PASS | `governance/models/consumable-company-financials-logical.md` |
| Physical model exists | PASS | `governance/models/consumable-company-financials-physical.md` |
| Data dictionary updated | PASS | `governance/data-dictionary.json` — consumable.company_financials added with 24 fields |
| Business terms mapped | PASS | BT-049 (Sector) and BT-050 (Companies Reporting) added in Step 2; remaining terms inherited from base.financial_facts |

### Verdict: APPROVED

All governance artifacts are present and consistent. DQ rules validate real Iceberg data with zero violations. Lineage captures column-level provenance including the four derived fields (record_id, sector, source_concept, companies_reporting). Models at all three levels are approved and match the implementation. No advisory findings.

## 12. Staff Engineer Review

**Agent:** @staff-engineer
**Date:** 2026-03-15
**Spec:** consumable-company-financials
**Production stats:** 244 tests pass, 50 DQ rules pass, 26,894 rows produced

### Code Review

#### build.py — Concept Collision Resolution

The collision resolution engine in `_select_concept()` is correct and well-structured:

1. **Primary concept preference** walks `PRIMARY_CONCEPTS[bt_id]` in order, returning the first match. This is the right approach — deterministic, auditable, and matches the spec exactly.

2. **Fallback** sorts by `(tier, -frequency)` — lowest tier number first (tier 1 is best), then most common concept. The `sort_key` function on line 226-229 has a dead code smell (it uses negated tier/freq but is never called — the actual sort on line 232-235 uses a lambda with the correct logic). Not a bug, but the unused `sort_key` should be cleaned up.

3. **Legacy CDE-to-BT translation** (lines 98-104) is applied as the very first step before any filtering. This is the correct sequence — translating IDs before the pipeline touches them prevents silent data loss from rows that would otherwise fail the `business_term_id IS NOT NULL` filter or the `PRIMARY_UNIT` lookup.

4. **Unit filtering** (lines 116-124) correctly skips unknown business terms and only keeps facts matching the expected unit. The `continue` on unknown BT-IDs is defensive — should never fire given the upstream filter, but doesn't hurt.

5. **companies_reporting** (lines 191-198) is computed as a second pass over the results, not during the per-group loop. This is correct because the count is per (business_term_id, fiscal_period) across ALL companies, not per grain group.

#### promote.py — Dedup Guard

The dedup guard is real:

1. Reads ALL existing record_ids from the table into a set (line 39-40).
2. Filters incoming records against the set (line 45).
3. Reports skipped count (line 47-48).
4. Only appends genuinely new records.

This is the same pattern as the base zone promotes. It works because record_id is a deterministic hash of the grain — same inputs always produce the same ID. The full-table scan for existing IDs is acceptable at 27K rows. At 10M+ rows this would need a bloom filter or partitioned check, but that's a future concern.

#### Tests — Real or Theater?

**test_build.py:** Not theater. Each test constructs specific input data with known values and asserts specific output properties:
- `test_concept_collision_primary_preferred`: 3 revenue concepts, asserts "Revenues" is selected (first in preference list) with val=100.0
- `test_concept_collision_fallback`: 2 non-primary concepts at different tiers, asserts tier-2 wins
- `test_unit_filtering`: Mixes USD and shares for BT-024, USD and USD/shares for BT-044, asserts correct unit survives for each
- `test_companies_reporting_count`: 2 companies for BT-024, 1 for BT-022, asserts exact counts
- `test_record_id_deterministic`: Runs build twice with same input, asserts identical record_ids with length 16

**test_promote.py:** Real Iceberg roundtrip tests using `tmp_path`:
- `test_promote_roundtrip`: Writes 1 record, reads back, asserts specific field values (record_id, cik, sector)
- `test_promote_dedup`: Writes same record twice, asserts promoted=0 and skipped_duplicates=1 on second write, reads back and asserts exactly 1 row
- `test_promote_empty`: Empty list returns promoted=0 without creating tables

**test_cli.py:** Integration tests that seed a real Iceberg table and run CLI commands, asserting on captured stdout output. Minimal but sufficient — the CLI is a thin wrapper.

All tests use specific assertions on specific values. No `assert True`, no `assert len(x) > 0` handwaving. Approved.

#### Architecture

The module structure (config/schema/build/promote/cli) mirrors the base zone pattern exactly. Code is readable, functions are small, dependencies are explicit. The separation of build (pure transformation) from promote (Iceberg I/O) enables testability — build tests don't need a database.

One minor observation: `schema.py` defines 24 field IDs (1-24) for 24 columns, matching the spec's 23 fields plus load_date. The field count in the spec table says 23 but the actual implementation correctly includes load_date as field 24. This is consistent with the project rule "load_date on every row."

#### Concerns

1. **Dead code in `_select_concept`:** The `sort_key` inner function (lines 226-229) is defined but never called. The actual sort uses a lambda with different sign semantics. Cosmetic — does not affect behavior. Should be cleaned up in a follow-up.

2. **No explicit Q4 handling:** The spec says fiscal_period values are "FY/Q1/Q2/Q3" but Q4 may appear in the source data. The build pipeline doesn't filter Q4 out — it just passes through whatever fiscal_period values exist in the source. This is probably correct (Q4 data exists and is useful), but the spec should be updated if Q4 is intentionally included.

Neither concern is blocking.

### Verdict: APPROVED

The implementation is solid. Collision resolution is correct and matches the spec. Dedup guard is real. Tests validate actual behavior. Legacy ID translation is handled at the right point in the pipeline. 26,894 rows with 50 DQ rules passing and 244 tests green. Ship it.

## 10. Dependencies

- `base-financial-facts-model` (🟢 COMPLETE) — source data
- `base-entity-resolution` (🟢 COMPLETE) — entity metadata
- `base-xbrl-tag-normalization` (🟢 COMPLETE) — business term mappings
- `infra-setup-duckdb-iceberg` (🟢 COMPLETE) — Iceberg infrastructure
