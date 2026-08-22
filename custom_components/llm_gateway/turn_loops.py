"""Replaceable turn-loop seams owned by the conversation kernel."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from .capability_executor import async_try_execute_local_capability

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable

    from homeassistant.core import HomeAssistant

    from .capabilities import RouteDecision
    from .capability_executor import LocalCapabilityResult


@dataclass(frozen=True, slots=True)
class TurnLoopContext:
    """Input a loop may inspect without owning turn lifecycle state."""

    text: str
    route_decision: RouteDecision


@dataclass(frozen=True, slots=True)
class TurnLoopServices:
    """Effects explicitly available to deterministic loops."""

    execute_local_capability: Callable[
        [HomeAssistant, str, RouteDecision],
        Awaitable[LocalCapabilityResult | None],
    ] = async_try_execute_local_capability


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
    ) -> LocalCapabilityResult | None:
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
    ) -> LocalCapabilityResult | None:
        return await services.execute_local_capability(
            hass,
            context.text,
            context.route_decision,
        )


def select_turn_loop(
    loops: Iterable[TurnLoop],
    context: TurnLoopContext,
) -> TurnLoop | None:
    """Select the first configured loop that claims the input."""
    return next((loop for loop in loops if loop.matches(context)), None)
