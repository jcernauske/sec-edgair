# Separation Plan: Domain-Agnostic Data Governance Framework

**Date:** 2026-03-15
**Status:** DRAFT (v2 — incorporates EDA-first discovery principle)
**Goal:** Extract a reusable framework from SEC EDGAIR that can ingest, govern, and transform *any* structured data through the same agent-driven pipeline.

---

## 0. The Chicken-and-Egg Problem: EDA Before Domain Knowledge

### The Current Assumption (Wrong for a Generic Framework)

The current pipeline front-loads domain knowledge:

```
SEC EDGAIR today:
  domain/manifest.yaml → tells agents "this is financial data"
  → data-steward proposes terms like "Revenue", "CIK"
  → semantic-modeler builds models using those terms
  → data-analyst runs EDA knowing what to look for
  → dq-rule-writer sets thresholds knowing what "normal" means
```

This is backwards for a domain-agnostic framework. **You can't tell the data analyst what the data is before they've looked at it.** The data is the truth.

### The Correct Order: Data Tells You What It Is

```
Generic framework:
  raw data lands (schema-on-read, no assumptions)
  → data-analyst runs EDA BLIND — no domain context
    - discovers: 20 distinct values in field "cik" (looks like an entity ID)
    - discovers: 3,289 distinct values in "concept" (looks like a taxonomy)
    - discovers: 39% null in "start_date" (structural pattern, not missing data)
    - discovers: values range from -2.9T to 80.8T (financial magnitudes)
    - discovers: field "accession_number" matches regex \d{10}-\d{2}-\d{6}
  → EDA report becomes the source of truth for domain discovery
  → data-steward reads EDA, proposes business terms FROM the data
  → semantic-modeler builds models FROM the discovered structure
  → dq-rule-writer sets thresholds FROM the observed distributions
```

### What This Changes in the Pipeline

**Raw Zone Pipeline (revised for generic framework):**

| # | Current (SEC-specific) | Generic (EDA-first) | Why |
|---|------------------------|---------------------|-----|
| 1 | @governance-reviewer pre-check | @governance-reviewer pre-check | Same — checks spec exists |
| 2 | @primary-agent ingests | @primary-agent ingests | Same — data lands raw |
| 3 | @data-analyst EDA (with domain context) | **@data-analyst EDA (BLIND — no domain assumptions)** | **Changed** — analyst discovers the domain |
| 4 | @dq-rule-writer writes rules | @dq-rule-writer writes rules from EDA | Same — rules come from evidence |
| 5 | @dq-engineer executes | @dq-engineer executes | Same |
| 6-9 | lineage, CDE, docs, review | lineage, CDE, docs, review | Same |

**Base Zone Pipeline (revised):**

| # | Current | Generic | Why |
|---|---------|---------|-----|
| 1 | Pre-review | Pre-review | Same |
| 2 | @data-steward proposes terms (from spec/domain knowledge) | **@data-steward proposes terms (from raw EDA report)** | **Changed** — terms emerge from data, not from domain expertise |
| 3 | @semantic-modeler proposes conceptual model | Same, but informed by EDA discoveries | Model reflects what the data actually contains |
| 4 | @semantic-modeler proposes logical model | Same | |
| 5 | @data-analyst EDA on base data | Same — but still blind to domain, profiles what the transformations produced | |
| 6+ | Rest of pipeline | Same | |

### The Key Principle

> **The domain manifest (`domain/manifest.yaml`) is a HINT, not a requirement.**
>
> - It tells the fetcher where to get data and how to authenticate
> - It tells the ingestor what schema to expect for raw landing
> - It does NOT tell the data analyst what the data means
> - It does NOT pre-define business terms
> - It does NOT assume what DQ thresholds should be
>
> The data analyst's EDA report is the actual domain discovery artifact. Everything downstream reads the EDA report, not the manifest, to understand the domain.

### What This Means for the Domain Manifest

The manifest shrinks. It only needs to know how to *get* the data, not what it *means*:

```yaml
# domain/manifest.yaml — MINIMAL version
name: sec-edgar
version: "1.0"
description: "SEC EDGAR XBRL financial data"   # human label, not used by agents

sources:
  - name: xbrl_company_facts
    fetcher: domain/sources/fetchers/api_fetcher.py
    flattener: domain/flatten/xbrl_flattener.py
    schema: domain/sources/xbrl_company_facts.yaml   # landing schema only
    rate_limit: 0.1

# REMOVED: entity_id, time_grain, glossary-seed, concept-mappings,
#          metrics, anomaly-rules, grouping-taxonomy, chat-context
# These are all DISCOVERED by the pipeline, not pre-declared.
```

### But Wait — What About the Concept Mappings?

The 2,000-line XBRL concept → business term mapping in `src/base/xbrl_tag_normalization/config.py` IS domain knowledge that can't be discovered from EDA alone. The data analyst can see that there are 3,289 distinct concepts, but can't know that `us-gaap:Revenues` maps to "Revenue."

This is a genuine chicken-and-egg:
- **Option A: Domain pack provides mappings upfront** — faster but assumes domain expertise before data is seen
- **Option B: Data analyst discovers clusters, human provides mappings iteratively** — slower but truly data-driven
- **Option C: Hybrid** — EDA discovers the structure (3,289 concepts, 4 taxonomies, frequency distributions), then concept mapping is a SEPARATE human-assisted step that happens AFTER EDA but BEFORE base zone modeling

**Recommendation: Option C.** The manifest can optionally include `concept-mappings/` for domains where the taxonomy is known. But the framework doesn't require it — if mappings are missing, the pipeline pauses at the concept normalization step and says "I found 3,289 distinct concepts. Here are the top 50 by frequency. How should these be grouped?"

This makes concept mapping an **optional accelerator**, not a prerequisite.

### Updated Manifest (Hybrid)

```yaml
# domain/manifest.yaml — hybrid version
name: sec-edgar
version: "1.0"
description: "SEC EDGAR XBRL financial data"

sources:
  - name: xbrl_company_facts
    fetcher: domain/sources/fetchers/api_fetcher.py
    flattener: domain/flatten/xbrl_flattener.py
    schema: domain/sources/xbrl_company_facts.yaml
    rate_limit: 0.1

# OPTIONAL domain hints — accelerators, not requirements
# If missing, the pipeline discovers these from EDA
hints:
  entity_id_field: cik                     # helps EDA know what to group by
  time_field: end_date                     # helps EDA detect temporal patterns
  concept_mappings: domain/concept-mappings/  # pre-built taxonomy mappings
  glossary_seed: domain/glossary-seed.json    # starter terms (auto-approved if from external standard)
  metrics: domain/metrics/                    # pre-defined derived metrics
  grouping_taxonomy: domain/grouping-taxonomy/ # peer grouping scheme
```

The `hints` section is entirely optional. Without it, the pipeline still works — it just asks more questions.

---

## 0.1. Shared Glossaries: Don't Reinvent Business Terms Per Project

### The Problem

If every project builds its own glossary from EDA, two healthcare claims projects will independently discover "NPI", "DRG Code", and "Readmission" — writing slightly different definitions, assigning different BT-IDs, and creating a governance mess when someone wants to compare across projects.

The current SEC EDGAIR glossary already has this pattern baked in:

| Source | Count | Auto-Approve? | Who Owns It |
|--------|-------|---------------|-------------|
| `xbrl-taxonomy` | 25 terms | Yes | FASB (external standard) |
| `sec-edgar` | 8 terms | Yes | SEC (external standard) |
| `project-specific` | 21 terms | No — human approval | This project |

The `xbrl-taxonomy` and `sec-edgar` terms are *shared knowledge*. Any SEC project would need them. The `project-specific` terms are local inventions (e.g., "Supersession Chain", "Conformation Status").

### The Three-Tier Glossary Hierarchy

