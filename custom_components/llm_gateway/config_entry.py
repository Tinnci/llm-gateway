"""Typed config entry for the LLM Gateway integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry

from .runtime import LLMGatewayRuntimeData

type LLMGatewayConfigEntry = ConfigEntry[LLMGatewayRuntimeData]
