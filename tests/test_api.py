"""Tests for the OpenAI-compatible client."""

from __future__ import annotations

import asyncio
import time
from typing import Self

import pytest
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.llm_gateway.api import (
    LLMGatewayAuthError,
    LLMGatewayCatalogNotModifiedError,
    LLMGatewayClient,
    LLMGatewayConnectionError,
    LLMGatewayError,
    LLMGatewayHTTPError,
    LLMGatewayQuotaExhaustedError,
    ModelCatalogFetch,
    _parse_usage,
    _strip_inline_tool_syntax,
)
from custom_components.llm_gateway.model_catalog import ModelCatalogCache

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
    with pytest.raises(LLMGatewayHTTPError) as err:
        await client.async_list_models()
    assert err.value.status == 500
    assert err.value.body == "boom"


async def test_chat_completion_returns_message(hass, aioclient_mock):
    aioclient_mock.post(
        f"{BASE}/chat/completions",
        json={"choices": [{"message": {"role": "assistant", "content": "hi"}}]},
    )
    client = LLMGatewayClient(async_get_clientsession(hass), BASE, "k")
    message, usage = await client.async_chat_completion(
        model="m",
        messages=[{"role": "user", "content": "x"}],
        max_tokens=8,
        temperature=0.1,
        top_p=0.9,
    )
    assert message["content"] == "hi"
    assert usage is None  # fixture response carries no usage block


async def test_chat_completion_can_require_tool_call(hass, aioclient_mock):
    aioclient_mock.post(
        f"{BASE}/chat/completions",
        json={"choices": [{"message": {"role": "assistant", "tool_calls": []}}]},
    )
    client = LLMGatewayClient(async_get_clientsession(hass), BASE, "k")
    await client.async_chat_completion(
        model="m",
        messages=[{"role": "user", "content": "x"}],
        tools=[{"type": "function", "function": {"name": "t"}}],
        tool_choice="required",
        max_tokens=8,
        temperature=0.1,
        top_p=0.9,
    )

    request_json = aioclient_mock.mock_calls[-1][2]
    assert request_json["tool_choice"] == "required"


async def test_chat_completion_can_force_named_tool(hass, aioclient_mock):
    aioclient_mock.post(
        f"{BASE}/chat/completions",
        json={"choices": [{"message": {"role": "assistant", "tool_calls": []}}]},
    )
    client = LLMGatewayClient(async_get_clientsession(hass), BASE, "k")
    tool_choice = {"type": "function", "function": {"name": "search_web"}}
    await client.async_chat_completion(
        model="m",
        messages=[{"role": "user", "content": "x"}],
        tools=[{"type": "function", "function": {"name": "search_web"}}],
        tool_choice=tool_choice,
        max_tokens=8,
        temperature=0.1,
        top_p=0.9,
    )

    request_json = aioclient_mock.mock_calls[-1][2]
    assert request_json["tool_choice"] == tool_choice


async def test_chat_completion_merges_extra_body_without_streaming(
    hass, aioclient_mock
):
    aioclient_mock.post(
        f"{BASE}/chat/completions",
        json={"choices": [{"message": {"role": "assistant", "content": "ok"}}]},
    )
    client = LLMGatewayClient(async_get_clientsession(hass), BASE, "k")
    await client.async_chat_completion(
        model="m",
        messages=[{"role": "user", "content": "x"}],
        extra_body={
            "chat_template_kwargs": {"enable_thinking": True},
            "reasoning_budget": 16384,
            "stream": True,
        },
        max_tokens=16384,
        temperature=1,
        top_p=0.95,
    )

    request_json = aioclient_mock.mock_calls[-1][2]
    assert request_json["max_tokens"] == 16384
    assert request_json["reasoning_budget"] == 16384
    assert request_json["chat_template_kwargs"] == {"enable_thinking": True}
    assert "stream" not in request_json


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


class _HangingRequest:
    async def __aenter__(self) -> Self:
        await asyncio.sleep(30)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object,
    ) -> bool:
        return False


