# Base Zone: XBRL Tag Normalization

## Status: 🟠 IMPLEMENTATION

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
| Zone | Base |
| Primary Agent | @tag-normalizer |
| Blocked By | — |
| Depends On | `raw-ingest-xbrl-company-facts` (🟢 COMPLETE), `base-entity-resolution` (🟠 IMPLEMENTATION) |

---

## Claude Code Prompt

```
Implement the following plan:

# Plan: `base-xbrl-tag-normalization` Spec + Implementation

Phase 2 (Base Zone) is in progress. Entity resolution is done — 20 companies resolved
to canonical identities. The next task is XBRL tag normalization: mapping 3,285 distinct
us-gaap XBRL concepts to canonical Critical Data Elements (CDEs).

Agent workflow:
1. @governance-reviewer — Pre-implementation review
2. @tag-normalizer — Build normalize, promote, CLI modules
3. @lineage-tracker — Log raw.xbrl_company_facts → base.concept_mappings lineage
4. @dq-engineer — DQ rules BASE-TN-001 through BASE-TN-005
5. @cde-tagger — Map 25 new financial CDEs (CDE-007 through CDE-031)
6. @doc-generator — Data dictionary for both tables
7. @governance-reviewer — Post-implementation verification
8. @staff-engineer — Final quality review
```

---

## 1. Feature Description

### Problem Statement

SEC EDGAR raw data contains 3,285 distinct us-gaap XBRL concept names across 547,398 facts from 20 companies. Companies use different tags for the same financial metric — `us-gaap:Revenues`, `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax`, `us-gaap:SalesRevenueNet` all mean "Revenue." Without normalization, cross-company financial comparison is impossible.

### User Story

As a data engineer building the SEC EDGAIR pipeline, I want every XBRL concept classified and mapped to a canonical CDE so that downstream consumers can compare financial metrics across companies without knowing which specific XBRL tag each company used.

### Success Criteria

- [ ] `normalize.py` reads raw.xbrl_company_facts, extracts 3,285 us-gaap concepts, classifies each into tiers
- [ ] 25 new CDEs defined (CDE-007 through CDE-031) covering core financial statements
- [ ] 37 exact-match mappings for highest-frequency concepts
- [ ] Prefix and pattern rules catch common variants
- [ ] All 3,285 concepts written to `base.concept_mappings` Iceberg table
- [ ] Tier 3 (unmapped) bypasses 👁️ human approval gate
- [ ] Coverage >= 80% of raw fact instances
- [ ] All 5 DQ rules pass at 100%
- [ ] All governance artifacts produced

## 2. Technical Design

### 2.1 Iceberg Tables

**`base.concept_mappings`** — XBRL concept to CDE mapping:

| Field | Type | Required | Purpose |
|-------|------|----------|---------|
| mapping_id | String | Yes | Stable ID (TN-0001...) |
| concept | String | Yes | Raw us-gaap concept name |
| canonical_cde | String | No | CDE name (null for unmapped) |
| cde_id | String | No | CDE catalog reference (null for unmapped) |
| financial_statement | String | Yes | balance_sheet, income_statement, cash_flow, per_share, other |
| category | String | Yes | Specific grouping: revenue, assets, eps, etc. |
| tier | Integer | Yes | 1 (core), 2 (common), 3 (unmapped) |
| confidence | Double | Yes | 0.0-1.0 |
| mapping_method | String | Yes | exact_match, prefix_match, pattern_match, unmapped |
| status | String | Yes | approved, pending, unmapped |
| mapped_by | String | Yes | "@tag-normalizer" |
| mapped_at | Timestamptz | Yes | When proposed |

**`base.tag_normalization_audit`** — same 8-field schema as entity_resolution_audit:

| Field | Type | Required | Purpose |
|-------|------|----------|---------|
| audit_id | String | Yes | UUID per entry |
| mapping_id | String | Yes | FK to concept_mappings |
| action | String | Yes | proposed, approved, rejected, classified_unmapped |
| actor | String | Yes | @tag-normalizer, human:jeff, auto |
| reasoning | String | Yes | Why this decision was made |
| evidence | String | Yes | JSON string — concept stats |
| confidence_at_action | Double | Yes | Confidence at time of action |
| timestamp | Timestamptz | Yes | When this action occurred |

### 2.2 Tiered Mapping Engine

| Tier | Method | Confidence | Expected Count |
|------|--------|-----------|----------------|
| 1 | Exact match against curated EXACT_MAPPINGS | 1.0 | ~37 concepts |
| 2 | Prefix match + pattern regex | 0.6-0.7 | ~150 concepts |
| 3 | Unmapped — tagged with heuristic category | 0.0 | ~3,000 concepts |

Priority cascade: exact match → prefix match → pattern match → unmapped.
First match wins within each tier.

### 2.3 25 New CDEs

| Category | CDEs |
|----------|------|
| **Balance Sheet (8)** | CDE-007 Total Assets, CDE-008 Total Liabilities, CDE-009 Total Stockholders Equity, CDE-010 Cash & Equivalents, CDE-011 Accounts Receivable, CDE-012 Inventory, CDE-013 PP&E, CDE-014 Goodwill |
| **Income Statement (8)** | CDE-015 Revenue, CDE-016 Cost of Revenue, CDE-017 Gross Profit, CDE-018 Operating Income, CDE-019 Net Income, CDE-020 Income Tax Expense, CDE-021 R&D Expense, CDE-022 SG&A Expense |
| **Cash Flow (4)** | CDE-023 Operating CF, CDE-024 Investing CF, CDE-025 Financing CF, CDE-026 Capital Expenditures |
| **Per-Share (3)** | CDE-027 EPS Basic, CDE-028 EPS Diluted, CDE-029 Dividends Per Share |
| **Other (2)** | CDE-030 Comprehensive Income, CDE-031 Retained Earnings |

