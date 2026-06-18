"""Voice Harness panel registration for LLM Gateway."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig

from .const import DOMAIN
from .views import async_register_views

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

URL_BASE = f"/api/{DOMAIN}/static"
PANEL_URL = "voice-harness"
PANEL_COMPONENT = "voice-harness-panel"
PANEL_MODULE_VERSION = "0.3.8"
PANEL_MODULE = f"{URL_BASE}/voice-harness-panel.js?v={PANEL_MODULE_VERSION}"
PANEL_TITLE = "Voice Harness"
DATA_PANEL_SETUP = f"{DOMAIN}_voice_harness_panel_setup"


async def async_setup_panel(hass: HomeAssistant) -> None:
    """Register the admin-only Voice Harness sidebar panel."""
    if hass.data.get(DATA_PANEL_SETUP):
        return
    hass.data[DATA_PANEL_SETUP] = True
    frontend_path = Path(__file__).parent / "frontend"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(URL_BASE, str(frontend_path), cache_headers=True)]
    )
    async_register_views(hass)
    frontend.async_register_built_in_panel(
        hass,
        component_name="custom",
        sidebar_title=PANEL_TITLE,
        sidebar_icon="mdi:microphone-message",
        frontend_url_path=PANEL_URL,
        config={
            "_panel_custom": {
                "name": PANEL_COMPONENT,
                "module_url": PANEL_MODULE,
            },
            "api_base": f"/api/{DOMAIN}",
        },
        require_admin=True,
        update=True,
        config_panel_domain=DOMAIN,
    )
