# SEC EDGAIR — Build Plan

**Date:** 2026-03-12
**Last Amended:** 2026-03-15
**Status:** Active — Phases 0-5 complete, Phase 6 pending
**Stack:** Python, DuckDB + Apache Iceberg tables, Claude Code with specialized agents
**Scope:** 20 public companies, FY2009-2026 (18 fiscal years)
**Home:** Standalone open source repo (private until ready)

---

## The Thesis

Every bank, asset manager, and insurance company pays teams of people and six figures in tooling to do semantic data modeling, data governance, and data quality. Most of them use tools like SQLDBM or Visio to design data models, then pay for Collibra or Alation to catalog the results. This project proves that an AI agent pipeline — the same spec-driven, multi-agent workflow used to build Arteeoo — can take a raw, messy, bitemporal financial dataset and deliver it as a clean, tested, governed, semantically meaningful data product with full governance metadata. Agents generate the models, the governance artifacts, and the documentation as a byproduct of doing the actual work — then a human reviews and approves.

The governance artifacts the agents produce are formatted for interoperability — OpenLineage for lineage, structured JSON catalogs compatible with Collibra/Alation/DataHub import, standardized data quality results. The argument isn't "replace your governance tools or your modeling tools." It's "agents can generate the first draft faster and more completely than manual processes, and your existing tools become the review and approval layer instead of the authoring layer."

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
- Big banks: JPMorgan Chase, Goldman Sachs, Bank of America, Northern Trust
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

#### Semantic Modeling (agent-generated, human-reviewed)

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

> **AMENDMENT (2026-03-15): The entire AI-Ready zone was re-architected based on the `consumable-to-ai-ready-insights.md` insight report and a `genai-architect` review. The original plan below (RAG, embeddings, chunking, pre-computed documents) was deprecated in favor of a tool-use chat interface where Claude queries the governed Iceberg tables directly via validated Python functions. See "AI-Ready Architecture Decision: Why Tool Use Beat RAG" below for the full rationale.**

#### ~~Grounding & Retrieval~~ (DEPRECATED — see amendment above)

| Task | Agent | Output | Status |
|------|-------|--------|--------|
| ~~Semantic embeddings~~ | ~~`@embedding-engineer`~~ | ~~Every entity, financial fact, and CDE vectorized and stored in a vector index. Enables semantic search: "find all companies that restated revenue downward" without writing SQL.~~ | DEPRECATED — unnecessary for structured data |
| ~~Grounding documents~~ | ~~`@doc-generator`~~ | ~~Structured fact sheets per company per quarter formatted for RAG consumption. "Based on SEC filings, JPMorgan's Q3 2024 revenue was $X, filed on Y, amended on Z." These are the documents that prevent hallucination.~~ | DEPRECATED — tool functions return live data |
| ~~Intelligent chunking~~ | ~~`@chunk-strategist`~~ | ~~Context-window-optimized chunks per company per period. Not raw data dumps — intelligently bounded documents with the right metadata attached so an LLM can reason about a company's financials without exceeding token limits or missing context.~~ | DEPRECATED — 125K rows fits easily in DuckDB; no chunking needed |

#### ~~AI Evaluation & Trust~~ (DEPRECATED — see amendment above)

| Task | Agent | Output | Status |
|------|-------|--------|--------|
| ~~Evaluation datasets~~ | ~~`@eval-engineer`~~ | ~~Known-good question/answer pairs generated from the governed data. "What was Apple's total assets in Q2 2023?" with the verified answer and the source lineage. This is what you need to test whether your AI is actually getting the right answers.~~ | DEPRECATED — replaced by 116 integration tests against real Iceberg data |
| ~~Confidence signals~~ | ~~`@dq-engineer`~~ | ~~Data quality scores surfaced as metadata on grounding documents. If a field has low quality scores, was recently amended, or has known issues, the AI consumes that signal and expresses appropriate uncertainty. Quality metadata isn't just for humans — it's context for the model.~~ | DEPRECATED — anomaly flags computed at query time by tool functions |
| ~~AI-to-source lineage~~ | ~~`@lineage-tracker`~~ | ~~When an AI makes a claim about a company's financials, you can trace it back through the grounding document, through the governed data, through the lineage, all the way to the raw SEC filing. That's the audit trail a regulator wants to see.~~ | PARTIALLY SUPERSEDED — runtime lineage events captured in `governance.lineage_events` Iceberg table; tool functions query governed tables with full upstream lineage |

