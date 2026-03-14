"""Temporal data quality rules for base.financial_facts.

Each validation function returns:
    {"rule_id", "passed", "violations", "total_checked", "message"}
"""

from __future__ import annotations

import datetime


def validate_no_future_filed_dates(
    facts: list[dict],
    *,
    reference_date: datetime.date | None = None,
) -> dict:
    """BASE-BT-001: No facts with filed_date in the future."""
    today = reference_date or datetime.date.today()
    violations = 0
    total = 0

    for f in facts:
        filed = f.get("filed_date")
        if filed is None:
            continue
        if isinstance(filed, str):
            filed = datetime.date.fromisoformat(filed)
        total += 1
        if filed > today:
            violations += 1

    return {
        "rule_id": "BASE-BT-001",
        "passed": violations == 0,
        "violations": violations,
        "total_checked": total,
        "message": f"No future filed_dates: {violations} violations out of {total} checked",
    }


def validate_start_before_end(facts: list[dict]) -> dict:
    """BASE-BT-002: start_date < end_date for all period facts."""
    violations = 0
    total = 0

    for f in facts:
        start = f.get("start_date")
        end = f.get("end_date")
        if start is None or end is None:
            continue
        if isinstance(start, str):
            start = datetime.date.fromisoformat(start)
        if isinstance(end, str):
            end = datetime.date.fromisoformat(end)
        total += 1
        if start >= end:
            violations += 1

    return {
        "rule_id": "BASE-BT-002",
        "passed": violations == 0,
        "violations": violations,
        "total_checked": total,
        "message": f"start_date < end_date: {violations} violations out of {total} checked",
    }


def validate_supersession_order(facts: list[dict]) -> dict:
    """BASE-BT-003: Superseded facts have filed_date <= superseding fact's filed_date."""
    violations = 0
    total = 0

    # Build lookup: accession_number -> filed_date
    accession_to_filed: dict[str, datetime.date] = {}
    for f in facts:
        acc = f.get("accession_number")
        filed = f.get("filed_date")
        if acc and filed:
            if isinstance(filed, str):
                filed = datetime.date.fromisoformat(filed)
            accession_to_filed[acc] = filed

    for f in facts:
        if not f.get("is_superseded"):
            continue

        superseded_by = f.get("superseded_by")
        if not superseded_by:
            continue

        total += 1
        original_filed = f.get("filed_date")
        if isinstance(original_filed, str):
            original_filed = datetime.date.fromisoformat(original_filed)

        superseding_filed = accession_to_filed.get(superseded_by)
        if superseding_filed and original_filed and original_filed > superseding_filed:
            violations += 1

    return {
        "rule_id": "BASE-BT-003",
        "passed": violations == 0,
        "violations": violations,
        "total_checked": total,
        "message": f"Supersession order: {violations} violations out of {total} checked",
    }


def validate_filed_after_period(facts: list[dict]) -> dict:
    """BASE-BT-004: filed_date >= end_date (filings come after period ends).

    Threshold: 99% (edge cases for early filers).
    """
    violations = 0
    total = 0

    for f in facts:
        filed = f.get("filed_date")
        end = f.get("end_date")
        if filed is None or end is None:
            continue
        if isinstance(filed, str):
            filed = datetime.date.fromisoformat(filed)
        if isinstance(end, str):
            end = datetime.date.fromisoformat(end)
        total += 1
        if filed < end:
            violations += 1

    pass_rate = ((total - violations) / total * 100) if total > 0 else 100.0
    passed = pass_rate >= 99.0

    return {
        "rule_id": "BASE-BT-004",
        "passed": passed,
        "violations": violations,
        "total_checked": total,
        "message": f"filed_date >= end_date: {violations} violations out of {total} checked ({pass_rate:.1f}% pass rate, 99% threshold)",
    }


def validate_superseded_by_exists(facts: list[dict]) -> dict:
    """BASE-BT-005: Every superseded_by accession exists in facts."""
    violations = 0
    total = 0

    all_accessions = {f.get("accession_number") for f in facts if f.get("accession_number")}

    for f in facts:
        superseded_by = f.get("superseded_by")
        if not superseded_by:
            continue

        total += 1
        if superseded_by not in all_accessions:
            violations += 1

    return {
        "rule_id": "BASE-BT-005",
        "passed": violations == 0,
        "violations": violations,
        "total_checked": total,
        "message": f"superseded_by references exist: {violations} violations out of {total} checked",
    }


def run_all_validations(
    facts: list[dict],
    *,
    reference_date: datetime.date | None = None,
) -> list[dict]:
    """Run all temporal DQ rules and return results."""
    return [
        validate_no_future_filed_dates(facts, reference_date=reference_date),
        validate_start_before_end(facts),
        validate_supersession_order(facts),
        validate_filed_after_period(facts),
        validate_superseded_by_exists(facts),
    ]
