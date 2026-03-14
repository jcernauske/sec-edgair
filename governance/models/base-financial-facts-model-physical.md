## Physical Model: Financial Facts Model
**Spec:** docs/specs/base-financial-facts-model.md
**Date:** 2026-03-14
**Agent:** @semantic-modeler
**Mode:** Backfill (reverse-engineered from existing implementation)
**Stage:** Physical (3 of 3)
**Status:** APPROVED
**Derived From (backfill):** Existing Iceberg tables + source code (documenting as-built)
**Source Files:** src/base/financial_facts_model/schema.py, model.py, fiscal_calendar.py, amendments.py, promote.py

```mermaid
erDiagram
    base_entity_mappings {
        STRING mapping_id PK "Stable ID | EntityMapping.mapping_id"
        INTEGER cik "SEC company identifier | EntityMapping.cik"
        STRING canonical_name "Normalized name | EntityMapping.canonical_name"
    }
    base_concept_mappings {
        STRING mapping_id PK "Stable ID | ConceptMapping.mapping_id"
        STRING concept "XBRL concept | ConceptMapping.concept"
        STRING cde_id "CDE reference | ConceptMapping.cde_id"
        STRING canonical_cde "CDE name | ConceptMapping.canonical_cde"
    }
    base_financial_facts {
        STRING fact_id PK "SHA-256 of grain fields | FinancialFact.fact_id"
        STRING entity_id FK "FK to entity_mappings | FinancialFact.entity_id"
        INTEGER cik "SEC company ID (denorm) | FinancialFact.cik"
        STRING canonical_name "Company name (denorm) | FinancialFact.canonical_name"
        STRING ticker "Stock ticker (denorm) | FinancialFact.ticker"
        STRING concept "XBRL concept name | FinancialFact.concept"
        STRING cde_id FK "CDE reference (denorm) | FinancialFact.cde_id"
        STRING canonical_cde "CDE name (denorm) | FinancialFact.canonical_cde"
        STRING financial_statement "Statement type (denorm) | FinancialFact.financial_statement"
        STRING category "Subcategory (denorm) | FinancialFact.category"
        INTEGER tier "Match tier (denorm) | FinancialFact.tier"
        STRING taxonomy "XBRL taxonomy source | FinancialFact.taxonomy"
        STRING unit "USD/shares/USD-per-share | FinancialFact.unit"
        DOUBLE val "Reported value | FinancialFact.val"
        DATE start_date "Period start (null=instant) | FinancialFact.start_date"
        DATE end_date "Period end | FinancialFact.end_date"
        INTEGER fiscal_year "Fiscal year | FinancialFact.fiscal_year"
        STRING fiscal_period "FY/Q1/Q2/Q3/Q4 | FinancialFact.fiscal_period"
        STRING fiscal_year_end "MMDD (denorm) | FinancialFact.fiscal_year_end"
        INTEGER calendar_year "Derived from end_date | FinancialFact.calendar_year"
        INTEGER calendar_quarter "Derived from end_date | FinancialFact.calendar_quarter"
        STRING accession_number "SEC filing ID | FinancialFact.accession_number"
        STRING form "10-K/10-Q/10-K-A | FinancialFact.form"
        DATE filed_date "SEC filing date | FinancialFact.filed_date"
        BOOLEAN is_amendment "Form ends in /A (derived) | FinancialFact.is_amendment"
        BOOLEAN is_superseded "Later filing exists (derived) | FinancialFact.is_superseded"
        STRING superseded_by "Superseding accession | FinancialFact.superseded_by"
        TIMESTAMPTZ promoted_at "When written to base | FinancialFact.promoted_at"
    }
    base_fiscal_calendar {
        STRING calendar_id PK "SHA-256 of grain | FiscalCalendar.calendar_id"
        INTEGER cik "Company | FiscalCalendar.cik"
        STRING entity_id FK "FK to entity_mappings | FiscalCalendar.entity_id"
        INTEGER fiscal_year "e.g. 2024 | FiscalCalendar.fiscal_year"
        STRING fiscal_period "FY/Q1/Q2/Q3/Q4 | FiscalCalendar.fiscal_period"
        STRING fiscal_year_end "MMDD from entity | FiscalCalendar.fiscal_year_end"
        DATE period_start "Earliest observed start | FiscalCalendar.period_start"
        DATE period_end "Latest observed end | FiscalCalendar.period_end"
        INTEGER calendar_year "Calendar year of end | FiscalCalendar.calendar_year"
        INTEGER calendar_quarter "Calendar quarter of end | FiscalCalendar.calendar_quarter"
        INTEGER duration_days "Period length (derived) | FiscalCalendar.duration_days"
        BOOLEAN is_annual "fiscal_period is FY | FiscalCalendar.is_annual"
    }
    base_amendment_tracking {
        STRING tracking_id PK "UUID | AmendmentTracking.tracking_id"
        INTEGER cik "Company | AmendmentTracking.cik"
        STRING concept "Amended XBRL concept | AmendmentTracking.concept"
        STRING unit "Measurement unit | AmendmentTracking.unit"
        DATE start_date "Period start | AmendmentTracking.start_date"
        DATE end_date "Period end | AmendmentTracking.end_date"
        STRING original_accession "Superseded filing | AmendmentTracking.original_accession"
        DATE original_filed_date "When original filed | AmendmentTracking.original_filed_date"
        DOUBLE original_val "Original value | AmendmentTracking.original_val"
        STRING amendment_accession "Superseding filing | AmendmentTracking.amendment_accession"
        DATE amendment_filed_date "When amendment filed | AmendmentTracking.amendment_filed_date"
        DOUBLE amendment_val "Corrected value | AmendmentTracking.amendment_val"
        DOUBLE val_change "Absolute change (derived) | AmendmentTracking.val_change"
        DOUBLE val_change_pct "Pct change (derived) | AmendmentTracking.val_change_pct"
        STRING amendment_form "10-K-A or 10-Q-A | AmendmentTracking.amendment_form"
        TIMESTAMPTZ detected_at "When detected | AmendmentTracking.detected_at"
    }
    base_entity_mappings ||--o{ base_financial_facts : "entity_id"
    base_concept_mappings ||--o{ base_financial_facts : "concept"
    base_financial_facts }o--|| base_fiscal_calendar : "cik + fiscal_year + fiscal_period"
    base_financial_facts ||--o{ base_amendment_tracking : "supersession pairs"
```

