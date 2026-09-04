"""Tests for replaceable turn-loop selection and execution."""

import asyncio
from dataclasses import replace

from custom_components.llm_gateway.capabilities import RouteDecision
from custom_components.llm_gateway.capability_executor import LocalCapabilityResult
from custom_components.llm_gateway.turn_loops import (
    ClarificationDialogueLoop,
    DeterministicCapabilityLoop,
    LocalLiveContextLoop,
    TurnLoopContext,
    TurnLoopContinuation,
    TurnLoopResult,
    TurnLoopServices,
    run_turn_loop,
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


async def test_harness_loop_continues_then_stops_with_a_bounded_step_count() -> None:
    class RepairingLoop:
        name = "repairing"
        calls = 0

        def matches(self, _context):
            return True

        async def run(self, _hass, context, _services):
            self.calls += 1
            if self.calls == 1:
                return TurnLoopContinuation("repair_target", context.state)
            return TurnLoopResult(
                status="complete",
                speech="好了。",
                route_kind="test",
                route_model="test",
                stop_reason="answered",
            )

    loop = RepairingLoop()
    result = await run_turn_loop(
        loop,
        "fake-hass",
        TurnLoopContext(
            text="查询",
            route_decision=_decision(
                route="local_live_context",
                next_action="call_tool_then_local_render",
            ),
        ),
        TurnLoopServices(),
    )

    assert result is not None
    assert result.step_count == 2
    assert result.continuation_reasons == ("repair_target",)
    assert [event.stage for event in result.trace_events] == [
        "harness_step_start",
        "harness_step_end",
        "harness_step_start",
        "harness_step_end",
    ]
    assert result.final_phase == "initial"
    assert result.total_duration_ms >= 0


async def test_harness_loop_rejects_write_continuations() -> None:
    original = _decision(next_action="execute_local")

    class RetryingWriteLoop:
        name = "retrying_write"

        def matches(self, _context):
            return True

        async def run(self, _hass, context, _services):
            return TurnLoopContinuation(
                "retry_write",
                context.state.advance("retry", "service_error"),
            )

    result = await run_turn_loop(
        RetryingWriteLoop(),
        "fake-hass",
        TurnLoopContext(text="打开灯", route_decision=original),
        TurnLoopServices(),
    )

    assert result is not None
    assert result.status == "failed"
    assert result.stop_reason == "write_loop_continuation_forbidden"
    assert result.final_phase == "invariant_failed"
    assert result.trace_events[-1].stage == "harness_loop_invariant_failed"


async def test_harness_loop_stops_a_hung_step_at_the_shared_deadline() -> None:
    class HungLoop:
        name = "hung"

        def matches(self, _context):
            return True

        async def run(self, _hass, _context, _services):
            await asyncio.sleep(1)

    result = await run_turn_loop(
        HungLoop(),
        "fake-hass",
        TurnLoopContext(text="查询", route_decision=_decision()),
        TurnLoopServices(),
        timeout_s=0.01,
    )

    assert result is not None
    assert result.status == "failed"
    assert result.stop_reason == "loop_timeout"
    assert [event.stage for event in result.trace_events[-2:]] == [
        "harness_step_end",
        "harness_loop_timeout",
    ]


async def test_local_live_context_loop_validates_device_state_before_stop() -> None:
    decision = _decision(
        route="local_live_context", next_action="call_tool_then_local_render"
    )
    decision = replace(
        decision,
        task_family="home_state",
        task_type="device_state_query",
        metadata={"domain": "fan", "device_hint": "风扇"},
    )
    context = TurnLoopContext(text="风扇开着吗？", route_decision=decision)

    async def execute(_args):
        return {
            "success": True,
            "result": (
                "Live Context:\n- names: 米家循环扇 风扇\n  domain: fan\n  state: on\n"
            ),
        }

    result = await run_turn_loop(
        LocalLiveContextLoop(),
        "fake-hass",
        context,
        TurnLoopServices(
            plan_live_context=lambda _text, _decision: (
                {"domain": "fan"},
                {"domain": "fan", "device_hint": "风扇"},
            ),
            execute_live_context=execute,
        ),
    )

    assert result is not None
    assert result.status == "complete"
    assert result.speech == "米家循环扇 风扇现在开着。"
    assert result.stop_reason == "answered"
    assert result.outcome_verdict["target_covered"] is True
    assert any(event.stage == "outcome_evaluated" for event in result.trace_events)


async def test_local_live_context_loop_rejects_unrelated_sensor_result() -> None:
    decision = replace(
        _decision(
            route="local_live_context", next_action="call_tool_then_local_render"
        ),
        task_family="home_state",
        task_type="device_state_query",
        metadata={"domain": "fan", "device_hint": "风扇"},
    )

    async def execute(_args):
        return {
            "success": True,
            "result": "Live Context:\n- names: 温度\n  domain: sensor\n  state: 26\n",
        }

    result = await run_turn_loop(
        LocalLiveContextLoop(),
        "fake-hass",
        TurnLoopContext(text="风扇开着吗？", route_decision=decision),
        TurnLoopServices(
            plan_live_context=lambda _text, _decision: (
                {"domain": "fan"},
                {"domain": "fan", "device_hint": "风扇"},
            ),
            execute_live_context=execute,
        ),
    )

    assert result is not None
    assert result.status == "failed"
    assert result.stop_reason == "requested_target_missing"
    assert result.outcome_verdict["answerable"] is False
    assert result.outcome_verdict["target_covered"] is False
    assert result.outcome_verdict["reason"] == "requested_target_missing"
    assert result.outcome_verdict["required_data"] == ["entity_state"]
    assert "温度" not in result.speech
    assert result.step_count == 1
    assert result.continuation_reasons == ()
    assert result.final_phase == "initial"


async def test_local_live_context_loop_recovers_with_broad_second_step() -> None:
    decision = replace(
        _decision(
            route="local_live_context", next_action="call_tool_then_local_render"
        ),
        task_family="home_state",
        task_type="device_state_query",
        metadata={"domain": "fan", "device_hint": "风扇", "area": "卧室"},
    )
    calls: list[dict[str, str]] = []

    async def execute(args):
        calls.append(args)
        if len(calls) == 1:
            return {
                "success": True,
                "result": (
                    "Live Context:\n- names: 温度\n  domain: sensor\n  state: 26\n"
                ),
            }
        return {
            "success": True,
            "result": (
                "Live Context:\n- names: 卧室风扇\n"
                "  domain: fan\n  state: off\n  areas: 卧室\n"
            ),
        }

    result = await run_turn_loop(
        LocalLiveContextLoop(),
        "fake-hass",
        TurnLoopContext(text="卧室风扇开着吗？", route_decision=decision),
        TurnLoopServices(
            plan_live_context=lambda _text, _decision: (
                {"domain": "fan", "area": "卧室"},
                {"domain": "fan", "area": "卧室", "device_hint": "风扇"},
            ),
            execute_live_context=execute,
        ),
    )

    assert result is not None
    assert result.speech == "卧室风扇现在关着。"
    assert result.step_count == 2
    assert result.stop_reason == "answered"
    assert result.final_phase == "relax_area"
    assert calls == [{"domain": "fan", "area": "卧室"}, {"domain": "fan"}]
    call_events = [
        event
        for event in result.trace_events
        if event.stage == "local_live_context_call"
    ]
    assert [event.attrs["iteration"] for event in call_events] == [0, 1]
    assert len({event.attrs["operation_id"] for event in call_events}) == 1


async def test_local_live_context_loop_retries_one_transient_tool_error() -> None:
    decision = replace(
        _decision(
            route="local_live_context", next_action="call_tool_then_local_render"
        ),
        task_family="home_state",
        task_type="device_state_query",
        metadata={"domain": "fan", "device_hint": "风扇"},
    )
    calls = 0

    async def execute(_args):
        nonlocal calls
        calls += 1
        if calls == 1:
            return {"error": "temporary_failure", "retryable": True}
        return {
            "success": True,
            "result": (
                "Live Context:\n- names: 米家循环扇 风扇\n  domain: fan\n  state: on\n"
            ),
        }

    result = await run_turn_loop(
        LocalLiveContextLoop(),
        "fake-hass",
        TurnLoopContext(text="风扇开着吗？", route_decision=decision),
        TurnLoopServices(
            plan_live_context=lambda _text, _decision: (
                {"domain": "fan"},
                {"domain": "fan", "device_hint": "风扇"},
            ),
            execute_live_context=execute,
        ),
    )

    assert result is not None
    assert result.status == "complete"
    assert result.step_count == 2
    assert result.continuation_reasons == ("retry_transient_tool_error",)
    assert result.final_phase == "retry_targeted"


async def test_local_live_context_loop_does_not_retry_permanent_error() -> None:
    decision = replace(
        _decision(
            route="local_live_context", next_action="call_tool_then_local_render"
        ),
        task_family="home_state",
        task_type="device_state_query",
        metadata={"domain": "fan", "device_hint": "风扇"},
    )
    calls = 0

    async def execute(_args):
        nonlocal calls
        calls += 1
        return {
            "error": "missing_GetLiveContext_tool",
            "code": "tool_unavailable",
            "retryable": False,
        }

    result = await run_turn_loop(
        LocalLiveContextLoop(),
        "fake-hass",
        TurnLoopContext(text="风扇开着吗？", route_decision=decision),
        TurnLoopServices(
            plan_live_context=lambda _text, _decision: (
                {"domain": "fan"},
                {"domain": "fan", "device_hint": "风扇"},
            ),
            execute_live_context=execute,
        ),
    )

    assert result is not None
    assert calls == 1
    assert result.status == "failed"
    assert result.outcome_verdict["retryable"] is False
