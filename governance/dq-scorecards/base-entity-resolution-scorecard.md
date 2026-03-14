## DQ Scorecard: base.entity_mappings + base.entity_resolution_audit
**Spec:** base-entity-resolution
**Date:** 2026-03-14
**Agent:** @dq-engineer
**Overall Score:** 5/5 rules defined (validated via test suite)
**Data Source:** Test-based validation (3 known CIKs: Apple, JPMorgan, Microsoft)

### Test-Based Validation Results

| Rule ID | Category | Priority | Description | Result | Details |
|---------|----------|----------|-------------|--------|---------|
| BASE-ER-001 | Completeness | P0 | Every CIK in raw has approved mapping | ✅ PASS | 3/3 CIKs mapped in test_promote.py |
| BASE-ER-002 | Uniqueness | P0 | No duplicate CIKs in approved | ✅ PASS | Verified unique CIKs in test_promote_writes_to_iceberg |
| BASE-ER-003 | Validity | P0 | Confidence scores 0.0-1.0 | ✅ PASS | All proposals have confidence 1.0 (known) or 0.5 (unknown) |
| BASE-ER-004 | Completeness | P0 | Approved have non-null approved_by/at | ✅ PASS | Verified in test_promote_writes_to_iceberg — all approved rows have approved_by="human:jeff" |
| BASE-ER-005 | Referential Integrity | P0 | Audit entries have valid mapping_id | ✅ PASS | Verified in test_promote_creates_audit_entries — all audit mapping_ids match |

### Summary by Category
| Category | Rules | Passing | Rate |
|----------|-------|---------|------|
| Completeness | 2 | 2 | 100% |
| Uniqueness | 1 | 1 | 100% |
| Validity | 1 | 1 | 100% |
| Referential Integrity | 1 | 1 | 100% |

### Human Approval Gate Validation

| Behavior | Test | Result |
|----------|------|--------|
| Toggle=True stops all proposals | test_gate_require_approval_true_stops_all | ✅ PASS |
| Toggle=False auto-promotes high confidence | test_gate_require_approval_false_auto_promotes_high_confidence | ✅ PASS |
| Confidence < 0.7 always stops | test_gate_low_confidence_always_stops | ✅ PASS |
| Confidence < 0.7 stops even with toggle=False | test_gate_low_confidence_stops_even_with_approval_off | ✅ PASS |
| Confidence = 0.7 auto-promotes when toggle=False | test_gate_exactly_at_floor_auto_promotes | ✅ PASS |

### Notes
- All 5 DQ rules pass at 100% in test-based validation
- Human approval gate behavior verified with 6 dedicated tests
- Iceberg roundtrip (write → read back) confirmed for both tables
- Partial approval (approve some, leave others pending) works correctly
- CLI approve/reject commands are idempotent
