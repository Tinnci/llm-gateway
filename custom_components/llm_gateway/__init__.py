"""The LLM Gateway integration: an OpenAI-compatible conversation agent."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LLMGatewayAuthError, LLMGatewayClient, LLMGatewayError
from .const import CONF_BASE_URL, DEFAULT_BASE_URL, DOMAIN
from .feedback import VoiceFeedbackStore
from .first_response_audio import FirstResponsePlayer
from .memory import VoiceMemory
from .panel import async_setup_panel
from .providers import ProviderSelector
from .runtime import DeepTaskManager, LLMGatewayRuntimeData, TurnController
from .traces import TraceStore
from .voice_runs import VoiceRunRecorder

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.typing import ConfigType

    from .config_entry import LLMGatewayConfigEntry

PLATFORMS = [Platform.CONVERSATION]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


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
    feedback = VoiceFeedbackStore()
    first_response_player = FirstResponsePlayer(hass, feedback, lambda: entry.options)
    provider_selector = ProviderSelector()
    entry.runtime_data = LLMGatewayRuntimeData(
        client=client,
        session=session,
        memory=memory,
        trace_store=trace_store,
        feedback=feedback,
        first_response_player=first_response_player,
        provider_selector=provider_selector,
        voice_runs=VoiceRunRecorder(),
        turn_controller=TurnController(),
        deep_tasks=DeepTaskManager(
            hass,
            client,
            session,
            lambda: entry.options,
            provider_selector,
        ),
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
