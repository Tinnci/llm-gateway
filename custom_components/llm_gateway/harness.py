"""Scenario harness helpers for voice assistant regression tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .capabilities import decide_route
from .policy import should_allow_search
from .voice_text import markdown_to_spoken_text

_SENTENCE_MARKS = "。！？!?"
_QUESTION_MARKS = "？?"
_CONFIRMATION_WORDS = ("确认", "确定", "吗")


@dataclass(frozen=True, slots=True)
class HarnessResult:
    """Result of one scenario evaluation."""

    passed: bool
    violations: list[str] = field(default_factory=list)


def load_yaml_scenarios(path: str | Path) -> list[dict[str, Any]]:
    """Load YAML scenarios from disk."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or []
    if isinstance(data, dict):
        data = data.get("scenarios", [])
    if not isinstance(data, list):
        raise TypeError("Scenario YAML must contain a list or a scenarios list")
    return [item for item in data if isinstance(item, dict)]


def evaluate_scenario(  # noqa: PLR0912 - compact rule list for harness reporting.
    scenario: dict[str, Any],
    actual: dict[str, Any],
) -> HarnessResult:
    """Evaluate the core voice/policy expectations for one scenario."""
    violations: list[str] = []
    user = str(scenario.get("user") or scenario.get("user_utterance") or "")
    expected = scenario.get("expected") or {}
    if not isinstance(expected, dict):
        expected = {}
    spoken_expected = (
        expected.get("spoken_response")
        or expected.get("expected_spoken_style")
        or scenario.get("expected_spoken_style")
        or {}
    )
    if not isinstance(spoken_expected, dict):
        spoken_expected = {}
    actual_response = str(actual.get("response") or actual.get("actual_response") or "")
    spoken = markdown_to_spoken_text(actual_response)
    expected_behavior = str(
        expected.get("behavior") or scenario.get("expected_behavior") or ""
    )
    risk_level = str(expected.get("risk_level") or scenario.get("risk_level") or "")
    route_decision = decide_route(user)
    route_expected = expected.get("route_decision") or expected.get("route")
    if not isinstance(route_expected, dict):
        route_expected = {}

    if (
        route_decision.requires_llm is False
        and route_decision.next_action == "answer_with_llm"
    ):
        violations.append("route_contract_non_llm_answers_with_llm")

    route_actual = route_decision.as_dict()
    for key, expected_value in route_expected.items():
        if route_actual.get(str(key)) != expected_value:
            violations.append(
                f"route_mismatch:{key}:expected={expected_value}:actual={route_actual.get(str(key))}"
            )

    if expected.get("must_search") is True and not should_allow_search(user):
        violations.append("search_required_but_policy_denied")
    if expected.get("must_search") is False and should_allow_search(user):
        violations.append("search_forbidden_but_policy_allowed")

    if spoken_expected.get("max_sentences") is not None:
        max_sentences = int(spoken_expected["max_sentences"])
        sentence_count = sum(spoken.count(mark) for mark in _SENTENCE_MARKS)
        if sentence_count > max_sentences:
            violations.append("spoken_response_too_long")

    if spoken_expected.get("max_questions") is not None:
        max_questions = int(spoken_expected["max_questions"])
        question_count = sum(spoken.count(mark) for mark in _QUESTION_MARKS)
        if question_count > max_questions:
            violations.append("spoken_response_too_many_questions")

    required_terms = [
        *spoken_expected.get("must_include", []),
        *spoken_expected.get("must_mention", []),
    ]
    violations.extend(
        f"spoken_missing:{required}"
        for required in required_terms
        if str(required) not in spoken
    )

    forbidden_terms = [
        *spoken_expected.get("must_not_mention", []),
        *spoken_expected.get("must_not_include", []),
    ]
    for forbidden in forbidden_terms:
        forbidden_text = str(forbidden)
        if forbidden_text in actual_response or forbidden_text in spoken:
            violations.append(f"spoken_forbidden:{forbidden}")

    unsafe_without_confirmation = expected.get(
        "must_not_call_service_without_confirmation"
    ) or (
        risk_level == "high"
        and expected_behavior in {"ask_confirmation", "confirm_before_action"}
    )
    if unsafe_without_confirmation and actual.get("called_service"):
        violations.append("unsafe_service_called_without_confirmation")

    if expected_behavior == "ask_confirmation" and not any(
        word in spoken for word in _CONFIRMATION_WORDS
    ):
        violations.append("confirmation_prompt_missing")

    return HarnessResult(not violations, violations)
