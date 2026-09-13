"""Read room conditions from Home Assistant's designated area sensors."""

from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING

from homeassistant.components.homeassistant import exposed_entities
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .static_context import (
    ExposedEntity,
    ScalarStateRenderResult,
    state_metrics_from_text,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, State

    from .capabilities import RouteDecision


def read_area_observation(
    hass: HomeAssistant, text: str, decision: RouteDecision
) -> ScalarStateRenderResult | None:
    """Use the chosen room source even when it cannot currently answer.

    Returning None delegates unconfigured rooms and explicit device questions
    to the existing context reader. An unavailable chosen source never does.
    """
    metrics = state_metrics_from_text(text)
    if (
        decision.scope not in {"indoor_environment", "home_summary"}
        or not metrics
        or not set(metrics) <= {"temperature", "humidity"}
        or decision.metadata.get("domain")
        or any(word in text for word in ("空调", "暖气", "温控"))
    ):
        return None
    if decision.scope == "home_summary":
        areas = tuple(ar.async_get(hass).async_list_areas())
        ambiguous = False
    else:
        areas, ambiguous = resolve_room_areas(hass, text)
    if ambiguous:
        return ScalarStateRenderResult(
            speech=f"你指的是{'、'.join(area.name for area in areas)}中的哪一个？",
            task_type=decision.task_type,
            source="ha_area_sensor",
            entity_count=0,
            entities=(),
            metrics=metrics,
            answerable=False,
            target_covered=False,
            missing_requirements=("area",),
            outcome_reason="ambiguous_target",
        )
    selected = tuple(
        area
        for area in areas
        if any(getattr(area, f"{metric}_entity_id") for metric in metrics)
    )
    if not selected:
        return None
    if decision.scope != "home_summary":
        selected = areas
    readings = tuple(
        _read_area_metric(hass, area, metric, decision)
        for area in selected
        for metric in metrics
    )
    if len(readings) == 1:
        return readings[0]
    entities = tuple(entity for reading in readings for entity in reading.entities)
    missing = tuple(
        dict.fromkeys(
            metric for reading in readings for metric in reading.missing_requirements
        )
    )
    return ScalarStateRenderResult(
        speech="".join(reading.speech for reading in readings),
        task_type=decision.task_type,
        source="ha_area_sensor",
        entity_count=len(entities),
        entities=entities,
        metrics=metrics,
        answerable=not missing,
        required_data=metrics,
        available_data=tuple(
            dict.fromkeys(
                metric for reading in readings for metric in reading.available_data
            )
        ),
        missing_requirements=missing,
        outcome_reason=next(
            (reading.outcome_reason for reading in readings if not reading.answerable),
            "answered",
        ),
    )


def resolve_room_areas(
    hass: HomeAssistant, text: str
) -> tuple[tuple[ar.AreaEntry, ...], bool]:
    """Match registry names and aliases without folding a numbered room into another.

    Longer overlapping names win. A shared alias is ambiguous; separate named
    rooms remain separate targets.
    """
    normalized = re.sub(r"\s+", "", text).casefold()
    labels = sorted(
        (
            (re.sub(r"\s+", "", label).casefold(), area)
            for area in ar.async_get(hass).async_list_areas()
            for label in (area.name, *area.aliases)
            if label.strip()
        ),
        key=lambda item: len(item[0]),
        reverse=True,
    )
    matches: dict[tuple[int, int], list[ar.AreaEntry]] = {}
    for label, area in labels:
        for match in re.finditer(re.escape(label) + r"(?!\d)", normalized):
            start, end = match.span()
            if any(
                left <= start and right >= end and right - left > end - start
                for left, right in matches
            ):
                continue
            entries = matches.setdefault((start, end), [])
            if area not in entries:
                entries.append(area)
    areas = {area.id: area for entries in matches.values() for area in entries}
    return tuple(areas.values()), any(len(entries) > 1 for entries in matches.values())


def _read_area_metric(
    hass: HomeAssistant, area: ar.AreaEntry, metric: str, decision: RouteDecision
) -> ScalarStateRenderResult:
    entity_id = getattr(area, f"{metric}_entity_id")
    entry = er.async_get(hass).async_get(entity_id) if entity_id else None
    visible = bool(entity_id) and exposed_entities.async_should_expose(
        hass, "conversation", entity_id
    )
    if entry and (entry.disabled_by or entry.hidden_by or entry.entity_category):
        visible = False
    state = hass.states.get(entity_id) if visible else None
    value = _numeric_state(state)
    reason = "answered" if value is not None else "requested_metric_missing"
    if state and _report_expired(state):
        value = None
        reason = "observation_expired"
    if not visible:
        reason = "not_exposed"
    label = "温度" if metric == "temperature" else "湿度"
    if value is None:
        speech = f"{area.name}{label}当前不可用。"
    elif metric == "humidity":
        speech = f"{area.name}湿度现在 {value:g}%。"
    else:
        unit = state.attributes.get("unit_of_measurement", "")
        scale = "华氏 " if unit == "°F" else ""
        speech = f"{area.name}现在 {scale}{value:g} 度。"
    entities = (
        ()
        if state is None
        else (
            ExposedEntity(
                entity_id=entity_id,
                name=state.name,
                domain="sensor",
                areas=(area.name,),
                state=state.state,
                unit_of_measurement=str(
                    state.attributes.get("unit_of_measurement", "")
                ),
                attributes=tuple(
                    (key, str(state.attributes[key]))
                    for key in (
                        "observed_at",
                        "observation_source",
                        "observation_max_age_s",
                    )
                    if key in state.attributes
                ),
                source="ha_registry",
            ),
        )
    )
    return ScalarStateRenderResult(
        speech=speech,
        task_type=decision.task_type,
        source="ha_area_sensor",
        entity_count=len(entities),
        entities=entities,
        metrics=(metric,),
        answerable=value is not None,
        required_data=(metric,),
        available_data=(metric,) if value is not None else (),
        missing_requirements=() if value is not None else (metric,),
        outcome_reason=reason,
    )


def _numeric_state(state: State | None) -> float | None:
    if state is None:
        return None
    try:
        value = float(state.state)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def _report_expired(state: State) -> bool:
    """Check field age without treating another metric's update as fresh data."""
    max_age = state.attributes.get("observation_max_age_s")
    if max_age is None:
        return False
    observed_at = state.attributes.get("observed_at")
    observed = (
        dt_util.parse_datetime(observed_at) if isinstance(observed_at, str) else None
    )
    if (
        observed is None
        or observed.tzinfo is None
        or not isinstance(max_age, int | float)
        or not math.isfinite(max_age)
        or max_age <= 0
    ):
        return True
    age = (dt_util.utcnow() - observed).total_seconds()
    return age < 0 or age >= max_age
