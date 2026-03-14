"""CLI for XBRL tag normalization: normalize, status, approve, reject, coverage.

Usage:
    python -m src.base.xbrl_tag_normalization.cli normalize
    python -m src.base.xbrl_tag_normalization.cli status
    python -m src.base.xbrl_tag_normalization.cli approve
    python -m src.base.xbrl_tag_normalization.cli approve TN-0001 TN-0002
    python -m src.base.xbrl_tag_normalization.cli reject TN-0042 --reason "Wrong CDE"
    python -m src.base.xbrl_tag_normalization.cli coverage
"""

from __future__ import annotations

import argparse
import sys

from src.base.entity_resolution.staging import (
    apply_gate,
    approve_proposals,
    get_pending,
    reject_proposals,
    write_staging,
)

from .config import (
    ARCHIVE_DIR,
    CATALOG_PATH,
    CONFIDENCE_FLOOR,
    REQUIRE_HUMAN_APPROVAL,
    STAGING_FILE,
    WAREHOUSE_PATH,
)
from .normalize import normalize_concepts
from .promote import promote_approved


def cmd_normalize(args: argparse.Namespace) -> None:
    """Scan raw zone for us-gaap concepts, classify, and stage."""
    raw_warehouse = args.raw_warehouse or str(WAREHOUSE_PATH).replace("base", "raw")

    proposals = normalize_concepts(
        raw_warehouse_path=raw_warehouse,
        catalog_path=args.catalog or str(CATALOG_PATH),
    )

    staging_path = args.staging or str(STAGING_FILE)

    # Separate tier 1+2 (need approval) from tier 3 (bypass gate)
    tier12 = [p for p in proposals if p["tier"] in (1, 2)]
    tier3 = [p for p in proposals if p["tier"] == 3]

    # Write all proposals to staging
    write_staging(proposals, staging_path)

    gate = apply_gate(
        tier12,
        require_human_approval=REQUIRE_HUMAN_APPROVAL,
        confidence_floor=CONFIDENCE_FLOOR,
    )

    print(f"Scanned {len(proposals)} us-gaap concepts:")
    print(f"  Tier 1 (exact match):   {len([p for p in proposals if p['tier'] == 1])}")
    print(f"  Tier 2 (prefix/pattern): {len([p for p in proposals if p['tier'] == 2])}")
    print(f"  Tier 3 (unmapped):      {len(tier3)}")
    print(f"\nStaged to: {staging_path}")
    print(f"  Tier 1+2 auto-promotable: {len(gate['auto_promote'])}")
    print(f"  Tier 1+2 needs review:    {len(gate['needs_review'])}")
    print(f"  Tier 3 bypasses gate:     {len(tier3)}")

    if gate["gate_action"] == "stop":
        print("\nHuman review required for Tier 1+2. Run:")
        print("  python -m src.base.xbrl_tag_normalization.cli status")
        print("  python -m src.base.xbrl_tag_normalization.cli approve")
    else:
        print("\nAll Tier 1+2 can be auto-promoted.")
        approved = approve_proposals(staging_path, actor="auto")
        result = promote_approved(
            staging_path=staging_path,
            warehouse_path=args.warehouse or str(WAREHOUSE_PATH),
            catalog_path=args.catalog or str(CATALOG_PATH),
            archive_dir=str(ARCHIVE_DIR),
        )
        print(f"Auto-promoted {result['promoted']} mappings to Iceberg.")


def cmd_status(args: argparse.Namespace) -> None:
    """Show pending Tier 1+2 proposals."""
    staging_path = args.staging or str(STAGING_FILE)
    pending = get_pending(staging_path)

    if not pending:
        print("No pending proposals.")
        return

    print(f"\n{'ID':<10} {'Concept':<55} {'CDE':<25} {'Tier':<6} {'Conf':<8} {'Method'}")
    print("-" * 120)
    for p in pending:
        cde = p.get("canonical_cde") or "(unmapped)"
        print(
            f"{p['mapping_id']:<10} {p['concept']:<55} {cde:<25} "
            f"{p['tier']:<6} {p['confidence']:<8.2f} {p['mapping_method']}"
        )
    print(f"\n{len(pending)} pending mapping(s)")


