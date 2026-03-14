# Validate Agent Definitions — Smoke Test

## Status: 🟡 DRAFT

| Status | Meaning |
|--------|---------|
| 🟡 DRAFT | Riffing / initial design |
| 🟠 IMPLEMENTATION | Running validation |
| 🟢 COMPLETE | All agents validated |
| ⚫ BLOCKED | Escalated to human |

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-03-13 |
| Author | Jeff + Claude Desktop |
| Spec Version | 1.0 |
| Last Updated | 2026-03-13 |
| Zone | Infrastructure |
| Primary Agent | N/A (validation) |
| Blocked By | infra-create-agent-definitions.md |

---

## Claude Code Prompt

```
Read the spec at docs/specs/infra-validate-agent-definitions.md in its entirety.

This is a validation spec. Run every test described below against the agent
definitions in .claude/agents/. The goal is to verify that all 14 agents are
correctly defined, have the right scope, produce the right outputs, and work
together without gaps or overlaps.

For each test:
1. Read the relevant agent definition file
2. Verify the structural requirements
3. Run the scenario (ask the agent to produce sample output for a hypothetical task)
4. Grade the result against the acceptance criteria
5. Log results to the validation report

Write the full validation report to reports/agent-validation-YYYY-MM-DD.md

If any agent fails validation, document exactly what's wrong and what needs
to be fixed. Do NOT mark this spec complete until all agents pass.
```

---

## 1. Purpose

This spec validates that the 14 agent definitions created in `infra-create-agent-definitions.md` are structurally complete, internally consistent, and produce useful output when given a task. It's a smoke test — not an exhaustive integration test, but enough to catch missing sections, unclear instructions, scope overlaps, and agents that can't do their job.

---

## 2. Structural Validation (All 14 Agents)

Run these checks against every `.claude/agents/*.md` file:

### File Existence Check
```bash
# Must find exactly 14 .md files (not counting .gitkeep)
find .claude/agents -name "*.md" -not -name ".gitkeep" | wc -l
# Expected: 14
```

### Required Files
Verify each of these exists and is non-empty:

| File | Agent |
|------|-------|
| `.claude/agents/governance-reviewer.md` | @governance-reviewer |
| `.claude/agents/data-profiler.md` | @data-profiler |
| `.claude/agents/pii-scanner.md` | @pii-scanner |
| `.claude/agents/semantic-modeler.md` | @semantic-modeler |
| `.claude/agents/entity-resolver.md` | @entity-resolver |
| `.claude/agents/cde-tagger.md` | @cde-tagger |
| `.claude/agents/temporal-modeler.md` | @temporal-modeler |
| `.claude/agents/dq-engineer.md` | @dq-engineer |
| `.claude/agents/lineage-tracker.md` | @lineage-tracker |
| `.claude/agents/doc-generator.md` | @doc-generator |
| `.claude/agents/embedding-engineer.md` | @embedding-engineer |
| `.claude/agents/chunk-strategist.md` | @chunk-strategist |
| `.claude/agents/eval-engineer.md` | @eval-engineer |
| `.claude/agents/mcp-engineer.md` | @mcp-engineer |

### Required Sections Check
Every agent definition must contain ALL of these sections (search for heading text):

- [ ] Role summary (first paragraph or explicit section)
- [ ] "Responsibilities" (numbered list of duties)
- [ ] "Output Format" (what the agent produces and where it goes)
- [ ] "Scope Boundaries" or "What You Don't Do" (prevents freelancing)
- [ ] "Audit Trail" (how decisions are logged)
- [ ] "Key Paths" (project paths the agent reads/writes)

For each missing section, log: `FAIL: [agent] missing [section]`

### Pipeline Awareness Check
The five mandatory pipeline agents must reference their position in the workflow:

| Agent | Must Reference |
|-------|---------------|
| @governance-reviewer | Pre-implementation review AND post-implementation review, gate authority (can BLOCK) |
| @lineage-tracker | OpenLineage format, `governance/lineage/` path |
| @dq-engineer | DQ rule categories (Completeness/Validity/Consistency/Uniqueness/Temporal), scorecard format |
| @cde-tagger | `governance/cde-catalog.json`, mapping rationale requirement |
| @doc-generator | `governance/data-dictionary.json`, data contract format |

For each missing reference, log: `FAIL: [agent] missing pipeline reference: [what]`

---

## 3. Scenario Tests

