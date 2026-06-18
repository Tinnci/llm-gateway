"""Compressed diagnostic trace storage for Voice Harness runs."""

from __future__ import annotations

import base64
import json
import zlib
from dataclasses import dataclass
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

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

SUMMARY_TEXT_LIMIT = 1200
RAW_TEXT_LIMIT = 12000
TRACE_ENCODING = "json+zlib+base64"
_SECRET_MARKERS = ("api_key", "apikey", "authorization", "password", "secret", "token")


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


class TraceStore:
    """Persistent, bounded diagnostic traces for admin debugging."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
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

        record = {
            "id": ulid.ulid_now(),
            "created_at": datetime.now(UTC).isoformat(),
            "conversation_id": turn.conversation_id or "",
            "user_text": _truncate(turn.user_text, SUMMARY_TEXT_LIMIT),
            "assistant_text": _truncate(turn.assistant_text, SUMMARY_TEXT_LIMIT),
            "route": {
                "kind": str(turn.route.get("kind") or ""),
                "model": str(turn.route.get("model") or ""),
                "max_tokens": turn.route.get("max_tokens"),
                "timeout_s": turn.route.get("timeout_s"),
            },
            "latency_ms": turn.latency_ms,
            "status": turn.status,
            "tools": _tool_summary(turn.raw_payload),
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
    panel_record = {
        key: value for key, value in record.items() if key != "raw_payload"
    }
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
    for message in raw_payload.get("messages") or []:
        if not isinstance(message, dict):
            continue
        for call in message.get("tool_calls") or []:
            function = call.get("function") or {}
            tools.append({"name": str(function.get("name") or ""), "phase": "call"})
        if message.get("role") == "tool":
            tools.append(
                {
                    "name": str(message.get("name") or ""),
                    "phase": "result",
                    "tool_call_id": str(message.get("tool_call_id") or ""),
                }
            )
    return [tool for tool in tools if tool.get("name") or tool.get("tool_call_id")]


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
