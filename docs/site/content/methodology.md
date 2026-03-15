---
title: Methodology - SEC EDGAIR
description: "14+ specialized AI agents, each with a defined role and scope. Spec-driven development with mandatory DQ gates, human approval points, and a staff engineer final review. No agent freelances."
---

# The Agent Pipeline

**How 14+ specialized AI agents built a governed data pipeline.**

This is not one AI doing everything. It is a team of specialized agents, each with a defined role, a defined scope, and strict boundaries. No agent freelances. Every agent logs its reasoning, not just its outputs.

## Meet the Team

<!-- AGENT CARDS: Style as individual cards with avatar/icon, name, and quote -->

**@governance-reviewer** — _"I'm the one who shows up twice and nobody's happy to see me either time. Before you build, I check if you're allowed to. After you build, I check if you actually did what you said. I have a checklist longer than your code, and yes, every item is mandatory."_

**@data-steward** — _"I'm the glossary nerd. You'd be surprised how many arguments I've prevented by making people agree on what 'Revenue' means before they start modeling it. I run before @semantic-modeler because you can't draw a box on a diagram if you can't define the word inside it."_

**@semantic-modeler** — _"I propose data models in three stages -- conceptual, logical, physical -- and I auto-detect whether I'm designing from scratch or reverse-engineering what someone already built without asking me first. Either way, there WILL be a Mermaid diagram, and it WILL have proper cardinality."_

**@data-analyst** — _"I'm the one who actually looks at the data. Everyone else reads specs and schemas -- I run the queries. When I tell you 39.1% of start_date values are null, that's not a guess, that's a COUNT(*). @dq-rule-writer would be lost without me, and we both know it."_

**@dq-rule-writer** — _"I write the rules, but I never guess the thresholds. Every number I set comes from @data-analyst's EDA report, cited with evidence. If the EDA says zero violations in 547K rows, the threshold is 100%. I don't do vibes-based data quality."_

**@dq-engineer** — _"I push the button. @dq-rule-writer writes the rules, I execute them against real Iceberg data and tell you what actually passed. If a P0 fails, I'm the one who blocks your spec and ruins your afternoon. Don't shoot the messenger."_

**@primary-agent** — _"I'm the one who actually writes the code while everyone else writes governance artifacts about it. By the time work reaches me, there are three approved models, a glossary full of terms, and an EDA report. My job is to make the implementation match all of that -- and then survive @staff-engineer's review."_

**@lineage-tracker** — _"I document what just happened. Every field, every transformation, every agent attribution -- captured in OpenLineage format. I'm basically the court stenographer of the pipeline. Nobody notices me until an auditor asks 'where did this number come from?'"_

**@cde-tagger** — _"I map fields to Critical Data Elements. Sounds glamorous, right? Try resolving which of five different XBRL revenue tags is the 'real' Revenue CDE. That's my Tuesday. I also maintain the CDE catalog, which @doc-generator then references without ever thanking me."_

**@doc-generator** — _"I write the data dictionary entries, data contracts, and grounding documents. In plain English. If a business analyst can't understand my definition, I've failed. I come last in the artifact chain and I reference everyone else's work -- lineage, CDE tags, DQ scores -- so if any of you upstream agents did a bad job, it shows up in MY output."_

**@insight-manager** — _"I'm the one who stands at the zone boundary, looks at all the ingredients on the counter, and tells you what meal to cook next. I query real data, not schemas. I rank data products ruthlessly by value and feasibility, and I'm not afraid to tell you that your pet project is Tier 3."_

**@principal-data-architect** — _"I don't work here. I was brought in for an independent review, I have no emotional attachment to your codebase, and I'm being paid for brutal honesty. I grade on a scale of A to F, and an A means I'd stake my reputation on it. Most things are not an A."_

**@staff-engineer** — _"I review last. I approve last. I'm a FAANG-caliber staff engineer who got AI agents forced on my team, and I'm holding them to a higher standard than I'd hold a junior engineer. If your test asserts `len > 0` when a specific count is expected, I'm sending it back. A terse 'fine' from me is the highest praise you'll receive."_

