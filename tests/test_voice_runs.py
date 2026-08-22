"""Tests for recent voice run timelines."""

from datetime import datetime

from custom_components.llm_gateway.voice_runs import VoiceRunRecorder


def test_voice_run_recorder_records_timeline() -> None:
    recorder = VoiceRunRecorder(limit=2)

    run_id = recorder.start(conversation_id="conv-1", user_text="打开灯")
    recorder.mark(run_id, "route_selected", attrs={"route": "fast"})
    timeline = recorder.finish(
        run_id,
        status="complete",
        route="fast",
        provider="primary",
        latency_ms=42,
    )

    snapshot = recorder.snapshot()

    assert snapshot[0]["id"] == run_id
    assert snapshot[0]["status"] == "complete"
    assert snapshot[0]["route"] == "fast"
    assert snapshot[0]["last_active_stage"] == "complete"
    assert snapshot[0]["running_duration_ms"] == 42
    assert [event["stage"] for event in timeline] == [
        "received",
        "route_selected",
        "complete",
    ]
    assert [event["source_sequence"] for event in timeline] == [0, 1, 2]
    assert all(event["turn_id"] == run_id for event in timeline)
    assert timeline[0]["caused_by"] == ""
    assert timeline[1]["caused_by"] == timeline[0]["event_id"]
    assert timeline[2]["caused_by"] == timeline[1]["event_id"]
    assert timeline[1]["event_type"] == "gateway.route.selected"
    assert timeline[1]["source"] == "llm-gateway"
    assert timeline[1]["privacy"] == "trace_safe"
    assert timeline[1]["payload"] == {"status": "ok", "route": "fast"}
    assert datetime.fromisoformat(timeline[1]["occurred_at"]).tzinfo is not None
    assert timeline[1]["monotonic_ms"] == timeline[1]["t_ms"]


def test_voice_run_recorder_reports_running_stage() -> None:
    recorder = VoiceRunRecorder(limit=2)

    run_id = recorder.start(conversation_id="conv-1", user_text="今天天气。")
    recorder.mark(run_id, "llm_iteration_start", attrs={"iteration": 1})

    [run] = recorder.snapshot()

    assert run["id"] == run_id
    assert run["status"] == "running"
    assert run["last_active_stage"] == "llm_iteration_start"
    assert run["running_duration_ms"] >= 0


def test_voice_run_recorder_normalizes_causal_event_types() -> None:
    recorder = VoiceRunRecorder()
    turn_id = recorder.start(conversation_id="conv-1", user_text="旧请求")
    recorder.mark(turn_id, "turn_cancelled")
    recorder.mark(turn_id, "stale_result_discarded")
    recorder.mark(turn_id, "barge_in_requested")

    events = recorder.timeline(turn_id)

    assert [event["event_type"] for event in events[-3:]] == [
        "gateway.turn.superseded",
        "gateway.result.late_dropped",
        "playback.interrupt.requested",
    ]


def test_voice_run_recorder_expires_stale_running_runs(monkeypatch) -> None:
    recorder = VoiceRunRecorder(limit=2)
    monkeypatch.setattr(
        "custom_components.llm_gateway.voice_runs.time.time",
        lambda: 1000.0,
    )
    run_id = recorder.start(conversation_id="conv-1", user_text="打开空调")
    recorder.mark(run_id, "first_response")

    monkeypatch.setattr(
        "custom_components.llm_gateway.voice_runs.time.time",
        lambda: 1000.0 + 601,
    )

    [run] = recorder.snapshot()

    assert run["id"] == run_id
    assert run["status"] == "stale"
    assert run["last_active_stage"] == "stale_expired"
    assert run["last_active_status"] == "stale"
    assert run["running_duration_ms"] == 601000
    assert run["events"][-1]["attrs"]["reason"] == (
        "run_exceeded_observable_voice_budget"
    )


def test_voice_run_recorder_prunes_old_runs() -> None:
    recorder = VoiceRunRecorder(limit=1)

    first = recorder.start(conversation_id=None, user_text="first")
    second = recorder.start(conversation_id=None, user_text="second")

    assert [run["id"] for run in recorder.snapshot()] == [second]
    assert recorder.timeline(first) == []
