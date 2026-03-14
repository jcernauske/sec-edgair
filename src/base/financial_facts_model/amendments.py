"""Detect amendment/supersession chains and build amendment_tracking table.

For each superseded fact, creates a tracking entry that pairs the original
filing with the superseding amendment, recording the value change.
"""

from __future__ import annotations

import datetime
import uuid

from .config import SUPERSESSION_GRAIN


def detect_amendments(facts: list[dict]) -> list[dict]:
    """Build amendment tracking entries from superseded facts.

    For each grain group with multiple filings, pairs each superseded
    filing with the latest (superseding) filing.
    """
    groups: dict[tuple, list[dict]] = {}

    for f in facts:
        key = tuple(f.get(field) for field in SUPERSESSION_GRAIN)
        groups.setdefault(key, []).append(f)

    now = datetime.datetime.now(datetime.timezone.utc)
    tracking = []

    for group in groups.values():
        if len(group) < 2:
            continue

        group.sort(key=lambda x: x["filed_date"])
        latest = group[-1]

        for original in group[:-1]:
            original_val = float(original["val"])
            amendment_val = float(latest["val"])
            val_change = amendment_val - original_val

            val_change_pct = None
            if original_val != 0:
                val_change_pct = (val_change / abs(original_val)) * 100.0

            tracking.append({
                "tracking_id": str(uuid.uuid4()),
                "cik": original["cik"],
                "concept": original["concept"],
                "unit": original["unit"],
                "start_date": original.get("start_date"),
                "end_date": original["end_date"],
                "original_accession": original["accession_number"],
                "original_filed_date": original["filed_date"],
                "original_val": original_val,
                "amendment_accession": latest["accession_number"],
                "amendment_filed_date": latest["filed_date"],
                "amendment_val": amendment_val,
                "val_change": val_change,
                "val_change_pct": val_change_pct,
                "amendment_form": latest["form"],
                "detected_at": now,
            })

    return tracking
