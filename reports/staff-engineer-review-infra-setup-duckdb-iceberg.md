# Staff Engineer Review: infra-setup-duckdb-iceberg

### Date: 2026-03-14
### Reviewer: @staff-engineer (15 YOE, production incident survivor)
### Status: CHANGES REQUIRED

### Verdict

Look, I love Claude, BUT... this is actually closer to production-quality than I expected. The core functionality is sound -- PyIceberg writes, DuckDB reads, snapshot isolation works, tests are real tests with real assertions. The discovery that `iceberg_scan`'s `version` parameter silently ignores the snapshot and returns latest is exactly the kind of finding that saves you at 3am. That said, there are two issues in the implementation that need fixing before I put my name on it: a bare `except Exception` that silently swallows errors where it shouldn't, and a potential path traversal via string interpolation in the `iceberg_scan` read path. The tests are good but could exercise one more failure mode. Fix the issues below and this ships.

### Code Quality

**`src/infra/iceberg_setup.py`**

The module docstring documenting the `iceberg_scan` time travel limitation is the most useful thing in this file. Someone will try to use `iceberg_scan` with a version parameter six months from now, and this will save them a day. The function signatures match the spec. The Arrow bridge pattern is the correct approach.

Two problems:

1. `create_test_table` uses bare `except Exception: pass` for namespace creation AND bare `except Exception` for table creation. The namespace one is tolerable -- `create_namespace` when it already exists is a known pattern. But the table creation catch is dangerous: if `create_table` fails for a reason OTHER than "table exists" (permissions, disk full, corrupt catalog), it silently swallows that error and tries to load a table that may not exist, giving a confusing secondary error instead of the real one. This is the kind of thing that makes you debug for two hours at 3am before you realize the actual problem was a permissions error that got eaten.

2. `read_current_with_iceberg_scan` interpolates `metadata_loc` directly into the SQL string. If `metadata_loc` ever contains a single quote (unlikely for file paths, but not impossible on some systems), this is a SQL injection into DuckDB. More practically, it will just break with a confusing parse error. Use parameterized queries.

3. `append_data` has a fragile heuristic for date conversion -- it checks `name.endswith("_date")` to decide whether to convert strings to dates. If someone adds a field called `update_date_source` or `is_dated`, this heuristic breaks silently. For this spec's limited test schema, it works. For anything beyond that, it's a bug factory. Flagging as moderate since the spec explicitly says "real schemas come in later specs" and this will need to be revisited anyway.

**`tests/infra/test_iceberg_roundtrip.py`**

Fine. Tests use `tmp_path` (good -- no test pollution). The fixture creates all three snapshots once and shares them across tests (efficient). Assertions are specific: they check row counts AND actual values AND types AND parent chains. This is not test theater.

### Test Quality

These are real tests. Specific observations:

- `test_current_state_values_match` asserts on sorted company IDs, confirming all 6 rows contain the expected companies. Not just `len == 6`.
- `test_snapshot_2_contains_amendments` checks that COMP_A has BOTH the original and amended value. This proves snapshot isolation is actually accumulating, not replacing.
- `test_parent_chain_is_correct` validates the full parent chain: first snapshot has no parent, each subsequent one points to the previous. This is the kind of test people skip and then wonder why their snapshot graph is corrupt.
- `test_field_types_preserved` confirms that dates come back as `datetime.date`, not strings. This matters for downstream consumers.
- `test_nonexistent_snapshot_raises_error` uses bare `pytest.raises(Exception)` -- should be narrowed to the specific exception type, but it at least confirms the failure path exists.
- Edge case coverage: empty table, idempotent setup, table-already-exists. All present. All with meaningful assertions.

One gap: there's no test that the VALUES in snapshot 1 are correct (e.g., COMP_A revenue is 1,000,000 not 1,100,000). The test checks company IDs and row counts but doesn't verify the actual numeric values at snapshot 1. At snapshot 2 it checks COMP_A has both values, which is good, but snapshot 1 should verify the original values haven't leaked in from snapshot 2. This is how you catch a "time travel returns all data regardless of snapshot" bug that happens to have the right row count.

### Spec Compliance

Checking every success criterion:

