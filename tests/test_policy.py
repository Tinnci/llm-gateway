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
    assert not should_allow_search("查一下今天空气质量")
    assert should_allow_search("帮我网上查一下今天的天气")
    assert should_allow_search("上海静安附近最近的麦当劳在哪里？")
    assert not should_allow_search("附近最近的麦当劳在哪里？")
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
    assert not should_force_search_in_voice_path("查一下今天空气质量")
    assert should_force_search_in_voice_path("帮我网上查一下今天的天气")
    assert should_force_search_in_voice_path("上海静安附近最近的麦当劳在哪里？")
    assert not should_force_search_in_voice_path("附近最近的麦当劳在哪里？")
    assert should_force_search_in_voice_path("这个设备错误码是什么意思")
    assert not should_force_search_in_voice_path("今天天气。")
    assert not should_force_search_in_voice_path("天气怎么样？")
    assert not should_force_search_in_voice_path("明天的天气怎么样？")
    assert not should_force_search_in_voice_path("What is the weather tomorrow?")
    assert not should_force_search_in_voice_path("What is the weather? Not today.")
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


def test_missing_location_blocks_search_with_permission_prompt():
    call = llm.ToolInput(
        id="search-1",
        tool_name="search_web",
        tool_args={"query": "附近 麦当劳"},
        external=True,
    )

    decision = validate_tool_call(call, "附近最近的麦当劳在哪里？")

    assert not decision.allowed
    assert decision.reason == "missing_user_slot"
    assert "位置" in decision.spoken_prompt
    assert "不需要联网搜索" not in decision.spoken_prompt
    assert decision.metadata["task_family"] == "location_dependent_query"
    assert decision.metadata["task_type"] == "nearby_place_query"
    assert decision.metadata["missing_requirements"] == ["location"]
    assert decision.metadata["user_visible_action"] == "ask_location_permission"
    assert decision.metadata["policy_name"] == "external_search_policy"


def test_weather_forecast_missing_location_blocks_as_user_slot_not_confirmation():
    call = llm.ToolInput(
        id="search-weather",
        tool_name="search_web",
        tool_args={"query": "明天 天气"},
        external=True,
    )

    decision = validate_tool_call(call, "明天的天气怎么样？")

    assert not decision.allowed
    assert decision.reason == "missing_user_slot"
    assert "哪个地方" in decision.spoken_prompt
    assert decision.metadata["blocked_reason"] == "missing_user_slot"
    assert decision.metadata["task_type"] == "weather_forecast_query"


def test_explicit_location_search_is_allowed():
    call = llm.ToolInput(
        id="search-1",
        tool_name="search_web",
        tool_args={"query": "上海静安 麦当劳"},
        external=True,
    )

    assert validate_tool_call(call, "上海静安附近最近的麦当劳在哪里？").allowed
