"""Tests for local first-response decisions."""

from __future__ import annotations

from custom_components.llm_gateway.first_response import (
    FAST_PROCESSING_CUE_DELAY_S,
    decide_first_response,
    stable_fact_answer,
)


def test_stable_quote_origin_cache_handles_asr_variants():
    assert (
        stable_fact_answer("关关隹鸠，在河之洲，这句话出自哪里？")
        == "这句诗出自《诗经·国风·周南·关雎》。"
    )


def test_first_response_keeps_stable_fact_off_search_path():
    decision = decide_first_response("关关雎鸠，在河之洲，这句话是出自哪里？")

    assert decision.task_type == "stable_fact"
    assert decision.cue == "none"


def test_first_response_uses_fast_search_cue_for_current_info():
    decision = decide_first_response("查一下今天空气质量")

    assert decision.task_type == "search_needed"
    assert decision.cue == "search"
    assert decision.spoken_hint == "我查一下。"
    assert decision.processing_cue_delay_s == FAST_PROCESSING_CUE_DELAY_S


def test_first_response_classifies_weather_as_local_state_by_default():
    for text in (
        "今天天气。",
        "天气怎么样？",
        "今天会下雨吗？",
        "外面冷不冷？",
        "空气质量怎么样？",
    ):
        decision = decide_first_response(text)
        assert decision.task_type == "weather_query"
        assert decision.cue == "none"
        assert decision.reason == "home_state_weather"


def test_first_response_classifies_inventory_as_fast_static_query():
    cases = {
        "你能看到哪些设备？": "device_inventory_query",
        "卧室有哪些设备？": "area_inventory_query",
        "有哪些灯？": "domain_inventory_query",
        "你能控制什么？": "capability_query",
        "你现在接入了哪些东西？": "device_inventory_query",
        "家里有啥可以控制？": "capability_query",
        "卧室都有啥？": "area_inventory_query",
        "你能看到天气吗？": "domain_inventory_query",
    }
    for text, task_type in cases.items():
        decision = decide_first_response(text)

        assert decision.task_type == task_type
        assert decision.cue == "none"
        assert decision.spoken_hint == ""
        assert decision.audio_suppressed_reason == "fast_static_query"


def test_first_response_inventory_classifier_avoids_action_and_weather_false_hits():
    assert decide_first_response("打开客厅灯").task_type == "home_control"
    assert decide_first_response("今天天气怎么样？").task_type == "weather_query"
    assert decide_first_response("卧室温度是多少？").task_type == "home_state"


def test_first_response_marks_high_risk_confirmation():
    for text in ("打开前门门锁", "打开前门"):
        decision = decide_first_response(text)

        assert decision.task_type == "high_risk"
        assert decision.cue == "confirmation"
        assert decision.spoken_hint == "这个需要确认。"
