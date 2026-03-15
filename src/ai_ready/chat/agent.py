"""Claude API agent with tool use loop.

Handles the conversation lifecycle:
1. Build system prompt with real data context
2. Send user message + conversation history to Claude
3. Execute any tool calls Claude makes
4. Return tool results to Claude for synthesis
5. Extract final text response
"""

from __future__ import annotations

import json
import logging

import anthropic

from src.ai_ready.tools.financial_tools import (
    compare_companies,
    get_company_metric,
    get_company_profile,
    get_company_trend,
    get_ratio,
    get_sector_summary,
    rank_companies,
)

from .system_prompt import build_system_prompt
from .tool_schemas import get_tool_definitions

logger = logging.getLogger(__name__)

# Map tool names to functions
TOOL_FUNCTIONS = {
    "get_company_metric": get_company_metric,
    "get_company_profile": get_company_profile,
    "compare_companies": compare_companies,
    "rank_companies": rank_companies,
    "get_company_trend": get_company_trend,
    "get_sector_summary": get_sector_summary,
    "get_ratio": get_ratio,
}

DEFAULT_MODEL = "claude-sonnet-4-5-20250514"
MAX_TOKENS = 4096


def execute_tool_call(tool_name: str, tool_input: dict) -> str:
    """Execute a single tool call and return the result as a JSON string."""
    func = TOOL_FUNCTIONS.get(tool_name)
    if func is None:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    try:
        result = func(**tool_input)
        return json.dumps(result, default=str)
    except Exception as e:
        logger.error("Tool %s failed: %s", tool_name, e)
        return json.dumps({"error": f"Tool execution failed: {str(e)}"})


def chat(
    user_message: str,
    history: list[dict],
    *,
    model: str = DEFAULT_MODEL,
    client: anthropic.Anthropic | None = None,
) -> tuple[str, list[dict]]:
    """Send a user message and return Claude's response.

    Args:
        user_message: The user's question.
        history: Conversation history (list of message dicts).
        model: Claude model to use.
        client: Anthropic client (created if not provided).

    Returns:
        Tuple of (response_text, updated_history).
    """
    if client is None:
        client = anthropic.Anthropic()

    system_prompt = build_system_prompt()
    tools = get_tool_definitions()

    # Build messages
    messages = list(history) + [{"role": "user", "content": user_message}]

    # Send to Claude
    response = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        tools=tools,
        messages=messages,
    )

    # Tool use loop
    while response.stop_reason == "tool_use":
        # Execute all tool calls
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                logger.info("Tool call: %s(%s)", block.name, json.dumps(block.input))
                result = execute_tool_call(block.name, block.input)
                logger.info("Tool result: %s", result[:200])
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        # Send tool results back
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

        response = client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            tools=tools,
            messages=messages,
        )

    # Extract text response
    text_blocks = [b.text for b in response.content if hasattr(b, "text")]
    response_text = "\n".join(text_blocks)

    # Update history
    messages.append({"role": "assistant", "content": response.content})

    return response_text, messages
