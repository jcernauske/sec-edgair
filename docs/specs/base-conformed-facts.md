# Base Zone: Conformed Facts

## Status: 🟢 COMPLETE

| Status | Meaning |
|--------|---------|
| 🟡 DRAFT | Riffing / initial design |
| 🔵 ARCH REVIEW | Awaiting @governance-reviewer approval |
| 🟠 IMPLEMENTATION | Agent pipeline running |
| 🟣 TESTING | DQ rules and validation |
| 🔴 CODE REVIEW | Reviewing |
| ✅ VERIFICATION | Build + DQ + governance verification |
| 🟢 COMPLETE | Shipped |
| ⚫ BLOCKED | Escalated to human |

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-03-15 |
| Author | Jeff + Claude Code |
| Spec Version | 1.0 |
| Last Updated | 2026-03-15 |
| Zone | Base |
| Primary Agent | @primary-agent |
| Blocked By | — |
| Depends On | `base-financial-facts-model` (🟢 COMPLETE), `base-entity-resolution` (🟢 COMPLETE), `base-xbrl-tag-normalization` (🟢 COMPLETE) |

---

## Claude Code Prompt

```
TBD — to be filled when implementation begins
```

---

## 1. Feature Description

### Problem Statement

The consumable zone has a structural dependency problem. Four of five consumable tables (`financial_ratios`, `period_over_period`, `peer_comparison`, `amendment_analysis`) read from `consumable.company_financials` rather than from base tables. This creates:

1. **Error propagation** — a bug in `company_financials` silently cascades to 4 downstream tables
2. **Broken lineage** — `fact_id` does not survive the consumable boundary; tracing `peer_comparison` back to a specific SEC filing requires hopping through 2 intermediate tables with fragile composite key lookups
3. **Build ordering dependency** — consumables must be rebuilt in sequence, not independently
4. **Misplaced business logic** — collision resolution, unit filtering, and supersession filtering are conformation decisions (determining what the truth is), not presentation decisions. They belong in the base zone.

The root cause: `base.financial_facts` outputs **all** competing concepts per business term per period. The hard work of deciding "which XBRL concept wins for Revenue?" is deferred to the consumable zone, forcing `company_financials` to become a de facto intermediate table rather than a true consumable.

### Architectural Principle

- **Base zone** = conformed, business-logic-applied, single source of truth
- **Consumable zone** = shaped for a specific use case, no new business logic, just assembly and presentation

### User Story

As a data engineer, I want the base zone to produce one authoritative fact per (entity, business_term, fiscal_year, fiscal_period) so that every consumable table can read directly from base without depending on other consumables or re-implementing business logic.

### Success Criteria

1. A new `base.conformed_facts` table exists with grain (cik, business_term_id, fiscal_year, fiscal_period) — one row per grain
2. All business logic currently in `consumable.company_financials` (collision resolution, unit filtering, supersession filtering) is performed in the base zone
3. `fact_id` from `base.financial_facts` is preserved as `source_fact_id` in `base.conformed_facts`, enabling direct lineage back to the original fact
4. All five consumable tables read from `base.conformed_facts` (and/or other base tables) — zero consumable-to-consumable dependencies
5. `consumable.company_financials` becomes a thin presentation layer (sector derivation, companies_reporting aggregate, column renaming) with no business logic
6. All existing verification checks (88/88 known 10-K figures) continue to pass
7. Lineage is traceable: consumable row → `base.conformed_facts.source_fact_id` → `base.financial_facts.fact_id` → raw grain fields → SEC filing

---

## 2. Design Decisions

### 2.1 Why a New Table (Not Evolving `base.financial_facts`)

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| Add conformed columns to `base.financial_facts` | No new table; single base fact table | Mixes raw-preserving facts (all concepts, superseded rows) with opinionated conformed view; breaks existing base DQ rules; `financial_facts` grain changes | **Rejected** |
| New `base.conformed_facts` table | Clean separation; `financial_facts` remains the raw-preserving record; conformed_facts is the opinionated view; existing DQ rules untouched | One more table in base | **Selected** |

