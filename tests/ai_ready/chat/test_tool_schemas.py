"""Tests for tool schema definitions.

Pure unit tests — validates the schema structure without calling Claude.
"""

from src.ai_ready.chat.tool_schemas import get_tool_definitions


class TestToolSchemas:
    """Tests for tool schema definitions."""

    def test_returns_7_tools(self):
        tools = get_tool_definitions()
        assert len(tools) == 7

    def test_all_tools_have_required_fields(self):
        tools = get_tool_definitions()
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool
            assert tool["input_schema"]["type"] == "object"
            assert "properties" in tool["input_schema"]
            assert "required" in tool["input_schema"]

    def test_tool_names(self):
        tools = get_tool_definitions()
        names = {t["name"] for t in tools}
        expected = {
            "get_company_metric",
            "get_company_profile",
            "compare_companies",
            "rank_companies",
            "get_company_trend",
            "get_sector_summary",
            "get_ratio",
        }
        assert names == expected

    def test_get_company_metric_schema(self):
        tools = get_tool_definitions()
        tool = next(t for t in tools if t["name"] == "get_company_metric")
        assert "ticker" in tool["input_schema"]["properties"]
        assert "metric" in tool["input_schema"]["properties"]
        assert "ticker" in tool["input_schema"]["required"]
        assert "metric" in tool["input_schema"]["required"]

    def test_compare_companies_schema(self):
        tools = get_tool_definitions()
        tool = next(t for t in tools if t["name"] == "compare_companies")
        assert "ticker_a" in tool["input_schema"]["properties"]
        assert "ticker_b" in tool["input_schema"]["properties"]
        assert "metrics" in tool["input_schema"]["properties"]

    def test_rank_companies_has_sector_filter(self):
        tools = get_tool_definitions()
        tool = next(t for t in tools if t["name"] == "rank_companies")
        assert "sector" in tool["input_schema"]["properties"]
        assert "top_n" in tool["input_schema"]["properties"]

    def test_get_ratio_schema(self):
        tools = get_tool_definitions()
        tool = next(t for t in tools if t["name"] == "get_ratio")
        assert "ticker" in tool["input_schema"]["required"]
        assert "ratio" in tool["input_schema"]["required"]
