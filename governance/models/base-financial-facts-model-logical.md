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
        identifier cde_id
        text canonical_cde
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

### Entities

#### FinancialFact
- **Primary Key:** fact_id (deterministic hash of grain)
- **Natural Key:** (cik, concept, unit, start_date, end_date, accession_number)
- **Description:** A single reported financial value from an SEC filing, enriched with entity and concept metadata. The central fact table of the Base zone.

| Attribute | Domain | Nullable | Description | CDE Reference |
|-----------|--------|----------|-------------|---------------|
| fact_id | Identifier | No | Deterministic hash of grain fields | — |
| entity_id | Identifier | No | Reference to resolved entity | — |
| cik | Identifier | No | SEC company identifier | CDE-001 |
| canonical_name | Text | No | Normalized company name (denormalized) | CDE-003 |
| ticker | Text | Yes | Stock ticker (denormalized) | — |
| concept | Text | No | XBRL concept name | — |
| cde_id | Identifier | Yes | Canonical CDE reference (null Tier 3) | CDE-007..CDE-031 |
| canonical_cde | Text | Yes | CDE name (null Tier 3, denormalized) | — |
| financial_statement | Text (enum) | No | Statement classification (denormalized) | — |
| category | Text | No | Subcategory (denormalized) | — |
| tier | Number (1-3) | No | Mapping quality tier (denormalized) | — |
| taxonomy | Text | No | XBRL taxonomy source | — |
| unit | Text | No | Measurement unit | — |
| val | Number | No | Reported value | — |
| start_date | Date | Yes | Period start (null for instant facts) | — |
| end_date | Date | No | Period end | — |
| fiscal_year | Number | No | Fiscal year of reporting | CDE-005 |
| fiscal_period | Text (enum) | No | FY, Q1, Q2, Q3, Q4 | CDE-006 |
| fiscal_year_end | Text (MMDD) | Yes | Company's fiscal year end (denormalized) | — |
| calendar_year | Number | No | Calendar year of end_date (derived) | — |
| calendar_quarter | Number (1-4) | No | Calendar quarter of end_date (derived) | — |
| accession_number | Identifier | No | SEC filing identifier | CDE-002 |
| form | Text | No | Filing form type | — |
| filed_date | Date | No | When filed with SEC | CDE-004 |
| is_amendment | Boolean | No | Filing is an amendment (derived) | — |
| is_superseded | Boolean | No | Later filing supersedes this one (derived) | — |
| superseded_by | Identifier | Yes | Accession of superseding filing | — |

#### FiscalCalendar
- **Primary Key:** calendar_id (deterministic hash of grain)
- **Natural Key:** (cik, fiscal_year, fiscal_period)
- **Description:** Temporal dimension mapping fiscal periods to calendar dates for each company. Built from observed filing data, not theoretical calendars.

| Attribute | Domain | Nullable | Description | CDE Reference |
|-----------|--------|----------|-------------|---------------|
| calendar_id | Identifier | No | Deterministic hash of grain | — |
| cik | Identifier | No | Company | CDE-001 |
| entity_id | Identifier | No | Reference to resolved entity | — |
| fiscal_year | Number | No | Fiscal year | CDE-005 |
| fiscal_period | Text (enum) | No | FY, Q1, Q2, Q3, Q4 | CDE-006 |
| fiscal_year_end | Text (MMDD) | No | Company's fiscal year end | — |
| period_start | Date | Yes | Earliest observed start_date | — |
| period_end | Date | No | Latest observed end_date | — |
| calendar_year | Number | No | Calendar year of period_end (derived) | — |
| calendar_quarter | Number (1-4) | No | Calendar quarter of period_end (derived) | — |
| duration_days | Number | Yes | Period length in days (derived) | — |
| is_annual | Boolean | No | Whether this is a full-year period (derived) | — |

#### AmendmentTracking
- **Primary Key:** tracking_id
- **Description:** Records each supersession event where an amended filing replaces an original. One row per (original → amendment) pair.

| Attribute | Domain | Nullable | Description | CDE Reference |
|-----------|--------|----------|-------------|---------------|
| tracking_id | Identifier | No | Unique event ID | — |
| cik | Identifier | No | Company | CDE-001 |
| concept | Text | No | XBRL concept that was amended | — |
| unit | Text | No | Measurement unit | — |
| start_date | Date | Yes | Period start of amended fact | — |
| end_date | Date | No | Period end of amended fact | — |
| original_accession | Identifier | No | Superseded filing | CDE-002 |
| original_filed_date | Date | No | When original was filed | CDE-004 |
| original_val | Number | No | Original reported value | — |
| amendment_accession | Identifier | No | Superseding filing | CDE-002 |
| amendment_filed_date | Date | No | When amendment was filed | CDE-004 |
| amendment_val | Number | No | Corrected value | — |
| val_change | Number | No | Absolute change (derived) | — |
| val_change_pct | Number | Yes | Percentage change (derived, null if div/0) | — |
| amendment_form | Text | No | Form type of amendment | — |

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
