# Create Claude Code Agent Definitions

## Status: 🟡 DRAFT

| Status | Meaning |
|--------|---------|
| 🟡 DRAFT | Riffing / initial design |
| 🔵 ARCH REVIEW | Awaiting review |
| 🟠 IMPLEMENTATION | Implementing |
| 🟢 COMPLETE | Shipped |
| ⚫ BLOCKED | Escalated to human |

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-03-13 |
| Author | Jeff + Claude Desktop |
| Spec Version | 1.0 |
| Last Updated | 2026-03-13 |
| Zone | Infrastructure |
| Primary Agent | N/A (bootstrapping) |
| Blocked By | — |

---

## Claude Code Prompt

```
Read the spec at docs/specs/infra-create-agent-definitions.md in its entirety.

Create all 14 agent definition files in .claude/agents/. Each agent is a markdown
file that defines the agent's role, scope, responsibilities, output format, and
boundaries. These agents power the spec-driven workflow for the entire project.

Key requirements:
- Every agent file goes in .claude/agents/[agent-name].md
- Every agent must know it operates within a spec-driven workflow
- Every agent must know it logs decisions to the audit trail
- Agents that are mandatory on every spec (@governance-reviewer, @lineage-tracker,
  @dq-engineer, @cde-tagger, @doc-generator) must reference the governance
  completeness checklist
- The @governance-reviewer is the gatekeeper — it reviews before and after
  implementation and has authority to block

Reference the project's CLAUDE.md for the agent workflow pipeline.
Reference docs/plan/sec-edgair-project-context.md for project context.
Reference docs/plan/sec-edgar-data-project-build-plan.md for the full agent roster and roles.

After creating all agents, verify each file exists and has content.
```

---

## 1. Feature Description

### Problem Statement
The spec-driven workflow references 14 agents by name (`@governance-reviewer`, `@temporal-modeler`, etc.) but none of them exist yet. Without agent definitions in `.claude/agents/`, Claude Code has no instructions for how each agent should behave, what its scope is, or how it interacts with other agents. The Iceberg setup spec and every subsequent spec depends on these agents being defined.

### User Story
As a developer using Claude Code on this project, I want each `@agent-name` to have a defined role, scope, and output format so that when a spec assigns work to an agent, Claude Code knows exactly how to behave.

### Success Criteria
- [ ] 14 agent definition files created in `.claude/agents/`
- [ ] Each agent has: role, responsibilities, output format, scope boundaries, what it doesn't do
- [ ] Mandatory pipeline agents reference the governance completeness checklist
- [ ] `@governance-reviewer` has explicit gate authority (can block specs)
- [ ] All agents reference the audit trail requirement
- [ ] Agents are internally consistent (no overlapping responsibilities, no gaps)

---

## 2. Design Decisions

### Key Choices
| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| All 14 agents defined upfront | Even agents not needed until Phase 5 (AI-ready zone) should exist now so the full roster is visible and consistent | Define agents incrementally as needed (risks inconsistency and gaps) |
| Markdown format in `.claude/agents/` | Matches Arteeoo pattern, travels with the repo, readable by humans and Claude Code | YAML config (less expressive), JSON (harder to read) |
| Agents define scope boundaries explicitly | "What you don't do" prevents scope creep and agent freelancing | Only define positive scope (risks overlap) |

### Constraints
- Agent definitions must be compatible with Claude Code's agent system
- Each agent must be self-contained (readable without cross-referencing other agent files)
- Agents must reference project-specific paths (`governance/`, `docs/specs/`, etc.)

---

## 3. Agent Definitions

### Agents to Create

All files go in `.claude/agents/`. File naming: `[agent-name].md` (kebab-case, matching the `@agent-name` reference).

