"""Tests for voice scenario harness helpers."""

from __future__ import annotations

from custom_components.llm_gateway.harness import evaluate_scenario


def test_evaluate_scenario_checks_spoken_style():
    result = evaluate_scenario(
        {
            "user": "把门打开",
            "expected": {
                "must_search": False,
                "spoken_response": {
                    "max_sentences": 2,
                    "must_include": ["确认"],
                    "must_not_mention": ["entity_id"],
                },
            },
        },
        {"response": "要打开前门门锁吗？请确认。"},
    )
    assert result.passed


def test_evaluate_scenario_reports_forbidden_text():
    result = evaluate_scenario(
        {
            "user": "打开卧室灯",
            "expected": {
                "spoken_response": {"must_not_mention": ["entity_id"]},
            },
        },
        {"response": "已调用 entity_id light.bedroom。"},
    )
    assert not result.passed
    assert "spoken_forbidden:entity_id" in result.violations
