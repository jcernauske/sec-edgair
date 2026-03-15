---
title: SEC EDGAIR
description: "AI agents don't just consume clean data. They create it. 14 specialized agents took raw SEC EDGAR filings and delivered governed, tested, AI-ready financial data -- with 128 DQ rules, 28 data models, and an A from the architect."
---

# Everyone says you can't use AI until you clean up your data.

## But what if you could use AI to get your data ready for AI?

14 AI agents took raw SEC EDGAR XBRL filings -- 547,398 financial facts from 20 public companies -- and delivered them as clean, modeled, governed, AI-ready data products. Not by consuming clean data. By *making* data clean.

Every business term, every data quality rule, every lineage event, every data model was produced by an AI agent and approved by a human. The conventional wisdom is wrong. AI is not just the consumer of clean data -- it is the tool that makes data clean.

<!-- METRIC CARDS: Display as a 2x3 or 3x2 grid of metric cards -->

| Metric | Value |
|--------|-------|
| DQ Rules | 128 across 9 dimensions (127 pass, 1 P1 advisory) |
| Verified | 88/88 checks against real 10-K filings |
| Architect Grade | A (up from B+, after real remediation) |
| Business Terms | 54 defined, mapped, approved |
| Data Models | 28 artifacts (conceptual, logical, physical) |
| Tests | 466 passing |

<!-- END METRIC CARDS -->

## The Pipeline

<!-- PIPELINE DIAGRAM: Render as a styled horizontal flow, not an image -->

```
SEC EDGAR XBRL  -->  Raw Zone   -->  Base Zone    -->  Consumable Zone  -->  AI-Ready Chat
20 companies         547K facts      786K rows         136K rows             8 tool functions
17 years of data     as-landed       normalized        5 data products       natural language
                     profiled        governed          ratio, growth,        "What was Apple's
                     classified      modeled           peer, amendment       revenue in 2024?"
```

Every zone transition is governed. Every promote emits runtime lineage events to an Iceberg table. Every table passes DQ rules before data is written. P0 failures block the pipeline.

## Who is this for?

### Chief Data & Analytics Officers

You want to know if AI agents can actually do the work your data teams spend months on -- modeling, governance, quality rules, documentation. The answer is yes, and the numbers prove it.

[See the results -->](results.md)

### Data Architects

You are skeptical. You have seen AI-generated code that looks good in a demo and falls apart under scrutiny. This project was reviewed by a @principal-data-architect agent -- yes, another AI agent -- who gave it a B+ the first time, then watched the team fix every finding and re-graded it an A. We know. Obama giving himself a medal. But read the findings -- they were real, and the fixes were real.

[See the architecture -->](architecture.md)

### Auditors & Compliance

You need to know where the human controls are. There are 4 human approval gates, a global `REQUIRE_HUMAN_APPROVAL` toggle, runtime lineage with snapshot IDs, and a full audit trail. Every row traces back to its SEC filing.

[See the governance controls -->](governance.md)

## What makes this different

This is not a demo. This is not synthetic data with placeholder governance.

- **Real data.** 547,398 financial facts from SEC EDGAR -- Apple, Microsoft, JPMorgan, Tesla, and 16 others.
- **Real verification.** 88 checks against actual 10-K annual reports. Apple's FY2023 revenue matches. Goldman Sachs' net income matches. Every company, every fiscal year-end pattern.
- **Real governance artifacts.** 54 business terms in a structured glossary. 128 DQ rules executed against Iceberg tables. 28 data model artifacts with Mermaid diagrams. Runtime lineage events with snapshot IDs and row counts.
- **Real architectural scrutiny.** A @principal-data-architect *agent* reviewed the full pipeline, filed 7 findings, and watched them get fixed. Yes, AI reviewing AI -- but the findings were legitimate and the fixes were structural. The re-review grade: A.
- **Real transparency.** 38 session logs documenting every decision, every mistake, every architectural debate. Nothing hidden.

## Built with

**Stack:** Python 3.11+, DuckDB + Apache Iceberg, Claude Code with 14+ specialized agents

**Source:** [github.com/jcernauske/sec_edgair](https://github.com/jcernauske/sec_edgair)

<!-- FOOTER NAV: Link to all pages -->

---

[Architecture](architecture.md) | [Governance](governance.md) | [Results](results.md) | [Methodology](methodology.md) | [Session Logs](sessions.md)
