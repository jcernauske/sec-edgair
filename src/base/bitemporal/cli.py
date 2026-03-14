"""CLI for bitemporal query, validation, and snapshot management.

Usage:
    python -m src.base.bitemporal.cli query --cik 320193 --concept Assets
    python -m src.base.bitemporal.cli as-known-on --date 2024-11-01
    python -m src.base.bitemporal.cli history --cik 320193 --concept Assets --end-date 2023-12-31
    python -m src.base.bitemporal.cli snapshots
    python -m src.base.bitemporal.cli validate
"""

from __future__ import annotations

import argparse
import datetime

from .config import CATALOG_PATH, FINANCIAL_FACTS_TABLE, NAMESPACE, WAREHOUSE_PATH


def _load_facts(args: argparse.Namespace) -> list[dict]:
    """Load current facts from Iceberg."""
    from src.infra.iceberg_setup import get_catalog, read_with_duckdb

    warehouse = args.warehouse or str(WAREHOUSE_PATH)
    catalog_path = args.catalog or str(CATALOG_PATH)
    catalog = get_catalog(warehouse, catalog_path)
    table = catalog.load_table(f"{NAMESPACE}.{FINANCIAL_FACTS_TABLE}")
    return read_with_duckdb(table)


def _load_table(args: argparse.Namespace):
    """Load the Iceberg table object."""
    from src.infra.iceberg_setup import get_catalog

    warehouse = args.warehouse or str(WAREHOUSE_PATH)
    catalog_path = args.catalog or str(CATALOG_PATH)
    catalog = get_catalog(warehouse, catalog_path)
    return catalog.load_table(f"{NAMESPACE}.{FINANCIAL_FACTS_TABLE}")


def cmd_query(args: argparse.Namespace) -> None:
    """Query current (non-superseded) facts."""
    from .queries import current_facts

    facts = _load_facts(args)
    result = current_facts(
        facts,
        cik=args.cik,
        concept=args.concept,
    )

    print(f"Current facts: {len(result)}")
    for f in result[:20]:
        print(f"  {f.get('canonical_name', f.get('cik'))}: "
              f"{f.get('concept')} = {f.get('val'):,.2f} {f.get('unit')} "
              f"({f.get('start_date')} to {f.get('end_date')})")

    if len(result) > 20:
        print(f"  ... and {len(result) - 20} more")


def cmd_as_known_on(args: argparse.Namespace) -> None:
    """Show facts as known on a specific date."""
    from .queries import as_known_on

    facts = _load_facts(args)
    date = datetime.date.fromisoformat(args.date)
    result = as_known_on(facts, date)

    print(f"Facts as known on {date}: {len(result)}")
    for f in result[:20]:
        print(f"  {f.get('canonical_name', f.get('cik'))}: "
              f"{f.get('concept')} = {f.get('val'):,.2f} {f.get('unit')} "
              f"(filed {f.get('filed_date')})")

    if len(result) > 20:
        print(f"  ... and {len(result) - 20} more")


def cmd_history(args: argparse.Namespace) -> None:
    """Show all versions of a fact across amendments."""
    from .queries import fact_history

    facts = _load_facts(args)
    start = datetime.date.fromisoformat(args.start_date) if args.start_date else None
    end = datetime.date.fromisoformat(args.end_date)

    if start is None:
        # Default: look for any start_date
        from .queries import current_facts
        current = current_facts(facts, cik=args.cik, concept=args.concept)
        matching = [f for f in current if f.get("end_date") == end]
        if matching:
            start = matching[0].get("start_date")
        if start is None:
            print("No matching facts found. Specify --start-date.")
            return

    result = fact_history(facts, args.cik, args.concept, start, end, args.unit)

    print(f"History for CIK {args.cik}, {args.concept} ({start} to {end}):")
    for f in result:
        status = "SUPERSEDED" if f.get("is_superseded") else "CURRENT"
        print(f"  [{status}] val={f.get('val'):,.2f} filed={f.get('filed_date')} "
              f"accession={f.get('accession_number')}")

    if not result:
        print("  No history found.")


def cmd_snapshots(args: argparse.Namespace) -> None:
    """List Iceberg snapshots with labels."""
    from .snapshot_registry import get_labeled_snapshots

    table = _load_table(args)
    snapshots = get_labeled_snapshots(table)

    print(f"Snapshots for {NAMESPACE}.{FINANCIAL_FACTS_TABLE}: {len(snapshots)}")
    for s in snapshots:
        print(f"  [{s['sequence']}] {s['label']}")
        print(f"       ID: {s['snapshot_id']}")
        print(f"       Time: {s['timestamp_iso']}")
        if s.get("parent_snapshot_id"):
            print(f"       Parent: {s['parent_snapshot_id']}")


def cmd_validate(args: argparse.Namespace) -> None:
    """Run all temporal DQ rules against current data."""
    from .validation import run_all_validations

    facts = _load_facts(args)
    results = run_all_validations(facts)

    passed = sum(1 for r in results if r["passed"])
    total = len(results)

    print(f"Temporal DQ Validation: {passed}/{total} rules passed")
    print()

    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  [{status}] {r['rule_id']}: {r['message']}")

    if passed < total:
        print(f"\nWARNING: {total - passed} rule(s) failed")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="bitemporal",
        description="Bitemporal query and validation CLI for SEC EDGAIR",
    )
    parser.add_argument("--warehouse", help="Path to Iceberg warehouse")
    parser.add_argument("--catalog", help="Path to catalog DB")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # query
    query_parser = subparsers.add_parser("query", help="Query current facts")
    query_parser.add_argument("--cik", type=int, help="Filter by CIK")
    query_parser.add_argument("--concept", help="Filter by concept name")

    # as-known-on
    ako_parser = subparsers.add_parser("as-known-on", help="Facts as known on a date")
    ako_parser.add_argument("--date", required=True, help="As-of date (YYYY-MM-DD)")

    # history
    hist_parser = subparsers.add_parser("history", help="Fact amendment history")
    hist_parser.add_argument("--cik", type=int, required=True, help="CIK")
    hist_parser.add_argument("--concept", required=True, help="Concept name")
    hist_parser.add_argument("--start-date", help="Period start (YYYY-MM-DD)")
    hist_parser.add_argument("--end-date", required=True, help="Period end (YYYY-MM-DD)")
    hist_parser.add_argument("--unit", default="USD", help="Unit (default: USD)")

    # snapshots
    subparsers.add_parser("snapshots", help="List Iceberg snapshots")

    # validate
    subparsers.add_parser("validate", help="Run temporal DQ rules")

    args = parser.parse_args(argv)

    commands = {
        "query": cmd_query,
        "as-known-on": cmd_as_known_on,
        "history": cmd_history,
        "snapshots": cmd_snapshots,
        "validate": cmd_validate,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
