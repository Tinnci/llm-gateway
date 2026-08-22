"""Replaceable turn-loop seams owned by the conversation kernel."""

from __future__ import annotations

from dataclasses import dataclass, field
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

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable

    from homeassistant.core import HomeAssistant

    from .capabilities import RouteDecision


@dataclass(frozen=True, slots=True)
class TurnLoopContext:
    """Input a loop may inspect without owning turn lifecycle state."""

    text: str
    route_decision: RouteDecision
    turn_id: str = ""


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
    ) -> TurnLoopResult | None:
        """Run without committing a response or writing traces."""


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
