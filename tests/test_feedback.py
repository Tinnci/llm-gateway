"""Tests for deterministic earcon and live display feedback."""

from __future__ import annotations

from custom_components.llm_gateway.feedback import (
    VoiceFeedbackPolicy,
    VoiceFeedbackStore,
)


def test_feedback_policy_does_not_map_search_first_response_to_searching() -> None:
    store = VoiceFeedbackStore()
    earcon, display = VoiceFeedbackPolicy(store).pipeline_event(
        turn_id="turn-search",
        stage="first_response",
        t_ms=120,
        attrs={"cue": "search", "spoken_hint": "我查一下。"},
    )

    assert earcon is None
    assert display is None


def test_feedback_policy_maps_search_started() -> None:
    store = VoiceFeedbackStore()
    earcon, display = VoiceFeedbackPolicy(store).pipeline_event(
        turn_id="turn-search",
        stage="search_started",
        t_ms=120,
        attrs={"query": "Home Assistant 最新语音更新"},
    )

    assert earcon["earcon_name"] == "search"
    assert earcon["played_at_ms"] == 120
    assert earcon["volume_profile"] in {"normal", "quiet"}
    assert display["state"] == "searching"
    assert display["progress"] == "indeterminate"
    assert display["deep_link"] == "/voice-harness/runs/turn-search"
    assert display["action_buttons"] == ["cancel", "open_panel"]


def test_feedback_policy_maps_confirmation_first_response() -> None:
    store = VoiceFeedbackStore()
    earcon, display = VoiceFeedbackPolicy(store).pipeline_event(
        turn_id="turn-risk",
        stage="first_response",
        t_ms=80,
        attrs={"cue": "confirmation", "spoken_hint": "这个需要确认。"},
    )

    assert earcon["earcon_name"] == "confirmation"
    assert display["state"] == "confirming"
    assert display["privacy_level"] == "sensitive"
    assert display["action_buttons"] == ["confirm", "cancel", "open_panel"]


def test_feedback_policy_does_not_confirm_missing_user_slot_policy_block() -> None:
    store = VoiceFeedbackStore()
    earcon, display = VoiceFeedbackPolicy(store).pipeline_event(
        turn_id="turn-weather",
        stage="tool_policy_block",
        t_ms=80,
        status="error",
        attrs={
            "blocked_reason": "missing_user_slot",
            "interaction_state": "awaiting_user_info",
            "spoken_prompt": "你想查哪个地方明天的天气？",
        },
    )

    assert earcon is None
    assert display["state"] == "clarifying"
    assert display["short_text"] == "你想查哪个地方明天的天气？"


def test_final_status_preserves_clarifying_state() -> None:
    store = VoiceFeedbackStore()
    VoiceFeedbackPolicy(store).pipeline_event(
        turn_id="turn-weather",
        stage="local_route_clarify",
        t_ms=80,
        attrs={"prompt": "你想查哪个地方明天的天气？"},
    )

    display = VoiceFeedbackPolicy(store).final_status(
        turn_id="turn-weather",
        status="complete",
        t_ms=120,
        short_text="你想查哪个地方明天的天气？",
    )

    assert display["state"] == "clarifying"


def test_feedback_policy_only_confirms_high_risk_policy_block() -> None:
    store = VoiceFeedbackStore()
    earcon, display = VoiceFeedbackPolicy(store).pipeline_event(
        turn_id="turn-risk",
        stage="tool_policy_block",
        t_ms=80,
        status="error",
        attrs={
            "blocked_reason": "confirmation_required",
            "interaction_state": "confirming_high_risk",
            "spoken_prompt": "要操作前门吗？请确认。",
        },
    )

    assert earcon["earcon_name"] == "confirmation"
    assert display["state"] == "confirming"


def test_feedback_policy_maps_action_success() -> None:
    store = VoiceFeedbackStore()
    earcon, display = VoiceFeedbackPolicy(store).pipeline_event(
        turn_id="turn-action",
        stage="tool_result",
        t_ms=300,
        status="ok",
        attrs={"name": "HassTurnOn"},
    )

    assert earcon["earcon_name"] == "success"
    assert display["state"] == "done"


def test_feedback_policy_maps_failure() -> None:
    store = VoiceFeedbackStore()
    earcon, display = VoiceFeedbackPolicy(store).pipeline_event(
        turn_id="turn-failure",
        stage="provider_error",
        t_ms=900,
        status="error",
        attrs={"error": "TimeoutError"},
    )

    assert earcon["earcon_name"] == "failure"
    assert display["state"] == "failed"
    assert display["short_text"] == "TimeoutError"


def test_quiet_hours_suppress_noncritical_thinking() -> None:
    store = VoiceFeedbackStore()

    event = store.emit_earcon(
        turn_id="turn-night",
        earcon_name="thinking",
        scheduled_at_ms=2000,
        quiet_hour=23,
    )

    assert event["played_at_ms"] is None
    assert event["suppressed_reason"] == "quiet_hours"
    assert event["volume_profile"] == "silent"
    assert event["quiet_hours_applied"]


def test_microphone_hot_suppresses_non_listening_safe_earcon() -> None:
    store = VoiceFeedbackStore()

    event = store.emit_earcon(
        turn_id="turn-hot",
        earcon_name="search",
        scheduled_at_ms=200,
        microphone_hot=True,
        quiet_hour=12,
    )

    assert event["played_at_ms"] is None
    assert event["suppressed_reason"] == "microphone_hot"
