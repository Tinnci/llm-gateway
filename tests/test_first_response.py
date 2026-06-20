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


def test_stable_literary_cache_handles_common_author_facts():
    assert stable_fact_answer("张若虚有什么样的诗？") == (
        "张若虚是唐代诗人，存世作品很少，最著名的是《春江花月夜》。"
        "通常提到他的代表作，主要就是这首。"
    )
    assert (
        stable_fact_answer("春江花月夜是谁写的？")
        == "《春江花月夜》的作者是唐代诗人张若虚。"
    )
    assert "将进酒" in (stable_fact_answer("李白有什么代表作？") or "")


def test_first_response_keeps_stable_fact_off_search_path():
    decision = decide_first_response("关关雎鸠，在河之洲，这句话是出自哪里？")

    assert decision.task_type == "stable_fact"
    assert decision.cue == "none"


def test_first_response_simple_stable_fact_does_not_say_look_it_up():
    decision = decide_first_response("Alexa 是什么？")

    assert decision.task_type == "stable_fact"
    assert decision.cue == "none"
    assert decision.spoken_hint == ""


def test_first_response_literary_knowledge_is_not_unknown():
    decision = decide_first_response("张若虚有什么样的诗？")

    assert decision.task_type == "stable_fact"
    assert decision.cue == "none"
    assert decision.reason == "local_stable_knowledge"


def test_first_response_uses_fast_search_cue_for_current_info():
    decision = decide_first_response("查一下 Home Assistant 最新语音更新")

    assert decision.task_type == "search_needed"
    assert decision.cue == "search"
    assert decision.spoken_hint == "我查一下。"
    assert decision.processing_cue_delay_s == FAST_PROCESSING_CUE_DELAY_S


def test_first_response_suppresses_missing_location_poi_prompt():
    decision = decide_first_response("我想知道附近最近的麦当劳在哪里？")

    assert decision.task_type == "nearby_place_query"
    assert decision.cue == "none"
    assert decision.spoken_hint == ""
    assert decision.audio_suppressed_reason == "missing_location"


def test_first_response_suppresses_unknown_fallback_hint():
    decision = decide_first_response("咕噜咕噜")

    assert decision.task_type == "unknown"
    assert decision.cue == "none"
    assert decision.spoken_hint == ""
    assert decision.reason == "unknown_or_ambiguous"


def test_first_response_volume_control_uses_no_spoken_hint():
    decision = decide_first_response("把自己的音量调到最大吗？")

    assert decision.task_type == "volume_control"
    assert decision.cue == "none"
    assert decision.spoken_hint == ""
    assert decision.reason == "volume_control"


def test_first_response_classifies_weather_as_local_state_by_default():
    cases = {
        "今天天气。": "outdoor_current_weather_query",
        "天气怎么样？": "outdoor_current_weather_query",
        "今天会下雨吗？": "outdoor_current_weather_query",
        "外面冷不冷？": "outdoor_current_weather_query",
        "空气质量怎么样？": "indoor_environment_query",
        "查一下今天空气质量": "indoor_environment_query",
    }
    for text, task_type in cases.items():
        decision = decide_first_response(text)
        assert decision.task_type == task_type
        assert decision.cue == "none"
        assert decision.reason in {"home_state_weather", "home_state_pattern"}


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
    assert decide_first_response("把风扇关了。").task_type == "home_control"
    assert decide_first_response("把空调开了").task_type == "home_control"
    assert (
        decide_first_response("今天天气怎么样？").task_type
        == "outdoor_current_weather_query"
    )
    assert decide_first_response("卧室温度是多少？").task_type == (
        "indoor_environment_query"
    )


def test_first_response_marks_high_risk_confirmation():
    for text in ("打开前门门锁", "打开前门"):
        decision = decide_first_response(text)

        assert decision.task_type == "high_risk"
        assert decision.cue == "confirmation"
        assert decision.spoken_hint == "这个需要确认。"
