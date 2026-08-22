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
SUMMARY_ITEM_LIMIT = 8
FACT_LIMIT = 64
FACT_CONTEXT_BUDGET_CHARS = 1600
UNSTABLE_FAILURE_MARKERS = (
    "没有权限",
    "无法查看",
    "没有实时天气信息",
    "没有 PM2.5 数据",
    "暂时没有本地天气数据",
    "暂时没有本地状态数据",
    "设备操作没有完成",
    "模型服务暂时没有响应",
)


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


@dataclass(frozen=True, slots=True)
class VoiceFact:
    """One bounded fact with provenance and lifecycle metadata."""

    key: str
    value: str
    scope: str
    evidence_turn_id: str
    confidence: float
    created_at: str
    expires_at: str = ""
    supersedes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "scope": self.scope,
            "evidence_turn_id": self.evidence_turn_id,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "supersedes": self.supersedes,
        }


@dataclass(frozen=True, slots=True)
class FactWrite:
    """Explicit request to create or supersede one structured fact."""

    key: str
    value: str
    scope: str
    evidence_turn_id: str
    confidence: float = 1.0
    expires_at: str = ""


class VoiceMemory:
    """Persistent structured memory plus short conversation sessions."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, 1, f"{DOMAIN}.{entry_id}.memory"
        )
        self._facts: list[VoiceFact] = []
        self._sessions: dict[str, SessionMemory] = {}
        self._default_session_id = entry_id

    async def async_load(self) -> None:
        """Load persistent memory from Home Assistant storage."""
        data = await self._store.async_load() or {}
        self._facts = [
            fact
            for index, item in enumerate(data.get("facts", []))
            if (fact := _fact_from_data(item, index)) is not None
        ][-FACT_LIMIT:]
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
        session_id = conversation_id or self._default_session_id
        now = datetime.now(UTC).isoformat()
        session = self._sessions.setdefault(session_id, SessionMemory())
        session.turns.append(MemoryTurn(user_text, assistant_text, now))
        session.updated_at = now
        if len(session.turns) >= SUMMARY_TURN_THRESHOLD:
            evicted = session.turns[:-RAW_TURN_LIMIT]
            session.summary = _merge_summary(session.summary, evicted)
            session.turns = session.turns[-RAW_TURN_LIMIT:]
        self._prune_sessions()
        await self._store.async_save(self._as_dict())

    async def async_upsert_fact(self, write: FactWrite) -> VoiceFact:
        """Persist one explicit fact, replacing the same key within its scope."""
        normalized_key = str(write.key or "").strip()[:80]
        normalized_value = str(write.value or "").strip()[:500]
        normalized_scope = str(write.scope or "global").strip()[:120] or "global"
        evidence = str(write.evidence_turn_id or "").strip()[:120]
        if not normalized_key or not normalized_value or not evidence:
            raise ValueError("fact key, value and evidence_turn_id are required")
        confidence = min(1.0, max(0.0, float(write.confidence)))
        previous = next(
            (
                item
                for item in reversed(self._facts)
                if item.key == normalized_key and item.scope == normalized_scope
            ),
            None,
        )
        fact = VoiceFact(
            key=normalized_key,
            value=normalized_value,
            scope=normalized_scope,
            evidence_turn_id=evidence,
            confidence=confidence,
            created_at=datetime.now(UTC).isoformat(),
            expires_at=str(write.expires_at or ""),
            supersedes=previous.evidence_turn_id if previous else "",
        )
        self._facts = [
            item
            for item in self._facts
            if not (item.key == fact.key and item.scope == fact.scope)
        ]
        self._facts.append(fact)
        self._facts = self._facts[-FACT_LIMIT:]
        await self._store.async_save(self._as_dict())
        return fact

    def relevant_facts(
        self,
        *,
        task_type: str = "",
        area_id: str = "",
        budget_chars: int = FACT_CONTEXT_BUDGET_CHARS,
    ) -> tuple[VoiceFact, ...]:
        """Return active facts relevant to one intent/area within a text budget."""
        selected: list[VoiceFact] = []
        remaining = max(0, budget_chars)
        now = datetime.now(UTC)
        for fact in reversed(self._facts):
            if not _fact_active(fact, now) or not _fact_relevant(
                fact, task_type=task_type, area_id=area_id
            ):
                continue
            rendered = f"{fact.key}={fact.value}"
            if len(rendered) > remaining:
                continue
            selected.append(fact)
            remaining -= len(rendered)
        return tuple(reversed(selected))

    def build_context(
        self,
        conversation_id: str | None,
        *,
        task_type: str = "",
        area_id: str = "",
    ) -> str:
        """Build a compact memory context system message."""
        parts: list[str] = []
        relevant_facts = self.relevant_facts(task_type=task_type, area_id=area_id)
        if relevant_facts:
            facts = "\n".join(
                f"- {fact.key}: {fact.value} (evidence={fact.evidence_turn_id})"
                for fact in relevant_facts
            )
            parts.append(f"长期记忆：\n{facts}")

        session_id = conversation_id or self._default_session_id
        if session := self._sessions.get(session_id):
            if session.summary:
                parts.append(f"本轮会话摘要：{session.summary}")
            if session.turns:
                recent = "\n".join(
                    _turn_context_line(turn) for turn in session.turns[-RAW_TURN_LIMIT:]
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
            "facts": [item.as_dict() for item in self._facts],
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
            "facts": [item.as_dict() for item in self._facts],
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


def _fact_from_data(data: object, index: int) -> VoiceFact | None:
    if isinstance(data, str) and data.strip():
        return VoiceFact(
            key=f"legacy_{index}",
            value=data.strip()[:500],
            scope="global",
            evidence_turn_id="legacy_store",
            confidence=0.5,
            created_at="",
        )
    if not isinstance(data, dict):
        return None
    key = str(data.get("key") or "").strip()
    value = str(data.get("value") or "").strip()
    evidence = str(data.get("evidence_turn_id") or "").strip()
    if not key or not value or not evidence:
        return None
    return VoiceFact(
        key=key[:80],
        value=value[:500],
        scope=str(data.get("scope") or "global")[:120],
        evidence_turn_id=evidence[:120],
        confidence=min(1.0, max(0.0, float(data.get("confidence", 1.0)))),
        created_at=str(data.get("created_at") or ""),
        expires_at=str(data.get("expires_at") or ""),
        supersedes=str(data.get("supersedes") or "")[:120],
    )


def _fact_active(fact: VoiceFact, now: datetime) -> bool:
    if not fact.expires_at:
        return True
    return _parse_time(fact.expires_at, now - timedelta(seconds=1)) > now


def _fact_relevant(fact: VoiceFact, *, task_type: str, area_id: str) -> bool:
    scope = fact.scope.casefold()
    if scope in {"global", "legacy"}:
        return True
    if scope.startswith("intent:"):
        return scope.removeprefix("intent:") in task_type.casefold()
    if scope.startswith("area:"):
        return bool(area_id) and scope.removeprefix("area:") == area_id.casefold()
    return False


def _turn_context_line(turn: MemoryTurn) -> str:
    assistant = str(turn.assistant or "").strip()
    if _is_unstable_failure(assistant):
        assistant = "上一轮回答失败，不能当作事实引用。"
    return f"用户：{turn.user}\n助手：{assistant}"


def _merge_summary(existing: str, turns: list[MemoryTurn]) -> str:
    items = [item.strip() for item in existing.split("；") if item.strip()]
    items.extend(turn.user.strip() for turn in turns if turn.user.strip())
    return "；".join(items[-SUMMARY_ITEM_LIMIT:])


def _is_unstable_failure(text: str) -> bool:
    normalized = str(text or "")
    return any(marker in normalized for marker in UNSTABLE_FAILURE_MARKERS)


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