```
┌─────────────────────────────────────────────┐
│  Tier 1: STANDARD GLOSSARIES (read-only)    │
│  Published industry/regulatory standards    │
│  Source of truth: the standard itself       │
│  Examples:                                  │
│    - xbrl-us-gaap (FASB taxonomy)           │
│    - sec-edgar (SEC filing concepts)        │
│    - hl7-fhir (healthcare interop)          │
│    - iso-20022 (financial messaging)        │
│    - cms-drg (Medicare diagnosis groups)    │
│  Auto-approved: always                      │
│  Maintained by: nobody in this project      │
├─────────────────────────────────────────────┤
│  Tier 2: DOMAIN GLOSSARIES (shared)         │
│  Curated term sets for a domain/industry    │
│  Source of truth: the domain community      │
│  Examples:                                  │
│    - edgair-finance (financial reporting)   │
│    - edgair-healthcare (claims/clinical)    │
│    - edgair-energy (utility/grid data)      │
│  Auto-approved: yes (vetted by community)   │
│  Maintained by: domain pack maintainers     │
├─────────────────────────────────────────────┤
│  Tier 3: PROJECT GLOSSARIES (local)         │
│  Terms invented by this specific project    │
│  Source of truth: this project              │
│  Examples:                                  │
│    - "Supersession Chain"                   │
│    - "Conformation Status"                  │
│    - "DQ Gate Pass"                         │
│  Auto-approved: NEVER — human approval      │
│  Maintained by: this project's data steward │
└─────────────────────────────────────────────┘
```

### How It Works

**The framework ships with a `glossaries/` registry:**

```
edgair/
├── glossaries/
│   ├── registry.yaml           # index of available glossaries
│   ├── standards/              # Tier 1: published standards (shipped with framework or fetched)
│   │   ├── xbrl-us-gaap.json
│   │   ├── sec-edgar.json
│   │   ├── iso-20022.json
│   │   └── ...
│   └── domains/                # Tier 2: community-curated domain glossaries
│       ├── finance.json
│       ├── healthcare.json
│       └── ...
```

**A project's `governance/business-glossary.json` composes from these tiers:**

```yaml
# domain/manifest.yaml
glossary:
  inherit:
    - standard:xbrl-us-gaap     # Tier 1 — auto-approved, read-only
    - standard:sec-edgar         # Tier 1 — auto-approved, read-only
    - domain:finance             # Tier 2 — auto-approved, shared
  # Tier 3 terms are discovered by EDA + @data-steward, stored locally
```

At project init, the framework:
1. Pulls inherited glossary terms into `governance/business-glossary.json` with `source` set to their tier
2. Assigns each inherited term a local `BT-XXX` ID (or preserves the upstream ID with a prefix)
3. Marks them `auto-approved` and `read-only: true`
4. @data-steward can reference these terms but cannot modify them
5. New terms discovered from EDA become Tier 3 (`project-specific`) and require human approval

### What This Means for the Data Steward

The @data-steward's job changes:

**Before (SEC EDGAIR today):** "Here's a spec. What business terms do we need? Let me check if XBRL taxonomy has a definition."

**After (generic framework):** "Here's the EDA report. The data has a field called `provider_npi` with 4,200 distinct values. Let me check if any inherited glossary already defines 'NPI'."
- If `standard:cms` defines NPI → use it, auto-approved
- If `domain:healthcare` defines NPI → use it, auto-approved
- If nobody defines NPI → propose a Tier 3 project-specific term → human approval gate

**The steward becomes a LINKER first, CREATOR second.** Most terms in a well-covered domain will already exist in Tier 1/2. The steward's real value is:
1. Linking data fields to existing shared terms
2. Proposing new Tier 3 terms only when the shared glossaries have gaps
3. Flagging when a project-specific term should be promoted to the domain glossary (Tier 3 → Tier 2)

### Term ID Namespacing

To avoid collisions across tiers:

```
Tier 1: ST-XBRL-001, ST-SEC-001, ST-CMS-001   (ST = Standard Term)
Tier 2: DT-FIN-001, DT-HC-001                   (DT = Domain Term)
Tier 3: BT-001, BT-002                          (BT = Business Term, project-local)
```

Or simpler — a single `BT-XXX` sequence per project with a `source_tier` field:

```json
{
  "term_id": "BT-024",
  "term": "Revenue",
  "source": "xbrl-us-gaap",
  "source_tier": 1,
  "source_term_id": "ST-XBRL-024",
  "read_only": true,
  "approved_by": "auto (inherited standard)"
}
```

### What This Means for the Separation Plan

The domain pack's `glossary-seed.json` hint (Section 0) is now reframed:

