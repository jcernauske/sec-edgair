# Spec: Generic Concept Normalization

## Status: 🟢 COMPLETE

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
| Zone | Base |
| Primary Agent | @primary-agent |
| Blocked By | `infra-domain-manifest` |
| Part Of | Framework Separation (Phase 1) |

---

## Problem Statement

`src/base/xbrl_tag_normalization/` has two things tangled together:

1. **A generic tiered matching algorithm** (`normalize.py`) — classify any concept through exact → prefix → pattern → heuristic tiers. This algorithm works on any taxonomy, not just XBRL.
2. **~2,000 lines of XBRL-specific mappings** (`config.py`) — hardcoded `us-gaap` concept → business term rules. These are SEC EDGAR domain knowledge.

A different data source (healthcare claims with CPT codes, energy data with meter types) would need the same tiered matching algorithm but completely different mappings. The algorithm is framework; the mappings are domain pack.

## Design Principle

**The algorithm is generic. The mappings are domain knowledge.** The framework provides the matching engine. Domain packs provide the concept → business term mappings as JSON config files. If no mappings are provided, the pipeline pauses at concept normalization and presents the top concepts for human-assisted mapping.

## Success Criteria

1. `src/base/concept_normalization/` exists (renamed from `xbrl_tag_normalization`)
2. `normalize.py` loads mappings from JSON files (via `domain/concept-mappings/`) instead of importing from a Python config module
3. `domain/concept-mappings/xbrl_us_gaap.json` contains the ~2,000 lines extracted from Python config
4. The `ConceptNormalizer` class accepts a mappings directory path and works with any taxonomy
5. When no mappings exist for a concept, the normalizer returns `tier: "unmapped"` instead of failing
6. When no mappings directory exists at all, the normalizer logs a clear message and returns all concepts as unmapped
7. Existing base zone DQ scorecards pass with identical results
8. All references throughout codebase updated (imports, agent definitions, DQ rules, specs)
9. Tests validate: mapping loading, tiered matching, unmapped handling, no-config graceful degradation

## Input

- `src/base/xbrl_tag_normalization/` — current module to rename and refactor
- `src/base/xbrl_tag_normalization/config.py` — ~2,000 lines of XBRL mappings to extract
- `domain/manifest.yaml` — hints.concept_mappings path (from `infra-domain-manifest`)

## Output

| Artifact | Path |
|----------|------|
| Renamed module | `src/base/concept_normalization/` (all files) |
| Generic normalizer | `src/base/concept_normalization/normalize.py` |
| Mapping loader | `src/base/concept_normalization/config.py` (reads from JSON, not hardcoded) |
| XBRL mappings | `domain/concept-mappings/xbrl_us_gaap.json` |
| Backwards-compat | `src/base/xbrl_tag_normalization/` (re-exports from new location) |
| Tests | `tests/base/test_concept_normalization.py` |

## Concept Mapping JSON Format

```json
{
  "mapping_metadata": {
    "name": "xbrl-us-gaap",
    "taxonomy": "us-gaap",
    "version": "2024",
    "description": "XBRL US GAAP concept to business term mappings",
    "term_count": 25,
    "rule_count": 150
  },
  "business_terms": {
    "BT-024": {
      "name": "Revenue",
      "financial_statement": "income_statement",
      "category": "line_item"
    }
  },
  "exact_mappings": {
    "Revenues": ["BT-024", "income_statement", "line_item"],
    "RevenueFromContractWithCustomerExcludingAssessedTax": ["BT-024", "income_statement", "line_item"],
    "SalesRevenueNet": ["BT-024", "income_statement", "line_item"]
  },
  "prefix_rules": [
    {
      "prefix": "Revenue",
      "business_term_id": "BT-024",
      "financial_statement": "income_statement",
      "category": "line_item"
    }
  ],
  "pattern_rules": [
    {
      "pattern": "(?i)^(total|net)?revenue",
      "business_term_id": "BT-024",
      "financial_statement": "income_statement",
      "category": "line_item"
    }
  ],
  "heuristic_categories": {
    "asset": {"financial_statement": "balance_sheet", "category": "line_item"},
    "liability": {"financial_statement": "balance_sheet", "category": "line_item"},
    "expense": {"financial_statement": "income_statement", "category": "line_item"}
  }
}
```

## ConceptNormalizer API

```python
# src/base/concept_normalization/normalize.py

class ConceptNormalizer:
    """Generic tiered concept normalization engine.

    Loads concept → business term mappings from JSON config files.
    Works with any taxonomy — XBRL, CPT codes, meter types, etc.
    """

    def __init__(self, mappings_dir: Path | None = None):
        """Load mappings from all JSON files in mappings_dir.

        If mappings_dir is None or doesn't exist, operates in
        discovery mode — all concepts return as unmapped.
        """

    def classify(self, concept: str) -> dict:
        """Classify a concept through the tier hierarchy.

        Returns:
            {
                "business_term_id": "BT-024" | None,
                "business_term": "Revenue" | None,
                "financial_statement": "income_statement" | None,
                "category": "line_item" | None,
                "tier": 1 | 2 | 3 | 4 | "unmapped",
                "confidence": 1.0 | 0.7 | 0.6 | 0.3 | 0.0,
                "mapping_method": "exact_match" | "prefix_match" | "pattern_match" | "heuristic" | "unmapped",
                "source_mapping": "xbrl-us-gaap" | None
            }
        """

    def get_unmapped_concepts(self) -> list[str]:
        """Return all concepts that have been classified as unmapped.
        Useful for presenting to humans for iterative mapping."""

    def get_mapping_coverage(self) -> dict:
        """Return mapping coverage stats: total classified, per-tier counts, unmapped count."""
```