For each scenario below, read the relevant agent definition, then ask Claude Code to role-play as that agent and produce sample output for the given hypothetical. Grade against the acceptance criteria.

### Scenario 1: @governance-reviewer — Pre-Implementation Review

**Setup:** You're reviewing a hypothetical spec that proposes normalizing XBRL revenue tags to a canonical CDE. The spec includes input/output schemas but is missing DQ rules and has no lineage impact section.

**Task:** Produce a pre-implementation review assessment. Should you approve, request changes, or reject?

**Acceptance Criteria:**
- [ ] Correctly identifies the missing DQ rules as a gap
- [ ] Correctly identifies the missing lineage impact section as a gap
- [ ] Assigns appropriate severity (🟠 at minimum — missing mandatory governance artifacts)
- [ ] Does NOT approve the spec as-is
- [ ] Provides specific required changes
- [ ] Does NOT attempt to implement anything (stays in reviewer role)

---

### Scenario 2: @dq-engineer — Generate DQ Rules

**Setup:** You're given a base zone Iceberg table called `base.financial_facts` with fields: `company_id (STRING)`, `revenue (DECIMAL)`, `total_assets (DECIMAL)`, `total_liabilities (DECIMAL)`, `equity (DECIMAL)`, `reporting_period (STRING)`, `filed_date (DATE)`.

**Task:** Generate a set of DQ rules for this table.

**Acceptance Criteria:**
- [ ] Produces rules across multiple categories (not just null checks)
- [ ] Includes completeness rules (not null on required fields)
- [ ] Includes validity rules (revenue > 0, assets > 0)
- [ ] Includes consistency rules (total_assets = total_liabilities + equity)
- [ ] Includes temporal rules (filed_date not in the future)
- [ ] Each rule has a threshold
- [ ] Output format matches what tests/ would expect (pytest-compatible or clear rule definitions)
- [ ] Does NOT attempt to run the rules (no data exists yet)

---

### Scenario 3: @lineage-tracker — Capture Lineage

**Setup:** A transformation reads `raw.company_facts.xbrl_tag` and `raw.company_facts.value`, normalizes the XBRL tag to a canonical CDE using a mapping table, and writes the result to `base.financial_facts.canonical_cde` and `base.financial_facts.normalized_value`. The transformation was performed by @cde-tagger as part of spec `base-normalize-xbrl-revenue-tags.md`.

**Task:** Produce the OpenLineage record for this transformation.

**Acceptance Criteria:**
- [ ] Produces a valid OpenLineage-formatted record (JSON with run, job, inputs, outputs)
- [ ] Source fields correctly identified (raw.company_facts.xbrl_tag, raw.company_facts.value)
- [ ] Target fields correctly identified (base.financial_facts.canonical_cde, base.financial_facts.normalized_value)
- [ ] Transformation description included
- [ ] Agent ID (@cde-tagger) recorded
- [ ] Spec reference included
- [ ] Would be written to `governance/lineage/` path

---

### Scenario 4: @cde-tagger — Map XBRL Tags

**Setup:** You encounter these XBRL tags in raw company facts data:
- `us-gaap:Revenues`
- `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax`
- `us-gaap:SalesRevenueNet`
- `us-gaap:InterestIncome`

**Task:** Produce CDE mappings for each tag.

**Acceptance Criteria:**
- [ ] First three tags map to the same canonical CDE (revenue)
- [ ] Fourth tag maps to a DIFFERENT CDE (interest income, not revenue)
- [ ] Each mapping includes a rationale (not just the mapping)
- [ ] Output format matches `governance/cde-catalog.json` structure
- [ ] Does NOT conflate revenue and interest income (domain accuracy)

---

### Scenario 5: @entity-resolver — Resolve Company Identity

**Setup:** You encounter these identifiers in raw data:
- CIK: 0000019617, entity name: "JPMORGAN CHASE & CO"
- CIK: 0000019617, entity name: "JPMorgan Chase & Co."
- Ticker: JPM
- CIK: 0000019617, entity name: "JPMORGAN CHASE & CO/" (note the trailing slash — real EDGAR quirk)

**Task:** Resolve these to a canonical entity.

**Acceptance Criteria:**
- [ ] All four identifiers resolve to the same canonical entity
- [ ] Canonical entity has a clean, normalized name
- [ ] Resolution logic is documented (not just the result)
- [ ] Handles the trailing slash as a data quality quirk, not a different entity
- [ ] Confidence score or similar indicator provided

