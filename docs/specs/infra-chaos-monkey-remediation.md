# Infrastructure: Chaos Monkey DQ Remediation

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
| Primary Agent | @dq-rule-writer |
| Blocked By | — |
| Depends On | `infra-chaos-monkey` (🟠 IMPLEMENTATION), `raw-ingest-xbrl-company-facts` (🟢 COMPLETE) |

---

## Claude Code Prompt

```
Implement the following plan:

# Plan: `infra-chaos-monkey-remediation` — Close DQ Gaps Found by Chaos Monkey

The chaos monkey ran against raw.xbrl_company_facts at 7% injection rate.
Result: 20% detection rate. 8 of 10 DQ dimensions had ZERO coverage.
This spec adds 15 new DQ rules (RAW-CF-014 through RAW-CF-028) targeting
the 8 undetected dimensions, then re-runs the chaos monkey to validate.

Agent workflow:
1. @dq-rule-writer — Write 15 new rules from chaos monkey AAR evidence
2. @dq-engineer — Execute all rules, produce scorecard
3. Re-run chaos monkey fullrun to validate detection rate
4. @staff-engineer — Final quality review
```

---

## 1. Feature Description

### Problem Statement

Chaos monkey run `chaos-2026-03-15-19-57-44` exposed critical DQ gaps:

| Dimension | Injected | Caught | Miss Rate | Verdict |
|-----------|----------|--------|-----------|---------|
| Completeness | 3,808 | 3,808 | 0.0% | PASS |
| Validity | 3,859 | 3,859 | 0.0% | PASS |
| Uniqueness | 3,923 | 0 | 100.0% | **P0 FAIL** |
| Consistency | 3,768 | 0 | 100.0% | **P0 FAIL** |
| Accuracy | 3,757 | 0 | 100.0% | **P0 FAIL** |
| Reasonableness | 3,761 | 0 | 100.0% | **P0 FAIL** |
| Freshness | 3,983 | 0 | 100.0% | **P0 FAIL** |
| Volume | 3,822 | 0 | 100.0% | **P0 FAIL** |
| Referential Integrity | 3,750 | 0 | 100.0% | **P0 FAIL** |
| Coverage | 3,886 | 0 | 100.0% | **P0 FAIL** |

80% of injected corruptions went undetected. The raw zone has 13 DQ rules but they only cover Completeness, Validity, Volume (weak), and Freshness (weak). Eight full dimensions have zero rule coverage.

### User Story

As a data governance team, we need DQ rules covering all 10 quality dimensions on the raw zone so that the chaos monkey adversarial test achieves >= 90% detection rate across all dimensions.

### Success Criteria

- [ ] 15 new DQ rules added (RAW-CF-014 through RAW-CF-028)
- [ ] All 10 DQ dimensions covered with at least 1 rule each
- [ ] All rules execute successfully against real `raw.xbrl_company_facts`
- [ ] Chaos monkey fullrun detection rate >= 90%
- [ ] All 10 dimensions show PASS in the chaos monkey reconciliation
- [ ] No P0 failures on clean data (rules must not false-positive against real data)

---

## 2. New DQ Rules

### 2.1 Uniqueness (0 rules → 2 rules)

**RAW-CF-014** — No exact duplicate rows

```json
{
  "rule_id": "RAW-CF-014",
  "category": "Uniqueness",
  "priority": "P0",
  "description": "No exact duplicate rows on grain (cik, concept, unit, end_date, accession_number)",
  "sql": "SELECT COUNT(*) FROM (SELECT cik, concept, unit, end_date, accession_number, COUNT(*) as cnt FROM raw.xbrl_company_facts GROUP BY cik, concept, unit, end_date, accession_number HAVING COUNT(*) > 1) dupes",
  "threshold": "result = 0",
  "rationale": "Chaos monkey injected 3,923 full row duplicates — zero caught. The raw grain is (cik, concept, unit, end_date, accession_number). Duplicates corrupt downstream aggregations.",
  "status": "proposed"
}
```

**RAW-CF-015** — No duplicate (cik, concept, end_date, fiscal_period, form) combinations

```json
{
  "rule_id": "RAW-CF-015",
  "category": "Uniqueness",
  "priority": "P1",
  "description": "No duplicate facts for same company/concept/period/form",
  "sql": "SELECT COUNT(*) FROM (SELECT cik, concept, end_date, fiscal_period, form, COUNT(*) as cnt FROM raw.xbrl_company_facts WHERE fiscal_period IS NOT NULL GROUP BY cik, concept, end_date, fiscal_period, form HAVING COUNT(*) > 1) dupes",
  "threshold": "result = 0",
  "rationale": "A company should not report the same concept twice for the same period in the same filing type. Duplicates indicate double-ingestion or parsing errors.",
  "status": "proposed"
}
```

