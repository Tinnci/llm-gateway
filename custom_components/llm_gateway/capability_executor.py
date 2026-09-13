"""Local capability execution for deterministic low-risk assistant turns."""

from __future__ import annotations

import asyncio
import re
from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from homeassistant.components.homeassistant import exposed_entities
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import Context, callback
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .resolution import (
    DeviceReference,
    SemanticResolutionFrame,
    resolve_device_referent,
)
from .room_context import resolve_room_areas

if TYPE_CHECKING:
    from collections.abc import Iterable

    from homeassistant.core import Event, HomeAssistant, State

    from .capabilities import RouteDecision

LocalActionKind = Literal[
    "turn_on",
    "turn_off",
    "brightness_up",
    "brightness_down",
    "climate_set_temperature",
    "room_set_temperature",
    "volume_up",
    "volume_down",
    "volume_set",
    "volume_mute",
    "assistant_volume_set",
]
LocalActionStatus = Literal[
    "executed",
    "dry_run",
    "partial",
    "clarify",
    "unsupported",
    "not_applicable",
    "error",
]
TargetScope = Literal["single", "area", "all"]

LOW_RISK_DOMAINS = {"climate", "fan", "light", "media_player", "switch"}
CLIMATE_MIN_SETPOINT = 5
CLIMATE_MAX_SETPOINT = 35
ASSISTANT_VOLUME_ENTITIES = (
    "input_number.kukui_tts_volume_day",
    "input_number.kukui_tts_volume_night",
    "input_number.kukui_fallback_clip_volume",
)
BULK_ACTION_MAX_CONCURRENCY = 4

_NORMALIZE_RE = re.compile(r"[\s《》「」『』“”\"'·.。,:：，、_\-—!?！？]+")
_AREA_HINTS = ("客厅", "卧室", "餐厅", "厨房", "书房", "卫生间", "阳台")
_ASSISTANT_VOLUME_RE = re.compile(r"(自己|你说话|你的声音|助手|播报|回答声音|说话声音)")
_MEDIA_VOLUME_RE = re.compile(r"(音箱|播放器|homepod|喇叭|扬声器|电视|媒体|客厅|卧室)")
_HIGH_RISK_RE = re.compile(
    r"(门锁|开门|前门|后门|报警|警报|车库门|卷帘门|门禁|热水器|取暖器|烤箱|炉灶|全屋)"
)
_ACTION_VERBS = (
    r"(?:打开|开启|关闭|关掉|关上|调亮|调暗|设置|调到|调成|调至|设为|"
    r"设定为|改到|改成|开|关)"
)
_ACTION_VERB_RE = re.compile(_ACTION_VERBS)
_NEGATED_ACTION_RE = re.compile(
    rf"(?:(不要|别|不用|无需|禁止).{{0,12}}{_ACTION_VERBS}|"
    rf"{_ACTION_VERBS}.{{0,8}}(不要|别|不用))"
)
_AMBIGUOUS_ACTION_RE = re.compile(
    r"(?=.*(?:打开|开启|开))(?=.*(?:关闭|关掉|关上|关))(?=.*(?:还是|或者|或))"
)


@dataclass(frozen=True, slots=True)
class LocalActionCandidate:
    """A deterministic local action parsed from user text."""

    family: str
    action: LocalActionKind
    domain: str = ""
    area: str = ""
    target_hint: str = ""
    target_scope: TargetScope = "single"
    target_temperature: float | None = None
    volume_level: float | None = None
    mute: bool | None = None
    confidence: float = 0.0


@dataclass(frozen=True, slots=True)
class LocalCapabilityResult:
    """Executor result with separated spoken and trace-safe metadata."""

    status: LocalActionStatus
    speech: str
    candidate: LocalActionCandidate | None = None
    service_calls: tuple[dict[str, Any], ...] = ()
    matches: tuple[dict[str, Any], ...] = ()
    reason: str = ""
    panel: dict[str, Any] = field(default_factory=dict)
    action_trace: dict[str, Any] = field(default_factory=dict)

    @property
    def handled(self) -> bool:
        """Return whether the conversation should finalize locally."""
        return self.status != "not_applicable"

    def trace_attrs(self) -> dict[str, Any]:
        """Return structured trace metadata without leaking into speech."""
        candidate = self.candidate
        return {
            "status": self.status,
            "reason": self.reason,
            "llm_used": False,
            "llm_final_used": False,
            "candidate": {
                "family": candidate.family,
                "action": candidate.action,
                "domain": candidate.domain,
                "area": candidate.area,
                "target_hint": candidate.target_hint,
                "target_scope": candidate.target_scope,
                "target_temperature": candidate.target_temperature,
                "volume_level": candidate.volume_level,
                "mute": candidate.mute,
                "confidence": candidate.confidence,
            }
            if candidate
            else None,
            "service_calls": deepcopy(list(self.service_calls)),
            "matches": deepcopy(list(self.matches)),
            "panel": deepcopy(self.panel),
            "action_trace": deepcopy(self.action_trace),
        }


