"""HA weather context provider.

This module is the seam between semantic weather capabilities and concrete Home
Assistant weather providers such as the tianqi integration. Callers should not
need to know whether weather data came from a weather entity, tianqi attributes,
or a future adapter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, State

WeatherForecastType = Literal["daily", "hourly"]

WEATHER_DOMAIN = "weather"
GET_FORECASTS_SERVICE = "get_forecasts"
UNAVAILABLE_STATES = {"", "unknown", "unavailable", "none", "null"}

CONDITION_LABELS = {
    "clear-night": "晴",
    "cloudy": "多云",
    "exceptional": "极端天气",
    "fog": "有雾",
    "hail": "冰雹",
    "lightning": "雷电",
    "lightning-rainy": "雷雨",
    "partlycloudy": "多云",
    "pouring": "大雨",
    "rainy": "有雨",
    "snowy": "下雪",
    "snowy-rainy": "雨夹雪",
    "sunny": "晴",
    "windy": "有风",
    "windy-variant": "大风",
}


@dataclass(frozen=True, slots=True)
class CurrentWeather:
    """Normalized current weather readings."""

    condition: str = ""
    condition_text: str = ""
    temperature: float | None = None
    temperature_unit: str = "°C"
    humidity: float | None = None
    pressure: float | None = None
    pressure_unit: str = ""
    wind_bearing: str = ""
    wind_speed: float | None = None
    wind_speed_unit: str = ""
    visibility: float | None = None
    visibility_unit: str = ""
    updated_time: str = ""


@dataclass(frozen=True, slots=True)
class WeatherNowcast:
    """Short-horizon weather hints exposed by providers such as tianqi."""

    minutely: str = ""
    hourly_hint: str = ""
    keypoint: str = ""
    alert: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class WeatherForecast:
    """One normalized forecast row."""

    datetime: str = ""
    condition: str = ""
    condition_text: str = ""
    temperature: float | None = None
    templow: float | None = None
    humidity: float | None = None
    precipitation: float | None = None
    wind_bearing: str = ""
    wind_speed: float | None = None


@dataclass(frozen=True, slots=True)
class WeatherForecasts:
    """Forecast rows grouped by provider horizon."""

    daily: tuple[WeatherForecast, ...] = ()
    hourly: tuple[WeatherForecast, ...] = ()


@dataclass(frozen=True, slots=True)
class WeatherContext:
    """Normalized weather context for answer rendering and tracing."""

    source: str
    provider: str
    entity_id: str
    location: str
    current: CurrentWeather
    nowcast: WeatherNowcast
    forecasts: WeatherForecasts = field(default_factory=WeatherForecasts)
    evidence: tuple[str, ...] = ()

    def trace_attrs(self) -> dict[str, Any]:
        """Return compact trace attrs for the Voice Harness."""
        return {
            "source": self.source,
            "provider": self.provider,
            "entity_id": self.entity_id,
            "location": self.location,
            "current": {
                "condition": self.current.condition,
                "condition_text": self.current.condition_text,
                "temperature": self.current.temperature,
                "temperature_unit": self.current.temperature_unit,
                "humidity": self.current.humidity,
                "wind_bearing": self.current.wind_bearing,
                "wind_speed": self.current.wind_speed,
                "wind_speed_unit": self.current.wind_speed_unit,
                "updated_time": self.current.updated_time,
            },
            "nowcast": {
                "minutely": self.nowcast.minutely,
                "hourly_hint": self.nowcast.hourly_hint,
                "keypoint": self.nowcast.keypoint,
            },
            "forecast_counts": {
                "daily": len(self.forecasts.daily),
                "hourly": len(self.forecasts.hourly),
            },
            "evidence": list(self.evidence),
        }


class WeatherContextProvider:
    """Resolve HA weather entities into normalized weather context."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass

    async def async_get_current(
        self,
        *,
        location_hint: str = "",
    ) -> WeatherContext | None:
        """Return current weather from the best matching HA weather entity."""
        state = self._select_weather_state(location_hint=location_hint)
        if state is None:
            return None
        return self._context_from_state(
            state, evidence=("weather_entity:" + state.entity_id,)
        )

    async def async_get_forecast(
        self,
        *,
        location_hint: str = "",
        forecast_type: WeatherForecastType = "daily",
    ) -> WeatherContext | None:
        """Return current weather plus forecast rows from HA weather service."""
        state = self._select_weather_state(location_hint=location_hint)
        if state is None:
            return None
        context = self._context_from_state(
            state, evidence=("weather_entity:" + state.entity_id,)
        )
        forecasts = await self._async_call_forecasts(state.entity_id, forecast_type)
        if forecasts is None:
            return context
        grouped = (
            WeatherForecasts(daily=forecasts)
            if forecast_type == "daily"
            else WeatherForecasts(hourly=forecasts)
        )
        return WeatherContext(
            source=context.source,
            provider=context.provider,
            entity_id=context.entity_id,
            location=context.location,
            current=context.current,
            nowcast=context.nowcast,
            forecasts=grouped,
            evidence=(
                *context.evidence,
                f"weather_forecast:{forecast_type}",
            ),
        )

    def _select_weather_state(self, *, location_hint: str) -> State | None:
        states = [
            state
            for state in self._hass.states.async_all(WEATHER_DOMAIN)
            if _state_is_available(state.state)
        ]
        if not states:
            return None
        return sorted(
            states,
            key=lambda state: _weather_state_score(
                self._hass,
                state,
                location_hint=location_hint,
            ),
            reverse=True,
        )[0]

    def _context_from_state(
        self,
        state: State,
        *,
        evidence: tuple[str, ...],
    ) -> WeatherContext:
        attrs = state.attributes
        condition = str(state.state or "")
        condition_text = str(attrs.get("condition_desc") or _condition_label(condition))
        return WeatherContext(
            source="ha_weather",
            provider=_provider_for_entity(self._hass, state.entity_id),
            entity_id=state.entity_id,
            location=_location_for_state(state),
            current=CurrentWeather(
                condition=condition,
                condition_text=condition_text,
                temperature=_float_or_none(attrs.get("temperature")),
                temperature_unit=str(attrs.get("temperature_unit") or "°C"),
                humidity=_float_or_none(attrs.get("humidity")),
                pressure=_float_or_none(attrs.get("pressure")),
                pressure_unit=str(attrs.get("pressure_unit") or ""),
                wind_bearing=str(attrs.get("wind_bearing") or ""),
                wind_speed=_float_or_none(attrs.get("wind_speed")),
                wind_speed_unit=str(attrs.get("wind_speed_unit") or ""),
                visibility=_float_or_none(attrs.get("visibility")),
                visibility_unit=str(attrs.get("visibility_unit") or ""),
                updated_time=str(attrs.get("updated_time") or ""),
            ),
            nowcast=WeatherNowcast(
                minutely=str(attrs.get("forecast_minutely") or ""),
                hourly_hint=str(attrs.get("forecast_hourly") or ""),
                keypoint=str(attrs.get("forecast_keypoint") or ""),
                alert=attrs.get("forecast_alert")
                if isinstance(attrs.get("forecast_alert"), dict)
                else {},
            ),
            evidence=(
                *evidence,
                f"provider:{_provider_for_entity(self._hass, state.entity_id)}",
            ),
        )

    async def _async_call_forecasts(
        self,
        entity_id: str,
        forecast_type: WeatherForecastType,
    ) -> tuple[WeatherForecast, ...] | None:
        if not self._hass.services.has_service(WEATHER_DOMAIN, GET_FORECASTS_SERVICE):
            return None
        try:
            response = await self._hass.services.async_call(
                WEATHER_DOMAIN,
                GET_FORECASTS_SERVICE,
                {ATTR_ENTITY_ID: entity_id, "type": forecast_type},
                blocking=True,
                return_response=True,
            )
        except (HomeAssistantError, ValueError, TypeError):
            return None
        raw_forecasts = _forecast_rows_from_response(response, entity_id)
        return tuple(_forecast_from_row(row) for row in raw_forecasts)


