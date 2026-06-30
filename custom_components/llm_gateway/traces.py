"""Compressed diagnostic trace storage for Voice Harness runs."""

from __future__ import annotations

import base64
import json
import zlib
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.storage import Store
from homeassistant.util import ulid

from .const import (
    CONF_DIAGNOSTIC_TRACES,
    CONF_TRACE_INCLUDE_RAW_MESSAGES,
    CONF_TRACE_MAX_RUNS,
    CONF_TRACE_RETENTION_HOURS,
    DOMAIN,
    MAX_TRACE_RETENTION_HOURS,
    MAX_TRACE_RUNS,
    RECOMMENDED_TRACE_MAX_RUNS,
    RECOMMENDED_TRACE_RETENTION_HOURS,
)
from .satellite_diagnostics import (
    SATELLITE_DIAGNOSTIC_SNAPSHOT_ENTITY_ID,
    satellite_diagnostic_snapshot,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

SUMMARY_TEXT_LIMIT = 1200
RAW_TEXT_LIMIT = 12000
TRACE_ENCODING = "json+zlib+base64"
_SECRET_MARKERS = ("api_key", "apikey", "authorization", "password", "secret", "token")
_NON_BLOCKING_STAGES = {
    "verifier_audit",
    "deep_verifier_audit",
    "summary",
    "memory_extraction",
    "deep_task_submitted",
    "feedback",
    "first_response_audio",
    "display_status",
}
_ACTION_TOOL_PREFIXES = ("Hass",)


@dataclass(slots=True)
class TraceTurn:
    """A completed assistant turn to store for diagnostics."""

    conversation_id: str | None
    user_text: str
    assistant_text: str
    route: dict[str, Any]
    latency_ms: int
    status: str
    raw_payload: dict[str, Any]
    run_id: str | None = None
    timeline: list[dict[str, Any]] = field(default_factory=list)


class TraceStore:
    """Persistent, bounded diagnostic traces for admin debugging."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._hass = hass
        self._store: Store[dict[str, Any]] = Store(
            hass, 1, f"{DOMAIN}.{entry_id}.traces"
        )
        self._records: list[dict[str, Any]] = []

    async def async_load(self) -> None:
        """Load compressed traces from storage."""
        data = await self._store.async_load() or {}
        records = data.get("records") if isinstance(data, dict) else []
        if not isinstance(records, list):
            records = []
        self._records = [record for record in records if isinstance(record, dict)]

    async def async_record_turn(
        self,
        options: dict[str, Any],
        turn: TraceTurn,
    ) -> None:
        """Record one completed voice/text run if diagnostic traces are enabled."""
        if not options.get(CONF_DIAGNOSTIC_TRACES):
            return

        tools = _tool_summary(turn.raw_payload)
        grounding = _grounding_summary(turn.raw_payload)
        verifier_mode = _verifier_mode(turn.raw_payload, grounding)
        errors = _error_summary(turn.raw_payload, tools, grounding, turn.timeline)
        record_id = turn.run_id or ulid.ulid_now()
        timeline_spans = _timeline_spans(turn.timeline)
        actions = _actions_summary(tools)
        earcons = _earcon_summary(turn.raw_payload)
        display_status = _display_status_summary(turn.raw_payload)
        first_response = _first_response_summary(turn.raw_payload, turn.timeline)
        first_response_audio = _first_response_audio_summary(turn.raw_payload)
        search_debug = _search_debug(tools, grounding, timeline_spans)
        diagnostic_snapshot = _diagnostic_snapshot_summary(
            satellite_diagnostic_snapshot(self._hass)
        )
        record = {
            "id": record_id,
            "run_id": record_id,
            "created_at": datetime.now(UTC).isoformat(),
            "conversation_id": turn.conversation_id or "",
            "input": _input_summary(turn.raw_payload, turn),
            "user_text": _truncate(turn.user_text, SUMMARY_TEXT_LIMIT),
            "assistant_text": _truncate(turn.assistant_text, SUMMARY_TEXT_LIMIT),
            "final_speech_text": _truncate(
                _speech_summary(turn.raw_payload).get("final") or turn.assistant_text,
                SUMMARY_TEXT_LIMIT,
            ),
            "route": {
                "kind": str(turn.route.get("kind") or ""),
                "model": str(turn.route.get("model") or ""),
                "max_tokens": turn.route.get("max_tokens"),
                "timeout_s": turn.route.get("timeout_s"),
                "provider": turn.route.get("provider"),
                "provider_attempts": turn.route.get("provider_attempts") or [],
            },
            "route_decision": _route_decision_summary(turn.route, timeline_spans),
            "latency_ms": turn.latency_ms,
            "status": turn.status,
            "completion": _completion_summary(
                turn.status, turn.latency_ms, timeline_spans
            ),
            "timeline": turn.timeline,
            "timeline_spans": timeline_spans,
            "critical_path": _critical_path(timeline_spans, verifier_mode),
            "critical_path_flags": _critical_path_flags(timeline_spans),
            "first_response_decision": first_response,
            "first_response_text": _first_response_text(
                first_response,
                first_response_audio,
            ),
            "first_response_audio": first_response_audio,
            "speech": _speech_summary(turn.raw_payload),
            "tools": tools,
            "tool_calls_by_iteration": _tool_calls_by_iteration(timeline_spans),
            "duplicate_tool_suppressions": _duplicate_tool_suppressions(timeline_spans),
            "grounding": grounding,
            "verifier_mode": verifier_mode,
            "debug_flags": _debug_flags(
                {
                    "first_response": first_response,
                    "verifier_mode": verifier_mode,
                    "route": turn.route,
                },
                tools,
                grounding,
                actions,
            ),
            "errors": errors,
            "search_gate": _search_gate_summary(first_response, search_debug),
            "search_debug": search_debug,
            "weather_context_path": _weather_context_path(
                first_response,
                tools,
                timeline_spans,
                search_debug,
            ),
            "audio_graph": _audio_graph_summary(
                turn.raw_payload,
                earcons,
                first_response_audio,
                timeline_spans,
            ),
            "earcon_diagnostics": _earcon_diagnostics_summary(
                earcons,
                timeline_spans,
            ),
            "aec_diagnostics": _aec_diagnostics_summary(turn.raw_payload),
            "diagnostic_snapshot": diagnostic_snapshot,
            "actions": actions,
            "earcons": earcons,
            "display_status": display_status,
            "raw_payload": None,
        }
        if options.get(CONF_TRACE_INCLUDE_RAW_MESSAGES):
            record["raw_payload"] = _compress_payload(turn.raw_payload)

        self._records.insert(0, record)
        self._prune(options)
        await self._store.async_save({"records": self._records})

    def snapshot(self, *, include_raw: bool = True) -> dict[str, Any]:
        """Return traces for the Voice Harness panel."""
        return {
            "records": [
                _record_for_panel(record, include_raw=include_raw)
                for record in self._records
            ],
            "storage": {
                "encoding": TRACE_ENCODING,
                "records": len(self._records),
                "compressed_bytes": sum(
                    int((record.get("raw_payload") or {}).get("compressed_bytes") or 0)
                    for record in self._records
                ),
            },
        }

    def list_runs(self, *, limit: int = 30) -> list[dict[str, Any]]:
        """Return recent runs without raw payloads."""
        return [
            _record_for_panel(record, include_raw=False)
            for record in self._records[: max(1, limit)]
        ]

    def get_run(
        self, run_id: str, *, include_raw: bool = True
    ) -> dict[str, Any] | None:
        """Return one run detail by trace/run id."""
        for record in self._records:
            if record.get("id") == run_id or record.get("run_id") == run_id:
                return _record_for_panel(record, include_raw=include_raw)
        return None

    def _prune(self, options: dict[str, Any]) -> None:
        max_runs = _bounded_int(
            options.get(CONF_TRACE_MAX_RUNS),
            default=RECOMMENDED_TRACE_MAX_RUNS,
            minimum=1,
            maximum=MAX_TRACE_RUNS,
        )
        retention_hours = _bounded_int(
            options.get(CONF_TRACE_RETENTION_HOURS),
            default=RECOMMENDED_TRACE_RETENTION_HOURS,
            minimum=1,
            maximum=MAX_TRACE_RETENTION_HOURS,
        )
        cutoff = datetime.now(UTC) - timedelta(hours=retention_hours)
        self._records = [
            record
            for record in self._records[:max_runs]
            if _parse_time(str(record.get("created_at") or ""), cutoff) >= cutoff
        ]


def _record_for_panel(record: dict[str, Any], *, include_raw: bool) -> dict[str, Any]:
    panel_record = {key: value for key, value in record.items() if key != "raw_payload"}
    raw_payload = record.get("raw_payload")
    if isinstance(raw_payload, dict):
        panel_record["raw_payload_meta"] = {
            "encoding": raw_payload.get("encoding"),
            "uncompressed_bytes": raw_payload.get("uncompressed_bytes"),
            "compressed_bytes": raw_payload.get("compressed_bytes"),
        }
        if include_raw:
            panel_record["raw_payload"] = _decompress_payload(raw_payload)
    return panel_record


def _compress_payload(payload: dict[str, Any]) -> dict[str, Any]:
    redacted = _redact_and_bound(payload)
    raw = json.dumps(redacted, ensure_ascii=False, separators=(",", ":")).encode()
    compressed = zlib.compress(raw, level=6)
    return {
        "encoding": TRACE_ENCODING,
        "data": base64.b64encode(compressed).decode("ascii"),
        "uncompressed_bytes": len(raw),
        "compressed_bytes": len(compressed),
    }


def _decompress_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    try:
        compressed = base64.b64decode(str(payload.get("data") or ""))
        raw = zlib.decompress(compressed)
        data = json.loads(raw.decode())
    except (ValueError, TypeError, zlib.error):
        return None
    return data if isinstance(data, dict) else None


def _redact_and_bound(value: object, *, key: str = "") -> object:
    if any(marker in key.lower() for marker in _SECRET_MARKERS):
        return "[redacted]"
    if isinstance(value, dict):
        return {
            str(item_key): _redact_and_bound(item_value, key=str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        return [_redact_and_bound(item, key=key) for item in value[:80]]
    if isinstance(value, str):
        return _truncate(value, RAW_TEXT_LIMIT)
    if isinstance(value, int | float | bool) or value is None:
        return value
    return _truncate(str(value), RAW_TEXT_LIMIT)


def _truncate(text: str, limit: int) -> str:
    value = str(text or "").replace("\x00", "").strip()
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def _tool_summary(raw_payload: dict[str, Any]) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    for event in raw_payload.get("tool_events") or []:
        if not isinstance(event, dict):
            continue
        result = event.get("result") if isinstance(event.get("result"), dict) else {}
        tool = {
            "name": str(event.get("name") or ""),
            "phase": str(event.get("phase") or ""),
            "tool_call_id": str(event.get("tool_call_id") or ""),
            "external": bool(event.get("external")),
            "status": str(event.get("status") or ""),
            "error": _truncate(
                str(event.get("error") or result.get("error") or ""),
                240,
            ),
            "args": _bound_mapping(event.get("args"), limit=800),
            "result": _bound_mapping(result, limit=1200),
        }
        tools.append(tool)
    if tools:
        _append_pseudo_tool_events(tools, raw_payload)
        return [tool for tool in tools if tool.get("name") or tool.get("tool_call_id")]

    for message in raw_payload.get("messages") or []:
        if not isinstance(message, dict):
            continue
        for call in message.get("tool_calls") or []:
            function = call.get("function") or {}
            tools.append(
                {
                    "name": str(function.get("name") or ""),
                    "phase": "call",
                    "tool_call_id": str(call.get("id") or ""),
                    "args": _parse_json_mapping(function.get("arguments")),
                }
            )
        if message.get("role") == "tool":
            tools.append(
                {
                    "name": str(message.get("name") or ""),
                    "phase": "result",
                    "tool_call_id": str(message.get("tool_call_id") or ""),
                    "result": _parse_json_mapping(message.get("content")),
                }
            )
    _append_pseudo_tool_events(tools, raw_payload)
    return [tool for tool in tools if tool.get("name") or tool.get("tool_call_id")]


def _grounding_summary(raw_payload: dict[str, Any]) -> dict[str, Any]:
    grounding = raw_payload.get("grounding")
    if not isinstance(grounding, dict):
        return {}
    return {
        "status": str(grounding.get("status") or ""),
        "candidates": [
            _truncate(str(candidate), 80)
            for candidate in grounding.get("candidates") or []
            if candidate
        ][:8],
        "canonical_answers": [
            _truncate(str(answer), 120)
            for answer in grounding.get("canonical_answers") or []
            if answer
        ][:4],
        "repairs": [
            {
                "from": _truncate(str(repair.get("from") or ""), 80),
                "to": _truncate(str(repair.get("to") or ""), 80),
            }
            for repair in grounding.get("repairs") or []
            if isinstance(repair, dict)
        ][:8],
        "confidence": grounding.get("confidence"),
        "reason": _truncate(str(grounding.get("reason") or ""), 300),
        "verifier": _verifier_summary(grounding.get("verifier")),
        "evidence": _evidence_summary(grounding.get("evidence")),
        "final_modified_by_grounding": bool(grounding.get("repairs")),
    }


def _verifier_summary(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    provider = value.get("provider") if isinstance(value.get("provider"), dict) else {}
    return {
        "mode": str(value.get("mode") or ""),
        "route": str(value.get("route") or ""),
        "model": _truncate(str(value.get("model") or ""), 160),
        "provider": str(provider.get("name") or ""),
        "latency_ms": value.get("latency_ms"),
        "audit_only": bool(value.get("audit_only")),
        "error": str(value.get("error") or ""),
        "raw_excerpt": _truncate(str(value.get("raw_excerpt") or ""), 240),
    }


def _input_summary(raw_payload: dict[str, Any], turn: TraceTurn) -> dict[str, Any]:
    input_payload = (
        raw_payload.get("input") if isinstance(raw_payload.get("input"), dict) else {}
    )
    return {
        "text": _truncate(
            str(input_payload.get("text") or turn.user_text),
            SUMMARY_TEXT_LIMIT,
        ),
        "conversation_id": str(
            input_payload.get("conversation_id") or turn.conversation_id or ""
        ),
        "language": str(input_payload.get("language") or ""),
        "device_id": str(input_payload.get("device_id") or ""),
    }


def _speech_summary(raw_payload: dict[str, Any]) -> dict[str, Any]:
    speech = (
        raw_payload.get("speech") if isinstance(raw_payload.get("speech"), dict) else {}
    )
    return {
        "raw": _truncate(str(speech.get("raw") or ""), SUMMARY_TEXT_LIMIT),
        "grounded": _truncate(str(speech.get("grounded") or ""), SUMMARY_TEXT_LIMIT),
        "final": _truncate(str(speech.get("final") or ""), SUMMARY_TEXT_LIMIT),
        "tts_cleaned": bool(speech.get("tts_cleaned")),
    }


def _first_response_summary(
    raw_payload: dict[str, Any],
    timeline: list[dict[str, Any]],
) -> dict[str, Any]:
    route = (
        raw_payload.get("route") if isinstance(raw_payload.get("route"), dict) else {}
    )
    first_response = route.get("first_response")
    if isinstance(first_response, dict):
        return _bound_mapping(first_response, limit=600)
    for event in [*(raw_payload.get("timeline") or []), *timeline]:
        if not isinstance(event, dict) or event.get("stage") != "first_response":
            continue
        attrs = event.get("attrs") if isinstance(event.get("attrs"), dict) else {}
        summary = _bound_mapping(attrs, limit=600)
        summary["triggered_ms"] = _safe_int(event.get("t_ms"))
        return summary
    return {}


def _route_decision_summary(
    route: dict[str, Any],
    timeline_spans: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return structured capability route metadata for the panel."""
    route_decision = route.get("route_decision")
    if isinstance(route_decision, dict):
        return _bound_mapping(route_decision, limit=1200)
    for span in timeline_spans:
        if str(span.get("stage") or "") != "route_decision":
            continue
        return _bound_mapping(span.get("attrs"), limit=1200)
    return {}


def _first_response_audio_summary(raw_payload: dict[str, Any]) -> dict[str, Any]:
    events = raw_payload.get("first_response_audio_events")
    if not isinstance(events, list) or not events:
        return {}
    latest = events[-1] if isinstance(events[-1], dict) else {}
    return _bound_mapping(latest, limit=800)


def _first_response_text(
    decision: dict[str, Any],
    audio: dict[str, Any],
) -> str:
    return _truncate(
        str(
            decision.get("spoken_hint")
            or decision.get("text")
            or audio.get("text")
            or ""
        ),
        240,
    )


def _completion_summary(
    status: str,
    latency_ms: int,
    timeline_spans: list[dict[str, Any]],
) -> dict[str, Any]:
    last_span = timeline_spans[-1] if timeline_spans else {}
    last_stage = str(last_span.get("stage") or "")
    complete = (
        status in {"complete", "ok", "queued", "error"} or last_stage == "complete"
    )
    return {
        "complete": complete,
        "status": status,
        "latency_ms": max(0, int(latency_ms or 0)),
        "last_active_stage": last_stage,
        "last_active_status": str(last_span.get("status") or ""),
        "running_duration_ms": 0 if complete else max(0, int(latency_ms or 0)),
    }


def _timeline_spans(timeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    events = [event for event in timeline if isinstance(event, dict)]
    for index, event in enumerate(events):
        start_ms = _safe_int(event.get("t_ms"))
        next_ms = (
            _safe_int(events[index + 1].get("t_ms"))
            if index + 1 < len(events)
            else start_ms
        )
        spans.append(
            {
                "stage": str(event.get("stage") or ""),
                "start_ms": start_ms,
                "duration_ms": max(0, next_ms - start_ms),
                "status": str(event.get("status") or "ok"),
                "attrs": _bound_mapping(event.get("attrs"), limit=800),
            }
        )
    return spans


def _tool_calls_by_iteration(
    timeline_spans: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_iteration: dict[int, dict[str, Any]] = {}
    for span in timeline_spans:
        stage = str(span.get("stage") or "")
        if stage not in {
            "tool_call",
            "tool_result",
            "search_result",
            "tool_call_suppressed",
            "tool_policy_block",
            "forced_final",
        }:
            continue
        attrs = _mapping_value(span.get("attrs"))
        if "iteration" not in attrs:
            continue
        iteration = _safe_int(attrs.get("iteration"))
        group = by_iteration.setdefault(
            iteration,
            {
                "iteration": iteration,
                "calls": [],
                "results": [],
                "suppressions": [],
                "events": [],
            },
        )
        compact_event = {
            "stage": stage,
            "start_ms": span.get("start_ms") or 0,
            "duration_ms": span.get("duration_ms") or 0,
            "status": span.get("status") or "ok",
            "attrs": attrs,
        }
        group["events"].append(compact_event)
        if stage == "tool_call":
            names = _list_value(attrs.get("names"))
            group["calls"].extend(str(name) for name in names if name)
        elif stage in {"tool_result", "search_result"}:
            group["results"].append(
                {
                    "name": str(attrs.get("name") or ""),
                    "status": span.get("status") or "ok",
                    "error": _truncate(str(attrs.get("error") or ""), 240),
                }
            )
        elif stage == "tool_call_suppressed":
            group["suppressions"].append(
                {
                    "name": str(attrs.get("name") or ""),
                    "reason": str(attrs.get("reason") or ""),
                    "status": span.get("status") or "ok",
                }
            )
        elif stage == "forced_final":
            group["forced_final_reason"] = str(attrs.get("reason") or "")
    return [
        {
            **group,
            "calls": list(dict.fromkeys(group["calls"])),
        }
        for _, group in sorted(by_iteration.items())
    ]


def _duplicate_tool_suppressions(
    timeline_spans: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    suppressions: list[dict[str, Any]] = []
    for span in timeline_spans:
        if str(span.get("stage") or "") != "tool_call_suppressed":
            continue
        attrs = _mapping_value(span.get("attrs"))
        reason = str(attrs.get("reason") or "")
        if not reason.startswith("duplicate_"):
            continue
        suppressions.append(
            {
                "iteration": _safe_int(attrs.get("iteration")),
                "name": str(attrs.get("name") or ""),
                "reason": reason,
                "start_ms": span.get("start_ms") or 0,
                "status": span.get("status") or "ok",
            }
        )
    return suppressions


def _list_value(value: object) -> list[Any]:
    if isinstance(value, list):
        return value
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        parsed = json.loads(value)
    except ValueError:
        return []
    return parsed if isinstance(parsed, list) else []


def _critical_path(
    timeline_spans: list[dict[str, Any]],
    verifier_mode: str,
) -> list[dict[str, Any]]:
    path: list[dict[str, Any]] = []
    for span in timeline_spans:
        stage = str(span.get("stage") or "")
        blocking = stage not in _NON_BLOCKING_STAGES
        if stage in {"grounding_verifier", "verifier"} and verifier_mode != "blocking":
            blocking = False
        reason = "voice_path" if blocking else "background_or_audit"
        if stage in {"feedback", "first_response_audio", "display_status"}:
            reason = "feedback_playback"
        path.append(
            {
                "stage": stage,
                "start_ms": span.get("start_ms") or 0,
                "duration_ms": span.get("duration_ms") or 0,
                "status": span.get("status") or "ok",
                "blocking": blocking,
                "reason": reason,
            }
        )
    return path


def _critical_path_flags(timeline_spans: list[dict[str, Any]]) -> dict[str, bool]:
    """Return explicit audio/feedback critical-path booleans."""
    feedback_stages = {"feedback", "first_response_audio", "display_status"}
    feedback_blocking = False
    audio_joined = False
    for span in timeline_spans:
        stage = str(span.get("stage") or "")
        if stage not in feedback_stages:
            continue
        attrs = _mapping_value(span.get("attrs"))
        if bool(attrs.get("blocking")):
            feedback_blocking = True
        if bool(attrs.get("audio_playback_joined_critical_path")):
            audio_joined = True
    return {
        "feedback_blocking_critical_path": feedback_blocking,
        "audio_playback_joined_critical_path": audio_joined,
    }


def _evidence_summary(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    evidence: list[dict[str, Any]] = []
    for item in value[:12]:
        if not isinstance(item, dict):
            continue
        evidence.append(
            {
                "evidence_id": str(item.get("evidence_id") or ""),
                "source_id": _truncate(str(item.get("source_id") or ""), 240),
                "evidence_type": str(item.get("evidence_type") or ""),
                "title": _truncate(str(item.get("title") or ""), 160),
                "text": _truncate(str(item.get("text") or ""), 240),
                "included_in_final": bool(item.get("included_in_final")),
            }
        )
    return evidence


def _earcon_summary(raw_payload: dict[str, Any]) -> list[dict[str, Any]]:
    events = raw_payload.get("earcon_events")
    if not isinstance(events, list):
        return []
    return [
        _bound_mapping(event, limit=600) for event in events if isinstance(event, dict)
    ][:16]


def _audio_graph_summary(
    raw_payload: dict[str, Any],
    earcons: list[dict[str, Any]],
    first_response_audio: dict[str, Any],
    timeline_spans: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return the best-known audio graph without claiming unproven AEC."""
    provided = raw_payload.get("audio_graph")
    if isinstance(provided, dict):
        return _audio_graph_defaults() | _bound_mapping(provided, limit=1600)

    graph = _audio_graph_defaults()
    if any(_earcon_can_play_while_listening(event) for event in earcons):
        graph["playback_sink"] = _playback_sink_from_feedback(first_response_audio)
    if _has_tts_or_first_response_audio(first_response_audio, timeline_spans):
        graph["tts_in_aec_reference"] = False
    return graph


def _audio_graph_defaults() -> dict[str, Any]:
    return {
        "raw_mic_source": "unknown",
        "aec_mic_source": "",
        "vad_source": "unknown",
        "endpoint_source": "unknown",
        "asr_source": "unknown",
        "wake_word_source": "unknown",
        "playback_sink": "unknown",
        "render_reference_source": "",
        "aec_enabled": False,
        "aec_reference_active": False,
        "earcon_in_aec_reference": False,
        "tts_in_aec_reference": False,
        "container_bypasses_host_audio_processing": None,
    }


def _earcon_diagnostics_summary(
    earcons: list[dict[str, Any]],
    timeline_spans: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return conservative full-duplex diagnostics for the latest earcon."""
    provided = _provided_earcon_diagnostics(timeline_spans)
    if provided:
        return provided
    event = _latest_played_earcon(earcons)
    if not event:
        return {}
    can_play = _earcon_can_play_while_listening(event)
    ignore_window = int(event.get("duration_ms") or 0) if can_play else 0
    return {
        "earcon_name": str(event.get("earcon_name") or ""),
        "can_play_while_listening": can_play,
        "mic_open_during_earcon": None,
        "vad_threshold_profile": "degraded_ignore_window" if can_play else "",
        "ignore_window_ms": min(250, max(0, ignore_window)),
        "false_vad_during_earcon": None,
        "asr_partial_during_earcon": "",
        "full_duplex_mode": "degraded" if can_play else "disabled",
        "degraded_reason": (
            "aec_reference_not_verified" if can_play else "not_listening_safe"
        ),
    }


def _aec_diagnostics_summary(raw_payload: dict[str, Any]) -> dict[str, Any]:
    """Return AEC measurements when supplied by the satellite layer."""
    provided = raw_payload.get("aec_diagnostics")
    if isinstance(provided, dict):
        return _bound_mapping(provided, limit=1000)
    return {
        "raw_echo_rms": None,
        "aec_echo_rms": None,
        "echo_suppression_db": None,
        "double_talk_detected": None,
        "residual_echo_likelihood": None,
    }


def _diagnostic_snapshot_summary(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Return a trace-safe view of the latest satellite diagnostic snapshot."""
    if not snapshot:
        return {
            "available": False,
            "entity_id": SATELLITE_DIAGNOSTIC_SNAPSHOT_ENTITY_ID,
        }
    checks = [
        _diagnostic_check_summary(check)
        for check in snapshot.get("checks") or []
        if isinstance(check, dict)
    ][:32]
    counts = {"ok": 0, "warning": 0, "error": 0}
    for check in checks:
        status = str(check.get("status") or "")
        if status in counts:
            counts[status] += 1
    return {
        "available": True,
        "entity_id": SATELLITE_DIAGNOSTIC_SNAPSHOT_ENTITY_ID,
        "schema_version": snapshot.get("schema_version"),
        "generated_at": str(snapshot.get("generated_at") or ""),
        "status": _diagnostic_snapshot_status(checks),
        "check_counts": counts,
        "first_failing_check": _diagnostic_check_summary(
            snapshot.get("first_failing_check")
        ),
        "checks": checks,
        "dependency_edges": _bound_value(
            snapshot.get("dependency_edges") or [],
            limit=400,
            depth=2,
        ),
        "startup_order": _bound_value(
            snapshot.get("startup_order") or [],
            limit=600,
            depth=3,
        ),
        "state_roots": _bound_mapping(snapshot.get("state_roots"), limit=800),
        "pipewire_graph": _bound_mapping(snapshot.get("pipewire_graph"), limit=1200),
        "asr": _bound_mapping(snapshot.get("asr"), limit=1200),
        "tts": _bound_mapping(snapshot.get("tts"), limit=1200),
        "acoustic_measurement": _bound_mapping(
            snapshot.get("acoustic_measurement"),
            limit=1200,
        ),
    }


def _diagnostic_check_summary(check: object) -> dict[str, Any]:
    if not isinstance(check, dict):
        return {}
    dependencies = check.get("depends_on")
    evidence = check.get("evidence")
    return {
        "id": str(check.get("id") or ""),
        "status": str(check.get("status") or ""),
        "layer": str(check.get("layer") or ""),
        "depends_on": [
            str(item) for item in dependencies[:12] if item is not None
        ]
        if isinstance(dependencies, list)
        else [],
        "evidence": _bound_value(
            evidence if isinstance(evidence, list) else [],
            limit=800,
            depth=2,
        ),
        "repair_hint": _truncate(str(check.get("repair_hint") or ""), 320),
        "blocking_dependents": [
            str(item)
            for item in (
                check.get("blocking_dependents")
                if isinstance(check.get("blocking_dependents"), list)
                else []
            )[:12]
        ],
    }


def _diagnostic_snapshot_status(checks: list[dict[str, Any]]) -> str:
    statuses = {str(check.get("status") or "") for check in checks}
    if "error" in statuses:
        return "error"
    if "warning" in statuses:
        return "warning"
    return "ok" if checks else "unknown"


def _provided_earcon_diagnostics(
    timeline_spans: list[dict[str, Any]],
) -> dict[str, Any]:
    for span in timeline_spans:
        if str(span.get("stage") or "") != "earcon_diagnostics":
            continue
        return _bound_mapping(span.get("attrs"), limit=1000)
    return {}


def _latest_played_earcon(earcons: list[dict[str, Any]]) -> dict[str, Any]:
    for event in reversed(earcons):
        if event.get("played_at_ms") is not None and not event.get("suppressed_reason"):
            return event
    return earcons[-1] if earcons else {}


def _earcon_can_play_while_listening(event: dict[str, Any]) -> bool:
    return bool(event.get("can_play_while_listening"))


def _has_tts_or_first_response_audio(
    first_response_audio: dict[str, Any],
    timeline_spans: list[dict[str, Any]],
) -> bool:
    if bool(first_response_audio.get("scheduled")):
        return True
    return any(
        str(span.get("stage") or "") == "first_response_audio"
        for span in timeline_spans
    )


def _playback_sink_from_feedback(first_response_audio: dict[str, Any]) -> str:
    backend = str(first_response_audio.get("backend") or "")
    adapter = str(first_response_audio.get("adapter") or "")
    if backend:
        return backend
    if adapter:
        return adapter
    return "unknown"


def _display_status_summary(raw_payload: dict[str, Any]) -> dict[str, Any]:
    events = raw_payload.get("display_status_events")
    if not isinstance(events, list):
        return {"events": [], "latest": None}
    bounded = [
        _display_event_summary(event) for event in events if isinstance(event, dict)
    ][:16]
    return {"events": bounded, "latest": bounded[-1] if bounded else None}


def _display_event_summary(event: dict[str, Any]) -> dict[str, Any]:
    buttons = event.get("action_buttons")
    return {
        "id": str(event.get("id") or ""),
        "turn_id": str(event.get("turn_id") or ""),
        "state": str(event.get("state") or ""),
        "title": _truncate(str(event.get("title") or ""), 80),
        "short_text": _truncate(str(event.get("short_text") or ""), 160),
        "privacy_level": str(event.get("privacy_level") or ""),
        "progress": str(event.get("progress") or ""),
        "action_buttons": [str(button) for button in buttons if isinstance(button, str)]
        if isinstance(buttons, list)
        else [],
        "expires_at": str(event.get("expires_at") or ""),
        "source": str(event.get("source") or ""),
        "deep_link": str(event.get("deep_link") or ""),
        "created_at": str(event.get("created_at") or ""),
    }


def _search_debug(
    tools: list[dict[str, Any]],
    grounding: dict[str, Any],
    timeline_spans: list[dict[str, Any]],
) -> dict[str, Any]:
    search_tools = [tool for tool in tools if tool.get("name") == "search_web"]
    search_calls = [tool for tool in search_tools if tool.get("phase") == "call"]
    search_results = [tool for tool in search_tools if tool.get("phase") == "result"]
    search_spans = [
        span
        for span in timeline_spans
        if str(span.get("stage") or "") == "search_result"
    ]
    evidence = grounding.get("evidence") if isinstance(grounding, dict) else []
    if not isinstance(evidence, list):
        evidence = []
    results: list[dict[str, Any]] = []
    for tool in search_results:
        result = _mapping_value(tool.get("result"))
        result_items = (
            result.get("results") if isinstance(result.get("results"), list) else []
        )
        results.extend(
            {
                "title": _truncate(str(item.get("title") or ""), 160),
                "url": _truncate(str(item.get("url") or ""), 240),
                "content": _truncate(str(item.get("content") or ""), 240),
            }
            for item in result_items[:8]
            if isinstance(item, dict)
        )
    return {
        "searched": bool(search_tools),
        "gate_reason": _search_gate_reason(search_calls or search_tools),
        "queries": [
            _truncate(query, 240)
            for tool in search_calls
            if isinstance(tool.get("args"), dict)
            if (query := str((tool.get("args") or {}).get("query") or "").strip())
        ],
        "providers": [
            {
                "provider": str((tool.get("result") or {}).get("provider") or ""),
                "status": str(tool.get("status") or "ok"),
                "error": _truncate(str(tool.get("error") or ""), 240),
            }
            for tool in search_results
        ],
        "latency_ms": max(
            [_safe_int(span.get("duration_ms")) for span in search_spans] or [0]
        ),
        "result_count": len(results),
        "results": results[:8],
        "evidence_extracted": len(evidence),
        "polluted_result": any(
            isinstance(item, dict) and item.get("evidence_type") != "quote_origin"
            for item in evidence
        ),
        "timeout": any(
            "timeout" in str(tool.get("error") or "").lower() for tool in search_tools
        ),
        "cache_hit": any(
            bool(_mapping_value(tool.get("result")).get("cache_hit"))
            for tool in search_results
        ),
    }


def _search_gate_summary(
    first_response: dict[str, Any],
    search_debug: dict[str, Any],
) -> dict[str, Any]:
    searched = bool(search_debug.get("searched"))
    task_type = str(first_response.get("task_type") or "")
    reason = str(first_response.get("reason") or search_debug.get("gate_reason") or "")
    decision = "searched" if searched else "not_searched"
    if _is_weather_task_type(task_type) and not searched:
        decision = "local_weather_first"
    elif reason == "explicit_or_current_search":
        decision = (
            "external_search_requested" if searched else "external_search_pending"
        )
    return {
        "task_type": task_type,
        "decision": decision,
        "reason": reason,
        "searched": searched,
        "queries": list(search_debug.get("queries") or [])[:4],
    }


def _weather_context_path(
    first_response: dict[str, Any],
    tools: list[dict[str, Any]],
    timeline_spans: list[dict[str, Any]],
    search_debug: dict[str, Any],
) -> dict[str, Any]:
    task_type = str(first_response.get("task_type") or "")
    live_context_calls = [
        tool
        for tool in tools
        if tool.get("phase") == "call" and tool.get("name") == "GetLiveContext"
    ]
    live_context_results = [
        tool
        for tool in tools
        if tool.get("phase") == "result" and tool.get("name") == "GetLiveContext"
    ]
    stages = {str(span.get("stage") or "") for span in timeline_spans}
    suppressed_reasons = [
        str(_mapping_value(span.get("attrs")).get("reason") or "")
        for span in timeline_spans
        if str(span.get("stage") or "") == "tool_call_suppressed"
    ]
    local_state_cache = "local_state_cache" in stages
    weather_entity = "weather_entity" in stages
    search_fallback = bool(search_debug.get("searched"))
    if not _is_weather_task_type(task_type) and not (weather_entity or search_fallback):
        return {
            "active": False,
            "task_type": task_type,
            "path": "not_weather",
            "ignored_get_live_context_calls": len(live_context_calls),
            "ignored_get_live_context_results": len(live_context_results),
        }

    if local_state_cache:
        path = "local_state_cache"
    elif weather_entity:
        path = "weather_entity"
    elif live_context_calls or live_context_results:
        path = "GetLiveContext"
    elif search_fallback:
        path = "search_fallback"
    else:
        path = "no_weather_context"

    return {
        "active": True,
        "task_type": task_type,
        "path": path,
        "local_state_cache": local_state_cache,
        "weather_entity": weather_entity,
        "get_live_context_calls": len(live_context_calls),
        "get_live_context_results": len(live_context_results),
        "search_fallback": search_fallback,
        "duplicate_live_context_suppressed": "duplicate_live_context"
        in suppressed_reasons,
    }


def _is_weather_task_type(task_type: str) -> bool:
    return task_type in {
        "weather_query",
        "outdoor_current_weather_query",
        "weather_forecast_query",
    }


def _actions_summary(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    calls = {
        str(tool.get("tool_call_id") or ""): tool
        for tool in tools
        if tool.get("phase") == "call"
    }
    for tool in tools:
        name = str(tool.get("name") or "")
        if not name.startswith(_ACTION_TOOL_PREFIXES):
            continue
        args = tool.get("args") if isinstance(tool.get("args"), dict) else {}
        result = tool.get("result") if isinstance(tool.get("result"), dict) else {}
        call = calls.get(str(tool.get("tool_call_id") or ""), tool)
        call_args = call.get("args") if isinstance(call.get("args"), dict) else args
        actions.append(
            {
                "tool": name,
                "phase": str(tool.get("phase") or ""),
                "tool_call_id": str(tool.get("tool_call_id") or ""),
                "area": str(call_args.get("area") or ""),
                "domain": str(
                    call_args.get("domain") or call_args.get("entity_domain") or ""
                ),
                "entity": str(
                    call_args.get("entity_id") or call_args.get("name") or ""
                ),
                "policy": "blocked" if tool.get("status") == "error" else "allowed",
                "risk": _risk_from_action(name, call_args),
                "status": str(tool.get("status") or "ok"),
                "error": _truncate(str(tool.get("error") or ""), 240),
                "state_diff": _bound_mapping(result.get("state_diff"), limit=1200),
                "unintended_state_change": bool(result.get("unintended_state_change")),
            }
        )
    return actions[:12]


def _verifier_mode(raw_payload: dict[str, Any], grounding: dict[str, Any]) -> str:
    verifier = grounding.get("verifier") if isinstance(grounding, dict) else {}
    if not isinstance(verifier, dict):
        return "disabled"
    if verifier.get("audit_only"):
        return "audit_only"
    if verifier.get("mode") == "model":
        return "blocking"
    raw_verifier = raw_payload.get("verifier")
    if isinstance(raw_verifier, dict) and raw_verifier.get("mode") == "audit_only":
        return "audit_only"
    return "disabled"


def _search_gate_reason(search_tools: list[dict[str, Any]]) -> str:
    if not search_tools:
        return "not_searched"
    if any((tool.get("args") or {}).get("query") for tool in search_tools):
        return "tool_call"
    return "unknown"


def _risk_from_action(name: str, args: dict[str, Any]) -> str:
    domain = str(args.get("domain") or args.get("entity_domain") or "")
    text = f"{name} {args}"
    if domain in {"lock", "alarm_control_panel", "cover", "valve"}:
        return "high"
    if any(keyword in text for keyword in ("门锁", "报警", "全屋", "热水器", "烤箱")):
        return "high"
    return "low"


def _debug_flags(
    context: dict[str, Any],
    tools: list[dict[str, Any]],
    grounding: dict[str, Any],
    actions: list[dict[str, Any]],
) -> dict[str, Any]:
    evidence = grounding.get("evidence") if isinstance(grounding, dict) else []
    if not isinstance(evidence, list):
        evidence = []
    first_response = _mapping_value(context.get("first_response"))
    route = _mapping_value(context.get("route"))
    verifier_mode = str(context.get("verifier_mode") or "")
    return {
        "search": any(tool.get("name") == "search_web" for tool in tools),
        "deep_route": str(route.get("kind") or "") == "deep"
        or bool(route.get("async_deep_task")),
        "deep_verifier_waited": verifier_mode == "blocking",
        "high_risk": str(first_response.get("task_type") or "") == "high_risk"
        or any(action.get("risk") == "high" for action in actions),
        "final_modified_by_grounding": bool(
            grounding.get("final_modified_by_grounding")
        ),
        "polluted_evidence_present": any(
            item.get("evidence_type") != "quote_origin"
            for item in evidence
            if isinstance(item, dict)
        ),
        "polluted_evidence_used": any(
            item.get("evidence_type") != "quote_origin"
            and bool(item.get("included_in_final"))
            for item in evidence
            if isinstance(item, dict)
        ),
        "tool_error": any(
            tool.get("status") == "error" or tool.get("error") for tool in tools
        ),
    }


def _error_summary(
    raw_payload: dict[str, Any],
    tools: list[dict[str, Any]],
    grounding: dict[str, Any],
    timeline: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = [
        {
            "type": "tool_error",
            "stage": str(tool.get("name") or "tool"),
            "message": _truncate(str(tool.get("error") or "tool error"), 240),
        }
        for tool in tools
        if tool.get("status") == "error" or tool.get("error")
    ]
    route = (
        raw_payload.get("route") if isinstance(raw_payload.get("route"), dict) else {}
    )
    errors.extend(
        [
            {
                "type": "provider_error",
                "stage": str(attempt.get("provider") or "provider"),
                "message": _truncate(str(attempt.get("error") or ""), 240),
            }
            for attempt in route.get("provider_attempts") or []
            if isinstance(attempt, dict) and attempt.get("status") == "error"
        ]
    )
    status = str(grounding.get("status") or "")
    if status in {"no_answer", "no_evidence", "unsupported", "verifier_error"}:
        errors.append(
            {
                "type": "grounding_error",
                "stage": "grounding",
                "message": _truncate(str(grounding.get("reason") or status), 240),
            }
        )
    for event in timeline:
        if not isinstance(event, dict) or event.get("status") != "error":
            continue
        attrs = event.get("attrs") if isinstance(event.get("attrs"), dict) else {}
        errors.append(
            {
                "type": "timeline_error",
                "stage": str(event.get("stage") or ""),
                "message": _truncate(json.dumps(attrs, ensure_ascii=False), 240),
            }
        )
    return errors[:12]


def _append_pseudo_tool_events(
    tools: list[dict[str, Any]], raw_payload: dict[str, Any]
) -> None:
    if _has_memory_context(raw_payload):
        tools.append({"name": "memory", "phase": "context", "status": "ok"})
    grounding = (
        raw_payload.get("grounding")
        if isinstance(raw_payload.get("grounding"), dict)
        else {}
    )
    verifier = grounding.get("verifier") if isinstance(grounding, dict) else {}
    if isinstance(verifier, dict) and verifier.get("mode"):
        tools.append(
            {
                "name": "grounding_verifier",
                "phase": str(verifier.get("mode") or ""),
                "status": "error"
                if grounding.get("status") == "verifier_error"
                else "ok",
                "error": str(grounding.get("reason") or ""),
            }
        )


def _has_memory_context(raw_payload: dict[str, Any]) -> bool:
    for message in raw_payload.get("messages") or []:
        if not isinstance(message, dict) or message.get("role") != "system":
            continue
        content = str(message.get("content") or "")
        if "本地记忆" in content or "最近上下文" in content:
            return True
    return False


def _parse_json_mapping(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return _bound_mapping(value, limit=800)
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        parsed = json.loads(value)
    except ValueError:
        return {"text": _truncate(value, 400)}
    return _bound_mapping(parsed, limit=800) if isinstance(parsed, dict) else {}


def _bound_mapping(value: object, *, limit: int) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    bounded: dict[str, Any] = {}
    for key, item in list(value.items())[:24]:
        bounded[str(key)] = _bound_value(item, limit=limit, depth=3)
    return bounded


def _bound_value(value: object, *, limit: int, depth: int) -> object:
    if isinstance(value, str):
        return _truncate(value, limit)
    if isinstance(value, int | float | bool) or value is None:
        return value
    if depth <= 0:
        return _truncate(json.dumps(value, ensure_ascii=False, default=str), limit)
    if isinstance(value, dict):
        return {
            str(key): _bound_value(item, limit=limit, depth=depth - 1)
            for key, item in list(value.items())[:12]
        }
    if isinstance(value, list | tuple):
        return [_bound_value(item, limit=limit, depth=depth - 1) for item in value[:24]]
    return _truncate(json.dumps(value, ensure_ascii=False, default=str), limit)


def _mapping_value(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_int(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _bounded_int(value: object, *, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def _parse_time(value: str, default: datetime) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return default
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed
