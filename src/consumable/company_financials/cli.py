"""CLI for consumable company financials pipeline.

Usage:
    python -m src.consumable.company_financials.cli build     # build the table
    python -m src.consumable.company_financials.cli status    # show table stats
    python -m src.consumable.company_financials.cli coverage  # business term x company matrix
    python -m src.consumable.company_financials.cli all       # build + status + coverage
"""

from __future__ import annotations

import argparse

from .build import build_company_financials
from .config import CATALOG_PATH, WAREHOUSE_PATH
from .promote import promote_company_financials


def cmd_build(args: argparse.Namespace) -> None:
    """Build consumable.company_financials from base tables."""
    warehouse = args.warehouse or str(WAREHOUSE_PATH)
    catalog = args.catalog or str(CATALOG_PATH)

    print("Building company financials...")
    records = build_company_financials(warehouse_path=warehouse, catalog_path=catalog)
    print(f"  Built {len(records)} records")

    result = promote_company_financials(
        records, warehouse_path=warehouse, catalog_path=catalog,
    )

    print(f"  Promoted: {result['promoted']}")
    if result.get("skipped_duplicates"):
        print(f"  Skipped duplicates: {result['skipped_duplicates']}")
    if result.get("snapshot_id"):
        print(f"  Snapshot ID: {result['snapshot_id']}")

    # Post-write DQ validation
    from src.infra.dq_runner import validate_after_write
    print("Running DQ validation...")
    dq_result = validate_after_write("consumable-company-financials")
    print(f"  DQ: {dq_result['rules_passed']}/{dq_result['rules_total']} rules passing")
    print(f"  P0 gate: {'PASS' if dq_result['p0_passed'] else 'FAIL'}")


def cmd_status(args: argparse.Namespace) -> None:
    """Show table statistics."""
    from src.infra.iceberg_setup import get_catalog, read_with_duckdb

    warehouse = args.warehouse or str(WAREHOUSE_PATH)
    catalog_path = args.catalog or str(CATALOG_PATH)
    catalog = get_catalog(warehouse, catalog_path)

    try:
        table = catalog.load_table("consumable.company_financials")
        rows = read_with_duckdb(table)
    except Exception:
        print("Company Financials: not yet created")
        return

    if not rows:
        print("Company Financials: 0 rows")
        return

    companies = set()
    terms = set()
    years = set()
    for r in rows:
        companies.add(r.get("cik"))
        terms.add(r.get("business_term_id"))
        fy = r.get("fiscal_year")
        if fy is not None:
            years.add(fy)

    print(f"Company Financials: {len(rows)} rows")
    print(f"  Companies: {len(companies)}")
    print(f"  Business terms: {len(terms)}")
    if years:
        print(f"  Fiscal year range: {min(years)} - {max(years)}")


def cmd_coverage(args: argparse.Namespace) -> None:
    """Print business term x company coverage matrix."""
    from src.infra.iceberg_setup import get_catalog, read_with_duckdb

    warehouse = args.warehouse or str(WAREHOUSE_PATH)
    catalog_path = args.catalog or str(CATALOG_PATH)
    catalog = get_catalog(warehouse, catalog_path)

    try:
        table = catalog.load_table("consumable.company_financials")
        rows = read_with_duckdb(table)
    except Exception:
        print("Company Financials: not yet created")
        return

    if not rows:
        print("No data for coverage matrix")
        return

    # Build coverage: business_term -> set of companies
    coverage: dict[str, set] = {}
    for r in rows:
        bt = r.get("business_term", "Unknown")
        bt_id = r.get("business_term_id", "")
        label = f"{bt_id}: {bt}"
        coverage.setdefault(label, set()).add(r.get("cik"))

    print("Coverage Matrix (business term -> company count):")
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
        prog="company-financials",
        description="Consumable company financials CLI for SEC EDGAIR",
    )
    parser.add_argument("--warehouse", help="Path to Iceberg warehouse")
    parser.add_argument("--catalog", help="Path to catalog DB")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("build", help="Build company_financials table")
    subparsers.add_parser("status", help="Show table stats")
    subparsers.add_parser("coverage", help="Show business term x company coverage")
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
