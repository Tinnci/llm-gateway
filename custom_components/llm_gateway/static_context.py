"""Deterministic inventory answers from Home Assistant static context."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Iterable

    from homeassistant.components import conversation

STATIC_CONTEXT_MARKER = "Static Context:"
MAX_DEVICE_EXAMPLES = 8
INVENTORY_SCORE_THRESHOLD = 4

InventoryTaskType = Literal[
    "device_inventory_query",
    "area_inventory_query",
    "domain_inventory_query",
    "capability_query",
    "exposed_context_query",
]
EntitySource = Literal["static_context", "live_context", "ha_registry"]

_DEVICE_START_RE = re.compile(r"^\s*-\s*names:\s*(?P<names>.+?)\s*$")
_FIELD_RE = re.compile(r"^\s*(?P<key>domain|areas):\s*(?P<value>.+?)\s*$")
_TEXT_NORMALIZE_RE = re.compile(r"[\s《》「」『』“”\"'`·.。,:：，、_\-—!?！？]+")

CONTROLLABLE_DOMAINS = {
    "automation",
    "climate",
    "cover",
    "fan",
    "humidifier",
    "light",
    "lock",
    "media_player",
    "scene",
    "script",
    "switch",
    "vacuum",
}

DOMAIN_LABELS = {
    "automation": "自动化",
    "climate": "空调/温控",
    "cover": "窗帘/门窗",
    "fan": "风扇",
    "humidifier": "加湿器",
    "light": "灯",
    "lock": "门锁",
    "media_player": "媒体播放器",
    "scene": "场景",
    "script": "脚本",
    "sensor": "传感器",
    "switch": "开关",
    "todo": "清单",
    "vacuum": "扫地机",
    "weather": "天气",
}

DOMAIN_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("light", ("灯", "灯光", "照明")),
    ("climate", ("空调", "温控", "暖气", "制冷", "制热")),
    ("fan", ("风扇", "循环扇")),
    ("sensor", ("传感器", "温度", "湿度", "温湿度", "空气质量", "pm25", "co2", "tvoc")),
    ("switch", ("开关", "模式", "童锁", "物理控制锁")),
    ("media_player", ("媒体", "播放器", "音箱", "homepod", "扬声器")),
    ("lock", ("门锁", "锁")),
    ("weather", ("天气",)),
    ("todo", ("清单", "购物")),
)

QUERY_TERMS = ("哪些", "什么", "啥", "多少", "几个", "列表", "清单", "列一下", "列出来")
CAPABILITY_TERMS = (
    "看到",
    "看见",
    "查看",
    "接入",
    "暴露",
    "控制",
    "管理",
    "支持",
    "能用",
)
CONTROL_TERMS = ("控制", "操作", "开关", "打开", "关闭", "调节", "设置")
EXISTENCE_TERMS = ("有", "都有", "有啥", "有什么")
SUBJECT_TERMS = ("设备", "实体", "东西", "装置", "能力", "功能", "项目")
LOCATION_HINTS = ("家里", "全屋", "房间", "区域")
COMMON_AREAS = ("卧室", "客厅", "餐厅", "厨房", "书房", "卫生间", "阳台")
STATE_VALUE_PHRASES = (
    "是多少",
    "多少度",
    "几度",
    "当前",
    "现在",
    "怎么样",
    "如何",
    "冷不冷",
    "热不热",
)
SCALAR_STATE_TERMS = ("温度", "湿度", "pm25", "co2", "tvoc", "空气质量", "天气")
INVENTORY_ENUMERATION_TERMS = (
    "设备",
    "实体",
    "传感器",
    "列表",
    "清单",
    "哪些",
    "有什么",
    "有啥",
)


@dataclass(frozen=True, slots=True)
class ExposedEntity:
    """One entity exposed to the assistant."""

    name: str
    domain: str
    areas: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    entity_id: str | None = None
    can_control: bool = False
    can_read_state: bool = True
    source: EntitySource = "static_context"


StaticDevice = ExposedEntity


@dataclass(frozen=True, slots=True)
class InventoryQuerySpec:
    """Structured inventory query derived from user text."""

    task_type: InventoryTaskType
    area: str = ""
    domain: str = ""
    capability: Literal["control", "read", "any"] = "any"


@dataclass(frozen=True, slots=True)
class _InventorySignals:
    """Semantic slots used to route static-context inventory questions."""

    area: str
    domain: str
    has_query: bool
    has_capability: bool
    has_control: bool
    has_existence: bool
    has_subject: bool
    has_location: bool
    has_state_value_query: bool
    mentions_assistant: bool


@dataclass(frozen=True, slots=True)
class InventoryRenderResult:
    """Rendered spoken summary plus debug metadata."""

    speech: str
    spec: InventoryQuerySpec
    entity_count: int
    areas: tuple[str, ...]
    domains: tuple[str, ...]
    entities: tuple[ExposedEntity, ...]

    def trace_attrs(self) -> dict[str, object]:
        """Return Voice Harness timeline attrs for the local renderer."""
        return {
            "task_type": self.spec.task_type,
            "source": "static_context_index",
            "area": self.spec.area,
            "domain": self.spec.domain,
            "capability": self.spec.capability,
            "entity_count": self.entity_count,
            "area_count": len(self.areas),
            "domain_count": len(self.domains),
            "areas": list(self.areas),
            "domains": list(self.domains),
            "entities": [
                {
                    "name": entity.name,
                    "domain": entity.domain,
                    "areas": list(entity.areas),
                    "can_control": entity.can_control,
                    "can_read_state": entity.can_read_state,
                    "source": entity.source,
                }
                for entity in self.entities
            ],
            "llm_used": False,
            "tools_used": [],
        }


class ExposedEntityIndex:
    """Structured index over assistant-exposed static entities."""

    def __init__(self, entities: Iterable[ExposedEntity]) -> None:
        self.entities = tuple(_dedup_entities(list(entities)))
        self.by_area = _group_by_area(self.entities)
        self.by_domain = _group_by_domain(self.entities)

    @property
    def entity_count(self) -> int:
        """Return exposed entity count."""
        return len(self.entities)

    @property
    def areas(self) -> tuple[str, ...]:
        """Return known areas."""
        return tuple(sorted(self.by_area))

    @property
    def domains(self) -> tuple[str, ...]:
        """Return known domains."""
        return tuple(sorted(self.by_domain))

    @classmethod
    def from_content(cls, content: list[conversation.Content]) -> ExposedEntityIndex:
        """Build an index from HA chat-log static context."""
        return cls(parse_static_devices_from_content(content))

    def area_from_text(self, text: str) -> str:
        """Resolve an area mention from indexed areas and common area words."""
        normalized = _normalize_query_text(text)
        for area in sorted((*self.areas, *COMMON_AREAS), key=len, reverse=True):
            if area and area in normalized:
                return area
        return ""

    def domain_from_text(self, text: str) -> str:
        """Resolve a domain mention from domain labels and keyword aliases."""
        normalized = _normalize_query_text(text)
        for domain in self.domains:
            label = DOMAIN_LABELS.get(domain, domain)
            if label and label in normalized:
                return domain
        return _domain_from_keywords(normalized)

    def query(self, spec: InventoryQuerySpec) -> tuple[ExposedEntity, ...]:
        """Return entities matching the query spec."""
        entities = self.entities
        if spec.area:
            entities = tuple(entity for entity in entities if spec.area in entity.areas)
        if spec.domain:
            entities = tuple(
                entity
                for entity in entities
                if _entity_matches_domain(entity, spec.domain)
            )
        if spec.capability == "control":
            entities = tuple(entity for entity in entities if entity.can_control)
        elif spec.capability == "read":
            entities = tuple(entity for entity in entities if entity.can_read_state)
        return entities

    def render(self, text: str) -> InventoryRenderResult | None:
        """Render a deterministic spoken inventory summary."""
        spec = classify_inventory_query(text, self)
        if spec is None:
            return None
        if not self.entities:
            return InventoryRenderResult(
                speech="我暂时看不到已暴露给助手的设备列表。",
                spec=spec,
                entity_count=0,
                areas=(),
                domains=(),
                entities=(),
            )

        entities = self.query(spec)
        if not entities:
            speech = f"我能看到已暴露给助手的设备，但没有找到{_scope_label(spec)}。"
        elif spec.task_type == "capability_query":
            speech = _render_capability_summary(entities)
        elif spec.task_type == "domain_inventory_query":
            speech = _render_domain_summary(spec, entities)
        elif spec.task_type == "area_inventory_query":
            speech = _render_area_summary(spec, entities)
        elif spec.task_type == "exposed_context_query":
            speech = _render_exposed_context_summary(spec, entities)
        else:
            speech = _render_device_summary(entities)

        return InventoryRenderResult(
            speech=speech,
            spec=spec,
            entity_count=len(entities),
            areas=tuple(sorted({area for entity in entities for area in entity.areas})),
            domains=tuple(sorted({entity.domain for entity in entities})),
            entities=entities,
        )


def classify_inventory_query(
    text: str,
    index: ExposedEntityIndex | None = None,
) -> InventoryQuerySpec | None:
    """Classify inventory/static-context queries using semantic slots."""
    normalized = _normalize_query_text(text)
    if not normalized:
        return None

    signals = _inventory_signals(normalized, index)
    if not _is_inventory_intent(signals):
        return None
    return _spec_from_inventory_signals(signals)


def _inventory_signals(
    normalized: str,
    index: ExposedEntityIndex | None,
) -> _InventorySignals:
    """Extract route signals without deciding facts or permissions."""
    area = index.area_from_text(normalized) if index else _area_from_common(normalized)
    domain = (
        index.domain_from_text(normalized)
        if index
        else _domain_from_keywords(normalized)
    )
    has_query = _contains_any(normalized, QUERY_TERMS)
    has_capability = _contains_any(normalized, CAPABILITY_TERMS)
    has_control = _contains_any(normalized, CONTROL_TERMS)
    has_existence = _contains_any(normalized, EXISTENCE_TERMS)
    has_subject = bool(domain) or _contains_any(normalized, SUBJECT_TERMS)
    has_location = bool(area) or _contains_any(normalized, LOCATION_HINTS)
    has_state_value_query = _looks_like_scalar_state_query(normalized, domain)
    mentions_assistant = "你" in normalized or "助手" in normalized
    return _InventorySignals(
        area=area,
        domain=domain,
        has_query=has_query,
        has_capability=has_capability,
        has_control=has_control,
        has_existence=has_existence,
        has_subject=has_subject,
        has_location=has_location,
        has_state_value_query=has_state_value_query,
        mentions_assistant=mentions_assistant,
    )


def _spec_from_inventory_signals(signals: _InventorySignals) -> InventoryQuerySpec:
    """Convert inventory signals into the deterministic local route."""
    capability: Literal["control", "read", "any"] = "any"
    if signals.has_control:
        capability = "control"
    if signals.has_control and not signals.area and not signals.domain:
        return InventoryQuerySpec("capability_query", capability="control")
    if signals.domain:
        return InventoryQuerySpec(
            "domain_inventory_query",
            area=signals.area,
            domain=signals.domain,
            capability=capability,
        )
    if signals.area:
        return InventoryQuerySpec(
            "area_inventory_query",
            area=signals.area,
            capability=capability,
        )
    if signals.has_subject and signals.has_query:
        return InventoryQuerySpec("device_inventory_query", capability=capability)
    if signals.has_capability and signals.mentions_assistant:
        return InventoryQuerySpec("exposed_context_query", capability=capability)
    return InventoryQuerySpec("device_inventory_query", capability=capability)


def is_device_inventory_query(text: str) -> bool:
    """Return whether text asks about exposed inventory/capabilities."""
    return classify_inventory_query(text) is not None


def render_device_inventory_answer(
    text: str,
    content: list[conversation.Content],
) -> str | None:
    """Render a short deterministic inventory answer from static context."""
    result = render_device_inventory(text, content)
    return result.speech if result else None


def render_device_inventory(
    text: str,
    content: list[conversation.Content],
) -> InventoryRenderResult | None:
    """Render inventory answer and debug metadata."""
    return ExposedEntityIndex.from_content(content).render(text)


def parse_static_devices_from_content(
    content: list[conversation.Content],
) -> list[ExposedEntity]:
    """Parse HA's plain-text static context from chat-log content."""
    entities: list[ExposedEntity] = []
    for item in content:
        if item.role != "system" or STATIC_CONTEXT_MARKER not in item.content:
            continue
        entities.extend(parse_static_devices(item.content))
    return _dedup_entities(entities)


