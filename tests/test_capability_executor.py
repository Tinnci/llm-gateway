"""Tests for local capability execution."""

from __future__ import annotations

import asyncio

import pytest
from homeassistant.components.homeassistant import exposed_entities
from homeassistant.helpers import area_registry as ar
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


@pytest.mark.parametrize("temperature", ["25.5", "26"])
async def test_climate_request_preserves_the_spoken_setpoint(hass, temperature):
    calls = []
    hass.states.async_set("climate.bedroom", "cool", {"friendly_name": "卧室空调"})

    async def set_temperature(call):
        calls.append(dict(call.data))

    hass.services.async_register("climate", "set_temperature", set_temperature)
    text = f"把卧室空调设为{temperature}度"
    route = decide_route(text)
    result = await async_try_execute_local_capability(hass, text, route)

    assert route.route == "local_action"
    assert result is not None
    assert result.status == "executed"
    assert calls == [
        {"entity_id": ["climate.bedroom"], "temperature": float(temperature)}
    ]
    assert result.service_calls[0]["confirmation_status"] == "unknown"


@pytest.mark.parametrize("text", ["不要把卧室空调设为25.5度", "别把卧室温度调到26度"])
async def test_negated_temperature_request_never_dispatches(hass, text):
    assert local_action_candidate(text) is None
    assert decide_route(text).next_action != "execute_local"


@pytest.mark.parametrize("room_name", ["卧室", "卧室 2", "小书房"])
async def test_room_temperature_changes_comfort_policy_instead_of_ac(hass, room_name):
    calls = []
    area = ar.async_get(hass).async_create(room_name)
    entity = er.async_get(hass).async_get_or_create(
        "climate",
        "roommind",
        f"roommind_{area.id}_comfort",
        suggested_object_id="renamed_comfort_control",
    )
    hass.states.async_set(
        entity.entity_id, "auto", {"friendly_name": room_name + "舒适目标"}
    )
    hass.states.async_set("climate.ac", "cool", {"friendly_name": room_name + "空调"})
    exposed_entities.async_expose_entity(
        hass, "conversation", entity.entity_id, should_expose=True
    )

    async def set_temperature(call):
        calls.append(dict(call.data))

    hass.services.async_register("climate", "set_temperature", set_temperature)
    text = f"把{room_name.replace(' ', '')}温度调到25.5度"
    route = decide_route(text)
    result = await async_try_execute_local_capability(hass, text, route)

    assert route.route == "local_action"
    assert result is not None
    assert result.status == "executed"
    assert calls == [{"entity_id": [entity.entity_id], "temperature": 25.5}]
    assert result.service_calls[0]["confirmation_status"] == "unknown"
    assert "舒适目标" in result.speech


@pytest.mark.parametrize(
    ("stored_temperature", "active", "suppressed", "matched"),
    [
        (25.5, True, False, True),
        (25.5, True, True, True),
        (25, True, False, False),
        (25.5, False, False, False),
    ],
)
async def test_room_policy_readback_does_not_claim_device_confirmation(
    hass, stored_temperature, active, suppressed, matched
):
    area = ar.async_get(hass).async_create("卧室")
    entity = er.async_get(hass).async_get_or_create(
        "climate", "roommind", f"roommind_{area.id}_comfort"
    )
    attributes = {"friendly_name": "卧室舒适目标", "temperature": 25}
    hass.states.async_set(entity.entity_id, "auto", attributes)
    exposed_entities.async_expose_entity(
        hass, "conversation", entity.entity_id, should_expose=True
    )

    async def set_temperature(call):
        hass.states.async_set(
            entity.entity_id,
            "auto",
            {
                **attributes,
                "override_temperature": stored_temperature,
                "override_active": active,
                "override_suppressed": suppressed,
            },
            context=call.context,
        )

    hass.services.async_register("climate", "set_temperature", set_temperature)
    text = "把卧室温度调到25.5度"
    result = await async_try_execute_local_capability(hass, text, decide_route(text))

    assert result is not None
    dispatch = result.service_calls[0]
    assert dispatch["control_scope"] == "room_comfort"
    assert dispatch["confirmation_status"] == "unknown"
    observation = dispatch["policy_observation"]
    assert observation["matches_request"] is matched
    assert observation["override_suppressed"] is suppressed
    assert observation["override_temperature"] == stored_temperature
    assert ("已保存" in result.speech) is matched
    assert ("离家策略" in result.speech) is (matched and suppressed)
    assert "已回报" not in result.speech
    hass.states.async_set(entity.entity_id, "auto", {"override_temperature": 30})
    assert observation["override_temperature"] == stored_temperature