### 2.2 Consistency (0 rules → 2 rules)

**RAW-CF-016** — start_date must be before end_date

```json
{
  "rule_id": "RAW-CF-016",
  "category": "Consistency",
  "priority": "P0",
  "description": "start_date is before or equal to end_date when both are present",
  "sql": "SELECT COUNT(*) FROM raw.xbrl_company_facts WHERE start_date IS NOT NULL AND end_date IS NOT NULL AND start_date > end_date",
  "threshold": "result = 0",
  "rationale": "Chaos monkey injected 1,853 date inversions (start_date=2099, end_date=2000) — zero caught. A reporting period cannot end before it starts.",
  "status": "proposed"
}
```

**RAW-CF-017** — fiscal_year is consistent with end_date year

```json
{
  "rule_id": "RAW-CF-017",
  "category": "Consistency",
  "priority": "P1",
  "description": "fiscal_year is within 1 year of end_date year when both are present",
  "sql": "SELECT COUNT(*) FROM raw.xbrl_company_facts WHERE fiscal_year IS NOT NULL AND end_date IS NOT NULL AND ABS(fiscal_year - EXTRACT(YEAR FROM end_date)) > 1",
  "threshold": "result = 0",
  "rationale": "Chaos monkey injected 1,915 fiscal_year/end_date mismatches (fy=1999, end_date=2024) — zero caught. Fiscal years can cross calendar boundaries but should never be >1 year apart.",
  "status": "proposed"
}
```

### 2.3 Accuracy (0 rules → 2 rules)

**RAW-CF-018** — No suspiciously small values for large-scale concepts

```json
{
  "rule_id": "RAW-CF-018",
  "category": "Accuracy",
  "priority": "P1",
  "description": "Values for balance-sheet concepts (Assets, Liabilities, etc.) are > $1000 for known large-cap companies",
  "sql": "SELECT COUNT(*) FROM raw.xbrl_company_facts WHERE concept IN ('Assets', 'Liabilities', 'StockholdersEquity', 'Revenues', 'CostOfRevenue') AND unit = 'USD' AND fiscal_period = 'FY' AND ABS(val) < 1000 AND ABS(val) > 0",
  "threshold": "result = 0",
  "rationale": "Chaos monkey injected 1,869 implausible values ($1 for Apple's revenue) — zero caught. All 20 companies are large-cap; core financial line items should never be under $1000 on annual filings.",
  "status": "proposed"
}
```

**RAW-CF-019** — No negative values for absolute-only concepts

```json
{
  "rule_id": "RAW-CF-019",
  "category": "Accuracy",
  "priority": "P1",
  "description": "Assets and Revenue are never negative",
  "sql": "SELECT COUNT(*) FROM raw.xbrl_company_facts WHERE concept IN ('Assets', 'Revenues', 'CashAndCashEquivalentsAtCarryingValue') AND val < 0",
  "threshold": "result = 0",
  "rationale": "Chaos monkey injected 1,888 negative absolute metrics — zero caught. Total assets, revenue, and cash cannot be negative by accounting definition.",
  "status": "proposed"
}
```

### 2.4 Reasonableness (0 rules → 2 rules)

**RAW-CF-020** — val is within reasonable absolute bounds

```json
{
  "rule_id": "RAW-CF-020",
  "category": "Reasonableness",
  "priority": "P0",
  "description": "No val values exceeding $100 trillion (1e14) in absolute terms",
  "sql": "SELECT COUNT(*) FROM raw.xbrl_company_facts WHERE ABS(val) > 1e14",
  "threshold": "result = 0",
  "rationale": "Chaos monkey injected 1,290 extreme outliers (val=999,999,999,999,999) — zero caught. The entire US GDP is ~$28 trillion. No single company fact should exceed $100 trillion.",
  "status": "proposed"
}
```

**RAW-CF-021** — fiscal_year is within plausible range

```json
{
  "rule_id": "RAW-CF-021",
  "category": "Reasonableness",
  "priority": "P0",
  "description": "fiscal_year is between 1990 and next year when present",
  "sql": "SELECT COUNT(*) FROM raw.xbrl_company_facts WHERE fiscal_year IS NOT NULL AND (fiscal_year < 1990 OR fiscal_year > EXTRACT(YEAR FROM CURRENT_DATE) + 1)",
  "threshold": "result = 0",
  "rationale": "Chaos monkey injected 1,247 impossible fiscal years (1850) — zero caught. XBRL EDGAR data starts in the 2000s; 1990 allows generous buffer. No future fiscal years beyond next year.",
  "status": "proposed"
}
```