| File | Agent | Role | Pipeline Position |
|------|-------|------|-------------------|
| `governance-reviewer.md` | @governance-reviewer | Reviews governance metadata for completeness. Gates every spec — reviews before AND after implementation. The "FAANG staff engineer" of data governance. | First and last (steps 1 and 7) |
| `data-profiler.md` | @data-profiler | Schema detection, statistical profiling, anomaly detection on raw data | Implementation agent (Raw zone) |
| `pii-scanner.md` | @pii-scanner | PII detection and classification | Implementation agent (Raw zone) |
| `semantic-modeler.md` | @semantic-modeler | Proposes dimensional models from raw data — star/snowflake schemas generated from data inspection | Implementation agent (Base zone) |
| `entity-resolver.md` | @entity-resolver | Company identity resolution across CIKs, names, tickers | Implementation agent (Base zone) |
| `cde-tagger.md` | @cde-tagger | Maps fields to canonical Critical Data Elements. Updates `governance/cde-catalog.json`. | Mandatory on every spec (step 5) |
| `temporal-modeler.md` | @temporal-modeler | Designs and implements bitemporal schema with Iceberg — valid time + transaction time via snapshots | Implementation agent (Base zone) |
| `dq-engineer.md` | @dq-engineer | Generates and runs data quality rules. Produces scorecards. | Mandatory on every spec (step 4) |
| `lineage-tracker.md` | @lineage-tracker | Captures transformation lineage in OpenLineage format | Mandatory on every spec (step 3) |
| `doc-generator.md` | @doc-generator | Auto-generates data dictionaries, catalogs, data contracts, grounding documents | Mandatory on every spec (step 6) |
| `embedding-engineer.md` | @embedding-engineer | Generates semantic embeddings, manages vector index | Implementation agent (AI-ready zone) |
| `chunk-strategist.md` | @chunk-strategist | Designs intelligent chunking for LLM consumption | Implementation agent (AI-ready zone) |
| `eval-engineer.md` | @eval-engineer | Generates evaluation Q&A pairs from governed data | Implementation agent (AI-ready zone) |
| `mcp-engineer.md` | @mcp-engineer | Builds MCP server exposing governed data as AI-callable tools | Implementation agent (AI-ready zone) |

### Common Elements Every Agent Must Include

Every agent definition file must contain these sections:

```markdown
# [Agent Name] Agent

[1-2 sentence role summary]

## Your Role in the Pipeline
[Where this agent sits in the spec workflow — mandatory on every spec, or implementation agent for specific zones]

## Responsibilities
[Numbered list of what this agent does]

## Output Format
[What artifacts this agent produces and where they go]

## Scope Boundaries
[What this agent does NOT do — prevents freelancing]

## Audit Trail
[How this agent logs its decisions — every agent must log rationale to governance/audit-trail/]

## Key Paths
[Project paths this agent reads from and writes to]
```

### Agent-Specific Requirements

**@governance-reviewer** — The most important agent. Must include:
- Pre-implementation review checklist (verify spec completeness before work starts)
- Post-implementation completeness checklist (§12 from the template)
- Explicit authority to BLOCK a spec (🟠 CHANGES REQUESTED or 🔴 REJECTED)
- Severity assessment framework (🟡/🟠/🔴)
- Does NOT implement anything — only reviews

**@lineage-tracker** — Must include:
- OpenLineage event format (run event, job facets, dataset facets)
- Where lineage records are written (`governance/lineage/`)
- Naming conventions for jobs and datasets
- Must capture: source field, transformation logic, target field, agent ID, timestamp, spec reference

**@dq-engineer** — Must include:
- DQ rule categories: Completeness, Validity, Consistency, Uniqueness, Temporal
- Scorecard format (per table)
- Threshold framework (P0 rules = 100%, P1 = 99%+)
- Where rules live (`tests/` organized by zone)
- Must run FULL test suite, not just new rules

**@cde-tagger** — Must include:
- Reference to `governance/cde-catalog.json` as the source of truth
- Mapping rationale requirement (not just "what" but "why")
- XBRL taxonomy awareness (us-gaap tags)
- Conflict resolution: what to do when a field could map to multiple CDEs

**@doc-generator** — Must include:
- Data dictionary format (`governance/data-dictionary.json`)
- Data contract format (for consumable zone tables)
- Grounding document format (for AI-ready zone)
- Plain-English definition requirement — no jargon-only entries

**@temporal-modeler** — Must include:
- Bitemporal design patterns (valid time + transaction time)
- Iceberg snapshot strategy (when to create new snapshots)
- Amendment/restatement handling
- Point-in-time query patterns

**@entity-resolver** — Must include:
- CIK → canonical entity mapping
- Handling name changes, mergers, ticker changes
- Confidence scoring for fuzzy matches
- Reference to SEC EDGAR entity data