def parse_static_devices(text: str) -> list[ExposedEntity]:
    """Parse entity entries from a Home Assistant static context block."""
    entities: list[ExposedEntity] = []
    current_name = ""
    current_domain = ""
    current_areas: tuple[str, ...] = ()

    def flush() -> None:
        if current_name and current_domain:
            entities.append(
                ExposedEntity(
                    name=_compact_spaces(current_name),
                    domain=current_domain.strip(),
                    areas=current_areas,
                    aliases=_aliases_for_name(current_name),
                    can_control=current_domain.strip() in CONTROLLABLE_DOMAINS,
                    can_read_state=True,
                    source="static_context",
                )
            )

    for line in str(text or "").splitlines():
        if match := _DEVICE_START_RE.match(line):
            flush()
            current_name = match.group("names")
            current_domain = ""
            current_areas = ()
            continue
        if not current_name:
            continue
        if match := _FIELD_RE.match(line):
            key = match.group("key")
            value = _compact_spaces(match.group("value"))
            if key == "domain":
                current_domain = value
            elif key == "areas":
                current_areas = tuple(_split_areas(value))
    flush()
    return entities


def _inventory_score(signals: _InventorySignals) -> int:
    score = 0
    score += 2 if signals.has_query else 0
    score += 2 if signals.has_capability else 0
    score += 2 if signals.has_subject else 0
    score += 1 if signals.has_location else 0
    score += 1 if signals.has_existence else 0
    score += 1 if signals.mentions_assistant else 0
    return score


