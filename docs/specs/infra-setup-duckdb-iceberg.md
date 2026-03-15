# Verify DuckDB + Iceberg Local Read/Write

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
| Created | 2026-03-13 |
| Author | Jeff + Claude Desktop |
| Spec Version | 1.0 |
| Last Updated | 2026-03-13 |
| Zone | Infrastructure |
| Primary Agent | @temporal-modeler |
| Blocked By | — |

---

## Claude Code Prompt

```
Read the spec at docs/specs/infra-setup-duckdb-iceberg.md in its entirety.

Prove that DuckDB can create, write, snapshot, and query Iceberg tables
on local file storage with zero infrastructure. This is the foundation
for the entire project — if this doesn't work, nothing else does.

Agent workflow:
1. @governance-reviewer — Pre-implementation review of this spec
2. @temporal-modeler — Implement the DuckDB + Iceberg verification
3. @lineage-tracker — Log infrastructure setup lineage (source of truth for "how was this environment configured")
4. @dq-engineer — Generate validation tests proving Iceberg behavior
5. @cde-tagger — N/A for infra spec (document as N/A)
6. @doc-generator — Document the verified DuckDB + Iceberg setup and capabilities
7. @governance-reviewer — Post-implementation verification

Key changes:
1. src/infra/iceberg_setup.py — CREATE — Iceberg catalog and table creation utilities
2. src/infra/__init__.py — CREATE — Package init
3. tests/infra/test_iceberg_roundtrip.py — CREATE — End-to-end Iceberg read/write/snapshot tests
4. tests/infra/__init__.py — CREATE — Package init
5. data/base/ — WRITE — Test Iceberg tables (gitignored)
6. governance/audit-trail/infra-setup-duckdb-iceberg.json — CREATE — Decision log

No dependencies on other specs. This is the first spec.
```

---

## 1. Feature Description

### Problem Statement
The entire SEC EDGAIR architecture depends on DuckDB reading and writing Apache Iceberg tables on local file storage. Iceberg's time travel via snapshots is how we handle bitemporality — amendments and restatements create new snapshots, and point-in-time queries use `SELECT ... AT (VERSION => snapshot_id)` or equivalent. If this doesn't work locally with zero infrastructure (no catalog server, no Docker, no cloud account), the project's core premise is broken.

DuckDB's Iceberg support has been evolving rapidly. We need to verify exactly what works today: table creation, data writes, snapshot creation, snapshot queries, and schema evolution. We need to know the boundaries before we build on top of them.

### User Story
As a developer cloning this repo, I want to run a single script that proves DuckDB + Iceberg works on my machine so that I know the foundation is solid before building anything on top of it.

### Success Criteria
- [ ] DuckDB can create an Iceberg table on local file storage (no catalog server)
- [ ] Data can be written to the table and a snapshot is created
- [ ] Additional data can be appended and a new snapshot is created
- [ ] Previous snapshots are queryable (time travel works)
- [ ] Snapshot metadata is inspectable (snapshot IDs, timestamps, parent snapshots)
- [ ] The entire setup requires zero external infrastructure
- [ ] A pytest suite validates all of the above
- [ ] The setup is documented with known limitations

---

## 2. Design Decisions

