"""Room queries must follow the configured observation, not a device target."""

from datetime import timedelta

import pytest
from homeassistant.components.homeassistant import exposed_entities
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.llm_gateway.capabilities import decide_route
from custom_components.llm_gateway.dialogue import resolve_room_query_followup
from custom_components.llm_gateway.room_context import read_area_observation


def _room_sensor(
    hass, *, name="卧室", value="26.4", metric="temperature", attributes=None
):
    registry = ar.async_get(hass)
    area = registry.async_get_area_by_name(name) or registry.async_create(name)
    entity = er.async_get(hass).async_get_or_create(
        "sensor", "test", f"{name}-{metric}", original_device_class=metric
    )
    er.async_get(hass).async_update_entity(entity.entity_id, area_id=area.id)
    hass.states.async_set(
        entity.entity_id,
        value,
        {
            "device_class": metric,
            "unit_of_measurement": "°C" if metric == "temperature" else "%",
            **(attributes or {}),
        },
    )
    exposed_entities.async_expose_entity(
        hass, "conversation", entity.entity_id, should_expose=True
    )
    registry.async_update(area.id, **{f"{metric}_entity_id": entity.entity_id})
    return entity.entity_id


async def test_area_sensor_wins_over_ac_and_unrelated_sensor(hass):
    entity_id = _room_sensor(hass)
    hass.states.async_set(
        "climate.ac", "cool", {"current_temperature": 24.4, "temperature": 25}
    )
    hass.states.async_set("sensor.another", "30", {"friendly_name": "卧室温度"})
    text = "卧室现在多少度？"

    result = read_area_observation(hass, text, decide_route(text))

    assert result is not None
    assert result.answerable
    assert result.speech == "卧室现在 26.4 度。"
    assert result.entities[0].entity_id == entity_id
    assert result.source == "ha_area_sensor"
    hass.states.async_set(entity_id, "27")
    assert result.entities[0].state == "26.4"


async def test_home_summary_uses_the_same_designated_sources(hass):
    bedroom = _room_sensor(hass)
    living = _room_sensor(hass, name="客厅", value="unavailable")
    hass.states.async_set("sensor.earlier", "28.1", {"friendly_name": "客厅温度"})
    text = "家里温度是多少？"

    result = read_area_observation(hass, text, decide_route(text))

    assert result is not None
    assert "26.4" in result.speech
    assert "客厅温度当前不可用" in result.speech
    assert "28.1" not in result.speech
    assert not result.answerable
    assert {entity.entity_id for entity in result.entities} == {bedroom, living}


async def test_named_rooms_do_not_drop_a_room_without_a_designated_sensor(hass):
    _room_sensor(hass)
    ar.async_get(hass).async_create("厨房")
    text = "卧室和厨房现在多少度？"

    result = read_area_observation(hass, text, decide_route(text))

    assert result is not None
    assert not result.answerable
    assert "卧室现在 26.4 度" in result.speech
    assert "厨房温度当前不可用" in result.speech
    assert "temperature" in result.missing_requirements


@pytest.mark.parametrize("value", ["unavailable", "unknown", "nan", "inf"])
async def test_missing_primary_never_falls_back_to_ac(hass, value):
    _room_sensor(hass, value=value)
    hass.states.async_set("climate.ac", "cool", {"current_temperature": 24.4})
    text = "卧室温度是多少？"

    result = read_area_observation(hass, text, decide_route(text))

    assert result is not None
    assert not result.answerable
    assert "24.4" not in result.speech
    assert "不可用" in result.speech


async def test_expired_field_report_is_not_kept_alive_by_other_updates(hass):
    observed = dt_util.utcnow() - timedelta(minutes=10)
    _room_sensor(
        hass,
        attributes={"observed_at": observed.isoformat(), "observation_max_age_s": 300},
    )
    text = "卧室现在多少度？"

    result = read_area_observation(hass, text, decide_route(text))

    assert result is not None
    assert not result.answerable
    assert "26.4" not in result.speech
    assert result.outcome_reason == "observation_expired"


