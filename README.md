# SEC EDGAIR

AI agent pipeline that takes raw SEC EDGAR XBRL data and delivers it as a clean, tested, governed, semantically meaningful, AI-ready data product.

**Stack:** Python 3.11+, DuckDB + Apache Iceberg, Claude Code with specialized agents

**Status:** Phase 2 — Base Zone (in progress)

## Background

**SEC** (Securities and Exchange Commission) is the US government agency that regulates public companies. **EDGAR** (Electronic Data Gathering, Analysis, and Retrieval) is the SEC's public database where every public company files their financial reports — quarterly earnings (10-Q), annual reports (10-K), insider trades, etc.

**XBRL** (eXtensible Business Reporting Language) is a standardized format for tagging financial data so computers can read it. Instead of a PDF that says "Revenue: $50B", XBRL tags that number with metadata — concept name, currency, reporting period, filing entity. Every fact gets a machine-readable label.

Without XBRL, comparing Apple's revenue to Microsoft's means reading two different PDFs with different layouts. With XBRL, you can programmatically pull every public company's revenue into a table in seconds.

This project takes that raw XBRL data and pipes it through a 4-zone pipeline (Raw → Base → Consumable → AI-Ready) so it ends up clean, normalized, and ready for AI models to reason over — turning government financial filings into structured data an LLM can actually use.

## Architecture

```
Raw → Base → Consumable → AI-Ready
```

Each zone is governed by AI agents that produce lineage, data quality rules, CDE mappings, and audit trails as a byproduct of the transformation work. Every spec follows a mandatory 8-agent pipeline ending with @staff-engineer review.

## What's Built

### Phase 0: Infrastructure

| Spec | Status | What It Does |
|------|--------|-------------|
| `infra-create-agent-definitions` | Complete | Defined 10 specialized Claude Code agents (@governance-reviewer, @entity-resolver, @data-profiler, @lineage-tracker, @dq-engineer, @cde-tagger, @doc-generator, @pii-scanner, @temporal-modeler, @tag-normalizer) |
| `infra-validate-agent-definitions` | Complete | Smoke-tested all agent definitions |
| `infra-fix-agent-definitions` | Complete | Post-validation remediation |
| `infra-create-staff-engineer-agent` | Complete | Added @staff-engineer as the final quality gate in every spec pipeline |
| `infra-setup-duckdb-iceberg` | Complete | DuckDB + Apache Iceberg local read/write with PyIceberg SqlCatalog (SQLite-backed). Shared catalog at `data/catalog/catalog.db`, zone-separated warehouses. Time-travel via PyIceberg scan (DuckDB's native iceberg_scan doesn't reliably support snapshots). |

### Phase 1: Raw Zone

| Spec | Status | What It Does |
|------|--------|-------------|
| `raw-ingest-xbrl-company-facts` | Complete | Ingests XBRL Company Facts from SEC EDGAR for 20 companies. Supports both per-company API calls and bulk ZIP download. Flattens deeply nested JSON into a 19-column flat Iceberg table (`raw.xbrl_company_facts`). **547,398 facts** across 20 companies, 3,285 distinct XBRL concepts. |
| `raw-profile-classify-company-facts` | Complete | Statistical profiling of all 19 fields (cardinality, null rates, distributions). PII scanning (none found — all public SEC data). Data classification with sensitivity tags. |

### Phase 2: Base Zone

| Spec | Status | What It Does |
|------|--------|-------------|
| `base-entity-resolution` | Complete | Maps SEC EDGAR CIKs to canonical company identities. 20 companies resolved via exact CIK match (confidence 1.0). Human approval gate with CLI (`approve`, `reject`, `status`). Produces `base.entity_mappings` + `base.entity_resolution_audit` Iceberg tables. |
| `base-xbrl-tag-normalization` | Complete | Maps 3,285 us-gaap XBRL concepts to 25 canonical financial CDEs via tiered matching engine. **Tier 1** (37 exact matches, confidence 1.0): core concepts like Revenue, Assets, Net Income. **Tier 2** (305 prefix/pattern matches, confidence 0.6-0.7): known variants. **Tier 3** (2,943 unmapped, confidence 0.0): long-tail concepts tagged with heuristic categories. Produces `base.concept_mappings` + `base.tag_normalization_audit` Iceberg tables. Reuses entity_resolution staging module for human approval gate. |

