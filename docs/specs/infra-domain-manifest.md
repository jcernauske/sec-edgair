# Spec: Domain Manifest and Loader

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
| Primary Agent | @primary-agent |
| Blocked By | — |
| Part Of | Framework Separation (Phase 1) |

---

## Problem Statement

All data source configuration is hardcoded in Python modules — SEC EDGAR API endpoints in `src/raw/xbrl_company_facts/config.py`, company rosters, rate limits, User-Agent strings, schema definitions. This makes the framework inseparable from SEC EDGAR data.

We need a single declarative file (`domain/manifest.yaml`) that tells the framework how to acquire data from any source, without hardcoding domain assumptions into the framework itself.

## Design Principle

**The manifest is for data ACQUISITION, not domain semantics.** It tells the framework where to get data and how to land it. It does NOT tell the framework what the data means — that's discovered through EDA.

Optional `hints` can accelerate the pipeline by providing domain knowledge upfront, but the framework must work without them.

## Success Criteria

1. `domain/manifest.yaml` exists with SEC EDGAR source configuration
2. `domain/sources/xbrl_company_facts.yaml` defines the source schema, entities, dedup grain, and fetch config
3. `domain/sources/fetchers/` contains the existing `fetch_api.py` and `fetch_bulk.py` (moved, not rewritten)
4. `domain/flatten/xbrl_flattener.py` contains the existing `flatten.py` (moved, not rewritten)
5. `src/domain_loader.py` can parse `domain/manifest.yaml` and return typed config objects
6. `src/raw/xbrl_company_facts/config.py` reads from the manifest instead of hardcoding values
7. Existing raw zone ingest pipeline still works identically (all DQ scorecards pass)
8. Tests validate manifest parsing, missing hints handling, and source config loading

## Input

- `src/raw/xbrl_company_facts/config.py` — hardcoded SEC config to extract
- `src/raw/xbrl_company_facts/fetch_api.py` — fetcher to move
- `src/raw/xbrl_company_facts/fetch_bulk.py` — fetcher to move
- `src/raw/xbrl_company_facts/flatten.py` — flattener to move
- `src/raw/xbrl_company_facts/schema.py` — schema definition to reference

## Output

| Artifact | Path |
|----------|------|
| Domain manifest | `domain/manifest.yaml` |
| Source definition | `domain/sources/xbrl_company_facts.yaml` |
| API fetcher | `domain/sources/fetchers/api_fetcher.py` (moved from src/raw) |
| Bulk fetcher | `domain/sources/fetchers/bulk_fetcher.py` (moved from src/raw) |
| Flattener | `domain/flatten/xbrl_flattener.py` (moved from src/raw) |
| Manifest loader | `src/domain_loader.py` |
| Updated raw config | `src/raw/xbrl_company_facts/config.py` (reads from manifest) |
| Tests | `tests/infra/test_domain_loader.py` |

## Manifest Schema

```yaml
# domain/manifest.yaml
name: sec-edgar
version: "1.0"
description: "SEC EDGAR XBRL financial data"

sources:
  - name: xbrl_company_facts
    source_config: domain/sources/xbrl_company_facts.yaml
    fetcher: domain/sources/fetchers/api_fetcher.py
    flattener: domain/flatten/xbrl_flattener.py

# Optional hints — accelerators, not requirements
# If missing, the pipeline discovers these from EDA
hints:
  entity_id_field: cik
  time_field: end_date
  glossary:
    inherit:
      - standard:xbrl-us-gaap
      - standard:sec-edgar
  concept_mappings: domain/concept-mappings/
  metrics: domain/metrics/
  grouping_taxonomy: domain/grouping-taxonomy/
  anomaly_rules: domain/anomaly-rules/
  chat_context: domain/chat-context/system_prompt.md
```

## Source Config Schema

```yaml
# domain/sources/xbrl_company_facts.yaml
name: xbrl_company_facts
namespace: raw
table: xbrl_company_facts

fetch:
  api:
    url_template: "https://data.sec.gov/api/xbrl/companyfacts/CIK{entity_id_padded}.json"
    headers:
      User-Agent: "SEC-EDGAIR jeff.cernauske@gmail.com"
    rate_limit_seconds: 0.1
  bulk:
    url: "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip"

entities:
  320193: "Apple Inc."
  19617: "JPMorgan Chase & Co."
  789019: "Microsoft Corp."
  1018724: "Amazon.com Inc."
  1652044: "Alphabet Inc."
  1326801: "Meta Platforms Inc."
  1318605: "Tesla Inc."
  1067983: "Berkshire Hathaway Inc."
  200406: "Johnson & Johnson"
  104169: "Walmart Inc."
  34088: "Exxon Mobil Corp."
  1403161: "Visa Inc."
  731766: "UnitedHealth Group Inc."
  80424: "Procter & Gamble Co."
  21344: "Coca-Cola Co."
  78003: "Pfizer Inc."
  1065280: "Netflix Inc."
  886982: "Goldman Sachs Group Inc."
  12927: "Boeing Co."
  50863: "Intel Corp."

dedup_grain:
  - cik
  - accession_number
  - concept
  - unit
  - end_date

cache_dir: data/raw/json_cache
```