- It's NOT "here are some terms to start with"
- It IS "here's which shared glossaries to inherit"

```yaml
# domain/manifest.yaml
hints:
  glossary:
    inherit:
      - standard:xbrl-us-gaap
      - standard:sec-edgar
      - domain:finance
```

Without this hint, the pipeline still works — @data-steward just can't auto-link to shared terms and has to create everything as Tier 3.

---

## 1. The Two Repos

| Repo | Purpose | Content |
|------|---------|---------|
| **`edgair`** (framework) | Domain-agnostic agent-governed data lakehouse | Infrastructure, agent definitions, governance scaffolding, zone pipeline pattern |
| **`edgair-sec-edgar`** (domain pack) | SEC EDGAR implementation | Fetchers, schemas, tag mappings, business glossary terms, ratios, anomaly rules |

The framework repo is usable on its own but ships with nothing to ingest. Domain packs plug into it via a `domain/` config directory.

---

## 2. What Lives Where

### Framework Repo (`edgair`)

```
edgair/
├── src/
│   ├── infra/                          # 100% survives as-is
│   │   ├── iceberg_setup.py            # DuckDB + Iceberg utilities
│   │   ├── dq_runner.py                # Rule executor + scorer
│   │   ├── dq_scorecard.py             # Scorecard generator
│   │   ├── lineage.py                  # OpenLineage events
│   │   └── chaos_monkey/               # Adversarial DQ testing
│   ├── raw/
│   │   └── base_ingestor.py            # NEW: abstract base class for ingestion
│   ├── base/
│   │   ├── entity_resolution/          # Survives with entity_id abstraction
│   │   ├── bitemporal/                 # 100% survives as-is
│   │   ├── conformed_facts/            # Survives (reads mappings from domain config)
│   │   └── concept_normalization/      # Renamed from xbrl_tag_normalization
│   ├── consumable/
│   │   ├── derived_metrics/            # Renamed from financial_ratios
│   │   ├── peer_comparison/            # Survives (reads grouping taxonomy from domain config)
│   │   ├── entity_rollup/              # Renamed from company_financials
│   │   └── period_over_period/         # 100% survives as-is
│   ├── ai_ready/
│   │   ├── chat/                       # Survives (system prompt loaded from domain config)
│   │   └── tools/                      # Generic query tools + formatters
│   └── config.py                       # Global config (approval gates, paths, chaos monkey)
├── governance/
│   ├── business-glossary.json          # Empty template with schema doc
│   ├── cde-catalog.json                # Empty template
│   ├── models/                         # Empty (populated per domain)
│   ├── dq-rules/                       # Empty (populated per domain)
│   ├── dq-results/                     # Empty
│   ├── dq-scorecards/                  # Empty
│   ├── eda/                            # Empty
│   ├── lineage/                        # Empty
│   └── conformation/                   # Empty
├── domain/                             # NEW: domain config directory
│   ├── manifest.yaml                   # Domain identity + metadata
│   ├── sources/                        # Data source definitions
│   ├── glossary-seed.json              # Starter business terms
│   ├── concept-mappings/               # Taxonomy → business term mappings
│   ├── metrics/                        # Derived metric definitions
│   ├── anomaly-rules/                  # Domain-specific anomaly definitions
│   ├── grouping-taxonomy/              # Peer grouping scheme (replaces SIC codes)
│   └── chat-context/                   # AI-Ready system prompt context
├── glossaries/                          # NEW: shared glossary registry
│   ├── registry.yaml                   # Index of available standard + domain glossaries
│   ├── standards/                      # Tier 1: published industry/regulatory standards
│   └── domains/                        # Tier 2: community-curated domain glossaries
├── .claude/
│   └── agents/                         # All agents survive (95% unchanged)
├── CLAUDE.md                           # Parameterized workflow guide
├── tests/
│   ├── infra/                          # 100% survives
│   ├── framework/                      # NEW: tests for framework abstractions
│   └── fixtures/                       # Empty (domain pack provides)
└── docs/
    ├── specs/                          # Empty (domain-specific)
    └── domain-pack-guide.md            # NEW: how to build a domain pack
```

### Domain Pack Repo (`edgair-sec-edgar`)