def local_action_candidate(text: str) -> LocalActionCandidate | None:
    """Return a local low-risk action candidate, if the text is deterministic."""
    normalized = _normalize(text)
    if (
        not normalized
        or _HIGH_RISK_RE.search(normalized)
        or unsafe_action_intent_reason(normalized)
    ):
        return None
    if "音量" in normalized or "声音" in normalized or "静音" in normalized:
        return _volume_candidate(text, normalized)
    return _home_control_candidate(text, normalized)


def unsafe_action_intent_reason(text: str) -> str:
    """Return why an apparent action must not be committed locally."""
    normalized = _normalize(text)
    if not normalized or not _ACTION_VERB_RE.search(normalized):
        return ""
    if _NEGATED_ACTION_RE.search(normalized):
        return "negated_action"
    if _AMBIGUOUS_ACTION_RE.search(normalized):
        return "ambiguous_action"
    return ""


async def async_try_execute_local_capability(
    hass: HomeAssistant,
    text: str,
    route_decision: RouteDecision,
) -> LocalCapabilityResult | None:
    """Execute a local capability when the route explicitly selected one."""
    if route_decision.task_family not in {"home_control", "volume_control"}:
        return None
    candidate = local_action_candidate(text)
    if candidate is None:
        return None
    if candidate.action == "assistant_volume_set":
        return await _async_execute_assistant_volume(hass, candidate)
    if candidate.action == "room_set_temperature":
        return await _async_execute_room_temperature(hass, candidate)
    return await _async_execute_ha_action(hass, candidate)


def _home_control_candidate(text: str, normalized: str) -> LocalActionCandidate | None:
    domain = _domain_from_text(normalized)
    target_temperature = _climate_target_temperature(re.sub(r"\s+", "", text))
    if target_temperature is not None and re.search(r"(了吗|了没|是否|是不是)", text):
        return None
    if (
        not domain
        and target_temperature is not None
        and any(word in normalized for word in ("温度", "室温", "舒适目标"))
    ):
        return LocalActionCandidate(
            family="home_control",
            action="room_set_temperature",
            domain="climate",
            target_hint=text,
            target_temperature=target_temperature,
            confidence=0.9,
        )
    if domain not in LOW_RISK_DOMAINS:
        return None
    if domain == "climate" and target_temperature is not None:
        return LocalActionCandidate(
            family="home_control",
            action="climate_set_temperature",
            domain=domain,
            area=_area_from_text(text),
            target_hint=_climate_target_hint(text, normalized),
            target_scope=_target_scope(text, domain=domain),
            target_temperature=target_temperature,
            confidence=0.88,
        )
    action: LocalActionKind | None = None
    if any(word in normalized for word in ("调亮", "亮一点", "更亮")):
        action = "brightness_up"
        domain = "light"
    elif any(word in normalized for word in ("调暗", "暗一点", "更暗")):
        action = "brightness_down"
        domain = "light"
    elif any(word in normalized for word in ("关闭", "关掉", "关上", "关一下", "关了")):
        action = "turn_off"
    elif any(word in normalized for word in ("打开", "开启", "开一下", "开了")):
        action = "turn_on"
    if action is None:
        return None
    return LocalActionCandidate(
        family="home_control",
        action=action,
        domain=domain,
        area=_area_from_text(text),
        target_hint=_target_hint(text),
        target_scope=_target_scope(text, domain=domain),
        confidence=0.86,
    )


def _volume_candidate(text: str, normalized: str) -> LocalActionCandidate | None:
    is_assistant = bool(_ASSISTANT_VOLUME_RE.search(normalized))
    is_media = bool(_MEDIA_VOLUME_RE.search(normalized))
    if is_assistant and not is_media:
        level = _volume_level_from_text(normalized)
        if level is None:
            level = (
                1.0
                if "大" in normalized or "高" in normalized or "最大" in normalized
                else 0.5
            )
        return LocalActionCandidate(
            family="volume_control",
            action="assistant_volume_set",
            area=_area_from_text(text),
            target_hint="assistant",
            volume_level=level,
            confidence=0.82,
        )
    if not is_media:
        return None
    action: LocalActionKind = "volume_set"
    level = _volume_level_from_text(normalized)
    mute: bool | None = None
    if "静音" in normalized:
        action = "volume_mute"
        mute = not any(word in normalized for word in ("取消静音", "解除静音"))
    elif level is not None:
        action = "volume_set"
    elif any(word in normalized for word in ("调高", "调大", "大一点", "高一点")):
        action = "volume_up"
    elif any(word in normalized for word in ("调低", "调小", "小一点", "低一点")):
        action = "volume_down"
    else:
        return None
    return LocalActionCandidate(
        family="volume_control",
        action=action,
        domain="media_player",
        area=_area_from_text(text),
        target_hint=_target_hint(text),
        volume_level=level,
        mute=mute,
        confidence=0.84,
    )


