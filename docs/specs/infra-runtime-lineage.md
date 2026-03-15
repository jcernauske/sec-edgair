# Infrastructure: Runtime Lineage

## Status: 🟢 COMPLETE

| Status | Meaning |
|--------|---------|
| 🟡 DRAFT | Riffing / initial design |
| 🟠 IMPLEMENTATION | Agent pipeline running |
| 🟢 COMPLETE | Shipped |

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-03-15 |
| Author | Jeff + Claude Code |
| Zone | Infrastructure (cross-cutting) |
| Depends On | All existing promote functions |

---

## Claude Code Prompt

```
I definitly want runtime lineage. I am ok if we create lineage docs from lineage docs.
```

---

## 1. Problem Statement

The 14 lineage JSON files in `governance/lineage/` are static documentation — they describe what the pipeline does but never capture when it ran, how many rows flowed, or which Iceberg snapshot was created. The principal data architect called this "documentation masquerading as lineage."

## 2. Solution

### Runtime Lineage Events → Iceberg Table

Every promote function emits a START and COMPLETE (or FAIL) event to `governance.lineage_events`. This is a real Iceberg table queryable with DuckDB.

### Static Lineage Docs → Generated

The existing `governance/lineage/*.json` files are regenerated from the lineage_events table, giving humans a structural view derived from actual runtime data.

## 3. Schema: `governance.lineage_events`

| # | Column | Type | Required | Description |
|---|--------|------|----------|-------------|
| 1 | event_id | String | Yes | UUID per event |
| 2 | run_id | String | Yes | UUID grouping START + COMPLETE for one execution |
| 3 | event_type | String | Yes | START, COMPLETE, FAIL |
| 4 | job_name | String | Yes | e.g. "base.conformed_facts" |
| 5 | job_namespace | String | Yes | "sec-edgair" |
| 6 | producer | String | Yes | e.g. "src/base/conformed_facts/promote.py" |
| 7 | input_tables | String | Yes | JSON array: ["base.financial_facts", "base.entity_mappings"] |
| 8 | output_table | String | Yes | e.g. "base.conformed_facts" |
| 9 | output_snapshot_id | Long | No | Iceberg snapshot ID from the write (COMPLETE only) |
| 10 | row_count | Integer | No | Rows written (COMPLETE only) |
| 11 | skipped_duplicates | Integer | No | Rows skipped by dedup guard |
| 12 | dq_rules_passed | Integer | No | DQ rules that passed (if validate_after_write ran) |
| 13 | dq_rules_total | Integer | No | Total DQ rules executed |
| 14 | dq_p0_passed | Boolean | No | P0 gate result |
| 15 | duration_ms | Integer | No | Elapsed time in ms (COMPLETE/FAIL only) |
| 16 | error_message | String | No | Error details (FAIL only) |
| 17 | event_time | Timestamptz | Yes | When this event was emitted |

**Grain:** One row per event. Two rows per successful run (START + COMPLETE).

## 4. Implementation

### `src/infra/lineage.py` — Lineage emitter

```python
def emit_start(job_name, input_tables, output_table, producer) -> str:
    """Emit a START event. Returns run_id for pairing with COMPLETE."""

def emit_complete(run_id, job_name, output_table, producer,
                  snapshot_id, row_count, skipped_duplicates,
                  dq_passed, dq_total, dq_p0_passed, duration_ms):
    """Emit a COMPLETE event."""

def emit_fail(run_id, job_name, output_table, producer,
              error_message, duration_ms):
    """Emit a FAIL event."""
```

### Instrumentation pattern in promote functions

```python
from src.infra.lineage import emit_start, emit_complete, emit_fail

def promote_conformed_facts(records, ...):
    run_id = emit_start(
        job_name="base.conformed_facts",
        input_tables=["base.financial_facts", "base.entity_mappings"],
        output_table="base.conformed_facts",
        producer="src/base/conformed_facts/promote.py",
    )
    start = time.monotonic()
    try:
        # ... existing promote logic ...
        emit_complete(run_id, ..., duration_ms=int((time.monotonic() - start) * 1000))
    except Exception as e:
        emit_fail(run_id, ..., error_message=str(e), ...)
        raise
```

### `governance/lineage/*.json` — Generated from runtime data

Add a CLI command: `python -m src.infra.lineage generate-docs`

This queries `governance.lineage_events` for the latest COMPLETE event per job_name, and writes the structural lineage JSON files from real data.

## 5. Promote Functions to Instrument

| Zone | Promote Function | Output Table | Input Tables |
|------|-----------------|--------------|--------------|
| Raw | `ingest_company_facts` | raw.xbrl_company_facts | SEC EDGAR API |
| Base | `promote_approved` (entity) | base.entity_mappings | staging proposals |
| Base | `promote_approved` (tags) | base.concept_mappings | staging proposals |
| Base | `promote_financial_facts` | base.financial_facts | raw.xbrl_company_facts, base.entity_mappings, base.concept_mappings |
| Base | `promote_fiscal_calendar` | base.fiscal_calendar | base.financial_facts |
| Base | `promote_amendment_tracking` | base.amendment_tracking | base.financial_facts |
| Base | `promote_conformed_facts` | base.conformed_facts | base.financial_facts, base.entity_mappings |
| Consumable | `promote_company_financials` | consumable.company_financials | base.conformed_facts, base.entity_mappings |
| Consumable | `promote_financial_ratios` | consumable.financial_ratios | base.conformed_facts |
| Consumable | `promote_period_over_period` | consumable.period_over_period | base.conformed_facts |
| Consumable | `promote_peer_comparison` | consumable.peer_comparison | base.conformed_facts, consumable.financial_ratios |
| Consumable | `promote_amendment_analysis` | consumable.amendment_analysis | base.amendment_tracking, base.conformed_facts |

## 6. Risk

| Risk | Mitigation |
|------|-----------|
| Lineage table doesn't exist on first run | `emit_start` creates table lazily on first call |
| Promote fails after START but before COMPLETE | FAIL event captures error; orphaned STARTs are queryable |
| Performance overhead | One Iceberg append per event (~ms); negligible vs the promote itself |
