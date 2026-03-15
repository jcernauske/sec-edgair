"""Chaos Monkey Reconciliation Engine.

Compares the chaos manifest (what was injected) against DQ results
(what was caught) to measure DQ rule coverage. Any undetected corruption
is a P0 gate failure.

This module is intentionally SEPARATE from the chaos monkey itself —
different trust boundaries.

Usage:
    python -m src.infra.chaos_reconciler reconcile --manifest <path> --dq-results <dir>
    python -m src.infra.chaos_reconciler report --manifest <path> --dq-results <dir>
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.infra.chaos_monkey.config import CHAOS_MANIFESTS_DIR, DQ_DIMENSIONS


def load_dq_results(dq_results_dir: Path, latest_only: bool = True) -> list[dict]:
    """Load DQ result files from the results directory.

    Args:
        dq_results_dir: Path to the DQ results directory.
        latest_only: If True, load only the most recent results file.
                     If False, load all files (may contain duplicates).
    """
    files = sorted(dq_results_dir.glob("*.json"))
    if not files:
        return []
    if latest_only:
        files = [files[-1]]  # Most recent by filename (timestamped)

    results = []
    for f in files:
        data = json.loads(f.read_text())
        if isinstance(data, list):
            results.extend(data)
        elif isinstance(data, dict) and "results" in data:
            results.extend(data["results"])
        elif isinstance(data, dict):
            results.append(data)
    return results


def reconcile(manifest: dict, dq_results: list[dict]) -> dict:
    """Compare chaos manifest against DQ results.

    For each corruption in the manifest, determine if any DQ rule
    flagged a failure that could correspond to it. This is a heuristic
    match — we check if the dimension of the corruption has any
    corresponding DQ failures.

    Returns a reconciliation report dict.
    """
    injections = manifest.get("injections", [])

    # Build a set of DQ dimensions that had failures
    failed_dimensions = set()
    failed_rules = []
    for result in dq_results:
        # DQ results have 'passed' field — we want failures
        if not result.get("passed", True):
            category = result.get("category", "").lower().replace(" ", "_")
            failed_dimensions.add(category)
            failed_rules.append(result)

    # For each corruption, check if its dimension had any DQ failure
    detected = []
    undetected = []
    for inj in injections:
        dim = inj["dimension"]
        if dim in failed_dimensions:
            detected.append(inj)
        else:
            undetected.append(inj)

    # Dimension-level summary
    dim_summary = {}
    for dim in DQ_DIMENSIONS:
        dim_injections = [i for i in injections if i["dimension"] == dim]
        dim_detected = [i for i in detected if i["dimension"] == dim]
        dim_undetected = [i for i in undetected if i["dimension"] == dim]
        count = len(dim_injections)
        caught = len(dim_detected)
        dim_summary[dim] = {
            "injected": count,
            "caught": caught,
            "missed": count - caught,
            "miss_rate": (count - caught) / count if count > 0 else 0.0,
            "status": "PASS" if count == caught else "P0 FAIL",
        }

    total = len(injections)
    total_detected = len(detected)
    total_undetected = len(undetected)
    gate_pass = total_undetected == 0

    return {
        "run_id": manifest.get("run_id", "unknown"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_injected": total,
        "total_detected": total_detected,
        "total_undetected": total_undetected,
        "detection_rate": total_detected / total if total > 0 else 0.0,
        "gate_decision": "PASS" if gate_pass else "P0 FAIL",
        "dimension_summary": dim_summary,
        "undetected_corruptions": undetected,
        "dq_failures_matched": len(failed_rules),
    }


def generate_report(reconciliation: dict) -> str:
    """Generate a markdown reconciliation report."""
    r = reconciliation
    lines = [
        "# Chaos Monkey Reconciliation Report",
        "",
        f"**Run:** {r['run_id']}",
        f"**Timestamp:** {r['timestamp']}",
        f"**Injected:** {r['total_injected']:,} corrupted rows across {len(DQ_DIMENSIONS)} dimensions",
        f"**Detected:** {r['total_detected']:,} ({r['detection_rate']:.1%})",
        f"**Undetected:** {r['total_undetected']:,} ({1 - r['detection_rate']:.1%})",
        "",
        "## Dimension Coverage",
        "",
        "| Dimension | Injected | Caught | Miss Rate | Status |",
        "|-----------|----------|--------|-----------|--------|",
    ]

    for dim in DQ_DIMENSIONS:
        s = r["dimension_summary"][dim]
        status = f"\\u2705 PASS" if s["status"] == "PASS" else f"\\u274c P0 FAIL"
        lines.append(
            f"| {dim.replace('_', ' ').title()} | {s['injected']:,} | "
            f"{s['caught']:,} | {s['miss_rate']:.2%} | {status} |"
        )

    lines.extend([
        "",
        "## \U0001f441\ufe0f P0 Gate Decision",
        "",
    ])

    if r["gate_decision"] == "PASS":
        lines.append(
            f"**\u2705 PASS** \u2014 All {r['total_injected']:,} corruptions were detected by DQ rules."
        )
    else:
        lines.append(
            f"**\u274c FAIL** \u2014 {r['total_undetected']:,} corruptions went undetected."
        )
        lines.append("")
        lines.append("Undetected corruptions by dimension:")
        # Group undetected by dimension
        by_dim: dict[str, list] = {}
        for u in r["undetected_corruptions"]:
            by_dim.setdefault(u["dimension"], []).append(u)
        for dim, items in sorted(by_dim.items()):
            lines.append(f"- **{dim.replace('_', ' ').title()}**: {len(items)} corruptions")
            for item in items[:3]:  # Show up to 3 examples
                lines.append(f"  - {item['corruption_id']}: {item['description']}")
            if len(items) > 3:
                lines.append(f"  - ... and {len(items) - 3} more")

        lines.extend([
            "",
            "## Recommended Actions",
            "",
            "New DQ rules must be written to cover the undetected dimensions before this spec can proceed.",
        ])

    return "\n".join(lines) + "\n"


def write_reconciliation_report(reconciliation: dict) -> Path:
    """Write the reconciliation report to governance/chaos-manifests/."""
    report = generate_report(reconciliation)
    now = datetime.now(timezone.utc)
    filename = f"reconciliation-{now.strftime('%Y-%m-%d-%H-%M-%S')}.md"
    CHAOS_MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
    path = CHAOS_MANIFESTS_DIR / filename
    path.write_text(report)
    return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chaos Monkey Reconciliation Engine"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # reconcile
    p_rec = sub.add_parser("reconcile", help="Compare manifest against DQ results")
    p_rec.add_argument("--manifest", required=True, type=Path, help="Path to chaos manifest JSON")
    p_rec.add_argument("--dq-results", required=True, type=Path, help="Path to DQ results directory")

    # report
    p_rep = sub.add_parser("report", help="Generate reconciliation report")
    p_rep.add_argument("--manifest", required=True, type=Path, help="Path to chaos manifest JSON")
    p_rep.add_argument("--dq-results", required=True, type=Path, help="Path to DQ results directory")

    args = parser.parse_args()

    if args.command in ("reconcile", "report"):
        manifest = json.loads(args.manifest.read_text())
        dq_results = load_dq_results(args.dq_results)
        result = reconcile(manifest, dq_results)

        if args.command == "reconcile":
            print(json.dumps(result, indent=2, default=str))
            if result["gate_decision"] != "PASS":
                sys.exit(1)
        else:
            report_path = write_reconciliation_report(result)
            print(f"Reconciliation report written to: {report_path}")
            if result["gate_decision"] != "PASS":
                print(f"\n\u274c P0 GATE FAIL \u2014 {result['total_undetected']} undetected corruptions")
                sys.exit(1)
            else:
                print(f"\n\u2705 PASS \u2014 All corruptions detected")


if __name__ == "__main__":
    main()