def _climate_target_temperature(normalized: str) -> float | None:
    match = re.search(
        r"(?:温度)?(?:调到|调成|调至|设为|设置为|设置到|设定为|改到|改成)([+-]?\d+(?:\.\d+)?)度?",
        normalized,
    )
    if match is None:
        return None
    try:
        value = float(match.group(1))
    except ValueError:
        return None
    if not CLIMATE_MIN_SETPOINT <= value <= CLIMATE_MAX_SETPOINT:
        return None
    return value


def _climate_target_hint(text: str, normalized: str) -> str:
    hint = re.sub(
        r"(?:的)?(?:温度)?(?:调到|调成|调至|设为|设置为|设置到|设定为|改到|改成)[+-]?\d+(?:\.\d+)?度?",
        "",
        normalized,
    )
    for word in ("把", "将", "请", "帮我", "帮忙"):
        hint = hint.replace(word, "")
    return hint or _target_hint(text) or "空调"


async def _async_execute_ha_action(
    hass: HomeAssistant, candidate: LocalActionCandidate
) -> LocalCapabilityResult:
    if _targets_all_entities(candidate):
        return await _async_execute_all_targets(hass, candidate)

    resolution_frame = _resolve_device_frame(hass, candidate)
    commitment = resolution_frame.commitment
    if commitment.state != "execute":
        matches = _states_for_candidate_ids(
            hass, _candidate_entity_ids(resolution_frame)
        )
        return LocalCapabilityResult(
            "clarify",
            commitment.prompt or _missing_target_speech(candidate),
            candidate=candidate,
            matches=tuple(_match_trace(match) for match in matches),
            reason=commitment.reason,
            action_trace=_resolution_action_trace(resolution_frame),
        )

    matches = _states_for_candidate_ids(hass, _committed_entity_ids(resolution_frame))
    if not matches:
        return LocalCapabilityResult(
            "clarify",
            _missing_target_speech(candidate),
            candidate=candidate,
            reason="no_matching_entity",
            action_trace=_resolution_action_trace(resolution_frame),
        )
    if _needs_single_target(candidate) and len(matches) > 1:
        return LocalCapabilityResult(
            "clarify",
            _ambiguous_target_speech(candidate, matches),
            candidate=candidate,
            matches=tuple(_match_trace(match) for match in matches),
            reason="ambiguous_target",
            action_trace=_resolution_action_trace(resolution_frame),
        )
    return await _async_dispatch_action(
        hass, candidate, matches, _resolution_action_trace(resolution_frame)
    )


async def _async_execute_room_temperature(
    hass: HomeAssistant, candidate: LocalActionCandidate
) -> LocalCapabilityResult:
    """Change the existing room policy; the RoomMind Control Cycle owns actuation."""
    areas, ambiguous = resolve_room_areas(hass, candidate.target_hint)
    if ambiguous or len(areas) != 1:
        return LocalCapabilityResult(
            "clarify",
            "你想调整哪个房间的舒适温度？",
            candidate=candidate,
            reason="ambiguous_target" if areas else "room_missing",
            action_trace={
                "control_scope": "room_comfort",
                "area_candidates": [
                    {"id": area.id, "name": area.name, "aliases": sorted(area.aliases)}
                    for area in areas or ar.async_get(hass).async_list_areas()
                ],
            },
        )
    area = areas[0]
    entity_id = er.async_get(hass).async_get_entity_id(
        "climate", "roommind", f"roommind_{area.id}_comfort"
    )
    state = hass.states.get(entity_id) if entity_id else None
    if (
        state is None
        or _entity_exclusion_reason(hass, state)
        or not exposed_entities.async_should_expose(hass, "conversation", entity_id)
    ):
        return LocalCapabilityResult(
            "error",
            f"{area.name}的舒适温度控制当前不可用。",
            candidate=candidate,
            reason="room_comfort_unavailable",
        )
    return await _async_dispatch_action(
        hass, candidate, [state], {"control_scope": "room_comfort", "area_id": area.id}
    )


