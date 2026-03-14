"""Statistical profiling for raw.xbrl_company_facts.

Reads the Iceberg table and computes per-field statistics:
cardinality, null rates, min/max, top values, type distributions.
"""

from __future__ import annotations

import datetime
from collections import Counter
from pathlib import Path

from src.infra.iceberg_setup import get_catalog, read_with_duckdb
from src.raw.xbrl_company_facts.config import CATALOG_PATH, WAREHOUSE_PATH


def profile_table(
    warehouse_path: Path | None = None,
    catalog_path: Path | None = None,
) -> dict:
    """Profile raw.xbrl_company_facts and return per-field statistics."""
    warehouse_path = warehouse_path or WAREHOUSE_PATH
    catalog_path = catalog_path or CATALOG_PATH

    catalog = get_catalog(warehouse_path, catalog_path)
    table = catalog.load_table("raw.xbrl_company_facts")
    rows = read_with_duckdb(table)

    total = len(rows)
    if total == 0:
        return {"total_rows": 0, "fields": {}}

    fields = list(rows[0])
    profiles: dict[str, dict] = {}

    for field in fields:
        values = [r[field] for r in rows]
        non_null = [v for v in values if v is not None]
        null_count = total - len(non_null)

        profile: dict = {
            "null_count": null_count,
            "null_rate": round(null_count / total, 4),
            "distinct_count": len(set(non_null)),
            "total_count": total,
        }

        if non_null:
            # Top values (for all types)
            counter = Counter(non_null)
            profile["top_values"] = [
                {"value": str(v), "count": c}
                for v, c in counter.most_common(10)
            ]

            # Numeric stats
            if isinstance(non_null[0], (int, float)):
                numeric = [float(v) for v in non_null]
                profile["min"] = min(numeric)
                profile["max"] = max(numeric)
                profile["mean"] = round(sum(numeric) / len(numeric), 4)

            # Date stats
            elif isinstance(non_null[0], (datetime.date, datetime.datetime)):
                profile["min"] = str(min(non_null))
                profile["max"] = str(max(non_null))

            # String stats
            elif isinstance(non_null[0], str):
                lengths = [len(v) for v in non_null]
                profile["min_length"] = min(lengths)
                profile["max_length"] = max(lengths)
                profile["mean_length"] = round(sum(lengths) / len(lengths), 1)

        profiles[field] = profile

    # Per-CIK row counts
    cik_counts = Counter(r["cik"] for r in rows)

    return {
        "total_rows": total,
        "field_count": len(fields),
        "cik_counts": {str(k): v for k, v in cik_counts.most_common()},
        "fields": profiles,
    }


def format_profile_report(profile: dict) -> str:
    """Format profile dict as markdown report."""
    lines = [
        f"## Data Profile: raw.xbrl_company_facts",
        f"**Source:** Iceberg table at data/raw/iceberg_warehouse",
        f"**Date:** {datetime.date.today()}",
        f"**Agent:** @data-profiler",
        f"**Record Count:** {profile['total_rows']:,}",
        f"**Field Count:** {profile['field_count']}",
        "",
        "### Row Counts by CIK",
        "| CIK | Rows |",
        "|-----|------|",
    ]
    for cik, count in profile["cik_counts"].items():
        lines.append(f"| {cik} | {count:,} |")

    lines.extend(["", "### Field Profiles", ""])

    for field, stats in profile["fields"].items():
        lines.append(f"#### {field}")
        lines.append(f"- **Distinct:** {stats['distinct_count']:,}")
        lines.append(f"- **Null Rate:** {stats['null_rate']*100:.1f}% ({stats['null_count']:,}/{stats['total_count']:,})")

        if "min" in stats and "max" in stats:
            lines.append(f"- **Min:** {stats['min']}")
            lines.append(f"- **Max:** {stats['max']}")
        if "mean" in stats:
            lines.append(f"- **Mean:** {stats['mean']:,.4f}")
        if "min_length" in stats:
            lines.append(f"- **Length:** {stats['min_length']}-{stats['max_length']} (avg {stats['mean_length']})")

        if "top_values" in stats:
            top = stats["top_values"][:5]
            lines.append(f"- **Top Values:** " + ", ".join(
                f"`{v['value'][:50]}` ({v['count']:,})" for v in top
            ))
        lines.append("")

    return "\n".join(lines)
