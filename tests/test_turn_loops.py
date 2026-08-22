"""Tests for replaceable turn-loop selection and execution."""

from dataclasses import replace

from custom_components.llm_gateway.capabilities import RouteDecision
from custom_components.llm_gateway.capability_executor import LocalCapabilityResult
from custom_components.llm_gateway.turn_loops import (
    ClarificationDialogueLoop,
    DeterministicCapabilityLoop,
    TurnLoopContext,
    TurnLoopServices,
    select_turn_loop,
)


def _decision(*, route: str = "local_action", next_action: str = "execute_local"):
    return RouteDecision(
        route=route,
        task_type="home_control",
        task_family="home_control",
        next_action=next_action,
        confidence=1.0,
    )


async def test_deterministic_loop_uses_injected_executor() -> None:
    calls = []

    async def execute(hass, text, decision):
        calls.append((hass, text, decision))
        return LocalCapabilityResult(status="executed", speech="好了。")

    context = TurnLoopContext(text="打开灯", route_decision=_decision())
    loop = select_turn_loop((DeterministicCapabilityLoop(),), context)

    assert loop is not None
    result = await loop.run(
        "fake-hass",
        context,
        TurnLoopServices(execute_local_capability=execute),
    )
    assert result is not None
    assert result.status == "executed"
    assert result.speech == "好了。"
    assert result.route_kind == "local_action"
    assert result.route_model == "capability_executor"
    assert result.trace_events[0].stage == "local_capability_execute"
    assert result.trace_events[0].status == "ok"
    assert calls == [("fake-hass", "打开灯", context.route_decision)]


def test_deterministic_loop_declines_non_local_route() -> None:
    context = TurnLoopContext(
        text="解释一下",
        route_decision=_decision(route="fast", next_action="answer"),
    )

    assert select_turn_loop((DeterministicCapabilityLoop(),), context) is None


async def test_clarification_loop_proposes_prompt_and_weather_frame() -> None:
    decision = _decision(route="local_clarify", next_action="clarify")
    decision = replace(
        decision,
        task_type="weather_forecast_query",
        task_family="location_dependent_query",
        missing_requirements=("location_hint",),
        user_visible_prompt="你想查哪个地方？",
    )
    context = TurnLoopContext(
        text="明天天气怎么样",
        route_decision=decision,
        turn_id="turn-weather",
    )
    loop = select_turn_loop(
        (DeterministicCapabilityLoop(), ClarificationDialogueLoop()),
        context,
    )

    assert isinstance(loop, ClarificationDialogueLoop)
    result = await loop.run("fake-hass", context, TurnLoopServices())

    assert result.status == "clarify"
    assert result.speech == "你想查哪个地方？"
    assert result.route_kind == "local_clarify"
    assert result.trace_events[0].attrs["llm_used"] is False
    assert result.dialogue_frame is not None
    assert result.dialogue_frame.id == "turn-weather:weather_location"
    assert result.dialogue_frame.status == "awaiting_referent"


def test_clarification_loop_does_not_claim_non_local_clarify_route() -> None:
    context = TurnLoopContext(
        text="解释一下",
        route_decision=_decision(route="fast", next_action="clarify"),
    )

    assert select_turn_loop((ClarificationDialogueLoop(),), context) is None