### Tables

#### base.financial_facts
- **Grain:** One fact observation per (cik, concept, unit, start_date, end_date, accession_number) — preserves all filing versions including amendments
- **Partitioning:** None
- **Estimated Row Count:** ~547,000

| Column | DuckDB Type | Nullable | Description | Source Mapping | Business Term | Term Def | CDE | PII |
|--------|------------|----------|-------------|----------------|---------------|----------|-----|-----|
| fact_id | STRING | No | SHA-256 hash of grain fields, truncated to 16 chars | Computed: SHA-256(cik, concept, unit, start_date, end_date, accession_number)[:16] | — | — | — | None |
| entity_id | STRING | No | FK to entity_mappings.mapping_id | Looked up by CIK | — | — | — | None |
| cik | INTEGER | No | SEC Central Index Key | raw.xbrl_company_facts.cik | Central Index Key (CIK) | Unique SEC-assigned numeric identifier for filing entities | CDE-001 | None |
| canonical_name | STRING | No | Normalized company name | entity_mappings.canonical_name | Canonical Company Identity | Normalized, human-approved company name as single source of truth | CDE-005 | None |
| ticker | STRING | Yes | Stock ticker | entity_mappings.ticker | — | — | — | None |
| concept | STRING | No | XBRL concept name | raw.xbrl_company_facts.concept | XBRL Concept | Specific financial metric tag from an XBRL taxonomy | — | None |
| cde_id | STRING | Yes | CDE catalog reference (null for Tier 3) | concept_mappings.cde_id | Canonical CDE | One of 25 standardized financial data elements for cross-company comparison | CDE-007..031 (dynamic) | None |
| canonical_cde | STRING | Yes | CDE name (null for Tier 3) | concept_mappings.canonical_cde | Canonical CDE | One of 25 standardized financial data elements for cross-company comparison | CDE-007..031 (dynamic) | None |
| financial_statement | STRING | No | Statement classification | concept_mappings.financial_statement | Financial Statement | Category of financial reporting (Balance Sheet, Income, Cash Flow, etc.) | — | None |
| category | STRING | No | Subcategory | concept_mappings.category | — | — | — | None |
| tier | INTEGER | No | Mapping tier (1/2/3) | concept_mappings.tier | Tier | Classification of match quality in tag normalization (1/2/3) | — | None |
| taxonomy | STRING | No | XBRL taxonomy (us-gaap, dei, etc.) | raw.xbrl_company_facts.taxonomy | XBRL Taxonomy | Structured classification system defining financial reporting concepts | — | None |
| unit | STRING | No | Measurement unit (USD, shares, USD/shares) | raw.xbrl_company_facts.unit | — | — | — | None |
| val | DOUBLE | No | Reported fact value | raw.xbrl_company_facts.val | — | — | — | None |
| start_date | DATE | Yes | Period start (null for instant facts) | raw.xbrl_company_facts.start_date | — | — | — | None |
| end_date | DATE | No | Period end | raw.xbrl_company_facts.end_date | — | — | — | None |
| fiscal_year | INTEGER | No | Fiscal year | raw.xbrl_company_facts.fiscal_year | Fiscal Period | Company reporting period identified by fiscal year and period type | CDE-005 | None |
| fiscal_period | STRING | No | FY, Q1, Q2, Q3, Q4 | raw.xbrl_company_facts.fiscal_period | Fiscal Period | Company reporting period identified by fiscal year and period type | CDE-006 | None |
| fiscal_year_end | STRING | Yes | MMDD format | entity_mappings.fiscal_year_end | — | — | — | None |
| calendar_year | INTEGER | No | Calendar year of end_date | Computed: end_date.year | — | — | — | None |
| calendar_quarter | INTEGER | No | Calendar quarter of end_date | Computed: (end_date.month - 1) / 3 + 1 | — | — | — | None |
| accession_number | STRING | No | SEC accession number | raw.xbrl_company_facts.accession_number | Accession Number | Unique identifier for each SEC EDGAR filing submission | CDE-002 | None |
| form | STRING | No | Filing form type | raw.xbrl_company_facts.form | — | — | — | None |
| filed_date | DATE | No | SEC filing date | raw.xbrl_company_facts.filed_date | Filing Date | Date the filing was officially submitted to and accepted by the SEC | CDE-004 | None |
| is_amendment | BOOLEAN | No | Form ends in "/A" | Computed: form.endswith("/A") | Amendment | Revised SEC filing that corrects or updates a prior submission | — | None |
| is_superseded | BOOLEAN | No | Later filing exists for same supersession grain | Computed by _apply_supersession() | Supersession | Later filing replaces earlier one for same company/concept/period | — | None |
| superseded_by | STRING | Yes | Accession number of superseding filing | Set by _apply_supersession() | Supersession | Later filing replaces earlier one for same company/concept/period | — | None |
| promoted_at | TIMESTAMPTZ | No | When written to base zone | Generated at promote time | — | — | — | None |