## Domain Loader API

```python
# src/domain_loader.py

@dataclass
class SourceConfig:
    name: str
    namespace: str
    table: str
    fetch: dict
    entities: dict
    dedup_grain: list[str]
    cache_dir: Path

@dataclass
class DomainHints:
    entity_id_field: str | None
    time_field: str | None
    glossary_inherit: list[str]     # e.g., ["standard:xbrl-us-gaap"]
    concept_mappings: Path | None
    metrics: Path | None
    grouping_taxonomy: Path | None
    anomaly_rules: Path | None
    chat_context: Path | None

@dataclass
class DomainManifest:
    name: str
    version: str
    description: str
    sources: list[SourceConfig]
    hints: DomainHints              # all fields None if no hints block

def load_manifest(manifest_path: Path | None = None) -> DomainManifest:
    """Load domain manifest. Defaults to PROJECT_ROOT / 'domain' / 'manifest.yaml'."""

def get_source(manifest: DomainManifest, source_name: str) -> SourceConfig:
    """Get a specific source config by name."""
```

## Migration Strategy

This is a **move-and-wrap**, not a rewrite:

1. Move `fetch_api.py` → `domain/sources/fetchers/api_fetcher.py` (add backwards-compat import in original location)
2. Move `fetch_bulk.py` → `domain/sources/fetchers/bulk_fetcher.py` (add backwards-compat import)
3. Move `flatten.py` → `domain/flatten/xbrl_flattener.py` (add backwards-compat import)
4. Extract hardcoded values from `src/raw/xbrl_company_facts/config.py` into YAML files
5. Update `config.py` to load from manifest via `domain_loader.py`
6. Existing imports throughout codebase continue to work (backwards-compat re-exports)

## Scope Boundaries

- This spec does NOT create the `BaseIngestor` ABC — that's `infra-base-ingestor`
- This spec does NOT move concept mappings — that's `infra-concept-normalization`
- This spec does NOT change any base/consumable/ai-ready code
- The hints section is defined but NOT consumed by any code in this spec — downstream specs will read hints as needed
- Backwards-compat imports in original locations ensure nothing breaks

## Agent Workflow

1. @governance-reviewer — Pre-implementation review
2. @primary-agent — Implementation (manifest, source configs, loader, file moves)
3. @data-analyst — N/A (no data to profile)
4. @dq-rule-writer — N/A (no data tables)
5. @dq-engineer — Run existing raw DQ scorecards to verify nothing broke
6. @lineage-tracker — Log manifest creation lineage
7. @cde-tagger — N/A
8. @doc-generator — Update data dictionary with manifest documentation
9. @governance-reviewer — Post-implementation verification
10. @staff-engineer — Final review

---

## Claude Code Prompt

```
Read the spec at docs/specs/infra-domain-manifest.md in its entirety.

Build the domain manifest system. This is the mechanism that makes the
framework data-source agnostic — all source configuration moves from
hardcoded Python to declarative YAML that any domain pack can provide.

Agent workflow:
1. @governance-reviewer — Pre-implementation review of this spec
2. @primary-agent — Implement manifest, source configs, loader, move fetchers/flattener
3. @dq-engineer — Run existing raw DQ scorecards to verify nothing broke
4. @lineage-tracker — Log manifest creation lineage
5. @doc-generator — Update data dictionary with manifest documentation
6. @governance-reviewer — Post-implementation verification
7. @staff-engineer — Final quality review

Key changes:
1. domain/manifest.yaml — CREATE — domain identity and source pointers
2. domain/sources/xbrl_company_facts.yaml — CREATE — source config extracted from Python
3. domain/sources/fetchers/api_fetcher.py — MOVE — from src/raw/xbrl_company_facts/fetch_api.py
4. domain/sources/fetchers/bulk_fetcher.py — MOVE — from src/raw/xbrl_company_facts/fetch_bulk.py
5. domain/flatten/xbrl_flattener.py — MOVE — from src/raw/xbrl_company_facts/flatten.py
6. src/domain_loader.py — CREATE — manifest parser returning typed config objects
7. src/raw/xbrl_company_facts/config.py — MODIFY — read from manifest instead of hardcoding
8. tests/infra/test_domain_loader.py — CREATE — manifest parsing and source config tests

No dependencies on other specs. Can be built in parallel with infra-glossary-registry.
```
