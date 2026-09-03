"""Replaceable turn-loop seams owned by the conversation kernel."""

from __future__ import annotations

import asyncio
import time
from copy import deepcopy
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any, Protocol

from .action_plan import ActionPlan, ActionPlanResult, async_execute_action_plan
from .capability_executor import (
    LocalCapabilityResult,
    async_try_execute_local_capability,
)
from .dialogue import (
    DialogueFrame,
    dialogue_frame_from_local_capability,
    dialogue_frame_from_route,
)
from .static_context import render_scalar_state_answer

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable

    from homeassistant.core import HomeAssistant

    from .capabilities import RouteDecision


@dataclass(frozen=True, slots=True)
class TurnLoopState:
    """Small immutable state carried between bounded loop steps."""

    phase: str = "initial"
    observations: tuple[str, ...] = ()

    def advance(self, phase: str, observation: str) -> TurnLoopState:
        """Return the next state without sharing mutable step memory."""
        return TurnLoopState(
            phase=phase,
            observations=(*self.observations, observation),
        )


@dataclass(frozen=True, slots=True)
class TurnLoopContext:
    """Input a loop may inspect without owning turn lifecycle state."""

    text: str
    route_decision: RouteDecision
    turn_id: str = ""
    step: int = 0
    state: TurnLoopState = field(default_factory=TurnLoopState)


@dataclass(frozen=True, slots=True)
class TurnLoopTraceEvent:
    """One trace event proposed by a loop and committed by the kernel."""

    stage: str
    status: str = "ok"
    attrs: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TurnLoopResult:
    """Effect proposal returned to the kernel for trace and response commit."""

    status: str
    speech: str
    route_kind: str
    route_model: str
    trace_events: tuple[TurnLoopTraceEvent, ...] = ()
    dialogue_frame: DialogueFrame | None = None
    proposed_actions: tuple[dict[str, Any], ...] = ()
    stop_reason: str = "completed"
    step_count: int = 1
    continuation_reasons: tuple[str, ...] = ()
    outcome_verdict: dict[str, Any] = field(default_factory=dict)
    total_duration_ms: int = 0
    final_phase: str = ""


@dataclass(frozen=True, slots=True)
class TurnLoopContinuation:
    """Request another bounded step before the turn can stop."""

    reason: str
    next_state: TurnLoopState
    trace_events: tuple[TurnLoopTraceEvent, ...] = ()


type TurnLoopDecision = TurnLoopResult | TurnLoopContinuation | None


@dataclass(frozen=True, slots=True)
class TurnLoopServices:
    """Effects explicitly available to deterministic loops."""

    execute_local_capability: Callable[
        [HomeAssistant, str, RouteDecision],
        Awaitable[LocalCapabilityResult | None],
    ] = async_try_execute_local_capability
    execute_action_plan: Callable[
        [HomeAssistant, ActionPlan], Awaitable[ActionPlanResult]
    ] = async_execute_action_plan
    plan_live_context: (
        Callable[[str, RouteDecision], tuple[dict[str, Any], dict[str, str]]] | None
    ) = None
    execute_live_context: (
        Callable[[dict[str, Any]], Awaitable[dict[str, Any]]] | None
    ) = None


class TurnLoop(Protocol):
    """One independently replaceable turn capability."""

    name: str

    def matches(self, context: TurnLoopContext) -> bool:
        """Return whether this loop owns the supplied input."""

    async def run(
        self,
        hass: HomeAssistant,
        context: TurnLoopContext,
        services: TurnLoopServices,
    ) -> TurnLoopDecision:
        """Run without committing a response or writing traces."""


MAX_HARNESS_LOOP_STEPS = 2
HARNESS_LOOP_TIMEOUT_S = 8.0


