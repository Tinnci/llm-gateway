"""Compare HA tool names without rewriting the names sent to its API."""

from __future__ import annotations


def canonical_ha_tool_name(name: str) -> str:
    """Recognize only the two built-in HA namespaces used by our policy.

    Other integration namespaces remain distinct, even when their suffix
    resembles a Home Assistant tool. Actual API calls retain the original name.
    """
    if name == "homeassistant__GetLiveContext":
        return "GetLiveContext"
    if name.startswith("intent__Hass"):
        return name.removeprefix("intent__")
    return name
