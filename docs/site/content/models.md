# Data Models

## Page Title
28 model artifacts. Every one machine-proposed, human-reviewed.

## Description
9 entity groups across 3 zones. Every model was proposed by an AI agent (@semantic-modeler), reviewed by a human, and linked to the business glossary. Conceptual models define what exists. Logical models define attributes and relationships. Physical models define actual Iceberg column types and source mappings.

## Key Metrics
- **28** model artifacts (conceptual + logical + physical)
- **9** entity groups across Base, Consumable, AI-Ready zones
- **3** abstraction levels per entity group

## Base Zone Models (4 entity groups, 12 artifacts)

### Entity Resolution
Maps raw SEC EDGAR entity names (inconsistent, all-caps, abbreviated) to canonical company identities with human-in-the-loop approval. 20 companies, full audit trail.

**Tables:** base.entity_mappings, base.entity_resolution_audit

### XBRL Tag Normalization
Classifies 3,285 XBRL concepts into 25 canonical financial data elements using a tiered matching engine. Tier 1 (exact), Tier 2 (pattern), Tier 3 (unmapped). Human-approved concept-to-CDE mappings.

**Tables:** base.concept_mappings, base.tag_normalization_audit

### Financial Facts Model
The heart of the base zone. Joins raw XBRL data with resolved entities and normalized concepts to produce 547K enriched facts, plus fiscal calendar (1,483 periods) and amendment tracking (264K supersession pairs).

**Tables:** base.financial_facts, base.fiscal_calendar, base.amendment_tracking

### Conformed Facts
The most important architectural decision in the pipeline. Resolves competing XBRL concepts to produce exactly one authoritative value per (company, metric, year, period). 28,849 rows from 547K base facts.

**Tables:** base.conformed_facts

## Consumable Zone Models (5 entity groups, 15 artifacts)

### Company Financials
The core consumable table. One row per company per business term per fiscal period. Eliminates XBRL complexity. ~27K rows from 547K base facts.

**Tables:** consumable.company_financials

### Financial Ratios
7 computed ratios (margins, leverage, efficiency) that normalize for company size. Both component values stored for full audit transparency. ~7K rows.

**Tables:** consumable.financial_ratios

### Period-Over-Period Growth
YoY absolute change, YoY percentage change, and 5-year CAGR. Growth types are rows, not columns. ~71K rows.

**Tables:** consumable.period_over_period

### Peer Comparison
Ranks companies within their sector. Dense ranking, sector averages, medians, and percentiles for both absolute values and ratios. ~28K rows.

**Tables:** consumable.peer_comparison

### Amendment Analysis
Precomputed summaries of SEC filing amendment patterns per company per year. Frequency, magnitude, timing, and diversity of restatements. ~371 rows.

**Tables:** consumable.amendment_analysis

## AI-Ready Zone Model (1 entity group, 1 artifact)

### Chat Interface
Claude-powered conversational interface using tool use (not RAG). 7 validated Python tool functions query DuckDB in-memory over the 5 consumable Iceberg tables. Zero infrastructure beyond what the pipeline already uses. Conceptual model only -- no new tables are created.

## Model Levels Explained

### Conceptual
High-level entity relationship diagrams. Shows what business concepts exist and how they relate. No attributes, no types. Answers: "What are we modeling?"

### Logical
Full attribute definitions with domains, nullability, business term mappings, and CDE/PII flags. Technology-agnostic. Answers: "What data do we need?"

### Physical
Actual Iceberg/DuckDB column definitions with types (STRING, INTEGER, DOUBLE, etc.), source mappings, and physical design decisions. Answers: "How is it stored?"

## Governance Integration
- Every model artifact references business terms by ID (BT-XXX)
- CDE and PII flags are derived from business glossary
- Models are stored in governance/models/ as markdown with embedded Mermaid
- All models are versioned in git alongside the code they describe