| Criterion | Status | Notes |
|-----------|--------|-------|
| DuckDB can create Iceberg table on local storage (no catalog server) | PASS | SqlCatalog with SQLite, no server |
| Data can be written and snapshot created | PASS | `append_data` returns snapshot ID |
| Additional data appended, new snapshot created | PASS | 3 batches, 3 snapshots |
| Previous snapshots queryable (time travel) | PASS | Via PyIceberg scan, NOT via `iceberg_scan` -- deviation documented |
| Snapshot metadata inspectable | PASS | IDs, timestamps, parents, operations |
| Zero external infrastructure | PASS | SQLite + local filesystem only |
| pytest suite validates all above | PASS | 19 tests, all passing |
| Setup documented with known limitations | PASS | Module docstring + audit trail JSON |

The spec asked to test BOTH `iceberg_scan` and the PyIceberg-to-Arrow approach and document which works. Both were tested, findings documented. The `iceberg_scan` limitation discovery is valuable.

The spec mentioned `data/catalog/.gitkeep` -- present.

The spec function signature for `read_with_duckdb` takes `warehouse_path, catalog_path, namespace, table_name` but the implementation takes `table: Table`. This is a deviation from the spec's pseudocode. It's actually a BETTER design (passing the table object avoids re-constructing the catalog), but it's undocumented as a deviation.

### Governance Artifacts

**`governance/audit-trail/infra-setup-duckdb-iceberg.json`** -- This is good. Real decisions with real rationale. The `iceberg_scan` time travel discovery is documented with version numbers. The `versions_tested` and `known_limitations` sections are exactly what future developers need.

**`governance/lineage/infra-setup-duckdb-iceberg.json`** -- Adequate. OpenLineage format, correct source/target. The `eventTime` is `2026-03-14T00:00:00Z` which is a placeholder timestamp (midnight UTC) rather than actual execution time. Minor.

### Issues

| # | Severity | File | Issue | Required Fix |
|---|----------|------|-------|-------------|
| 1 | SERIOUS | src/infra/iceberg_setup.py:54-57 | `create_test_table` catches ALL exceptions from `create_table` and silently falls back to `load_table`. If table creation fails for a real reason (permissions, disk, corrupt catalog), the error is swallowed and replaced with a confusing secondary error from `load_table`. | Catch the specific exception PyIceberg raises for "table already exists" (likely `TableAlreadyExistsError` from `pyiceberg.exceptions`). Let all other exceptions propagate. |
| 2 | MODERATE | src/infra/iceberg_setup.py:110 | `read_current_with_iceberg_scan` interpolates `metadata_loc` directly into SQL via f-string. If the path contains special characters (single quotes, semicolons), this breaks or worse. | Use DuckDB's parameterized query mechanism or at minimum escape the path value. |
| 3 | MODERATE | src/infra/iceberg_setup.py:66-69 | Date field detection relies on column name ending with `_date`. This heuristic will break for fields like `is_dated` or `date_source`. | Check the Iceberg schema field type (`DateType`) instead of inferring from the column name. The schema is already available via `table.schema().fields`. |
| 4 | MINOR | tests/infra/test_iceberg_roundtrip.py:105-112 | Snapshot 1 isolation test checks company IDs and row count but not the actual values. Does not verify that COMP_A revenue at snapshot 1 is 1,000,000 (not 1,100,000 from snapshot 2). | Add a value assertion: verify COMP_A's revenue at snapshot 1 is exactly 1,000,000. |
| 5 | MINOR | tests/infra/test_iceberg_roundtrip.py:210 | `pytest.raises(Exception)` is too broad -- any exception passes this test, including `AttributeError` from a typo in the test itself. | Narrow to the specific exception type PyIceberg raises for invalid snapshot IDs. |
| 6 | MINOR | src/infra/iceberg_setup.py:48-51 | `create_namespace` also uses bare `except Exception: pass`. Tolerable for "already exists" but could mask real errors. | Catch `NamespaceAlreadyExistsError` specifically if PyIceberg exposes it. |

### What's Acceptable

- The PyIceberg scan to Arrow to DuckDB bridge pattern is the correct architecture. The discovery that `iceberg_scan`'s version parameter silently fails is the single most valuable output of this spec.
- Test structure is solid. Tests are organized by spec DQ rule categories. Assertions validate behavior, not just "it didn't crash."
- Audit trail captures real decisions with version numbers and alternatives considered. Not boilerplate.
- The fixture uses `tmp_path` for full isolation. No leftover state between test runs.
- 19 tests in 0.70 seconds. No performance concerns in the test suite.

