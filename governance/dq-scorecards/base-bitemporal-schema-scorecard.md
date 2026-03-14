## DQ Scorecard: Bitemporal Schema — Temporal Validation
**Spec:** base-bitemporal-schema
**Date:** 2026-03-14
**Agent:** @dq-engineer
**Overall Score:** 5/5 rules defined (validated via test suite)
**Data Source:** Test-based validation (temporal queries, snapshot registry, DQ rules)

### Test-Based Validation Results

| Rule ID | Category | Priority | Description | Result | Details |
|---------|----------|----------|-------------|--------|---------|
| BASE-BT-001 | Validity | P0 | No future filed_dates | PASS | test_pass_all_past, test_fail_future_date verify both scenarios |
| BASE-BT-002 | Validity | P0 | start_date < end_date | PASS | test_pass_valid_range, test_fail_start_equals_end verify boundary |
| BASE-BT-003 | Consistency | P0 | Supersession filing order | PASS | test_pass_correct_order, test_fail_wrong_order verify temporal ordering |
| BASE-BT-004 | Validity | P1 | filed_date >= end_date (99%) | PASS | test_pass_filed_after_end, test_fail_filed_before_end verify threshold |
| BASE-BT-005 | Referential Integrity | P0 | superseded_by exists | PASS | test_pass_reference_exists, test_fail_reference_missing verify lookups |

### Summary by Category
| Category | Rules | Passing | Rate |
|----------|-------|---------|------|
| Validity | 3 | 3 | 100% |
| Consistency | 1 | 1 | 100% |
| Referential Integrity | 1 | 1 | 100% |

### Query Helpers Validation

| Behavior | Test | Result |
|----------|------|--------|
| current_facts excludes superseded | test_excludes_superseded | PASS |
| current_facts filter by cik | test_filter_by_cik | PASS |
| current_facts filter by concept | test_filter_by_concept | PASS |
| current_facts filter by cde_id | test_filter_by_cde_id | PASS |
| current_facts returns all non-superseded | test_no_filters_returns_all_current | PASS |
| as_known_on before amendment | test_before_amendment | PASS |
| as_known_on after amendment | test_after_amendment | PASS |
| as_known_on accepts string dates | test_string_date_accepted | PASS |
| fact_history returns sorted versions | test_returns_all_versions_sorted | PASS |
| fact_history filters by grain | test_filters_by_grain | PASS |
| compare_periods basic comparison | test_basic_comparison | PASS |
| compare_periods missing returns None | test_missing_period_returns_none | PASS |

### Snapshot Registry Validation

| Behavior | Test | Result |
|----------|------|--------|
| Labeled snapshots with sequence | test_labels_and_sequence | PASS |
| find_snapshot_at correct snapshot | test_finds_correct_snapshot | PASS |
| find_snapshot_at returns None before first | test_returns_none_before_first | PASS |
| snapshot_diff_summary shows additions | test_diff_shows_added_facts | PASS |
| read_at_snapshot returns correct data | test_reads_specific_snapshot | PASS |

### CLI Validation

| Behavior | Test | Result |
|----------|------|--------|
| validate command runs all 5 rules | test_validate_runs_all_rules | PASS |
| snapshots command lists snapshots | test_snapshots_command | PASS |

### Notes
- All 5 DQ rules pass at 100% in test-based validation
- 29 total tests covering queries, validation, snapshots, and CLI
- All 175 tests in full suite pass (29 new + 146 existing)
- No new Iceberg tables created — this is a pure query/validation layer
