"""Tests for the gateway-native tool registry."""

from __future__ import annotations

import asyncio
import inspect

from custom_components.llm_gateway.const import (
    CONF_SEARCH_ENABLED,
    CONF_TAVILY_API_KEY,
)
from custom_components.llm_gateway.tools_registry import (
    SEARCH_TOOL,
    enabled_external_tools,
    execute_external_tools,
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


def _no_specs(_options):
    return []


async def test_execute_is_coroutine_factory():
    """Registry execute is an awaitable-returning callable."""
    assert inspect.iscoroutinefunction(SEARCH_TOOL.execute)


async def test_execute_external_tools_runs_concurrently_in_order():
    started: list[str] = []
    executor_started: list[str] = []
    finished: list[str] = []
    both_started = asyncio.Event()

    async def slow_execute(_session, _options, call):
        executor_started.append(call.tool_name)
        if len(executor_started) == 2:
            both_started.set()
        await asyncio.wait_for(both_started.wait(), timeout=1)
        return {"ok": call.tool_name}

    def make_call(name):
        return type("Call", (), {"tool_name": name, "tool_args": {}, "id": name})()

    calls = [
        (make_call("a"), SEARCH_TOOL),
        (make_call("b"), SEARCH_TOOL),
    ]
    # SEARCH_TOOL.execute is the real search executor; stub it locally.
    calls[0] = (
        calls[0][0],
        type(calls[0][1])(
            name="a", spoken_hint="h", build_specs=_no_specs, execute=slow_execute
        ),
    )
    calls[1] = (
        calls[1][0],
        type(calls[1][1])(
            name="b", spoken_hint="h", build_specs=_no_specs, execute=slow_execute
        ),
    )

    results = await execute_external_tools(
        calls,
        None,
        {},
        on_start=lambda call: started.append(call.tool_name),
        on_result=lambda call, _result: finished.append(call.tool_name),
    )

    assert [call.tool_name for call, _result in results] == ["a", "b"]
    assert started == ["a", "b"]
    assert executor_started == ["a", "b"]
    assert set(finished) == {"a", "b"}
