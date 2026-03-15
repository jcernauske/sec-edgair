# SEC EDGAIR — Build Plan

**Date:** 2026-03-12
**Status:** Draft
**Stack:** Python, DuckDB + Apache Iceberg tables, Claude Code with specialized agents
**Scope:** 10-20 public companies, 5 years of filings
**Home:** Standalone open source repo (private until ready)

---

## The Thesis

Every bank, asset manager, and insurance company pays teams of people and six figures in tooling to do semantic data modeling, data governance, and data quality. Most of them draw pictures in SQLDBM or Visio and call it a data model, then pay for Collibra or Alation to catalog the results. This project proves that an AI agent pipeline — the same spec-driven, multi-agent workflow used to build Arteeoo — can take a raw, messy, bitemporal financial dataset and deliver it as a clean, tested, governed, semantically meaningful data product with full governance metadata. No diagrams. No SQLDBM. No Visio. No humans manually entering metadata into a $500K/year governance tool. Just agents that understand the domain.

The governance artifacts the agents produce are formatted for interoperability — OpenLineage for lineage, structured JSON catalogs compatible with Collibra/Alation/DataHub import, standardized data quality results. The argument isn't "replace your governance tool." It's "your agents can populate your governance tool faster and more completely than your humans do, and they never forget to update it."

---

## Storage Architecture: DuckDB + Iceberg

**Engine:** DuckDB — in-process analytical database, zero infrastructure, anyone who clones the repo can run it immediately.

**Table Format:** Apache Iceberg — open table format with built-in time travel via snapshots. Every write creates a new snapshot. Previous versions are always queryable.

**Why Iceberg matters for this project:**
- Bitemporal support is partially built in — Iceberg snapshots track when data was written (transaction time). Combined with the valid time modeled in the data itself, you get full bitemporality.
- When an SEC filing gets amended, the new version is written as a new snapshot. Point-in-time queries become `SELECT * FROM table AT (VERSION => snapshot_id)` instead of hand-rolled supersession logic.
- Iceberg is what every bank is evaluating for their lakehouse. Producing Iceberg tables makes this project directly portable to any enterprise environment.
- The same code works against local storage (for the open source demo) or S3 Tables / Databricks / Snowflake (for anyone who wants to scale it up).

**Local setup:** DuckDB writes Iceberg tables to local file storage. No catalog server, no Docker, no cloud account required. Catalog layer can be added later (Apache Polaris, Lakekeeper) if needed, but Phase 0 stays zero-infrastructure.

---

## Dataset: SEC EDGAR XBRL Company Facts

**Source:** https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip

**Why this dataset:**
- Public, free, no licensing issues
- Financial data — your audience lives in this world
- Genuinely messy — inconsistent entity names, varying XBRL tags, mixed fiscal calendars
- Naturally bitemporal — filings have a valid period (what quarter/year the data covers) and a transaction time (when the filing was submitted, amended, or restated)
- Amendments and restatements create multiple versions of the same fact — textbook slowly-changing data
- Entity resolution challenges — companies change names, merge, spin off, change tickers
- Large enough to be credible, scoped enough to be manageable at 10-20 companies

**Target companies (suggested — mix of sectors for variety):**
- Big banks: JPMorgan Chase, Goldman Sachs, Bank of America, Northern Trust (why not)
- Tech: Apple, Microsoft, Alphabet
- Healthcare: UnitedHealth, Pfizer
- Retail: Walmart, Amazon
- Industrial: Caterpillar, 3M
- Energy: ExxonMobil, Chevron

This gives you cross-sector variety for demonstrating entity resolution, tag normalization, and fiscal calendar differences.

---

## Architecture: Raw → Base → Consumable

### Raw Zone

**What happens here:** Data lands as-is. Nothing is transformed. Agents observe, profile, and tag — but don't alter.

| Task | Agent | Output |
|------|-------|--------|
| Ingest XBRL bulk data for target companies | Ingest Agent | Raw JSON files, one per company, stored as-landed |
| Data profiling | Profiler Agent | Schema detection, data types, cardinality, null rates, anomaly flags, statistical summaries |
| PII detection | PII Scanner Agent | Flag any personally identifiable information (officer names, addresses in some filings) — classify and tag |
| Data classification | Classification Agent | Sensitivity tagging (public, internal, confidential, restricted) — SEC filings are public, but we're demonstrating the pattern |
| Source metadata capture | Metadata Agent | Source URL, download timestamp, file hash, record counts, ingestion lineage record |

