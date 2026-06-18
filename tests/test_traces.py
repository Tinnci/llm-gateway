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
            raw_payload={"messages": [{"role": "user", "content": "查一下卧室温度"}]},
        ),
    )

    snapshot = store.snapshot()
    record = snapshot["records"][0]
    assert record["conversation_id"] == "conv-1"
    assert record["user_text"] == "查一下卧室温度"
    assert record["assistant_text"] == "卧室现在 24 度。"
    assert record["route"]["kind"] == "fast"
    assert record["timeline"][0]["stage"] == "received"
    assert "raw_payload" not in record
    assert snapshot["storage"]["records"] == 1
    assert snapshot["storage"]["compressed_bytes"] == 0


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
    assert record["tools"] == [
        {"name": "HassTurnOn", "phase": "call"},
        {"name": "HassTurnOn", "phase": "result", "tool_call_id": "call-1"},
    ]


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
