# Infrastructure: Governance Model Alignment

## Status: 🟡 DRAFT

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
| Created | 2026-03-14 |
| Author | Jeff + Claude Code |
| Spec Version | 1.0 |
| Last Updated | 2026-03-14 |
| Zone | Infrastructure (cross-cutting) |
| Primary Agent | @primary-agent |
| Blocked By | — |
| Depends On | All base zone specs (🟢 COMPLETE) |
| Blocks | All consumable zone specs |

---

## Claude Code Prompt

```
Implement the infra-governance-model-alignment spec.

This refactors the governance model to fix a conceptual error: CDEs were used as
attribute definitions when they should be flags. Business terms are the canonical
reference layer. CDE and PII become boolean flags on attributes in the logical model,
not separate catalogs.

This is a cross-cutting infrastructure change that touches base zone code, schemas,
DQ rules, tests, and governance artifacts. No new tables — field renames and artifact
restructuring.
```

---

## 1. Feature Description

### Problem Statement

The current governance model has a structural error: CDEs (Critical Data Elements) are used as the normalization target for XBRL concepts. `concept_mappings.cde_id` maps concepts to CDE-007 through CDE-031, and `financial_facts` carries these IDs as if they were attributes. But CDEs are governance flags — a tag that says "this attribute is critical and needs extra governance controls." They are not the attributes themselves.

The result:
- Multiple XBRL concepts map to the same "CDE" (e.g., 4 revenue concepts → CDE-015), creating collision problems in the consumable zone
- The CDE catalog (`governance/cde-catalog.json`) is really a business glossary of financial metrics — it defines terms, not governance flags
- PII is tracked in a separate policy file but not connected to the business glossary or data models in a unified way
- The conceptual separation between "what does this data mean" (business terms) and "how critical is it" (CDE flag) is lost

### What Should Be True

1. **Business terms** are the canonical reference layer. Every XBRL concept maps to a business term. Business terms are source-agnostic — when we add stock prices, FRED data, or IFRS filings, they map to the same terms.

2. **CDE** is a boolean flag (`is_cde`) on a business term. It means "this term represents data that is critical to business operations and requires enhanced governance." The CDE catalog is not a separate artifact — it's a filtered view of the business glossary where `is_cde=true`.

3. **PII** is a boolean flag (`is_pii`) on a business term. It means "this term's data contains or derives from personally identifiable information." Currently all false for SEC financial data, but the architecture must support it for Phase 7 (insider ownership data).

4. **Logical model attributes** reference business terms. The model says "this column represents BT-022 (Revenue)" — not "this column is CDE-015."

### Success Criteria

- [ ] `concept_mappings` field rename: `cde_id` → `business_term_id`, `canonical_cde` → `business_term`
- [ ] `financial_facts` field rename: same two fields
- [ ] CDE catalog (31 entries) merged into business glossary as business terms with `is_cde: true`
- [ ] Business glossary terms gain `is_cde` and `is_pii` boolean flags
- [ ] All base zone Python code updated for field renames
- [ ] All DQ rules updated for field renames
- [ ] All tests pass with new field names
- [ ] All governance models updated (CDE Reference column → Business Term column, or attribute gets `is_cde` flag)
- [ ] `governance/cde-catalog.json` removed (replaced by glossary filter)
- [ ] CLAUDE.md rules updated
- [ ] Pipeline produces identical data with new field names on re-run

## 2. Technical Design

### 2.1 Field Renames

#### `base.concept_mappings`

| Old Field | New Field | Type | Notes |
|-----------|-----------|------|-------|
| `cde_id` | `business_term_id` | String | BT-XXX reference (null for unmapped Tier 3) |
| `canonical_cde` | `business_term` | String | Term name (null for unmapped Tier 3) |

All other fields unchanged.

#### `base.financial_facts`

| Old Field | New Field | Type | Notes |
|-----------|-----------|------|-------|
| `cde_id` | `business_term_id` | String | Denormalized from concept_mappings (null for Tier 3) |
| `canonical_cde` | `business_term` | String | Denormalized from concept_mappings (null for Tier 3) |

All other fields unchanged.

### 2.2 ID Mapping: CDE → Business Term

The 31 CDE entries need to map to business terms. Some already have BT equivalents:

#### Already Mapped (6 CDEs → existing BTs)

| CDE ID | CDE Name | Existing BT | Action |
|--------|----------|-------------|--------|
| CDE-001 | Central Index Key | BT-001 | Add `is_cde: true` to BT-001 |
| CDE-002 | SEC Accession Number | BT-002 | Add `is_cde: true` to BT-002 |
| CDE-003 | Legal Entity Name | BT-003 | Add `is_cde: true` to BT-003 |
| CDE-004 | SEC Filing Date | BT-006 | Add `is_cde: true` to BT-006 |
| CDE-005 | Canonical Entity Name | BT-005 | Add `is_cde: true` to BT-005 |
| CDE-006 | Entity Mapping ID | — | Becomes BT-026 with `is_cde: true` |

#### Financial CDEs → New Business Terms (25 CDEs → new BTs)

CDE-007 through CDE-031 become BT-026 through BT-050 (or whatever the next available IDs are). Three already have partial BT equivalents:

| CDE ID | CDE Name | Existing BT | Action |
|--------|----------|-------------|--------|
| CDE-007 | Total Assets | BT-024 | Add `is_cde: true` to BT-024 |
| CDE-015 | Revenue | BT-022 | Add `is_cde: true` to BT-022 |
| CDE-019 | Net Income | BT-023 | Add `is_cde: true` to BT-023 |

The remaining 22 financial CDEs (Total Liabilities, Equity, Cash, AR, Inventory, PP&E, Goodwill, Cost of Revenue, Gross Profit, Operating Income, Tax Expense, R&D, SGA, Operating CF, Investing CF, Financing CF, CapEx, EPS Basic, EPS Diluted, DPS, Comprehensive Income, Retained Earnings) become new business terms.

#### ID Translation Table

The `concept_mappings` and `financial_facts` tables currently store CDE-XXX IDs. These must be translated to BT-XXX IDs. The translation is deterministic and defined in config.

```python
CDE_TO_BT = {
    # Entity/Filing CDEs → existing BTs
    "CDE-001": "BT-001",  # CIK
    "CDE-002": "BT-002",  # Accession Number
    "CDE-003": "BT-003",  # Legal Entity Name
    "CDE-004": "BT-006",  # Filing Date
    "CDE-005": "BT-005",  # Canonical Entity Name (reusing BT-005 "Canonical Company Identity")
    "CDE-006": "BT-026",  # Entity Mapping ID (new BT)

    # Financial CDEs → existing or new BTs
    "CDE-007": "BT-024",  # Total Assets (existing)
    "CDE-008": "BT-027",  # Total Liabilities (new)
    "CDE-009": "BT-028",  # Total Stockholders Equity (new)
    "CDE-010": "BT-029",  # Cash and Cash Equivalents (new)
    "CDE-011": "BT-030",  # Accounts Receivable (new)
    "CDE-012": "BT-031",  # Inventory (new)
    "CDE-013": "BT-032",  # PP&E (new)
    "CDE-014": "BT-033",  # Goodwill (new)
    "CDE-015": "BT-022",  # Revenue (existing)
    "CDE-016": "BT-034",  # Cost of Revenue (new)
    "CDE-017": "BT-035",  # Gross Profit (new)
    "CDE-018": "BT-036",  # Operating Income (new)
    "CDE-019": "BT-023",  # Net Income (existing)
    "CDE-020": "BT-037",  # Income Tax Expense (new)
    "CDE-021": "BT-038",  # R&D Expense (new)
    "CDE-022": "BT-039",  # SGA Expense (new)
    "CDE-023": "BT-040",  # Operating Cash Flow (new)
    "CDE-024": "BT-041",  # Investing Cash Flow (new)
    "CDE-025": "BT-042",  # Financing Cash Flow (new)
    "CDE-026": "BT-043",  # Capital Expenditures (new)
    "CDE-027": "BT-044",  # EPS Basic (new)
    "CDE-028": "BT-045",  # EPS Diluted (new)
    "CDE-029": "BT-046",  # Dividends Per Share (new)
    "CDE-030": "BT-047",  # Comprehensive Income (new)
    "CDE-031": "BT-048",  # Retained Earnings (new)
}
```

### 2.3 Business Glossary Schema Change

Each term gains two new flags:

```json
{
    "term_id": "BT-022",
    "term": "Revenue",
    "definition": "Total revenue recognized from the sale of goods and services...",
    "source": "xbrl-taxonomy",
    "is_cde": true,
    "is_pii": false,
    "cde_rationale": "Revenue is the primary top-line metric for financial analysis. Critical for cross-company comparison, valuation ratios, and regulatory reporting.",
    "pii_rationale": null,
    ...
}
```

