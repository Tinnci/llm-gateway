"""Regression coverage for Home Assistant 2026.10 tool results."""

from unittest.mock import PropertyMock, patch

from homeassistant.components.conversation import ToolResultContent
from homeassistant.helpers.llm import ToolResult

from custom_components.llm_gateway.conversation import _tool_events_from_content
from custom_components.llm_gateway.history_policy import content_to_messages


def test_history_reads_structured_result_without_legacy_property() -> None:
    content = ToolResultContent(
        agent_id="conversation.test",
        tool_call_id="call-1",
        tool_name="GetLiveContext",
        result=ToolResult(data={"temperature": 22}),
    )
    with patch.object(
        ToolResultContent,
        "tool_result",
        new_callable=PropertyMock,
        side_effect=AssertionError("legacy access"),
    ):
        messages = content_to_messages([content])
    assert messages == [
        {"role": "tool", "tool_call_id": "call-1", "content": '{"temperature":22}'}
    ]


def test_trace_preserves_structured_error_without_error_key() -> None:
    content = ToolResultContent(
        agent_id="conversation.test",
        tool_call_id="call-1",
        tool_name="HassTurnOn",
        result=ToolResult(data={"detail": "permission denied"}, error=True),
    )
    events = _tool_events_from_content([content])
    assert events[0]["status"] == "error"
    assert events[0]["result"] == {"detail": "permission denied"}
