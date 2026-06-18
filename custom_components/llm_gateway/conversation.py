"""Conversation agent for the LLM Gateway integration."""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any, Literal

from homeassistant.components import conversation
from homeassistant.const import CONF_LLM_HASS_API, CONF_PROMPT, MATCH_ALL
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import llm
from homeassistant.helpers.json import json_dumps
from homeassistant.util import ulid
from voluptuous_openapi import convert

from .api import LLMGatewayClient, LLMGatewayError
from .const import (
    CONF_TEMPERATURE,
    CONF_TOP_P,
    DEEP_TASK_ACK_SPEECH,
    DOMAIN,
    GATEWAY_ERROR_SPEECH,
    LOGGER,
    MAX_TOOL_ITERATIONS,
    RECOMMENDED_TEMPERATURE,
    RECOMMENDED_TOP_P,
    TOOL_LOOP_ERROR_SPEECH,
)
from .policy import validate_tool_call
from .router import legacy_model_from_options, parse_extra_body, select_model_route
from .search import (
    async_execute_search_tool,
    available_search_tools,
    mark_external_tool_calls,
)
from .traces import TraceTurn
from .voice_text import markdown_to_spoken_text

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .config_entry import LLMGatewayConfigEntry
    from .router import ModelRoute
    from .runtime import LLMGatewayRuntimeData


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
    return mark_external_tool_calls(calls)


def _is_action_tool(tool_name: str) -> bool:
    """Return whether a built-in Assist tool changes Home Assistant state."""
    return tool_name.startswith("Hass")


