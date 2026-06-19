"""Tests for first-response audio playback scheduling."""

from __future__ import annotations

from custom_components.llm_gateway.feedback import VoiceFeedbackStore
from custom_components.llm_gateway.first_response_audio import FirstResponsePlayer


def _marker(events: list[dict]):
    def mark(
        run_id: str,
        stage: str,
        *,
        status: str = "ok",
        attrs: dict | None = None,
    ) -> dict:
        event = {
            "run_id": run_id,
            "stage": stage,
            "status": status,
            "attrs": dict(attrs or {}),
        }
        events.append(event)
        return event

    return mark


async def test_first_response_audio_schedules_when_spoken_hint_exists(hass) -> None:
    store = VoiceFeedbackStore()
    events: list[dict] = []
    player = FirstResponsePlayer(hass, store, dict)

    event = player.schedule(
        turn_id="turn-search",
        t_ms=150,
        attrs={"spoken_hint": "我查一下。"},
        marker=_marker(events),
    )

    assert event["scheduled"] is True
    assert event["played"] is False
    assert event["source"] == "cached_tts"
    assert event["adapter"] == "local"
    assert event["suppressed_reason"] == "playback_unavailable:missing_local_adapter"
    assert events[-1]["attrs"]["first_response_audio.scheduled"] is True


async def test_first_response_audio_marks_played_when_local_script_available(
    hass,
) -> None:
    calls = []

    async def handle(call):
        calls.append(dict(call.data))

    hass.services.async_register("script", "llm_gateway_first_response", handle)
    store = VoiceFeedbackStore()
    events: list[dict] = []
    player = FirstResponsePlayer(hass, store, dict)

    event = player.schedule(
        turn_id="turn-search",
        t_ms=150,
        attrs={"spoken_hint": "我查一下。"},
        marker=_marker(events),
    )
    await hass.async_block_till_done()

    [updated] = store.first_response_audio_for_turn("turn-search")
    assert event["scheduled"] is True
    assert updated["played"] is True
    assert updated["played_at_ms"] is not None
    assert updated["adapter"] == "local"
    assert updated["backend"] == "script.llm_gateway_first_response"
    assert calls[0]["message"] == "我查一下。"
    assert calls[0]["adapter"] == "display_agent"
    assert events[-1]["attrs"]["first_response_audio.played"] is True


async def test_first_response_audio_prefers_display_agent_rest_command(hass) -> None:
    calls = []

    async def handle(call):
        calls.append(dict(call.data))

    hass.services.async_register("rest_command", "kukui_voice_feedback", handle)
    store = VoiceFeedbackStore()
    events: list[dict] = []
    player = FirstResponsePlayer(hass, store, dict)

    event = player.schedule(
        turn_id="turn-search",
        t_ms=110,
        attrs={"spoken_hint": "我查一下。"},
        marker=_marker(events),
    )
    await hass.async_block_till_done()

    [updated] = store.first_response_audio_for_turn("turn-search")
    assert event["backend"] == "rest_command.kukui_voice_feedback"
    assert updated["played"] is True
    assert updated["selection_reason"] == "auto_discovered_local_service"
    assert updated["local_service"] == "rest_command.kukui_voice_feedback"
    assert calls[0]["turn_id"] == "turn-search"
    assert calls[0]["text"] == "我查一下。"


async def test_first_response_audio_auto_discovers_tts_and_media_player(hass) -> None:
    calls = []

    async def handle(call):
        calls.append(dict(call.data))

    hass.services.async_register("tts", "speak", handle)
    hass.states.async_set(
        "tts.google_translate_en_com",
        "unknown",
        {"friendly_name": "Google Translate"},
    )
    hass.states.async_set(
        "tts.edge_tts_service_edge_tts",
        "2026-06-19T00:00:00+00:00",
        {"friendly_name": "Edge TTS Service Edge TTS"},
    )
    hass.states.async_set(
        "media_player.ke_ting_433",
        "idle",
        {"friendly_name": "Homepod mini"},
    )
    store = VoiceFeedbackStore()
    events: list[dict] = []
    player = FirstResponsePlayer(
        hass,
        store,
        lambda: {"first_response_playback_adapter": "ha_media_player"},
    )

    event = player.schedule(
        turn_id="turn-search",
        t_ms=120,
        attrs={"spoken_hint": "我查一下。"},
        marker=_marker(events),
    )
    await hass.async_block_till_done()

    [updated] = store.first_response_audio_for_turn("turn-search")
    assert event["backend"] == "tts.speak"
    assert updated["played"] is True
    assert updated["adapter"] == "ha_media_player"
    assert updated["selection_reason"] == "auto_discovered_tts_media_player"
    assert updated["tts_entity"] == "tts.edge_tts_service_edge_tts"
    assert updated["media_player_entity"] == "media_player.ke_ting_433"
    assert calls[0] == {
        "media_player_entity_id": "media_player.ke_ting_433",
        "message": "我查一下。",
        "cache": True,
        "entity_id": "tts.edge_tts_service_edge_tts",
    }
    assert events[-1]["attrs"]["first_response_audio.media_player_entity"] == (
        "media_player.ke_ting_433"
    )


async def test_first_response_audio_does_not_auto_interrupt_busy_player(hass) -> None:
    def handle(*_args: object) -> None:
        return None

    hass.services.async_register("tts", "speak", handle)
    hass.states.async_set(
        "tts.edge_tts_service_edge_tts",
        "2026-06-19T00:00:00+00:00",
        {"friendly_name": "Edge TTS Service Edge TTS"},
    )
    hass.states.async_set(
        "media_player.ke_ting_433",
        "playing",
        {"friendly_name": "Homepod mini"},
    )
    store = VoiceFeedbackStore()
    events: list[dict] = []
    player = FirstResponsePlayer(
        hass,
        store,
        lambda: {"first_response_playback_adapter": "ha_media_player"},
    )

    event = player.schedule(
        turn_id="turn-search",
        t_ms=120,
        attrs={"spoken_hint": "我查一下。"},
        marker=_marker(events),
    )

    assert event["backend"] == "none"
    assert event["suppressed_reason"] == "playback_unavailable:missing_media_player"


async def test_first_response_audio_records_suppressed_reason(hass) -> None:
    store = VoiceFeedbackStore()
    events: list[dict] = []
    player = FirstResponsePlayer(
        hass,
        store,
        lambda: {"first_response_audio_enabled": False},
    )

    event = player.schedule(
        turn_id="turn-muted",
        t_ms=80,
        attrs={"spoken_hint": "这个需要确认。"},
        marker=_marker(events),
    )

    assert event["scheduled"] is False
    assert event["played"] is False
    assert event["suppressed_reason"] == "disabled"
    assert events[-1]["status"] == "error"
