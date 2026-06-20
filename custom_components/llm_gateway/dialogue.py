"""Dialogue-state helpers for follow-up turns and user-visible interaction state."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from .capabilities import RouteDecision

DialogueRelation = Literal[
    "new_task",
    "slot_fill",
    "permission",
    "cancellation",
    "unresolved",
]
InteractionState = Literal[
    "captured",
    "classifying",
    "local_executing",
    "searching",
    "awaiting_user_info",
    "slot_filled",
    "confirming_high_risk",
    "blocked",
    "capability_missing",
    "done",
    "failed",
    "cancelled",
]

_CANCEL_RE = re.compile(r"^(取消|不用了|算了|别查了|不要了|停|停止)[。！？!,.，\s]*$")
_SEARCH_PERMISSION_RE = re.compile(
    r"^(搜索一下|搜一下|查一下|可以|好的|行|联网查)[。！？!,.，\s]*$"
)
_LOCATION_ONLY_RE = re.compile(r"^[\u4e00-\u9fffA-Za-z0-9·\-\s]{2,18}[。！？!,.，\s]*$")
_SHORT_LOCATION_MAX_LEN = 8
_LOCATION_MARKERS = (
    "上海",
    "静安",
    "浦东",
    "黄浦",
    "徐汇",
    "长宁",
    "北京",
    "广州",
    "深圳",
    "杭州",
)


@dataclass(slots=True)
class PendingTask:
    """A short-lived task waiting for user-supplied slots."""

    id: str
    task_type: str
    required_user_slots: tuple[str, ...]
    filled_slots: dict[str, Any] = field(default_factory=dict)
    allowed_tools: tuple[str, ...] = ()
    user_visible_prompt: str = ""
    expires_after_turns: int = 2
    turns_seen: int = 0
    route_decision: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "task_type": self.task_type,
            "required_user_slots": list(self.required_user_slots),
            "filled_slots": dict(self.filled_slots),
            "allowed_tools": list(self.allowed_tools),
            "user_visible_prompt": self.user_visible_prompt,
            "expires_after_turns": self.expires_after_turns,
            "turns_seen": self.turns_seen,
            "route_decision": dict(self.route_decision),
        }


@dataclass(frozen=True, slots=True)
class PendingResolution:
    """Result of resolving a user utterance against a pending task."""

    relation: DialogueRelation
    pending_task: PendingTask | None = None
    slot_updates: dict[str, Any] = field(default_factory=dict)
    effective_text: str = ""
    prompt: str = ""
    interaction_state: InteractionState = "classifying"
    expired: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "dialogue_relation": self.relation,
            "target_pending_task_id": self.pending_task.id if self.pending_task else "",
            "slot_updates": dict(self.slot_updates),
            "effective_text": self.effective_text,
            "prompt": self.prompt,
            "interaction_state": self.interaction_state,
            "expired": self.expired,
            "pending_task": self.pending_task.as_dict() if self.pending_task else {},
        }


def pending_task_from_route(turn_id: str, route: RouteDecision) -> PendingTask | None:
    """Create a pending task for routes that need user-supplied slots."""
    if "location_hint" not in route.missing_requirements:
        return None
    return PendingTask(
        id=f"{turn_id}:weather_location",
        task_type=route.task_type,
        required_user_slots=("location_hint",),
        allowed_tools=route.allowed_tools,
        user_visible_prompt=route.user_visible_prompt,
        route_decision=route.as_dict(),
    )


def resolve_pending_task(text: str, pending: PendingTask | None) -> PendingResolution:
    """Resolve a short follow-up utterance before normal routing."""
    value = str(text or "").strip()
    if pending is None:
        return PendingResolution("new_task")
    pending.turns_seen += 1
    if pending.turns_seen > pending.expires_after_turns:
        return PendingResolution("unresolved", pending_task=pending, expired=True)
    if _CANCEL_RE.match(value):
        return PendingResolution(
            "cancellation",
            pending_task=pending,
            prompt="好的，已取消。",
            interaction_state="cancelled",
        )
    if _SEARCH_PERMISSION_RE.match(value):
        return PendingResolution(
            "permission",
            pending_task=pending,
            slot_updates={"search_allowed": True},
            prompt=pending.user_visible_prompt or "可以搜索。你想查哪个地方？",
            interaction_state="awaiting_user_info",
        )
    if "location_hint" in pending.required_user_slots and _looks_like_location(value):
        location = value.strip(" 。！？!,.，")
        updates = {"location_hint": location}
        pending.filled_slots.update(updates)
        return PendingResolution(
            "slot_fill",
            pending_task=pending,
            slot_updates=updates,
            effective_text=_weather_effective_text(pending, location),
            interaction_state="slot_filled",
        )
    return PendingResolution(
        "unresolved",
        pending_task=pending,
        prompt=pending.user_visible_prompt,
        interaction_state="awaiting_user_info",
    )


def interaction_state_for_policy_block(
    reason: str,
    metadata: dict[str, Any],
) -> InteractionState:
    """Map policy reasons to user-visible interaction states."""
    blocked_reason = str(metadata.get("blocked_reason") or reason)
    if blocked_reason == "confirmation_required":
        return "confirming_high_risk"
    if blocked_reason in {"missing_user_slot", "missing_requirements"}:
        return "awaiting_user_info"
    if blocked_reason in {"search_forbidden", "tool_disabled", "provider_missing"}:
        return "capability_missing"
    return "blocked"


def _looks_like_location(value: str) -> bool:
    if not _LOCATION_ONLY_RE.match(value):
        return False
    return (
        any(marker in value for marker in _LOCATION_MARKERS)
        or len(value.strip()) <= _SHORT_LOCATION_MAX_LEN
    )


def _weather_effective_text(pending: PendingTask, location: str) -> str:
    route = pending.route_decision
    horizon = str(route.get("time_horizon") or "")
    horizon_text = {"tomorrow": "明天", "future": "未来", "today": "今天"}.get(
        horizon,
        "",
    )
    return f"{location}{horizon_text}的天气怎么样？"
