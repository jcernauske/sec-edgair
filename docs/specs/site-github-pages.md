# GitHub Pages Site

## Status: 🟡 DRAFT

| Status | Meaning |
|--------|---------|
| 🟡 DRAFT | Riffing / initial design |
| 🟠 IMPLEMENTATION | Agent pipeline running |
| 🟢 COMPLETE | Shipped |

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-03-15 |
| Author | Jeff + Claude Code |
| Zone | Documentation / Marketing |
| Primary Agents | @content-strategist, @web-designer |
| Depends On | All specs complete |

---

## Claude Code Prompt

```
The README is getting to be...alot. Can we add a "marketing agent" or "contet writer agent" whose task is to produce content for GitHub pages intended to prove this value propisition to a Chief Data and Analytics officer, a Data Architect that will be skepitcal of the agent pipeline, auditors and compliance people who will need to understand the human in the loop approvals, etc. We will also need a "web designer" agent to produce the Github pages, and i want them to be beautiful
```

---

## 1. Problem Statement

The README is 370+ lines trying to serve four audiences simultaneously: developers (quickstart), executives (why this matters), architects (does it hold up), and auditors (where are the controls). It's doing all four jobs poorly.

## 2. Solution

A GitHub Pages site with dedicated pages for each persona, built from real project artifacts. Every claim backed by a file path or data point. Beautiful, fast, static HTML/CSS.

## 3. Target Personas

### CDAO ("Show me the ROI")
- 14 AI agents produced what would take a team of 5 several months
- 128 DQ rules, 21 data models, runtime lineage — all agent-generated with human approval gates
- 547K raw facts → 136K consumable rows → natural language chat interface
- 88/88 verification checks against real 10-K figures
- Architect Agent grade: A

### Skeptical Data Architect ("Prove it works")
- Full architecture deep dive: 4-zone medallion, Iceberg tables, DuckDB
- The B+ → A journey: what was wrong, how it was fixed, what the architect said
- Runtime lineage to Iceberg (not static docs)
- 128 DQ rules across 9 dimensions including Accuracy and Reasonableness
- Negative testing: 10 checks proving bad data is absent
- Code links to every claim

### Auditors & Compliance ("Where are the controls?")
- REQUIRE_HUMAN_APPROVAL global toggle
- 4 human approval gates: business terms, conceptual model, logical model, DQ rules
- Runtime lineage: every promote emits events with snapshot IDs
- Traceability: consumable row → conformed_facts → financial_facts → SEC filing
- Governance artifact inventory: glossary, models, lineage, DQ rules, audit trail
- Session logs: full transparency on every decision

## 4. Site Map

```
docs/site/
  index.html              Landing page — the hook, key metrics, persona routing
  architecture.html       For data architects — zone diagram, lineage, DQ deep dive
  governance.html         For auditors — approval gates, traceability, controls
  results.html            For CDAOs — the numbers, the ROI story
  methodology.html        The agent pipeline — 14 agents, their roles, the workflow
  sessions.html           Session log index — raw transparency
  assets/
    css/style.css         Main stylesheet
    css/theme.css         Dark/light mode tokens
    js/main.js            Minimal interactions (nav, scroll, theme toggle)
```

## 5. Design Requirements

- Dark mode default, light mode toggle
- System font stack (fast, no FOUT)
- Under 100KB total page weight
- Mobile-first responsive
- Metric cards for key numbers (128 DQ Rules, 88/88 Verified, A Grade, 20 Companies)
- Pipeline flow diagram as styled HTML (not image)
- Mermaid.js for ER diagrams (CDN, lazy-loaded)
- Code blocks with syntax highlighting
- Semantic HTML, accessible, no tracking

## 6. Content Requirements

Every page must:
- Open with a one-sentence hook that speaks directly to the persona
- Include 3-5 "proof points" — specific metrics or artifacts that back the claim
- Link to the actual files in the repo (governance/, src/, docs/)
- End with a natural next page for the reader's journey

The landing page must:
- Explain what this is in one sentence
- Show 4-6 key metrics as cards
- Route each persona to their page in under 5 seconds
- Include the pipeline diagram (Raw → Base → Consumable → AI-Ready)

## 7. Content Sources

The @content-strategist derives all copy from these real artifacts:

| Source | What It Proves |
|--------|---------------|
| `README.md` | Project overview, metrics, structure |
| `governance/reviews/principal-data-architect-re-review.md` | Architecture grade + specific findings |
| `governance/business-glossary.json` | 54 business terms |
| `governance/dq-rules/*.json` | 128 DQ rules across 9 dimensions |
| `governance/models/` | 21 data models |
| `governance/lineage/` | Lineage events |
| `src/infra/lineage.py` | Runtime lineage implementation |
| `src/config.py` | REQUIRE_HUMAN_APPROVAL |
| `scripts/verify*.py` | 98 verification checks (57 + 31 + 10) |
| `docs/sessions/` | Session logs (the raw story) |
| `docs/specs/` | Every spec that was written and shipped |
| `CLAUDE.md` | The agent pipeline definition |

## 8. Agent Workflow

1. @content-strategist reads all source artifacts, produces page copy in markdown (one file per page)
2. @web-designer reads the copy and the design spec, produces HTML/CSS/JS
3. Jeff reviews
4. Deploy via GitHub Pages (enable in repo settings, point to `docs/site/`)

## 9. GitHub Pages Setup

- Source: `docs/site/` directory
- Branch: `main`
- No Jekyll (add `.nojekyll` file)
- Custom 404 page

## 10. What the README Becomes

After the site is live, the README slims down to:
- Project name + one-line description
- Badges
- Link to the GitHub Pages site
- Quick start (install + run)
- Project structure (abbreviated)
- License

Everything else moves to the site.
