"""Local first-response decisions for voice turns."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

TaskType = Literal[
    "home_control",
    "home_state",
    "search_needed",
    "stable_fact",
    "planning",
    "high_risk",
    "unknown",
]

CueType = Literal["none", "thinking", "search", "confirmation", "planning"]

DEFAULT_PROCESSING_CUE_DELAY_S = 2.5
FAST_PROCESSING_CUE_DELAY_S = 0.35
THINKING_PROCESSING_CUE_DELAY_S = 1.2

_NORMALIZE_RE = re.compile(r"[\s《》「」『』“”\"'`·.。,:：，、_\-—!?！？]+")
_HOME_CONTROL_RE = re.compile(r"(打开|开启|关闭|关掉|调亮|调暗|设置|开一下|关一下)")
_HOME_STATE_RE = re.compile(r"(多少|是不是|现在|开着吗|关着吗|锁了吗|温度|湿度|状态)")
_EXPLICIT_SEARCH_RE = re.compile(
    r"(查一下|搜一下|搜索|最新|今天|明天|新闻|交通|天气|空气质量|说明书|错误码|固件|兼容|价格|电价)"
)
_STABLE_FACT_RE = re.compile(r"(出自哪里|出自哪|出处|谁写的|什么意思|是什么|典故|原文)")
_PLANNING_RE = re.compile(r"(帮我设计|规划|以后我说|如果.+就|自动化|场景|方案)")
_HIGH_RISK_RE = re.compile(
    r"(门锁|开门|报警|警报|车库门|卷帘门|门禁|热水器|取暖器|烤箱|炉灶|全屋)"
)

_QUOTE_ORIGINS = {
    "关关雎鸠在河之洲": "这句诗出自《诗经·国风·周南·关雎》。",
    "关关睢鸠在河之洲": "这句诗出自《诗经·国风·周南·关雎》。",
    "关关隹鸠在河之洲": "这句诗出自《诗经·国风·周南·关雎》。",
}


@dataclass(frozen=True, slots=True)
class FirstResponseDecision:
    """Local voice feedback policy before slow model/search work finishes."""

    task_type: TaskType
    cue: CueType
    spoken_hint: str
    processing_cue_delay_s: float
    reason: str

    def as_dict(self) -> dict[str, object]:
        """Return trace-safe metadata."""
        return {
            "task_type": self.task_type,
            "cue": self.cue,
            "spoken_hint": self.spoken_hint,
            "processing_cue_delay_s": self.processing_cue_delay_s,
            "reason": self.reason,
        }


def decide_first_response(text: str) -> FirstResponseDecision:
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

    checks = (
        (
            bool(_HIGH_RISK_RE.search(normalized)),
            ("high_risk", "confirmation", "这个需要确认。", "risk_keyword"),
            FAST_PROCESSING_CUE_DELAY_S,
        ),
        (
            bool(stable_fact_answer(normalized)),
            ("stable_fact", "none", "", "local_stable_knowledge"),
            DEFAULT_PROCESSING_CUE_DELAY_S,
        ),
        (
            bool(_PLANNING_RE.search(normalized)),
            (
                "planning",
                "planning",
                "我来规划一下，不会直接执行。",
                "planning_keyword",
            ),
            FAST_PROCESSING_CUE_DELAY_S,
        ),
        (
            bool(_EXPLICIT_SEARCH_RE.search(normalized)),
            ("search_needed", "search", "我查一下。", "explicit_or_current_search"),
            FAST_PROCESSING_CUE_DELAY_S,
        ),
        (
            bool(_STABLE_FACT_RE.search(normalized)),
            ("stable_fact", "thinking", "我看一下。", "stable_fact_question"),
            THINKING_PROCESSING_CUE_DELAY_S,
        ),
        (
            bool(_HOME_STATE_RE.search(normalized)),
            ("home_state", "none", "", "home_state_pattern"),
            DEFAULT_PROCESSING_CUE_DELAY_S,
        ),
        (
            bool(_HOME_CONTROL_RE.search(normalized)),
            ("home_control", "none", "", "home_control_pattern"),
            DEFAULT_PROCESSING_CUE_DELAY_S,
        ),
    )
    for matched, fields, delay_s in checks:
        if matched:
            task_type, cue, spoken_hint, reason = fields
            return _decision(task_type, cue, spoken_hint, delay_s, reason)

    return _decision(
        "unknown",
        "thinking",
        "我看一下。",
        THINKING_PROCESSING_CUE_DELAY_S,
        "fallback",
    )


def _decision(
    task_type: TaskType,
    cue: CueType,
    spoken_hint: str,
    processing_cue_delay_s: float,
    reason: str,
) -> FirstResponseDecision:
    return FirstResponseDecision(
        task_type=task_type,
        cue=cue,
        spoken_hint=spoken_hint,
        processing_cue_delay_s=processing_cue_delay_s,
        reason=reason,
    )


def stable_fact_answer(text: str) -> str | None:
    """Return a high-confidence local answer for tiny canonical knowledge."""
    normalized = _normalize(text)
    for quote, answer in _QUOTE_ORIGINS.items():
        if quote in normalized:
            return answer
    return None


def _normalize(text: str) -> str:
    return _NORMALIZE_RE.sub("", str(text or ""))
