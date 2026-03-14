"""Iceberg snapshot enrichment and time travel utilities.

In-memory registry — no new tables. Enriches PyIceberg's get_snapshots()
with ISO timestamps, labels, and diff summaries.
"""

from __future__ import annotations

import datetime

from src.infra.iceberg_setup import get_snapshots, read_with_duckdb


def get_labeled_snapshots(table) -> list[dict]:
    """Enrich raw snapshots with timestamp_iso, label, and sequence number."""
    raw = get_snapshots(table)
    labeled = []

    for i, snap in enumerate(raw, start=1):
        ts_ms = snap["timestamp_ms"]
        ts_iso = datetime.datetime.fromtimestamp(
            ts_ms / 1000, tz=datetime.timezone.utc
        ).isoformat()

        operation = snap.get("operation", "unknown")
        label = f"snapshot-{i:03d}-{operation}"

        labeled.append({
            **snap,
            "timestamp_iso": ts_iso,
            "label": label,
            "sequence": i,
        })

    return labeled


def find_snapshot_at(
    table,
    as_of_datetime: datetime.datetime | str,
) -> dict | None:
    """Find the snapshot current at a given datetime.

    Returns the latest snapshot with timestamp_ms <= as_of_datetime, or None.
    """
    if isinstance(as_of_datetime, str):
        as_of_datetime = datetime.datetime.fromisoformat(as_of_datetime)

    if as_of_datetime.tzinfo is None:
        as_of_datetime = as_of_datetime.replace(tzinfo=datetime.timezone.utc)

    as_of_ms = int(as_of_datetime.timestamp() * 1000)

    snapshots = get_labeled_snapshots(table)
    candidates = [s for s in snapshots if s["timestamp_ms"] <= as_of_ms]

    if not candidates:
        return None

    return max(candidates, key=lambda s: s["timestamp_ms"])


def snapshot_diff_summary(
    table,
    snap_before: int,
    snap_after: int,
) -> dict:
    """Count added/removed facts between two snapshots.

    Returns {"snap_before", "snap_after", "count_before", "count_after", "added", "removed"}.
    """
    facts_before = read_with_duckdb(table, snapshot_id=snap_before)
    facts_after = read_with_duckdb(table, snapshot_id=snap_after)

    ids_before = {f.get("fact_id") for f in facts_before if f.get("fact_id")}
    ids_after = {f.get("fact_id") for f in facts_after if f.get("fact_id")}

    return {
        "snap_before": snap_before,
        "snap_after": snap_after,
        "count_before": len(facts_before),
        "count_after": len(facts_after),
        "added": len(ids_after - ids_before),
        "removed": len(ids_before - ids_after),
    }


def read_at_snapshot(table, snapshot_id: int) -> list[dict]:
    """Convenience wrapper around read_with_duckdb(snapshot_id)."""
    return read_with_duckdb(table, snapshot_id=snapshot_id)
