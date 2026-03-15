# Spec: Base Ingestor Abstraction

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
| Zone | Infrastructure / Raw |
| Primary Agent | @primary-agent |
| Blocked By | `infra-domain-manifest` |
| Part Of | Framework Separation (Phase 1) |

---

## Problem Statement

The raw zone ingestion pipeline (`src/raw/xbrl_company_facts/ingest.py`) is a monolith that mixes generic lakehouse operations (Iceberg table creation, dedup, append, lineage emission) with SEC-specific operations (EDGAR API calls, XBRL JSON flattening, CIK padding). A different data source would need to copy-paste the entire file and replace the domain parts.

We need an abstract base class that captures the generic ingest pattern — fetch → flatten → dedup → write → DQ gate — so domain packs only implement `fetch()` and `flatten()`.

## Design Principle

**Domain packs bring the data. The framework brings the lakehouse.** A domain pack author should never need to know about PyIceberg, DuckDB, dedup grains, snapshot management, lineage emission, or DQ gating. They write two functions: "here's how to get the data" and "here's how to flatten it into rows."

## Success Criteria

1. `src/raw/base_ingestor.py` defines a `BaseIngestor` ABC with `fetch()` and `flatten()` as abstract methods
2. `BaseIngestor.ingest()` handles the full generic pipeline: table creation, dedup, append, lineage, DQ
3. `src/raw/xbrl_company_facts/ingest.py` is refactored to extend `BaseIngestor`
4. The existing raw zone pipeline produces identical results (same row counts, same DQ scorecard)
5. `BaseIngestor` reads source config from `DomainManifest` (via `domain_loader.py`)
6. Tests validate the ABC contract and verify the XBRL ingestor still works

## Input

- `src/raw/xbrl_company_facts/ingest.py` — current monolithic ingestor
- `src/domain_loader.py` — manifest loader (from `infra-domain-manifest` spec)
- `domain/manifest.yaml` — source configuration
- `src/infra/iceberg_setup.py` — Iceberg utilities

## Output

| Artifact | Path |
|----------|------|
| Base ingestor ABC | `src/raw/base_ingestor.py` |
| Refactored XBRL ingestor | `src/raw/xbrl_company_facts/ingest.py` |
| Tests | `tests/raw/test_base_ingestor.py` |

## BaseIngestor API

```python
# src/raw/base_ingestor.py

class BaseIngestor(ABC):
    """Framework base class for raw zone ingestion.

    Domain packs extend this and implement fetch() and flatten().
    The framework handles everything else: Iceberg table management,
    dedup, lineage emission, and DQ gating.
    """

    def __init__(self, source_config: SourceConfig, manifest: DomainManifest):
        self.source = source_config
        self.manifest = manifest

    @abstractmethod
    def fetch(self, entities: dict, method: str, **kwargs) -> dict[str, Any]:
        """Fetch raw data from the source.

        Args:
            entities: {entity_id: label} dict from source config
            method: fetch method name (must exist in source_config.fetch)

        Returns:
            {entity_id: raw_data} — raw data per entity, any format.
            The framework passes each value to flatten().
        """

    @abstractmethod
    def flatten(self, raw_data: Any, entity_id: str) -> list[dict]:
        """Flatten raw data into tabular records.

        Args:
            raw_data: whatever fetch() returned for one entity
            entity_id: the entity identifier

        Returns:
            List of flat dicts ready for Iceberg append.
            The framework adds ingested_at, source_url, source_method, load_date.
        """

    def ingest(
        self,
        entities: dict | None = None,
        method: str = "api",
        warehouse_path: Path | None = None,
        catalog_path: Path | None = None,
    ) -> dict:
        """Generic ingest pipeline: fetch → flatten → dedup → write → DQ.

        This method is NOT abstract — it's the framework's implementation.
        Domain packs do NOT override this.
        """
        # 1. Resolve config (entities from source_config if not provided)
        # 2. Get or create Iceberg table
        # 3. Build existing grain set for dedup
        # 4. Call self.fetch(entities, method)
        # 5. For each entity: call self.flatten(raw_data, entity_id)
        # 6. Add framework metadata (ingested_at, source_url, source_method, load_date)
        # 7. Dedup against existing grains (using source_config.dedup_grain)
        # 8. Append to Iceberg
        # 9. Emit lineage
        # 10. Return summary
```

