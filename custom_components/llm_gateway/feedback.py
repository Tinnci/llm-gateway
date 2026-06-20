"""Deterministic voice feedback policy and live display events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from homeassistant.util import dt as dt_util
from homeassistant.util import ulid

DisplayState = Literal[
    "listening",
    "captured",
    "thinking",
    "continuing",
    "searching",
    "clarifying",
    "confirming",
    "executing",
    "blocked",
    "capability_missing",
    "done",
    "failed",
    "cancelled",
]
PrivacyLevel = Literal["public", "private", "sensitive"]
ProgressKind = Literal["none", "indeterminate", "percent"]

FEEDBACK_LIMIT = 80
QUIET_HOURS_START = 22
QUIET_HOURS_END = 7
QUIET_SUPPRESS_PRIORITY_BELOW = 70
SHORT_TEXT_LIMIT = 120

EARCON_LIBRARY: dict[str, dict[str, Any]] = {
    "wake": {
        "semantic_state": "listening",
        "duration_ms": 150,
        "priority": 90,
        "can_play_while_listening": True,
        "quiet_hours_behavior": "attenuate",
        "trace_event_name": "earcon_wake",
    },
    "captured": {
        "semantic_state": "captured",
        "duration_ms": 148,
        "priority": 40,
        "can_play_while_listening": True,
        "quiet_hours_behavior": "suppress_noncritical",
        "trace_event_name": "earcon_captured",
    },
    "thinking": {
        "semantic_state": "thinking",
        "duration_ms": 340,
        "priority": 20,
        "can_play_while_listening": False,
        "quiet_hours_behavior": "suppress_noncritical",
        "trace_event_name": "earcon_thinking",
    },
    "search": {
        "semantic_state": "searching",
        "duration_ms": 194,
        "priority": 50,
        "can_play_while_listening": False,
        "quiet_hours_behavior": "attenuate",
        "trace_event_name": "earcon_search",
    },
    "confirmation": {
        "semantic_state": "confirming",
        "duration_ms": 170,
        "priority": 90,
        "can_play_while_listening": False,
        "quiet_hours_behavior": "attenuate",
        "trace_event_name": "earcon_confirmation",
    },
    "success": {
        "semantic_state": "done",
        "duration_ms": 136,
        "priority": 50,
        "can_play_while_listening": False,
        "quiet_hours_behavior": "suppress_noncritical",
        "trace_event_name": "earcon_success",
    },
    "failure": {
        "semantic_state": "failed",
        "duration_ms": 246,
        "priority": 80,
        "can_play_while_listening": False,
        "quiet_hours_behavior": "attenuate",
        "trace_event_name": "earcon_failure",
    },
    "cancel": {
        "semantic_state": "cancelled",
        "duration_ms": 152,
        "priority": 60,
        "can_play_while_listening": True,
        "quiet_hours_behavior": "attenuate",
        "trace_event_name": "earcon_cancel",
    },
}

PIPELINE_EARCONS = {
    "wake_word_detected": "wake",
    "stt_vad_end": "captured",
    "speech_captured": "captured",
    "action_success": "success",
    "failure": "failure",
    "error": "failure",
    "no_match": "failure",
    "cancel": "cancel",
}


@dataclass(frozen=True, slots=True)
class DisplayStatusEvent:
    """Platform-neutral live display status event."""

    id: str
    turn_id: str
    state: DisplayState
    title: str
    short_text: str
    privacy_level: PrivacyLevel
    progress: ProgressKind
    action_buttons: list[str]
    expires_at: str
    source: str
    deep_link: str
    created_at: str

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable event."""
        return {
            "id": self.id,
            "turn_id": self.turn_id,
            "state": self.state,
            "title": self.title,
            "short_text": self.short_text,
            "privacy_level": self.privacy_level,
            "progress": self.progress,
            "action_buttons": list(self.action_buttons),
            "expires_at": self.expires_at,
            "source": self.source,
            "deep_link": self.deep_link,
            "created_at": self.created_at,
        }