async def run_turn_loop(  # noqa: PLR0913 - explicit policy overrides aid tests.
    loop: TurnLoop,
    hass: HomeAssistant,
    context: TurnLoopContext,
    services: TurnLoopServices,
    *,
    max_steps: int = MAX_HARNESS_LOOP_STEPS,
    timeout_s: float = HARNESS_LOOP_TIMEOUT_S,
) -> TurnLoopResult | None:
    """Drive one loop through bounded steps until it can stop."""
    started = time.monotonic()
    effective_steps = max(1, int(max_steps))
    deadline = started + max(0.001, float(timeout_s))
    committed_route = deepcopy(context.route_decision)
    state = context.state
    events: list[TurnLoopTraceEvent] = []
    continuation_reasons: list[str] = []
    for step in range(1, effective_steps + 1):
        current = TurnLoopContext(
            text=context.text,
            route_decision=deepcopy(committed_route),
            turn_id=context.turn_id,
            step=step,
            state=state,
        )
        step_started = time.monotonic()
        events.append(
            TurnLoopTraceEvent(
                stage="harness_step_start",
                attrs={"loop": loop.name, "step": step},
            )
        )
        try:
            async with asyncio.timeout(max(0.001, deadline - time.monotonic())):
                decision = await loop.run(hass, current, services)
        except TimeoutError:
            return _loop_timeout_failure(
                loop,
                events,
                step=step,
                step_started=step_started,
                started=started,
                phase=state.phase,
            )
        if decision is None:
            events.append(
                TurnLoopTraceEvent(
                    stage="harness_step_end",
                    status="error",
                    attrs={"loop": loop.name, "step": step, "outcome": "declined"},
                )
            )
            return None
        if isinstance(decision, TurnLoopContinuation):
            if committed_route.next_action in {"execute_local", "execute_plan"}:
                return _loop_invariant_failure(
                    loop,
                    events,
                    step=step,
                    started=started,
                    reason="write_loop_continuation_forbidden",
                )
            continuation_reasons.append(decision.reason)
            events.extend(decision.trace_events)
            events.append(
                TurnLoopTraceEvent(
                    stage="harness_step_end",
                    status="warning",
                    attrs={
                        "loop": loop.name,
                        "step": step,
                        "outcome": "continue",
                        "reason": decision.reason,
                        "duration_ms": _elapsed_ms(step_started),
                        "next_phase": decision.next_state.phase,
                    },
                )
            )
            state = decision.next_state
            continue
        events.extend(decision.trace_events)
        event_status = (
            "error"
            if decision.status in {"failed", "blocked", "error"}
            else "warning"
            if decision.status in {"partial", "clarify"}
            else "ok"
        )
        events.append(
            TurnLoopTraceEvent(
                stage="harness_step_end",
                status=event_status,
                attrs={
                    "loop": loop.name,
                    "step": step,
                    "outcome": decision.status,
                    "stop_reason": decision.stop_reason,
                    "duration_ms": _elapsed_ms(step_started),
                },
            )
        )
        return replace(
            decision,
            trace_events=tuple(events),
            step_count=step,
            continuation_reasons=tuple(continuation_reasons),
            total_duration_ms=_elapsed_ms(started),
            final_phase=state.phase,
        )
    return TurnLoopResult(
        status="failed",
        speech="这次查询没有在限定步骤内完成，请稍后重试。",
        route_kind="local_harness_guard",
        route_model="harness_loop",
        trace_events=(
            *events,
            TurnLoopTraceEvent(
                stage="harness_loop_budget_exceeded",
                status="error",
                attrs={"loop": loop.name, "max_steps": effective_steps},
            ),
        ),
        stop_reason="step_budget_exceeded",
        step_count=effective_steps,
        continuation_reasons=tuple(continuation_reasons),
        total_duration_ms=_elapsed_ms(started),
        final_phase=state.phase,
        outcome_verdict={
            "answerable": False,
            "target_covered": False,
            "reason": "step_budget_exceeded",
        },
    )


def _elapsed_ms(started: float) -> int:
    return max(0, round((time.monotonic() - started) * 1000))


