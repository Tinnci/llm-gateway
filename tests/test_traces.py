"""Tests for compressed diagnostic traces."""

from __future__ import annotations

from custom_components.llm_gateway.const import (
    CONF_DIAGNOSTIC_TRACES,
    CONF_TRACE_INCLUDE_RAW_MESSAGES,
    CONF_TRACE_MAX_RUNS,
    CONF_TRACE_RETENTION_HOURS,
)
from custom_components.llm_gateway.traces import TraceStore, TraceTurn


async def test_trace_store_is_disabled_by_default(hass):
    store = TraceStore(hass, "entry-disabled")
    await store.async_load()

    await store.async_record_turn(
        {},
        TraceTurn(
            conversation_id="conv-1",
            user_text="打开客厅灯",
            assistant_text="好了。",
            route={"kind": "fast", "model": "m"},
            latency_ms=42,
            status="ok",
            raw_payload={"messages": []},
        ),
    )

    assert store.snapshot()["records"] == []


async def test_trace_store_records_bounded_summary_without_raw(hass):
    store = TraceStore(hass, "entry-summary")
    await store.async_load()

    await store.async_record_turn(
        {
            CONF_DIAGNOSTIC_TRACES: True,
            CONF_TRACE_MAX_RUNS: 2,
            CONF_TRACE_RETENTION_HOURS: 24,
        },
        TraceTurn(
            conversation_id="conv-1",
            user_text="查一下卧室温度",
            assistant_text="卧室现在 24 度。",
            route={"kind": "fast", "model": "fast-model", "max_tokens": 512},
            latency_ms=88,
            status="ok",
            timeline=[{"stage": "received", "t_ms": 0, "status": "ok", "attrs": {}}],
            raw_payload={
                "grounding": {
                    "status": "repaired",
                    "candidates": ["诗经", "关雎"],
                    "repairs": [{"from": "诗经·关关", "to": "诗经·关雎"}],
                },
                "messages": [{"role": "user", "content": "查一下卧室温度"}],
            },
        ),
    )

    snapshot = store.snapshot()
    record = snapshot["records"][0]
    assert record["conversation_id"] == "conv-1"
    assert record["user_text"] == "查一下卧室温度"
    assert record["assistant_text"] == "卧室现在 24 度。"
    assert record["route"]["kind"] == "fast"
    assert record["timeline"][0]["stage"] == "received"
    assert record["grounding"]["status"] == "repaired"
    assert record["grounding"]["repairs"] == [{"from": "诗经·关关", "to": "诗经·关雎"}]
    assert "raw_payload" not in record
    assert snapshot["storage"]["records"] == 1
    assert snapshot["storage"]["compressed_bytes"] == 0


async def test_trace_timeline_spans_keep_structured_inventory_attrs(hass):
    store = TraceStore(hass, "entry-inventory")
    await store.async_load()

    await store.async_record_turn(
        {
            CONF_DIAGNOSTIC_TRACES: True,
            CONF_TRACE_MAX_RUNS: 2,
            CONF_TRACE_RETENTION_HOURS: 24,
        },
        TraceTurn(
            conversation_id="conv-inventory",
            user_text="你能看到哪些设备？",
            assistant_text="我能看到已暴露给助手的设备。",
            route={
                "kind": "local_static_context",
                "model": "device_inventory_renderer",
            },
            latency_ms=35,
            status="complete",
            timeline=[
                {
                    "stage": "local_inventory_render",
                    "t_ms": 10,
                    "status": "ok",
                    "attrs": {
                        "task_type": "device_inventory_query",
                        "llm_used": False,
                        "tools_used": [],
                        "entities": [
                            {
                                "name": "客厅灯",
                                "domain": "light",
                                "areas": ["客厅"],
                            }
                        ],
                    },
                }
            ],
            raw_payload={"messages": []},
        ),
    )

    attrs = store.snapshot()["records"][0]["timeline_spans"][0]["attrs"]
    assert attrs["tools_used"] == []
    assert attrs["entities"][0]["name"] == "客厅灯"
    assert attrs["entities"][0]["areas"] == ["客厅"]


