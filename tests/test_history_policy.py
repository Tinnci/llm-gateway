"""Tests for model-visible history bounding."""

from __future__ import annotations

from dataclasses import dataclass, field

from custom_components.llm_gateway.history_policy import (
    bound_model_messages,
    content_to_messages,
)


@dataclass(slots=True)
class _Call:
    id: str
    tool_name: str = "search_web"
    tool_args: dict = field(default_factory=lambda: {"query": "x"})


@dataclass(slots=True)
class _Item:
    role: str
    content: str | None = None
    tool_calls: list[_Call] | None = None
    tool_call_id: str | None = None
    tool_result: dict | None = None


def _conversation(turns: int):
    """Build a user/assistant ping-pong with one tool transaction mid-way."""
    items: list[_Item] = [_Item("system", "base prompt")]
    for i in range(turns):
        items.append(_Item("user", f"u{i}"))
        if i == 1:
            items.append(_Item("assistant", None, tool_calls=[_Call("c1")]))
            items.append(
                _Item(
                    "tool_result",
                    tool_call_id="c1",
                    tool_result={"ok": True},
                )
            )
        items.append(_Item("assistant", f"a{i}"))
    return items


def test_short_conversation_passes_through_unbounded():
    messages = content_to_messages(_conversation(3))
    bounded, elided = bound_model_messages(messages, max_messages=40)

    assert elided == 0
    assert bounded == messages


def test_long_conversation_trimmed_with_digest_note():
    messages = content_to_messages(_conversation(30))
    total_non_system = sum(1 for m in messages if m["role"] != "system")
    bounded, elided = bound_model_messages(messages, max_messages=20)

    assert 0 < elided < total_non_system
    digest = [m for m in bounded if "omitted" in (m.get("content") or "")]
    assert len(digest) == 1
    assert str(elided) in digest[0]["content"]
    assert bounded[-1] == messages[-1]
    # System blocks always retained.
    assert bounded[0] == messages[0]


def test_tool_transaction_never_split():
    messages = content_to_messages(_conversation(30))
    bounded, _elided = bound_model_messages(messages, max_messages=14)

    call_index = next(i for i, m in enumerate(bounded) if m.get("tool_calls"))
    assert bounded[call_index + 1]["role"] == "tool"
    assert bounded[call_index + 1]["tool_call_id"] == "c1"


def test_min_recent_floor_respected():
    messages = content_to_messages(_conversation(40))
    bounded, elided = bound_model_messages(messages, max_messages=10, min_recent=12)

    kept = [m for m in bounded if m["role"] != "system"]
    kept = [m for m in kept if "omitted" not in (m.get("content") or "")]
    assert elided > 0
    assert len(kept) >= 12


def test_converter_matches_legacy_shape():
    messages = content_to_messages(_conversation(2))
    assistant_with_call = next(m for m in messages if m.get("tool_calls"))
    assert assistant_with_call["tool_calls"][0]["function"]["name"] == "search_web"
    assert assistant_with_call["tool_calls"][0]["id"] == "c1"
