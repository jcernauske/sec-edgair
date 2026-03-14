# SEC EDGAIR — Claude Code Instructions

## Project Overview
SEC EDGAIR is an AI agent pipeline that processes SEC EDGAR XBRL financial data through four zones (Raw → Base → Consumable → AI-Ready) with full governance metadata at every step.

## Stack
- Python 3.11+
- DuckDB with Iceberg extension
- Apache Iceberg tables (local storage, no catalog server)
- uv for dependency management

## Key Paths
- Source code: `src/` (organized by zone: raw, base, consumable, ai_ready)
- Data: `data/` (gitignored, organized by zone)
- Governance artifacts: `governance/`
- Data models: `governance/models/` (conceptual, logical, physical)
- Business glossary: `governance/business-glossary.json`
- Specs: `docs/specs/`
- Tests: `tests/` (organized by zone)
- Agent definitions: `.claude/agents/`

## Agent Workflow

### Raw Zone Pipeline (physical-only, quick and dirty)
1. @governance-reviewer — Pre-implementation review
2. @primary-agent — Implementation
3. @lineage-tracker — OpenLineage capture
4. @dq-engineer — Quality rules + scorecard
5. @cde-tagger — CDE mapping update
6. @doc-generator — Dictionary + contracts update
7. @governance-reviewer — Post-implementation completeness check
8. @staff-engineer — Final quality review (LAST gate before completion)

### Base & Consumable Zone Pipeline (with data modeling gates)

The pipeline auto-detects **greenfield** vs **backfill** mode:

- **Greenfield** (tables don't exist yet): models are proposed BEFORE implementation
- **Backfill** (tables already exist): models are reverse-engineered FROM existing tables/code

#### Greenfield Mode (new tables)
1. @governance-reviewer — Pre-implementation review (checks model gate below)
2. @data-steward — Identify and propose **business terms** from spec → **HUMAN APPROVAL GATE** (project-specific terms only; external standard terms auto-approve)
3. @semantic-modeler — Propose **conceptual model** (referencing approved glossary terms) → **HUMAN APPROVAL GATE**
4. @semantic-modeler — Propose **logical model** → **HUMAN APPROVAL GATE**
5. @semantic-modeler — Generate **physical model** from approved logical
6. @primary-agent — Implementation (must match approved physical model)
7. @lineage-tracker — OpenLineage capture
8. @dq-engineer — Quality rules + scorecard
9. @cde-tagger — CDE mapping update
10. @doc-generator — Dictionary + contracts update
11. @governance-reviewer — Post-implementation completeness check (verifies models match)
12. @staff-engineer — Final quality review (LAST gate before completion)

#### Backfill Mode (existing tables, missing models)
1. @semantic-modeler — Reverse-engineer **physical model** from existing tables/code
2. @semantic-modeler — Abstract **logical model** from physical → **HUMAN APPROVAL GATE**
3. @semantic-modeler — Abstract **conceptual model** from logical → **HUMAN APPROVAL GATE**
4. @data-steward — Extract **business terms** from conceptual model → **HUMAN APPROVAL GATE** (project-specific terms only)
5. @governance-reviewer — Post-backfill completeness check (verifies models and glossary are consistent with existing implementation)
6. @staff-engineer — Final review

#### Mode Detection
@semantic-modeler determines the mode automatically:
- If the spec's target tables exist in the Iceberg catalog AND source code exists in `src/` → **backfill**
- If the spec's target tables do not exist → **greenfield**
- If a spec modifies existing tables (schema evolution) → **greenfield** for the new/changed parts

The human approval gates are controlled by `REQUIRE_HUMAN_APPROVAL` in `src/config.py`. When False (dev/demo mode), models auto-advance but all three artifacts are still produced in `governance/models/`.

Model artifacts are stored in `governance/models/` as `[spec-name]-conceptual.md`, `[spec-name]-logical.md`, `[spec-name]-physical.md`.

## Rules
- Specs are the source of truth — if it's not in the spec, it doesn't get built
- Every transformation produces governance artifacts (lineage, DQ rules, CDE tags, audit trail)
- DQ rules validate real data, never placeholders
- Every agent logs its reasoning, not just outputs
- No changes to data schemas without a spec
- Base/Consumable tables require approved business terms → conceptual → logical → physical models before implementation
- Business terms from external standards (XBRL taxonomy, SEC EDGAR) are auto-approved; project-specific terms require human approval
- `REQUIRE_HUMAN_APPROVAL` in `src/config.py` is the single global toggle for all human-in-the-loop gates
- @staff-engineer reviews last — no spec is marked complete until he approves
- @staff-engineer can send work back to any agent for fixes
- Test theater (tests that don't validate real behavior) is a rejection
- When model files in `governance/models/` are created or modified, update the corresponding Mermaid diagrams in the "Data Models" section of `README.md` (all three levels: conceptual, logical, AND physical — full details live in governance/models/)
- When `governance/business-glossary.json` is modified, update the "Business Glossary" section of `README.md` (term counts, key terms tables)
- Data models must cross-reference business glossary terms: conceptual entities get `Business Term` column + `†` marker, logical attributes get `Business Term` column, physical columns get `Business Term` + `Term Def` columns

# Session Logging

## Purpose
Every Claude Code session is logged for three reasons:
1. Open source transparency — anyone can see exactly how this project was built
2. Blog content — the Jeff ↔ Claude interactions are the story
3. Continuity — pick up where we left off between sessions

## Session Log Location
All session logs go in `docs/sessions/`

## At the START of Every Session

Create a new file: `docs/sessions/YYYY-MM-DD-HH-MM-session.md`

Write the following header immediately:

```markdown
# Session: [YYYY-MM-DD HH:MM]

## Prompt Provided
\`\`\`
[Paste the EXACT prompt you were given, verbatim, no edits]
\`\`\`

## Specs Referenced
- [List any spec files referenced in the prompt or during the session]

## Session Goal
[1-2 sentence summary of what this session is trying to accomplish]
```

## At the END of Every Session

Append the following to the same session log file:

```markdown
## Changes Made

### Files Created
| File | Purpose |
|------|---------|
| `path/to/file` | What it does |

### Files Modified
| File | What Changed |
|------|-------------|
| `path/to/file` | Summary of changes |

### Files Deleted
| File | Why |
|------|-----|
| `path/to/file` | Reason |

## Decisions Made
[List any judgment calls, trade-offs, or architectural decisions with rationale.
These are the interesting bits for blog posts.]

## Problems Encountered
[Anything that didn't work the first time, workarounds, surprises in the data.
These are ALSO the interesting bits for blog posts.]

## Current State
[What's working now that wasn't before this session]

## Next Steps
[What should the next session pick up on]

## Session Stats
- Duration: ~[X] minutes
- Files created: X
- Files modified: X
- DQ rules added: X (if applicable)
- Governance artifacts produced: [list] (if applicable)
```

## Rules
- The verbatim prompt capture is non-negotiable — copy it exactly as received, including typos
- Be honest in Problems Encountered — the failures are better content than the successes
- Decisions Made should capture the WHY, not just the WHAT
- If a session spans multiple specs, log all of them
- Don't sanitize or polish — raw is better for the blog narrative
- Session logs are NEVER deleted, only appended to
- If you need to reference a previous session, check `docs/sessions/` first
