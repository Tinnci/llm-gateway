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


def test_explicit_current_info_beats_default_weather_state():
    decision = decide_route("查一下今天空气质量")

    assert decision.task_family == "external_current_info"
    assert decision.task_type == "search_needed"
    assert decision.next_action == "search"
    assert decision.allowed_tools == ("search_web",)


def test_default_weather_stays_home_state():
    decision = decide_route("空气质量怎么样？")

    assert decision.task_family == "home_state"
    assert decision.task_type == "weather_query"
    assert decision.allowed_tools == ("GetLiveContext",)
