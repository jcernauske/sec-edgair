# Spec: Load Date Tracking

## Problem Statement

The pipeline has two temporal axes that are currently conflated:

1. **Business time** — when something happened in the real world (`filed_date`, `end_date`, `fiscal_period`)
2. **System time** — when our pipeline learned about it (`ingested_at`, `promoted_at`)

"Show me Apple's revenue" uses business time. "Show me exactly what this table looked like on March 14th" uses system time. Today, system time exists as `ingested_at`/`promoted_at` timestamps buried in columns, but there's no clean, consistent `load_date` across all tables that answers: **"when did this row land in this zone?"**

This matters in production because:
- SEC EDGAR publishes new filings daily. Monday's pipeline run sees different data than Friday's.
- A DQ failure on Wednesday needs to be investigated against Wednesday's data, not today's.
- Auditors ask "what did you know and when did you know it" — that's `load_date`, not `filed_date`.
- Partitioning by `load_date` makes incremental processing efficient (only scan today's partition).

## What Already Exists

| Table | System Time Column | Type | Notes |
|-------|-------------------|------|-------|
| `raw.xbrl_company_facts` | `ingested_at` | TIMESTAMPTZ | When the raw fact was fetched and written |
| `base.financial_facts` | `promoted_at` | TIMESTAMPTZ | When promoted from raw → base |
| `base.entity_mappings` | `approved_at` | TIMESTAMPTZ | When the mapping was approved (business decision, not load) |
| `base.concept_mappings` | `mapped_at` | TIMESTAMPTZ | When classified (business decision, not load) |
| `base.fiscal_calendar` | — | — | No system time at all |
| `base.amendment_tracking` | `detected_at` | TIMESTAMPTZ | When the amendment was detected |

Problems:
- No consistent column name across tables
- Timestamps, not dates — harder to partition and query
- Some columns conflate business decisions with system time (`approved_at` is when a human clicked approve, not when the row was loaded)
- Some tables have no system time at all (`fiscal_calendar`)

## Solution

Add `load_date` (DATE) to every Iceberg table in every zone. One column, same name, same meaning everywhere:

> **`load_date`**: The calendar date (UTC) when this row was written to this table in this zone.

### Key properties:
- **Type**: DATE (not TIMESTAMP — date-level granularity is sufficient and partition-friendly)
- **Immutable**: Once set, never changes. A row promoted on March 14 has `load_date = 2026-03-14` forever.
- **Per-zone**: A fact ingested into raw on March 14 gets `load_date = 2026-03-14` in raw. When promoted to base on March 15, the base row gets `load_date = 2026-03-15`. Different zones, different load dates.
- **Not a business date**: `load_date` is orthogonal to `filed_date`, `end_date`, etc. Apple's Q4 2025 10-K (`filed_date = 2026-01-31`) loaded into raw on `load_date = 2026-03-14`.

### Three temporal axes (with bitemporal)

After this change, the pipeline supports three temporal axes:

| Axis | Column(s) | Question It Answers |
|------|-----------|-------------------|
| **Business time** | `filed_date`, `end_date`, `fiscal_period` | When did this happen in the real world? |
| **System time** | `load_date` | When did our pipeline learn about it? |
| **Iceberg time** | Snapshot ID / `ingested_at` / `promoted_at` | What was the exact state at a specific pipeline execution? |

Business time + system time = classic **bitemporal**. Iceberg time adds a third dimension for debugging and lineage (which specific pipeline run produced this row).

### Existing timestamp columns

Keep `ingested_at` and `promoted_at` as-is. They serve a different purpose:
- `load_date` = "what day" (for partitioning, querying, auditing)
- `ingested_at` / `promoted_at` = "what microsecond" (for ordering within a day, debugging)

No columns are removed. `load_date` is derived from the existing timestamps (`ingested_at.date()` for raw, `promoted_at.date()` for base).

## Changes Per Table

### Raw Zone

| Table | Change |
|-------|--------|
| `raw.xbrl_company_facts` | Add `load_date DATE` — set to `ingested_at.date()` at write time |

### Base Zone

| Table | Change |
|-------|--------|
| `base.financial_facts` | Add `load_date DATE` — set to `promoted_at.date()` at write time |
| `base.entity_mappings` | Add `load_date DATE` — set to `date.today()` at promote time |
| `base.entity_resolution_audit` | Add `load_date DATE` — set to `date.today()` at promote time |
| `base.concept_mappings` | Add `load_date DATE` — set to `date.today()` at promote time |
| `base.tag_normalization_audit` | Add `load_date DATE` — set to `date.today()` at promote time |
| `base.fiscal_calendar` | Add `load_date DATE` — set to `date.today()` at promote time |
| `base.amendment_tracking` | Add `load_date DATE` — set to `detected_at.date()` at write time |

## Query Patterns Enabled

```sql
-- What landed today?
SELECT * FROM base.financial_facts WHERE load_date = CURRENT_DATE

-- What did we know as of March 14?
SELECT * FROM base.financial_facts WHERE load_date <= '2026-03-14'

-- How many facts per day?
SELECT load_date, COUNT(*) FROM base.financial_facts GROUP BY load_date ORDER BY load_date

-- Delta between two loads
SELECT * FROM base.financial_facts
WHERE load_date = '2026-03-15'
  AND fact_id NOT IN (SELECT fact_id FROM base.financial_facts WHERE load_date = '2026-03-14')

-- DQ investigation: what was the state when the failure happened?
SELECT * FROM base.entity_mappings WHERE load_date = '2026-03-14'
```

## Migration Strategy

Existing rows need `load_date` backfilled:

| Table | Backfill Strategy |
|-------|------------------|
| `raw.xbrl_company_facts` | `load_date = ingested_at::DATE` |
| `base.financial_facts` | `load_date = promoted_at::DATE` |
| `base.entity_mappings` | `load_date = approved_at::DATE` (closest proxy) |
| `base.entity_resolution_audit` | `load_date = timestamp::DATE` |
| `base.concept_mappings` | `load_date = mapped_at::DATE` |
| `base.tag_normalization_audit` | `load_date = timestamp::DATE` |
| `base.fiscal_calendar` | `load_date = CURRENT_DATE` (no better proxy) |
| `base.amendment_tracking` | `load_date = detected_at::DATE` |

Iceberg supports schema evolution (adding columns), so this is a non-destructive migration. Existing rows get the column added with NULL, then backfilled via table overwrite.

## Implementation

### Files to Modify

| File | Change |
|------|--------|
| `src/raw/xbrl_company_facts/schema.py` | Add `load_date` to schema |
| `src/raw/xbrl_company_facts/ingest.py` | Set `load_date` at write time |
| `src/base/entity_resolution/schema.py` | Add `load_date` to both schemas |
| `src/base/entity_resolution/promote.py` | Set `load_date` at promote time |
| `src/base/xbrl_tag_normalization/schema.py` | Add `load_date` to both schemas |
| `src/base/xbrl_tag_normalization/promote.py` | Set `load_date` at promote time |
| `src/base/financial_facts_model/schema.py` | Add `load_date` to all 3 schemas |
| `src/base/financial_facts_model/promote.py` | Set `load_date` at promote time |
| `governance/data-dictionary.json` | Document `load_date` across all tables |
| `governance/models/` | Add `load_date` to physical models |

### Files to Create

| File | Purpose |
|------|---------|
| `src/infra/migrate_load_date.py` | One-time migration script: add column + backfill |

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| DATE not TIMESTAMP | Day-level is sufficient for "what did we know when." Partitioning by date is standard. Microsecond precision lives in `ingested_at`/`promoted_at`. |
| Per-zone, not inherited | Raw `load_date` and base `load_date` are independent. Data can sit in raw for days before promotion. Each zone tracks when *it* received the data. |
| Column, not just Iceberg snapshots | Snapshots get expired/compacted. A column is permanent, queryable with standard SQL, and visible to downstream consumers who don't know Iceberg. |
| Same name everywhere | `load_date` in every table, every zone. No `raw_load_date` vs `base_load_date`. The table's zone tells you which zone's load date it is. |
| Keep existing timestamps | `ingested_at` and `promoted_at` stay. They answer "what microsecond" for debugging. `load_date` answers "what day" for operations. |

## Verification

1. All tables have `load_date DATE` column
2. Existing rows have `load_date` backfilled from nearest timestamp
3. New writes set `load_date` automatically
4. `SELECT DISTINCT load_date FROM table` returns expected dates
5. Pipeline re-run produces rows with today's `load_date`
6. DQ rule: `load_date IS NOT NULL` (P0) added for all tables
