## DQ Scorecard: base-bitemporal-schema
**Spec:** base-bitemporal-schema
**Date:** 2026-03-14
**Agent:** @dq-engineer
**Overall Score:** 5/5 rules passing (100%)
**Data Source:** Production Data Validation (executed 2026-03-14T22:21:17.644410+00:00)
**Run ID:** 2457f85d

### Execution Results

| Rule ID | Category | Priority | Description | Result | Details |
|---------|----------|----------|-------------|--------|---------|
| BASE-BT-001 | Validity | P0 | No facts with filed_date in the future | PASS | actual=0.0, threshold=result = 0.0 |
| BASE-BT-002 | Validity | P0 | start_date < end_date for all period facts | PASS | actual=0.0, threshold=result = 0.0 |
| BASE-BT-003 | Consistency | P0 | Superseded facts have filed_date <= superseding fact's filed_date | PASS | actual=0.0, threshold=result = 0.0 |
| BASE-BT-004 | Validity | P1 | filed_date >= end_date (filings come after period ends) | PASS | actual=100.0, threshold=result >= 99.0 |
| BASE-BT-005 | Referential Integrity | P0 | Every superseded_by accession number exists in facts | PASS | actual=0.0, threshold=result = 0.0 |

### Summary by Category
| Category | Rules | Passing | Rate |
|----------|-------|---------|------|
| Consistency | 1 | 1 | 100% |
| Referential Integrity | 1 | 1 | 100% |
| Validity | 3 | 3 | 100% |

### Gate Status
- **P0 Gate: PASS** — All critical rules passed.

