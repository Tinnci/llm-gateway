"""Tests for model provider fallback."""

from __future__ import annotations

import pytest
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.llm_gateway.api import LLMGatewayClient, LLMGatewayHTTPError
from custom_components.llm_gateway.const import CONF_PROVIDER_PROFILES
from custom_components.llm_gateway.providers import (
    ProviderSelector,
    async_chat_completion_with_fallback,
    normalize_provider_profiles_json,
    parse_provider_profiles,
    route_for_provider,
)
from custom_components.llm_gateway.router import ModelRoute

PRIMARY = "https://primary.test/v1"
FALLBACK = "https://fallback.test/v1"


def _route() -> ModelRoute:
    return ModelRoute(
        kind="fast",
        model="primary-fast",
        max_tokens=64,
        timeout_s=10,
        extra_body={"primary": True},
    )


def _options() -> dict[str, str]:
    return {
        CONF_PROVIDER_PROFILES: normalize_provider_profiles_json(
            {
                "providers": [
                    {
                        "name": "fallback",
                        "base_url": FALLBACK,
                        "api_key": "fallback-key",
                        "models": {"fast": "fallback-fast"},
                        "soft_timeout_s": {"fast": 3},
                        "max_tokens": {"fast": 32},
                        "extra_body": {"fast": {"fallback": True}},
                    }
                ]
            }
        )
    }


def test_parse_and_normalize_provider_profiles() -> None:
    raw = """
    {
      "providers": [
        {
          "name": "fallback",
          "base_url": "https://fallback.test/v1/",
          "api_key": "secret",
          "fast_model": "fallback-fast"
        }
      ]
    }
    """

    profiles = parse_provider_profiles(raw)

    assert profiles[0].name == "fallback"
    assert profiles[0].base_url == FALLBACK
    assert profiles[0].models["fast"] == "fallback-fast"
    assert profiles[0].safe_dict()["has_api_key"] is True
    assert "api_key" not in profiles[0].safe_dict()
    assert normalize_provider_profiles_json(raw).startswith('{"providers":')


def test_route_for_provider_overrides_tier_values() -> None:
    profile = parse_provider_profiles(_options()[CONF_PROVIDER_PROFILES])[0]

    route = route_for_provider(_route(), profile)

    assert route.model == "fallback-fast"
    assert route.max_tokens == 32
    assert route.timeout_s == 3
    assert route.extra_body == {"fallback": True}


def test_provider_selector_moves_cooled_provider_to_end() -> None:
    selector = ProviderSelector(failure_threshold=2, cooldown_s=60)
    candidates = [
        ("primary", object(), _route()),
        ("fallback", object(), _route()),
    ]

    selector.record_failure("primary", "fast", retryable=True, error="timeout")
    assert selector.order_candidates(candidates, "fast")[0][0] == "primary"

    selector.record_failure("primary", "fast", retryable=True, error="timeout")
    ordered = selector.order_candidates(candidates, "fast")

    assert [candidate[0] for candidate in ordered] == ["fallback", "primary"]
    assert selector.snapshot()[0]["cooldown_remaining_s"] > 0


def test_provider_selector_success_clears_penalty() -> None:
    selector = ProviderSelector(failure_threshold=1, cooldown_s=60)
    candidates = [
        ("primary", object(), _route()),
        ("fallback", object(), _route()),
    ]

    selector.record_failure("primary", "fast", retryable=True, error="timeout")
    assert selector.order_candidates(candidates, "fast")[0][0] == "fallback"

    selector.record_success("primary", "fast")

    assert selector.order_candidates(candidates, "fast")[0][0] == "primary"
    assert selector.snapshot() == []


async def test_chat_completion_falls_back_on_retryable_http_error(
    hass, aioclient_mock
):
    aioclient_mock.post(PRIMARY + "/chat/completions", status=500, text="boom")
    aioclient_mock.post(
        FALLBACK + "/chat/completions",
        json={"choices": [{"message": {"role": "assistant", "content": "ok"}}]},
    )
    session = async_get_clientsession(hass)
    client = LLMGatewayClient(session, PRIMARY, "primary-key")

    result = await async_chat_completion_with_fallback(
        session=session,
        primary_client=client,
        route=_route(),
        options=_options(),
        messages=[{"role": "user", "content": "hi"}],
        tools=None,
        tool_choice=None,
        temperature=0.2,
        top_p=0.9,
    )

    assert result.message["content"] == "ok"
    assert result.provider["name"] == "fallback"
    assert result.provider["fallback_used"] is True
    assert [attempt["status"] for attempt in result.attempts] == ["error", "complete"]
    assert result.attempts[0]["retryable"] is True


async def test_chat_completion_does_not_fallback_on_non_retryable_http_error(
    hass, aioclient_mock
):
    aioclient_mock.post(PRIMARY + "/chat/completions", status=400, text="bad request")
    session = async_get_clientsession(hass)
    client = LLMGatewayClient(session, PRIMARY, "primary-key")

    with pytest.raises(LLMGatewayHTTPError) as err:
        await async_chat_completion_with_fallback(
            session=session,
            primary_client=client,
            route=_route(),
            options=_options(),
            messages=[{"role": "user", "content": "hi"}],
            tools=None,
            tool_choice=None,
            temperature=0.2,
            top_p=0.9,
        )

    assert err.value.status == 400