**`is_cde`** — Boolean. True means this term represents data that is critical to business operations and requires enhanced governance (data quality monitoring, lineage tracking, access controls, stewardship).

**`is_pii`** — Boolean. True means data associated with this term contains or derives from personally identifiable information. Triggers PII governance requirements (masking, retention policies, access restrictions, privacy impact assessment).

**`cde_rationale`** — String (nullable). WHY this term is/isn't a CDE. Required when `is_cde: true`.

**`pii_rationale`** — String (nullable). WHY this term is/isn't PII. Required when `is_pii: true`.

### 2.4 CDE Catalog Retirement

`governance/cde-catalog.json` is deleted. Its contents are merged into `governance/business-glossary.json`. The "CDE catalog" becomes a virtual concept: any tooling that needs "all CDEs" queries the glossary for `is_cde: true`.

### 2.5 Governance Model Updates

The logical model attribute tables currently have three governance columns:

```
| Attribute | ... | CDE Reference | Business Term | PII |
```

This becomes:

```
| Attribute | ... | Business Term | Is CDE | Is PII |
```

- **Business Term** — BT-XXX reference (the semantic meaning of this attribute)
- **Is CDE** — Boolean, derived from the business term's `is_cde` flag
- **Is PII** — Boolean, derived from the business term's `is_pii` flag

The "CDE Reference" column is removed — it was a separate ID that duplicated what the business term already provides.

### 2.6 CLAUDE.md Rule Updates

Current rule:
> Data models store governance metadata as **IDs only** (`BT-XXX`, `CDE-XXX`, PII flag) — never inline definitions.

New rule:
> Data models store governance metadata as **IDs only** (`BT-XXX`) with derived flags (`is_cde`, `is_pii`) — never inline definitions. CDE and PII status are properties of business terms, not separate catalogs.

Current rule:
> All model levels include `Business Term`, `CDE`, `PII` columns

New rule:
> All model levels include `Business Term`, `Is CDE`, `Is PII` columns. CDE and PII flags are derived from the referenced business term.

### 2.7 Files Impacted

#### Python Code (field renames)

| File | Changes |
|------|---------|
| `src/base/xbrl_tag_normalization/config.py` | `EXACT_MAPPINGS`, `PREFIX_RULES`, `PATTERN_RULES`: cde_id → business_term_id, update IDs from CDE-XXX to BT-XXX. `CDE_DEFINITIONS` → `BUSINESS_TERM_DEFINITIONS` (or remove and reference glossary). |
| `src/base/xbrl_tag_normalization/normalize.py` | All references to cde_id, canonical_cde → business_term_id, business_term |
| `src/base/xbrl_tag_normalization/schema.py` | Schema field names |
| `src/base/xbrl_tag_normalization/promote.py` | Field references |
| `src/base/xbrl_tag_normalization/cli.py` | Display labels, field references |
| `src/base/financial_facts_model/schema.py` | Schema field names |
| `src/base/financial_facts_model/model.py` | Field references in join/enrichment |
| `src/base/bitemporal/queries.py` | `cde_id` filter parameter → `business_term_id` |

#### DQ Rules (SQL field references)

| File | Changes |
|------|---------|
| `governance/dq-rules/base-tag-normalization.json` | SQL referencing cde_id → business_term_id |
| `governance/dq-rules/base-financial-facts-model.json` | SQL referencing cde_id → business_term_id |
| Any other DQ rule files with CDE references | Field renames in SQL |

#### Tests

| File | Changes |
|------|---------|
| `tests/base/xbrl_tag_normalization/test_normalize.py` | All assertions on cde_id/canonical_cde |
| `tests/base/xbrl_tag_normalization/test_promote.py` | Field names |
| `tests/base/financial_facts_model/test_model.py` | Field names in assertions |
| `tests/base/financial_facts_model/test_promote.py` | Field names |
| `tests/base/bitemporal/test_queries.py` | cde_id parameter |
| All other test files referencing these fields | Field renames |

#### Governance Artifacts

| File | Changes |
|------|---------|
| `governance/business-glossary.json` | Add `is_cde`, `is_pii`, `cde_rationale`, `pii_rationale` to all terms. Remove `cde_reference`. Merge 22 new financial terms from CDE catalog. |
| `governance/cde-catalog.json` | **DELETE** — merged into business glossary |
| `governance/models/*.md` (9 files) | CDE Reference → Is CDE, PII → Is PII. Update all attribute tables. |
| `governance/dq-scorecards/*.md` | Update any CDE field references |
| `governance/lineage/*.json` | Update field references |
| `governance/eda/*.md` | Update field references |
| `governance/audit-trail/*.json` | Update CDE references |
| `governance/insights/base-to-consumable-insights.md` | Update CDE references |
| `governance/data-dictionary.json` | Update field definitions |

