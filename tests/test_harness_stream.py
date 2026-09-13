"""Exercise real preview transport, cancellation, and proposal-only execution."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.setup import async_setup_component

from custom_components.llm_gateway.api import (
    LLMGatewayClient,
    LLMGatewayConnectionError,
)
from custom_components.llm_gateway.harness_stream import async_register_stream


async def test_stream_disconnect_is_not_completion(hass, aioclient_mock):
    aioclient_mock.post(
        "https://preview.test/v1/chat/completions",
        text='data: {"choices":[{"delta":{"content":"partial"}}]}\n\n',
    )
    client = LLMGatewayClient(
        async_get_clientsession(hass), "https://preview.test/v1", "secret"
    )
    received = []
    stream = client.async_stream_preview(
        model="test", messages=[], max_tokens=10, timeout_s=5
    )
    received.append(await anext(stream))
    with pytest.raises(LLMGatewayConnectionError, match="before completion"):
        await anext(stream)
    assert received == [{"type": "delta", "delta": {"content": "partial"}}]


async def test_stream_keeps_usage_and_ignores_extra_body_message_override(
    hass, aioclient_mock
):
    aioclient_mock.post(
        "https://preview.test/v1/chat/completions",
        text=(
            'data: {"choices":[{"delta":{"content":"hello"},"finish_reason":"stop"}],'
            '"usage":{"prompt_tokens":4,"completion_tokens":2}}\n\ndata: [DONE]\n'
        ),
    )
    client = LLMGatewayClient(
        async_get_clientsession(hass), "https://preview.test/v1", "secret"
    )
    events = [
        event
        async for event in client.async_stream_preview(
            model="test",
            messages=[{"role": "user", "content": "safe"}],
            max_tokens=10,
            timeout_s=5,
            extra_body={
                "messages": [{"role": "system", "content": "override"}],
                "stream": False,
            },
        )
    ]
    assert events[-1]["usage"]["output_tokens"] == 2
    assert aioclient_mock.mock_calls[0][2]["messages"][0]["content"] == "safe"
    assert aioclient_mock.mock_calls[0][2]["stream"] is True
    assert aioclient_mock.mock_calls[0][2]["stream_options"] == {"include_usage": True}


async def test_preview_streams_tokens_and_tools_without_dispatch(
    hass, hass_ws_client, mock_config_entry
):
    assert await async_setup_component(hass, "websocket_api", {})
    mock_config_entry.add_to_hass(hass)
    async_register_stream(hass)
    client = await hass_ws_client(hass)

    async def generate(*args: object, **kwargs: object):
        yield {"type": "delta", "delta": {"content": "hello"}}
        yield {
            "type": "delta",
            "delta": {
                "tool_calls": [
                    {"index": 0, "function": {"name": "turn_on", "arguments": "{}"}}
                ]
            },
        }
        yield {"type": "usage", "usage": {"output_tokens": 2}}

    with (
        patch.object(LLMGatewayClient, "async_stream_preview", generate),
        patch.object(type(hass.services), "async_call") as dispatch,
    ):
        await client.send_json(
            {
                "id": 1,
                "type": "llm_gateway/harness/stream",
                "entry_id": mock_config_entry.entry_id,
                "user": "hello",
            }
        )
        ack = await client.receive_json()
        assert ack["success"]
        events = []
        while True:
            event = (await client.receive_json())["event"]
            events.append(event)
            if event["type"] == "complete":
                break
        assert any(event.get("text") == "hello" for event in events)
        assert (
            next(event for event in events if event["type"] == "tool")["status"]
            == "proposed"
        )
        assert events[-1]["mode"] == "model_preview"
        dispatch.assert_not_called()
        await client.send_json(
            {"id": 2, "type": "unsubscribe_events", "subscription": 1}
        )
        assert (await client.receive_json())["success"]


async def test_unsubscribe_cancels_provider(hass, hass_ws_client, mock_config_entry):
    assert await async_setup_component(hass, "websocket_api", {})
    mock_config_entry.add_to_hass(hass)
    async_register_stream(hass)
    client = await hass_ws_client(hass)
    cancelled = asyncio.Event()

    async def generate(*args: object, **kwargs: object):
        try:
            yield {"type": "delta", "delta": {"content": "start"}}
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    with patch.object(LLMGatewayClient, "async_stream_preview", generate):
        await client.send_json(
            {
                "id": 1,
                "type": "llm_gateway/harness/stream",
                "entry_id": mock_config_entry.entry_id,
                "user": "hello",
            }
        )
        assert (await client.receive_json())["success"]
        assert (await client.receive_json())["event"]["type"] == "route"
        assert (await client.receive_json())["event"]["type"] == "token"
        await client.send_json(
            {"id": 2, "type": "unsubscribe_events", "subscription": 1}
        )
        assert (await client.receive_json())["success"]
        await asyncio.wait_for(cancelled.wait(), timeout=1)


async def test_preview_rejects_non_admin(hass, hass_ws_client, hass_read_only_user):
    assert await async_setup_component(hass, "websocket_api", {})
    async_register_stream(hass)
    refresh = await hass.auth.async_create_refresh_token(
        hass_read_only_user, client_id="https://test.local/"
    )
    token = hass.auth.async_create_access_token(refresh)
    client = await hass_ws_client(hass, token)
    await client.send_json(
        {
            "id": 1,
            "type": "llm_gateway/harness/stream",
            "entry_id": "missing",
            "user": "hello",
        }
    )
    result = await client.receive_json()
    assert result["success"] is False
    assert result["error"]["code"] == "unauthorized"