async def _async_dispatch_action(
    hass: HomeAssistant,
    candidate: LocalActionCandidate,
    matches: list[State],
    action_trace: dict[str, Any],
) -> LocalCapabilityResult:
    """Record one HA dispatch separately from physical device application."""
    service, data = _service_for_candidate(candidate, matches)
    if not service:
        return LocalCapabilityResult(
            "unsupported",
            "这个操作我还不能本地执行。",
            candidate=candidate,
            matches=tuple(_match_trace(match) for match in matches),
            reason="unsupported_action",
            action_trace=action_trace,
        )
    domain, service_name = service.split(".", 1)
    dispatch = await _async_dispatch_service(hass, domain, service_name, data)
    dispatch["control_scope"] = action_trace.get("control_scope", "device")
    if dispatch["dispatch_status"] == "failed":
        return LocalCapabilityResult(
            "error",
            "执行失败了，请稍后再试。",
            candidate=candidate,
            service_calls=(dispatch,),
            matches=tuple(_match_trace(match) for match in matches),
            reason=dispatch["error"],
            action_trace=action_trace,
        )
    if candidate.action == "room_set_temperature":
        # This is a later policy observation, separate from device application.
        state = hass.states.get(matches[0].entity_id)
        attributes = state.attributes if state else {}
        dispatch["policy_observation"] = {
            "entity_id": matches[0].entity_id,
            "observed_at": state.last_updated.isoformat() if state else None,
            "override_temperature": attributes.get("override_temperature"),
            "override_active": attributes.get("override_active"),
            "override_suppressed": attributes.get("override_suppressed"),
            "matches_request": bool(
                state
                and state.state not in {"unavailable", "unknown"}
                and attributes.get("override_active") is True
                and attributes.get("override_temperature")
                == candidate.target_temperature
            ),
        }
    return LocalCapabilityResult(
        "executed",
        _dispatch_speech(candidate, matches, dispatch),
        candidate=candidate,
        service_calls=(dispatch,),
        matches=tuple(_match_trace(match) for match in matches),
        action_trace=action_trace,
    )


async def _async_dispatch_service(
    hass: HomeAssistant, domain: str, service: str, data: dict[str, Any]
) -> dict[str, Any]:
    """Capture the driver's existing evidence without adding a second wait loop."""
    context = Context()
    entity_ids = list(data.get(ATTR_ENTITY_ID, []))
    evidence: list[dict[str, Any]] = []

    @callback
    def capture(event: Event) -> None:
        if (
            event.data.get("context_id") == context.id
            and event.data.get("entity_id") in entity_ids
        ):
            evidence.append(deepcopy(dict(event.data)))

    # A driver may report application before the blocking HA service returns.
    unsubscribe = hass.bus.async_listen("tcl_udp_ac_command_result", capture)
    dispatch = {
        "domain": domain,
        "service": service,
        "entity_ids": entity_ids,
        "data": deepcopy(data),
        "context_id": context.id,
        "dispatch_status": "sent",
        "acceptance_status": "unknown",
        "confirmation_status": "unknown",
    }
    try:
        await hass.services.async_call(
            domain, service, data, blocking=True, context=context
        )
    except Exception as err:  # noqa: BLE001 - HA service exceptions vary by integration
        dispatch.update(dispatch_status="failed", error=type(err).__name__)
    finally:
        unsubscribe()
    covered = bool(evidence) and set(entity_ids) <= {
        item["entity_id"] for item in evidence
    }
    if covered and all(
        item.get("transport_outcome")
        in {"accepted_by_udp", "accepted_by_cloud", "accepted_by_both"}
        for item in evidence
    ):
        dispatch["acceptance_status"] = "accepted"
    if dispatch["dispatch_status"] == "sent":
        if any(item.get("outcome") == "not_confirmed" for item in evidence):
            dispatch["confirmation_status"] = "not_confirmed"
        elif covered and all(item.get("outcome") == "applied" for item in evidence):
            dispatch["confirmation_status"] = "confirmed"
    return {**dispatch, "integration_evidence": list(evidence)}


