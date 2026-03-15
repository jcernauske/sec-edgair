"""CLI for consumable financial ratios pipeline.

Usage:
    python -m src.consumable.financial_ratios.cli build     # build the table
    python -m src.consumable.financial_ratios.cli status    # show table stats
    python -m src.consumable.financial_ratios.cli coverage  # ratio x company matrix
    python -m src.consumable.financial_ratios.cli all       # build + status + coverage
"""

from __future__ import annotations

import argparse

from .build import build_financial_ratios
from .config import CATALOG_PATH, WAREHOUSE_PATH
from .promote import promote_financial_ratios


def cmd_build(args: argparse.Namespace) -> None:
    """Build consumable.financial_ratios from company_financials."""
    warehouse = args.warehouse or str(WAREHOUSE_PATH)
    catalog = args.catalog or str(CATALOG_PATH)

    print("Building financial ratios...")
    records = build_financial_ratios(warehouse_path=warehouse, catalog_path=catalog)
    print(f"  Built {len(records)} records")

    result = promote_financial_ratios(
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
        table = catalog.load_table("consumable.financial_ratios")
        rows = read_with_duckdb(table)
    except Exception:
        print("Financial Ratios: not yet created")
        return

    if not rows:
        print("Financial Ratios: 0 rows")
        return

    companies = set()
    ratios = set()
    years = set()
    for r in rows:
        companies.add(r.get("cik"))
        ratios.add(r.get("ratio_id"))
        fy = r.get("fiscal_year")
        if fy is not None:
            years.add(fy)

    print(f"Financial Ratios: {len(rows)} rows")
    print(f"  Companies: {len(companies)}")
    print(f"  Ratios: {len(ratios)}")
    if years:
        print(f"  Fiscal year range: {min(years)} - {max(years)}")

    # Per-ratio breakdown
    ratio_counts: dict[str, int] = {}
    for r in rows:
        rid = r.get("ratio_name", r.get("ratio_id", "Unknown"))
        ratio_counts[rid] = ratio_counts.get(rid, 0) + 1
    print("  Per ratio:")
    for name in sorted(ratio_counts):
        print(f"    {name}: {ratio_counts[name]} rows")


def cmd_coverage(args: argparse.Namespace) -> None:
    """Print ratio x company coverage matrix."""
    from src.infra.iceberg_setup import get_catalog, read_with_duckdb

    warehouse = args.warehouse or str(WAREHOUSE_PATH)
    catalog_path = args.catalog or str(CATALOG_PATH)
    catalog = get_catalog(warehouse, catalog_path)

    try:
        table = catalog.load_table("consumable.financial_ratios")
        rows = read_with_duckdb(table)
    except Exception:
        print("Financial Ratios: not yet created")
        return

    if not rows:
        print("No data for coverage matrix")
        return

    # Build coverage: ratio -> set of companies
    coverage: dict[str, set] = {}
    for r in rows:
        label = f"{r.get('ratio_id', '')}: {r.get('ratio_name', 'Unknown')}"
        coverage.setdefault(label, set()).add(r.get("cik"))

    print("Coverage Matrix (ratio -> company count):")
    print("-" * 55)
    for label in sorted(coverage):
        count = len(coverage[label])
        bar = "#" * count
        print(f"  {label:<40s} {count:>2d}  {bar}")


def cmd_all(args: argparse.Namespace) -> None:
    """Run build, then status, then coverage."""
    cmd_build(args)
    print()
    cmd_status(args)
    print()
    cmd_coverage(args)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="financial-ratios",
        description="Consumable financial ratios CLI for SEC EDGAIR",
    )
    parser.add_argument("--warehouse", help="Path to Iceberg warehouse")
    parser.add_argument("--catalog", help="Path to catalog DB")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("build", help="Build financial_ratios table")
    subparsers.add_parser("status", help="Show table stats")
    subparsers.add_parser("coverage", help="Show ratio x company coverage")
    subparsers.add_parser("all", help="Run build + status + coverage")

    args = parser.parse_args(argv)

    commands = {
        "build": cmd_build,
        "status": cmd_status,
        "coverage": cmd_coverage,
        "all": cmd_all,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
