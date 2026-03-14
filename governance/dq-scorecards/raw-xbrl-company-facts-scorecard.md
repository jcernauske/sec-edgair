## DQ Scorecard: raw.xbrl_company_facts
**Spec:** raw-ingest-xbrl-company-facts
**Date:** 2026-03-14
**Agent:** @dq-engineer
**Overall Score:** 16/16 rules defined (awaiting live data execution)
**Data Source:** Fixture-based validation (CIK0000320193_sample.json — 9 rows)

### Fixture-Based Validation Results

| Rule ID | Category | Priority | Description | Result | Details |
|---------|----------|----------|-------------|--------|---------|
| RAW-CF-001 | Completeness | P0 | cik IS NOT NULL | ✅ PASS | 100% (9/9) |
| RAW-CF-002 | Completeness | P0 | entity_name IS NOT NULL | ✅ PASS | 100% (9/9) |
| RAW-CF-003 | Completeness | P0 | end_date IS NOT NULL | ✅ PASS | 100% (9/9) |
| RAW-CF-004 | Completeness | P0 | val IS NOT NULL | ✅ PASS | 100% (9/9) |
| RAW-CF-005 | Completeness | P0 | accession_number IS NOT NULL | ✅ PASS | 100% (9/9) |
| RAW-CF-006 | Completeness | P0 | filed_date IS NOT NULL | ✅ PASS | 100% (9/9) |
| RAW-CF-007 | Completeness | P0 | ingested_at IS NOT NULL | ✅ PASS | 100% (9/9) |
| RAW-CF-008 | Completeness | P0 | source_url IS NOT NULL | ✅ PASS | 100% (9/9) |
| RAW-CF-009 | Completeness | P0 | source_method IS NOT NULL | ✅ PASS | 100% (9/9) |
| RAW-CF-010 | Validity | P1 | taxonomy in known set | ✅ PASS | 100% — us-gaap, dei |
| RAW-CF-011 | Validity | P1 | form in known set | ✅ PASS | 100% — 10-K |
| RAW-CF-012 | Validity | P1 | fiscal_period in known set | ✅ PASS | 100% — FY, Q4 |
| RAW-CF-013 | Validity | P0 | source_method in {api, bulk_zip} | ✅ PASS | 100% — api |
| RAW-CF-014 | Range | P1 | filed_date between 1993-01-01 and today+30d | ✅ PASS | 100% — 2023-11-03 |
| RAW-CF-015 | Volume | P2 | Row count per CIK > 1000 | ⚠️ N/A | Fixture has 9 rows (truncated) — rule applies to live data only |
| RAW-CF-016 | Completeness | P0 | All requested CIKs present | ✅ PASS | 100% (1/1 requested CIK present) |

### Summary by Category
| Category | Rules | Passing | Rate |
|----------|-------|---------|------|
| Completeness | 10 | 10 | 100% |
| Validity | 4 | 4 | 100% |
| Range | 1 | 1 | 100% |
| Volume | 1 | N/A | Fixture-limited |

### Notes
- RAW-CF-015 (row count > 1000 per CIK) cannot be validated against fixture data (9 rows). This rule is meaningful only against live SEC EDGAR data.
- All P0 rules pass at 100%. All P1 rules pass at 100%.
- Validation performed against Iceberg roundtrip data (write → read back → assert), not just in-memory — tests confirm DQ rules hold after Iceberg persistence.
