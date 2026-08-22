"""Shared configuration helpers for the options flow and the panel API.

The HA options flow and the Voice Harness config API must validate and redact
identically, otherwise one UI drifts from the other. This module is the single
home for that shared behaviour.
"""

from __future__ import annotations

import json
from typing import Any

from .const import (
    CONF_BRAVE_API_KEY,
    CONF_DEEP_EXTRA_BODY,
    CONF_EXTRA_BODY,
    CONF_FAST_EXTRA_BODY,
    CONF_FIRECRAWL_API_KEY,
    CONF_MID_EXTRA_BODY,
    CONF_PROVIDER_PROFILES,
    CONF_SERPER_API_KEY,
    CONF_TAVILY_API_KEY,
)
from .providers import normalize_provider_profiles_json, parse_provider_profiles

# Options that contain or carry write-only secrets. GET responses never include
# their raw values; they are represented as has_<key> or as a redacted summary.
SECRET_OPTION_KEYS = {
    CONF_TAVILY_API_KEY,
    CONF_SERPER_API_KEY,
    CONF_FIRECRAWL_API_KEY,
    CONF_BRAVE_API_KEY,
    CONF_PROVIDER_PROFILES,
}

JSON_OPTION_FIELDS = (
    CONF_EXTRA_BODY,
    CONF_FAST_EXTRA_BODY,
    CONF_MID_EXTRA_BODY,
    CONF_DEEP_EXTRA_BODY,
)

OPTIONAL_SECRET_FIELDS = (
    CONF_TAVILY_API_KEY,
    CONF_SERPER_API_KEY,
    CONF_FIRECRAWL_API_KEY,
    CONF_BRAVE_API_KEY,
)


def normalize_json_option(
    user_input: dict[str, Any], errors: dict[str, str], field: str
) -> None:
    """Validate and compact one JSON text option in place."""
    raw = (user_input.get(field) or "").strip()
    if not raw:
        user_input.pop(field, None)
        return

    try:
        json.loads(raw)
    except ValueError:
        errors[field] = "invalid_json"
    else:
        user_input[field] = raw


def normalize_provider_profiles_option(
    user_input: dict[str, Any], errors: dict[str, str]
) -> None:
    """Validate and compact provider profiles JSON in place."""
    raw = (user_input.get(CONF_PROVIDER_PROFILES) or "").strip()
    if not raw:
        user_input.pop(CONF_PROVIDER_PROFILES, None)
        return

    try:
        user_input[CONF_PROVIDER_PROFILES] = normalize_provider_profiles_json(raw)
    except ValueError:
        errors[CONF_PROVIDER_PROFILES] = "invalid_provider_profiles"


def normalize_optional_secret(user_input: dict[str, Any], field: str) -> None:
    """Keep a non-empty secret, otherwise remove the key so it is unchanged."""
    value = (user_input.get(field) or "").strip()
    if value:
        user_input[field] = value
    else:
        user_input.pop(field, None)


def provider_profiles_summary(options: dict[str, Any]) -> list[dict[str, Any]]:
    """Return a safe summary of configured fallback providers."""
    raw = options.get(CONF_PROVIDER_PROFILES)
    if raw in (None, ""):
        return []
    try:
        profiles = parse_provider_profiles(raw)
    except ValueError:
        return [{"error": "invalid_provider_profiles"}]
    return [
        {
            "name": profile.name,
            "base_url": profile.base_url,
            "has_api_key": bool(profile.api_key),
            "models": dict(profile.models),
        }
        for profile in profiles
    ]


def redact_options(options: dict[str, Any]) -> dict[str, Any]:
    """Return a panel-safe copy of entry options.

    Non-secret fields are copied as-is. Secret fields become has_<key> booleans
    so the UI can show whether a value exists without ever receiving it.
    Provider profiles become a redacted summary list.
    """
    redacted: dict[str, Any] = {}
    for key, value in options.items():
        if key == CONF_PROVIDER_PROFILES:
            continue
        if key in SECRET_OPTION_KEYS:
            redacted[f"has_{key}"] = bool(str(value or "").strip())
            continue
        redacted[key] = value

    profiles = provider_profiles_summary(options)
    redacted["provider_profiles_configured"] = bool(profiles)
    redacted["provider_profiles"] = profiles
    return redacted
