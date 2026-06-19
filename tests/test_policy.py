"""Tests for search and tool policy."""

from __future__ import annotations

from homeassistant.helpers import llm

from custom_components.llm_gateway.policy import (
    should_allow_search,
    should_force_search_in_voice_path,
    should_require_search,
    validate_tool_call,
)


def test_search_policy_gating():
    assert should_allow_search("查一下今天空气质量")
    assert should_allow_search("帮我网上查一下今天的天气")
    assert should_allow_search("这个设备错误码是什么意思")
    assert should_allow_search("关关雎鸠，在河之洲，这句话是出自哪里？")
    assert not should_allow_search("今天天气。")
    assert not should_allow_search("空气质量怎么样？")
    assert not should_allow_search("打开卧室灯")
    assert not should_allow_search("把它调暗一点")


def test_search_policy_requires_grounding_for_source_questions():
    assert should_require_search("关关雎鸠，在河之洲，这句话是出自哪里？")
    assert should_require_search("这个典故的原文是什么？")
    assert not should_require_search("查一下今天空气质量")
    assert not should_require_search("打开卧室灯")


def test_search_policy_only_forces_voice_path_for_current_or_explicit_search():
    assert should_force_search_in_voice_path("查一下今天空气质量")
    assert should_force_search_in_voice_path("帮我网上查一下今天的天气")
    assert should_force_search_in_voice_path("这个设备错误码是什么意思")
    assert not should_force_search_in_voice_path("今天天气。")
    assert not should_force_search_in_voice_path("天气怎么样？")
    assert not should_force_search_in_voice_path(
        "关关雎鸠，在河之洲，这句话是出自哪里？"
    )
    assert not should_force_search_in_voice_path("打开卧室灯")


def test_high_risk_tool_requires_confirmation():
    call = llm.ToolInput(
        id="1",
        tool_name="HassTurnOn",
        tool_args={"domain": "lock", "name": "前门门锁"},
    )
    decision = validate_tool_call(call, "打开前门")
    assert not decision.allowed
    assert decision.reason == "confirmation_required"
    assert "确认" in decision.spoken_prompt


def test_high_risk_tool_allows_confirmed_request():
    call = llm.ToolInput(
        id="1",
        tool_name="HassTurnOn",
        tool_args={"domain": "lock", "name": "前门门锁"},
    )
    decision = validate_tool_call(call, "确认打开前门")
    assert decision.allowed


def test_low_risk_home_action_allowed():
    call = llm.ToolInput(
        id="1",
        tool_name="HassTurnOn",
        tool_args={"domain": "light", "name": "卧室灯"},
    )
    assert validate_tool_call(call, "打开卧室灯").allowed
