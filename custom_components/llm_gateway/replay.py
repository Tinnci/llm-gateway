"""Side-effect-free replay and fork of stored voice turns."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

from .capabilities import decide_route
from .capability_executor import LocalCapabilityResult, local_action_candidate
from .traces import TraceTurn
from .turn_loops import (
    DeterministicCapabilityLoop,
    TurnLoopContext,
    TurnLoopServices,
    select_turn_loop,
)
from .voice_runs import VoiceRunRecorder

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .capabilities import RouteDecision
    from .traces import TraceStore

MAX_PROMPT_OVERRIDE_CHARS = 1200
SUPPORTED_LOOPS = {"deterministic_capability"}
SUPPORTED_ROUTES = {"recorded", "local_action"}


class ReplayError(ValueError):
    """A replay request cannot be executed safely."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class ReplayOverrides:
    """Bounded replay choices recorded in fork lineage."""

    loop: str = "deterministic_capability"
    route: str = "recorded"
    prompt: str = ""

    @classmethod
    def from_payload(cls, payload: object) -> ReplayOverrides:
        if payload is None:
            return cls()
        if not isinstance(payload, dict):
            raise ReplayError("invalid_overrides", "overrides must be an object")
        unknown = set(payload) - {"loop", "route", "prompt"}
        if unknown:
            raise ReplayError(
                "unsupported_override",
                f"unsupported overrides: {', '.join(sorted(unknown))}",
            )
        loop = str(payload.get("loop") or "deterministic_capability")
        route = str(payload.get("route") or "recorded")
        prompt = str(payload.get("prompt") or "")
        if loop not in SUPPORTED_LOOPS:
            raise ReplayError("unsupported_loop", f"unsupported loop: {loop}")
        if route not in SUPPORTED_ROUTES:
            raise ReplayError("unsupported_route", f"unsupported route: {route}")
        if len(prompt) > MAX_PROMPT_OVERRIDE_CHARS:
            raise ReplayError("prompt_too_long", "prompt override is too long")
        return cls(loop=loop, route=route, prompt=prompt)

    def as_dict(self) -> dict[str, str]:
        return {"loop": self.loop, "route": self.route, "prompt": self.prompt}


async def async_replay_turn(
    hass: HomeAssistant,
    trace_store: TraceStore,
    options: dict[str, Any],
    source_run_id: str,
    overrides: ReplayOverrides,
) -> dict[str, Any]:
    """Fork a stored turn through dry-run loop services and return its trace."""
    source = trace_store.get_run(source_run_id, include_raw=False)
    if source is None:
        raise ReplayError("run_not_found", "source run was not found or was pruned")
    user_text = str(
        source.get("user_text") or source.get("input", {}).get("text") or ""
    )
    if not user_text:
        raise ReplayError("missing_input", "source run has no replayable input")

    decision = _replay_route(user_text, overrides)
    context = TurnLoopContext(text=user_text, route_decision=decision)
    loop = select_turn_loop((DeterministicCapabilityLoop(),), context)
    if loop is None or loop.name != overrides.loop:
        raise ReplayError(
            "loop_not_applicable", "selected loop does not match the turn"
        )

    recorder = VoiceRunRecorder(limit=1)
    fork_id = recorder.start(
        conversation_id=str(source.get("conversation_id") or "") or None,
        user_text=user_text,
    )
    recorder.mark(
        fork_id,
        "replay_started",
        attrs={"replay_of": source_run_id, "mode": "dry_run"},
    )
    recorder.mark(fork_id, "loop_selected", attrs={"loop": loop.name})
    result = await loop.run(
        hass,
        context,
        TurnLoopServices(execute_local_capability=_async_dry_run_capability),
    )
    if result is None:
        raise ReplayError("not_replayable", "turn produced no dry-run proposal")
    proposed_actions = list(result.proposed_actions)
    recorder.mark(
        fork_id,
        "loop_completed",
        attrs={"loop": loop.name, "outcome": result.status},
    )
    timeline = recorder.finish(fork_id, status="complete", route="replay")
    lineage = {
        "replay_of": source_run_id,
        "fork_id": fork_id,
        "mode": "dry_run",
        "overrides": overrides.as_dict(),
    }
    replay_options = dict(options)
    replay_options["diagnostic_traces"] = True
    await trace_store.async_record_turn(
        replay_options,
        TraceTurn(
            conversation_id=str(source.get("conversation_id") or "") or None,
            user_text=user_text,
            assistant_text=result.speech,
            route={
                "kind": "replay",
                "model": "dry-run",
                "route_decision": decision.as_dict(),
            },
            latency_ms=int(timeline[-1].get("t_ms") or 0),
            status="complete",
            raw_payload={
                "input": {"text": user_text},
                "speech": {"final": result.speech},
                "replay": lineage,
                "proposed_actions": proposed_actions,
            },
            run_id=fork_id,
            timeline=timeline,
            lineage=lineage,
        ),
    )
    record = trace_store.get_run(fork_id, include_raw=False)
    if record is None:  # pragma: no cover - Store contract guard
        raise ReplayError("fork_not_stored", "fork trace was not stored")
    return record


def _replay_route(text: str, overrides: ReplayOverrides) -> RouteDecision:
    decision = decide_route(text)
    if overrides.route == "local_action":
        return replace(
            decision,
            route="local_action",
            next_action="execute_local",
            requires_llm=False,
        )
    return decision


async def _async_dry_run_capability(
    _hass: HomeAssistant,
    text: str,
    _decision: RouteDecision,
) -> LocalCapabilityResult | None:
    """Produce an action proposal without resolving or calling HA services."""
    candidate = local_action_candidate(text)
    if candidate is None:
        return None
    proposal = {
        "family": candidate.family,
        "action": candidate.action,
        "domain": candidate.domain,
        "area": candidate.area,
        "target_hint": candidate.target_hint,
        "target_scope": candidate.target_scope,
        "target_temperature": candidate.target_temperature,
        "volume_level": candidate.volume_level,
        "mute": candidate.mute,
    }
    return LocalCapabilityResult(
        status="dry_run",
        speech="Dry-run completed; no Home Assistant service was called.",
        candidate=candidate,
        reason="dry_run",
        action_trace={"proposed_actions": [proposal]},
    )
