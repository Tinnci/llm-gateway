"""Non-blocking first-response audio playback."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_FIRST_RESPONSE_AUDIO_ENABLED,
    CONF_FIRST_RESPONSE_LOCAL_SERVICE,
    CONF_FIRST_RESPONSE_MEDIA_PLAYER,
    CONF_FIRST_RESPONSE_PLAYBACK_ADAPTER,
    CONF_FIRST_RESPONSE_TTS_ENTITY,
    DOMAIN,
    FIRST_RESPONSE_ADAPTER_AUTO,
    FIRST_RESPONSE_ADAPTER_HA_MEDIA_PLAYER,
    FIRST_RESPONSE_ADAPTER_LOCAL,
    FIRST_RESPONSE_PLAYBACK_ADAPTERS,
    LOGGER,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, State

    from .feedback import VoiceFeedbackStore

FIRST_RESPONSE_SCRIPT_DOMAIN = "script"
FIRST_RESPONSE_SCRIPT_SERVICE = "llm_gateway_first_response"
LOCAL_SERVICE_CANDIDATES = (
    ("rest_command", "kukui_voice_feedback"),
    ("script", "kukui_voice_feedback"),
    ("rest_command", "kukui_voice_first_response"),
    ("script", "kukui_voice_first_response"),
    (FIRST_RESPONSE_SCRIPT_DOMAIN, FIRST_RESPONSE_SCRIPT_SERVICE),
)
TTS_DOMAIN = "tts"
TTS_SPEAK_SERVICE = "speak"
FIRST_RESPONSE_TARGET_MS = 300
MEDIA_PLAYER_DOMAIN = "media_player"
AUTO_MEDIA_IDLE_STATES = {"idle", "paused", "standby", "off", "on"}
UNAVAILABLE_STATES = {"unavailable", "unknown"}

SHORT_TTS_CACHE: dict[str, str] = {
    "我看一下。": "thinking",
    "我查一下。": "search",
    "这个需要确认。": "confirmation",
    "你要控制哪个房间？": "clarify_room",
    "好了。": "done",
}

type RunMarker = Callable[..., dict[str, Any] | None]


@dataclass(frozen=True, slots=True)
class PlaybackRoute:
    """Resolved first-response playback backend."""

    backend: str
    reason: str
    adapter: str = "none"
    local_service: str = ""
    tts_entity: str = ""
    media_player_entity: str = ""


def first_response_audio_status(
    hass: HomeAssistant,
    options: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the playback route and candidates visible in the panel."""
    route = resolve_first_response_playback_route(hass, options)
    configured_tts = str(options.get(CONF_FIRST_RESPONSE_TTS_ENTITY) or "").strip()
    configured_local_service = str(
        options.get(CONF_FIRST_RESPONSE_LOCAL_SERVICE) or ""
    ).strip()
    configured_media_player = str(
        options.get(CONF_FIRST_RESPONSE_MEDIA_PLAYER) or ""
    ).strip()
    enabled = options.get(CONF_FIRST_RESPONSE_AUDIO_ENABLED, True) is not False
    adapter = _playback_adapter(options)
    return {
        "enabled": enabled,
        "adapter": adapter,
        "configured": {
            "local_service": configured_local_service,
            "local_service_exists": _service_exists(hass, configured_local_service),
            "tts_entity": configured_tts,
            "media_player_entity": configured_media_player,
            "tts_entity_exists": _entity_available(hass, configured_tts),
            "media_player_entity_exists": _entity_available(
                hass, configured_media_player
            ),
        },
        "route": {
            "backend": route.backend,
            "reason": route.reason,
            "adapter": route.adapter,
            "local_service": route.local_service,
            "tts_entity": route.tts_entity,
            "media_player_entity": route.media_player_entity,
        },
        "can_play": enabled and route.backend != "none",
        "services": {
            "script_llm_gateway_first_response": hass.services.has_service(
                FIRST_RESPONSE_SCRIPT_DOMAIN,
                FIRST_RESPONSE_SCRIPT_SERVICE,
            ),
            "tts_speak": hass.services.has_service(TTS_DOMAIN, TTS_SPEAK_SERVICE),
        },
        "candidates": {
            "local_services": _local_service_candidates(hass),
            "tts": _tts_candidates(hass),
            "media_player": _media_player_candidates(hass),
        },
    }


