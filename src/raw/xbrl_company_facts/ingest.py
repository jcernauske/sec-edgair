"""Orchestrator: fetch → flatten → write to Iceberg.

One snapshot per company for natural lineage boundaries.
"""

from __future__ import annotations

import datetime
from pathlib import Path

from pyiceberg.exceptions import NamespaceAlreadyExistsError, TableAlreadyExistsError

from src.infra.iceberg_setup import append_data, get_catalog, read_with_duckdb
from src.raw.xbrl_company_facts.config import (
    API_URL_TEMPLATE,
    BULK_ZIP_URL,
    CATALOG_PATH,
    DEFAULT_CIKS,
    JSON_CACHE_DIR,
    USER_AGENT,
    WAREHOUSE_PATH,
)
from src.raw.xbrl_company_facts.fetch_api import fetch_company_facts
from src.raw.xbrl_company_facts.fetch_bulk import fetch_bulk_company_facts
from src.raw.xbrl_company_facts.flatten import flatten_company_facts
from src.raw.xbrl_company_facts.schema import XBRL_COMPANY_FACTS_SCHEMA

TABLE_NAMESPACE = "raw"
TABLE_NAME = "xbrl_company_facts"


def _get_or_create_table(warehouse_path: Path, catalog_path: Path):
    """Get or create the raw.xbrl_company_facts Iceberg table."""
    catalog = get_catalog(warehouse_path, catalog_path)

    try:
        catalog.create_namespace(TABLE_NAMESPACE)
    except NamespaceAlreadyExistsError:
        pass

    identifier = f"{TABLE_NAMESPACE}.{TABLE_NAME}"
    try:
        return catalog.create_table(identifier, schema=XBRL_COMPANY_FACTS_SCHEMA)
    except TableAlreadyExistsError:
        return catalog.load_table(identifier)


def ingest_company_facts(
    ciks: dict[int, str] | None = None,
    method: str = "api",
    cache_dir: Path | None = None,
    warehouse_path: Path | None = None,
    catalog_path: Path | None = None,
    user_agent: str | None = None,
) -> dict[int, dict]:
    """Ingest XBRL Company Facts for the given CIKs.

    Args:
        ciks: {CIK: company_name} dict. Defaults to DEFAULT_CIKS.
        method: "api" for per-company fetch, "bulk_zip" for bulk download.
        cache_dir: JSON cache directory. Defaults to config.
        warehouse_path: Iceberg warehouse path. Defaults to config.
        catalog_path: Iceberg catalog path. Defaults to config.
        user_agent: HTTP User-Agent. Defaults to config.

    Returns:
        {cik: {"rows": N, "snapshot_id": X}} summary per company.
    """
    ciks = ciks or DEFAULT_CIKS
    cache_dir = cache_dir or JSON_CACHE_DIR
    warehouse_path = warehouse_path or WAREHOUSE_PATH
    catalog_path = catalog_path or CATALOG_PATH
    user_agent = user_agent or USER_AGENT

    table = _get_or_create_table(warehouse_path, catalog_path)

    # Build set of existing fact grains for dedup
    # Dedup on (cik, accession_number, concept, unit, end_date) — NOT on CIK alone,
    # because new filings for existing CIKs must flow through in incremental loads
    existing_grains = set()
    try:
        existing = read_with_duckdb(table)
        existing_grains = {
            (r["cik"], r["accession_number"], r["concept"], r["unit"], str(r.get("end_date", "")))
            for r in existing
        }
    except Exception:
        pass

    # Fetch raw JSON
    if method == "api":
        raw_data = {
            cik: fetch_company_facts(cik, cache_dir, user_agent) for cik in ciks
        }
    elif method == "bulk_zip":
        raw_data = fetch_bulk_company_facts(list(ciks.keys()), cache_dir, user_agent)
    else:
        raise ValueError(f"Unknown method: {method!r}. Use 'api' or 'bulk_zip'.")

    # Flatten and write one snapshot per company
    results: dict[int, dict] = {}
    for cik in ciks:
        data = raw_data[cik]
        flat_rows = flatten_company_facts(data)

        ingested_at = datetime.datetime.now(tz=datetime.timezone.utc)
        if method == "api":
            source_url = API_URL_TEMPLATE.format(cik_padded=f"{cik:010d}")
        else:
            source_url = BULK_ZIP_URL

        load_date = ingested_at.date()
        for row in flat_rows:
            row["ingested_at"] = ingested_at
            row["source_url"] = source_url
            row["source_method"] = method
            row["load_date"] = load_date

        # Dedup: skip facts already in the table
        original_count = len(flat_rows)
        flat_rows = [
            r for r in flat_rows
            if (r["cik"], r["accession_number"], r["concept"], r["unit"], str(r.get("end_date", "")))
            not in existing_grains
        ]
        skipped = original_count - len(flat_rows)

        if not flat_rows:
            results[cik] = {"rows": 0, "skipped": skipped}
            continue

        if skipped:
            print(f"  CIK {cik}: {skipped} existing facts skipped, {len(flat_rows)} new facts")

        snapshot_id = append_data(table, flat_rows)
        results[cik] = {"rows": len(flat_rows), "snapshot_id": snapshot_id, "skipped": skipped}

    total_skipped = sum(r.get("skipped", 0) for r in results.values())
    total_new = sum(r.get("rows", 0) for r in results.values())
    if total_skipped:
        print(f"Dedup summary: {total_new} new facts ingested, {total_skipped} duplicates skipped")

    return results
