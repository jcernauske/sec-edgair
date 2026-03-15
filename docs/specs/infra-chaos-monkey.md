# Infrastructure: Chaos Monkey (Adversarial DQ Testing)

## Status: 🟡 DRAFT

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
| Zone | Infrastructure (cross-cutting) |
| Primary Agent | @chaos-monkey |
| Blocked By | — |
| Depends On | `raw-ingest-xbrl-company-facts` (🟢 COMPLETE), `infra-setup-duckdb-iceberg` (🟢 COMPLETE) |

---

## Claude Code Prompt

```
Implement the following plan:

# Plan: `infra-chaos-monkey` Spec + Implementation

Build an adversarial data injection system ("Chaos Monkey") that pollutes
the raw zone with realistic garbage data to stress-test DQ rules. Dev-only,
with layered runtime kill switches. Must violate every DQ dimension per run
and produce a manifest for post-pipeline reconciliation.

Agent workflow:
1. @governance-reviewer — Pre-implementation review
2. @chaos-monkey — Build injection engine, manifest writer, reconciler
3. @staff-engineer — Final quality review
```

---

## 1. Feature Description

### Problem Statement

We have 128+ DQ rules across 10 dimensions. We believe they work because they pass against clean data. But we've never proven they catch dirty data. In enterprise environments, a high % might be garbage — nulls, duplicates, type mismatches, orphan keys, impossible values. If our DQ rules can't catch intentionally injected corruption, they can't catch real corruption either.

### Concept

The Chaos Monkey is an adversarial agent that:
1. Reads ONLY the raw zone physical schema (no knowledge of DQ rules, no knowledge of tests)
2. Injects 5-10% corrupted rows into a **shadow copy** of raw data
3. Produces a detailed manifest of every corruption it injected
4. A separate reconciliation step compares the manifest against DQ results
5. Any undetected corruption = **P0 gate failure**

The information asymmetry is the point. The monkey doesn't know what the DQ rules check for, so it can't game them. If it accidentally finds a gap, that's a real gap.

### User Story

As a data governance team, we want adversarial testing of our DQ rules so that we can prove to auditors that our quality gates catch realistic enterprise data corruption — not just pass against clean data.

### Success Criteria

- [ ] Layered runtime kill switch: `CHAOS_MONKEY_ENABLED` config flag AND `SEC_EDGAIR_ENV=dev` environment variable — both required
- [ ] Hard exit with loud error if either condition not met (no silent fallback, no degraded mode)
- [ ] Injects corrupted rows at 5-10% of source row count (configurable, default 7%)
- [ ] Violates ALL 10 DQ dimensions in every run (at least one corruption per dimension)
- [ ] Produces timestamped manifest in `governance/chaos-manifests/`
- [ ] Manifest records: corruption ID, dimension violated, what was changed, original value, corrupted value, row identifier
- [ ] Chaos monkey has NO access to DQ rules, DQ results, or test files
- [ ] Reconciler compares manifest against DQ results and produces coverage report
- [ ] Undetected corruptions = P0 gate failure
- [ ] All injections target a shadow copy (never mutates real raw tables)

---

## 2. Technical Design

### 2.1 Runtime Safety — The Kill Switch

**This is the most important section of this spec.**

The Chaos Monkey must NEVER run against production data. Three layers of protection:

```python
# Layer 1: Config flag (src/config.py)
CHAOS_MONKEY_ENABLED = False  # Default OFF

# Layer 2: Environment variable (runtime)
# SEC_EDGAIR_ENV must equal "dev" — checked at runtime, not import time

# Layer 3: Path validation
# Refuses to write to any path that doesn't contain "/dev/" or "/shadow/"
```