### Phases 3-4: Consumable & AI-Ready

Not yet started.

## Data Pipeline Summary

```
SEC EDGAR API/Bulk ZIP
    ↓
raw.xbrl_company_facts          547,398 facts, 20 companies, 19 columns
    ↓
base.entity_mappings            20 CIK → canonical company identity mappings
base.concept_mappings           3,285 XBRL concept → CDE classifications
    ↓
(consumable zone — next)
    ↓
(ai-ready zone — future)
```

## Governance

Every transformation produces governance artifacts automatically:

- **31 CDEs** defined in `governance/cde-catalog.json` (6 entity/filing + 25 financial)
- **5 Iceberg tables** documented in `governance/data-dictionary.json`
- **OpenLineage** events in `governance/lineage/`
- **DQ rules** with scorecards in `governance/dq-rules/` and `governance/dq-scorecards/`
- **Audit trails** capturing every design decision in `governance/audit-trail/`
- **PII:** None detected. All data is public SEC filings — no personal or sensitive information.

## 25 Canonical Financial CDEs

| Category | CDEs |
|----------|------|
| Balance Sheet (8) | Total Assets, Total Liabilities, Total Stockholders Equity, Cash & Equivalents, Accounts Receivable, Inventory, PP&E, Goodwill |
| Income Statement (8) | Revenue, Cost of Revenue, Gross Profit, Operating Income, Net Income, Income Tax Expense, R&D Expense, SG&A Expense |
| Cash Flow (4) | Operating CF, Investing CF, Financing CF, Capital Expenditures |
| Per-Share (3) | EPS Basic, EPS Diluted, Dividends Per Share |
| Other (2) | Comprehensive Income, Retained Earnings |

## Data Models

Full model documentation (conceptual, logical, physical) lives in [`governance/models/`](governance/models/).

### Conceptual: Entity Resolution

```mermaid
erDiagram
    RAW_ENTITY }o--|| CANONICAL_COMPANY : "resolves to"
    CANONICAL_COMPANY ||--o{ RESOLUTION_DECISION : "has history of"
    HUMAN_REVIEWER ||--o{ RESOLUTION_DECISION : "approves or rejects"
```

### Conceptual: XBRL Tag Normalization

```mermaid
erDiagram
    XBRL_CONCEPT }o--o| CANONICAL_CDE : "maps to (optional)"
    XBRL_CONCEPT ||--o{ CLASSIFICATION_DECISION : "has history of"
    CANONICAL_CDE ||--|{ FINANCIAL_STATEMENT : "belongs to"
    HUMAN_REVIEWER ||--o{ CLASSIFICATION_DECISION : "approves or rejects"
```

### Conceptual: Financial Facts Model

```mermaid
erDiagram
    COMPANY ||--o{ FINANCIAL_FACT : "reports"
    FINANCIAL_CONCEPT ||--o{ FINANCIAL_FACT : "measures"
    COMPANY ||--o{ FISCAL_PERIOD : "operates in"
    FINANCIAL_FACT ||--o{ AMENDMENT : "corrected by"
    FISCAL_PERIOD ||--o{ FINANCIAL_FACT : "contains"
    SEC_FILING ||--o{ FINANCIAL_FACT : "source of"
```

### Logical: Entity Resolution

```mermaid
erDiagram
    EntityMapping {
        identifier mapping_id PK
        identifier cik
        text canonical_name
        text raw_entity_name
        text ticker
        text sic_code
        text fiscal_year_end
        number confidence
        text resolution_method
        text status
        text resolved_by
        text approved_by
        timestamp resolved_at
        timestamp approved_at
    }
    EntityResolutionAudit {
        identifier audit_id PK
        identifier mapping_id FK
        text action
        text actor
        text reasoning
        text evidence
        number confidence_at_action
        timestamp timestamp
    }
    EntityMapping ||--o{ EntityResolutionAudit : "has audit trail"
```

### Logical: XBRL Tag Normalization

