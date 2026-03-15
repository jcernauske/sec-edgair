# Data Steward Assessment: base-conformed-facts
**Date:** 2026-03-15
**Agent:** @data-steward
**Mode:** Greenfield

## Existing Terms Reused

This table inherits nearly all of its columns from `base.financial_facts` and reuses existing approved glossary terms. No new financial or entity terms are needed.

### Entity & Filing Terms
| Term ID | Term | Column(s) in conformed_facts |
|---------|------|------------------------------|
| BT-001 | Central Index Key (CIK) | `cik` |
| BT-002 | Accession Number | `accession_number` |
| BT-003 | Legal Entity Name | `canonical_name` (inherited via entity resolution) |
| BT-005 | Canonical Company Identity | `entity_id`, `canonical_name` |
| BT-006 | Filing Date | `filed_date` |
| BT-025 | SIC Code | Not stored directly, but used upstream in entity_mappings |
| BT-026 | Entity Mapping ID | `entity_id` |

### Financial Structure Terms
| Term ID | Term | Column(s) in conformed_facts |
|---------|------|------------------------------|
| BT-009 | XBRL Concept | `source_concept` (the winning XBRL concept after collision resolution) |
| BT-013 | Financial Business Term | `business_term_id`, `business_term` |
| BT-017 | Financial Fact | `val`, `unit` (the value and unit from the winning fact) |
| BT-018 | Fiscal Period | `fiscal_year`, `fiscal_period` |
| BT-019 | Fiscal Calendar | `fiscal_year_end`, `calendar_year`, `calendar_quarter` |
| BT-021 | Financial Statement | `financial_statement`, `category` |

### All 25 Financial Metric Terms (referenced via business_term_id)
| Term ID | Term |
|---------|------|
| BT-022 | Revenue |
| BT-023 | Net Income |
| BT-024 | Total Assets |
| BT-027 | Total Liabilities |
| BT-028 | Total Stockholders Equity |
| BT-029 | Cash and Cash Equivalents |
| BT-030 | Accounts Receivable |
| BT-031 | Inventory |
| BT-032 | Property Plant and Equipment |
| BT-033 | Goodwill |
| BT-034 | Cost of Revenue |
| BT-035 | Gross Profit |
| BT-036 | Operating Income |
| BT-037 | Income Tax Expense |
| BT-038 | Research and Development Expense |
| BT-039 | Selling General and Administrative Expense |
| BT-040 | Operating Cash Flow |
| BT-041 | Investing Cash Flow |
| BT-042 | Financing Cash Flow |
| BT-043 | Capital Expenditures |
| BT-044 | Earnings Per Share Basic |
| BT-045 | Earnings Per Share Diluted |
| BT-046 | Dividends Per Share |
| BT-047 | Comprehensive Income |
| BT-048 | Retained Earnings |

### Pipeline Terms (already exist)
| Term ID | Term | Relevance |
|---------|------|-----------|
| BT-012 | Supersession | Supersession filtering is applied as input logic (WHERE is_superseded = false) |
| BT-015 | Tier | Used in tier/frequency fallback collision resolution |

**Total existing terms reused: 34** (7 entity/filing + 2 financial structure + 25 financial metrics)

## New Terms Proposed

**None required.**

The spec explicitly states it "reuses all existing BT-XXX terms from base.financial_facts (no new financial terms)." After reviewing the schema, I confirm this is accurate. The new columns introduced by this table (`conformed_id`, `source_fact_id`, `competing_fact_count`, `selection_reason`, `promoted_at`, `load_date`) are all pipeline/system metadata, not business concepts. See classification below.

## Metadata Classification

The following columns are **pipeline execution metadata** -- they describe how and when the conformation process ran, not business concepts. They do NOT warrant business terms.

| Column | Classification | Rationale |
|--------|---------------|-----------|
| `conformed_id` | **System metadata** | Synthetic surrogate key (SHA-256 hash of grain). An internal identifier for deduplication, not a business concept. Analogous to `fact_id` in financial_facts, which is also not a business term. |
| `source_fact_id` | **Lineage metadata** | Foreign key back to `base.financial_facts.fact_id`. A pointer for traceability, not a business concept. |
| `competing_fact_count` | **Pipeline metadata** | Integer recording how many candidate facts existed before collision resolution. This is an audit/observability metric about the pipeline's behavior, not a financial or entity concept. |
| `selection_reason` | **Pipeline metadata** | Enumerated string ("primary_concept" / "tier_frequency_fallback" / "sole_candidate") describing which resolution algorithm branch selected the winning fact. This is pipeline decision logging, not a business concept. |
| `promoted_at` | **System metadata** | Timestamp of when the row was written. Standard pipeline bookkeeping. |
| `load_date` | **System metadata** | Pipeline run date. Standard pipeline bookkeeping. |

### Governance Reviewer Advisory Confirmation

The @governance-reviewer asked: "Confirm whether `selection_reason` and `competing_fact_count` are pipeline metadata, not business terms."

**Confirmed: both are pipeline metadata.** They describe the conformation algorithm's behavior (which branch of collision resolution logic ran, and how many candidates it chose from). They are analogous to `confidence_score` and `match_method` in entity resolution -- observable artifacts of how the pipeline made a decision, not business domain concepts. No business user would ask "what is the competing fact count for Apple's revenue?" -- they would ask "what is Apple's revenue?", which is answered by the `val` column mapped to BT-022.

## Recommendation

**PROCEED** -- No new business terms are required.

All business concepts in `base.conformed_facts` are already defined in the glossary (34 existing terms). The five new columns are pipeline/system metadata that do not represent business concepts and therefore do not need glossary entries.

The `used_in_models` field for referenced terms should be updated to include `"base-conformed-facts"` when the conceptual model is produced by @semantic-modeler.
