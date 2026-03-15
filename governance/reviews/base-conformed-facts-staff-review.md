# Staff Engineer Review: base-conformed-facts

### Date: 2026-03-15
### Reviewer: @staff-engineer
### Status: APPROVED

### Verdict

This is solid work. The collision resolution logic is correctly ported from `consumable.company_financials`, the governance artifact extraction (Python config to JSON) is done right, the DQ rules are real (not theater), and the lineage chain is intact. The code is simple, readable, and does what the spec asks for. There are a few issues worth flagging -- one moderate, one minor, and a couple of nits -- but none are blocking.

I would put my name on this.

### Code Quality

**`schema.py`** -- Clean. 25 fields match the physical model exactly. Field IDs are sequential. Required/optional flags match spec. Nothing to say.

**`config.py`** -- Good separation. Loading rules from a JSON governance artifact instead of hardcoding is the right call. The `_load_rules()` function returns `{}` if the file is missing, which means `PRIMARY_CONCEPTS` and `PRIMARY_UNIT` will both be empty dicts, and the pipeline will silently produce zero output (every fact skipped because `expected_unit = PRIMARY_UNIT.get(bt_id)` returns None). This is acceptable for "shouldn't happen in a properly configured environment" as the docstring states, and the DQ volume rule (BASE-CF-012) would catch zero output. The `LEGACY_CDE_TO_BT` mapping matches the consumable config exactly.

**`build.py`** -- This is the heart of the module and it's well-written.
- The filtering pipeline (lines 140-165) exactly matches the consumable's Steps 1-2 (supersession, null BT, null FY, unit filtering).
- The grouping (lines 168-176) uses the same grain.
- `_select_concept()` correctly extends the consumable version by adding `selection_reason` tracking and the `sole_candidate` path. The consumable version had an implicit sole_candidate path (single-element group would just match on primary_concept or fallback), but the base version makes it explicit with a dedicated code path -- good.
- `_compute_concept_frequency()` operates on `unit_filtered` (line 181), same as the consumable (line 138). Correct.
- The `fiscal_year_end` lookup from `entity_mappings` (lines 41-49, 126, 217) correctly uses CIK-based join rather than copying from `financial_facts`. This matches the lineage JSON which says `fiscal_year_end` comes from `base.entity_mappings`.
- Logging is useful and quantitative (row counts at each filter step, collision resolution stats).
- One observation: `float(selected.get("val", 0))` at line 213 means a missing `val` silently becomes 0.0 rather than failing. In practice, `val` is required in `financial_facts` so this never fires, but it's a defensive default that could mask bugs. Not blocking since DQ rule BASE-CF-007 (val consistency check) would catch a 0.0 that doesn't match the source.

**`promote.py`** -- Has the DQ gate (`validate_after_write` at line 99). Uses full overwrite (drop + recreate), which is correct for a table that's recomputed entirely from source each run. The `validate` parameter (line 30) allows skipping DQ in tests -- fine.

One issue: lines 66-71, the dedup guard after a drop-and-recreate:
```python
except (NoSuchTableError, Exception):
    pass
```
`(NoSuchTableError, Exception)` catches literally everything because `Exception` is the base class. This is `except Exception: pass` with extra steps. The intent is to handle "table just created, no data yet," but this swallows real errors (e.g., DuckDB connection failure, permission error, corrupted parquet). Since the table was just dropped and recreated two lines above, it will always be empty, making this entire dedup guard (lines 66-78) dead code in practice. See Issue #1.

**`cli.py`** -- Straightforward. `cmd_build` does a dry run (build without promote), `cmd_promote` does build + promote + DQ. The `cmd_status` function has `except Exception` at line 93 which again swallows everything -- same pattern issue. The docstring says `promote` is "promote only (reads from last build)" but it actually calls `build_conformed_facts()` again. Minor docstring inaccuracy at line 6.

### Test Quality

No dedicated test files exist for `base.conformed_facts`. The DQ rules (19 rules, all passing against real Iceberg data) serve as the integration test suite. The DQ rules are NOT theater:

- BASE-CF-001/002: Grain uniqueness -- real structural validation
- BASE-CF-003: Referential integrity (source_fact_id exists in financial_facts) -- this is the lineage chain test
- BASE-CF-007: Val consistency (conformed val matches source val) -- catches transformation bugs
- BASE-CF-010: Cross-field consistency (sole_candidate iff competing_fact_count=1) -- validates the new selection_reason logic
- BASE-CF-019: No superseded facts leak through -- structural filter validation

These rules validate real behavior against real Iceberg data. The thresholds are derived from the EDA report with documented rationale. Acceptable.

### Spec Compliance

1. **New `base.conformed_facts` table with correct grain** -- Done. One row per (cik, business_term_id, fiscal_year, fiscal_period).
2. **Business logic moved from consumable** -- Done. Supersession filtering, null BT filtering, null FY filtering, unit filtering, concept collision resolution, legacy ID normalization -- all present in `build.py`.
3. **`source_fact_id` preserved for lineage** -- Done. `source_fact_id = selected.get("fact_id", "")` at line 203.
4. **Success criteria #4 (consumables rewired)** -- Not done, but spec explicitly defers this to Phase 2. Phase 1 only.
5. **Success criteria #5 (company_financials thin layer)** -- Deferred to Phase 2. Correct.
6. **Success criteria #6 (88/88 verification checks)** -- Not verified in this phase since consumables aren't rewired yet. Phase 2.
7. **Success criteria #7 (lineage chain)** -- Done. Lineage JSON has column-level mapping from `base.conformed_facts.source_fact_id` to `base.financial_facts.fact_id`.
8. **Governance conformation artifact** -- Done. `concept-priority-rules.json` has 25 business terms, matches consumable config exactly.
9. **Physical model match** -- Schema in `schema.py` is an exact copy of the physical model's schema definition.

### Collision Resolution Port Verification

I compared `_select_concept()` in `build.py` (lines 62-96) against the consumable's version in `company_financials/build.py` (lines 203-230):

- **Primary concept walk:** Identical logic (walk `PRIMARY_CONCEPTS` list, return first match).
- **Tier/frequency fallback:** Identical sort key: `(tier ascending, concept_freq descending)`.
- **New: sole_candidate path:** Lines 80-81 add early return for single-fact groups. The consumable version falls through to primary_concept check even for single-fact groups, which would return `"primary_concept"` if the concept is in the list or `"tier_frequency_fallback"` if not. The base version returns `"sole_candidate"` for all single-fact groups, which is semantically more accurate. This is a deliberate behavioral difference, not a bug.
- **PRIMARY_CONCEPTS and PRIMARY_UNIT values:** I compared the JSON artifact against the consumable's Python config. All 25 business terms match exactly -- same concepts in the same order, same units.

The port is correct.

### Issues

| # | Severity | File | Issue | Required Fix |
|---|----------|------|-------|-------------|
| 1 | Minor | `src/base/conformed_facts/promote.py:70` | `except (NoSuchTableError, Exception): pass` catches all exceptions silently. Since the table is dropped and recreated immediately before this block, the dedup guard (lines 66-78) is dead code in the current full-rebuild strategy. The broad exception swallowing could mask real errors if the rebuild strategy changes. | Change to `except NoSuchTableError: pass` or remove the entire dedup guard block since it's dead code after a drop+recreate. Either fix is acceptable. Not blocking. |
| 2 | Nit | `src/base/conformed_facts/cli.py:6` | Docstring says "promote only (reads from last build)" but `cmd_promote` actually calls `build_conformed_facts()` -- it rebuilds, doesn't read from a cache. | Update docstring to match behavior. |

### What's Acceptable

- The filtering pipeline is a faithful port from consumable. No logic was lost or silently changed.
- The `selection_reason` and `competing_fact_count` metadata additions are the right way to make collision resolution transparent without changing the resolved values.
- 19 DQ rules with EDA-derived thresholds and documented rationale. The distribution-based rule (BASE-CF-018) is a particularly good idea for catching behavioral drift.
- The governance conformation artifact (`concept-priority-rules.json`) correctly externalizes what was previously buried in Python config. Version field present.
- The lineage JSON has column-level mappings for all 25 columns. The `fiscal_year_end` lineage correctly points to `entity_mappings`, not `financial_facts`.
- Code is simple and readable. No abstraction astronautics. Functions do one thing. Names are precise.
