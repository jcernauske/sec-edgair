# Infrastructure: Semantic DQ Rules & Negative Testing

## Status: 🟢 COMPLETE

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
| Zone | Infrastructure (cross-cutting) |
| Depends On | `base-conformed-facts` (🟢 COMPLETE), `infra-dq-execution-framework` (🟢 COMPLETE) |

---

## Claude Code Prompt

```
How should we fix both? Let's discuss a solution, draft and execute a spec, then ask him to regrade
```

---

## 1. Problem Statement

The Principal Data Architect held Data Quality & Trust at A- because of two gaps:

1. **No negative testing** — verification scripts prove correct values exist but don't prove incorrect values are absent. A bug that writes duplicate grains, leaks superseded facts, or mixes fiscal years would go undetected.

2. **No semantic correctness DQ rules** — existing 111 rules cover structural integrity (uniqueness, referential integrity, completeness, volume) but not business-logic plausibility. Revenue being negative, EPS being $50 billion, or Net Income exceeding Revenue are all structurally valid but semantically wrong.

Both gaps target the same blind spot: the system validates *structure* but not *meaning*.

## 2. Solution

### Two complementary fixes

| Fix | What | Where | When It Runs |
|-----|------|-------|-------------|
| Negative verification script | Assertions that bad data is ABSENT | `scripts/verify_negative.py` | On-demand (like existing verify scripts) |
| Semantic DQ rules | Business-logic plausibility constraints | `governance/dq-rules/` | Via `dq_runner` on every promote |

### DQ Dimension Alignment

Every rule — existing and new — maps to a primary DQ dimension. The existing `category` field already serves this purpose. We add two new dimensions:

| Dimension | Description | Example |
|-----------|-------------|---------|
| **Accuracy** (new) | Proving incorrect data is absent | No superseded facts in consumable tables |
| **Reasonableness** (new) | Business-logic plausibility bounds | Revenue should be positive for non-financial companies |

Full dimension inventory after this spec:

| Dimension | Existing Rules | New Rules |
|-----------|---------------|-----------|
| Uniqueness | 14 | 0 |
| Completeness | 16 | 0 |
| Validity | 12 | 0 |
| Consistency | 22 | 0 |
| Freshness | 4 | 0 |
| Referential Integrity | 8 | 0 |
| Volume | 8 | 0 |
| **Accuracy** | 0 | ~8 |
| **Reasonableness** | 0 | ~10 |

---

## 3. Negative Verification Script

`scripts/verify_negative.py` — runs against real Iceberg tables, asserts things that should NOT exist.

### Checks

| # | Check | Table | What It Proves |
|---|-------|-------|---------------|
| 1 | No duplicate grains | consumable.company_financials | Collision resolution didn't produce duplicates |
| 2 | No superseded facts | consumable.company_financials | Supersession filter didn't leak |
| 3 | No unmapped facts (null BT) | base.conformed_facts | Null BT filter didn't leak |
| 4 | No null fiscal years | base.conformed_facts | Null FY filter didn't leak |
| 5 | No wrong-unit values | base.conformed_facts | Unit filter didn't leak (e.g., USD/shares in a USD metric) |
| 6 | No fiscal year collisions | consumable.company_financials | Same company + metric + period doesn't appear in two fiscal years |
| 7 | No orphan ratios | consumable.financial_ratios | Every ratio has both numerator and denominator in company_financials |
| 8 | No stale records across rebuilds | consumable.company_financials | Row count matches base.conformed_facts (no leftover rows from prior runs) |
| 9 | No duplicate peer rankings | consumable.peer_comparison | Same company + metric + year + period + source has exactly one rank |
| 10 | No cross-zone grain violations | base.conformed_facts vs consumable | Every consumable company_financials grain exists in conformed_facts |

Output format matches existing verify scripts:
```
[ OK] No duplicate grains in company_financials (28,849 rows, 28,849 unique grains)
[ OK] No superseded facts leaked to conformed_facts
[FAIL] Found 3 wrong-unit values in conformed_facts
...
Results: 9 pass | 1 fail | 10 total
```

---

## 4. Semantic DQ Rules (Reasonableness)

New rules added to existing spec DQ rule files. Each rule has `"category": "Reasonableness"`.

### base-conformed-facts rules

