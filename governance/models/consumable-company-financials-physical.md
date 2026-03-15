## Physical Model: Company Financials
**Spec:** docs/specs/consumable-company-financials.md
**Date:** 2026-03-14
**Agent:** @semantic-modeler
**Mode:** Greenfield (new consumable zone table)
**Stage:** Physical (3 of 3)
**Status:** APPROVED
**Derived From:** governance/models/consumable-company-financials-logical.md

```mermaid
erDiagram
    base_entity_mappings {
        STRING mapping_id PK "Stable ID | EntityMapping.mapping_id"
        INTEGER cik "SEC company identifier | EntityMapping.cik"
        STRING canonical_name "Normalized name | EntityMapping.canonical_name"
        STRING ticker "Stock ticker | EntityMapping.ticker"
        STRING sic_code "SIC industry code | EntityMapping.sic_code"
        STRING fiscal_year_end "MMDD | EntityMapping.fiscal_year_end"
    }
    base_financial_facts {
        STRING fact_id PK "SHA-256 of grain | FinancialFact.fact_id"
        INTEGER cik "SEC company ID | FinancialFact.cik"
        STRING business_term_id "BT-XXX reference | FinancialFact.business_term_id"
        STRING concept "XBRL concept | FinancialFact.concept"
        DOUBLE val "Reported value | FinancialFact.val"
        STRING unit "USD or USD/shares | FinancialFact.unit"
        INTEGER tier "Match tier 1/2/3 | FinancialFact.tier"
        BOOLEAN is_superseded "Superseded flag | FinancialFact.is_superseded"
    }
    consumable_company_financials {
        STRING record_id PK "SHA-256 of grain fields | CompanyFinancials.record_id"
        INTEGER cik "SEC company identifier | CompanyFinancials.cik"
        STRING entity_id "Resolved entity ref | CompanyFinancials.entity_id"
        STRING ticker "Stock ticker (denorm) | CompanyFinancials.ticker"
        STRING canonical_name "Normalized name (denorm) | CompanyFinancials.canonical_name"
        STRING sector "SIC-to-sector (derived) | CompanyFinancials.sector"
        STRING business_term_id "BT-XXX reference | CompanyFinancials.business_term_id"
        STRING business_term "Human-readable name (denorm) | CompanyFinancials.business_term"
        STRING financial_statement "Statement type (denorm) | CompanyFinancials.financial_statement"
        STRING category "Subcategory (denorm) | CompanyFinancials.category"
        DOUBLE val "Selected financial value | CompanyFinancials.val"
        STRING unit "USD or USD/shares | CompanyFinancials.unit"
        STRING source_concept "Selected XBRL concept | CompanyFinancials.source_concept"
        INTEGER fiscal_year "Fiscal year | CompanyFinancials.fiscal_year"
        STRING fiscal_period "FY/Q1/Q2/Q3 | CompanyFinancials.fiscal_period"
        STRING fiscal_year_end "MMDD (denorm) | CompanyFinancials.fiscal_year_end"
        DATE period_end_date "Reporting period end | CompanyFinancials.period_end_date"
        INTEGER calendar_year "Calendar year of end | CompanyFinancials.calendar_year"
        INTEGER calendar_quarter "Calendar quarter of end | CompanyFinancials.calendar_quarter"
        STRING accession_number "Source filing ID | CompanyFinancials.accession_number"
        DATE filed_date "SEC filing date | CompanyFinancials.filed_date"
        INTEGER companies_reporting "Coverage count | CompanyFinancials.companies_reporting"
        TIMESTAMPTZ promoted_at "When written to consumable | CompanyFinancials.promoted_at"
        DATE load_date "System date tracking | CompanyFinancials.load_date"
    }
    base_entity_mappings ||--o{ consumable_company_financials : "cik → sector, fiscal_year_end"
    base_financial_facts ||--o{ consumable_company_financials : "filtered + collision-resolved"
```

### Tables

#### consumable.company_financials
- **Grain:** One row per (cik, business_term_id, fiscal_year, fiscal_period) -- after concept collision resolution and supersession/unit filtering
- **Partitioning:** None (estimated ~27K rows, sub-second full scan)
- **Estimated Row Count:** ~27,000

