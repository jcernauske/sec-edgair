# Base Zone: Entity Resolution

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
| Primary Agent | @entity-resolver |
| Blocked By | — |
| Depends On | `raw-ingest-xbrl-company-facts` (🟢 COMPLETE) |

---

## Claude Code Prompt

```
Implement the following plan:

# Plan: `base-entity-resolution` Spec + Implementation

Phase 1 (Raw Zone) is complete. 104,810 XBRL facts from 3 companies sit in
raw.xbrl_company_facts. Phase 2 starts with entity resolution — mapping CIKs
to canonical company identities with a human approval gate.

Agent workflow:
1. @governance-reviewer — Pre-implementation review
2. @entity-resolver — Build resolve, staging, promote, CLI modules
3. @lineage-tracker — Log raw.xbrl_company_facts → base.entity_mappings lineage
4. @dq-engineer — DQ rules BASE-ER-001 through BASE-ER-005
5. @cde-tagger — Map canonical_name, mapping_id as new CDEs
6. @doc-generator — Data dictionary for both tables
7. @governance-reviewer — Post-implementation verification
8. @staff-engineer — Final quality review
```

---

## 1. Feature Description

### Problem Statement

SEC EDGAR identifies companies by CIK (Central Index Key), but entity names vary in format across filings: "Apple Inc.", "JPMorgan Chase & Co", "MICROSOFT CORPORATION". Before any downstream analytics, we need a canonical mapping from CIK to a normalized company identity.

Critically, auditors need confidence that entity resolution decisions are logged, auditable, transparent, and reviewable. AI agents proposing mappings is fine — but a human approval gate must exist for production use.

### User Story

As a data engineer building the SEC EDGAIR pipeline, I want CIKs mapped to canonical company identities with full audit trails so that downstream consumers can join on a stable entity identifier and auditors can verify every resolution decision.

### Success Criteria

- [ ] `resolve.py` reads raw.xbrl_company_facts, groups by CIK, and proposes mappings with confidence scores
- [ ] Proposed mappings are written to `governance/entity-resolution/proposed-mappings.json` for human review
- [ ] CLI supports `status`, `approve`, `reject` commands
- [ ] `promote.py` writes approved mappings to `base.entity_mappings` Iceberg table
- [ ] Every decision is logged in `base.entity_resolution_audit` Iceberg table
- [ ] 👁️ Confidence < 0.7 always requires human approval regardless of toggle
- [ ] All 5 DQ rules pass at 100%
- [ ] All governance artifacts produced

## 2. Technical Design

### 2.1 Iceberg Tables

**`base.entity_mappings`** — canonical mapping table:

| Field | Type | Required | Purpose |
|-------|------|----------|---------|
| mapping_id | String | Yes | Stable ID (ER-001, ER-002...) |
| cik | Integer | Yes | SEC CIK number |
| canonical_name | String | Yes | Normalized display name |
| raw_entity_name | String | Yes | As-received from SEC EDGAR |
| ticker | String | No | Primary ticker symbol |
| sic_code | String | No | Standard Industrial Classification |
| fiscal_year_end | String | No | MMDD format |
| confidence | Double | Yes | 0.0-1.0 resolution confidence |
| resolution_method | String | Yes | "exact_cik_match", "fuzzy_name_match", etc. |
| status | String | Yes | "approved", "pending", "rejected" |
| resolved_by | String | Yes | "@entity-resolver" or agent name |
| approved_by | String | No | "human:jeff" or "auto" |
| resolved_at | Timestamptz | Yes | When proposed |
| approved_at | Timestamptz | No | When approved/rejected |

**`base.entity_resolution_audit`** — every decision with reasoning:

| Field | Type | Required | Purpose |
|-------|------|----------|---------|
| audit_id | String | Yes | UUID per entry |
| mapping_id | String | Yes | FK to entity_mappings |
| action | String | Yes | "proposed", "approved", "rejected", "updated" |
| actor | String | Yes | "@entity-resolver", "human:jeff", "auto" |
| reasoning | String | Yes | Why this decision was made |
| evidence | String | Yes | JSON string — source citations |
| confidence_at_action | Double | Yes | Confidence at time of action |
| timestamp | Timestamptz | Yes | When this action occurred |

### 2.2 👁️ Human Approval Gate

**Toggle:** `REQUIRE_HUMAN_APPROVAL = True` in config. When True, proposed mappings pause for review. When False, auto-promote (dev/demo mode).

**Hard floor:** Mappings with `confidence < 0.7` ALWAYS pause regardless of toggle.

