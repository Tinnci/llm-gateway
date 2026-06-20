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
    "confirmation",
    "correction",
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
_CONFIRM_RE = re.compile(r"^(对|是|是的|对的|没错|嗯|确认|就是它)[。！？!,.，\s]*$")
_LOCATION_ONLY_RE = re.compile(r"^[\u4e00-\u9fffA-Za-z0-9·\-\s]{2,18}[。！？!,.，\s]*$")
_ORDINAL_RE = re.compile(r"(?:第)?([一二三四五六七八九十\d])个?")
_FOLLOWUP_NORMALIZE_RE = re.compile(r"[\s《》「」『』“”\"'`·.。,:：，、_\-—!?！？]+")
_SHORT_LOCATION_MAX_LEN = 8
MIN_FOLLOWUP_PART_LEN = 2
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


@dataclass(slots=True)
class DialogueFrame:
    """A transactional frame waiting for referents, confirmation, or correction."""

    id: str
    frame_type: str
    operation: str
    status: str
    missing_referents: tuple[str, ...] = ()
    filled_referents: dict[str, Any] = field(default_factory=dict)
    last_prompt: str = ""
    allowed_tools: tuple[str, ...] = ()
    candidates: tuple[dict[str, Any], ...] = ()
    expires_after_turns: int = 2
    turns_seen: int = 0
    route_decision: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """Return trace-safe frame state."""
        return {
            "id": self.id,
            "frame_type": self.frame_type,
            "operation": self.operation,
            "status": self.status,
            "missing_referents": list(self.missing_referents),
            "filled_referents": dict(self.filled_referents),
            "last_prompt": self.last_prompt,
            "allowed_tools": list(self.allowed_tools),
            "candidates": [dict(candidate) for candidate in self.candidates],
            "expires_after_turns": self.expires_after_turns,
            "turns_seen": self.turns_seen,
            "route_decision": dict(self.route_decision),
        }