#### ~~MCP / Tool Use Integration~~ (SUPERSEDED)

| Task | Agent | Output | Status |
|------|-------|--------|--------|
| ~~MCP server~~ | ~~`@mcp-engineer`~~ | ~~A Model Context Protocol server that exposes the governed data as tools an AI agent can call. Instead of stuffing data into a prompt, an AI agent can query "get JPMorgan Q3 2024 revenue" and get back a structured response with the value, source lineage, quality score, and amendment history.~~ | SUPERSEDED — built as direct Claude API tool use instead of MCP. Same concept (AI calls validated functions to get governed data), simpler implementation. MCP remains a future option. |

**~~Deliverables:~~** (DEPRECATED — see replacement deliverables below)
- ~~Vector index of all entities, facts, and CDEs (local, portable)~~
- ~~RAG-ready grounding documents per company per quarter~~
- ~~Intelligently chunked context documents with metadata~~
- ~~Evaluation dataset — verified Q&A pairs with source lineage~~
- ~~Quality-aware confidence signals for AI consumption~~
- ~~Full AI-to-source lineage — from AI claim to raw SEC filing~~
- ~~MCP server for agent tool use (optional but impressive)~~

**The thesis for this layer:** Every bank is trying to do AI on financial data. Most of them are shoving unstructured data into a vector store and praying. This layer shows what "AI-ready data" actually looks like — governed, chunked, grounded, with quality signals and full lineage from AI output back to source. It's the bridge between "we have data" and "compliance signed off on our AI."

> **The thesis still holds.** The implementation just proved there's a better way to deliver it than what we originally proposed. See the amendment section below.

---

### AI-Ready Zone — As Built (Amendment 2026-03-15)

**What was actually built:** A tool-use chat interface (`ai-ready-chat-interface`) where Claude queries the 5 consumable Iceberg tables via 7 validated Python tool functions. No embeddings, no RAG, no pre-computed documents, no vector store. Users type natural language questions; Claude calls validated tools; tools run parameterized DuckDB queries against real Iceberg data; Claude synthesizes the results into formatted answers with anomaly flags, fiscal alignment warnings, and cited numbers.

#### Architecture

```
User Question
    │
    ▼
┌──────────────────────────────────┐
│  Claude (tool_use)               │
│  System prompt (~3K tokens):     │
│  - 20 companies + metadata       │
│  - 25 metrics + 7 ratios         │
│  - Known anomalies (~20 flags)   │
│  - Fiscal year alignment rules   │
│  - Tool schemas                  │
└──────────┬───────────────────────┘
           │ tool calls
           ▼
┌──────────────────────────────────┐
│  7 Tool Functions                │
│  (validated, parameterized)      │
│                                  │
│  get_company_metric()            │
│  get_company_profile()           │
│  compare_companies()             │
│  rank_companies()                │
│  get_company_trend()             │
│  get_sector_summary()            │
│  get_ratio()                     │
└──────────┬───────────────────────┘
           │ DuckDB SQL
           ▼
┌──────────────────────────────────┐
│  5 Consumable Iceberg Tables     │
│  (125,814 rows, read-only)       │
└──────────────────────────────────┘
```

#### Deliverables (as built)