| Rule ID | Description | Priority | Rationale |
|---------|------------|----------|-----------|
| BASE-CF-020 | Revenue (BT-022) should be positive for non-financial companies | P1 | Negative revenue is almost always a data issue. Financial companies may have negative revenue in specific periods (net interest). |
| BASE-CF-021 | Total Assets (BT-024) must be positive | P0 | Definitionally impossible to have negative total assets. Zero is also suspect. |
| BASE-CF-022 | Per-share metrics (BT-044, 045, 046) magnitude < 10,000 | P1 | EPS of $50B means a unit filtering bug. Real EPS ranges from -$100 to $1,000 at most. |
| BASE-CF-023 | Value magnitude for USD metrics should be < 10 trillion | P1 | No company has reported a single metric > $10T. Catches unit/scale errors. |
| BASE-CF-024 | Each company's metrics for a given period should come from <= 3 distinct accession numbers | P1 | Most metrics come from 1-2 filings. >3 suggests collision resolution picked from too many sources. |

### consumable-company-financials rules

| Rule ID | Description | Priority | Rationale |
|---------|------------|----------|-----------|
| CONS-CF-009 | Net Income magnitude should be <= Revenue magnitude for non-financial companies | P2 | Net Income exceeding Revenue indicates a data mapping issue (wrong concept selected). Financial companies excluded (interest income structure differs). |
| CONS-CF-010 | Companies reporting per (BT, period) should be >= 2 for common metrics (Revenue, Net Income, Total Assets) | P2 | If only 1 company reports Revenue, something is wrong with the population. |

### consumable-financial-ratios rules

| Rule ID | Description | Priority | Rationale |
|---------|------------|----------|-----------|
| CONS-FR-011 | Gross Margin between -1.0 and 1.0 | P1 | Gross Margin > 100% or < -100% indicates a numerator/denominator mismatch. |
| CONS-FR-012 | Operating Margin between -5.0 and 1.0 | P1 | Operating Margin > 100% is impossible. < -500% indicates pre-revenue company or data issue. |
| CONS-FR-013 | Net Margin between -10.0 and 1.0 | P1 | Same logic. Wider lower bound for companies with large one-time losses. |
| CONS-FR-014 | CapEx-to-Revenue between 0.0 and 1.0 | P1 | CapEx > Revenue would mean a company spends more on capital than it earns. Abs(CapEx) used, so should always be positive. |
| CONS-FR-015 | R&D Intensity between 0.0 and 1.0 | P1 | R&D > Revenue is possible for pre-revenue biotech but not for our 20 large-cap companies. |

### Accuracy Rules (new dimension)

Added to existing spec DQ rule files. Each rule has `"category": "Accuracy"`.

### base-conformed-facts accuracy rules

| Rule ID | Description | Priority | Rationale |
|---------|------------|----------|-----------|
| BASE-CF-025 | No superseded facts (is_superseded should not exist in source data that made it through) | P0 | Supersession filter is the first step. If a superseded fact survives, the entire conformation is suspect. |
| BASE-CF-026 | No null business_term_id values | P0 | Null BT filter is step 2. Leakage means unmapped concepts pollute the conformed table. |
| BASE-CF-027 | No facts with wrong unit per business term | P0 | Unit filter is step 3. A USD/shares value in a USD metric produces wrong magnitude. |

### consumable-company-financials accuracy rules

| Rule ID | Description | Priority | Rationale |
|---------|------------|----------|-----------|
| CONS-CF-011 | Row count matches base.conformed_facts | P0 | company_financials is a 1:1 presentation layer over conformed_facts. Mismatch means rows were created or lost. |
| CONS-CF-012 | No company has the same metric in two different fiscal years for the same fiscal period | P0 | Would indicate a collision resolution bug where two different source facts both survived. |

---

## 5. Implementation Plan

### Phase 1: Semantic DQ Rules
1. @data-analyst — profile real data for threshold evidence (what are actual value ranges?)
2. @dq-rule-writer — write rules with EDA-derived thresholds
3. @dq-engineer — execute rules, produce scorecard

### Phase 2: Negative Verification Script
1. Create `scripts/verify_negative.py`
2. Run against real Iceberg tables
3. All checks must pass

### Phase 3: Verification
1. Full DQ suite passes (existing 111 + new rules)
2. Both verification scripts pass (positive + negative)
3. Ask @principal-data-architect to re-grade Data Quality & Trust

---

## 6. Risk

| Risk | Mitigation |
|------|-----------|
| Reasonableness thresholds too tight → false positives | EDA profiles real data first; use P1/P2 for business-logic rules |
| Financial sector companies violate rules (different P&L structure) | Rules exclude financial sector where appropriate (SIC-based filter in SQL) |
| New Accuracy rules overlap with existing structural rules | Accuracy rules are explicit "absence of bad data" checks; structural rules check "presence of good data" |