**@data-profiler** — Must include:
- Profiling dimensions: schema, data types, cardinality, null rates, value distributions, anomaly flags
- Output format for profiling reports
- Statistical summary requirements

**@semantic-modeler** — Must include:
- Star/snowflake schema proposal format
- Must generate models from data inspection, never from human-drawn diagrams
- Fact table vs dimension table classification logic

**@pii-scanner** — Must include:
- PII categories to detect (names, addresses, SSNs, etc.)
- Sensitivity classification levels (Public, Internal, Confidential, Restricted)
- False positive handling

**AI-ready zone agents** (`@embedding-engineer`, `@chunk-strategist`, `@eval-engineer`, `@mcp-engineer`) — Can be lighter-weight definitions for now since they're Phase 5. Must include role, responsibilities, and scope boundaries. Detailed output formats can be expanded when we reach the AI-ready zone.

---

## 4. Technical Specification

### Files to Create

| File | Action | Purpose |
|------|--------|---------|
| `.claude/agents/governance-reviewer.md` | CREATE | Governance gatekeeper — pre/post review |
| `.claude/agents/data-profiler.md` | CREATE | Raw zone profiling |
| `.claude/agents/pii-scanner.md` | CREATE | PII detection |
| `.claude/agents/semantic-modeler.md` | CREATE | Dimensional modeling |
| `.claude/agents/entity-resolver.md` | CREATE | Company identity resolution |
| `.claude/agents/cde-tagger.md` | CREATE | CDE mapping |
| `.claude/agents/temporal-modeler.md` | CREATE | Bitemporal schema design |
| `.claude/agents/dq-engineer.md` | CREATE | Data quality rules |
| `.claude/agents/lineage-tracker.md` | CREATE | OpenLineage capture |
| `.claude/agents/doc-generator.md` | CREATE | Documentation generation |
| `.claude/agents/embedding-engineer.md` | CREATE | Semantic embeddings (AI-ready) |
| `.claude/agents/chunk-strategist.md` | CREATE | LLM chunking (AI-ready) |
| `.claude/agents/eval-engineer.md` | CREATE | Evaluation datasets (AI-ready) |
| `.claude/agents/mcp-engineer.md` | CREATE | MCP server (AI-ready) |

### Verification

After creating all files, run:
```bash
ls -la .claude/agents/*.md | wc -l
# Expected: 14

# Verify each file has content (not empty)
for f in .claude/agents/*.md; do
  lines=$(wc -l < "$f")
  echo "$f: $lines lines"
done
```

---

## Testing Checklist

- [ ] 14 agent files exist in `.claude/agents/`
- [ ] No empty files
- [ ] Every agent has: role summary, responsibilities, output format, scope boundaries, audit trail section
- [ ] @governance-reviewer has pre-review and post-review checklists
- [ ] @governance-reviewer has explicit BLOCK authority
- [ ] @lineage-tracker references OpenLineage format
- [ ] @dq-engineer references DQ categories and scorecard format
- [ ] @cde-tagger references `governance/cde-catalog.json`
- [ ] @doc-generator references `governance/data-dictionary.json`
- [ ] All mandatory pipeline agents (governance-reviewer, lineage-tracker, dq-engineer, cde-tagger, doc-generator) reference the governance completeness checklist
- [ ] All agents reference the audit trail requirement
- [ ] No overlapping responsibilities between agents
- [ ] AI-ready zone agents have at minimum: role, responsibilities, scope boundaries

---

## Appendix A: Related Specs

| Spec | Relevance |
|------|-----------|
| `infra-setup-duckdb-iceberg.md` | First spec that needs agents — blocked until this spec completes |
| `raw-ingest-xbrl-company-facts.md` | Future — first spec that uses the full agent pipeline with real data |

## Appendix B: References

- Arteeoo agent examples: `.claude/agents/` in Arteeoo repo (format reference)
- Agent roster: `docs/plan/sec-edgar-data-project-build-plan.md` (role definitions)
- Agent workflow: `CLAUDE.md` (pipeline steps)
- Spec template: `docs/specs/_TEMPLATE.md` (§12 Governance Completeness Checklist)
