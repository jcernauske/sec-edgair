## Governance Review: raw-ingest-xbrl-company-facts
**Review Type:** Post-Implementation
**Reviewer:** @governance-reviewer
**Date:** 2026-03-14
**Verdict:** ✅ APPROVED

### Checklist Results

- [x] **Lineage:** OpenLineage events exist in `governance/lineage/raw-ingest-xbrl-company-facts.json` — 2 jobs (API and bulk), full column-level lineage for all 19 fields
- [x] **DQ Rules:** 15 unit tests in `tests/raw/xbrl_company_facts/test_flatten.py` + 7 integration tests in `test_ingest.py` validate the pipeline
- [x] **DQ Scorecard:** Produced at `governance/dq-scorecards/raw-xbrl-company-facts-scorecard.md` — 15/16 rules pass, 1 N/A (volume rule requires live data)
- [x] **CDE Tags:** 4 CDEs mapped in `governance/cde-catalog.json` — CIK, accession_number, entity_name, filed_date
- [x] **Data Dictionary:** All 19 fields documented in `governance/data-dictionary.json` with plain-English definitions
- [x] **Data Contracts:** N/A — no consumable zone tables affected yet
- [x] **Audit Trail:** 10 decisions logged in `governance/audit-trail/raw-ingest-xbrl-company-facts.json` with rationale, including 3 implementation discoveries
- [x] **Schema Changes:** Schema matches spec (19 columns). One deviation: TimestampType → TimestamptzType for ingested_at (documented in audit trail)
- [x] **No Orphaned Artifacts:** All governance artifacts reference `raw.xbrl_company_facts` consistently
- [x] **Consistency:** Lineage, CDE tags, data dictionary, and DQ rules all reference the same field names and table name

### Issues Found
| # | Severity | Description | Resolution Required |
|---|----------|-------------|---------------------|
| 1 | 🟡 ADVISORY | TimestampType changed to TimestamptzType in schema — minor deviation from original spec §3 | Documented in audit trail. Spec should be updated to reflect actual type. |
| 2 | 🟡 ADVISORY | pytz added as dependency (not in original spec) — required by DuckDB for timestamptz columns | Documented in audit trail. Necessary for correct operation. |

### Decision Rationale
All governance artifacts are present, internally consistent, and reference real implementation. No boilerplate — lineage includes column-level mappings, audit trail includes implementation discoveries, and DQ rules validate against actual Iceberg roundtrip data. Two advisory items are implementation improvements, not governance gaps.

Tests: 42 passing (20 infra + 15 flatten + 7 ingest), 4 network tests correctly deselected. No regressions.
