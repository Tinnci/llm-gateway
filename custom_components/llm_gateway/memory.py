"""Short session memory and durable structured memory for voice turns."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.storage import Store

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

SESSION_TTL = timedelta(minutes=10)
RAW_TURN_LIMIT = 6
SUMMARY_TURN_THRESHOLD = 8


@dataclass(slots=True)
class MemoryTurn:
    """One recent conversation turn."""

    user: str
    assistant: str
    created_at: str


@dataclass(slots=True)
class SessionMemory:
    """Memory for one conversation id."""

    turns: list[MemoryTurn] = field(default_factory=list)
    summary: str = ""
    updated_at: str = ""


class VoiceMemory:
    """Persistent structured memory plus short conversation sessions."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, 1, f"{DOMAIN}.{entry_id}.memory"
        )
        self._facts: list[str] = []
        self._sessions: dict[str, SessionMemory] = {}

    async def async_load(self) -> None:
        """Load persistent memory from Home Assistant storage."""
        data = await self._store.async_load() or {}
        self._facts = [str(item) for item in data.get("facts", []) if item]
        self._sessions = {
            key: _session_from_dict(value)
            for key, value in (data.get("sessions") or {}).items()
            if isinstance(value, dict)
        }
        self._prune_sessions()

    async def async_record_turn(
        self, conversation_id: str | None, user_text: str, assistant_text: str
    ) -> None:
        """Record a completed turn."""
        if not conversation_id:
            return
        now = datetime.now(UTC).isoformat()
        session = self._sessions.setdefault(conversation_id, SessionMemory())
        session.turns.append(MemoryTurn(user_text, assistant_text, now))
        session.turns = session.turns[-RAW_TURN_LIMIT:]
        session.updated_at = now
        if len(session.turns) >= SUMMARY_TURN_THRESHOLD and not session.summary:
            session.summary = "；".join(turn.user for turn in session.turns[-4:])
        self._prune_sessions()
        await self._store.async_save(self._as_dict())

    def build_context(self, conversation_id: str | None) -> str:
        """Build a compact memory context system message."""
        parts: list[str] = []
        if self._facts:
            facts = "\n".join(f"- {fact}" for fact in self._facts[:12])
            parts.append(f"长期记忆：\n{facts}")

        if conversation_id and (session := self._sessions.get(conversation_id)):
            if session.summary:
                parts.append(f"本轮会话摘要：{session.summary}")
            if session.turns:
                recent = "\n".join(
                    f"用户：{turn.user}\n助手：{turn.assistant}"
                    for turn in session.turns[-RAW_TURN_LIMIT:]
                )
                parts.append("最近上下文：\n" + recent)

        if not parts:
            return ""

        return (
            "以下是助手可用的本地记忆。只在相关时使用；不要向用户朗读内部标题、"
            "entity_id 或存储细节。\n\n" + "\n\n".join(parts)
        )

    def snapshot(self) -> dict[str, Any]:
        """Return an admin/debug snapshot for the Voice Harness panel."""
        return {
            "facts": list(self._facts),
            "sessions": [
                {
                    "conversation_id": key,
                    "summary": session.summary,
                    "updated_at": session.updated_at,
                    "turns": [
                        {
                            "user": turn.user,
                            "assistant": turn.assistant,
                            "created_at": turn.created_at,
                        }
                        for turn in session.turns
                    ],
                }
                for key, session in sorted(self._sessions.items())
            ],
        }

    def _as_dict(self) -> dict[str, Any]:
        return {
            "facts": self._facts,
            "sessions": {
                key: _session_to_dict(value) for key, value in self._sessions.items()
            },
        }

    def _prune_sessions(self) -> None:
        now = datetime.now(UTC)
        self._sessions = {
            key: session
            for key, session in self._sessions.items()
            if _parse_time(session.updated_at, now) + SESSION_TTL >= now
        }


def _session_from_dict(data: dict[str, Any]) -> SessionMemory:
    return SessionMemory(
        turns=[
            MemoryTurn(
                user=str(turn.get("user", "")),
                assistant=str(turn.get("assistant", "")),
                created_at=str(turn.get("created_at", "")),
            )
            for turn in data.get("turns", [])
            if isinstance(turn, dict)
        ][-RAW_TURN_LIMIT:],
        summary=str(data.get("summary", "")),
        updated_at=str(data.get("updated_at", "")),
    )


def _session_to_dict(session: SessionMemory) -> dict[str, Any]:
    return {
        "turns": [
            {
                "user": turn.user,
                "assistant": turn.assistant,
                "created_at": turn.created_at,
            }
            for turn in session.turns
        ],
        "summary": session.summary,
        "updated_at": session.updated_at,
    }


def _parse_time(value: str, default: datetime) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return default
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed
