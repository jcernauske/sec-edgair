---
title: Trust & Verification
description: "An adversarial audit of an AI-built data pipeline. 12 hallucination risks identified, examined against 128 DQ rules, 88 verification checks, 12 chaos monkey runs, and 4 human approval gates. Honest assessment of what holds up and what does not."
---

# Trust & Verification

**For the skeptical architect, the compliance officer, and the CDO who have seen too many AI demos that fell apart under scrutiny.**

This page is structured as an adversarial dialogue. The auditor asks the hard questions. The project responds with specific evidence. Then the auditor gives an honest grade. No marketing. No hand-waving.

The meta-question: **This entire pipeline was built by AI agents. Every business term definition, every concept mapping, every DQ rule threshold, every data model -- an AI agent proposed it. A human approved it. But the human approved what the AI suggested. If the AI was confidently wrong, would the human have caught it?**

---

## Part 1: Risk Register

Twelve specific places where AI hallucination could produce outputs that look correct but are wrong.

| # | Risk | Severity | Category |
|---|------|----------|----------|
| 1 | Concept mappings assign XBRL tags to wrong business terms | Critical | Semantic accuracy |
| 2 | Business term definitions are plausible but incorrect | High | Semantic accuracy |
| 3 | DQ rule thresholds are set by AI without domain grounding | High | Rule calibration |
| 4 | Verification scripts compare AI output to AI-generated expected values | Critical | Circular validation |
| 5 | 88 checks verified out of 547K+ facts -- coverage is <0.02% | High | Coverage gap |
| 6 | Entity resolution maps CIKs to wrong companies | Critical | Identity |
| 7 | Financial fact values silently mutated during transformation | Critical | Data integrity |
| 8 | The "architect review" was another AI agent grading AI agents | Medium | Independence |
| 9 | Prefix/pattern mapping rules produce false positives at scale | High | Classification |
| 10 | Human approval gate can be globally disabled with one flag | Medium | Control bypass |
| 11 | Reasonableness bounds are too wide to catch subtle errors | Medium | Threshold calibration |
| 12 | No independent external audit or reconciliation to non-EDGAR source | High | External validation |

---

## Part 2: Challenge, Response, and Evidence

### Risk 1: Concept Mappings Assign XBRL Tags to Wrong Business Terms

**Challenge:** The AI mapped `RevenueFromContractWithCustomerExcludingAssessedTax` to BT-022 (Revenue). Is that right? What about `SalesRevenueNet` -- is that Revenue or something else? The XBRL taxonomy has thousands of concepts with subtle distinctions. An AI could plausibly map `OtherOperatingIncome` to Revenue and nobody would notice until a financial analyst got a wrong number.

**Response:**

The mapping system uses a three-tier architecture with declining confidence levels, defined in `src/base/xbrl_tag_normalization/config.py`:

- **Tier 1 (Exact match, confidence 1.0):** 35 hardcoded XBRL concept names mapped to specific business terms (lines 189-233). These are the canonical concepts that the US GAAP taxonomy defines for each financial line item. Example: `"RevenueFromContractWithCustomerExcludingAssessedTax": ("BT-022", "income_statement", "revenue")` at line 207.

- **Tier 2 (Prefix rules, confidence 0.7):** 22 prefix patterns (lines 241-275). Example: any concept starting with `"RevenueFromContract"` maps to BT-022. This catches variant concepts like `RevenueFromContractWithCustomerIncludingAssessedTax`.

- **Tier 3 (Unmapped, confidence 0.0):** Concepts that match no rule stay unmapped with `business_term_id = NULL`. These are not used in downstream analysis.

**Structural controls:**

1. DQ rule `BASE-TN-002` (P0) enforces that no concept maps to multiple business terms: `SELECT concept, COUNT(DISTINCT business_term_id) ... HAVING COUNT(DISTINCT business_term_id) > 1`. File: `governance/dq-rules/base-tag-normalization.json`, line 18.

2. DQ rule `BASE-TN-006` (P0) enforces Tier 3 concepts have NULL business_term_id and Tier 1+2 have non-NULL. File: `governance/dq-rules/base-tag-normalization.json`, line 66.

3. The verification script `scripts/verify.py` cross-checks pipeline output against 57 known 10-K figures across 20 companies. If Revenue were mapped to the wrong concept, Apple's FY2023 Revenue would not match $383.3B (line 15). It does match.

