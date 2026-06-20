"""Tests for capability-based semantic routing."""

from __future__ import annotations

from custom_components.llm_gateway.capabilities import (
    CAPABILITY_CONTRACTS,
    CAPABILITY_REGISTRY,
    decide_route,
    plan_multi_intent,
    plan_typed_semantic,
    resolve_entity,
)


def test_capability_registry_covers_core_task_families():
    families = {capability.family for capability in CAPABILITY_REGISTRY}

    assert {
        "home_inventory",
        "home_state",
        "home_control",
        "home_capability",
        "volume_control",
        "location_dependent_query",
        "external_current_info",
        "stable_knowledge",
        "automation_planning",
        "conversation_control",
        "unknown_or_ambiguous",
    } <= families


def test_home_inventory_family_stays_local_static():
    decision = decide_route("你能看到哪些设备？")

    assert decision.task_family == "home_inventory"
    assert decision.task_type == "device_inventory_query"
    assert decision.route == "local_static_context"
    assert not decision.requires_llm
    assert not decision.allowed_tools


def test_multi_intent_planner_splits_inventory_and_temperature():
    plan = plan_multi_intent("你现在我们家里有哪些设备？家里的温度是什么样的？")

    assert plan.is_multi_intent
    assert [subtask.route_decision.task_type for subtask in plan.subtasks] == [
        "device_inventory_query",
        "home_temperature_summary",
    ]
    assert plan.subtasks[0].route_decision.route == "local_static_context"
    assert plan.subtasks[1].route_decision.route == "local_live_context"


def test_multi_intent_planner_splits_temperature_and_humidity_with_area():
    plan = plan_multi_intent("卧室温度和湿度分别是多少？")

    assert plan.is_multi_intent
    assert [subtask.text for subtask in plan.subtasks] == [
        "卧室温度是多少",
        "卧室湿度是多少",
    ]
    assert all(
        subtask.route_decision.route == "local_live_context"
        for subtask in plan.subtasks
    )


def test_typed_semantic_plan_exposes_required_frame_fields():
    plan = plan_typed_semantic("你现在我们家里有哪些设备？家里的温度是什么样的？")

    assert plan.is_composite
    assert [frame.operation for frame in plan.frames] == [
        "inventory_summary",
        "home_temperature_summary",
    ]
    for frame in plan.frames:
        data = frame.as_dict()
        assert {
            "domain",
            "operation",
            "scope",
            "area",
            "metric",
            "time_horizon",
            "data_requirement",
            "forecast_required",
            "risk",
            "capability",
        } <= data.keys()


def test_multi_intent_planner_splits_indoor_and_outdoor_temperature():
    plan = plan_typed_semantic("室内和室外温度分别是多少？")

    assert plan.is_composite
    assert [frame.scope for frame in plan.frames] == [
        "indoor_environment",
        "outdoor_weather",
    ]
    assert [frame.capability for frame in plan.frames] == [
        "indoor_environment_query",
        "outdoor_current_weather_query",
    ]


def test_weather_route_contract_separates_forecast_from_indoor_state():
    tomorrow = decide_route("明天的天气怎么样？")

    assert tomorrow.task_type == "weather_forecast_query"
    assert tomorrow.scope == "outdoor_weather"
    assert tomorrow.time_horizon == "tomorrow"
    assert tomorrow.forecast_required
    assert tomorrow.requires_external_info
    assert tomorrow.allowed_tools == ("search_web",)
    assert tomorrow.next_action == "clarify"
    assert tomorrow.missing_requirements == ("location_hint",)

    bedroom = decide_route("卧室温度是多少？")
    assert bedroom.task_type == "indoor_environment_query"
    assert bedroom.scope == "indoor_environment"
    assert bedroom.time_horizon == "now"
    assert not bedroom.forecast_required

    home_air = decide_route("家里空气质量怎么样？")
    assert home_air.task_type == "home_state"
    assert home_air.scope == "home_summary"
    assert not home_air.forecast_required

    jingan = decide_route("静安天气怎么样？")
    assert jingan.task_type == "outdoor_current_weather_query"
    assert jingan.scope == "outdoor_weather"
    assert jingan.location_hint == "静安"


def test_weather_forecast_contract_forbids_current_sensor_data():
    contract = CAPABILITY_CONTRACTS["weather_forecast_query"]

    assert contract.required_user_slots == ("location_hint",)
    assert "search_web" in contract.allowed_tools
    assert "GetLiveContext" in contract.forbidden_tools
    assert "current_room_temperature" in contract.forbidden_data
    assert contract.answerability_guard == "forecast_required_never_uses_current_sensor"

    decision = decide_route("What is the weather tomorrow?")

    assert decision.task_type == "weather_forecast_query"
    assert decision.forecast_required
    assert decision.scope == "outdoor_weather"
    assert decision.time_horizon == "tomorrow"
    assert decision.next_action == "clarify"
    assert decision.requires_external_info
    assert not decision.requires_llm
    assert decision.missing_requirements == ("location_hint",)
    assert decision.metadata["answerability"] == "missing_user_slot"
    assert (
        decision.metadata["capability_contract"]["answerability_guard"]
        == "forecast_required_never_uses_current_sensor"
    )


