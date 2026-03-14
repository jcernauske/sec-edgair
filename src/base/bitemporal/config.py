"""Configuration for bitemporal query module.

Read-only module — no new Iceberg tables. Operates on existing base.financial_facts.
"""

from src.base.financial_facts_model.config import (
    CATALOG_PATH,
    NAMESPACE,
    FINANCIAL_FACTS_TABLE,
    SUPERSESSION_GRAIN,
    WAREHOUSE_PATH,
)

# Re-export for local use
__all__ = [
    "CATALOG_PATH",
    "FINANCIAL_FACTS_TABLE",
    "NAMESPACE",
    "SUPERSESSION_GRAIN",
    "WAREHOUSE_PATH",
]

# Agent identity
AGENT_ID = "@bitemporal-schema"
