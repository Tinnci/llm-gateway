"""Capability-based semantic routing for assistant turns."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from .static_context import classify_inventory_query

TaskFamily = Literal[
    "home_control",
    "home_state",
    "home_inventory",
    "home_capability",
    "volume_control",
    "location_dependent_query",
    "external_current_info",
    "stable_knowledge",
    "content_generation",
    "automation_planning",
    "conversation_control",
    "general_conversation",
    "unknown_or_ambiguous",
]

TaskType = Literal[
    "home_control",
    "home_state",
    "weather_query",
    "device_inventory_query",
    "area_inventory_query",
    "domain_inventory_query",
    "capability_query",
    "exposed_context_query",
    "static_context_query",
    "nearby_place_query",
    "volume_control",
    "search_needed",
    "stable_fact",
    "planning",
    "conversation_control",
    "general_conversation",
    "content_generation",
    "high_risk",
    "unknown",
]

NextAction = Literal[
    "execute_local",
    "call_tool_then_local_render",
    "ask_location_permission",
    "search",
    "ask_confirmation",
    "answer_with_llm",
    "clarify",
    "plan_async",
]

RiskLevel = Literal["low", "privacy_location", "high"]

_LOCATION_WORDS = (
    "附近",
    "最近",
    "离我最近",
    "离我近",
    "周边",
    "旁边",
    "身边",
    "附近有没有",
)
_PLACE_WORDS = (
    "麦当劳",
    "肯德基",
    "星巴克",
    "咖啡",
    "咖啡店",
    "药店",
    "便利店",
    "超市",
    "餐厅",
    "饭店",
    "快餐",
    "医院",
    "诊所",
    "银行",
    "atm",
    "加油站",
    "停车场",
    "地铁站",
    "公交站",
)
_PLACE_QUERY_WORDS = ("在哪", "哪里", "找", "有没有", "怎么走", "地址", "位置")
_EXPLICIT_LOCATION_HINTS = (
    "上海",
    "静安",
    "浦东",
    "黄浦",
    "徐汇",
    "长宁",
    "人民广场",
    "南京西路",
    "陆家嘴",
)
_HOME_CONTROL_RE = re.compile(
    r"(打开|开启|关闭|关掉|关上|开了|关了|调亮|调暗|设置|开一下|关一下)"
)
_HOME_STATE_RE = re.compile(r"(多少|是不是|现在|开着吗|关着吗|锁了吗|温度|湿度|状态)")
_WEATHER_RE = re.compile(
    r"(天气|空气质量|空气怎么样|下雨|雨|外面|室外|冷不冷|热不热|气温|pm2\.?5|雾霾)"
)
_EXTERNAL_CURRENT_RE = re.compile(
    r"(查一下|搜一下|搜索|网上|上网|联网|外网|最新|新闻|交通|说明书|错误码|固件|兼容|价格|电价|发布)"
)
_EXPLICIT_EXTERNAL_RE = re.compile(
    r"(搜一下|搜索|网上|上网|联网|外网|最新|新闻|交通|说明书|错误码|固件|兼容|价格|电价|发布)"
)
_STABLE_KNOWLEDGE_RE = re.compile(
    r"(出自哪里|出自哪|出处|谁写的|什么意思|是什么|典故|原文)"
)
_LITERARY_KNOWLEDGE_RE = re.compile(
    r"(诗|词|代表作|作品|作者|诗人|文学|春江花月夜|张若虚|李白|杜甫|苏轼|王维|白居易)"
)
_LITERARY_QUERY_RE = re.compile(
    r"(有什么|有哪些|什么样|哪首|是谁写|谁写|写过|代表作|作品|作者|赏析|意思|理解)"
)
_VOLUME_RE = re.compile(
    r"(音量|声音|声量|大声|小声|调大|调小|调高|调低|最大|最小|静音)"
)
_ASSISTANT_VOLUME_RE = re.compile(r"(自己|你说话|你的声音|助手|播报|回答声音|说话声音)")
_MEDIA_VOLUME_RE = re.compile(r"(音箱|播放器|homepod|喇叭|扬声器|电视|客厅|卧室|媒体)")
_PLANNING_RE = re.compile(
    r"(帮我设计|规划|以后我说|如果.+就|自动化|场景|方案|深度分析|详细分析|完整分析|架构|排查方案|控制管线)"
)
_HIGH_RISK_RE = re.compile(
    r"(门锁|开门|前门|后门|报警|警报|车库门|卷帘门|门禁|热水器|取暖器|烤箱|炉灶|全屋)"
)
_CONVERSATION_CONTROL_RE = re.compile(r"^(停|停止|别说了|取消|不用了|等一下|等等)$")
_GREETING_RE = re.compile(
    r"^(你好|您好|嗨|hello|hi|在吗|早上好|下午好|晚上好)[。！？!,.，\s]*$",
    re.IGNORECASE,
)
_CONTENT_GENERATION_RE = re.compile(
    r"(写|生成|总结|翻译|润色|起草|讲个|解释一下|说明一下)"
)
_NORMALIZE_RE = re.compile(r"[\s《》「」『』“”\"'`·.。,:：，、_\-—!?！？]+")


@dataclass(frozen=True, slots=True)
class Capability:
    """Registered assistant capability family."""

    family: TaskFamily
    examples: tuple[str, ...]
    route: str
    tools: tuple[str, ...] = ()
    requires_llm: bool = False
    requires_location: bool = False
    requires_live_home_context: bool = False
    requires_external_info: bool = False


@dataclass(frozen=True, slots=True)
class RouteDecision:
    """Structured route decision shared by router, policy, and trace."""

    task_family: TaskFamily
    task_type: TaskType
    confidence: float
    requires_location: bool = False
    requires_live_home_context: bool = False
    requires_external_info: bool = False
    requires_user_confirmation: bool = False
    requires_llm: bool = False
    allowed_tools: tuple[str, ...] = ()
    forbidden_tools: tuple[str, ...] = ()
    next_action: NextAction = "answer_with_llm"
    user_visible_prompt: str = ""
    route: str = "fast"
    risk: RiskLevel = "low"
    missing_requirements: tuple[str, ...] = ()
    matched_capability: str = ""
    metadata: dict[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        """Return trace-safe metadata."""
        return {
            "task_family": self.task_family,
            "task_type": self.task_type,
            "confidence": self.confidence,
            "requires_location": self.requires_location,
            "requires_live_home_context": self.requires_live_home_context,
            "requires_external_info": self.requires_external_info,
            "requires_user_confirmation": self.requires_user_confirmation,
            "requires_llm": self.requires_llm,
            "allowed_tools": list(self.allowed_tools),
            "forbidden_tools": list(self.forbidden_tools),
            "next_action": self.next_action,
            "user_visible_prompt": self.user_visible_prompt,
            "route": self.route,
            "risk": self.risk,
            "missing_requirements": list(self.missing_requirements),
            "matched_capability": self.matched_capability,
            "metadata": dict(self.metadata),
        }


CAPABILITY_REGISTRY: tuple[Capability, ...] = (
    Capability(
        family="home_control",
        examples=("打开客厅灯", "把卧室灯调暗一点", "关闭风扇"),
        route="home_action",
        tools=("HassTurnOn", "HassTurnOff", "HassCallService"),
    ),
    Capability(
        family="home_inventory",
        examples=(
            "你能看到哪些设备",
            "家里有哪些设备",
            "卧室有什么设备",
            "有哪些灯",
        ),
        route="local_static_context",
    ),
    Capability(
        family="home_capability",
        examples=("你能控制什么", "你现在接入了哪些东西", "你支持哪些设备"),
        route="local_static_context",
    ),
    Capability(
        family="home_state",
        examples=("家里 PM2.5 是多少", "客厅温度多少", "今天天气怎么样"),
        route="local_live_context",
        tools=("GetLiveContext",),
        requires_live_home_context=True,
    ),
    Capability(
        family="volume_control",
        examples=("把自己的音量调到最大", "你说话声音大一点", "把客厅音箱音量调高"),
        route="local_clarify_or_home_action",
        tools=("HassCallService",),
    ),
    Capability(
        family="location_dependent_query",
        examples=(
            "附近最近的麦当劳在哪里",
            "附近有没有药店",
            "离我最近的便利店",
            "附近咖啡店",
        ),
        route="location_search",
        tools=("get_location", "search_places", "search_web"),
        requires_location=True,
        requires_external_info=True,
    ),
    Capability(
        family="external_current_info",
        examples=("今天有什么新闻", "Home Assistant 最新版本", "查一下错误码"),
        route="search",
        tools=("search_web",),
        requires_external_info=True,
        requires_llm=True,
    ),
    Capability(
        family="stable_knowledge",
        examples=("这句话出自哪里", "张若虚有什么样的诗", "李白有什么代表作"),
        route="fast_qa",
        requires_llm=True,
    ),
    Capability(
        family="automation_planning",
        examples=("帮我设计一个自动化", "以后我说睡觉就关灯", "如果晚上十一点就执行"),
        route="deep_async",
        requires_llm=True,
    ),
    Capability(
        family="conversation_control",
        examples=("停", "取消", "别说了"),
        route="local_control",
    ),
    Capability(
        family="general_conversation",
        examples=("你好", "在吗"),
        route="fast",
        requires_llm=True,
    ),
    Capability(
        family="content_generation",
        examples=("写一段文字", "总结一下", "翻译这句话"),
        route="fast",
        requires_llm=True,
    ),
    Capability(
        family="unknown_or_ambiguous",
        examples=("无法判定的请求", "歧义请求"),
        route="local_clarify",
    ),
)


def decide_route(text: str) -> RouteDecision:  # noqa: PLR0911, PLR0912
    """Return a structured capability route decision for one utterance."""
    value = str(text or "").strip()
    normalized = _normalize(value)
    if not normalized:
        return _unknown("empty")

    if _CONVERSATION_CONTROL_RE.search(value):
        return RouteDecision(
            task_family="conversation_control",
            task_type="conversation_control",
            confidence=0.96,
            next_action="execute_local",
            route="local_control",
            matched_capability="conversation_control",
        )

    if _GREETING_RE.search(value):
        return RouteDecision(
            task_family="general_conversation",
            task_type="general_conversation",
            confidence=0.92,
            requires_llm=True,
            next_action="answer_with_llm",
            route="fast",
            matched_capability="general_conversation",
        )

    if _HIGH_RISK_RE.search(value):
        return RouteDecision(
            task_family="home_control",
            task_type="high_risk",
            confidence=0.9,
            requires_user_confirmation=True,
            allowed_tools=("HassTurnOn", "HassTurnOff", "HassCallService"),
            next_action="ask_confirmation",
            user_visible_prompt="这个需要确认。",
            risk="high",
            matched_capability="home_control",
        )

    if _VOLUME_RE.search(value):
        return _volume_route(value)

    inventory_spec = classify_inventory_query(value)
    if inventory_spec is not None:
        family: TaskFamily = (
            "home_capability"
            if inventory_spec.task_type in {"capability_query", "exposed_context_query"}
            else "home_inventory"
        )
        return RouteDecision(
            task_family=family,
            task_type=inventory_spec.task_type,
            confidence=0.98,
            next_action="execute_local",
            route="local_static_context",
            matched_capability=family,
        )

    if _is_location_dependent(value, normalized):
        has_location = _has_explicit_location(value)
        return RouteDecision(
            task_family="location_dependent_query",
            task_type="nearby_place_query",
            confidence=0.86,
            requires_location=True,
            requires_external_info=True,
            requires_llm=has_location,
            allowed_tools=("get_location", "search_places", "search_web"),
            forbidden_tools=("HassTurnOn", "HassTurnOff", "HassCallService"),
            next_action="search" if has_location else "ask_location_permission",
            user_visible_prompt=""
            if has_location
            else "我需要知道你的位置才能查附近地点。要使用当前位置吗？",
            route="mid" if has_location else "local_clarify",
            risk="privacy_location",
            missing_requirements=() if has_location else ("location",),
            matched_capability="location_dependent_query",
            metadata={"explicit_location": has_location},
        )

    if _EXPLICIT_EXTERNAL_RE.search(value):
        return RouteDecision(
            task_family="external_current_info",
            task_type="search_needed",
            confidence=0.82,
            requires_external_info=True,
            requires_llm=True,
            allowed_tools=("search_web",),
            next_action="search",
            route="mid",
            matched_capability="external_current_info",
        )

    if _PLANNING_RE.search(value):
        return RouteDecision(
            task_family="automation_planning",
            task_type="planning",
            confidence=0.86,
            requires_llm=True,
            next_action="plan_async",
            user_visible_prompt="我来规划一下，不会直接执行。",
            route="deep",
            matched_capability="automation_planning",
        )

    if _WEATHER_RE.search(value):
        return RouteDecision(
            task_family="home_state",
            task_type="weather_query",
            confidence=0.82,
            requires_live_home_context=True,
            allowed_tools=("GetLiveContext",),
            next_action="call_tool_then_local_render",
            route="local_live_context",
            matched_capability="home_state",
        )

    if _EXTERNAL_CURRENT_RE.search(value):
        return RouteDecision(
            task_family="external_current_info",
            task_type="search_needed",
            confidence=0.78,
            requires_external_info=True,
            requires_llm=True,
            allowed_tools=("search_web",),
            next_action="search",
            route="mid",
            matched_capability="external_current_info",
        )

    if _HOME_STATE_RE.search(value):
        return RouteDecision(
            task_family="home_state",
            task_type="home_state",
            confidence=0.74,
            requires_live_home_context=True,
            allowed_tools=("GetLiveContext",),
            next_action="call_tool_then_local_render",
            route="local_live_context",
            matched_capability="home_state",
        )

    if _STABLE_KNOWLEDGE_RE.search(value) or _is_literary_knowledge(value):
        return RouteDecision(
            task_family="stable_knowledge",
            task_type="stable_fact",
            confidence=0.78,
            requires_llm=True,
            next_action="answer_with_llm",
            route="fast",
            matched_capability="literary_knowledge"
            if _is_literary_knowledge(value)
            else "stable_knowledge",
        )

    if _HOME_CONTROL_RE.search(value):
        return RouteDecision(
            task_family="home_control",
            task_type="home_control",
            confidence=0.72,
            allowed_tools=("HassTurnOn", "HassTurnOff", "HassCallService"),
            next_action="answer_with_llm",
            route="fast",
            matched_capability="home_control",
        )

    if _CONTENT_GENERATION_RE.search(value):
        return RouteDecision(
            task_family="content_generation",
            task_type="content_generation",
            confidence=0.7,
            requires_llm=True,
            next_action="answer_with_llm",
            route="fast",
            matched_capability="content_generation",
        )

    return _unknown("no_capability_match")


def task_family_for_text(text: str) -> TaskFamily:
    """Return just the task family for compact callers."""
    return decide_route(text).task_family


def _unknown(reason: str) -> RouteDecision:
    return RouteDecision(
        task_family="unknown_or_ambiguous",
        task_type="unknown",
        confidence=0.2,
        next_action="clarify",
        user_visible_prompt="我还不确定你想让我做什么，可以换个说法吗？",
        route="local_clarify",
        matched_capability="unknown_or_ambiguous",
        metadata={"reason": reason},
    )


def _is_literary_knowledge(text: str) -> bool:
    return bool(_LITERARY_KNOWLEDGE_RE.search(text) and _LITERARY_QUERY_RE.search(text))


def _volume_route(text: str) -> RouteDecision:
    is_assistant = bool(_ASSISTANT_VOLUME_RE.search(text))
    is_media = bool(_MEDIA_VOLUME_RE.search(text))
    if is_assistant and not is_media:
        return RouteDecision(
            task_family="volume_control",
            task_type="volume_control",
            confidence=0.78,
            next_action="clarify",
            user_visible_prompt=(
                "你是要调我说话的音量，还是调整某个播放器的音量？"
            ),
            route="local_clarify",
            matched_capability="self_or_media_volume_control",
            metadata={"clarification_reason": "assistant_or_media_volume"},
        )
    if is_media and not is_assistant:
        return RouteDecision(
            task_family="volume_control",
            task_type="volume_control",
            confidence=0.8,
            allowed_tools=("HassCallService",),
            next_action="answer_with_llm",
            route="fast",
            matched_capability="media_volume_control",
        )
    return RouteDecision(
        task_family="volume_control",
        task_type="volume_control",
        confidence=0.62,
        next_action="clarify",
        user_visible_prompt="你是要调我说话的音量，还是调整某个播放器的音量？",
        route="local_clarify",
        matched_capability="self_or_media_volume_control",
        metadata={"clarification_reason": "ambiguous_volume_target"},
    )


def _is_location_dependent(text: str, normalized: str) -> bool:
    has_location_word = any(word in text for word in _LOCATION_WORDS)
    has_place = any(word.lower() in normalized for word in _PLACE_WORDS)
    has_query = any(word in text for word in _PLACE_QUERY_WORDS)
    return has_place and (has_location_word or has_query)


def _has_explicit_location(text: str) -> bool:
    if any(hint in text for hint in _EXPLICIT_LOCATION_HINTS):
        return True
    return bool(re.search(r"在[^，。！？?]{2,12}附近", text)) and "我" not in text


def _normalize(text: str) -> str:
    return _NORMALIZE_RE.sub("", str(text or "")).lower()