async def test_trace_store_compresses_and_redacts_raw_payload(hass):
    store = TraceStore(hass, "entry-raw")
    await store.async_load()

    await store.async_record_turn(
        {
            CONF_DIAGNOSTIC_TRACES: True,
            CONF_TRACE_INCLUDE_RAW_MESSAGES: True,
            CONF_TRACE_MAX_RUNS: 3,
            CONF_TRACE_RETENTION_HOURS: 24,
        },
        TraceTurn(
            conversation_id="conv-raw",
            user_text="打开前门",
            assistant_text="要打开前门门锁吗？请确认。",
            route={"kind": "fast", "model": "fast-model"},
            latency_ms=120,
            status="ok",
            raw_payload={
                "api_key": "should-not-be-stored",
                "headers": {"authorization": "Bearer secret"},
                "messages": [
                    {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": "call-1",
                                "function": {
                                    "name": "HassTurnOn",
                                    "arguments": '{"domain":"lock"}',
                                },
                            },
                        ],
                    },
                    {
                        "role": "tool",
                        "name": "HassTurnOn",
                        "tool_call_id": "call-1",
                        "content": '{"error":"confirmation required"}',
                    },
                ],
            },
        ),
    )

    record = store.snapshot()["records"][0]
    assert record["raw_payload_meta"]["encoding"] == "json+zlib+base64"
    assert record["raw_payload_meta"]["compressed_bytes"] > 0
    assert record["raw_payload"]["api_key"] == "[redacted]"
    assert record["raw_payload"]["headers"]["authorization"] == "[redacted]"
    assert record["tools"][0]["name"] == "HassTurnOn"
    assert record["tools"][0]["phase"] == "call"
    assert record["tools"][0]["args"] == {"domain": "lock"}
    assert record["tools"][1]["phase"] == "result"
    assert record["tools"][1]["tool_call_id"] == "call-1"
    assert record["actions"][0]["risk"] == "high"
    assert record["debug_flags"]["high_risk"]


async def test_trace_store_prunes_to_configured_run_limit(hass):
    store = TraceStore(hass, "entry-prune")
    await store.async_load()
    options = {
        CONF_DIAGNOSTIC_TRACES: True,
        CONF_TRACE_MAX_RUNS: 2,
        CONF_TRACE_RETENTION_HOURS: 24,
    }

    for index in range(3):
        await store.async_record_turn(
            options,
            TraceTurn(
                conversation_id=f"conv-{index}",
                user_text=f"user {index}",
                assistant_text=f"assistant {index}",
                route={"kind": "fast", "model": "m"},
                latency_ms=10,
                status="ok",
                raw_payload={"messages": []},
            ),
        )

    records = store.snapshot()["records"]
    assert [record["conversation_id"] for record in records] == ["conv-2", "conv-1"]


