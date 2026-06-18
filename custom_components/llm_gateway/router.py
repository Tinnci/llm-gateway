"""Model routing for voice-first assistant turns."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from .const import (
    CONF_CHAT_MODEL,
    CONF_CHAT_TIMEOUT,
    CONF_DEEP_CHAT_TIMEOUT,
    CONF_DEEP_EXTRA_BODY,
    CONF_DEEP_MAX_TOKENS,
    CONF_DEEP_MODEL,
    CONF_EXTRA_BODY,
    CONF_FAST_CHAT_TIMEOUT,
    CONF_FAST_EXTRA_BODY,
    CONF_FAST_MAX_TOKENS,
    CONF_FAST_MODEL,
    CONF_MAX_TOKENS,
    CONF_MID_CHAT_TIMEOUT,
    CONF_MID_EXTRA_BODY,
    CONF_MID_MAX_TOKENS,
    CONF_MID_MODEL,
    CONF_ROUTING_MODE,
    LOGGER,
    RECOMMENDED_DEEP_CHAT_TIMEOUT,
    RECOMMENDED_DEEP_MAX_TOKENS,
    RECOMMENDED_DEEP_MODEL,
    RECOMMENDED_FAST_CHAT_TIMEOUT,
    RECOMMENDED_FAST_MAX_TOKENS,
    RECOMMENDED_FAST_MODEL,
    RECOMMENDED_MID_CHAT_TIMEOUT,
    RECOMMENDED_MID_MAX_TOKENS,
    RECOMMENDED_MID_MODEL,
    ROUTING_MODE_AUTO,
    ROUTING_MODE_DEEP,
    ROUTING_MODE_FAST,
    ROUTING_MODE_MID,
)

RouteKind = Literal["fast", "mid", "deep"]
_DEEP_LENGTH_THRESHOLD = 120

_DEEP_KEYWORDS = (
    "深度",
    "详细分析",
    "完整分析",
    "完整方案",
    "架构",
    "规划",
    "长文",
    "比较一下",
    "做一个方案",
    "排查方案",
)
_MID_KEYWORDS = (
    "查一下",
    "搜一下",
    "搜索",
    "最新",
    "说明书",
    "错误码",
    "固件",
    "兼容",
    "为什么",
    "诊断",
    "排查",
    "天气",
    "新闻",
    "交通",
    "电价",
)


@dataclass(frozen=True, slots=True)
class ModelRoute:
    """Resolved model route and generation settings."""

    kind: RouteKind
    model: str
    max_tokens: int
    timeout_s: int
    extra_body: dict[str, Any] | None
    async_deep_task: bool = False


def select_model_route(text: str, options: dict[str, Any]) -> ModelRoute:
    """Choose the route and settings for one user turn."""
    mode = options.get(CONF_ROUTING_MODE, ROUTING_MODE_AUTO)
    if mode == ROUTING_MODE_FAST:
        kind: RouteKind = "fast"
    elif mode == ROUTING_MODE_MID:
        kind = "mid"
    elif mode == ROUTING_MODE_DEEP:
        kind = "deep"
    else:
        kind = classify_route(text)

    return _route_from_options(kind, options)


def classify_route(text: str) -> RouteKind:
    """Classify a user turn into fast/mid/deep."""
    normalized = text.strip().lower()
    if not normalized:
        return "fast"

    if len(normalized) > _DEEP_LENGTH_THRESHOLD or any(
        keyword in normalized for keyword in _DEEP_KEYWORDS
    ):
        return "deep"
    if any(keyword in normalized for keyword in _MID_KEYWORDS):
        return "mid"
    return "fast"


def parse_extra_body(raw: str | None) -> dict[str, Any] | None:
    """Parse optional OpenAI-compatible extra body JSON."""
    if not raw:
        return None

    try:
        parsed = json.loads(raw.strip())
    except ValueError:
        LOGGER.warning("Ignoring invalid extra_body JSON")
        return None

    if not isinstance(parsed, dict):
        LOGGER.warning("Ignoring non-object extra_body JSON")
        return None

    return parsed


def _route_from_options(kind: RouteKind, options: dict[str, Any]) -> ModelRoute:
    if kind == "fast":
        return ModelRoute(
            kind=kind,
            model=options.get(CONF_FAST_MODEL)
            or options.get(CONF_CHAT_MODEL)
            or RECOMMENDED_FAST_MODEL,
            max_tokens=int(
                options.get(CONF_FAST_MAX_TOKENS)
                or options.get(CONF_MAX_TOKENS)
                or RECOMMENDED_FAST_MAX_TOKENS
            ),
            timeout_s=int(
                options.get(CONF_FAST_CHAT_TIMEOUT)
                or options.get(CONF_CHAT_TIMEOUT)
                or RECOMMENDED_FAST_CHAT_TIMEOUT
            ),
            extra_body=parse_extra_body(
                options.get(CONF_FAST_EXTRA_BODY) or options.get(CONF_EXTRA_BODY)
            ),
        )

    if kind == "mid":
        return ModelRoute(
            kind=kind,
            model=options.get(CONF_MID_MODEL) or RECOMMENDED_MID_MODEL,
            max_tokens=int(
                options.get(CONF_MID_MAX_TOKENS) or RECOMMENDED_MID_MAX_TOKENS
            ),
            timeout_s=int(
                options.get(CONF_MID_CHAT_TIMEOUT) or RECOMMENDED_MID_CHAT_TIMEOUT
            ),
            extra_body=parse_extra_body(options.get(CONF_MID_EXTRA_BODY)),
        )

    return ModelRoute(
        kind=kind,
        model=options.get(CONF_DEEP_MODEL) or RECOMMENDED_DEEP_MODEL,
        max_tokens=int(
            options.get(CONF_DEEP_MAX_TOKENS) or RECOMMENDED_DEEP_MAX_TOKENS
        ),
        timeout_s=int(
            options.get(CONF_DEEP_CHAT_TIMEOUT) or RECOMMENDED_DEEP_CHAT_TIMEOUT
        ),
        extra_body=parse_extra_body(options.get(CONF_DEEP_EXTRA_BODY)),
        async_deep_task=True,
    )


def legacy_model_from_options(options: dict[str, Any]) -> str:
    """Return the configured model for device info while preserving old options."""
    return (
        options.get(CONF_FAST_MODEL)
        or options.get(CONF_CHAT_MODEL)
        or RECOMMENDED_FAST_MODEL
    )