## Refactored XBRL Ingestor

```python
# src/raw/xbrl_company_facts/ingest.py

class XBRLCompanyFactsIngestor(BaseIngestor):
    """SEC EDGAR XBRL Company Facts ingestor."""

    def fetch(self, entities, method, **kwargs):
        if method == "api":
            return {eid: fetch_company_facts(eid, ...) for eid in entities}
        elif method == "bulk_zip":
            return fetch_bulk_company_facts(list(entities.keys()), ...)

    def flatten(self, raw_data, entity_id):
        return flatten_company_facts(raw_data)


# Backwards-compatible function API
def ingest_company_facts(**kwargs) -> dict:
    """Legacy API — wraps XBRLCompanyFactsIngestor."""
    manifest = load_manifest()
    source = get_source(manifest, "xbrl_company_facts")
    ingestor = XBRLCompanyFactsIngestor(source, manifest)
    return ingestor.ingest(**kwargs)
```

## What BaseIngestor Handles (Domain Packs Don't Touch)

| Concern | How |
|---------|-----|
| Iceberg table creation | Reads `source_config.namespace` + `source_config.table`, creates if not exists |
| Schema | Domain pack's source config YAML includes the Iceberg schema definition |
| Dedup | Reads `source_config.dedup_grain`, builds grain set from existing data |
| Metadata columns | Adds `ingested_at`, `source_url`, `source_method`, `load_date` to every row |
| Lineage | Emits OpenLineage start/complete/fail events |
| DQ gating | Optionally runs DQ rules after write (if rules exist for this spec) |
| Error handling | Wraps fetch/flatten in try/except, emits lineage fail on error |

## Scope Boundaries

- This spec does NOT create new data sources — it only refactors the existing XBRL ingestor
- This spec does NOT change the Iceberg schema for `raw.xbrl_company_facts`
- This spec does NOT modify DQ rules or scorecards
- This spec does NOT move the schema definition (`schema.py` stays in place)
- The `BaseIngestor.ingest()` implementation is extracted from the current `ingest_company_facts()` — same logic, same behavior, just refactored

## Agent Workflow

1. @governance-reviewer — Pre-implementation review
2. @primary-agent — Implementation (ABC, refactor XBRL ingestor)
3. @data-analyst — N/A (no new data)
4. @dq-rule-writer — N/A (no new rules)
5. @dq-engineer — Run existing raw DQ scorecards to verify identical results
6. @lineage-tracker — Update lineage to reference new module paths
7. @cde-tagger — N/A
8. @doc-generator — Update data dictionary with BaseIngestor docs
9. @governance-reviewer — Post-implementation verification
10. @staff-engineer — Final review

---

## Claude Code Prompt

```
Read the spec at docs/specs/infra-base-ingestor.md in its entirety.

Build the BaseIngestor abstraction. This is what makes the raw zone
pluggable — domain packs implement fetch() and flatten(), the framework
handles everything else (Iceberg, dedup, lineage, DQ gating).

IMPORTANT: This spec depends on infra-domain-manifest being complete.
Verify that domain/manifest.yaml and src/domain_loader.py exist before starting.

Agent workflow:
1. @governance-reviewer — Pre-implementation review of this spec
2. @primary-agent — Implement BaseIngestor ABC, refactor XBRL ingestor to extend it
3. @dq-engineer — Run existing raw DQ scorecards to verify identical results
4. @lineage-tracker — Update lineage for new module paths
5. @doc-generator — Update data dictionary with BaseIngestor documentation
6. @governance-reviewer — Post-implementation verification
7. @staff-engineer — Final quality review

Key changes:
1. src/raw/base_ingestor.py — CREATE — abstract base class for raw zone ingestion
2. src/raw/xbrl_company_facts/ingest.py — REFACTOR — extend BaseIngestor, keep backwards-compat function
3. tests/raw/test_base_ingestor.py — CREATE — ABC contract and XBRL ingestor tests

Depends on: infra-domain-manifest (needs domain/manifest.yaml and src/domain_loader.py)
```
