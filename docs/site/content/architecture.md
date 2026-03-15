---
title: Architecture - SEC EDGAIR
description: "4-zone medallion architecture with DuckDB + Apache Iceberg, 14 Iceberg tables, runtime lineage, and DQ gates on every promote. Reviewed by a @principal-data-architect agent: grade A."
---

# Architecture

**For the skeptic who wants to see the wiring.**

You have seen AI-generated pipelines that look impressive in a slide deck. You want to know if this one holds up when you pull on the threads. Here is every thread.

## The Zones

```
SEC EDGAR API/Bulk ZIP
    |
    v
raw.xbrl_company_facts              547,398 facts, 20 companies, 19 columns
    |
    v
base.entity_mappings                20 CIK -> canonical company identity
base.concept_mappings               3,285 XBRL concept -> business term classifications
base.financial_facts                547K enriched facts, 28 columns
base.conformed_facts                28,849 rows -- one authoritative fact per grain
base.fiscal_calendar                1,483 fiscal periods
base.amendment_tracking             264K supersession pairs
    |
    v
consumable.company_financials       28,849 rows -- cross-company comparison
consumable.financial_ratios         7,102 rows -- 7 computed ratios
consumable.period_over_period       71,402 rows -- YoY growth + 5yr CAGR
consumable.peer_comparison          28,633 rows -- sector ranks + percentiles
consumable.amendment_analysis       371 rows -- restatement patterns
    |
    v
AI-Ready Chat Interface             8 tool functions -> Claude API -> answers
```

14 Iceberg tables. Each zone reads only from the prior zone's tables via PyIceberg scan -> Arrow -> DuckDB. No zone reaches backward more than one level.

## Storage: DuckDB + Apache Iceberg

**DuckDB** is the compute engine. In-process, zero infrastructure, anyone who clones the repo runs it immediately. No Docker, no cloud account, no catalog server.

**Apache Iceberg** is the table format. Open standard with built-in time travel via snapshots. Every write creates a new snapshot. Previous versions are always queryable. The same code works against local storage or S3/Databricks/Snowflake.

Why this matters: Iceberg is what every enterprise is evaluating for their lakehouse. This project produces Iceberg tables that are directly portable to any Iceberg-compatible environment.

Source: [`src/infra/iceberg_setup.py`](../../src/infra/iceberg_setup.py), spec: [`docs/specs/infra-setup-duckdb-iceberg.md`](../../docs/specs/infra-setup-duckdb-iceberg.md)

## Zone Boundaries

Each zone has a reason to exist:

| Zone | Purpose | Tables | Key Logic |
|------|---------|--------|-----------|
| **Raw** | Land data as-is. Profile, classify, but never transform. | 1 | XBRL bulk ingest, PII scan (none found), data classification |
| **Base** | Normalize, conform, govern. Domain complexity lives here. | 7 | Entity resolution, tag normalization (3,285 -> 25), fiscal calendar, supersession, amendment tracking |
| **Consumable** | Purpose-built analytical tables. Opinionated about what questions they answer. | 5 | Ratios, growth, peer rankings, amendment intelligence |
| **AI-Ready** | Expose governed data to an LLM. | 0 (application layer) | 8 tool functions over DuckDB, no new tables |

The AI-Ready zone deliberately creates no new Iceberg tables. It queries the consumable tables via validated Python functions. Claude never writes SQL.

## The Conformed Facts Layer

The most important architectural decision in the pipeline: `base.conformed_facts`.

Raw XBRL data has a problem: multiple concepts map to the same business metric. Apple might report Revenue as `RevenueFromContractWithCustomerExcludingAssessedTax` in one filing and `Revenues` in another. After tag normalization, you can have 3-5 competing facts for the same (company, metric, year).

`base.conformed_facts` resolves this. One authoritative fact per (company, metric, year, period), selected by concept priority rules stored as a governance artifact in [`governance/conformation/concept-priority-rules.json`](../../governance/conformation/concept-priority-rules.json). Every consumable table reads from conformed_facts, not from financial_facts directly.

This matters because:
- Business logic (collision resolution, unit filtering, supersession filtering) lives in the base zone, not scattered across 5 consumable tables
- The concept priority rules are a versioned JSON artifact, not buried Python config
- Adding a new XBRL concept mapping is a governance change, not a code change

From the architect re-review:

> "The `base.conformed_facts` table is architecturally sound. It answers a different question than `base.financial_facts`: 'what is the single best value for each metric?' vs 'what did the filings say?' The grain is correct, the lineage columns are well-designed, and the build logic is clean. This is the right abstraction boundary."

Source: [`governance/reviews/principal-data-architect-re-review.md`](../../governance/reviews/principal-data-architect-re-review.md)

## Runtime Lineage

Every promote function emits START/COMPLETE/FAIL events to a `governance.lineage_events` Iceberg table.

Each event captures:
- `run_id` -- pairs START and COMPLETE events
- `snapshot_id` -- the Iceberg snapshot created by this write
- `output_row_count` -- how many rows were written
- `dq_passed` -- whether DQ rules passed
- `duration_ms` -- how long the promote took
- `error_message` -- what went wrong (on FAIL events)

All 11 promote functions are instrumented. Lineage write failures log warnings but do not block the pipeline -- the correct design for a cross-cutting concern.

The static lineage JSON files in `governance/lineage/` are now *derived* from runtime data via `python -m src.infra.lineage generate-docs`. They are projections of reality, not primary sources.

From the architect re-review:

> "The difference between 'we have lineage docs' and 'every promote emits runtime events to an Iceberg table with snapshot IDs, row counts, and DQ results' is the difference between aspiration and engineering."

