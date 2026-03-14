# Base Zone: Bitemporal Schema

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
| Primary Agent | @bitemporal-schema |
| Blocked By | — |
| Depends On | `base-financial-facts-model` (🟢 COMPLETE) |

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

## Staff Engineer Review
### Date: 2026-03-14
### Reviewer: @staff-engineer
### Status: APPROVED

### Review Summary

This spec is clean, focused, and well-executed. It does exactly what the spec says — adds an ergonomic layer (query helpers, snapshot management, temporal DQ rules) on top of the existing `base.financial_facts` table without creating new tables or modifying existing schemas. Approved.

### Code Quality

**queries.py** — Solid. The `as_known_on` function is the most interesting piece: it correctly re-computes supersession within a filed_date window rather than relying on the pre-computed `is_superseded` flag. This is the right approach because `is_superseded` reflects the *current* state, not the state at a historical point in time. The SUPERSESSION_GRAIN is imported from `financial_facts_model.config` (single source of truth) rather than re-defined. `compare_periods` handles the division-by-zero case for `pct_change` when `val1 == 0`.

**snapshot_registry.py** — Clean separation. Functions that need Iceberg infra are isolated here, keeping `queries.py` and `validation.py` testable with plain list[dict]. The `snapshot_diff_summary` uses `fact_id` set arithmetic to compute added/removed counts, which is correct.

**validation.py** — All 5 rules handle string-vs-date coercion consistently. The 99% threshold on BASE-BT-004 is well-justified (NT filings, early filings). `run_all_validations` aggregates cleanly with a `reference_date` parameter that threads through to BASE-BT-001, making tests deterministic.

**cli.py** — Functional. The `cmd_history` auto-detection of `start_date` when not provided is a nice UX touch. Lazy imports (`from .queries import ...` inside command functions) keep startup fast.

**config.py** — Read-only re-export of `financial_facts_model.config`. No new state, no new tables. Exactly right.

### Test Quality

29 tests, all passing. No test theater detected.

- **test_queries.py** (12 tests): Uses a well-constructed `_make_fact` factory with realistic defaults. Tests validate actual behavior — `test_before_amendment` and `test_after_amendment` verify that `as_known_on` returns different values based on the as-of date window, which is the core bitemporal query use case. `test_missing_period_returns_none` validates the null case.

- **test_validation.py** (10 tests): Each rule has both pass and fail scenarios with assertions on violation counts, not just boolean pass/fail. The `test_fail_start_equals_end` correctly treats `start == end` as a violation (the spec says `start < end`, not `start <= end`). Tests use explicit `reference_date` parameters to avoid time-dependent flakiness.

- **test_snapshot_registry.py** (5 tests): These are real integration tests — they create actual Iceberg tables in temp directories, append data to create multiple snapshots, then test `get_labeled_snapshots`, `find_snapshot_at`, `snapshot_diff_summary`, and `read_at_snapshot` against real snapshot IDs. No mocks. This is the right way to test snapshot behavior.

- **test_cli.py** (2 tests): Mocks `_load_facts` and `_load_table` to test CLI wiring without Iceberg infra. Validates that the `validate` command outputs all 5 rule IDs and the pass count.

### Governance Artifacts

All four governance artifacts are substantive, not boilerplate:

- **Lineage** (`governance/lineage/base-bitemporal-schema.json`): Correctly identifies `base.financial_facts` as the sole input with `usage: "Read-only"` and empty outputs (no new tables). Includes spec reference and agent attribution.

- **Audit Trail** (`governance/audit-trail/base-bitemporal-schema.json`): Six decisions documented with rationale and confidence levels. Each one explains the *why* (e.g., "filed_date is the real-world 'when was this known?' signal" for the as_known_on design choice).

- **DQ Rules** (`governance/dq-rules/base-bitemporal-schema.json`): All 5 rules documented with categories, priorities, thresholds, and rationale. The rules match the implementation exactly — function signatures, threshold values, and descriptions are consistent.

- **DQ Scorecard** (`governance/dq-scorecards/base-bitemporal-schema-scorecard.md`): Comprehensive — covers not just the 5 DQ rules but also the 12 query helper behaviors and 5 snapshot registry behaviors with test cross-references. Reports full suite compatibility (175 tests passing).

### Minor Observations (Non-blocking)

1. **Empty list edge cases**: `as_known_on([])` returns `[]`, `compare_periods` with empty input returns `None`, `fact_history` with no matches returns `[]`. All behave sensibly, though none have explicit tests for the empty case. Not blocking because the behavior is correct by construction (list comprehensions on empty lists return empty lists).

2. **CLI test coverage**: Only 2 of 5 CLI commands are tested (`validate`, `snapshots`). The `query`, `as-known-on`, and `history` commands are untested at the CLI layer, though their underlying functions are thoroughly tested in `test_queries.py`. Acceptable since the CLI is thin wiring.

3. **`cmd_query` assumes val is always a number** (line 55: `f.get('val'):,.2f`). If `val` is None, this would raise a TypeError. Low risk since `financial_facts` validates non-null values upstream, but worth noting.

### Verdict

**APPROVED.** The implementation matches the spec, the tests validate real behavior, the governance artifacts contain real reasoning, and the architectural decisions are sound. The minor observations above are informational — none warrant blocking.

Spec is ready to be marked COMPLETE.