def _is_inventory_intent(signals: _InventorySignals) -> bool:
    score = _inventory_score(signals)
    if signals.has_state_value_query and not (
        signals.has_capability and signals.mentions_assistant
    ):
        return False
    if signals.has_capability and (
        signals.has_query or signals.has_subject or signals.mentions_assistant
    ):
        return True
    if (
        signals.has_subject
        and signals.has_query
        and (
            signals.has_existence or signals.has_location or signals.mentions_assistant
        )
    ):
        return True
    return (
        signals.has_location
        and signals.has_query
        and signals.has_existence
        and (score >= INVENTORY_SCORE_THRESHOLD)
    )


def _looks_like_scalar_state_query(normalized: str, domain: str) -> bool:
    """Return true for value questions like temperature, humidity, AQI, weather."""
    if _contains_any(normalized, STATE_VALUE_PHRASES):
        return True
    if domain not in {"sensor", "weather", "climate"}:
        return False
    if "多少" not in normalized or _contains_any(
        normalized, INVENTORY_ENUMERATION_TERMS
    ):
        return False
    return _contains_any(normalized, SCALAR_STATE_TERMS)


def _render_device_summary(entities: tuple[ExposedEntity, ...]) -> str:
    area_parts = _area_domain_parts(entities)
    examples = _entity_names(entities)[:5]
    body = "，".join(area_parts)
    if examples:
        body += "，例如" + "、".join(examples)
    return (
        f"我能看到已暴露给助手的设备，主要有{body}。"
        "完整列表可以在 Voice Harness 面板里展开。"
    )


