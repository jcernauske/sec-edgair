"""CLI for consumable period-over-period growth pipeline.

Usage:
    python -m src.consumable.period_over_period.cli build     # build the table
    python -m src.consumable.period_over_period.cli status    # show table stats
    python -m src.consumable.period_over_period.cli coverage  # growth type x business term matrix
    python -m src.consumable.period_over_period.cli all       # build + status + coverage
"""

from __future__ import annotations

import argparse

from .build import build_period_over_period
from .config import CATALOG_PATH, WAREHOUSE_PATH
from .promote import promote_period_over_period


def cmd_build(args: argparse.Namespace) -> None:
    """Build consumable.period_over_period from company_financials."""
    warehouse = args.warehouse or str(WAREHOUSE_PATH)
    catalog = args.catalog or str(CATALOG_PATH)

    print("Building period-over-period growth...")
    records = build_period_over_period(warehouse_path=warehouse, catalog_path=catalog)
    print(f"  Built {len(records)} records")

    result = promote_period_over_period(
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
    dq_result = validate_after_write("consumable-period-over-period")
    print(f"  DQ: {dq_result['rules_passed']}/{dq_result['rules_total']} rules passing")
    print(f"  P0 gate: {'PASS' if dq_result['p0_passed'] else 'FAIL'}")


def cmd_status(args: argparse.Namespace) -> None:
    """Show table statistics."""
    from src.infra.iceberg_setup import get_catalog, read_with_duckdb

    warehouse = args.warehouse or str(WAREHOUSE_PATH)
    catalog_path = args.catalog or str(CATALOG_PATH)
    catalog = get_catalog(warehouse, catalog_path)

    try:
        table = catalog.load_table("consumable.period_over_period")
        rows = read_with_duckdb(table)
    except Exception:
        print("Period-Over-Period: not yet created")
        return

    if not rows:
        print("Period-Over-Period: 0 rows")
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

    print(f"Period-Over-Period: {len(rows)} rows")
    print(f"  Companies: {len(companies)}")
    print(f"  Business terms: {len(terms)}")
    if years:
        print(f"  Fiscal year range: {min(years)} - {max(years)}")

    # Per growth type breakdown
    type_counts: dict[str, int] = {}
    for r in rows:
        gt = r.get("growth_type", "Unknown")
        type_counts[gt] = type_counts.get(gt, 0) + 1
    print("  Per growth type:")
    for name in sorted(type_counts):
        print(f"    {name}: {type_counts[name]} rows")


def cmd_coverage(args: argparse.Namespace) -> None:
    """Print growth type x business term coverage matrix."""
    from src.infra.iceberg_setup import get_catalog, read_with_duckdb

    warehouse = args.warehouse or str(WAREHOUSE_PATH)
    catalog_path = args.catalog or str(CATALOG_PATH)
    catalog = get_catalog(warehouse, catalog_path)

    try:
        table = catalog.load_table("consumable.period_over_period")
        rows = read_with_duckdb(table)
    except Exception:
        print("Period-Over-Period: not yet created")
        return

    if not rows:
        print("No data for coverage matrix")
        return

    # Build coverage: (growth_type, business_term) -> set of companies
    coverage: dict[tuple, set] = {}
    for r in rows:
        label = (r.get("growth_type", ""), r.get("business_term_id", ""))
        coverage.setdefault(label, set()).add(r.get("cik"))

    # Print by growth type
    growth_types = sorted(set(k[0] for k in coverage))
    for gt in growth_types:
        print(f"\n{gt}:")
        print("-" * 55)
        for (g, bt), companies in sorted(coverage.items()):
            if g != gt:
                continue
            count = len(companies)
            bar = "#" * count
            print(f"  {bt:<12s} {count:>2d}  {bar}")


def cmd_all(args: argparse.Namespace) -> None:
    """Run build, then status, then coverage."""
    cmd_build(args)
    print()
    cmd_status(args)
    print()
    cmd_coverage(args)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="period-over-period",
        description="Consumable period-over-period growth CLI for SEC EDGAIR",
    )
    parser.add_argument("--warehouse", help="Path to Iceberg warehouse")
    parser.add_argument("--catalog", help="Path to catalog DB")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("build", help="Build period_over_period table")
    subparsers.add_parser("status", help="Show table stats")
    subparsers.add_parser("coverage", help="Show growth type x business term coverage")
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