def resolve_first_response_playback_route(  # noqa: PLR0911 - explicit route ladder.
    hass: HomeAssistant,
    options: Mapping[str, Any],
) -> PlaybackRoute:
    """Resolve the backend the runtime will use for first-response audio."""
    adapter = _playback_adapter(options)
    if adapter == FIRST_RESPONSE_ADAPTER_LOCAL:
        return _resolve_local_route(hass, options)

    if adapter == FIRST_RESPONSE_ADAPTER_AUTO:
        route = _resolve_local_route(hass, options)
        if route.backend != "none":
            return route

    if adapter not in {
        FIRST_RESPONSE_ADAPTER_HA_MEDIA_PLAYER,
        FIRST_RESPONSE_ADAPTER_AUTO,
    }:
        return PlaybackRoute(
            backend="none",
            reason="disabled_adapter",
            adapter=adapter,
        )

    if (
        options.get(CONF_FIRST_RESPONSE_TTS_ENTITY)
        and options.get(CONF_FIRST_RESPONSE_MEDIA_PLAYER)
        and hass.services.has_service(TTS_DOMAIN, TTS_SPEAK_SERVICE)
    ):
        return PlaybackRoute(
            backend=f"{TTS_DOMAIN}.{TTS_SPEAK_SERVICE}",
            reason="configured_tts_media_player",
            adapter=FIRST_RESPONSE_ADAPTER_HA_MEDIA_PLAYER,
            tts_entity=str(options[CONF_FIRST_RESPONSE_TTS_ENTITY]),
            media_player_entity=str(options[CONF_FIRST_RESPONSE_MEDIA_PLAYER]),
        )
    if hass.services.has_service(TTS_DOMAIN, TTS_SPEAK_SERVICE):
        tts_entity = _auto_tts_entity(hass)
        media_player = _auto_media_player(hass)
        if tts_entity and media_player:
            return PlaybackRoute(
                backend=f"{TTS_DOMAIN}.{TTS_SPEAK_SERVICE}",
                reason="auto_discovered_tts_media_player",
                adapter=FIRST_RESPONSE_ADAPTER_HA_MEDIA_PLAYER,
                tts_entity=tts_entity,
                media_player_entity=media_player,
            )
        missing = []
        if not tts_entity:
            missing.append("tts_entity")
        if not media_player:
            missing.append("media_player")
        return PlaybackRoute(
            backend="none",
            reason="missing_" + "_and_".join(missing),
            adapter=FIRST_RESPONSE_ADAPTER_HA_MEDIA_PLAYER,
        )
    return PlaybackRoute(
        backend="none",
        reason="missing_tts_service",
        adapter=FIRST_RESPONSE_ADAPTER_HA_MEDIA_PLAYER,
    )


def _resolve_local_route(
    hass: HomeAssistant,
    options: Mapping[str, Any],
) -> PlaybackRoute:
    configured = str(options.get(CONF_FIRST_RESPONSE_LOCAL_SERVICE) or "").strip()
    if configured:
        if _service_exists(hass, configured):
            return PlaybackRoute(
                backend=configured,
                reason="configured_local_service",
                adapter=FIRST_RESPONSE_ADAPTER_LOCAL,
                local_service=configured,
            )
        return PlaybackRoute(
            backend="none",
            reason="configured_local_service_missing",
            adapter=FIRST_RESPONSE_ADAPTER_LOCAL,
            local_service=configured,
        )

    for domain, service in LOCAL_SERVICE_CANDIDATES:
        if hass.services.has_service(domain, service):
            service_id = f"{domain}.{service}"
            return PlaybackRoute(
                backend=service_id,
                reason="auto_discovered_local_service",
                adapter=FIRST_RESPONSE_ADAPTER_LOCAL,
                local_service=service_id,
            )
    return PlaybackRoute(
        backend="none",
        reason="missing_local_adapter",
        adapter=FIRST_RESPONSE_ADAPTER_LOCAL,
    )


def _playback_adapter(options: Mapping[str, Any]) -> str:
    adapter = str(
        options.get(CONF_FIRST_RESPONSE_PLAYBACK_ADAPTER)
        or FIRST_RESPONSE_ADAPTER_LOCAL
    ).strip()
    if adapter in FIRST_RESPONSE_PLAYBACK_ADAPTERS:
        return adapter
    return FIRST_RESPONSE_ADAPTER_LOCAL


def _service_exists(hass: HomeAssistant, service_id: str) -> bool | None:
    if not service_id:
        return None
    if "." not in service_id:
        return False
    domain, service = service_id.split(".", 1)
    return hass.services.has_service(domain, service)


def _local_service_candidates(hass: HomeAssistant) -> list[dict[str, Any]]:
    return [
        {
            "service": f"{domain}.{service}",
            "available": hass.services.has_service(domain, service),
            "preferred": index == 0,
        }
        for index, (domain, service) in enumerate(LOCAL_SERVICE_CANDIDATES)
    ]


