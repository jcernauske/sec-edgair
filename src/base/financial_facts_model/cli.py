"""CLI for base financial facts model pipeline.

Usage:
    python -m src.base.financial_facts_model.cli model      # build financial_facts
    python -m src.base.financial_facts_model.cli calendar    # build fiscal_calendar
    python -m src.base.financial_facts_model.cli amendments  # detect amendments
    python -m src.base.financial_facts_model.cli status      # show table stats
    python -m src.base.financial_facts_model.cli all         # run everything
"""

from __future__ import annotations

import argparse

from .amendments import detect_amendments
from .config import CATALOG_PATH, WAREHOUSE_PATH
from .fiscal_calendar import build_fiscal_calendar
from .model import build_financial_facts
from .promote import (
    promote_amendment_tracking,
    promote_financial_facts,
    promote_fiscal_calendar,
)


def cmd_model(args: argparse.Namespace) -> None:
    """Build financial_facts table from raw + entity + concept data."""
    warehouse = args.warehouse or str(WAREHOUSE_PATH)
    catalog = args.catalog or str(CATALOG_PATH)

    print("Building financial facts...")
    facts = build_financial_facts(warehouse_path=warehouse, catalog_path=catalog)

    result = promote_financial_facts(facts, warehouse_path=warehouse, catalog_path=catalog)

    superseded = sum(1 for f in facts if f.get("is_superseded"))
    amendments = sum(1 for f in facts if f.get("is_amendment"))

    print(f"  Total facts: {result['promoted']}")
    print(f"  Superseded:  {superseded}")
    print(f"  Amendments:  {amendments}")
    print(f"  Snapshot ID: {result.get('snapshot_id')}")


def cmd_calendar(args: argparse.Namespace) -> None:
    """Build fiscal_calendar table from observed periods."""
    warehouse = args.warehouse or str(WAREHOUSE_PATH)
    catalog = args.catalog or str(CATALOG_PATH)

    print("Building fiscal calendar...")
    entries = build_fiscal_calendar(warehouse_path=warehouse, catalog_path=catalog)

    result = promote_fiscal_calendar(entries, warehouse_path=warehouse, catalog_path=catalog)

    annual = sum(1 for e in entries if e.get("is_annual"))
    quarterly = len(entries) - annual

    print(f"  Calendar entries: {result['promoted']}")
    print(f"  Annual periods:   {annual}")
    print(f"  Quarterly periods: {quarterly}")
    print(f"  Snapshot ID: {result.get('snapshot_id')}")


def cmd_amendments(args: argparse.Namespace) -> None:
    """Detect amendments from built financial facts."""
    warehouse = args.warehouse or str(WAREHOUSE_PATH)
    catalog = args.catalog or str(CATALOG_PATH)

    print("Detecting amendments...")
    facts = build_financial_facts(warehouse_path=warehouse, catalog_path=catalog)
    tracking = detect_amendments(facts)

    result = promote_amendment_tracking(tracking, warehouse_path=warehouse, catalog_path=catalog)

    print(f"  Amendment pairs: {result['promoted']}")
    if tracking:
        with_change = [t for t in tracking if t["val_change"] != 0]
        print(f"  With value change: {len(with_change)}")
    print(f"  Snapshot ID: {result.get('snapshot_id')}")


def cmd_status(args: argparse.Namespace) -> None:
    """Show table statistics."""
    from src.infra.iceberg_setup import get_catalog, read_with_duckdb

    warehouse = args.warehouse or str(WAREHOUSE_PATH)
    catalog_path = args.catalog or str(CATALOG_PATH)
    catalog = get_catalog(warehouse, catalog_path)

    tables = [
        ("base.financial_facts", "Financial Facts"),
        ("base.fiscal_calendar", "Fiscal Calendar"),
        ("base.amendment_tracking", "Amendment Tracking"),
    ]

    for table_id, label in tables:
        try:
            table = catalog.load_table(table_id)
            rows = read_with_duckdb(table)
            print(f"{label}: {len(rows)} rows")
        except Exception:
            print(f"{label}: not yet created")


def cmd_all(args: argparse.Namespace) -> None:
    """Run all steps: model, calendar, amendments."""
    cmd_model(args)
    print()
    cmd_calendar(args)
    print()
    cmd_amendments(args)
    print()
    cmd_status(args)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="financial-facts-model",
        description="Base financial facts model CLI for SEC EDGAIR",
    )
    parser.add_argument("--warehouse", help="Path to Iceberg warehouse")
    parser.add_argument("--catalog", help="Path to catalog DB")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("model", help="Build financial_facts table")
    subparsers.add_parser("calendar", help="Build fiscal_calendar table")
    subparsers.add_parser("amendments", help="Detect amendments")
    subparsers.add_parser("status", help="Show table stats")
    subparsers.add_parser("all", help="Run everything")

    args = parser.parse_args(argv)

    commands = {
        "model": cmd_model,
        "calendar": cmd_calendar,
        "amendments": cmd_amendments,
        "status": cmd_status,
        "all": cmd_all,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