#### base.fiscal_calendar
- **Grain:** One row per (cik, fiscal_year, fiscal_period)
- **Partitioning:** None
- **Estimated Row Count:** ~1,600 (20 companies x ~80 periods)

| Column | DuckDB Type | Nullable | Description | Source Mapping | Business Term | Term Def | CDE | PII |
|--------|------------|----------|-------------|----------------|---------------|----------|-----|-----|
| calendar_id | STRING | No | SHA-256 hash of (cik, fiscal_year, fiscal_period) | Computed | — | — | — | None |
| cik | INTEGER | No | Company | raw.xbrl_company_facts.cik | Central Index Key (CIK) | Unique SEC-assigned numeric identifier for filing entities | CDE-001 | None |
| entity_id | STRING | No | FK to entity_mappings | Looked up by CIK | — | — | — | None |
| fiscal_year | INTEGER | No | e.g., 2024 | raw.xbrl_company_facts.fiscal_year | Fiscal Period | Company reporting period identified by fiscal year and period type | CDE-005 | None |
| fiscal_period | STRING | No | FY, Q1, Q2, Q3, Q4 | raw.xbrl_company_facts.fiscal_period | Fiscal Period | Company reporting period identified by fiscal year and period type | CDE-006 | None |
| fiscal_year_end | STRING | No | MMDD from entity_mappings | entity_mappings.fiscal_year_end | — | — | — | None |
| period_start | DATE | Yes | Earliest start_date observed for this period | Computed: min(start_date) | — | — | — | None |
| period_end | DATE | No | Latest end_date observed for this period | Computed: max(end_date) | — | — | — | None |
| calendar_year | INTEGER | No | Calendar year of period_end | Computed: period_end.year | — | — | — | None |
| calendar_quarter | INTEGER | No | Calendar quarter of period_end | Computed: (period_end.month - 1) / 3 + 1 | — | — | — | None |
| duration_days | INTEGER | Yes | period_end - period_start in days | Computed (null if period_start is null) | — | — | — | None |
| is_annual | BOOLEAN | No | True if fiscal_period == "FY" | Computed | — | — | — | None |

