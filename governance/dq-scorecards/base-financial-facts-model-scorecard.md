## DQ Scorecard: base-financial-facts-model
**Spec:** base-financial-facts-model
**Date:** 2026-03-14
**Agent:** @dq-engineer
**Overall Score:** 7/7 rules passing (100%)
**Data Source:** Production Data Validation (executed 2026-03-14T21:22:27.286392+00:00)
**Run ID:** f0502cde

### Execution Results

| Rule ID | Category | Priority | Description | Result | Details |
|---------|----------|----------|-------------|--------|---------|
| BASE-FM-001 | Referential Integrity | P0 | Every fact has a valid entity_id (joins to entity_mappings) | PASS | actual=0.0, threshold=result = 0.0 |
| BASE-FM-002 | Uniqueness | P0 | fact_id is unique (no duplicate grain) | PASS | actual=0, threshold=result_count = 0.0 |
| BASE-FM-003 | Consistency | P0 | is_superseded=True facts have non-null superseded_by | PASS | actual=0.0, threshold=result = 0.0 |
| BASE-FM-004 | Completeness | P1 | Fiscal calendar covers all (entity, fiscal_year, fiscal_period) combinations in facts | PASS | actual=0.0, threshold=result = 0.0 |
| BASE-FM-005 | Validity | P0 | calendar_quarter is 1-4 | PASS | actual=0.0, threshold=result = 0.0 |
| BASE-FM-006 | Referential Integrity | P0 | Amendment tracking entries reference valid accession_numbers | PASS | actual=0.0, threshold=result = 0.0 |
| BASE-FM-007 | Completeness | P0 | No orphan facts (every cik has entity_mapping) | PASS | actual=0.0, threshold=result = 0.0 |

### Summary by Category
| Category | Rules | Passing | Rate |
|----------|-------|---------|------|
| Completeness | 2 | 2 | 100% |
| Consistency | 1 | 1 | 100% |
| Referential Integrity | 2 | 2 | 100% |
| Uniqueness | 1 | 1 | 100% |
| Validity | 1 | 1 | 100% |

### Gate Status
- **P0 Gate: PASS** — All critical rules passed.

