"""Read-only projections for programmatic Voice Harness inspection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class RunQuery:
    """Validated filters for one newest-first run page."""

    limit: int
    cursor: str | None = None
    since: datetime | None = None
    status: str | None = None
    route: str | None = None
    provider: str | None = None
    contains: str | None = None
    has_error: bool | None = None


def run_summary(record: dict[str, Any]) -> dict[str, Any]:
    """Return the bounded fields needed to choose a run for investigation."""
    route = record.get("route") if isinstance(record.get("route"), dict) else {}
    turn = (
        record.get("turn_summary")
        if isinstance(record.get("turn_summary"), dict)
        else {}
    )
    errors = record.get("errors") if isinstance(record.get("errors"), list) else []
    tools = turn.get("tools") if isinstance(turn.get("tools"), list) else []
    return {
        "schema_version": int(record.get("schema_version") or 0),
        "run_id": str(record.get("run_id") or record.get("id") or ""),
        "created_at": str(record.get("created_at") or ""),
        "conversation_id": str(record.get("conversation_id") or ""),
        "status": str(record.get("status") or ""),
        "user_text": str(record.get("user_text") or ""),
        "assistant_text": str(record.get("assistant_text") or ""),
        "final_speech_text": str(record.get("final_speech_text") or ""),
        "route": {
            "kind": str(route.get("kind") or turn.get("route") or ""),
            "model": str(route.get("model") or ""),
            "provider": str(route.get("provider") or ""),
        },
        "task_family": str(turn.get("task_family") or ""),
        "task_type": str(turn.get("task_type") or ""),
        "latency_ms": int(record.get("latency_ms") or 0),
        "tools": [str(tool) for tool in tools[:20]],
        "error_count": len(errors),
        "error_types": sorted(
            {
                str(error.get("type") or "unknown")
                for error in errors
                if isinstance(error, dict)
            }
        ),
        "has_raw_payload": isinstance(record.get("raw_payload"), dict),
    }


def query_runs(records: list[dict[str, Any]], query: RunQuery) -> dict[str, Any]:
    """Filter newest-first trace records and return one cursor page."""
    needle = (query.contains or "").casefold()
    filtered = []
    for record in records:
        summary = run_summary(record)
        if query.since is not None:
            created_at = _parse_datetime(summary["created_at"])
            if created_at is None or created_at < query.since:
                continue
        if query.status and summary["status"] != query.status:
            continue
        if query.route and summary["route"]["kind"] != query.route:
            continue
        if query.provider and summary["route"]["provider"] != query.provider:
            continue
        if (
            query.has_error is not None
            and (summary["error_count"] > 0) != query.has_error
        ):
            continue
        if (
            needle
            and needle
            not in "\n".join(
                (
                    summary["user_text"],
                    summary["assistant_text"],
                    summary["final_speech_text"],
                )
            ).casefold()
        ):
            continue
        filtered.append(summary)

    start = 0
    if query.cursor:
        positions = [
            index
            for index, item in enumerate(filtered)
            if item["run_id"] == query.cursor
        ]
        if not positions:
            raise ValueError("cursor does not match the filtered run set")
        start = positions[0] + 1
    page = filtered[start : start + query.limit]
    has_more = start + len(page) < len(filtered)
    return {
        "records": page,
        "has_more": has_more,
        "next_cursor": page[-1]["run_id"] if has_more and page else None,
    }


def query_events(
    record: dict[str, Any],
    *,
    event_types: tuple[str, ...] = (),
    source: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """Return matching append-only events from one run."""
    events = record.get("event_stream")
    if not isinstance(events, list):
        return []
    return [
        event
        for event in events
        if isinstance(event, dict)
        and _matches_event_type(str(event.get("event_type") or ""), event_types)
        and (not source or str(event.get("source") or "") == source)
        and (not status or _event_status(event) == status)
    ]


def compare_runs(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """Compare investigation-relevant outcomes without returning both full records."""
    left_summary = run_summary(left)
    right_summary = run_summary(right)
    left_events = _event_types(left)
    right_events = _event_types(right)
    left_tools = set(left_summary["tools"])
    right_tools = set(right_summary["tools"])
    left_errors = set(left_summary["error_types"])
    right_errors = set(right_summary["error_types"])
    return {
        "left_run_id": left_summary["run_id"],
        "right_run_id": right_summary["run_id"],
        "status": {"left": left_summary["status"], "right": right_summary["status"]},
        "route": {
            "left": left_summary["route"],
            "right": right_summary["route"],
            "changed": left_summary["route"] != right_summary["route"],
        },
        "latency_ms": {
            "left": left_summary["latency_ms"],
            "right": right_summary["latency_ms"],
            "delta": right_summary["latency_ms"] - left_summary["latency_ms"],
        },
        "reply_changed": (
            left_summary["assistant_text"] != right_summary["assistant_text"]
        ),
        "tools": {
            "added": sorted(right_tools - left_tools),
            "removed": sorted(left_tools - right_tools),
        },
        "error_types": {
            "added": sorted(right_errors - left_errors),
            "removed": sorted(left_errors - right_errors),
        },
        "event_types": {
            "added": sorted(right_events - left_events),
            "removed": sorted(left_events - right_events),
        },
    }


def _matches_event_type(value: str, patterns: tuple[str, ...]) -> bool:
    if not patterns:
        return True
    return any(
        value.startswith(pattern[:-1]) if pattern.endswith("*") else value == pattern
        for pattern in patterns
    )


def _event_types(record: dict[str, Any]) -> set[str]:
    events = record.get("event_stream")
    if not isinstance(events, list):
        return set()
    return {
        str(event.get("event_type") or "")
        for event in events
        if isinstance(event, dict) and event.get("event_type")
    }


def _event_status(event: dict[str, Any]) -> str:
    direct = event.get("status")
    if direct:
        return str(direct)
    payload = event.get("payload")
    return str(payload.get("status") or "") if isinstance(payload, dict) else ""


def _parse_datetime(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None
