"""Add consumable.financial_ratios to data dictionary."""
import json
from pathlib import Path

dict_path = Path("governance/data-dictionary.json")

with open(dict_path) as f:
    d = json.load(f)

d["tables"].append({
    "table_name": "consumable.financial_ratios",
    "zone": "consumable",
    "description": "Cross-company financial ratio comparison table. One row per (company, ratio, fiscal year, fiscal period). Computes 7 financial ratios from consumable.company_financials by joining numerator and denominator business terms. Preserves both component values for audit transparency.",
    "spec_reference": "docs/specs/consumable-financial-ratios.md",
    "row_grain": "One computed ratio value for one company in one fiscal period: (cik, ratio_id, fiscal_year, fiscal_period).",
    "fields": [
        {"field_name": "record_id", "data_type": "STRING", "nullable": False, "definition": "Deterministic SHA-256 hash of grain fields (cik, ratio_id, fiscal_year, fiscal_period), truncated to 16 chars. Primary key.", "dq_rules": ["CONS-FR-001"], "last_updated": "2026-03-14", "updated_by": "@doc-generator"},
        {"field_name": "cik", "data_type": "INTEGER", "nullable": False, "definition": "SEC Central Index Key from consumable.company_financials.", "business_term_reference": "BT-001", "dq_rules": ["CONS-FR-003"], "last_updated": "2026-03-14", "updated_by": "@doc-generator"},
        {"field_name": "entity_id", "data_type": "STRING", "nullable": False, "definition": "FK to entity_mappings.mapping_id.", "last_updated": "2026-03-14", "updated_by": "@doc-generator"},
        {"field_name": "ticker", "data_type": "STRING", "nullable": True, "definition": "Stock ticker symbol (denormalized).", "last_updated": "2026-03-14", "updated_by": "@doc-generator"},
        {"field_name": "canonical_name", "data_type": "STRING", "nullable": False, "definition": "Normalized company name (denormalized).", "business_term_reference": "BT-005", "last_updated": "2026-03-14", "updated_by": "@doc-generator"},
        {"field_name": "sector", "data_type": "STRING", "nullable": False, "definition": "Industry sector (denormalized from company_financials).", "business_term_reference": "BT-049", "last_updated": "2026-03-14", "updated_by": "@doc-generator"},
        {"field_name": "ratio_id", "data_type": "STRING", "nullable": False, "definition": "Ratio definition ID: RATIO-001 (Gross Margin), RATIO-002 (Operating Margin), RATIO-003 (Net Margin), RATIO-004 (Debt-to-Equity), RATIO-005 (R&D Intensity), RATIO-006 (SGA Ratio), RATIO-007 (CapEx-to-Revenue).", "business_term_reference": "BT-051", "dq_rules": ["CONS-FR-002", "CONS-FR-008"], "last_updated": "2026-03-14", "updated_by": "@doc-generator"},
        {"field_name": "ratio_name", "data_type": "STRING", "nullable": False, "definition": "Human-readable ratio name (e.g., 'Net Margin', 'Debt-to-Equity').", "business_term_reference": "BT-051", "last_updated": "2026-03-14", "updated_by": "@doc-generator"},
        {"field_name": "ratio_value", "data_type": "DOUBLE", "nullable": False, "definition": "Computed ratio: numerator_val / denominator_val. For RATIO-007, abs(numerator) is used.", "dq_rules": ["CONS-FR-004", "CONS-FR-009"], "last_updated": "2026-03-14", "updated_by": "@doc-generator"},
        {"field_name": "numerator_bt_id", "data_type": "STRING", "nullable": False, "definition": "Business term ID of the numerator component (e.g., BT-023 for Net Income).", "dq_rules": ["CONS-FR-006"], "last_updated": "2026-03-14", "updated_by": "@doc-generator"},
        {"field_name": "numerator_bt_name", "data_type": "STRING", "nullable": False, "definition": "Human-readable name of the numerator business term.", "last_updated": "2026-03-14", "updated_by": "@doc-generator"},
        {"field_name": "numerator_val", "data_type": "DOUBLE", "nullable": False, "definition": "Value of the numerator from company_financials. Original value preserved (not abs'd).", "last_updated": "2026-03-14", "updated_by": "@doc-generator"},
        {"field_name": "denominator_bt_id", "data_type": "STRING", "nullable": False, "definition": "Business term ID of the denominator component (e.g., BT-022 for Revenue).", "dq_rules": ["CONS-FR-006", "CONS-FR-010"], "last_updated": "2026-03-14", "updated_by": "@doc-generator"},
        {"field_name": "denominator_bt_name", "data_type": "STRING", "nullable": False, "definition": "Human-readable name of the denominator business term.", "last_updated": "2026-03-14", "updated_by": "@doc-generator"},
        {"field_name": "denominator_val", "data_type": "DOUBLE", "nullable": False, "definition": "Value of the denominator from company_financials. Never zero.", "dq_rules": ["CONS-FR-005"], "last_updated": "2026-03-14", "updated_by": "@doc-generator"},
        {"field_name": "fiscal_year", "data_type": "INTEGER", "nullable": False, "definition": "Fiscal year of the reporting period.", "last_updated": "2026-03-14", "updated_by": "@doc-generator"},
        {"field_name": "fiscal_period", "data_type": "STRING", "nullable": False, "definition": "Fiscal period: FY, Q1, Q2, Q3.", "last_updated": "2026-03-14", "updated_by": "@doc-generator"},
        {"field_name": "fiscal_year_end", "data_type": "STRING", "nullable": True, "definition": "Fiscal year end in MMDD format (denormalized).", "last_updated": "2026-03-14", "updated_by": "@doc-generator"},
        {"field_name": "period_end_date", "data_type": "DATE", "nullable": False, "definition": "End date of the reporting period.", "last_updated": "2026-03-14", "updated_by": "@doc-generator"},
        {"field_name": "calendar_year", "data_type": "INTEGER", "nullable": False, "definition": "Calendar year of period_end_date.", "last_updated": "2026-03-14", "updated_by": "@doc-generator"},
        {"field_name": "calendar_quarter", "data_type": "INTEGER", "nullable": False, "definition": "Calendar quarter (1-4) of period_end_date.", "last_updated": "2026-03-14", "updated_by": "@doc-generator"},
        {"field_name": "companies_reporting", "data_type": "INTEGER", "nullable": False, "definition": "Count of distinct companies with this ratio for this fiscal_period type.", "business_term_reference": "BT-050", "dq_rules": ["CONS-FR-007"], "last_updated": "2026-03-14", "updated_by": "@doc-generator"},
        {"field_name": "promoted_at", "data_type": "TIMESTAMPTZ", "nullable": False, "definition": "UTC timestamp when this row was written to the consumable zone.", "last_updated": "2026-03-14", "updated_by": "@doc-generator"},
        {"field_name": "load_date", "data_type": "DATE", "nullable": False, "definition": "System date for pipeline auditing.", "last_updated": "2026-03-14", "updated_by": "@doc-generator"},
    ],
})

with open(dict_path, "w") as f:
    json.dump(d, f, indent=2)
    f.write("\n")

print(f"Data dictionary updated: {len(d['tables'])} tables")
