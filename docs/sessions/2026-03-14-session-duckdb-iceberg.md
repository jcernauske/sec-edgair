# Session: 2026-03-14

## Prompt Provided
```
infra-setup-duckdb-iceberg.md

bro you working on this or what
```

## Specs Referenced
- docs/specs/infra-setup-duckdb-iceberg.md

## Session Goal
Implement the DuckDB + Iceberg infrastructure verification spec — prove that PyIceberg can write Iceberg tables and DuckDB can read them (including time travel via snapshots) on local file storage with zero infrastructure.

## Changes Made

### Files Created
| File | Purpose |
|------|---------|
| `src/infra/__init__.py` | Package init |
| `src/infra/iceberg_setup.py` | Core Iceberg utilities: catalog setup, table creation, append, DuckDB read (Arrow bridge + native iceberg_scan), snapshot metadata |
| `tests/infra/__init__.py` | Package init |
| `tests/infra/test_iceberg_roundtrip.py` | 19 tests covering roundtrip integrity, snapshot isolation, metadata, schema, edge cases |
| `data/catalog/.gitkeep` | Catalog directory placeholder |
| `governance/audit-trail/infra-setup-duckdb-iceberg.json` | Decision log with 4 architectural decisions and version-specific findings |
| `governance/lineage/infra-setup-duckdb-iceberg.json` | OpenLineage record for the infra setup |

### Files Modified
| File | What Changed |
|------|-------------|
| `pyproject.toml` | Added `pythonpath = ["."]` to pytest config so `src.` imports work; updated pyiceberg dep to include `[sql-sqlite]` extra |

### Files Deleted
None.

## Decisions Made

1. **Arrow bridge is the ONLY reliable time travel pattern.** DuckDB's native `iceberg_scan(path, version := snap_id)` silently ignores the version parameter and returns all 6 rows regardless of which snapshot you request. Tested on DuckDB 1.5.0. This is a critical discovery — the project MUST route all time travel queries through PyIceberg scan → Arrow → DuckDB.

2. **DuckDB iceberg_scan retained for current-state reads.** It works fine for reading the latest snapshot (all 6 rows). Useful as a simpler read path when time travel isn't needed.

3. **SQLAlchemy was a missing dependency.** PyIceberg's SqlCatalog requires sqlalchemy, which wasn't pulled in by the base `pyiceberg` package. Fixed by switching to `pyiceberg[sql-sqlite]` extra.

4. **Added `pythonpath` to pytest config.** The project uses a `src/` layout without being installed as a package. Adding `pythonpath = ["."]` lets pytest find `src.infra.iceberg_setup` without needing `pip install -e .`.

## Problems Encountered

1. **`iceberg_scan` version parameter doesn't do what you'd expect.** The DuckDB docs suggest `version` enables time travel, but in practice (v1.5.0) it returned the full current state regardless of the snapshot ID passed. This is exactly the risk the spec called out. The fallback (PyIceberg scan → Arrow) works perfectly.

2. **Missing sqlalchemy.** `pyiceberg>=0.7` doesn't pull in sqlalchemy by default — you need the `[sql-sqlite]` extra. Quick fix once discovered.

## Current State
- DuckDB + Iceberg is proven working on local file storage with zero infrastructure
- 19 tests pass covering all success criteria from the spec
- Write path: PyIceberg (SqlCatalog + SQLite) → Iceberg tables in `data/base/iceberg_warehouse/`
- Read path (current): DuckDB `iceberg_scan` OR PyIceberg scan → Arrow → DuckDB
- Read path (time travel): PyIceberg scan(snapshot_id=N) → Arrow → DuckDB ONLY
- Versions verified: DuckDB 1.5.0, PyIceberg 0.11.1, PyArrow 23.0.1, Python 3.14.3

## Staff Engineer Review

@staff-engineer reviewed and returned **CHANGES REQUIRED** with 6 issues (1 serious, 2 moderate, 3 minor). All 6 fixed:

| # | Severity | Issue | Fix |
|---|----------|-------|-----|
| 1 | SERIOUS | Bare `except Exception` on `create_table` swallows real errors | Catch `TableAlreadyExistsError` specifically |
| 2 | MODERATE | SQL string interpolation in `iceberg_scan` read path | Use DuckDB parameterized query (`con.execute(sql, [param])`) |
| 3 | MODERATE | Date field detection by column name heuristic | Check Iceberg schema `DateType` instead |
| 4 | MINOR | Snapshot 1 test missing value assertions | Added test verifying COMP_A=1M, COMP_B=5M at snap1 |
| 5 | MINOR | `pytest.raises(Exception)` too broad | Narrowed to `ValueError, match="Snapshot not found"` |
| 6 | MINOR | Bare `except Exception` on `create_namespace` | Catch `NamespaceAlreadyExistsError` specifically |

Re-review: **APPROVED.** 20/20 tests passing. Full review at `reports/staff-engineer-review-infra-setup-duckdb-iceberg.md`.

## Current State
- Spec marked 🟢 COMPLETE
- DuckDB + Iceberg proven working on local file storage with zero infrastructure
- 20 tests pass (19 original + 1 new value assertion test added per staff engineer feedback)
- Write path: PyIceberg (SqlCatalog + SQLite) → Iceberg tables in `data/base/iceberg_warehouse/`
- Read path (current): DuckDB `iceberg_scan` OR PyIceberg scan → Arrow → DuckDB
- Read path (time travel): PyIceberg scan(snapshot_id=N) → Arrow → DuckDB ONLY
- Versions verified: DuckDB 1.5.0, PyIceberg 0.11.1, PyArrow 23.0.1, Python 3.14.3

## Next Steps
1. Proceed to `raw-ingest-xbrl-company-facts.md` — the infra foundation is solid
2. Monitor DuckDB Iceberg extension updates — native time travel may work in future versions

## Session Stats
- Duration: ~20 minutes
- Files created: 8 (7 implementation + 1 staff engineer review report)
- Files modified: 3 (pyproject.toml + iceberg_setup.py + test_iceberg_roundtrip.py after staff review fixes)
- DQ rules added: 5 (roundtrip integrity, snapshot isolation x2, metadata completeness, schema consistency)
- Governance artifacts produced: audit-trail/infra-setup-duckdb-iceberg.json, lineage/infra-setup-duckdb-iceberg.json
- Staff engineer review rounds: 2 (CHANGES REQUIRED → APPROVED)
