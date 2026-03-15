## Logical Model: Financial Facts Model
**Spec:** docs/specs/base-financial-facts-model.md
**Date:** 2026-03-14
**Agent:** @semantic-modeler
**Mode:** Backfill (reverse-engineered from existing implementation)
**Stage:** Logical (2 of 3)
**Status:** APPROVED
**Derived From (backfill):** governance/models/base-financial-facts-model-physical.md + source code

```mermaid
erDiagram
    Entity {
        identifier entity_id PK
        identifier cik
        text canonical_name
        text ticker
        text sic_code
        text fiscal_year_end
    }
    Concept {
        identifier mapping_id PK
        text concept
        identifier business_term_id
        text business_term
        text financial_statement
        text category
        number tier
    }
    FinancialFact {
        identifier fact_id PK
        identifier entity_id FK
        text concept FK
        text taxonomy
        text unit
        number val
        date start_date
        date end_date
        number fiscal_year
        text fiscal_period
        number calendar_year
        number calendar_quarter
        identifier accession_number
        text form
        date filed_date
        boolean is_amendment
        boolean is_superseded
        identifier superseded_by
    }
    FiscalCalendar {
        identifier calendar_id PK
        identifier cik FK
        identifier entity_id FK
        number fiscal_year
        text fiscal_period
        date period_start
        date period_end
        number duration_days
        boolean is_annual
    }
    AmendmentTracking {
        identifier tracking_id PK
        identifier cik
        text concept
        text unit
        date end_date
        identifier original_accession
        number original_val
        identifier amendment_accession
        number amendment_val
        number val_change
        number val_change_pct
    }
    Entity ||--o{ FinancialFact : "reported by"
    Concept ||--o{ FinancialFact : "classified as"
    Entity ||--o{ FiscalCalendar : "has periods"
    FinancialFact ||--o{ AmendmentTracking : "superseded by"
```

> **†** Entities marked with † have a matching business glossary term

### Entities

#### FinancialFact
- **Primary Key:** fact_id (deterministic hash of grain)
- **Natural Key:** (cik, concept, unit, start_date, end_date, accession_number)
- **Description:** A single reported financial value from an SEC filing, enriched with entity and concept metadata. The central fact table of the Base zone.

| Attribute | Domain | Nullable | Description | Business Term | Is CDE | Is PII |
|-----------|--------|----------|-------------|--------------|--------|--------|
| fact_id | Identifier | No | Deterministic hash of grain fields | — | No | No |
| entity_id | Identifier | No | Reference to resolved entity | — | No | No |
| cik | Identifier | No | SEC company identifier | BT-001 | Yes | No |
| canonical_name | Text | No | Normalized company name (denormalized) | BT-005 | Yes | No |
| ticker | Text | Yes | Stock ticker (denormalized) | — | No | No |
| concept | Text | No | XBRL concept name | BT-009 | No | No |
| cde_id | Identifier | Yes | Canonical CDE reference (null Tier 3) | BT-013 | Yes | No |
| canonical_cde | Text | Yes | CDE name (null Tier 3, denormalized) | BT-013 | No | No |
| financial_statement | Text (enum) | No | Statement classification (denormalized) | BT-021 | No | No |
| category | Text | No | Subcategory (denormalized) | — | No | No |
| tier | Number (1-3) | No | Mapping quality tier (denormalized) | BT-015 | No | No |
| taxonomy | Text | No | XBRL taxonomy source | BT-020 | No | No |
| unit | Text | No | Measurement unit | — | No | No |
| val | Number | No | Reported value | — | No | No |
| start_date | Date | Yes | Period start (null for instant facts) | — | No | No |
| end_date | Date | No | Period end | — | No | No |
| fiscal_year | Number | No | Fiscal year of reporting | BT-018 | Yes | No |
| fiscal_period | Text (enum) | No | FY, Q1, Q2, Q3, Q4 | BT-018 | Yes | No |
| fiscal_year_end | Text (MMDD) | Yes | Company's fiscal year end (denormalized) | — | No | No |
| calendar_year | Number | No | Calendar year of end_date (derived) | — | No | No |
| calendar_quarter | Number (1-4) | No | Calendar quarter of end_date (derived) | — | No | No |
| accession_number | Identifier | No | SEC filing identifier | BT-002 | Yes | No |
| form | Text | No | Filing form type | — | No | No |
| filed_date | Date | No | When filed with SEC | BT-006 | Yes | No |
| is_amendment | Boolean | No | Filing is an amendment (derived) | BT-007 | No | No |
| is_superseded | Boolean | No | Later filing supersedes this one (derived) | BT-012 | No | No |
| superseded_by | Identifier | Yes | Accession of superseding filing | BT-012 | No | No |

#### FiscalCalendar
- **Primary Key:** calendar_id (deterministic hash of grain)
- **Natural Key:** (cik, fiscal_year, fiscal_period)
- **Description:** Temporal dimension mapping fiscal periods to calendar dates for each company. Built from observed filing data, not theoretical calendars.

