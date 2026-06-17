"""Shared fixtures for the LLM Gateway tests."""

from __future__ import annotations

import pytest
from homeassistant.const import CONF_API_KEY
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.llm_gateway.const import (
    CONF_BASE_URL,
    CONF_CHAT_MODEL,
    DEFAULT_BASE_URL,
    DOMAIN,
    RECOMMENDED_CHAT_MODEL,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom integrations in all tests."""
    return


@pytest.fixture(autouse=True)
async def setup_homeassistant_component(hass):
    """Set up the core integration so conversation's exposed-entities store exists."""
    assert await async_setup_component(hass, "homeassistant", {})


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a configured (but not yet set up) entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="LLM Gateway",
        data={CONF_BASE_URL: DEFAULT_BASE_URL, CONF_API_KEY: "test-key"},
        options={CONF_CHAT_MODEL: RECOMMENDED_CHAT_MODEL},
    )
