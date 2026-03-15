---
title: AI-Ready - SEC EDGAIR
description: "We planned RAG, embeddings, and vector databases. Then we looked at the actual data and scrapped all of it. This is the story of why tool use over DuckDB beat the conventional AI playbook."
---

# We Designed the Whole RAG Pipeline. Then We Threw It Away.

**For the data architect who has watched a RAG project deliver approximate answers to questions that have exact answers.**

The original plan was conventional. Respectable, even. We were going to do what every enterprise AI project does: chunk the financial data into documents, embed them into vectors, store them in a vector database, and build a retrieval-augmented generation pipeline. We had the whole thing designed. We had the agents named.

Then we looked at the actual data. And we scrapped all of it.

This is the story of why.

## Act I: The Original Plan

The build plan for the AI-Ready zone read like every enterprise AI project brief you have seen. Phase 5 had four dedicated agents:

- **@embedding-engineer** -- vectorize 547K financial facts into dense embeddings, build a FAISS index, enable semantic retrieval
- **@chunk-strategist** -- split financial data into context-window-optimized chunks with metadata headers and overlap management
- **@eval-engineer** -- generate thousands of question/answer pairs from governed data for testing AI accuracy
- **@mcp-engineer** -- build a Model Context Protocol server exposing governed data as AI-callable tools

The deliverables were standard:

- Vector index of all entities, facts, and CDEs
- RAG-ready grounding documents per company per quarter (~340 pre-computed JSON documents)
- Intelligently chunked context documents with metadata
- Evaluation dataset with verified Q&A pairs and source lineage
- Quality-aware confidence signals for AI consumption
- Full AI-to-source lineage from AI claim to raw SEC filing

This is what "AI-ready data" looks like in every slide deck, every vendor pitch, every architecture diagram. Nobody would have questioned it.

## Act II: The Pivot Moment

Between the consumable zone and the AI-ready zone, the @insight-manager agent ran its standard zone transition analysis. It queried all 5 consumable Iceberg tables -- 125,814 rows of clean, governed financial data -- and produced a report.

The opening line was the diagnosis:

> "The data is **structurally hostile to LLM consumption**: answering 'summarize Apple's financial health' requires 5 separate table queries across 118 columns, fiscal year alignment math, and knowledge of which numbers need caveats."

But the recommendation was not "build a better RAG pipeline." It was the opposite. The insight report ranked 13 potential AI-Ready data products, and the top recommendations were pre-computed JSON documents and tool functions -- not embeddings.

Then came the architecture review. The prompt was blunt: "Be brutally honest about what's actually needed vs. what's over-engineering." The architect's analysis was decisive:

> "RAG solves the problem of finding relevant information in a large, unstructured corpus. We don't have that problem. We have 5 clean, structured Iceberg tables with 125K rows, 50 passing DQ rules, and DuckDB that joins them in milliseconds."

Five of the seven originally planned specs were cut. The entire RAG pipeline -- embeddings, vector store, pre-computed documents, chunking -- was deprecated. In its place: 8 Python functions that Claude calls as tools.

## Act III: Why RAG Was Wrong for This Data

The conventional AI playbook assumes your data looks like documents. Contracts, reports, policies, emails -- unstructured text where the challenge is finding the relevant passage. RAG was designed for that problem. It is brilliant for that problem.

Financial data in governed Iceberg tables is not that problem.

Here is what would have actually happened if we had built the RAG pipeline:

**Semantic embeddings would have added a probabilistic retrieval step to data that already has exact answers.** "What was Apple's revenue in FY2024?" is not a semantic similarity search. It is a lookup: `WHERE ticker = 'AAPL' AND business_term_name = 'Revenue' AND fiscal_year = 2024`. A `WHERE` clause is faster, cheaper, and deterministic. The embedding adds latency, infrastructure, and a failure mode (the correct document might not be in the top-K results) for zero benefit.

**Pre-computed grounding documents would have created a cache invalidation problem where none existed.** We would have generated ~340 JSON documents (20 companies x 17 years), each containing a company's full financial profile. These documents go stale the moment the underlying data changes. DuckDB joins the 5 consumable tables in under 50 milliseconds. There is no latency problem to solve with pre-computation. Every query returns live data from governed Iceberg tables, not a potentially stale snapshot.

