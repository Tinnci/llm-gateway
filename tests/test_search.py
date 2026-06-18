"""Tests for optional search tool wiring."""

from __future__ import annotations

from homeassistant.helpers import llm

from custom_components.llm_gateway.const import CONF_SEARCH_ENABLED, CONF_TAVILY_API_KEY
from custom_components.llm_gateway.grounding import enrich_search_result_with_grounding
from custom_components.llm_gateway.search import (
    SEARCH_TOOL_NAME,
    available_search_tools,
    mark_external_tool_calls,
    search_providers_from_options,
)


def test_search_tools_require_enabled_provider():
    assert available_search_tools({}) == []
    assert (
        available_search_tools(
            {CONF_SEARCH_ENABLED: True, CONF_TAVILY_API_KEY: "tvly-test"}
        )[0]["function"]["name"]
        == SEARCH_TOOL_NAME
    )


def test_search_tool_calls_are_marked_external():
    calls = [
        llm.ToolInput(
            id="1",
            tool_name=SEARCH_TOOL_NAME,
            tool_args={"query": "最新天气"},
        ),
        llm.ToolInput(id="2", tool_name="HassTurnOn", tool_args={}),
    ]

    marked = mark_external_tool_calls(calls)
    assert marked[0].external
    assert not marked[1].external


def test_search_provider_order():
    providers = search_providers_from_options(
        {CONF_SEARCH_ENABLED: True, CONF_TAVILY_API_KEY: "k"}
    )
    assert [provider.name for provider in providers] == ["tavily"]


def test_search_result_extracts_source_candidates():
    result = enrich_search_result_with_grounding(
        {
            "provider": "mock",
            "query": "关关雎鸠 出处",
            "results": [
                {
                    "title": "《诗经》之《关雎》原文赏析",
                    "content": "关关雎鸠，在河之洲。",
                }
            ],
        }
    )

    assert result["source_candidates"] == ["诗经", "关雎"]
    assert "Do not rename titles" in result["grounding_instruction"]