def _loop_invariant_failure(
    loop: TurnLoop,
    events: list[TurnLoopTraceEvent],
    *,
    step: int,
    started: float,
    reason: str,
) -> TurnLoopResult:
    verdict = {"answerable": False, "reason": reason}
    return TurnLoopResult(
        status="failed",
        speech="这次查询无法安全继续，请重新发起。",
        route_kind="local_harness_guard",
        route_model="harness_loop",
        trace_events=(
            *events,
            TurnLoopTraceEvent(
                stage="harness_loop_invariant_failed",
                status="error",
                attrs={"loop": loop.name, "step": step, "reason": reason},
            ),
        ),
        stop_reason=reason,
        step_count=step,
        outcome_verdict=verdict,
        total_duration_ms=_elapsed_ms(started),
        final_phase="invariant_failed",
    )


def _loop_timeout_failure(  # noqa: PLR0913 - terminal trace needs both clocks.
    loop: TurnLoop,
    events: list[TurnLoopTraceEvent],
    *,
    step: int,
    step_started: float,
    started: float,
    phase: str,
) -> TurnLoopResult:
    reason = "loop_timeout"
    verdict = {"answerable": False, "target_covered": False, "reason": reason}
    return TurnLoopResult(
        status="failed",
        speech="这次查询超时了，请稍后重试。",
        route_kind="local_harness_guard",
        route_model="harness_loop",
        trace_events=(
            *events,
            TurnLoopTraceEvent(
                stage="harness_step_end",
                status="error",
                attrs={
                    "loop": loop.name,
                    "step": step,
                    "outcome": "failed",
                    "stop_reason": reason,
                    "duration_ms": _elapsed_ms(step_started),
                },
            ),
            TurnLoopTraceEvent(
                stage="harness_loop_timeout",
                status="error",
                attrs={"loop": loop.name, "step": step, "phase": phase},
            ),
        ),
        stop_reason=reason,
        step_count=step,
        outcome_verdict=verdict,
        total_duration_ms=_elapsed_ms(started),
        final_phase=phase,
    )