def _render_area_summary(
    spec: InventoryQuerySpec,
    entities: tuple[ExposedEntity, ...],
) -> str:
    groups = "、".join(_domain_groups(entities))
    examples = "、".join(_entity_names(entities)[:MAX_DEVICE_EXAMPLES])
    return f"{spec.area}里我能看到已暴露给助手的{groups}，包括{examples}。"


def _render_domain_summary(
    spec: InventoryQuerySpec,
    entities: tuple[ExposedEntity, ...],
) -> str:
    label = DOMAIN_LABELS.get(spec.domain, spec.domain)
    examples = "、".join(_entity_names(entities)[:MAX_DEVICE_EXAMPLES])
    return f"我能看到已暴露给助手的{label}包括{examples}。"


def _render_capability_summary(entities: tuple[ExposedEntity, ...]) -> str:
    controllable = tuple(entity for entity in entities if entity.can_control)
    groups = "、".join(_domain_groups(controllable or entities))
    examples = "、".join(_entity_names(controllable or entities)[:5])
    return f"我能控制已暴露给助手的{groups}，例如{examples}。高风险设备仍需要先确认。"


def _render_exposed_context_summary(
    spec: InventoryQuerySpec,
    entities: tuple[ExposedEntity, ...],
) -> str:
    if spec.domain == "weather":
        examples = "、".join(_entity_names(entities)[:MAX_DEVICE_EXAMPLES])
        return f"可以。我能看到已暴露给助手的天气或环境相关实体，包括{examples}。"
    return _render_device_summary(entities)