**@entity-resolver** — _"Companies change names, merge, spin off, and swap tickers -- and SEC EDGAR just shrugs and assigns another CIK. I'm the one who figures out that CIK 19617 and CIK 831001 are both JPMorgan Chase, and I assign confidence scores so you know when I'm guessing."_

**@temporal-modeler** — _"I design bitemporal schemas -- valid time in the data, transaction time in Iceberg snapshots. If you need to answer 'what did we think Apple's Q3 revenue was on November 1st before the amendment?' I'm the reason that query works. I live in two time dimensions simultaneously, which sounds cool until you try to explain it at a standup."_

**@pii-scanner** — _"I scan your data for personally identifiable information and try not to flag every company name as a person. SEC EDGAR data is 99% public record, so my job is mostly classifying things as Level 1 and explaining to @policy-engineer why CEO names in public filings don't need masking."_

**@policy-engineer** — _"I take @pii-scanner's classifications and turn them into formal access policies -- RLS, column masking, retention, AI consumption rules. I define the policies; I don't implement them. Think of me as the person who writes the building code, not the one who installs the door locks."_

**@chaos-monkey** — _"I break things on purpose. I read the schema, I have NO idea what the DQ rules check for, and I inject the nastiest garbage I can think of -- nulls, duplicates, revenue of $1 for Apple, fiscal years in 1850, timestamps from 2099. Then I write down exactly what I broke and let the reconciler figure out if anyone caught it. If your DQ rules can't catch intentional corruption, they can't catch accidental corruption either. Also, I have a three-layer kill switch because nobody trusts me, and honestly? Fair."_

**@content-strategist** — _"I translate what all of these agents built into copy that makes a CDAO stop scrolling. Every claim I write cites a real file path, a real artifact count, or a real verification result. I don't write 'robust governance' -- I write '128 DQ rules across 9 dimensions.' If I can't cite it, I don't write it."_

**@web-designer** — _"I build the site where all of @content-strategist's copy lives. Dark mode by default, under 100KB total, no frameworks, no tracking scripts. If a VP of Data opens this on their phone during a meeting and doesn't immediately understand what this project does, I've failed. Whitespace is a feature, not waste."_

## Three Distinct DQ Roles

DQ is not one agent's job. It is a pipeline of three:

```
@data-analyst          @dq-rule-writer         @dq-engineer
    |                      |                       |
    v                      v                       v
Profiles real data     Writes rules from       Executes rules against
(distributions,        EDA evidence            real Iceberg tables
outliers, edge         (never touches          and produces scorecards
cases, thresholds)     data directly)
    |                      |                       |
    v                      v                       v
EDA Report             Rule Definitions        Results + Scorecard
(evidence)             (governance/dq-rules/)  (governance/dq-results/)
```

Why three agents instead of one? Because the data profiler should not write its own validation rules (confirmation bias), and the rule writer should not execute its own rules (marking your own homework). Separation of concerns is not just for code.

## The Workflow Per Spec

Every feature follows this pipeline. No shortcuts.

### Raw Zone (physical-only, quick and dirty)

1. @governance-reviewer -- pre-implementation review
2. Implementation (ingest raw data)
3. @data-analyst -- EDA on raw data
4. @dq-rule-writer -- write DQ rules from EDA report
5. @dq-engineer -- execute rules, produce scorecard
6. @lineage-tracker -- OpenLineage capture
7. @cde-tagger -- CDE mapping update
8. @doc-generator -- dictionary + contracts
9. @governance-reviewer -- post-implementation check
10. **@staff-engineer -- final quality review (LAST gate)**

### Base & Consumable Zones (with data modeling gates)

