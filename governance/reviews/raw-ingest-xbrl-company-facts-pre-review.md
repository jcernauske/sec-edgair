## Governance Review: raw-ingest-xbrl-company-facts
**Review Type:** Pre-Implementation
**Reviewer:** @governance-reviewer
**Date:** 2026-03-14
**Verdict:** ✅ APPROVED

### Checklist Results

- [x] Spec has a clear problem statement and success criteria — 13 success criteria in §1
- [x] Input data sources are identified with paths — SEC EDGAR API endpoint and bulk ZIP URL specified
- [x] Output artifacts are defined with paths and formats — `raw.xbrl_company_facts` Iceberg table, `data/raw/iceberg_warehouse`
- [x] Transformations are described (what changes, why) — JSON flattening from nested XBRL to 19-column flat table
- [x] Zone assignment is correct — Raw zone, appropriate for as-received data with minimal transformation
- [x] Primary implementation agent is identified — @data-profiler
- [x] DQ rule categories are specified — RAW-CF-001 through RAW-CF-016 with thresholds defined in §10
- [x] CDE mapping impact is assessed — 4 CDEs identified: CIK, accession_number, entity_name, filed_date
- [x] Lineage scope is defined — Two OpenLineage jobs: API ingest and bulk ZIP ingest
- [x] Breaking changes to existing schemas are flagged — N/A, new table
- [x] Testing approach is defined — 4 tiers: unit, integration, live API, live bulk

### Issues Found
| # | Severity | Description | Resolution Required |
|---|----------|-------------|---------------------|
| 1 | 🟡 ADVISORY | `USER_AGENT` in config.py uses placeholder email `research@example.com` — must be updated before live API tests | Update before running @pytest.mark.network tests |
| 2 | 🟡 ADVISORY | Warehouse path `data/raw/iceberg_warehouse` is separate from base zone `data/base/iceberg_warehouse` — this is correct for zone isolation but should be documented | Already documented in §2 Design Decisions |
| 3 | 🟡 ADVISORY | `httpx` dependency not yet in pyproject.toml — must be added during implementation | @data-profiler will add during Step 2 |

### Decision Rationale
Spec is comprehensive and implementation-ready. All 13 sections are present. §1-§4 contain sufficient detail for implementation. §10 governance artifacts (lineage, CDE, DQ rules, data dictionary, audit trail) are fully specified with real content. The flat-table design decision is appropriate for the raw zone. The testing strategy with fixture-based offline tests is sound.

No blocking issues. Three advisory items logged — all are addressable during implementation. Proceeding to implementation.