| Column | Iceberg Type | Nullable | Description | Source Mapping | Business Term | Is CDE | Is PII |
|--------|-------------|----------|-------------|----------------|---------------|--------|--------|
| record_id | STRING | No | SHA-256 hash of (cik, business_term_id, fiscal_year, fiscal_period), truncated to 16 chars | Computed | -- | No | No |
| cik | INTEGER | No | SEC Central Index Key | base.financial_facts.cik | BT-001 | Yes | No |
| entity_id | STRING | No | FK to entity_mappings.mapping_id | base.financial_facts.entity_id | -- | No | No |
| ticker | STRING | Yes | Stock ticker symbol | base.financial_facts.ticker | -- | No | No |
| canonical_name | STRING | No | Normalized company name | base.financial_facts.canonical_name | BT-005 | Yes | No |
| sector | STRING | No | Industry sector | Derived: SIC_TO_SECTOR[entity_mappings.sic_code] | BT-049 | No | No |
| business_term_id | STRING | No | Canonical business term reference | base.financial_facts.business_term_id | BT-013 | No | No |
| business_term | STRING | No | Human-readable business term name | base.financial_facts.business_term | BT-013 | No | No |
| financial_statement | STRING | No | Statement classification | base.financial_facts.financial_statement | BT-021 | No | No |
| category | STRING | No | Subcategory within statement | base.financial_facts.category | -- | No | No |
| val | DOUBLE | No | Financial value from primary concept selection | base.financial_facts.val (collision-resolved) | -- | No | No |
| unit | STRING | No | Measurement unit (USD or USD/shares) | base.financial_facts.unit (filtered to primary) | -- | No | No |
| source_concept | STRING | No | XBRL concept selected by collision resolution | base.financial_facts.concept (selected) | BT-009 | No | No |
| fiscal_year | INTEGER | No | Fiscal year of reporting | base.financial_facts.fiscal_year | BT-018 | Yes | No |
| fiscal_period | STRING | No | FY, Q1, Q2, Q3 | base.financial_facts.fiscal_period | BT-018 | Yes | No |
| fiscal_year_end | STRING | Yes | Company fiscal year end (MMDD) | base.entity_mappings.fiscal_year_end | -- | No | No |
| period_end_date | DATE | No | End date of reporting period | base.financial_facts.end_date | -- | No | No |
| calendar_year | INTEGER | No | Calendar year of period_end_date | base.financial_facts.calendar_year | -- | No | No |
| calendar_quarter | INTEGER | No | Calendar quarter of period_end_date | base.financial_facts.calendar_quarter | -- | No | No |
| accession_number | STRING | No | Source SEC filing accession number | base.financial_facts.accession_number | BT-002 | Yes | No |
| filed_date | DATE | No | Date source filing was submitted | base.financial_facts.filed_date | BT-006 | Yes | No |
| companies_reporting | INTEGER | No | Distinct CIKs reporting this business term for this fiscal_period type | Computed: COUNT(DISTINCT cik) per (business_term_id, fiscal_period) | BT-050 | No | No |
| promoted_at | TIMESTAMPTZ | No | When written to consumable zone | Generated at promote time | -- | No | No |
| load_date | DATE | No | System date for load tracking | Generated at promote time | -- | No | No |

### Physical Design Decisions
- **Intentionally denormalized** -- canonical_name, ticker, sector, business_term, financial_statement, category, fiscal_year_end, and companies_reporting are all copied or derived. The consumable zone is the primary query surface for analysts and LLMs; avoiding joins is the entire point.
- **record_id is a truncated SHA-256** -- deterministic, collision-resistant at 16 hex chars for this data volume (~27K rows). Enables idempotent re-runs.
- **Concept collision resolved before write** -- each (cik, business_term_id, fiscal_year, fiscal_period) group has exactly one row. The source_concept column records which XBRL concept was selected.
- **No partitioning** -- data volume doesn't justify it. Full scans are sub-second.
- **sector is derived at build time** -- computed from entity_mappings.sic_code via a static SIC_TO_SECTOR lookup. Not stored in any source table.
- **companies_reporting is a computed aggregate** -- count of distinct CIKs per (business_term_id, fiscal_period) across all years. Denormalized per row so consumers see coverage without a second query.
- **Unit filtering applied before write** -- only the primary unit per business term category is kept (USD for dollar amounts, USD/shares for per-share metrics).