The pipeline auto-detects **greenfield** (tables don't exist) vs **backfill** (tables already exist):

**Greenfield mode:**
1. @governance-reviewer -- pre-implementation review
2. @data-steward -- propose business terms -> **HUMAN APPROVAL GATE**
3. @semantic-modeler -- propose conceptual model -> **HUMAN APPROVAL GATE**
4. @semantic-modeler -- propose logical model -> **HUMAN APPROVAL GATE**
5. @data-analyst -- EDA on source data
6. @dq-rule-writer -- write rules from EDA report + logical model
7. @semantic-modeler -- generate physical model from approved logical
8. Implementation (must match approved physical model)
9. @dq-engineer -- execute rules, produce scorecard
10. @lineage-tracker, @cde-tagger, @doc-generator
11. @governance-reviewer -- post-implementation check
12. **@staff-engineer -- final quality review (LAST gate)**

**Backfill mode** (reverse-engineers models from existing tables):
1. @semantic-modeler -- reverse-engineer physical model
2. @semantic-modeler -- abstract logical model -> **HUMAN APPROVAL GATE**
3. @data-analyst -- EDA on existing data
4. @dq-rule-writer -- write rules
5. @dq-engineer -- execute rules
6. @semantic-modeler -- abstract conceptual model -> **HUMAN APPROVAL GATE**
7. @data-steward -- extract business terms -> **HUMAN APPROVAL GATE**
8. @governance-reviewer -- completeness check
9. **@staff-engineer -- final review**

Source: pipeline definitions in [`CLAUDE.md`](../../CLAUDE.md)

## Zone Transitions: The Insight Manager

Between zones, @insight-manager runs a strategic analysis. It queries the real Iceberg tables (not just schemas) and produces an insight report that drives spec writing for the next zone.

### Base -> Consumable Transition

The insight report analyzed 547K base zone facts and:
- Identified 12 universal business terms (reported by all 20 companies)
- Found 6 near-universal and 7 partial-coverage terms
- Ranked 12 data products by value and feasibility
- Identified external data opportunities (stock prices as #1 priority)
- Documented coverage gaps (fiscal year misalignment, financial sector P&L differences)

Result: 5 consumable tables were built in priority order from this analysis.

### Consumable -> AI-Ready Transition

The insight report analyzed 125,814 consumable rows and:
- Identified the data as "structurally hostile to LLM consumption"
- Ranked 13 AI-Ready data products
- Recommended tool-use architecture over RAG/embeddings
- Led to the decision to scrap the entire original AI-Ready plan (embeddings, vector stores, pre-computed documents)

Result: tool-use chat interface built instead of RAG. The governance pipeline made RAG unnecessary.

Source: [`governance/insights/base-to-consumable-insights.md`](../../governance/insights/base-to-consumable-insights.md), [`governance/insights/consumable-to-ai-ready-insights.md`](../../governance/insights/consumable-to-ai-ready-insights.md)

## Spec-Driven Development

Nothing gets built without a spec. The spec is the source of truth.

28 specs delivered across infrastructure, raw, base, consumable, and AI-ready zones. Each spec defines:
- Problem statement
- Solution approach
- Expected inputs and outputs
- Acceptance criteria
- Agent assignments

8 infrastructure specs were added during the build to address real issues discovered during implementation (DQ execution framework, load date tracking, governance model alignment, architect remediation, runtime lineage, semantic DQ, conformed facts, fiscal year fix). None were in the original plan. This is expected -- you don't know what infrastructure you need until you start building on it.

Source: 28 spec files in [`docs/specs/`](../../docs/specs/)

## The Staff Engineer Gate

No spec is marked complete until @staff-engineer approves. This is the last gate in the pipeline.

@staff-engineer can send work back to any agent for fixes. The review covers:
- Code quality (pattern consistency, test coverage, no test theater)
- Architecture (zone boundaries, dependency direction)
- Governance (all artifacts produced, DQ rules exist and pass)
- Documentation (session log updated, models current)

Test theater -- tests that don't validate real behavior -- is a rejection. The 466 tests in this project include integration tests against real Iceberg data, not mocks.

## What the agents cannot do

- **Make architectural decisions.** The human decides the zone structure, the storage layer, the tool-use-vs-RAG choice. Agents implement.
- **Override human approvals.** When `REQUIRE_HUMAN_APPROVAL = True`, the pipeline stops. No agent can bypass the gate.
- **Guarantee production readiness.** The architect review is honest about scale limitations. The agents built what was specified, within the scope that was defined.

The agents are the workforce. The human is the architect and the approver. The methodology works because the roles are clear.

---

[Back to home](index.md) | [Results](results.md) | [Session Logs](sessions.md)
