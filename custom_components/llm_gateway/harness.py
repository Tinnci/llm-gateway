"""Scenario harness helpers for voice assistant regression tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .policy import should_allow_search
from .voice_text import markdown_to_spoken_text

_SENTENCE_MARKS = "。！？!?"


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


def evaluate_scenario(
    scenario: dict[str, Any],
    actual: dict[str, Any],
) -> HarnessResult:
    """Evaluate the core voice/policy expectations for one scenario."""
    violations: list[str] = []
    user = str(scenario.get("user") or scenario.get("user_utterance") or "")
    expected = scenario.get("expected") or {}
    spoken_expected = expected.get("spoken_response") or expected.get(
        "expected_spoken_style"
    ) or {}
    actual_response = str(actual.get("response") or actual.get("actual_response") or "")
    spoken = markdown_to_spoken_text(actual_response)

    if expected.get("must_search") is True and not should_allow_search(user):
        violations.append("search_required_but_policy_denied")
    if expected.get("must_search") is False and should_allow_search(user):
        violations.append("search_forbidden_but_policy_allowed")

    if spoken_expected.get("max_sentences") is not None:
        max_sentences = int(spoken_expected["max_sentences"])
        sentence_count = sum(spoken.count(mark) for mark in _SENTENCE_MARKS)
        if sentence_count > max_sentences:
            violations.append("spoken_response_too_long")

    violations.extend(
        f"spoken_missing:{required}"
        for required in spoken_expected.get("must_include", [])
        if str(required) not in spoken
    )

    for forbidden in spoken_expected.get("must_not_mention", []):
        forbidden_text = str(forbidden)
        if forbidden_text in actual_response or forbidden_text in spoken:
            violations.append(f"spoken_forbidden:{forbidden}")

    if expected.get("must_not_call_service_without_confirmation") and actual.get(
        "called_service"
    ):
        violations.append("unsafe_service_called_without_confirmation")

    return HarnessResult(not violations, violations)