```mermaid
erDiagram
    ConceptMapping {
        identifier mapping_id PK
        text concept
        text canonical_cde
        identifier cde_id
        text financial_statement
        text category
        number tier
        number confidence
        text mapping_method
        text status
        text mapped_by
        timestamp mapped_at
    }
    TagNormalizationAudit {
        identifier audit_id PK
        identifier mapping_id FK
        text action
        text actor
        text reasoning
        text evidence
        number confidence_at_action
        timestamp timestamp
    }
    CanonicalCDE {
        identifier cde_id PK
        text name
        text category
        text subcategory
        text definition
    }
    ConceptMapping }o--o| CanonicalCDE : "maps to"
    ConceptMapping ||--o{ TagNormalizationAudit : "has audit trail"
```

### Logical: Financial Facts Model

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

### Physical: Entity Resolution

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

### Physical: XBRL Tag Normalization

```mermaid
erDiagram
    base_concept_mappings {
        STRING mapping_id PK "Stable ID (TN-0001..) | ConceptMapping.mapping_id"
        STRING concept "Raw XBRL concept name | ConceptMapping.concept"
        STRING canonical_cde "CDE name or null | ConceptMapping.canonical_cde"
        STRING cde_id "CDE-007..031 or null | ConceptMapping.cde_id"
        STRING financial_statement "Statement classification | ConceptMapping.financial_statement"
        STRING category "Subcategory | ConceptMapping.category"
        INTEGER tier "Match quality 1/2/3 | ConceptMapping.tier"
        DOUBLE confidence "1.0/0.7/0.6/0.0 by tier | ConceptMapping.confidence"
        STRING mapping_method "How match was determined | ConceptMapping.mapping_method"
        STRING status "approved or unmapped | ConceptMapping.status"
        STRING mapped_by "Classifying agent | ConceptMapping.mapped_by"
        TIMESTAMPTZ mapped_at "When classified | ConceptMapping.mapped_at"
    }
    base_tag_normalization_audit {
        STRING audit_id PK "UUID | TagNormalizationAudit.audit_id"
        STRING mapping_id FK "FK to concept_mappings | TagNormalizationAudit.mapping_id"
        STRING action "proposed/approved/rejected | TagNormalizationAudit.action"
        STRING actor "Who performed action | TagNormalizationAudit.actor"
        STRING reasoning "Classification rationale | TagNormalizationAudit.reasoning"
        STRING evidence "JSON fact/company counts | TagNormalizationAudit.evidence"
        DOUBLE confidence_at_action "Confidence at action time | TagNormalizationAudit.confidence_at_action"
        TIMESTAMPTZ timestamp "When action occurred | TagNormalizationAudit.timestamp"
    }
    base_concept_mappings ||--o{ base_tag_normalization_audit : "tracked by"
```

### Physical: Financial Facts Model

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

## Quick Start

```bash
# Install
uv sync

# Run tests (106 tests)
uv run pytest

# Run XBRL tag normalization
uv run python -m src.base.xbrl_tag_normalization.cli normalize
uv run python -m src.base.xbrl_tag_normalization.cli status
uv run python -m src.base.xbrl_tag_normalization.cli approve
uv run python -m src.base.xbrl_tag_normalization.cli coverage

# Run entity resolution
uv run python -m src.base.entity_resolution.cli resolve
uv run python -m src.base.entity_resolution.cli approve
```

## Project Structure

```
src/                            Source code organized by zone
  infra/                        DuckDB + Iceberg utilities
  raw/                          Raw zone ingestion + profiling
  base/                         Base zone normalization
    entity_resolution/           CIK → canonical company identity
    xbrl_tag_normalization/      XBRL concept → canonical CDE
data/                           Data files organized by zone (gitignored)
governance/                     Governance artifacts
  cde-catalog.json              31 Critical Data Element definitions
  data-dictionary.json          5 table schemas with field-level docs
  models/                       Data models (conceptual, logical, physical) with Mermaid diagrams
  lineage/                      OpenLineage events
  dq-rules/                     Data quality rule definitions
  dq-scorecards/                DQ validation results
  audit-trail/                  Design decision logs
docs/
  specs/                        Spec-driven development specs
  sessions/                     Claude Code session logs
tests/                          Tests organized by zone (106 passing)
.claude/agents/                 Agent definitions for Claude Code
```