async def _async_execute_all_targets(
    hass: HomeAssistant, candidate: LocalActionCandidate
) -> LocalCapabilityResult:
    matches: list[State] = []
    excluded_entities: list[dict[str, str]] = []
    for state in hass.states.async_all(candidate.domain):
        exclusion_reason = _entity_exclusion_reason(hass, state)
        if exclusion_reason:
            excluded_entities.append(
                {
                    "entity_id": state.entity_id,
                    "reason": exclusion_reason,
                }
            )
            continue
        matches.append(state)
    trace = {
        "target_scope": "all",
        "excluded_entities": excluded_entities[:32],
    }
    if not matches:
        return LocalCapabilityResult(
            "clarify",
            _missing_target_speech(candidate),
            candidate=candidate,
            reason="no_matching_entity",
            action_trace=trace,
        )
    actionable: list[State] = []
    skipped_entities: list[dict[str, str]] = []
    for state in matches:
        satisfied_reason = _already_satisfied_reason(candidate, state)
        if satisfied_reason:
            skipped_entities.append(
                {"entity_id": state.entity_id, "reason": satisfied_reason}
            )
            continue
        actionable.append(state)
    trace["skipped_entities"] = skipped_entities[:32]
    if not actionable:
        return LocalCapabilityResult(
            "executed",
            _already_satisfied_speech(candidate),
            candidate=candidate,
            matches=tuple(_match_trace(match) for match in matches),
            action_trace={
                **trace,
                "attempted_count": 0,
                "succeeded_count": 0,
                "failed_count": 0,
                "failed_entities": [],
            },
        )
    service, _data = _service_for_candidate(candidate, actionable)
    if not service:
        return LocalCapabilityResult(
            "unsupported",
            "这个操作我还不能本地执行。",
            candidate=candidate,
            matches=tuple(_match_trace(match) for match in matches),
            reason="unsupported_action",
            action_trace=trace,
        )
    domain, service_name = service.split(".", 1)
    semaphore = asyncio.Semaphore(BULK_ACTION_MAX_CONCURRENCY)
    service_calls = tuple(
        await asyncio.gather(
            *(
                _async_call_bulk_target(
                    hass,
                    candidate,
                    state,
                    domain=domain,
                    service_name=service_name,
                    semaphore=semaphore,
                )
                for state in actionable
            )
        )
    )
    failed_entities = [
        {
            "entity_id": dispatch["entity_ids"][0],
            "reason": dispatch["error"],
            "context_id": dispatch["context_id"],
            "dispatch_status": "failed",
        }
        for dispatch in service_calls
        if dispatch["dispatch_status"] == "failed"
    ]
    succeeded_count = len(service_calls) - len(failed_entities)
    trace.update(
        {
            "attempted_count": len(actionable),
            "succeeded_count": succeeded_count,
            "failed_count": len(failed_entities),
            "failed_entities": failed_entities[:32],
        }
    )
    if not succeeded_count:
        status, reason = "error", "all_targets_failed"
        speech = "执行失败了，请稍后再试。"
    elif failed_entities:
        status, reason = "partial", "partial_failure"
        speech = _partial_success_speech(
            candidate,
            succeeded_count=succeeded_count,
            failed_count=len(failed_entities),
        )
    else:
        status, reason = "executed", ""
        speech = _dispatch_speech(candidate, matches)
    return LocalCapabilityResult(
        status,
        speech,
        candidate=candidate,
        service_calls=service_calls,
        matches=tuple(_match_trace(match) for match in matches),
        reason=reason,
        action_trace=trace,
    )


async def _async_call_bulk_target(  # noqa: PLR0913 - explicit service context.
    hass: HomeAssistant,
    candidate: LocalActionCandidate,
    state: State,
    *,
    domain: str,
    service_name: str,
    semaphore: asyncio.Semaphore,
) -> dict[str, Any]:
    _service, data = _service_for_candidate(candidate, [state])
    async with semaphore:
        return await _async_dispatch_service(hass, domain, service_name, data)


async def _async_execute_assistant_volume(
    hass: HomeAssistant, candidate: LocalActionCandidate
) -> LocalCapabilityResult:
    entity_ids = [
        entity_id
        for entity_id in ASSISTANT_VOLUME_ENTITIES
        if hass.states.get(entity_id)
    ]
    if not entity_ids or not hass.services.has_service("input_number", "set_value"):
        return LocalCapabilityResult(
            "clarify",
            "我说话音量控制还没有配置好。",
            candidate=candidate,
            reason="assistant_volume_unconfigured",
        )
    service_calls: list[dict[str, Any]] = []
    requested_level = (
        candidate.volume_level if candidate.volume_level is not None else 0.5
    )
    for entity_id in entity_ids:
        state = hass.states.get(entity_id)
        value = _bounded_assistant_volume_value(state, requested_level)
        await hass.services.async_call(
            "input_number",
            "set_value",
            {ATTR_ENTITY_ID: [entity_id], "value": value},
            blocking=True,
        )
        service_calls.append(
            {
                "domain": "input_number",
                "service": "set_value",
                "entity_ids": [entity_id],
                "value": value,
            }
        )
    verified_state = {
        entity_id: (state.state if (state := hass.states.get(entity_id)) else "")
        for entity_id in entity_ids
    }
    return LocalCapabilityResult(
        "executed",
        "已请求调整播报音量。",
        candidate=candidate,
        service_calls=tuple(service_calls),
        action_trace={
            "adapter": "ha_input_number",
            "target": "assistant_voice",
            "requested_level": requested_level,
            "status": "executed",
            "verified_state": verified_state,
        },
    )


