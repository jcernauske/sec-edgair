"""Add BT-051 (Financial Ratio) to business glossary."""
import json
from pathlib import Path

glossary_path = Path("governance/business-glossary.json")

with open(glossary_path) as f:
    g = json.load(f)

g["terms"].append({
    "term_id": "BT-051",
    "term": "Financial Ratio",
    "definition": "A computed metric expressing the relationship between two financial values (numerator / denominator). Used to normalize for company size and enable cross-company comparison. Examples: Gross Margin, Net Margin, Debt-to-Equity.",
    "source": "project-specific",
    "source_reference": "docs/specs/consumable-financial-ratios.md",
    "synonyms": ["Ratio", "Financial Metric Ratio"],
    "related_terms": ["BT-013"],
    "category": "financial",
    "owner": "Finance / Data Governance",
    "status": "approved",
    "approved_by": "auto (REQUIRE_HUMAN_APPROVAL gate)",
    "approved_at": "2026-03-14T16:00:00Z",
    "used_in_models": ["consumable-financial-ratios"],
    "is_cde": False,
    "is_pii": False,
    "cde_rationale": "Derived metric, not a primary data element.",
    "pii_rationale": None,
})

g["glossary_metadata"]["term_count"] = len(g["terms"])
g["glossary_metadata"]["last_updated"] = "2026-03-14"

with open(glossary_path, "w") as f:
    json.dump(g, f, indent=2)
    f.write("\n")

print(f"Glossary updated: {len(g['terms'])} terms")