@dataclass(slots=True)
class DialogueFrameStack:
    """Short-lived transactional frame stack for follow-up turns."""

    active_frames: list[DialogueFrame] = field(default_factory=list)

    def push(self, frame: DialogueFrame) -> None:
        """Push one active frame, replacing stale frames of the same type."""
        self.active_frames = [
            item
            for item in self.active_frames
            if item.status in {"awaiting_referent", "awaiting_confirmation"}
            and item.frame_type != frame.frame_type
        ]
        self.active_frames.append(frame)

    def active_frame(self) -> DialogueFrame | None:
        """Return the newest frame still accepting a follow-up."""
        for frame in reversed(self.active_frames):
            if frame.status in {"awaiting_referent", "awaiting_confirmation"}:
                return frame
        return None

    def complete(self, frame: DialogueFrame) -> None:
        """Mark a frame completed and remove it from active matching."""
        frame.status = "completed"

    def suspend(self, frame: DialogueFrame) -> None:
        """Suspend a frame when a high-confidence unrelated new task arrives."""
        frame.status = "suspended"

    def expire(self, frame: DialogueFrame) -> None:
        """Expire a stale frame."""
        frame.status = "expired"

    def cancel(self, frame: DialogueFrame) -> None:
        """Cancel a frame by user request."""
        frame.status = "cancelled"

    def as_dict(self) -> dict[str, Any]:
        """Return trace-safe stack state."""
        return {
            "active_frames": [
                frame.as_dict()
                for frame in self.active_frames
                if frame.status in {"awaiting_referent", "awaiting_confirmation"}
            ],
            "frames": [frame.as_dict() for frame in self.active_frames],
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


@dataclass(frozen=True, slots=True)
class DialogueTransaction:
    """Resolved relationship between the new utterance and the frame stack."""

    relation: DialogueRelation
    target_frame: DialogueFrame | None = None
    suspended_frame: DialogueFrame | None = None
    slot_updates: dict[str, Any] = field(default_factory=dict)
    effective_text: str = ""
    prompt: str = ""
    interaction_state: InteractionState = "classifying"
    expired: bool = False

    def as_dict(self) -> dict[str, Any]:
        """Return trace-safe transaction state."""
        return {
            "dialogue_relation": self.relation,
            "target_frame_id": self.target_frame.id if self.target_frame else "",
            "suspended_frame_id": (
                self.suspended_frame.id if self.suspended_frame else ""
            ),
            "slot_updates": dict(self.slot_updates),
            "effective_text": self.effective_text,
            "prompt": self.prompt,
            "interaction_state": self.interaction_state,
            "expired": self.expired,
            "target_frame": self.target_frame.as_dict() if self.target_frame else {},
            "suspended_frame": (
                self.suspended_frame.as_dict() if self.suspended_frame else {}
            ),
        }


def dialogue_frame_from_route(
    turn_id: str,
    route: RouteDecision,
) -> DialogueFrame | None:
    """Create a transactional dialogue frame for routes needing referents."""
    missing = tuple(str(item) for item in route.missing_requirements)
    if "location_hint" not in missing:
        return None
    return DialogueFrame(
        id=f"{turn_id}:weather_location",
        frame_type="weather_forecast",
        operation="forecast",
        status="awaiting_referent",
        missing_referents=("location",),
        allowed_tools=route.allowed_tools,
        last_prompt=route.user_visible_prompt,
        route_decision=route.as_dict(),
    )


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


def resolve_dialogue_transaction(  # noqa: PLR0911 - explicit transaction states aid audit.
    text: str,
    stack: DialogueFrameStack,
) -> DialogueTransaction:
    """Resolve a new utterance against the active frame stack.

    This function classifies the relationship only.  It does not emit user-visible
    UI.  A high-confidence unrelated task suspends the active frame so stale
    prompts do not leak into the new turn.
    """
    value = str(text or "").strip()
    frame = stack.active_frame()
    if frame is None:
        return DialogueTransaction("new_task")

    frame.turns_seen += 1
    if frame.turns_seen > frame.expires_after_turns:
        stack.expire(frame)
        return DialogueTransaction("unresolved", target_frame=frame, expired=True)

    if _CANCEL_RE.match(value):
        stack.cancel(frame)
        return DialogueTransaction(
            "cancellation",
            target_frame=frame,
            prompt="好的，已取消。",
            interaction_state="cancelled",
        )

    if _SEARCH_PERMISSION_RE.match(value):
        return DialogueTransaction(
            "permission",
            target_frame=frame,
            slot_updates={"search_allowed": True},
            prompt=frame.last_prompt or "可以搜索。你想查哪个地方？",
            interaction_state="awaiting_user_info",
        )

    if (
        frame.frame_type == "home_control"
        and "target_device" in frame.missing_referents
        and _CONFIRM_RE.match(value)
    ):
        candidate = frame.candidates[0] if frame.candidates else {}
        if candidate:
            return _commit_device_candidate(stack, frame, candidate)

    if _looks_like_new_task(value):
        stack.suspend(frame)
        return DialogueTransaction(
            "new_task",
            suspended_frame=frame,
            interaction_state="classifying",
        )

    if "location" in frame.missing_referents and _looks_like_location(value):
        location = value.strip(" 。！？!,.，")
        updates = {"location_hint": location}
        frame.filled_referents.update(updates)
        stack.complete(frame)
        return DialogueTransaction(
            "slot_fill",
            target_frame=frame,
            slot_updates=updates,
            effective_text=_weather_effective_text_from_route(
                frame.route_decision,
                location,
            ),
            interaction_state="slot_filled",
        )

    if (
        frame.frame_type == "home_control"
        and "target_device" in frame.missing_referents
    ):
        candidate = _select_device_candidate(value, frame.candidates)
        if candidate:
            return _commit_device_candidate(stack, frame, candidate)

    return DialogueTransaction(
        "unresolved",
        target_frame=frame,
        prompt=frame.last_prompt,
        interaction_state="awaiting_user_info",
    )


def resolve_pending_task(text: str, pending: PendingTask | None) -> PendingResolution:
    """Resolve a short follow-up utterance before normal routing."""
    if pending is None:
        return PendingResolution("new_task")
    stack = DialogueFrameStack(
        [
            DialogueFrame(
                id=pending.id,
                frame_type="weather_forecast",
                operation="forecast",
                status="awaiting_referent",
                missing_referents=tuple(
                    "location"
                    if item == "location_hint"
                    else str(item).removesuffix("_hint")
                    for item in pending.required_user_slots
                ),
                filled_referents=dict(pending.filled_slots),
                last_prompt=pending.user_visible_prompt,
                allowed_tools=pending.allowed_tools,
                expires_after_turns=pending.expires_after_turns,
                turns_seen=pending.turns_seen,
                route_decision=dict(pending.route_decision),
            )
        ]
    )
    transaction = resolve_dialogue_transaction(text, stack)
    if transaction.target_frame:
        pending.turns_seen = transaction.target_frame.turns_seen
        pending.filled_slots.update(transaction.slot_updates)
    return PendingResolution(
        transaction.relation,
        pending_task=pending if transaction.relation != "new_task" else None,
        slot_updates=transaction.slot_updates,
        effective_text=transaction.effective_text,
        prompt=transaction.prompt,
        interaction_state=transaction.interaction_state,
        expired=transaction.expired,
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


def _looks_like_new_task(value: str) -> bool:
    """Return true for utterances that should not be bound to an active frame."""
    normalized = value.strip().lower()
    if not normalized:
        return False
    if re.search(
        r"\b("
        r"who\s+(?:is|was)|"
        r"do\s+you\s+know|"
        r"can\s+you|"
        r"tell\s+me|"
        r"what\s+(?:is|are|did)|"
        r"turn\s+(?:on|off)|"
        r"open|close"
        r")\b",
        normalized,
    ):
        return True
    return bool(
        re.search(
            r"(打开|关闭|查询|查一下|搜索|介绍|告诉我|谁|什么|天气|明天|后天|"
            r"音量|播放|暂停|停止播放|设置|调到)",
            value,
        )
    )


def _select_device_candidate(
    value: str,
    candidates: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    """Resolve a short target-device follow-up against frame candidates."""
    if not candidates:
        return {}
    normalized = _normalize_followup(value)
    if not normalized:
        return {}
    if (index := _candidate_index(value)) and 0 <= index - 1 < len(candidates):
        return candidates[index - 1]
    for candidate in candidates:
        name = str(candidate.get("name") or "")
        entity_id = str(candidate.get("id") or "")
        candidate_text = _normalize_followup(f"{name} {entity_id}")
        if normalized and (
            normalized in candidate_text
            or any(
                part and part in candidate_text for part in _followup_parts(normalized)
            )
        ):
            return candidate
    return {}


def _commit_device_candidate(
    stack: DialogueFrameStack,
    frame: DialogueFrame,
    candidate: dict[str, Any],
) -> DialogueTransaction:
    """Commit one selected target-device candidate into a follow-up turn."""
    name = str(candidate.get("name") or candidate.get("id") or "")
    frame.filled_referents["target_device"] = dict(candidate)
    stack.complete(frame)
    return DialogueTransaction(
        "slot_fill",
        target_frame=frame,
        slot_updates={"target_device": dict(candidate)},
        effective_text=_home_control_effective_text(frame.operation, name),
        interaction_state="slot_filled",
    )


def _candidate_index(value: str) -> int:
    if match := _ORDINAL_RE.search(value):
        token = match.group(1)
        if token.isdigit():
            return int(token)
        return {
            "一": 1,
            "二": 2,
            "两": 2,
            "三": 3,
            "四": 4,
            "五": 5,
            "六": 6,
            "七": 7,
            "八": 8,
            "九": 9,
            "十": 10,
        }.get(token, 0)
    return 0


def _normalize_followup(value: str) -> str:
    normalized = _FOLLOWUP_NORMALIZE_RE.sub("", str(value or "")).lower()
    for word in ("那个", "这个", "的", "一下", "就", "吧"):
        normalized = normalized.replace(word, "")
    return normalized


def _followup_parts(normalized: str) -> tuple[str, ...]:
    return tuple(
        part
        for part in re.split(
            r"(灯|灯泡|球泡|挂灯|宜家|米家|麦希瑟|yeelight)", normalized
        )
        if len(part) >= MIN_FOLLOWUP_PART_LEN
    )


def _home_control_effective_text(operation: str, target_name: str) -> str:
    verb = {
        "turn_on": "打开",
        "turn_off": "关闭",
        "brightness_up": "调亮",
        "brightness_down": "调暗",
        "volume_up": "调高音量",
        "volume_down": "调低音量",
        "volume_set": "调整音量",
        "volume_mute": "静音",
    }.get(operation, "操作")
    return f"{verb}已确认的{target_name}"


def _weather_effective_text(pending: PendingTask, location: str) -> str:
    return _weather_effective_text_from_route(pending.route_decision, location)


def _weather_effective_text_from_route(route: dict[str, Any], location: str) -> str:
    horizon = str(route.get("time_horizon") or "")
    horizon_text = {"tomorrow": "明天", "future": "未来", "today": "今天"}.get(
        horizon,
        "",
    )
    return f"{location}{horizon_text}的天气怎么样？"