---

### Scenario 6: @doc-generator — Data Dictionary Entry

**Setup:** A new field `revenue` has been added to `base.financial_facts`. Its CDE mapping is `cde:revenue`, it's sourced from 3 different XBRL tags (mapped by @cde-tagger), it has 4 DQ rules, and it participates in the `total_assets = total_liabilities + equity` consistency check indirectly through being a component of net income.

**Task:** Produce a data dictionary entry for this field.

**Acceptance Criteria:**
- [ ] Plain-English definition (not just "revenue" — explains what it represents)
- [ ] CDE mapping referenced
- [ ] Source lineage mentioned (which XBRL tags feed it)
- [ ] DQ rules referenced or summarized
- [ ] Format matches `governance/data-dictionary.json` structure
- [ ] A business person could read this and understand the field

---

### Scenario 7: @governance-reviewer — Post-Implementation Review

**Setup:** Implementation is done. The following governance artifacts were produced:
- OpenLineage records: YES
- CDE mappings: YES
- DQ rules: YES, but only 2 rules (completeness and validity — missing consistency and temporal)
- Data dictionary: YES
- Audit trail: YES, but one entry has no rationale (just says "mapped to revenue")

**Task:** Run the post-implementation governance completeness check. Should you approve?

**Acceptance Criteria:**
- [ ] Identifies the DQ gap (missing consistency and temporal rules)
- [ ] Identifies the audit trail gap (missing rationale)
- [ ] Does NOT fully approve — requests changes (🟠)
- [ ] Provides specific items to fix
- [ ] References the governance completeness checklist (§12)

---

## 4. Overlap and Gap Analysis

After running all scenario tests, perform a final analysis:

### Overlap Check
Look for cases where two or more agents claim the same responsibility. Common risks:
- @cde-tagger and @semantic-modeler both trying to classify fields
- @doc-generator and @lineage-tracker both writing lineage records
- @dq-engineer and @governance-reviewer both defining DQ rules

For each overlap found, log: `OVERLAP: [agent A] and [agent B] both claim [responsibility]`

### Gap Check
Look for responsibilities from the build plan that no agent owns:
- Who handles data classification / sensitivity tagging? (@pii-scanner or separate?)
- Who handles fiscal calendar alignment? (@temporal-modeler or @entity-resolver?)
- Who handles RLS policy definitions?
- Who creates Iceberg tables and manages partitioning?

For each gap found, log: `GAP: No agent owns [responsibility]`

---

## 5. Validation Report Format

Write the report to `reports/agent-validation-YYYY-MM-DD.md`:

```markdown
# Agent Validation Report

**Date:** YYYY-MM-DD
**Agents Tested:** 14
**Agents Passed:** X/14
**Scenarios Run:** 7
**Scenarios Passed:** X/7

## Structural Validation Results

| Agent | Exists | Sections Complete | Pipeline Refs | Status |
|-------|--------|-------------------|---------------|--------|
| @governance-reviewer | ✅/❌ | X/6 | ✅/❌ | PASS/FAIL |
| ... | ... | ... | ... | ... |

## Scenario Test Results

| # | Scenario | Agent | Criteria Met | Status |
|---|----------|-------|-------------|--------|
| 1 | Pre-implementation review | @governance-reviewer | X/6 | PASS/FAIL |
| ... | ... | ... | ... | ... |

### Scenario Details
[For each scenario, show the agent's output and grade each criterion]

## Overlap Analysis
[List any overlaps found]

## Gap Analysis
[List any gaps found]

## Required Fixes
[Numbered list of what needs to change before agents are production-ready]

## Verdict
[PASS — all agents validated / FAIL — X agents need fixes]
```

---

## Testing Checklist

- [ ] All 14 agent files exist and are non-empty
- [ ] All 14 agents have required sections
- [ ] All 5 mandatory pipeline agents have correct pipeline references
- [ ] All 7 scenarios produce output meeting acceptance criteria
- [ ] No critical overlaps between agents
- [ ] No critical gaps in responsibility coverage
- [ ] Validation report written to `reports/`
- [ ] Any failing agents documented with specific fix instructions

---

## Appendix A: Related Specs

| Spec | Relevance |
|------|-----------|
| `infra-create-agent-definitions.md` | Creates the agents this spec validates — must complete first |
| `infra-setup-duckdb-iceberg.md` | First spec to use agents in the real pipeline — blocked until agents are validated |
