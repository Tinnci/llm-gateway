"""Tests for the conversation entity and its helpers."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.components import conversation
from homeassistant.core import Context
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import llm

from custom_components.llm_gateway.api import LLMGatewayConnectionError
from custom_components.llm_gateway.const import (
    DEEP_TASK_ACK_SPEECH,
    DEFAULT_BASE_URL,
    GATEWAY_ERROR_SPEECH,
)
from custom_components.llm_gateway.conversation import (
    _content_to_messages,
    _extra_body_from_options,
    _is_action_tool,
    _parse_tool_calls,
)

MODELS_URL = f"{DEFAULT_BASE_URL}/models"
CHAT_URL = f"{DEFAULT_BASE_URL}/chat/completions"


def test_content_to_messages_roundtrip():
    content = [
        conversation.SystemContent(content="sys"),
        conversation.UserContent(content="hi"),
        conversation.AssistantContent(agent_id="a", content="ok"),
        conversation.ToolResultContent(
            agent_id="a",
            tool_call_id="42",
            tool_name="t",
            tool_result={"ok": True},
        ),
    ]
    messages = _content_to_messages(content)
    assert messages[0] == {"role": "system", "content": "sys"}
    assert messages[1] == {"role": "user", "content": "hi"}
    assert messages[2] == {"role": "assistant", "content": "ok"}
    assert messages[3]["role"] == "tool"
    assert messages[3]["tool_call_id"] == "42"


def test_content_to_messages_tool_calls():
    content = [
        conversation.AssistantContent(
            agent_id="a",
            content=None,
            tool_calls=[
                llm.ToolInput(id="1", tool_name="turn_on", tool_args={"area": "客厅"})
            ],
        ),
    ]
    messages = _content_to_messages(content)
    assert messages[0]["tool_calls"][0]["function"]["name"] == "turn_on"
    assert "客厅" in messages[0]["tool_calls"][0]["function"]["arguments"]


def test_parse_tool_calls():
    calls = _parse_tool_calls(
        [{"id": "1", "function": {"name": "t", "arguments": '{"a": 1}'}}]
    )
    assert calls[0].id == "1"
    assert calls[0].tool_name == "t"
    assert calls[0].tool_args == {"a": 1}
    assert _parse_tool_calls(None) == []


def test_parse_tool_calls_bad_args_generates_id():
    calls = _parse_tool_calls([{"function": {"name": "t", "arguments": "not-json"}}])
    assert calls[0].tool_args == {}
    assert calls[0].id  # an id was generated


def test_action_tool_detection():
    assert _is_action_tool("HassTurnOn")
    assert _is_action_tool("HassLightSet")
    assert not _is_action_tool("GetLiveContext")


def test_extra_body_from_options():
    assert _extra_body_from_options({}) is None
    assert _extra_body_from_options({"extra_body": "[]"}) is None
    assert _extra_body_from_options({"extra_body": '{"reasoning_budget": 1}'}) == {
        "reasoning_budget": 1
    }


async def test_converse_plain(hass, aioclient_mock, mock_config_entry):
    aioclient_mock.get(
        MODELS_URL, json={"data": [{"id": "qwen/qwen3-next-80b-a3b-instruct"}]}
    )
    aioclient_mock.post(
        CHAT_URL,
        json={
            "choices": [
                {"message": {"role": "assistant", "content": "你好，有什么可以帮您？"}}
            ]
        },
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    entities = er.async_entries_for_config_entry(ent_reg, mock_config_entry.entry_id)
    agent_id = entities[0].entity_id

    result = await conversation.async_converse(
        hass, "你好", None, Context(), agent_id=agent_id
    )
    assert result.response.speech["plain"]["speech"] == "你好，有什么可以帮您？"


async def test_converse_sanitizes_markdown_for_tts(
    hass, aioclient_mock, mock_config_entry
):
    aioclient_mock.get(
        MODELS_URL, json={"data": [{"id": "qwen/qwen3-next-80b-a3b-instruct"}]}
    )
    aioclient_mock.post(
        CHAT_URL,
        json={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "这是 **重要** 内容。第二句。第三句。",
                    }
                }
            ]
        },
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    entities = er.async_entries_for_config_entry(ent_reg, mock_config_entry.entry_id)
    agent_id = entities[0].entity_id

    result = await conversation.async_converse(
        hass, "说明一下", None, Context(), agent_id=agent_id
    )
    assert result.response.speech["plain"]["speech"] == "这是 重要 内容。第二句。"


async def test_converse_deep_route_submits_background_task(
    hass, aioclient_mock, mock_config_entry
):
    aioclient_mock.get(
        MODELS_URL, json={"data": [{"id": "qwen/qwen3-next-80b-a3b-instruct"}]}
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    entities = er.async_entries_for_config_entry(ent_reg, mock_config_entry.entry_id)
    agent_id = entities[0].entity_id

    with patch(
        "custom_components.llm_gateway.runtime.DeepTaskManager.submit",
        return_value="task-1",
    ) as submit:
        result = await conversation.async_converse(
            hass, "请深度分析整个控制管线", None, Context(), agent_id=agent_id
        )

    assert result.response.speech["plain"]["speech"] == DEEP_TASK_ACK_SPEECH
    submit.assert_called_once()


async def test_converse_blocks_high_risk_tool_without_confirmation(
    hass, aioclient_mock, mock_config_entry
):
    aioclient_mock.get(
        MODELS_URL, json={"data": [{"id": "qwen/qwen3-next-80b-a3b-instruct"}]}
    )
    aioclient_mock.post(
        CHAT_URL,
        json={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": "call-1",
                                "type": "function",
                                "function": {
                                    "name": "HassTurnOn",
                                    "arguments": '{"domain":"lock","name":"前门门锁"}',
                                },
                            }
                        ],
                    }
                }
            ]
        },
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    entities = er.async_entries_for_config_entry(ent_reg, mock_config_entry.entry_id)
    agent_id = entities[0].entity_id

    result = await conversation.async_converse(
        hass, "打开前门", None, Context(), agent_id=agent_id
    )
    assert "确认" in result.response.speech["plain"]["speech"]


async def test_converse_gateway_timeout_returns_spoken_error(
    hass, aioclient_mock, mock_config_entry
):
    aioclient_mock.get(
        MODELS_URL, json={"data": [{"id": "qwen/qwen3-next-80b-a3b-instruct"}]}
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    entities = er.async_entries_for_config_entry(ent_reg, mock_config_entry.entry_id)
    agent_id = entities[0].entity_id

    with patch(
        "custom_components.llm_gateway.api.LLMGatewayClient.async_chat_completion",
        side_effect=LLMGatewayConnectionError("timeout"),
    ):
        result = await conversation.async_converse(
            hass, "打开风扇", None, Context(), agent_id=agent_id
        )

    assert result.response.speech["plain"]["speech"] == GATEWAY_ERROR_SPEECH
