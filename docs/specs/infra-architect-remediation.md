# Infrastructure: Principal Architect Remediation

## Status: 🟢 COMPLETE

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-03-15 |
| Author | Jeff + Claude Code |
| Spec Version | 1.0 |
| Zone | Cross-cutting (infra + consumable + ai-ready) |
| Informed By | `governance/reviews/principal-data-architect-review.md` |

---

## Claude Code Prompt

```
Implement the infra-architect-remediation spec.

This addresses all actionable findings from the Principal Data Architect review.
7 remediation items across code quality, scalability, and AI-readiness.

Read governance/reviews/principal-data-architect-review.md for full context.
```

---

## 1. Remediation Items

### Item 1: Add DQ gates to consumable promote functions (Grade impact: B → A)

**Finding:** All 5 consumable promote functions write to Iceberg without running DQ rules. The base zone has `validate_after_write()` — consumable zone doesn't.

**Fix:** After every successful promote in each consumable CLI `cmd_build`, run the DQ rules for that spec. If P0 fails, raise an error. Match the base zone pattern.

**Files:**
- `src/consumable/company_financials/cli.py`
- `src/consumable/financial_ratios/cli.py`
- `src/consumable/period_over_period/cli.py`
- `src/consumable/peer_comparison/cli.py`
- `src/consumable/amendment_analysis/cli.py`

### Item 2: Replace bare except clauses in dedup guards

**Finding:** Every promote function has `except Exception: pass` when loading existing record IDs. This swallows real errors (schema mismatches, corrupted files).

**Fix:** Catch `NoSuchTableError` (table doesn't exist yet — expected on first run) and let everything else propagate.

**Files:** All 5 consumable promote.py files + base promote files

### Item 3: Make anomaly checker generic

**Finding:** Negative equity check is hardcoded to Boeing (`ticker == "BA"`). Any other company with negative equity won't get flagged.

**Fix:** Check the condition generically (any company with Stockholders Equity < 0 or D/E > 50x), not ticker-specific.

**File:** `src/ai_ready/tools/anomaly_checker.py`

### Item 4: Add amendment analysis tool function

**Finding:** `consumable.amendment_analysis` is loaded into DuckDB but no tool function queries it. Users asking "Which companies restated their earnings?" get no answer.

**Fix:** Add `get_amendment_summary(ticker, fiscal_year)` as tool #8.

**Files:**
- `src/ai_ready/tools/financial_tools.py`
- `src/ai_ready/chat/tool_schemas.py`
- `src/ai_ready/chat/system_prompt.py`
- `tests/ai_ready/tools/test_financial_tools.py`

### Item 5: Delete dead code

**Finding:** Three pieces of dead code identified.

**Fix:**
- Remove `read_current_with_iceberg_scan()` from `src/infra/iceberg_setup.py`
- Remove `src/infra/migrate_load_date.py` (one-time migration script)
- Rename `create_test_table` to `get_or_create_table` in `src/infra/iceberg_setup.py` and all callers

### Item 6: Replace in-memory dedup with DuckDB anti-joins (Scalability fix)

**Finding:** Every promote function reads ALL existing records into a Python set for dedup. At 547K rows this is fine. At 5M+ rows it breaks.

**Current pattern (every promote.py):**
```python
existing = read_with_duckdb(table)  # Materializes ENTIRE table
existing_ids = {r["record_id"] for r in existing}  # Python set in memory
records = [r for r in records if r["record_id"] not in existing_ids]  # Python filter
```

**Fixed pattern:**
```python
# Load new records into a temp DuckDB table
con = duckdb.connect()
new_arrow = pa.Table.from_pylist(records)
con.register("new_records", new_arrow)

# Load existing Iceberg table
existing_arrow = table.scan(selected_fields=["record_id"]).to_arrow()
con.register("existing", existing_arrow)

# Anti-join in DuckDB — never materializes full table as Python dicts
result = con.execute("""
    SELECT n.* FROM new_records n
    LEFT JOIN existing e ON n.record_id = e.record_id
    WHERE e.record_id IS NULL
""").arrow()

# Only the new records, filtered by DuckDB
records = result.to_pylist()
```

**Key improvements:**
- PyIceberg `scan(selected_fields=["record_id"])` reads only the record_id column, not all 25 columns
- DuckDB anti-join is O(N) with hash join, same as Python set, but operates on columnar Arrow data
- Memory footprint: ~1 column (record_id strings) instead of full rows
- Scales to 10M+ rows without Python memory pressure

**Files:** All promote.py files (5 consumable + base)

Also update `read_with_duckdb` to support column selection, or add a new `read_column_with_duckdb(table, column)` helper.

### Item 7: Replace full-table DQ reads with scan pushdown

**Finding:** The DQ runner loads entire Iceberg tables via `scan().to_arrow()` for every SQL rule execution.

**Fix:** Instead of loading tables into memory and registering them, use DuckDB's `iceberg_scan()` directly with the metadata file path. This lets DuckDB read only the data needed for each SQL query (predicate pushdown, column pruning).

**Current pattern (dq_runner):**
```python
arrow = table.scan().to_arrow()  # Full table in memory
con.register(table_name, arrow)  # Register for SQL
con.execute(rule["sql"])  # Query against in-memory copy
```

**Fixed pattern:**
```python
# Get metadata path from PyIceberg
metadata_path = table.metadata_location
# Let DuckDB read directly from Iceberg files with pushdown
sql = rule["sql"].replace(f"{namespace}.{name}", f"iceberg_scan('{metadata_path}')")
con.execute(sql)
```

This is a bigger change since DQ rule SQL references table names like `consumable.company_financials` which need to be rewritten to `iceberg_scan('path/to/metadata.json')`. Could implement as a SQL rewrite layer in the DQ runner.

**File:** `src/infra/dq_runner.py`

## 2. Priority Order

| # | Item | Risk Level | Effort | Do Now? |
|---|------|-----------|--------|---------|
| 1 | DQ gates on consumable promote | High | Low | Yes |
| 2 | Bare except clauses | Medium | Low | Yes |
| 3 | Generic anomaly checker | Medium | Low | Yes |
| 4 | Amendment analysis tool | Low | Low | Yes |
| 5 | Dead code cleanup | Low | Low | Yes |
| 6 | DuckDB anti-join dedup | Medium | Medium | Yes |
| 7 | DQ runner scan pushdown | Medium | Medium | Yes |

## 3. Verification

After all fixes:
- `uv run pytest tests/` — 442+ tests pass
- `uv run python -m src.infra.dq_runner run` — 92 rules, P0 PASS
- `PYTHONPATH=. uv run python scripts/verify.py` — 57/57
- `PYTHONPATH=. uv run python scripts/verify_all_metrics.py` — 31/31
- Rebuild all consumable tables and verify DQ gates fire
- Test dedup with a re-promote (should skip all existing records via anti-join)
