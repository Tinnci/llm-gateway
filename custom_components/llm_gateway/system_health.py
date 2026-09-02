"""System health support for LLM Gateway."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.core import callback

if TYPE_CHECKING:
    from homeassistant.components import system_health
    from homeassistant.core import HomeAssistant

from .const import DOMAIN


@callback
def async_register(
    _hass: HomeAssistant, register: system_health.SystemHealthRegistration
) -> None:
    """Register LLM Gateway system-health information."""
    register.async_register_info(system_health_info)


async def system_health_info(hass: HomeAssistant) -> dict[str, Any]:
    """Return lightweight health information without provider secrets."""
    entries = hass.config_entries.async_entries(DOMAIN)
    loaded = [entry for entry in entries if entry.runtime_data is not None]
    provider_health = [
        row
        for entry in loaded
        for row in entry.runtime_data.provider_selector.snapshot()
    ]
    return {
        "configured_entries": len(entries),
        "loaded_entries": len(loaded),
        "provider_failures": sum(
            int(row.get("failures") or 0) for row in provider_health
        ),
        "providers_in_cooldown": sum(
            int(row.get("cooldown_remaining_s") or 0) > 0 for row in provider_health
        ),
        "diagnostic_traces_enabled": any(
            bool(entry.options.get("diagnostic_traces")) for entry in entries
        ),
    }