4. The verification script `scripts/verify_all_metrics.py` checks all 25 business terms for Apple FY2023 against the 10-K filing. Revenue, Cost of Revenue, Gross Profit, Operating Income, Net Income, and 20 other metrics all match within 1% tolerance. If any concept mapping were wrong, the corresponding metric would fail.

**What is NOT validated:** The 2,947 Tier 3 concepts (89.6% of all XBRL concepts) are unmapped and unverified. If a financially material concept exists in Tier 3 that should be mapped to a business term, the pipeline would silently exclude it from consumable tables. DQ rule `BASE-TN-004` (P1) checks that Tier 1+2 cover at least 25% of raw fact instances (actual: 30%). This catches gross undercoverage but not individual misses.

**Grade: Adequate.** Tier 1 exact mappings are verifiable against the XBRL taxonomy specification. Tier 2 prefix rules introduce classification risk but are constrained to common patterns. The 10-K cross-checks provide meaningful end-to-end validation. The gap is in Tier 3: no mechanism to detect concepts that *should* be mapped but are not.

---

### Risk 2: Business Term Definitions Are Plausible but Incorrect

**Challenge:** The AI defined 54 business terms in `governance/business-glossary.json`. For example, BT-022 (Revenue) is defined as "Total revenue recognized from the sale of goods and services, before deductions." Is that correct? GAAP Revenue recognition has changed significantly (ASC 606). A plausible-sounding definition could be subtly wrong.

**Response:**

The glossary uses a three-tier source system:

- **XBRL taxonomy terms** (auto-approved): Definitions sourced from the US GAAP XBRL Taxonomy. These are authoritative by construction. Example: BT-001 (CIK) cites "SEC EDGAR Filing Manual, Section 3.1".
- **SEC EDGAR terms** (auto-approved): Definitions from SEC documentation.
- **Project-specific terms** (require human approval): Terms the project created for pipeline concepts.

Of the 54 terms, 41 cite external authoritative sources. The remaining 13 are project-specific (e.g., BT-049 "Concept Mapping" -- a pipeline artifact, not a financial concept).

**What is NOT validated:** The AI's paraphrasing of XBRL taxonomy definitions is not machine-compared to the original XBRL taxonomy text. A human approved the glossary, but the human was reviewing AI-generated definitions, not the authoritative source text side-by-side. For terms like "Revenue" this is low risk (the concept is well-understood). For terms like "Comprehensive Income" or "Retained Earnings" the distinction between GAAP definitions matters more.

**Grade: Adequate.** External-standard terms have authoritative citations. Project-specific terms are flagged for human review. The gap: no automated comparison of AI-written definitions to source-of-truth XBRL taxonomy text.

---

### Risk 3: DQ Rule Thresholds Are Set by AI Without Domain Grounding

**Challenge:** The AI proposed that Revenue should be > 0 for all non-financial companies (rule `BASE-CF-020`). Is that true? Are there valid cases where revenue is zero or negative? Who decided that `ABS(val) > 1e14` is the right threshold for extreme outliers (rule `RAW-CF-020`)?

**Response:**

DQ thresholds are derived from EDA (Exploratory Data Analysis) against real data, not from the AI's general knowledge. The evidence chain is:

1. **@data-analyst** profiles real Iceberg data, producing EDA reports in `governance/eda/`. These contain actual distributions, min/max values, and outlier counts.

2. **@dq-rule-writer** writes rules from EDA evidence, citing the specific EDA findings in each rule's `rationale` field.

Example evidence chain for `BASE-CF-020` (Revenue > 0):
- Rationale field: "EDA: 1,326/1,329 Revenue values (99.77%) are positive. 3 negative values exist: Apple ($-29M), Microsoft ($-6B), Goldman Sachs ($-4.7B)."
- The rule accounts for known exceptions: Goldman Sachs excluded as financial; Apple and Microsoft negatives tolerated (threshold `<= 2`).
- File: `governance/dq-rules/base-conformed-facts.json`, rule `BASE-CF-020`, line 239.

Example evidence chain for `RAW-CF-020` ($100 trillion bound):
- Rationale: "Chaos monkey injected 1,290 extreme outliers (val=999,999,999,999,999) -- zero caught. The entire US GDP is ~$28 trillion."
- This rule was added *after* the chaos monkey found the gap. File: `governance/dq-rules/raw-xbrl-company-facts.json`, line 249.

