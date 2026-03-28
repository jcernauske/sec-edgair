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

## What if you could use AI adversarially to make your data pipelines resilient?

Most DQ rules are written to pass against clean data. They're never asked to defend themselves against garbage.

That's a problem. Because production data doesn't arrive clean. It arrives with nulls where nulls shouldn't be, timestamps from 1900, fiscal years set to 1850, duplicate rows, orphaned keys, and values that passed every upstream check and are still wrong. Your DQ rules need to prove they can catch that -- not just the test data you wrote them for.

So we built a Chaos Monkey.

<!-- CHAOS MONKEY CONCEPT VISUAL: Two-panel illustration. Left panel: "DQ rules passing against clean data" -- simple green checkmarks, labeled 'false confidence'. Right panel: "DQ rules surviving adversarial injection" -- monkey throwing garbage, rules catching it, labeled 'actual confidence'. -->

An AI agent whose only job is to break things on purpose. It injects realistic garbage into a shadow copy of production data -- nulls in required fields, impossible fiscal years, duplicate primary keys, fake accession numbers, values that are plausible but wrong. It violates all 10 DQ dimensions on every run: Completeness, Validity, Uniqueness, Consistency, Accuracy, Reasonableness, Freshness, Volume, Referential Integrity, Coverage. Randomized strategies each time. The monkey doesn't know what the DQ rules check for -- it only has access to the physical schema. If it knew, it would work around them. That's the point.

Three layers of safety ensure it can never run against real data: a config flag, an environment variable check (`SEC_EDGAIR_ENV=dev`), and output path validation that hard-blocks any write outside the shadow zone. Any layer fails, `sys.exit()`. No fallback.

### The first run

<!-- BEFORE/AFTER CARD: Display as a dramatic before/after split. Left side (red/warning): "Run 1 -- 20% detection". Right side (green): "After remediation -- 100% detection". Large typography. -->

The first real run injected 38,317 corruptions across all 10 dimensions. Detection rate: 20%. Eight of the 10 DQ dimensions had zero rule coverage. The rules that existed were catching what they were built to catch. They'd just never been asked about anything else.

That failure was the most useful thing the pipeline produced. The after-action report itemized every gap -- which dimensions, which strategies, which field corruptions went undetected. That report drove 15 new DQ rules.

### After remediation

<!-- STRESS TEST METRICS: Display as a compact 2x2 metric grid alongside a small "5-run streak" visual (5 green checkmarks in a row) -->

| Metric | Value |
|--------|-------|
| Total runs | 13 |
| Total corruptions injected | 498,121 |
| Detection rate before remediation | 20% |
| Detection rate after remediation | 100% |
| Stress test | 191,585 adversarial corruptions across 5 consecutive randomized runs |
| Escapes | 0 |

Five consecutive runs. Different random seeds, different strategy mixes, 25 corruption strategies targeting 28 fields. Every corruption caught. Zero escapes.

<!-- AFTER-ACTION REPORT PREVIEW: Display as a collapsed/expandable document preview or a stylized "report card" showing the four sections: Injection Summary, DQ Results, Reconciliation Scorecard, Suggested Remediations. The goal is to show the artifact is real and structured, not just a log file. -->

Each run produces an after-action report: what the monkey injected, what the DQ rules caught, a reconciliation scorecard by dimension, and suggested remediations for anything that slipped through. When the detection rate was 20%, that report told us exactly what to fix. When it reached 100%, the report confirmed it.

The 20% result was not a failure to be hidden. It was the feature working correctly.

[See the chaos reports -->](governance.md#chaos-monkey)

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

**Source:** [github.com/jcernauske/sec-edgair](https://github.com/jcernauske/sec-edgair)

<!-- FOOTER NAV: Link to all pages -->

---

[Architecture](architecture.md) | [Governance](governance.md) | [Results](results.md) | [Methodology](methodology.md) | [Session Logs](sessions.md)