### Key Choices
| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Use PyIceberg for catalog/table management, DuckDB for querying | DuckDB's native Iceberg extension is read-only as of early 2026. PyIceberg handles writes, DuckDB handles analytical queries. This is the standard pattern. | DuckDB Iceberg extension alone (can't write), Spark (too heavy, violates zero-infra) |
| SQLite-backed PyIceberg catalog | Zero infrastructure, file-based, survives process restarts. Catalog file lives in `data/catalog/` | REST catalog (needs a server), Hive Metastore (way too heavy), in-memory (doesn't persist) |
| Store Iceberg warehouse in `data/base/` | Matches the project's zone layout. Base zone is where governed Iceberg tables live. | Separate `data/iceberg/` directory (unnecessary split) |
| Test with synthetic financial data | We need controlled data to verify snapshot behavior — known values we can assert against. Real EDGAR data comes in the next spec. | Use real EDGAR data (adds parsing complexity to what should be a pure infra test) |

### Open Questions (Resolved)
| Question | Resolution |
|----------|------------|
| Can DuckDB read Iceberg tables written by PyIceberg? | This is what we're testing. If it doesn't work, we need to know now. |
| Does DuckDB support `AT VERSION` or `AT TIMESTAMP` for Iceberg? | Verify during implementation. Document the exact syntax that works. |
| What's the PyIceberg catalog type for pure local? | `sql` catalog type with SQLite backend — no server needed. |

### Constraints
- Zero external infrastructure — no Docker, no cloud, no catalog server
- Must work on macOS (Jeff's dev machine) and Linux (CI, contributors)
- DuckDB Iceberg extension is read-only — all writes go through PyIceberg
- PyIceberg requires PyArrow (already in dependencies)

---

## 3. Data Contract / Schema Design

> This spec uses synthetic test data to verify infrastructure. The schema is intentionally
> simple — just enough structure to prove Iceberg works. Real schemas come in later specs.

### Test Table Schema (Iceberg)

| Field | Type | Description |
|-------|------|-------------|
| company_id | STRING | Synthetic company identifier |
| metric_name | STRING | Financial metric name (e.g., "revenue", "total_assets") |
| value | DOUBLE | Metric value |
| reporting_period | STRING | Period identifier (e.g., "Q3-2024") |
| filed_date | DATE | Simulated filing date |

### Iceberg Table Properties

| Property | Value |
|----------|-------|
| Table name | test_db.financial_facts_test |
| Warehouse | data/base/iceberg_warehouse |
| Catalog type | sql (SQLite backend) |
| Catalog file | data/catalog/catalog.db |

### Snapshot Test Plan

| Snapshot | Contents | Purpose |
|----------|----------|---------|
| Snapshot 1 | 3 rows — original filings for companies A, B, C | Prove basic write + snapshot creation |
| Snapshot 2 | Snapshot 1 rows + 2 new rows — amended values for companies A, B | Prove append creates new snapshot, original data preserved |
| Snapshot 3 | All previous rows + 1 row — new filing for company D | Prove multiple snapshots accumulate correctly |

### Query Verification

| Query | Expected Result |
|-------|----------------|
| Current table (no time travel) | All 6 rows across all snapshots |
| At Snapshot 1 | Only 3 original rows |
| At Snapshot 2 | 5 rows (original 3 + 2 amendments) |
| Snapshot metadata inspection | 3 snapshots with timestamps and parent references |

---

## 4. Technical Specification

### Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `src/infra/__init__.py` | CREATE | Package init |
| `src/infra/iceberg_setup.py` | CREATE | Iceberg catalog initialization, table creation, write utilities |
| `tests/infra/__init__.py` | CREATE | Package init |
| `tests/infra/test_iceberg_roundtrip.py` | CREATE | Full roundtrip test: create → write → snapshot → query → time travel |
| `data/catalog/.gitkeep` | CREATE | Catalog directory (catalog.db is gitignored) |

### Core Implementation: `src/infra/iceberg_setup.py`

This module provides:

1. **`get_catalog(warehouse_path, catalog_path)`** — Returns a PyIceberg `SqlCatalog` backed by SQLite at the given path. Creates the catalog DB if it doesn't exist.

2. **`create_test_table(catalog, namespace, table_name, schema)`** — Creates an Iceberg table with the given schema in the given namespace. Creates the namespace if it doesn't exist. Returns the table object.

3. **`append_data(table, records: list[dict])`** — Converts records to a PyArrow table and appends to the Iceberg table. Returns the new snapshot ID.

4. **`read_with_duckdb(warehouse_path, catalog_path, namespace, table_name, snapshot_id=None)`** — Reads the Iceberg table using DuckDB. If `snapshot_id` is provided, reads that specific snapshot. Returns a list of dicts (or a PyArrow table — implementation decides).

5. **`get_snapshots(table)`** — Returns snapshot metadata: snapshot ID, timestamp, parent snapshot ID, operation type.

```python
# Pseudocode for the key verification:

# 1. Create catalog and table
catalog = get_catalog("data/base/iceberg_warehouse", "data/catalog/catalog.db")
table = create_test_table(catalog, "test_db", "financial_facts_test", SCHEMA)

# 2. Write batch 1 → snapshot 1
snap1 = append_data(table, BATCH_1)  # 3 rows

# 3. Write batch 2 → snapshot 2
snap2 = append_data(table, BATCH_2)  # 2 more rows

# 4. Write batch 3 → snapshot 3
snap3 = append_data(table, BATCH_3)  # 1 more row

# 5. Query current state via DuckDB → expect 6 rows
current = read_with_duckdb(...)
assert len(current) == 6

# 6. Query at snapshot 1 via DuckDB → expect 3 rows
historical = read_with_duckdb(..., snapshot_id=snap1)
assert len(historical) == 3

# 7. Inspect snapshot metadata
snapshots = get_snapshots(table)
assert len(snapshots) == 3
```

### DuckDB + Iceberg Read Pattern

DuckDB reads Iceberg tables through the `iceberg_scan` function or by attaching the catalog. The exact mechanism depends on what DuckDB's current Iceberg extension supports. Implementation should try both approaches and document what works:

**Approach A — `iceberg_scan` function:**
```sql
SELECT * FROM iceberg_scan('data/base/iceberg_warehouse/test_db/financial_facts_test');
```

**Approach B — PyIceberg scan → DuckDB:**
```python
# Use PyIceberg to scan (supports snapshot selection), convert to Arrow, load into DuckDB
arrow_table = table.scan(snapshot_id=snap1).to_arrow()
duckdb.sql("SELECT * FROM arrow_table")
```

Both approaches should be tested. Document which works, which doesn't, and any caveats.

### Edge Cases to Handle
1. Catalog DB doesn't exist yet — should be created automatically
2. Namespace doesn't exist — should be created automatically
3. Table already exists — should handle gracefully (return existing or raise clear error)
4. DuckDB Iceberg extension not installed — clear error message with install instructions
5. Empty table query — should return empty result, not error
6. Snapshot ID that doesn't exist — should raise clear error

### Testing Impact Analysis

#### Existing DQ Rules at Risk
None — this is the first spec. No existing tests.

#### New DQ Rules Required

| Category | What to Validate | Priority | Threshold |
|----------|------------------|----------|-----------|
| Roundtrip integrity | Data written via PyIceberg matches data read via DuckDB | P0 | 100% |
| Snapshot isolation | Querying snapshot N returns exactly the rows from snapshots 1..N | P0 | 100% |
| Snapshot metadata | All snapshots have IDs, timestamps, and correct parent references | P0 | 100% |
| Schema consistency | Iceberg schema matches expected field names and types | P1 | 100% |
| Idempotency | Running setup twice doesn't corrupt existing data | P1 | 100% |

#### Lineage Impact

| Source | Transformation | Target | OpenLineage Job |
|--------|---------------|--------|-----------------|
| (manual synthetic data) | Iceberg table creation + write | data/base/iceberg_warehouse/test_db/financial_facts_test | infra.create_test_table |

---

## 5. Architecture Review

### Date: [YYYY-MM-DD]
### Reviewer: @governance-reviewer
### Status: ⏳ PENDING | ✅ APPROVED | 🟠 CHANGES REQUESTED | 🔴 REJECTED

### Assessment

#### Data Model Integrity
[To be filled by @governance-reviewer]

#### Governance Completeness
[To be filled by @governance-reviewer]

#### Risk Assessment
| Risk | Severity | Mitigation |
|------|----------|------------|
| DuckDB can't read PyIceberg-written tables | 🔴 | Test early. If broken, fall back to PyIceberg scan → Arrow → DuckDB path |
| DuckDB Iceberg extension doesn't support snapshot queries | 🟠 | Use PyIceberg for snapshot selection, DuckDB for analytical queries on the Arrow result |
| PyIceberg SQLite catalog has concurrency issues | 🟡 | Not a concern for single-user local dev. Document limitation for future scaling |

#### Verdict
- [ ] Architecture is sound, proceed to implementation
- [ ] Minor adjustments needed (see below), proceed with caution
- [ ] Significant changes required, do not proceed
- [ ] Fundamental issues, escalate to human

### Required Changes
1. [To be filled]

### Resolution
[To be filled after iteration]

---

## 6. Implementation Log

### Started: [YYYY-MM-DD HH:MM]
### Completed: [YYYY-MM-DD HH:MM]
### Status: ⏳ IN PROGRESS | ✅ DONE | 🔴 BLOCKED

### Agent Activity

| Step | Agent | Action | Timestamp | Status |
|------|-------|--------|-----------|--------|
| Pre-review | @governance-reviewer | Reviewed spec | — | ⏳ |
| Implementation | @temporal-modeler | Built Iceberg setup utilities | — | ⏳ |
| Lineage | @lineage-tracker | Logged infra setup lineage | — | ⏳ |
| DQ | @dq-engineer | Generated roundtrip validation tests | — | ⏳ |
| CDE | @cde-tagger | N/A — infra spec | — | N/A |
| Docs | @doc-generator | Documented DuckDB + Iceberg setup | — | ⏳ |
| Post-review | @governance-reviewer | Governance completeness check | — | ⏳ |

### Files Modified

| File | Changes | Lines |
|------|---------|-------|
| `path/to/file` | [Summary] | +XX/-YY |

### Implementation Notes
[Key decisions made during implementation — especially: which DuckDB Iceberg read pattern works]

### Discoveries
[Critical: document exactly what DuckDB + Iceberg can and cannot do as of today's versions]

### Deviations from Spec
| Deviation | Reason | Severity |
|-----------|--------|----------|
| [What changed] | [Why] | 🟡/🟠/🔴 |

### Build Status
- [ ] Clean build achieved
- [ ] No new warnings introduced
- [ ] All governance artifacts produced

---

## 7. Test Coverage (DQ Results)

### Date: [YYYY-MM-DD]
### Status: ⏳ IN PROGRESS | ✅ DONE | 🔴 BLOCKED

### DQ Rules Executed

| Rule | Type | Table | Threshold | Result | Pass/Fail |
|------|------|-------|-----------|--------|-----------|
| Roundtrip integrity | Consistency | financial_facts_test | 100% | — | ⏳ |
| Snapshot isolation (snap 1) | Consistency | financial_facts_test | 100% | — | ⏳ |
| Snapshot isolation (snap 2) | Consistency | financial_facts_test | 100% | — | ⏳ |
| Snapshot metadata complete | Completeness | (metadata) | 100% | — | ⏳ |
| Schema consistency | Validity | financial_facts_test | 100% | — | ⏳ |

### DQ Scorecard

| Table | Rules Passed | Rules Failed | Rules Warning | Overall |
|-------|-------------|-------------|---------------|---------|
| financial_facts_test | — | — | — | ⏳ |

### Edge Cases Covered
- [ ] Empty table query
- [ ] Duplicate writes (idempotency)
- [ ] Non-existent snapshot ID
- [ ] Table already exists

### Gaps Identified
[To be filled]

---

## 8. Code Review (Post-Implementation Governance Review)

### Date: [YYYY-MM-DD]
### Reviewer: @governance-reviewer
### Status: ⏳ PENDING | ✅ APPROVED | 🟠 CHANGES REQUIRED | 🔴 BLOCKED

### Summary
[To be filled]

### Governance Artifacts Verified

| Artifact | Present | Valid | Notes |
|----------|---------|-------|-------|
| OpenLineage records | ⏳ | ⏳ | Infra setup lineage |
| CDE mappings in catalog | N/A | N/A | No CDEs in infra spec |
| DQ rules generated | ⏳ | ⏳ | Roundtrip + snapshot tests |
| DQ scorecard produced | ⏳ | ⏳ | — |
| Data dictionary updated | ⏳ | ⏳ | Document test table schema |
| Audit trail entries | ⏳ | ⏳ | Catalog type decision, read pattern decision |
| Data contracts updated | N/A | N/A | No consumables affected |

### Findings
[To be filled]

### What's Good
[To be filled]

### Required Changes
[To be filled]

---

## 9. Verification

### Date: [YYYY-MM-DD]
### Status: ⏳ PENDING | ✅ PASSED | 🔴 FAILED

### Build Verification
```
Build result: ⏳
Warnings: —
Errors: —
```

### DQ Verification
```
DQ Rules Run: —
Passed: —
Failed: —
Warning: —
```

### Governance Verification
```
Lineage Records: ⏳
CDE Mappings: N/A
Data Dictionary: ⏳
Audit Trail: ⏳
Data Contracts: N/A
```

### Build Accountability Log

| Attempt | Status | Broken By | Error Summary | Fixed By | Resolution |
|---------|--------|-----------|---------------|----------|------------|
| 1 | ⏳ | — | — | — | — |

### Final Checklist
- [ ] All DQ rules pass
- [ ] No new warnings
- [ ] All governance artifacts produced and valid
- [ ] Lineage complete from source to target
- [ ] CDE mappings in catalog (N/A for this spec)
- [ ] Data dictionary updated
- [ ] Audit trail entries present with rationale
- [ ] Iceberg snapshots created correctly
- [ ] Point-in-time queries return expected results

---

## 10. Governance Artifacts

### Lineage Records (OpenLineage)

| Source | Transformation | Target | Job Name |
|--------|---------------|--------|----------|
| (synthetic test data) | PyIceberg table creation + append | data/base/iceberg_warehouse/test_db/financial_facts_test | infra.verify_iceberg_setup |

### CDE Mappings

N/A — Infrastructure spec. No business data fields to map.

### DQ Rules

| Rule | Type | Table | Field | Threshold |
|------|------|-------|-------|-----------|
| Roundtrip write/read match | Consistency | financial_facts_test | (all) | 100% |
| Snapshot 1 row count = 3 | Completeness | financial_facts_test | — | 100% |
| Snapshot 2 row count = 5 | Completeness | financial_facts_test | — | 100% |
| Snapshot 3 row count = 6 | Completeness | financial_facts_test | — | 100% |
| All snapshots have metadata | Completeness | (metadata) | — | 100% |

### Data Dictionary Entries

| Field | Plain-English Definition | CDE | Source | Owner |
|-------|------------------------|-----|--------|-------|
| company_id | Synthetic test company identifier | N/A | Test data | @temporal-modeler |
| metric_name | Name of financial metric (test) | N/A | Test data | @temporal-modeler |
| value | Numeric metric value (test) | N/A | Test data | @temporal-modeler |
| reporting_period | Fiscal period identifier (test) | N/A | Test data | @temporal-modeler |
| filed_date | Simulated SEC filing date (test) | N/A | Test data | @temporal-modeler |

### Audit Trail Entries

| Decision | Agent | Rationale | Confidence |
|----------|-------|-----------|------------|
| Use PyIceberg SqlCatalog with SQLite backend | @temporal-modeler | Zero infrastructure requirement — no catalog server needed. SQLite is file-based, works everywhere. | High |
| Use PyIceberg for writes, DuckDB for reads | @temporal-modeler | DuckDB Iceberg extension is read-only. This is the documented pattern for the ecosystem. | High |
| DuckDB Iceberg read pattern selection | @temporal-modeler | [To be filled during implementation — which approach works] | [TBD] |

### Classification Tags

| Table/Field | Sensitivity | RLS Policy |
|-------------|------------|------------|
| financial_facts_test.* | Public (test data) | N/A |

---

## 11. Discussion

> Async communication channel between agents (or between Claude and human).
> Format: `[YYYY-MM-DD HH:MM] @agent-name → @target`

---

## 12. Governance Completeness Checklist

- [ ] All new/modified fields have CDE mappings in `governance/cde-catalog.json` (N/A — test data)
- [ ] All transformations logged in OpenLineage format in `governance/lineage/`
- [ ] DQ rules generated for all new/modified fields
- [ ] DQ scorecard produced for all affected tables
- [ ] Data dictionary entries created/updated in `governance/data-dictionary.json`
- [ ] Data contracts updated for affected consumable zone tables (N/A)
- [ ] Agent decision rationale logged to `governance/audit-trail/`
- [ ] Classification/sensitivity tags assigned
- [ ] Grounding documents updated (N/A — not AI-ready zone)
- [ ] Evaluation datasets updated (N/A — not AI-ready zone)

---

## 13. Final Review

### Date: [YYYY-MM-DD]
### Status: 🟢 SHIPPED | 🔄 REVISIONS NEEDED

### Notes
[Final observations — especially: what are the known limitations of DuckDB + Iceberg as tested?]

### Follow-up Items
- [ ] Real EDGAR data ingestion (next spec: `raw-ingest-xbrl-company-facts.md`)
- [ ] Catalog migration path if we need REST catalog later
- [ ] Document version-specific behavior (DuckDB version X, PyIceberg version Y)

### End-to-End Governance Demo Impact
This spec establishes the Iceberg foundation that makes bitemporal history queryable via snapshots — a core component of the governance walkthrough. Without working time travel, the demo can't show amendment history.

---

## Appendix A: Related Specs

| Spec | Relevance |
|------|-----------|
| `raw-ingest-xbrl-company-facts.md` | Next spec — depends on this infra being verified |
| `base-temporal-amendment-handling.md` | Future — builds on snapshot behavior proven here |

## Appendix B: References

- [PyIceberg documentation](https://py.iceberg.apache.org/)
- [DuckDB Iceberg extension](https://duckdb.org/docs/extensions/iceberg.html)
- [Apache Iceberg spec — Snapshots](https://iceberg.apache.org/spec/#snapshots)
- [PyIceberg SqlCatalog](https://py.iceberg.apache.org/configuration/#sql-catalog)
