"""Comprehensive After-Action Report (AAR) for chaos monkey runs.

The AAR is the single document that tells the full story:
  1. What the monkey injected (from the manifest)
  2. What DQ rules ran against the shadow zone (from DQ results)
  3. What was caught vs missed (from reconciliation)
  4. Suggested remediations for gaps

Every chaos monkey run ALWAYS produces an AAR. No silent runs.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from src.infra.chaos_monkey.config import CHAOS_MANIFESTS_DIR, DQ_DIMENSIONS

# Reports directory
CHAOS_REPORTS_DIR = CHAOS_MANIFESTS_DIR.parent / "chaos-reports"


# ---------------------------------------------------------------------------
# Remediation knowledge base
# ---------------------------------------------------------------------------
# Maps DQ dimensions to specific, actionable remediation suggestions.
# The monkey doesn't know the DQ rules, but the REPORT does — it's generated
# after the information barrier no longer matters.

_REMEDIATIONS: dict[str, list[str]] = {
    "completeness": [
        "Add NOT NULL checks for all required fields (`cik`, `entity_name`, `val`, `end_date`, etc.)",
        "Add row-count-per-CIK floor to catch partial loads",
        "Add completeness ratio rule: `COUNT(field) / COUNT(*) >= threshold`",
    ],
    "validity": [
        "Add allowed-value checks: `fiscal_period IN ('FY','Q1','Q2','Q3','Q4')`",
        "Add pattern validation for `form` (10-K, 10-Q, 8-K, etc.)",
        "Add non-empty string checks: `LENGTH(TRIM(field)) > 0`",
        "Add taxonomy validation against known XBRL taxonomies",
    ],
    "uniqueness": [
        "Add duplicate detection: `GROUP BY (cik, concept, end_date, accession_number) HAVING COUNT(*) > 1`",
        "Add full-row duplicate check using row hashing",
        "Add primary key uniqueness constraint via DQ rule",
    ],
    "consistency": [
        "Add date range validation: `start_date <= end_date`",
        "Add fiscal year / end_date consistency: `EXTRACT(YEAR FROM end_date) BETWEEN fiscal_year-1 AND fiscal_year+1`",
        "Add cross-field consistency for `fiscal_period` vs date range length",
    ],
    "accuracy": [
        "Add statistical outlier detection: `val` outside 3 sigma of per-concept mean",
        "Add sign validation per concept: revenue should be positive, expenses context-dependent",
        "Add minimum value thresholds for known large-cap companies",
        "Add year-over-year change bounds: flag >1000% swings",
    ],
    "reasonableness": [
        "Add absolute bounds: `val BETWEEN -1e15 AND 1e15`",
        "Add fiscal year range: `fiscal_year BETWEEN 1990 AND EXTRACT(YEAR FROM CURRENT_DATE)+1`",
        "Add CIK range validation: `cik > 0 AND cik < 10000000`",
        "Add z-score or IQR-based outlier detection per concept",
    ],
    "freshness": [
        "Add timestamp recency: `ingested_at <= CURRENT_TIMESTAMP`",
        "Add filed_date range: `filed_date BETWEEN '1993-01-01' AND CURRENT_DATE`",
        "Add staleness detection: `ingested_at > CURRENT_TIMESTAMP - INTERVAL '30 days'`",
    ],
    "volume": [
        "Add row count bounds per CIK: flag CIKs with >2x median row count",
        "Add overall table volume bounds: `COUNT(*) BETWEEN min AND max`",
        "Add per-concept volume distribution check",
    ],
    "referential_integrity": [
        "Add CIK existence check against `base.entity_mappings`",
        "Add accession number format validation: `accession_number LIKE '%-__-______'`",
        "Add cross-table join validation for downstream foreign keys",
    ],
    "coverage": [
        "Add period type coverage: every CIK should have at least one 'FY' row",
        "Add unit distribution check: majority of financial concepts should have 'USD'",
        "Add concept coverage: key concepts (Assets, Revenue, etc.) present per CIK",
    ],
}


def generate_aar(
    manifest: dict,
    dq_results: list[dict],
    dq_rules: list[dict],
    reconciliation: dict,
) -> str:
    """Generate the comprehensive After-Action Report.

    Args:
        manifest: The chaos monkey injection manifest.
        dq_results: All DQ rule execution results from the shadow zone run.
        dq_rules: All DQ rule definitions (for context).
        reconciliation: The reconciliation output (detected vs missed).
    """
    now = datetime.now(timezone.utc)
    injections = manifest.get("injections", [])
    gate = reconciliation["gate_decision"]

    # Stats
    dim_counts = Counter(i["dimension"] for i in injections)
    strategy_counts = Counter(i["strategy"] for i in injections)
    field_counts = Counter(i["field"] for i in injections)

    # DQ result stats — deduplicate by rule_id (keep latest per rule)
    seen_rules: dict[str, dict] = {}
    for r in dq_results:
        rid = r.get("rule_id", "unknown")
        seen_rules[rid] = r  # Last occurrence wins (latest run)
    deduped_results = list(seen_rules.values())

    total_rules = len(deduped_results)
    passed_rules = sum(1 for r in deduped_results if r.get("passed", True) and not r.get("error"))
    failed_rules = [r for r in deduped_results if not r.get("passed", True) and not r.get("error")]
    errored_rules = [r for r in deduped_results if r.get("error")]

    lines = [
        "# Chaos Monkey After-Action Report",
        "",
        f"**Date:** {now.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"**Run ID:** {manifest.get('run_id', 'unknown')}",
        f"**Source Table:** `{manifest.get('source_table', 'unknown')}`",
        f"**Gate Decision:** {'PASS' if gate == 'PASS' else 'P0 FAIL'}",
        "",
        "---",
        "",
    ]

    # =======================================================================
    # Section 1: Injection Summary
    # =======================================================================
    lines.extend([
        "## 1. Injection Summary",
        "",
        "*What the chaos monkey did.*",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Source rows | {manifest.get('source_row_count', 0):,} |",
        f"| Corrupted rows injected | {manifest.get('injected_row_count', 0):,} |",
        f"| Injection rate | {manifest.get('injection_rate', 0):.0%} |",
        f"| Dimensions covered | {sum(1 for v in manifest.get('dimension_coverage', {}).values() if v)}/10 |",
        f"| Unique strategies used | {len(strategy_counts)} |",
        f"| Unique fields targeted | {len(field_counts)} |",
        "",
        "### Corruption by Dimension",
        "",
        "| Dimension | Corruptions | % of Total |",
        "|-----------|-------------|------------|",
    ])

    total_inj = len(injections)
    for dim in DQ_DIMENSIONS:
        count = dim_counts.get(dim, 0)
        pct = count / total_inj * 100 if total_inj > 0 else 0
        lines.append(f"| {dim.replace('_', ' ').title()} | {count:,} | {pct:.1f}% |")

    lines.extend([
        "",
        "### Strategies Used",
        "",
        "| Strategy | Count |",
        "|----------|-------|",
    ])
    for strategy, count in strategy_counts.most_common():
        lines.append(f"| `{strategy}` | {count:,} |")

    lines.extend([
        "",
        "### Sample Corruptions (3 per dimension)",
        "",
    ])
    for dim in DQ_DIMENSIONS:
        dim_injs = [i for i in injections if i["dimension"] == dim]
        if not dim_injs:
            continue
        lines.append(f"**{dim.replace('_', ' ').title()}**")
        lines.append("")
        lines.append("| ID | Strategy | Description |")
        lines.append("|-----|----------|-------------|")
        for i in dim_injs[:3]:
            desc = i["description"][:80] + "..." if len(i["description"]) > 80 else i["description"]
            lines.append(f"| `{i['corruption_id']}` | `{i['strategy']}` | {desc} |")
        if len(dim_injs) > 3:
            lines.append(f"| | | *...{len(dim_injs) - 3} more* |")
        lines.append("")

    # =======================================================================
    # Section 2: DQ Results Against Shadow Zone
    # =======================================================================
    lines.extend([
        "---",
        "",
        "## 2. DQ Results Against Shadow Zone",
        "",
        "*What the DQ rules found when executed against the corrupted data.*",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total DQ rules executed | {total_rules} |",
        f"| Rules passed | {passed_rules} |",
        f"| Rules failed | {len(failed_rules)} |",
        f"| Rules errored | {len(errored_rules)} |",
        "",
    ])

    if failed_rules:
        lines.extend([
            "### Failed Rules (caught corruptions)",
            "",
            "| Rule ID | Category | Violations | Detail |",
            "|---------|----------|------------|--------|",
        ])
        for r in failed_rules:
            rule_id = r.get("rule_id", "?")
            category = r.get("category", "?")
            violations = r.get("violations", r.get("raw_value", "?"))
            detail = r.get("detail", r.get("description", ""))
            detail_short = str(detail)[:60] + "..." if len(str(detail)) > 60 else str(detail)
            lines.append(f"| `{rule_id}` | {category} | {violations} | {detail_short} |")
        lines.append("")

    if errored_rules:
        lines.extend([
            "### Errored Rules",
            "",
            "| Rule ID | Error |",
            "|---------|-------|",
        ])
        for r in errored_rules:
            error_msg = str(r.get("error", "?")).replace("\n", " ")[:80]
            lines.append(f"| `{r.get('rule_id', '?')}` | {error_msg} |")
        lines.append("")

    # Rules that passed (summary only)
    passed = [r for r in deduped_results if r.get("passed", True) and not r.get("error")]
    if passed:
        lines.extend([
            "### Passed Rules (did not detect corruptions in their scope)",
            "",
            "| Rule ID | Category |",
            "|---------|----------|",
        ])
        for r in passed:
            lines.append(f"| `{r.get('rule_id', '?')}` | {r.get('category', '?')} |")
        lines.append("")

    # =======================================================================
    # Section 3: Reconciliation — Caught vs Missed
    # =======================================================================
    lines.extend([
        "---",
        "",
        "## 3. Reconciliation — Caught vs Missed",
        "",
        "*Did the DQ rules catch what the monkey injected?*",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total corruptions | {reconciliation['total_injected']:,} |",
        f"| Detected | {reconciliation['total_detected']:,} ({reconciliation['detection_rate']:.1%}) |",
        f"| Undetected | {reconciliation['total_undetected']:,} ({1 - reconciliation['detection_rate']:.1%}) |",
        f"| DQ rules that fired | {reconciliation.get('dq_failures_matched', 0)} |",
        "",
        "### Dimension Scorecard",
        "",
        "| Dimension | Injected | Caught | Missed | Miss Rate | Verdict |",
        "|-----------|----------|--------|--------|-----------|---------|",
    ])

    for dim in DQ_DIMENSIONS:
        s = reconciliation["dimension_summary"].get(dim, {})
        injected = s.get("injected", 0)
        caught = s.get("caught", 0)
        missed = s.get("missed", 0)
        miss_rate = s.get("miss_rate", 0)
        status = s.get("status", "?")
        verdict = "PASS" if status == "PASS" else "P0 FAIL"
        lines.append(
            f"| {dim.replace('_', ' ').title()} | {injected:,} | {caught:,} | "
            f"{missed:,} | {miss_rate:.1%} | {verdict} |"
        )

    # =======================================================================
    # Section 4: Gate Decision
    # =======================================================================
    lines.extend([
        "",
        "---",
        "",
        "## 4. Gate Decision",
        "",
    ])

    if gate == "PASS":
        lines.extend([
            f"**PASS** — All {reconciliation['total_injected']:,} corruptions "
            f"were detected by at least one DQ rule across all 10 dimensions.",
            "",
            "The DQ rule suite is validated against adversarial injection at "
            f"{manifest.get('injection_rate', 0):.0%} corruption rate.",
        ])
    else:
        lines.extend([
            f"**P0 FAIL** — {reconciliation['total_undetected']:,} corruptions went undetected.",
            "",
            "Undetected corruptions by dimension:",
            "",
        ])
        by_dim: dict[str, list] = {}
        for u in reconciliation.get("undetected_corruptions", []):
            by_dim.setdefault(u["dimension"], []).append(u)
        for dim, items in sorted(by_dim.items()):
            lines.append(f"- **{dim.replace('_', ' ').title()}**: {len(items):,} corruptions undetected")
            for item in items[:3]:
                lines.append(f"  - `{item['corruption_id']}`: {item['description']}")
            if len(items) > 3:
                lines.append(f"  - *...and {len(items) - 3} more*")

    # =======================================================================
    # Section 5: Suggested Remediations
    # =======================================================================
    lines.extend([
        "",
        "---",
        "",
        "## 5. Suggested Remediations",
        "",
    ])

    if gate == "PASS":
        lines.extend([
            "No remediations required — all dimensions covered.",
            "",
            "**Hardening suggestions** (optional, to increase depth of coverage):",
            "",
        ])
        # Still show some suggestions for strengthening
        for dim in DQ_DIMENSIONS:
            remeds = _REMEDIATIONS.get(dim, [])
            if remeds:
                lines.append(f"- **{dim.replace('_', ' ').title()}**: {remeds[0]}")
    else:
        lines.append("**Required** — these gaps must be closed before the pipeline is validated:")
        lines.append("")

        # Show remediations for failed dimensions
        failed_dims = [
            dim for dim in DQ_DIMENSIONS
            if reconciliation["dimension_summary"].get(dim, {}).get("status") != "PASS"
        ]
        for dim in failed_dims:
            lines.append(f"### {dim.replace('_', ' ').title()}")
            lines.append("")
            remeds = _REMEDIATIONS.get(dim, ["No specific remediation available."])
            for r in remeds:
                lines.append(f"- {r}")
            lines.append("")

        # Show passing dimensions briefly
        passing_dims = [d for d in DQ_DIMENSIONS if d not in failed_dims]
        if passing_dims:
            lines.extend([
                "### Passing Dimensions (no action required)",
                "",
            ])
            for dim in passing_dims:
                lines.append(f"- {dim.replace('_', ' ').title()}")
            lines.append("")

    # =======================================================================
    # Section 6: Artifacts
    # =======================================================================
    lines.extend([
        "",
        "---",
        "",
        "## 6. Artifacts",
        "",
        "| Artifact | Location |",
        "|----------|----------|",
        f"| Injection manifest | `{manifest.get('run_id', 'unknown')}` in `governance/chaos-manifests/` |",
        f"| DQ results | `governance/dq-results/` |",
        f"| This report | `governance/chaos-reports/` |",
        "",
    ])

    return "\n".join(lines) + "\n"


def load_dq_rules(dq_rules_dir: Path) -> list[dict]:
    """Load all DQ rule definitions from governance/dq-rules/."""
    rules = []
    for f in sorted(dq_rules_dir.glob("*.json")):
        data = json.loads(f.read_text())
        spec_rules = data.get("rules", [])
        for rule in spec_rules:
            rule["spec"] = data.get("spec", f.stem)
            rule["tables"] = data.get("tables", [])
        rules.extend(spec_rules)
    return rules


def write_after_action_report(
    manifest: dict,
    dq_results: list[dict],
    dq_rules: list[dict],
    reconciliation: dict,
) -> Path:
    """Write the comprehensive AAR to governance/chaos-reports/.

    Returns the path to the written report.
    """
    report = generate_aar(
        manifest=manifest,
        dq_results=dq_results,
        dq_rules=dq_rules,
        reconciliation=reconciliation,
    )

    CHAOS_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    filename = f"chaos-aar-{now.strftime('%Y-%m-%d-%H-%M-%S')}.md"
    path = CHAOS_REPORTS_DIR / filename
    path.write_text(report)
    return path
