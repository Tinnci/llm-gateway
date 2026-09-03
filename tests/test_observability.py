"""Tests for agent-readable Voice Harness projections."""

from datetime import UTC, datetime

import pytest

from custom_components.llm_gateway.observability import (
    RunQuery,
    compare_runs,
    query_events,
    query_runs,
    run_summary,
)


def _record(  # noqa: PLR0913 - compact factory makes comparison cases readable.
    run_id: str,
    *,
    created_at: str,
    status: str = "complete",
    route: str = "fast",
    latency_ms: int = 100,
    reply: str = "好了。",
) -> dict:
    return {
        "schema_version": 1,
        "run_id": run_id,
        "created_at": created_at,
        "conversation_id": f"conversation-{run_id}",
        "status": status,
        "user_text": "打开客厅灯",
        "assistant_text": reply,
        "final_speech_text": reply,
        "route": {"kind": route, "model": "model", "provider": "primary"},
        "turn_summary": {
            "task_family": "home_control",
            "task_type": "device_action",
            "tools": ["HassTurnOn"],
        },
        "latency_ms": latency_ms,
        "errors": [] if status == "complete" else [{"type": "provider_error"}],
        "event_stream": [
            {
                "event_id": f"event-{run_id}",
                "event_type": "gateway.route.selected",
                "source": "llm_gateway",
                "payload": {"status": "ok"},
            }
        ],
    }


def test_run_summary_is_small_and_reply_focused() -> None:
    summary = run_summary(_record("run-1", created_at="2026-09-02T10:00:00+00:00"))

    assert summary["run_id"] == "run-1"
    assert summary["assistant_text"] == "好了。"
    assert summary["tools"] == ["HassTurnOn"]
    assert "event_stream" not in summary


def test_query_runs_filters_and_pages_with_run_id_cursor() -> None:
    records = [
        _record("run-3", created_at="2026-09-02T12:00:00+00:00", status="error"),
        _record("run-2", created_at="2026-09-02T11:00:00+00:00"),
        _record("run-1", created_at="2026-09-02T10:00:00+00:00"),
    ]

    first = query_runs(records, RunQuery(limit=1, has_error=False))
    assert first["records"][0]["run_id"] == "run-2"
    assert first["next_cursor"] == "run-2"
    second = query_runs(records, RunQuery(limit=1, has_error=False, cursor="run-2"))
    assert second["records"][0]["run_id"] == "run-1"
    assert second["has_more"] is False

    recent = query_runs(
        records,
        RunQuery(
            limit=10,
            since=datetime(2026, 9, 2, 11, 30, tzinfo=UTC),
        ),
    )
    assert [row["run_id"] for row in recent["records"]] == ["run-3"]

    with pytest.raises(ValueError, match="cursor"):
        query_runs(records, RunQuery(limit=1, cursor="missing"))


def test_query_runs_exposes_and_filters_harness_outcome() -> None:
    record = _record("run-loop", created_at="2026-09-02T12:00:00+00:00")
    record["turn_summary"]["matched_capability"] = "device_state_query"
    record["route"]["harness_loop"] = {
        "name": "local_live_context",
        "step_count": 1,
        "total_duration_ms": 18,
        "final_phase": "broad_live_context",
        "stop_reason": "requested_target_missing",
        "outcome_verdict": {
            "answerable": False,
            "target_covered": False,
        },
    }

    [summary] = query_runs(
        [record],
        RunQuery(
            limit=10,
            capability="device_state_query",
            outcome="not_answered",
            failure_stage="requested_target_missing",
        ),
    )["records"]

    assert summary["outcome"] == "not_answered"
    assert summary["failure_stage"] == "requested_target_missing"
    assert summary["harness_loop"]["target_covered"] is False
    assert summary["harness_loop"]["total_duration_ms"] == 18
    assert summary["harness_loop"]["final_phase"] == "broad_live_context"


def test_run_summary_uses_route_terminal_outcome_for_local_clarification() -> None:
    summary = run_summary(
        {
            "run_id": "clarify-1",
            "status": "complete",
            "route": {
                "kind": "local_multi_intent_clarify",
                "terminal_outcome": "clarify",
                "outcome_verdict": {
                    "answerable": False,
                    "reason": "requires_separate_turns",
                },
            },
        }
    )

    assert summary["terminal_outcome"] == "clarify"
    assert summary["outcome"] == "not_answered"
    assert summary["failure_stage"] == "requires_separate_turns"


def test_event_query_and_run_comparison_are_bounded() -> None:
    left = _record(
        "left",
        created_at="2026-09-02T10:00:00+00:00",
        latency_ms=100,
    )
    right = _record(
        "right",
        created_at="2026-09-02T11:00:00+00:00",
        latency_ms=180,
        route="mid",
        reply="已打开。",
    )
    right["event_stream"].append(
        {
            "event_id": "event-tool",
            "event_type": "gateway.tool.completed",
            "source": "llm_gateway",
            "payload": {"status": "ok"},
        }
    )

    events = query_events(right, event_types=("gateway.tool.*",), status="ok")
    assert [event["event_id"] for event in events] == ["event-tool"]

    comparison = compare_runs(left, right)
    assert comparison["route"]["changed"] is True
    assert comparison["latency_ms"]["delta"] == 80
    assert comparison["reply_changed"] is True
    assert comparison["event_types"]["added"] == ["gateway.tool.completed"]

    right["event_stream"].append(
        {
            "event_id": "event-malformed",
            "event_type": "gateway.tool.failed",
            "source": "llm_gateway",
            "payload": "legacy payload",
        }
    )
    assert query_events(right, status="ok") == right["event_stream"][:2]
