"""Conversation agent for the LLM Gateway integration."""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any, Literal

from homeassistant.components import conversation
from homeassistant.const import CONF_LLM_HASS_API, CONF_PROMPT, MATCH_ALL
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import llm
from homeassistant.helpers.intent import IntentResponse
from homeassistant.helpers.json import json_dumps
from homeassistant.util import ulid
from voluptuous_openapi import convert

from .api import LLMGatewayClient, LLMGatewayError, ToolChoice
from .capabilities import (
    MultiIntentPlan,
    RouteDecision,
    decide_route,
    plan_multi_intent,
)
from .capability_executor import async_try_execute_local_capability
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
    TOOL_LOOP_GUARD_SPEECH,
)
from .dialogue import (
    PendingTask,
    interaction_state_for_policy_block,
    pending_task_from_route,
    resolve_pending_task,
)
from .feedback import (
    VoiceFeedbackPolicy,
    feedback_trace_attrs,
)
from .first_response import (
    FirstResponseDecision,
    decide_first_response,
    stable_fact_answer,
)
from .grounding import (
    GroundingResult,
    initial_grounding_result,
)
from .policy import should_force_search_in_voice_path, validate_tool_call
from .providers import async_chat_completion_with_fallback
from .router import (
    legacy_model_from_options,
    parse_extra_body,
    select_model_route,
)
from .search import (
    SEARCH_TOOL_NAME,
    async_execute_search_tool,
    available_search_tools,
    mark_external_tool_calls,
)
from .static_context import render_device_inventory, render_scalar_state_answer
from .traces import TraceTurn
from .voice_controls import async_handle_voice_runtime_command
from .voice_text import markdown_to_spoken_text

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .config_entry import LLMGatewayConfigEntry
    from .router import ModelRoute
    from .runtime import LLMGatewayRuntimeData, TurnToken

VOICE_RESPONSE_CONTRACT = """Voice response contract:
- Final assistant content is spoken aloud, so use plain text rather than Markdown.
- Do not wrap quotations, poems, entity names, or short facts in code fences.
- Use code fences only when the user explicitly asks for code.
- Use search_web only when current external information is required or the user
  explicitly asks to search. Stable facts may be answered without web search.
- Keep the spoken answer concise; put long details in the Home Assistant panel.
"""

LIVE_CONTEXT_TOOL_NAME = "GetLiveContext"
_LIVE_CONTEXT_ENTITY_HINT_TERMS = (
    "天气",
    "空气质量",
    "温度",
    "湿度",
    "pm2.5",
    "pm25",
    "co2",
    "tvoc",
    "eco2",
)
_GENERIC_LIVE_CONTEXT_NAMES = {
    "天气",
    "空气质量",
    "温度",
    "湿度",
    "pm2.5",
    "pm25",
    "co2",
    "tvoc",
    "eco2",
}
_HOME_AREA_HINTS = {"卧室", "客厅", "餐厅", "厨房", "书房", "卫生间", "阳台"}
WEATHER_CONTEXT_FALLBACK_SPEECH = "暂时没有本地天气数据。"
HOME_STATE_FALLBACK_SPEECH = "暂时没有本地状态数据。"
HIGH_RISK_FALLBACK_SPEECH = "这个需要确认。"
SAME_TOOL_SAME_ARGS_LIMIT = 1
FORCED_FINAL_CONTRACT = """Tool loop guard:
Use the tool results already present in this conversation and provide the final
spoken answer now. Do not call any more tools. If the available local/live
context is insufficient, say that briefly instead of searching or retrying.
"""
INVENTORY_TASK_TYPES = {
    "device_inventory_query",
    "area_inventory_query",
    "domain_inventory_query",
    "capability_query",
    "exposed_context_query",
}


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


def _parse_tool_calls(
    raw: list[dict[str, Any]] | None,
    user_text: str = "",
) -> list[llm.ToolInput]:
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
        tool_name = function.get("name", "")
        calls.append(
            llm.ToolInput(
                id=call.get("id") or ulid.ulid_now(),
                tool_name=tool_name,
                tool_args=_normalize_tool_args(tool_name, args, user_text=user_text),
            )
        )
    return mark_external_tool_calls(calls)


def _normalize_tool_args(
    tool_name: str,
    args: object,
    *,
    user_text: str = "",
) -> dict[str, Any]:
    """Normalize model tool args before HA tool execution."""
    normalized = dict(args) if isinstance(args, dict) else {}
    if tool_name == LIVE_CONTEXT_TOOL_NAME:
        if normalized.get("name") == LIVE_CONTEXT_TOOL_NAME:
            normalized.pop("name", None)
        area = normalized.get("area")
        if isinstance(area, str) and _looks_like_live_context_entity_hint(area):
            normalized.setdefault("name", area)
            normalized.pop("area", None)
        elif (
            isinstance(area, str)
            and _looks_like_weather_state_text(user_text)
            and area not in _HOME_AREA_HINTS
        ):
            normalized.pop("area", None)
        name = normalized.get("name")
        if isinstance(name, str) and _is_generic_live_context_name(name):
            normalized.pop("name", None)
    return normalized


def _looks_like_live_context_entity_hint(value: str) -> bool:
    normalized = _normalize_live_context_hint(value)
    return any(term in normalized for term in _LIVE_CONTEXT_ENTITY_HINT_TERMS)


def _is_generic_live_context_name(value: str) -> bool:
    normalized = _normalize_live_context_hint(value)
    if normalized in _GENERIC_LIVE_CONTEXT_NAMES:
        return True
    has_specific_metric = any(
        metric in normalized
        for metric in ("pm2.5", "pm25", "co2", "tvoc", "eco2", "温度", "湿度")
    )
    return not has_specific_metric and (
        "天气" in normalized or "空气质量" in normalized
    )


def _looks_like_weather_state_text(value: str) -> bool:
    normalized = _normalize_live_context_hint(value)
    return any(
        term in normalized
        for term in ("天气", "空气质量", "pm2.5", "pm25", "雾霾", "气温")
    )


def _normalize_live_context_hint(value: str) -> str:
    normalized = value.strip().lower().replace(" ", "").replace("．", ".")
    return normalized.replace("pm2点5", "pm2.5").replace("pm₂.₅", "pm2.5")


def _is_action_tool(tool_name: str) -> bool:
    """Return whether a built-in Assist tool changes Home Assistant state."""
    return tool_name.startswith("Hass")


def _tool_choice_for_turn(
    user_text: str,
    tools: list[dict[str, Any]] | None,
    *,
    force_tool_call: bool,
    force_live_context: bool = False,
    require_grounding: bool = True,
) -> ToolChoice | None:
    """Return a narrow tool choice for turns that need deterministic grounding."""
    if force_tool_call:
        return "required"
    if force_live_context and _has_tool(tools, LIVE_CONTEXT_TOOL_NAME):
        return {"type": "function", "function": {"name": LIVE_CONTEXT_TOOL_NAME}}
    if (
        require_grounding
        and should_force_search_in_voice_path(user_text)
        and _has_tool(tools, SEARCH_TOOL_NAME)
    ):
        return {"type": "function", "function": {"name": SEARCH_TOOL_NAME}}
    return None


def _has_tool(tools: list[dict[str, Any]] | None, tool_name: str) -> bool:
    for tool in tools or []:
        function = tool.get("function") or {}
        if function.get("name") == tool_name:
            return True
    return False


