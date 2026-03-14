## EDA Report: Base Zone Tables
**Source:** base.entity_mappings, base.concept_mappings, base.financial_facts, base.fiscal_calendar, base.amendment_tracking
**Date:** 2026-03-14
**Agent:** @data-analyst
**Tables:** 5 | **Total Records:** 791,124

### Key Findings

- **70.1% of financial_facts have NULL cde_id/canonical_cde** — expected. Tier 3 unmapped concepts (89.6% of concept_mappings) don't have CDEs. Only Tier 1+2 (10.4%) get CDE assignments.
- **48.3% of financial_facts are superseded** — almost half. Every original filing that gets amended produces a superseded row. This is the expected supersession ratio for 20 large-cap companies.
- **39.1% of financial_facts have NULL start_date** — inherited from raw (instant-type facts). By design.
- **fiscal_calendar has 1 NULL period_start** — one fiscal period where no start_date was observed. Edge case.
- **amendment_tracking has 1.9% NULL val_change_pct** — 4,661 rows where original_val = 0 (can't compute percentage change from zero). Mathematical impossibility, not a bug.
- **All entity_mappings have identical confidence (1.0)** — all 20 companies were exact CIK matches. Low diversity, but correct.
- **Zero duplicate CIKs, zero duplicate fact_ids** — dedup guards working.

### Table: base.entity_mappings (20 rows)

| Observation | Value | DQ Implication |
|-------------|-------|----------------|
| All status = 'approved' | 20/20 | Correct — all human-approved |
| All confidence = 1.0 | 20/20 | Expected — all exact CIK matches |
| All resolution_method = 'exact_cik_match' | 20/20 | Homogeneous — will diversify with fuzzy matching |
| 4 distinct fiscal_year_end values | 0630, 0930, 1231, 1031 | Companies have different fiscal years |
| Zero duplicate CIKs | 0 | Dedup guard working |

### Table: base.concept_mappings (3,285 rows)

| Observation | Value | DQ Implication |
|-------------|-------|----------------|
| 89.6% are Tier 3 (unmapped) | 2,943 | Expected — long tail of XBRL concepts |
| 89.6% have NULL cde_id | 2,943 | Matches Tier 3 count exactly — correct |
| 2 status values: approved (342), unmapped (2,943) | — | No 'pending' or 'rejected' in promoted data — correct |
| 4 confidence values: 0.0, 0.6, 0.7, 1.0 | — | Matches tier definitions exactly |

### Table: base.financial_facts (547,398 rows)

| Observation | Value | DQ Implication |
|-------------|-------|----------------|
| 0 null entity_id | 0 | Every fact resolved to an entity |
| 0 bad calendar_quarter | 0 | All in [1, 4] |
| 48.3% superseded | 264,373 | Expected for 20 companies with amendment history |
| 0.9% amendments | 4,786 | Low amendment rate — most filings are originals |
| 51.7% null superseded_by | 283,025 | Matches non-superseded rows (100% - 48.3%) |
| 70.1% null cde_id | 383,499 | Tier 3 concepts have no CDE — expected |
| 39.1% null start_date | 214,231 | Instant-type facts — inherited from raw |

### Table: base.fiscal_calendar (1,294 rows)

| Observation | Value | DQ Implication |
|-------------|-------|----------------|
| 1 null period_start | 1 of 1,294 | Edge case — one period with no observed start_date |
| 1 null duration_days | 1 of 1,294 | Same row — can't compute duration without start |
| 0 negative/zero durations | 0 | All valid |
| ~equal Q1/Q2/Q3/FY distribution | 313-328 each | Balanced — no missing quarters |

### Table: base.amendment_tracking (239,127 rows)

| Observation | Value | DQ Implication |
|-------------|-------|----------------|
| 41.7% null start_date | 99,736 | Instant-type facts — inherited from raw |
| 1.9% null val_change_pct | 4,661 | Division by zero (original_val = 0) — mathematical, not a bug |
| 5 distinct amendment_form values | — | 10-K/A, 10-Q/A, 8-K, etc. |

### Edge Cases for DQ Thresholds

| Observation | Count | Percentage | Recommendation |
|-------------|-------|------------|----------------|
| cde_id NULL in financial_facts | 383,499 | 70.1% | NOT a violation — Tier 3 concepts. Do not add completeness rule. |
| superseded_by NULL in financial_facts | 283,025 | 51.7% | NOT a violation — non-superseded rows. Do not add completeness rule. |
| start_date NULL in financial_facts | 214,231 | 39.1% | NOT a violation — instant-type facts. |
| period_start NULL in fiscal_calendar | 1 | 0.08% | P2 — worth tracking but not blocking |
| val_change_pct NULL in amendment_tracking | 4,661 | 1.9% | NOT a violation — div by zero. |

### Recommendations for @dq-rule-writer

1. **Do NOT add completeness rules for cde_id, superseded_by, start_date** — high null rates are by design
2. **Consider P0 rule: `is_superseded = true` implies `superseded_by IS NOT NULL`** — already exists (BASE-FM-003), verified 0 violations
3. **Consider P0 rule: `status = 'approved'` in concept_mappings implies `cde_id IS NOT NULL`** — already exists (BASE-TN-005), verified 0 violations
4. **Consider P2 rule for fiscal_calendar period_start completeness** — 1 null out of 1,294 (99.9%)
5. **Consider P0 rule: load_date IS NOT NULL across all tables** — structural, should never be null
6. **Consider P0 rule: entity_mappings.confidence in [0, 1]** — already exists (BASE-ER-003)
7. **Consider P1 rule: amendment_tracking.val_change_pct IS NOT NULL where original_val != 0** — 0 violations expected when denominator is non-zero
