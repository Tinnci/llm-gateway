"""Integration setup keeps local diagnostics available during provider outages."""

from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.llm_gateway import async_setup_entry
from custom_components.llm_gateway.api import LLMGatewayError
from custom_components.llm_gateway.const import DOMAIN


async def test_setup_keeps_local_runtime_available_offline(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"base_url": "https://example.invalid/v1", "api_key": "test"},
    )
    entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.llm_gateway.LLMGatewayClient.async_list_models",
            new_callable=AsyncMock,
        ) as discover,
        patch(
            "custom_components.llm_gateway.VoiceMemory.async_load",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.llm_gateway.TraceStore.async_load",
            new_callable=AsyncMock,
        ),
        patch.object(
            hass.config_entries, "async_forward_entry_setups", new_callable=AsyncMock
        ) as forward,
    ):
        discover.side_effect = LLMGatewayError("provider offline")
        assert await async_setup_entry(hass, entry)
        assert entry.runtime_data.trace_store is not None
        assert entry.runtime_data.provider_selector is not None
        forward.assert_awaited_once()
        discover.assert_not_awaited()
