## DQ Scorecard: base.financial_facts + base.fiscal_calendar + base.amendment_tracking
**Spec:** base-financial-facts-model
**Date:** 2026-03-14
**Agent:** @dq-engineer
**Overall Score:** 7/7 rules defined (validated via test suite)
**Data Source:** Test-based validation (join logic, supersession, fiscal calendar, Iceberg roundtrip)

### Test-Based Validation Results

| Rule ID | Category | Priority | Description | Result | Details |
|---------|----------|----------|-------------|--------|---------|
| BASE-FM-001 | Referential Integrity | P0 | Every fact has valid entity_id | PASS | test_join_enriches_entity_fields verifies entity_id populated; test_join_skips_unknown_entities confirms orphans excluded |
| BASE-FM-002 | Uniqueness | P0 | fact_id is unique | PASS | test_fact_id_deterministic + test_fact_id_differs_for_different_accession verify hash correctness |
| BASE-FM-003 | Consistency | P0 | is_superseded=True has superseded_by | PASS | test_supersession_amendment_supersedes_original, test_supersession_chain_three_filings verify pairing |
| BASE-FM-004 | Completeness | P1 | Fiscal calendar covers all periods in facts | PASS | test_build_calendar_quarterly_periods produces entries for all observed periods |
| BASE-FM-005 | Validity | P0 | calendar_quarter is 1-4 | PASS | test_calendar_quarter_q1/q2/q3/q4 verify all four quarters |
| BASE-FM-006 | Referential Integrity | P0 | Amendment tracking references valid accessions | PASS | test_amendment_detected verifies original_accession and amendment_accession match input facts |
| BASE-FM-007 | Completeness | P0 | No orphan facts | PASS | test_join_skips_unknown_entities confirms model excludes facts without entity_mappings |

### Summary by Category
| Category | Rules | Passing | Rate |
|----------|-------|---------|------|
| Referential Integrity | 2 | 2 | 100% |
| Uniqueness | 1 | 1 | 100% |
| Consistency | 1 | 1 | 100% |
| Completeness | 2 | 2 | 100% |
| Validity | 1 | 1 | 100% |

### Join Logic Validation

| Behavior | Test | Result |
|----------|------|--------|
| Entity fields enriched (entity_id, canonical_name, ticker) | test_join_enriches_entity_fields | PASS |
| Concept fields enriched (cde_id, canonical_cde, tier) | test_join_enriches_concept_fields | PASS |
| Unmapped concepts get tier=3 defaults | test_join_unmapped_concept | PASS |
| Unknown CIKs excluded from output | test_join_skips_unknown_entities | PASS |
| Calendar year/quarter from end_date | test_calendar_year_and_quarter | PASS |
| is_amendment from form type | test_amendment_flag_in_facts | PASS |

### Supersession Validation

| Behavior | Test | Result |
|----------|------|--------|
| Single filing → not superseded | test_supersession_single_filing | PASS |
| Later filing supersedes earlier | test_supersession_amendment_supersedes_original | PASS |
| Chain of 3 → only latest is current | test_supersession_chain_three_filings | PASS |
| Different concepts are independent | test_supersession_different_concepts_independent | PASS |

### Fiscal Calendar Validation

| Behavior | Test | Result |
|----------|------|--------|
| Basic period extraction | test_build_calendar_basic | PASS |
| January fiscal year end (Walmart) | test_build_calendar_january_fiscal_year_end | PASS |
| June fiscal year end (Microsoft) | test_build_calendar_june_fiscal_year_end | PASS |
| All quarters + FY | test_build_calendar_quarterly_periods | PASS |
| Instant facts (no start_date) | test_build_calendar_instant_facts_no_start_date | PASS |

### Amendment Tracking Validation

| Behavior | Test | Result |
|----------|------|--------|
| No amendments for single filing | test_no_amendments_single_filing | PASS |
| Amendment detected with val_change | test_amendment_detected | PASS |
| Zero original → null pct | test_amendment_val_change_pct_zero_original | PASS |
| Chain produces multiple entries | test_amendment_chain_three_filings | PASS |

### Iceberg Roundtrip Validation

| Behavior | Test | Result |
|----------|------|--------|
| Financial facts roundtrip | test_promote_financial_facts | PASS |
| Fiscal calendar roundtrip | test_promote_fiscal_calendar | PASS |
| Amendment tracking roundtrip | test_promote_amendment_tracking | PASS |
| Empty list is noop | test_promote_empty_list_is_noop | PASS |
| Multiple facts written | test_promote_multiple_facts | PASS |

### Notes
- All 7 DQ rules pass at 100% in test-based validation
- 40 total tests covering join logic, supersession, fiscal calendar, amendments, promotion, and CLI
- All 146 tests in full suite pass (40 new + 106 existing)
- No staging/approval gate needed — join is deterministic from approved upstream tables
