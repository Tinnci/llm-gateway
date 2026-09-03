"""Tests for local capability execution."""

from __future__ import annotations

from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import EntityCategory

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
    assert candidate.target_scope == "area"


def test_local_action_candidate_parses_climate_control():
    candidate = local_action_candidate("打开空调。")

    assert candidate is not None
    assert candidate.family == "home_control"
    assert candidate.action == "turn_on"
    assert candidate.domain == "climate"
    assert candidate.target_hint == "空调"


def test_local_action_candidate_rejects_high_risk_control():
    assert local_action_candidate("打开前门门锁") is None


def test_local_action_candidate_rejects_negated_and_ambiguous_actions():
    assert local_action_candidate("不要打开客厅灯") is None
    assert local_action_candidate("客厅灯不要关") is None
    assert local_action_candidate("打开灯还是关灯？") is None


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


async def test_local_executor_applies_explicit_all_lights_scope(hass):
    calls: list[dict] = []

    async def turn_on(call):
        calls.append(dict(call.data))

    hass.states.async_set("light.desk", "off", {"friendly_name": "书桌灯"})
    hass.states.async_set("light.monitor", "off", {"friendly_name": "显示器挂灯"})
    hass.services.async_register("light", "turn_on", turn_on)

    route = decide_route("打开所有灯。")
    result = await async_try_execute_local_capability(hass, "打开所有灯。", route)

    assert result is not None
    assert result.status == "executed"
    assert result.speech == "已打开所有灯。"
    assert calls == [
        {"entity_id": ["light.desk"]},
        {"entity_id": ["light.monitor"]},
    ]
    assert result.trace_attrs()["candidate"]["target_scope"] == "all"


async def test_local_executor_excludes_config_entities_from_all_scope(hass):
    calls: list[dict] = []

    async def turn_on(call):
        calls.append(dict(call.data))

    registry = er.async_get(hass)
    indicator = registry.async_get_or_create(
        "light",
        "test",
        "fan-indicator",
        suggested_object_id="fan_indicator",
        entity_category=EntityCategory.CONFIG,
    )
    hass.states.async_set("light.desk", "off", {"friendly_name": "书桌灯"})
    hass.states.async_set(
        indicator.entity_id,
        "off",
        {"friendly_name": "循环扇指示灯"},
    )
    hass.services.async_register("light", "turn_on", turn_on)

    route = decide_route("打开所有灯。")
    result = await async_try_execute_local_capability(hass, "打开所有灯。", route)

    assert result is not None
    assert result.status == "executed"
    assert calls == [{"entity_id": ["light.desk"]}]
    assert result.action_trace["excluded_entities"] == [
        {
            "entity_id": indicator.entity_id,
            "reason": "entity_category:config",
        }
    ]


async def test_local_executor_reports_partial_all_scope_failure(hass):
    calls: list[dict] = []

    async def turn_on(call):
        calls.append(dict(call.data))
        if call.data["entity_id"] == ["light.unreliable"]:
            raise RuntimeError("device timed out")

    hass.states.async_set("light.desk", "off", {"friendly_name": "书桌灯"})
    hass.states.async_set(
        "light.unreliable",
        "off",
        {"friendly_name": "离线灯"},
    )
    hass.states.async_set("light.already_on", "on", {"friendly_name": "常亮灯"})
    hass.services.async_register("light", "turn_on", turn_on)

    route = decide_route("打开所有灯。")
    result = await async_try_execute_local_capability(hass, "打开所有灯。", route)

    assert result is not None
    assert result.status == "partial"
    assert result.speech == "已打开 1 个灯，1 个失败。"
    assert calls == [
        {"entity_id": ["light.desk"]},
        {"entity_id": ["light.unreliable"]},
    ]
    assert result.service_calls == (
        {
            "domain": "light",
            "service": "turn_on",
            "entity_ids": ["light.desk"],
        },
    )
    assert result.action_trace["skipped_entities"] == [
        {"entity_id": "light.already_on", "reason": "already_on"}
    ]
    assert result.action_trace["failed_entities"] == [
        {"entity_id": "light.unreliable", "reason": "RuntimeError"}
    ]


def test_local_action_candidate_generalizes_explicit_all_scope() -> None:
    all_fans = local_action_candidate("关闭全部风扇")
    every_switch = local_action_candidate("打开每个开关")

    assert all_fans is not None
    assert all_fans.target_scope == "all"
    assert every_switch is not None
    assert every_switch.target_scope == "all"


async def test_local_executor_calls_climate_service(hass):
    calls: list[dict] = []

    async def turn_on(call):
        calls.append(dict(call.data))

    hass.states.async_set(
        "climate.bedroom_ac",
        "off",
        {"friendly_name": "卧室空调"},
    )
    hass.services.async_register("climate", "turn_on", turn_on)

    route = decide_route("打开空调。")
    result = await async_try_execute_local_capability(hass, "打开空调。", route)

    assert route.next_action == "execute_local"
    assert route.metadata["domain"] == "climate"
    assert result is not None
    assert result.status == "executed"
    assert result.speech == "已打开卧室空调。"
    assert calls == [{"entity_id": ["climate.bedroom_ac"]}]