**Deliverables:**
- Raw data files, untouched
- Profiling report (automated)
- PII scan results
- Classification tags
- Lineage record: source → raw landing

---

### Base Zone

**What happens here:** This is where the real work lives. AI agents clean, conform, model, and govern the data. Every transformation is logged. Every decision is documented.

#### Semantic Modeling (no diagrams)

| Task | Agent | Output |
|------|-------|--------|
| Propose dimensional model from raw data | Modeling Agent | Star/snowflake schema proposal — entity tables, fact tables, dimension tables, relationships — all generated from data inspection, not from a human drawing boxes |
| Entity resolution | Entity Agent | Map CIKs to canonical company identities across name changes, mergers, ticker symbol changes, fiscal year end changes |
| XBRL tag normalization | CDE Agent | Map varying XBRL tags (us-gaap:Revenues, us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax, etc.) to canonical Critical Data Elements |
| Fiscal calendar alignment | Calendar Agent | Normalize fiscal year ends — Apple's Sep FY vs JPMorgan's Dec FY — into a queryable temporal structure |

#### Bitemporal Modeling

| Task | Agent | Output |
|------|-------|--------|
| Design bitemporal schema | Temporal Agent | Valid time (reporting period start/end) + transaction time (filing date, amendment date) properly structured as separate dimensions. Iceberg snapshots handle the system/transaction time layer; valid time is modeled explicitly in the data. |
| Handle amendments/restatements | Temporal Agent | New Iceberg snapshot per amendment — original filings preserved in previous snapshots, never overwritten. Supersession metadata tracked in the data layer. |
| Point-in-time query support | Temporal Agent | Enable queries like "What did we think Apple's Q3 revenue was on November 1?" via Iceberg time travel (`AT VERSION`) combined with valid-time filtering |

#### Data Governance

| Task | Agent | Output |
|------|-------|--------|
| CDE tagging | CDE Agent | Every field tagged with its critical data element classification — is this Revenue? Is this Total Assets? Is this EPS? |
| Lineage capture | Lineage Agent | Every transformation from raw to base logged in **OpenLineage format** — source field, transformation logic, agent that performed it, timestamp, version. Compatible with Marquez, DataHub, Collibra import. |
| Data quality rules | DQ Agent | Automated validation: null checks, referential integrity, temporal consistency (no future-dated filings), cross-field validation (assets = liabilities + equity), duplicate detection. Results in standardized format with pass/fail/warning per rule per table. |
| Row-level security policies | RLS Agent | Proposed RLS policies based on data classification — demonstrating the pattern even though SEC data is public. "If this were PII, here's the policy." |
| Data dictionary generation | Documentation Agent | Automated data dictionary — every table, every field, plain-English definition, source, lineage, quality rules, CDE mapping. Structured JSON exportable to Collibra/Alation/DataHub. |
| Decision audit trail | All Agents | Every agent logs its reasoning — why the entity resolver mapped this CIK to this company, why the CDE tagger classified this field as Revenue and not Other Income. Not just outputs, rationales. |

**Deliverables:**
- Clean, governed, bitemporal Iceberg tables
- Full lineage from raw to base in OpenLineage format
- CDE mapping catalog (structured JSON, import-ready)
- Data quality test suite with scorecard per table
- RLS policy definitions
- Auto-generated data dictionary (structured JSON, import-ready)
- Agent decision audit trail

---

### Consumable Zone

**What happens here:** Specific, use-case-shaped data products built on top of Base. These are opinionated about what questions they answer.

| Consumable | Description | Audience |
|------------|-------------|----------|
| Financial Comparison Dataset | Normalized financial metrics across 10-20 companies, comparable across fiscal calendars, with canonical CDEs | Analysts, dashboards |
| Amendment/Restatement Tracker | Every financial fact that was amended or restated, with before/after values, filing dates, and magnitude of change | Risk, compliance, audit |
| Point-in-Time Snapshot API | Query any company's financials as they were known on any given date — not what they are now, what they were then. Powered by Iceberg time travel. | Portfolio management, backtesting |

**Deliverables:**
- Queryable Iceberg tables (portable to S3 Tables, Databricks, Snowflake, or any Iceberg-compatible environment)
- Data contracts per consumable — schema, freshness SLA, quality thresholds, breaking change policy (generated by agents, not written by humans)
- API or query interface (DuckDB SQL, optional thin REST layer)
- Documentation

