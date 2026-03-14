# Base Zone: Financial Facts Model

## Status: 🟠 IMPLEMENTATION

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
| Zone | Base |
| Primary Agent | @financial-facts-model |
| Blocked By | — |
| Depends On | `raw-ingest-xbrl-company-facts` (🟢 COMPLETE), `base-entity-resolution` (🟢 COMPLETE), `base-xbrl-tag-normalization` (🟢 COMPLETE) |

---

## Claude Code Prompt

```
Implement the following plan:

# Plan: `base-financial-facts-model` Spec + Implementation

## Context

Phase 2 (Base Zone) has entity resolution (20 companies) and XBRL tag normalization (3,285 concepts → 25 CDEs) complete. The build plan's remaining Phase 2 items are: dimensional model, bitemporal schema, amendment handling, fiscal calendar normalization.

These split into two specs:
- Spec A: `base-financial-facts-model` — dimensional model + amendments + fiscal calendar (this plan)
- Spec B: `base-bitemporal-schema` — temporal query patterns + snapshot management (future, depends on Spec A)

This plan covers Spec A only.
```

---

## 1. Feature Description

### Problem Statement

The raw zone contains ~547K XBRL fact observations and the base zone has entity_mappings (20 companies) and concept_mappings (3,285 concepts → 25 CDEs). These exist as separate tables with no join. Without a unified fact table, downstream consumers must perform complex multi-way joins and handle amendment detection, fiscal calendar alignment, and supersession tracking themselves.

### User Story

As a data engineer building the SEC EDGAIR pipeline, I want a denormalized financial facts table that joins raw facts with entity and concept metadata, detects amendments and supersession, and provides a fiscal calendar dimension, so that downstream consumers can query enriched financial data without complex joins.

### Success Criteria

- [ ] `model.py` joins raw.xbrl_company_facts + base.entity_mappings + base.concept_mappings
- [ ] All ~547K raw facts promoted to `base.financial_facts` (filtered to known entities)
- [ ] Derived fields computed: fact_id, calendar_year, calendar_quarter, is_amendment, is_superseded, superseded_by
- [ ] `base.fiscal_calendar` built from observed periods for all 20 companies
- [ ] `base.amendment_tracking` captures all supersession pairs with val_change
- [ ] No staging/approval gate (join is deterministic)
- [ ] All 7 DQ rules pass at 100%
- [ ] All governance artifacts produced

## 2. Technical Design

### 2.1 Iceberg Tables

#### `base.financial_facts` — Central Fact Table

Grain: **(cik, concept, unit, start_date, end_date, accession_number)**

| Field | Type | Required | Source |
|-------|------|----------|--------|
| fact_id | String | Yes | Deterministic SHA-256 hash of grain fields |
| entity_id | String | Yes | entity_mappings.mapping_id |
| cik | Integer | Yes | raw.cik |
| canonical_name | String | Yes | entity_mappings.canonical_name |
| ticker | String | No | entity_mappings.ticker |
| concept | String | Yes | raw.concept |
| cde_id | String | No | concept_mappings.cde_id (null for tier 3) |
| canonical_cde | String | No | concept_mappings.canonical_cde (null for tier 3) |
| financial_statement | String | Yes | concept_mappings.financial_statement |
| category | String | Yes | concept_mappings.category |
| tier | Integer | Yes | concept_mappings.tier |
| taxonomy | String | Yes | raw.taxonomy |
| unit | String | Yes | raw.unit |
| val | Double | Yes | raw.val |
| start_date | Date | No | raw.start_date (null for instant facts) |
| end_date | Date | Yes | raw.end_date |
| fiscal_year | Integer | Yes | raw.fiscal_year |
| fiscal_period | String | Yes | raw.fiscal_period |
| fiscal_year_end | String | No | entity_mappings.fiscal_year_end |
| calendar_year | Integer | Yes | Computed: end_date.year |
| calendar_quarter | Integer | Yes | Computed: (end_date.month - 1) // 3 + 1 |
| accession_number | String | Yes | raw.accession_number |
| form | String | Yes | raw.form |
| filed_date | Date | Yes | raw.filed_date |
| is_amendment | Boolean | Yes | Derived: form ends in '/A' |
| is_superseded | Boolean | Yes | Derived: later filing exists for same grain |
| superseded_by | String | No | accession_number of superseding filing |
| promoted_at | Timestamptz | Yes | When written to base |

#### `base.fiscal_calendar` — Temporal Dimension

Grain: **(cik, fiscal_year, fiscal_period)**

| Field | Type | Required | Purpose |
|-------|------|----------|---------|
| calendar_id | String | Yes | Deterministic hash of grain |
| cik | Integer | Yes | Company |
| entity_id | String | Yes | FK to entity_mappings |
| fiscal_year | Integer | Yes | e.g. 2024 |
| fiscal_period | String | Yes | FY/Q1/Q2/Q3/Q4 |
| fiscal_year_end | String | Yes | MMDD from entity_mappings |
| period_start | Date | No | Earliest start_date observed |
| period_end | Date | Yes | Latest end_date for this period |
| calendar_year | Integer | Yes | Calendar year of period_end |
| calendar_quarter | Integer | Yes | Calendar quarter of period_end |
| duration_days | Integer | No | period_end - period_start |
| is_annual | Boolean | Yes | fiscal_period == 'FY' |

