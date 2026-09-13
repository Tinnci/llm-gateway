"""Authenticated streaming model previews for the Voice Harness playground."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LLMGatewayClient, LLMGatewayError
from .const import CONF_BASE_URL, DOMAIN
from .harness import evaluate_scenario
from .router import select_model_route
from .tools_registry import enabled_external_tools


@callback
def async_register_stream(hass: HomeAssistant) -> None:
    """Register the admin-only diagnostic subscription."""
    websocket_api.async_register_command(hass, stream_preview)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "llm_gateway/harness/stream",
        vol.Required("entry_id"): str,
        vol.Required("user"): vol.All(str, vol.Length(min=1, max=12000)),
        vol.Optional("route", default="auto"): vol.In(["auto", "fast", "mid", "deep"]),
        vol.Optional("expected", default=dict): dict,
    }
)
@websocket_api.require_admin
@callback
def stream_preview(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Stream one provider generation; tool calls remain unexecuted proposals."""
    entry = hass.config_entries.async_get_entry(msg["entry_id"])
    if entry is None or entry.domain != DOMAIN:
        connection.send_error(msg["id"], "entry_not_found", "Gateway entry not found")
        return
    options = deepcopy(dict(entry.options))
    options["routing_mode"] = msg["route"]
    client = LLMGatewayClient(
        async_get_clientsession(hass),
        str(entry.data.get(CONF_BASE_URL) or ""),
        str(entry.data.get(CONF_API_KEY) or ""),
    )
    task = hass.async_create_background_task(
        _preview(connection, msg, client, options),
        "Voice Harness model preview",
        eager_start=False,
    )
    connection.subscriptions[msg["id"]] = task.cancel
    connection.send_result(msg["id"])


async def _preview(
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    client: LLMGatewayClient,
    options: dict[str, Any],
) -> None:
    """Forward observed chunks and cancel the upstream request on unsubscribe."""

    def send(event: dict[str, Any]) -> None:
        connection.send_event(msg["id"], event)

    response = ""
    finish_reason = ""
    tool_calls: dict[int, dict[str, str]] = {}
    try:
        route = select_model_route(msg["user"], options)
        send({"type": "route", "route": route.kind, "model": route.model})
        tools = [
            spec
            for tool in enabled_external_tools(options)
            for spec in tool.build_specs(options)
        ]
        messages = [
            {
                "role": "system",
                "content": (
                    "This is a voice response preview. Answer briefly in "
                    "the user's language. "
                    "Tools can be proposed but will not be executed. "
                    "No device has been "
                    "changed and no live sensor reading has been supplied. Never claim "
                    "that an action was applied or invent a physical observation."
                ),
            },
            {"role": "user", "content": msg["user"]},
        ]
        async for event in client.async_stream_preview(
            model=route.model,
            messages=messages,
            max_tokens=route.max_tokens,
            timeout_s=route.timeout_s,
            tools=tools,
            extra_body=route.extra_body,
            temperature=float(options.get("temperature", 0.3)),
            top_p=float(options.get("top_p", 1.0)),
        ):
            if event["type"] == "delta":
                delta = event["delta"]
                content = delta.get("content")
                if isinstance(content, str):
                    response += content
                    send({"type": "token", "text": content})
                for call in delta.get("tool_calls") or []:
                    index = int(call.get("index", 0))
                    current = tool_calls.setdefault(
                        index, {"name": "", "arguments": ""}
                    )
                    function = call.get("function") or {}
                    current["name"] += str(function.get("name") or "")
                    current["arguments"] += str(function.get("arguments") or "")
                    send(
                        {
                            "type": "tool",
                            "index": index,
                            **current,
                            "status": "proposed",
                        }
                    )
            else:
                if event["type"] == "finish":
                    finish_reason = str(event["reason"])
                send(event)
        if not response and not tool_calls:
            raise LLMGatewayError(  # noqa: TRY301 - report through this subscription
                "Provider returned no answer or tool proposal"
            )
        result = evaluate_scenario(
            {"user": msg["user"], "expected": msg["expected"]},
            {"response": response},
        )
        violations = [*result.violations]
        if finish_reason in {"length", "content_filter"}:
            violations.append("generation_" + finish_reason)
        send(
            {
                "type": "complete",
                "response": response,
                "passed": not violations,
                "violations": violations,
                "finish_reason": finish_reason,
                "tool_calls": list(tool_calls.values()),
                "mode": "model_preview",
            }
        )
    except asyncio.CancelledError:
        raise
    except (LLMGatewayError, ValueError, TypeError, KeyError, AttributeError) as err:
        send({"type": "error", "message": str(err)})
