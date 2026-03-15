# Spec: Shared Glossary Registry

## Status: 🟠 IMPLEMENTATION

| Status | Meaning |
|--------|---------|
| 🟡 DRAFT | Riffing / initial design |
| 🔵 ARCH REVIEW | Awaiting @governance-reviewer approval |
| 🟠 IMPLEMENTATION | Agent pipeline running |
| 🟣 TESTING | DQ rules and validation |
| 🔴 CODE REVIEW | Reviewing |
| ✅ VERIFICATION | Build + DQ + governance verification |
| 🟢 COMPLETE | Shipped |
| ⚫ BLOCKED | Escalated to human |

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-03-15 |
| Author | Jeff + Claude Code |
| Spec Version | 1.0 |
| Last Updated | 2026-03-15 |
| Zone | Infrastructure |
| Primary Agent | @data-steward |
| Blocked By | — |
| Part Of | Framework Separation (Phase 1) |

---

## Problem Statement

Every project currently builds its own business glossary from scratch. Two projects in the same domain (e.g., SEC EDGAR) would independently discover and define the same terms — "Revenue", "CIK", "Accession Number" — with slightly different definitions, different BT-IDs, and no way to compare across projects.

The current SEC EDGAIR glossary already has the pattern: `xbrl-taxonomy` and `sec-edgar` sourced terms are auto-approved because they come from authoritative standards. But this is implicit — hardcoded in the @data-steward agent's behavior, not in a formal registry that the framework can load.

We need to externalize this into a three-tier glossary hierarchy that any project can inherit from.

## Design Principle

**The data is the truth.** Shared glossaries are accelerators, not requirements. A project with no glossary hints still works — EDA discovers the domain, @data-steward creates all terms as Tier 3 (project-specific, human approval required). Shared glossaries just let the steward skip discovery for well-known terms.

## Three-Tier Hierarchy

```
Tier 1: STANDARDS — published industry/regulatory standards (read-only, always auto-approved)
Tier 2: DOMAINS  — community-curated domain glossaries (shared, auto-approved)
Tier 3: PROJECT  — terms invented by this specific project (local, human approval required)
```

### Tier 1: Standards
- Published by external authorities (FASB, SEC, CMS, ISO, HL7)
- Read-only — projects cannot modify these definitions
- Always auto-approved regardless of `REQUIRE_HUMAN_APPROVAL` setting
- Framework ships with common standards; more can be added as JSON files
- Examples: `xbrl-us-gaap`, `sec-edgar`, `hl7-fhir`, `iso-20022`

### Tier 2: Domains
- Curated by domain pack maintainers or community
- Shared across projects in the same industry/domain
- Auto-approved (vetted by the domain community)
- Can reference Tier 1 terms via `related_terms`
- Examples: `finance` (financial reporting patterns), `healthcare` (claims/clinical patterns)

### Tier 3: Project
- Invented by this project for pipeline-specific concepts
- Local to the project's `governance/business-glossary.json`
- Always requires human approval (regardless of `REQUIRE_HUMAN_APPROVAL`)
- Can reference Tier 1 and Tier 2 terms
- Can be promoted to Tier 2 if useful across projects

## Success Criteria

1. `glossaries/` directory exists with `registry.yaml`, `standards/`, and `domains/` subdirectories
2. Current 54 glossary terms are split: 33 into `standards/` (8 sec-edgar + 25 xbrl-us-gaap), 0 into `domains/` (none exist yet), 21 remain as Tier 3 in project glossary
3. `src/infra/glossary_loader.py` can load a project glossary composed from inherited tiers
4. Each inherited term in the project glossary has `source_tier`, `read_only`, and `upstream_term_id` fields
5. @data-steward agent is updated to check inherited glossaries before proposing new terms
6. `governance/business-glossary.json` metadata section includes `inherited_from` list
7. Tests validate: tier loading, term inheritance, ID namespacing, read-only enforcement

## Input

- `governance/business-glossary.json` — current 54-term glossary to split
- `src/config.py` — `REQUIRE_HUMAN_APPROVAL` toggle
- `.claude/agents/data-steward.md` — agent definition to update

## Output

| Artifact | Path |
|----------|------|
| Registry index | `glossaries/registry.yaml` |
| XBRL US-GAAP standard glossary | `glossaries/standards/xbrl-us-gaap.json` |
| SEC EDGAR standard glossary | `glossaries/standards/sec-edgar.json` |
| Glossary loader | `src/infra/glossary_loader.py` |
| Updated project glossary | `governance/business-glossary.json` (Tier 3 terms only + inherited refs) |
| Updated data steward agent | `.claude/agents/data-steward.md` |
| Tests | `tests/infra/test_glossary_loader.py` |

## Standard Glossary Format

Each standard/domain glossary file follows this schema:

```json
{
  "glossary_metadata": {
    "name": "xbrl-us-gaap",
    "tier": 1,
    "authority": "Financial Accounting Standards Board (FASB)",
    "version": "2024",
    "description": "US GAAP XBRL Taxonomy — authoritative financial reporting concepts",
    "term_count": 25
  },
  "terms": [
    {
      "term_id": "ST-XBRL-001",
      "term": "Revenue",
      "definition": "Total revenue recognized from the sale of goods and services.",
      "source_reference": "us-gaap:Revenues",
      "synonyms": ["Sales", "Net Sales", "Total Revenue"],
      "category": "financial",
      "is_cde": true,
      "is_pii": false
    }
  ]
}
```