**Intelligent chunking would have added complexity to solve a problem that does not exist at this scale.** A single company's full financial profile for one year is approximately 2,000 tokens. The entire 20-company roster fits in the system prompt at approximately 3,000 tokens. The consumable zone -- all 125,814 rows -- could fit in a single Claude context window as raw JSON. There is no chunking problem. Chunking would have added boundary management, overlap handling, and metadata attachment logic to solve a nonexistent problem.

**Evaluation Q&A pairs would have been static snapshots of something better tested dynamically.** Instead of generating thousands of pre-computed question/answer pairs, 116 integration tests query real Iceberg data and assert correct results. The tests run in CI and catch regressions. Pre-generated Q&A pairs are frozen at creation time. Integration tests against live data are always current.

**A vector database would have added infrastructure for zero analytical value.** No Docker container to run. No embedding model to host or pay for. No index to rebuild when data changes. No similarity threshold to tune. Just DuckDB, which was already in the stack.

## The Comparison

| | RAG Pipeline | Tool Use Pipeline |
|---|---|---|
| **Retrieval** | Probabilistic (top-K nearest neighbors in embedding space) | Deterministic (`WHERE` clause returns exact match) |
| **Data freshness** | Stale until re-embedded and re-indexed | Always live -- every query hits real Iceberg tables |
| **Infrastructure** | Vector database + embedding model + refresh pipeline | Zero additional (DuckDB already in stack) |
| **Auditability** | Retrieval step is probabilistic and hard to explain | Tool call parameters are the audit trail |
| **Precision** | Embeddings lose exact financial figures | SQL returns exact values to the penny |
| **Chunking** | Required -- boundary management, overlap, metadata | Not needed -- full company profile is ~2K tokens |
| **Cost per query** | Embedding + retrieval + generation | Generation only (~$0.03/question) |
| **Anomaly detection** | Pre-scored on documents (goes stale) | Computed at query time against actual data point |
| **Fiscal alignment** | Would need to pre-compute all possible comparison pairs | Computed dynamically for any comparison |
| **Failure mode** | Correct document not in top-K results | Tool returns error with helpful message |

## What We Didn't Build

These agents were designed, named, and ready to go. They were never built.

| Agent | What It Would Have Done | Why It Was Cut |
|-------|------------------------|----------------|
| **@embedding-engineer** | Vectorize 547K financial facts into dense embeddings, build and maintain a FAISS index | Embeddings add a lossy, probabilistic retrieval step to data that has exact answers via SQL |
| **@chunk-strategist** | Split financial data into context-window-optimized chunks with metadata headers and overlap | Data fits in context without chunking. A company's full profile is ~2K tokens. |
| **@eval-engineer** | Generate thousands of verified Q&A pairs for testing AI accuracy | Replaced by 116 integration tests that query real Iceberg data and catch regressions |
| **@mcp-engineer** | Build an MCP server exposing governed data as tools | Superseded by direct Claude API tool use. Same functions, simpler implementation. MCP wrappable later. |

This is the cutting room floor. Every one of these agents would have produced governance artifacts, session logs, specs, and DQ rules. The project would have been larger, more complex, and delivered worse answers.

## Act IV: What Was Actually Built

8 validated Python functions. That is the entire AI-Ready zone.

| Tool Function | What It Does | Example Question |
|--------------|-------------|-----------------|
| `get_company_metric()` | Returns a specific metric for a company with formatting, YoY growth, sector rank, and anomaly flags | "What was Apple's revenue in FY2024?" |
| `get_company_profile()` | Returns all metrics, ratios, and amendment stats for a company in one call | "Tell me about Boeing's FY2023 financials" |
| `compare_companies()` | Side-by-side comparison with delta analysis and fiscal alignment warnings | "Compare Apple and Microsoft on profitability" |
| `rank_companies()` | Ranks all companies (or a sector) by any metric | "Which company has the highest net margin?" |
| `get_company_trend()` | Multi-year time series with YoY changes and trend direction | "How has Tesla's revenue changed over time?" |
| `get_sector_summary()` | Sector-level aggregates: average, median, leader, laggard | "How is the Technology sector performing?" |
| `get_ratio()` | Returns a computed ratio with its components and sector context | "What is Apple's debt-to-equity ratio?" |
| `get_amendment_summary()` | Amendment and restatement patterns for a company | "Has Goldman Sachs had many restatements?" |