def _resolve_entities(
    hass: HomeAssistant, candidate: LocalActionCandidate
) -> list[State]:
    frame = _resolve_device_frame(hass, candidate)
    committed_ids = _committed_entity_ids(frame)
    if committed_ids:
        return [
            state
            for entity_id in committed_ids
            if (state := hass.states.get(entity_id)) is not None
        ]
    candidate_ids = _candidate_entity_ids(frame)
    if candidate_ids:
        return [
            state
            for entity_id in candidate_ids
            if (state := hass.states.get(entity_id)) is not None
        ][:12]

    # Fallback for unusual domains or registry states not indexed by the
    # resolution kernel yet.
    states = [
        state
        for state in hass.states.async_all(candidate.domain)
        if not _entity_exclusion_reason(hass, state)
    ]
    if candidate.area:
        states = [
            state
            for state in states
            if candidate.area in _entity_area_names(hass, state.entity_id)
            or candidate.area in _normalize(_state_name(state))
        ]
    hint = _normalize(candidate.target_hint)
    if hint:
        strong = [
            state
            for state in states
            if hint in _normalize(_state_name(state))
            or any(
                part and part in _normalize(_state_name(state))
                for part in _hint_parts(hint)
            )
        ]
        if strong:
            states = strong
    if not candidate.area and len(states) > 1:
        exact = [
            state
            for state in states
            if _normalize(_state_name(state)) in _hint_parts(hint)
        ]
        if exact:
            states = exact
    return states[:12]


def _states_for_candidate_ids(
    hass: HomeAssistant,
    entity_ids: tuple[str, ...],
) -> list[State]:
    return [
        state
        for entity_id in entity_ids
        if (state := hass.states.get(entity_id)) is not None
    ]


def _resolve_device_frame(
    hass: HomeAssistant,
    candidate: LocalActionCandidate,
) -> SemanticResolutionFrame:
    states = tuple(
        DeviceReference(
            id=state.entity_id,
            name=_state_name(state),
            domain=candidate.domain,
            areas=_entity_area_names(hass, state.entity_id),
            aliases=(_state_name(state),),
            state=state.state,
        )
        for state in hass.states.async_all(candidate.domain)
        if not _entity_exclusion_reason(hass, state)
    )
    return resolve_device_referent(
        raw_text=candidate.target_hint,
        domain=candidate.domain,
        action=candidate.action,
        devices=states,
        area=candidate.area,
    )


def _committed_entity_ids(frame: SemanticResolutionFrame) -> tuple[str, ...]:
    if frame.commitment.state != "execute":
        return ()
    for referent in frame.referents:
        if referent.slot == "target_device" and referent.candidates:
            return (referent.candidates[0].id,)
    return ()


def _candidate_entity_ids(frame: SemanticResolutionFrame) -> tuple[str, ...]:
    for referent in frame.referents:
        if referent.slot == "target_device":
            return tuple(candidate.id for candidate in referent.candidates)
    return ()


def _resolution_action_trace(frame: SemanticResolutionFrame) -> dict[str, Any]:
    referent = frame.referents[0] if frame.referents else None
    candidates = referent.candidates if referent else ()
    return {
        "resolution_frame": frame.as_dict(),
        "commitment_decision": frame.commitment.as_dict(),
        "referent_status": referent.status if referent else "",
        "candidate_scores": [candidate.as_dict() for candidate in candidates],
        "top_candidate": candidates[0].as_dict() if candidates else {},
    }


def _entity_area_names(hass: HomeAssistant, entity_id: str) -> tuple[str, ...]:
    try:
        entity_reg = er.async_get(hass)
        area_reg = ar.async_get(hass)
        device_reg = dr.async_get(hass)
        entry = entity_reg.async_get(entity_id)
        area_ids: list[str] = []
        if entry is not None:
            if entry.area_id:
                area_ids.append(entry.area_id)
            if entry.device_id:
                device = device_reg.async_get(entry.device_id)
                if device and device.area_id:
                    area_ids.append(device.area_id)
        names: list[str] = []
        for area_id in area_ids:
            area = area_reg.async_get_area(area_id)
            if area and area.name:
                names.append(area.name)
        return tuple(names)
    except Exception:  # noqa: BLE001 - registry APIs differ across HA versions
        return ()