def _area_domain_parts(entities: tuple[ExposedEntity, ...]) -> list[str]:
    by_area = _group_by_area(entities)
    parts: list[str] = []
    for area, area_entities in sorted(by_area.items()):
        label = area if area != "__none__" else "未分区"
        parts.append(f"{label}的{'、'.join(_domain_groups(tuple(area_entities)))}")
    return parts[:4]


def _domain_groups(entities: tuple[ExposedEntity, ...]) -> list[str]:
    counts: dict[str, int] = {}
    for entity in entities:
        counts[entity.domain] = counts.get(entity.domain, 0) + 1
    return [
        f"{DOMAIN_LABELS.get(domain, domain)}{count}个"
        for domain, count in sorted(
            counts.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ][:5]


def _entity_names(entities: tuple[ExposedEntity, ...]) -> list[str]:
    return _dedup_names(entity.name for entity in entities)


def _scope_label(spec: InventoryQuerySpec) -> str:
    label = ""
    if spec.area:
        label += f"{spec.area}的"
    if spec.domain:
        label += DOMAIN_LABELS.get(spec.domain, spec.domain)
    if spec.capability == "control" and not label:
        label = "可控制设备"
    return label or "匹配设备"


def _entity_matches_domain(entity: ExposedEntity, domain: str) -> bool:
    if entity.domain == domain:
        return True
    normalized_name = _normalize_query_text(entity.name)
    if domain == "weather":
        return "天气" in normalized_name or entity.domain == "weather"
    if domain == "sensor":
        return entity.domain == "sensor"
    return False


def _area_from_common(text: str) -> str:
    for area in sorted(COMMON_AREAS, key=len, reverse=True):
        if area in text:
            return area
    return ""


def _domain_from_keywords(text: str) -> str:
    for domain, keywords in DOMAIN_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return domain
    return ""


def _group_by_area(
    entities: tuple[ExposedEntity, ...],
) -> dict[str, list[ExposedEntity]]:
    grouped: dict[str, list[ExposedEntity]] = {}
    for entity in entities:
        areas = entity.areas or ("__none__",)
        for area in areas:
            grouped.setdefault(area, []).append(entity)
    return grouped


def _group_by_domain(
    entities: tuple[ExposedEntity, ...],
) -> dict[str, list[ExposedEntity]]:
    grouped: dict[str, list[ExposedEntity]] = {}
    for entity in entities:
        grouped.setdefault(entity.domain, []).append(entity)
    return grouped


def _dedup_names(names: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for name in names:
        text = _compact_spaces(str(name))
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _dedup_entities(entities: list[ExposedEntity]) -> list[ExposedEntity]:
    seen: set[tuple[str, str, tuple[str, ...]]] = set()
    result: list[ExposedEntity] = []
    for entity in entities:
        key = (entity.name, entity.domain, entity.areas)
        if key in seen:
            continue
        seen.add(key)
        result.append(entity)
    return result


def _aliases_for_name(name: str) -> tuple[str, ...]:
    compact = _compact_spaces(name)
    aliases = {compact}
    for part in re.split(r"[* ]+", compact):
        if part:
            aliases.add(part)
    return tuple(sorted(aliases))


def _split_areas(value: str) -> list[str]:
    return [area.strip() for area in re.split(r"[,，/、]", value) if area.strip()]


def _compact_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _normalize_query_text(text: str) -> str:
    normalized = str(text or "").strip().lower().replace("pm2.5", "pm25")
    return _TEXT_NORMALIZE_RE.sub("", normalized)


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)