## Project Glossary Changes

After migration, `governance/business-glossary.json` looks like:

```json
{
  "glossary_metadata": {
    "version": "3.0",
    "term_count": 54,
    "inherited_from": [
      {"glossary": "xbrl-us-gaap", "tier": 1, "terms_inherited": 25},
      {"glossary": "sec-edgar", "tier": 1, "terms_inherited": 8}
    ]
  },
  "terms": [
    {
      "term_id": "BT-001",
      "term": "Central Index Key (CIK)",
      "source": "sec-edgar",
      "source_tier": 1,
      "upstream_term_id": "ST-SEC-001",
      "read_only": true,
      "status": "approved",
      "approved_by": "auto (inherited standard)",
      "...": "rest of fields unchanged"
    },
    {
      "term_id": "BT-010",
      "term": "Supersession Chain",
      "source": "project-specific",
      "source_tier": 3,
      "upstream_term_id": null,
      "read_only": false,
      "status": "approved",
      "approved_by": "human:jeff",
      "...": "rest of fields unchanged"
    }
  ]
}
```

## Registry Format

```yaml
# glossaries/registry.yaml
standards:
  - name: xbrl-us-gaap
    file: standards/xbrl-us-gaap.json
    authority: FASB
    term_count: 25
    description: "US GAAP XBRL Taxonomy financial reporting concepts"

  - name: sec-edgar
    file: standards/sec-edgar.json
    authority: SEC
    term_count: 8
    description: "SEC EDGAR filing types, entity identifiers, regulatory concepts"

domains:
  # None yet — created when domain packs mature
  # - name: finance
  #   file: domains/finance.json
  #   term_count: 0
  #   description: "Cross-project financial reporting patterns"
```

## Data Steward Agent Changes

Update `.claude/agents/data-steward.md` to:

1. **Check inherited glossaries first** — before proposing a new term, search Tier 1 and Tier 2 for an existing definition
2. **Link, don't duplicate** — if a matching term exists in a shared glossary, link to it (set `upstream_term_id`) instead of creating a new definition
3. **Only create Tier 3 terms for genuine gaps** — terms that no shared glossary covers
4. **Flag promotion candidates** — if a Tier 3 term seems broadly useful, note it as a candidate for Tier 2 promotion

## Scope Boundaries

- This spec does NOT create domain glossaries (Tier 2) — those emerge when multiple projects share terms
- This spec does NOT change the glossary term schema (fields like `is_cde`, `is_pii` stay the same)
- This spec does NOT modify any zone code (raw, base, consumable, ai-ready) — only infrastructure and governance
- ID migration: existing `BT-XXX` IDs are preserved. No renaming. The `upstream_term_id` field adds the link to the shared glossary without breaking existing references.

## Migration Plan

1. Extract 25 `xbrl-taxonomy` terms from `governance/business-glossary.json` → `glossaries/standards/xbrl-us-gaap.json`
2. Extract 8 `sec-edgar` terms → `glossaries/standards/sec-edgar.json`
3. Add `source_tier`, `upstream_term_id`, `read_only` fields to all 54 terms in project glossary
4. Create `glossaries/registry.yaml`
5. Create `src/infra/glossary_loader.py`
6. Update `governance/business-glossary.json` metadata with `inherited_from`
7. Update `.claude/agents/data-steward.md`
8. Write tests

## Agent Workflow

1. @governance-reviewer — Pre-implementation review
2. @primary-agent — Implementation (glossary split, loader, registry)
3. @data-analyst — N/A (no data to profile)
4. @dq-rule-writer — N/A (no data tables)
5. @dq-engineer — N/A
6. @lineage-tracker — Log glossary restructuring
7. @cde-tagger — N/A (CDEs unchanged)
8. @doc-generator — Update data dictionary with glossary tier docs
9. @governance-reviewer — Post-implementation check
10. @staff-engineer — Final review

---

## Claude Code Prompt

```
Read the spec at docs/specs/infra-glossary-registry.md in its entirety.

Build the three-tier shared glossary registry. This is the foundation for
domain-agnostic business term management — projects inherit from shared
standard and domain glossaries instead of every project reinventing terms.

Agent workflow:
1. @governance-reviewer — Pre-implementation review of this spec
2. @primary-agent — Implement glossary split, registry, and loader
3. @lineage-tracker — Log glossary restructuring lineage
4. @doc-generator — Update data dictionary with glossary tier documentation
5. @governance-reviewer — Post-implementation verification
6. @staff-engineer — Final quality review

Key changes:
1. glossaries/registry.yaml — CREATE — index of available shared glossaries
2. glossaries/standards/xbrl-us-gaap.json — CREATE — 25 terms extracted from project glossary
3. glossaries/standards/sec-edgar.json — CREATE — 8 terms extracted from project glossary
4. src/infra/glossary_loader.py — CREATE — loads composed glossary from inherited tiers
5. governance/business-glossary.json — MODIFY — add source_tier, upstream_term_id, read_only fields; update metadata
6. .claude/agents/data-steward.md — MODIFY — link-first behavior, check shared glossaries before proposing
7. tests/infra/test_glossary_loader.py — CREATE — tier loading, inheritance, read-only enforcement tests

No dependencies on other specs. Can be built in parallel with infra-domain-manifest.
```