#### base.amendment_tracking
- **Grain:** One row per supersession pair (original filing → amending filing)
- **Partitioning:** None
- **Estimated Row Count:** Sparse (only amendments exist)

| Column | DuckDB Type | Nullable | Description | Source Mapping | Business Term | Term Def | CDE | PII |
|--------|------------|----------|-------------|----------------|---------------|----------|-----|-----|
| tracking_id | STRING | No | UUID primary key | Generated (uuid4) | — | — | — | None |
| cik | INTEGER | No | Company | From financial_facts | Central Index Key (CIK) | Unique SEC-assigned numeric identifier for filing entities | CDE-001 | None |
| concept | STRING | No | XBRL concept amended | From financial_facts | XBRL Concept | Specific financial metric tag from an XBRL taxonomy | — | None |
| unit | STRING | No | Measurement unit | From financial_facts | — | — | — | None |
| start_date | DATE | Yes | Period start of amended fact | From financial_facts | — | — | — | None |
| end_date | DATE | No | Period end of amended fact | From financial_facts | — | — | — | None |
| original_accession | STRING | No | First filing (superseded) | From superseded fact | Accession Number | Unique identifier for each SEC EDGAR filing submission | CDE-002 | None |
| original_filed_date | DATE | No | When original was filed | From superseded fact | Filing Date | Date the filing was officially submitted to and accepted by the SEC | CDE-004 | None |
| original_val | DOUBLE | No | Original reported value | From superseded fact | — | — | — | None |
| amendment_accession | STRING | No | Amending filing | From superseding fact | Accession Number | Unique identifier for each SEC EDGAR filing submission | CDE-002 | None |
| amendment_filed_date | DATE | No | When amendment was filed | From superseding fact | Filing Date | Date the filing was officially submitted to and accepted by the SEC | CDE-004 | None |
| amendment_val | DOUBLE | No | New reported value | From superseding fact | — | — | — | None |
| val_change | DOUBLE | No | amendment_val - original_val | Computed | — | — | — | None |
| val_change_pct | DOUBLE | Yes | Percentage change (null if original_val = 0) | Computed | — | — | — | None |
| amendment_form | STRING | No | "10-K/A", "10-Q/A" | From superseding fact | Amendment | Revised SEC filing that corrects or updates a prior submission | — | None |
| detected_at | TIMESTAMPTZ | No | When detected by pipeline | Generated at detection time | — | — | — | None |

### Physical Design Decisions
- **Denormalized financial_facts** — entity and concept metadata is duplicated into the fact table to avoid joins at query time. This is intentional: the fact table is the primary query surface, and 547K rows with 28 columns is trivially scannable.
- **fact_id is a truncated SHA-256** — deterministic, collision-resistant at 16 hex chars for this data volume. Enables idempotent re-runs.
- **Supersession is precomputed** — is_superseded and superseded_by are set during build, not at query time. Consumers can filter `WHERE NOT is_superseded` for latest values.
- **No partitioning on any table** — data volume doesn't justify it. Full scans are sub-second.
- **fiscal_calendar uses observed boundaries** — period_start and period_end come from actual data, not from fiscal_year_end math. This handles edge cases where companies report outside expected windows.
- **amendment_tracking is sparse** — most facts are not amended. Table only contains rows where supersession was detected.