async def test_hidden_primary_is_not_read_or_replaced(hass):
    entity_id = _room_sensor(hass)
    exposed_entities.async_expose_entity(
        hass, "conversation", entity_id, should_expose=False
    )
    text = "卧室现在多少度？"

    result = read_area_observation(hass, text, decide_route(text))

    assert result is not None
    assert not result.answerable
    assert not result.entities
    assert "26.4" not in result.speech


async def test_explicit_device_query_keeps_its_own_temperature_source(hass):
    _room_sensor(hass)
    text = "卧室空调现在多少度？"

    assert read_area_observation(hass, text, decide_route(text)) is None


@pytest.mark.parametrize("text", ["卧室2现在多少度？", "次卧现在多少度？"])
async def test_numbered_room_and_alias_do_not_read_the_other_bedroom(hass, text):
    _room_sensor(hass)
    second = _room_sensor(hass, name="卧室 2", value="28.1")
    registry = ar.async_get(hass)
    area = registry.async_get_area_by_name("卧室 2")
    registry.async_update(area.id, aliases={"次卧"})

    result = read_area_observation(hass, text, decide_route(text))

    assert result is not None
    assert result.answerable
    assert result.entities[0].entity_id == second
    assert "28.1" in result.speech
    assert "26.4" not in result.speech


async def test_shared_room_alias_requests_clarification(hass):
    for name in ("卧室", "客厅"):
        _room_sensor(hass, name=name)
        registry = ar.async_get(hass)
        area = registry.async_get_area_by_name(name)
        registry.async_update(area.id, aliases={"房间"})
    text = "房间现在多少度？"

    result = read_area_observation(hass, text, decide_route(text))

    assert result is not None
    assert not result.answerable
    assert result.outcome_reason == "ambiguous_target"
    assert not result.entities


@pytest.mark.parametrize("humidity", ["61.2", "unavailable"])
async def test_combined_metrics_keep_both_designated_sources(hass, humidity):
    temperature_id = _room_sensor(hass)
    humidity_id = _room_sensor(hass, metric="humidity", value=humidity)
    text = "卧室温湿度多少？"

    result = read_area_observation(hass, text, decide_route(text))

    assert result is not None
    assert result.answerable is (humidity != "unavailable")
    assert set(result.metrics) == {"temperature", "humidity"}
    assert {entity.entity_id for entity in result.entities} == {
        temperature_id,
        humidity_id,
    }
    assert "26.4" in result.speech
    assert ("61.2" if humidity != "unavailable" else "湿度当前不可用") in result.speech


def test_followup_supports_registered_room_names_with_spaces():
    assert (
        resolve_room_query_followup(
            "那卧室2呢？", ["卧室现在多少度？"], area_names=("卧室 2",)
        )
        == "卧室 2温度是多少？"
    )


def test_followup_does_not_drop_a_metric_from_a_combined_question():
    text = "那客厅呢？"
    assert (
        resolve_room_query_followup(text, ["卧室温湿度多少？"])
        == "客厅温度和湿度是多少？"
    )


@pytest.mark.parametrize(
    ("history", "expected"),
    [
        (["卧室现在多少度？"], "客厅温度是多少？"),
        (["卧室湿度多少？"], "客厅湿度是多少？"),
        (["卧室现在多少度？", "那厨房呢？"], "客厅温度是多少？"),
        (["卧室现在多少度？", "讲个笑话"], "那客厅呢？"),
        (["打开卧室的灯"], "那客厅呢？"),
        (["卧室空调设定多少度？"], "那客厅呢？"),
        ([], "那客厅呢？"),
    ],
)
def test_room_followup_inherits_only_an_uninterrupted_room_read(history, expected):
    assert resolve_room_query_followup("那客厅呢？", history) == expected
