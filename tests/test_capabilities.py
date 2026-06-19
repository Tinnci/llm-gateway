"""Tests for capability-based semantic routing."""

from __future__ import annotations

from custom_components.llm_gateway.capabilities import (
    CAPABILITY_REGISTRY,
    decide_route,
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


def test_unknown_is_clarification_not_direct_answer():
    decision = decide_route("咕噜咕噜")

    assert decision.task_family == "unknown_or_ambiguous"
    assert decision.task_type == "unknown"
    assert decision.next_action == "clarify"
    assert decision.route == "local_clarify"
    assert "换个说法" in decision.user_visible_prompt


def test_literary_knowledge_routes_to_stable_knowledge():
    utterances = (
        "张若虚有什么样的诗？",
        "李白有什么代表作？",
        "春江花月夜是谁写的？",
        "某句诗是什么意思？",
    )

    for text in utterances:
        decision = decide_route(text)

        assert decision.task_family == "stable_knowledge", text
        assert decision.task_type == "stable_fact"
        assert decision.route == "fast"
        assert decision.requires_llm
        assert decision.next_action == "answer_with_llm"


def test_volume_control_gets_targeted_route_or_clarification():
    self_volume = decide_route("把自己的音量调到最大吗？")

    assert self_volume.task_family == "volume_control"
    assert self_volume.task_type == "volume_control"
    assert self_volume.next_action == "clarify"
    assert "我说话的音量" in self_volume.user_visible_prompt
    assert "播放器" in self_volume.user_visible_prompt

    media_volume = decide_route("把客厅音箱音量调高")

    assert media_volume.task_family == "volume_control"
    assert media_volume.task_type == "volume_control"
    assert media_volume.next_action == "answer_with_llm"
    assert "HassCallService" in media_volume.allowed_tools


def test_bare_lookup_weather_stays_home_state():
    decision = decide_route("查一下今天空气质量")

    assert decision.task_family == "home_state"
    assert decision.task_type == "weather_query"
    assert decision.next_action == "answer_with_llm"
    assert decision.allowed_tools == ("GetLiveContext",)


def test_explicit_web_weather_can_search():
    decision = decide_route("帮我网上查一下今天的天气")

    assert decision.task_family == "external_current_info"
    assert decision.task_type == "search_needed"
    assert decision.next_action == "search"
    assert decision.allowed_tools == ("search_web",)


def test_default_weather_stays_home_state():
    decision = decide_route("空气质量怎么样？")

    assert decision.task_family == "home_state"
    assert decision.task_type == "weather_query"
    assert decision.allowed_tools == ("GetLiveContext",)