async def test_local_executor_sets_climate_temperature(hass):
    calls: list[dict] = []

    async def set_temperature(call):
        calls.append(dict(call.data))

    hass.states.async_set(
        "climate.bedroom_ac",
        "cool",
        {"friendly_name": "卧室空调", "current_temperature": 27.8, "temperature": 25.5},
    )
    hass.services.async_register("climate", "set_temperature", set_temperature)

    route = decide_route("把空调的温度调到 16 度。")
    result = await async_try_execute_local_capability(
        hass,
        "把空调的温度调到 16 度。",
        route,
    )

    assert route.next_action == "execute_local"
    assert route.metadata["action"] == "climate_set_temperature"
    assert route.metadata["target_temperature"] == 16.0
    assert result is not None
    assert result.status == "executed"
    assert result.speech == "已把卧室空调设为16度。"
    assert calls == [{"entity_id": ["climate.bedroom_ac"], "temperature": 16.0}]
    assert result.trace_attrs()["candidate"]["target_temperature"] == 16.0


async def test_local_executor_clarifies_ambiguous_media_player(hass):
    hass.states.async_set("media_player.a", "idle", {"friendly_name": "客厅音箱 A"})
    hass.states.async_set("media_player.b", "idle", {"friendly_name": "客厅音箱 B"})

    route = decide_route("把客厅音箱音量调到最大")
    result = await async_try_execute_local_capability(
        hass, "把客厅音箱音量调到最大", route
    )

    assert result is not None
    assert result.status == "clarify"
    assert "我找到几个播放器" in result.speech
    assert "客厅音箱 A" in result.speech
    assert "客厅音箱 B" in result.speech


async def test_local_executor_targeted_clarifies_numeric_light_reference(hass):
    calls: list[dict] = []

    async def turn_on(call):
        calls.append(dict(call.data))

    hass.states.async_set(
        "light.devcea_1055",
        "off",
        {"friendly_name": "宜家麦希瑟E27 1055lm智能球泡灯 灯"},
    )
    hass.states.async_set(
        "light.monitor",
        "off",
        {"friendly_name": "Yeelight 显示器挂灯 灯"},
    )
    hass.services.async_register("light", "turn_on", turn_on)

    route = decide_route("打开 1,055 00 的那个灯。")
    result = await async_try_execute_local_capability(
        hass, "打开 1,055 00 的那个灯。", route
    )

    assert result is not None
    assert result.status == "clarify"
    assert "1055lm" in result.speech
    assert calls == []
    frame = result.trace_attrs()["action_trace"]["resolution_frame"]
    referent = frame["referents"][0]
    assert referent["candidates"][0]["id"] == "light.devcea_1055"
    assert "numeric_match:1055" in referent["candidates"][0]["evidence"]
    assert frame["commitment"]["state"] == "targeted_clarify"


async def test_local_executor_targeted_clarifies_asr_light_reference(hass):
    hass.states.async_set(
        "light.devcea_1055",
        "off",
        {"friendly_name": "宜家麦希瑟E27 1055lm智能球泡灯 灯"},
    )

    route = decide_route("打开米家麦西色灯。")
    result = await async_try_execute_local_capability(hass, "打开米家麦西色灯。", route)

    assert result is not None
    assert result.status == "clarify"
    frame = result.trace_attrs()["action_trace"]["resolution_frame"]
    evidence = frame["referents"][0]["candidates"][0]["evidence"]
    assert "asr_normalization:麦西色≈麦希瑟" in evidence
    assert frame["commitment"]["state"] == "targeted_clarify"


async def test_assistant_volume_reports_unconfigured(hass):
    route = decide_route("把自己的音量调到最大")
    result = await async_try_execute_local_capability(
        hass, "把自己的音量调到最大", route
    )

    assert result is not None
    assert result.status == "clarify"
    assert result.speech == "我说话音量控制还没有配置好。"


async def test_assistant_volume_trace_includes_verified_action_state(hass):
    calls: list[dict] = []
    hass.states.async_set("input_number.kukui_tts_volume_day", "0.58")
    hass.states.async_set("input_number.kukui_tts_volume_night", "0.38")
    hass.states.async_set("input_number.kukui_fallback_clip_volume", "0.42")

    async def set_value(call):
        calls.append(dict(call.data))
        for entity_id in call.data["entity_id"]:
            hass.states.async_set(entity_id, str(call.data["value"]))

    hass.services.async_register("input_number", "set_value", set_value)

    route = decide_route("把你自己的音量调到最高")
    result = await async_try_execute_local_capability(
        hass, "把你自己的音量调到最高", route
    )

    assert result is not None
    assert result.status == "executed"
    trace = result.trace_attrs()
    assert trace["action_trace"]["adapter"] == "ha_input_number"
    assert trace["action_trace"]["target"] == "assistant_voice"
    assert trace["action_trace"]["requested_level"] == 1.0
    assert trace["action_trace"]["status"] == "executed"
    assert trace["action_trace"]["verified_state"] == {
        "input_number.kukui_tts_volume_day": "1.0",
        "input_number.kukui_tts_volume_night": "1.0",
        "input_number.kukui_fallback_clip_volume": "1.0",
    }
    assert len(calls) == 3
