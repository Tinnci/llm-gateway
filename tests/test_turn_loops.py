"""Tests for replaceable turn-loop selection and execution."""

from custom_components.llm_gateway.capabilities import RouteDecision
from custom_components.llm_gateway.capability_executor import LocalCapabilityResult
from custom_components.llm_gateway.turn_loops import (
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
    assert result == LocalCapabilityResult(status="executed", speech="好了。")
    assert calls == [("fake-hass", "打开灯", context.route_decision)]


def test_deterministic_loop_declines_non_local_route() -> None:
    context = TurnLoopContext(
        text="解释一下",
        route_decision=_decision(route="fast", next_action="answer"),
    )

    assert select_turn_loop((DeterministicCapabilityLoop(),), context) is None
