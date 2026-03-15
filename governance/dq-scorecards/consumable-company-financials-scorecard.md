## DQ Scorecard: consumable-company-financials
**Spec:** consumable-company-financials
**Date:** 2026-03-15
**Agent:** @dq-engineer
**Overall Score:** 8/8 rules passing (100%)
**Data Source:** Production Data Validation (executed 2026-03-15T03:43:33.708783+00:00)
**Run ID:** f3e7c245

### Execution Results

| Rule ID | Category | Priority | Description | Result | Details |
|---------|----------|----------|-------------|--------|---------|
| CONS-CF-001 | Uniqueness | P0 | record_id is unique (no duplicate grain) | PASS | actual=0, threshold=result_count = 0.0 |
| CONS-CF-002 | Referential Integrity | P0 | Every row has valid business_term_id (exists in concept_mappings) | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-CF-003 | Referential Integrity | P0 | Every row has valid cik (exists in entity_mappings) | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-CF-004 | Completeness | P0 | No null val (every row has a financial value) | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-CF-005 | Consistency | P0 | Unit matches expected unit for business term category | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-CF-006 | Consistency | P0 | companies_reporting is accurate (matches actual count) | PASS | actual=0, threshold=result_count = 0.0 |
| CONS-CF-007 | Completeness | P0 | All 25 financial business terms represented in the table | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-CF-008 | Completeness | P0 | All 20 companies represented in the table | PASS | actual=0.0, threshold=result = 0.0 |

### Summary by Category
| Category | Rules | Passing | Rate |
|----------|-------|---------|------|
| Completeness | 3 | 3 | 100% |
| Consistency | 2 | 2 | 100% |
| Referential Integrity | 2 | 2 | 100% |
| Uniqueness | 1 | 1 | 100% |

### Gate Status
- **P0 Gate: PASS** — All critical rules passed.
