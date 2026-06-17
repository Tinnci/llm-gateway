"""Tests for the config and options flows."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_API_KEY
from homeassistant.data_entry_flow import FlowResultType

from custom_components.llm_gateway.const import (
    CONF_BASE_URL,
    CONF_CHAT_MODEL,
    CONF_MAX_TOKENS,
    CONF_TEMPERATURE,
    CONF_TOP_P,
    DEFAULT_BASE_URL,
    DOMAIN,
)

MODELS_URL = f"{DEFAULT_BASE_URL}/models"


async def test_user_flow_success(hass, aioclient_mock):
    aioclient_mock.get(MODELS_URL, json={"data": [{"id": "m"}]})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM

    with patch("custom_components.llm_gateway.async_setup_entry", return_value=True):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_BASE_URL: DEFAULT_BASE_URL, CONF_API_KEY: "k"},
        )
    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"][CONF_API_KEY] == "k"


async def test_user_flow_invalid_auth(hass, aioclient_mock):
    aioclient_mock.get(MODELS_URL, status=401)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_BASE_URL: DEFAULT_BASE_URL, CONF_API_KEY: "bad"},
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_user_flow_cannot_connect(hass, aioclient_mock):
    aioclient_mock.get(MODELS_URL, status=500)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_BASE_URL: DEFAULT_BASE_URL, CONF_API_KEY: "k"},
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_options_flow(hass, aioclient_mock, mock_config_entry):
    aioclient_mock.get(MODELS_URL, json={"data": [{"id": "m1"}, {"id": "m2"}]})
    mock_config_entry.add_to_hass(hass)
    with patch("custom_components.llm_gateway.async_setup_entry", return_value=True):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] == FlowResultType.FORM

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_CHAT_MODEL: "m2",
            CONF_MAX_TOKENS: 512,
            CONF_TEMPERATURE: 0.2,
            CONF_TOP_P: 0.9,
        },
    )
    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"][CONF_CHAT_MODEL] == "m2"