## Discovery Mode (No Mappings)

When `hints.concept_mappings` is missing from the manifest or the directory is empty:

1. The normalizer logs: `"No concept mappings found. Operating in discovery mode — all concepts will be unmapped."`
2. Every `classify()` call returns `tier: "unmapped"`, `confidence: 0.0`
3. The pipeline continues — unmapped concepts still land in base tables with `tier: "unmapped"`
4. The EDA report shows the unmapped concept distribution
5. @data-steward can review the top unmapped concepts and propose mappings iteratively
6. Once mappings are added to `domain/concept-mappings/`, re-running normalization picks them up

This is the "no hints" path — the pipeline works, it just needs human input to map concepts.

## Migration Strategy

1. Create `src/base/concept_normalization/` directory
2. Copy all files from `src/base/xbrl_tag_normalization/` to new location
3. Extract Python config dicts from `config.py` into `domain/concept-mappings/xbrl_us_gaap.json`
4. Rewrite `normalize.py` to load from JSON via `ConceptNormalizer` class
5. Rewrite `config.py` to read mapping path from manifest hints
6. Create backwards-compat `src/base/xbrl_tag_normalization/__init__.py` that re-exports from new location
7. Update all imports, DQ rule SQL references, agent definitions, and specs
8. Run base zone DQ scorecards to verify identical results

## References to Update

- `src/base/xbrl_tag_normalization/` → `src/base/concept_normalization/` (all internal imports)
- `governance/dq-rules/base-tag-normalization.json` — SQL table references (if any)
- `governance/dq-rules/base-xbrl-tag-normalization.json` — SQL table references (if any)
- `.claude/agents/` — any agent that references "xbrl_tag_normalization" or "tag normalization"
- `docs/specs/base-xbrl-tag-normalization.md` — add note pointing to new location
- `README.md` — update any architecture references

## Scope Boundaries

- This spec does NOT change the Iceberg table name (`base.tag_mappings` or equivalent) — only the Python module name
- This spec does NOT add new concept mappings — only extracts existing ones to JSON
- This spec does NOT change the tiered matching algorithm — same logic, different config source
- This spec does NOT modify DQ rule SQL — only updates file paths if needed
- The backwards-compat re-export ensures nothing breaks during transition

## Agent Workflow

1. @governance-reviewer — Pre-implementation review
2. @primary-agent — Implementation (rename, extract mappings, refactor normalizer)
3. @data-analyst — N/A (no new data)
4. @dq-rule-writer — N/A (no new rules)
5. @dq-engineer — Run existing base DQ scorecards to verify identical results
6. @lineage-tracker — Update lineage for new module paths
7. @cde-tagger — N/A
8. @doc-generator — Update data dictionary with concept normalization docs
9. @governance-reviewer — Post-implementation verification
10. @staff-engineer — Final review

---

## Claude Code Prompt

```
Read the spec at docs/specs/infra-concept-normalization.md in its entirety.

Generalize the concept normalization system. The tiered matching algorithm
is domain-agnostic — it works on any taxonomy. The XBRL-specific mappings
move to domain/concept-mappings/ as JSON config that the engine loads at runtime.

IMPORTANT: This spec depends on infra-domain-manifest being complete.
Verify that domain/manifest.yaml and src/domain_loader.py exist before starting.

Agent workflow:
1. @governance-reviewer — Pre-implementation review of this spec
2. @primary-agent — Rename module, extract mappings to JSON, refactor normalizer to load from config
3. @dq-engineer — Run existing base DQ scorecards to verify identical results
4. @lineage-tracker — Update lineage for new module paths
5. @doc-generator — Update data dictionary with concept normalization documentation
6. @governance-reviewer — Post-implementation verification
7. @staff-engineer — Final quality review

Key changes:
1. src/base/concept_normalization/ — CREATE — renamed module directory
2. src/base/concept_normalization/normalize.py — REFACTOR — ConceptNormalizer class, loads from JSON
3. src/base/concept_normalization/config.py — REFACTOR — reads mapping path from manifest
4. domain/concept-mappings/xbrl_us_gaap.json — CREATE — ~2,000 lines extracted from Python config
5. src/base/xbrl_tag_normalization/__init__.py — MODIFY — backwards-compat re-exports
6. tests/base/test_concept_normalization.py — CREATE — normalizer tests including discovery mode

Depends on: infra-domain-manifest (needs domain/manifest.yaml and src/domain_loader.py)
```
