"""Tests for search and tool policy."""

from __future__ import annotations

from homeassistant.helpers import llm

from custom_components.llm_gateway.policy import should_allow_search, validate_tool_call


def test_search_policy_gating():
    assert should_allow_search("查一下今天空气质量")
    assert should_allow_search("这个设备错误码是什么意思")
    assert not should_allow_search("打开卧室灯")
    assert not should_allow_search("把它调暗一点")


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
