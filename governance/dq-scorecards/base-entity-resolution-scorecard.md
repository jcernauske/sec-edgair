## DQ Scorecard: base-entity-resolution
**Spec:** base-entity-resolution
**Date:** 2026-03-14
**Agent:** @dq-engineer
**Overall Score:** 5/5 rules passing (100%)
**Data Source:** Production Data Validation (executed 2026-03-14T21:35:20.066375+00:00)
**Run ID:** e5e9f552

### Execution Results

| Rule ID | Category | Priority | Description | Result | Details |
|---------|----------|----------|-------------|--------|---------|
| BASE-ER-001 | Completeness | P0 | Every CIK in raw.xbrl_company_facts has an approved mapping in base.entity_mappings | PASS | actual=0.0, threshold=result = 0.0 |
| BASE-ER-002 | Uniqueness | P0 | No duplicate CIKs in approved mappings | PASS | actual=0, threshold=result_count = 0.0 |
| BASE-ER-003 | Validity | P0 | All confidence scores between 0.0 and 1.0 inclusive | PASS | actual=0.0, threshold=result = 0.0 |
| BASE-ER-004 | Completeness | P0 | Approved mappings have non-null approved_by and approved_at | PASS | actual=0.0, threshold=result = 0.0 |
| BASE-ER-005 | Referential Integrity | P0 | Every audit entry has a valid mapping_id that exists in entity_mappings | PASS | actual=0.0, threshold=result = 0.0 |

### Summary by Category
| Category | Rules | Passing | Rate |
|----------|-------|---------|------|
| Completeness | 2 | 2 | 100% |
| Referential Integrity | 1 | 1 | 100% |
| Uniqueness | 1 | 1 | 100% |
| Validity | 1 | 1 | 100% |

### Gate Status
- **P0 Gate: PASS** — All critical rules passed.

