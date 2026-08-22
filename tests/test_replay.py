"""Tests for side-effect-free turn replay and fork lineage."""

import pytest

from custom_components.llm_gateway.const import CONF_DIAGNOSTIC_TRACES
from custom_components.llm_gateway.replay import (
    ReplayError,
    ReplayOverrides,
    async_replay_turn,
)
from custom_components.llm_gateway.traces import TraceStore, TraceTurn


async def _source_turn(hass) -> tuple[TraceStore, str]:
    store = TraceStore(hass, "replay-test")
    await store.async_load()
    await store.async_record_turn(
        {CONF_DIAGNOSTIC_TRACES: True},
        TraceTurn(
            conversation_id="conv-replay",
            user_text="打开所有灯。",
            assistant_text="已打开所有灯。",
            route={"kind": "local_action", "model": "capability_executor"},
            latency_ms=30,
            status="complete",
            raw_payload={"input": {"text": "打开所有灯。"}},
            run_id="source-run",
        ),
    )
    return store, "source-run"


async def test_replay_records_fork_without_calling_live_service(hass) -> None:
    calls = []

    async def turn_on(call):
        calls.append(call)

    hass.services.async_register("light", "turn_on", turn_on)
    store, source_run_id = await _source_turn(hass)

    record = await async_replay_turn(
        hass,
        store,
        {CONF_DIAGNOSTIC_TRACES: True},
        source_run_id,
        ReplayOverrides(prompt="candidate-b"),
    )

    assert calls == []
    assert record["lineage"] == {
        "replay_of": source_run_id,
        "fork_id": record["run_id"],
        "mode": "dry_run",
        "overrides": {
            "loop": "deterministic_capability",
            "route": "recorded",
            "prompt": "candidate-b",
        },
    }
    assert record["proposed_actions"] == [
        {
            "family": "home_control",
            "action": "turn_on",
            "domain": "light",
            "area": "",
            "target_hint": "所有灯",
            "target_scope": "all",
            "target_temperature": None,
            "volume_level": None,
            "mute": None,
        }
    ]
    assert any(
        event["event_type"] == "gateway.replay.started"
        for event in record["event_stream"]
    )


async def test_replay_rejects_missing_source(hass) -> None:
    store = TraceStore(hass, "missing-replay")
    await store.async_load()

    with pytest.raises(ReplayError, match="not found") as error:
        await async_replay_turn(
            hass,
            store,
            {CONF_DIAGNOSTIC_TRACES: True},
            "missing",
            ReplayOverrides(),
        )

    assert error.value.code == "run_not_found"


def test_replay_rejects_unsupported_override() -> None:
    with pytest.raises(ReplayError, match="unsupported overrides") as error:
        ReplayOverrides.from_payload({"temperature": 1})

    assert error.value.code == "unsupported_override"