async def test_trace_store_serializes_debug_run_detail(hass):
    store = TraceStore(hass, "entry-debug-detail")
    await store.async_load()

    await store.async_record_turn(
        {
            CONF_DIAGNOSTIC_TRACES: True,
            CONF_TRACE_MAX_RUNS: 30,
            CONF_TRACE_RETENTION_HOURS: 24,
        },
        TraceTurn(
            conversation_id="conv-search",
            user_text="查一下这个错误码",
            assistant_text="我没查到可靠结果。",
            route={
                "kind": "mid",
                "model": "mid-model",
                "provider_attempts": [
                    {
                        "provider": "primary",
                        "model": "mid-model",
                        "status": "complete",
                        "latency_ms": 1200,
                    }
                ],
            },
            latency_ms=1800,
            status="complete",
            timeline=[
                {
                    "stage": "received",
                    "t_ms": 0,
                    "status": "ok",
                    "attrs": {},
                },
                {
                    "stage": "first_response",
                    "t_ms": 40,
                    "status": "ok",
                    "attrs": {
                        "task_type": "search_needed",
                        "cue": "search",
                        "spoken_hint": "我查一下。",
                    },
                },
                {
                    "stage": "search_result",
                    "t_ms": 1400,
                    "status": "error",
                    "attrs": {"name": "search_web", "error": "TimeoutError"},
                },
                {
                    "stage": "complete",
                    "t_ms": 1800,
                    "status": "complete",
                    "attrs": {},
                },
            ],
            raw_payload={
                "input": {
                    "text": "查一下这个错误码",
                    "conversation_id": "conv-search",
                    "language": "zh-CN",
                },
                "speech": {"final": "我没查到可靠结果。", "tts_cleaned": True},
                "tool_events": [
                    {
                        "phase": "call",
                        "tool_call_id": "search-1",
                        "name": "search_web",
                        "external": True,
                        "args": {"query": "E7 错误码"},
                    },
                    {
                        "phase": "result",
                        "tool_call_id": "search-1",
                        "name": "search_web",
                        "status": "error",
                        "error": "TimeoutError",
                        "result": {"error": "TimeoutError"},
                    },
                ],
                "grounding": {
                    "status": "verifier_error",
                    "reason": "verifier_returned_non_json",
                    "evidence": [
                        {
                            "evidence_id": "ev-1",
                            "source_id": "https://example.test",
                            "evidence_type": "quote_origin",
                            "text": "typed evidence",
                            "included_in_final": False,
                        }
                    ],
                    "verifier": {"mode": "model", "raw_excerpt": "not json"},
                },
                "earcon_events": [
                    {
                        "turn_id": "conv-search",
                        "earcon_name": "search",
                        "semantic_state": "searching",
                        "scheduled_at_ms": 40,
                        "played_at_ms": 40,
                        "duration_ms": 194,
                        "priority": 50,
                        "can_play_while_listening": False,
                        "quiet_hours_behavior": "attenuate",
                        "trace_event_name": "earcon_search",
                        "suppressed_reason": "",
                        "volume_profile": "normal",
                        "microphone_hot": False,
                        "quiet_hours_applied": False,
                    }
                ],
                "display_status_events": [
                    {
                        "id": "display-1",
                        "turn_id": "conv-search",
                        "state": "searching",
                        "title": "Searching",
                        "short_text": "我查一下。",
                        "privacy_level": "private",
                        "progress": "indeterminate",
                        "action_buttons": ["cancel", "open_panel"],
                        "expires_at": "2026-06-19T00:00:45+00:00",
                        "source": "voice_gateway",
                        "deep_link": "/voice-harness/runs/conv-search",
                        "created_at": "2026-06-19T00:00:00+00:00",
                    }
                ],
                "first_response_audio_events": [
                    {
                        "id": "audio-1",
                        "turn_id": "conv-search",
                        "text": "我查一下。",
                        "phrase_key": "search",
                        "scheduled": True,
                        "scheduled_at_ms": 40,
                        "played": False,
                        "played_at_ms": None,
                        "source": "cached_tts",
                        "backend": "none",
                        "suppressed_reason": "playback_unavailable",
                        "target_ms": 300,
                    }
                ],
                "messages": [],
            },
        ),
    )

    record = store.snapshot()["records"][0]
    assert record["input"]["conversation_id"] == "conv-search"
    assert record["first_response_decision"]["cue"] == "search"
    assert record["first_response_decision"]["triggered_ms"] == 40
    assert record["debug_flags"]["search"]
    assert record["debug_flags"]["deep_verifier_waited"]
    assert record["verifier_mode"] == "blocking"
    assert record["tools"][0]["name"] == "search_web"
    assert record["grounding"]["evidence"][0]["evidence_type"] == "quote_origin"
    assert record["earcons"][0]["earcon_name"] == "search"
    assert record["display_status"]["latest"]["state"] == "searching"
    assert record["display_status"]["latest"]["action_buttons"] == [
        "cancel",
        "open_panel",
    ]
    assert record["first_response_audio"]["scheduled"] is True
    assert record["first_response_audio"]["played"] is False
    assert record["first_response_audio"]["suppressed_reason"] == "playback_unavailable"
    assert record["errors"][0]["type"] == "tool_error"
    assert record["timeline_spans"][1]["stage"] == "first_response"