| Attribute | Domain | Nullable | Description | Business Term | Is CDE | Is PII |
|-----------|--------|----------|-------------|--------------|--------|--------|
| calendar_id | Identifier | No | Deterministic hash of grain | — | No | No |
| cik | Identifier | No | Company | BT-001 | Yes | No |
| entity_id | Identifier | No | Reference to resolved entity | — | No | No |
| fiscal_year | Number | No | Fiscal year | BT-018 | Yes | No |
| fiscal_period | Text (enum) | No | FY, Q1, Q2, Q3, Q4 | BT-018 | Yes | No |
| fiscal_year_end | Text (MMDD) | No | Company's fiscal year end | — | No | No |
| period_start | Date | Yes | Earliest observed start_date | — | No | No |
| period_end | Date | No | Latest observed end_date | — | No | No |
| calendar_year | Number | No | Calendar year of period_end (derived) | — | No | No |
| calendar_quarter | Number (1-4) | No | Calendar quarter of period_end (derived) | — | No | No |
| duration_days | Number | Yes | Period length in days (derived) | — | No | No |
| is_annual | Boolean | No | Whether this is a full-year period (derived) | — | No | No |

#### AmendmentTracking
- **Primary Key:** tracking_id
- **Description:** Records each supersession event where an amended filing replaces an original. One row per (original → amendment) pair.

| Attribute | Domain | Nullable | Description | Business Term | Is CDE | Is PII |
|-----------|--------|----------|-------------|--------------|--------|--------|
| tracking_id | Identifier | No | Unique event ID | — | No | No |
| cik | Identifier | No | Company | BT-001 | Yes | No |
| concept | Text | No | XBRL concept that was amended | BT-009 | No | No |
| unit | Text | No | Measurement unit | — | No | No |
| start_date | Date | Yes | Period start of amended fact | — | No | No |
| end_date | Date | No | Period end of amended fact | — | No | No |
| original_accession | Identifier | No | Superseded filing | BT-002 | Yes | No |
| original_filed_date | Date | No | When original was filed | BT-006 | Yes | No |
| original_val | Number | No | Original reported value | — | No | No |
| amendment_accession | Identifier | No | Superseding filing | BT-002 | Yes | No |
| amendment_filed_date | Date | No | When amendment was filed | BT-006 | Yes | No |
| amendment_val | Number | No | Corrected value | — | No | No |
| val_change | Number | No | Absolute change (derived) | — | No | No |
| val_change_pct | Number | Yes | Percentage change (derived, null if div/0) | — | No | No |
| amendment_form | Text | No | Form type of amendment | BT-007 | No | No |

#### Entity (reference — defined in base-entity-resolution)
- See governance/models/base-entity-resolution-logical.md

#### Concept (reference — defined in base-xbrl-tag-normalization)
- See governance/models/base-xbrl-tag-normalization-logical.md

### Relationships
| Parent Entity | Child Entity | FK Field | Cardinality | On Delete |
|--------------|-------------|----------|-------------|-----------|
| Entity | FinancialFact | entity_id | 1:N | Restrict |
| Concept | FinancialFact | concept | 1:N | Restrict |
| Entity | FiscalCalendar | cik + entity_id | 1:N | Restrict |
| FinancialFact | AmendmentTracking | supersession grain | 1:N (sparse) | Cascade |

### Normalization Decisions
- **FinancialFact is intentionally denormalized** — canonical_name, ticker, canonical_cde, financial_statement, category, tier, and fiscal_year_end are all copied from parent entities. This is a deliberate analytical optimization: the fact table is the primary query surface, and avoiding joins at query time is worth the storage cost at 547K rows.
- **FiscalCalendar uses observed dates, not computed dates** — period_start and period_end come from actual filing data (min/max of observed dates), not from fiscal_year_end arithmetic. This handles companies that report outside expected windows.
- **AmendmentTracking stores both original and amendment values** — denormalized to avoid joining back to financial_facts. Makes it self-contained for amendment analysis.
- **Entity and Concept are cross-references** — defined in their own specs' logical models. The financial_facts_model uses them as parent dimensions.

### Grain Definitions
- **FinancialFact:** One row per (cik, concept, unit, start_date, end_date, accession_number). Preserves all filing versions — amendments create new rows, not updates.
- **FiscalCalendar:** One row per (cik, fiscal_year, fiscal_period). ~80 periods per company.
- **AmendmentTracking:** One row per supersession pair. Sparse — only exists where amendments were filed.

### Alternatives Considered
- **Normalized fact table (no denormalization)** — rejected. Would require 3-way join (entity + concept + fact) for every query. At this scale the join cost is trivial, but the ergonomic cost is real. Every consumer would need to know the join keys.
- **Separate dimension for filing metadata** — rejected. Accession number, form, and filed_date are part of the fact grain, not a separate dimension. A filing can contain many facts, but facts aren't reused across filings.
- **Computing fiscal calendar from fiscal_year_end math** — rejected. Real-world fiscal calendars have irregularities. Observed dates are ground truth.
- **Storing amendment_tracking as a view over financial_facts** — considered but rejected. Precomputing makes amendment analysis faster and the tracking table serves as an explicit governance artifact showing what changed.