def _tts_candidates(hass: HomeAssistant) -> list[dict[str, Any]]:
    return [
        {
            "entity_id": state.entity_id,
            "state": state.state,
            "name": str(state.attributes.get("friendly_name") or state.entity_id),
            "usable": state.state not in UNAVAILABLE_STATES,
            "preferred": _is_preferred_tts(state),
        }
        for state in sorted(
            hass.states.async_all(TTS_DOMAIN), key=lambda item: item.entity_id
        )
    ]


def _media_player_candidates(hass: HomeAssistant) -> list[dict[str, Any]]:
    return [
        {
            "entity_id": state.entity_id,
            "state": state.state,
            "name": str(state.attributes.get("friendly_name") or state.entity_id),
            "usable": state.state in AUTO_MEDIA_IDLE_STATES,
            "preferred": _is_preferred_media_player(state),
        }
        for state in sorted(
            hass.states.async_all(MEDIA_PLAYER_DOMAIN), key=lambda item: item.entity_id
        )
    ]


def _entity_available(hass: HomeAssistant, entity_id: str) -> bool | None:
    if not entity_id:
        return None
    state = hass.states.get(entity_id)
    return bool(state and state.state not in UNAVAILABLE_STATES)


def _auto_tts_entity(hass: HomeAssistant) -> str:
    states = [
        state
        for state in hass.states.async_all(TTS_DOMAIN)
        if state.state not in UNAVAILABLE_STATES
    ]
    if not states:
        return ""
    preferred = [state for state in states if _is_preferred_tts(state)]
    if preferred:
        return preferred[0].entity_id
    return states[0].entity_id if len(states) == 1 else ""


def _auto_media_player(hass: HomeAssistant) -> str:
    candidates = [
        state
        for state in hass.states.async_all(MEDIA_PLAYER_DOMAIN)
        if state.state in AUTO_MEDIA_IDLE_STATES
    ]
    if len(candidates) == 1:
        return candidates[0].entity_id
    preferred = [state for state in candidates if _is_preferred_media_player(state)]
    return preferred[0].entity_id if len(preferred) == 1 else ""


def _is_preferred_tts(state: State) -> bool:
    return (
        "edge" in state.entity_id.lower()
        or "edge" in str(state.attributes.get("friendly_name") or "").lower()
    )


def _is_preferred_media_player(state: State) -> bool:
    haystack = f"{state.entity_id} {state.attributes.get('friendly_name')}".lower()
    return any(
        marker in haystack
        for marker in ("voice", "assistant", "kukui", "homepod", "speaker")
    )