def _extra_body_from_options(options: dict[str, Any]) -> dict[str, Any] | None:
    """Parse optional OpenAI-compatible extra body JSON from options."""
    return parse_extra_body(options.get("extra_body"))


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
            model=legacy_model_from_options(entry.options),
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
        started = time.monotonic()
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

        runtime = self.entry.runtime_data
        route = select_model_route(user_input.text, options)
        self._inject_memory_context(chat_log, runtime, user_input.conversation_id)

        if route.async_deep_task:
            messages = _content_to_messages(chat_log.content)
            task_id = runtime.deep_tasks.submit(
                route=route,
                messages=messages,
                user_text=user_input.text,
                temperature=options.get(CONF_TEMPERATURE, RECOMMENDED_TEMPERATURE),
                top_p=options.get(CONF_TOP_P, RECOMMENDED_TOP_P),
            )
            LOGGER.info(
                "Submitted deep task task_id=%s model=%s messages=%d",
                task_id,
                route.model,
                len(messages),
            )
            async for _tool_result in chat_log.async_add_assistant_content(
                conversation.AssistantContent(
                    agent_id=self.entity_id,
                    content=DEEP_TASK_ACK_SPEECH,
                )
            ):
                pass
        else:
            await self._async_run_chat_log(chat_log, route, user_input.text)

        result = conversation.async_get_result_from_chat_log(user_input, chat_log)
        spoken = result.response.speech.get("plain", {}).get("speech", "")
        if spoken:
            result.response.async_set_speech(markdown_to_spoken_text(spoken))
        assistant_text = result.response.speech.get("plain", {}).get("speech", "")
        await runtime.memory.async_record_turn(
            user_input.conversation_id,
            user_input.text,
            assistant_text,
        )
        await runtime.trace_store.async_record_turn(
            options,
            TraceTurn(
                conversation_id=user_input.conversation_id,
                user_text=user_input.text,
                assistant_text=assistant_text,
                route=_route_trace(route),
                latency_ms=int((time.monotonic() - started) * 1000),
                status=_trace_status(assistant_text),
                raw_payload={
                    "input": {
                        "text": user_input.text,
                        "conversation_id": user_input.conversation_id or "",
                        "language": getattr(user_input, "language", "") or "",
                        "device_id": getattr(user_input, "device_id", "") or "",
                    },
                    "route": _route_trace(route),
                    "messages": _content_to_messages(chat_log.content),
                    "speech": {
                        "final": assistant_text,
                        "tts_cleaned": bool(spoken),
                    },
                },
            ),
        )
        return result

    def _inject_memory_context(
        self,
        chat_log: conversation.ChatLog,
        runtime: LLMGatewayRuntimeData,
        conversation_id: str | None,
    ) -> None:
        """Append compact local memory into the model context."""
        memory_context = runtime.memory.build_context(conversation_id)
        if memory_context:
            chat_log.content.insert(
                1, conversation.SystemContent(content=memory_context)
            )

    async def _async_run_chat_log(  # noqa: PLR0912
        self,
        chat_log: conversation.ChatLog,
        route: ModelRoute,
        user_text: str,
    ) -> None:
        """Drive the model, executing tool calls until it returns a final answer."""
        runtime = self.entry.runtime_data
        client: LLMGatewayClient = runtime.client
        options = self.entry.options

        tools: list[dict[str, Any]] | None = None
        if chat_log.llm_api:
            tools = [
                _format_tool(tool, chat_log.llm_api.custom_serializer)
                for tool in chat_log.llm_api.tools
            ]
        search_tools = available_search_tools(options)
        if search_tools:
            tools = [*(tools or []), *search_tools]

        force_tool_call = False
        for iteration in range(1, MAX_TOOL_ITERATIONS + 1):
            messages = _content_to_messages(chat_log.content)
            LOGGER.info(
                "Conversation model turn iteration=%d route=%s model=%s "
                "messages=%d tools=%d",
                iteration,
                route.kind,
                route.model,
                len(messages),
                len(tools or []),
            )
            try:
                message = await client.async_chat_completion(
                    model=route.model,
                    messages=messages,
                    tools=tools,
                    tool_choice="required" if force_tool_call else None,
                    extra_body=route.extra_body,
                    timeout_s=route.timeout_s,
                    max_tokens=route.max_tokens,
                    temperature=options.get(CONF_TEMPERATURE, RECOMMENDED_TEMPERATURE),
                    top_p=options.get(CONF_TOP_P, RECOMMENDED_TOP_P),
                )
            except LLMGatewayError as err:
                LOGGER.error("Error talking to the gateway: %s", err)
                error_content = conversation.AssistantContent(
                    agent_id=self.entity_id,
                    content=GATEWAY_ERROR_SPEECH,
                )
                async for _tool_result in chat_log.async_add_assistant_content(
                    error_content
                ):
                    pass
                return

            content = conversation.AssistantContent(
                agent_id=self.entity_id,
                content=message.get("content") or None,
                tool_calls=_parse_tool_calls(message.get("tool_calls")) or None,
            )
            if content.tool_calls:
                LOGGER.info(
                    "Assistant tool calls iteration=%d names=%s",
                    iteration,
                    ",".join(call.tool_name for call in content.tool_calls),
                )
                policy_block = self._policy_block(content.tool_calls, user_text)
                if policy_block:
                    async for _tool_result in chat_log.async_add_assistant_content(
                        conversation.AssistantContent(
                            agent_id=self.entity_id,
                            content=policy_block,
                        )
                    ):
                        pass
                    return
            async for tool_result in chat_log.async_add_assistant_content(content):
                result = tool_result.tool_result
                if _is_action_tool(tool_result.tool_name):
                    force_tool_call = "error" in result
                LOGGER.info(
                    "Tool result iteration=%d name=%s success=%s error=%s",
                    iteration,
                    tool_result.tool_name,
                    "error" not in result,
                    result.get("error", "none"),
                )

            for tool_call in content.tool_calls or []:
                if not tool_call.external:
                    continue
                result = await async_execute_search_tool(
                    runtime.session,
                    options,
                    tool_call,
                )
                chat_log.async_add_assistant_content_without_tools(
                    conversation.ToolResultContent(
                        agent_id=self.entity_id,
                        tool_call_id=tool_call.id,
                        tool_name=tool_call.tool_name,
                        tool_result=result,
                    )
                )

            if not chat_log.unresponded_tool_results:
                return

        LOGGER.error("Tool-call loop exceeded %d iterations", MAX_TOOL_ITERATIONS)
        error_content = conversation.AssistantContent(
            agent_id=self.entity_id,
            content=TOOL_LOOP_ERROR_SPEECH,
        )
        async for _tool_result in chat_log.async_add_assistant_content(error_content):
            pass

    def _policy_block(
        self, tool_calls: list[llm.ToolInput], user_text: str
    ) -> str | None:
        """Return a spoken block prompt if any tool call violates policy."""
        for tool_call in tool_calls:
            decision = validate_tool_call(tool_call, user_text)
            if decision.allowed:
                continue
            LOGGER.info(
                "Tool call blocked by policy name=%s reason=%s",
                tool_call.tool_name,
                decision.reason,
            )
            return decision.spoken_prompt or "这个操作需要先确认。"
        return None


def _route_trace(route: ModelRoute) -> dict[str, Any]:
    """Return route metadata safe for diagnostic traces."""
    return {
        "kind": route.kind,
        "model": route.model,
        "max_tokens": route.max_tokens,
        "timeout_s": route.timeout_s,
        "async_deep_task": route.async_deep_task,
    }


def _trace_status(assistant_text: str) -> str:
    """Classify the completed turn for trace filtering."""
    if assistant_text in {GATEWAY_ERROR_SPEECH, TOOL_LOOP_ERROR_SPEECH}:
        return "error"
    if assistant_text == DEEP_TASK_ACK_SPEECH:
        return "queued"
    return "complete"
