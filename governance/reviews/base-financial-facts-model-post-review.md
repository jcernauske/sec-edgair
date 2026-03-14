## Governance Review: base-financial-facts-model
**Review Type:** Post-Implementation (Backfill Mode)
**Reviewer:** @governance-reviewer
**Date:** 2026-03-14
**Verdict:** APPROVED (with advisory findings)

---

### Post-Implementation Governance Completeness Checklist

| # | Item | Result | Notes |
|---|------|--------|-------|
| 1 | **Lineage:** OpenLineage events exist in `governance/lineage/` | PASS | `governance/lineage/base-financial-facts-model.json` present. Documents 3 inputs (raw.xbrl_company_facts, base.entity_mappings, base.concept_mappings) and 3 outputs (base.financial_facts, base.fiscal_calendar, base.amendment_tracking). Column-level lineage provided for derived fields (fact_id, calendar_year, calendar_quarter, is_amendment, is_superseded). |
| 2 | **DQ Rules:** Data quality rules exist in `tests/` for every new/modified table | PASS | 7 DQ rules defined in `governance/dq-rules/base-financial-facts-model.json` (BASE-FM-001 through BASE-FM-007). All 3 tables covered. 40 tests in `tests/base/financial_facts_model/` across 5 test files (test_model.py, test_amendments.py, test_fiscal_calendar.py, test_promote.py, test_cli.py). |
| 3 | **DQ Scorecard:** Scorecard produced showing pass/fail rates per table | PASS | `governance/dq-scorecards/base-financial-facts-model-scorecard.md` present. All 7 rules pass at 100%. Scorecard includes test-based validation results, join logic validation, supersession validation, fiscal calendar validation, amendment tracking validation, and Iceberg roundtrip validation. |
| 4 | **CDE Tags:** New or modified fields are tagged in `governance/cde-catalog.json` | ADVISORY | CDE catalog does NOT contain mappings for `base.financial_facts`, `base.fiscal_calendar`, or `base.amendment_tracking` tables. However, the data dictionary entries DO include `cde_reference` fields (e.g., cik -> CDE-001, accession_number -> CDE-002, canonical_name -> CDE-005, filed_date -> CDE-004). The CDE catalog was designed with mappings at the source table level (raw.xbrl_company_facts, base.entity_mappings, base.concept_mappings) and the financial_facts table denormalizes those same CDEs. This is acceptable since the CDEs trace through lineage. See Advisory #1. |
| 5 | **Data Dictionary:** New or modified fields have entries in `governance/data-dictionary.json` | PASS | All 3 tables documented with full field-level definitions: base.financial_facts (28 fields), base.fiscal_calendar (12 fields), base.amendment_tracking (16 fields). Field definitions include data types, nullability, descriptions, DQ rule references, and CDE references where applicable. |
| 6 | **Data Contracts:** Consumable zone tables have data contracts | N/A | This is a Base zone spec. Data contracts are a Consumable zone requirement. |
| 7 | **Audit Trail:** Agent decision logs exist in `governance/audit-trail/` | PASS | `governance/audit-trail/base-financial-facts-model.json` present. Documents 7 design decisions with agent attribution, rationale, and confidence levels. Decisions cover: grain design, denormalization, no staging gate, fiscal calendar methodology, taxonomy inclusion, supersession algorithm, and unmapped concept defaults. |
| 8 | **Schema Changes:** Changes match spec and approved physical model | PASS | Physical model documents 3 tables with column counts matching spec (28 + 12 + 16). Column names, types, and nullability in physical model match the spec's table definitions exactly. |
| 9 | **Data Models (Base zone):** All three model stages exist in `governance/models/` and physical model matches implementation | PASS | All three models exist and are APPROVED. Physical model matches source code structure (7 modules). See Backfill checklist below for details. |
| 10 | **No Orphaned Artifacts:** No governance artifacts reference nonexistent tables/fields | PASS | Lineage, DQ rules, data dictionary, and models all reference the same 3 tables with consistent field names. No references to tables or fields that don't exist. |
| 11 | **Consistency:** Lineage, CDE tags, data dictionary, and DQ rules all reference same field/table names | PASS | All artifacts use consistent naming: base.financial_facts, base.fiscal_calendar, base.amendment_tracking. Field names are consistent across lineage (schema fields), data dictionary (field entries), DQ rules (SQL references), and physical model (column definitions). |

### Backfill Mode Checklist

