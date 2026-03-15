"""Split the project glossary into standard tier glossaries.

Extracts sec-edgar and xbrl-taxonomy terms into glossaries/standards/,
and updates governance/business-glossary.json with tier metadata.
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def make_standard_glossary(name, tier, authority, version, description, terms_list, id_prefix):
    """Build a standard glossary file from extracted terms."""
    upstream_terms = []
    for i, t in enumerate(terms_list, 1):
        upstream = {
            "term_id": f"{id_prefix}-{i:03d}",
            "project_term_id": t["term_id"],
            "term": t["term"],
            "definition": t["definition"],
            "source_reference": t.get("source_reference"),
            "synonyms": t.get("synonyms", []),
            "category": t.get("category"),
            "is_cde": t.get("is_cde", False),
            "is_pii": t.get("is_pii", False),
        }
        if t.get("cde_rationale"):
            upstream["cde_rationale"] = t["cde_rationale"]
        upstream_terms.append(upstream)

    return {
        "glossary_metadata": {
            "name": name,
            "tier": tier,
            "authority": authority,
            "version": version,
            "description": description,
            "term_count": len(upstream_terms),
        },
        "terms": upstream_terms,
    }


def main():
    glossary_path = PROJECT_ROOT / "governance" / "business-glossary.json"
    with open(glossary_path) as f:
        glossary = json.load(f)

    terms = glossary["terms"]

    sec_terms = [t for t in terms if t["source"] == "sec-edgar"]
    xbrl_terms = [t for t in terms if t["source"] == "xbrl-taxonomy"]
    proj_terms = [t for t in terms if t["source"] == "project-specific"]

    print(f"Source distribution: {len(sec_terms)} sec-edgar, {len(xbrl_terms)} xbrl-taxonomy, {len(proj_terms)} project-specific")

    # Build standard glossaries
    sec_glossary = make_standard_glossary(
        name="sec-edgar",
        tier=1,
        authority="U.S. Securities and Exchange Commission",
        version="2024",
        description="SEC EDGAR filing types, entity identifiers, and regulatory concepts",
        terms_list=sec_terms,
        id_prefix="ST-SEC",
    )

    xbrl_glossary = make_standard_glossary(
        name="xbrl-us-gaap",
        tier=1,
        authority="Financial Accounting Standards Board (FASB)",
        version="2024",
        description="US GAAP XBRL Taxonomy - authoritative financial reporting concepts",
        terms_list=xbrl_terms,
        id_prefix="ST-XBRL",
    )

    # Write standard glossary files
    standards_dir = PROJECT_ROOT / "glossaries" / "standards"
    standards_dir.mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "glossaries" / "domains").mkdir(parents=True, exist_ok=True)

    with open(standards_dir / "sec-edgar.json", "w") as f:
        json.dump(sec_glossary, f, indent=2)
        f.write("\n")
    print(f"Wrote {len(sec_terms)} terms to glossaries/standards/sec-edgar.json")

    with open(standards_dir / "xbrl-us-gaap.json", "w") as f:
        json.dump(xbrl_glossary, f, indent=2)
        f.write("\n")
    print(f"Wrote {len(xbrl_terms)} terms to glossaries/standards/xbrl-us-gaap.json")

    # Build BT-ID to upstream-ID mapping
    bt_to_upstream = {}
    for t in sec_glossary["terms"]:
        bt_to_upstream[t["project_term_id"]] = t["term_id"]
    for t in xbrl_glossary["terms"]:
        bt_to_upstream[t["project_term_id"]] = t["term_id"]

    # Update project glossary with tier info
    for term in terms:
        if term["source"] in ("sec-edgar", "xbrl-taxonomy"):
            term["source_tier"] = 1
            term["upstream_term_id"] = bt_to_upstream.get(term["term_id"])
            term["read_only"] = True
        elif term["source"] == "project-specific":
            term["source_tier"] = 3
            term["upstream_term_id"] = None
            term["read_only"] = False

    # Update metadata
    glossary["glossary_metadata"]["version"] = "3.0"
    glossary["glossary_metadata"]["inherited_from"] = [
        {"glossary": "sec-edgar", "tier": 1, "terms_inherited": len(sec_terms)},
        {"glossary": "xbrl-us-gaap", "tier": 1, "terms_inherited": len(xbrl_terms)},
    ]

    with open(glossary_path, "w") as f:
        json.dump(glossary, f, indent=2)
        f.write("\n")
    print(f"Updated project glossary: {len(terms)} terms with source_tier, upstream_term_id, read_only")


if __name__ == "__main__":
    main()
