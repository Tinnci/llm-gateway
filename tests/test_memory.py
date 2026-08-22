"""Tests for bounded local voice memory."""

from unittest.mock import AsyncMock

from custom_components.llm_gateway.memory import VoiceMemory


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
