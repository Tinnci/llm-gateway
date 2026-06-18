"""Optional web-search tools for routed assistant turns."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any
from urllib.parse import urlencode

import aiohttp
from homeassistant.helpers import llm

from .const import (
    CONF_BRAVE_API_KEY,
    CONF_FIRECRAWL_API_KEY,
    CONF_SEARCH_ENABLED,
    CONF_SERPER_API_KEY,
    CONF_TAVILY_API_KEY,
    LOGGER,
)

SEARCH_TOOL_NAME = "search_web"
_DEFAULT_MAX_RESULTS = 5

SEARCH_TOOL_SPEC: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": SEARCH_TOOL_NAME,
        "description": (
            "Search the web for current external facts, device manuals, firmware, "
            "compatibility, error codes, weather, news, traffic, prices, or "
            "source/origin verification for quotations and named works. "
            "Never use this for direct Home Assistant control."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Focused search query.",
                },
                "freshness": {
                    "type": "string",
                    "enum": ["day", "week", "month", "year", "any"],
                    "description": "Freshness requirement for results.",
                },
                "max_results": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 8,
                    "description": "Maximum number of search results.",
                },
            },
            "required": ["query"],
        },
    },
}


@dataclass(frozen=True, slots=True)
class SearchProvider:
    """Resolved search provider credentials."""

    name: str
    api_key: str


def search_providers_from_options(options: dict[str, Any]) -> list[SearchProvider]:
    """Return enabled providers in priority order."""
    if not options.get(CONF_SEARCH_ENABLED):
        return []

    providers: list[SearchProvider] = []
    for name, option_key, env_key in (
        ("tavily", CONF_TAVILY_API_KEY, "TAVILY_API_KEY"),
        ("serper", CONF_SERPER_API_KEY, "SERPER_API_KEY"),
        ("firecrawl", CONF_FIRECRAWL_API_KEY, "FIRECRAWL_API_KEY"),
        ("brave", CONF_BRAVE_API_KEY, "BRAVE_API_KEY"),
    ):
        key = (options.get(option_key) or os.environ.get(env_key) or "").strip()
        if key:
            providers.append(SearchProvider(name, key))
    return providers


def available_search_tools(options: dict[str, Any]) -> list[dict[str, Any]]:
    """Return OpenAI tool specs for enabled search providers."""
    return [SEARCH_TOOL_SPEC] if search_providers_from_options(options) else []


def mark_external_tool_calls(calls: list[llm.ToolInput]) -> list[llm.ToolInput]:
    """Mark locally handled tool calls as external to Home Assistant."""
    marked: list[llm.ToolInput] = []
    for call in calls:
        if call.tool_name == SEARCH_TOOL_NAME:
            marked.append(
                llm.ToolInput(
                    id=call.id,
                    tool_name=call.tool_name,
                    tool_args=call.tool_args,
                    external=True,
                )
            )
        else:
            marked.append(call)
    return marked


async def async_execute_search_tool(
    session: aiohttp.ClientSession,
    options: dict[str, Any],
    tool_call: llm.ToolInput,
) -> dict[str, Any]:
    """Execute a local search tool call and return a compact result."""
    query = str(tool_call.tool_args.get("query") or "").strip()
    max_results = _bounded_max_results(tool_call.tool_args.get("max_results"))
    if not query:
        return {"error": "missing_query"}

    providers = search_providers_from_options(options)
    if not providers:
        return {"error": "search_unconfigured"}

    last_error: str | None = None
    for provider in providers:
        started = time.monotonic()
        try:
            result = await _async_search_provider(session, provider, query, max_results)
        except (TimeoutError, TypeError, aiohttp.ClientError, ValueError) as err:
            last_error = type(err).__name__
            LOGGER.warning(
                "Search provider failed provider=%s latency_ms=%d error=%s",
                provider.name,
                int((time.monotonic() - started) * 1000),
                last_error,
            )
            continue

        LOGGER.info(
            "Search provider completed provider=%s latency_ms=%d result_count=%d",
            provider.name,
            int((time.monotonic() - started) * 1000),
            len(result.get("results", [])),
        )
        return result

    return {"error": "search_failed", "last_error": last_error or "unknown"}


async def _async_search_provider(
    session: aiohttp.ClientSession,
    provider: SearchProvider,
    query: str,
    max_results: int,
) -> dict[str, Any]:
    if provider.name == "tavily":
        return await _async_tavily(session, provider.api_key, query, max_results)
    if provider.name == "serper":
        return await _async_serper(session, provider.api_key, query, max_results)
    if provider.name == "firecrawl":
        return await _async_firecrawl(session, provider.api_key, query, max_results)
    if provider.name == "brave":
        return await _async_brave(session, provider.api_key, query, max_results)
    raise ValueError(f"Unknown provider {provider.name}")


async def _async_tavily(
    session: aiohttp.ClientSession, api_key: str, query: str, max_results: int
) -> dict[str, Any]:
    async with session.post(
        "https://api.tavily.com/search",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"query": query, "max_results": max_results, "search_depth": "basic"},
        timeout=aiohttp.ClientTimeout(total=15),
    ) as resp:
        data = await _json_response(resp)
    return {
        "provider": "tavily",
        "query": query,
        "results": [
            _result(item.get("title"), item.get("url"), item.get("content"))
            for item in data.get("results", [])[:max_results]
        ],
    }


async def _async_serper(
    session: aiohttp.ClientSession, api_key: str, query: str, max_results: int
) -> dict[str, Any]:
    async with session.post(
        "https://google.serper.dev/search",
        headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
        json={"q": query, "num": max_results},
        timeout=aiohttp.ClientTimeout(total=15),
    ) as resp:
        data = await _json_response(resp)
    return {
        "provider": "serper",
        "query": query,
        "results": [
            _result(item.get("title"), item.get("link"), item.get("snippet"))
            for item in data.get("organic", [])[:max_results]
        ],
    }


async def _async_firecrawl(
    session: aiohttp.ClientSession, api_key: str, query: str, max_results: int
) -> dict[str, Any]:
    async with session.post(
        "https://api.firecrawl.dev/v2/search",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"query": query, "limit": max_results},
        timeout=aiohttp.ClientTimeout(total=20),
    ) as resp:
        data = await _json_response(resp)
    results = data.get("data") or data.get("results") or []
    return {
        "provider": "firecrawl",
        "query": query,
        "results": [
            _result(
                item.get("title"),
                item.get("url"),
                item.get("description") or item.get("markdown"),
            )
            for item in results[:max_results]
        ],
    }


async def _async_brave(
    session: aiohttp.ClientSession, api_key: str, query: str, max_results: int
) -> dict[str, Any]:
    params = urlencode({"q": query, "count": max_results})
    async with session.get(
        f"https://api.search.brave.com/res/v1/web/search?{params}",
        headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
        timeout=aiohttp.ClientTimeout(total=15),
    ) as resp:
        data = await _json_response(resp)
    web_results = (data.get("web") or {}).get("results") or []
    return {
        "provider": "brave",
        "query": query,
        "results": [
            _result(item.get("title"), item.get("url"), item.get("description"))
            for item in web_results[:max_results]
        ],
    }


async def _json_response(resp: aiohttp.ClientResponse) -> dict[str, Any]:
    if resp.status >= HTTPStatus.BAD_REQUEST:
        body = await resp.text()
        raise ValueError(f"HTTP {resp.status}: {body[:120]}")
    data = await resp.json()
    if not isinstance(data, dict):
        raise TypeError("non_object_json")
    return data


def _result(title: object, url: object, content: object) -> dict[str, str]:
    return {
        "title": str(title or "")[:180],
        "url": str(url or "")[:500],
        "content": str(content or "")[:800],
    }


def _bounded_max_results(value: object) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return _DEFAULT_MAX_RESULTS
    return max(1, min(number, 8))