```
edgair-sec-edgar/
├── domain/
│   ├── manifest.yaml                   # name: sec-edgar, version: 1.0
│   ├── sources/
│   │   ├── xbrl_company_facts.yaml     # API endpoint, auth, rate limits, schema
│   │   └── fetchers/
│   │       ├── api_fetcher.py          # fetch_company_facts()
│   │       └── bulk_fetcher.py         # fetch_bulk_company_facts()
│   ├── glossary-seed.json              # 54 SEC/XBRL business terms
│   ├── concept-mappings/
│   │   └── xbrl_us_gaap.json          # 2000+ concept → BT mappings (from tag_norm config.py)
│   ├── metrics/
│   │   └── financial_ratios.yaml       # 7 ratio definitions (numerator/denominator BT pairs)
│   ├── anomaly-rules/
│   │   └── sec_anomalies.yaml          # Negative equity, fiscal year misalignment, etc.
│   ├── grouping-taxonomy/
│   │   └── sic_sectors.yaml            # SIC code → sector mapping
│   ├── chat-context/
│   │   └── system_prompt.md            # SEC EDGAR domain context for AI chat
│   └── flatten/
│       └── xbrl_flattener.py           # XBRL JSON → flat records
├── tests/
│   └── fixtures/                       # Apple, Microsoft, etc. sample data
├── docs/
│   └── specs/                          # All existing SEC-specific specs
└── README.md
```

---

## 3. The Key Abstractions

### 3.1 Domain Manifest (`domain/manifest.yaml`)

The entry point for data acquisition only. Tells the framework *how to get the data*, not *what it means*. Domain understanding is discovered through EDA.

```yaml
name: sec-edgar
version: "1.0"
description: "SEC EDGAR XBRL financial data"

sources:
  - name: xbrl_company_facts
    fetcher: domain/sources/fetchers/api_fetcher.py
    flattener: domain/flatten/xbrl_flattener.py
    schema: domain/sources/xbrl_company_facts.yaml
    rate_limit: 0.1

# Optional hints — accelerators, not requirements
# If missing, the pipeline discovers these from EDA
hints:
  entity_id_field: cik
  time_field: end_date
  concept_mappings: domain/concept-mappings/
  glossary_seed: domain/glossary-seed.json
  metrics: domain/metrics/
  grouping_taxonomy: domain/grouping-taxonomy/
  anomaly_rules: domain/anomaly-rules/
  chat_context: domain/chat-context/system_prompt.md
```

See **Section 0** for why domain knowledge is optional — the data analyst discovers the domain through EDA, and everything downstream reads the EDA report.

### 3.2 Source Definition (`domain/sources/xbrl_company_facts.yaml`)

Replaces hardcoded fetcher config.

```yaml
name: xbrl_company_facts
namespace: raw
table: xbrl_company_facts
fetch_methods:
  api:
    url_template: "https://data.sec.gov/api/xbrl/companyfacts/CIK{entity_id_padded}.json"
    headers:
      User-Agent: "{user_agent}"
    rate_limit_seconds: 0.1
  bulk:
    url: "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip"

entities:
  320193: "Apple Inc."
  19617: "JPMorgan Chase & Co."
  # ... rest of roster

schema:
  fields:
    - name: cik
      type: integer
      description: "Central Index Key"
    - name: entity_name
      type: string
    # ... rest of schema

dedup_grain:
  - cik
  - accession_number
  - concept
  - unit
  - end_date
```

### 3.3 Base Ingestor (Abstract Base)

Replaces the current hardcoded `ingest.py`:

```python
# src/raw/base_ingestor.py
class BaseIngestor(ABC):
    """Framework base class for raw zone ingestion."""

    def __init__(self, source_config: dict, domain_manifest: dict):
        self.source = source_config
        self.manifest = domain_manifest

    @abstractmethod
    def fetch(self, entities: dict, method: str) -> dict[str, Any]:
        """Fetch raw data. Returns {entity_id: raw_data}."""

    @abstractmethod
    def flatten(self, raw_data: Any) -> list[dict]:
        """Flatten raw data into tabular records."""

    def ingest(self, entities=None, method="api"):
        """Orchestrate fetch → flatten → dedup → write to Iceberg."""
        # Generic logic currently in ingest.py
        # Uses self.source for schema, dedup grain, table name
        ...
```

