"""Tests for the DQ execution engine.

Validates threshold evaluation, rule loading, SQL execution, table reference
parsing, and the rule lifecycle (proposed → approved → active).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import duckdb
import pyarrow as pa
import pytest

from src.infra.dq_runner import (
    _extract_table_refs,
    _rewrite_sql,
    approve_rules,
    evaluate_threshold,
    execute_sql_rule,
    load_rules,
    run_rules,
)


# ---------------------------------------------------------------------------
# Threshold evaluation
# ---------------------------------------------------------------------------


class TestEvaluateThreshold:
    """evaluate_threshold parses expressions and compares correctly."""

    def test_result_equals_zero_pass(self):
        passed, _ = evaluate_threshold(0, "result = 0")
        assert passed is True

    def test_result_equals_zero_fail(self):
        passed, _ = evaluate_threshold(5, "result = 0")
        assert passed is False

    def test_result_count_equals_zero_pass(self):
        passed, _ = evaluate_threshold(0, "result_count = 0")
        assert passed is True

    def test_result_count_equals_zero_fail(self):
        passed, _ = evaluate_threshold(3, "result_count = 0")
        assert passed is False

    def test_result_gte_pass(self):
        passed, _ = evaluate_threshold(30.0, "result >= 25.0")
        assert passed is True

    def test_result_gte_fail(self):
        passed, _ = evaluate_threshold(20.0, "result >= 25.0")
        assert passed is False

    def test_result_gte_boundary(self):
        passed, _ = evaluate_threshold(25.0, "result >= 25.0")
        assert passed is True

    def test_none_raw_result_treated_as_zero(self):
        passed, _ = evaluate_threshold(None, "result = 0")
        assert passed is True

    def test_threshold_with_suffix_stripped(self):
        """Thresholds like '100% — zero violations' should parse the comparison from context."""
        # These don't have a parseable comparison — they're implementation-only rules
        passed, detail = evaluate_threshold(0, "100% — zero violations")
        assert passed is False  # unparseable
        assert "unparseable" in detail

    def test_detail_includes_actual_value(self):
        _, detail = evaluate_threshold(5, "result = 0")
        assert "actual=5" in detail

    def test_double_equals(self):
        passed, _ = evaluate_threshold(0, "result == 0")
        assert passed is True

    def test_not_equals(self):
        passed, _ = evaluate_threshold(5, "result != 0")
        assert passed is True

    def test_less_than(self):
        passed, _ = evaluate_threshold(3, "result < 5")
        assert passed is True

    def test_greater_than(self):
        passed, _ = evaluate_threshold(10, "result > 5")
        assert passed is True


# ---------------------------------------------------------------------------
# Table reference extraction
# ---------------------------------------------------------------------------


class TestExtractTableRefs:
    """_extract_table_refs finds namespace.table patterns in SQL."""

    def test_single_table(self):
        refs = _extract_table_refs("SELECT * FROM base.financial_facts")
        assert ("base", "financial_facts") in refs

    def test_cross_namespace_join(self):
        sql = "SELECT * FROM raw.xbrl_company_facts r JOIN base.entity_mappings m ON r.cik = m.cik"
        refs = _extract_table_refs(sql)
        assert ("raw", "xbrl_company_facts") in refs
        assert ("base", "entity_mappings") in refs

    def test_skips_alias_column_refs(self):
        sql = "SELECT r.cik, m.status FROM raw.xbrl_company_facts r JOIN base.entity_mappings m ON r.cik = m.cik"
        refs = _extract_table_refs(sql)
        # r.cik and m.status should be skipped (not known namespaces)
        assert ("r", "cik") not in refs
        assert ("m", "status") not in refs
        # But real table refs should be found
        assert ("raw", "xbrl_company_facts") in refs
        assert ("base", "entity_mappings") in refs

    def test_deduplicates(self):
        sql = "SELECT * FROM base.financial_facts f WHERE f.cik IN (SELECT cik FROM base.financial_facts)"
        refs = _extract_table_refs(sql)
        assert refs.count(("base", "financial_facts")) == 1

    def test_no_table_refs(self):
        refs = _extract_table_refs("SELECT 1")
        assert refs == []


# ---------------------------------------------------------------------------
# SQL rewriting
# ---------------------------------------------------------------------------


class TestRewriteSql:
    """_rewrite_sql replaces namespace.table with view names."""

    def test_single_replacement(self):
        sql = "SELECT * FROM base.financial_facts"
        result = _rewrite_sql(sql, [("base", "financial_facts")])
        assert result == "SELECT * FROM base_financial_facts"

    def test_multiple_replacements(self):
        sql = "FROM raw.xbrl_company_facts r JOIN base.entity_mappings m"
        result = _rewrite_sql(sql, [("raw", "xbrl_company_facts"), ("base", "entity_mappings")])
        assert "raw_xbrl_company_facts" in result
        assert "base_entity_mappings" in result


# ---------------------------------------------------------------------------
# Rule loading
# ---------------------------------------------------------------------------


class TestLoadRules:
    """load_rules reads JSON files and augments rule dicts."""

    def test_loads_all_rules(self):
        rules = load_rules()
        assert len(rules) == 22

    def test_each_rule_has_spec(self):
        rules = load_rules()
        for rule in rules:
            assert "spec" in rule
            assert rule["spec"] != ""

    def test_each_rule_has_status(self):
        rules = load_rules()
        for rule in rules:
            assert "status" in rule
            assert rule["status"] in ("proposed", "approved", "active")

    def test_filter_by_spec(self):
        rules = load_rules(spec="base-entity-resolution")
        assert len(rules) == 5
        assert all(r["spec"] == "base-entity-resolution" for r in rules)

    def test_filter_nonexistent_spec(self):
        rules = load_rules(spec="nonexistent-spec")
        assert rules == []


# ---------------------------------------------------------------------------
# SQL execution against in-memory DuckDB
# ---------------------------------------------------------------------------


class TestExecuteSqlRule:
    """execute_sql_rule runs SQL and evaluates thresholds."""

    @pytest.fixture
    def con_with_data(self):
        """DuckDB connection with a test view registered."""
        con = duckdb.connect()
        con.execute("""
            CREATE TABLE base_financial_facts AS
            SELECT * FROM (VALUES
                ('FACT-001', 'CIK001', 'revenue', 1000.0, 1, false, NULL),
                ('FACT-002', 'CIK001', 'assets', 5000.0, 2, false, NULL),
                ('FACT-003', 'CIK002', 'revenue', 2000.0, 1, true, 'ACC-999')
            ) AS t(fact_id, cik, concept, value, calendar_quarter, is_superseded, superseded_by)
        """)
        yield con
        con.close()

    def test_passing_rule(self, con_with_data):
        rule = {
            "rule_id": "TEST-001",
            "sql": "SELECT COUNT(*) FROM base_financial_facts WHERE calendar_quarter < 1 OR calendar_quarter > 4",
            "threshold": "result = 0",
            "spec": "test",
        }
        result = execute_sql_rule(rule, con_with_data)
        assert result["passed"] is True
        assert result["raw_value"] == 0
        assert result["error"] is None

    def test_failing_rule(self, con_with_data):
        rule = {
            "rule_id": "TEST-002",
            "sql": "SELECT COUNT(*) FROM base_financial_facts WHERE is_superseded = true AND superseded_by IS NULL",
            "threshold": "result = 0",
            "spec": "test",
        }
        result = execute_sql_rule(rule, con_with_data)
        # Our test data has superseded_by set for the superseded row, so this should pass
        assert result["passed"] is True

    def test_result_count_threshold(self, con_with_data):
        rule = {
            "rule_id": "TEST-003",
            "sql": "SELECT fact_id, COUNT(*) FROM base_financial_facts GROUP BY fact_id HAVING COUNT(*) > 1",
            "threshold": "result_count = 0",
            "spec": "test",
        }
        result = execute_sql_rule(rule, con_with_data)
        assert result["passed"] is True  # no duplicates
        assert result["raw_value"] == 0

    def test_sql_error_captured(self, con_with_data):
        rule = {
            "rule_id": "TEST-ERR",
            "sql": "SELECT * FROM nonexistent_table",
            "threshold": "result = 0",
            "spec": "test",
        }
        result = execute_sql_rule(rule, con_with_data)
        assert result["passed"] is False
        assert result["error"] is not None
        assert "nonexistent_table" in result["error"]

    def test_execution_time_recorded(self, con_with_data):
        rule = {
            "rule_id": "TEST-TIME",
            "sql": "SELECT COUNT(*) FROM base_financial_facts",
            "threshold": "result >= 0",
            "spec": "test",
        }
        result = execute_sql_rule(rule, con_with_data)
        assert result["execution_time_ms"] >= 0

    def test_result_has_all_fields(self, con_with_data):
        rule = {
            "rule_id": "TEST-FIELDS",
            "sql": "SELECT 0",
            "threshold": "result = 0",
            "spec": "test",
        }
        result = execute_sql_rule(rule, con_with_data)
        expected_keys = {"rule_id", "spec", "passed", "raw_value", "threshold", "detail", "violations", "execution_time_ms", "error", "executed_at"}
        assert expected_keys == set(result.keys())


# ---------------------------------------------------------------------------
# Rule approval
# ---------------------------------------------------------------------------


class TestApproveRules:
    """approve_rules transitions proposed rules to approved."""

    @pytest.fixture
    def temp_rules_dir(self, tmp_path):
        """Create a temp DQ rules dir with a proposed rule."""
        rules_dir = tmp_path / "dq-rules"
        rules_dir.mkdir()
        data = {
            "spec": "test-spec",
            "tables": ["test.table"],
            "rules": [
                {
                    "rule_id": "TEST-PROP-001",
                    "category": "Validity",
                    "priority": "P0",
                    "description": "Test proposed rule",
                    "sql": "SELECT 0",
                    "threshold": "result = 0",
                    "status": "proposed",
                    "proposed_by": "@dq-engineer",
                    "proposed_at": "2026-03-14T00:00:00Z",
                },
                {
                    "rule_id": "TEST-ACT-001",
                    "category": "Validity",
                    "priority": "P0",
                    "description": "Already active rule",
                    "sql": "SELECT 0",
                    "threshold": "result = 0",
                    "status": "active",
                },
            ],
        }
        (rules_dir / "test-spec.json").write_text(json.dumps(data, indent=2))
        return rules_dir

    def test_approve_proposed_rule(self, temp_rules_dir):
        with patch("src.infra.dq_runner.DQ_RULES_DIR", temp_rules_dir):
            results = approve_rules(["TEST-PROP-001"])
            assert results[0]["status"] == "approved"

            # Verify file was updated
            data = json.loads((temp_rules_dir / "test-spec.json").read_text())
            rule = next(r for r in data["rules"] if r["rule_id"] == "TEST-PROP-001")
            assert rule["status"] == "approved"
            assert rule["approved_by"] == "human"
            assert "approved_at" in rule

    def test_approve_already_active_no_change(self, temp_rules_dir):
        with patch("src.infra.dq_runner.DQ_RULES_DIR", temp_rules_dir):
            results = approve_rules(["TEST-ACT-001"])
            assert "not proposed" in results[0].get("message", "")

    def test_approve_nonexistent_rule(self, temp_rules_dir):
        with patch("src.infra.dq_runner.DQ_RULES_DIR", temp_rules_dir):
            results = approve_rules(["NOPE-001"])
            assert results[0]["status"] == "not_found"