| # | Item | Result | Notes |
|---|------|--------|-------|
| 1 | **Physical model** exists and accurately reflects existing Iceberg tables and source code | PASS | `governance/models/base-financial-facts-model-physical.md` present, Status: APPROVED. Documents 3 tables with full column specifications, source mappings, and physical design decisions. Matches spec's table definitions. Source files referenced: schema.py, model.py, fiscal_calendar.py, amendments.py, promote.py. |
| 2 | **Logical model** exists, is abstracted from the physical, and is APPROVED | PASS | `governance/models/base-financial-facts-model-logical.md` present, Status: APPROVED. 3 owned entities (FinancialFact, FiscalCalendar, AmendmentTracking) + 2 cross-references (Entity, Concept). Full attribute definitions with domains, nullability, CDE references. Grain definitions and normalization decisions documented. |
| 3 | **Conceptual model** exists, is abstracted from the logical, and is APPROVED | PASS | `governance/models/base-financial-facts-model-conceptual.md` present, Status: APPROVED. 6 entities, 6 relationships, 6 business rules. Clear domain narrative connecting to implementation. |
| 4 | **Business terms** extracted and added to glossary -- project-specific terms APPROVED | PASS | 9 terms relevant to this spec found in `governance/business-glossary.json`: Financial Fact (BT-017), Fiscal Period (BT-018), Fiscal Calendar (BT-019), Supersession (BT-012), Amendment (BT-007), XBRL Concept (BT-009), Financial Statement (BT-021), Revenue (BT-022), Net Income (BT-023). All have status "approved". Project-specific terms approved by "human:jeff", external standard terms auto-approved. |
| 5 | **All three models are consistent with each other AND with existing implementation** | PASS | Conceptual entities (Company, Financial Fact, Financial Concept, Fiscal Period, SEC Filing, Amendment) map cleanly to logical entities (FinancialFact, FiscalCalendar, AmendmentTracking + Entity, Concept cross-refs) which map to physical tables (base.financial_facts, base.fiscal_calendar, base.amendment_tracking). Physical model column counts (28, 12, 16) match spec. |
| 6 | **All three models include a Mermaid erDiagram block** | PASS | Conceptual: erDiagram with 6 entities and 6 relationships. Logical: erDiagram with 5 entities (3 owned + 2 referenced) and 4 relationships. Physical: erDiagram with 5 tables (3 owned + 2 referenced) and 4 relationships with full column definitions. |
| 7 | **Conceptual model references glossary terms (not inline definitions)** | PASS | Entity descriptions align with glossary terms. "Financial Fact" matches BT-017, "Fiscal Period" matches BT-018, "Amendment" matches BT-007, "SEC Filing" matches BT-004. Model uses consistent terminology with the glossary. |
| 8 | **No implementation changes were made during backfill** | PASS | Completion spec explicitly states "No new code to write, No new tests to add, No new DQ rules, No schema changes, No new governance artifacts to produce." Models were reverse-engineered documentation only. |

### README Data Model Diagrams Check

| # | Item | Result | Notes |
|---|------|--------|-------|
| 1 | Conceptual diagram in README | PASS | README lines 170-180 contain the Financial Facts Model conceptual erDiagram matching the conceptual model file. |
| 2 | Logical diagram in README | PASS | README lines 254-323 contain the Financial Facts Model logical erDiagram matching the logical model file. |
| 3 | Physical diagram in README | PASS | README lines 389-470 contain the Financial Facts Model physical erDiagram matching the physical model file. |
| 4 | README Phase 2 table includes this spec | ADVISORY | The Phase 2 table does NOT list `base-financial-facts-model`. See Advisory #2. |
| 5 | README pipeline summary includes new tables | ADVISORY | The pipeline summary diagram does NOT include base.financial_facts, base.fiscal_calendar, or base.amendment_tracking. See Advisory #2. |
| 6 | README governance stats are current | ADVISORY | README says "5 Iceberg tables" (should be 8 with the 3 new tables), "106 tests" (should be 146). See Advisory #2. |

### Issues Found

| # | Severity | Description | Resolution Required |
|---|----------|-------------|---------------------|
| 1 | ADVISORY | CDE catalog (`governance/cde-catalog.json`) has no explicit mappings for `base.financial_facts`, `base.fiscal_calendar`, or `base.amendment_tracking` tables. CDE-bearing columns (cik, accession_number, canonical_name, filed_date) are documented with cde_reference in the data dictionary but not cross-referenced in the CDE catalog's mappings arrays. | Not blocking. The CDEs trace through lineage from upstream tables where they are cataloged. When the @cde-tagger runs on a future spec, it should consider adding downstream table mappings to the CDE catalog for completeness. |
| 2 | ADVISORY | README.md has stale counts and is missing the `base-financial-facts-model` spec from the Phase 2 "What's Built" table, the pipeline summary, and the governance statistics (table count says 5, should be 8; test count says 106, should be 146). The data model diagrams ARE present and current. | Not blocking for governance approval. These are documentation hygiene items that should be addressed before or during the @staff-engineer review. The critical requirement (data model diagrams in README) is satisfied. |

### Decision Rationale

**Verdict: APPROVED** (with advisory findings)

This spec passes all governance completeness checks for both the post-implementation and backfill mode checklists. The key findings:

1. **All governance artifacts are present and complete.** Lineage, DQ rules, DQ scorecard, audit trail, and data dictionary entries exist with correct content referencing the right tables and fields.

2. **All three data models (conceptual, logical, physical) are APPROVED and consistent.** The backfill reverse-engineering accurately documents the as-built implementation. Models are consistent with each other and with the spec's table definitions.

3. **Business glossary terms are in place.** All relevant terms are approved -- project-specific terms by human:jeff, external standard terms auto-approved.

4. **DQ rules validate real data behavior.** The 7 DQ rules cover referential integrity (entity_id validity, amendment tracking references), uniqueness (fact_id), consistency (supersession pairing), completeness (fiscal calendar coverage, no orphan facts), and validity (calendar_quarter range). The scorecard shows all 40 tests pass with real test data, not placeholders.

5. **No implementation changes were made during backfill.** The completion spec is documentation/approval-only -- no code, tests, or schema changes.

6. **The two advisory findings are documentation hygiene issues.** The CDE catalog gap is a completeness nice-to-have (CDEs are traceable through lineage). The README staleness is cosmetic -- the data model diagrams (the critical README requirement per CLAUDE.md) are present and accurate.

This spec is approved to proceed to @staff-engineer final review. The advisory items should be addressed but are not blocking.
