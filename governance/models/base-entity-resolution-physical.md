## Physical Model: Entity Resolution
**Spec:** docs/specs/base-entity-resolution.md
**Date:** 2026-03-14
**Agent:** @semantic-modeler
**Mode:** Backfill (reverse-engineered from existing implementation)
**Stage:** Physical (3 of 3)
**Status:** PROPOSED
**Derived From (backfill):** Existing Iceberg tables + source code (documenting as-built)
**Source Files:** src/base/entity_resolution/schema.py, resolve.py, promote.py

```mermaid
erDiagram
    base_entity_mappings {
        STRING mapping_id PK "Stable ID (ER-001..) | EntityMapping.mapping_id"
        INTEGER cik "SEC company identifier | EntityMapping.cik"
        STRING canonical_name "Normalized display name | EntityMapping.canonical_name"
        STRING raw_entity_name "Original from SEC EDGAR | EntityMapping.raw_entity_name"
        STRING ticker "Stock ticker symbol | EntityMapping.ticker"
        STRING sic_code "Industry classification | EntityMapping.sic_code"
        STRING fiscal_year_end "MMDD format | EntityMapping.fiscal_year_end"
        DOUBLE confidence "Resolution confidence 0-1 | EntityMapping.confidence"
        STRING resolution_method "exact_cik_match or fuzzy | EntityMapping.resolution_method"
        STRING status "Approval status | EntityMapping.status"
        STRING resolved_by "Proposing agent | EntityMapping.resolved_by"
        STRING approved_by "Human or auto approver | EntityMapping.approved_by"
        TIMESTAMPTZ resolved_at "When proposed | EntityMapping.resolved_at"
        TIMESTAMPTZ approved_at "When approved | EntityMapping.approved_at"
    }
    base_entity_resolution_audit {
        STRING audit_id PK "UUID | EntityResolutionAudit.audit_id"
        STRING mapping_id FK "FK to entity_mappings | EntityResolutionAudit.mapping_id"
        STRING action "proposed/approved/rejected | EntityResolutionAudit.action"
        STRING actor "Who performed action | EntityResolutionAudit.actor"
        STRING reasoning "Decision explanation | EntityResolutionAudit.reasoning"
        STRING evidence "JSON supporting data | EntityResolutionAudit.evidence"
        DOUBLE confidence_at_action "Confidence at action time | EntityResolutionAudit.confidence_at_action"
        TIMESTAMPTZ timestamp "When action occurred | EntityResolutionAudit.timestamp"
    }
    base_entity_mappings ||--o{ base_entity_resolution_audit : "tracked by"
```

### Tables

#### base.entity_mappings
- **Grain:** One resolved entity — one row per unique CIK/company mapping
- **Partitioning:** None (20 rows)
- **Row Count:** 20

| Column | DuckDB Type | Nullable | Description | Source Mapping | Business Term | Term Def | CDE | PII |
|--------|------------|----------|-------------|----------------|---------------|----------|-----|-----|
| mapping_id | STRING | No | Stable ID (ER-001, ER-002...) | Generated sequentially | — | — | CDE-006 | None |
| cik | INTEGER | No | SEC Central Index Key | raw.xbrl_company_facts.cik | Central Index Key (CIK) | Unique numeric identifier assigned by SEC to every filing entity | CDE-001 | None |
| canonical_name | STRING | No | Normalized company display name | KNOWN_ENTITIES lookup or title-case heuristic | Canonical Company Identity | Normalized, human-approved company identity; single source of truth | CDE-005 | None |
| raw_entity_name | STRING | No | As-received from SEC EDGAR | raw.xbrl_company_facts.entity_name (most common per CIK) | Legal Entity Name | Official company name as registered with the SEC | CDE-003 | None |
| ticker | STRING | Yes | Primary stock ticker symbol | KNOWN_ENTITIES lookup | — | — | — | None |
| sic_code | STRING | Yes | Standard Industrial Classification | KNOWN_ENTITIES lookup | SIC Code | Four-digit SEC code classifying a company's primary business line | — | None |
| fiscal_year_end | STRING | Yes | MMDD format | KNOWN_ENTITIES lookup | — | — | — | None |
| confidence | DOUBLE | No | Resolution confidence (0.0-1.0) | 1.0 for exact CIK match, 0.5 for fuzzy | Confidence Score | Numeric value (0.0-1.0) representing pipeline certainty in a mapping | — | None |
| resolution_method | STRING | No | "exact_cik_match" or "fuzzy_name_normalize" | Determined by KNOWN_ENTITIES hit/miss | — | — | — | None |
| status | STRING | No | Always "approved" (post-gate) | Set on approval | — | — | — | None |
| resolved_by | STRING | No | Agent name | "@entity-resolver" | — | — | — | None |
| approved_by | STRING | Yes | Approver identity | "human:jeff" or "auto" | Human Approval Gate | Pipeline pause point for human review before proceeding | — | None |
| resolved_at | TIMESTAMPTZ | No | When mapping was proposed | Generated at resolve time | — | — | — | None |
| approved_at | TIMESTAMPTZ | Yes | When mapping was approved | Set on approval | — | — | — | None |

#### base.entity_resolution_audit
- **Grain:** One audit event per action on a mapping (append-only log)
- **Partitioning:** None (low volume)
- **Row Count:** ~40-60 (2-3 events per mapping)

| Column | DuckDB Type | Nullable | Description | Source Mapping | Business Term | Term Def | CDE | PII |
|--------|------------|----------|-------------|----------------|---------------|----------|-----|-----|
| audit_id | STRING | No | UUID primary key | Generated (uuid4) | — | — | — | None |
| mapping_id | STRING | No | FK to entity_mappings | From proposal | — | — | — | None |
| action | STRING | No | "proposed", "approved", "rejected", "updated" | Pipeline stage | — | — | — | None |
| actor | STRING | No | Who performed action | "@entity-resolver", "human:jeff", "auto" | — | — | — | None |
| reasoning | STRING | No | Why decision was made | Generated explanation | — | — | — | None |
| evidence | STRING | No | JSON string with supporting data | Serialized evidence dict | — | — | — | None |
| confidence_at_action | DOUBLE | No | Confidence at time of action | From proposal | Confidence Score | Numeric value (0.0-1.0) representing pipeline certainty in a mapping | — | None |
| timestamp | TIMESTAMPTZ | No | When action occurred | Generated at action time | — | — | — | None |

### Physical Design Decisions
- **No partitioning** — both tables are small (20 entities, ~60 audit rows). Scan-all is fine.
- **STRING for mapping_id** — uses "ER-NNN" format for human readability in staging/approval workflow.
- **evidence stored as JSON string** — avoids nested types in Iceberg. Parsed by consumers as needed.
- **Audit table is append-only** — no updates or deletes. Full history of every decision.
- **TIMESTAMPTZ for all timestamps** — UTC, timezone-aware for cross-system consistency.