The chaos monkey validated that 15 new DQ rules (RAW-CF-014 through RAW-CF-028), all added post-chaos-testing, catch 100% of injected corruptions across 10 dimensions. Evidence: `governance/chaos-reports/chaos-aar-2026-03-15-20-20-09.md`, Section 3: 38,317/38,317 corruptions detected (100%).

**What is NOT validated:** The Reasonableness rules for financial ratios use wide bounds ([-100, 100] for most ratios). These catch extreme outliers but would not catch a 20% error in Operating Margin. The rationale acknowledges this: "catches catastrophic failures, not subtle issues" (from `docs/site/content/results.md`, line 164).

**Grade: Strong for structural rules, Adequate for value-range rules.** Thresholds grounded in EDA evidence are defensible. The chaos monkey provides adversarial validation. The gap: reasonableness bounds are wide by design -- they catch data corruption, not data quality drift.

---

### Risk 4: Verification Scripts Compare AI Output to AI-Generated Expected Values

**Challenge:** The project claims "88/88 verification checks against real 10-K filings." But who created the expected values in `scripts/verify.py`? If the AI generated both the pipeline output and the expected values, you are comparing AI output to AI output. That is circular validation.

**Response:**

The expected values in `scripts/verify.py` are hardcoded financial figures from public 10-K filings. Each value has a source citation. Examples from the file:

- Line 13: `"expected": 391_035_000_000, "source": "Apple 10-K FY2024"` (Apple Revenue FY2024)
- Line 52: `"expected": 158_104_000_000, "source": "JPM 10-K FY2023"` (JPMorgan Revenue FY2023)
- Line 58: `"expected": -2_222_000_000, "source": "Boeing 10-K FY2023"` (Boeing Net Income -- negative, testing loss scenarios)

These values are verifiable by anyone with access to SEC EDGAR. Apple's FY2024 10-K (accession number 0000320193-24-000123) reports Revenue of $391,035M on the Consolidated Statements of Operations. The values are NOT generated by the pipeline -- they are manually researched from the actual filings.

**However, there is a legitimate concern:** The expected values were entered by the same AI agents that built the pipeline. While the values are objectively verifiable, a skeptic could argue that the AI selected 10-K figures that it knew the pipeline would produce correctly, avoiding edge cases.

The negative verification script (`scripts/verify_negative.py`) partially addresses this by asserting the *absence* of incorrect data: no duplicate grains, no superseded fact leaks, no null business terms, no wrong-unit values, no fiscal year collisions, no orphan ratios, and cross-zone row alignment. These 10 checks are structural, not value-based, and harder to game.

**Grade: Adequate.** The expected values are independently verifiable from public SEC filings. The concern about selection bias is valid but mitigated by the breadth of coverage (20 companies, 8 sectors, all 4 fiscal year-end patterns, negative values, per-share values). An independent party could re-derive every expected value from sec.gov in about an hour.

---

### Risk 5: 88 Checks Verified Out of 547K+ Facts -- Coverage Is <0.02%

**Challenge:** The pipeline processes 547,398 raw facts and produces 136,257 consumable rows. Only 88 specific values were verified against 10-K filings. That is a coverage rate of 0.016%. What about the other 99.98% of the data?

**Response:**

The 88 value-level checks are the tip of the verification pyramid:

| Layer | What It Checks | Coverage |
|-------|---------------|----------|
| 128 DQ rules | Structural integrity, referential integrity, uniqueness, completeness, consistency, validity, volume, accuracy, reasonableness | Every row in every table, every execution |
| 10 negative checks | Absence of known error patterns | Full table scans across 5 tables |
| 88 value checks | Specific financial values against 10-K filings | 88 specific data points across 20 companies |
| Chaos monkey | Adversarial injection of 38,317 corrupted rows across 10 DQ dimensions | 100% detection rate validated |

The DQ rules execute SQL against every row. For example:
- `BASE-CF-006` checks 22 columns for NULL values across all 28,849 rows in `base.conformed_facts`.
- `CONS-CF-001` checks every `record_id` for uniqueness across all 26,894 rows in `consumable.company_financials`.
- `RAW-CF-002` checks 7 required fields for NULLs across all 547,398 raw rows.

The 88 value checks serve a different purpose: they validate *semantic accuracy*, not structural integrity. DQ rules prove the data is internally consistent. The 10-K checks prove the data matches external reality.

