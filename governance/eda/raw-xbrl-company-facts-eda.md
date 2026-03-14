## EDA Report: raw.xbrl_company_facts
**Source:** raw.xbrl_company_facts (Iceberg)
**Date:** 2026-03-14
**Agent:** @data-analyst
**Record Count:** 547,398
**Field Count:** 20

### Key Findings

- **39.1% of rows have NULL start_date** — these are instant-type XBRL facts (balance sheet items). Not a data quality issue — it's by design. DQ rules must NOT flag this.
- **59.0% of rows have NULL frame** — SEC only includes frame for facts that match calendar-year quarters. Expected.
- **0.5% have NULL fiscal_year and fiscal_period** — 2,516 rows, all from 8-K filings. 8-Ks are event-based, not period-based.
- **64,097 negative values (11.7%)** — legitimate. Net losses, accumulated deficits, treasury stock. NOT a DQ issue.
- **14,964 zero values (2.7%)** — legitimate. Zero dividends, zero R&D, etc.
- **72 rows where filed_date < end_date (0.013%)** — NT filings and preliminary filings. Known edge case.
- **56 distinct units** — most are USD (88.8%), but includes `segment`, `Segment` (case inconsistency), `country`, `years`, `Plaintiff`, etc. Long tail of exotic units.
- **4 taxonomies** — us-gaap dominates (99.6%), with dei (0.3%), invest (0.1%), srt (0.0%).
- **0 accession number format violations** — all match `NNNNNNNNNN-NN-NNNNNN`.
- **label and description have identical null patterns** — 2,437 nulls each (0.4%). Same rows missing both.

### Field Profiles

#### cik (int)
- **Null Rate:** 0%
- **Cardinality:** 20 distinct (expected — 20 companies)
- **Range:** 12,927 to 1,652,044
- **Anomalies:** None

#### entity_name (string)
- **Null Rate:** 0%
- **Cardinality:** 20 distinct
- **Note:** Names are ALL CAPS for some companies ("GOLDMAN SACHS GROUP INC") and mixed case for others ("JPMorgan Chase & Co"). Source inconsistency, not our bug.

#### taxonomy (string)
- **Null Rate:** 0%
- **Cardinality:** 4 distinct
- **Distribution:** us-gaap 99.6%, dei 0.3%, invest 0.1%, srt 0.0%

#### concept (string)
- **Null Rate:** 0%
- **Cardinality:** 3,289 distinct
- **Top 5:** NetIncomeLoss (5,344), EarningsPerShareDiluted (4,588), EarningsPerShareBasic (4,504), IncomeTaxExpenseBenefit (4,354), CashAndCashEquivalentsAtCarryingValue (4,088)

#### label (string)
- **Null Rate:** 0.4% (2,437 rows)
- **Cardinality:** 3,202 distinct
- **Note:** Nulls align exactly with description nulls — same 2,437 rows missing both

#### description (string)
- **Null Rate:** 0.4% (2,437 rows)
- **Cardinality:** 3,181 distinct

#### unit (string)
- **Null Rate:** 0%
- **Cardinality:** 56 distinct
- **Distribution:** USD 88.8%, shares 4.9%, USD/shares 3.9%, pure 2.2%, then long tail
- **Anomaly:** Case inconsistency — both `segment` (232) and `Segment` (174) exist. Same for `Year` (44) vs `years` (47).

#### start_date (date)
- **Null Rate:** 39.1% (214,231 rows) — instant-type facts, expected
- **Range:** 2003-01-01 to 2025-12-01
- **Note:** NULL rate is consistent across all form types (~38-40%)

#### end_date (date)
- **Null Rate:** 0%
- **Range:** 2006-06-30 to 2026-03-11
- **Cardinality:** 1,132 distinct

#### val (double)
- **Null Rate:** 0%
- **Cardinality:** 75,959 distinct (13.9% unique)
- **Range:** -2,952,048,000,000 to 80,832,000,000,000
- **Percentiles:** P1=-7.2B, P25=17M, P50=771M, P75=6.6B, P99=428.6B
- **Zeros:** 14,964 (2.7%) — legitimate
- **Negatives:** 64,097 (11.7%) — legitimate (losses, deficits, treasury stock)
- **Anomalies:** None — the extreme range is expected for large-cap financials (JPMorgan, Berkshire)

#### accession_number (string)
- **Null Rate:** 0%
- **Cardinality:** 1,328 distinct
- **Format:** 100% match `NNNNNNNNNN-NN-NNNNNN`

#### fiscal_year (int)
- **Null Rate:** 0.5% (2,516 rows — all 8-K filings)
- **Range:** 2009 to 2026
- **Median:** 2018

#### fiscal_period (string)
- **Null Rate:** 0.5% (2,516 rows — all 8-K filings)
- **Values:** FY (203,093), Q3 (127,006), Q2 (124,986), Q1 (89,797)
- **Note:** No Q4 — SEC uses FY for Q4 filings

#### form (string)
- **Null Rate:** 0%
- **Values:** 10-Q (61.9%), 10-K (35.0%), 8-K (2.2%), 10-K/A (0.6%), 10-Q/A (0.3%)

#### filed_date (date)
- **Null Rate:** 0%
- **Range:** 2009-07-22 to 2026-03-13

#### frame (string)
- **Null Rate:** 59.0% (322,964 rows) — expected, SEC only includes frame for calendar-year-aligned facts

#### ingested_at (timestamptz)
- **Null Rate:** 0%
- **Cardinality:** 20 distinct (one per CIK — batch ingest)

#### source_url / source_method / load_date
- All 0% null, all consistent

### Edge Cases for DQ Thresholds

| Observation | Count | Percentage | Recommendation |
|-------------|-------|------------|----------------|
| start_date IS NULL | 214,231 | 39.1% | NOT a violation — instant-type facts. Do not add a completeness rule for this field. |
| frame IS NULL | 322,964 | 59.0% | NOT a violation — SEC behavior. Do not add a completeness rule. |
| fiscal_year IS NULL | 2,516 | 0.5% | NOT a violation — 8-K filings. Do not add a completeness rule. |
| filed_date < end_date | 72 | 0.013% | P1 at 99% — NT filings and preliminary filings |
| label IS NULL | 2,437 | 0.4% | P2 at 99% — minor but worth tracking |
| val < 0 | 64,097 | 11.7% | NOT a violation — legitimate financial negatives |
| val = 0 | 14,964 | 2.7% | NOT a violation — legitimate zeros |
| Unit case inconsistency | ~450 | 0.08% | P3 informational — `segment` vs `Segment`, `years` vs `Year` |

### Anomalies

| Field | Type | Count | Severity | Details |
|-------|------|-------|----------|---------|
| unit | Case inconsistency | ~450 | Low | `segment`/`Segment` (406 total), `Year`/`years` (91 total) |
| label/description | Co-null | 2,437 | Low | Same rows missing both — likely concepts without XBRL labels |

### Recommendations for @dq-rule-writer

1. **Do NOT add null checks for start_date, frame, fiscal_year, fiscal_period** — high null rates are by design, not data quality issues
2. **Do NOT add "val >= 0" rules** — 11.7% of values are legitimately negative
3. **Consider P3 rule for unit case inconsistency** — `segment` vs `Segment` suggests source inconsistency
4. **Consider P2 rule for label/description completeness** — 99.6% populated, 0.4% missing
5. **Existing RAW-CF-005 (no future filed_date) is correct** — 0 violations
6. **Existing RAW-CF-007 (≥100 facts per CIK) is well-calibrated** — minimum is 17,446 facts
