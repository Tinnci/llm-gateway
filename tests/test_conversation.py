"""Tests for the conversation entity and its helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from homeassistant.components import conversation
from homeassistant.const import CONF_LLM_HASS_API
from homeassistant.core import Context
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import llm

from custom_components.llm_gateway.api import LLMGatewayConnectionError
from custom_components.llm_gateway.const import (
    CONF_DIAGNOSTIC_TRACES,
    CONF_PROVIDER_PROFILES,
    CONF_SEARCH_ENABLED,
    CONF_TAVILY_API_KEY,
    CONF_TRACE_INCLUDE_RAW_MESSAGES,
    DEEP_TASK_ACK_SPEECH,
    DEFAULT_BASE_URL,
    GATEWAY_ERROR_SPEECH,
)
from custom_components.llm_gateway.conversation import (
    LIVE_CONTEXT_TOOL_NAME,
    VOICE_RESPONSE_CONTRACT,
    _async_grounding_for_turn,
    _content_to_messages,
    _duplicate_tool_reason,
    _extra_body_from_options,
    _is_action_tool,
    _normalize_tool_args,
    _parse_tool_calls,
    _record_tool_calls,
    _tool_choice_for_turn,
    _tool_events_from_content,
)
from custom_components.llm_gateway.runtime import TurnController

MODELS_URL = f"{DEFAULT_BASE_URL}/models"
CHAT_URL = f"{DEFAULT_BASE_URL}/chat/completions"
FALLBACK_BASE_URL = "https://fallback.test/v1"
FALLBACK_CHAT_URL = f"{FALLBACK_BASE_URL}/chat/completions"
STATIC_CONTEXT = (
    "Static Context: An overview of the areas and the devices in this smart "
    "home:\n"
    "- names: Homepod mini\n"
    "  domain: media_player\n"
    "  areas: 客厅\n"
    "- names: 客厅灯\n"
    "  domain: light\n"
    "  areas: 客厅\n"
    "- names: Yeelight 显示器挂灯 灯\n"
    "  domain: light\n"
    "  areas: 卧室\n"
    "- names: 卧室空调\n"
    "  domain: climate\n"
    "  areas: 卧室\n"
    "- names: 静安天气 PM2.5\n"
    "  domain: sensor\n"
)
LIVE_CONTEXT_RESULT = {
    "success": True,
    "result": (
        "Live Context: An overview of the areas and the devices in this smart "
        "home:\n"
        "- names: zM1_AD46 温度\n"
        "  domain: sensor\n"
        "  state: '25.5'\n"
        "  areas: 卧室\n"
        "  attributes:\n"
        "    unit_of_measurement: °C\n"
        "- names: zM1_AD46 湿度\n"
        "  domain: sensor\n"
        "  state: '80.2'\n"
        "  areas: 卧室\n"
        "  attributes:\n"
        "    unit_of_measurement: %\n"
    ),
}


async def _setup_agent(hass, mock_config_entry, options=None) -> str:
    mock_config_entry.add_to_hass(hass)
    if options:
        hass.config_entries.async_update_entry(
            mock_config_entry,
            options={**mock_config_entry.options, **options},
        )
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    entities = er.async_entries_for_config_entry(ent_reg, mock_config_entry.entry_id)
    return entities[0].entity_id


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


def test_normalize_live_context_args_removes_tool_name_as_entity_name():
    assert _normalize_tool_args(
        LIVE_CONTEXT_TOOL_NAME,
        {"name": LIVE_CONTEXT_TOOL_NAME, "area": "静安"},
    ) == {"area": "静安"}


def test_normalize_live_context_area_entity_hint_to_name():
    assert _normalize_tool_args(
        LIVE_CONTEXT_TOOL_NAME,
        {"area": "静安天气 PM2.5"},
    ) == {"name": "静安天气 PM2.5"}


def test_normalize_live_context_generic_metric_name_is_not_exact_entity():
    assert _normalize_tool_args(
        LIVE_CONTEXT_TOOL_NAME,
        {"domain": ["sensor"], "name": "PM2.5"},
    ) == {"domain": ["sensor"]}


def test_normalize_live_context_weather_prefix_name_is_not_exact_entity():
    assert _normalize_tool_args(
        LIVE_CONTEXT_TOOL_NAME,
        {"domain": "sensor", "name": "静安天气"},
    ) == {"domain": "sensor"}


def test_normalize_live_context_external_area_hint_for_weather_query():
    assert _normalize_tool_args(
        LIVE_CONTEXT_TOOL_NAME,
        {"domain": "sensor", "area": "静安"},
        user_text="查一下今天空气质量",
    ) == {"domain": "sensor"}


def test_normalize_live_context_keeps_home_area_for_weather_query():
    assert _normalize_tool_args(
        LIVE_CONTEXT_TOOL_NAME,
        {"domain": "sensor", "area": "卧室"},
        user_text="查一下卧室空气质量",
    ) == {"domain": "sensor", "area": "卧室"}


def test_turn_controller_marks_previous_turn_stale():
    controller = TurnController()

    first = controller.start("turn-1")
    second = controller.start("turn-2")

    assert first.cancelled_turn_id == ""
    assert second.cancelled_turn_id == "turn-1"
    assert second.cancel_reason == "superseded_by_new_turn"
    assert not controller.is_current(first.token)
    assert controller.is_current(second.token)
    assert controller.stale_attrs(first.token)["superseded_by"] == "turn-2"

    controller.finish(second.token)
    assert not controller.is_current(second.token)


def test_tool_events_are_limited_to_current_turn():
    content = [
        conversation.UserContent(content="今天天气。"),
        conversation.AssistantContent(
            agent_id="a",
            content=None,
            tool_calls=[
                llm.ToolInput(
                    id="old-live",
                    tool_name=LIVE_CONTEXT_TOOL_NAME,
                    tool_args={},
                )
            ],
        ),
        conversation.ToolResultContent(
            agent_id="a",
            tool_call_id="old-live",
            tool_name=LIVE_CONTEXT_TOOL_NAME,
            tool_result={"error": "old failure"},
        ),
        conversation.UserContent(content="你能看到哪些设备？"),
        conversation.AssistantContent(agent_id="a", content="我能看到设备。"),
    ]

    assert _tool_events_from_content(content, "你能看到哪些设备？") == []


def test_action_tool_detection():
    assert _is_action_tool("HassTurnOn")
    assert _is_action_tool("HassLightSet")
    assert not _is_action_tool("GetLiveContext")


def test_duplicate_tool_guard_suppresses_live_context_once_recorded():
    counts = {}
    call = llm.ToolInput(
        id="live-1",
        tool_name=LIVE_CONTEXT_TOOL_NAME,
        tool_args={},
    )

    assert _duplicate_tool_reason(call, counts) is None
    _record_tool_calls([call], counts)

    assert _duplicate_tool_reason(call, counts) == "duplicate_live_context"


def test_tool_choice_for_turn_does_not_force_search_for_stable_source_questions():
    tools = [{"type": "function", "function": {"name": "search_web"}}]
    assert (
        _tool_choice_for_turn(
            "关关雎鸠，在河之洲，这句话是出自哪里？",
            tools,
            force_tool_call=False,
        )
        is None
    )


def test_tool_choice_for_turn_forces_search_for_current_questions():
    tools = [{"type": "function", "function": {"name": "search_web"}}]
    assert _tool_choice_for_turn(
        "查一下 Home Assistant 最新语音更新",
        tools,
        force_tool_call=False,
    ) == {"type": "function", "function": {"name": "search_web"}}


def test_tool_choice_for_turn_does_not_force_search_for_weather_local_state():
    tools = [{"type": "function", "function": {"name": "search_web"}}]
    assert (
        _tool_choice_for_turn(
            "今天天气。",
            tools,
            force_tool_call=False,
        )
        is None
    )


def test_tool_choice_for_bare_lookup_weather_forces_live_context_not_search():
    tools = [
        {"type": "function", "function": {"name": LIVE_CONTEXT_TOOL_NAME}},
        {"type": "function", "function": {"name": "search_web"}},
    ]

    assert _tool_choice_for_turn(
        "查一下今天空气质量",
        tools,
        force_tool_call=False,
        force_live_context=True,
    ) == {"type": "function", "function": {"name": LIVE_CONTEXT_TOOL_NAME}}


def test_tool_choice_for_home_state_forces_live_context_when_requested():
    tools = [
        {"type": "function", "function": {"name": LIVE_CONTEXT_TOOL_NAME}},
        {"type": "function", "function": {"name": "search_web"}},
    ]

    assert _tool_choice_for_turn(
        "卧室温度是多少",
        tools,
        force_tool_call=False,
        force_live_context=True,
    ) == {"type": "function", "function": {"name": LIVE_CONTEXT_TOOL_NAME}}


def test_tool_choice_for_turn_forces_live_context_for_weather_when_available():
    tools = [
        {"type": "function", "function": {"name": LIVE_CONTEXT_TOOL_NAME}},
        {"type": "function", "function": {"name": "search_web"}},
    ]

    assert _tool_choice_for_turn(
        "今天天气。",
        tools,
        force_tool_call=False,
        force_live_context=True,
    ) == {"type": "function", "function": {"name": LIVE_CONTEXT_TOOL_NAME}}


def test_tool_choice_for_turn_preserves_action_retry():
    assert _tool_choice_for_turn("打开灯", [], force_tool_call=True) == "required"


async def test_async_grounding_for_turn_uses_cheap_canonical_evidence():
    content = [
        conversation.ToolResultContent(
            agent_id="a",
            tool_call_id="search-1",
            tool_name="search_web",
            tool_result={
                "source_candidates": ["诗经", "关雎"],
                "results": [
                    {
                        "title": "关雎原文翻译",
                        "content": "《关雎》是《诗经·周南》第一篇。",
                    }
                ],
            },
        )
    ]
    runtime = SimpleNamespace(
        session=object(),
        client=object(),
        provider_selector=None,
    )

    with patch(
        "custom_components.llm_gateway.conversation.async_chat_completion_with_fallback",
    ) as verify:
        grounding = await _async_grounding_for_turn(
            runtime,
            {},
            "关关雎鸠，在河之洲，这句话是出自哪里？",
            "这句诗出自《诗经·关关》。",
            content,
        )

    verify.assert_not_called()
    assert grounding.status == "repaired"
    assert grounding.text == "这句诗出自《诗经·周南·关雎》。"
    assert grounding.confidence == 0.92
    assert grounding.verifier["mode"] == "cheap_evidence"


async def test_async_grounding_for_turn_ignores_non_source_turns():
    grounding = await _async_grounding_for_turn(
        SimpleNamespace(),
        {},
        "打开灯",
        "这句诗出自《诗经·关关》。",
        [],
    )
    assert grounding.status == "not_required"
    assert grounding.text == "这句诗出自《诗经·关关》。"


async def test_async_grounding_for_turn_does_not_call_deep_verifier_without_evidence():
    content = [
        conversation.ToolResultContent(
            agent_id="a",
            tool_call_id="search-1",
            tool_name="search_web",
            tool_result={
                "source_candidates": ["已凉", "诗经", "禽经", "关雎"],
                "results": [],
            },
        )
    ]
    runtime = SimpleNamespace(session=object(), client=object(), provider_selector=None)

    with patch(
        "custom_components.llm_gateway.conversation.async_chat_completion_with_fallback",
        side_effect=LLMGatewayConnectionError("timeout"),
    ) as verify:
        grounding = await _async_grounding_for_turn(
            runtime,
            {},
            "关关雎鸠，在河之洲，这句话是出自哪里？",
            "这句诗出自《诗经·周南·关关》。",
            content,
        )

    verify.assert_not_called()
    assert grounding.status == "no_evidence"
    assert grounding.text == "这句诗出自《诗经·周南·关关》。"


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
    request_json = aioclient_mock.mock_calls[-1][2]
    assert any(
        message["role"] == "system" and message["content"] == VOICE_RESPONSE_CONTRACT
        for message in request_json["messages"]
    )


async def test_converse_records_search_feedback_trace(
    hass, aioclient_mock, mock_config_entry
):
    aioclient_mock.get(
        MODELS_URL, json={"data": [{"id": "qwen/qwen3-next-80b-a3b-instruct"}]}
    )
    aioclient_mock.post(
        CHAT_URL,
        json={
            "choices": [{"message": {"role": "assistant", "content": "有更新。"}}]
        },
    )
    agent_id = await _setup_agent(
        hass,
        mock_config_entry,
        {
            CONF_DIAGNOSTIC_TRACES: True,
            CONF_TRACE_INCLUDE_RAW_MESSAGES: True,
        },
    )

    result = await conversation.async_converse(
        hass,
        "查一下 Home Assistant 最新语音更新",
        None,
        Context(),
        agent_id=agent_id,
    )

    assert result.response.speech["plain"]["speech"] == "有更新。"
    trace = mock_config_entry.runtime_data.trace_store.snapshot()["records"][0]
    assert [event["earcon_name"] for event in trace["earcons"]] == [
        "captured",
        "search",
    ]
    assert any(
        event["state"] == "searching" for event in trace["display_status"]["events"]
    )
    assert trace["display_status"]["latest"]["state"] == "done"
    assert trace["first_response_audio"]["scheduled"] is True
    assert trace["first_response_audio"]["played"] is False
    assert trace["first_response_audio"]["suppressed_reason"].startswith(
        "playback_unavailable"
    )


async def test_device_inventory_query_uses_static_context_renderer(
    hass, aioclient_mock, mock_config_entry
):
    aioclient_mock.get(
        MODELS_URL, json={"data": [{"id": "qwen/qwen3-next-80b-a3b-instruct"}]}
    )
    agent_id = await _setup_agent(
        hass,
        mock_config_entry,
        {
            CONF_DIAGNOSTIC_TRACES: True,
            CONF_TRACE_INCLUDE_RAW_MESSAGES: True,
        },
    )

    async def provide_static_context(
        self,
        *_args: object,
        **_kwargs: object,
    ) -> None:
        self.content.append(conversation.SystemContent(content=STATIC_CONTEXT))

    with (
        patch(
            "homeassistant.components.conversation.ChatLog.async_provide_llm_data",
            provide_static_context,
        ),
        patch(
            "custom_components.llm_gateway.conversation.async_chat_completion_with_fallback",
        ) as completion,
    ):
        result = await conversation.async_converse(
            hass, "你能看到哪些设备？", None, Context(), agent_id=agent_id
        )

    completion.assert_not_called()
    speech = result.response.speech["plain"]["speech"]
    assert "已暴露给助手的设备" in speech
    assert "客厅灯" in speech
    assert "卧室空调" in speech
    assert "没有权限" not in speech
    trace = mock_config_entry.runtime_data.trace_store.snapshot()["records"][0]
    assert trace["first_response_decision"]["task_type"] == "device_inventory_query"
    assert trace["first_response_audio"]["scheduled"] is False
    assert trace["first_response_audio"]["suppressed_reason"] == "fast_static_query"
    assert not trace["tools"]
    assert trace["route"]["kind"] == "local_static_context"
    render_span = next(
        span
        for span in trace["timeline_spans"]
        if span["stage"] == "local_inventory_render"
    )
    assert render_span["attrs"]["llm_used"] is False
    assert render_span["attrs"]["tools_used"] == []
    assert render_span["attrs"]["entity_count"] >= 5


async def test_nearby_place_query_without_location_asks_permission_locally(
    hass, aioclient_mock, mock_config_entry
):
    aioclient_mock.get(
        MODELS_URL, json={"data": [{"id": "qwen/qwen3-next-80b-a3b-instruct"}]}
    )
    agent_id = await _setup_agent(
        hass,
        mock_config_entry,
        {
            CONF_DIAGNOSTIC_TRACES: True,
            CONF_TRACE_INCLUDE_RAW_MESSAGES: True,
        },
    )

    with patch(
        "custom_components.llm_gateway.conversation.async_chat_completion_with_fallback",
    ) as completion:
        result = await conversation.async_converse(
            hass,
            "我想知道附近最近的麦当劳在哪里？",
            None,
            Context(),
            agent_id=agent_id,
        )

    completion.assert_not_called()
    speech = result.response.speech["plain"]["speech"]
    assert speech == "我需要知道你的位置才能查附近地点。要使用当前位置吗？"
    assert "不需要联网搜索" not in speech
    trace = mock_config_entry.runtime_data.trace_store.snapshot()["records"][0]
    assert trace["route"]["kind"] == "local_clarify"
    assert trace["route_decision"]["task_family"] == "location_dependent_query"
    assert trace["route_decision"]["task_type"] == "nearby_place_query"
    assert trace["route_decision"]["missing_requirements"] == ["location"]
    assert trace["first_response_decision"]["task_type"] == "nearby_place_query"
    assert trace["first_response_audio"]["scheduled"] is False
    assert trace["first_response_audio"]["suppressed_reason"] == "missing_location"
    assert not trace["tools"]
    clarify_span = next(
        span
        for span in trace["timeline_spans"]
        if span["stage"] == "local_route_clarify"
    )
    assert clarify_span["attrs"]["llm_used"] is False
    assert clarify_span["attrs"]["tools_used"] == []


async def test_literary_stable_fact_answers_locally_without_model(
    hass, aioclient_mock, mock_config_entry
):
    aioclient_mock.get(
        MODELS_URL, json={"data": [{"id": "qwen/qwen3-next-80b-a3b-instruct"}]}
    )
    agent_id = await _setup_agent(
        hass,
        mock_config_entry,
        {
            CONF_DIAGNOSTIC_TRACES: True,
            CONF_TRACE_INCLUDE_RAW_MESSAGES: True,
        },
    )

    with patch(
        "custom_components.llm_gateway.conversation.async_chat_completion_with_fallback",
    ) as completion:
        result = await conversation.async_converse(
            hass, "张若虚有什么样的诗？", None, Context(), agent_id=agent_id
        )

    completion.assert_not_called()
    speech = result.response.speech["plain"]["speech"]
    assert "《春江花月夜》" in speech
    assert "存世作品很少" in speech
    trace = mock_config_entry.runtime_data.trace_store.snapshot()["records"][0]
    assert trace["route"]["kind"] == "local_stable_fact"
    assert trace["first_response_decision"]["reason"] == "local_stable_knowledge"
    assert not trace["tools"]


async def test_unknown_query_clarifies_locally_without_model_final(
    hass, aioclient_mock, mock_config_entry
):
    aioclient_mock.get(
        MODELS_URL, json={"data": [{"id": "qwen/qwen3-next-80b-a3b-instruct"}]}
    )
    agent_id = await _setup_agent(
        hass,
        mock_config_entry,
        {
            CONF_DIAGNOSTIC_TRACES: True,
            CONF_TRACE_INCLUDE_RAW_MESSAGES: True,
        },
    )

    with patch(
        "custom_components.llm_gateway.conversation.async_chat_completion_with_fallback",
    ) as completion:
        result = await conversation.async_converse(
            hass, "咕噜咕噜", None, Context(), agent_id=agent_id
        )

    completion.assert_not_called()
    speech = result.response.speech["plain"]["speech"]
    assert "换个说法" in speech
    trace = mock_config_entry.runtime_data.trace_store.snapshot()["records"][0]
    assert trace["route"]["kind"] == "local_clarify"
    assert trace["route_decision"]["task_family"] == "unknown_or_ambiguous"
    assert trace["first_response_decision"]["cue"] == "none"
    assert not trace["tools"]


async def test_home_state_uses_local_live_context_without_model(
    hass, aioclient_mock, mock_config_entry
):
    aioclient_mock.get(
        MODELS_URL, json={"data": [{"id": "qwen/qwen3-next-80b-a3b-instruct"}]}
    )
    agent_id = await _setup_agent(
        hass,
        mock_config_entry,
        {
            CONF_LLM_HASS_API: "assist",
            CONF_DIAGNOSTIC_TRACES: True,
            CONF_TRACE_INCLUDE_RAW_MESSAGES: True,
        },
    )

    class FakeLiveContextApi:
        custom_serializer = None

        def __init__(self) -> None:
            self.tools = [SimpleNamespace(name=LIVE_CONTEXT_TOOL_NAME)]

        async def async_call_tool(self, tool_input: llm.ToolInput):
            assert tool_input.tool_name == LIVE_CONTEXT_TOOL_NAME
            assert tool_input.tool_args == {"domain": "sensor", "area": "卧室"}
            return LIVE_CONTEXT_RESULT

    async def provide_live_context_api(
        self,
        *_args: object,
        **_kwargs: object,
    ) -> None:
        self.llm_api = FakeLiveContextApi()
        self.content.append(conversation.SystemContent(content=STATIC_CONTEXT))

    with (
        patch(
            "homeassistant.components.conversation.ChatLog.async_provide_llm_data",
            provide_live_context_api,
        ),
        patch(
            "custom_components.llm_gateway.conversation.async_chat_completion_with_fallback",
        ) as completion,
    ):
        result = await conversation.async_converse(
            hass, "卧室温度是多少？", None, Context(), agent_id=agent_id
        )

    completion.assert_not_called()
    assert result.response.speech["plain"]["speech"] == "卧室现在 25.5 度。"
    trace = mock_config_entry.runtime_data.trace_store.snapshot()["records"][0]
    assert trace["route"]["kind"] == "local_live_context"
    assert trace["route"]["model"] == "live_context_renderer"
    assert trace["route_decision"]["route"] == "local_live_context"
    assert trace["route_decision"]["next_action"] == "call_tool_then_local_render"
    assert trace["route_decision"]["requires_llm"] is False
    assert trace["tools"][0]["phase"] == "call"
    assert trace["tools"][0]["name"] == LIVE_CONTEXT_TOOL_NAME
    assert trace["tools"][0]["args"] == {"domain": "sensor", "area": "卧室"}
    render_span = next(
        span
        for span in trace["timeline_spans"]
        if span["stage"] == "local_state_render"
    )
    assert render_span["attrs"]["llm_final_used"] is False
    assert render_span["attrs"]["source"] == "GetLiveContext"


async def test_weather_query_uses_local_context_path_without_forced_search(
    hass, aioclient_mock, mock_config_entry
):
    aioclient_mock.get(
        MODELS_URL, json={"data": [{"id": "qwen/qwen3-next-80b-a3b-instruct"}]}
    )
    agent_id = await _setup_agent(
        hass,
        mock_config_entry,
        {
            CONF_LLM_HASS_API: "assist",
            CONF_SEARCH_ENABLED: True,
            CONF_TAVILY_API_KEY: "tvly-test",
            CONF_DIAGNOSTIC_TRACES: True,
            CONF_TRACE_INCLUDE_RAW_MESSAGES: True,
        },
    )
    requests = []
    responses = iter(
        [
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "live-1",
                        "type": "function",
                        "function": {
                            "name": LIVE_CONTEXT_TOOL_NAME,
                            "arguments": "{}",
                        },
                    }
                ],
            },
            {"role": "assistant", "content": "暂时没有本地天气数据。"},
        ]
    )

    async def fake_completion(**kwargs: object):
        requests.append(kwargs)
        return SimpleNamespace(
            message=next(responses),
            provider={"name": "primary", "fallback_used": False},
            attempts=[],
        )

    with patch(
        "custom_components.llm_gateway.conversation.async_chat_completion_with_fallback",
        side_effect=fake_completion,
    ):
        result = await conversation.async_converse(
            hass, "今天天气。", None, Context(), agent_id=agent_id
        )

    assert result.response.speech["plain"]["speech"] == "暂时没有本地天气数据。"
    assert requests[0].get("tool_choice") != {
        "type": "function",
        "function": {"name": "search_web"},
    }
    trace = mock_config_entry.runtime_data.trace_store.snapshot()["records"][0]
    assert trace["first_response_decision"]["task_type"] == "weather_query"
    assert trace["search_gate"]["decision"] == "local_weather_first"
    assert not trace["search_debug"]["searched"]
    assert trace["weather_context_path"]["path"] == "GetLiveContext"
    live_context_calls = [
        tool
        for tool in trace["tools"]
        if tool["phase"] == "call" and tool["name"] == LIVE_CONTEXT_TOOL_NAME
    ]
    assert live_context_calls
    assert len(live_context_calls) == 1


async def test_weather_query_suppresses_repeated_live_context_call(
    hass, aioclient_mock, mock_config_entry
):
    aioclient_mock.get(
        MODELS_URL, json={"data": [{"id": "qwen/qwen3-next-80b-a3b-instruct"}]}
    )
    agent_id = await _setup_agent(
        hass,
        mock_config_entry,
        {
            CONF_LLM_HASS_API: "assist",
            CONF_DIAGNOSTIC_TRACES: True,
            CONF_TRACE_INCLUDE_RAW_MESSAGES: True,
        },
    )
    responses = iter(
        [
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "live-1",
                        "type": "function",
                        "function": {
                            "name": LIVE_CONTEXT_TOOL_NAME,
                            "arguments": "{}",
                        },
                    }
                ],
            },
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "live-2",
                        "type": "function",
                        "function": {
                            "name": LIVE_CONTEXT_TOOL_NAME,
                            "arguments": '{"name":"静安天气"}',
                        },
                    }
                ],
            },
            {"role": "assistant", "content": "已有信息不足。"},
        ]
    )

    async def fake_completion(**kwargs: object):
        return SimpleNamespace(
            message=next(responses),
            provider={"name": "primary", "fallback_used": False},
            attempts=[],
        )

    with patch(
        "custom_components.llm_gateway.conversation.async_chat_completion_with_fallback",
        side_effect=fake_completion,
    ):
        result = await conversation.async_converse(
            hass, "今天天气。", None, Context(), agent_id=agent_id
        )

    assert result.response.speech["plain"]["speech"] == "已有信息不足。"
    trace = mock_config_entry.runtime_data.trace_store.snapshot()["records"][0]
    live_calls = [
        tool
        for tool in trace["tools"]
        if tool["phase"] == "call" and tool["name"] == LIVE_CONTEXT_TOOL_NAME
    ]
    suppressed = [
        span
        for span in trace["timeline_spans"]
        if span["stage"] == "tool_call_suppressed"
    ]
    assert len(live_calls) == 1
    assert suppressed[0]["attrs"]["reason"] == "duplicate_live_context"
    assert trace["duplicate_tool_suppressions"][0]["reason"] == (
        "duplicate_live_context"
    )
    assert trace["weather_context_path"]["duplicate_live_context_suppressed"] is True


async def test_weather_query_empty_final_gets_local_context_fallback(
    hass, aioclient_mock, mock_config_entry
):
    aioclient_mock.get(
        MODELS_URL, json={"data": [{"id": "qwen/qwen3-next-80b-a3b-instruct"}]}
    )
    agent_id = await _setup_agent(
        hass,
        mock_config_entry,
        {
            CONF_LLM_HASS_API: "assist",
            CONF_DIAGNOSTIC_TRACES: True,
            CONF_TRACE_INCLUDE_RAW_MESSAGES: True,
        },
    )

    async def fake_completion(**kwargs: object):
        return SimpleNamespace(
            message={"role": "assistant", "content": ""},
            provider={"name": "primary", "fallback_used": False},
            attempts=[],
        )

    with patch(
        "custom_components.llm_gateway.conversation.async_chat_completion_with_fallback",
        side_effect=fake_completion,
    ):
        result = await conversation.async_converse(
            hass, "今天天气。", None, Context(), agent_id=agent_id
        )

    assert result.response.speech["plain"]["speech"] == "暂时没有本地天气数据。"
    trace = mock_config_entry.runtime_data.trace_store.snapshot()["records"][0]
    assert trace["final_speech_text"] == "暂时没有本地天气数据。"
    assert any(span["stage"] == "fallback_final" for span in trace["timeline_spans"])


async def test_explicit_web_weather_can_search_without_repeating_live_context(
    hass, aioclient_mock, mock_config_entry
):
    aioclient_mock.get(
        MODELS_URL, json={"data": [{"id": "qwen/qwen3-next-80b-a3b-instruct"}]}
    )
    aioclient_mock.post(
        "https://api.tavily.com/search",
        json={
            "results": [
                {
                    "title": "上海天气",
                    "url": "https://weather.example/shanghai",
                    "content": "今天多云。",
                }
            ]
        },
    )
    agent_id = await _setup_agent(
        hass,
        mock_config_entry,
        {
            CONF_LLM_HASS_API: "assist",
            CONF_SEARCH_ENABLED: True,
            CONF_TAVILY_API_KEY: "tvly-test",
            CONF_DIAGNOSTIC_TRACES: True,
            CONF_TRACE_INCLUDE_RAW_MESSAGES: True,
        },
    )
    responses = iter(
        [
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "search-1",
                        "type": "function",
                        "function": {
                            "name": "search_web",
                            "arguments": '{"query":"上海 今天 天气","max_results":2}',
                        },
                    }
                ],
            },
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "live-1",
                        "type": "function",
                        "function": {
                            "name": LIVE_CONTEXT_TOOL_NAME,
                            "arguments": "{}",
                        },
                    }
                ],
            },
            {"role": "assistant", "content": "今天多云。"},
        ]
    )

    async def fake_completion(**kwargs: object):
        return SimpleNamespace(
            message=next(responses),
            provider={"name": "primary", "fallback_used": False},
            attempts=[],
        )

    with patch(
        "custom_components.llm_gateway.conversation.async_chat_completion_with_fallback",
        side_effect=fake_completion,
    ):
        result = await conversation.async_converse(
            hass, "帮我网上查一下今天的天气。", None, Context(), agent_id=agent_id
        )

    assert result.response.speech["plain"]["speech"] == "今天多云。"
    trace = mock_config_entry.runtime_data.trace_store.snapshot()["records"][0]
    assert trace["search_debug"]["searched"]
    assert trace["search_gate"]["decision"] == "external_search_requested"
    assert trace["weather_context_path"]["search_fallback"] is True
    assert (
        len(
            [
                tool
                for tool in trace["tools"]
                if tool["phase"] == "call" and tool["name"] == LIVE_CONTEXT_TOOL_NAME
            ]
        )
        == 1
    )


async def test_converse_records_high_risk_confirmation_feedback(
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
    agent_id = await _setup_agent(
        hass,
        mock_config_entry,
        {
            CONF_DIAGNOSTIC_TRACES: True,
            CONF_TRACE_INCLUDE_RAW_MESSAGES: True,
        },
    )

    result = await conversation.async_converse(
        hass, "打开前门", None, Context(), agent_id=agent_id
    )

    assert "确认" in result.response.speech["plain"]["speech"]
    trace = mock_config_entry.runtime_data.trace_store.snapshot()["records"][0]
    assert "confirmation" in [event["earcon_name"] for event in trace["earcons"]]
    assert trace["debug_flags"]["high_risk"] is True
    assert trace["display_status"]["latest"]["state"] == "confirming"
    assert trace["display_status"]["latest"]["action_buttons"] == [
        "confirm",
        "cancel",
        "open_panel",
    ]


async def test_home_state_empty_final_gets_status_fallback(
    hass, aioclient_mock, mock_config_entry
):
    aioclient_mock.get(
        MODELS_URL, json={"data": [{"id": "qwen/qwen3-next-80b-a3b-instruct"}]}
    )
    agent_id = await _setup_agent(
        hass,
        mock_config_entry,
        {
            CONF_DIAGNOSTIC_TRACES: True,
            CONF_TRACE_INCLUDE_RAW_MESSAGES: True,
        },
    )

    async def fake_completion(**kwargs: object):
        return SimpleNamespace(
            message={"role": "assistant", "content": ""},
            provider={"name": "primary", "fallback_used": False},
            attempts=[],
        )

    with patch(
        "custom_components.llm_gateway.conversation.async_chat_completion_with_fallback",
        side_effect=fake_completion,
    ):
        result = await conversation.async_converse(
            hass, "卧室温度是多少？", None, Context(), agent_id=agent_id
        )

    assert result.response.speech["plain"]["speech"] == "暂时没有本地状态数据。"
    trace = mock_config_entry.runtime_data.trace_store.snapshot()["records"][0]
    assert trace["first_response_decision"]["task_type"] == "home_state"
    assert trace["final_speech_text"] == "暂时没有本地状态数据。"
    assert any(span["stage"] == "fallback_final" for span in trace["timeline_spans"])


async def test_high_risk_empty_final_gets_confirmation_fallback(
    hass, aioclient_mock, mock_config_entry
):
    aioclient_mock.get(
        MODELS_URL, json={"data": [{"id": "qwen/qwen3-next-80b-a3b-instruct"}]}
    )
    agent_id = await _setup_agent(
        hass,
        mock_config_entry,
        {
            CONF_DIAGNOSTIC_TRACES: True,
            CONF_TRACE_INCLUDE_RAW_MESSAGES: True,
        },
    )

    async def fake_completion(**kwargs: object):
        return SimpleNamespace(
            message={"role": "assistant", "content": ""},
            provider={"name": "primary", "fallback_used": False},
            attempts=[],
        )

    with patch(
        "custom_components.llm_gateway.conversation.async_chat_completion_with_fallback",
        side_effect=fake_completion,
    ):
        result = await conversation.async_converse(
            hass, "打开前门门锁", None, Context(), agent_id=agent_id
        )

    assert result.response.speech["plain"]["speech"] == "这个需要确认。"
    trace = mock_config_entry.runtime_data.trace_store.snapshot()["records"][0]
    assert trace["first_response_decision"]["task_type"] == "high_risk"
    assert trace["debug_flags"]["high_risk"] is True
    assert trace["final_speech_text"] == "这个需要确认。"


async def test_converse_records_plain_feedback_without_search_overplay(
    hass, aioclient_mock, mock_config_entry
):
    aioclient_mock.get(
        MODELS_URL, json={"data": [{"id": "qwen/qwen3-next-80b-a3b-instruct"}]}
    )
    aioclient_mock.post(
        CHAT_URL,
        json={
            "choices": [{"message": {"role": "assistant", "content": "卧室 24 度。"}}]
        },
    )
    agent_id = await _setup_agent(
        hass,
        mock_config_entry,
        {
            CONF_DIAGNOSTIC_TRACES: True,
            CONF_TRACE_INCLUDE_RAW_MESSAGES: True,
        },
    )

    await conversation.async_converse(
        hass, "卧室现在多少度", None, Context(), agent_id=agent_id
    )

    trace = mock_config_entry.runtime_data.trace_store.snapshot()["records"][0]
    names = [event["earcon_name"] for event in trace["earcons"]]
    assert names == ["captured"]
    assert "search" not in names
    assert "thinking" not in names
    assert trace["display_status"]["latest"]["state"] == "done"


async def test_converse_records_failure_feedback_trace(
    hass, aioclient_mock, mock_config_entry
):
    aioclient_mock.get(
        MODELS_URL, json={"data": [{"id": "qwen/qwen3-next-80b-a3b-instruct"}]}
    )
    agent_id = await _setup_agent(
        hass,
        mock_config_entry,
        {
            CONF_DIAGNOSTIC_TRACES: True,
            CONF_TRACE_INCLUDE_RAW_MESSAGES: True,
        },
    )

    with patch(
        "custom_components.llm_gateway.api.LLMGatewayClient.async_chat_completion",
        side_effect=LLMGatewayConnectionError("timeout"),
    ):
        result = await conversation.async_converse(
            hass, "打开风扇", None, Context(), agent_id=agent_id
        )

    assert result.response.speech["plain"]["speech"] == GATEWAY_ERROR_SPEECH
    trace = mock_config_entry.runtime_data.trace_store.snapshot()["records"][0]
    assert trace["status"] == "error"
    assert "failure" in [event["earcon_name"] for event in trace["earcons"]]
    assert trace["display_status"]["latest"]["state"] == "failed"


async def test_converse_voice_pause_command_calls_local_service(
    hass, aioclient_mock, mock_config_entry
):
    calls = []

    async def handle_pause(call):
        calls.append(dict(call.data))

    hass.services.async_register("rest_command", "kukui_voice_pause", handle_pause)
    aioclient_mock.get(
        MODELS_URL, json={"data": [{"id": "qwen/qwen3-next-80b-a3b-instruct"}]}
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    entities = er.async_entries_for_config_entry(ent_reg, mock_config_entry.entry_id)
    agent_id = entities[0].entity_id

    result = await conversation.async_converse(
        hass, "闭嘴 5 分钟", None, Context(), agent_id=agent_id
    )

    assert result.response.speech["plain"]["speech"] == "我会停止响应语音唤醒 5 分钟。"
    assert calls == [{"seconds": 300, "reason": "voice_command"}]


async def test_converse_voice_resume_command_calls_local_service(
    hass, aioclient_mock, mock_config_entry
):
    calls = []

    async def handle_resume(call):
        calls.append(dict(call.data))

    hass.services.async_register("rest_command", "kukui_voice_resume", handle_resume)
    aioclient_mock.get(
        MODELS_URL, json={"data": [{"id": "qwen/qwen3-next-80b-a3b-instruct"}]}
    )
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    entities = er.async_entries_for_config_entry(ent_reg, mock_config_entry.entry_id)
    agent_id = entities[0].entity_id

    result = await conversation.async_converse(
        hass, "恢复语音唤醒", None, Context(), agent_id=agent_id
    )

    assert result.response.speech["plain"]["speech"] == "语音唤醒已恢复。"
    assert calls == [{}]


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


async def test_converse_falls_back_to_secondary_provider_and_traces_attempts(
    hass, aioclient_mock, mock_config_entry
):
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={
            **mock_config_entry.options,
            CONF_DIAGNOSTIC_TRACES: True,
            CONF_TRACE_INCLUDE_RAW_MESSAGES: True,
            CONF_PROVIDER_PROFILES: (
                '{"providers":[{"name":"fallback","base_url":"'
                + FALLBACK_BASE_URL
                + '","api_key":"fallback-key","models":{"fast":"fallback-fast"}}]}'
            ),
        },
    )
    aioclient_mock.get(
        MODELS_URL, json={"data": [{"id": "qwen/qwen3-next-80b-a3b-instruct"}]}
    )
    aioclient_mock.post(CHAT_URL, status=500, text="primary down")
    aioclient_mock.post(
        FALLBACK_CHAT_URL,
        json={
            "choices": [
                {"message": {"role": "assistant", "content": "已切到备用 provider。"}}
            ]
        },
    )
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    entities = er.async_entries_for_config_entry(ent_reg, mock_config_entry.entry_id)
    agent_id = entities[0].entity_id

    result = await conversation.async_converse(
        hass, "你好", None, Context(), agent_id=agent_id
    )

    assert result.response.speech["plain"]["speech"] == "已切到备用 provider。"
    traces = mock_config_entry.runtime_data.trace_store.snapshot()["records"]
    attempts = traces[0]["route"]["provider_attempts"]
    assert traces[0]["route"]["provider"]["name"] == "fallback"
    assert [attempt["provider"] for attempt in attempts] == ["primary", "fallback"]
    assert attempts[0]["retryable"] is True
    assert traces[0]["raw_payload"]["speech"] == {
        "raw": "已切到备用 provider。",
        "grounded": "已切到备用 provider。",
        "final": "已切到备用 provider。",
        "tts_cleaned": True,
    }