**What is NOT validated:** For the ~136K consumable rows that are NOT among the 88 verified values, the only guarantee is structural correctness (DQ rules) and lineage traceability (every row carries `accession_number` back to its SEC filing). A subtle transformation bug that produces a plausible but wrong value for, say, Intel's FY2019 R&D Expense would not be caught unless someone manually checks Intel's 10-K.

**Grade: Adequate.** The verification pyramid is well-structured. 88 value checks across 20 companies and 8 sectors provides meaningful sampling. The DQ rules provide full structural coverage. The gap: semantic accuracy is verified by sampling, not exhaustively.

---

### Risk 6: Entity Resolution Maps CIKs to Wrong Companies

**Challenge:** The AI mapped CIK 320193 to "Apple Inc." How do you know that is correct? What if a CIK was mapped to the wrong company?

**Response:**

Entity resolution uses a hardcoded lookup table of 20 CIK-to-company mappings in `src/base/entity_resolution/config.py` (lines 13-134). These are not AI-inferred -- they are CIK numbers from SEC EDGAR, which is a public, authoritative registry. Anyone can verify that CIK 320193 is Apple Inc. by visiting `https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=320193`.

The staging/approval gate in `src/base/entity_resolution/staging.py` enforces:
- Mappings below `CONFIDENCE_FLOOR` (0.7) always require human review (line 73)
- When `REQUIRE_HUMAN_APPROVAL = True`, all mappings require human review (line 76)
- A hard floor exists that cannot be bypassed even when the toggle is off (line 73)

DQ controls:
- `BASE-ER-001` (P0): Every CIK in raw data has an approved mapping (no orphans)
- `BASE-ER-002` (P0): No duplicate CIKs in approved mappings (one mapping per entity)
- `BASE-ER-004` (P0): Every approved mapping has non-null `approved_by` and `approved_at` (audit trail)

Since all 20 entities use exact CIK matches at confidence 1.0, and CIK is a SEC-assigned identifier, this mapping is verifiable against an authoritative external source.

**Grade: Strong.** CIK-to-company mapping is deterministic and externally verifiable. The approval gate has a hard floor that cannot be toggled off. This is one of the strongest controls in the pipeline.

---

### Risk 7: Financial Fact Values Silently Mutated During Transformation

**Challenge:** The pipeline moves data from raw to base to consumable. At each stage, values could be transformed, truncated, or corrupted. How do you prove the numbers that come out match the numbers that went in?

**Response:**

DQ rule `BASE-CF-007` (P1) explicitly validates value preservation:
```sql
SELECT COUNT(*) FROM base.conformed_facts cf
JOIN base.financial_facts ff ON cf.source_fact_id = ff.fact_id
WHERE cf.val != ff.val
```
File: `governance/dq-rules/base-conformed-facts.json`, line 84. Threshold: `result = 0`. This proves that conformed_facts values are exact copies of the winning fact values -- no transformation applied.

DQ rule `CONS-CF-011` (P0) validates row count alignment between consumable and base:
```sql
SELECT ABS(
  (SELECT COUNT(*) FROM consumable.company_financials)
  - (SELECT COUNT(*) FROM base.conformed_facts)
)
```
File: `governance/dq-rules/consumable-company-financials.json`, line 131. Threshold: `result = 0`. No rows created or lost.

Negative verification check 8 (`check_row_count_alignment` in `scripts/verify_negative.py`, line 225) independently confirms the same: `company_financials` row count equals `conformed_facts` row count.

The `accession_number` field is preserved at every layer, enabling manual trace-back to the original SEC filing for any value.

**Grade: Strong.** Value preservation is validated by cross-table DQ rules. Row count alignment is checked at both DQ and verification levels. Lineage is traceable via `accession_number` at every layer.

---

### Risk 8: The "Architect Review" Was Another AI Agent Grading AI Agents

**Challenge:** The project cites a "principal data architect" review that gave the pipeline a B+ then an A. But this was an AI agent reviewing other AI agents' work. This is not independent validation.

**Response:**

The project acknowledges this directly in `docs/site/content/results.md` (line 84): *"Yes -- an AI agent grading other AI agents' work. We are fully aware of the optics."*

The project's defense is that the findings were actionable and the fixes were real:
- The review identified 6 specific architectural problems (in-memory dedup, missing DQ gates, hardcoded anomaly detection, static lineage, no negative testing, buried config)
- Each finding was remediated in a tracked spec (`docs/specs/infra-architect-remediation.md`)
- The re-review confirmed the remediations were implemented

