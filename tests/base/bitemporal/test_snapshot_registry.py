"""Tests for snapshot registry (requires Iceberg fixtures)."""

import datetime
import tempfile
from pathlib import Path

from pyiceberg.schema import Schema
from pyiceberg.types import (
    BooleanType,
    DateType,
    DoubleType,
    IntegerType,
    NestedField,
    StringType,
    TimestamptzType,
)

from src.base.bitemporal.snapshot_registry import (
    find_snapshot_at,
    get_labeled_snapshots,
    read_at_snapshot,
    snapshot_diff_summary,
)
from src.infra.iceberg_setup import append_data, create_test_table, get_catalog


FINANCIAL_FACTS_SCHEMA = Schema(
    NestedField(1, "fact_id", StringType(), required=False),
    NestedField(2, "entity_id", StringType(), required=False),
    NestedField(3, "cik", IntegerType(), required=False),
    NestedField(4, "canonical_name", StringType(), required=False),
    NestedField(5, "ticker", StringType(), required=False),
    NestedField(6, "concept", StringType(), required=False),
    NestedField(7, "business_term_id", StringType(), required=False),
    NestedField(8, "business_term", StringType(), required=False),
    NestedField(9, "financial_statement", StringType(), required=False),
    NestedField(10, "category", StringType(), required=False),
    NestedField(11, "tier", IntegerType(), required=False),
    NestedField(12, "taxonomy", StringType(), required=False),
    NestedField(13, "unit", StringType(), required=False),
    NestedField(14, "val", DoubleType(), required=False),
    NestedField(15, "start_date", DateType(), required=False),
    NestedField(16, "end_date", DateType(), required=False),
    NestedField(17, "fiscal_year", IntegerType(), required=False),
    NestedField(18, "fiscal_period", StringType(), required=False),
    NestedField(19, "fiscal_year_end", StringType(), required=False),
    NestedField(20, "calendar_year", IntegerType(), required=False),
    NestedField(21, "calendar_quarter", IntegerType(), required=False),
    NestedField(22, "accession_number", StringType(), required=False),
    NestedField(23, "form", StringType(), required=False),
    NestedField(24, "filed_date", DateType(), required=False),
    NestedField(25, "is_amendment", BooleanType(), required=False),
    NestedField(26, "is_superseded", BooleanType(), required=False),
    NestedField(27, "superseded_by", StringType(), required=False),
    NestedField(28, "promoted_at", TimestamptzType(), required=False),
)


def _make_test_fact(fact_id: str, val: float = 1000.0) -> dict:
    return {
        "fact_id": fact_id,
        "entity_id": "ER-320193",
        "cik": 320193,
        "canonical_name": "Apple Inc.",
        "ticker": "AAPL",
        "concept": "Assets",
        "business_term_id": "BT-024",
        "business_term": "Total Assets",
        "financial_statement": "balance_sheet",
        "category": "assets",
        "tier": 1,
        "taxonomy": "us-gaap",
        "unit": "USD",
        "val": val,
        "start_date": datetime.date(2023, 1, 1),
        "end_date": datetime.date(2023, 12, 31),
        "fiscal_year": 2023,
        "fiscal_period": "FY",
        "fiscal_year_end": "0930",
        "calendar_year": 2023,
        "calendar_quarter": 4,
        "accession_number": f"0000-23-{fact_id}",
        "form": "10-K",
        "filed_date": datetime.date(2024, 2, 15),
        "is_amendment": False,
        "is_superseded": False,
        "superseded_by": None,
        "promoted_at": datetime.datetime(2024, 3, 1, tzinfo=datetime.timezone.utc),
    }


def _setup_table_with_snapshots():
    """Create a test table with two snapshots."""
    tmpdir = tempfile.mkdtemp()
    warehouse = Path(tmpdir) / "warehouse"
    catalog_db = Path(tmpdir) / "catalog.db"
    catalog = get_catalog(str(warehouse), str(catalog_db))

    table = create_test_table(catalog, "base", "financial_facts", FINANCIAL_FACTS_SCHEMA)

    # Snapshot 1: one fact
    snap1 = append_data(table, [_make_test_fact("F001")])

    # Snapshot 2: add another fact
    snap2 = append_data(table, [_make_test_fact("F002", val=2000.0)])

    return table, snap1, snap2


class TestGetLabeledSnapshots:

    def test_labels_and_sequence(self):
        table, snap1, snap2 = _setup_table_with_snapshots()
        labeled = get_labeled_snapshots(table)

        assert len(labeled) == 2
        assert labeled[0]["sequence"] == 1
        assert labeled[1]["sequence"] == 2
        assert "timestamp_iso" in labeled[0]
        assert labeled[0]["label"].startswith("snapshot-001-")
        assert labeled[1]["label"].startswith("snapshot-002-")


class TestFindSnapshotAt:

    def test_finds_correct_snapshot(self):
        table, snap1, snap2 = _setup_table_with_snapshots()
        labeled = get_labeled_snapshots(table)

        # Find snapshot at a time between snap1 and snap2
        ts1 = labeled[0]["timestamp_ms"]
        ts2 = labeled[1]["timestamp_ms"]
        midpoint = datetime.datetime.fromtimestamp(
            (ts1 + ts2) / 2 / 1000, tz=datetime.timezone.utc,
        )

        result = find_snapshot_at(table, midpoint)
        assert result is not None
        assert result["snapshot_id"] == snap1

    def test_returns_none_before_first(self):
        table, snap1, snap2 = _setup_table_with_snapshots()
        very_early = datetime.datetime(2000, 1, 1, tzinfo=datetime.timezone.utc)
        result = find_snapshot_at(table, very_early)
        assert result is None


class TestSnapshotDiffSummary:

    def test_diff_shows_added_facts(self):
        table, snap1, snap2 = _setup_table_with_snapshots()
        diff = snapshot_diff_summary(table, snap1, snap2)

        assert diff["count_before"] == 1
        assert diff["count_after"] == 2
        assert diff["added"] == 1
        assert diff["removed"] == 0


class TestReadAtSnapshot:

    def test_reads_specific_snapshot(self):
        table, snap1, snap2 = _setup_table_with_snapshots()

        facts_at_1 = read_at_snapshot(table, snap1)
        facts_at_2 = read_at_snapshot(table, snap2)

        assert len(facts_at_1) == 1
        assert len(facts_at_2) == 2
