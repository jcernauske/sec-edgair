## Physical Model: XBRL Tag Normalization
**Spec:** docs/specs/base-xbrl-tag-normalization.md
**Date:** 2026-03-14
**Agent:** @semantic-modeler
**Mode:** Backfill (reverse-engineered from existing implementation)
**Stage:** Physical (3 of 3)
**Status:** PROPOSED
**Derived From (backfill):** Existing Iceberg tables + source code (documenting as-built)
**Source Files:** src/base/xbrl_tag_normalization/schema.py, normalize.py, promote.py

```mermaid
erDiagram
    base_concept_mappings {
        STRING mapping_id PK
        STRING concept
        STRING canonical_cde
        STRING cde_id
        STRING financial_statement
        STRING category
        INTEGER tier
        DOUBLE confidence
        STRING mapping_method
        STRING status
        STRING mapped_by
        TIMESTAMPTZ mapped_at
    }
    base_tag_normalization_audit {
        STRING audit_id PK
        STRING mapping_id FK
        STRING action
        STRING actor
        STRING reasoning
        STRING evidence
        DOUBLE confidence_at_action
        TIMESTAMPTZ timestamp
    }
    base_concept_mappings ||--o{ base_tag_normalization_audit : "tracked by"
```

### Tables

#### base.concept_mappings
- **Grain:** One row per distinct us-gaap XBRL concept
- **Partitioning:** None
- **Row Count:** 3,285

| Column | DuckDB Type | Nullable | Description | Source Mapping |
|--------|------------|----------|-------------|----------------|
| mapping_id | STRING | No | Stable ID (TN-0001...) | Generated sequentially |
| concept | STRING | No | Raw us-gaap XBRL concept name | raw.xbrl_company_facts distinct concepts (us-gaap taxonomy only) |
| canonical_cde | STRING | Yes | Mapped CDE name (null for Tier 3) | CDE_DEFINITIONS lookup via tier matching |
| cde_id | STRING | Yes | CDE catalog reference CDE-007..CDE-031 (null for Tier 3) | From EXACT_MAPPINGS, PREFIX_RULES, or PATTERN_RULES |
| financial_statement | STRING | No | balance_sheet, income_statement, cash_flow, per_share, other | From matching rule or HEURISTIC_CATEGORIES |
| category | STRING | No | Subcategory (revenue, assets, eps, tax...) | From matching rule or HEURISTIC_CATEGORIES |
| tier | INTEGER | No | 1 (exact), 2 (prefix/pattern), 3 (unmapped) | Determined by matching engine |
| confidence | DOUBLE | No | 1.0 / 0.7 / 0.6 / 0.0 by tier | Fixed per tier level |
| mapping_method | STRING | No | exact_match, prefix_match, pattern_match, unmapped | From matching engine |
| status | STRING | No | "approved" (Tier 1+2), "unmapped" (Tier 3) | Set by approval gate |
| mapped_by | STRING | No | "@tag-normalizer" | Fixed |
| mapped_at | TIMESTAMPTZ | No | When mapping was proposed | Generated at normalize time |

#### base.tag_normalization_audit
- **Grain:** One audit event per action on a concept mapping (append-only log)
- **Partitioning:** None
- **Row Count:** ~6,500 (2 events per mapping: proposed + approved/classified)

| Column | DuckDB Type | Nullable | Description | Source Mapping |
|--------|------------|----------|-------------|----------------|
| audit_id | STRING | No | UUID primary key | Generated (uuid4) |
| mapping_id | STRING | No | FK to concept_mappings | From proposal |
| action | STRING | No | "proposed", "approved", "rejected", "classified_unmapped" | Pipeline stage |
| actor | STRING | No | Who performed action | "@tag-normalizer", "human:jeff", "auto" |
| reasoning | STRING | No | Why decision was made | Generated explanation with match details |
| evidence | STRING | No | JSON string (fact_count, company_count) | Serialized from raw data analysis |
| confidence_at_action | DOUBLE | No | Confidence at time of action | From proposal |
| timestamp | TIMESTAMPTZ | No | When action occurred | Generated at action time |

### Physical Design Decisions
- **No partitioning** — 3,285 rows scans instantly.
- **Tiered confidence is fixed, not computed** — Tier 1 = 1.0, Tier 2 prefix = 0.7, Tier 2 pattern = 0.6, Tier 3 = 0.0. Simplifies reasoning about match quality.
- **canonical_cde and cde_id are nullable** — Tier 3 unmapped concepts have no CDE assignment. This is intentional; 2,943 of 3,285 concepts are long-tail tags that don't map to any of the 25 canonical CDEs.
- **Reuses entity_resolution staging module** — the approval gate logic (staging.py) is shared, not duplicated.
- **evidence stored as JSON string** — contains fact_count and company_count for coverage analysis.
