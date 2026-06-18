"""Tests for the Voice Harness panel."""

from __future__ import annotations

from homeassistant.components import frontend
from homeassistant.setup import async_setup_component

from custom_components.llm_gateway.const import (
    CONF_CHAT_MODEL,
    CONF_DIAGNOSTIC_TRACES,
    CONF_FAST_CHAT_TIMEOUT,
    CONF_FAST_MAX_TOKENS,
    CONF_FAST_MODEL,
    CONF_PROVIDER_PROFILES,
    CONF_TRACE_MAX_RUNS,
    ROUTING_MODE_MID,
)
from custom_components.llm_gateway.panel import (
    PANEL_MODULE,
    PANEL_TITLE,
    PANEL_URL,
    async_setup_panel,
)


async def test_panel_registers_sidebar_entry(hass):
    """Voice Harness is exposed as an admin-only custom panel."""
    assert await async_setup_component(hass, "http", {})

    await async_setup_panel(hass)

    panel = hass.data[frontend.DATA_PANELS][PANEL_URL]
    assert panel.sidebar_title == PANEL_TITLE
    assert panel.sidebar_icon == "mdi:microphone-message"
    assert panel.require_admin
    assert panel.config["_panel_custom"]["name"] == "voice-harness-panel"
    assert panel.config["_panel_custom"]["module_url"] == PANEL_MODULE
    assert panel.config["api_base"] == "/api/llm_gateway"


async def test_harness_status_api(hass, hass_client):
    """The panel status API returns sample scenarios."""
    assert await async_setup_component(hass, "http", {})
    hass.states.async_set(
        "binary_sensor.kukui_voice_paused",
        "off",
        {"friendly_name": "Kukui 语音暂停"},
    )
    hass.states.async_set(
        "input_number.kukui_voice_pause_minutes",
        "30",
        {"friendly_name": "Kukui 语音暂停分钟数", "unit_of_measurement": "min"},
    )
    await async_setup_panel(hass)
    client = await hass_client()

    response = await client.get("/api/llm_gateway/harness/status")

    assert response.status == 200
    data = await response.json()
    assert data["panel"]["url_path"] == PANEL_URL
    assert data["panel"]["title_i18n"]["zh-Hans"] == "语音测试台"
    assert data["panel"]["title_i18n"]["en"] == PANEL_TITLE
    assert data["earcons"]["pack"] == "ha_voice_minimal_v0"
    assert data["earcons"]["files"]["confirmation"]["url"].endswith("/confirmation.wav")
    assert data["earcons"]["files"]["processing_loop"]["url"].endswith(
        "/processing_loop.wav"
    )
    assert data["earcons"]["files"]["provider_fallback"]["url"].endswith(
        "/provider_fallback.wav"
    )
    assert data["prompt_policies"]
    assert any(policy["id"] == "latency_wait" for policy in data["prompt_policies"])
    assert data["sample_scenarios"]
    assert data["editable"]["routing_modes"]
    assert data["editable"]["max_tokens"]["max"] >= 16384
    assert data["satellite"]["states"]["voice_paused"]["state"] == "off"
    assert data["satellite"]["states"]["pause_minutes"]["unit"] == "min"
    assert (
        data["satellite"]["states"]["pause_requested"]["entity_id"]
        == "input_boolean.kukui_voice_pause_requested"
    )


async def test_harness_evaluate_api(hass, hass_client):
    """The ad hoc scenario API evaluates policy and spoken text."""
    assert await async_setup_component(hass, "http", {})
    await async_setup_panel(hass)
    client = await hass_client()

    response = await client.post(
        "/api/llm_gateway/harness/evaluate",
        json={
            "user": "打开前门门锁",
            "response": "要操作前门门锁吗？请确认。",
            "expected": {
                "must_search": False,
                "spoken_response": {
                    "max_sentences": 2,
                    "must_include": ["确认"],
                    "must_not_mention": ["entity_id"],
                },
            },
        },
    )

    assert response.status == 200
    data = await response.json()
    assert data["passed"]
    assert data["route"]["kind"] == "fast"
    assert not data["search"]["allowed"]
    assert data["spoken"] == "要操作前门门锁吗？请确认。"


async def test_harness_options_api_updates_safe_fields(
    hass, hass_client, mock_config_entry
):
    """The panel can update the safe editable subset of options."""
    assert await async_setup_component(hass, "http", {})
    mock_config_entry.add_to_hass(hass)
    await async_setup_panel(hass)
    client = await hass_client()

    response = await client.post(
        "/api/llm_gateway/harness/options",
        json={
            "entry_id": mock_config_entry.entry_id,
            "options": {
                "routing_mode": ROUTING_MODE_MID,
                "models": {
                    "fast": "fast-model",
                    "mid": "mid-model",
                    "deep": "deep-model",
                },
                "max_tokens": {"fast": 256, "mid": 1024, "deep": 4096},
                "timeouts": {"fast": 12, "mid": 45, "deep": 120},
                "trace": {
                    "enabled": True,
                    "include_raw_messages": False,
                    "max_runs": 40,
                    "retention_hours": 36,
                },
            },
        },
    )

    assert response.status == 200
    data = await response.json()
    assert data["entry"]["options"]["routing_mode"] == ROUTING_MODE_MID
    assert data["entry"]["options"]["models"]["fast"] == "fast-model"
    assert data["entry"]["trace"]["enabled"]
    assert mock_config_entry.options[CONF_FAST_MODEL] == "fast-model"
    assert mock_config_entry.options[CONF_CHAT_MODEL] == "fast-model"
    assert mock_config_entry.options[CONF_FAST_MAX_TOKENS] == 256
    assert mock_config_entry.options[CONF_FAST_CHAT_TIMEOUT] == 12
    assert mock_config_entry.options[CONF_DIAGNOSTIC_TRACES]
    assert mock_config_entry.options[CONF_TRACE_MAX_RUNS] == 40


async def test_harness_status_api_redacts_provider_profile_secrets(
    hass, hass_client, mock_config_entry
):
    """Provider fallback profiles are visible without API keys."""
    assert await async_setup_component(hass, "http", {})
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={
            **mock_config_entry.options,
            CONF_PROVIDER_PROFILES: (
                '{"providers":[{"name":"fallback","base_url":"https://fallback.test/v1",'
                '"api_key":"secret","models":{"fast":"fallback-fast"}}]}'
            ),
        },
    )
    await async_setup_panel(hass)
    client = await hass_client()

    response = await client.get("/api/llm_gateway/harness/status")

    assert response.status == 200
    data = await response.json()
    providers = data["entries"][0]["model_providers"]
    assert providers["fallback_enabled"]
    assert providers["fallbacks"][0]["name"] == "fallback"
    assert providers["fallbacks"][0]["has_api_key"] is True
    assert "api_key" not in providers["fallbacks"][0]


async def test_harness_options_api_rejects_invalid_values(
    hass, hass_client, mock_config_entry
):
    """The panel options API rejects out-of-range values."""
    assert await async_setup_component(hass, "http", {})
    mock_config_entry.add_to_hass(hass)
    await async_setup_panel(hass)
    client = await hass_client()

    response = await client.post(
        "/api/llm_gateway/harness/options",
        json={
            "entry_id": mock_config_entry.entry_id,
            "options": {"timeouts": {"fast": 1, "mid": 45, "deep": 120}},
        },
    )

    assert response.status == 400
    data = await response.json()
    assert data["code"] == "invalid_options"
