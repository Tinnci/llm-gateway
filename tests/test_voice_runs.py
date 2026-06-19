"""Tests for recent voice run timelines."""

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


def test_voice_run_recorder_reports_running_stage() -> None:
    recorder = VoiceRunRecorder(limit=2)

    run_id = recorder.start(conversation_id="conv-1", user_text="今天天气。")
    recorder.mark(run_id, "llm_iteration_start", attrs={"iteration": 1})

    [run] = recorder.snapshot()

    assert run["id"] == run_id
    assert run["status"] == "running"
    assert run["last_active_stage"] == "llm_iteration_start"
    assert run["running_duration_ms"] >= 0


def test_voice_run_recorder_prunes_old_runs() -> None:
    recorder = VoiceRunRecorder(limit=1)

    first = recorder.start(conversation_id=None, user_text="first")
    second = recorder.start(conversation_id=None, user_text="second")

    assert [run["id"] for run in recorder.snapshot()] == [second]
    assert recorder.timeline(first) == []
