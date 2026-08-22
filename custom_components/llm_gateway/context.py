"""Bounded, reconstructable context composition for model-backed voice turns."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from .memory import VoiceMemory

DEFAULT_CONTEXT_BUDGET_CHARS = 6000


@dataclass(frozen=True, slots=True)
class TurnContextRequest:
    """Facts contributors may use to decide whether context is relevant."""

    conversation_id: str | None
    route_kind: str
    task_type: str
    budget_chars: int = DEFAULT_CONTEXT_BUDGET_CHARS


@dataclass(frozen=True, slots=True)
class ContextSlice:
    """One provenance-bearing context fragment."""

    id: str
    source: str
    content: str
    priority: int
    evidence_ids: tuple[str, ...] = ()
    preexisting: bool = False


class ContextContributor(Protocol):
    """Adapter that contributes at most one bounded context slice."""

    async def async_get_context(
        self, request: TurnContextRequest
    ) -> ContextSlice | None:
        """Return relevant context without mutating the chat log."""


@dataclass(frozen=True, slots=True)
class ContextComposition:
    """Selected context plus enough evidence to explain its assembly."""

    slices: tuple[ContextSlice, ...]
    skipped: tuple[str, ...] = ()
    truncated: tuple[str, ...] = ()

    @property
    def injected(self) -> tuple[ContextSlice, ...]:
        return tuple(item for item in self.slices if not item.preexisting)

    def trace_attrs(self, *, include_content: bool = False) -> dict[str, object]:
        return {
            "budget_chars": sum(len(item.content) for item in self.injected),
            "slices": [
                {
                    "id": item.id,
                    "source": item.source,
                    "priority": item.priority,
                    "chars": len(item.content),
                    "evidence_ids": list(item.evidence_ids),
                    "preexisting": item.preexisting,
                    **({"content": item.content} if include_content else {}),
                }
                for item in self.slices
            ],
            "skipped": list(self.skipped),
            "truncated": list(self.truncated),
        }


class ExistingContextContributor:
    """Expose HA-provided model context without injecting a second copy."""

    def __init__(self, system_messages: list[str]) -> None:
        self._content = "\n\n".join(item for item in system_messages if item.strip())

    async def async_get_context(
        self, _request: TurnContextRequest
    ) -> ContextSlice | None:
        if not self._content:
            return None
        return ContextSlice(
            id="ha_llm_data",
            source="home_assistant",
            content=self._content,
            priority=1000,
            evidence_ids=("chat_log:system",),
            preexisting=True,
        )


class StaticContextContributor:
    """Provide one fixed, high-priority voice contract."""

    def __init__(self, slice_id: str, content: str, *, priority: int = 100) -> None:
        self._slice = ContextSlice(
            id=slice_id,
            source="llm_gateway",
            content=content,
            priority=priority,
            evidence_ids=(f"static:{slice_id}",),
        )

    async def async_get_context(
        self, _request: TurnContextRequest
    ) -> ContextSlice:
        return self._slice


class MemoryContextContributor:
    """Project bounded local session memory into relevant model turns."""

    def __init__(self, memory: VoiceMemory) -> None:
        self._memory = memory

    async def async_get_context(
        self, request: TurnContextRequest
    ) -> ContextSlice | None:
        content = self._memory.build_context(request.conversation_id)
        if not content:
            return None
        return ContextSlice(
            id="session_memory",
            source="voice_memory",
            content=content,
            priority=50,
            evidence_ids=(f"session:{request.conversation_id or 'entry'}",),
        )


class TurnContextComposer:
    """Select, deduplicate and bound model-visible context in fixed order."""

    async def async_compose(
        self,
        request: TurnContextRequest,
        contributors: tuple[ContextContributor, ...],
    ) -> ContextComposition:
        candidates = [
            item
            for contributor in contributors
            if (item := await contributor.async_get_context(request)) is not None
        ]
        candidates.sort(key=lambda item: item.priority, reverse=True)
        selected: list[ContextSlice] = []
        skipped: list[str] = []
        truncated: list[str] = []
        seen: set[str] = set()
        remaining = max(0, request.budget_chars)
        for item in candidates:
            normalized = item.content.strip()
            if not normalized or normalized in seen:
                skipped.append(item.id)
                continue
            seen.add(normalized)
            if item.preexisting:
                selected.append(item)
                continue
            if remaining <= 0:
                skipped.append(item.id)
                continue
            content = item.content[:remaining]
            if len(content) < len(item.content):
                truncated.append(item.id)
            selected.append(
                ContextSlice(
                    id=item.id,
                    source=item.source,
                    content=content,
                    priority=item.priority,
                    evidence_ids=item.evidence_ids,
                    preexisting=item.preexisting,
                )
            )
            remaining -= len(content)
        return ContextComposition(
            slices=tuple(selected),
            skipped=tuple(skipped),
            truncated=tuple(truncated),
        )
