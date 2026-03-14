"""Core entity resolution logic.

Reads raw.xbrl_company_facts, groups by CIK, extracts entity names,
and proposes mappings with confidence scores.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.infra.iceberg_setup import get_catalog, read_with_duckdb

from .config import KNOWN_ENTITIES


def resolve_entities(
    *,
    raw_warehouse_path: str | Path,
    catalog_path: str | Path,
) -> list[dict]:
    """Read raw.xbrl_company_facts and propose entity mappings.

    Groups facts by CIK, extracts the most common entity name per CIK,
    and matches against KNOWN_ENTITIES for confidence scoring.

    Returns a list of proposed mapping dicts.
    """
    catalog = get_catalog(raw_warehouse_path, catalog_path)
    table = catalog.load_table("raw.xbrl_company_facts")
    rows = read_with_duckdb(table)

    # Group by CIK, collect entity names
    cik_names: dict[int, list[str]] = {}
    for row in rows:
        cik = row["cik"]
        name = row["entity_name"]
        if cik not in cik_names:
            cik_names[cik] = []
        cik_names[cik].append(name)

    now = datetime.now(timezone.utc)
    proposals = []

    for idx, (cik, names) in enumerate(sorted(cik_names.items()), start=1):
        # Most common name as the raw entity name
        raw_name = max(set(names), key=names.count)
        mapping_id = f"ER-{idx:03d}"

        if cik in KNOWN_ENTITIES:
            meta = KNOWN_ENTITIES[cik]
            proposals.append({
                "mapping_id": mapping_id,
                "cik": cik,
                "canonical_name": meta["canonical_name"],
                "raw_entity_name": raw_name,
                "ticker": meta.get("ticker"),
                "sic_code": meta.get("sic_code"),
                "fiscal_year_end": meta.get("fiscal_year_end"),
                "confidence": 1.0,
                "resolution_method": "exact_cik_match",
                "status": "pending",
                "resolved_by": "@entity-resolver",
                "approved_by": None,
                "resolved_at": now.isoformat(),
                "approved_at": None,
                "reasoning": f"CIK {cik} directly matched in KNOWN_ENTITIES. "
                             f"Raw name '{raw_name}' mapped to canonical '{meta['canonical_name']}'.",
                "evidence": json.dumps({
                    "source": "KNOWN_ENTITIES config",
                    "cik": cik,
                    "raw_name": raw_name,
                    "name_occurrences": len(names),
                    "unique_names": list(set(names)),
                }),
            })
        else:
            # Unknown CIK — lower confidence, fuzzy match
            proposals.append({
                "mapping_id": mapping_id,
                "cik": cik,
                "canonical_name": _normalize_name(raw_name),
                "raw_entity_name": raw_name,
                "ticker": None,
                "sic_code": None,
                "fiscal_year_end": None,
                "confidence": 0.5,
                "resolution_method": "fuzzy_name_normalize",
                "status": "pending",
                "resolved_by": "@entity-resolver",
                "approved_by": None,
                "resolved_at": now.isoformat(),
                "approved_at": None,
                "reasoning": f"CIK {cik} not found in KNOWN_ENTITIES. "
                             f"Name normalized from '{raw_name}' via title-case heuristic.",
                "evidence": json.dumps({
                    "source": "fuzzy_name_normalize",
                    "cik": cik,
                    "raw_name": raw_name,
                    "name_occurrences": len(names),
                    "unique_names": list(set(names)),
                }),
            })

    return proposals


def resolve_entities_from_records(records: list[dict]) -> list[dict]:
    """Resolve entities from a list of raw fact records (for testing without Iceberg).

    Same logic as resolve_entities but takes records directly instead of reading
    from an Iceberg table.
    """
    cik_names: dict[int, list[str]] = {}
    for row in records:
        cik = row["cik"]
        name = row["entity_name"]
        if cik not in cik_names:
            cik_names[cik] = []
        cik_names[cik].append(name)

    now = datetime.now(timezone.utc)
    proposals = []

    for idx, (cik, names) in enumerate(sorted(cik_names.items()), start=1):
        raw_name = max(set(names), key=names.count)
        mapping_id = f"ER-{idx:03d}"

        if cik in KNOWN_ENTITIES:
            meta = KNOWN_ENTITIES[cik]
            proposals.append({
                "mapping_id": mapping_id,
                "cik": cik,
                "canonical_name": meta["canonical_name"],
                "raw_entity_name": raw_name,
                "ticker": meta.get("ticker"),
                "sic_code": meta.get("sic_code"),
                "fiscal_year_end": meta.get("fiscal_year_end"),
                "confidence": 1.0,
                "resolution_method": "exact_cik_match",
                "status": "pending",
                "resolved_by": "@entity-resolver",
                "approved_by": None,
                "resolved_at": now.isoformat(),
                "approved_at": None,
                "reasoning": f"CIK {cik} directly matched in KNOWN_ENTITIES. "
                             f"Raw name '{raw_name}' mapped to canonical '{meta['canonical_name']}'.",
                "evidence": json.dumps({
                    "source": "KNOWN_ENTITIES config",
                    "cik": cik,
                    "raw_name": raw_name,
                    "name_occurrences": len(names),
                    "unique_names": list(set(names)),
                }),
            })
        else:
            proposals.append({
                "mapping_id": mapping_id,
                "cik": cik,
                "canonical_name": _normalize_name(raw_name),
                "raw_entity_name": raw_name,
                "ticker": None,
                "sic_code": None,
                "fiscal_year_end": None,
                "confidence": 0.5,
                "resolution_method": "fuzzy_name_normalize",
                "status": "pending",
                "resolved_by": "@entity-resolver",
                "approved_by": None,
                "resolved_at": now.isoformat(),
                "approved_at": None,
                "reasoning": f"CIK {cik} not found in KNOWN_ENTITIES. "
                             f"Name normalized from '{raw_name}' via title-case heuristic.",
                "evidence": json.dumps({
                    "source": "fuzzy_name_normalize",
                    "cik": cik,
                    "raw_name": raw_name,
                    "name_occurrences": len(names),
                    "unique_names": list(set(names)),
                }),
            })

    return proposals


def _normalize_name(name: str) -> str:
    """Basic name normalization: title case, strip extra whitespace."""
    return " ".join(name.strip().title().split())
