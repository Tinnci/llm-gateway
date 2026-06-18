"""Tests for source grounding verifier helpers."""

from __future__ import annotations

from custom_components.llm_gateway.grounding import (
    build_grounding_verifier_messages,
    initial_grounding_result,
    parse_grounding_verifier_response,
    source_canonical_answers_from_results,
)


def test_initial_grounding_result_requires_source_questions():
    result = initial_grounding_result("打开灯", "好了。", [])

    assert result.status == "not_required"
    assert result.text == "好了。"


def test_initial_grounding_result_extracts_candidates():
    result = initial_grounding_result(
        "关关雎鸠，在河之洲，这句话是出自哪里？",
        "这句诗出自《诗经·关关》。",
        [
            {
                "source_candidates": ["诗经", "关雎"],
                "results": [],
            }
        ],
    )

    assert result.status == "no_evidence"
    assert result.candidates == ["诗经", "关雎"]


def test_initial_grounding_result_repairs_from_single_canonical_answer():
    result = initial_grounding_result(
        "关关雎鸠，在河之洲，这句话是出自哪里？",
        "这句诗出自《诗经·关关》。",
        [
            {
                "results": [
                    {
                        "title": "周南·关雎_百科",
                        "content": "《关雎》是《诗经·周南》第一篇。",
                    }
                ],
            }
        ],
    )

    assert result.status == "repaired"
    assert result.text == "这句诗出自《诗经·周南·关雎》。"
    assert result.canonical_answers == ["《诗经·周南·关雎》"]


def test_build_grounding_verifier_messages_contains_evidence():
    messages = build_grounding_verifier_messages(
        user_text="关关雎鸠，在河之洲，这句话是出自哪里？",
        assistant_text="这句诗出自《诗经·关关》。",
        search_results=[
            {
                "results": [
                    {
                        "title": "周南·关雎_百度百科",
                        "url": "https://example.test/guanju",
                        "content": "《关雎》是《诗经·周南》第一篇。",
                    }
                ]
            }
        ],
    )

    assert messages[0]["role"] == "system"
    assert "Output JSON only" in messages[0]["content"]
    assert (
        "selected_answer must be empty or exactly one allowed answer"
        in messages[0]["content"]
    )
    assert "周南·关雎_百度百科" in messages[1]["content"]
    assert "Return exactly this JSON shape" in messages[1]["content"]


def test_parse_grounding_verifier_response_selects_allowed_answer():
    result = parse_grounding_verifier_response(
        '{"verdict":"select","selected_answer":"《诗经·周南·关雎》",'
        '"confidence":0.93,"reason":"证据支持《关雎》"}',
        fallback_text="这句诗出自《诗经·关关》。",
        candidates=["诗经", "关雎"],
        canonical_answers=["《诗经·周南·关雎》"],
    )

    assert result.status == "repaired"
    assert result.text == "这句诗出自《诗经·周南·关雎》。"
    assert result.confidence == 0.93
    assert result.repairs == [
        {"from": "这句诗出自《诗经·关关》。", "to": "这句诗出自《诗经·周南·关雎》。"}
    ]


def test_parse_grounding_verifier_response_rejects_unlisted_answer():
    result = parse_grounding_verifier_response(
        '{"verdict":"select","selected_answer":"《禽经·周南·关关》",'
        '"confidence":0.93,"reason":"bad merge"}',
        fallback_text="这句诗出自《诗经·周南·关雎》。",
        candidates=["诗经", "禽经", "关雎"],
        canonical_answers=["《诗经·周南·关雎》"],
    )

    assert result.status == "verifier_error"
    assert result.text == "这句诗出自《诗经·周南·关雎》。"
    assert result.reason == "verifier_selected_unlisted_answer"


def test_parse_grounding_verifier_response_handles_non_json():
    result = parse_grounding_verifier_response(
        "不是 JSON",
        fallback_text="原答案",
        candidates=[],
    )

    assert result.status == "verifier_error"
    assert result.text == "原答案"
    assert result.verifier["raw_excerpt"] == "不是 JSON"


def test_source_canonical_answers_ignore_polluted_related_titles():
    answers = source_canonical_answers_from_results(
        [
            {
                "results": [
                    {
                        "title": "周南·关雎_百科",
                        "content": (
                            "《关雎》是《诗经·周南》第一篇。"
                            "相关星图包括《已凉》《高唐赋》《四愁诗》。"
                            "《尔雅》《禽经》解释雎鸠这种鸟。"
                        ),
                    }
                ]
            }
        ]
    )

    assert answers == ["《诗经·周南·关雎》"]
