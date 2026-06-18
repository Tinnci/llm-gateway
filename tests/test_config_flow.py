"""Tests for the config and options flows."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_API_KEY
from homeassistant.data_entry_flow import FlowResultType

from custom_components.llm_gateway.const import (
    CONF_BASE_URL,
    CONF_CHAT_TIMEOUT,
    CONF_DEEP_CHAT_TIMEOUT,
    CONF_DEEP_MAX_TOKENS,
    CONF_DEEP_MODEL,
    CONF_DIAGNOSTIC_TRACES,
    CONF_EXTRA_BODY,
    CONF_FAST_MODEL,
    CONF_MAX_TOKENS,
    CONF_MID_MODEL,
    CONF_ROUTING_MODE,
    CONF_SEARCH_ENABLED,
    CONF_TEMPERATURE,
    CONF_TOP_P,
    CONF_TRACE_INCLUDE_RAW_MESSAGES,
    CONF_TRACE_MAX_RUNS,
    CONF_TRACE_RETENTION_HOURS,
    DEFAULT_BASE_URL,
    DOMAIN,
    ROUTING_MODE_AUTO,
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
            CONF_ROUTING_MODE: ROUTING_MODE_AUTO,
            CONF_FAST_MODEL: "m2",
            CONF_MID_MODEL: "m1",
            CONF_DEEP_MODEL: "m2",
            CONF_EXTRA_BODY: '{"reasoning_budget": 16384}',
            CONF_MAX_TOKENS: 16384,
            CONF_DEEP_MAX_TOKENS: 16384,
            CONF_TEMPERATURE: 1,
            CONF_TOP_P: 0.9,
            CONF_CHAT_TIMEOUT: 180,
            CONF_DEEP_CHAT_TIMEOUT: 180,
            CONF_SEARCH_ENABLED: True,
            CONF_DIAGNOSTIC_TRACES: True,
            CONF_TRACE_INCLUDE_RAW_MESSAGES: True,
            CONF_TRACE_MAX_RUNS: 20,
            CONF_TRACE_RETENTION_HOURS: 12,
        },
    )
    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"][CONF_FAST_MODEL] == "m2"
    assert result2["data"][CONF_MAX_TOKENS] == 16384
    assert result2["data"][CONF_DEEP_MAX_TOKENS] == 16384
    assert result2["data"][CONF_EXTRA_BODY] == '{"reasoning_budget": 16384}'
    assert result2["data"][CONF_CHAT_TIMEOUT] == 180
    assert result2["data"][CONF_DIAGNOSTIC_TRACES]
    assert result2["data"][CONF_TRACE_INCLUDE_RAW_MESSAGES]
    assert result2["data"][CONF_TRACE_MAX_RUNS] == 20
    assert result2["data"][CONF_TRACE_RETENTION_HOURS] == 12


async def test_options_flow_rejects_invalid_extra_body(
    hass, aioclient_mock, mock_config_entry
):
    aioclient_mock.get(MODELS_URL, json={"data": [{"id": "m1"}]})
    mock_config_entry.add_to_hass(hass)
    with patch("custom_components.llm_gateway.async_setup_entry", return_value=True):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_FAST_MODEL: "m1",
            CONF_MID_MODEL: "m1",
            CONF_DEEP_MODEL: "m1",
            CONF_EXTRA_BODY: "not-json",
            CONF_MAX_TOKENS: 1024,
            CONF_TEMPERATURE: 0.3,
            CONF_TOP_P: 0.95,
            CONF_CHAT_TIMEOUT: 60,
        },
    )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {CONF_EXTRA_BODY: "invalid_json"}
