"""Tests for chaos manifest write/read roundtrip."""

from __future__ import annotations

import datetime
import json
from pathlib import Path

import pytest

from src.infra.chaos_monkey.injector import Corruption, InjectionPlan
from src.infra.chaos_monkey.manifest import read_manifest, write_manifest


@pytest.fixture
def sample_plan() -> InjectionPlan:
    plan = InjectionPlan()
    plan.corruptions = [
        Corruption(
            corruption_id="CHAOS-00001", dimension="completeness",
            strategy="null_required_field",
            description="Set cik to NULL",
            field_name="cik", original_value="320193", corrupted_value=None,
            row_identifier="shadow-row-00001",
            expected_detection="Any NOT NULL check on cik",
        ),
        Corruption(
            corruption_id="CHAOS-00002", dimension="uniqueness",
            strategy="full_row_duplicate",
            description="Exact row copy",
            field_name="*", original_value="existing", corrupted_value="duplicate",
            row_identifier="shadow-row-00002",
            expected_detection="Any uniqueness rule",
        ),
    ]
    plan.corrupted_rows = [{"cik": None}, {"cik": 320193}]
    return plan


class TestManifestRoundtrip:
    """Write and read manifests preserve all data."""

    def test_write_read_roundtrip(self, sample_plan, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "src.infra.chaos_monkey.manifest.CHAOS_MANIFESTS_DIR", tmp_path
        )

        path = write_manifest(
            sample_plan,
            source_table="raw.xbrl_company_facts",
            source_row_count=1000,
            injection_rate=0.07,
            run_id="chaos-test-001",
        )

        assert path.exists()
        manifest = read_manifest(path)
        assert manifest["run_id"] == "chaos-test-001"
        assert manifest["source_table"] == "raw.xbrl_company_facts"
        assert manifest["source_row_count"] == 1000
        assert manifest["injected_row_count"] == 2
        assert manifest["injection_rate"] == 0.07
        assert len(manifest["injections"]) == 2
        assert manifest["injections"][0]["corruption_id"] == "CHAOS-00001"
        assert manifest["injections"][0]["dimension"] == "completeness"

    def test_manifest_has_all_required_fields(self, sample_plan, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "src.infra.chaos_monkey.manifest.CHAOS_MANIFESTS_DIR", tmp_path
        )

        path = write_manifest(
            sample_plan,
            source_table="raw.xbrl_company_facts",
            source_row_count=500,
            injection_rate=0.05,
        )

        manifest = read_manifest(path)
        required_keys = {
            "run_id", "timestamp", "environment", "source_table",
            "source_row_count", "injected_row_count", "injection_rate",
            "dimension_coverage", "injections",
        }
        assert required_keys.issubset(manifest.keys())

        injection_keys = {
            "corruption_id", "dimension", "strategy", "description",
            "field", "original_value", "corrupted_value",
            "row_identifier", "expected_detection",
        }
        for inj in manifest["injections"]:
            assert injection_keys.issubset(inj.keys())

    def test_manifest_filename_is_timestamped(self, sample_plan, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "src.infra.chaos_monkey.manifest.CHAOS_MANIFESTS_DIR", tmp_path
        )

        path = write_manifest(
            sample_plan,
            source_table="raw.xbrl_company_facts",
            source_row_count=100,
            injection_rate=0.07,
        )
        assert path.name.startswith("chaos-manifest-")
        assert path.suffix == ".json"