### 2.5 Freshness (1 weak rule → 2 more rules)

Existing RAW-CF-008 checks "latest filed_date within 2 years" — too coarse. Chaos monkey injected future timestamps and ancient dates that slipped through.

**RAW-CF-022** — No future ingestion timestamps

```json
{
  "rule_id": "RAW-CF-022",
  "category": "Freshness",
  "priority": "P0",
  "description": "ingested_at is never in the future",
  "sql": "SELECT COUNT(*) FROM raw.xbrl_company_facts WHERE ingested_at > CURRENT_TIMESTAMP + INTERVAL '1 hour'",
  "threshold": "result = 0",
  "rationale": "Chaos monkey injected 2,002 future timestamps (ingested_at=2099) — zero caught. The 1-hour buffer handles timezone/clock skew. Anything beyond that is data corruption.",
  "status": "proposed"
}
```

**RAW-CF-023** — filed_date is not ancient

```json
{
  "rule_id": "RAW-CF-023",
  "category": "Freshness",
  "priority": "P0",
  "description": "filed_date is after 1993 (SEC EDGAR inception)",
  "sql": "SELECT COUNT(*) FROM raw.xbrl_company_facts WHERE filed_date < '1993-01-01'",
  "threshold": "result = 0",
  "rationale": "Chaos monkey injected 1,981 ancient dates (filed_date=1900) — zero caught. SEC EDGAR launched in 1993. No filing can predate the system.",
  "status": "proposed"
}
```

### 2.6 Volume (1 weak rule → 1 more rule)

Existing RAW-CF-007 checks "each CIK has >= 100 facts" — doesn't catch volume spikes.

**RAW-CF-024** — No CIK has disproportionate row count

```json
{
  "rule_id": "RAW-CF-024",
  "category": "Volume",
  "priority": "P1",
  "description": "No single CIK has more than 3x the median CIK row count",
  "sql": "SELECT COUNT(*) FROM (SELECT cik, COUNT(*) as cnt FROM raw.xbrl_company_facts GROUP BY cik) t WHERE cnt > 3 * (SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY cnt) FROM (SELECT COUNT(*) as cnt FROM raw.xbrl_company_facts GROUP BY cik) m)",
  "threshold": "result = 0",
  "rationale": "Chaos monkey injected 3,822 volume spike rows clustered on specific CIKs — zero caught. A CIK with 3x the median count suggests either a burst injection, a double-ingest, or a data source anomaly.",
  "status": "proposed"
}
```

### 2.7 Referential Integrity (0 rules → 2 rules)

**RAW-CF-025** — All CIKs are in the known company list

```json
{
  "rule_id": "RAW-CF-025",
  "category": "Referential Integrity",
  "priority": "P0",
  "description": "Every CIK in raw data is one of the 20 expected companies",
  "sql": "SELECT COUNT(DISTINCT cik) FROM raw.xbrl_company_facts WHERE cik NOT IN (320193, 19617, 789019, 1018724, 1652044, 1326801, 1318605, 1067983, 200406, 104169, 34088, 1403161, 731766, 80424, 21344, 78003, 1065280, 886982, 12927, 50863)",
  "threshold": "result = 0",
  "rationale": "Chaos monkey injected orphan CIKs (9999999, 8888888) — zero caught. The pipeline ingests exactly 20 companies. Any other CIK indicates injection, corruption, or a fetch targeting the wrong endpoint.",
  "status": "proposed"
}
```

**RAW-CF-026** — taxonomy is a known XBRL taxonomy

```json
{
  "rule_id": "RAW-CF-026",
  "category": "Referential Integrity",
  "priority": "P1",
  "description": "taxonomy is one of the known XBRL taxonomies (us-gaap, dei, srt, invest)",
  "sql": "SELECT COUNT(*) FROM raw.xbrl_company_facts WHERE taxonomy NOT IN ('us-gaap', 'dei', 'srt', 'invest')",
  "threshold": "result = 0",
  "rationale": "Chaos monkey injected fake taxonomies ('fake-gaap-2099') via validity dimension — but referential integrity should also catch unknown taxonomies. Only 4 taxonomies exist in our data.",
  "status": "proposed"
}
```

### 2.8 Coverage (0 rules → 2 rules)

**RAW-CF-027** — Every CIK has at least one annual (FY) filing

