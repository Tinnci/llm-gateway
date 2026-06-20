"""Tests for HA weather entity context retrieval."""

from __future__ import annotations

from homeassistant.core import SupportsResponse

from custom_components.llm_gateway.weather_context import (
    WeatherContextProvider,
    render_weather_context_answer,
)


def _set_weather_state(hass) -> None:
    hass.states.async_set(
        "weather.jingan",
        "partlycloudy",
        {
            "friendly_name": "静安天气 静安",
            "temperature": 26.7,
            "temperature_unit": "°C",
            "humidity": 85,
            "pressure": 1007.0,
            "pressure_unit": "hPa",
            "wind_bearing": "西风",
            "wind_speed": 1.0,
            "wind_speed_unit": "km/h",
            "visibility": 8.0,
            "visibility_unit": "km",
            "condition_desc": "多云",
            "forecast_minutely": "未来2小时不会下雨",
            "forecast_keypoint": "有降水，带雨伞，短期外出可收起雨伞。",
            "updated_time": "20:05",
            "supported_features": 3,
        },
    )


async def test_weather_context_provider_reads_current_weather_entity(hass) -> None:
    _set_weather_state(hass)

    context = await WeatherContextProvider(hass).async_get_current(location_hint="静安")

    assert context is not None
    assert context.entity_id == "weather.jingan"
    assert context.provider == "ha_weather"
    assert context.location == "静安"
    assert context.current.condition == "partlycloudy"
    assert context.current.condition_text == "多云"
    assert context.current.temperature == 26.7
    assert context.nowcast.minutely == "未来2小时不会下雨"
    assert "weather_entity:weather.jingan" in context.evidence

    speech = render_weather_context_answer(context, time_horizon="now")
    assert "静安现在多云" in speech
    assert "26.7 度" in speech
    assert "未来2小时不会下雨" in speech


async def test_weather_context_provider_calls_ha_forecast_service(hass) -> None:
    _set_weather_state(hass)
    calls: list[dict[str, object]] = []

    async def get_forecasts(call):
        calls.append(dict(call.data))
        return {
            "weather.jingan": {
                "forecast": [
                    {
                        "condition": "rainy",
                        "datetime": "2026-06-21T00:00:00+08:00",
                        "temperature": 27.0,
                        "templow": 22.0,
                        "precipitation": 2.0,
                        "humidity": 78,
                        "wind_bearing": "东风",
                    }
                ]
            }
        }

    hass.services.async_register(
        "weather",
        "get_forecasts",
        get_forecasts,
        supports_response=SupportsResponse.ONLY,
    )

    context = await WeatherContextProvider(hass).async_get_forecast(
        location_hint="静安",
        forecast_type="daily",
    )

    assert context is not None
    assert calls == [{"entity_id": "weather.jingan", "type": "daily"}]
    assert context.forecasts.daily
    assert context.forecasts.daily[0].condition == "rainy"
    assert "weather_forecast:daily" in context.evidence

    speech = render_weather_context_answer(context, time_horizon="tomorrow")
    assert "静安明天天气" in speech
    assert "有雨" in speech
    assert "22 到 27 度" in speech
    assert "降水 2 毫米" in speech
