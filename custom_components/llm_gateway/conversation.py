"""Conversation agent for the LLM Gateway integration."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Literal

from homeassistant.components import conversation
from homeassistant.const import CONF_LLM_HASS_API, CONF_PROMPT, MATCH_ALL
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import llm
from homeassistant.helpers.json import json_dumps
from homeassistant.util import ulid
from voluptuous_openapi import convert

from .api import LLMGatewayClient, LLMGatewayError
from .const import (
    CONF_CHAT_MODEL,
    CONF_MAX_TOKENS,
    CONF_TEMPERATURE,
    CONF_TOP_P,
    DOMAIN,
    LOGGER,
    MAX_TOOL_ITERATIONS,
    RECOMMENDED_CHAT_MODEL,
    RECOMMENDED_MAX_TOKENS,
    RECOMMENDED_TEMPERATURE,
    RECOMMENDED_TOP_P,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .config_entry import LLMGatewayConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 - required by the platform signature
    entry: LLMGatewayConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the conversation entity."""
    async_add_entities([LLMGatewayConversationEntity(entry)])


def _format_tool(
    tool: llm.Tool, custom_serializer: Callable[[Any], Any] | None
) -> dict[str, Any]:
    """Convert an HA LLM tool into an OpenAI function-tool spec."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": convert(tool.parameters, custom_serializer=custom_serializer),
        },
    }


def _content_to_messages(content: list[conversation.Content]) -> list[dict[str, Any]]:
    """Convert HA chat-log content into OpenAI chat-completions messages."""
    messages: list[dict[str, Any]] = []
    for item in content:
        if item.role == "system":
            messages.append({"role": "system", "content": item.content})
        elif item.role == "user":
            messages.append({"role": "user", "content": item.content})
        elif item.role == "assistant":
            message: dict[str, Any] = {
                "role": "assistant",
                "content": item.content or "",
            }
            if item.tool_calls:
                message["tool_calls"] = [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.tool_name,
                            "arguments": json_dumps(call.tool_args),
                        },
                    }
                    for call in item.tool_calls
                ]
            messages.append(message)
        elif item.role == "tool_result":
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": item.tool_call_id,
                    "content": json_dumps(item.tool_result),
                }
            )
    return messages


def _parse_tool_calls(raw: list[dict[str, Any]] | None) -> list[llm.ToolInput]:
    """Parse OpenAI tool_calls into HA ToolInput objects."""
    if not raw:
        return []
    calls: list[llm.ToolInput] = []
    for call in raw:
        function = call.get("function") or {}
        arguments = function.get("arguments") or "{}"
        try:
            args = json.loads(arguments) if isinstance(arguments, str) else arguments
        except ValueError:
            LOGGER.warning("Could not parse tool arguments: %s", arguments)
            args = {}
        calls.append(
            llm.ToolInput(
                id=call.get("id") or ulid.ulid_now(),
                tool_name=function.get("name", ""),
                tool_args=args,
            )
        )
    return calls


class LLMGatewayConversationEntity(
    conversation.ConversationEntity, conversation.AbstractConversationAgent
):
    """An OpenAI-compatible conversation agent."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, entry: LLMGatewayConfigEntry) -> None:
        """Initialize the agent."""
        self.entry = entry
        self._attr_unique_id = entry.entry_id
        self._attr_device_info = dr.DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="LLM Gateway",
            model=entry.options.get(CONF_CHAT_MODEL, RECOMMENDED_CHAT_MODEL),
            entry_type=dr.DeviceEntryType.SERVICE,
        )
        if entry.options.get(CONF_LLM_HASS_API):
            self._attr_supported_features = (
                conversation.ConversationEntityFeature.CONTROL
            )

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return a list of supported languages."""
        return MATCH_ALL

    async def async_added_to_hass(self) -> None:
        """Register as the conversation agent for this entry."""
        await super().async_added_to_hass()
        conversation.async_set_agent(self.hass, self.entry, self)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister the conversation agent."""
        conversation.async_unset_agent(self.hass, self.entry)
        await super().async_will_remove_from_hass()

    async def _async_handle_message(
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog,
    ) -> conversation.ConversationResult:
        """Process one user turn."""
        options = self.entry.options
        try:
            await chat_log.async_provide_llm_data(
                user_input.as_llm_context(DOMAIN),
                options.get(CONF_LLM_HASS_API),
                options.get(CONF_PROMPT),
                user_input.extra_system_prompt,
            )
        except conversation.ConverseError as err:
            return err.as_conversation_result()

        await self._async_run_chat_log(chat_log)
        return conversation.async_get_result_from_chat_log(user_input, chat_log)

    async def _async_run_chat_log(self, chat_log: conversation.ChatLog) -> None:
        """Drive the model, executing tool calls until it returns a final answer."""
        client: LLMGatewayClient = self.entry.runtime_data
        options = self.entry.options
        model = options.get(CONF_CHAT_MODEL, RECOMMENDED_CHAT_MODEL)

        tools: list[dict[str, Any]] | None = None
        if chat_log.llm_api:
            tools = [
                _format_tool(tool, chat_log.llm_api.custom_serializer)
                for tool in chat_log.llm_api.tools
            ]

        for _iteration in range(MAX_TOOL_ITERATIONS):
            messages = _content_to_messages(chat_log.content)
            try:
                message = await client.async_chat_completion(
                    model=model,
                    messages=messages,
                    tools=tools,
                    max_tokens=options.get(CONF_MAX_TOKENS, RECOMMENDED_MAX_TOKENS),
                    temperature=options.get(CONF_TEMPERATURE, RECOMMENDED_TEMPERATURE),
                    top_p=options.get(CONF_TOP_P, RECOMMENDED_TOP_P),
                )
            except LLMGatewayError as err:
                LOGGER.error("Error talking to the gateway: %s", err)
                raise HomeAssistantError(
                    f"Error talking to LLM Gateway: {err}"
                ) from err

            content = conversation.AssistantContent(
                agent_id=self.entity_id,
                content=message.get("content") or None,
                tool_calls=_parse_tool_calls(message.get("tool_calls")) or None,
            )
            async for _tool_result in chat_log.async_add_assistant_content(content):
                # Tool results are appended to the chat log as they resolve.
                pass

            if not chat_log.unresponded_tool_results:
                return