**Startup sequence:**
```python
def safety_check():
    """Three-layer kill switch. ALL must pass or hard exit."""

    # Layer 1: Config flag
    if not config.CHAOS_MONKEY_ENABLED:
        sys.exit("CHAOS MONKEY BLOCKED: CHAOS_MONKEY_ENABLED is False in config.py")

    # Layer 2: Environment variable
    env = os.environ.get("SEC_EDGAIR_ENV", "")
    if env != "dev":
        sys.exit(f"CHAOS MONKEY BLOCKED: SEC_EDGAIR_ENV={env!r}, must be 'dev'")

    # Layer 3: Output path validation
    if "/dev/" not in str(output_path) and "/shadow/" not in str(output_path):
        sys.exit(f"CHAOS MONKEY BLOCKED: output path {output_path} is not a dev/shadow path")

    # All clear — log prominently
    logger.warning("🐒 CHAOS MONKEY ACTIVE — injecting adversarial data into shadow zone")
```

No try/except around this. No fallback. No "continue anyway" flag. `sys.exit()` or nothing.

### 2.2 The 10 DQ Dimensions and Corruption Strategies

The monkey must inject at least one corruption per dimension per run. It picks from these strategies randomly, but guarantees full dimension coverage:

| # | DQ Dimension | Corruption Strategy | Example |
|---|-------------|---------------------|---------|
| 1 | **Completeness** | Null out required fields | `cik=NULL`, `entity_name=NULL`, `val=NULL` |
| 2 | **Validity** | Invalid values in constrained fields | `fiscal_period="Q9"`, `form="99-Z"`, `unit=""` |
| 3 | **Uniqueness** | Duplicate primary keys / full row copies | Exact duplicate rows, same `(cik, concept, end_date, accession_number)` |
| 4 | **Consistency** | Contradictory field combinations | `start_date > end_date`, `fiscal_year=2024` with `end_date=2019-12-31` |
| 5 | **Accuracy** | Plausible but wrong values | Revenue of $1 for Apple, negative `val` for absolute metrics |
| 6 | **Reasonableness** | Extreme outliers | `val=999999999999999`, `fiscal_year=1850`, `cik=0` |
| 7 | **Freshness** | Stale or future timestamps | `ingested_at` in year 2099, `filed_date` in 1900 |
| 8 | **Volume** | Row count anomalies | Inject a burst of 50+ rows for one CIK (volume spike) |
| 9 | **Referential Integrity** | Orphan keys | `cik=9999999` (nonexistent), `accession_number="FAKE-000-00"` |
| 10 | **Coverage** | Missing expected combinations | Inject rows that create gaps: a CIK with zero annual filings, a concept with no USD unit |

### 2.3 Shadow Zone Architecture

The monkey NEVER touches real raw tables. Instead:

```
data/
  raw/                          ← REAL data (untouched)
    iceberg_warehouse/
  shadow/                       ← CHAOS MONKEY playground
    iceberg_warehouse/
      raw.db/
        xbrl_company_facts/     ← Copy of real + injected garbage
```

**Flow:**
1. Copy real raw data into shadow zone
2. Inject corrupted rows into the shadow copy
3. Downstream pipeline (base zone) runs against shadow data
4. DQ rules execute against shadow-derived tables
5. Reconciler compares DQ catches against chaos manifest

### 2.4 Manifest Format

Every injection is recorded in `governance/chaos-manifests/chaos-manifest-YYYY-MM-DD-HH-MM-SS.json`:

```json
{
  "run_id": "chaos-2026-03-15-14-30-00",
  "timestamp": "2026-03-15T14:30:00Z",
  "environment": "dev",
  "source_table": "raw.xbrl_company_facts",
  "source_row_count": 547398,
  "injected_row_count": 38318,
  "injection_rate": 0.07,
  "dimension_coverage": {
    "completeness": true,
    "validity": true,
    "uniqueness": true,
    "consistency": true,
    "accuracy": true,
    "reasonableness": true,
    "freshness": true,
    "volume": true,
    "referential_integrity": true,
    "coverage": true
  },
  "injections": [
    {
      "corruption_id": "CHAOS-001",
      "dimension": "completeness",
      "strategy": "null_required_field",
      "description": "Set cik to NULL on injected row",
      "field": "cik",
      "original_value": "320193",
      "corrupted_value": null,
      "row_identifier": "shadow-row-00001",
      "expected_detection": "Any DQ rule checking NOT NULL on cik"
    },
    {
      "corruption_id": "CHAOS-002",
      "dimension": "uniqueness",
      "strategy": "full_row_duplicate",
      "description": "Exact copy of existing row (CIK 320193, concept Assets, 2024-01-01)",
      "field": "*",
      "original_value": "row hash abc123",
      "corrupted_value": "exact duplicate",
      "row_identifier": "shadow-row-00002",
      "expected_detection": "Any uniqueness/duplicate DQ rule"
    }
  ]
}
```

