"""Tests for model routing."""

from __future__ import annotations

from custom_components.llm_gateway.const import (
    CONF_CHAT_MODEL,
    CONF_DEEP_EXTRA_BODY,
    CONF_DEEP_MODEL,
    CONF_FAST_MODEL,
    CONF_MID_MODEL,
    CONF_ROUTING_MODE,
    RECOMMENDED_DEEP_MODEL,
    RECOMMENDED_FAST_MODEL,
    RECOMMENDED_MID_MODEL,
    ROUTING_MODE_DEEP,
)
from custom_components.llm_gateway.router import (
    classify_route,
    select_model_route,
    select_verifier_route,
)


def test_classify_route():
    assert classify_route("打开卧室灯") == "fast"
    assert classify_route("今天天气。") == "fast"
    assert classify_route("查一下这个空调错误码 E7") == "mid"
    assert classify_route("附近最近的麦当劳在哪里？") == "fast"
    assert classify_route("上海静安附近最近的麦当劳在哪里？") == "mid"
    assert classify_route("关关雎鸠，在河之洲，这句话是出自哪里？") == "mid"
    assert classify_route("请深度分析整个控制管线") == "deep"


def test_select_model_route_defaults():
    assert select_model_route("打开灯", {}).model == RECOMMENDED_FAST_MODEL
    assert select_model_route("查一下最新固件", {}).model == RECOMMENDED_MID_MODEL
    assert select_model_route("深度分析一下", {}).model == RECOMMENDED_DEEP_MODEL


def test_select_model_route_legacy_chat_model_is_fast_fallback():
    route = select_model_route("打开灯", {CONF_CHAT_MODEL: "legacy/model"})
    assert route.kind == "fast"
    assert route.model == "legacy/model"


def test_select_model_route_forced_deep():
    route = select_model_route(
        "打开灯",
        {
            CONF_ROUTING_MODE: ROUTING_MODE_DEEP,
            CONF_FAST_MODEL: "fast",
            CONF_MID_MODEL: "mid",
            CONF_DEEP_MODEL: "deep",
        },
    )
    assert route.kind == "deep"
    assert route.model == "deep"
    assert route.async_deep_task


def test_select_verifier_route_uses_bounded_deep_model():
    route = select_verifier_route({CONF_DEEP_MODEL: "deep"})
    assert route.kind == "deep"
    assert route.model == "deep"
    assert route.max_tokens <= 512
    assert route.timeout_s <= 45
    assert route.extra_body == {"response_format": {"type": "json_object"}}
    assert route.async_deep_task is False


def test_select_verifier_route_preserves_extra_body_with_json_response():
    route = select_verifier_route(
        {
            CONF_DEEP_MODEL: "deep",
            CONF_DEEP_EXTRA_BODY: '{"reasoning_budget": 256}',
        }
    )

    assert route.extra_body == {
        "reasoning_budget": 256,
        "response_format": {"type": "json_object"},
    }
