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


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    """Result of policy validation."""

    allowed: bool
    reason: str = "allowed"
    spoken_prompt: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def should_allow_search(
    text: str,
    route_decision: RouteDecision | None = None,
) -> bool:
    """Return whether the assistant may use web search for this user turn."""
    route = route_decision or decide_route(text)
    return "search_web" in route.allowed_tools and not route.missing_requirements


def should_force_search_in_voice_path(
    text: str,
    route_decision: RouteDecision | None = None,
) -> bool:
    """Request search first when the committed route selects that operation."""
    route = route_decision or decide_route(text)
    return route.next_action == "search" and should_allow_search(text, route)


def validate_tool_call(  # noqa: PLR0911
    tool_call: llm.ToolInput,
    user_text: str,
    route_decision: RouteDecision | None = None,
) -> PolicyDecision:
    """Validate a proposed tool call before execution."""
    route = route_decision or decide_route(user_text)
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
        if should_allow_search(user_text, route):
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
