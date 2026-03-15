## DQ Scorecard: consumable-peer-comparison
**Spec:** consumable-peer-comparison
**Date:** 2026-03-15
**Agent:** @dq-engineer
**Overall Score:** 10/10 rules passing (100%)
**Data Source:** Production Data Validation (executed 2026-03-15T05:32:35.605087+00:00)
**Run ID:** 55a4b9b7

### Execution Results

| Rule ID | Category | Priority | Description | Result | Details |
|---------|----------|----------|-------------|--------|---------|
| CONS-PC-001 | Uniqueness | P0 | record_id is unique (no duplicate grain) | PASS | actual=0, threshold=result_count = 0.0 |
| CONS-PC-002 | Validity | P0 | Every row has valid metric_source (company_financials or financial_ratios) | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-PC-003 | Referential Integrity | P0 | Every row has valid cik (exists in source tables) | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-PC-004 | Completeness | P0 | No null metric_value, sector_rank, sector_avg, sector_median, sector_percentile | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-PC-005 | Consistency | P0 | sector_rank is between 1 and peer_count (inclusive) | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-PC-006 | Consistency | P0 | sector_percentile is between 0.0 and 1.0 (inclusive) | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-PC-007 | Consistency | P0 | peer_count >= 2 for every row (minimum peer threshold) | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-PC-008 | Consistency | P0 | sector_rank 1 has sector_percentile 1.0 | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-PC-009 | Consistency | P0 | No single-company sectors (Energy, Industrials, Communication Services excluded) | PASS | actual=0.0, threshold=result = 0.0 |
| CONS-PC-010 | Consistency | P0 | peer_count matches actual distinct CIKs per (sector, metric_id, fiscal_year, fiscal_period, metric_source) | PASS | actual=0, threshold=result_count = 0.0 |

### Summary by Category
| Category | Rules | Passing | Rate |
|----------|-------|---------|------|
| Completeness | 1 | 1 | 100% |
| Consistency | 6 | 6 | 100% |
| Referential Integrity | 1 | 1 | 100% |
| Uniqueness | 1 | 1 | 100% |
| Validity | 1 | 1 | 100% |

### Gate Status
- **P0 Gate: PASS** — All critical rules passed.