@pytest.mark.parametrize("exposed", [True, False])
async def test_missing_or_unexposed_room_comfort_never_falls_back_to_ac(hass, exposed):
    calls = []
    area = ar.async_get(hass).async_create("卧室")
    hass.states.async_set("climate.ac", "cool", {"friendly_name": "卧室空调"})
    if not exposed:
        entity = er.async_get(hass).async_get_or_create(
            "climate", "roommind", f"roommind_{area.id}_comfort"
        )
        hass.states.async_set(
            entity.entity_id, "auto", {"friendly_name": "卧室舒适目标"}
        )
        exposed_entities.async_expose_entity(
            hass, "conversation", entity.entity_id, should_expose=False
        )

    async def set_temperature(call):
        calls.append(dict(call.data))

    hass.services.async_register("climate", "set_temperature", set_temperature)
    text = "卧室温度调到26度"
    result = await async_try_execute_local_capability(hass, text, decide_route(text))

    assert result is not None
    assert result.status == "error"
    assert result.reason == "room_comfort_unavailable"
    assert not calls


def test_question_about_a_room_target_does_not_change_it():
    assert decide_route("卧室温度调到26度了吗？").next_action != "execute_local"


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
    assert result.speech == "已向客厅灯发送打开请求。"
    assert calls == [{"entity_id": ["light.living_room"]}]
    assert hass.states.get("light.living_room").state == "off"
    assert result.service_calls[0]["dispatch_status"] == "sent"
    assert result.service_calls[0]["confirmation_status"] == "unknown"
    assert result.service_calls[0]["context_id"]
    trace = result.trace_attrs()
    trace["service_calls"][0]["entity_ids"].clear()
    assert result.service_calls[0]["entity_ids"] == ["light.living_room"]


async def test_failed_dispatch_retains_its_context_without_claiming_delivery(hass):
    contexts = []
    hass.states.async_set("light.living_room", "off", {"friendly_name": "客厅灯"})

    async def turn_on(call):
        contexts.append(call.context.id)
        raise RuntimeError("Device unavailable")

    hass.services.async_register("light", "turn_on", turn_on)
    text = "打开客厅灯"
    result = await async_try_execute_local_capability(hass, text, decide_route(text))

    assert result is not None
    assert result.status == "error"
    assert result.service_calls[0]["dispatch_status"] == "failed"
    assert result.service_calls[0]["context_id"] == contexts[0]
    assert result.service_calls[0]["confirmation_status"] == "unknown"


@pytest.mark.parametrize(
    ("outcome", "confirmation"),
    [("applied", "confirmed"), ("not_confirmed", "not_confirmed")],
)
async def test_driver_evidence_before_dispatch_return_is_kept(
    hass, outcome, confirmation
):
    hass.states.async_set("climate.bedroom", "cool", {"friendly_name": "卧室空调"})

    async def set_temperature(call):
        hass.bus.async_fire(
            "tcl_udp_ac_command_result",
            {
                "entity_id": "climate.bedroom",
                "context_id": call.context.id,
                "command_id": "temperature-command",
                "outcome": outcome,
                "transport_outcome": "accepted_by_udp",
                "expected_status": {"target_temperature": 25.5},
                "status": {"target_temperature": 25.5 if outcome == "applied" else 25},
            },
        )
        await asyncio.sleep(0)

    hass.services.async_register("climate", "set_temperature", set_temperature)
    text = "把卧室空调设为25.5度"
    result = await async_try_execute_local_capability(hass, text, decide_route(text))

    assert result is not None
    dispatch = result.service_calls[0]
    assert dispatch["dispatch_status"] == "sent"
    assert dispatch["confirmation_status"] == confirmation
    assert dispatch["acceptance_status"] == "accepted"
    assert dispatch["integration_evidence"][0]["context_id"] == dispatch["context_id"]
    assert ("已回报设定" in result.speech) is (outcome == "applied")
    trace = result.trace_attrs()
    trace["service_calls"][0]["integration_evidence"][0]["status"].clear()
    assert dispatch["integration_evidence"][0]["status"]
    assert not hass.bus.async_listeners().get("tcl_udp_ac_command_result")