Key: `expected_detection` is written by the monkey in natural language — it describes what KIND of rule should catch this, without referencing specific rule IDs (which it doesn't know).

### 2.5 Reconciliation Engine

After the full pipeline runs against shadow data and DQ rules execute:

```python
# python -m src.infra.chaos_reconciler reconcile --manifest <path> --dq-results <path>
```

The reconciler:
1. Loads the chaos manifest (list of all corruptions with IDs)
2. Loads the DQ results from the pipeline run
3. For each corruption, determines if ANY DQ rule flagged it
4. Produces a coverage report

**Reconciliation report** (`governance/chaos-manifests/reconciliation-YYYY-MM-DD-HH-MM-SS.md`):

```markdown
# Chaos Monkey Reconciliation Report

**Run:** chaos-2026-03-15-14-30-00
**Injected:** 38,318 corrupted rows across 10 dimensions
**Detected:** 37,950 (99.04%)
**Undetected:** 368 (0.96%)

## Dimension Coverage

| Dimension | Injected | Caught | Miss Rate | Status |
|-----------|----------|--------|-----------|--------|
| Completeness | 4,200 | 4,200 | 0.00% | ✅ PASS |
| Validity | 3,800 | 3,800 | 0.00% | ✅ PASS |
| Uniqueness | 5,100 | 5,100 | 0.00% | ✅ PASS |
| Accuracy | 3,500 | 3,132 | 10.51% | ❌ P0 FAIL |
| ...

## 👁️ P0 Gate Decision

**❌ FAIL** — 368 corruptions went undetected.

Undetected corruptions by dimension:
- Accuracy: 368 rows with plausible-but-wrong values not caught

## Recommended Actions
- Add DQ rules targeting value reasonableness for [specific fields]
- Consider statistical outlier detection for val field
```

**Gate logic:**
- 100% dimension detection (every dimension had at least 1 catch) = PASS
- 0 undetected corruptions = PASS
- ANY undetected corruption = **P0 FAIL** — the pipeline has a DQ gap
- P0 FAIL means: new DQ rules must be written before the spec can proceed

### 2.6 Module Structure

```
src/infra/
    chaos_monkey/
        __init__.py
        config.py          # Kill switch, injection rate, dimension config
        safety.py           # Three-layer runtime check (sys.exit on fail)
        injector.py         # Core: read schema, generate corruptions per dimension
        manifest.py         # Write/read chaos manifests
        shadow.py           # Shadow zone setup: copy real data, apply injections
        cli.py              # CLI: inject, reconcile, report
    chaos_reconciler.py     # Post-pipeline: diff manifest vs DQ results

governance/
    chaos-manifests/        # Timestamped injection logs + reconciliation reports
```

### 2.7 Information Barrier

**The monkey MUST NOT have access to:**
- `governance/dq-rules/` (rule definitions)
- `governance/dq-results/` (execution results)
- `governance/dq-scorecards/` (scorecards)
- `tests/` (test files)
- Any DQ-related source code (`src/infra/dq_runner.py`, `src/infra/dq_scorecard.py`)

**The monkey ONLY has access to:**
- `src/raw/*/schema.py` (physical schemas — what columns exist, what types they are)
- `data/raw/` (to copy source data into shadow zone)
- `governance/chaos-manifests/` (to write its own output)
- `src/infra/chaos_monkey/` (its own code)

This is enforced by convention and agent definition, not runtime sandboxing. The `@chaos-monkey` agent definition will explicitly exclude DQ-related paths from its allowed file access.

### 2.8 CLI Interface

```bash
# Run injection (requires both safety flags)
SEC_EDGAIR_ENV=dev python -m src.infra.chaos_monkey inject \
    --table raw.xbrl_company_facts \
    --rate 0.07

# View latest manifest
python -m src.infra.chaos_monkey manifest --latest

# Run reconciliation after pipeline completes
python -m src.infra.chaos_monkey reconcile \
    --manifest governance/chaos-manifests/chaos-manifest-2026-03-15-14-30-00.json \
    --dq-results governance/dq-results/

# Generate reconciliation report
python -m src.infra.chaos_monkey report --run-id chaos-2026-03-15-14-30-00
```

---

## 3. Testing Strategy

Tests for the chaos monkey itself (meta-testing — we're testing the tester):

| Test File | What |
|-----------|------|
| test_safety.py | Kill switch: missing config flag → exit, wrong env → exit, bad path → exit, all-clear → proceed |
| test_injector.py | Given a schema, generates corruptions across all 10 dimensions |
| test_manifest.py | Manifest write/read roundtrip, all required fields present |
| test_shadow.py | Shadow zone created correctly, real data untouched after injection |
| test_reconciler.py | Known manifest + known DQ results → correct detection/miss counts |
| test_dimension_coverage.py | Every run produces at least 1 corruption per dimension |

**Critical test: the kill switch tests are the most important tests in this spec.** If these fail, everything else is irrelevant.

---

## 4. DQ Rules

No DQ rules for this spec. The chaos monkey IS the DQ testing tool — it doesn't need DQ rules of its own.

---

## 5. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Shadow zone, not mutation | Real data must never be touched. Shadow copy means full reversibility — delete the shadow dir and it's gone. |
| 5-10% injection rate | Realistic enterprise garbage rate. Lower would be too easy; higher would drown signal. |
| ALL 10 dimensions every run | Partial coverage defeats the purpose. Every run is a full adversarial sweep. |
| Information barrier (no DQ knowledge) | The monkey can't game what it can't see. If it knew the rules, it would only violate what's checked. |
| `sys.exit()` not exceptions | Exceptions can be caught and swallowed. `sys.exit()` is a hard stop. You can't accidentally continue. |
| Manifest with natural-language expectations | The monkey describes what SHOULD catch each corruption without naming specific rules. This helps humans understand gaps without breaking the information barrier. |
| Full row duplicates as a corruption type | Enterprise classic. Copy/paste rows are the #1 uniqueness problem in real data. |
| Reconciler is separate from monkey | Separation of concerns. The monkey injects and records. The reconciler judges. Different trust boundaries. |
| P0 gate on ANY undetected corruption | Aggressive, but that's the point. If we can't catch intentional garbage, we can't catch accidental garbage. |

---

## 6. Agent Workflow

1. @governance-reviewer — Pre-implementation review
2. @chaos-monkey — Build safety checks, injector, manifest writer, shadow zone, CLI
3. @chaos-monkey — Build reconciliation engine and reporting
4. @staff-engineer — Final quality review

---

## 7. Governance Artifacts

- `governance/chaos-manifests/` — Timestamped injection logs
- `governance/chaos-manifests/reconciliation-*.md` — Post-pipeline coverage reports
- `.claude/agents/chaos-monkey.md` — Agent definition (schema-aware, DQ-blind)

---

## 8. Future Extensions

| Extension | Value |
|-----------|-------|
| Multi-table chaos | Extend to base zone tables as more tables are created |
| Chaos profiles | "Financial services" profile (decimal precision attacks), "Healthcare" profile (date sensitivity), etc. |
| Regression chaos | Re-run same manifest to verify a DQ fix actually catches what it missed |
| CI integration | Run chaos monkey as part of CI pipeline in dev branches |
| Chaos budget tracking | Track which dimensions have the most misses over time — focus DQ investment there |
