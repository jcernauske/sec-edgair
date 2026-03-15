"""Merge CDE catalog into business glossary with is_cde/is_pii flags.

One-time migration script for infra-governance-model-alignment spec.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def main():
    glossary_path = PROJECT_ROOT / "governance" / "business-glossary.json"
    cde_path = PROJECT_ROOT / "governance" / "cde-catalog.json"

    with open(glossary_path) as f:
        glossary = json.load(f)
    with open(cde_path) as f:
        cde_catalog = json.load(f)

    # CDE → BT mapping (complete translation table)
    CDE_TO_BT = {
        "CDE-001": "BT-001", "CDE-002": "BT-002", "CDE-003": "BT-003",
        "CDE-004": "BT-006", "CDE-005": "BT-005", "CDE-006": "BT-026",
        "CDE-007": "BT-024", "CDE-008": "BT-027", "CDE-009": "BT-028",
        "CDE-010": "BT-029", "CDE-011": "BT-030", "CDE-012": "BT-031",
        "CDE-013": "BT-032", "CDE-014": "BT-033", "CDE-015": "BT-022",
        "CDE-016": "BT-034", "CDE-017": "BT-035", "CDE-018": "BT-036",
        "CDE-019": "BT-023", "CDE-020": "BT-037", "CDE-021": "BT-038",
        "CDE-022": "BT-039", "CDE-023": "BT-040", "CDE-024": "BT-041",
        "CDE-025": "BT-042", "CDE-026": "BT-043", "CDE-027": "BT-044",
        "CDE-028": "BT-045", "CDE-029": "BT-046", "CDE-030": "BT-047",
        "CDE-031": "BT-048",
    }

    # CDEs that map to already-existing BTs
    EXISTING_BT_FOR_CDE = {
        "CDE-001": "BT-001", "CDE-002": "BT-002", "CDE-003": "BT-003",
        "CDE-004": "BT-006", "CDE-005": "BT-005", "CDE-007": "BT-024",
        "CDE-015": "BT-022", "CDE-019": "BT-023",
    }

    cde_by_id = {c["cde_id"]: c for c in cde_catalog["cdes"]}

    CDE_RATIONALE = {
        "Entity Identification": "Core entity identifier critical for cross-system joins and audit trails.",
        "Filing Identification": "Primary filing identifier critical for source traceability and regulatory audit.",
        "Filing Metadata": "Filing temporal metadata critical for amendment detection and regulatory timeline analysis.",
        "Balance Sheet": "Core balance sheet metric critical for financial health assessment and cross-company comparison.",
        "Income Statement": "Core income statement metric critical for profitability analysis and cross-company comparison.",
        "Cash Flow": "Core cash flow metric critical for liquidity analysis and cross-company comparison.",
        "Per-Share": "Core per-share metric critical for investor valuation and cross-company comparison.",
        "Other": "Core financial metric critical for comprehensive financial analysis.",
    }

    # Step 1: Add is_cde, is_pii flags to ALL existing terms
    cde_bt_ids = set(EXISTING_BT_FOR_CDE.values())
    for term in glossary["terms"]:
        tid = term["term_id"]
        is_cde = tid in cde_bt_ids
        term["is_cde"] = is_cde
        term["is_pii"] = False
        if is_cde:
            for cde_id, bt_id in EXISTING_BT_FOR_CDE.items():
                if bt_id == tid:
                    cat = cde_by_id[cde_id]["category"]
                    term["cde_rationale"] = CDE_RATIONALE.get(cat, "Critical data element.")
                    break
        else:
            term["cde_rationale"] = None
        term["pii_rationale"] = None
        # Remove old cde_reference field
        term.pop("cde_reference", None)

    # Step 2: Update BT-013 "Canonical CDE" → "Financial Business Term"
    for term in glossary["terms"]:
        if term["term_id"] == "BT-013":
            term["term"] = "Financial Business Term"
            term["definition"] = (
                "One of the standardized financial metric terms in the business glossary "
                "(e.g., Revenue, Total Assets, Net Income) that serve as the common language "
                "for cross-company financial comparison. XBRL concepts map to these terms "
                "through the tag normalization process. Terms critical to operations are "
                "flagged with is_cde=true."
            )
            term["synonyms"] = ["Financial Metric", "Canonical Financial Term"]
            break

    # Step 3: Create new BTs for CDEs that don't have existing BTs
    existing_ids = {t["term_id"] for t in glossary["terms"]}
    new_terms = []
    for cde_id, bt_id in sorted(CDE_TO_BT.items()):
        if bt_id in existing_ids:
            continue
        cde = cde_by_id[cde_id]
        cat = cde["category"]
        is_entity = cat in ("Entity Identification", "Filing Identification", "Filing Metadata")
        new_term = {
            "term_id": bt_id,
            "term": cde["name"],
            "definition": cde["definition"],
            "source": "project-specific" if is_entity else "xbrl-taxonomy",
            "source_reference": "docs/specs/base-entity-resolution.md" if is_entity else "us-gaap XBRL Taxonomy",
            "synonyms": [],
            "related_terms": [],
            "category": "entity" if is_entity else "financial",
            "owner": "Data Engineering" if is_entity else "Finance",
            "status": "approved",
            "approved_by": "human:jeff" if is_entity else "auto (authoritative external standard)",
            "approved_at": "2026-03-14T00:00:00Z",
            "is_cde": True,
            "is_pii": False,
            "cde_rationale": CDE_RATIONALE.get(cat, "Critical data element."),
            "pii_rationale": None,
            "used_in_models": ["base-xbrl-tag-normalization", "base-financial-facts-model"],
        }
        new_terms.append(new_term)

    glossary["terms"].extend(new_terms)
    glossary["glossary_metadata"]["term_count"] = len(glossary["terms"])
    glossary["glossary_metadata"]["last_updated"] = "2026-03-14"
    glossary["glossary_metadata"]["version"] = "2.0"

    with open(glossary_path, "w") as f:
        json.dump(glossary, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Updated glossary: {len(glossary['terms'])} terms")
    print(f"New terms added: {len(new_terms)}")
    is_cde_count = len([t for t in glossary["terms"] if t["is_cde"]])
    print(f"is_cde=true: {is_cde_count}")

    # Print BT_TO_CDE reverse mapping for reference
    print("\n=== BT_TO_CDE reverse mapping ===")
    bt_to_cde = {v: k for k, v in CDE_TO_BT.items()}
    for bt_id in sorted(bt_to_cde):
        cde_id = bt_to_cde[bt_id]
        print(f"  {bt_id} <- {cde_id} ({cde_by_id[cde_id]['name']})")


if __name__ == "__main__":
    main()