Each function validates inputs, runs parameterized DuckDB queries against real Iceberg data, formats numbers ($394.3B, 25.3%, rank #1 of 5), checks anomaly rules, and returns a structured dictionary. Claude never writes SQL. Claude never sees raw data. Claude calls typed functions and gets back formatted, flagged, auditable results.

The anomaly checker fires automatically. When Boeing's debt-to-equity ratio comes back at 346x, the tool attaches a flag: "Extreme leverage ratio driven by near-zero or negative equity denominator." When comparing Apple (September fiscal year) to Microsoft (June fiscal year), the tool attaches a warning: "Fiscal year ends differ. These cover different 12-month calendar periods." The LLM does not need to know these rules. The tools enforce them.

## Act V: The Irony

This is the part that matters.

The entire SEC EDGAIR project exists to prove one thesis: AI agents can take raw, messy data and deliver it as clean, governed, semantically modeled data products. The pipeline transforms 547,398 raw XBRL facts through four zones -- raw, base, consumable, AI-ready -- with 128 DQ rules, 54 business terms, 28 data models, and runtime lineage at every step.

The original AI-Ready plan assumed that after all this governance work, you would still need to approximate the data through embeddings and retrieve it probabilistically through vector search. That assumption was wrong. The governance pipeline did its job so well that the data was already perfectly queryable. You do not need approximate retrieval for data that is clean, modeled, and indexed. You just query it.

The governance pipeline made RAG unnecessary.

And that is the strongest possible argument for the governance pipeline.

Most enterprise AI projects reach for RAG because their data is a mess. Documents are scattered across SharePoint. Tables have no consistent naming. Business terms mean different things in different departments. Fiscal calendars are not aligned. Data quality is unknown. In that world, RAG is the right answer -- because you cannot trust a direct query against data you have not governed.

But if you do the governance work first -- if you normalize the entities, conform the tags, model the dimensions, validate the quality, align the fiscal calendars, and track the lineage -- then you have data that answers direct queries precisely. You do not need a search engine for a filing cabinet that is already alphabetized.

The conventional wisdom says: fix your data, then build AI on top of it. That is correct. But it implies that "building AI on top of it" means RAG. This project proves that is not always true. Sometimes "building AI on top of it" means giving the LLM 8 functions and a DuckDB connection.

## What This Means For Your Project

If you are building an enterprise AI project and reaching for RAG as the default architecture, ask yourself two questions:

**1. Is your data structured or unstructured?** If it lives in tables with known schemas, defined business terms, and consistent grain -- RAG is solving a problem you do not have. A query engine is faster, cheaper, and deterministic.

**2. Have you governed the data first?** If the answer is no, RAG might be necessary -- not because it is the right architecture, but because it papers over the governance gap. Embeddings can find "relevant" documents even when naming is inconsistent. Vector search can surface related records even when joins are broken. RAG is a compensating control for ungoverned data.

The dependency is backwards in most organizations. They build RAG to compensate for bad data instead of fixing the data to eliminate the need for RAG. Both paths work. One of them produces a permanent asset (governed data). The other produces a fragile pipeline that depends on approximate retrieval continuing to return the right results.

This project took the longer path. The results speak for themselves: 88/88 verification checks against real 10-K filings, every answer traceable from chat response to raw SEC filing, zero vector infrastructure, zero embedding costs, zero staleness risk.

> "Tool use over DuckDB is the correct architecture for this dataset. At 136K rows across 5 structured tables, the data fits comfortably in memory, DuckDB runs joins in milliseconds, and Claude can express any analytical query through the tool functions."
>
> -- @principal-data-architect agent, re-review (grade: A)

The governance pipeline made RAG unnecessary -- which is the strongest possible argument for the governance pipeline.
