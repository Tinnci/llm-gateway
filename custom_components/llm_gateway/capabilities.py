"""Capability-based semantic routing for assistant turns."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from .capability_executor import local_action_candidate
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
    "indoor_environment_query",
    "outdoor_current_weather_query",
    "weather_forecast_query",
    "home_temperature_summary",
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
EnvironmentScope = Literal[
    "indoor_environment",
    "outdoor_weather",
    "home_summary",
    "",
]
TimeHorizon = Literal["now", "today", "tomorrow", "future", ""]
FrameDomain = Literal[
    "home",
    "environment",
    "weather",
    "knowledge",
    "location",
    "control",
    "conversation",
    "unknown",
]
DataRequirement = Literal[
    "static_context",
    "live_context",
    "weather_forecast",
    "external_search",
    "location",
    "none",
    "unknown",
]

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
_SENTENCE_SPLIT_RE = re.compile(r"[？?。!！；;]+")
_FORECAST_TOMORROW_RE = re.compile(r"(明天|明日)")
_FORECAST_FUTURE_RE = re.compile(r"(后天|大后天|周末|下周|未来|下午|晚上|今晚)")
_LOCATION_HINT_RE = re.compile(
    r"(静安|上海|浦东|黄浦|徐汇|长宁|人民广场|南京西路|陆家嘴)"
)
INVENTORY_TASK_TYPES = {
    "device_inventory_query",
    "area_inventory_query",
    "domain_inventory_query",
    "capability_query",
    "exposed_context_query",
    "static_context_query",
}


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
    scope: EnvironmentScope = ""
    time_horizon: TimeHorizon = ""
    forecast_required: bool = False
    location_hint: str = ""
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
            "scope": self.scope,
            "time_horizon": self.time_horizon,
            "forecast_required": self.forecast_required,
            "location_hint": self.location_hint,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class EnvironmentQuerySpec:
    """Structured weather / indoor-environment query contract."""

    scope: EnvironmentScope = ""
    time_horizon: TimeHorizon = "now"
    forecast_required: bool = False
    location_hint: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "scope": self.scope,
            "time_horizon": self.time_horizon,
            "forecast_required": self.forecast_required,
            "location_hint": self.location_hint,
        }


@dataclass(frozen=True, slots=True)
class SemanticFrame:
    """One typed semantic frame in a capability-first plan."""

    index: int
    text: str
    domain: FrameDomain
    operation: str
    scope: EnvironmentScope = ""
    area: str = ""
    metric: str = ""
    time_horizon: TimeHorizon = ""
    data_requirement: DataRequirement = "unknown"
    forecast_required: bool = False
    risk: RiskLevel = "low"
    capability: str = ""

    def as_dict(self) -> dict[str, object]:
        """Return trace-safe typed frame metadata."""
        return {
            "index": self.index,
            "text": self.text,
            "domain": self.domain,
            "operation": self.operation,
            "scope": self.scope,
            "area": self.area,
            "metric": self.metric,
            "time_horizon": self.time_horizon,
            "data_requirement": self.data_requirement,
            "forecast_required": self.forecast_required,
            "risk": self.risk,
            "capability": self.capability,
        }


@dataclass(frozen=True, slots=True)
class TypedSemanticPlan:
    """Typed semantic plan for one user utterance."""

    original_text: str
    frames: tuple[SemanticFrame, ...]

    @property
    def is_composite(self) -> bool:
        return len(self.frames) > 1

    def as_dict(self) -> dict[str, object]:
        """Return trace-safe semantic plan metadata."""
        return {
            "original_text": self.original_text,
            "is_composite": self.is_composite,
            "frames": [frame.as_dict() for frame in self.frames],
        }


@dataclass(frozen=True, slots=True)
class MultiIntentSubtask:
    """One independently routed user subtask."""

    index: int
    text: str
    route_decision: RouteDecision
    semantic_frame: SemanticFrame

    def as_dict(self) -> dict[str, object]:
        return {
            "index": self.index,
            "text": self.text,
            "route_decision": self.route_decision.as_dict(),
            "semantic_frame": self.semantic_frame.as_dict(),
        }


@dataclass(frozen=True, slots=True)
class MultiIntentPlan:
    """Planner output for an utterance that may contain several intents."""

    original_text: str
    subtasks: tuple[MultiIntentSubtask, ...]

    @property
    def is_multi_intent(self) -> bool:
        return len(self.subtasks) > 1

    def as_dict(self) -> dict[str, object]:
        typed_plan = TypedSemanticPlan(
            self.original_text,
            tuple(subtask.semantic_frame for subtask in self.subtasks),
        )
        return {
            "original_text": self.original_text,
            "is_multi_intent": self.is_multi_intent,
            "typed_semantic_plan": typed_plan.as_dict(),
            "subtasks": [subtask.as_dict() for subtask in self.subtasks],
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

    if _looks_like_environment_state_question(value):
        return _environment_route(value, confidence=0.82)

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
        return _environment_route(value, confidence=0.86)

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
        return _environment_route(value, confidence=0.74)

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
        candidate = local_action_candidate(value)
        if candidate is not None and candidate.family == "home_control":
            return RouteDecision(
                task_family="home_control",
                task_type="home_control",
                confidence=candidate.confidence,
                allowed_tools=("local_service_call",),
                forbidden_tools=("search_web",),
                next_action="execute_local",
                route="local_action",
                matched_capability="local_home_control",
                metadata={
                    "action": candidate.action,
                    "domain": candidate.domain,
                    "area": candidate.area,
                },
            )
        return RouteDecision(
            task_family="home_control",
            task_type="home_control",
            confidence=0.72,
            requires_llm=True,
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


def _environment_route(text: str, *, confidence: float) -> RouteDecision:
    """Return the split environment/weather capability route for one query."""
    environment = classify_environment_query(text)
    task_type: TaskType = "home_state"
    matched_capability = "indoor_environment_query"
    if environment.forecast_required:
        missing = () if environment.location_hint else ("location_hint",)
        return RouteDecision(
            task_family="external_current_info",
            task_type="weather_forecast_query",
            confidence=confidence,
            requires_external_info=True,
            requires_llm=not missing,
            allowed_tools=("search_web",),
            next_action="search" if not missing else "clarify",
            user_visible_prompt="" if not missing else "你想查哪个地方明天的天气？",
            route="mid" if not missing else "local_clarify",
            matched_capability="weather_forecast_query",
            scope=environment.scope or "outdoor_weather",
            time_horizon=environment.time_horizon,
            forecast_required=True,
            location_hint=environment.location_hint,
            missing_requirements=missing,
            metadata=environment.as_dict(),
        )
    if environment.scope == "outdoor_weather":
        task_type = "outdoor_current_weather_query"
        matched_capability = "outdoor_current_weather_query"
    elif (
        environment.scope == "home_summary" and _metric_from_text(text) == "temperature"
    ):
        task_type = "home_temperature_summary"
        matched_capability = "home_temperature_summary"
    elif environment.scope == "indoor_environment":
        task_type = "indoor_environment_query"
        matched_capability = "indoor_environment_query"
    return RouteDecision(
        task_family="home_state",
        task_type=task_type,
        confidence=confidence,
        requires_live_home_context=True,
        allowed_tools=("GetLiveContext",),
        next_action="call_tool_then_local_render",
        route="local_live_context",
        matched_capability=matched_capability,
        scope=environment.scope,
        time_horizon=environment.time_horizon,
        forecast_required=environment.forecast_required,
        location_hint=environment.location_hint,
        metadata=environment.as_dict() if environment.scope else {},
    )


def plan_multi_intent(text: str) -> MultiIntentPlan:
    """Split supported multi-question utterances into independently routed subtasks."""
    original = str(text or "").strip()
    if not original:
        return MultiIntentPlan(original, ())

    expanded = _expand_indoor_outdoor_question(original)
    if not expanded:
        expanded = _expand_metric_pair_question(original)
    parts = expanded or _split_sentence_subtasks(original)
    parts = _inherit_previous_area(parts)
    normalized_parts = [_normalize_subtask_for_route(part) for part in parts]
    subtasks = tuple(
        _subtask_for_text(index, part)
        for index, part in enumerate(normalized_parts)
        if part.strip()
    )
    if len(subtasks) <= 1:
        return MultiIntentPlan(original, subtasks)
    supported = tuple(
        subtask
        for subtask in subtasks
        if subtask.route_decision.task_family
        in {"home_inventory", "home_capability", "home_state"}
    )
    return MultiIntentPlan(original, supported if len(supported) > 1 else subtasks)


def plan_typed_semantic(text: str) -> TypedSemanticPlan:
    """Return the typed semantic plan for one user utterance."""
    plan = plan_multi_intent(text)
    return TypedSemanticPlan(
        plan.original_text,
        tuple(subtask.semantic_frame for subtask in plan.subtasks),
    )


def _subtask_for_text(index: int, text: str) -> MultiIntentSubtask:
    decision = decide_route(text)
    return MultiIntentSubtask(
        index=index,
        text=text,
        route_decision=decision,
        semantic_frame=_semantic_frame(index, text, decision),
    )


def classify_environment_query(text: str) -> EnvironmentQuerySpec:
    """Return weather-vs-indoor scope and forecast requirements."""
    value = str(text or "")
    normalized = _normalize(value)
    time_horizon: TimeHorizon = "now"
    if _FORECAST_TOMORROW_RE.search(value):
        time_horizon = "tomorrow"
    elif "今天" in value or "今日" in value:
        time_horizon = "today"
    elif _FORECAST_FUTURE_RE.search(value):
        time_horizon = "future"
    forecast_required = time_horizon in {"tomorrow", "future"}
    location_hint = _location_hint(value)

    indoor_areas = ("卧室", "客厅", "餐厅", "厨房", "书房", "卫生间", "阳台")
    indoor_metrics = ("温度", "湿度", "空气质量", "pm25", "pm2")
    any_indoor_metrics = ("温度", "湿度", "空气质量", "pm25", "pm2", "co2", "tvoc")
    has_indoor_area = any(area in value for area in indoor_areas)
    if "家里" in value or "全屋" in value:
        scope: EnvironmentScope = "home_summary"
    elif "室内" in value or (
        has_indoor_area and any(term in normalized for term in indoor_metrics)
    ):
        scope = "indoor_environment"
    elif (
        "外面" in value
        or "室外" in value
        or location_hint
        or "天气" in value
        or "下雨" in value
        or "雨" in value
    ):
        scope = "outdoor_weather"
    elif any(term in normalized for term in any_indoor_metrics):
        scope = "indoor_environment"
    else:
        scope = ""
    if forecast_required and not scope:
        scope = "outdoor_weather"
    return EnvironmentQuerySpec(
        scope=scope,
        time_horizon=time_horizon,
        forecast_required=forecast_required,
        location_hint=location_hint,
    )


def _semantic_frame(
    index: int,
    text: str,
    decision: RouteDecision,
) -> SemanticFrame:
    """Build a typed semantic frame from a route decision."""
    capability = decision.matched_capability or decision.task_type
    metric = _metric_from_text(text)
    operation = decision.task_type
    domain: FrameDomain = "unknown"
    data_requirement: DataRequirement = "unknown"
    if decision.task_type in INVENTORY_TASK_TYPES:
        domain = "home"
        operation = "inventory_summary"
        data_requirement = "static_context"
    elif decision.task_type == "home_temperature_summary":
        domain = "environment"
        operation = "home_temperature_summary"
        data_requirement = "live_context"
        metric = metric or "temperature"
    elif decision.task_type == "indoor_environment_query":
        domain = "environment"
        operation = "read_metric"
        data_requirement = "live_context"
    elif decision.task_type == "outdoor_current_weather_query":
        domain = "weather"
        operation = "current_weather"
        data_requirement = "live_context"
    elif decision.task_type == "weather_forecast_query":
        domain = "weather"
        operation = "forecast"
        data_requirement = "weather_forecast"
        metric = metric or "weather"
    elif decision.task_family == "stable_knowledge":
        domain = "knowledge"
        operation = "answer_fact"
        data_requirement = "none"
    elif decision.task_family == "volume_control":
        domain = "control"
        operation = "set_volume"
        data_requirement = "none"
    elif decision.task_family == "location_dependent_query":
        domain = "location"
        operation = "nearby_place_search"
        data_requirement = "location"
    elif decision.task_family == "conversation_control":
        domain = "conversation"
        operation = "control_turn"
        data_requirement = "none"
    return SemanticFrame(
        index=index,
        text=text,
        domain=domain,
        operation=operation,
        scope=decision.scope,
        area=_area_hint(text),
        metric=metric,
        time_horizon=decision.time_horizon,
        data_requirement=data_requirement,
        forecast_required=decision.forecast_required,
        risk=decision.risk,
        capability=capability,
    )


def _unknown(reason: str) -> RouteDecision:
    return RouteDecision(
        task_family="unknown_or_ambiguous",
        task_type="unknown",
        confidence=0.35,
        requires_llm=True,
        next_action="answer_with_llm",
        route="fast",
        matched_capability="unknown_or_ambiguous",
        metadata={"reason": reason, "planner": "llm_route_generalization"},
    )


def _split_sentence_subtasks(text: str) -> list[str]:
    parts = [
        part.strip(" ，,")
        for part in _SENTENCE_SPLIT_RE.split(text)
        if part.strip(" ，,")
    ]
    return parts or [text]


def _normalize_subtask_for_route(text: str) -> str:
    value = str(text or "")
    if any(term in value for term in ("设备", "实体", "东西")) and any(
        term in value for term in ("哪些", "什么", "有啥", "有什么")
    ):
        value = value.replace("现在", "")
    return value.strip()


def _expand_metric_pair_question(text: str) -> list[str]:
    if "温度" not in text or "湿度" not in text:
        return []
    if not any(marker in text for marker in ("分别", "和", "以及", "还有")):
        return []
    area = _area_hint(text)
    prefix = area or ""
    return [f"{prefix}温度是多少", f"{prefix}湿度是多少"]


def _expand_indoor_outdoor_question(text: str) -> list[str]:
    value = str(text or "")
    if "室内" not in value:
        return []
    if not any(term in value for term in ("室外", "外面", "外头")):
        return []
    if not any(marker in value for marker in ("分别", "和", "以及", "还有")):
        return []
    metric = "温度"
    if "湿度" in value:
        metric = "湿度"
    elif "空气质量" in value or "pm2" in _normalize(value):
        metric = "空气质量"
    elif "天气" in value:
        metric = "天气"
    return [f"室内{metric}是多少", f"室外{metric}是多少"]


def _inherit_previous_area(parts: list[str]) -> list[str]:
    result: list[str] = []
    previous_area = ""
    for part in parts:
        area = _area_hint(part)
        routed_part = part
        if area:
            previous_area = area
        elif previous_area and _looks_like_area_state_followup(part):
            routed_part = f"{previous_area}{part}"
        result.append(routed_part)
    return result


def _looks_like_area_state_followup(text: str) -> bool:
    return any(
        term in text
        for term in ("温度", "湿度", "空气质量", "多少", "几度", "冷不冷", "热不热")
    )


def _looks_like_environment_state_question(text: str) -> bool:
    normalized = _normalize(text)
    has_metric = any(term in normalized for term in ("温度", "湿度", "co2", "tvoc"))
    has_value_question = any(
        term in normalized
        for term in ("多少", "几度", "现在", "当前", "什么样", "怎么样", "如何")
    )
    return has_metric and has_value_question


def _area_hint(text: str) -> str:
    for area in ("卫生间", "卧室", "客厅", "餐厅", "厨房", "书房", "阳台"):
        if area in text:
            return area
    return ""


def _metric_from_text(text: str) -> str:
    normalized = _normalize(text)
    metric_patterns = (
        ("air_quality", ("空气质量",)),
        ("pm25", ("pm25", "pm2")),
        ("co2", ("co2", "二氧化碳")),
        ("tvoc", ("tvoc", "甲醛")),
        ("temperature", ("温度", "气温", "几度")),
        ("humidity", ("湿度",)),
        ("weather", ("天气",)),
    )
    for metric, patterns in metric_patterns:
        if any(pattern in normalized for pattern in patterns):
            return metric
    return ""


def _location_hint(text: str) -> str:
    match = _LOCATION_HINT_RE.search(text)
    return match.group(1) if match else ""


def _is_literary_knowledge(text: str) -> bool:
    return bool(_LITERARY_KNOWLEDGE_RE.search(text) and _LITERARY_QUERY_RE.search(text))


def _volume_route(text: str) -> RouteDecision:
    candidate = local_action_candidate(text)
    if candidate is not None and candidate.family == "volume_control":
        return RouteDecision(
            task_family="volume_control",
            task_type="volume_control",
            confidence=candidate.confidence,
            allowed_tools=("local_service_call",),
            forbidden_tools=("search_web",),
            next_action="execute_local",
            route="local_action",
            matched_capability=(
                "assistant_volume_control"
                if candidate.action == "assistant_volume_set"
                else "media_volume_control"
            ),
            metadata={
                "action": candidate.action,
                "domain": candidate.domain,
                "area": candidate.area,
            },
        )
    is_assistant = bool(_ASSISTANT_VOLUME_RE.search(text))
    is_media = bool(_MEDIA_VOLUME_RE.search(text))
    if is_assistant and not is_media:
        return RouteDecision(
            task_family="volume_control",
            task_type="volume_control",
            confidence=0.78,
            next_action="clarify",
            user_visible_prompt=("你是要调我说话的音量，还是调整某个播放器的音量？"),
            route="local_clarify",
            matched_capability="self_or_media_volume_control",
            metadata={"clarification_reason": "assistant_or_media_volume"},
        )
    if is_media and not is_assistant:
        return RouteDecision(
            task_family="volume_control",
            task_type="volume_control",
            confidence=0.8,
            requires_llm=True,
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
