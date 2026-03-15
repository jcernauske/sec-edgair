"""CLI for base.conformed_facts pipeline.

Usage:
    python -m src.base.conformed_facts.cli build     # build + promote conformed_facts
    python -m src.base.conformed_facts.cli promote    # build + promote to Iceberg with DQ gate
    python -m src.base.conformed_facts.cli status     # show table stats
"""

from __future__ import annotations

import argparse
import logging

from .build import build_conformed_facts
from .config import CATALOG_PATH, WAREHOUSE_PATH
from .promote import promote_conformed_facts

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def cmd_build(args: argparse.Namespace) -> None:
    """Build and promote conformed_facts table."""
    warehouse = args.warehouse or str(WAREHOUSE_PATH)
    catalog = args.catalog or str(CATALOG_PATH)

    print("Building conformed facts...")
    records = build_conformed_facts(warehouse_path=warehouse, catalog_path=catalog)

    print(f"  Built {len(records)} conformed facts")

    # Stats
    sole = sum(1 for r in records if r["selection_reason"] == "sole_candidate")
    primary = sum(1 for r in records if r["selection_reason"] == "primary_concept")
    fallback = sum(1 for r in records if r["selection_reason"] == "tier_frequency_fallback")
    print(f"  Resolution: {sole} sole, {primary} primary_concept, {fallback} fallback")

    unique_ciks = len({r["cik"] for r in records})
    unique_bts = len({r["business_term_id"] for r in records})
    print(f"  Companies: {unique_ciks}, Business terms: {unique_bts}")


def cmd_promote(args: argparse.Namespace) -> None:
    """Build and promote conformed_facts to Iceberg with DQ gate."""
    warehouse = args.warehouse or str(WAREHOUSE_PATH)
    catalog = args.catalog or str(CATALOG_PATH)

    print("Building conformed facts...")
    records = build_conformed_facts(warehouse_path=warehouse, catalog_path=catalog)
    print(f"  Built {len(records)} conformed facts")

    print("Promoting to Iceberg...")
    result = promote_conformed_facts(
        records,
        warehouse_path=warehouse,
        catalog_path=catalog,
        validate=True,
    )

    print(f"  Promoted: {result['promoted']} rows")
    print(f"  Snapshot: {result.get('snapshot_id')}")
    if "dq_passed" in result:
        print(f"  DQ: {result['dq_passed']}/{result['dq_total']} rules passed")


def cmd_status(args: argparse.Namespace) -> None:
    """Show table statistics."""
    from src.infra.iceberg_setup import get_catalog, read_with_duckdb

    warehouse = args.warehouse or str(WAREHOUSE_PATH)
    catalog_path = args.catalog or str(CATALOG_PATH)
    catalog = get_catalog(warehouse, catalog_path)

    try:
        table = catalog.load_table("base.conformed_facts")
        rows = read_with_duckdb(table)
        print(f"Conformed Facts: {len(rows)} rows")

        unique_ciks = len({r["cik"] for r in rows})
        unique_bts = len({r["business_term_id"] for r in rows})
        print(f"  Companies: {unique_ciks}")
        print(f"  Business terms: {unique_bts}")

        reasons = {}
        for r in rows:
            reason = r.get("selection_reason", "unknown")
            reasons[reason] = reasons.get(reason, 0) + 1
        for reason, count in sorted(reasons.items()):
            print(f"  {reason}: {count}")
    except Exception:
        print("Conformed Facts: not yet created")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="conformed-facts",
        description="Base conformed facts CLI for SEC EDGAIR",
    )
    parser.add_argument("--warehouse", help="Path to Iceberg warehouse")
    parser.add_argument("--catalog", help="Path to catalog DB")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("build", help="Build conformed_facts (dry run, no promote)")
    subparsers.add_parser("promote", help="Build + promote conformed_facts to Iceberg")
    subparsers.add_parser("status", help="Show table stats")

    args = parser.parse_args(argv)

    commands = {
        "build": cmd_build,
        "promote": cmd_promote,
        "status": cmd_status,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
