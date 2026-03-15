## DQ Scorecard: consumable-amendment-analysis
**Spec:** consumable-amendment-analysis
**Date:** 2026-03-15
**Agent:** @dq-engineer
**Overall Score:** 10/10 rules passing (100%)
**Data Source:** Production Data Validation (executed 2026-03-15T05:32:14.860458+00:00)
**Run ID:** a5b15fc8

### Execution Results

| Rule ID | Category | Priority | Description | Result | Details |
|---------|----------|----------|-------------|--------|---------|
| CONS-AA-001 | Uniqueness | P0 | record_id is unique (no duplicate grain) | PASS | actual=0, threshold=result_count = 0.0 |
| CONS-AA-002 | Referential Integrity | P0 | Every row has valid cik (exists in consumable.company_financials) | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-AA-003 | Completeness | P0 | No null amendment_count (every row has a count) | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-AA-004 | Validity | P0 | amendment_count > 0 (no zero-amendment rows) | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-AA-005 | Validity | P0 | mean_abs_change >= 0 (magnitude is non-negative) | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-AA-006 | Validity | P0 | median_abs_change >= 0 (magnitude is non-negative) | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-AA-007 | Consistency | P0 | max_abs_change >= median_abs_change (max is at least as large) | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-AA-008 | Consistency | P0 | distinct_concepts <= amendment_count (can't have more distinct concepts than amendments) | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-AA-009 | Completeness | P0 | All 20 companies represented in the table | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-AA-010 | Consistency | P0 | total_val_impact >= max_abs_change (total is at least as large as max) | PASS | actual=0.0, threshold=result = 0.0 |

### Summary by Category
| Category | Rules | Passing | Rate |
|----------|-------|---------|------|
| Completeness | 2 | 2 | 100% |
| Consistency | 3 | 3 | 100% |
| Referential Integrity | 1 | 1 | 100% |
| Uniqueness | 1 | 1 | 100% |
| Validity | 3 | 3 | 100% |

### Gate Status
- **P0 Gate: PASS** — All critical rules passed.

