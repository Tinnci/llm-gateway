"""Local first-response decisions for voice turns."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from .capabilities import decide_route

TaskType = Literal[
    "home_control",
    "home_state",
    "weather_query",
    "indoor_environment_query",
    "outdoor_current_weather_query",
    "weather_forecast_query",
    "home_temperature_summary",
    "device_inventory_query",
    "area_inventory_query",
    "domain_inventory_query",
    "capability_query",
    "nearby_place_query",
    "exposed_context_query",
    "static_context_query",
    "search_needed",
    "stable_fact",
    "volume_control",
    "planning",
    "high_risk",
    "unknown",
]

CueType = Literal["none", "thinking", "search", "confirmation", "planning"]

DEFAULT_PROCESSING_CUE_DELAY_S = 2.5
FAST_PROCESSING_CUE_DELAY_S = 0.35
THINKING_PROCESSING_CUE_DELAY_S = 1.2

_NORMALIZE_RE = re.compile(r"[\s《》「」『』“”\"'`·.。,:：，、_\-—!?！？]+")
_QUOTE_ORIGINS = {
    "关关雎鸠在河之洲": "这句诗出自《诗经·国风·周南·关雎》。",
    "关关睢鸠在河之洲": "这句诗出自《诗经·国风·周南·关雎》。",
    "关关隹鸠在河之洲": "这句诗出自《诗经·国风·周南·关雎》。",
}
_ZHANG_RUOXU_WORKS_TERMS = ("诗", "代表作", "作品", "写过", "什么样")
_AUTHOR_TERMS = ("谁写", "谁写的", "作者")
_LI_BAI_WORKS_TERMS = ("代表作", "作品", "写过", "诗")


@dataclass(frozen=True, slots=True)
class FirstResponseDecision:
    """Local voice feedback policy before slow model/search work finishes."""

    task_type: TaskType
    cue: CueType
    spoken_hint: str
    processing_cue_delay_s: float
    reason: str
    audio_suppressed_reason: str = ""

    def as_dict(self) -> dict[str, object]:
        """Return trace-safe metadata."""
        return {
            "task_type": self.task_type,
            "cue": self.cue,
            "spoken_hint": self.spoken_hint,
            "processing_cue_delay_s": self.processing_cue_delay_s,
            "reason": self.reason,
            "audio_suppressed_reason": self.audio_suppressed_reason,
        }


def decide_first_response(text: str) -> FirstResponseDecision:  # noqa: PLR0911, PLR0912
    """Return local first-response policy for a user utterance."""
    normalized = str(text or "").strip()
    if not normalized:
        return _decision(
            "unknown",
            "thinking",
            "我看一下。",
            THINKING_PROCESSING_CUE_DELAY_S,
            "empty_or_unknown",
        )

    if stable_fact_answer(normalized):
        return _decision(
            "stable_fact",
            "none",
            "",
            DEFAULT_PROCESSING_CUE_DELAY_S,
            "local_stable_knowledge",
        )

    route = decide_route(normalized)
    if route.task_family in {"home_inventory", "home_capability"}:
        return _decision(
            route.task_type,
            "none",
            "",
            DEFAULT_PROCESSING_CUE_DELAY_S,
            "local_static_context_inventory",
            "fast_static_query",
        )
    if route.task_family == "location_dependent_query":
        return _decision(
            route.task_type,
            "none" if route.next_action == "ask_location_permission" else "search",
            "",
            DEFAULT_PROCESSING_CUE_DELAY_S,
            "location_dependent_query",
            "missing_location"
            if route.next_action == "ask_location_permission"
            else "",
        )
    if route.task_type == "planning":
        return _decision(
            "planning",
            "planning",
            "我来规划一下，不会直接执行。",
            FAST_PROCESSING_CUE_DELAY_S,
            "planning_keyword",
        )
    if route.task_type == "search_needed":
        return _decision(
            "search_needed",
            "search",
            "我查一下。",
            FAST_PROCESSING_CUE_DELAY_S,
            "explicit_or_current_search",
        )
    if route.task_type in {"weather_query", "outdoor_current_weather_query"}:
        return _decision(
            route.task_type,
            "none",
            "",
            DEFAULT_PROCESSING_CUE_DELAY_S,
            "home_state_weather",
        )
    if route.task_type == "weather_forecast_query":
        return _decision(
            "weather_forecast_query",
            "search",
            "",
            DEFAULT_PROCESSING_CUE_DELAY_S,
            "weather_forecast",
        )
    if route.task_type in {
        "home_state",
        "indoor_environment_query",
        "home_temperature_summary",
    }:
        return _decision(
            route.task_type,
            "none",
            "",
            DEFAULT_PROCESSING_CUE_DELAY_S,
            "home_state_pattern",
        )
    if route.task_type == "stable_fact":
        return _decision(
            "stable_fact",
            "none",
            "",
            DEFAULT_PROCESSING_CUE_DELAY_S,
            "stable_fact_question",
        )
    if route.task_family == "volume_control":
        return _decision(
            "volume_control",
            "none",
            "",
            DEFAULT_PROCESSING_CUE_DELAY_S,
            "volume_control",
        )
    if route.task_type == "home_control":
        return _decision(
            "home_control",
            "none",
            "",
            DEFAULT_PROCESSING_CUE_DELAY_S,
            "home_control_pattern",
        )
    if route.task_type == "high_risk":
        return _decision(
            "high_risk",
            "confirmation",
            "这个需要确认。",
            FAST_PROCESSING_CUE_DELAY_S,
            "risk_keyword",
        )
    if route.task_family == "content_generation":
        return _decision(
            "unknown",
            "none",
            "",
            DEFAULT_PROCESSING_CUE_DELAY_S,
            "content_generation",
        )

    return _decision(
        "unknown",
        "none",
        "",
        THINKING_PROCESSING_CUE_DELAY_S,
        "unknown_or_ambiguous",
    )


def _decision(  # noqa: PLR0913 - mirrors FirstResponseDecision fields.
    task_type: TaskType,
    cue: CueType,
    spoken_hint: str,
    processing_cue_delay_s: float,
    reason: str,
    audio_suppressed_reason: str = "",
) -> FirstResponseDecision:
    return FirstResponseDecision(
        task_type=task_type,
        cue=cue,
        spoken_hint=spoken_hint,
        processing_cue_delay_s=processing_cue_delay_s,
        reason=reason,
        audio_suppressed_reason=audio_suppressed_reason,
    )


def stable_fact_answer(text: str) -> str | None:
    """Return a high-confidence local answer for tiny canonical knowledge."""
    normalized = _normalize(text)
    for quote, answer in _QUOTE_ORIGINS.items():
        if quote in normalized:
            return answer
    if "张若虚" in normalized and any(
        term in normalized for term in _ZHANG_RUOXU_WORKS_TERMS
    ):
        return (
            "张若虚是唐代诗人，存世作品很少，最著名的是《春江花月夜》。"
            "通常提到他的代表作，主要就是这首。"
        )
    if "春江花月夜" in normalized and any(term in normalized for term in _AUTHOR_TERMS):
        return "《春江花月夜》的作者是唐代诗人张若虚。"
    if "李白" in normalized and any(term in normalized for term in _LI_BAI_WORKS_TERMS):
        return (
            "李白的代表作包括《静夜思》《将进酒》《蜀道难》《望庐山瀑布》《行路难》等。"
        )
    return None


def _normalize(text: str) -> str:
    return _NORMALIZE_RE.sub("", str(text or ""))