The architect review is documentation of an AI-driven review process. It is not a substitute for independent human review. The project makes no claim otherwise.

**Grade: Weak as independent validation, Adequate as a process artifact.** The review produced real findings and real fixes. But an AI agent cannot serve as an independent auditor of other AI agents. A regulator would require a human architect review.

---

### Risk 9: Prefix/Pattern Mapping Rules Produce False Positives at Scale

**Challenge:** The Tier 2 prefix rule maps any concept starting with `"RevenueFromContract"` to Revenue (BT-022). What about `RevenueFromContractWithCustomerExcludingAssessedTax_DiscontinuedOperations`? That is revenue from discontinued operations -- arguably not the same as the Revenue line item. The pattern rules (Tier 2, confidence 0.6) use regex like `(?i).*Revenue.*(?!Deferred|Remaining|Recognized)` which could match concepts that are not revenue.

**Response:**

The prefix rules are at confidence 0.7, and pattern rules at confidence 0.6. Both are below the exact match confidence of 1.0. The staging gate in `src/base/entity_resolution/staging.py` (and its equivalent for tag normalization) applies the `CONFIDENCE_FLOOR` of 0.7:

- Tier 1 (confidence 1.0): auto-promotes when `REQUIRE_HUMAN_APPROVAL = False`
- Tier 2 prefixes (confidence 0.7): auto-promotes when `REQUIRE_HUMAN_APPROVAL = False` (at the floor)
- Tier 2 patterns (confidence 0.6): **always requires human review** because 0.6 < 0.7 floor

This is defined in `src/base/xbrl_tag_normalization/config.py`, line 12: `CONFIDENCE_FLOOR = 0.7`.

DQ rule `BASE-TN-002` (P0) prevents any concept from mapping to multiple business terms. If a prefix rule incorrectly captures a concept that should map to a different business term, this DQ rule would fire when the correct mapping is also attempted.

**What is NOT validated:** A concept that *should* map to BT-036 (Operating Income) but is captured by the Revenue prefix rule (BT-022) would not trigger `BASE-TN-002` because it maps to exactly one term -- just the wrong one. The only defense is the 10-K cross-checks: if Apple's Operating Income is wrong because a concept was mis-mapped to Revenue, the Operating Income verification would fail.

**Grade: Adequate.** The confidence floor provides a structural defense for low-confidence mappings. The one-to-one DQ rule prevents split mappings. The gap: a confident-but-wrong prefix match would only be caught by downstream 10-K verification.

---

### Risk 10: Human Approval Gate Can Be Globally Disabled With One Flag

**Challenge:** `REQUIRE_HUMAN_APPROVAL = True` in `src/config.py` (line 20) is a single boolean. Set it to `False` and every gate auto-approves. This is a global kill switch for governance.

**Response:**

The toggle exists by design for two modes:
- `True`: Production mode. All proposals pause for human review.
- `False`: Dev/demo mode. Proposals auto-advance but all artifacts are still produced.

Critical safety nets when the toggle is off:

1. **Hard confidence floor:** Mappings below `CONFIDENCE_FLOOR` (0.7) always require human review regardless of the toggle. This is enforced in `src/base/entity_resolution/staging.py`, line 73: `if confidence < confidence_floor: needs_review.append(proposal)`. The floor check happens *before* the toggle check.

2. **DQ P0 gate cannot be toggled off:** `validate_after_write()` in `src/infra/dq_runner.py` (line 274) raises `DQValidationError` on P0 failures regardless of the approval toggle. This is wired into all 11 promote functions (11 files reference `validate_after_write`).

3. **The toggle is visible:** It is in `src/config.py`, a tracked file in version control. Any change is auditable via git history.

4. **Current state:** `REQUIRE_HUMAN_APPROVAL = True` (line 20). It is on.

**Grade: Adequate.** The confidence floor and P0 gate provide defense-in-depth. The toggle's existence is a pragmatic engineering choice. A regulator would want the toggle enforced at the infrastructure level (e.g., environment variable, secrets manager) rather than a Python constant.

---

### Risk 11: Reasonableness Bounds Are Too Wide to Catch Subtle Errors

