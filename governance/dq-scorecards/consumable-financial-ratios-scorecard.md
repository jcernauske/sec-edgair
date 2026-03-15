## DQ Scorecard: consumable-financial-ratios
**Spec:** consumable-financial-ratios
**Date:** 2026-03-15
**Agent:** @dq-engineer
**Overall Score:** 15/15 rules passing (100%)
**Data Source:** Production Data Validation (executed 2026-03-15T17:59:47.226382+00:00)
**Run ID:** 4a709237

### Execution Results

| Rule ID | Category | Priority | Description | Result | Details |
|---------|----------|----------|-------------|--------|---------|
| CONS-FR-001 | Uniqueness | P0 | record_id is unique (no duplicate grain) | PASS | actual=0, threshold=result_count = 0.0 |
| CONS-FR-002 | Validity | P0 | Every row has valid ratio_id (RATIO-001 through RATIO-007) | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-FR-003 | Referential Integrity | P0 | Every row has valid cik (exists in consumable.company_financials) | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-FR-004 | Completeness | P0 | No null ratio_value (every row has a computed value) | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-FR-005 | Consistency | P0 | denominator_val is never 0 (division by zero guard) | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-FR-006 | Consistency | P0 | Numerator and denominator business term IDs match the ratio definition | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-FR-007 | Consistency | P0 | companies_reporting is accurate (matches actual distinct company count per ratio per period type) | PASS | actual=0, threshold=result_count = 0.0 |
| CONS-FR-008 | Completeness | P0 | All 7 ratios represented in the table | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-FR-009 | Consistency | P0 | CapEx-to-Revenue (RATIO-007) ratio_value is always >= 0 (abs applied) | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-FR-010 | Consistency | P0 | Margin ratios (RATIO-001, 002, 003, 005, 006, 007) use Revenue (BT-022) as denominator | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-FR-011 | Reasonableness | P1 | Gross Margin (RATIO-001) between -1.0 and 1.0 | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-FR-012 | Reasonableness | P2 | Operating Margin (RATIO-002) between -100.0 and 100.0 | PASS | actual=2.0, threshold=result <= 2.0 |
| CONS-FR-013 | Reasonableness | P2 | Net Margin (RATIO-003) between -100.0 and 100.0 | PASS | actual=1.0, threshold=result <= 1.0 |
| CONS-FR-014 | Reasonableness | P2 | CapEx-to-Revenue (RATIO-007) between 0.0 and 100.0 | PASS | actual=2.0, threshold=result <= 2.0 |
| CONS-FR-015 | Reasonableness | P2 | R&D Intensity (RATIO-005) between -100.0 and 100.0 | PASS | actual=1.0, threshold=result <= 1.0 |

### Summary by Category
| Category | Rules | Passing | Rate |
|----------|-------|---------|------|
| Completeness | 2 | 2 | 100% |
| Consistency | 5 | 5 | 100% |
| Reasonableness | 5 | 5 | 100% |
| Referential Integrity | 1 | 1 | 100% |
| Uniqueness | 1 | 1 | 100% |
| Validity | 1 | 1 | 100% |

### Gate Status
- **P0 Gate: PASS** — All critical rules passed.

