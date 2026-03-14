"""CLI for entity resolution: resolve, status, approve, reject.

Usage:
    python -m src.base.entity_resolution.cli resolve
    python -m src.base.entity_resolution.cli status
    python -m src.base.entity_resolution.cli approve
    python -m src.base.entity_resolution.cli approve ER-001 ER-002
    python -m src.base.entity_resolution.cli reject ER-003 --reason "Wrong entity"
"""

from __future__ import annotations

import argparse
import sys

from .config import (
    ARCHIVE_DIR,
    CATALOG_PATH,
    CONFIDENCE_FLOOR,
    REQUIRE_HUMAN_APPROVAL,
    STAGING_FILE,
    WAREHOUSE_PATH,
)
from .promote import promote_approved
from .resolve import resolve_entities
from .staging import (
    apply_gate,
    approve_proposals,
    get_pending,
    reject_proposals,
    write_staging,
)


def cmd_resolve(args: argparse.Namespace) -> None:
    """Resolve entities from raw zone and write proposals to staging."""
    from .config import CATALOG_PATH as raw_catalog

    raw_warehouse = args.raw_warehouse or str(WAREHOUSE_PATH).replace("base", "raw")

    proposals = resolve_entities(
        raw_warehouse_path=raw_warehouse,
        catalog_path=args.catalog or str(raw_catalog),
    )

    staging_path = args.staging or str(STAGING_FILE)
    write_staging(proposals, staging_path)

    gate = apply_gate(
        proposals,
        require_human_approval=REQUIRE_HUMAN_APPROVAL,
        confidence_floor=CONFIDENCE_FLOOR,
    )

    print(f"Proposed {len(proposals)} entity mappings → {staging_path}")
    print(f"  Auto-promotable: {len(gate['auto_promote'])}")
    print(f"  Needs review:    {len(gate['needs_review'])}")

    if gate["gate_action"] == "stop":
        print("\nHuman review required. Run:")
        print("  python -m src.base.entity_resolution.cli status")
        print("  python -m src.base.entity_resolution.cli approve")
    else:
        print("\nAll mappings can be auto-promoted.")
        # Auto-promote
        approved = approve_proposals(staging_path, actor="auto")
        result = promote_approved(
            staging_path=staging_path,
            warehouse_path=args.warehouse or str(WAREHOUSE_PATH),
            catalog_path=args.catalog or str(CATALOG_PATH),
            archive_dir=str(ARCHIVE_DIR),
        )
        print(f"Auto-promoted {result['promoted']} mappings to Iceberg.")


def cmd_status(args: argparse.Namespace) -> None:
    """Show pending proposals."""
    staging_path = args.staging or str(STAGING_FILE)
    pending = get_pending(staging_path)

    if not pending:
        print("No pending proposals.")
        return

    print(f"\n{'ID':<10} {'CIK':<12} {'Canonical Name':<30} {'Confidence':<12} {'Method'}")
    print("-" * 80)
    for p in pending:
        print(f"{p['mapping_id']:<10} {p['cik']:<12} {p['canonical_name']:<30} {p['confidence']:<12.2f} {p['resolution_method']}")
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
        print(f"  {a['mapping_id']} — {a['canonical_name']} (CIK {a['cik']})")

    result = promote_approved(
        staging_path=staging_path,
        warehouse_path=args.warehouse or str(WAREHOUSE_PATH),
        catalog_path=args.catalog or str(CATALOG_PATH),
        archive_dir=str(ARCHIVE_DIR),
    )

    print(f"\nPromoted {result['promoted']} to Iceberg.")
    print(f"  Mappings snapshot: {result.get('mappings_snapshot_id')}")
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
        print(f"  {r['mapping_id']} — {r['canonical_name']} (reason: {args.reason})")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="entity-resolution",
        description="Entity resolution CLI for SEC EDGAIR",
    )
    parser.add_argument("--staging", help="Path to staging JSON file")
    parser.add_argument("--warehouse", help="Path to Iceberg warehouse")
    parser.add_argument("--catalog", help="Path to catalog DB")
    parser.add_argument("--actor", help="Actor name for audit trail")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # resolve
    resolve_parser = subparsers.add_parser("resolve", help="Resolve entities from raw zone")
    resolve_parser.add_argument("--raw-warehouse", help="Path to raw zone warehouse")

    # status
    subparsers.add_parser("status", help="Show pending proposals")

    # approve
    approve_parser = subparsers.add_parser("approve", help="Approve pending mappings")
    approve_parser.add_argument("mapping_ids", nargs="*", help="Specific mapping IDs (or all if empty)")

    # reject
    reject_parser = subparsers.add_parser("reject", help="Reject specific mappings")
    reject_parser.add_argument("mapping_ids", nargs="+", help="Mapping IDs to reject")
    reject_parser.add_argument("--reason", required=True, help="Rejection reason")

    args = parser.parse_args(argv)

    commands = {
        "resolve": cmd_resolve,
        "status": cmd_status,
        "approve": cmd_approve,
        "reject": cmd_reject,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
