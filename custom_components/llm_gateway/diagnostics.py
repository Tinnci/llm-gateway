"""Diagnostics support for LLM Gateway."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.const import CONF_API_KEY, CONF_LLM_HASS_API, CONF_PROMPT
from homeassistant.helpers.redact import async_redact_data

from .const import (
    CONF_BASE_URL,
    CONF_BRAVE_API_KEY,
    CONF_FIRECRAWL_API_KEY,
    CONF_PROVIDER_PROFILES,
    CONF_SERPER_API_KEY,
    CONF_TAVILY_API_KEY,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .config_entry import LLMGatewayConfigEntry

_ENTRY_REDACT = {CONF_API_KEY, CONF_BASE_URL}
_OPTION_REDACT = {
    CONF_BRAVE_API_KEY,
    CONF_FIRECRAWL_API_KEY,
    CONF_LLM_HASS_API,
    CONF_PROMPT,
    CONF_PROVIDER_PROFILES,
    CONF_SERPER_API_KEY,
    CONF_TAVILY_API_KEY,
}


async def async_get_config_entry_diagnostics(
    _hass: HomeAssistant, entry: LLMGatewayConfigEntry
) -> dict[str, Any]:
    """Return a bounded, text-free diagnostic summary for one config entry."""
    runtime = entry.runtime_data
    trace_snapshot = runtime.trace_store.snapshot(include_raw=False)
    storage = trace_snapshot.get("storage") or {}
    provider_health = [
        {
            "provider": row.get("provider"),
            "route": row.get("route"),
            "failures": row.get("failures"),
            "cooldown_remaining_s": row.get("cooldown_remaining_s"),
        }
        for row in runtime.provider_selector.snapshot()
    ]
    return {
        "entry": async_redact_data(dict(entry.data), _ENTRY_REDACT),
        "options": async_redact_data(dict(entry.options), _OPTION_REDACT),
        "runtime": {
            "trace_records": int(storage.get("records") or 0),
            "trace_compressed_bytes": int(storage.get("compressed_bytes") or 0),
            "provider_health": provider_health,
            "active_turn": bool(runtime.turn_controller.current_turn_id),
            "recent_voice_runs": len(runtime.voice_runs.snapshot()),
        },
    }
