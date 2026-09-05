"""Replay reported questions through the real router, planner, loop and renderer."""

import pytest

from custom_components.llm_gateway.capabilities import decide_route
from custom_components.llm_gateway.capability_executor import (
    local_action_candidate,
)
from custom_components.llm_gateway.conversation import (
    _local_live_context_slots,
    _local_live_context_tool_args,
)
from custom_components.llm_gateway.turn_loops import (
    LocalLiveContextLoop,
    TurnLoopContext,
    TurnLoopServices,
    run_turn_loop,
)


async def query(hass, text, payload):
    calls = []

    async def read(args):
        calls.append(args)
        return {"success": True, "result": payload}

    decision = decide_route(text)
    context = TurnLoopContext(
        text=text, route_decision=decision, turn_id="reported-question"
    )
    loop = LocalLiveContextLoop()
    assert loop.matches(context)
    result = await run_turn_loop(
        loop,
        hass,
        context,
        TurnLoopServices(
            plan_live_context=lambda text, route: (
                _local_live_context_tool_args(text, route),
                _local_live_context_slots(text, route),
            ),
            execute_live_context=read,
        ),
    )
    return result, calls


@pytest.mark.parametrize(
    ("payload", "answerable"),
    [
        ("- names: 风扇\n  domain: fan\n  state: on\n  percentage: 40\n", True),
        ("- names: 风扇\n  domain: fan\n  state: on\n", False),
        ("- names: 温度\n  domain: sensor\n  state: 26.2\n", False),
    ],
)
async def test_fan_speed_requires_fan_percentage(hass, payload, answerable):
    result, calls = await query(hass, "现在风扇的速度是多少？", payload)
    assert calls == [{"domain": "fan"}]
    assert result.outcome_verdict["answerable"] is answerable
    assert result.status == ("complete" if answerable else "failed")
    if answerable:
        assert "40%" in result.speech
        assert "percentage" in result.outcome_verdict["available_data"]
    assert "温度" not in result.speech


async def test_weather_prefers_weather_entity(hass):
    hass.states.async_set(
        "weather.home", "sunny", {"friendly_name": "本地天气", "temperature": 28}
    )
    result, calls = await query(hass, "今天天气怎么样？", "")
    assert calls == []
    assert result.outcome_verdict["answerable"] is True
    assert result.route_kind == "local_weather"
    assert "晴" in result.speech


async def test_weather_does_not_substitute_air_quality(hass):
    result, calls = await query(
        hass, "今天天气怎么样？", "- names: 室外PM2.5\n  domain: sensor\n  state: 32\n"
    )
    assert calls == [{"domain": "weather"}]
    assert result.outcome_verdict["answerable"] is False
    assert result.status == "failed"
    assert "32" not in result.speech


async def test_status_question_stays_read_only(hass):
    result, calls = await query(
        hass, "现在风扇打开，是吗？", "- names: 风扇\n  domain: fan\n  state: on\n"
    )
    assert calls == [{"domain": "fan"}]
    assert result.speech == "风扇现在开着。"


@pytest.mark.parametrize("text", ["关闭所有灯。", "关闭所有的灯。", "关闭全部的灯。"])
def test_explicit_all_scope_survives_grammar(text):
    candidate = local_action_candidate(text)
    assert candidate.target_scope == "all"