---

### AI-Ready Zone

**What happens here:** The governed, consumable data is transformed into formats that AI systems can consume directly — as context for RAG, as grounding truth, as training data, and as evaluation benchmarks. This is the layer that answers "you can't do AI until you fix your data" with "the data is fixed, here's the AI-ready output."

#### Grounding & Retrieval

| Task | Agent | Output |
|------|-------|--------|
| Semantic embeddings | `@embedding-engineer` | Every entity, financial fact, and CDE vectorized and stored in a vector index. Enables semantic search: "find all companies that restated revenue downward" without writing SQL. |
| Grounding documents | `@doc-generator` | Structured fact sheets per company per quarter formatted for RAG consumption. "Based on SEC filings, JPMorgan's Q3 2024 revenue was $X, filed on Y, amended on Z." These are the documents that prevent hallucination. |
| Intelligent chunking | `@chunk-strategist` | Context-window-optimized chunks per company per period. Not raw data dumps — intelligently bounded documents with the right metadata attached so an LLM can reason about a company's financials without exceeding token limits or missing context. |

#### AI Evaluation & Trust

| Task | Agent | Output |
|------|-------|--------|
| Evaluation datasets | `@eval-engineer` | Known-good question/answer pairs generated from the governed data. "What was Apple's total assets in Q2 2023?" with the verified answer and the source lineage. This is what you need to test whether your AI is actually getting the right answers. |
| Confidence signals | `@dq-engineer` | Data quality scores surfaced as metadata on grounding documents. If a field has low quality scores, was recently amended, or has known issues, the AI consumes that signal and expresses appropriate uncertainty. Quality metadata isn't just for humans — it's context for the model. |
| AI-to-source lineage | `@lineage-tracker` | When an AI makes a claim about a company's financials, you can trace it back through the grounding document, through the governed data, through the lineage, all the way to the raw SEC filing. That's the audit trail a regulator wants to see. |

#### MCP / Tool Use Integration

| Task | Agent | Output |
|------|-------|--------|
| MCP server | `@mcp-engineer` | A Model Context Protocol server that exposes the governed data as tools an AI agent can call. Instead of stuffing data into a prompt, an AI agent can query "get JPMorgan Q3 2024 revenue" and get back a structured response with the value, source lineage, quality score, and amendment history. |

**Deliverables:**
- Vector index of all entities, facts, and CDEs (local, portable)
- RAG-ready grounding documents per company per quarter
- Intelligently chunked context documents with metadata
- Evaluation dataset — verified Q&A pairs with source lineage
- Quality-aware confidence signals for AI consumption
- Full AI-to-source lineage — from AI claim to raw SEC filing
- MCP server for agent tool use (optional but impressive)

**The thesis for this layer:** Every bank is trying to do AI on financial data. Most of them are shoving unstructured data into a vector store and praying. This layer shows what "AI-ready data" actually looks like — governed, chunked, grounded, with quality signals and full lineage from AI output back to source. It's the bridge between "we have data" and "compliance signed off on our AI."

---

## Governance Demo: The "Collibra Killer" Walkthrough

The flagship demo for this project: pick a single field in the consumable zone — say, JPMorgan's Q3 2024 Revenue — and show the full governance stack:

1. **Lineage** — trace from consumable back through base to the raw XBRL filing, every transformation logged in OpenLineage format
2. **CDE mapping** — this field is tagged as "Revenue" regardless of which XBRL tag JPMorgan used to report it
3. **Data quality** — the quality rules this field passed (not null, positive value, cross-validated against total revenue, temporally consistent)
4. **Classification** — sensitivity tag, proposed RLS policy
5. **Bitemporal history** — the amendment history via Iceberg snapshots, showing what the value was at different points in time
6. **Decision audit** — the agent's reasoning for every classification and transformation decision
7. **Data dictionary** — plain-English definition, owner, source, freshness

All generated automatically. No human entered any of this into a GUI. The agents produced it as a byproduct of doing the actual work.

**The argument to a CDO:** Your $500K/year governance tool isn't the problem. Your manual process for feeding it is. These agents generate more complete governance metadata in hours than your team produces in months — and it's in a format you can import directly into whatever catalog you already own.

---