**Flow:**
```
resolve.py reads raw.xbrl_company_facts
    → groups by CIK, extracts entity names, computes confidence
    → writes proposed-mappings.json to governance/entity-resolution/

If require_human_approval=True:  STOP, print review instructions
If require_human_approval=False AND confidence >= 0.7:  auto-promote
If confidence < 0.7:  ALWAYS STOP regardless of toggle

Human reviews via CLI:
    cli.py status                        → show pending
    cli.py approve                       → approve all pending
    cli.py approve ER-001 ER-002         → approve specific
    cli.py reject ER-003 --reason "..."  → reject with reason

promote.py writes approved mappings → Iceberg tables
    → entity_mappings (status=approved)
    → entity_resolution_audit (action=approved, actor=human:jeff)
    → archives staging file with timestamp
```

### 2.3 Module Structure

```
src/base/
    __init__.py
    entity_resolution/
        __init__.py
        config.py        # Toggle, paths, thresholds
        schema.py         # Both Iceberg schemas
        resolve.py        # Core: read raw, propose mappings with confidence
        staging.py        # Write/read proposed-mappings.json, gate logic
        promote.py        # Move approved → Iceberg tables + audit
        cli.py            # CLI: resolve, status, approve, reject
```

## 3. Testing Strategy

All offline, using tmp_path fixtures:

| Test File | What |
|-----------|------|
| test_resolve.py | Resolution logic: 3 known CIKs → 3 mappings, confidence 1.0 |
| test_staging.py | Write/read staging JSON, toggle behavior, low-confidence override |
| test_promote.py | Iceberg roundtrip: approve → write → read back → verify |
| test_cli.py | CLI approve/reject commands, status display |
| test_gate_behavior.py | Toggle True stops, False auto-promotes, <0.7 always stops |

## 4. DQ Rules

| Rule | Type | Threshold |
|------|------|-----------|
| BASE-ER-001 | Every CIK in raw has an approved mapping | 100% |
| BASE-ER-002 | No duplicate CIKs in approved mappings | 100% |
| BASE-ER-003 | All confidence scores 0.0-1.0 | 100% |
| BASE-ER-004 | Approved mappings have non-null approved_by/approved_at | 100% |
| BASE-ER-005 | Every audit entry has valid mapping_id | 100% |

## 5. Lineage

*Placeholder — to be filled by @lineage-tracker*

## 6. CDE Mappings

*Placeholder — to be filled by @cde-tagger*

## 7. Data Dictionary

*Placeholder — to be filled by @doc-generator*

## 8. Pre-Implementation Review

*Placeholder — to be filled by @governance-reviewer*

## 9. Post-Implementation Review

*Placeholder — to be filled by @governance-reviewer*

## 10. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| CLI for approval, not JSON editing | Auditable, idempotent, prevents syntax errors |
| Confidence < 0.7 always pauses | Hard floor auditors can trust — auto-promote can't bypass risky matches |
| Shared catalog, `base` namespace | Same `data/catalog/catalog.db`, different namespace. Existing pattern. |
| Warehouse at `data/base/iceberg_warehouse` | Mirrors raw zone pattern |
| Archive staging files with timestamp | Preserves proposal history without querying Iceberg |
| Status field on entity_mappings | Downstream queries filter `WHERE status = 'approved'` |
| Rejected stays out of entity_mappings | Downstream consumers query without noise. Full rejection history lives in audit table |

## 11. Agent Workflow

1. @governance-reviewer — Pre-implementation review
2. @entity-resolver — Build resolve, staging, promote, CLI modules
3. @lineage-tracker — Log raw.xbrl_company_facts → base.entity_mappings lineage
4. @dq-engineer — DQ rules BASE-ER-001 through BASE-ER-005
5. @cde-tagger — Map canonical_name, mapping_id as new CDEs
6. @doc-generator — Data dictionary for both tables
7. @governance-reviewer — Post-implementation verification
8. @staff-engineer — Final quality review

## 12. Governance Artifacts

- `governance/lineage/base-entity-resolution.json` — OpenLineage
- `governance/audit-trail/base-entity-resolution.json` — Schema decisions
- `governance/cde-catalog.json` — Add CDE-005, CDE-006
- `governance/data-dictionary.json` — Add both new tables
- `governance/dq-scorecards/base-entity-resolution-scorecard.md` — DQ results
- `governance/entity-resolution/proposed-mappings.json` — Staging area

## 13. Dependencies

- `raw-ingest-xbrl-company-facts` (🟢 COMPLETE) — source data
- `infra-setup-duckdb-iceberg` (🟢 COMPLETE) — Iceberg infrastructure