Source: [`src/infra/lineage.py`](../../src/infra/lineage.py), spec: [`docs/specs/infra-runtime-lineage.md`](../../docs/specs/infra-runtime-lineage.md)

## DQ Gates

128 SQL-based DQ rules across 9 dimensions, executed against real Iceberg tables.

| Dimension | Example |
|-----------|---------|
| Uniqueness | No duplicate grains in conformed_facts |
| Completeness | No null business_term_id in financial_facts |
| Validity | All fiscal_year values between 2000 and 2030 |
| Consistency | companies_reporting count matches actual distinct CIKs |
| Freshness | Load dates within expected recency |
| Referential Integrity | Every company_financials.company_cik exists in entity_mappings |
| Volume | Row counts within expected ranges |
| Accuracy | No superseded facts leaked through filters |
| Reasonableness | Operating margins between -100x and 100x (evidence-based) |

P0 failures **block** the pipeline. No data is written to Iceberg until DQ passes.

All promote functions in the base zone call `validate_after_write()` directly. Consumable zone DQ gates run via CLI build commands.

Source: 11 rule files in [`governance/dq-rules/`](../../governance/dq-rules/), execution engine: [`src/infra/dq_runner.py`](../../src/infra/dq_runner.py)

## AI-Ready: Why Tool Use, Not RAG

The original plan called for embeddings, vector stores, RAG, pre-computed grounding documents, and an MCP server. All of it was scrapped.

The insight report from the consumable-to-AI-ready zone transition identified the problem: **RAG solves for finding relevant information in a large, unstructured corpus. We don't have that problem.** We have 5 clean, structured Iceberg tables with 136K rows and DuckDB that joins them in milliseconds.

What was built instead: 8 validated Python tool functions that Claude calls to answer questions. No embeddings, no vector store, no pre-computed documents, no document refresh pipeline.

| What RAG would have added | What tool use provides instead |
|---------------------------|-------------------------------|
| Probabilistic retrieval (top-K nearest neighbors) | Deterministic retrieval (WHERE clause) |
| Stale pre-computed documents | Always-live queries against Iceberg |
| Embedding re-indexing on data changes | No index to maintain |
| Chunking and boundary management | Data fits in context without chunking |
| Vector database infrastructure | Zero infrastructure (DuckDB is already in the stack) |

From the architect review:

> "Tool use over DuckDB is the correct architecture for this dataset. At 136K rows across 5 structured tables, the data fits comfortably in memory, DuckDB runs joins in milliseconds, and Claude can express any analytical query through the 7 tool functions."

Source: [`docs/specs/ai-ready-chat-interface.md`](../../docs/specs/ai-ready-chat-interface.md), insight report: [`governance/insights/consumable-to-ai-ready-insights.md`](../../governance/insights/consumable-to-ai-ready-insights.md)

## The Architect Review

<!-- IMAGE: Obama medal meme. Caption: "When your AI agent reviews your AI agents' work." -->

Full disclosure: the @principal-data-architect is itself an AI agent. So yes, this is AI reviewing AI. We'll pause while you make the Obama-giving-himself-a-medal joke.

Done? Good. Now read the actual findings -- because they were real, and the fixes were structural. The value of this review isn't impartial human judgment. It's that a systematic architectural review with a defined rubric caught problems that were then systematically fixed and re-verified. The findings, the fixes, and the re-review are all in the repo for you to evaluate.

The first review graded it B+.

**Original findings (B+):**
1. In-memory dedup pattern does not scale beyond 20 companies
2. Consumable promote code lacks DQ gates that exist in base zone
3. Anomaly checker hardcodes Boeing-specific rules instead of deriving from data
4. No negative testing in verification scripts
5. Static lineage files are "documentation masquerading as lineage"
6. Concept priority rules buried in Python config, not a governance artifact
7. Missing tool function for amendment_analysis data

**What was fixed:**
1. DuckDB anti-join dedup via `filter_existing_records()` -- columnar engine, single column, hash join
2. `validate_after_write()` added to all consumable CLI build commands
3. Generic anomaly detection -- any company with negative equity, not just Boeing
4. `scripts/verify_negative.py` with 10 targeted absence checks
5. Runtime lineage events to `governance.lineage_events` Iceberg table
6. Concept priority rules extracted to `governance/conformation/concept-priority-rules.json`
7. `get_amendment_summary` tool added (tool #8)

**Re-review grade: A.**

> "The remediation work is thorough, well-targeted, and high-quality. Every top risk from the original review has been addressed."

> "Would I ship this? To the stated audience, yes. Would I stake my reputation on it? On the data quality, verification rigor, and architectural soundness -- yes. On production readiness at scale -- still no, but the path to production is clearer now."

Source: original review [`governance/reviews/principal-data-architect-review.md`](../../governance/reviews/principal-data-architect-review.md), re-review [`governance/reviews/principal-data-architect-re-review.md`](../../governance/reviews/principal-data-architect-re-review.md)

## What is not production-ready

The architect agent was honest. So are we.

- **Incremental refresh.** The pipeline does full rebuilds. For 20 companies this takes seconds. At production scale, you need change detection.
- **Concurrent access.** The SQLite-backed PyIceberg catalog does not support concurrent writers.
- **Monitoring.** DQ rules run on-demand via CLI. Production needs scheduled execution with alerting.
- **Memory at scale.** `read_with_duckdb()` still materializes full tables as Python dicts. The dedup path is fixed, but the read path would need attention at 100x scale.

These are known, documented, and architectural -- not bugs. The path to production is clear.

---

[Back to home](index.md) | [Governance controls](governance.md) | [Results](results.md)