**Challenge:** The Reasonableness DQ rules use bounds like [-100, 100] for Operating Margin (`CONS-FR-012`). That is an absurdly wide range. A company with a true 30% operating margin could report 2% or 80% and the DQ rule would pass. These bounds catch data corruption, not data quality issues.

**Response:**

The project explicitly acknowledges this. From `docs/site/content/results.md` (line 164): *"The Reasonableness DQ bounds are wide ([-100, 100] for most ratios) -- they catch catastrophic failures, not subtle issues."*

The bounds were widened from tighter spec-defined ranges after EDA revealed real outliers:
- Netflix Q1 2010: Operating Margin of 4,862x (revenue was $12K in that quarter -- the company was pre-scale)
- Exxon FY2008: Net Margin of 367x ($45B NI / $123M revenue -- a data artifact from quarterly-vs-annual mismatch)

These are documented in the rationale fields of rules `CONS-FR-012` through `CONS-FR-015` in `governance/dq-rules/consumable-financial-ratios.json`.

The tight-bound alternative would require company-specific or sector-specific rules, which the pipeline does not implement.

**Grade: Weak for detecting subtle errors, Adequate for detecting data corruption.** The bounds serve their stated purpose (catching catastrophic failures). A production system would need tighter, context-sensitive bounds -- ideally per-company or per-sector baseline ranges with drift detection.

---

### Risk 12: No Independent External Audit or Reconciliation to Non-EDGAR Source

**Challenge:** The 88 verification checks compare pipeline output to values from the same source (SEC EDGAR 10-K filings). This verifies that the pipeline faithfully reproduces EDGAR data. It does not verify that the EDGAR data is correct. Furthermore, no independent third party (Bloomberg, FactSet, S&P Capital IQ) has reconciled this data.

**Response:**

This is a genuine gap. The pipeline verifies internal consistency and faithfulness to the SEC EDGAR source. It does not verify against any independent data provider.

The project's position (from `docs/site/content/results.md`, line 159): *"This is not production-ready at scale."* And: *"The project's value is in the methodology, not in claiming perfection."*

The pipeline's traceability architecture (every row carries `accession_number`) makes third-party reconciliation *possible* -- you could join pipeline output to Bloomberg data by (ticker, metric, fiscal_year) and compare. But this has not been done.

**Grade: Missing.** No external reconciliation exists. This is the largest gap in the project's trust story. A financial services regulator would require reconciliation to at least one independent data source before the data could be used for any regulated purpose.

---

## Part 3: Honest Assessment

### Controls That Are Strong

| Control | Why It Is Strong |
|---------|-----------------|
| **Entity resolution** (Risk 6) | CIK-to-company mappings are deterministic, externally verifiable against sec.gov, and protected by a confidence floor that cannot be toggled off |
| **Value preservation** (Risk 7) | Cross-table DQ rules prove values are not mutated. Row count alignment checked at two independent levels |
| **DQ P0 gate** | `validate_after_write()` runs on all 11 promotes, raises exceptions on P0 failures, cannot be disabled by the approval toggle |
| **Chaos monkey** | 38,317 adversarial corruptions across 10 dimensions, 100% detection rate, with 12 after-action reports in `governance/chaos-reports/` |
| **Lineage traceability** | `accession_number` preserved at every layer. Runtime lineage events in Iceberg table. Any value traceable to source SEC filing |

### Controls That Are Adequate

| Control | Why It Is Adequate | What Would Make It Strong |
|---------|-------------------|---------------------------|
| **Concept mappings** (Risk 1) | Tier 1 exact matches are verifiable. 10-K cross-checks catch end-to-end errors. But Tier 3 has no coverage validation | Automated comparison of Tier 1 mappings against XBRL taxonomy spec. Tier 3 materiality analysis |
| **Business term definitions** (Risk 2) | External sources cited. Human approval gates. But no machine comparison to authoritative text | Side-by-side comparison tool: AI definition vs XBRL taxonomy definition |
| **DQ thresholds** (Risk 3) | EDA-grounded. Chaos-validated. But reasonableness bounds are wide | Per-company baseline ranges. Statistical drift detection |
| **Verification values** (Risk 4) | Independently verifiable from sec.gov. But created by same AI agents | Independent party re-derives expected values from scratch |
| **Verification coverage** (Risk 5) | Pyramid structure: 128 DQ rules + 10 negative checks + 88 value checks | Expand value checks to all 25 metrics for all 20 companies (500 checks) |
| **Approval toggle** (Risk 10) | Confidence floor + P0 gate provide defense-in-depth | Environment-level enforcement, not a Python constant |