#### Documentation

| File | Changes |
|------|---------|
| `CLAUDE.md` | Update rules about CDE, PII, model columns |
| `README.md` | Update any CDE references |
| `docs/specs/consumable-company-financials.md` | Rewrite to use business_term_id instead of cde_id |

### 2.8 What Does NOT Change

- Table grain definitions (grain fields don't include cde_id/canonical_cde)
- Supersession logic
- Amendment tracking
- Fiscal calendar
- Entity resolution
- The DQ framework itself
- The number of rules or their logic (just field names in SQL)
- Test count or test coverage

## 3. CLI Commands

No new CLI commands. Existing CLIs will work after field renames. Re-run the pipeline to rebuild tables with new field names:

```
python -m src.base.xbrl_tag_normalization.cli normalize
python -m src.base.xbrl_tag_normalization.cli approve
python -m src.base.financial_facts_model.cli all
python -m src.base.bitemporal.cli validate
python -m src.infra.dq_runner run
python -m src.infra.dq_runner scorecard
```

## 4. DQ Rules

No new DQ rules. Existing rules updated for field renames:

| Rule | Change |
|------|--------|
| BASE-TN-005 | `cde_id` → `business_term_id` in SQL |
| BASE-FM-* | Any SQL referencing `cde_id` or `canonical_cde` → new field names |

## 5. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Business terms as the hub, not CDEs | Business terms are source-agnostic. When we add stock prices or IFRS data, concepts map to the same terms. CDEs as the hub would require a new CDE for every new source — that's not how CDEs work. |
| CDE as a boolean flag on business terms | CDEs are a governance classification, not an entity. "Is this critical?" is a yes/no question about a term, not a separate catalog entry. |
| PII as a boolean flag on business terms | Same reasoning. "Does this contain PII?" is a property of the term. Currently all false — architecture must support Phase 7 insider data. |
| Rationale fields for CDE/PII flags | "Why is Revenue a CDE?" matters for governance audits. A boolean without rationale is checkbox compliance. |
| CDE-to-BT ID mapping in config | Deterministic, auditable translation. No ambiguity about which CDE became which BT. |
| Delete cde-catalog.json, don't archive | It's in git history. Keeping a dead file around creates confusion about source of truth. |
| Rename fields, not add aliases | Clean break. Aliases create "which one do I use?" confusion. The old field names were wrong — delete them. |

## 6. Governance Artifacts

- `governance/audit-trail/infra-governance-model-alignment.json` — Decision log for this refactor
- `governance/business-glossary.json` — Updated with merged terms + flags
- `governance/models/*.md` — Updated all 9 model documents
- All existing governance artifacts updated for field renames

## 7. Testing

No new test files. All existing tests updated for field renames. Full suite must pass after refactor.

Expected: 146 tests, same count as before.

## 8. Migration Path

1. Update `governance/business-glossary.json` first — merge CDE catalog, add flags
2. Delete `governance/cde-catalog.json`
3. Update all Python code (config, normalize, schema, model, promote, cli, queries)
4. Update all DQ rules (SQL field references)
5. Update all tests
6. Run full test suite — verify 146 tests pass
7. Update governance models (9 markdown files)
8. Update governance artifacts (lineage, audit trail, data dictionary, EDA, scorecards, insights)
9. Update CLAUDE.md, README.md, all specs
10. Delete existing Iceberg data (`data/` is gitignored, pipeline rebuilds)
11. Re-run full pipeline to produce tables with new field names
12. Re-run DQ rules and regenerate scorecards

## 9. Agent Workflow

This is an infrastructure refactor, not a zone pipeline spec. Simplified workflow:

1. @governance-reviewer — Pre-implementation review (verify the conceptual fix is correct)
2. @primary-agent — Execute the refactor
3. @dq-engineer — Re-run all DQ rules after refactor, verify all pass
4. @governance-reviewer — Post-implementation verify all artifacts are consistent
5. @staff-engineer — Final review

## 10. Dependencies

- All base zone specs (🟢 COMPLETE) — this modifies their artifacts
- Blocks all consumable zone specs — consumable must build on the corrected model
