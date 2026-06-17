"""Constants for the LLM Gateway integration."""

from __future__ import annotations

import logging

DOMAIN = "llm_gateway"
LOGGER = logging.getLogger(__package__)

DEFAULT_NAME = "LLM Gateway"

# Connection (stored in entry.data).
CONF_BASE_URL = "base_url"
# CONF_API_KEY comes from homeassistant.const.
# Default points at NVIDIA NIM, an OpenAI-compatible endpoint with a free tier.
DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"

# Generation settings (stored in entry.options).
CONF_CHAT_MODEL = "chat_model"
CONF_MAX_TOKENS = "max_tokens"
CONF_TEMPERATURE = "temperature"
CONF_TOP_P = "top_p"
# CONF_PROMPT and CONF_LLM_HASS_API come from homeassistant.const.

RECOMMENDED_CHAT_MODEL = "qwen/qwen3-next-80b-a3b-instruct"
RECOMMENDED_MAX_TOKENS = 1024
RECOMMENDED_TEMPERATURE = 0.3
RECOMMENDED_TOP_P = 0.95

# Safety bound on tool-call round trips per user turn.
MAX_TOOL_ITERATIONS = 8

# Network timeouts (seconds).
TIMEOUT_MODELS = 15
TIMEOUT_CHAT = 60