class _HangingSession:
    def request(self, *args: object, **kwargs: object) -> _HangingRequest:
        return _HangingRequest()


async def test_chat_completion_has_outer_hard_timeout():
    client = LLMGatewayClient(_HangingSession(), BASE, "k")
    started = time.monotonic()

    with pytest.raises(LLMGatewayConnectionError):
        await client.async_chat_completion(
            model="m",
            messages=[{"role": "user", "content": "x"}],
            max_tokens=8,
            temperature=0.1,
            top_p=0.9,
            timeout_s=1,
        )

    assert time.monotonic() - started < 3


async def test_parse_usage_normalizes_provider_shapes():
    """OpenAI and DeepSeek usage blocks fold into four neutral buckets."""
    openai = _parse_usage(
        {
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "total_tokens": 120,
                "prompt_tokens_details": {"cached_tokens": 64},
            }
        }
    )
    assert openai == {
        "input_tokens": 100,
        "output_tokens": 20,
        "total_tokens": 120,
        "cached_input_tokens": 64,
    }
    deepseek = _parse_usage(
        {
            "usage": {
                "prompt_tokens": 50,
                "completion_tokens": 5,
                "prompt_cache_hit_tokens": 32,
            }
        }
    )
    assert deepseek["cached_input_tokens"] == 32
    assert deepseek["total_tokens"] == 55
    assert _parse_usage({"choices": []}) is None
    assert _parse_usage({"usage": {}}) is None


async def test_quota_wording_raises_terminal_error(hass, aioclient_mock):
    """Provider quota wording becomes a terminal error, never a retry."""
    aioclient_mock.post(
        f"{BASE}/chat/completions",
        status=429,
        json={"error": {"code": "insufficient_quota", "message": "insufficient quota"}},
    )
    client = LLMGatewayClient(async_get_clientsession(hass), BASE, "k")
    with pytest.raises(LLMGatewayQuotaExhaustedError):
        await client.async_chat_completion(
            model="m",
            messages=[{"role": "user", "content": "x"}],
            max_tokens=8,
            temperature=0.1,
            top_p=0.9,
        )


async def test_plain_rate_limit_stays_transient(hass, aioclient_mock):
    """A bare 429 without quota wording remains an ordinary HTTP error."""
    aioclient_mock.post(
        f"{BASE}/chat/completions",
        status=429,
        json={"error": {"message": "rate limit exceeded, slow down"}},
    )
    client = LLMGatewayClient(async_get_clientsession(hass), BASE, "k")
    with pytest.raises(LLMGatewayHTTPError):
        await client.async_chat_completion(
            model="m",
            messages=[{"role": "user", "content": "x"}],
            max_tokens=8,
            temperature=0.1,
            top_p=0.9,
        )


async def test_list_models_conditional_uses_validators(hass, aioclient_mock):
    """Validators go out as conditional headers and validators come back."""
    aioclient_mock.get(
        f"{BASE}/models",
        json={"data": [{"id": "b"}, {"id": "a"}]},
        headers={"ETag": '"v2"', "Last-Modified": "Tue, 01 Jan 2036 00:00:00 GMT"},
    )
    client = LLMGatewayClient(async_get_clientsession(hass), BASE, "k")
    fetch = await client.async_list_models_conditional(
        etag='"v1"', last_modified="Mon, 01 Jan 2035 00:00:00 GMT"
    )
    assert fetch.models == ["a", "b"]
    assert fetch.etag == '"v2"'
    assert fetch.not_modified is False
    sent_headers = aioclient_mock.mock_calls[-1][3] or {}
    assert sent_headers.get("If-None-Match") == '"v1"'
    assert "If-Modified-Since" in sent_headers


class _StubClient:
    """Scriptable stand-in for LLMGatewayClient catalog calls."""

    def __init__(self, script: list) -> None:
        self._script = list(script)
        self.calls = []

    async def async_list_models_conditional(self, *, etag=None, last_modified=None):
        self.calls.append((etag, last_modified))
        action = self._script.pop(0)
        if isinstance(action, Exception):
            raise action
        return action


