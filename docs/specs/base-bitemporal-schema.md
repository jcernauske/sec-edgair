# Base Zone: Bitemporal Schema

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
| Primary Agent | @bitemporal-schema |
| Blocked By | — |
| Depends On | `base-financial-facts-model` (🟠 IMPLEMENTATION) |

---

## Claude Code Prompt

```
Implement the following plan:

# Plan: `base-bitemporal-schema` Spec + Implementation

## Context

This is the **last remaining Phase 2 (Base Zone) item**. The `base-financial-facts-model` spec built the bitemporal foundation:
- `base.financial_facts` (28 fields) with valid time (`start_date`, `end_date`) and transaction time markers (`filed_date`, `is_superseded`, `superseded_by`, `promoted_at`)
- `base.amendment_tracking` pairs original vs amendment filings with `val_change`
- `base.fiscal_calendar` provides temporal alignment
- Iceberg snapshots provide automatic transaction time via `get_snapshots()` and `read_with_duckdb(snapshot_id)`

**What's missing:** The schema is right, but there are no query helpers, temporal validation, or snapshot management tools. Downstream consumers would have to re-implement temporal logic themselves. This spec adds the ergonomic layer.
```

---

## 1. Feature Description

### Problem Statement

The `base-financial-facts-model` spec built the bitemporal data model with valid time fields (`start_date`, `end_date`), transaction time markers (`filed_date`, `is_superseded`, `superseded_by`, `promoted_at`), and Iceberg snapshot-based system time. However, there are no query helpers, temporal validation rules, or snapshot management tools. Downstream consumers would need to re-implement temporal logic (point-in-time queries, amendment history, snapshot time travel) themselves.

### User Story

As a data engineer building the SEC EDGAIR pipeline, I want temporal query helpers, snapshot management, and validation rules that operate on the existing `base.financial_facts` table, so that downstream consumers can perform point-in-time queries, track amendment history, compare periods, and validate temporal consistency without re-implementing bitemporal logic.

## 2. What Was Built

### No New Tables

This spec adds a query/validation module that operates on existing `base.financial_facts`. No new Iceberg tables are created.

### Module Structure

```
src/base/bitemporal/
    __init__.py
    __main__.py            # python -m support
    config.py              # Imports from financial_facts_model (read-only)
    queries.py             # Temporal query helpers (pure functions on list[dict])
    snapshot_registry.py   # Iceberg snapshot enrichment + time travel
    validation.py          # 5 temporal DQ rules
    cli.py                 # query, as-known-on, history, snapshots, validate
```

### Query Helpers (`queries.py`)

| Function | Purpose |
|----------|---------|
| `current_facts(facts, *, cik, concept, cde_id)` | Non-superseded facts with optional filters |
| `as_known_on(facts, as_of_date)` | Point-in-time view using filed_date windowing |
| `fact_history(facts, cik, concept, start_date, end_date, unit)` | All versions of a fact across amendments |
| `compare_periods(facts, cik, concept, period1_end, period2_end, unit)` | Period-over-period comparison with change/pct |
| `facts_at_snapshot(table, snapshot_id, *, cik, concept)` | Iceberg snapshot-based system time travel |

### Snapshot Registry (`snapshot_registry.py`)

| Function | Purpose |
|----------|---------|
| `get_labeled_snapshots(table)` | Enriches snapshots with ISO timestamps, labels, sequence |
| `find_snapshot_at(table, as_of_datetime)` | Find snapshot current at a given datetime |
| `snapshot_diff_summary(table, snap_before, snap_after)` | Count added/removed facts between snapshots |
| `read_at_snapshot(table, snapshot_id)` | Convenience wrapper for snapshot reads |

### Temporal DQ Rules (`validation.py`)

| Rule ID | Description | Threshold |
|---------|-------------|-----------|
| BASE-BT-001 | No facts with filed_date in the future | 100% |
| BASE-BT-002 | start_date < end_date for all period facts | 100% |
| BASE-BT-003 | Superseded facts have filed_date <= superseding fact's filed_date | 100% |
| BASE-BT-004 | filed_date >= end_date (filings come after period ends) | 99% |
| BASE-BT-005 | Every superseded_by accession exists in facts | 100% |

### CLI

```
python -m src.base.bitemporal.cli query --cik 320193 --concept Assets
python -m src.base.bitemporal.cli as-known-on --date 2024-11-01
python -m src.base.bitemporal.cli history --cik 320193 --concept Assets --end-date 2023-12-31
python -m src.base.bitemporal.cli snapshots
python -m src.base.bitemporal.cli validate
```

## 3. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| No new Iceberg tables | Schema is already correct — this adds query/validation, not data |
| `as_known_on` uses `filed_date`, not Iceberg snapshots | `filed_date` is the real-world "when was this known?" signal; Iceberg snapshot time is system-level |
| Query helpers on `list[dict]` | Matches existing pattern, keeps testable without Iceberg infra |
| Snapshot registry is in-memory | Storing snapshot metadata in Iceberg would be circular |
| Import `SUPERSESSION_GRAIN` from financial_facts_model.config | Single source of truth; clean dependency |
| BASE-BT-004 uses 99% threshold | Edge cases (NT filings, preliminary filings) would cause false failures at 100% |

## 4. Test Coverage

29 tests across 4 test files:

| File | Tests | Coverage |
|------|-------|----------|
| `test_queries.py` | 12 | current_facts filters, as_known_on before/after, fact_history, compare_periods |
| `test_validation.py` | 10 | All 5 rules with pass/fail scenarios |
| `test_snapshot_registry.py` | 5 | Labeled snapshots, find_snapshot_at, diff_summary, read_at_snapshot |
| `test_cli.py` | 2 | validate + snapshots commands |

## 5. Governance Artifacts

| Artifact | Path |
|----------|------|
| OpenLineage | `governance/lineage/base-bitemporal-schema.json` |
| Audit Trail | `governance/audit-trail/base-bitemporal-schema.json` |
| DQ Rules | `governance/dq-rules/base-bitemporal-schema.json` |
| DQ Scorecard | `governance/dq-scorecards/base-bitemporal-schema-scorecard.md` |