def test_forecast_arbitration_beats_inventory_and_supports_english_family():
    utterances = (
        "明天的天气是什么样的？你能搜索一下吗？",
        "What is the weather? Not today.",
        "What is the weather tomorrow?",
        "Tomorrow weather forecast",
    )

    for text in utterances:
        decision = decide_route(text)

        assert decision.task_family == "external_current_info", text
        assert decision.task_type == "weather_forecast_query", text
        assert decision.forecast_required, text
        assert decision.next_action == "clarify", text
        assert decision.route == "local_clarify", text
        assert decision.missing_requirements == ("location_hint",), text


def test_typed_semantic_plan_merges_english_forecast_correction():
    plan = plan_typed_semantic("What is the weather? Not today.")

    assert not plan.is_composite
    frame = plan.frames[0]
    assert frame.capability == "weather_forecast_query"
    assert frame.forecast_required
    assert frame.answerability == "missing_user_slot"


def test_location_dependent_paraphrases_require_location_without_explicit_place():
    utterances = (
        "我想知道附近最近的麦当劳在哪里？",
        "最近的麦当劳在哪？",
        "帮我找一下附近麦当劳",
        "附近有没有麦当劳",
        "离我最近的快餐店是哪家",
        "我想吃麦当劳，最近的店在哪",
        "附近有没有药店？",
        "最近的便利店在哪里？",
    )

    for text in utterances:
        decision = decide_route(text)

        assert decision.task_family == "location_dependent_query", text
        assert decision.task_type == "nearby_place_query"
        assert decision.requires_location
        assert decision.requires_external_info
        assert decision.next_action == "ask_location_permission"
        assert decision.missing_requirements == ("location",)
        assert "search_web" in decision.allowed_tools
        assert "HassTurnOn" in decision.forbidden_tools


def test_location_dependent_query_with_explicit_location_can_search():
    decision = decide_route("上海静安附近最近的麦当劳在哪里？")

    assert decision.task_family == "location_dependent_query"
    assert decision.task_type == "nearby_place_query"
    assert decision.next_action == "search"
    assert decision.route == "mid"
    assert decision.missing_requirements == ()
    assert decision.metadata["explicit_location"] is True


def test_unknown_uses_llm_generalization_before_clarification():
    decision = decide_route("咕噜咕噜")

    assert decision.task_family == "unknown_or_ambiguous"
    assert decision.task_type == "unknown"
    assert decision.next_action == "answer_with_llm"
    assert decision.route == "fast"
    assert decision.requires_llm
    assert decision.metadata["planner"] == "llm_route_generalization"


def test_literary_knowledge_routes_to_stable_knowledge():
    expectations = (
        ("张若虚有什么样的诗？", "works_by_author_query", "list_works"),
        ("李白有什么代表作？", "works_by_author_query", "list_works"),
        ("春江花月夜是谁写的？", "literary_knowledge_query", "answer_literary_fact"),
        ("某句诗是什么意思？", "literary_knowledge_query", "answer_literary_fact"),
    )

    for text, task_type, operation in expectations:
        decision = decide_route(text)

        assert decision.task_family == "stable_knowledge", text
        assert decision.task_type == task_type
        assert decision.route == "fast"
        assert decision.requires_llm
        assert decision.next_action == "answer_with_llm"
        assert decision.metadata["language"] == "zh"
        assert decision.metadata["operation"] == operation
        assert decision.metadata["answerability"] == "answerable"


def test_english_literary_and_person_knowledge_routes_are_typed():
    woolf = decide_route("Can you tell me more about what Virginia Wolf have written?")

    assert woolf.task_family == "stable_knowledge"
    assert woolf.task_type == "works_by_author_query"
    assert woolf.matched_capability == "works_by_author_query"
    assert woolf.metadata["domain"] == "literature"
    assert woolf.metadata["operation"] == "list_works"
    resolution = woolf.metadata["entity_resolution"]
    assert resolution["raw_entity"] == "Virginia Wolf"
    assert resolution["canonical_entity"] == "Virginia Woolf"
    assert resolution["correction_type"] == "spelling"
    assert resolution["confidence"] >= 0.9
    assert resolution["ambiguous"] is False
    assert woolf.metadata["answerability"] == "answerable"

    person = decide_route("Who is Virginia Woolf?")
    assert person.task_family == "stable_knowledge"
    assert person.task_type == "person_knowledge_query"
    assert person.matched_capability == "person_knowledge_query"
    assert person.metadata["entity_resolution"]["canonical_entity"] == "Virginia Woolf"


