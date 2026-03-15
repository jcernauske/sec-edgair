"""XBRL Company Facts ingestor — extends BaseIngestor.

Implements SEC EDGAR-specific fetch() and flatten().
The framework (BaseIngestor) handles Iceberg, dedup, and metadata.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pyiceberg.schema import Schema

from src.domain_loader import DomainHints, DomainManifest, SourceConfig, get_source, load_manifest
from src.raw.base_ingestor import BaseIngestor
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


class XBRLCompanyFactsIngestor(BaseIngestor):
    """SEC EDGAR XBRL Company Facts ingestor."""

    def get_schema(self) -> Schema:
        return XBRL_COMPANY_FACTS_SCHEMA

    def fetch(self, entities: dict, method: str, **kwargs) -> dict[Any, Any]:
        cache_dir = kwargs.get("cache_dir", self.source.cache_dir)
        user_agent = kwargs.get("user_agent", USER_AGENT)

        if method == "api":
            return {
                cik: fetch_company_facts(cik, cache_dir, user_agent)
                for cik in entities
            }
        elif method == "bulk_zip":
            return fetch_bulk_company_facts(
                list(entities.keys()), cache_dir, user_agent
            )
        else:
            raise ValueError(f"Unknown method: {method!r}. Use 'api' or 'bulk_zip'.")

    def flatten(self, raw_data: Any, entity_id: Any) -> list[dict]:
        return flatten_company_facts(raw_data)

    def get_source_url(self, entity_id: Any, method: str) -> str:
        if method == "api":
            return API_URL_TEMPLATE.format(cik_padded=f"{entity_id:010d}")
        return BULK_ZIP_URL


# --- Backwards-compatible function API ---


def ingest_company_facts(
    ciks: dict[int, str] | None = None,
    method: str = "api",
    cache_dir: Path | None = None,
    warehouse_path: Path | None = None,
    catalog_path: Path | None = None,
    user_agent: str | None = None,
) -> dict[int, dict]:
    """Ingest XBRL Company Facts for the given CIKs.

    Legacy API -- wraps XBRLCompanyFactsIngestor for backwards compatibility.
    All existing callers continue to work unchanged.
    """
    try:
        manifest = load_manifest()
        source = get_source(manifest, "xbrl_company_facts")
    except (FileNotFoundError, KeyError):
        # Fallback: create a minimal SourceConfig from hardcoded defaults
        source = SourceConfig(
            name="xbrl_company_facts",
            namespace="raw",
            table="xbrl_company_facts",
            fetch={},
            entities=DEFAULT_CIKS,
            dedup_grain=["cik", "accession_number", "concept", "unit", "end_date"],
            cache_dir=JSON_CACHE_DIR,
        )
        manifest = DomainManifest(
            name="sec-edgar",
            version="1.0",
            description="SEC EDGAR XBRL financial data",
            sources=[source],
            hints=DomainHints(),
        )

    ingestor = XBRLCompanyFactsIngestor(source, manifest)

    return ingestor.ingest(
        entities=ciks,
        method=method,
        warehouse_path=warehouse_path or WAREHOUSE_PATH,
        catalog_path=catalog_path or CATALOG_PATH,
        cache_dir=cache_dir or JSON_CACHE_DIR,
        user_agent=user_agent or USER_AGENT,
    )
