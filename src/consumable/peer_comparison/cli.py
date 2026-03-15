"""CLI for consumable peer comparison pipeline.

Usage:
    python -m src.consumable.peer_comparison.cli build     # build the table
    python -m src.consumable.peer_comparison.cli status    # show table stats
    python -m src.consumable.peer_comparison.cli coverage  # sector x metric coverage matrix
    python -m src.consumable.peer_comparison.cli all       # build + status + coverage
"""

from __future__ import annotations

import argparse

from .build import build_peer_comparison
from .config import CATALOG_PATH, WAREHOUSE_PATH
from .promote import promote_peer_comparison


def cmd_build(args: argparse.Namespace) -> None:
    """Build consumable.peer_comparison from company_financials + financial_ratios."""
    warehouse = args.warehouse or str(WAREHOUSE_PATH)
    catalog = args.catalog or str(CATALOG_PATH)

    print("Building peer comparison...")
    records = build_peer_comparison(warehouse_path=warehouse, catalog_path=catalog)
    print(f"  Built {len(records)} records")

    result = promote_peer_comparison(
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
    dq_result = validate_after_write("consumable-peer-comparison")
    print(f"  DQ: {dq_result['rules_passed']}/{dq_result['rules_total']} rules passing")
    print(f"  P0 gate: {'PASS' if dq_result['p0_passed'] else 'FAIL'}")


def cmd_status(args: argparse.Namespace) -> None:
    """Show table statistics."""
    from src.infra.iceberg_setup import get_catalog, read_with_duckdb

    warehouse = args.warehouse or str(WAREHOUSE_PATH)
    catalog_path = args.catalog or str(CATALOG_PATH)
    catalog = get_catalog(warehouse, catalog_path)

    try:
        table = catalog.load_table("consumable.peer_comparison")
        rows = read_with_duckdb(table)
    except Exception:
        print("Peer Comparison: not yet created")
        return

    if not rows:
        print("Peer Comparison: 0 rows")
        return

    companies = set()
    sectors = set()
    metrics = set()
    sources = set()
    years = set()
    for r in rows:
        companies.add(r.get("cik"))
        sectors.add(r.get("sector"))
        metrics.add(r.get("metric_id"))
        sources.add(r.get("metric_source"))
        fy = r.get("fiscal_year")
        if fy is not None:
            years.add(fy)

    print(f"Peer Comparison: {len(rows)} rows")
    print(f"  Companies: {len(companies)}")
    print(f"  Sectors: {len(sectors)}")
    print(f"  Distinct metrics: {len(metrics)}")
    print(f"  Metric sources: {sorted(sources)}")
    if years:
        print(f"  Fiscal year range: {min(years)} - {max(years)}")

    # Per-source breakdown
    source_counts: dict[str, int] = {}
    for r in rows:
        src = r.get("metric_source", "Unknown")
        source_counts[src] = source_counts.get(src, 0) + 1
    print("  Per source:")
    for name in sorted(source_counts):
        print(f"    {name}: {source_counts[name]} rows")


def cmd_coverage(args: argparse.Namespace) -> None:
    """Print sector x metric coverage matrix."""
    from src.infra.iceberg_setup import get_catalog, read_with_duckdb

    warehouse = args.warehouse or str(WAREHOUSE_PATH)
    catalog_path = args.catalog or str(CATALOG_PATH)
    catalog = get_catalog(warehouse, catalog_path)

    try:
        table = catalog.load_table("consumable.peer_comparison")
        rows = read_with_duckdb(table)
    except Exception:
        print("Peer Comparison: not yet created")
        return

    if not rows:
        print("No data for coverage matrix")
        return

    # Build coverage: sector -> set of metric_ids
    coverage: dict[str, set] = {}
    for r in rows:
        sector = r.get("sector", "Unknown")
        coverage.setdefault(sector, set()).add(r.get("metric_id"))

    # Peer count per sector (from first row of each sector)
    peer_counts: dict[str, int] = {}
    for r in rows:
        sector = r.get("sector", "Unknown")
        if sector not in peer_counts:
            peer_counts[sector] = r.get("peer_count", 0)

    print("Coverage Matrix (sector -> metric count, peer count):")
    print("-" * 60)
    for sector in sorted(coverage):
        count = len(coverage[sector])
        peers = peer_counts.get(sector, 0)
        bar = "#" * count
        print(f"  {sector:<30s} {count:>3d} metrics  {peers:>2d} peers  {bar}")


def cmd_all(args: argparse.Namespace) -> None:
    """Run build, then status, then coverage."""
    cmd_build(args)
    print()
    cmd_status(args)
    print()
    cmd_coverage(args)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="peer-comparison",
        description="Consumable peer comparison CLI for SEC EDGAIR",
    )
    parser.add_argument("--warehouse", help="Path to Iceberg warehouse")
    parser.add_argument("--catalog", help="Path to catalog DB")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("build", help="Build peer_comparison table")
    subparsers.add_parser("status", help="Show table stats")
    subparsers.add_parser("coverage", help="Show sector x metric coverage")
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