#### `base.amendment_tracking` — Supersession Audit Trail

| Field | Type | Required | Purpose |
|-------|------|----------|---------|
| tracking_id | String | Yes | UUID |
| cik | Integer | Yes | Company |
| concept | String | Yes | XBRL concept |
| unit | String | Yes | Measurement unit |
| start_date | Date | No | Period start |
| end_date | Date | Yes | Period end |
| original_accession | String | Yes | First filing |
| original_filed_date | Date | Yes | When original was filed |
| original_val | Double | Yes | Original value |
| amendment_accession | String | Yes | Amending filing |
| amendment_filed_date | Date | Yes | When amendment was filed |
| amendment_val | Double | Yes | New value |
| val_change | Double | Yes | amendment_val - original_val |
| val_change_pct | Double | No | % change (null if original_val = 0) |
| amendment_form | String | Yes | 10-K/A or 10-Q/A |
| detected_at | Timestamptz | Yes | When detected |

### 2.2 Module Structure

```
src/base/financial_facts_model/
    __init__.py
    config.py              # Paths, table names, grain definitions
    schema.py              # 3 Iceberg schemas (28 + 12 + 16 fields)
    model.py               # Core: join raw + entity + concept, compute derived fields
    amendments.py          # Detect supersession chains, build amendment_tracking
    fiscal_calendar.py     # Build fiscal_calendar from observed periods
    promote.py             # Write all 3 tables to Iceberg
    cli.py                 # model, calendar, amendments, status, all
```

### 2.3 Supersession Algorithm

```
For each group of (cik, concept, unit, start_date, end_date):
    Sort by filed_date ASC
    If only 1 accession_number → is_superseded=False
    If multiple accession_numbers:
        Latest filed_date → is_superseded=False (current)
        All earlier → is_superseded=True, superseded_by=latest.accession_number
```

### 2.4 No Staging/Approval Gate

Unlike entity resolution and tag normalization, the financial facts join is purely mechanical: CIK → entity_mappings, concept → concept_mappings. Both upstream tables are already approved. No human decision needed.

## 3. CLI Commands

```
python -m src.base.financial_facts_model.cli model      # build financial_facts
python -m src.base.financial_facts_model.cli calendar    # build fiscal_calendar
python -m src.base.financial_facts_model.cli amendments  # detect amendments
python -m src.base.financial_facts_model.cli status      # show table stats
python -m src.base.financial_facts_model.cli all         # run everything
```

## 4. DQ Rules

| Rule | Description | Threshold |
|------|-------------|-----------|
| BASE-FM-001 | Every fact has a valid entity_id | 100% |
| BASE-FM-002 | fact_id is unique (no duplicate grain) | 100% |
| BASE-FM-003 | is_superseded=True facts have non-null superseded_by | 100% |
| BASE-FM-004 | Fiscal calendar covers all (entity, year, period) in facts | 100% |
| BASE-FM-005 | calendar_quarter is 1-4 | 100% |
| BASE-FM-006 | Amendment tracking references valid accession_numbers | 100% |
| BASE-FM-007 | No orphan facts (every cik has entity_mapping) | 100% |

## 5. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Grain includes accession_number | Preserves all filing versions. Amendments produce separate rows. Dedup is downstream. |
| Denormalize entity + concept fields | Avoids JOINs for common queries. ~547K rows x 28 cols is small. |
| No staging/approval gate | Join is deterministic — no human judgment beyond already-approved mappings. |
| Fiscal calendar from observed data | Don't guess period boundaries — extract from actual (start_date, end_date) in filings. |
| Keep all taxonomies | dei/invest/srt facts are small but may be useful downstream. |
| Supersession by filed_date | filed_date is the universal authority for 'which filing is newer'. |

## 6. Governance Artifacts

- `governance/lineage/base-financial-facts-model.json`
- `governance/audit-trail/base-financial-facts-model.json`
- `governance/dq-rules/base-financial-facts-model.json`
- `governance/dq-scorecards/base-financial-facts-model-scorecard.md`
- `governance/data-dictionary.json` — 3 new table definitions added

## 7. Testing

```
tests/base/financial_facts_model/
    __init__.py
    test_model.py           # 14 tests: join logic, fact_id determinism, derived fields, supersession
    test_amendments.py      # 6 tests: supersession detection, val_change, chains
    test_fiscal_calendar.py # 12 tests: calendar for various fiscal year ends, edge cases
    test_promote.py         # 5 tests: Iceberg roundtrip for all 3 tables
    test_cli.py             # 3 tests: CLI commands
```

40 total tests, all passing. Full suite: 146 tests (40 new + 106 existing).