- 7 validated tool functions querying real Iceberg data via DuckDB
- Anomaly detection engine (7 rules covering Boeing negative equity, extreme D/E, fiscal misalignment, etc.)
- Number formatting library ($394.3B, 25.3%, rank #1 of 5)
- Dynamic system prompt built from live data (~3K tokens)
- Interactive CLI: `python -m src.ai_ready.cli`
- 116 tests (unit + integration against real Iceberg data), 442 total project tests
- OpenLineage lineage for the chat interface (reads-only from 5 consumable tables)
- Runtime lineage events via `governance.lineage_events` Iceberg table (infra-runtime-lineage spec)

#### Specs Delivered

| Spec | Status | Description |
|------|--------|-------------|
| `ai-ready-chat-interface` | COMPLETE | Tool-use chat interface — 7 tools, anomaly flags, fiscal alignment warnings, 116 tests |
| `ai-ready-dedup-tool-enrichment` | COMPLETE | Deduplication and enrichment pass on tool layer |

---

### AI-Ready Architecture Decision: Why Tool Use Beat RAG

This section documents why the delivered AI-Ready zone is architecturally superior to the original plan. The decision was driven by the `consumable-to-ai-ready-insights.md` insight report (which analyzed the actual data shape and query patterns) and a `genai-architect` review of the proposed approaches.

#### The original plan's assumptions were wrong

The original Phase 5 plan assumed the AI-Ready zone would look like most enterprise AI projects: vectorize the data, chunk it for context windows, build grounding documents, create evaluation datasets. This is the standard RAG playbook. It's also the wrong architecture for this data.

The key insight: **RAG solves the problem of finding relevant information in a large, unstructured corpus.** We don't have that problem. We have 5 clean, structured Iceberg tables with 125,814 rows, 50 passing DQ rules, and DuckDB that joins them in milliseconds. The data is already organized, governed, and queryable. Vectorizing it would be like building a search engine for a filing cabinet that's already alphabetized.

#### What each deprecated component would have actually done (and why it's unnecessary)

**Semantic embeddings + vector index:** Would have vectorized 547K financial facts into dense vectors, built a FAISS or similar index, and used cosine similarity to retrieve "relevant" facts for a user query. But relevance in structured financial data isn't semantic — it's parametric. "Apple's FY2024 revenue" is a lookup by (ticker=AAPL, metric=Revenue, fiscal_year=2024), not a nearest-neighbor search in embedding space. A `WHERE` clause is faster, cheaper, and deterministic. Embeddings add a probabilistic retrieval step to a problem that has an exact answer.

**Grounding documents (pre-computed fact sheets):** Would have pre-generated ~340 JSON documents (20 companies x 17 years), each containing a company's full financial profile for one year. The problem: these documents go stale the moment the underlying data changes (re-runs, corrections, new filings). They create a cache invalidation problem where none existed. DuckDB joins the 5 consumable tables in <50ms — there is no latency problem to solve with pre-computation. Every query returns live data from the governed Iceberg tables, not a potentially stale snapshot.

**Intelligent chunking:** Would have split financial data into context-window-optimized chunks with metadata headers. This solves a real problem — for unstructured text. Our data is already structured. A single company's full financial profile for one year fits in ~2K tokens. The entire 20-company roster fits in the system prompt at ~3K tokens. There is no chunking problem. The entire consumable zone could fit in a single Claude context window as raw JSON. Chunking would have added complexity (boundary management, overlap handling, metadata attachment) to solve a problem that doesn't exist at this data scale.

**Evaluation datasets (Q&A pairs):** Would have generated thousands of verified question/answer pairs for testing AI accuracy. Instead, 116 integration tests query real Iceberg data and assert correct results — with the added benefit that they run in CI and catch regressions. Pre-generated Q&A pairs are static; integration tests against live data are dynamic. The tests validate the same thing (AI gets the right answer) but can't go stale.

**Confidence signals on grounding documents:** Would have attached DQ scores to pre-computed documents so the AI could express uncertainty. Instead, anomaly flags are computed at query time by the tool functions. When `get_company_metric("BA", "Stockholders Equity", 2022)` returns a negative value, the anomaly checker fires and includes a flag explaining that Boeing's negative equity reflects accumulated losses, not extreme debt. This is more precise (anomaly checks run against the actual queried data point, not a pre-scored document) and can't go stale.

**MCP server:** Would have wrapped the governed data as MCP-protocol tools for any AI agent to call. What was built instead — Claude API tool use with 7 validated Python functions — achieves the same goal (AI calls structured functions to get governed data) with less infrastructure. The tool functions are the same regardless of whether they're exposed via MCP, REST, or direct API tool use. MCP can be added as a thin wrapper later if needed; the tool layer doesn't change.

#### What tool use gives us that RAG doesn't

1. **Deterministic retrieval.** "Apple's FY2024 revenue" returns exactly one number from exactly one table. RAG returns the top-K nearest neighbors and hopes the right one is in the set.

2. **Always-live data.** Every query hits the real Iceberg tables. No stale cache, no document refresh pipeline, no embedding re-indexing when data changes.

3. **Built-in anomaly detection.** Anomaly flags are computed at query time against the actual data point, not pre-scored against a snapshot. When Boeing's D/E ratio is 346x, the flag fires with the real number and the real explanation.

4. **Fiscal year alignment warnings.** Cross-company comparisons automatically detect when fiscal year ends differ and include a warning. This would be extremely difficult to pre-compute for all possible comparison pairs.

5. **Composability.** Claude can call multiple tools in sequence to answer complex questions ("Compare the 5-year revenue CAGR of all Technology companies, ranked by profitability") without us pre-computing every possible combination.

6. **Zero infrastructure.** No vector database. No embedding model. No document store. No refresh pipeline. Just DuckDB (already in the stack) and 7 Python functions.

7. **Auditability.** Every answer traces back through a tool call → DuckDB query → Iceberg table → governed data with full lineage. The tool call parameters are the audit trail. With RAG, the audit trail includes a probabilistic retrieval step that's harder to explain to a regulator.

#### The thesis is stronger, not weaker

The original thesis was: "AI-ready data means governed, grounded, auditable data that AI can consume." That thesis survives. The implementation just proved that for structured, governed data at this scale, the best AI interface is tool use over a query engine — not a vector store. The agents already cleaned, conformed, and governed the data through 4 zones. The AI-Ready zone's job was to expose that work to an LLM. Tool use does that with zero information loss and zero staleness risk. RAG would have added a lossy, potentially stale intermediate layer between the governed data and the AI.

The irony: the original plan proposed RAG because that's what "AI-ready" means in most enterprise contexts. But most enterprise AI projects need RAG because their data is unstructured, ungoverned, and scattered. This project's entire point was to fix that. Once you fix the data, you don't need RAG. **The governance pipeline made RAG unnecessary — which is the strongest possible argument for the governance pipeline.**

---

## Governance Demo: End-to-End Walkthrough

The flagship demo for this project: pick a single field in the consumable zone — say, JPMorgan's Q3 2024 Revenue — and show the full governance stack:

1. **Lineage** — trace from consumable back through base to the raw XBRL filing, every transformation logged in OpenLineage format
2. **CDE mapping** — this field is tagged as "Revenue" regardless of which XBRL tag JPMorgan used to report it
3. **Data quality** — the quality rules this field passed (not null, positive value, cross-validated against total revenue, temporally consistent)
4. **Classification** — sensitivity tag, proposed RLS policy
5. **Bitemporal history** — the amendment history via Iceberg snapshots, showing what the value was at different points in time
6. **Decision audit** — the agent's reasoning for every classification and transformation decision
7. **Data dictionary** — plain-English definition, owner, source, freshness

All generated automatically. No human entered any of this into a GUI. The agents produced it as a byproduct of doing the actual work.

**The argument to a CDO:** Your governance tools aren't the problem. Your manual process for feeding them is. Agents can generate the first draft of governance metadata in hours — lineage, quality rules, data dictionary entries, CDE mappings — and produce it in formats your existing catalog can import. The human review step stays; the manual authoring step goes away.

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

#### ~~Future Agents (AI-Ready Zone)~~ (DEPRECATED — see amendment)

> **AMENDMENT (2026-03-15):** These agents were not built. The AI-Ready zone was re-architected to use tool-use over DuckDB, eliminating the need for embedding, chunking, and pre-computed evaluation infrastructure. The `@primary-agent` built the tool functions, anomaly checker, and chat interface directly.

| Agent | Role | Phase | Status |
|-------|------|-------|--------|
| ~~`@embedding-engineer`~~ | ~~Semantic embeddings, vector index management~~ | ~~Phase 5~~ | DEPRECATED — embeddings unnecessary for structured data |
| ~~`@chunk-strategist`~~ | ~~Intelligent chunking for LLM consumption~~ | ~~Phase 5~~ | DEPRECATED — data fits in context without chunking |
| ~~`@eval-engineer`~~ | ~~Evaluation Q&A pairs with verified answers and lineage~~ | ~~Phase 5~~ | DEPRECATED — replaced by 116 integration tests |
| ~~`@mcp-engineer`~~ | ~~MCP server exposing governed data as AI-callable tools~~ | ~~Phase 5~~ | DEFERRED — tool functions built; MCP wrapper can be added later |

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

### Phase 4 — Consumable Zone (COMPLETE)

> **AMENDMENT (2026-03-15):** All 5 core data products delivered (4A + 4B tables). 4C (external data) and 4D (demo walkthrough) deferred to post-Phase 5 — the AI-Ready chat interface became the de facto demo, making the standalone walkthrough lower priority. External data enrichment remains valuable but non-blocking.

#### 4A — Core Data Products (from insight report Tier 1) — COMPLETE
- [x] `consumable-company-financials` (🟢 COMPLETE) — 26,894 rows, 20 companies, 25 business terms, FY2009-2026. One row per (company, business term, fiscal_year, fiscal_period). Concept collision resolution via primary concept preference. 8 DQ rules, all passing.
- [x] `consumable-financial-ratios` (🟢 COMPLETE) — 6,544 rows, 20 companies, 7 ratios (gross margin, operating margin, net margin, debt-to-equity, R&D intensity, SGA ratio, capex-to-revenue). Coverage: 9-20 companies per ratio. 10 DQ rules, all passing.
- [x] `consumable-period-over-period` (🟢 COMPLETE) — 65,445 rows, 20 companies, 25 business terms x 3 growth types (YoY, sequential, CAGR). 12 DQ rules, all passing.
- [x] `consumable-amendment-analysis` (🟢 COMPLETE) — 371 rows, 20 companies, 16 aggregate amendment stats. 10 DQ rules, all passing.
- [x] **Milestone:** Four queryable consumable tables — cross-company comparison, ratios, growth, amendment intelligence

#### 4B — Comparative Analysis (from insight report Tier 2) — PARTIALLY COMPLETE
- [x] `consumable-peer-comparison` (🟢 COMPLETE) — 26,559 rows, 17 companies across 5 multi-company sectors, 32 metrics with ranks/percentiles. 10 DQ rules, all passing.
- [ ] Data contracts per consumable — schema, freshness SLA, quality thresholds, breaking change policy *(deferred to Phase 6)*

#### 4C — External Data Enrichment (DEFERRED)
- [ ] `raw-ingest-stock-prices` — Daily stock prices for all 20 tickers (Yahoo Finance or Alpha Vantage). New raw data source. Join on (ticker, date). *(deferred — valuable but non-blocking for AI-Ready zone)*
- [ ] `consumable-valuation-ratios` — P/E, P/B, P/S, dividend yield. Requires stock prices + existing EPS/equity/revenue business terms. *(blocked by stock prices)*
- [ ] Consider: FRED API integration for macro indicators (GDP, CPI, rates) — join on date for macro-adjusted analysis. *(deferred)*

#### 4D — Demo & Documentation (DEFERRED)
- [ ] Build the end-to-end governance demo walkthrough — single field, full governance stack *(deferred — the AI-Ready chat interface serves as the primary demo for now)*
- [ ] Point-in-time query support — demonstrate `AT VERSION` queries via bitemporal module *(deferred)*
- [ ] **Milestone:** Full consumable zone with data products, external enrichment, governance, and demo-ready walkthrough *(partially met — 5 data products shipped, demo and external data deferred)*

#### Phase 4 — Zone Transition: Consumable → AI-Ready (COMPLETE, added)
> **AMENDMENT (2026-03-15):** Second zone transition added, following the same pattern as Phase 3.

- [x] @insight-manager produced `governance/insights/consumable-to-ai-ready-insights.md`
- [x] Analyzed 125,814 consumable rows across 5 tables
- [x] Ranked 13 AI-Ready data products by value/feasibility
- [x] Identified that the data is "structurally hostile to LLM consumption" without a query interface
- [x] Recommended tool-use architecture over RAG/embeddings (validated by genai-architect review)
- [x] **Milestone:** Data-driven architecture decision for AI-Ready zone — tool use over RAG

### Phase 5 — AI-Ready Zone (COMPLETE — RE-ARCHITECTED)

> **AMENDMENT (2026-03-15):** Phase 5 was completely re-architected based on the consumable-to-ai-ready insight report and a genai-architect review. See "AI-Ready Architecture Decision: Why Tool Use Beat RAG" in the Architecture section above for the full rationale. The original deliverables are listed with strikethrough; the actual deliverables follow.

#### Original Plan (DEPRECATED)
- ~~[ ] Semantic embeddings — vectorize entities, facts, business terms~~ *(DEPRECATED: unnecessary for structured data — see rationale)*
- ~~[ ] Grounding documents — structured fact sheets per company per quarter~~ *(DEPRECATED: DuckDB joins in <50ms, pre-computation adds staleness risk)*
- ~~[ ] Intelligent chunking — context-window-optimized documents with metadata~~ *(DEPRECATED: full company profile is ~2K tokens, no chunking problem at this scale)*
- ~~[ ] Evaluation datasets — verified Q&A pairs with source lineage~~ *(DEPRECATED: replaced by 116 integration tests against real Iceberg data)*
- ~~[ ] Confidence signals — quality scores surfaced as AI-consumable metadata~~ *(DEPRECATED: anomaly flags computed at query time by tool functions)*
- ~~[ ] AI-to-source lineage — full chain from AI claim to raw filing~~ *(PARTIALLY SUPERSEDED: runtime lineage events in governance.lineage_events table)*
- ~~[ ] MCP server (stretch goal) — expose governed data as AI-callable tools~~ *(SUPERSEDED: built as Claude API tool use — MCP wrappable later)*
- ~~[ ] **Milestone:** Full AI-ready data product — grounded, chunked, evaluated, with lineage from AI output to SEC filing~~

#### As Built (2026-03-15)
- [x] `ai-ready-chat-interface` (🟢 COMPLETE) — Tool-use chat interface: 7 validated Python functions query 5 consumable Iceberg tables via DuckDB. Claude never writes SQL. Anomaly flags, fiscal alignment warnings, number formatting ($394.3B, 25.3%), 116 tests.
- [x] `ai-ready-dedup-tool-enrichment` (🟢 COMPLETE) — Deduplication and enrichment pass on tool layer.
- [x] `infra-runtime-lineage` (🟢 COMPLETE) — Runtime lineage events captured in `governance.lineage_events` Iceberg table. Every promote function emits START/COMPLETE/FAIL events with row counts, snapshot IDs, and DQ results.
- [x] Interactive CLI: `python -m src.ai_ready.cli` — natural language financial analysis over governed data
- [x] 442 tests passing (116 new in AI-Ready zone)
- [x] **Milestone:** AI-ready chat interface querying governed Iceberg data via validated tool functions — no RAG, no embeddings, no pre-computed documents. Every answer traces back through tool call → DuckDB query → Iceberg table → governed data with full upstream lineage.

### Infrastructure Specs (Added During Build — Not in Original Plan)

> **AMENDMENT (2026-03-15):** The following infrastructure specs were added during Phases 2-5 to address real issues discovered during implementation. None were in the original build plan. This is expected — you don't know what infrastructure you need until you start building on it.

| Spec | Phase Added | Why It Was Needed |
|------|-------------|-------------------|
| `infra-dq-execution-framework` | Phase 2 | DQ rules need a runner. Original plan assumed DQ rules would "just work" — in practice, needed a framework for rule definition (JSON), execution (DuckDB SQL), result storage, and scorecard generation. |
| `infra-load-date-tracking` | Phase 2 | Promote functions needed idempotency — without load date tracking, re-running a pipeline doubled the data. |
| `infra-governance-model-alignment` | Phase 2-3 | Governance model refactoring driven by the insight that CDEs are flags on business terms, not standalone entities. Required restructuring `governance/models/` and business glossary. |
| `infra-architect-remediation` | Phase 4 | Principal Data Architect review (external) identified issues with lineage being "documentation masquerading as lineage" and DQ rules lacking semantic/negative testing. |
| `infra-runtime-lineage` | Phase 5 | Converted static lineage JSON docs into runtime events captured in a `governance.lineage_events` Iceberg table. Every promote function now emits START/COMPLETE/FAIL events with row counts and snapshot IDs. |
| `infra-semantic-dq-and-negative-testing` | Phase 5 | In progress. Addresses architect feedback: DQ rules need semantic validation (accounting equation, ratio consistency) and negative testing (rules that should fail on bad data). |
| `base-conformed-facts` | Phase 2 | Conformed facts table joining financial_facts + entity_mappings + tag_normalization. Not anticipated in original plan — emerged as the natural output of entity resolution + tag normalization. |
| `base-fiscal-year-fix` | Phase 2 | Bug fix: fiscal year boundaries were incorrect for non-December FY-end companies (Apple, Microsoft, PG, Visa, Walmart). Discovered during EDA. |

### Phase 6 — Open Source Prep (Weeks 14-15)
- [ ] Clean up repo for public consumption
- [ ] Write README that tells the story — raw to base to consumable to AI-ready, full governance at every layer
- [ ] Add contributing guidelines
- [ ] License selection (MIT or Apache 2.0)
- [ ] Record a demo or write a walkthrough — the single-field governance deep dive AND the AI-ready demo
- [ ] Publish

---

---

## Open Questions

- [x] Which 10-20 companies specifically? → **RESOLVED:** 20 companies selected across 8 sectors (Technology, Financials, Healthcare, Consumer Staples, Consumer Discretionary, Industrials, Energy, Communication Services). Includes AAPL, MSFT, GOOGL, INTC, NFLX, JPM, GS, BRK.A, V, UNH, PFE, JNJ, WMT, AMZN, PG, BA, CAT, XOM, CVX, TSLA.
- [x] How deep on RLS? → **RESOLVED:** Pattern demonstration only. `@policy-engineer` produced RLS policy definitions as governance artifacts but no functional enforcement. Sufficient for the thesis (demonstrating the pattern on public data).
- [ ] Do we want a simple web UI for the point-in-time queries? (Nice to have, not essential) → **Still open.** The CLI chat interface (`python -m src.ai_ready.cli`) is the current demo. A web UI would be Phase 6 polish.
- [x] Iceberg catalog layer — start without one, add Polaris/Lakekeeper later if needed? → **RESOLVED:** No catalog server. Local file storage + DuckDB Iceberg extension has been sufficient for the entire build. Zero infrastructure requirement validated.

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
