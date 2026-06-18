"""The LLM Gateway integration: an OpenAI-compatible conversation agent."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LLMGatewayAuthError, LLMGatewayClient, LLMGatewayError
from .const import CONF_BASE_URL, DEFAULT_BASE_URL
from .memory import VoiceMemory
from .panel import async_setup_panel
from .runtime import DeepTaskManager, LLMGatewayRuntimeData
from .traces import TraceStore

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.typing import ConfigType

    from .config_entry import LLMGatewayConfigEntry

PLATFORMS = [Platform.CONVERSATION]


async def async_setup(hass: HomeAssistant, _config: ConfigType) -> bool:
    """Set up domain-level resources for LLM Gateway."""
    await async_setup_panel(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: LLMGatewayConfigEntry) -> bool:
    """Set up LLM Gateway from a config entry."""
    session = async_get_clientsession(hass)
    client = LLMGatewayClient(
        session,
        entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL),
        entry.data[CONF_API_KEY],
    )

    # Validate connectivity/credentials up front so the entry reflects reality.
    try:
        await client.async_list_models()
    except LLMGatewayAuthError as err:
        raise ConfigEntryNotReady(str(err)) from err
    except LLMGatewayError as err:
        raise ConfigEntryNotReady(str(err)) from err

    memory = VoiceMemory(hass, entry.entry_id)
    await memory.async_load()
    trace_store = TraceStore(hass, entry.entry_id)
    await trace_store.async_load()
    entry.runtime_data = LLMGatewayRuntimeData(
        client=client,
        session=session,
        memory=memory,
        deep_tasks=DeepTaskManager(hass, client),
        trace_store=trace_store,
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: LLMGatewayConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(
    hass: HomeAssistant, entry: LLMGatewayConfigEntry
) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)