### Recommendations

1. Fix issue #1 (bare except on table creation) before merging. This is the kind of thing that costs you two hours in prod debugging.
2. Fix issue #3 (date heuristic) before the next spec introduces real schemas. The current approach technically works for this spec's test data but is a latent bug.
3. Issues #2, #4, #5, #6 can be addressed in a follow-up but should not be forgotten.

### Questions for the Author

1. The spec's `read_with_duckdb` signature takes `warehouse_path, catalog_path, namespace, table_name` but the implementation takes `table: Table`. Was this a deliberate improvement? If so, document it as a spec deviation.
2. Has the `iceberg_scan` silent version failure been reported upstream to DuckDB? This affects anyone using their Iceberg extension for time travel.
3. What happens if two processes try to `append_data` to the same table simultaneously via the SQLite catalog? The audit trail mentions "single-user" but the code doesn't enforce it. Is there a plan for this when CI runs parallel tests?

---

## Re-Review: Round 2

### Date: 2026-03-14
### Reviewer: @staff-engineer
### Status: APPROVED

### Issues Addressed
| # | Original Issue | Fixed? | Notes |
|---|---------------|--------|-------|
| 1 | SERIOUS: Bare `except Exception` on `create_table` swallows real errors | Yes | Now catches `TableAlreadyExistsError` specifically (imported from `pyiceberg.exceptions`). All other exceptions propagate. This is exactly what I asked for. |
| 2 | MODERATE: SQL string interpolation in `iceberg_scan` query | Yes | Now uses `con.execute("SELECT * FROM iceberg_scan(?)", [metadata_loc])` -- parameterized query, no interpolation. Clean fix. |
| 3 | MODERATE: Date field detection via column name heuristic (`name.endswith("_date")`) | Yes | Now builds a set of date fields by checking `isinstance(f.field_type, DateType)` against the Iceberg schema. This is schema-driven, not name-driven. Will work correctly regardless of column naming conventions. |
| 4 | MINOR: Snapshot 1 test missing value assertions | Yes | New test `test_snapshot_1_has_original_values_not_amendments` verifies COMP_A revenue is 1,000,000.0 (not 1,100,000.0) and COMP_B total_assets is 5,000,000.0 (not 5,200,000.0) at snapshot 1. This catches the "time travel returns wrong data but right row count" class of bugs. Test count went from 19 to 20. |
| 5 | MINOR: `pytest.raises(Exception)` too broad on nonexistent snapshot test | Yes | Now uses `pytest.raises(ValueError, match="Snapshot not found")`. Both the exception type and the message are validated. A typo in the test itself would raise `AttributeError` or `NameError`, which would NOT match `ValueError`, so this test is no longer accidentally passable. |
| 6 | MINOR: Bare `except Exception: pass` on `create_namespace` | Yes | Now catches `NamespaceAlreadyExistsError` specifically (imported from `pyiceberg.exceptions` on the same line as `TableAlreadyExistsError`). |

### New Issues Found

None. The fixes are surgical -- each one addresses exactly the problem I raised without introducing new complexity or side effects. No new code paths, no new dependencies, no new abstractions. The imports were added cleanly. The test data constants were already in scope. The `DateType` import was the only new type import needed and it's used immediately.

### Test Results

All 20 tests pass in 0.72 seconds. The new test (`test_snapshot_1_has_original_values_not_amendments`) exercises the value-level snapshot isolation that was previously only checked at the row-count level.

```
tests/infra/test_iceberg_roundtrip.py  20 passed in 0.72s
```

### Verdict

All six issues addressed. No regressions. No new problems. Tests pass.

I'll be honest -- and I don't say this often -- the fixes are clean. No over-engineering, no "while I'm in here let me refactor everything" scope creep, no introducing a new abstraction layer to solve a one-line problem. Each fix does exactly one thing. That's... refreshing. I'm sure Claude had good intentions here, and this time, the execution matched.

The CEO said use AI. He didn't say trust AI. But in this case, after human review caught six issues and the fixes came back correct on the first try... I'll allow it. This time.

Approved for merge.