## Agent Architecture (Claude Code)

Same spec-driven, multi-agent workflow as Arteeoo. Every agent has a defined role, a defined scope, and doesn't freelance.

### Agents

#### Active Agents (built and running)

| Agent | Role | Status |
|-------|------|--------|
| `@governance-reviewer` | Pre/post-implementation review, governance completeness checks | Active |
| `@staff-engineer` | Final quality gate — FAANG-caliber code review, last approval before spec completion | Active |
| `@data-analyst` | EDA profiling — distributions, outliers, edge cases, threshold evidence | Active |
| `@dq-rule-writer` | Writes DQ rules from EDA evidence (never queries data directly) | Active |
| `@dq-engineer` | Executes DQ rules against real Iceberg data, produces scorecards | Active |
| `@entity-resolver` | Company identity resolution — CIK to canonical identity with approval gate | Active |
| `@semantic-modeler` | Proposes conceptual → logical → physical models, detects greenfield vs backfill | Active |
| `@data-steward` | Business glossary management — proposes terms, manages approval workflow | Active |
| `@cde-tagger` | Maps fields to canonical Critical Data Elements | Active |
| `@lineage-tracker` | Captures transformation lineage in OpenLineage format | Active |
| `@doc-generator` | Auto-generates data dictionaries, catalogs, data contracts | Active |
| `@temporal-modeler` | Designs bitemporal schema, temporal query helpers | Active |
| `@pii-scanner` | PII detection and classification | Active |
| `@policy-engineer` | Row-level security and data protection policies | Active |
| `@insight-manager` | **Zone transition agent** — analyzes completed zone data, recommends data products for next zone, ranks by value/feasibility | Active |

#### Future Agents (AI-Ready Zone)

| Agent | Role | Phase |
|-------|------|-------|
| `@embedding-engineer` | Semantic embeddings, vector index management | Phase 5 |
| `@chunk-strategist` | Intelligent chunking for LLM consumption | Phase 5 |
| `@eval-engineer` | Evaluation Q&A pairs with verified answers and lineage | Phase 5 |
| `@mcp-engineer` | MCP server exposing governed data as AI-callable tools | Phase 5 |

### Workflow Per Feature/Transformation

1. Write a spec (what transformation, why, expected input/output)
2. Spec reviewed by `@governance-reviewer`
3. `@data-steward` proposes business terms → human approval gate
4. `@semantic-modeler` proposes conceptual → logical → physical models → human approval gates
5. `@data-analyst` EDA on source data (profiles, distributions, threshold evidence)
6. `@dq-rule-writer` writes rules from EDA report (never queries data directly)
7. Implementation by appropriate agent (must match approved physical model)
8. `@dq-engineer` executes rules against real Iceberg data, produces scorecard
9. `@lineage-tracker` logs the transformation in OpenLineage format
10. `@cde-tagger` updates CDE mappings
11. `@doc-generator` updates documentation, data dictionary, and data contracts
12. `@governance-reviewer` post-implementation completeness check
13. `@staff-engineer` final quality review — LAST gate before spec completion
14. All agents log decision rationale to audit trail

### Zone Transition Workflow

