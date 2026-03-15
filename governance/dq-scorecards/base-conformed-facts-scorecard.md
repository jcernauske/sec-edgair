## DQ Scorecard: base-conformed-facts
**Spec:** base-conformed-facts
**Date:** 2026-03-15
**Agent:** @dq-engineer
**Overall Score:** 27/27 rules passing (100%)
**Data Source:** Production Data Validation (executed 2026-03-15T17:59:42.631976+00:00)
**Run ID:** 36578b2f

### Execution Results

| Rule ID | Category | Priority | Description | Result | Details |
|---------|----------|----------|-------------|--------|---------|
| BASE-CF-001 | Uniqueness | P0 | One row per grain (cik, business_term_id, fiscal_year, fiscal_period) — no duplicates | PASS | actual=0, threshold=result_count = 0.0 |
| BASE-CF-002 | Uniqueness | P0 | conformed_id is unique across all rows | PASS | actual=0, threshold=result_count = 0.0 |
| BASE-CF-003 | Referential Integrity | P0 | Every source_fact_id exists in base.financial_facts | PASS | actual=0.0, threshold=result = 0.0 |
| BASE-CF-004 | Completeness | P0 | All 20 in-scope companies are represented | PASS | actual=20.0, threshold=result = 20.0 |
| BASE-CF-005 | Completeness | P0 | All 25 business terms are represented | PASS | actual=25.0, threshold=result = 25.0 |
| BASE-CF-006 | Completeness | P0 | No NULL values in required columns | PASS | actual=0.0, threshold=result = 0.0 |
| BASE-CF-007 | Consistency | P1 | val in conformed_facts matches val in financial_facts for the referenced source_fact_id | PASS | actual=0.0, threshold=result = 0.0 |
| BASE-CF-008 | Consistency | P0 | competing_fact_count is >= 1 for all rows | PASS | actual=0.0, threshold=result = 0.0 |
| BASE-CF-009 | Consistency | P0 | selection_reason is one of the three valid enum values | PASS | actual=0.0, threshold=result = 0.0 |
| BASE-CF-010 | Consistency | P0 | sole_candidate selection_reason only when competing_fact_count = 1, and vice versa | PASS | actual=0.0, threshold=result = 0.0 |
| BASE-CF-011 | Consistency | P1 | Per-share business terms (BT-044, BT-045, BT-046) have unit = 'USD/shares'; all others have unit = 'USD' | PASS | actual=0.0, threshold=result = 0.0 |
| BASE-CF-012 | Volume | P0 | Row count within expected range (25,000 to 35,000) | PASS | actual=0.0, threshold=result = 0.0 |
| BASE-CF-013 | Completeness | P2 | Every company has at least 15 business terms | PASS | actual=0, threshold=result_count = 0.0 |
| BASE-CF-014 | Validity | P0 | fiscal_period is a valid value (FY, Q1, Q2, Q3) | PASS | actual=0.0, threshold=result = 0.0 |
| BASE-CF-015 | Validity | P0 | calendar_quarter is between 1 and 4 | PASS | actual=0.0, threshold=result = 0.0 |
| BASE-CF-016 | Validity | P1 | Fiscal year range is within expected bounds (min <= 2010, max >= current_year - 1) | PASS | actual=0.0, threshold=result = 0.0 |
| BASE-CF-017 | Freshness | P1 | promoted_at is within the last 7 days (pipeline recency check) | PASS | actual=0.0, threshold=result = 0.0 |
| BASE-CF-018 | Consistency | P1 | selection_reason distribution is within expected ranges | PASS | actual=0.0, threshold=result = 0.0 |
| BASE-CF-019 | Completeness | P0 | No superseded facts leak into conformed_facts | PASS | actual=0.0, threshold=result = 0.0 |
| BASE-CF-020 | Reasonableness | P1 | Revenue (BT-022) should be positive for non-financial companies | PASS | actual=2.0, threshold=result <= 2.0 |
| BASE-CF-021 | Reasonableness | P0 | Total Assets (BT-024) must be positive | PASS | actual=0.0, threshold=result = 0.0 |
| BASE-CF-022 | Reasonableness | P1 | Per-share metrics (BT-044, BT-045, BT-046) magnitude < 10,000 | PASS | actual=0.0, threshold=result = 0.0 |
| BASE-CF-023 | Reasonableness | P1 | USD metrics magnitude should be < 10 trillion | PASS | actual=0.0, threshold=result = 0.0 |
| BASE-CF-024 | Reasonableness | P1 | Each company's metrics for a given period should come from <= 4 distinct accession numbers | PASS | actual=0, threshold=result_count = 0.0 |
| BASE-CF-025 | Accuracy | P0 | No superseded facts in conformed_facts (source fact must not be superseded) | PASS | actual=0.0, threshold=result = 0.0 |
| BASE-CF-026 | Accuracy | P0 | No null business_term_id values in conformed_facts | PASS | actual=0.0, threshold=result = 0.0 |
| BASE-CF-027 | Accuracy | P0 | No facts with wrong unit per business term (USD for dollar metrics, USD/shares for per-share) | PASS | actual=0.0, threshold=result = 0.0 |

### Summary by Category
| Category | Rules | Passing | Rate |
|----------|-------|---------|------|
| Accuracy | 3 | 3 | 100% |
| Completeness | 5 | 5 | 100% |
| Consistency | 6 | 6 | 100% |
| Freshness | 1 | 1 | 100% |
| Reasonableness | 5 | 5 | 100% |
| Referential Integrity | 1 | 1 | 100% |
| Uniqueness | 2 | 2 | 100% |
| Validity | 3 | 3 | 100% |
| Volume | 1 | 1 | 100% |

### Gate Status
- **P0 Gate: PASS** — All critical rules passed.