class VoiceFeedbackStore:
    """In-memory adapter for earcon and live display feedback."""

    def __init__(self, *, limit: int = FEEDBACK_LIMIT) -> None:
        self._limit = limit
        self._earcons: list[dict[str, Any]] = []
        self._display_events: list[dict[str, Any]] = []
        self._first_response_audio: list[dict[str, Any]] = []

    def emit_earcon(
        self,
        *,
        turn_id: str,
        earcon_name: str,
        scheduled_at_ms: int,
        microphone_hot: bool = False,
        quiet_hour: int | None = None,
    ) -> dict[str, Any]:
        """Record one deterministic earcon decision."""
        spec = EARCON_LIBRARY[earcon_name]
        quiet_hours_applied = _is_quiet_hour(quiet_hour)
        suppressed_reason = ""
        volume_profile = "normal"

        if microphone_hot and not spec["can_play_while_listening"]:
            suppressed_reason = "microphone_hot"
            volume_profile = "silent"
        elif quiet_hours_applied:
            behavior = str(spec["quiet_hours_behavior"])
            if (
                behavior == "suppress_noncritical"
                and int(spec["priority"]) < QUIET_SUPPRESS_PRIORITY_BELOW
            ):
                suppressed_reason = "quiet_hours"
                volume_profile = "silent"
            elif behavior in {"attenuate", "suppress_noncritical"}:
                volume_profile = "quiet"

        event = {
            "turn_id": turn_id,
            "earcon_name": earcon_name,
            "semantic_state": spec["semantic_state"],
            "scheduled_at_ms": max(0, int(scheduled_at_ms)),
            "played_at_ms": None if suppressed_reason else max(0, int(scheduled_at_ms)),
            "duration_ms": int(spec["duration_ms"]),
            "priority": int(spec["priority"]),
            "can_play_while_listening": bool(spec["can_play_while_listening"]),
            "quiet_hours_behavior": str(spec["quiet_hours_behavior"]),
            "trace_event_name": str(spec["trace_event_name"]),
            "suppressed_reason": suppressed_reason,
            "volume_profile": volume_profile,
            "microphone_hot": microphone_hot,
            "quiet_hours_applied": quiet_hours_applied,
        }
        self._earcons.insert(0, event)
        self._earcons = self._earcons[: self._limit]
        return event

    def emit_display(  # noqa: PLR0913 - mirrors the display status schema fields.
        self,
        *,
        turn_id: str,
        state: DisplayState,
        title: str,
        short_text: str,
        privacy_level: PrivacyLevel = "private",
        progress: ProgressKind = "none",
        action_buttons: list[str] | None = None,
        ttl_s: int = 45,
    ) -> dict[str, Any]:
        """Record one live display status event."""
        now = datetime.now(UTC)
        event = DisplayStatusEvent(
            id=ulid.ulid_now(),
            turn_id=turn_id,
            state=state,
            title=title,
            short_text=_short_text(short_text),
            privacy_level=privacy_level,
            progress=progress,
            action_buttons=list(action_buttons or []),
            expires_at=(now + timedelta(seconds=ttl_s)).isoformat(),
            source="voice_gateway",
            deep_link=f"/voice-harness/runs/{turn_id}",
            created_at=now.isoformat(),
        ).as_dict()
        self._display_events.insert(0, event)
        self._display_events = self._display_events[: self._limit]
        return event

    def earcons_for_turn(self, turn_id: str) -> list[dict[str, Any]]:
        """Return earcon events for one turn in chronological order."""
        return [
            event
            for event in reversed(self._earcons)
            if event.get("turn_id") == turn_id
        ]

    def display_events_for_turn(self, turn_id: str) -> list[dict[str, Any]]:
        """Return display events for one turn in chronological order."""
        return [
            event
            for event in reversed(self._display_events)
            if event.get("turn_id") == turn_id
        ]

    def emit_first_response_audio(  # noqa: PLR0913 - mirrors trace schema fields.
        self,
        *,
        turn_id: str,
        text: str,
        scheduled_at_ms: int,
        source: str,
        phrase_key: str,
        backend: str,
        adapter: str = "",
        local_service: str = "",
        tts_entity: str = "",
        media_player_entity: str = "",
        selection_reason: str = "",
        scheduled: bool = True,
        suppressed_reason: str = "",
    ) -> dict[str, Any]:
        """Record first-response audio scheduling state."""
        event = {
            "id": ulid.ulid_now(),
            "turn_id": turn_id,
            "text": _short_text(text),
            "phrase_key": phrase_key,
            "scheduled": scheduled,
            "scheduled_at_ms": max(0, int(scheduled_at_ms)),
            "played": False,
            "played_at_ms": None,
            "source": source,
            "backend": backend,
            "adapter": adapter,
            "local_service": local_service,
            "tts_entity": tts_entity,
            "media_player_entity": media_player_entity,
            "selection_reason": selection_reason,
            "suppressed_reason": suppressed_reason,
            "target_ms": 300,
        }
        self._first_response_audio.insert(0, event)
        self._first_response_audio = self._first_response_audio[: self._limit]
        return event

    def update_first_response_audio(  # noqa: PLR0913 - mirrors trace schema fields.
        self,
        event_id: str,
        *,
        played: bool,
        played_at_ms: int | None = None,
        source: str | None = None,
        backend: str | None = None,
        adapter: str | None = None,
        local_service: str | None = None,
        tts_entity: str | None = None,
        media_player_entity: str | None = None,
        selection_reason: str | None = None,
        suppressed_reason: str = "",
    ) -> dict[str, Any] | None:
        """Update a previously scheduled first-response audio event."""
        for event in self._first_response_audio:
            if event.get("id") != event_id:
                continue
            event["played"] = played
            event["played_at_ms"] = (
                max(0, int(played_at_ms)) if played_at_ms is not None else None
            )
            if source is not None:
                event["source"] = source
            if backend is not None:
                event["backend"] = backend
            if adapter is not None:
                event["adapter"] = adapter
            if local_service is not None:
                event["local_service"] = local_service
            if tts_entity is not None:
                event["tts_entity"] = tts_entity
            if media_player_entity is not None:
                event["media_player_entity"] = media_player_entity
            if selection_reason is not None:
                event["selection_reason"] = selection_reason
            event["suppressed_reason"] = suppressed_reason
            return event
        return None

    def first_response_audio_for_turn(self, turn_id: str) -> list[dict[str, Any]]:
        """Return first-response audio events for one turn in chronological order."""
        return [
            event
            for event in reversed(self._first_response_audio)
            if event.get("turn_id") == turn_id
        ]

    def latest_display_for_turn(self, turn_id: str) -> dict[str, Any] | None:
        """Return the newest display event for one turn."""
        for event in self._display_events:
            if event.get("turn_id") == turn_id:
                return event
        return None

    def snapshot(self) -> dict[str, Any]:
        """Return feedback state for the panel live adapter."""
        return {
            "latest_display": self._display_events[0] if self._display_events else None,
            "display_events": list(self._display_events),
            "earcon_events": list(self._earcons),
            "first_response_audio": list(self._first_response_audio),
        }


