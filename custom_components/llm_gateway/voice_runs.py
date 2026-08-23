"""In-memory timeline for recent voice/text assistant runs."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from homeassistant.util import ulid

RUN_LIMIT = 40
STALE_RUNNING_MS = 10 * 60 * 1000
EVENT_TYPES = {
    "barge_in_requested": "playback.interrupt.requested",
    "stale_result_discarded": "gateway.result.late_dropped",
    "turn_cancelled": "gateway.turn.superseded",
}
EVENT_TYPE_TO_STAGE = {event_type: stage for stage, event_type in EVENT_TYPES.items()}
MAX_ATTR_ITEMS = 40
MAX_ATTR_TEXT = 2000
MAX_ATTR_DEPTH = 4


def event_stage(event: dict[str, Any]) -> str:
    """Return the original pipeline stage for one serialized event.

    Canonical events derive the stage from ``event_type``; legacy records that
    still carry a top-level ``stage`` keep working through the same projection.
    """
    legacy_stage = event.get("stage")
    if legacy_stage:
        return str(legacy_stage)
    event_type = str(event.get("event_type") or "")
    if event_type in EVENT_TYPE_TO_STAGE:
        return EVENT_TYPE_TO_STAGE[event_type]
    if event_type.startswith("gateway."):
        return event_type.removeprefix("gateway.").replace(".", "_")
    return event_type


def event_payload(event: dict[str, Any]) -> dict[str, Any]:
    """Return the merged status + attrs payload for one serialized event."""
    payload = event.get("payload")
    if isinstance(payload, dict):
        return dict(payload)
    legacy_attrs = event.get("attrs")
    attrs = dict(legacy_attrs) if isinstance(legacy_attrs, dict) else {}
    return {"status": str(event.get("status") or "ok"), **attrs}


def _bound_attrs(value: object, *, depth: int = 0) -> object:
    """Bound live-run attrs at the recorder boundary.

    Diagnostic attrs are JSON-safe at the call sites, but this keeps one
    oversized tool result or entity list from growing an in-memory run without
    limit. The full trace store still applies its own redaction and bounds.
    """
    if depth >= MAX_ATTR_DEPTH:
        return _truncate_attr_text(value)
    if isinstance(value, dict):
        return {
            str(key): _bound_attrs(item, depth=depth + 1)
            for key, item in list(value.items())[:MAX_ATTR_ITEMS]
        }
    if isinstance(value, list):
        return [_bound_attrs(item, depth=depth + 1) for item in value[:MAX_ATTR_ITEMS]]
    if isinstance(value, str):
        return _truncate_attr_text(value)
    if isinstance(value, bool | int | float) or value is None:
        return value
    return _truncate_attr_text(value)


def _truncate_attr_text(value: object) -> str:
    text = str(value).replace("\x00", "").strip()
    if len(text) <= MAX_ATTR_TEXT:
        return text
    return text[: MAX_ATTR_TEXT - 1].rstrip() + "…"


@dataclass(frozen=True, slots=True)
class VoiceRunEvent:
    """One immutable event in a correlated voice-turn stream."""

    event_id: str
    turn_id: str
    sequence: int
    stage: str
    t_ms: int
    occurred_at: str
    caused_by: str = ""
    status: str = "ok"
    attrs: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """Return the canonical serialized event.

        The canonical form is intentionally flat: ordering/identity fields at
        top level, everything stage-specific inside ``payload``. Callers that
        need the legacy stage/attrs view derive it through :func:`event_stage`
        and :func:`event_payload` instead of maintaining a second copy.
        """
        return {
            "event_id": self.event_id,
            "turn_id": self.turn_id,
            "event_type": EVENT_TYPES.get(
                self.stage,
                f"gateway.{self.stage.replace('_', '.')}",
            ),
            "source": "llm-gateway",
            "source_sequence": self.sequence,
            "occurred_at": self.occurred_at,
            "monotonic_ms": self.t_ms,
            "caused_by": self.caused_by,
            "privacy": "trace_safe",
            "payload": {**_bound_attrs(self.attrs), "status": self.status},
        }


@dataclass(slots=True)
class VoiceRun:
    """One observable assistant run."""

    id: str
    created_at: float
    started_monotonic: float
    conversation_id: str
    user_text: str
    status: str = "running"
    route: str = ""
    provider: str = ""
    latency_ms: int = 0
    events: list[VoiceRunEvent] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        last_event = self.events[-1] if self.events else None
        elapsed_ms = round((time.time() - self.created_at) * 1000)
        running_duration_ms = (
            elapsed_ms if self.status == "running" else self.latency_ms
        )
        return {
            "id": self.id,
            "created_at": self.created_at,
            "conversation_id": self.conversation_id,
            "user_text": self.user_text,
            "status": self.status,
            "route": self.route,
            "provider": self.provider,
            "latency_ms": self.latency_ms,
            "running_duration_ms": max(0, int(running_duration_ms or 0)),
            "last_active_stage": last_event.stage if last_event else "",
            "last_active_status": last_event.status if last_event else "",
            "events": [event.as_dict() for event in self.events],
        }


class VoiceRunRecorder:
    """Record recent assistant run timelines for diagnostics."""

    def __init__(self, *, limit: int = RUN_LIMIT) -> None:
        self._limit = limit
        self._runs: dict[str, VoiceRun] = {}
        self._order: list[str] = []

    def start(self, *, conversation_id: str | None, user_text: str) -> str:
        """Start a run and return its id."""
        run_id = ulid.ulid_now()
        run = VoiceRun(
            id=run_id,
            created_at=time.time(),
            started_monotonic=time.monotonic(),
            conversation_id=conversation_id or "",
            user_text=user_text,
        )
        self._runs[run_id] = run
        self._order.insert(0, run_id)
        self.mark(run_id, "received")
        self._prune()
        return run_id

    def mark(
        self,
        run_id: str,
        stage: str,
        *,
        status: str = "ok",
        attrs: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Append a pipeline event to a run."""
        run = self._runs.get(run_id)
        if run is None:
            return None
        previous = run.events[-1] if run.events else None
        event = VoiceRunEvent(
            event_id=ulid.ulid_now(),
            turn_id=run_id,
            sequence=len(run.events),
            stage=stage,
            t_ms=max(0, round((time.monotonic() - run.started_monotonic) * 1000)),
            occurred_at=datetime.now(UTC).isoformat(),
            caused_by=previous.event_id if previous else "",
            status=status,
            attrs=dict(attrs or {}),
        )
        run.events.append(event)
        return event.as_dict()

    def finish(
        self,
        run_id: str,
        *,
        status: str,
        route: str = "",
        provider: str = "",
        latency_ms: int = 0,
    ) -> list[dict[str, Any]]:
        """Finish a run and return its event timeline."""
        run = self._runs.get(run_id)
        if run is None:
            return []
        run.status = status
        run.route = route
        run.provider = provider
        run.latency_ms = latency_ms
        self.mark(
            run_id,
            "complete",
            status=status,
            attrs={"route": route, "provider": provider, "latency_ms": latency_ms},
        )
        return [event.as_dict() for event in run.events]

    def timeline(self, run_id: str) -> list[dict[str, Any]]:
        """Return the current run timeline."""
        self._expire_stale_runs()
        run = self._runs.get(run_id)
        if run is None:
            return []
        return [event.as_dict() for event in run.events]

    def snapshot(self) -> list[dict[str, Any]]:
        """Return recent runs newest first."""
        self._expire_stale_runs()
        return [
            self._runs[run_id].as_dict()
            for run_id in self._order
            if run_id in self._runs
        ]

    def _prune(self) -> None:
        extra = self._order[self._limit :]
        self._order = self._order[: self._limit]
        for run_id in extra:
            self._runs.pop(run_id, None)

    def _expire_stale_runs(self) -> None:
        now = time.time()
        for run in self._runs.values():
            if run.status != "running":
                continue
            elapsed_ms = max(0, round((now - run.created_at) * 1000))
            if elapsed_ms < STALE_RUNNING_MS:
                continue
            run.status = "stale"
            run.latency_ms = elapsed_ms
            run.events.append(
                VoiceRunEvent(
                    event_id=ulid.ulid_now(),
                    turn_id=run.id,
                    sequence=len(run.events),
                    stage="stale_expired",
                    t_ms=elapsed_ms,
                    occurred_at=datetime.now(UTC).isoformat(),
                    caused_by=run.events[-1].event_id if run.events else "",
                    status="stale",
                    attrs={
                        "max_running_ms": STALE_RUNNING_MS,
                        "reason": "run_exceeded_observable_voice_budget",
                    },
                )
            )