class FirstResponsePlayer:
    """Schedule short first-response audio without blocking the voice path."""

    def __init__(
        self,
        hass: HomeAssistant,
        store: VoiceFeedbackStore,
        options_getter: Callable[[], Mapping[str, Any]],
    ) -> None:
        self._hass = hass
        self._store = store
        self._options_getter = options_getter

    def schedule(
        self,
        *,
        turn_id: str,
        t_ms: int,
        attrs: dict[str, Any],
        marker: RunMarker,
    ) -> dict[str, Any] | None:
        """Schedule first-response audio and return the trace event."""
        text = str(attrs.get("spoken_hint") or "").strip()
        phrase_key = SHORT_TTS_CACHE.get(text, "dynamic")
        source = "cached_tts" if phrase_key != "dynamic" else "short_tts"

        if not text:
            event = self._store.emit_first_response_audio(
                turn_id=turn_id,
                text="",
                scheduled_at_ms=t_ms,
                source="none",
                phrase_key="none",
                backend="none",
                scheduled=False,
                suppressed_reason=str(
                    attrs.get("audio_suppressed_reason") or "no_spoken_hint"
                ),
            )
            _mark_audio(turn_id, marker, event)
            return event

        options = dict(self._options_getter())
        if options.get(CONF_FIRST_RESPONSE_AUDIO_ENABLED, True) is False:
            event = self._store.emit_first_response_audio(
                turn_id=turn_id,
                text=text,
                scheduled_at_ms=t_ms,
                source=source,
                phrase_key=phrase_key,
                backend="none",
                scheduled=False,
                suppressed_reason="disabled",
            )
            _mark_audio(turn_id, marker, event)
            return event

        if attrs.get("microphone_hot"):
            event = self._store.emit_first_response_audio(
                turn_id=turn_id,
                text=text,
                scheduled_at_ms=t_ms,
                source=source,
                phrase_key=phrase_key,
                backend="none",
                scheduled=False,
                suppressed_reason="microphone_hot_suppressed",
            )
            _mark_audio(turn_id, marker, event)
            return event

        route = self._select_route(options)
        event = self._store.emit_first_response_audio(
            turn_id=turn_id,
            text=text,
            scheduled_at_ms=t_ms,
            source=source,
            phrase_key=phrase_key,
            backend=route.backend,
            adapter=route.adapter,
            local_service=route.local_service,
            tts_entity=route.tts_entity,
            media_player_entity=route.media_player_entity,
            selection_reason=route.reason,
            scheduled=True,
            suppressed_reason=""
            if route.backend != "none"
            else f"playback_unavailable:{route.reason}",
        )
        _mark_audio(turn_id, marker, event)

        if route.backend == "none":
            return event

        self._hass.async_create_task(
            self._async_play(
                turn_id=turn_id,
                event_id=str(event["id"]),
                text=text,
                source=source,
                route=route,
                marker=marker,
            ),
            name=f"{DOMAIN}_first_response_audio_{turn_id}",
        )
        return event

    def _select_route(self, options: dict[str, Any]) -> PlaybackRoute:
        return resolve_first_response_playback_route(self._hass, options)

    async def _async_play(  # noqa: PLR0913 - carries one scheduled playback context.
        self,
        *,
        turn_id: str,
        event_id: str,
        text: str,
        source: str,
        route: PlaybackRoute,
        marker: RunMarker,
    ) -> None:
        try:
            if route.adapter == FIRST_RESPONSE_ADAPTER_LOCAL:
                domain, service = route.backend.split(".", 1)
                await self._hass.services.async_call(
                    domain,
                    service,
                    {
                        "message": text,
                        "text": text,
                        "phrase_key": SHORT_TTS_CACHE.get(text, "dynamic"),
                        "source": source,
                        "turn_id": turn_id,
                        "semantic_state": SHORT_TTS_CACHE.get(text, "dynamic"),
                        "adapter": "display_agent",
                    },
                    blocking=False,
                )
            else:
                await self._hass.services.async_call(
                    TTS_DOMAIN,
                    TTS_SPEAK_SERVICE,
                    {
                        "media_player_entity_id": route.media_player_entity,
                        "message": text,
                        "cache": True,
                    },
                    target={"entity_id": route.tts_entity},
                    blocking=False,
                )
        except (HomeAssistantError, ValueError, TypeError) as err:
            LOGGER.warning(
                "First response playback failed backend=%s error=%s",
                route.backend,
                type(err).__name__,
            )
            updated = self._store.update_first_response_audio(
                event_id,
                played=False,
                source=source,
                backend=route.backend,
                adapter=route.adapter,
                local_service=route.local_service,
                suppressed_reason=f"service_error:{type(err).__name__}",
            )
            if updated:
                _mark_audio(turn_id, marker, updated)
            return

        updated = self._store.update_first_response_audio(
            event_id,
            played=True,
            played_at_ms=_scheduled_at_ms(self._store, turn_id, event_id),
            source=source,
            backend=route.backend,
            adapter=route.adapter,
            local_service=route.local_service,
            suppressed_reason="",
        )
        if updated:
            _mark_audio(turn_id, marker, updated)


def first_response_audio_trace_attrs(event: dict[str, Any]) -> dict[str, Any]:
    """Return compact first-response audio trace fields."""
    return {
        "first_response_text": event.get("text") or "",
        "first_response_audio.scheduled": bool(event.get("scheduled")),
        "first_response_audio.played": bool(event.get("played")),
        "first_response_audio.played_at_ms": event.get("played_at_ms"),
        "first_response_audio.source": event.get("source") or "",
        "first_response_audio.backend": event.get("backend") or "",
        "first_response_audio.adapter": event.get("adapter") or "",
        "first_response_audio.local_service": event.get("local_service") or "",
        "first_response_audio.tts_entity": event.get("tts_entity") or "",
        "first_response_audio.media_player_entity": (
            event.get("media_player_entity") or ""
        ),
        "first_response_audio.selection_reason": (event.get("selection_reason") or ""),
        "first_response_audio.suppressed_reason": event.get("suppressed_reason") or "",
        "first_response_audio.target_ms": FIRST_RESPONSE_TARGET_MS,
    }


def _mark_audio(turn_id: str, marker: RunMarker, event: dict[str, Any]) -> None:
    marker(
        turn_id,
        "first_response_audio",
        status="error" if event.get("suppressed_reason") else "ok",
        attrs=first_response_audio_trace_attrs(event),
    )


def _scheduled_at_ms(
    store: VoiceFeedbackStore,
    turn_id: str,
    event_id: str,
) -> int:
    for event in store.first_response_audio_for_turn(turn_id):
        if event.get("id") == event_id:
            return int(event.get("scheduled_at_ms") or 0)
    return 0