def _entity_exclusion_reason(  # noqa: PLR0911 - explicit exclusion states.
    hass: HomeAssistant, state: State
) -> str:
    """Return why an entity must not be a user-facing control target."""
    if state.state in {"unavailable", "unknown"}:
        return state.state
    try:
        entry = er.async_get(hass).async_get(state.entity_id)
    except Exception:  # noqa: BLE001 - registry APIs differ across HA versions
        return ""
    if entry is None:
        return ""
    if entry.disabled_by is not None:
        return "disabled"
    if entry.hidden_by is not None:
        return "hidden"
    if entry.entity_category is not None:
        category = getattr(entry.entity_category, "value", entry.entity_category)
        return f"entity_category:{category}"
    return ""


def _service_for_candidate(  # noqa: PLR0911 - explicit HA service mapping.
    candidate: LocalActionCandidate, matches: list[State]
) -> tuple[str, dict[str, Any]]:
    entity_ids = [state.entity_id for state in matches]
    if candidate.action == "turn_on":
        return f"{candidate.domain}.turn_on", {ATTR_ENTITY_ID: entity_ids}
    if candidate.action == "turn_off":
        return f"{candidate.domain}.turn_off", {ATTR_ENTITY_ID: entity_ids}
    if candidate.action == "brightness_up":
        return "light.turn_on", {ATTR_ENTITY_ID: entity_ids, "brightness_step_pct": 20}
    if candidate.action == "brightness_down":
        return "light.turn_on", {ATTR_ENTITY_ID: entity_ids, "brightness_step_pct": -20}
    if candidate.action in {"climate_set_temperature", "room_set_temperature"}:
        return (
            "climate.set_temperature",
            {
                ATTR_ENTITY_ID: entity_ids,
                "temperature": candidate.target_temperature,
            },
        )
    if candidate.action == "volume_up":
        return "media_player.volume_up", {ATTR_ENTITY_ID: entity_ids}
    if candidate.action == "volume_down":
        return "media_player.volume_down", {ATTR_ENTITY_ID: entity_ids}
    if candidate.action == "volume_set":
        return (
            "media_player.volume_set",
            {
                ATTR_ENTITY_ID: entity_ids,
                "volume_level": candidate.volume_level
                if candidate.volume_level is not None
                else 0.5,
            },
        )
    if candidate.action == "volume_mute":
        return (
            "media_player.volume_mute",
            {ATTR_ENTITY_ID: entity_ids, "is_volume_muted": bool(candidate.mute)},
        )
    return "", {}


def _dispatch_speech(
    candidate: LocalActionCandidate,
    matches: list[State],
    dispatch: dict[str, Any] | None = None,
) -> str:
    """Service completion establishes dispatch, not physical application."""
    dispatch = dispatch or {}
    confirmation_status = dispatch.get("confirmation_status", "unknown")
    label = (
        f"所有{_domain_label(candidate.domain)}"
        if _targets_all_entities(candidate)
        else _target_label(candidate, matches)
    )
    action = {
        "turn_on": "打开",
        "turn_off": "关闭",
        "brightness_up": "调亮",
        "brightness_down": "调暗",
        "volume_up": "调高音量",
        "volume_down": "调低音量",
        "volume_set": "调整音量",
        "volume_mute": "静音" if candidate.mute else "取消静音",
    }.get(candidate.action, "操作")
    if candidate.action in {"climate_set_temperature", "room_set_temperature"}:
        temperature = _format_temperature(candidate.target_temperature)
        policy = dispatch.get("policy_observation", {})
        if candidate.action == "room_set_temperature" and policy.get("matches_request"):
            suffix = "当前离家策略仍优先。" if policy.get("override_suppressed") else ""
            return f"{label}已保存为{temperature}度。{suffix}"
        if confirmation_status == "confirmed":
            return f"{label}已回报设定 {temperature} 度。"
        return f"已请求将{label}设为{temperature}度。"
    if confirmation_status == "confirmed":
        return f"{label}已回报请求的状态。"
    return f"已向{label}发送{action}请求。"


def _partial_success_speech(
    candidate: LocalActionCandidate,
    *,
    succeeded_count: int,
    failed_count: int,
) -> str:
    action = {
        "turn_on": "打开",
        "turn_off": "关闭",
        "brightness_up": "调亮",
        "brightness_down": "调暗",
        "climate_set_temperature": "设置",
    }.get(candidate.action, "操作")
    label = _domain_label(candidate.domain)
    return (
        f"已向 {succeeded_count} 个{label}发送{action}请求，{failed_count} 个发送失败。"
    )


def _already_satisfied_reason(
    candidate: LocalActionCandidate,
    state: State,
) -> str:
    if candidate.action == "turn_on" and state.state == "on":
        return "already_on"
    if candidate.action == "turn_off" and state.state == "off":
        return "already_off"
    return ""


def _already_satisfied_speech(candidate: LocalActionCandidate) -> str:
    state = "打开" if candidate.action == "turn_on" else "关闭"
    return f"所有{_domain_label(candidate.domain)}已经{state}。"


