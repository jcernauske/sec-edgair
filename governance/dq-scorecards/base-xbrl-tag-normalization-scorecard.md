## DQ Scorecard: base-xbrl-tag-normalization
**Spec:** base-xbrl-tag-normalization
**Date:** 2026-03-14
**Agent:** @dq-engineer
**Overall Score:** 5/5 rules passing (100%)
**Data Source:** Production Data Validation (executed 2026-03-14T21:22:27.286392+00:00)
**Run ID:** f0502cde

### Execution Results

| Rule ID | Category | Priority | Description | Result | Details |
|---------|----------|----------|-------------|--------|---------|
| BASE-TN-001 | Completeness | P0 | Every Tier 1 concept has an approved mapping with valid business term | PASS | actual=0.0, threshold=result = 0.0 |
| BASE-TN-002 | Uniqueness | P0 | No concept maps to multiple business terms | PASS | actual=0, threshold=result_count = 0.0 |
| BASE-TN-003 | Validity | P0 | All confidence scores between 0.0 and 1.0 inclusive | PASS | actual=0.0, threshold=result = 0.0 |
| BASE-TN-004 | Coverage | P1 | Mapped concepts (Tier 1+2) cover >= 25% of raw fact instances | PASS | actual=30.0, threshold=result >= 25.0 |
| BASE-TN-005 | Referential Integrity | P0 | Approved mappings have valid business_term_id referencing business glossary | PASS | actual=0.0, threshold=result = 0.0 |

### Summary by Category
| Category | Rules | Passing | Rate |
|----------|-------|---------|------|
| Completeness | 1 | 1 | 100% |
| Coverage | 1 | 1 | 100% |
| Referential Integrity | 1 | 1 | 100% |
| Uniqueness | 1 | 1 | 100% |
| Validity | 1 | 1 | 100% |

### Gate Status
- **P0 Gate: PASS** — All critical rules passed.

