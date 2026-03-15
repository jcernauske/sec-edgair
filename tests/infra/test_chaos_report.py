"""Tests for the comprehensive After-Action Report (AAR)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.infra.chaos_monkey.config import DQ_DIMENSIONS
from src.infra.chaos_monkey.report import generate_aar, write_after_action_report


def _make_manifest() -> dict:
    injections = []
    for i, dim in enumerate(DQ_DIMENSIONS):
        for j in range(3):
            injections.append({
                "corruption_id": f"CHAOS-{i*3+j+1:05d}",
                "dimension": dim,
                "strategy": f"test_{dim}",
                "description": f"Test corruption for {dim} #{j}",
                "field": "test_field",
                "original_value": "original",
                "corrupted_value": "corrupted",
                "row_identifier": f"shadow-row-{i*3+j+1:05d}",
                "expected_detection": f"Any {dim} rule",
            })
    return {
        "run_id": "chaos-test-001",
        "timestamp": "2026-03-15T14:00:00Z",
        "source_table": "raw.xbrl_company_facts",
        "source_row_count": 1000,
        "injected_row_count": 30,
        "injection_rate": 0.07,
        "dimension_coverage": {d: True for d in DQ_DIMENSIONS},
        "injections": injections,
    }


def _make_dq_results(failed_dims: list[str]) -> list[dict]:
    results = []
    for dim in failed_dims:
        results.append({
            "rule_id": f"TEST-{dim.upper()}-001",
            "category": dim.replace("_", " ").title(),
            "passed": False,
            "raw_value": 5,
            "violations": 5,
            "threshold": "result = 0",
            "detail": f"Found 5 violations in {dim}",
        })
    # Some passing rules
    results.append({
        "rule_id": "TEST-CLEAN-001",
        "category": "Completeness",
        "passed": True,
        "raw_value": 0,
        "violations": 0,
        "threshold": "result = 0",
    })
    return results


def _make_reconciliation(gate: str = "PASS") -> dict:
    dim_summary = {}
    for dim in DQ_DIMENSIONS:
        if gate == "PASS":
            dim_summary[dim] = {"injected": 3, "caught": 3, "missed": 0, "miss_rate": 0.0, "status": "PASS"}
        else:
            status = "P0 FAIL" if dim == "accuracy" else "PASS"
            missed = 3 if dim == "accuracy" else 0
            dim_summary[dim] = {"injected": 3, "caught": 3 - missed, "missed": missed, "miss_rate": missed / 3, "status": status}
    return {
        "run_id": "chaos-test-001",
        "timestamp": "2026-03-15T14:00:00Z",
        "total_injected": 30,
        "total_detected": 30 if gate == "PASS" else 27,
        "total_undetected": 0 if gate == "PASS" else 3,
        "detection_rate": 1.0 if gate == "PASS" else 0.9,
        "gate_decision": gate,
        "dimension_summary": dim_summary,
        "undetected_corruptions": [] if gate == "PASS" else [
            {"corruption_id": "CHAOS-00013", "dimension": "accuracy", "description": "Set val to $1"},
            {"corruption_id": "CHAOS-00014", "dimension": "accuracy", "description": "Negated val"},
            {"corruption_id": "CHAOS-00015", "dimension": "accuracy", "description": "Set val to $1"},
        ],
        "dq_failures_matched": 10 if gate == "PASS" else 9,
    }


class TestGenerateAAR:
    """Comprehensive AAR contains all 5 sections."""

    def test_pass_report_has_all_sections(self):
        manifest = _make_manifest()
        dq_results = _make_dq_results(DQ_DIMENSIONS)
        reconciliation = _make_reconciliation("PASS")
        report = generate_aar(manifest, dq_results, [], reconciliation)

        assert "## 1. Injection Summary" in report
        assert "## 2. DQ Results Against Shadow Zone" in report
        assert "## 3. Reconciliation" in report
        assert "## 4. Gate Decision" in report
        assert "## 5. Suggested Remediations" in report
        assert "## 6. Artifacts" in report

    def test_fail_report_shows_remediations(self):
        manifest = _make_manifest()
        dq_results = _make_dq_results([d for d in DQ_DIMENSIONS if d != "accuracy"])
        reconciliation = _make_reconciliation("P0 FAIL")
        report = generate_aar(manifest, dq_results, [], reconciliation)

        assert "P0 FAIL" in report
        assert "Accuracy" in report
        assert "Suggested Remediations" in report
        assert "statistical outlier" in report.lower() or "outlier" in report.lower()

    def test_pass_report_shows_hardening_suggestions(self):
        manifest = _make_manifest()
        dq_results = _make_dq_results(DQ_DIMENSIONS)
        reconciliation = _make_reconciliation("PASS")
        report = generate_aar(manifest, dq_results, [], reconciliation)

        assert "No remediations required" in report
        assert "Hardening suggestions" in report

    def test_dq_results_section_shows_failures(self):
        manifest = _make_manifest()
        failed = ["completeness", "validity"]
        dq_results = _make_dq_results(failed)
        reconciliation = _make_reconciliation("P0 FAIL")
        report = generate_aar(manifest, dq_results, [], reconciliation)

        assert "Failed Rules" in report
        assert "TEST-COMPLETENESS-001" in report
        assert "TEST-VALIDITY-001" in report

    def test_dimension_scorecard_present(self):
        manifest = _make_manifest()
        dq_results = _make_dq_results(DQ_DIMENSIONS)
        reconciliation = _make_reconciliation("PASS")
        report = generate_aar(manifest, dq_results, [], reconciliation)

        assert "Dimension Scorecard" in report
        for dim in DQ_DIMENSIONS:
            assert dim.replace("_", " ").title() in report


class TestWriteAAR:
    """AAR writes to disk correctly."""

    def test_write_creates_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.infra.chaos_monkey.report.CHAOS_REPORTS_DIR", tmp_path)
        manifest = _make_manifest()
        dq_results = _make_dq_results(DQ_DIMENSIONS)
        reconciliation = _make_reconciliation("PASS")
        path = write_after_action_report(manifest, dq_results, [], reconciliation)
        assert path.exists()
        assert path.name.startswith("chaos-aar-")
        assert path.suffix == ".md"
        content = path.read_text()
        assert "After-Action Report" in content