Between zones (after all specs in a zone are complete, before the next zone's specs are written):

1. `@insight-manager` analyzes completed zone data (queries real Iceberg tables, not schemas)
2. Produces ranked data product recommendations, coverage analysis, external data opportunities
3. Output drives spec writing for the next zone — no spec written without insight report
4. Insight report saved to `governance/insights/[source]-to-[target]-insights.md`

---

## Build Phases

### Phase 0 — Setup (Week 1)
- [x] Create private GitHub repo
- [x] Set up Python project structure (uv for dependency management)
- [x] Set up DuckDB with Iceberg extension, verify local Iceberg table read/write
- [x] Set up Claude Code with CLAUDE.md and agent definitions
- [x] Download EDGAR bulk data for target companies
- [x] Verify data access and basic parsing

### Phase 1 — Raw Zone (COMPLETE)
- [x] Build ingest pipeline for XBRL company facts — 547,398 facts from 20 companies
- [x] Data profiling agent — schema, types, cardinality, nulls, anomalies (EDA report)
- [x] PII scanner — flag officer names, addresses
- [x] Data classification — sensitivity tagging
- [x] Source metadata capture — lineage from source to raw
- [x] DQ rules — 8 rules, all passing
- [x] **Milestone:** Raw data landed, profiled, classified, with full ingestion lineage

### Phase 2 — Base Zone: Modeling + Governance (COMPLETE)
- [x] Entity resolution — 20 companies, CIK to canonical identity, human-approved
- [x] XBRL tag normalization — 3,285 concepts → 25 CDEs (Tier 1/2/3)
- [x] Dimensional model — financial_facts (547K facts), fiscal_calendar (1,294 periods), amendment_tracking (239K pairs)
- [x] Bitemporal schema — valid time + transaction time via Iceberg snapshots, query helpers, temporal DQ rules
- [x] Amendment/restatement handling — supersession detection, val_change tracking
- [x] Fiscal calendar normalization — observed period boundaries per company
- [x] CDE tagging — 31 CDEs (CDE-001 through CDE-031), structured JSON catalog
- [x] Full lineage capture — OpenLineage format for all 6 base specs
- [x] Data quality — 42 DQ rules, all passing, scorecards from real execution
- [x] Business glossary — 25 terms (external auto-approved, project-specific human-approved)
- [x] Data dictionary — auto-generated, structured JSON
- [x] Agent decision audit trail — rationale for every classification and transformation
- [x] **Milestone:** 8 Iceberg tables across raw + base zones, fully governed, 42 DQ rules passing, 146 tests

### Phase 3 — Zone Transition: @insight-manager Analysis (COMPLETE)
- [x] @insight-manager agent created — strategic data product discovery at zone boundaries
- [x] Insight report produced: `governance/insights/base-to-consumable-insights.md`
- [x] Queried real Iceberg data — coverage matrix, per-company profiles, CDE distributions
- [x] Identified 12 universal CDEs (all 20 companies), 6 near-universal, 7 partial
- [x] Ranked data products by value/feasibility (6 Tier 1-2, 6 Tier 3)
- [x] Identified external data opportunities (stock prices = #1 priority)
- [x] Documented coverage gaps and risks (fiscal year misalignment, financial sector P&L structure)
- [x] **Milestone:** Data-driven roadmap for consumable zone, not assumptions

### Phase 4 — Consumable Zone (Weeks 9-12)

#### 4A — Core Data Products (from insight report Tier 1)
- [ ] `consumable-company-financials` — Denormalized comparison table: one row per (company, CDE, fiscal_year, fiscal_period). Current facts only. Filters `is_superseded=false`. The foundation everything else builds on.
- [ ] `consumable-financial-ratios` — Computed ratios from existing CDEs: gross margin, operating margin, net margin, debt-to-equity, R&D intensity, SGA ratio, capex-to-revenue. Derived from company financials.
- [ ] `consumable-period-over-period` — YoY change, sequential change, CAGR for each (company, CDE). Time-series analysis layer.
- [ ] `consumable-amendment-analysis` — Amendment frequency, magnitude, patterns per company. Unique insight about corporate reporting quality.
- [ ] **Milestone:** Four queryable consumable tables — cross-company comparison, ratios, growth, amendment intelligence

#### 4B — Comparative Analysis (from insight report Tier 2)
- [ ] `consumable-peer-comparison` — Sector grouping via SIC codes, peer ranks, percentiles within sector. Requires SIC-to-GICS sector mapping.
- [ ] Data contracts per consumable — schema, freshness SLA, quality thresholds, breaking change policy

#### 4C — External Data Enrichment (from insight report — highest-value external source)
- [ ] `raw-ingest-stock-prices` — Daily stock prices for all 20 tickers (Yahoo Finance or Alpha Vantage). New raw data source. Join on (ticker, date).
- [ ] `consumable-valuation-ratios` — P/E, P/B, P/S, dividend yield. Requires stock prices + existing EPS/equity/revenue CDEs.
- [ ] Consider: FRED API integration for macro indicators (GDP, CPI, rates) — join on date for macro-adjusted analysis.

#### 4D — Demo & Documentation
- [ ] Build the "Collibra killer" demo walkthrough — single field, full governance stack
- [ ] Point-in-time query support — demonstrate `AT VERSION` queries via bitemporal module
- [ ] **Milestone:** Full consumable zone with data products, external enrichment, governance, and demo-ready walkthrough

### Phase 5 — AI-Ready Zone (Weeks 11-13)
- [ ] Semantic embeddings — vectorize entities, facts, CDEs
- [ ] Grounding documents — structured fact sheets per company per quarter
- [ ] Intelligent chunking — context-window-optimized documents with metadata
- [ ] Evaluation datasets — verified Q&A pairs with source lineage
- [ ] Confidence signals — quality scores surfaced as AI-consumable metadata
- [ ] AI-to-source lineage — full chain from AI claim to raw filing
- [ ] MCP server (stretch goal) — expose governed data as AI-callable tools
- [ ] **Milestone:** Full AI-ready data product — grounded, chunked, evaluated, with lineage from AI output to SEC filing

### Phase 6 — Open Source Prep (Weeks 14-15)
- [ ] Clean up repo for public consumption
- [ ] Write README that tells the story — raw to base to consumable to AI-ready, full governance at every layer
- [ ] Add contributing guidelines
- [ ] License selection (MIT or Apache 2.0)
- [ ] Record a demo or write a walkthrough — the single-field governance deep dive AND the AI-ready demo
- [ ] Publish

---

## LinkedIn Content That Falls Out of This

Once the project ships, the following posts write themselves:

1. "I built a complete data governance pipeline with AI agents — no SQLDBM, no Visio, no diagrams" (launch post)
2. "Every bank pays 15 people to do what 10 agents did in 15 weeks" (the provocation)
3. "Bitemporal data modeling: AI got it right on the first try, most data teams get it wrong for months" (technical deep dive)
4. "I automated CDE tagging with an AI agent and it found classifications our manual process missed" (governance-specific)
5. "The data quality test suite an AI wrote is more comprehensive than most I've seen written by humans" (callback to the human coder / mediocre code theme)
6. "Your $500K governance tool isn't the problem. Your manual process for feeding it is." (the Collibra provocation)
7. "I traced a single financial fact from consumable to raw source — full lineage, audit trail, quality rules — all generated by agents" (the demo walkthrough post)
8. "Everyone says 'you can't do AI until you fix your data.' OK — I fixed the data. Here's what AI-ready actually looks like." (the AI-ready layer reveal)
9. "Most banks are shoving unstructured data into a vector store and praying. Here's what grounded, governed, auditable AI looks like instead." (the compliance-approved AI post)
10. "I built an MCP server that lets AI agents query governed financial data with full lineage back to the SEC filing. Your compliance team can audit every answer." (the MCP/tool-use post — if built)

---

## Open Questions

- [ ] Which 10-20 companies specifically? (Suggested list above, Jeff to confirm)
- [ ] How deep on RLS? (Pattern demonstration vs. functional implementation)
- [ ] Do we want a simple web UI for the point-in-time queries? (Nice to have, not essential)
- [ ] Iceberg catalog layer — start without one, add Polaris/Lakekeeper later if needed?

---

## Phase 7 — Follow-On: Insider Ownership Data Product (PII Governance)

**Problem:** SEC EDGAR XBRL financial data is entirely public with no PII. The pipeline's PII detection and governance capabilities can't be meaningfully tested against synthetic data without it feeling forced. Real PII governance problems emerge when you join two datasets and suddenly have personal information tied to financial data.

**Solution:** Build a second data product from SEC EDGAR Forms 3/4/5 (insider ownership filings) and join it to the existing financial facts.

**Why Forms 3/4/5:**
- Filed per-insider, per-transaction — naturally person-centric
- Include the **issuer CIK** (join key to existing `base.financial_facts`) and **reporting person CIK**
- Contain real PII: officer/director names, relationships to company, titles
- Available as structured XML on EDGAR — no PDF scraping
- Millions of filings available
- The join key (`company_cik`) already exists in our pipeline

**Proposed pipeline:**
- `raw.insider_ownership` — ingest Forms 3/4/5 XML from EDGAR
- `base.board_members` — canonical person identities with names, titles, company relationships
- Join to `base.financial_facts` via `cik` — now you have personal compensation data tied to financial performance

**What this enables:**
- Real PII detection (names, person CIKs, relationships) — not synthetic
- PII governance policies that matter (masking, access control, retention)
- RLS policies with actual teeth — "only compliance can see insider names tied to trading data"
- The governance demo becomes dramatically more compelling: "here's how the agents handled real PII when two public datasets were joined"

**The thesis:** PII governance isn't about scanning for SSNs in a text field. It's about what happens when you join two innocuous datasets and create something sensitive. That's the real-world problem, and this is how you demonstrate solving it.
