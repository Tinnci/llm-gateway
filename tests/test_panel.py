"""Tests for the Voice Harness panel."""

from __future__ import annotations

from homeassistant.components import frontend
from homeassistant.setup import async_setup_component

from custom_components.llm_gateway.panel import (
    PANEL_MODULE,
    PANEL_URL,
    async_setup_panel,
)


async def test_panel_registers_sidebar_entry(hass):
    """Voice Harness is exposed as an admin-only custom panel."""
    assert await async_setup_component(hass, "http", {})

    await async_setup_panel(hass)

    panel = hass.data[frontend.DATA_PANELS][PANEL_URL]
    assert panel.sidebar_title == "语音测试台"
    assert panel.sidebar_icon == "mdi:microphone-message"
    assert panel.require_admin
    assert panel.config["_panel_custom"]["name"] == "voice-harness-panel"
    assert panel.config["_panel_custom"]["module_url"] == PANEL_MODULE
    assert panel.config["api_base"] == "/api/llm_gateway"


async def test_harness_status_api(hass, hass_client):
    """The panel status API returns sample scenarios."""
    assert await async_setup_component(hass, "http", {})
    await async_setup_panel(hass)
    client = await hass_client()

    response = await client.get("/api/llm_gateway/harness/status")

    assert response.status == 200
    data = await response.json()
    assert data["panel"]["url_path"] == PANEL_URL
    assert data["earcons"]["pack"] == "ha_voice_minimal_v0"
    assert data["earcons"]["files"]["confirmation"]["url"].endswith("/confirmation.wav")
    assert data["prompt_policies"]
    assert data["sample_scenarios"]


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
