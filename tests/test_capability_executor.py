"""Tests for local capability execution."""

from __future__ import annotations

from custom_components.llm_gateway.capabilities import decide_route
from custom_components.llm_gateway.capability_executor import (
    async_try_execute_local_capability,
    local_action_candidate,
)


def test_local_action_candidate_parses_low_risk_home_control():
    candidate = local_action_candidate("打开客厅灯")

    assert candidate is not None
    assert candidate.family == "home_control"
    assert candidate.action == "turn_on"
    assert candidate.domain == "light"
    assert candidate.area == "客厅"


def test_local_action_candidate_rejects_high_risk_control():
    assert local_action_candidate("打开前门门锁") is None


def test_local_action_candidate_parses_media_volume():
    candidate = local_action_candidate("把客厅音箱音量调到最大")

    assert candidate is not None
    assert candidate.family == "volume_control"
    assert candidate.action == "volume_set"
    assert candidate.domain == "media_player"
    assert candidate.area == "客厅"
    assert candidate.volume_level == 1.0


async def test_local_executor_calls_light_service(hass):
    calls: list[dict] = []

    async def turn_on(call):
        calls.append(dict(call.data))

    hass.states.async_set(
        "light.living_room",
        "off",
        {"friendly_name": "客厅灯"},
    )
    hass.services.async_register("light", "turn_on", turn_on)

    route = decide_route("打开客厅灯")
    result = await async_try_execute_local_capability(hass, "打开客厅灯", route)

    assert result is not None
    assert result.status == "executed"
    assert result.speech == "已打开客厅灯。"
    assert calls == [{"entity_id": ["light.living_room"]}]


async def test_local_executor_clarifies_ambiguous_media_player(hass):
    hass.states.async_set("media_player.a", "idle", {"friendly_name": "客厅音箱 A"})
    hass.states.async_set("media_player.b", "idle", {"friendly_name": "客厅音箱 B"})

    route = decide_route("把客厅音箱音量调到最大")
    result = await async_try_execute_local_capability(
        hass, "把客厅音箱音量调到最大", route
    )

    assert result is not None
    assert result.status == "clarify"
    assert "找到多个播放器" in result.speech
    assert "你想操作哪一个" in result.speech


async def test_assistant_volume_reports_unconfigured(hass):
    route = decide_route("把自己的音量调到最大")
    result = await async_try_execute_local_capability(
        hass, "把自己的音量调到最大", route
    )

    assert result is not None
    assert result.status == "clarify"
    assert result.speech == "我说话音量控制还没有配置好。"
