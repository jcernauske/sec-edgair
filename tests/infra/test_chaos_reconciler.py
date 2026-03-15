"""Tests for the Chaos Monkey reconciliation engine.

Validates that the reconciler correctly matches chaos manifest
corruptions against DQ results and produces accurate coverage reports.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.infra.chaos_monkey.config import DQ_DIMENSIONS
from src.infra.chaos_reconciler import generate_report, reconcile, write_reconciliation_report


def _make_manifest(dimensions: list[str] | None = None) -> dict:
    """Create a test manifest with corruptions across specified dimensions."""
    if dimensions is None:
        dimensions = DQ_DIMENSIONS

    injections = []
    for i, dim in enumerate(dimensions):
        injections.append({
            "corruption_id": f"CHAOS-{i+1:05d}",
            "dimension": dim,
            "strategy": "test_strategy",
            "description": f"Test corruption for {dim}",
            "field": "test_field",
            "original_value": "original",
            "corrupted_value": "corrupted",
            "row_identifier": f"shadow-row-{i+1:05d}",
            "expected_detection": f"Any {dim} DQ rule",
        })

    return {
        "run_id": "chaos-test-001",
        "timestamp": "2026-03-15T14:00:00Z",
        "source_table": "raw.xbrl_company_facts",
        "source_row_count": 1000,
        "injected_row_count": len(injections),
        "injection_rate": 0.07,
        "dimension_coverage": {d: d in dimensions for d in DQ_DIMENSIONS},
        "injections": injections,
    }


def _make_dq_results(failed_dimensions: list[str]) -> list[dict]:
    """Create DQ results with failures in specified dimensions."""
    results = []
    for dim in failed_dimensions:
        results.append({
            "rule_id": f"TEST-{dim.upper()}-001",
            "category": dim.replace("_", " ").title(),
            "passed": False,
            "actual_value": 5,
            "threshold": "result = 0",
        })
    # Also add some passing rules
    results.append({
        "rule_id": "TEST-PASS-001",
        "category": "Completeness",
        "passed": True,
        "actual_value": 0,
        "threshold": "result = 0",
    })
    return results


class TestReconcile:
    """Reconciler correctly matches corruptions to DQ catches."""

    def test_all_detected_is_pass(self):
        manifest = _make_manifest()
        dq_results = _make_dq_results(DQ_DIMENSIONS)
        result = reconcile(manifest, dq_results)
        assert result["gate_decision"] == "PASS"
        assert result["total_undetected"] == 0

    def test_missing_dimension_is_p0_fail(self):
        manifest = _make_manifest()
        # DQ catches everything EXCEPT accuracy
        caught = [d for d in DQ_DIMENSIONS if d != "accuracy"]
        dq_results = _make_dq_results(caught)
        result = reconcile(manifest, dq_results)
        assert result["gate_decision"] == "P0 FAIL"
        assert result["total_undetected"] >= 1
        assert result["dimension_summary"]["accuracy"]["status"] == "P0 FAIL"

    def test_empty_dq_results_is_total_fail(self):
        manifest = _make_manifest()
        result = reconcile(manifest, [])
        assert result["gate_decision"] == "P0 FAIL"
        assert result["total_undetected"] == result["total_injected"]

    def test_detection_rate_calculation(self):
        manifest = _make_manifest()
        # Catch 8 out of 10 dimensions
        caught = DQ_DIMENSIONS[:8]
        dq_results = _make_dq_results(caught)
        result = reconcile(manifest, dq_results)
        assert result["detection_rate"] == 0.8  # 8/10

    def test_dimension_summary_structure(self):
        manifest = _make_manifest()
        dq_results = _make_dq_results(DQ_DIMENSIONS)
        result = reconcile(manifest, dq_results)
        for dim in DQ_DIMENSIONS:
            summary = result["dimension_summary"][dim]
            assert "injected" in summary
            assert "caught" in summary
            assert "missed" in summary
            assert "miss_rate" in summary
            assert "status" in summary


class TestGenerateReport:
    """Report generation produces valid markdown."""

    def test_pass_report_contains_pass(self):
        manifest = _make_manifest()
        dq_results = _make_dq_results(DQ_DIMENSIONS)
        result = reconcile(manifest, dq_results)
        report = generate_report(result)
        assert "PASS" in report
        assert "Chaos Monkey Reconciliation Report" in report

    def test_fail_report_contains_undetected(self):
        manifest = _make_manifest()
        caught = [d for d in DQ_DIMENSIONS if d != "freshness"]
        dq_results = _make_dq_results(caught)
        result = reconcile(manifest, dq_results)
        report = generate_report(result)
        assert "FAIL" in report
        assert "Freshness" in report

    def test_report_has_dimension_table(self):
        manifest = _make_manifest()
        dq_results = _make_dq_results(DQ_DIMENSIONS)
        result = reconcile(manifest, dq_results)
        report = generate_report(result)
        assert "| Dimension |" in report
        assert "Completeness" in report

    def test_write_report_to_disk(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "src.infra.chaos_reconciler.CHAOS_MANIFESTS_DIR", tmp_path
        )
        manifest = _make_manifest()
        dq_results = _make_dq_results(DQ_DIMENSIONS)
        result = reconcile(manifest, dq_results)
        path = write_reconciliation_report(result)
        assert path.exists()
        assert path.name.startswith("reconciliation-")
        content = path.read_text()
        assert "Chaos Monkey Reconciliation Report" in content
