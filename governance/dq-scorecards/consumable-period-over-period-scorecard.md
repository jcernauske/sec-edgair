## DQ Scorecard: consumable-period-over-period
**Spec:** consumable-period-over-period
**Date:** 2026-03-15
**Agent:** @dq-engineer
**Overall Score:** 12/12 rules passing (100%)
**Data Source:** Production Data Validation (executed 2026-03-15T04:58:33.340974+00:00)
**Run ID:** a981f059

### Execution Results

| Rule ID | Category | Priority | Description | Result | Details |
|---------|----------|----------|-------------|--------|---------|
| CONS-PP-001 | Uniqueness | P0 | record_id is unique (no duplicate grain) | PASS | actual=0, threshold=result_count = 0.0 |
| CONS-PP-002 | Validity | P0 | Every row has valid growth_type (yoy_change, yoy_pct_change, cagr_5yr) | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-PP-003 | Referential Integrity | P0 | Every row has valid cik (exists in consumable.company_financials) | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-PP-004 | Completeness | P0 | No null growth_value (every row has a computed value) | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-PP-005 | Consistency | P0 | YoY rows have non-null prior_val | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-PP-006 | Consistency | P0 | CAGR rows have non-null base_val and base_fiscal_year | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-PP-007 | Consistency | P0 | CAGR base_fiscal_year = fiscal_year - 5 | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-PP-008 | Consistency | P0 | YoY pct change: prior_val is never 0 (division by zero guard) | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-PP-009 | Consistency | P0 | CAGR: base_val is always > 0 | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-PP-010 | Completeness | P0 | All 3 growth types represented in the table | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-PP-011 | Completeness | P0 | All 25 business terms represented in YoY rows | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-PP-012 | Consistency | P0 | companies_reporting is accurate (matches actual distinct company count per growth_type per business_term_id per fiscal_period) | PASS | actual=0, threshold=result_count = 0.0 |

### Summary by Category
| Category | Rules | Passing | Rate |
|----------|-------|---------|------|
| Completeness | 3 | 3 | 100% |
| Consistency | 6 | 6 | 100% |
| Referential Integrity | 1 | 1 | 100% |
| Uniqueness | 1 | 1 | 100% |
| Validity | 1 | 1 | 100% |

### Gate Status
- **P0 Gate: PASS** — All critical rules passed.