Domain packs implement `fetch()` and `flatten()`. The framework handles Iceberg writes, dedup, lineage, and DQ gating.

### 3.4 Concept Normalization (Generic)

Rename `xbrl_tag_normalization` → `concept_normalization`. The tiered matching algorithm (exact → prefix → pattern → heuristic) is completely generic. Only the *mappings* are domain-specific.

```python
# src/base/concept_normalization/normalize.py
class ConceptNormalizer:
    def __init__(self, mappings_dir: Path):
        """Load concept mappings from domain config."""
        self.exact, self.prefix, self.pattern, self.heuristic = self._load(mappings_dir)

    def classify(self, concept: str) -> dict:
        """Same tiered algorithm, zero domain assumptions."""
        ...
```

### 3.5 Metric Definitions (Config-Driven)

Replace hardcoded `financial_ratios/config.py` with YAML:

```yaml
# domain/metrics/financial_ratios.yaml
metrics:
  - id: gross_margin
    label: "Gross Margin"
    type: ratio
    numerator: BT-028   # Gross Profit
    denominator: BT-024  # Revenue
    format: percentage
    higher_is: better

  - id: net_margin
    label: "Net Margin"
    type: ratio
    numerator: BT-029   # Net Income
    denominator: BT-024  # Revenue
    format: percentage
    higher_is: better
```

The `derived_metrics/` module reads this YAML and computes. No code changes needed per domain.

---

## 4. Migration Steps (Ordered)

### Phase 1: Create the abstraction layer (framework stays in this repo)

Don't fork yet. Build the abstractions in place, then split.

| Step | What | Files Touched | Risk |
|------|------|---------------|------|
| 1.1 | Create `domain/manifest.yaml` schema and loader | NEW: `src/domain_loader.py`, `domain/manifest.yaml` | Low |
| 1.2 | Create `domain/sources/` schema, move SEC config there | MOVE: `src/raw/xbrl_company_facts/config.py` → `domain/sources/xbrl_company_facts.yaml` | Low |
| 1.3 | Create `BaseIngestor` ABC, make XBRL ingestor extend it | NEW: `src/raw/base_ingestor.py`, REFACTOR: `src/raw/xbrl_company_facts/ingest.py` | Medium |
| 1.4 | Extract tag normalization mappings to `domain/concept-mappings/` | MOVE: 2000 lines from `src/base/xbrl_tag_normalization/config.py` → `domain/concept-mappings/xbrl_us_gaap.json` | Medium |
| 1.5 | Rename `xbrl_tag_normalization` → `concept_normalization`, load mappings from domain dir | RENAME + REFACTOR | Medium |
| 1.6 | Extract ratio definitions to `domain/metrics/` | MOVE: `src/consumable/financial_ratios/config.py` → `domain/metrics/financial_ratios.yaml` | Low |
| 1.7 | Extract SIC mappings to `domain/grouping-taxonomy/` | MOVE: `src/consumable/shared.py` SIC dict → `domain/grouping-taxonomy/sic_sectors.yaml` | Low |
| 1.8 | Extract anomaly rules to `domain/anomaly-rules/` | MOVE: `src/ai_ready/tools/anomaly_checker.py` hardcoded rules → `domain/anomaly-rules/sec_anomalies.yaml` | Low |
| 1.9 | Extract system prompt to `domain/chat-context/` | MOVE: `src/ai_ready/chat/system_prompt.py` context → `domain/chat-context/system_prompt.md` | Low |
| 1.10 | Extract glossary seed from current glossary | COPY: `governance/business-glossary.json` → `domain/glossary-seed.json` | Low |
| 1.11 | Parameterize `iceberg_setup.py` catalog name | EDIT: `src/infra/iceberg_setup.py` line 38 ("sec_edgair" → from manifest) | Low |
| 1.12 | Parameterize entity_id references throughout base zone | EDIT: entity_resolution, financial_facts_model (CIK → manifest.entity_id.field) | Medium |

### Phase 2: Generalize the agents and CLAUDE.md