`base.financial_facts` preserves all facts including superseded ones and competing concepts. That's valuable — it's the "what did the SEC filings actually say?" table. `base.conformed_facts` answers a different question: "what is the single best value for each metric?" These are distinct responsibilities.

### 2.2 Business Logic to Move

The following logic currently lives in `src/consumable/company_financials/build.py` and will move to the new base module:

| Logic | Current Location | What It Does |
|-------|-----------------|--------------|
| Supersession filtering | `build.py` lines 108-113 | `WHERE is_superseded = false` |
| Null BT filtering | `build.py` lines 108-113 | `WHERE business_term_id IS NOT NULL` |
| Null fiscal year filtering | `build.py` lines 108-113 | `WHERE fiscal_year IS NOT NULL` |
| Unit filtering | `build.py` lines 116-124 + `config.py` PRIMARY_UNIT | Keep only rows matching expected unit per business term (USD vs USD/shares) |
| Concept collision resolution | `build.py` lines 145-148 + `config.py` PRIMARY_CONCEPTS | When multiple XBRL concepts map to same BT in same period, select one using priority list then tier/frequency fallback |
| Legacy ID normalization | `build.py` lines 101-104 + `config.py` LEGACY_CDE_TO_BT | CDE-XXX → BT-XXX translation |

### 2.3 Business Logic That Stays in Consumable

| Logic | Stays In | Reason |
|-------|----------|--------|
| Sector derivation (SIC_TO_SECTOR) | `consumable.company_financials` | Presentation/enrichment, not conformation |
| `companies_reporting` aggregate | `consumable.company_financials` | Aggregate metric for display, not truth determination |
| Column renaming (`end_date` → `period_end_date`) | `consumable.company_financials` | Presentation |
| `record_id` computation | Each consumable | Per-consumable grain identity |

### 2.4 Configuration as Governance Artifacts

The collision resolution configuration (`PRIMARY_CONCEPTS`, `PRIMARY_UNIT`) encodes business rules about what XBRL concepts represent each business term. Moving this to the base zone is an opportunity to make it a governance artifact rather than Python config:

| Artifact | Format | Location |
|----------|--------|----------|
| `concept-priority-rules.json` | JSON: `{ "BT-022": { "primary_concepts": [...], "primary_unit": "USD" } }` | `governance/conformation/concept-priority-rules.json` |

This addresses the principal data architect's recommendation: "Make the business_term_id → PRIMARY_CONCEPTS mapping data-driven instead of hardcoded in config.py."

### 2.5 Lineage Preservation

| Field | Purpose |
|-------|---------|
| `source_fact_id` | Direct FK to `base.financial_facts.fact_id` — the winning fact |
| `competing_fact_count` | Integer: how many facts competed for this grain (1 = no collision) |
| `selection_reason` | String: "primary_concept", "tier_frequency_fallback", or "sole_candidate" — why this fact won |

This solves the lineage gap the principal data architect flagged. Every conformed fact has a one-hop traceable path back to the specific base fact and SEC filing.

---

## 3. Technical Specification

### 3.1 `base.conformed_facts` Schema

| # | Column | Type | Required | Source |
|---|--------|------|----------|--------|
| 1 | conformed_id | String | Yes | SHA-256 of grain (cik, business_term_id, fiscal_year, fiscal_period), truncated 16 chars |
| 2 | source_fact_id | String | Yes | `base.financial_facts.fact_id` — the winning fact |
| 3 | entity_id | String | Yes | Inherited from financial_facts |
| 4 | cik | Integer | Yes | Inherited |
| 5 | canonical_name | String | Yes | Inherited |
| 6 | ticker | String | No | Inherited |
| 7 | business_term_id | String | Yes | Inherited (after legacy ID normalization) |
| 8 | business_term | String | Yes | Inherited |
| 9 | financial_statement | String | Yes | Inherited |
| 10 | category | String | Yes | Inherited |
| 11 | source_concept | String | Yes | The XBRL concept that won collision resolution |
| 12 | val | Double | Yes | The value from the winning fact |
| 13 | unit | String | Yes | The unit (post-unit-filtering) |
| 14 | fiscal_year | Integer | Yes | Inherited |
| 15 | fiscal_period | String | Yes | Inherited |
| 16 | fiscal_year_end | String | No | Inherited |
| 17 | period_end_date | Date | Yes | From financial_facts.end_date |
| 18 | calendar_year | Integer | Yes | Inherited |
| 19 | calendar_quarter | Integer | Yes | Inherited |
| 20 | accession_number | String | Yes | From the winning fact's filing |
| 21 | filed_date | Date | Yes | From the winning fact |
| 22 | competing_fact_count | Integer | Yes | Number of facts that competed for this grain |
| 23 | selection_reason | String | Yes | "primary_concept" / "tier_frequency_fallback" / "sole_candidate" |
| 24 | promoted_at | Timestamptz | Yes | When this row was written |
| 25 | load_date | Date | Yes | Pipeline run date |