async def test_trace_store_summarizes_weather_tool_loop_debug_fields(hass):
    store = TraceStore(hass, "entry-weather-debug")
    await store.async_load()

    await store.async_record_turn(
        {
            CONF_DIAGNOSTIC_TRACES: True,
            CONF_TRACE_MAX_RUNS: 30,
            CONF_TRACE_RETENTION_HOURS: 24,
        },
        TraceTurn(
            conversation_id="conv-weather",
            user_text="今天天气。",
            assistant_text="暂时没有本地天气数据。",
            route={"kind": "fast", "model": "fast-model"},
            latency_ms=1400,
            status="complete",
            timeline=[
                {"stage": "received", "t_ms": 0, "status": "ok", "attrs": {}},
                {
                    "stage": "first_response",
                    "t_ms": 50,
                    "status": "ok",
                    "attrs": {
                        "task_type": "weather_query",
                        "cue": "none",
                        "spoken_hint": "",
                        "reason": "home_state_weather",
                    },
                },
                {
                    "stage": "tool_call",
                    "t_ms": 500,
                    "status": "ok",
                    "attrs": {
                        "iteration": 1,
                        "names": ["GetLiveContext"],
                    },
                },
                {
                    "stage": "tool_result",
                    "t_ms": 650,
                    "status": "ok",
                    "attrs": {
                        "iteration": 1,
                        "name": "GetLiveContext",
                    },
                },
                {
                    "stage": "tool_call_suppressed",
                    "t_ms": 1100,
                    "status": "error",
                    "attrs": {
                        "iteration": 2,
                        "name": "GetLiveContext",
                        "reason": "duplicate_live_context",
                    },
                },
                {
                    "stage": "forced_final",
                    "t_ms": 1101,
                    "status": "ok",
                    "attrs": {
                        "iteration": 2,
                        "reason": "duplicate_live_context",
                    },
                },
                {
                    "stage": "complete",
                    "t_ms": 1400,
                    "status": "complete",
                    "attrs": {},
                },
            ],
            raw_payload={
                "input": {"text": "今天天气。", "conversation_id": "conv-weather"},
                "speech": {"final": "暂时没有本地天气数据。"},
                "tool_events": [
                    {
                        "phase": "call",
                        "tool_call_id": "live-1",
                        "name": "GetLiveContext",
                        "args": {},
                    },
                    {
                        "phase": "result",
                        "tool_call_id": "live-1",
                        "name": "GetLiveContext",
                        "status": "ok",
                        "result": {"success": True, "result": {}},
                    },
                ],
                "grounding": {"status": "not_required", "verifier": {}},
                "messages": [],
            },
        ),
    )

    record = store.snapshot()["records"][0]
    assert record["first_response_decision"]["task_type"] == "weather_query"
    assert record["search_gate"]["decision"] == "local_weather_first"
    assert record["search_gate"]["reason"] == "home_state_weather"
    assert record["search_debug"]["searched"] is False
    assert record["weather_context_path"]["path"] == "GetLiveContext"
    assert record["weather_context_path"]["get_live_context_calls"] == 1
    assert record["weather_context_path"]["duplicate_live_context_suppressed"] is True
    assert record["tool_calls_by_iteration"][0]["calls"] == ["GetLiveContext"]
    assert record["tool_calls_by_iteration"][1]["suppressions"][0]["reason"] == (
        "duplicate_live_context"
    )
    assert record["duplicate_tool_suppressions"][0]["name"] == "GetLiveContext"
    assert record["completion"]["complete"] is True
    assert record["completion"]["last_active_stage"] == "complete"


