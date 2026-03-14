## PII Scan Report: raw.xbrl_company_facts
**Date:** 2026-03-14
**Agent:** @pii-scanner
**Records Scanned:** 104,810
**PII Instances Found:** 0

### Findings
| # | Field | PII Category | Sensitivity | Confidence | Sample (Redacted) | Recommended Action |
|---|-------|-------------|-------------|------------|-------------------|-------------------|
| — | — | — | — | — | — | No PII detected |

### Summary by Sensitivity
| Level | Count | Fields Affected |
|-------|-------|----------------|
| Public (Level 1) | 19 fields | All — SEC EDGAR data is public by law |
| Internal (Level 2) | 0 | — |
| Confidential (Level 3) | 0 | — |
| Restricted (Level 4) | 0 | — |

### Fields Analyzed

| Field | PII Risk | Finding |
|-------|----------|---------|
| cik | None | Numeric company identifier, not personally identifiable |
| entity_name | Low — checked | Company names (e.g., "Apple Inc.", "MICROSOFT CORPORATION"), not personal names. Verified: 3 distinct values, all are public company legal names. |
| taxonomy | None | XBRL taxonomy identifiers (us-gaap, dei, invest, srt) |
| concept | None | XBRL concept names (financial metrics) |
| label | None | Human-readable labels for XBRL concepts |
| description | Low — checked | XBRL concept descriptions. Scanned for embedded personal names — none found. Max length 1,668 chars, all are standardized taxonomy descriptions. |
| unit | None | Measurement units (USD, shares, pure) |
| start_date | None | Reporting period dates |
| end_date | None | Reporting period dates |
| val | None | Financial values (numeric) |
| accession_number | None | SEC filing identifiers (format: XXXXXXXXXX-YY-ZZZZZZ) |
| fiscal_year | None | Year integers (2009-2026) |
| fiscal_period | None | Period codes (FY, Q1, Q2, Q3) |
| form | None | SEC form types (10-K, 10-Q, 8-K, 10-Q/A, 10-K/A) |
| filed_date | None | SEC filing dates |
| frame | None | XBRL frame identifiers (CY2010, CY2023Q1I, etc.) |
| ingested_at | None | Pipeline-generated timestamps |
| source_url | None | SEC EDGAR API URLs |
| source_method | None | Literal "api" — pipeline metadata |

### False Positive Candidates
| Field | Detected As | Why It's Likely False | Recommendation |
|-------|-------------|----------------------|----------------|
| entity_name | Potential personal name | Values are all company legal names (verified against SEC EDGAR entity registry). "JPMorgan Chase & Co" contains a personal name historically but is a company name in this context. | No action — company name, not PII |

### Recommendations
- **No PII handling required** for raw.xbrl_company_facts
- All 19 fields classified as **Public (Level 1)** — SEC EDGAR data is public record
- When the pipeline expands to include officer/director data from other SEC filings (e.g., DEF 14A proxy statements), PII scanning will find personal names and addresses. This scan establishes the baseline and proves the pattern.
- The entity_name field contains company legal names only. If future data sources introduce individual names (e.g., signing officers), those fields should be scanned separately.
