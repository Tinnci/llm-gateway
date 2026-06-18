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


def test_first_response_marks_high_risk_confirmation():
    decision = decide_first_response("打开前门门锁")

    assert decision.task_type == "high_risk"
    assert decision.cue == "confirmation"
    assert decision.spoken_hint == "这个需要确认。"
