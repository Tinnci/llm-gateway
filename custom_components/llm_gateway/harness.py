"""Scenario harness helpers for voice assistant regression tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

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
    computed_route = decide_route(user).as_dict()
    route_decision = (
        actual.get("route_decision")
        if isinstance(actual.get("route_decision"), dict)
        else computed_route
    )
    route_expected = expected.get("route_decision") or expected.get("route")
    if not isinstance(route_expected, dict):
        route_expected = {}

    if (
        route_decision.get("requires_llm") is False
        and route_decision.get("next_action") == "answer_with_llm"
    ):
        violations.append("route_contract_non_llm_answers_with_llm")

    violations.extend(_route_violations(route_decision, route_expected))
    violations.extend(
        _nested_expectation_violations(
            actual.get("tool_args"),
            expected.get("tool_args"),
            prefix="tool_args",
        )
    )
    violations.extend(
        _nested_expectation_violations(
            actual.get("outcome_verdict"),
            expected.get("outcome_verdict"),
            prefix="outcome_verdict",
        )
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


def _nested_expectation_violations(
    actual: object,
    expected: object,
    *,
    prefix: str,
) -> list[str]:
    """Compare a bounded expected mapping against captured runtime evidence."""
    if not isinstance(expected, dict):
        return []
    actual_mapping = actual if isinstance(actual, dict) else {}
    return [
        f"{prefix}_mismatch:{key}:expected={expected_value}:"
        f"actual={actual_mapping.get(str(key))}"
        for key, expected_value in expected.items()
        if actual_mapping.get(str(key)) != expected_value
    ]


def _route_violations(
    route_actual: dict[str, Any],
    route_expected: dict[str, Any],
) -> list[str]:
    violations: list[str] = []
    for key, expected_value in route_expected.items():
        if key == "metadata" and isinstance(expected_value, dict):
            violations.extend(_route_metadata_violations(route_actual, expected_value))
            continue
        actual_value = route_actual.get(str(key))
        if actual_value != expected_value:
            violations.append(
                f"route_mismatch:{key}:expected={expected_value}:actual={actual_value}"
            )
    return violations


def _route_metadata_violations(
    route_actual: dict[str, Any],
    metadata_expected: dict[str, Any],
) -> list[str]:
    actual_metadata = route_actual.get("metadata")
    if not isinstance(actual_metadata, dict):
        actual_metadata = {}
    violations: list[str] = []
    for metadata_key, expected_value in metadata_expected.items():
        actual_value = actual_metadata.get(str(metadata_key))
        if actual_value != expected_value:
            violations.append(
                "route_mismatch:"
                f"metadata.{metadata_key}:expected={expected_value}:"
                f"actual={actual_value}"
            )
    return violations