def test_ambiguous_named_entity_does_not_route_to_freeform_unknown_answer():
    decision = decide_route("Do you know who is Virginia Hope?")

    assert decision.task_family == "stable_knowledge"
    assert decision.task_type == "ambiguous_entity_query"
    assert decision.next_action == "clarify"
    assert decision.route == "local_clarify"
    assert not decision.requires_llm
    assert not decision.allowed_tools
    assert "Virginia Woolf" in decision.user_visible_prompt
    resolution = decision.metadata["entity_resolution"]
    assert resolution["raw_entity"] == "Virginia Hope"
    assert resolution["canonical_entity_candidates"] == ["Virginia Woolf"]
    assert resolution["ambiguous"] is True
    assert resolution["needs_clarification"] is True
    assert decision.metadata["answerability"] == "ambiguous_entity"


def test_entity_resolver_records_canonical_correction_and_ambiguity():
    wolf = resolve_entity("Virginia Wolf")
    hope = resolve_entity("Virginia Hope")

    assert wolf.canonical_entity == "Virginia Woolf"
    assert wolf.correction_type == "spelling"
    assert wolf.confidence >= 0.9
    assert not wolf.ambiguous

    assert hope.raw_entity == "Virginia Hope"
    assert hope.candidates == ("Virginia Woolf",)
    assert hope.confidence < 0.7
    assert hope.ambiguous


def test_volume_control_gets_targeted_route_or_clarification():
    self_volume = decide_route("把自己的音量调到最大吗？")

    assert self_volume.task_family == "volume_control"
    assert self_volume.task_type == "volume_control"
    assert self_volume.next_action == "execute_local"
    assert self_volume.route == "local_action"
    assert not self_volume.requires_llm

    media_volume = decide_route("把客厅音箱音量调高")

    assert media_volume.task_family == "volume_control"
    assert media_volume.task_type == "volume_control"
    assert media_volume.next_action == "execute_local"
    assert media_volume.route == "local_action"
    assert not media_volume.requires_llm


def test_home_state_routes_to_local_live_context_without_llm():
    for text in (
        "卧室温度是多少？",
        "当前卧室的温度是多少？",
        "当前客厅的温度是多少？",
        "卧室湿度多少？",
    ):
        decision = decide_route(text)

        assert decision.task_family == "home_state", text
        assert decision.task_type == "indoor_environment_query"
        assert decision.route == "local_live_context"
        assert decision.next_action == "call_tool_then_local_render"
        assert not decision.requires_llm
        assert decision.requires_live_home_context
        assert decision.allowed_tools == ("GetLiveContext",)


def test_colloquial_home_control_routes_to_control_capability():
    utterances = (
        "把风扇关了。",
        "把卧室灯关了",
        "把空调开了",
        "把客厅灯关上",
    )

    for text in utterances:
        decision = decide_route(text)

        assert decision.task_family == "home_control", text
        assert decision.task_type == "home_control"
        if "空调" in text:
            assert decision.route == "fast"
            assert decision.requires_llm
        else:
            assert decision.route == "local_action"
            assert decision.next_action == "execute_local"
            assert not decision.requires_llm


def test_bare_lookup_weather_stays_home_state():
    decision = decide_route("查一下今天空气质量")

    assert decision.task_family == "home_state"
    assert decision.task_type == "indoor_environment_query"
    assert decision.route == "local_live_context"
    assert decision.next_action == "call_tool_then_local_render"
    assert not decision.requires_llm
    assert decision.allowed_tools == ("GetLiveContext",)


def test_explicit_web_weather_can_search():
    decision = decide_route("帮我网上查一下今天的天气")

    assert decision.task_family == "external_current_info"
    assert decision.task_type == "search_needed"
    assert decision.next_action == "search"
    assert decision.allowed_tools == ("search_web",)


def test_bare_search_request_asks_for_query_without_tools():
    decision = decide_route("搜索一下。")

    assert decision.task_family == "external_current_info"
    assert decision.task_type == "search_needed"
    assert decision.next_action == "clarify"
    assert decision.route == "local_clarify"
    assert decision.missing_requirements == ("query",)
    assert decision.allowed_tools == ()
    assert decision.user_visible_prompt == "你想搜索什么？"


def test_default_weather_stays_home_state():
    decision = decide_route("空气质量怎么样？")

    assert decision.task_family == "home_state"
    assert decision.task_type == "indoor_environment_query"
    assert decision.route == "local_live_context"
    assert decision.next_action == "call_tool_then_local_render"
    assert not decision.requires_llm
    assert decision.allowed_tools == ("GetLiveContext",)