def _format_temperature(value: float | None) -> str:
    if value is None:
        return ""
    if float(value).is_integer():
        return str(int(value))
    return f"{value:g}"


def _target_label(candidate: LocalActionCandidate, matches: list[State]) -> str:
    if len(matches) == 1:
        return _state_name(matches[0])
    if candidate.area:
        return f"{candidate.area}{_domain_label(candidate.domain)}"
    return _domain_label(candidate.domain)


def _missing_target_speech(candidate: LocalActionCandidate) -> str:
    label = _domain_label(candidate.domain) if candidate.domain else "目标设备"
    if candidate.area:
        return f"我没找到{candidate.area}的{label}。"
    return f"你想操作哪个{label}？"


def _ambiguous_target_speech(
    candidate: LocalActionCandidate, matches: Iterable[State]
) -> str:
    names = "、".join(_state_name(state) for state in list(matches)[:3])
    label = _domain_label(candidate.domain) if candidate.domain else "设备"
    return f"找到多个{label}：{names}。你想操作哪一个？"


def _match_trace(state: State) -> dict[str, str]:
    return {
        "entity_id": state.entity_id,
        "name": _state_name(state),
        "state": state.state,
    }


def _needs_single_target(candidate: LocalActionCandidate) -> bool:
    return candidate.domain == "media_player" or not candidate.area


def _targets_all_entities(candidate: LocalActionCandidate) -> bool:
    return candidate.target_scope == "all"


def _target_scope(text: str, *, domain: str) -> TargetScope:
    normalized = _normalize(text)
    label = _domain_label(domain)
    if any(
        phrase in normalized
        for phrase in (
            f"{quantifier}{particle}{label}"
            for quantifier in ("所有", "全部", "每个", "每一")
            for particle in ("", "的")
        )
    ):
        return "all"
    if _area_from_text(text):
        return "area"
    return "single"


def _bounded_assistant_volume_value(state: State | None, level: float) -> float:
    minimum = _float_attr(state, "min", 0.0)
    maximum = _float_attr(state, "max", 1.0)
    if maximum > 1.0 and 0.0 <= level <= 1.0:
        return minimum + ((maximum - minimum) * level)
    return max(minimum, min(maximum, level))


def _float_attr(state: State | None, name: str, default: float) -> float:
    try:
        return float((state.attributes if state else {}).get(name, default))
    except (TypeError, ValueError):
        return default


def _domain_from_text(normalized: str) -> str:
    if any(word in normalized for word in ("灯", "灯光", "照明")):
        return "light"
    if any(word in normalized for word in ("空调", "温控", "恒温器", "暖气")):
        return "climate"
    if any(word in normalized for word in ("风扇", "循环扇")):
        return "fan"
    if any(
        word in normalized
        for word in ("音箱", "播放器", "homepod", "喇叭", "扬声器", "电视", "媒体")
    ):
        return "media_player"
    if "开关" in normalized:
        return "switch"
    return ""


def _domain_label(domain: str) -> str:
    return {
        "light": "灯",
        "climate": "空调",
        "fan": "风扇",
        "switch": "开关",
        "media_player": "播放器",
    }.get(domain, "设备")


def _area_from_text(text: str) -> str:
    for area in sorted(_AREA_HINTS, key=len, reverse=True):
        if area in text:
            return area
    return ""


def _target_hint(text: str) -> str:
    normalized = _normalize(text)
    for word in (
        "打开",
        "开启",
        "关闭",
        "关掉",
        "关上",
        "关了",
        "开了",
        "开一下",
        "关一下",
        "调亮",
        "调暗",
        "调高",
        "调低",
        "调大",
        "调小",
        "音量",
        "最大",
        "最小",
        "静音",
        "把",
        "到",
    ):
        normalized = normalized.replace(word, "")
    return normalized


def _volume_level_from_text(normalized: str) -> float | None:
    if "最大" in normalized or "最高" in normalized:
        return 1.0
    if "最小" in normalized or "最低" in normalized:
        return 0.0
    match = re.search(r"(\d{1,3})%", normalized)
    if match:
        return max(0.0, min(1.0, int(match.group(1)) / 100))
    return None


def _state_name(state: State) -> str:
    return str(state.attributes.get("friendly_name") or state.name or state.entity_id)


def _hint_parts(hint: str) -> tuple[str, ...]:
    return tuple(
        part
        for part in re.split(r"(灯|空调|温控|恒温器|暖气|音箱|播放器|开关|风扇)", hint)
        if part
    )


def _normalize(text: str) -> str:
    return _NORMALIZE_RE.sub("", str(text or "")).lower()