@pytest.mark.parametrize("mismatch", ["context_id", "entity_id"])
async def test_unrelated_driver_evidence_cannot_confirm_a_request(hass, mismatch):
    hass.states.async_set("climate.bedroom", "cool", {"friendly_name": "卧室空调"})

    async def set_temperature(call):
        evidence = {
            "entity_id": "climate.bedroom",
            "context_id": call.context.id,
            "outcome": "applied",
            "transport_outcome": "accepted_by_udp",
        }
        evidence[mismatch] = "another-request-or-device"
        hass.bus.async_fire("tcl_udp_ac_command_result", evidence)
        await asyncio.sleep(0)

    hass.services.async_register("climate", "set_temperature", set_temperature)
    text = "把卧室空调设为25.5度"
    result = await async_try_execute_local_capability(hass, text, decide_route(text))

    assert result is not None
    assert result.service_calls[0]["confirmation_status"] == "unknown"
    assert result.service_calls[0]["integration_evidence"] == []
    assert "已回报" not in result.speech


async def test_zero_volume_is_not_replaced_with_half_volume(hass):
    calls = []
    hass.states.async_set(
        "media_player.speaker", "playing", {"friendly_name": "客厅音箱"}
    )

    async def set_volume(call):
        calls.append(dict(call.data))

    hass.services.async_register("media_player", "volume_set", set_volume)
    text = "把客厅音箱音量调到最小"
    result = await async_try_execute_local_capability(hass, text, decide_route(text))

    assert result is not None
    assert calls == [{"entity_id": ["media_player.speaker"], "volume_level": 0.0}]


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
    assert result.speech == "已向所有灯发送打开请求。"
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
    assert result.speech == "已向 1 个灯发送打开请求，1 个发送失败。"
    assert calls == [
        {"entity_id": ["light.desk"]},
        {"entity_id": ["light.unreliable"]},
    ]
    assert tuple(
        {key: call[key] for key in ("domain", "service", "entity_ids")}
        for call in result.service_calls
    ) == (
        {
            "domain": "light",
            "service": "turn_on",
            "entity_ids": ["light.desk"],
        },
        {
            "domain": "light",
            "service": "turn_on",
            "entity_ids": ["light.unreliable"],
        },
    )
    assert result.service_calls[1]["dispatch_status"] == "failed"
    assert result.service_calls[1]["data"] == {"entity_id": ["light.unreliable"]}
    assert result.action_trace["skipped_entities"] == [
        {"entity_id": "light.already_on", "reason": "already_on"}
    ]
    [failed] = result.action_trace["failed_entities"]
    assert failed["entity_id"] == "light.unreliable"
    assert failed["reason"] == "RuntimeError"
    assert failed["dispatch_status"] == "failed"
    assert failed["context_id"] != result.service_calls[0]["context_id"]


async def test_all_failed_bulk_requests_keep_their_dispatch_evidence(hass):
    hass.states.async_set("light.bedroom", "on", {"friendly_name": "卧室灯"})

    async def turn_off(_call):
        raise RuntimeError("Device unavailable")

    hass.services.async_register("light", "turn_off", turn_off)
    text = "关闭所有灯"
    result = await async_try_execute_local_capability(hass, text, decide_route(text))

    assert result.status == "error"
    assert len(result.service_calls) == 1
    assert result.service_calls[0]["dispatch_status"] == "failed"
    assert result.service_calls[0]["confirmation_status"] == "unknown"
    assert result.service_calls[0]["context_id"]


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
    assert result.speech == "已向卧室空调发送打开请求。"
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
    assert result.speech == "已请求将卧室空调设为16度。"
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