def _tool_name(tool: dict[str, Any]) -> str:
    function = tool.get("function") or {}
    return str(function.get("name") or "")


def _filter_visible_tools(
    tools: list[dict[str, Any]] | None,
    route_decision: RouteDecision,
) -> list[dict[str, Any]] | None:
    """Expose only tools allowed by the capability route."""
    if tools is None:
        return None
    allowed = set(route_decision.allowed_tools)
    if not allowed:
        return []
    return [tool for tool in tools if _tool_name(tool) in allowed]


def _is_live_context_task_type(task_type: str) -> bool:
    return task_type in {
        "weather_query",
        "home_state",
        "indoor_environment_query",
        "outdoor_current_weather_query",
        "home_temperature_summary",
    }


def _multi_intent_is_local(plan: MultiIntentPlan) -> bool:
    """Return whether all planned subtasks can complete without model execution."""
    if not plan.is_multi_intent:
        return False
    for subtask in plan.subtasks:
        decision = subtask.route_decision
        if decision.forecast_required or decision.requires_external_info:
            return False
        if decision.task_type in INVENTORY_TASK_TYPES:
            continue
        if decision.next_action == "call_tool_then_local_render":
            continue
        return False
    return True


def _compose_spoken_subanswers(subanswers: list[str]) -> str:
    """Compose local subtask answers into one concise spoken response."""
    parts = [part.strip() for part in subanswers if part and part.strip()]
    if not parts:
        return ""
    return " ".join(_ensure_sentence(part) for part in parts)


def _final_must_cover(plan: MultiIntentPlan) -> list[str]:
    """Return stable coverage keys for every subtask the composer must include."""
    return [
        f"{subtask.route_decision.task_type}:{subtask.index}"
        for subtask in plan.subtasks
    ]


def _ensure_sentence(text: str) -> str:
    value = str(text or "").strip()
    return value if value.endswith(("。", "！", "？", ".", "!", "?")) else f"{value}。"


def _chat_log_has_tool(chat_log: conversation.ChatLog, tool_name: str) -> bool:
    llm_api = getattr(chat_log, "llm_api", None)
    return any(
        getattr(tool, "name", "") == tool_name
        for tool in getattr(llm_api, "tools", ()) or ()
    )


def _local_live_context_tool_args(text: str) -> dict[str, Any]:
    slots = _local_live_context_slots(text)
    args: dict[str, Any] = {}
    domain = str(slots.get("domain") or "")
    area = str(slots.get("area") or "")
    if domain:
        args["domain"] = domain
    if area:
        args["area"] = area
    return _normalize_tool_args(LIVE_CONTEXT_TOOL_NAME, args, user_text=text)


def _local_live_context_slots(text: str) -> dict[str, str]:
    normalized = _normalize_live_context_hint(text)
    area = _local_live_context_area(text)
    metric = _local_live_context_metric(normalized)
    device_hint = ""
    if "空调" in text:
        domain = "climate"
        device_hint = "空调"
    else:
        domain = "sensor"
    return {
        "area": area,
        "metric": metric,
        "domain": domain,
        "device_hint": device_hint,
    }


def _local_live_context_area(text: str) -> str:
    for area in sorted(_HOME_AREA_HINTS, key=len, reverse=True):
        if area in text:
            return area
    return ""


def _local_live_context_metric(normalized: str) -> str:
    metric_terms = (
        ("air_quality", ("空气质量", "空气怎么样")),
        ("pm25", ("pm25", "pm2.5", "雾霾")),
        ("eco2", ("eco2",)),
        ("co2", ("co2", "二氧化碳")),
        ("tvoc", ("tvoc", "甲醛", "挥发")),
        ("temperature", ("温度", "气温", "几度", "冷不冷", "热不热")),
        ("humidity", ("湿度",)),
        ("weather", ("天气",)),
    )
    for metric, terms in metric_terms:
        if any(term in normalized for term in terms):
            return metric
    return "state"


def _tool_call_fingerprint(tool_call: llm.ToolInput) -> tuple[str, str]:
    """Return a stable per-turn fingerprint for duplicate tool suppression."""
    if tool_call.tool_name == LIVE_CONTEXT_TOOL_NAME:
        return (tool_call.tool_name, "*")
    return (
        tool_call.tool_name,
        json.dumps(
            tool_call.tool_args,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ),
    )


def _duplicate_tool_reason(
    tool_call: llm.ToolInput,
    tool_counts: dict[tuple[str, str], int],
) -> str | None:
    """Return a trace reason if this tool call should be suppressed."""
    if _is_action_tool(tool_call.tool_name):
        return None
    if (
        tool_counts.get(_tool_call_fingerprint(tool_call), 0)
        < SAME_TOOL_SAME_ARGS_LIMIT
    ):
        return None
    if tool_call.tool_name == LIVE_CONTEXT_TOOL_NAME:
        return "duplicate_live_context"
    if tool_call.tool_name == SEARCH_TOOL_NAME:
        return "duplicate_search"
    return "duplicate_tool"


