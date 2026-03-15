# Principal Data Architect Re-Review

**Date:** 2026-03-15
**Reviewer:** @principal-data-architect
**Scope:** Re-evaluation after remediation work

## Changes Since Original Review

Substantial remediation was executed across four specs and one infrastructure change:

1. **base.conformed_facts** — A new base zone table that centralizes all business logic (collision resolution, unit filtering, supersession filtering) that was previously embedded in consumable.company_financials. All five consumable tables now read from base, eliminating consumable-on-consumable dependencies. The concept priority rules were extracted from Python config into `governance/conformation/concept-priority-rules.json` as a machine-readable governance artifact.

2. **Runtime lineage** — A `governance.lineage_events` Iceberg table that captures START/COMPLETE/FAIL events with snapshot IDs, row counts, DQ results, and duration. All 11 promote functions are instrumented. Static lineage docs are now generated from runtime data.

3. **DuckDB anti-join dedup** — `filter_existing_records()` in iceberg_setup.py replaces the Python set-based dedup pattern. Reads only the ID column via PyIceberg scan, performs anti-join in DuckDB's columnar engine. All consumable promotes use this.

4. **AI-Ready improvements** — Generic anomaly detection (any company with negative equity, not just Boeing), `get_amendment_summary` tool added (tool #8), 6 shared enrichment helpers extracted from financial_tools.py (reduced from ~1,390 to 1,202 lines).

5. **Code quality** — DQ gates added to all 5 consumable CLI build commands via `validate_after_write()`. Bare except clauses eliminated. Dead code removed (`read_current_with_iceberg_scan`, `migrate_load_date.py`). `create_test_table` renamed to `get_or_create_table`. Shared `consumable/shared.py` extracts `SIC_TO_SECTOR` and `build_sector_lookup`.

**By the numbers:** 466 tests (up from 442), 129 DQ rules (up from 111, originally 92), 14 Iceberg tables (up from 13), all verification checks still passing (positive + negative).

## Section Re-Grades

### Architecture
**Original:** B+
**Updated:** A

**Rationale:** Both scaling concerns from the original review are resolved.

The in-memory dedup pattern (Python set over full table reads) has been replaced with `filter_existing_records()`, which uses PyIceberg `scan(selected_fields=(id_field,))` to read only the ID column, then performs a DuckDB anti-join. This is the right fix: columnar engine, single column, hash join. Memory footprint goes from O(N * columns) to O(N * 1 column) and the join runs in DuckDB's optimized engine rather than Python iteration. At 10M rows, this still works.

More importantly, the consumable-on-consumable dependency chain is eliminated. Before: `base → company_financials → financial_ratios → peer_comparison` (3 hops, sequential build). After: all consumables originate from `base.conformed_facts`. The one remaining consumable-to-consumable dependency (`peer_comparison ← financial_ratios`) is appropriate — ratios are computed presentation-layer values that peer_comparison aggregates.

The `base.conformed_facts` table is architecturally sound. It answers a different question than `base.financial_facts`: "what is the single best value for each metric?" vs "what did the filings say?" The grain is correct, the lineage columns (`source_fact_id`, `competing_fact_count`, `selection_reason`) are well-designed, and the build logic is clean. This is the right abstraction boundary.

The DQ runner still does full-table scans (Item 7 in the remediation spec was "Yes" but I don't see evidence of iceberg_scan pushdown in the DQ runner). At current scale this doesn't matter. It's the right item to defer.

What keeps this from A+ is that `read_with_duckdb()` still materializes full tables as Python dicts for every build function (not just dedup). The build functions in base and consumable all call `read_with_duckdb(table)` which returns `list[dict]`. This is a smaller concern than the dedup pattern was, but it means the pipeline's read path is still O(N * columns) in memory. For the current 20-company dataset this is academic.

### Data Quality & Trust
**Original:** A-
**Updated:** A

**Rationale:** Both gaps I flagged are now closed. The grade moves up.

The Pfizer discrepancy (1.81% difference on Revenue) was investigated and documented as expected behavior — the broader `RevenuesNetOfInterestExpense` concept was correctly selected per the collision resolution rules, and was even added to BT-022's primary_concepts list in `concept-priority-rules.json`. This is the right resolution: understand it, document it, make a deliberate choice. Good.

DQ rules grew from 111 to 129. The 18 new rules add two dimensions that were entirely missing: **Accuracy** (8 rules) and **Reasonableness** (10 rules). This is no longer a system that only validates structure — it now validates meaning.

**Negative testing is real.** `scripts/verify_negative.py` runs 10 checks against real Iceberg tables, each asserting something should NOT exist: no duplicate grains, no superseded facts leaked, no null business terms, no wrong-unit values, no fiscal year collisions, no orphan ratios, no cross-zone grain violations. These are targeted at the specific pipeline failure modes — supersession filter leaks, unit filter leaks, collision resolution duplicates. This is genuine negative testing, not repackaged positive checks with inverted assertions.

**Accuracy rules are meaningful.** BASE-CF-025/026/027 validate that the three pipeline filters (supersession, null BT, wrong unit) did not leak. CONS-CF-011 validates row count alignment between base and consumable (1:1 invariant). CONS-CF-012 validates no fiscal year collisions — exactly the "Apple's Revenue should not appear in two different fiscal years for the same period" example I cited. All are P0. All passed against real data.

**Reasonableness thresholds are evidence-based.** The spec proposed tight bounds (Operating Margin [-5, 1], CapEx-to-Revenue [0, 1]) but EDA revealed real outliers — Netflix Q1 2010 with $12K revenue producing a 4,862x Operating Margin, Exxon FY2008 with a 367x Net Margin from a likely quarterly-vs-annual mapping artifact. The rules were adjusted to [-100, 100] with explicit outlier tolerances (`result <= 2`) and each rationale documents the specific root cause. This is the right approach: set bounds from data, document the exceptions, don't pretend the data is cleaner than it is. The Gross Margin rule (RATIO-001) kept the tight [-1, 1] bound because the EDA confirmed no violations — showing the team tightened where they could and loosened only where the data demanded it.

All 54 rules across the three tables (27 + 12 + 15) passed against real data with timestamped execution results. No P0 failures.

What keeps this from A+: the Accuracy rules for BASE-CF-025/026/027 overlap with existing Completeness/Consistency rules (BASE-CF-019, BASE-CF-006, BASE-CF-011) — same SQL, different dimension label. This is defensible for dimension coverage but not additional protection. The Reasonableness bounds on ratio rules are wide enough ([-100, 100]) that they would only catch catastrophic failures, not subtle data issues. These are minor — the coverage gap that held this at A- is genuinely closed.

### Governance
**Original:** B+
**Updated:** A

**Rationale:** The single biggest deduction in the original review was "documentation masquerading as lineage." That is comprehensively fixed.

`governance.lineage_events` is a real Iceberg table with a well-designed schema: event_id, run_id (for START/COMPLETE pairing), event_type, job metadata, snapshot IDs, row counts, DQ results, duration, and error messages. Every promote function is instrumented — all 11 of them. The instrumentation is fault-tolerant (lineage write failures log warnings but don't block the pipeline), which is the correct design for a cross-cutting concern.

The `generate-docs` CLI command regenerates static lineage JSON files from runtime data, meaning the governance/lineage/*.json files are now derived artifacts, not primary sources. This inverts the original problem: before, the files were fiction; now they're projections of reality.

The concept-priority-rules.json governance artifact is a smart addition. Moving collision resolution configuration from Python code to a versioned JSON file means a new XBRL concept mapping can be added by editing a governance artifact rather than modifying source code. This directly addresses my "What I'd Do Differently" item #4.

What keeps this from A+: the audit-trail JSON files are still human-readable decision logs, not machine-queryable governance events. This was a minor deduction in the original review and remains minor. The lineage fix was the material gap and it's closed.

### AI-Readiness
**Original:** B+
**Updated:** A-

**Rationale:** All three deductions from the original review are addressed.

The anomaly checker is now generic: Rule 2 checks `"stockholders equity" in metric.lower() and value < 0` — any company, not just Boeing. Rule 3 checks D/E ratio > 50x generically. This is the correct pattern: derive anomalies from data conditions, not ticker symbols.

The `get_amendment_summary` tool (tool #8) fills the gap where amendment_analysis data was loaded but inaccessible to the chat agent. Users can now ask "Which companies restated their earnings?" and get an answer.

Six shared enrichment helpers were extracted from `financial_tools.py`: `_fetch_metric_growth`, `_fetch_metric_peer_rank`, `_fetch_ratio_peer_rank`, `_fetch_net_margin`, `_fetch_ratio_yoy`, `_get_sector_stats`. The file went from ~1,390 to 1,202 lines. The spec targeted ~900 lines — the reduction is meaningful but less aggressive than planned. The named helpers (`_enrich_metric`, `_enrich_ratio` from the spec) were not implemented as described; instead, lower-level fetch functions were extracted. This is a reasonable alternative — the individual fetch functions are more composable, even if the calling code still has some assembly logic.

What keeps this from A: the gap between "questions users will ask" and "questions the tools can answer" is narrower but still present. Multi-step analytical questions ("How has R&D spending as % of revenue changed vs sector average?") still require multiple tool calls. Rule 6 in the anomaly checker (financial sector missing ratios) still only triggers for Gross Margin and Operating Margin, missing other ratios meaningless for financials. These are minor but real.

### Code Quality
**Original:** B
**Updated:** A-

**Rationale:** The most significant code quality gap — missing DQ gates in consumable promotes — is closed. Every consumable CLI build command now calls `validate_after_write()` after promote. This matches the base zone pattern and fulfills the project's own rule ("All promote code must check-before-write").

The bare except clauses are gone. The old pattern (`existing = read_with_duckdb(table); existing_ids = {r["record_id"] for r in existing}` wrapped in `try/except Exception: pass`) is replaced by `filter_existing_records()`, which handles the empty-table case internally without swallowing errors.

Dead code is cleaned up: `read_current_with_iceberg_scan` removed, `migrate_load_date.py` deleted, `create_test_table` renamed to `get_or_create_table`. The shared `consumable/shared.py` extracts `SIC_TO_SECTOR` and `build_sector_lookup` — previously duplicated across consumable modules.

All promote functions now follow a consistent pattern: emit_start → try → filter_existing_records → append_data → emit_complete → catch → emit_fail → raise. This is clean, auditable, and identical across all 11 promotes.

What keeps this from A: the `_compute_record_id` function is still defined independently in every module (conformed_facts, company_financials, financial_ratios, etc.) with identical logic — only the `RECORD_ID_GRAIN` differs. This should be a shared utility. Return type hints are still missing from most functions. The `financial_tools.py` refactoring was partial — 1,202 lines is still large for a single file, and the enrichment extraction could go further. But these are polish items, not structural gaps.

## Remaining Gaps

1. ~~**No negative testing in verification scripts.**~~ **RESOLVED.** `scripts/verify_negative.py` with 10 targeted absence checks.

2. **`read_with_duckdb()` still returns `list[dict]`.** Every build function materializes full tables as Python dicts. The dedup path is fixed, but the data read path is still O(N * columns) in memory. This would need attention at 100x scale.

3. **DQ runner still does full-table scans.** Item 7 from the remediation spec (iceberg_scan pushdown in DQ runner) does not appear to have been implemented. At current scale, irrelevant.

4. **Consumable DQ gates are in CLI, not promote.** The base.conformed_facts promote has `validate_after_write` directly in the promote function. The five consumable promotes do not — the DQ gates are in the CLI `cmd_build` functions instead. This means programmatic callers of `promote_company_financials()` bypass DQ validation. The inconsistency is worth noting, though the CLI is the primary execution path.

5. **Financial sector anomaly rule is still narrow.** Rule 6 only flags Gross Margin and Operating Margin as N/A for financials. Other ratios (CapEx Ratio, etc.) may also be misleading for banks.

6. **No incremental refresh, monitoring, or concurrent access safety.** These were flagged as "What's Missing for Production" in the original review and remain unaddressed. They're also not in scope for the current project phase.

## Original "What I'd Cut" — Status

| Item | Status |
|------|--------|
| Static OpenLineage JSON files | **Resolved** — now generated from runtime data |
| `read_current_with_iceberg_scan` | **Removed** |
| `infra/migrate_load_date.py` | **Removed** |

All three items addressed. Clean.

## Overall Verdict
**Original:** B+
**Updated:** A

The remediation work is thorough, well-targeted, and high-quality. Every top risk from the original review has been addressed:

- **Missing DQ gates** → All consumable CLI builds now run `validate_after_write()`
- **In-memory scaling** → DuckDB anti-join dedup via `filter_existing_records()`
- **Hardcoded anomaly detection** → Generic rules based on data conditions
- **No negative testing** → 10-check negative verification script proving bad data is absent
- **No semantic DQ rules** → 18 new Accuracy + Reasonableness rules with evidence-based thresholds

The biggest architectural improvement is `base.conformed_facts` and the consumable rewiring. This isn't just a fix — it's a meaningful improvement to the system's data architecture. Business logic now lives in the base zone where it belongs. Consumables are thin presentation layers. The dependency graph is flatter and more maintainable. The concept priority rules are a governance artifact, not buried Python config.

The runtime lineage implementation closes the most embarrassing gap from the original review. The difference between "we have lineage docs" and "every promote emits runtime events to an Iceberg table with snapshot IDs, row counts, and DQ results" is the difference between aspiration and engineering.

The semantic DQ and negative testing work closes the last gap that was holding back a clean A. The DQ framework now covers 9 dimensions (Uniqueness, Completeness, Validity, Consistency, Freshness, Referential Integrity, Volume, Accuracy, Reasonableness) with 129 rules across all tables. The negative verification script is the complement the positive verification was missing — together they form a complete correctness argument: correct data exists AND incorrect data is absent.

What prevents an A+: the remaining gaps are real but minor. The DQ gate inconsistency (promote vs CLI), the partial financial_tools.py refactoring, the still-present `read_with_duckdb` memory pattern, and the wide Reasonableness bounds on ratio rules. These are A→A+ gaps, not structural deficiencies.

Would I ship this? Yes, to the stated audience. Would I stake my reputation on it? On the data quality, verification rigor, and architectural soundness — yes. On production readiness at scale — still no, but the path to production is clearer now, and the hardest architectural decisions have been made correctly.

The AI-agent-driven methodology continues to impress. The fact that a review → remediation → re-review cycle this comprehensive was executed coherently across architecture, governance, code quality, testing, and now semantic data quality — with 129 DQ rules, 10 negative checks, a new base zone table, runtime lineage, and dedup optimization — is strong evidence that the agent pipeline produces disciplined engineering output, not just code.