class LocalLiveContextLoop:
    """Query live HA context and stop only after answerability validation."""

    name = "local_live_context"

    def matches(self, context: TurnLoopContext) -> bool:
        return (
            context.route_decision.task_type == "device_state_query"
            and context.route_decision.next_action == "call_tool_then_local_render"
        )

    async def run(
        self,
        _hass: HomeAssistant,
        context: TurnLoopContext,
        services: TurnLoopServices,
    ) -> TurnLoopDecision:
        if services.plan_live_context is None or services.execute_live_context is None:
            return None
        tool_args, slots = services.plan_live_context(
            context.text, context.route_decision
        )
        strategy = context.state.phase
        if strategy == "relax_area":
            tool_args = {
                key: value for key, value in tool_args.items() if key != "area"
            }
        slots = {**slots, "strategy": strategy}
        events = [
            TurnLoopTraceEvent(
                stage="local_live_context_call",
                attrs={
                    "name": "GetLiveContext",
                    "args": tool_args,
                    "slots": slots,
                    "llm_used": False,
                    "tools_used": ["GetLiveContext"],
                    "step": context.step,
                    "iteration": context.step - 1,
                    "strategy": strategy,
                    "operation_id": _live_context_operation_id(context),
                },
            )
        ]
        result = await services.execute_live_context(tool_args)
        error = str(result.get("error") or "")
        events.append(
            TurnLoopTraceEvent(
                stage="tool_result",
                status="error" if error else "ok",
                attrs={
                    "name": "GetLiveContext",
                    "iteration": context.step - 1,
                    "local_live_context": True,
                    "step": context.step,
                    "strategy": strategy,
                    "operation_id": _live_context_operation_id(context),
                    "error": error,
                    "retryable": bool(result.get("retryable")),
                },
            )
        )
        if error:
            if strategy == "initial" and result.get("retryable") is True:
                return TurnLoopContinuation(
                    reason="retry_transient_tool_error",
                    next_state=context.state.advance("retry_targeted", "tool_error"),
                    trace_events=tuple(events),
                )
            verdict = {
                "answerable": False,
                "target_covered": False,
                "reason": "tool_error",
                "error_code": str(result.get("code") or error),
                "retryable": bool(result.get("retryable")),
            }
            events.append(
                TurnLoopTraceEvent(
                    stage="outcome_evaluated", status="error", attrs=verdict
                )
            )
            return TurnLoopResult(
                status="failed",
                speech="暂时没有本地状态数据。",
                route_kind="local_live_context",
                route_model="live_context_renderer",
                trace_events=tuple(events),
                stop_reason="tool_error",
                outcome_verdict=verdict,
            )
        rendered = render_scalar_state_answer(
            context.text,
            result,
            task_type=context.route_decision.task_type,
            route_decision=context.route_decision,
        )
        if rendered is None:
            verdict = {
                "answerable": False,
                "target_covered": False,
                "reason": "no_renderable_state",
            }
            events.extend(
                (
                    TurnLoopTraceEvent(
                        stage="local_state_render", status="error", attrs=verdict
                    ),
                    TurnLoopTraceEvent(
                        stage="outcome_evaluated", status="error", attrs=verdict
                    ),
                )
            )
            return TurnLoopResult(
                status="failed",
                speech="暂时没有本地状态数据。",
                route_kind="local_live_context",
                route_model="live_context_renderer",
                trace_events=tuple(events),
                stop_reason="no_renderable_state",
                outcome_verdict=verdict,
            )
        if (
            not rendered.answerable
            and rendered.outcome_reason == "requested_target_missing"
            and strategy == "initial"
            and "area" in tool_args
        ):
            events.append(
                TurnLoopTraceEvent(
                    stage="outcome_evaluated",
                    status="warning",
                    attrs={
                        "answerable": False,
                        "target_covered": False,
                        "reason": "requested_target_missing",
                        "provisional": True,
                        "operation_id": _live_context_operation_id(context),
                    },
                )
            )
            return TurnLoopContinuation(
                reason="relax_area_filter",
                next_state=context.state.advance(
                    "relax_area", "requested_target_missing"
                ),
                trace_events=tuple(events),
            )
        verdict = {
            "answerable": rendered.answerable,
            "target_covered": rendered.target_covered,
            "reason": rendered.outcome_reason or "answered",
            "required_data": list(rendered.required_data),
            "available_data": list(rendered.available_data),
        }
        events.extend(
            (
                TurnLoopTraceEvent(
                    stage="local_state_render",
                    status="ok" if rendered.answerable else "warning",
                    attrs=rendered.trace_attrs(),
                ),
                TurnLoopTraceEvent(
                    stage="outcome_evaluated",
                    status="ok" if rendered.answerable else "warning",
                    attrs=verdict,
                ),
            )
        )
        result_status = (
            "complete"
            if rendered.answerable
            else "clarify"
            if rendered.outcome_reason == "ambiguous_target"
            else "failed"
        )
        return TurnLoopResult(
            status=result_status,
            speech=rendered.speech,
            route_kind="local_live_context",
            route_model="live_context_renderer",
            trace_events=tuple(events),
            stop_reason=verdict["reason"],
            outcome_verdict=verdict,
        )


def _live_context_operation_id(context: TurnLoopContext) -> str:
    turn = context.turn_id or "unassigned"
    return f"{turn}:GetLiveContext"


