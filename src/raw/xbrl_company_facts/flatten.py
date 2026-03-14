"""Pure flattening logic: nested XBRL Company Facts JSON → flat dicts.

No I/O, no side effects. Does NOT add pipeline metadata (ingested_at,
source_url, source_method) — the orchestrator adds those.
"""

from __future__ import annotations


def flatten_company_facts(data: dict) -> list[dict]:
    """Flatten a SEC EDGAR Company Facts JSON response into one dict per fact.

    Walks: data.facts → taxonomy → concept → units → unit → observations.
    """
    cik = data["cik"]
    entity_name = data["entityName"]
    rows: list[dict] = []

    facts = data.get("facts", {})
    for taxonomy, concepts in facts.items():
        for concept_name, concept_data in concepts.items():
            label = concept_data.get("label")
            description = concept_data.get("description")

            units = concept_data.get("units", {})
            for unit_name, observations in units.items():
                for obs in observations:
                    rows.append({
                        "cik": cik,
                        "entity_name": entity_name,
                        "taxonomy": taxonomy,
                        "concept": concept_name,
                        "label": label,
                        "description": description,
                        "unit": unit_name,
                        "start_date": obs.get("start"),
                        "end_date": obs["end"],
                        "val": float(obs["val"]),
                        "accession_number": obs["accn"],
                        "fiscal_year": obs.get("fy"),
                        "fiscal_period": obs.get("fp"),
                        "form": obs["form"],
                        "filed_date": obs["filed"],
                        "frame": obs.get("frame"),
                    })

    return rows
