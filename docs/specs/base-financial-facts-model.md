# Base Zone: Financial Facts Model

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

## Staff Engineer Review
### Date: 2026-03-14
### Reviewer: @staff-engineer
### Status: APPROVED

### Summary

This is solid work. The implementation faithfully matches the spec, the tests are real, and the governance artifacts are not boilerplate. Approving with minor observations noted below.

### Code Review

**config.py** — Clean separation of grain definitions, table names, and paths. SUPERSESSION_GRAIN and FACT_ID_GRAIN are defined once and used consistently across model.py and amendments.py. No issues.

**schema.py** — All 28 fields for financial_facts, 12 for fiscal_calendar, and 16 for amendment_tracking match the spec exactly. Field IDs are sequential. Required/optional flags match the spec's "Required" column. No drift.

**model.py** — The join logic is straightforward and correct:
- Entity lookup by CIK, concept lookup by concept name.
- Unknown CIKs are filtered out (correct per spec: "filtered to known entities").
- Unmapped concepts get tier=3/other/uncategorized defaults rather than being dropped. This preserves all facts for known entities regardless of concept mapping coverage. Good decision, correctly tested.
- `_apply_supersession` groups by the right grain and marks all-but-latest as superseded. The sort-by-filed_date approach matches the spec's algorithm exactly.
- Date normalization handles both string and date objects, which matters for the dual in-memory/Iceberg code paths.
- `promoted_at` is set once at build time, not per-record. Fine for batch operations.

**amendments.py** — Correctly pairs each superseded filing with the latest (not pairwise chaining). The val_change_pct null-when-zero-original handling is correct. Uses abs(original_val) in the denominator, which is the right call for negative values.

**fiscal_calendar.py** — Aggregates period boundaries correctly: min(start_dates) and max(end_dates) across all facts in a (cik, fiscal_year, fiscal_period) group. Handles the instant-fact case (no start_date) by allowing period_start to be None. Duration_days is None when period_start is None. All correct.

**promote.py** — Three parallel promote functions with identical structure. Uses `create_test_table` which is an existing infra pattern. Empty-list short circuit returns promoted=0 without touching the catalog. Fine.

**cli.py** — Five subcommands as specified. `cmd_all` runs model, calendar, amendments, status in sequence. The amendments command rebuilds facts from scratch rather than reading the just-promoted table, which is slightly wasteful but correct and avoids ordering dependency issues. Acceptable.

### Test Review

**Not theater.** Every test constructs specific input records with specific expected outputs and asserts on concrete values.

- **test_model.py (14 tests)**: Covers fact_id determinism, entity/concept enrichment, unmapped concept defaults, unknown entity filtering, calendar year/quarter derivation, amendment flag detection, and supersession for single/double/triple filing chains plus cross-concept independence. The supersession chain test (3 filings, verify A1 and A2 both point to A3) is the kind of test that catches real bugs.

- **test_amendments.py (6 tests)**: Covers no-amendment case, basic amendment detection with val_change verification, zero-original-val edge case, three-filing chain, cross-concept independence, and required field presence. The val_change_pct assertions (5.0 for 50/1000, None for 0 denominator) validate actual arithmetic, not just "not null."

- **test_fiscal_calendar.py (12 tests)**: Tests calendar quarter math for all four quarters, calendar_id determinism, and then five build scenarios: basic, January FYE (Walmart), June FYE (Microsoft), all quarters plus FY, instant facts with no start_date, unknown entity filtering, and multiple-facts-same-period boundary merging. The boundary merging test (three facts, one with no start_date, verifying earliest start and latest end) is particularly good — it validates the aggregation logic, not just "it returned something."

- **test_promote.py (5 tests)**: Iceberg roundtrip for all three tables using tmp_path fixtures, empty-list noop, and multi-record write. These are integration tests against real Iceberg tables, not mocks.

- **test_cli.py (3 tests)**: Status with seeded data, status with empty warehouse, and help flag. The seeding helper constructs all three tables with realistic records. Adequate for CLI coverage.

### Governance Artifacts

**Lineage (base-financial-facts-model.json)**: OpenLineage format with correct inputs (raw.xbrl_company_facts, base.entity_mappings, base.concept_mappings) and outputs (all three tables). Column-level lineage for 8 derived fields with specific transformation descriptions (e.g., "SHA-256 hash of (cik, concept, unit, start_date, end_date, accession_number), truncated to 16 chars"). This is not template filler — the descriptions match the actual code.

**Audit trail (base-financial-facts-model.json)**: Seven architectural decisions with rationale. All match the spec's Section 5 design decisions. The "unmapped concepts get tier=3" decision is documented here but not in the spec, which is fine — it's an implementation-level decision that belongs in the audit trail.

**DQ rules (base-financial-facts-model.json)**: All 7 rules from spec Section 4 with SQL queries, thresholds, and rationale. The SQL is executable (not pseudocode). Rule BASE-FM-004 uses a cross-table join check, which is the right approach for fiscal calendar completeness.

**DQ scorecard**: Maps each rule to specific tests by name. The "Join Logic Validation" and "Supersession Validation" sections go beyond the 7 DQ rules to document additional behavioral coverage. This is useful, not padding.

### Observations (Non-Blocking)

1. **Fact ID truncation**: `hashlib.sha256(...).hexdigest()[:16]` gives 16 hex chars = 64 bits of entropy. With ~547K facts, collision probability is negligible (~2.3e-8). Fine for this scale, but if the dataset grows by orders of magnitude, this could become a concern. Worth noting for future specs.

2. **Supersession pairs all earlier filings to the latest**: In a chain of A1 -> A2 -> A3, the code creates (A1, A3) and (A2, A3) tracking entries. This means A2's relationship to A1 is not captured in amendment_tracking. The spec explicitly says "pairs each superseded filing with the latest (superseding) filing" so this is correct per spec. But downstream consumers who want the full chain history should be aware.

3. **No idempotency guard on promote**: Running `cli all` twice will append duplicate rows. The spec doesn't require idempotency, and this is consistent with other promote patterns in the codebase. Just noting it.

4. **`_calendar_quarter` is duplicated** in both model.py and fiscal_calendar.py. Minor DRY violation. Could be in a shared utility, but for 2 lines of code it's not worth the abstraction.

### Verdict

The implementation matches the spec. The tests validate real behavior with real assertions. The governance artifacts reference actual code and actual data. The architecture decisions are documented with rationale. 40 tests, all passing, 0.46 seconds.

**APPROVED. Mark spec as COMPLETE.**
