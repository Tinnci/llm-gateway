"""Policy decisions for tool use and web search."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .capabilities import RouteDecision, decide_route

if TYPE_CHECKING:
    from homeassistant.helpers import llm

HIGH_RISK_DOMAINS = {
    "lock",
    "alarm_control_panel",
    "cover",
    "valve",
}
HIGH_RISK_KEYWORDS = (
    "门锁",
    "锁",
    "报警",
    "警报",
    "车库门",
    "卷帘门",
    "门禁",
    "热水器",
    "取暖器",
    "烤箱",
    "炉灶",
    "全屋",
)
CONFIRMATION_KEYWORDS = ("确认", "确定", "是的", "对", "执行", "打开吧", "关掉吧")

_SEARCH_ALLOW_KEYWORDS = (
    "查一下",
    "搜一下",
    "搜索",
    "网上",
    "上网",
    "联网",
    "外网",
    "最新",
    "新闻",
    "交通",
    "说明书",
    "错误码",
    "固件",
    "兼容",
    "价格",
    "电价",
    "发布",
    "出处",
    "出自哪里",
    "来源",
    "典故",
    "原文",
)
_SEARCH_REQUIRE_KEYWORDS = (
    "出处",
    "出自哪里",
    "典故",
    "原文",
)
_VOICE_PATH_SEARCH_KEYWORDS = (
    "查一下",
    "搜一下",
    "搜索",
    "网上",
    "上网",
    "联网",
    "外网",
    "最新",
    "新闻",
    "交通",
    "说明书",
    "错误码",
    "固件",
    "兼容",
    "价格",
    "电价",
    "发布",
)
_SEARCH_FORBID_KEYWORDS = (
    "打开",
    "关",
    "调暗",
    "调亮",
    "设置",
    "温度",
    "湿度",
    "室温",
    "刚才",
    "那个",
    "它",
)


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    """Result of policy validation."""

    allowed: bool
    reason: str = "allowed"
    spoken_prompt: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def should_allow_search(text: str) -> bool:
    """Return whether the assistant may use web search for this user turn."""
    normalized = text.strip().lower()
    if not normalized:
        return False
    route = decide_route(text)
    if route.task_family in {"location_dependent_query", "external_current_info"}:
        return "search_web" in route.allowed_tools and not route.missing_requirements
    if route.task_family in {
        "home_control",
        "home_inventory",
        "home_capability",
        "home_state",
        "conversation_control",
    }:
        return False
    if any(keyword in normalized for keyword in _SEARCH_ALLOW_KEYWORDS):
        return True
    if any(keyword in normalized for keyword in _SEARCH_FORBID_KEYWORDS):
        return False
    return False


def should_require_search(text: str) -> bool:
    """Return whether the assistant should ground the turn with web search."""
    normalized = text.strip().lower()
    return should_allow_search(normalized) and any(
        keyword in normalized for keyword in _SEARCH_REQUIRE_KEYWORDS
    )


def should_force_search_in_voice_path(text: str) -> bool:
    """Return whether search should be forced before the first model answer."""
    normalized = text.strip().lower()
    if not normalized:
        return False
    route = decide_route(text)
    if route.task_family == "location_dependent_query":
        return route.next_action == "search"
    if route.task_family == "external_current_info":
        return route.next_action == "search" and not route.missing_requirements
    return should_allow_search(normalized) and any(
        keyword in normalized for keyword in _VOICE_PATH_SEARCH_KEYWORDS
    )


def validate_tool_call(  # noqa: PLR0911
    tool_call: llm.ToolInput, user_text: str
) -> PolicyDecision:
    """Validate a proposed tool call before execution."""
    route = decide_route(user_text)
    if tool_call.external and tool_call.tool_name == "search_web":
        if route.missing_requirements:
            return PolicyDecision(
                allowed=False,
                reason="missing_user_slot",
                spoken_prompt=_search_block_prompt(route),
                metadata=_policy_metadata(
                    route,
                    blocked_reason="missing_user_slot",
                    policy_name="external_search_policy",
                ),
            )
        if should_allow_search(user_text) and "search_web" in route.allowed_tools:
            return PolicyDecision(allowed=True, metadata=_policy_metadata(route))
        return PolicyDecision(
            allowed=False,
            reason="search_forbidden",
            spoken_prompt=_search_block_prompt(route),
            metadata=_policy_metadata(
                route,
                blocked_reason="search_forbidden",
                policy_name="external_search_policy",
            ),
        )

    if not _is_home_action(tool_call.tool_name):
        return PolicyDecision(allowed=True, metadata=_policy_metadata(route))

    if not _requires_confirmation(tool_call):
        return PolicyDecision(allowed=True, metadata=_policy_metadata(route))

    if _contains_confirmation(user_text):
        return PolicyDecision(allowed=True, metadata={"confirmed": True})

    target = _target_label(tool_call)
    return PolicyDecision(
        allowed=False,
        reason="confirmation_required",
        spoken_prompt=f"要操作{target}吗？请确认。",
        metadata=_policy_metadata(
            route,
            blocked_reason="confirmation_required",
            user_visible_action="ask_confirmation",
            policy_name="high_risk_confirmation",
            extra={"risk": "high", "target": target},
        ),
    )


def _search_block_prompt(route: RouteDecision) -> str:
    if route.missing_requirements:
        return route.user_visible_prompt or "这个问题还缺少必要信息。"
    if route.task_family == "unknown_or_ambiguous":
        return "我还不确定你想查什么，可以换个说法吗？"
    if route.task_type == "weather_forecast_query":
        return "我现在没有可用的天气预报来源，不能直接查明天的天气。"
    return "当前不能使用搜索来回答这个问题。"


def _policy_metadata(
    route: RouteDecision,
    *,
    blocked_reason: str = "",
    user_visible_action: str = "",
    policy_name: str = "",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "task_family": route.task_family,
        "task_type": route.task_type,
        "blocked_reason": blocked_reason,
        "user_visible_action": user_visible_action or route.next_action,
        "allowed_tools": list(route.allowed_tools),
        "missing_requirements": list(route.missing_requirements),
        "policy_name": policy_name,
        **(extra or {}),
    }


def _is_home_action(tool_name: str) -> bool:
    return tool_name.startswith("Hass")


def _requires_confirmation(tool_call: llm.ToolInput) -> bool:
    args = tool_call.tool_args
    text = str(args)
    domain = str(args.get("domain") or args.get("entity_domain") or "")
    service = str(args.get("service") or "")

    if domain in HIGH_RISK_DOMAINS:
        return True
    if domain == "switch" and any(keyword in text for keyword in HIGH_RISK_KEYWORDS):
        return True
    if service in {"unlock", "open_cover", "open"}:
        return True
    return any(keyword in text for keyword in HIGH_RISK_KEYWORDS)


def _contains_confirmation(user_text: str) -> bool:
    return any(keyword in user_text for keyword in CONFIRMATION_KEYWORDS)


def _target_label(tool_call: llm.ToolInput) -> str:
    args = tool_call.tool_args
    for key in ("name", "area", "device", "entity_id", "domain"):
        if value := args.get(key):
            return str(value)
    return "这个高风险设备"
