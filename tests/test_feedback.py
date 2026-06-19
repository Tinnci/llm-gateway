"""Tests for deterministic earcon and live display feedback."""

from __future__ import annotations

from custom_components.llm_gateway.feedback import (
    VoiceFeedbackPolicy,
    VoiceFeedbackStore,
)


def test_feedback_policy_maps_search_first_response() -> None:
    store = VoiceFeedbackStore()
    earcon, display = VoiceFeedbackPolicy(store).pipeline_event(
        turn_id="turn-search",
        stage="first_response",
        t_ms=120,
        attrs={"cue": "search", "spoken_hint": "我查一下。"},
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