| Step | What | Risk |
|------|------|------|
| 2.1 | Replace EDGAR-specific examples in agent .md files with `{{domain}}` placeholders | Low |
| 2.2 | Update CLAUDE.md project overview to reference `domain/manifest.yaml` instead of hardcoded SEC references | Low |
| 2.3 | Add domain-aware instructions: "read domain/manifest.yaml to understand the current dataset" | Low |
| 2.4 | Remove `consumable/amendment_analysis/` from framework (SEC-only concept) — move to domain pack as custom module | Low |

### Phase 3: Test framework without domain pack

| Step | What | Risk |
|------|------|------|
| 3.1 | Create a minimal test domain pack (e.g., CSV weather data — 5 fields, no API) | Low |
| 3.2 | Run full pipeline: ingest → EDA → DQ rules → base modeling → consumable metrics → AI chat | Medium |
| 3.3 | Verify all agents work without EDGAR-specific assumptions | Medium |
| 3.4 | Write framework tests (test domain loader, base ingestor contract, concept normalizer without mappings) | Low |

### Phase 4: Split into two repos

| Step | What | Risk |
|------|------|------|
| 4.1 | Create `edgair` repo, copy framework code | Low |
| 4.2 | Create `edgair-sec-edgar` repo, copy domain pack + SEC-specific modules | Low |
| 4.3 | Wire up domain pack installation (`pip install -e ../edgair-sec-edgar` or copy `domain/` dir) | Low |
| 4.4 | Verify SEC EDGAR pipeline runs against framework repo + domain pack | Medium |
| 4.5 | Archive original `sec_edgair` repo with pointer to both new repos | Low |

---

## 5. Domain Pack Interface Contract

A domain pack MUST provide (minimum viable data acquisition):

| Artifact | Format | Purpose |
|----------|--------|---------|
| `manifest.yaml` | YAML | Identity + source pointers (NOT domain semantics) |
| `sources/*.yaml` | YAML | At least one source definition with landing schema + dedup grain |
| `sources/fetchers/*.py` | Python | Fetcher implementing `fetch(entities, method) → dict` |
| `flatten/*.py` | Python | Flattener implementing `flatten(raw_data) → list[dict]` |

That's it. Everything else is discovered from the data.

A domain pack MAY provide (accelerators — skip discovery steps):

| Artifact | Format | Purpose | What it skips |
|----------|--------|---------|---------------|
| `hints.entity_id_field` | YAML key | Tells EDA what to group by | EDA guessing the entity grain |
| `hints.time_field` | YAML key | Tells EDA where temporal patterns are | EDA guessing the time dimension |
| `glossary-seed.json` | JSON | Pre-approved business terms | @data-steward term discovery |
| `concept-mappings/*.json` | JSON | Taxonomy → business term mappings | Human-assisted concept grouping |
| `metrics/*.yaml` | YAML | Derived metric definitions | @data-analyst suggesting what's computable |
| `anomaly-rules/*.yaml` | YAML | Domain-specific anomaly patterns | @data-analyst discovering anomalies from scratch |
| `grouping-taxonomy/*.yaml` | YAML | Peer grouping scheme | Human choosing how to segment entities |
| `chat-context/*.md` | Markdown | AI-Ready system prompt context | AI chat having zero domain context |
| `custom-modules/` | Python | Domain-specific consumable modules | Framework-only consumable patterns |
| `tests/fixtures/` | JSON/CSV | Test data | Generating test data from EDA |

**The more hints you provide, the faster the pipeline runs. The fewer you provide, the more the pipeline discovers on its own.**

---

## 6. What Doesn't Change

These survive the separation with zero modifications:

- `src/infra/` — all of it (iceberg_setup, dq_runner, dq_scorecard, lineage, chaos_monkey)
- `src/base/bitemporal/` — all of it
- `src/consumable/period_over_period/` — all of it
- `src/ai_ready/tools/db.py` — connection pooling
- `src/ai_ready/tools/formatters.py` — number formatting
- `src/config.py` — global toggles (REQUIRE_HUMAN_APPROVAL, CHAOS_MONKEY_ENABLED, paths)
- `governance/` directory structure — all of it (just emptied of SEC content)
- DQ rule JSON schema — format is already generic
- Lineage event schema — already OpenLineage compliant
- Session logging format
- Agent workflow pipeline (Raw → Base → Consumable → AI-Ready)