### Controls That Are Weak or Missing

| Control | Status | Impact |
|---------|--------|--------|
| **Reasonableness bounds** (Risk 11) | Weak | Subtle value errors (20% off) would pass all DQ rules |
| **Independent architect review** (Risk 8) | Weak | AI agent review is not a substitute for human architect review |
| **External reconciliation** (Risk 12) | Missing | No comparison to Bloomberg, FactSet, or any non-EDGAR source |
| **Prefix/pattern false positive detection** (Risk 9) | Adequate but unverified | No automated test validates that prefix rules do not capture wrong concepts |

---

## Part 4: What Would Satisfy a Financial Services Regulator

A regulator in banking, insurance, or asset management would require the following before this data could be used for any regulated purpose:

### 1. Independent Data Reconciliation
Reconcile pipeline output against at least one independent data provider (Bloomberg, FactSet, S&P Capital IQ) for all companies and all metrics. Document discrepancies and root causes. Currently: **Not done.**

### 2. Human Model Validation
An independent human data architect (not an AI agent) reviews the conceptual, logical, and physical models in `governance/models/` and signs off. The AI-generated architect review in `governance/reviews/` is a process artifact, not an independent audit. Currently: **Not done.** The `@principal-data-architect` review was an AI agent.

### 3. Mapping Certification
Each of the 35 Tier 1 XBRL concept mappings should be certified against the US GAAP XBRL Taxonomy specification by a subject matter expert (CPA or XBRL specialist). The AI proposed them correctly as far as the 10-K cross-checks can tell, but "correct by output" is not the same as "certified by reference." Currently: **Not done.**

### 4. Tighter Reasonableness Bounds
Replace the wide [-100, 100] ratio bounds with company-specific or sector-specific ranges derived from historical baselines. Implement statistical drift detection (e.g., if Apple's Gross Margin moves more than 5 percentage points year-over-year, flag for investigation). Currently: **Wide bounds only.** Rules like `CONS-FR-012` explicitly tolerate extreme outliers.

### 5. Access Control on Approval Toggle
Move `REQUIRE_HUMAN_APPROVAL` from a Python constant (`src/config.py`, line 20) to an environment variable or secrets manager with audit logging. Prevent developers from disabling governance controls without a change management record. Currently: **Python constant in version-controlled file.** Auditable via git history but not access-controlled.

### 6. Automated Regression Testing Against Known Values
The 88 verification checks in `scripts/verify.py` and `scripts/verify_all_metrics.py` should run automatically on every pipeline execution (CI/CD), not just on manual invocation. Currently: **Manual execution only.** These are scripts, not integrated tests.

### 7. Data Retention and Immutability Proof
While Iceberg provides snapshot isolation, a regulator would want proof that snapshots are retained for the required retention period (typically 7 years for financial data) and that previous snapshots are not deletable by operators. Currently: **Iceberg snapshots exist but no retention policy is enforced.**

### 8. Formal Data Lineage Standard
The runtime lineage events in `governance.lineage_events` follow OpenLineage conventions, but a regulator may require formal BCBS 239 compliance (risk data aggregation and risk reporting), including data quality attestation at each transformation step. Currently: **OpenLineage-format events exist.** No formal BCBS 239 mapping.

---

## The Bottom Line

This pipeline demonstrates that AI agents can produce data governance artifacts -- business terms, data models, DQ rules, lineage records -- that are structurally sound, internally consistent, and verifiable against external references. The 128 DQ rules, 12 chaos monkey runs, 88 verification checks, and 4 human approval gates represent a level of governance rigor that many *human-built* data pipelines do not achieve.

But "better than many human-built pipelines" is not the bar for regulated industries. The bar is: **can you prove to a skeptical regulator that the data is correct, the controls are effective, and the process is auditable?**

Today, the answer is: mostly yes for structural controls (entity resolution, value preservation, referential integrity, uniqueness), and not yet for semantic controls (concept mapping certification, external reconciliation, tight reasonableness bounds).

The architecture makes it possible to close these gaps. The gaps are known, documented, and addressable. That is itself a form of trustworthiness -- not the trustworthiness of perfection, but the trustworthiness of transparency.

---

[Back to home](index.md) | [Governance](governance.md) | [Results](results.md)
