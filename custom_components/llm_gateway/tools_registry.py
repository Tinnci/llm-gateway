"""Single declaration point for gateway-native external tools.

Gateway tools live outside Home Assistant's intent stack: their OpenAI
specs are injected next to the HA tool schema and their execution is
driven by the tool loop itself. Adding one means appending a
:class:`ExternalTool` here — spec source, executor, and the spoken hint
played while it runs — instead of touching three modules.

@module llm_gateway.tools_registry
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .search import (
    SEARCH_TOOL_NAME,
    async_execute_search_tool,
    available_search_tools,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    import aiohttp


@dataclass(frozen=True, slots=True)
class ExternalTool:
    """A gateway-native tool executed outside Home Assistant."""

    name: str
    spoken_hint: str
    build_specs: Callable[[dict[str, Any]], list[dict[str, Any]]]
    execute: Callable[
        [aiohttp.ClientSession, dict[str, Any], Any],
        Awaitable[dict[str, Any]],
    ]


async def _execute_search(
    session: aiohttp.ClientSession,
    options: dict[str, Any],
    tool_call: Any,  # noqa: ANN401 - llm.ToolInput arrives via the loop
) -> dict[str, Any]:
    return await async_execute_search_tool(session, options, tool_call)


SEARCH_TOOL = ExternalTool(
    name=SEARCH_TOOL_NAME,
    spoken_hint="我查一下。",
    build_specs=available_search_tools,
    execute=_execute_search,
)

_EXTERNAL_TOOLS: tuple[ExternalTool, ...] = (SEARCH_TOOL,)


def enabled_external_tools(
    options: dict[str, Any],
) -> tuple[ExternalTool, ...]:
    """Return declarations whose providers are configured."""
    return tuple(tool for tool in _EXTERNAL_TOOLS if tool.build_specs(options))


def find_external_tool(name: str) -> ExternalTool | None:
    """Look up a declaration by tool name."""
    return next((tool for tool in _EXTERNAL_TOOLS if tool.name == name), None)


async def execute_external_tools(
    calls: list[tuple[Any, ExternalTool]],
    session: aiohttp.ClientSession,
    options: dict[str, Any],
    *,
    on_start: Callable[[Any], None] | None = None,
    on_result: Callable[[Any, dict[str, Any]], None] | None = None,
) -> list[tuple[Any, dict[str, Any]]]:
    """Run a batch of external tools concurrently, preserving input order.

    Each declaration is invoked with the shared session/options; per-call
    trace callbacks fire around execution. Results align with ``calls``.
    """

    async def one(
        call: Any,  # noqa: ANN401 - gateway calls are loosely typed ToolInputs
        declaration: ExternalTool,
    ) -> tuple[Any, dict[str, Any]]:
        if on_start is not None:
            on_start(call)
        result = await declaration.execute(session, options, call)
        if on_result is not None:
            on_result(call, result)
        return (call, result)

    return list(
        await asyncio.gather(*(one(call, declaration) for call, declaration in calls))
    )
