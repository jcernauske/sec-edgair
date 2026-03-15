"""Shared utilities for consumable zone modules.

Common lookups and derivations that multiple consumable tables need.
"""

from __future__ import annotations

from src.infra.iceberg_setup import get_catalog, read_with_duckdb


# SIC-to-Sector: static mapping from SIC codes to human-readable sectors
# Derived from the 20 companies in scope
SIC_TO_SECTOR: dict[str, str] = {
    "2086": "Consumer Staples",        # Coca-Cola
    "2834": "Healthcare",              # Pfizer, J&J
    "2841": "Consumer Staples",        # P&G
    "2911": "Energy",                  # Exxon
    "3571": "Technology",              # Apple
    "3674": "Technology",              # Intel
    "3711": "Consumer Discretionary",  # Tesla
    "3721": "Industrials",             # Boeing
    "5331": "Consumer Staples",        # Walmart
    "5961": "Consumer Discretionary",  # Amazon
    "6020": "Financials",              # JPMorgan
    "6211": "Financials",              # Goldman Sachs
    "6324": "Healthcare",              # UnitedHealth
    "6331": "Financials",              # Berkshire
    "7370": "Technology",              # Meta
    "7372": "Technology",              # Microsoft, Alphabet
    "7389": "Financials",              # Visa
    "7841": "Communication Services",  # Netflix
}


def build_sector_lookup(
    entity_mappings: list[dict] | None = None,
    warehouse_path=None,
    catalog_path=None,
) -> dict[int, str]:
    """Build CIK -> sector lookup from entity_mappings.

    Reads entity_mappings from Iceberg if not provided.
    """
    if entity_mappings is None:
        from src.config import CATALOG_PATH as DEFAULT_CP
        from pathlib import Path

        wh = Path(warehouse_path) if warehouse_path else Path(__file__).resolve().parents[2] / "data" / "raw" / "iceberg_warehouse"
        cp = Path(catalog_path) if catalog_path else DEFAULT_CP
        catalog = get_catalog(wh, cp)
        em_table = catalog.load_table("base.entity_mappings")
        entity_mappings = read_with_duckdb(em_table)

    lookup: dict[int, str] = {}
    for em in entity_mappings:
        cik = em.get("cik")
        sic = em.get("sic_code")
        if cik is not None and sic is not None:
            lookup[cik] = SIC_TO_SECTOR.get(sic, "Unknown")
    return lookup
