# Raw Zone: Profile, PII Scan, and Classify Company Facts

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
| Created | 2026-03-14 |
| Author | Jeff + Claude Code |
| Spec Version | 1.0 |
| Last Updated | 2026-03-14 |
| Zone | Raw |
| Primary Agent | @data-profiler, @pii-scanner |
| Blocked By | — |
| Depends On | `raw-ingest-xbrl-company-facts` (🟢 COMPLETE) |

---

## Claude Code Prompt

```
Read the spec at docs/specs/raw-profile-classify-company-facts.md in its entirety.

Complete the remaining Phase 1 (Raw Zone) tasks for raw.xbrl_company_facts:
1. Data profiling — statistical profile of all 19 fields (cardinality, nulls, distributions, anomalies)
2. PII scanning — scan for personally identifiable information
3. Data classification — assign sensitivity tags to every field

This is an observation-only spec. No data is transformed. Agents observe, measure,
classify, and produce governance artifacts.

Agent workflow:
1. @governance-reviewer — Pre-implementation review
2. @data-profiler — Profile all 19 fields against the live 104,810 rows
3. @pii-scanner — Scan for PII across all fields
4. @policy-engineer — Define classification and access policies based on PII scan
5. @lineage-tracker — N/A (no new transformations)
6. @dq-engineer — N/A (no new DQ rules needed — profiling is observational)
7. @cde-tagger — N/A (CDEs already mapped)
8. @doc-generator — N/A (dictionary already complete)
9. @governance-reviewer — Post-implementation verification
10. @staff-engineer — Final quality review

Key outputs:
1. governance/profiles/raw-xbrl-company-facts-profile.md — Statistical profile
2. governance/pii-scans/raw-xbrl-company-facts-pii-scan.md — PII scan report
3. governance/policies/POL-001-classification.json — Data classification policy
4. src/raw/xbrl_company_facts/profile.py — Profiling script (reusable)
5. tests/raw/xbrl_company_facts/test_profile.py — Profiling validation tests

No dependencies beyond raw-ingest-xbrl-company-facts (COMPLETE).
```

---

## 1. Feature Description

### Problem Statement
The raw.xbrl_company_facts table has 104,810 rows across 3 companies. Before moving to Base zone modeling, we need to understand the data: field distributions, cardinality, null rates, anomalies, and whether any PII slipped through. This observation informs every downstream agent — the entity resolver needs to know cardinality of CIK/entity_name, the CDE tagger needs to know taxonomy distributions, and the temporal modeler needs to know fiscal period patterns.

### Success Criteria
- [ ] Statistical profile produced for all 19 fields
- [ ] PII scan completed with findings report
- [ ] Data classification assigned to every field
- [ ] Profiling script is reusable (can re-run after new ingestions)
- [ ] Profile validates against live Iceberg data, not fixture data

---

## 2. Design Decisions

| Decision | Rationale |
|----------|-----------|
| Profile live Iceberg data, not cached JSON | Proves the Iceberg roundtrip preserved data fidelity |
| Reusable profiling script | Re-run after adding more companies or re-ingesting |
| PII scan expects no findings | SEC XBRL Company Facts are structured financial data — no officer names, addresses, or SSNs in this dataset. The scan demonstrates the pattern. |
| All fields classified as Public | SEC EDGAR data is public by law. Classification demonstrates the governance pattern for when we handle non-public data. |

---

## 3-4. Technical Specification

### Files to Create

| File | Purpose |
|------|---------|
| `src/raw/xbrl_company_facts/profile.py` | Reusable profiling script — reads Iceberg table, computes stats per field |
| `tests/raw/xbrl_company_facts/test_profile.py` | Tests that profiling runs and produces expected output structure |
| `governance/profiles/raw-xbrl-company-facts-profile.md` | Statistical profile report |
| `governance/pii-scans/raw-xbrl-company-facts-pii-scan.md` | PII scan report |
| `governance/policies/POL-001-classification.json` | Data classification policy |

---

## 5. Implementation Log

### Agent Activity

| Step | Agent | Action | Status |
|------|-------|--------|--------|
| Profile | @data-profiler | Profiled all 19 fields against 104,810 live rows | ✅ |
| PII Scan | @pii-scanner | Scanned all fields — 0 PII instances found | ✅ |
| Classification | @policy-engineer | All 19 fields classified as Public (Level 1) | ✅ |
| Tests | @data-profiler | 5 profiler tests passing | ✅ |

### Files Created

| File | Purpose |
|------|---------|
| `src/raw/xbrl_company_facts/profile.py` | Reusable profiling script |
| `tests/raw/xbrl_company_facts/test_profile.py` | 5 profiler validation tests |
| `governance/profiles/raw-xbrl-company-facts-profile.md` | Full statistical profile |
| `governance/pii-scans/raw-xbrl-company-facts-pii-scan.md` | PII scan report (no findings) |
| `governance/policies/POL-001-classification.json` | Data classification policy |

### Key Profile Findings

| Field | Notable Finding |
|-------|----------------|
| taxonomy | 4 distinct values: us-gaap (99.6%), dei, invest, srt |
| concept | 1,409 distinct XBRL concepts |
| label | 0.9% null (998 rows) — some concepts have no label |
| fiscal_year | 1.7% null (1,742 rows) — some facts lack fiscal year |
| fiscal_period | 4 values: FY (33%), Q2 (24%), Q3 (23%), Q1 (18%) — no Q4 (reported as FY) |
| start_date | 40.5% null — instant/balance-sheet facts |
| frame | 59.2% null — expected, many facts lack frame |
| val | Range: -2.95T to 80.8T — JPMorgan drives the extremes |
| form | 5 types: 10-Q (63%), 10-K (31%), 8-K (5%), 10-Q/A, 10-K/A |
| accession_number | 210 distinct filings, all exactly 20 chars |
| entity_name | 3 values — note MICROSOFT CORPORATION is all-caps |
| unit | 17 distinct units including USD, shares, USD/shares, pure, segment |

---

## 10. Governance Artifacts

### Profiling Report
`governance/profiles/raw-xbrl-company-facts-profile.md` — 19-field statistical profile against 104,810 live rows.

### PII Scan Report
`governance/pii-scans/raw-xbrl-company-facts-pii-scan.md` — All 19 fields scanned, 0 PII instances found. entity_name checked for personal names — confirmed company legal names only.

### Data Classification
`governance/policies/POL-001-classification.json` — All fields Public (Level 1). No RLS, masking, or access restrictions needed.

---

## 13. Final Review

### Date: 2026-03-14
### Status: 🟢 SHIPPED

### Notes
Phase 1 (Raw Zone) is now complete. All raw zone tasks are done:
- Data ingested (104,810 rows, 3 companies)
- Data profiled (19 fields, statistical distributions)
- PII scanned (no findings — structured financial data)
- Data classified (all Public)
- Full governance artifacts produced

### Profile Insights for Phase 2
- **Entity resolution**: 3 CIKs, 3 entity names — name format varies (Apple Inc. vs MICROSOFT CORPORATION)
- **Tag normalization**: 1,409 distinct XBRL concepts across 4 taxonomies — significant normalization needed
- **Temporal modeling**: fiscal_year/fiscal_period null for 1.7% of facts; start_date absent for 40.5% (instant facts)
- **Fiscal calendar**: No Q4 period — Apple/Microsoft report Q4 as part of FY. JPMorgan uses calendar year.
