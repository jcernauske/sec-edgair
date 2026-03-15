"""CLI for the Chaos Monkey.

Usage:
    SEC_EDGAIR_ENV=dev python -m src.infra.chaos_monkey inject [--rate 0.07] [--seed 42]
    python -m src.infra.chaos_monkey manifest --latest
    python -m src.infra.chaos_monkey aar --manifest <path> --dq-results <dir>
    python -m src.infra.chaos_monkey cleanup
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from src.infra.chaos_monkey.config import (
    DEFAULT_INJECTION_RATE,
    MAX_INJECTION_RATE,
    MIN_INJECTION_RATE,
    SHADOW_WAREHOUSE_PATH,
)
from src.infra.chaos_monkey.injector import generate_corruptions
from src.infra.chaos_monkey.manifest import get_latest_manifest, read_manifest, write_manifest
from src.infra.chaos_monkey.report import load_dq_rules, write_after_action_report
from src.infra.chaos_monkey.safety import safety_check
from src.infra.chaos_monkey.shadow import (
    copy_real_data_to_shadow,
    inject_corruptions_to_shadow,
    setup_shadow_zone,
    teardown_shadow_zone,
)
from src.infra.chaos_reconciler import load_dq_results, reconcile
from src.infra.dq_runner import run_rules as dq_run_rules

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def cmd_inject(args: argparse.Namespace) -> None:
    """Run the full injection pipeline."""
    rate = args.rate
    if not (MIN_INJECTION_RATE <= rate <= MAX_INJECTION_RATE):
        sys.exit(
            f"Injection rate {rate} out of range [{MIN_INJECTION_RATE}, {MAX_INJECTION_RATE}]"
        )

    # Three-layer kill switch — hard exit if any layer fails
    safety_check(SHADOW_WAREHOUSE_PATH)

    # Step 1: Set up shadow zone
    logger.info("Setting up shadow zone...")
    setup_shadow_zone()

    # Step 2: Copy real data
    logger.info("Copying real data to shadow zone...")
    row_count, rows = copy_real_data_to_shadow()

    if not rows:
        sys.exit("No source data found in raw.xbrl_company_facts. Nothing to corrupt.")

    # Step 3: Generate corruptions
    logger.info("Generating corruptions at %.0f%% rate...", rate * 100)
    plan = generate_corruptions(rows, injection_rate=rate, seed=args.seed)

    if not plan.all_dimensions_covered:
        missing = [d for d, v in plan.dimension_coverage.items() if not v]
        sys.exit(f"DIMENSION COVERAGE FAILURE: Missing dimensions: {missing}")

    # Step 4: Inject into shadow
    logger.info("Injecting %d corrupted rows into shadow zone...", len(plan.corrupted_rows))
    snapshot_id = inject_corruptions_to_shadow(plan)

    # Step 5: Write manifest
    manifest_path = write_manifest(
        plan,
        source_table="raw.xbrl_company_facts",
        source_row_count=row_count,
        injection_rate=rate,
    )

    # Summary
    print()
    print("\U0001f412 CHAOS MONKEY INJECTION COMPLETE")
    print(f"  Source rows:     {row_count:,}")
    print(f"  Corrupted rows:  {len(plan.corrupted_rows):,}")
    print(f"  Injection rate:  {rate:.0%}")
    print(f"  Dimensions hit:  {sum(plan.dimension_coverage.values())}/10")
    print(f"  Manifest:        {manifest_path}")
    print(f"  Shadow zone:     {SHADOW_WAREHOUSE_PATH}")
    print(f"  Snapshot ID:     {snapshot_id}")
    print()
    print("Next steps:")
    print("  1. Run the pipeline against the shadow zone")
    print("  2. Execute DQ rules against shadow-derived tables")
    print("  3. Generate AAR: python -m src.infra.chaos_monkey aar \\")
    print(f"       --manifest {manifest_path} \\")
    print("       --dq-results governance/dq-results/")


def cmd_manifest(args: argparse.Namespace) -> None:
    """Display the latest manifest."""
    path = get_latest_manifest()
    if path is None:
        print("No chaos manifests found.")
        return

    manifest = read_manifest(path)
    print(f"Latest manifest: {path}")
    print(f"  Run ID:          {manifest['run_id']}")
    print(f"  Timestamp:       {manifest['timestamp']}")
    print(f"  Source rows:     {manifest['source_row_count']:,}")
    print(f"  Injected rows:   {manifest['injected_row_count']:,}")
    print(f"  Injection rate:  {manifest['injection_rate']:.0%}")
    print(f"  Corruptions:     {len(manifest['injections'])}")
    print()
    print("Dimension coverage:")
    for dim, covered in manifest["dimension_coverage"].items():
        status = "\u2705" if covered else "\u274c"
        count = sum(1 for i in manifest["injections"] if i["dimension"] == dim)
        print(f"  {status} {dim}: {count} corruptions")


def cmd_aar(args: argparse.Namespace) -> None:
    """Generate the comprehensive After-Action Report.

    Pulls together:
      1. Chaos manifest (what was injected)
      2. DQ results (what rules fired against shadow zone)
      3. Reconciliation (caught vs missed)
      4. Suggested remediations
    """
    manifest_path = args.manifest
    dq_results_dir = args.dq_results
    dq_rules_dir = args.dq_rules

    # Load all inputs
    logger.info("Loading manifest from %s", manifest_path)
    manifest = json.loads(manifest_path.read_text())

    logger.info("Loading DQ results from %s", dq_results_dir)
    dq_results = load_dq_results(dq_results_dir)

    logger.info("Loading DQ rules from %s", dq_rules_dir)
    dq_rules = load_dq_rules(dq_rules_dir)

    # Run reconciliation
    logger.info("Running reconciliation...")
    reconciliation = reconcile(manifest, dq_results)

    # Generate and write AAR
    report_path = write_after_action_report(
        manifest=manifest,
        dq_results=dq_results,
        dq_rules=dq_rules,
        reconciliation=reconciliation,
    )

    # Print summary
    gate = reconciliation["gate_decision"]
    print()
    print("\U0001f412 CHAOS MONKEY AFTER-ACTION REPORT")
    print(f"  Report:          {report_path}")
    print(f"  Corruptions:     {reconciliation['total_injected']:,}")
    print(f"  Detected:        {reconciliation['total_detected']:,} ({reconciliation['detection_rate']:.1%})")
    print(f"  Undetected:      {reconciliation['total_undetected']:,}")
    print(f"  Gate decision:   {gate}")

    if gate != "PASS":
        print()
        print(f"\u274c P0 GATE FAIL \u2014 {reconciliation['total_undetected']:,} undetected corruptions")
        print(f"  See {report_path} for remediations")
        sys.exit(1)
    else:
        print()
        print("\u2705 ALL CORRUPTIONS DETECTED \u2014 DQ rules validated")


def cmd_fullrun(args: argparse.Namespace) -> None:
    """Full cycle: inject → run DQ against shadow → reconcile → AAR.

    One command to get the real scorecard.
    """
    from src.infra.chaos_monkey.config import (
        SHADOW_CATALOG_PATH,
        SHADOW_WAREHOUSE_PATH,
    )
    from src.infra.iceberg_setup import get_catalog

    rate = args.rate
    if not (MIN_INJECTION_RATE <= rate <= MAX_INJECTION_RATE):
        sys.exit(f"Injection rate {rate} out of range [{MIN_INJECTION_RATE}, {MAX_INJECTION_RATE}]")

    # Three-layer kill switch
    safety_check(SHADOW_WAREHOUSE_PATH)

    # === PHASE 1: INJECT ===
    print("\n\U0001f412 PHASE 1: INJECTION")
    print("=" * 60)

    logger.info("Setting up shadow zone...")
    setup_shadow_zone()

    logger.info("Copying real data to shadow zone...")
    row_count, rows = copy_real_data_to_shadow()
    if not rows:
        sys.exit("No source data found in raw.xbrl_company_facts.")

    logger.info("Generating corruptions at %.0f%% rate...", rate * 100)
    plan = generate_corruptions(rows, injection_rate=rate, seed=args.seed)
    if not plan.all_dimensions_covered:
        missing = [d for d, v in plan.dimension_coverage.items() if not v]
        sys.exit(f"DIMENSION COVERAGE FAILURE: Missing dimensions: {missing}")

    logger.info("Injecting %d corrupted rows...", len(plan.corrupted_rows))
    snapshot_id = inject_corruptions_to_shadow(plan)

    manifest_path = write_manifest(
        plan,
        source_table="raw.xbrl_company_facts",
        source_row_count=row_count,
        injection_rate=rate,
    )

    print(f"  Source rows:     {row_count:,}")
    print(f"  Corrupted rows:  {len(plan.corrupted_rows):,}")
    print(f"  Dimensions hit:  {sum(plan.dimension_coverage.values())}/10")
    print(f"  Manifest:        {manifest_path}")

    # === PHASE 2: RUN DQ AGAINST SHADOW ===
    print(f"\n\U0001f412 PHASE 2: DQ RULES VS SHADOW ZONE")
    print("=" * 60)

    shadow_catalog = get_catalog(SHADOW_WAREHOUSE_PATH, SHADOW_CATALOG_PATH)
    logger.info("Executing DQ rules against shadow zone...")
    dq_result = dq_run_rules(spec="raw-ingest-xbrl-company-facts", catalog=shadow_catalog)

    print(f"  Rules executed:  {dq_result['rules_total']}")
    print(f"  Passed:          {dq_result['rules_passed']}")
    print(f"  Failed:          {dq_result['rules_failed']}")
    print(f"  Errored:         {dq_result['rules_errored']}")

    dq_results = dq_result.get("results", [])

    # === PHASE 3: RECONCILE + AAR ===
    print(f"\n\U0001f412 PHASE 3: RECONCILIATION + AFTER-ACTION REPORT")
    print("=" * 60)

    manifest = json.loads(manifest_path.read_text())
    dq_rules = load_dq_rules(Path("governance/dq-rules"))
    reconciliation = reconcile(manifest, dq_results)

    report_path = write_after_action_report(
        manifest=manifest,
        dq_results=dq_results,
        dq_rules=dq_rules,
        reconciliation=reconciliation,
    )

    gate = reconciliation["gate_decision"]
    print(f"  Corruptions:     {reconciliation['total_injected']:,}")
    print(f"  Detected:        {reconciliation['total_detected']:,} ({reconciliation['detection_rate']:.1%})")
    print(f"  Undetected:      {reconciliation['total_undetected']:,}")
    print(f"  Gate decision:   {gate}")
    print(f"  Report:          {report_path}")

    # === SUMMARY ===
    print(f"\n{'=' * 60}")
    if gate == "PASS":
        print("\u2705 ALL CORRUPTIONS DETECTED — DQ rules validated")
    else:
        print(f"\u274c P0 GATE FAIL — {reconciliation['total_undetected']:,} undetected corruptions")
        print(f"  See {report_path} for remediations")

    # Clean up shadow zone
    logger.info("Cleaning up shadow zone...")
    teardown_shadow_zone()
    print("  Shadow zone cleaned up")


def cmd_cleanup(args: argparse.Namespace) -> None:
    """Remove the shadow zone."""
    teardown_shadow_zone()
    print("Shadow zone cleaned up.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="\U0001f412 Chaos Monkey \u2014 Adversarial DQ Testing"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # inject
    p_inject = sub.add_parser("inject", help="Inject corrupted data into shadow zone")
    p_inject.add_argument(
        "--rate", type=float, default=DEFAULT_INJECTION_RATE,
        help=f"Injection rate (default: {DEFAULT_INJECTION_RATE})",
    )
    p_inject.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for reproducibility",
    )

    # manifest
    sub.add_parser("manifest", help="Show latest chaos manifest")

    # aar (after-action report)
    p_aar = sub.add_parser("aar", help="Generate comprehensive After-Action Report")
    p_aar.add_argument(
        "--manifest", required=True, type=Path,
        help="Path to chaos manifest JSON",
    )
    p_aar.add_argument(
        "--dq-results", required=True, type=Path,
        help="Path to DQ results directory",
    )
    p_aar.add_argument(
        "--dq-rules", type=Path, default=Path("governance/dq-rules"),
        help="Path to DQ rules directory (default: governance/dq-rules/)",
    )

    # fullrun (the whole cycle)
    p_full = sub.add_parser("fullrun", help="Full cycle: inject → DQ → reconcile → AAR")
    p_full.add_argument(
        "--rate", type=float, default=DEFAULT_INJECTION_RATE,
        help=f"Injection rate (default: {DEFAULT_INJECTION_RATE})",
    )
    p_full.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for reproducibility",
    )

    # cleanup
    sub.add_parser("cleanup", help="Remove the shadow zone")

    args = parser.parse_args()

    if args.command == "inject":
        cmd_inject(args)
    elif args.command == "manifest":
        cmd_manifest(args)
    elif args.command == "aar":
        cmd_aar(args)
    elif args.command == "fullrun":
        cmd_fullrun(args)
    elif args.command == "cleanup":
        cmd_cleanup(args)


if __name__ == "__main__":
    main()
