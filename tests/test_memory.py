"""Tests for bounded local voice memory."""

from unittest.mock import AsyncMock

from custom_components.llm_gateway.memory import FactWrite, VoiceMemory


async def test_memory_summarizes_evicted_turns_and_keeps_six_raw(hass) -> None:
    memory = VoiceMemory(hass, "entry-memory")
    memory._store.async_save = AsyncMock()

    for index in range(8):
        await memory.async_record_turn(
            "conversation-1", f"用户-{index}", f"回答-{index}"
        )

    session = memory.snapshot()["sessions"][0]
    assert session["summary"] == "用户-0；用户-1"
    assert [turn["user"] for turn in session["turns"]] == [
        "用户-2",
        "用户-3",
        "用户-4",
        "用户-5",
        "用户-6",
        "用户-7",
    ]


async def test_memory_uses_entry_scoped_session_without_conversation_id(hass) -> None:
    memory = VoiceMemory(hass, "entry-memory")
    memory._store.async_save = AsyncMock()

    await memory.async_record_turn(None, "打开灯", "已打开。")

    assert "打开灯" in memory.build_context(None)
    assert memory.snapshot()["sessions"][0]["conversation_id"] == "entry-memory"


async def test_structured_facts_are_relevant_bounded_and_superseded(hass) -> None:
    memory = VoiceMemory(hass, "entry-memory")
    memory._store.async_save = AsyncMock()

    await memory.async_upsert_fact(
        FactWrite("night_brightness", "10%", "intent:light", "turn-1")
    )
    replacement = await memory.async_upsert_fact(
        FactWrite("night_brightness", "15%", "intent:light", "turn-2")
    )
    await memory.async_upsert_fact(
        FactWrite("favorite_temperature", "24℃", "intent:climate", "turn-3")
    )

    assert replacement.supersedes == "turn-1"
    light_facts = memory.relevant_facts(task_type="light_control")
    assert [fact.value for fact in light_facts] == ["15%"]
    assert "24℃" not in memory.build_context(None, task_type="light_control")


async def test_legacy_string_fact_is_loaded_with_evidence(hass) -> None:
    memory = VoiceMemory(hass, "entry-memory")
    memory._store.async_load = AsyncMock(return_value={"facts": ["夜间灯光 10%"]})

    await memory.async_load()

    fact = memory.snapshot()["facts"][0]
    assert fact["value"] == "夜间灯光 10%"
    assert fact["evidence_turn_id"] == "legacy_store"