async def _fresh_catalog(hass):
    return ModelCatalogCache(hass)


async def test_catalog_ttl_short_circuits_network(hass, aioclient_mock):
    """Within TTL the cache answers without touching the provider."""
    aioclient_mock.get(f"{BASE}/models", json={"data": [{"id": "a"}]})
    client = LLMGatewayClient(async_get_clientsession(hass), BASE, "k")
    catalog = await _fresh_catalog(hass)

    first = await catalog.async_get(client=client, base_url=BASE)
    assert first.source == "fetched"
    second = await catalog.async_get(client=client, base_url=BASE)
    assert second.source == "cache"
    assert len(aioclient_mock.mock_calls) == 1


async def test_catalog_304_revalidates_without_download(hass):
    """A 304 keeps the stored models and only refreshes validators."""
    fetched = ModelCatalogFetch(models=["a"], etag='"v1"', last_modified="yesterday")
    stub = _StubClient(
        [
            fetched,
            LLMGatewayCatalogNotModifiedError(etag='"v1"', last_modified="today"),
        ]
    )
    catalog = await _fresh_catalog(hass)

    await catalog.async_get(client=stub, base_url=BASE)
    again = await catalog.async_get(client=stub, base_url=BASE, force=True)

    assert again.source == "revalidated"
    assert again.models == ["a"]
    assert stub.calls[-1] == ('"v1"', "yesterday")


async def test_catalog_serves_stale_when_provider_fails(hass):
    """Provider outage degrades to the stale catalog instead of erroring."""
    stub = _StubClient(
        [
            ModelCatalogFetch(models=["keep"]),
            LLMGatewayConnectionError("down"),
        ]
    )
    catalog = await _fresh_catalog(hass)

    await catalog.async_get(client=stub, base_url=BASE)
    stale = await catalog.async_get(client=stub, base_url=BASE, force=True)

    assert stale.source == "cache"
    assert stale.stale is True
    assert stale.models == ["keep"]


async def test_catalog_auth_error_propagates(hass):
    """Auth failures must surface, never masquerade as a stale cache."""
    stub = _StubClient(
        [
            ModelCatalogFetch(models=["ok"]),
            LLMGatewayAuthError("bad key"),
        ]
    )
    catalog = await _fresh_catalog(hass)
    await catalog.async_get(client=stub, base_url=BASE)

    with pytest.raises(LLMGatewayAuthError):
        await catalog.async_get(client=stub, base_url=BASE, force=True)


def test_strip_inline_tool_syntax_variants():
    """Inline tool-call XML is removed; ordinary prose and plain words stay."""
    assert (
        _strip_inline_tool_syntax("正常回答，没有任何标记。")
        == "正常回答，没有任何标记。"
    )
    dirty = '好的。<tool_call>{"name":"search_web"}</tool_call>以上便是结果。'
    assert _strip_inline_tool_syntax(dirty) == "好的。以上便是结果。"
    unclosed = '前缀 <tool_call>{"name":"x"}'
    assert _strip_inline_tool_syntax(unclosed) == "前缀"
    assert _strip_inline_tool_syntax("") == ""


async def test_chat_completion_strips_inline_tool_syntax(hass, aioclient_mock):
    """Content-channel leakage is cleaned before it reaches any consumer."""
    aioclient_mock.post(
        f"{BASE}/chat/completions",
        json={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": '答案。<tool_call>{"name":"x"}</tool_call>',
                    }
                }
            ],
            "usage": {"prompt_tokens": 3, "completion_tokens": 4},
        },
    )
    client = LLMGatewayClient(async_get_clientsession(hass), BASE, "k")
    message, usage = await client.async_chat_completion(
        model="m",
        messages=[{"role": "user", "content": "x"}],
        max_tokens=8,
        temperature=0.1,
        top_p=0.9,
    )
    assert message["content"] == "答案。"
    assert usage["total_tokens"] == 7