async def test_trace_store_keeps_polluted_evidence_out_of_quote_origin(hass):
    store = TraceStore(hass, "entry-polluted-evidence")
    await store.async_load()

    await store.async_record_turn(
        {
            CONF_DIAGNOSTIC_TRACES: True,
            CONF_TRACE_MAX_RUNS: 30,
            CONF_TRACE_RETENTION_HOURS: 24,
        },
        TraceTurn(
            conversation_id="conv-poem",
            user_text="关关雎鸠，在河之洲，这句话是出自哪里？",
            assistant_text="这句诗出自《诗经·周南·关雎》。",
            route={"kind": "mid", "model": "mid-model"},
            latency_ms=120,
            status="complete",
            raw_payload={
                "speech": {"final": "这句诗出自《诗经·周南·关雎》。"},
                "grounding": {
                    "status": "ok",
                    "canonical_answers": ["《诗经·周南·关雎》"],
                    "evidence": [
                        {
                            "evidence_id": "ev-1",
                            "source_id": "https://example.test/guanju",
                            "evidence_type": "quote_origin",
                            "text": "《诗经·周南·关雎》",
                            "included_in_final": True,
                        },
                        {
                            "evidence_id": "ev-2",
                            "source_id": "https://example.test/guanju",
                            "evidence_type": "term_explanation_source",
                            "text": "《禽经》",
                            "included_in_final": False,
                        },
                        {
                            "evidence_id": "ev-3",
                            "source_id": "https://example.test/guanju",
                            "evidence_type": "term_explanation_source",
                            "text": "《尔雅》",
                            "included_in_final": False,
                        },
                    ],
                    "verifier": {"mode": "cheap_evidence"},
                },
                "messages": [],
            },
        ),
    )

    evidence = store.snapshot()["records"][0]["grounding"]["evidence"]
    by_text = {item["text"]: item for item in evidence}
    assert by_text["《禽经》"]["evidence_type"] == "term_explanation_source"
    assert by_text["《尔雅》"]["evidence_type"] == "term_explanation_source"
    assert not by_text["《禽经》"]["included_in_final"]
    assert not by_text["《尔雅》"]["included_in_final"]


async def test_trace_store_marks_non_search_home_control_run(hass):
    store = TraceStore(hass, "entry-home-control")
    await store.async_load()

    await store.async_record_turn(
        {
            CONF_DIAGNOSTIC_TRACES: True,
            CONF_TRACE_MAX_RUNS: 30,
            CONF_TRACE_RETENTION_HOURS: 24,
        },
        TraceTurn(
            conversation_id="conv-home",
            user_text="打开客厅灯",
            assistant_text="好了。",
            route={"kind": "fast", "model": "fast-model"},
            latency_ms=300,
            status="complete",
            raw_payload={
                "input": {"text": "打开客厅灯", "conversation_id": "conv-home"},
                "speech": {"final": "好了。"},
                "timeline": [
                    {
                        "stage": "first_response",
                        "t_ms": 10,
                        "status": "ok",
                        "attrs": {"task_type": "home_control", "cue": "none"},
                    }
                ],
                "tool_events": [
                    {
                        "phase": "call",
                        "tool_call_id": "ha-1",
                        "name": "HassTurnOn",
                        "args": {"domain": "light", "area": "客厅"},
                    }
                ],
                "grounding": {"status": "not_required", "verifier": {}},
                "messages": [],
            },
        ),
    )

    record = store.snapshot()["records"][0]
    assert not record["debug_flags"]["search"]
    assert record["verifier_mode"] == "disabled"
    assert record["tools"][0]["name"] == "HassTurnOn"
