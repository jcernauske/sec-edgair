"""Tests for system prompt generation.

Integration tests — requires Iceberg data for full prompt generation.
"""

import pytest

from src.ai_ready.tools.db import get_db, reset_db


@pytest.fixture(autouse=True, scope="module")
def _load_db():
    get_db()
    yield
    reset_db()


class TestSystemPrompt:
    """Tests for system prompt generation."""

    def test_builds_prompt(self):
        from src.ai_ready.chat.system_prompt import build_system_prompt
        prompt = build_system_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 500

    def test_prompt_contains_companies(self):
        from src.ai_ready.chat.system_prompt import build_system_prompt
        prompt = build_system_prompt()
        assert "AAPL" in prompt
        assert "MSFT" in prompt

    def test_prompt_contains_metrics(self):
        from src.ai_ready.chat.system_prompt import build_system_prompt
        prompt = build_system_prompt()
        assert "BT-022" in prompt or "Revenue" in prompt

    def test_prompt_contains_ratios(self):
        from src.ai_ready.chat.system_prompt import build_system_prompt
        prompt = build_system_prompt()
        assert "RATIO-" in prompt or "Net Margin" in prompt

    def test_prompt_contains_anomaly_guidance(self):
        from src.ai_ready.chat.system_prompt import build_system_prompt
        prompt = build_system_prompt()
        assert "Boeing" in prompt or "anomal" in prompt.lower()

    def test_prompt_contains_formatting_instructions(self):
        from src.ai_ready.chat.system_prompt import build_system_prompt
        prompt = build_system_prompt()
        assert "fiscal year" in prompt.lower()