def _record_tool_calls(
    tool_calls: list[llm.ToolInput],
    tool_counts: dict[tuple[str, str], int],
) -> None:
    """Record executed non-action tool calls for per-turn duplicate detection."""
    for tool_call in tool_calls:
        if _is_action_tool(tool_call.tool_name):
            continue
        fingerprint = _tool_call_fingerprint(tool_call)
        tool_counts[fingerprint] = tool_counts.get(fingerprint, 0) + 1


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
        self._pending_tasks: dict[str, PendingTask] = {}
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

    async def _async_handle_message(  # noqa: C901, PLR0911, PLR0912, PLR0915
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog,
    ) -> conversation.ConversationResult:
        """Process one user turn."""
        started = time.monotonic()
        options = self.entry.options
        runtime = self.entry.runtime_data
        run_id = runtime.voice_runs.start(
            conversation_id=user_input.conversation_id,
            user_text=user_input.text,
        )
        turn_start = runtime.turn_controller.start(run_id)
        turn_token = turn_start.token
        self._mark_run(
            runtime,
            run_id,
            "turn_started",
            attrs=turn_start.as_dict(),
        )
        if turn_start.cancelled_turn_id:
            runtime.voice_runs.mark(
                turn_start.cancelled_turn_id,
                "turn_cancelled",
                status="cancelled",
                attrs={
                    "reason": turn_start.cancel_reason,
                    "superseded_by": run_id,
                    "generation": turn_token.generation,
                },
            )
            await self._async_request_local_barge_in(
                runtime,
                run_id,
                turn_start.cancelled_turn_id,
            )
        self._mark_run(
            runtime,
            run_id,
            "speech_captured",
            attrs={"short_text": "已听到。"},
        )
        try:
            await chat_log.async_provide_llm_data(
                user_input.as_llm_context(DOMAIN),
                options.get(CONF_LLM_HASS_API),
                options.get(CONF_PROMPT),
                user_input.extra_system_prompt,
            )
        except conversation.ConverseError as err:
            self._mark_run(
                runtime,
                run_id,
                "llm_data",
                status="error",
                attrs={"error": type(err).__name__},
            )
            runtime.voice_runs.finish(
                run_id,
                status="error",
                latency_ms=int((time.monotonic() - started) * 1000),
            )
            runtime.turn_controller.finish(turn_token)
            return err.as_conversation_result()
        _insert_system_once(chat_log.content, VOICE_RESPONSE_CONTRACT, index=1)
        self._mark_run(runtime, run_id, "llm_data")
        pending_key = user_input.conversation_id or self.entry.entry_id
        pending_resolution = resolve_pending_task(
            user_input.text,
            self._pending_tasks.get(pending_key),
        )
        effective_text = pending_resolution.effective_text or user_input.text
        if pending_resolution.relation != "new_task":
            self._mark_run(
                runtime,
                run_id,
                "pending_state_resolver",
                attrs=pending_resolution.as_dict(),
            )
        if pending_resolution.relation == "cancellation":
            self._pending_tasks.pop(pending_key, None)
            async for _tool_result in chat_log.async_add_assistant_content(
                conversation.AssistantContent(
                    agent_id=self.entity_id,
                    content=pending_resolution.prompt or "好的，已取消。",
                )
            ):
                pass
            return await self._async_finalize_turn(
                user_input,
                chat_log,
                started,
                {"kind": "local_dialogue_control", "model": "pending_state_resolver"},
                run_id,
                turn_token,
            )
        if pending_resolution.relation == "permission":
            async for _tool_result in chat_log.async_add_assistant_content(
                conversation.AssistantContent(
                    agent_id=self.entity_id,
                    content=pending_resolution.prompt or "你想查哪个地方？",
                )
            ):
                pass
            return await self._async_finalize_turn(
                user_input,
                chat_log,
                started,
                {"kind": "local_dialogue_followup", "model": "pending_state_resolver"},
                run_id,
                turn_token,
            )
        if pending_resolution.relation == "slot_fill":
            self._pending_tasks.pop(pending_key, None)
            _insert_system_once(
                chat_log.content,
                f"Resolved follow-up request: {effective_text}",
                index=1,
            )

        route_decision = decide_route(effective_text)
        self._mark_run(
            runtime,
            run_id,
            "route_decision",
            attrs={
                **route_decision.as_dict(),
                "effective_text": effective_text,
                "dialogue_relation": pending_resolution.relation,
            },
        )

        local_control_speech = await async_handle_voice_runtime_command(
            self.hass, user_input.text
        )
        if local_control_speech is not None:
            self._mark_run(runtime, run_id, "local_control")
            async for _tool_result in chat_log.async_add_assistant_content(
                conversation.AssistantContent(
                    agent_id=self.entity_id,
                    content=local_control_speech,
                )
            ):
                pass
            return await self._async_finalize_turn(
                user_input,
                chat_log,
                started,
                {
                    "kind": "local_control",
                    "model": "voice_runtime_control",
                    "max_tokens": 0,
                    "timeout_s": 0,
                    "async_deep_task": False,
                    "route_decision": route_decision.as_dict(),
                },
                run_id,
                turn_token,
            )

        first_response = decide_first_response(effective_text)
        self._mark_run(
            runtime,
            run_id,
            "first_response",
            attrs=first_response.as_dict(),
        )
        multi_intent_plan = plan_multi_intent(effective_text)
        if multi_intent_plan.is_multi_intent:
            multi_intent_result = await self._async_try_multi_intent(
                user_input,
                chat_log,
                started,
                first_response,
                route_decision,
                multi_intent_plan,
                run_id,
                turn_token,
            )
            if multi_intent_result is not None:
                return multi_intent_result
        if (
            route_decision.next_action == "execute_local"
            and route_decision.route == "local_action"
        ):
            local_capability_result = await async_try_execute_local_capability(
                self.hass,
                effective_text,
                route_decision,
            )
            if local_capability_result is not None and local_capability_result.handled:
                self._mark_run(
                    runtime,
                    run_id,
                    "local_capability_execute",
                    status=(
                        "ok"
                        if local_capability_result.status == "executed"
                        else local_capability_result.status
                    ),
                    attrs=local_capability_result.trace_attrs(),
                )
                async for _tool_result in chat_log.async_add_assistant_content(
                    conversation.AssistantContent(
                        agent_id=self.entity_id,
                        content=local_capability_result.speech,
                    )
                ):
                    pass
                return await self._async_finalize_turn(
                    user_input,
                    chat_log,
                    started,
                    _local_route_trace(
                        "local_action",
                        "capability_executor",
                        first_response,
                        route_decision,
                    ),
                    run_id,
                    turn_token,
                )
            self._mark_run(
                runtime,
                run_id,
                "local_capability_execute",
                status="error",
                attrs={
                    **route_decision.as_dict(),
                    "reason": "executor_not_applicable",
                    "llm_used": False,
                },
            )
            async for _tool_result in chat_log.async_add_assistant_content(
                conversation.AssistantContent(
                    agent_id=self.entity_id,
                    content="这个操作我还不能本地执行，请换个说法。",
                )
            ):
                pass
            return await self._async_finalize_turn(
                user_input,
                chat_log,
                started,
                _local_route_trace(
                    "local_action",
                    "capability_executor",
                    first_response,
                    route_decision,
                ),
                run_id,
                turn_token,
            )
        if route_decision.next_action in {"ask_location_permission", "clarify"}:
            prompt = (
                route_decision.user_visible_prompt
                or "我还不确定你想让我做什么，可以换个说法吗？"
            )
            pending = pending_task_from_route(run_id, route_decision)
            if pending is not None:
                self._pending_tasks[pending_key] = pending
            self._mark_run(
                runtime,
                run_id,
                "local_route_clarify",
                attrs={
                    **route_decision.as_dict(),
                    "pending_task": pending.as_dict() if pending else {},
                    "interaction_state": "awaiting_user_info",
                    "llm_used": False,
                    "tools_used": [],
                    "tools_used_count": 0,
                },
            )
            async for _tool_result in chat_log.async_add_assistant_content(
                conversation.AssistantContent(
                    agent_id=self.entity_id,
                    content=prompt,
                )
            ):
                pass
            return await self._async_finalize_turn(
                user_input,
                chat_log,
                started,
                _local_route_trace(
                    "local_clarify",
                    "capability_router",
                    first_response,
                    route_decision,
                ),
                run_id,
                turn_token,
            )
        if first_response.task_type in INVENTORY_TASK_TYPES:
            inventory = render_device_inventory(
                effective_text,
                chat_log.content,
            )
            if inventory:
                self._mark_run(
                    runtime,
                    run_id,
                    "local_inventory_render",
                    attrs=inventory.trace_attrs(),
                )
                async for _tool_result in chat_log.async_add_assistant_content(
                    conversation.AssistantContent(
                        agent_id=self.entity_id,
                        content=inventory.speech,
                    )
                ):
                    pass
                return await self._async_finalize_turn(
                    user_input,
                    chat_log,
                    started,
                    {
                        "kind": "local_static_context",
                        "model": "device_inventory_renderer",
                        "max_tokens": 0,
                        "timeout_s": 0,
                        "async_deep_task": False,
                        "first_response": first_response.as_dict(),
                        "route_decision": route_decision.as_dict(),
                    },
                    run_id,
                    turn_token,
                )
        if local_answer := stable_fact_answer(effective_text):
            self._mark_run(
                runtime,
                run_id,
                "local_stable_answer",
                attrs={"source": "local_knowledge_cache"},
            )
            async for _tool_result in chat_log.async_add_assistant_content(
                conversation.AssistantContent(
                    agent_id=self.entity_id,
                    content=local_answer,
                )
            ):
                pass
            return await self._async_finalize_turn(
                user_input,
                chat_log,
                started,
                {
                    "kind": "local_stable_fact",
                    "model": "local_knowledge_cache",
                    "max_tokens": 0,
                    "timeout_s": 0,
                    "async_deep_task": False,
                    "first_response": first_response.as_dict(),
                    "route_decision": route_decision.as_dict(),
                },
                run_id,
                turn_token,
            )

        if route_decision.next_action == "call_tool_then_local_render":
            local_live_result = await self._async_try_local_live_context(
                user_input,
                chat_log,
                started,
                first_response,
                route_decision,
                run_id,
                turn_token,
            )
            if local_live_result is not None:
                return local_live_result

        route = select_model_route(effective_text, options)
        self._mark_run(
            runtime,
            run_id,
            "route_selected",
            attrs={
                "route": route.kind,
                "model": route.model,
                "timeout_s": route.timeout_s,
            },
        )
        self._inject_memory_context(chat_log, runtime, user_input.conversation_id)

        if route.async_deep_task:
            messages = _content_to_messages(chat_log.content)
            task_id = runtime.deep_tasks.submit(
                route=route,
                messages=messages,
                user_text=effective_text,
                temperature=options.get(CONF_TEMPERATURE, RECOMMENDED_TEMPERATURE),
                top_p=options.get(CONF_TOP_P, RECOMMENDED_TOP_P),
            )
            LOGGER.info(
                "Submitted deep task task_id=%s model=%s messages=%d",
                task_id,
                route.model,
                len(messages),
            )
            self._mark_run(
                runtime,
                run_id,
                "deep_task_submitted",
                attrs={"task_id": task_id, "model": route.model},
            )
            provider_runs: list[dict[str, Any]] = [
                {
                    "iteration": 0,
                    "provider": {
                        "name": "background",
                        "model": route.model,
                        "fallback_used": False,
                        "fallback_reason": "",
                    },
                    "attempts": [],
                    "task_id": task_id,
                }
            ]
            async for _tool_result in chat_log.async_add_assistant_content(
                conversation.AssistantContent(
                    agent_id=self.entity_id,
                    content=DEEP_TASK_ACK_SPEECH,
                )
            ):
                pass
        else:
            provider_runs = await self._async_run_chat_log(
                chat_log,
                route,
                effective_text,
                run_id,
                first_response,
                turn_token,
            )

        return await self._async_finalize_turn(
            user_input,
            chat_log,
            started,
            _route_trace(route, provider_runs, route_decision),
            run_id,
            turn_token,
        )

    async def _async_try_local_live_context(  # noqa: PLR0913
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog,
        started: float,
        first_response: FirstResponseDecision,
        route_decision: RouteDecision,
        run_id: str,
        turn_token: TurnToken,
    ) -> conversation.ConversationResult | None:
        """Execute GetLiveContext locally and render scalar state without an LLM."""
        runtime = self.entry.runtime_data
        if not _chat_log_has_tool(chat_log, LIVE_CONTEXT_TOOL_NAME):
            self._mark_run(
                runtime,
                run_id,
                "local_live_context_unavailable",
                attrs={
                    "reason": "missing_GetLiveContext_tool",
                    "llm_used": False,
                    "route": route_decision.route,
                },
            )
            return None

        tool_args = _local_live_context_tool_args(user_input.text)
        slots = _local_live_context_slots(user_input.text)
        tool_call = llm.ToolInput(
            id=ulid.ulid_now(),
            tool_name=LIVE_CONTEXT_TOOL_NAME,
            tool_args=tool_args,
        )
        self._mark_run(
            runtime,
            run_id,
            "local_live_context_call",
            attrs={
                "name": LIVE_CONTEXT_TOOL_NAME,
                "args": tool_args,
                "slots": slots,
                "llm_used": False,
                "tools_used": [LIVE_CONTEXT_TOOL_NAME],
            },
        )
        try:
            async for tool_result in chat_log.async_add_assistant_content(
                conversation.AssistantContent(
                    agent_id=self.entity_id,
                    content=None,
                    tool_calls=[tool_call],
                )
            ):
                result = tool_result.tool_result
                self._mark_run(
                    runtime,
                    run_id,
                    "tool_result",
                    status="error" if "error" in result else "ok",
                    attrs={
                        "name": tool_result.tool_name,
                        "iteration": 0,
                        "local_live_context": True,
                    },
                )
                if "error" in result:
                    self._mark_run(
                        runtime,
                        run_id,
                        "local_live_context_failed",
                        status="error",
                        attrs={
                            "error": str(result.get("error") or ""),
                            "llm_used": False,
                        },
                    )
                    break
                local_state = render_scalar_state_answer(
                    user_input.text,
                    result,
                    task_type=first_response.task_type,
                    route_decision=route_decision,
                )
                if local_state is not None:
                    self._mark_run(
                        runtime,
                        run_id,
                        "local_state_render",
                        attrs=local_state.trace_attrs(),
                    )
                    async for _tool_result in chat_log.async_add_assistant_content(
                        conversation.AssistantContent(
                            agent_id=self.entity_id,
                            content=local_state.speech,
                        )
                    ):
                        pass
                    return await self._async_finalize_turn(
                        user_input,
                        chat_log,
                        started,
                        _local_route_trace(
                            "local_live_context",
                            "live_context_renderer",
                            first_response,
                            route_decision,
                        ),
                        run_id,
                        turn_token,
                    )
        except (HomeAssistantError, ValueError) as err:
            self._mark_run(
                runtime,
                run_id,
                "local_live_context_failed",
                status="error",
                attrs={
                    "error": type(err).__name__,
                    "llm_used": False,
                },
            )

        fallback = _empty_response_fallback(first_response)
        self._mark_run(
            runtime,
            run_id,
            "local_state_render",
            status="error",
            attrs={
                "reason": "no_renderable_state",
                "llm_final_used": False,
                "source": "GetLiveContext",
            },
        )
        async for _tool_result in chat_log.async_add_assistant_content(
            conversation.AssistantContent(
                agent_id=self.entity_id,
                content=fallback,
            )
        ):
            pass
        return await self._async_finalize_turn(
            user_input,
            chat_log,
            started,
            _local_route_trace(
                "local_live_context",
                "live_context_renderer",
                first_response,
                route_decision,
            ),
            run_id,
            turn_token,
        )

    async def _async_try_multi_intent(  # noqa: PLR0911, PLR0913
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog,
        started: float,
        first_response: FirstResponseDecision,
        route_decision: RouteDecision,
        multi_intent_plan: MultiIntentPlan,
        run_id: str,
        turn_token: TurnToken,
    ) -> conversation.ConversationResult | None:
        """Execute supported local subtasks and compose one short spoken answer."""
        runtime = self.entry.runtime_data
        if not _multi_intent_is_local(multi_intent_plan):
            return None
        if any(
            subtask.route_decision.next_action == "call_tool_then_local_render"
            for subtask in multi_intent_plan.subtasks
        ) and not _chat_log_has_tool(chat_log, LIVE_CONTEXT_TOOL_NAME):
            return None

        self._mark_run(
            runtime,
            run_id,
            "multi_intent_plan",
            attrs=multi_intent_plan.as_dict(),
        )
        final_must_cover = _final_must_cover(multi_intent_plan)
        subanswers: list[str] = []
        subtask_traces: list[dict[str, Any]] = []
        for subtask in multi_intent_plan.subtasks:
            decision = subtask.route_decision
            if decision.task_type in INVENTORY_TASK_TYPES:
                inventory = render_device_inventory(subtask.text, chat_log.content)
                if inventory is None:
                    return None
                self._mark_run(
                    runtime,
                    run_id,
                    "local_inventory_render",
                    attrs={
                        **inventory.trace_attrs(),
                        "subtask_index": subtask.index,
                        "subtask_text": subtask.text,
                    },
                )
                subanswers.append(inventory.speech)
                subtask_traces.append(subtask.as_dict())
                continue

            if decision.next_action != "call_tool_then_local_render":
                return None
            tool_args = _local_live_context_tool_args(subtask.text)
            tool_call = llm.ToolInput(
                id=ulid.ulid_now(),
                tool_name=LIVE_CONTEXT_TOOL_NAME,
                tool_args=tool_args,
            )
            self._mark_run(
                runtime,
                run_id,
                "local_live_context_call",
                attrs={
                    "name": LIVE_CONTEXT_TOOL_NAME,
                    "args": tool_args,
                    "subtask_index": subtask.index,
                    "subtask_text": subtask.text,
                    "llm_used": False,
                    "tools_used": [LIVE_CONTEXT_TOOL_NAME],
                },
            )
            llm_api = chat_log.llm_api
            if llm_api is None:
                return None
            try:
                result = await llm_api.async_call_tool(tool_call)
            except (HomeAssistantError, ValueError) as err:
                self._mark_run(
                    runtime,
                    run_id,
                    "tool_result",
                    status="error",
                    attrs={
                        "name": LIVE_CONTEXT_TOOL_NAME,
                        "iteration": 0,
                        "local_live_context": True,
                        "subtask_index": subtask.index,
                        "error": type(err).__name__,
                    },
                )
                return None
            self._mark_run(
                runtime,
                run_id,
                "tool_result",
                status="error" if "error" in result else "ok",
                attrs={
                    "name": LIVE_CONTEXT_TOOL_NAME,
                    "iteration": 0,
                    "local_live_context": True,
                    "subtask_index": subtask.index,
                },
            )
            rendered = None
            if "error" not in result:
                rendered = render_scalar_state_answer(
                    subtask.text,
                    result,
                    task_type=decision.task_type,
                    route_decision=decision,
                )
            if rendered is None:
                return None
            self._mark_run(
                runtime,
                run_id,
                "local_state_render",
                status="ok" if rendered.answerable else "error",
                attrs={
                    **rendered.trace_attrs(),
                    "subtask_index": subtask.index,
                    "subtask_text": subtask.text,
                },
            )
            subanswers.append(rendered.speech)
            subtask_traces.append(subtask.as_dict())

        speech = _compose_spoken_subanswers(subanswers)
        if not speech:
            return None
        self._mark_run(
            runtime,
            run_id,
            "spoken_answer_composer",
            attrs={
                "subanswer_count": len(subanswers),
                "llm_final_used": False,
                "subtasks": subtask_traces,
                "final_must_cover": final_must_cover,
            },
        )
        async for _tool_result in chat_log.async_add_assistant_content(
            conversation.AssistantContent(agent_id=self.entity_id, content=speech)
        ):
            pass
        return await self._async_finalize_turn(
            user_input,
            chat_log,
            started,
            {
                "kind": "local_multi_intent",
                "model": "spoken_answer_composer",
                "max_tokens": 0,
                "timeout_s": 0,
                "async_deep_task": False,
                "first_response": first_response.as_dict(),
                "route_decision": {
                    **route_decision.as_dict(),
                    "metadata": {
                        **dict(route_decision.metadata),
                        "multi_intent": True,
                        "subtasks": subtask_traces,
                        "final_must_cover": final_must_cover,
                    },
                },
            },
            run_id,
            turn_token,
        )

    async def _async_finalize_turn(  # noqa: PLR0913
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog,
        started: float,
        route_trace: dict[str, Any],
        run_id: str,
        turn_token: TurnToken,
    ) -> conversation.ConversationResult:
        """Build the HA result, clean TTS, and record diagnostics."""
        options = self.entry.options
        runtime = self.entry.runtime_data
        if not runtime.turn_controller.is_current(turn_token):
            return await self._async_finalize_stale_turn(
                user_input,
                chat_log,
                started,
                route_trace,
                run_id,
                turn_token,
            )
        result = conversation.async_get_result_from_chat_log(user_input, chat_log)
        raw_spoken = result.response.speech.get("plain", {}).get("speech", "")
        first_response = decide_first_response(user_input.text)
        if not raw_spoken.strip():
            fallback_spoken = _empty_response_fallback(first_response)
            if fallback_spoken:
                raw_spoken = fallback_spoken
                result.response.async_set_speech(raw_spoken)
                self._mark_run(
                    runtime,
                    run_id,
                    "fallback_final",
                    attrs={
                        "reason": "empty_response",
                        "task_type": first_response.task_type,
                    },
                )

        grounding = await _async_grounding_for_turn(
            runtime,
            options,
            user_input.text,
            raw_spoken,
            chat_log.content,
        )
        grounded_spoken = grounding.text
        if grounding.status != "not_required":
            self._mark_run(
                runtime,
                run_id,
                "cheap_grounding",
                status="error"
                if grounding.status
                in {"no_answer", "no_evidence", "unsupported", "verifier_error"}
                else "ok",
                attrs=grounding.as_dict(),
            )
        if grounded_spoken:
            max_sentences = 4 if route_trace.get("kind") == "local_multi_intent" else 2
            result.response.async_set_speech(
                markdown_to_spoken_text(grounded_spoken, max_sentences=max_sentences)
            )
            self._mark_run(runtime, run_id, "tts_cleaned")
        assistant_text = result.response.speech.get("plain", {}).get("speech", "")
        await runtime.memory.async_record_turn(
            user_input.conversation_id,
            user_input.text,
            assistant_text,
        )
        latency_ms = int((time.monotonic() - started) * 1000)
        status = _trace_status(assistant_text)
        self._final_feedback(runtime, run_id, status, latency_ms, assistant_text)
        timeline = runtime.voice_runs.finish(
            run_id,
            status=status,
            route=str(route_trace.get("kind") or ""),
            provider=str((route_trace.get("provider") or {}).get("name") or ""),
            latency_ms=latency_ms,
        )
        await runtime.trace_store.async_record_turn(
            options,
            TraceTurn(
                conversation_id=user_input.conversation_id,
                user_text=user_input.text,
                assistant_text=assistant_text,
                route=route_trace,
                latency_ms=latency_ms,
                status=status,
                timeline=timeline,
                raw_payload={
                    "input": {
                        "text": user_input.text,
                        "conversation_id": user_input.conversation_id or "",
                        "language": getattr(user_input, "language", "") or "",
                        "device_id": getattr(user_input, "device_id", "") or "",
                    },
                    "route": route_trace,
                    "timeline": timeline,
                    "tool_events": _tool_events_from_content(
                        chat_log.content,
                        user_input.text,
                    ),
                    "messages": _content_to_messages(chat_log.content),
                    "speech": {
                        "raw": raw_spoken,
                        "grounded": grounded_spoken,
                        "final": assistant_text,
                        "tts_cleaned": bool(raw_spoken),
                    },
                    "grounding": grounding.as_dict(),
                    "earcon_events": runtime.feedback.earcons_for_turn(run_id),
                    "display_status_events": runtime.feedback.display_events_for_turn(
                        run_id
                    ),
                    "first_response_audio_events": (
                        runtime.feedback.first_response_audio_for_turn(run_id)
                    ),
                },
                run_id=run_id,
            ),
        )
        runtime.turn_controller.finish(turn_token)
        return result

    async def _async_finalize_stale_turn(  # noqa: PLR0913
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog,
        started: float,
        route_trace: dict[str, Any],
        run_id: str,
        turn_token: TurnToken,
    ) -> conversation.ConversationResult:
        """Finish a stale turn without emitting user-visible output."""
        options = self.entry.options
        runtime = self.entry.runtime_data
        attrs = runtime.turn_controller.stale_attrs(turn_token)
        self._mark_run(
            runtime,
            run_id,
            "stale_result_discarded",
            status="cancelled",
            attrs=attrs,
        )
        latency_ms = int((time.monotonic() - started) * 1000)
        timeline = runtime.voice_runs.finish(
            run_id,
            status="cancelled",
            route=str(route_trace.get("kind") or "cancelled"),
            provider="turn_controller",
            latency_ms=latency_ms,
        )
        await runtime.trace_store.async_record_turn(
            options,
            TraceTurn(
                conversation_id=user_input.conversation_id,
                user_text=user_input.text,
                assistant_text="",
                route={**route_trace, "cancelled": True, "turn": attrs},
                latency_ms=latency_ms,
                status="cancelled",
                timeline=timeline,
                raw_payload={
                    "input": {
                        "text": user_input.text,
                        "conversation_id": user_input.conversation_id or "",
                        "language": getattr(user_input, "language", "") or "",
                        "device_id": getattr(user_input, "device_id", "") or "",
                    },
                    "route": {**route_trace, "cancelled": True, "turn": attrs},
                    "timeline": timeline,
                    "tool_events": _tool_events_from_content(
                        chat_log.content,
                        user_input.text,
                    ),
                    "messages": _content_to_messages(chat_log.content),
                    "speech": {
                        "raw": "",
                        "grounded": "",
                        "final": "",
                        "tts_cleaned": False,
                    },
                    "grounding": {"status": "not_required"},
                    "earcon_events": runtime.feedback.earcons_for_turn(run_id),
                    "display_status_events": runtime.feedback.display_events_for_turn(
                        run_id
                    ),
                    "first_response_audio_events": (
                        runtime.feedback.first_response_audio_for_turn(run_id)
                    ),
                },
                run_id=run_id,
            ),
        )
        response = IntentResponse(language=getattr(user_input, "language", "") or "zh")
        return conversation.ConversationResult(
            response=response,
            conversation_id=user_input.conversation_id,
        )

    def _mark_run(
        self,
        runtime: LLMGatewayRuntimeData,
        run_id: str,
        stage: str,
        *,
        status: str = "ok",
        attrs: dict[str, Any] | None = None,
    ) -> None:
        """Record a timeline event and deterministic feedback side effects."""
        event = runtime.voice_runs.mark(run_id, stage, status=status, attrs=attrs)
        if event is None:
            return
        event_attrs = event.get("attrs") if isinstance(event.get("attrs"), dict) else {}
        if stage == "first_response" and (
            event_attrs.get("spoken_hint") or event_attrs.get("audio_suppressed_reason")
        ):
            runtime.first_response_player.schedule(
                turn_id=run_id,
                t_ms=int(event.get("t_ms") or 0),
                attrs=event_attrs,
                marker=runtime.voice_runs.mark,
            )
        earcon, display = VoiceFeedbackPolicy(runtime.feedback).pipeline_event(
            turn_id=run_id,
            stage=stage,
            t_ms=int(event.get("t_ms") or 0),
            status=str(event.get("status") or status),
            attrs=event_attrs,
        )
        if earcon or display:
            runtime.voice_runs.mark(
                run_id,
                "feedback",
                attrs=feedback_trace_attrs(earcon, display),
            )

    def _final_feedback(
        self,
        runtime: LLMGatewayRuntimeData,
        run_id: str,
        status: str,
        latency_ms: int,
        assistant_text: str,
    ) -> None:
        """Emit final display feedback after the spoken result is known."""
        display = VoiceFeedbackPolicy(runtime.feedback).final_status(
            turn_id=run_id,
            status=status,
            t_ms=latency_ms,
            short_text=assistant_text,
        )
        runtime.voice_runs.mark(
            run_id,
            "display_status",
            attrs={
                "display_state": display.get("state"),
                "short_text": display.get("short_text"),
                "deep_link": display.get("deep_link"),
            },
        )

    async def _async_request_local_barge_in(
        self,
        runtime: LLMGatewayRuntimeData,
        run_id: str,
        previous_turn_id: str,
    ) -> None:
        """Ask the local display-agent adapter to stop old playback."""
        service_domain = "rest_command"
        service_name = "kukui_voice_barge_in"
        attrs = {
            "service": f"{service_domain}.{service_name}",
            "previous_turn_id": previous_turn_id,
            "new_turn_id": run_id,
        }
        if not self.hass.services.has_service(service_domain, service_name):
            self._mark_run(
                runtime,
                run_id,
                "barge_in_requested",
                status="error",
                attrs={**attrs, "reason": "missing_local_barge_in_service"},
            )
            return
        try:
            await self.hass.services.async_call(
                service_domain,
                service_name,
                {
                    "reason": "superseded_by_new_turn",
                    "previous_turn_id": previous_turn_id,
                    "new_turn_id": run_id,
                },
                blocking=False,
            )
        except (HomeAssistantError, ValueError, TypeError) as err:
            self._mark_run(
                runtime,
                run_id,
                "barge_in_requested",
                status="error",
                attrs={**attrs, "reason": type(err).__name__},
            )
            return
        self._mark_run(runtime, run_id, "barge_in_requested", attrs=attrs)

    def _inject_memory_context(
        self,
        chat_log: conversation.ChatLog,
        runtime: LLMGatewayRuntimeData,
        conversation_id: str | None,
    ) -> None:
        """Append compact local memory into the model context."""
        memory_context = runtime.memory.build_context(conversation_id)
        if memory_context:
            _insert_system_once(chat_log.content, memory_context, index=1)

    async def _async_run_chat_log(  # noqa: C901, PLR0911, PLR0912, PLR0913, PLR0915
        self,
        chat_log: conversation.ChatLog,
        route: ModelRoute,
        user_text: str,
        run_id: str,
        first_response: FirstResponseDecision,
        turn_token: TurnToken,
    ) -> list[dict[str, Any]]:
        """Drive the model, executing tool calls until it returns a final answer."""
        runtime = self.entry.runtime_data
        client: LLMGatewayClient = runtime.client
        options = self.entry.options
        provider_runs: list[dict[str, Any]] = []

        tools: list[dict[str, Any]] | None = None
        if chat_log.llm_api:
            tools = [
                _format_tool(tool, chat_log.llm_api.custom_serializer)
                for tool in chat_log.llm_api.tools
            ]
        search_tools = available_search_tools(options)
        if search_tools:
            tools = [*(tools or []), *search_tools]
        route_decision = decide_route(user_text)
        tools = _filter_visible_tools(tools, route_decision)
        self._mark_run(
            runtime,
            run_id,
            "visible_tool_schema",
            attrs={
                "allowed_tools": list(route_decision.allowed_tools),
                "visible_tool_schema": [_tool_name(tool) for tool in tools or []],
                "task_type": route_decision.task_type,
            },
        )

        force_tool_call = False
        force_final = False
        forced_final_contract_added = False
        tool_counts: dict[tuple[str, str], int] = {}
        for iteration in range(1, MAX_TOOL_ITERATIONS + 1):
            if not runtime.turn_controller.is_current(turn_token):
                self._mark_run(
                    runtime,
                    run_id,
                    "backend_tasks_cancelled",
                    status="cancelled",
                    attrs={
                        "reason": "stale_before_provider",
                        **runtime.turn_controller.stale_attrs(turn_token),
                    },
                )
                return provider_runs
            if force_final and not forced_final_contract_added:
                chat_log.content.append(
                    conversation.SystemContent(content=FORCED_FINAL_CONTRACT)
                )
                forced_final_contract_added = True
            effective_tools = None if force_final else tools
            messages = _content_to_messages(chat_log.content)
            LOGGER.info(
                "Conversation model turn iteration=%d route=%s model=%s "
                "messages=%d tools=%d forced_final=%s",
                iteration,
                route.kind,
                route.model,
                len(messages),
                len(effective_tools or []),
                force_final,
            )
            self._mark_run(
                runtime,
                run_id,
                "llm_iteration_start",
                attrs={
                    "iteration": iteration,
                    "route": route.kind,
                    "model": route.model,
                    "forced_final": force_final,
                },
            )
            try:
                tool_choice = (
                    "none"
                    if force_final
                    else _tool_choice_for_turn(
                        user_text,
                        effective_tools,
                        force_tool_call=force_tool_call,
                        force_live_context=(
                            _is_live_context_task_type(first_response.task_type)
                            and iteration == 1
                        ),
                        require_grounding=iteration == 1,
                    )
                )
                fallback_result = await async_chat_completion_with_fallback(
                    session=runtime.session,
                    primary_client=client,
                    route=route,
                    options=options,
                    messages=messages,
                    tools=effective_tools,
                    tool_choice=tool_choice,
                    temperature=options.get(CONF_TEMPERATURE, RECOMMENDED_TEMPERATURE),
                    top_p=options.get(CONF_TOP_P, RECOMMENDED_TOP_P),
                    selector=runtime.provider_selector,
                    processing_cue_delay_s=first_response.processing_cue_delay_s,
                )
                message = fallback_result.message
                self._mark_run(
                    runtime,
                    run_id,
                    "provider_complete",
                    attrs={
                        "iteration": iteration,
                        "provider": fallback_result.provider.get("name"),
                        "fallback_used": fallback_result.provider.get("fallback_used"),
                        "attempts": len(fallback_result.attempts),
                    },
                )
                provider_runs.append(
                    {
                        "iteration": iteration,
                        "provider": fallback_result.provider,
                        "attempts": fallback_result.attempts,
                    }
                )
                if not runtime.turn_controller.is_current(turn_token):
                    self._mark_run(
                        runtime,
                        run_id,
                        "backend_tasks_cancelled",
                        status="cancelled",
                        attrs={
                            "reason": "stale_after_provider",
                            "iteration": iteration,
                            **runtime.turn_controller.stale_attrs(turn_token),
                        },
                    )
                    return provider_runs
            except LLMGatewayError as err:
                LOGGER.error("Error talking to the gateway: %s", err)
                self._mark_run(
                    runtime,
                    run_id,
                    "provider_error",
                    status="error",
                    attrs={"error": type(err).__name__},
                )
                error_content = conversation.AssistantContent(
                    agent_id=self.entity_id,
                    content=GATEWAY_ERROR_SPEECH,
                )
                async for _tool_result in chat_log.async_add_assistant_content(
                    error_content
                ):
                    pass
                return provider_runs

            content = conversation.AssistantContent(
                agent_id=self.entity_id,
                content=message.get("content") or None,
                tool_calls=_parse_tool_calls(
                    message.get("tool_calls"),
                    user_text,
                )
                or None,
            )
            if content.tool_calls:
                if not runtime.turn_controller.is_current(turn_token):
                    self._mark_run(
                        runtime,
                        run_id,
                        "backend_tasks_cancelled",
                        status="cancelled",
                        attrs={
                            "reason": "stale_before_tool_execution",
                            "iteration": iteration,
                            **runtime.turn_controller.stale_attrs(turn_token),
                        },
                    )
                    return provider_runs
                if force_final:
                    for tool_call in content.tool_calls:
                        self._mark_run(
                            runtime,
                            run_id,
                            "tool_call_suppressed",
                            status="error",
                            attrs={
                                "iteration": iteration,
                                "name": tool_call.tool_name,
                                "reason": "forced_final_tool_call",
                            },
                        )
                    async for _tool_result in chat_log.async_add_assistant_content(
                        conversation.AssistantContent(
                            agent_id=self.entity_id,
                            content=content.content or TOOL_LOOP_GUARD_SPEECH,
                        )
                    ):
                        pass
                    return provider_runs

                LOGGER.info(
                    "Assistant tool calls iteration=%d names=%s",
                    iteration,
                    ",".join(call.tool_name for call in content.tool_calls),
                )
                self._mark_run(
                    runtime,
                    run_id,
                    "tool_call",
                    attrs={
                        "iteration": iteration,
                        "names": [call.tool_name for call in content.tool_calls],
                    },
                )
                suppressed = [
                    (tool_call, reason)
                    for tool_call in content.tool_calls
                    if (reason := _duplicate_tool_reason(tool_call, tool_counts))
                    is not None
                ]
                if suppressed:
                    for tool_call, reason in suppressed:
                        self._mark_run(
                            runtime,
                            run_id,
                            "tool_call_suppressed",
                            status="error",
                            attrs={
                                "iteration": iteration,
                                "name": tool_call.tool_name,
                                "reason": reason,
                            },
                        )
                    if content.content:
                        async for _tool_result in chat_log.async_add_assistant_content(
                            conversation.AssistantContent(
                                agent_id=self.entity_id,
                                content=content.content,
                            )
                        ):
                            pass
                        return provider_runs
                    force_final = True
                    self._mark_run(
                        runtime,
                        run_id,
                        "forced_final",
                        attrs={"reason": suppressed[0][1], "iteration": iteration},
                    )
                    continue

                policy_block = self._policy_block(content.tool_calls, user_text)
                if policy_block:
                    prompt, block_attrs = policy_block
                    self._mark_run(
                        runtime,
                        run_id,
                        "tool_policy_block",
                        status="error",
                        attrs={"iteration": iteration, **block_attrs},
                    )
                    async for _tool_result in chat_log.async_add_assistant_content(
                        conversation.AssistantContent(
                            agent_id=self.entity_id,
                            content=prompt,
                        )
                    ):
                        pass
                    return provider_runs
                _record_tool_calls(content.tool_calls, tool_counts)
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
                self._mark_run(
                    runtime,
                    run_id,
                    "tool_result",
                    status="error" if "error" in result else "ok",
                    attrs={"name": tool_result.tool_name, "iteration": iteration},
                )
                if (
                    _is_live_context_task_type(first_response.task_type)
                    and tool_result.tool_name == LIVE_CONTEXT_TOOL_NAME
                    and "error" not in result
                ):
                    local_state = render_scalar_state_answer(
                        user_text,
                        result,
                        task_type=first_response.task_type,
                    )
                    if local_state is not None:
                        self._mark_run(
                            runtime,
                            run_id,
                            "local_state_render",
                            attrs=local_state.trace_attrs(),
                        )
                        async for _tool_result in chat_log.async_add_assistant_content(
                            conversation.AssistantContent(
                                agent_id=self.entity_id,
                                content=local_state.speech,
                            )
                        ):
                            pass
                        return provider_runs
                    force_final = True
                    self._mark_run(
                        runtime,
                        run_id,
                        "forced_final",
                        attrs={
                            "reason": "weather_live_context_ready",
                            "iteration": iteration,
                        },
                    )

            if content.tool_calls and not runtime.turn_controller.is_current(
                turn_token
            ):
                self._mark_run(
                    runtime,
                    run_id,
                    "backend_tasks_cancelled",
                    status="cancelled",
                    attrs={
                        "reason": "stale_before_external_tool",
                        "iteration": iteration,
                        **runtime.turn_controller.stale_attrs(turn_token),
                    },
                )
                return provider_runs

            for tool_call in content.tool_calls or []:
                if not tool_call.external:
                    continue
                result = await async_execute_search_tool(
                    runtime.session,
                    options,
                    tool_call,
                )
                self._mark_run(
                    runtime,
                    run_id,
                    "search_result",
                    status="error" if "error" in result else "ok",
                    attrs={"name": tool_call.tool_name, "iteration": iteration},
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
                return provider_runs

        LOGGER.error("Tool-call loop exceeded %d iterations", MAX_TOOL_ITERATIONS)
        error_content = conversation.AssistantContent(
            agent_id=self.entity_id,
            content=TOOL_LOOP_ERROR_SPEECH,
        )
        async for _tool_result in chat_log.async_add_assistant_content(error_content):
            pass
        return provider_runs

    def _policy_block(
        self, tool_calls: list[llm.ToolInput], user_text: str
    ) -> tuple[str, dict[str, Any]] | None:
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
            attrs = {
                "tool": tool_call.tool_name,
                "blocked_reason": decision.reason,
                "spoken_prompt": decision.spoken_prompt or "",
                "interaction_state": interaction_state_for_policy_block(
                    decision.reason,
                    decision.metadata,
                ),
                **decision.metadata,
            }
            return decision.spoken_prompt or "当前不能执行这个请求。", attrs
        return None


def _route_trace(
    route: ModelRoute,
    provider_runs: list[dict[str, Any]] | None = None,
    route_decision: RouteDecision | None = None,
) -> dict[str, Any]:
    """Return route metadata safe for diagnostic traces."""
    provider_runs = provider_runs or []
    last_provider = provider_runs[-1]["provider"] if provider_runs else None
    trace = {
        "kind": route.kind,
        "model": route.model,
        "max_tokens": route.max_tokens,
        "timeout_s": route.timeout_s,
        "async_deep_task": route.async_deep_task,
        "provider": last_provider,
        "provider_runs": provider_runs,
        "provider_attempts": [
            {
                **attempt,
                "iteration": run.get("iteration"),
            }
            for run in provider_runs
            for attempt in run.get("attempts", [])
            if isinstance(attempt, dict)
        ],
    }
    if route_decision is not None:
        trace["route_decision"] = route_decision.as_dict()
    return trace


def _local_route_trace(
    kind: str,
    model: str,
    first_response: FirstResponseDecision,
    route_decision: RouteDecision,
) -> dict[str, Any]:
    """Return trace metadata for local capability routes."""
    return {
        "kind": kind,
        "model": model,
        "max_tokens": 0,
        "timeout_s": 0,
        "async_deep_task": False,
        "first_response": first_response.as_dict(),
        "route_decision": route_decision.as_dict(),
    }


def _trace_status(assistant_text: str) -> str:
    """Classify the completed turn for trace filtering."""
    if assistant_text in {
        GATEWAY_ERROR_SPEECH,
        TOOL_LOOP_ERROR_SPEECH,
        TOOL_LOOP_GUARD_SPEECH,
    }:
        return "error"
    if assistant_text == DEEP_TASK_ACK_SPEECH:
        return "queued"
    return "complete"


def _empty_response_fallback(first_response: FirstResponseDecision) -> str:
    """Return a short safe fallback for task types that must not go silent."""
    if first_response.task_type in {"weather_query", "outdoor_current_weather_query"}:
        return WEATHER_CONTEXT_FALLBACK_SPEECH
    if first_response.task_type in {
        "home_state",
        "indoor_environment_query",
        "home_temperature_summary",
    }:
        return HOME_STATE_FALLBACK_SPEECH
    if first_response.task_type == "high_risk":
        return first_response.spoken_hint or HIGH_RISK_FALLBACK_SPEECH
    return ""


async def _async_grounding_for_turn(
    _runtime: LLMGatewayRuntimeData,
    _options: dict[str, Any],
    user_text: str,
    assistant_text: str,
    content: list[conversation.Content],
) -> GroundingResult:
    """Run cheap source grounding on the voice critical path."""
    search_results = _search_results_from_content(
        _current_turn_content(content, user_text)
    )
    return initial_grounding_result(user_text, assistant_text, search_results)


def _search_results_from_content(
    content: list[conversation.Content],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for item in content:
        if item.role != "tool_result" or item.tool_name != SEARCH_TOOL_NAME:
            continue
        result = item.tool_result
        if isinstance(result, dict):
            results.append(result)
    return results


def _tool_events_from_content(
    content: list[conversation.Content],
    user_text: str = "",
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for item in _current_turn_content(content, user_text):
        if item.role == "assistant":
            events.extend(
                [
                    {
                        "phase": "call",
                        "tool_call_id": call.id,
                        "name": call.tool_name,
                        "external": bool(getattr(call, "external", False)),
                        "args": call.tool_args,
                    }
                    for call in item.tool_calls or []
                ]
            )
        elif item.role == "tool_result":
            result = item.tool_result if isinstance(item.tool_result, dict) else {}
            events.append(
                {
                    "phase": "result",
                    "tool_call_id": item.tool_call_id,
                    "name": item.tool_name,
                    "status": "error" if "error" in result else "ok",
                    "error": str(result.get("error") or ""),
                    "result": result,
                }
            )
    return events


def _current_turn_content(
    content: list[conversation.Content],
    user_text: str,
) -> list[conversation.Content]:
    """Return chat-log content belonging to the current user turn."""
    if not user_text:
        return content
    for index in range(len(content) - 1, -1, -1):
        item = content[index]
        if item.role == "user" and item.content == user_text:
            return content[index:]
    return content


def _insert_system_once(
    content: list[conversation.Content],
    text: str,
    *,
    index: int,
) -> None:
    """Insert a system prompt only if the same text is not already present."""
    if any(item.role == "system" and item.content == text for item in content):
        return
    content.insert(index, conversation.SystemContent(content=text))