def cmd_approve(args: argparse.Namespace) -> None:
    """Approve mappings and promote to Iceberg."""
    staging_path = args.staging or str(STAGING_FILE)
    mapping_ids = args.mapping_ids if args.mapping_ids else None
    actor = args.actor or "human:jeff"

    approved = approve_proposals(staging_path, mapping_ids, actor=actor)

    if not approved:
        print("No pending mappings to approve.")
        return

    print(f"Approved {len(approved)} mapping(s):")
    for a in approved:
        print(f"  {a['mapping_id']} — {a['concept']} → {a.get('canonical_cde', 'N/A')}")

    result = promote_approved(
        staging_path=staging_path,
        warehouse_path=args.warehouse or str(WAREHOUSE_PATH),
        catalog_path=args.catalog or str(CATALOG_PATH),
        archive_dir=str(ARCHIVE_DIR),
    )

    print(f"\nPromoted {result['promoted']} to Iceberg.")
    print(f"  Approved: {result.get('approved_count', 0)}")
    print(f"  Unmapped: {result.get('unmapped_count', 0)}")
    print(f"  Audit entries: {result.get('audit_entries')}")


def cmd_reject(args: argparse.Namespace) -> None:
    """Reject specific mappings with a reason."""
    staging_path = args.staging or str(STAGING_FILE)

    if not args.mapping_ids:
        print("Error: must specify mapping IDs to reject.", file=sys.stderr)
        sys.exit(1)

    if not args.reason:
        print("Error: --reason is required for rejections.", file=sys.stderr)
        sys.exit(1)

    actor = args.actor or "human:jeff"
    rejected = reject_proposals(
        staging_path, args.mapping_ids, reason=args.reason, actor=actor,
    )

    if not rejected:
        print("No pending mappings matched the given IDs.")
        return

    print(f"Rejected {len(rejected)} mapping(s):")
    for r in rejected:
        print(f"  {r['mapping_id']} — {r['concept']} (reason: {args.reason})")


def cmd_coverage(args: argparse.Namespace) -> None:
    """Show coverage statistics."""
    from src.base.entity_resolution.staging import read_staging

    staging_path = args.staging or str(STAGING_FILE)
    proposals = read_staging(staging_path)

    if not proposals:
        print("No proposals found. Run 'normalize' first.")
        return

    total = len(proposals)
    tier_counts = {1: 0, 2: 0, 3: 0}
    for p in proposals:
        tier_counts[p["tier"]] = tier_counts.get(p["tier"], 0) + 1

    mapped = tier_counts[1] + tier_counts[2]

    print(f"Coverage Report")
    print(f"{'='*40}")
    print(f"Total concepts:     {total}")
    print(f"Tier 1 (exact):     {tier_counts[1]}")
    print(f"Tier 2 (prefix/pat): {tier_counts[2]}")
    print(f"Tier 3 (unmapped):  {tier_counts[3]}")
    print(f"Mapped concepts:    {mapped}/{total} ({mapped/total*100:.1f}%)")

    # Count by CDE
    cde_counts: dict[str, int] = {}
    for p in proposals:
        cde = p.get("canonical_cde")
        if cde:
            cde_counts[cde] = cde_counts.get(cde, 0) + 1

    if cde_counts:
        print(f"\n{'CDE':<35} {'Concepts Mapped'}")
        print("-" * 50)
        for cde, count in sorted(cde_counts.items(), key=lambda x: -x[1]):
            print(f"{cde:<35} {count}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="xbrl-tag-normalization",
        description="XBRL tag normalization CLI for SEC EDGAIR",
    )
    parser.add_argument("--staging", help="Path to staging JSON file")
    parser.add_argument("--warehouse", help="Path to Iceberg warehouse")
    parser.add_argument("--catalog", help="Path to catalog DB")
    parser.add_argument("--actor", help="Actor name for audit trail")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # normalize
    normalize_parser = subparsers.add_parser("normalize", help="Scan and classify concepts")
    normalize_parser.add_argument("--raw-warehouse", help="Path to raw zone warehouse")

    # status
    subparsers.add_parser("status", help="Show pending proposals")

    # approve
    approve_parser = subparsers.add_parser("approve", help="Approve pending mappings")
    approve_parser.add_argument("mapping_ids", nargs="*", help="Specific mapping IDs (or all if empty)")

    # reject
    reject_parser = subparsers.add_parser("reject", help="Reject specific mappings")
    reject_parser.add_argument("mapping_ids", nargs="+", help="Mapping IDs to reject")
    reject_parser.add_argument("--reason", required=True, help="Rejection reason")

    # coverage
    subparsers.add_parser("coverage", help="Show coverage statistics")

    args = parser.parse_args(argv)

    commands = {
        "normalize": cmd_normalize,
        "status": cmd_status,
        "approve": cmd_approve,
        "reject": cmd_reject,
        "coverage": cmd_coverage,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
