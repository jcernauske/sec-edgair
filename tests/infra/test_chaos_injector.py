"""Tests for the Chaos Monkey injection engine.

Validates that corruptions are generated across all 10 DQ dimensions
and that the output structure is correct.
"""

from __future__ import annotations

import datetime

import pytest

from src.infra.chaos_monkey.config import DQ_DIMENSIONS
from src.infra.chaos_monkey.injector import Corruption, InjectionPlan, generate_corruptions


def _make_sample_rows(count: int = 100) -> list[dict]:
    """Generate sample raw zone rows for testing."""
    rows = []
    for i in range(count):
        rows.append({
            "cik": 320193,
            "entity_name": "Apple Inc.",
            "taxonomy": "us-gaap",
            "concept": "Assets",
            "label": "Total Assets",
            "description": "Sum of all assets",
            "unit": "USD",
            "start_date": datetime.date(2024, 1, 1),
            "end_date": datetime.date(2024, 12, 31),
            "val": 352583000000.0,
            "accession_number": f"0000320193-24-{i:05d}",
            "fiscal_year": 2024,
            "fiscal_period": "FY",
            "form": "10-K",
            "filed_date": datetime.date(2024, 10, 31),
            "frame": "CY2024",
            "ingested_at": datetime.datetime(2026, 3, 14, tzinfo=datetime.timezone.utc),
            "source_url": "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json",
            "source_method": "api",
            "load_date": datetime.date(2026, 3, 14),
        })
    return rows


class TestGenerateCorruptions:
    """Core injection engine produces valid, dimension-complete output."""

    def test_covers_all_10_dimensions(self):
        rows = _make_sample_rows(200)
        plan = generate_corruptions(rows, injection_rate=0.07, seed=42)
        assert plan.all_dimensions_covered
        for dim in DQ_DIMENSIONS:
            assert plan.dimension_coverage[dim], f"Missing dimension: {dim}"

    def test_respects_injection_rate(self):
        rows = _make_sample_rows(1000)
        plan = generate_corruptions(rows, injection_rate=0.07, seed=42)
        # Should be approximately 7% of 1000 = 70, but at least MIN_PER_DIMENSION * 10
        assert len(plan.corrupted_rows) >= 50
        assert len(plan.corrupted_rows) <= 150  # Generous upper bound

    def test_minimum_per_dimension(self):
        rows = _make_sample_rows(200)
        plan = generate_corruptions(rows, injection_rate=0.05, seed=42)
        for dim in DQ_DIMENSIONS:
            dim_count = sum(1 for c in plan.corruptions if c.dimension == dim)
            assert dim_count >= 5, f"{dim} has only {dim_count} corruptions (min 5)"

    def test_corruption_ids_are_unique(self):
        rows = _make_sample_rows(200)
        plan = generate_corruptions(rows, injection_rate=0.07, seed=42)
        ids = [c.corruption_id for c in plan.corruptions]
        assert len(ids) == len(set(ids)), "Duplicate corruption IDs found"

    def test_corruptions_have_all_required_fields(self):
        rows = _make_sample_rows(100)
        plan = generate_corruptions(rows, injection_rate=0.07, seed=42)
        for c in plan.corruptions:
            assert c.corruption_id.startswith("CHAOS-")
            assert c.dimension in DQ_DIMENSIONS
            assert c.strategy
            assert c.description
            assert c.field_name
            assert c.row_identifier.startswith("shadow-row-")
            assert c.expected_detection

    def test_seed_produces_reproducible_output(self):
        rows = _make_sample_rows(100)
        plan1 = generate_corruptions(rows, injection_rate=0.07, seed=42)
        plan2 = generate_corruptions(rows, injection_rate=0.07, seed=42)
        ids1 = [c.corruption_id for c in plan1.corruptions]
        ids2 = [c.corruption_id for c in plan2.corruptions]
        assert ids1 == ids2

    def test_different_seeds_produce_different_output(self):
        rows = _make_sample_rows(100)
        plan1 = generate_corruptions(rows, injection_rate=0.07, seed=42)
        plan2 = generate_corruptions(rows, injection_rate=0.07, seed=99)
        descs1 = [c.description for c in plan1.corruptions]
        descs2 = [c.description for c in plan2.corruptions]
        assert descs1 != descs2


class TestInjectionPlan:
    """InjectionPlan tracks dimension coverage correctly."""

    def test_empty_plan_no_coverage(self):
        plan = InjectionPlan()
        assert not plan.all_dimensions_covered
        for dim in DQ_DIMENSIONS:
            assert not plan.dimension_coverage[dim]

    def test_partial_coverage_detected(self):
        plan = InjectionPlan()
        plan.corruptions.append(Corruption(
            corruption_id="CHAOS-00001", dimension="completeness",
            strategy="test", description="test", field_name="cik",
            original_value="1", corrupted_value=None,
            row_identifier="row-1", expected_detection="test",
        ))
        assert plan.dimension_coverage["completeness"] is True
        assert plan.dimension_coverage["validity"] is False
        assert not plan.all_dimensions_covered