---

## 7. Example: What a Healthcare Claims Domain Pack Looks Like

To prove the framework is truly generic, here's a minimal domain pack — just enough to acquire data:

```yaml
# domain/manifest.yaml — MINIMUM VIABLE
name: healthcare-claims
version: "1.0"
description: "CMS Medicare claims data"

sources:
  - name: cms_claims
    fetcher: domain/sources/fetchers/cms_fetcher.py
    flattener: domain/flatten/claims_flattener.py
    schema: domain/sources/cms_claims.yaml
```

That's the entire manifest. No glossary, no concept mappings, no metrics.

What happens:
1. Data lands in raw zone
2. @data-analyst runs EDA **blind** and discovers:
   - "provider_npi" has 4,200 distinct values, looks like an entity identifier
   - "service_date" spans 2020-2024, quarterly patterns visible
   - "drg_code" has 742 distinct values, looks like a classification taxonomy
   - "total_charges" is always positive, range $47 to $3.2M, median $12,400
   - "readmission_flag" is boolean, 14.2% true
3. @data-steward reads EDA, proposes terms: "Provider", "DRG Code", "Readmission", "Total Charges"
4. @semantic-modeler builds: Provider → Claim → Diagnosis (from the data structure, not from healthcare knowledge)
5. @dq-rule-writer sets thresholds from observed distributions

An experienced healthcare data team could also provide the accelerated version:

```yaml
# domain/manifest.yaml — WITH HINTS
name: healthcare-claims
version: "1.0"
description: "CMS Medicare claims data"

sources:
  - name: cms_claims
    fetcher: domain/sources/fetchers/cms_fetcher.py
    flattener: domain/flatten/claims_flattener.py
    schema: domain/sources/cms_claims.yaml

hints:
  entity_id_field: provider_npi
  time_field: service_date
  glossary_seed: domain/glossary-seed.json       # NPI, DRG, CPT, HCPCS terms
  concept_mappings: domain/concept-mappings/       # CPT → clinical category
  metrics: domain/metrics/                         # Readmission rate, avg LOS
  grouping_taxonomy: domain/grouping-taxonomy/drg_categories.yaml
```

Same pipeline, same agents, same governance artifacts. The hints just let it run faster by skipping discovery steps the team already knows the answers to.

---

## 8. Naming

| Option | Framework | Domain Pack |
|--------|-----------|-------------|
| A | `edgair` | `edgair-sec-edgar` |
| B | `agentlake` | `agentlake-sec-edgar` |
| C | `govlake` | `govlake-sec-edgar` |
| D | `lakegov` | `lakegov-sec-edgar` |

Recommendation: **Option A (`edgair`)**. The name already works without the "SEC" prefix — "EDGAIR" reads as "edge + AI + R(ules)" which is domain-agnostic. SEC EDGAR was always a happy coincidence, not the meaning.

---

## 9. Estimated Effort

| Phase | Effort | Can be parallelized? |
|-------|--------|---------------------|
| Phase 1: Abstractions | 3-5 sessions | Steps 1.4-1.10 are independent |
| Phase 2: Agent generalization | 1-2 sessions | All steps independent |
| Phase 3: Test with alternate domain | 2-3 sessions | Sequential |
| Phase 4: Repo split | 1 session | Sequential |
| **Total** | **7-11 sessions** | |

---

## 10. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Over-abstracting: adding plugin complexity that slows development | High | Phase 3 forces validation with a real second domain before splitting |
| Breaking SEC EDGAR pipeline during refactor | Medium | All refactoring happens in-place first (Phase 1); SEC pipeline must pass all DQ scorecards before Phase 4 |
| CLAUDE.md becomes too generic to be useful | Medium | Domain packs can include their own `CLAUDE.md` additions that merge with framework instructions |
| Agent prompts lose specificity when examples are removed | Low | Replace EDGAR examples with domain-neutral examples, not `{{placeholders}}` — agents work better with concrete examples |
| Custom modules (amendment_analysis) don't fit the plugin model cleanly | Low | Domain packs get a `custom-modules/` escape hatch for domain-specific consumable logic |