def render_weather_context_answer(
    context: WeatherContext,
    *,
    time_horizon: str,
) -> str:
    """Render a concise spoken weather answer."""
    if time_horizon in {"tomorrow", "future"} and context.forecasts.daily:
        return _render_forecast_answer(
            context.location,
            context.forecasts.daily[0],
            time_horizon=time_horizon,
        )
    return _render_current_answer(context)


def _render_forecast_answer(
    location: str,
    forecast: WeatherForecast,
    *,
    time_horizon: str,
) -> str:
    label = "明天" if time_horizon == "tomorrow" else "未来"
    condition = forecast.condition_text or _condition_label(forecast.condition)
    parts = [f"{location}{label}天气：{condition}"]
    if forecast.templow is not None and forecast.temperature is not None:
        low = _format_number(forecast.templow)
        high = _format_number(forecast.temperature)
        parts.append(f"{low} 到 {high} 度")
    elif forecast.temperature is not None:
        parts.append(f"{_format_number(forecast.temperature)} 度")
    if forecast.precipitation is not None:
        parts.append(f"降水 {_format_number(forecast.precipitation)} 毫米")
    if forecast.humidity is not None:
        parts.append(f"湿度 {_format_number(forecast.humidity)}%")
    if forecast.wind_bearing:
        parts.append(forecast.wind_bearing)
    return "，".join(parts) + "。"


