# Pre-Implementation Review: base-conformed-facts

**Reviewer:** @governance-reviewer
**Date:** 2026-03-15
**Verdict:** APPROVED WITH CONDITIONS

## Checklist

- [x] Spec defines clear problem statement
- [x] Success criteria are measurable
- [x] Dependencies identified and satisfied
- [x] Governance artifacts listed
- [x] Data modeling gate acknowledged (greenfield -> C/L/P required)
- [x] DQ rule categories identified
- [x] Rollout strategy is incremental (not big-bang)
- [x] Risk assessment covers data correctness

## Findings

### 1. Problem Statement & Success Criteria (PASS)

The spec articulates a real architectural problem: business logic (collision resolution, unit filtering, supersession filtering) currently lives in the consumable zone, creating consumable-to-consumable dependencies that break lineage, couple build ordering, and propagate errors. The proposed solution -- a new `base.conformed_facts` table that performs all conformation in the base zone -- is well-motivated.

Success criteria are concrete and measurable: one row per grain, `fact_id` lineage preserved, 88/88 verification checks passing, all consumables rewired to read from base. These are verifiable.

### 2. Dependencies (PASS)

All three dependencies are confirmed COMPLETE with existing source code and governance models:

| Dependency | Status | Models Exist | Code Exists |
|-----------|--------|-------------|-------------|
| `base-financial-facts-model` | COMPLETE | C/L/P all present | `src/base/financial_facts_model/` |
| `base-entity-resolution` | COMPLETE | C/L/P all present | `src/base/entity_resolution/` |
| `base-xbrl-tag-normalization` | COMPLETE | C/L/P all present | `src/base/xbrl_tag_normalization/` |

### 3. Data Modeling Gate (CONDITION REQUIRED)

This is a **greenfield** spec -- `src/base/conformed_facts/` does not exist, and no `base-conformed-facts-*.md` models exist in `governance/models/`. Per the project rules (CLAUDE.md), the greenfield pipeline requires:

1. @data-steward identifies business terms -> 👁️ HUMAN APPROVAL GATE
2. @semantic-modeler proposes conceptual model -> 👁️ HUMAN APPROVAL GATE
3. @semantic-modeler proposes logical model -> 👁️ HUMAN APPROVAL GATE
4. @data-analyst performs EDA on source data
5. @dq-rule-writer writes DQ rules from EDA + logical model
6. @semantic-modeler generates physical model from approved logical
7. @primary-agent implements (must match approved physical model)

The spec correctly lists all three model artifacts as "to be produced" in Section 9, confirming awareness. However, `REQUIRE_HUMAN_APPROVAL = True`, so the human approval gates at steps 1-3 are real blocking gates.

**Condition:** The data modeling pipeline (steps 1-6 above) must complete before @primary-agent begins implementation. The spec's Phase 1 rollout must not begin until the physical model is approved.

### 4. Business Terms (PASS -- reuse expected)

The spec states it will "reuse existing BT-XXX terms" (Section 9). This is correct -- `base.conformed_facts` does not introduce new business concepts; it reshapes existing base data. The business glossary already contains all 54 terms including the relevant ones (BT-022 Revenue, BT-024 Assets, etc.). The `concept-priority-rules.json` governance artifact references existing BT-XXX IDs.

@data-steward should still confirm no new project-specific terms are needed (e.g., for `selection_reason`, `competing_fact_count`), but these are pipeline-internal metadata fields, not business terms. This is a lightweight check, not a blocking concern.

### 5. Governance Artifacts (PASS)

Section 9 lists a comprehensive set of governance artifacts to be produced:

- Conceptual, logical, physical models
- Business term mappings
- DQ rules
- Lineage event (new table + updated lineage for all 5 consumables)
- CDE mapping update
- README diagram updates

This is thorough. The requirement to update lineage for all 5 consumable tables (not just the new base table) shows appropriate scope awareness.

### 6. DQ Rule Categories (PASS)

Section 7 identifies 8 rule categories covering uniqueness, referential integrity, completeness, consistency, and volume. These are well-chosen for a conformation table. Notably:

- **Referential integrity** (`source_fact_id` -> `base.financial_facts`) is critical for the lineage promise
- **Consistency** (val matches source fact) catches conformation bugs
- **Uniqueness** on the grain enforces the "one row per grain" contract

Missing but minor: no freshness rule is listed. Since this is a derived table, freshness is less critical, but a rule like "promoted_at within expected range of pipeline run" would be useful. Not blocking.

### 7. Rollout Strategy (PASS)

The three-phase approach is well-designed:

- **Phase 1** is purely additive (new table, no changes to existing pipeline)
- **Phase 2** rewires consumables one at a time with verification after each
- **Phase 3** cleans up dead code

This is textbook incremental rollout. Each phase has a clear rollback boundary.

### 8. Risk Assessment (PASS with note)

Four risks are identified with appropriate mitigations. One additional risk worth noting:

| Risk | Impact | Mitigation |
|------|--------|------------|
| Schema of `base.conformed_facts` differs from approved physical model | Medium -- governance violation | @governance-reviewer post-implementation check will compare Iceberg schema to physical model |
| New governance artifact (`concept-priority-rules.json`) lacks a versioning/change-control process | Low -- could drift over time | Add a version field (spec already includes `"version": "1.0"`) and document change process |

Neither of these is blocking.

### 9. Spec Completeness (PASS)

The spec includes: problem statement, design decisions with rationale, full schema definition (25 columns), module structure, governance artifact format, dependency graphs (before/after), rollout phases, risk assessment, DQ rule categories, and governance artifact checklist. This is one of the most thorough specs in the project.

### 10. Consumable Refactoring Scope (ADVISORY)

The spec defines changes to all 5 consumable tables in Section 3.4. This is ambitious scope for a single spec. The phased rollout mitigates risk, but the spec should be clear that Phase 2 consumable rewiring may require updates to existing consumable DQ rules (the risk table mentions this). Each consumable rewire should be verified against its own existing DQ scorecard, not just the 88 verification checks.

## Conditions (must be addressed before implementation)

1. **DATA MODELING GATE (BLOCKING):** The greenfield data modeling pipeline must complete before implementation begins:
   - @data-steward confirms business term reuse (no new terms needed)
   - @semantic-modeler produces conceptual model -> human approval
   - @semantic-modeler produces logical model -> human approval
   - @semantic-modeler generates physical model from approved logical
   - All three models saved to `governance/models/base-conformed-facts-{conceptual,logical,physical}.md`

2. **SPEC STATUS (BLOCKING):** Spec status should be updated from DRAFT to ARCH REVIEW (this review), then to IMPLEMENTATION only after the data modeling gate clears.

## Advisory Items (non-blocking)

1. Consider adding a freshness DQ rule for `promoted_at` timestamp validation.
2. @data-steward should explicitly confirm that `selection_reason` and `competing_fact_count` are pipeline metadata, not business terms requiring glossary entries.
3. Phase 2 consumable rewiring should verify against each consumable's existing DQ scorecard, not just the 88-check verification suite.

## Decision Rationale

The spec is well-written, architecturally sound, and addresses a real structural problem in the current pipeline. All dependencies are satisfied. The governance artifact list is comprehensive. The rollout strategy is incremental with clear rollback boundaries.

The sole blocking condition is the greenfield data modeling gate, which the spec itself acknowledges (Section 9 lists models as "to be produced"). This is not a deficiency in the spec -- it is the normal greenfield workflow. The spec is approved to proceed to the data modeling pipeline; implementation begins after models are approved.