### 2.4 👁️ Human Approval Gate

Reuses `src/base/entity_resolution/staging.py` — same interface:
- `REQUIRE_HUMAN_APPROVAL = True` in config
- `CONFIDENCE_FLOOR = 0.7`
- Tier 1+2 proposals go through staging/approval
- **Tier 3 bypasses the gate** — written directly as `status="unmapped"`

### 2.5 Module Structure

```
src/base/xbrl_tag_normalization/
    __init__.py
    config.py        # CDE_DEFINITIONS, EXACT_MAPPINGS, PREFIX_RULES, PATTERN_RULES
    schema.py         # CONCEPT_MAPPINGS_SCHEMA, TAG_NORMALIZATION_AUDIT_SCHEMA
    normalize.py      # Core: scan raw concepts, classify, compute coverage
    promote.py        # Write approved + unmapped to Iceberg
    cli.py            # normalize, status, approve, reject, coverage
```

No staging.py — reusing entity_resolution's.

## 3. Testing Strategy

| Test File | Tests | What |
|-----------|-------|------|
| test_normalize.py | 18 | Exact/prefix/pattern match, unmapped, heuristic categories, coverage |
| test_promote.py | 5 | Iceberg roundtrip, audit entries, archiving |
| test_cli.py | 4 | CLI status, approve, reject |
| **Total** | **27** | |

No staging tests — reusing already-tested module.

## 4. DQ Rules

| Rule | Type | Threshold |
|------|------|-----------|
| BASE-TN-001 | Every Tier 1 concept has approved mapping | 100% |
| BASE-TN-002 | No concept maps to multiple CDEs | 100% |
| BASE-TN-003 | All confidence scores 0.0-1.0 | 100% |
| BASE-TN-004 | Coverage >= 80% of raw fact instances | 80% |
| BASE-TN-005 | Approved mappings have valid cde_id | 100% |

## 5. CLI Commands

```
python -m src.base.xbrl_tag_normalization.cli normalize   # scan + classify + stage
python -m src.base.xbrl_tag_normalization.cli status      # show pending tier 1+2
python -m src.base.xbrl_tag_normalization.cli approve     # approve all/specific
python -m src.base.xbrl_tag_normalization.cli reject TN-0042 --reason "..."
python -m src.base.xbrl_tag_normalization.cli coverage    # % facts covered
```

## 6. Lineage

See `governance/lineage/base-tag-normalization.json`.

## 7. CDE Mappings

See `governance/cde-catalog.json` — CDE-007 through CDE-031.

## 8. Data Dictionary

See `governance/data-dictionary.json` — base.concept_mappings, base.tag_normalization_audit.

## 9. Pre-Implementation Review

*Placeholder — to be filled by @governance-reviewer*

## 10. Post-Implementation Review

*Placeholder — to be filled by @governance-reviewer*

## 11. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| 25 CDEs, not more | Covers core financial statements. Sector-specific CDEs are Consumable zone |
| All 3,285 concepts get a row | Complete census enables coverage analysis and future extension |
| Primary financial statement only | Depreciation on income_statement, not cash_flow. Cross-statement is downstream |
| All revenue variants → one CDE | Gross/net/segment distinctions are Consumable zone |
| Reuse entity_resolution.staging | Same interface (dicts with status/mapping_id/confidence). DRY > copy-paste |
| Tier 3 bypasses approval gate | Unmapped concepts don't need human review — explicitly "not yet mapped" |
| Heuristic categories for unmapped | Even unmapped concepts get rough financial_statement/category via substring matching |

## 12. Agent Workflow

1. @governance-reviewer — Pre-implementation review
2. @tag-normalizer — Build normalize, promote, CLI modules
3. @lineage-tracker — Log raw.xbrl_company_facts → base.concept_mappings lineage
4. @dq-engineer — DQ rules BASE-TN-001 through BASE-TN-005
5. @cde-tagger — Map 25 new financial CDEs
6. @doc-generator — Data dictionary for both tables
7. @governance-reviewer — Post-implementation verification
8. @staff-engineer — Final quality review

## 13. Governance Artifacts

- `governance/lineage/base-tag-normalization.json` — OpenLineage
- `governance/audit-trail/base-tag-normalization.json` — Design decisions
- `governance/dq-rules/base-tag-normalization.json` — 5 DQ rules
- `governance/dq-scorecards/base-tag-normalization-scorecard.md` — DQ results
- `governance/cde-catalog.json` — CDE-007 through CDE-031 (25 new)
- `governance/data-dictionary.json` — 2 new table definitions

## 14. Dependencies

- `raw-ingest-xbrl-company-facts` (🟢 COMPLETE) — source data
- `base-entity-resolution` (🟠 IMPLEMENTATION) — entity context
- `infra-setup-duckdb-iceberg` (🟢 COMPLETE) — Iceberg infrastructure