def _render_current_answer(context: WeatherContext) -> str:
    current = context.current
    condition = current.condition_text or _condition_label(current.condition)
    parts = [f"{context.location}现在{condition}"]
    if current.temperature is not None:
        parts.append(f"{_format_number(current.temperature)} 度")
    if current.humidity is not None:
        parts.append(f"湿度 {_format_number(current.humidity)}%")
    if current.wind_bearing:
        wind = current.wind_bearing
        if current.wind_speed is not None:
            speed = _format_number(current.wind_speed)
            unit = current.wind_speed_unit or "km/h"
            wind += f"，风速 {speed} {unit}"
        parts.append(wind)
    if current.visibility is not None:
        visibility = _format_number(current.visibility)
        unit = current.visibility_unit or "km"
        parts.append(f"能见度 {visibility} {unit}")
    speech = "，".join(parts) + "。"
    if context.nowcast.minutely:
        speech += context.nowcast.minutely
        if not speech.endswith(("。", "！", "？", ".", "!", "?")):
            speech += "。"
    if context.nowcast.keypoint:
        speech += f"提示：{context.nowcast.keypoint}"
        if not speech.endswith(("。", "！", "？", ".", "!", "?")):
            speech += "。"
    return speech


def _weather_state_score(
    hass: HomeAssistant,
    state: State,
    *,
    location_hint: str,
) -> tuple[int, int, str]:
    attrs = state.attributes
    name = str(attrs.get("friendly_name") or state.entity_id)
    normalized_hint = _normalize(location_hint)
    searchable = _normalize(f"{state.entity_id} {name}")
    platform = _provider_for_entity(hass, state.entity_id)
    hint_score = 10 if normalized_hint and normalized_hint in searchable else 0
    provider_score = 3 if platform == "tianqi" else 0
    feature_score = int(attrs.get("supported_features") or 0)
    return (hint_score + provider_score, feature_score, state.entity_id)


def _provider_for_entity(hass: HomeAssistant, entity_id: str) -> str:
    registry = er.async_get(hass)
    entry = registry.async_get(entity_id)
    if entry is not None and entry.platform:
        return str(entry.platform)
    return "ha_weather"


def _location_for_state(state: State) -> str:
    friendly = str(state.attributes.get("friendly_name") or "")
    value = friendly or state.entity_id.removeprefix(f"{WEATHER_DOMAIN}.")
    for suffix in ("天气", " 静安"):
        value = value.replace(suffix, " ")
    parts = [part for part in value.replace("_", " ").split() if part]
    if not parts:
        return "当地"
    if "静安" in friendly:
        return "静安"
    return parts[0]


def _forecast_rows_from_response(
    response: object,
    entity_id: str,
) -> list[dict[str, Any]]:
    if not isinstance(response, dict):
        return []
    payload = response.get(entity_id)
    if isinstance(payload, dict) and isinstance(payload.get("forecast"), list):
        return [row for row in payload["forecast"] if isinstance(row, dict)]
    service_response = response.get("service_response")
    if isinstance(service_response, dict):
        nested = service_response.get(entity_id)
        if isinstance(nested, dict) and isinstance(nested.get("forecast"), list):
            return [row for row in nested["forecast"] if isinstance(row, dict)]
    return []


def _forecast_from_row(row: dict[str, Any]) -> WeatherForecast:
    condition = str(row.get("condition") or "")
    return WeatherForecast(
        datetime=str(row.get("datetime") or ""),
        condition=condition,
        condition_text=_condition_label(condition),
        temperature=_float_or_none(row.get("temperature")),
        templow=_float_or_none(row.get("templow")),
        humidity=_float_or_none(row.get("humidity")),
        precipitation=_float_or_none(row.get("precipitation")),
        wind_bearing=str(row.get("wind_bearing") or ""),
        wind_speed=_float_or_none(row.get("wind_speed")),
    )


def _state_is_available(value: str) -> bool:
    return str(value or "").strip().lower() not in UNAVAILABLE_STATES


def _condition_label(condition: str) -> str:
    return CONDITION_LABELS.get(str(condition or ""), str(condition or "天气"))


def _float_or_none(value: object) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_number(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.1f}".rstrip("0").rstrip(".")


def _normalize(value: str) -> str:
    return (
        str(value or "")
        .strip()
        .lower()
        .replace(" ", "")
        .replace("_", "")
        .replace(".", "")
    )
