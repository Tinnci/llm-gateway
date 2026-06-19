"""In-memory timeline for recent voice/text assistant runs."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from homeassistant.util import ulid

RUN_LIMIT = 40


@dataclass(slots=True)
class VoiceRunEvent:
    """One timestamped pipeline event."""

    stage: str
    t_ms: int
    status: str = "ok"
    attrs: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "t_ms": self.t_ms,
            "status": self.status,
            "attrs": dict(self.attrs),
        }


@dataclass(slots=True)
class VoiceRun:
    """One observable assistant run."""

    id: str
    created_at: float
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
        event = VoiceRunEvent(
            stage=stage,
            t_ms=round((time.time() - run.created_at) * 1000),
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
        run = self._runs.get(run_id)
        if run is None:
            return []
        return [event.as_dict() for event in run.events]

    def snapshot(self) -> list[dict[str, Any]]:
        """Return recent runs newest first."""
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