```json
{
  "rule_id": "RAW-CF-027",
  "category": "Coverage",
  "priority": "P1",
  "description": "Every CIK has at least one FY (annual) fact",
  "sql": "SELECT COUNT(*) FROM (SELECT DISTINCT cik FROM raw.xbrl_company_facts EXCEPT SELECT DISTINCT cik FROM raw.xbrl_company_facts WHERE fiscal_period = 'FY') missing",
  "threshold": "result = 0",
  "rationale": "Chaos monkey injected a fake CIK with only quarterly data — zero caught. Every public company files 10-Ks (annual). A CIK with zero FY rows means either the data is incomplete or the CIK is fake.",
  "status": "proposed"
}
```

**RAW-CF-028** — Majority of financial facts use USD unit

```json
{
  "rule_id": "RAW-CF-028",
  "category": "Coverage",
  "priority": "P1",
  "description": "At least 80% of facts have unit = 'USD' or 'shares' or 'pure'",
  "sql": "SELECT ROUND(100.0 * SUM(CASE WHEN unit IN ('USD', 'shares', 'pure', 'USD/shares') THEN 1 ELSE 0 END) / COUNT(*), 1) FROM raw.xbrl_company_facts",
  "threshold": "result >= 80.0",
  "rationale": "Chaos monkey injected rows with 'FAKE_CURRENCY' — zero caught. Our 20 US companies should overwhelmingly report in USD. If coverage drops below 80%, either the data source changed or garbage was injected.",
  "status": "proposed"
}
```

---

## 3. Dimension Coverage Matrix (After Remediation)

| Dimension | Existing Rules | New Rules | Total |
|-----------|---------------|-----------|-------|
| Completeness | RAW-CF-001, 002, 009, 013 | — | 4 |
| Validity | RAW-CF-003, 004, 005, 006, 010, 011, 012 | — | 7 |
| Uniqueness | — | RAW-CF-014, 015 | 2 |
| Consistency | — | RAW-CF-016, 017 | 2 |
| Accuracy | — | RAW-CF-018, 019 | 2 |
| Reasonableness | — | RAW-CF-020, 021 | 2 |
| Freshness | RAW-CF-008 | RAW-CF-022, 023 | 3 |
| Volume | RAW-CF-007 | RAW-CF-024 | 2 |
| Referential Integrity | — | RAW-CF-025, 026 | 2 |
| Coverage | — | RAW-CF-027, 028 | 2 |
| **Total** | **13** | **15** | **28** |

---

## 4. Testing Strategy

### Phase 1: Validate against clean data (no false positives)

All 28 rules must PASS against real `raw.xbrl_company_facts`:

```bash
python -m src.infra.dq_runner run --spec raw-ingest-xbrl-company-facts
```

Any failure = the rule is too aggressive and needs threshold adjustment. This is critical — rules that false-positive on clean data are worse than no rules.

### Phase 2: Validate against chaos monkey (detection rate)

```bash
SEC_EDGAIR_ENV=dev python -m src.infra.chaos_monkey fullrun --rate 0.07 --seed 42
```

Target: >= 90% detection rate, all 10 dimensions PASS.

---

## 5. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| 15 new rules, not fewer | Every missed dimension needs at least 2 rules for depth. One rule per dimension would be fragile — a single edge case could bypass it. |
| Hardcoded CIK list in RAW-CF-025 | The 20 CIKs are in `src/raw/xbrl_company_facts/config.py`. Hardcoding in the SQL is explicit and auditable. If the company list changes, the rule must be updated (and that's a feature, not a bug — it forces review). |
| RAW-CF-018 targets specific concepts | Accuracy rules need domain knowledge. "Assets should be > $1000" only works for known concepts on annual filings. Broader rules would false-positive on per-share metrics or ratios. |
| Generous bounds on reasonableness | $100 trillion ceiling, 1990 floor on fiscal_year. These catch chaos monkey garbage (999T, 1850) without flagging legitimate edge cases. |
| 3x median for volume spikes | Simple, robust. Doesn't require precomputed baselines. Catches the chaos monkey's burst injections without flagging companies that legitimately have more filings. |
| Coverage rules use 80% threshold | Not 100% — some legitimate edge cases exist (foreign currency units, non-standard concepts). 80% catches bulk injection without being fragile. |

---

## 6. Agent Workflow

1. @dq-rule-writer — Add 15 rules to `governance/dq-rules/raw-xbrl-company-facts.json`
2. @dq-engineer — Execute all 28 rules against real data (Phase 1: no false positives)
3. @dq-engineer — Run chaos monkey fullrun (Phase 2: detection rate)
4. @staff-engineer — Final quality review

---

## 7. Governance Artifacts

- `governance/dq-rules/raw-xbrl-company-facts.json` — Updated with 15 new rules
- `governance/dq-results/` — Execution results from both phases
- `governance/dq-scorecards/raw-ingest-xbrl-company-facts-scorecard.md` — Updated scorecard
- `governance/chaos-reports/` — Post-remediation AAR