**Grain:** (cik, business_term_id, fiscal_year, fiscal_period) — same as current `consumable.company_financials`

**Expected row count:** ~26,894 (same as current company_financials, since it's the same grain with the same logic)

### 3.2 Module Structure

```
src/base/conformed_facts/
    __init__.py
    schema.py          # Iceberg schema definition
    build.py           # Core logic: filtering + collision resolution + lineage annotation
    config.py          # Reads governance/conformation/concept-priority-rules.json
    promote.py         # Write to Iceberg with DQ gate (validate_after_write)
    cli.py             # CLI entry point
```

### 3.3 Governance Artifact

```
governance/conformation/
    concept-priority-rules.json    # PRIMARY_CONCEPTS + PRIMARY_UNIT per BT, machine-readable
```

Format:
```json
{
  "version": "1.0",
  "description": "Concept collision resolution rules for base.conformed_facts",
  "rules": {
    "BT-022": {
      "business_term": "Revenue",
      "primary_concepts": [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "RevenuesNetOfInterestExpense",
        "SalesRevenueNet"
      ],
      "primary_unit": "USD"
    }
  }
}
```

### 3.4 Consumable Refactoring

After `base.conformed_facts` is built, each consumable changes its source:

| Consumable | Current Source | New Source |
|------------|---------------|-----------|
| `company_financials` | `base.financial_facts` + `base.entity_mappings` | `base.conformed_facts` + `base.entity_mappings` (for sector lookup only) |
| `financial_ratios` | `consumable.company_financials` | `base.conformed_facts` |
| `period_over_period` | `consumable.company_financials` | `base.conformed_facts` |
| `peer_comparison` | `consumable.company_financials` + `consumable.financial_ratios` | `base.conformed_facts` + `consumable.financial_ratios` |
| `amendment_analysis` | `base.amendment_tracking` + `consumable.company_financials` | `base.amendment_tracking` + `base.conformed_facts` |

**Note on `peer_comparison`:** It still reads `consumable.financial_ratios` because it needs computed ratio values (presentation-layer math). But the dependency chain shortens from `base → company_financials → financial_ratios → peer_comparison` to `base → financial_ratios → peer_comparison`. The remaining dependency is appropriate — ratios are computed values that peer_comparison aggregates.

### 3.5 What `consumable.company_financials` Becomes

Post-refactor, `company_financials` is a thin presentation layer:

```python
def build_company_financials(conformed_facts=None, entity_mappings=None):
    """Read base.conformed_facts, add sector + companies_reporting."""
    # 1. Read base.conformed_facts (all business logic already applied)
    # 2. Join entity_mappings for SIC code
    # 3. Derive sector from SIC_TO_SECTOR
    # 4. Compute companies_reporting aggregate
    # 5. Compute record_id
    # 6. Return records
```

No filtering. No collision resolution. No unit selection. Just enrichment and assembly.

---

## 4. Dependency Graph (Before vs After)

### Before (current)
```
base.financial_facts ──────→ consumable.company_financials ──→ consumable.financial_ratios
base.entity_mappings ──────┘              │                            │
                                          ├──→ consumable.period_over_period
                                          ├──→ consumable.peer_comparison ←──┘
base.amendment_tracking ──→ consumable.amendment_analysis ←──┘
```

### After (proposed)
```
base.financial_facts ──→ base.conformed_facts ──→ consumable.company_financials
base.entity_mappings ─┘         │                  (thin: +sector, +companies_reporting)
                                ├──→ consumable.financial_ratios
                                ├──→ consumable.period_over_period
                                ├──→ consumable.peer_comparison ←── consumable.financial_ratios
                                │                                   (ratios are computed values,
base.amendment_tracking ────────┴──→ consumable.amendment_analysis   this dependency is appropriate)
```

Key change: all consumables originate from base. The only remaining consumable-to-consumable dependency (`peer_comparison` ← `financial_ratios`) is appropriate because ratios are computed presentation-layer values that peer_comparison aggregates — not business logic.

---

## 5. Rollout Strategy

### Phase 1: Build `base.conformed_facts` (additive, no breaking changes)
1. Create `src/base/conformed_facts/` module
2. Create `governance/conformation/concept-priority-rules.json` from current Python config
3. Build and promote `base.conformed_facts` table
4. Write DQ rules for the new table
5. Verify: row count matches `consumable.company_financials`, values match

### Phase 2: Rewire consumables (one at a time)
1. Rewire `consumable.company_financials` to read from `base.conformed_facts` — strip business logic, keep only presentation
2. Run all 88 verification checks — must still pass
3. Rewire `financial_ratios` to read from `base.conformed_facts`
4. Rewire `period_over_period` to read from `base.conformed_facts`
5. Rewire `amendment_analysis` to read from `base.conformed_facts` + `base.amendment_tracking`
6. Rewire `peer_comparison` to read from `base.conformed_facts` + `consumable.financial_ratios`
7. Run full DQ suite + all verification checks after each rewire

### Phase 3: Cleanup
1. Remove collision resolution logic from `consumable.company_financials`
2. Remove `PRIMARY_CONCEPTS` and `PRIMARY_UNIT` from `src/consumable/company_financials/config.py`
3. Update lineage JSON files to reflect new data flow
4. Update governance models (conceptual, logical, physical) for the new table
5. Update README data model diagrams

---

## 6. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Verification regression (88 checks fail) | High — proves data correctness | Run verification after every phase; rollback if any check fails |
| Consumable DQ rules reference old source | Medium — rules may break | Audit all consumable DQ rules for source table references before rewiring |
| `peer_comparison` still depends on `financial_ratios` | Low — this is an appropriate dependency | Document why: ratios are computed values, not business logic |
| Configuration drift between JSON artifact and old Python config | Medium — dual-source-of-truth during rollout | Phase 1 generates JSON FROM Python config; Phase 3 deletes Python config |

---

## 7. DQ Rules (to be written by @dq-rule-writer)

Expected rule categories for `base.conformed_facts`:

| Category | Example |
|----------|---------|
| Uniqueness | One row per (cik, business_term_id, fiscal_year, fiscal_period) |
| Referential integrity | Every `source_fact_id` exists in `base.financial_facts` |
| Completeness | All 20 companies have conformed facts |
| Completeness | All 25 business terms represented |
| Consistency | `val` matches `base.financial_facts.val` for the referenced `source_fact_id` |
| Consistency | `competing_fact_count` >= 1 for all rows |
| Consistency | `selection_reason` is one of the three valid values |
| Volume | Row count within expected range |

---

## 8. Implementation Log

_To be filled during implementation._

---

## 9. Governance Artifacts

_To be produced during implementation:_
- [ ] Conceptual model (`governance/models/base-conformed-facts-conceptual.md`)
- [ ] Logical model (`governance/models/base-conformed-facts-logical.md`)
- [ ] Physical model (`governance/models/base-conformed-facts-physical.md`)
- [ ] Business term mappings (reuse existing BT-XXX terms)
- [ ] DQ rules (`governance/dq-rules/base-conformed-facts.json`)
- [ ] Lineage event (`governance/lineage/base-conformed-facts.json`)
- [ ] Updated lineage events for all 5 consumable tables
- [ ] CDE mapping update
- [ ] Updated README data model diagrams

---

## 10. Final Review

| Reviewer | Date | Status | Notes |
|----------|------|--------|-------|
| @governance-reviewer | — | Pending | — |
| @staff-engineer | — | Pending | — |
