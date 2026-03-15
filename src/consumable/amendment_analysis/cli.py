"""CLI for consumable amendment analysis pipeline.

Usage:
    python -m src.consumable.amendment_analysis.cli build     # build the table
    python -m src.consumable.amendment_analysis.cli status    # show table stats
    python -m src.consumable.amendment_analysis.cli all       # build + status
"""

from __future__ import annotations

import argparse

from .build import build_amendment_analysis
from .config import CATALOG_PATH, WAREHOUSE_PATH
from .promote import promote_amendment_analysis


def cmd_build(args: argparse.Namespace) -> None:
    """Build consumable.amendment_analysis from amendment_tracking + company_financials."""
    warehouse = args.warehouse or str(WAREHOUSE_PATH)
    catalog = args.catalog or str(CATALOG_PATH)

    print("Building amendment analysis...")
    records = build_amendment_analysis(warehouse_path=warehouse, catalog_path=catalog)
    print(f"  Built {len(records)} records")

    result = promote_amendment_analysis(
        records, warehouse_path=warehouse, catalog_path=catalog,
    )

    print(f"  Promoted: {result['promoted']}")
    if result.get("skipped_duplicates"):
        print(f"  Skipped duplicates: {result['skipped_duplicates']}")
    if result.get("snapshot_id"):
        print(f"  Snapshot ID: {result['snapshot_id']}")


def cmd_status(args: argparse.Namespace) -> None:
    """Show table statistics."""
    from src.infra.iceberg_setup import get_catalog, read_with_duckdb

    warehouse = args.warehouse or str(WAREHOUSE_PATH)
    catalog_path = args.catalog or str(CATALOG_PATH)
    catalog = get_catalog(warehouse, catalog_path)

    try:
        table = catalog.load_table("consumable.amendment_analysis")
        rows = read_with_duckdb(table)
    except Exception:
        print("Amendment Analysis: not yet created")
        return

    if not rows:
        print("Amendment Analysis: 0 rows")
        return

    companies = set()
    years = set()
    total_amendments = 0
    for r in rows:
        companies.add(r.get("cik"))
        fy = r.get("fiscal_year")
        if fy is not None:
            years.add(fy)
        ac = r.get("amendment_count")
        if ac is not None:
            total_amendments += ac

    print(f"Amendment Analysis: {len(rows)} rows")
    print(f"  Companies: {len(companies)}")
    print(f"  Total amendments summarized: {total_amendments:,}")
    if years:
        print(f"  Fiscal year range: {min(years)} - {max(years)}")

    # Top amenders
    by_company: dict[str, int] = {}
    for r in rows:
        name = r.get("canonical_name", "Unknown")
        ac = r.get("amendment_count", 0)
        by_company[name] = by_company.get(name, 0) + ac

    print("  Top amenders:")
    for name, count in sorted(by_company.items(), key=lambda x: -x[1])[:5]:
        print(f"    {name}: {count:,}")


def cmd_all(args: argparse.Namespace) -> None:
    """Run build, then status."""
    cmd_build(args)
    print()
    cmd_status(args)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="amendment-analysis",
        description="Consumable amendment analysis CLI for SEC EDGAIR",
    )
    parser.add_argument("--warehouse", help="Path to Iceberg warehouse")
    parser.add_argument("--catalog", help="Path to catalog DB")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("build", help="Build amendment_analysis table")
    subparsers.add_parser("status", help="Show table stats")
    subparsers.add_parser("all", help="Run build + status")

    args = parser.parse_args(argv)

    commands = {
        "build": cmd_build,
        "status": cmd_status,
        "all": cmd_all,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
