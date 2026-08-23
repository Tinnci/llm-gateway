"""Tests for the gateway-native tool registry."""

from __future__ import annotations

import inspect

from custom_components.llm_gateway.const import (
    CONF_SEARCH_ENABLED,
    CONF_TAVILY_API_KEY,
)
from custom_components.llm_gateway.tools_registry import (
    SEARCH_TOOL,
    enabled_external_tools,
    find_external_tool,
)


def test_search_tool_disabled_without_provider():
    assert enabled_external_tools({}) == ()


def test_search_tool_enabled_with_tavily_key():
    tools = enabled_external_tools(
        {CONF_SEARCH_ENABLED: True, CONF_TAVILY_API_KEY: "tvly-key"}
    )
    assert [t.name for t in tools] == ["search_web"]


def test_specs_shape_and_hint_lookup():
    specs = SEARCH_TOOL.build_specs(
        {CONF_SEARCH_ENABLED: True, CONF_TAVILY_API_KEY: "k"}
    )
    assert len(specs) == 1
    function = specs[0]["function"]
    assert function["name"] == "search_web"
    assert "query" in function["parameters"]["properties"]

    found = find_external_tool("search_web")
    assert found is not None
    assert found.spoken_hint
    assert find_external_tool("nonexistent") is None


async def test_execute_is_coroutine_factory():
    """Registry execute is an awaitable-returning callable."""
    assert inspect.iscoroutinefunction(SEARCH_TOOL.execute)