class VoiceFeedbackPolicy:
    """Local policy mapping pipeline state to earcons and display status."""

    def __init__(self, store: VoiceFeedbackStore) -> None:
        self._store = store

    def pipeline_event(  # noqa: PLR0911 - explicit event mapping is easier to audit.
        self,
        *,
        turn_id: str,
        stage: str,
        t_ms: int,
        attrs: dict[str, Any] | None = None,
        status: str = "ok",
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        """Apply feedback policy to one pipeline event."""
        attrs = attrs or {}
        if stage == "first_response":
            return self._first_response(turn_id=turn_id, t_ms=t_ms, attrs=attrs)
        if stage == "pending_state_resolver":
            return self._pending_state(turn_id=turn_id, t_ms=t_ms, attrs=attrs)
        if stage == "local_route_clarify":
            return self._clarifying(turn_id, t_ms, attrs)
        if stage == "search_started":
            return self._emit_searching(turn_id, t_ms, attrs)
        if stage == "tool_policy_block":
            return self._policy_block(turn_id, t_ms, attrs)
        if stage == "search_result":
            if status == "error":
                return self._emit_failure(turn_id, t_ms, "搜索失败。")
            return None, None
        if stage == "tool_result" and status == "ok":
            name = str(attrs.get("name") or "")
            if name.startswith("Hass"):
                return self._emit_success(turn_id, t_ms, "已执行。")
        if status == "error":
            return self._emit_failure(
                turn_id,
                t_ms,
                str(attrs.get("error") or "失败。"),
            )

        earcon_name = PIPELINE_EARCONS.get(stage)
        if earcon_name:
            earcon = self._store.emit_earcon(
                turn_id=turn_id,
                earcon_name=earcon_name,
                scheduled_at_ms=t_ms,
            )
            display = self._display_for_earcon(turn_id, earcon_name, attrs)
            return earcon, display
        return None, None

    def final_status(
        self,
        *,
        turn_id: str,
        status: str,
        t_ms: int,
        short_text: str,
    ) -> dict[str, Any]:
        """Emit final display state, with failure earcon for error status."""
        latest = self._store.latest_display_for_turn(turn_id)
        if status == "error":
            if latest and latest.get("state") == "failed":
                return latest
            self._emit_failure(turn_id, t_ms, short_text or "请求失败。")
            return self._store.display_events_for_turn(turn_id)[-1]
        if latest and latest.get("state") in {
            "clarifying",
            "confirming",
            "blocked",
            "capability_missing",
            "cancelled",
        }:
            return latest
        return self._store.emit_display(
            turn_id=turn_id,
            state="done",
            title="Done",
            short_text=short_text or "完成。",
            privacy_level="private",
            ttl_s=25,
        )

    def _first_response(
        self,
        *,
        turn_id: str,
        t_ms: int,
        attrs: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        cue = str(attrs.get("cue") or "")
        text = str(attrs.get("spoken_hint") or attrs.get("reason") or "")
        if cue == "search":
            # Search feedback is only user-truthful once an allowed search tool
            # actually starts.  Keep first_response classification trace-only.
            return None, None
        if cue == "confirmation":
            return self._emit_confirmation(turn_id, t_ms, text or "这个需要确认。")
        if cue in {"thinking", "planning"}:
            delay_ms = int(float(attrs.get("processing_cue_delay_s") or 0) * 1000)
            earcon = self._store.emit_earcon(
                turn_id=turn_id,
                earcon_name="thinking",
                scheduled_at_ms=t_ms + max(0, delay_ms),
            )
            display = self._store.emit_display(
                turn_id=turn_id,
                state="thinking",
                title="Thinking",
                short_text=text or "我看一下。",
                progress="indeterminate",
                action_buttons=["cancel", "open_panel"],
            )
            return earcon, display
        return None, None

    def _pending_state(
        self,
        *,
        turn_id: str,
        t_ms: int,
        attrs: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        state = str(attrs.get("interaction_state") or "")
        text = str(attrs.get("prompt") or attrs.get("effective_text") or "")
        if state == "awaiting_user_info":
            # Pending resolution only classifies the relationship to an active
            # frame.  The user-visible clarification is emitted later by the
            # commitment/local_route_clarify stage, after the new turn is known
            # not to be an unrelated task.
            return None, None
        if state == "slot_filled":
            display = self._store.emit_display(
                turn_id=turn_id,
                state="continuing",
                title="Continuing",
                short_text=text or "继续处理。",
                progress="indeterminate",
                action_buttons=["cancel", "open_panel"],
                ttl_s=20,
            )
            return None, display
        if state == "cancelled":
            earcon = self._store.emit_earcon(
                turn_id=turn_id,
                earcon_name="cancel",
                scheduled_at_ms=t_ms,
            )
            display = self._store.emit_display(
                turn_id=turn_id,
                state="cancelled",
                title="Cancelled",
                short_text=str(attrs.get("prompt") or "已取消。"),
                action_buttons=["open_panel"],
                ttl_s=20,
            )
            return earcon, display
        return None, None

    def _clarifying(
        self,
        turn_id: str,
        _t_ms: int,
        attrs: dict[str, Any],
    ) -> tuple[None, dict[str, Any]]:
        text = str(
            attrs.get("spoken_prompt")
            or attrs.get("user_visible_prompt")
            or attrs.get("prompt")
            or "还需要补充信息。"
        )
        display = self._store.emit_display(
            turn_id=turn_id,
            state="clarifying",
            title="More information needed",
            short_text=text,
            action_buttons=["cancel", "open_panel"],
            ttl_s=45,
        )
        return None, display

    def _emit_searching(
        self,
        turn_id: str,
        t_ms: int,
        attrs: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        text = str(attrs.get("spoken_hint") or attrs.get("query") or "我查一下。")
        earcon = self._store.emit_earcon(
            turn_id=turn_id,
            earcon_name="search",
            scheduled_at_ms=t_ms,
        )
        display = self._store.emit_display(
            turn_id=turn_id,
            state="searching",
            title="Searching",
            short_text=text,
            progress="indeterminate",
            action_buttons=["cancel", "open_panel"],
        )
        return earcon, display

    def _emit_confirmation(
        self, turn_id: str, t_ms: int, short_text: str
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        earcon = self._store.emit_earcon(
            turn_id=turn_id,
            earcon_name="confirmation",
            scheduled_at_ms=t_ms,
        )
        display = self._store.emit_display(
            turn_id=turn_id,
            state="confirming",
            title="Confirm",
            short_text=short_text,
            privacy_level="sensitive",
            action_buttons=["confirm", "cancel", "open_panel"],
        )
        return earcon, display

    def _policy_block(
        self, turn_id: str, t_ms: int, attrs: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        state = str(attrs.get("interaction_state") or "")
        text = str(attrs.get("spoken_prompt") or attrs.get("prompt") or "")
        blocked_reason = str(attrs.get("blocked_reason") or attrs.get("reason") or "")
        if state == "confirming_high_risk" or blocked_reason == "confirmation_required":
            return self._emit_confirmation(turn_id, t_ms, text or "这个操作需要确认。")
        if state == "awaiting_user_info" or blocked_reason in {
            "missing_user_slot",
            "missing_requirements",
        }:
            return self._clarifying(
                turn_id,
                t_ms,
                {**attrs, "spoken_prompt": text or "还需要补充信息。"},
            )
        display = self._store.emit_display(
            turn_id=turn_id,
            state="capability_missing" if state == "capability_missing" else "blocked",
            title="Blocked",
            short_text=text or "当前不能执行这个请求。",
            action_buttons=["open_panel"],
            ttl_s=60,
        )
        return None, display

    def _emit_success(
        self, turn_id: str, t_ms: int, short_text: str
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        earcon = self._store.emit_earcon(
            turn_id=turn_id,
            earcon_name="success",
            scheduled_at_ms=t_ms,
        )
        display = self._store.emit_display(
            turn_id=turn_id,
            state="done",
            title="Done",
            short_text=short_text,
            action_buttons=["open_panel"],
            ttl_s=20,
        )
        return earcon, display

    def _emit_failure(
        self, turn_id: str, t_ms: int, short_text: str
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        earcon = self._store.emit_earcon(
            turn_id=turn_id,
            earcon_name="failure",
            scheduled_at_ms=t_ms,
        )
        display = self._store.emit_display(
            turn_id=turn_id,
            state="failed",
            title="Failed",
            short_text=short_text,
            action_buttons=["open_panel"],
            ttl_s=60,
        )
        return earcon, display

    def _display_for_earcon(
        self,
        turn_id: str,
        earcon_name: str,
        attrs: dict[str, Any],
    ) -> dict[str, Any] | None:
        if earcon_name == "wake":
            return self._store.emit_display(
                turn_id=turn_id,
                state="listening",
                title="Listening",
                short_text="正在听。",
                progress="indeterminate",
            )
        if earcon_name == "captured":
            return self._store.emit_display(
                turn_id=turn_id,
                state="captured",
                title="Captured",
                short_text=str(attrs.get("short_text") or "已听到。"),
            )
        if earcon_name == "cancel":
            return self._store.emit_display(
                turn_id=turn_id,
                state="failed",
                title="Cancelled",
                short_text="已取消。",
            )
        return None


def feedback_trace_attrs(
    earcon: dict[str, Any] | None,
    display: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return compact timeline attrs for feedback events."""
    return {
        "earcon_name": earcon.get("earcon_name") if earcon else "",
        "display_state": display.get("state") if display else "",
        "suppressed_reason": earcon.get("suppressed_reason") if earcon else "",
        "volume_profile": earcon.get("volume_profile") if earcon else "",
    }


def _is_quiet_hour(hour: int | None) -> bool:
    current = dt_util.now().hour if hour is None else hour
    return current >= QUIET_HOURS_START or current < QUIET_HOURS_END


def _short_text(value: str) -> str:
    text = str(value or "").replace("\x00", "").strip()
    return (
        text[: SHORT_TEXT_LIMIT - 3].rstrip() + "..."
        if len(text) > SHORT_TEXT_LIMIT
        else text
    )
