## DQ Scorecard: consumable-company-financials
**Spec:** consumable-company-financials
**Date:** 2026-03-15
**Agent:** @dq-engineer
**Overall Score:** 12/12 rules passing (100%)
**Data Source:** Production Data Validation (executed 2026-03-15T17:59:46.534373+00:00)
**Run ID:** d983d6ea

### Execution Results

| Rule ID | Category | Priority | Description | Result | Details |
|---------|----------|----------|-------------|--------|---------|
| CONS-CF-001 | Uniqueness | P0 | record_id is unique (no duplicate grain) | PASS | actual=0, threshold=result_count = 0.0 |
| CONS-CF-002 | Referential Integrity | P0 | Every row has valid business_term_id (exists in concept_mappings) | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-CF-003 | Referential Integrity | P0 | Every row has valid cik (exists in entity_mappings) | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-CF-004 | Completeness | P0 | No null val (every row has a financial value) | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-CF-005 | Consistency | P0 | Unit matches expected unit for business term category (USD for dollar amounts, USD/shares for per-share) | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-CF-006 | Consistency | P0 | companies_reporting is accurate (matches actual distinct company count per business_term_id and fiscal_period) | PASS | actual=0, threshold=result_count = 0.0 |
| CONS-CF-007 | Completeness | P0 | All 25 financial business terms represented in the table | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-CF-008 | Completeness | P0 | All 20 companies represented in the table | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-CF-009 | Reasonableness | P2 | Net Income magnitude should not exceed Revenue magnitude for non-financial companies | PASS | actual=12.0, threshold=result <= 12.0 |
| CONS-CF-010 | Reasonableness | P2 | Common metrics (Revenue, Net Income, Total Assets) should have >= 2 companies reporting per period type | PASS | actual=0, threshold=result_count = 0.0 |
| CONS-CF-011 | Accuracy | P0 | Row count matches base.conformed_facts (1:1 presentation layer) | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-CF-012 | Accuracy | P0 | No fiscal year collisions (same company + metric + period + period_end_date in two fiscal years) | PASS | actual=0.0, threshold=result = 0.0 |

### Summary by Category
| Category | Rules | Passing | Rate |
|----------|-------|---------|------|
| Accuracy | 2 | 2 | 100% |
| Completeness | 3 | 3 | 100% |
| Consistency | 2 | 2 | 100% |
| Reasonableness | 2 | 2 | 100% |
| Referential Integrity | 2 | 2 | 100% |
| Uniqueness | 1 | 1 | 100% |

### Gate Status
- **P0 Gate: PASS** — All critical rules passed.

