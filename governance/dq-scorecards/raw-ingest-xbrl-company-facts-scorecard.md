## DQ Scorecard: raw-ingest-xbrl-company-facts
**Spec:** raw-ingest-xbrl-company-facts
**Date:** 2026-03-14
**Agent:** @dq-engineer
**Overall Score:** 8/8 rules passing (100%)
**Data Source:** Production Data Validation (executed 2026-03-14T22:50:53.539354+00:00)
**Run ID:** 6d2ec99b

### Execution Results

| Rule ID | Category | Priority | Description | Result | Details |
|---------|----------|----------|-------------|--------|---------|
| RAW-CF-001 | Completeness | P0 | All 20 expected CIKs are present in the raw table | PASS | actual=0.0, threshold=result = 0.0 |
| RAW-CF-002 | Completeness | P0 | No null values in required fields | PASS | actual=0.0, threshold=result = 0.0 |
| RAW-CF-003 | Validity | P0 | CIK is a positive integer | PASS | actual=0.0, threshold=result = 0.0 |
| RAW-CF-004 | Validity | P0 | Accession numbers match SEC format (NNNNNNNNNN-NN-NNNNNN) | PASS | actual=0.0, threshold=result = 0.0 |
| RAW-CF-005 | Validity | P0 | No facts with filed_date in the future | PASS | actual=0.0, threshold=result = 0.0 |
| RAW-CF-006 | Validity | P1 | All val values are finite (no NaN or Inf) | PASS | actual=0.0, threshold=result = 0.0 |
| RAW-CF-007 | Volume | P1 | Each CIK has at least 100 facts | PASS | actual=0.0, threshold=result = 0.0 |
| RAW-CF-008 | Freshness | P2 | Latest filed_date is within last 2 years | PASS | actual=0.0, threshold=result = 0.0 |

### Summary by Category
| Category | Rules | Passing | Rate |
|----------|-------|---------|------|
| Completeness | 2 | 2 | 100% |
| Freshness | 1 | 1 | 100% |
| Validity | 4 | 4 | 100% |
| Volume | 1 | 1 | 100% |

### Gate Status
- **P0 Gate: PASS** — All critical rules passed.

