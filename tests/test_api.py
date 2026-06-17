"""Tests for the OpenAI-compatible client."""

from __future__ import annotations

import pytest
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.llm_gateway.api import (
    LLMGatewayAuthError,
    LLMGatewayClient,
    LLMGatewayError,
)

BASE = "https://gw.test/v1"


async def test_list_models_sorted_and_filtered(hass, aioclient_mock):
    aioclient_mock.get(
        f"{BASE}/models",
        json={"data": [{"id": "b"}, {"id": "a"}, {"id": ""}, {}]},
    )
    client = LLMGatewayClient(async_get_clientsession(hass), BASE, "k")
    assert await client.async_list_models() == ["a", "b"]


async def test_trailing_slash_base_url(hass, aioclient_mock):
    aioclient_mock.get(f"{BASE}/models", json={"data": [{"id": "a"}]})
    client = LLMGatewayClient(async_get_clientsession(hass), f"{BASE}/", "k")
    assert await client.async_list_models() == ["a"]


async def test_auth_error(hass, aioclient_mock):
    aioclient_mock.get(f"{BASE}/models", status=401)
    client = LLMGatewayClient(async_get_clientsession(hass), BASE, "k")
    with pytest.raises(LLMGatewayAuthError):
        await client.async_list_models()


async def test_http_error(hass, aioclient_mock):
    aioclient_mock.get(f"{BASE}/models", status=500, text="boom")
    client = LLMGatewayClient(async_get_clientsession(hass), BASE, "k")
    with pytest.raises(LLMGatewayError):
        await client.async_list_models()


async def test_chat_completion_returns_message(hass, aioclient_mock):
    aioclient_mock.post(
        f"{BASE}/chat/completions",
        json={"choices": [{"message": {"role": "assistant", "content": "hi"}}]},
    )
    client = LLMGatewayClient(async_get_clientsession(hass), BASE, "k")
    message = await client.async_chat_completion(
        model="m",
        messages=[{"role": "user", "content": "x"}],
        max_tokens=8,
        temperature=0.1,
        top_p=0.9,
    )
    assert message["content"] == "hi"


async def test_chat_completion_malformed(hass, aioclient_mock):
    aioclient_mock.post(f"{BASE}/chat/completions", json={"nope": True})
    client = LLMGatewayClient(async_get_clientsession(hass), BASE, "k")
    with pytest.raises(LLMGatewayError):
        await client.async_chat_completion(
            model="m",
            messages=[],
            max_tokens=8,
            temperature=0.1,
            top_p=0.9,
        )