class DeterministicCapabilityLoop:
    """Execute explicit low-risk local actions without an LLM call."""

    name = "deterministic_capability"

    def matches(self, context: TurnLoopContext) -> bool:
        decision = context.route_decision
        return (
            decision.next_action == "execute_local" and decision.route == "local_action"
        )

    async def run(
        self,
        hass: HomeAssistant,
        context: TurnLoopContext,
        services: TurnLoopServices,
    ) -> TurnLoopResult | None:
        capability = await services.execute_local_capability(
            hass,
            context.text,
            context.route_decision,
        )
        if capability is None or not capability.handled:
            return None
        trace_attrs = capability.trace_attrs()
        action_trace = trace_attrs.get("action_trace")
        action_trace = action_trace if isinstance(action_trace, dict) else {}
        proposed_actions = tuple(
            dict(action)
            for action in action_trace.get("proposed_actions", ())
            if isinstance(action, dict)
        )
        events = [
            TurnLoopTraceEvent(
                stage="local_capability_execute",
                status={"executed": "ok", "partial": "warning"}.get(
                    capability.status, capability.status
                ),
                attrs=trace_attrs,
            )
        ]
        frame = None
        if capability.status == "clarify":
            frame = dialogue_frame_from_local_capability(
                context.turn_id,
                capability.speech,
                context.route_decision,
                trace_attrs,
            )
            events.append(
                TurnLoopTraceEvent(
                    stage="local_route_clarify",
                    attrs={
                        "llm_used": False,
                        "tools_used": [],
                        "tools_used_count": 0,
                        **context.route_decision.as_dict(),
                        "interaction_state": "awaiting_user_info",
                        "prompt": capability.speech,
                        "commitment": action_trace.get("resolution_frame", {}).get(
                            "commitment", {}
                        ),
                    },
                )
            )
        return TurnLoopResult(
            status=capability.status,
            speech=capability.speech,
            route_kind="local_action",
            route_model="capability_executor",
            trace_events=tuple(events),
            dialogue_frame=frame,
            proposed_actions=proposed_actions,
        )


class ClarificationDialogueLoop:
    """Propose a local clarification without owning dialogue state or commit."""

    name = "clarification_dialogue"

    def matches(self, context: TurnLoopContext) -> bool:
        decision = context.route_decision
        return decision.route == "local_clarify" and decision.next_action in {
            "ask_location_permission",
            "clarify",
        }

    async def run(
        self,
        _hass: HomeAssistant,
        context: TurnLoopContext,
        _services: TurnLoopServices,
    ) -> TurnLoopResult:
        decision = context.route_decision
        prompt = (
            decision.user_visible_prompt or "我还不确定你想让我做什么，可以换个说法吗？"
        )
        return TurnLoopResult(
            status="clarify",
            speech=prompt,
            route_kind="local_clarify",
            route_model="capability_router",
            trace_events=(
                TurnLoopTraceEvent(
                    stage="local_route_clarify",
                    attrs={
                        "llm_used": False,
                        "tools_used": [],
                        "tools_used_count": 0,
                        **decision.as_dict(),
                        "interaction_state": "awaiting_user_info",
                    },
                ),
            ),
            dialogue_frame=dialogue_frame_from_route(context.turn_id, decision),
        )


class ActionPlanLoop:
    """Execute one validated declarative compound plan."""

    name = "action_plan"

    def matches(self, context: TurnLoopContext) -> bool:
        return context.route_decision.next_action == "execute_plan" and isinstance(
            context.route_decision.metadata.get("action_plan"), dict
        )

    async def run(
        self,
        hass: HomeAssistant,
        context: TurnLoopContext,
        services: TurnLoopServices,
    ) -> TurnLoopResult:
        plan = ActionPlan.from_payload(context.route_decision.metadata["action_plan"])
        result = await services.execute_action_plan(hass, plan)
        return TurnLoopResult(
            status=result.status,
            speech=result.speech,
            route_kind="local_action_plan",
            route_model="typed_action_plan",
            proposed_actions=tuple(item.as_dict() for item in plan.actions),
            trace_events=(
                TurnLoopTraceEvent(
                    stage="action_plan_execute",
                    status=(
                        "warning"
                        if result.status in {"partial", "blocked", "error"}
                        else "ok"
                    ),
                    attrs={
                        "status": result.status,
                        "reason": result.reason,
                        "reads": dict(result.reads),
                        "actions": list(result.actions),
                        "failed_actions": list(result.failed_actions),
                        "policy": list(result.policy),
                    },
                ),
            ),
        )


def select_turn_loop(
    loops: Iterable[TurnLoop],
    context: TurnLoopContext,
) -> TurnLoop | None:
    """Select the first configured loop that claims the input."""
    return next((loop for loop in loops if loop.matches(context)), None)
