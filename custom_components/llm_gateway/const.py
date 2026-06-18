"""Constants for the LLM Gateway integration."""

from __future__ import annotations

import logging

DOMAIN = "llm_gateway"
LOGGER = logging.getLogger(__package__)

DEFAULT_NAME = "LLM Gateway"

# Connection (stored in entry.data).
CONF_BASE_URL = "base_url"
# CONF_API_KEY comes from homeassistant.const.
DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"

# Generation settings (stored in entry.options).
CONF_CHAT_MODEL = "chat_model"
CONF_ROUTING_MODE = "routing_mode"
CONF_FAST_MODEL = "fast_model"
CONF_MID_MODEL = "mid_model"
CONF_DEEP_MODEL = "deep_model"
CONF_MAX_TOKENS = "max_tokens"
CONF_FAST_MAX_TOKENS = "fast_max_tokens"
CONF_MID_MAX_TOKENS = "mid_max_tokens"
CONF_DEEP_MAX_TOKENS = "deep_max_tokens"
CONF_TEMPERATURE = "temperature"
CONF_TOP_P = "top_p"
CONF_EXTRA_BODY = "extra_body"
CONF_FAST_EXTRA_BODY = "fast_extra_body"
CONF_MID_EXTRA_BODY = "mid_extra_body"
CONF_DEEP_EXTRA_BODY = "deep_extra_body"
CONF_CHAT_TIMEOUT = "chat_timeout"
CONF_FAST_CHAT_TIMEOUT = "fast_chat_timeout"
CONF_MID_CHAT_TIMEOUT = "mid_chat_timeout"
CONF_DEEP_CHAT_TIMEOUT = "deep_chat_timeout"
CONF_SEARCH_ENABLED = "search_enabled"
CONF_TAVILY_API_KEY = "tavily_api_key"
CONF_SERPER_API_KEY = "serper_api_key"
CONF_FIRECRAWL_API_KEY = "firecrawl_api_key"
CONF_BRAVE_API_KEY = "brave_api_key"
CONF_DIAGNOSTIC_TRACES = "diagnostic_traces"
CONF_TRACE_INCLUDE_RAW_MESSAGES = "trace_include_raw_messages"
CONF_TRACE_MAX_RUNS = "trace_max_runs"
CONF_TRACE_RETENTION_HOURS = "trace_retention_hours"
CONF_PROVIDER_PROFILES = "provider_profiles"
# CONF_PROMPT and CONF_LLM_HASS_API come from homeassistant.const.

ROUTING_MODE_AUTO = "auto"
ROUTING_MODE_FAST = "fast"
ROUTING_MODE_MID = "mid"
ROUTING_MODE_DEEP = "deep"
ROUTING_MODES = (
    ROUTING_MODE_AUTO,
    ROUTING_MODE_FAST,
    ROUTING_MODE_MID,
    ROUTING_MODE_DEEP,
)

RECOMMENDED_FAST_MODEL = "nvidia/nemotron-3-nano-30b-a3b"
RECOMMENDED_MID_MODEL = "nvidia/nemotron-3-nano-30b-a3b"
RECOMMENDED_DEEP_MODEL = "nvidia/nemotron-3-super-120b-a12b"
RECOMMENDED_DEEP_FALLBACK_MODEL = "nvidia/llama-3_3-nemotron-super-49b-v1"
RECOMMENDED_CHAT_MODEL = RECOMMENDED_FAST_MODEL
RECOMMENDED_MAX_TOKENS = 1024
RECOMMENDED_FAST_MAX_TOKENS = 512
RECOMMENDED_MID_MAX_TOKENS = 2048
RECOMMENDED_DEEP_MAX_TOKENS = 4096
RECOMMENDED_TEMPERATURE = 0.3
RECOMMENDED_TOP_P = 0.95
RECOMMENDED_CHAT_TIMEOUT = 60
RECOMMENDED_FAST_CHAT_TIMEOUT = 30
RECOMMENDED_MID_CHAT_TIMEOUT = 90
RECOMMENDED_DEEP_CHAT_TIMEOUT = 180
MAX_CONFIGURED_TOKENS = 16384
MAX_CHAT_TIMEOUT = 300
RECOMMENDED_TRACE_MAX_RUNS = 30
RECOMMENDED_TRACE_RETENTION_HOURS = 24
MAX_TRACE_RUNS = 200
MAX_TRACE_RETENTION_HOURS = 168

# Safety bound on tool-call round trips per user turn.
MAX_TOOL_ITERATIONS = 6

# Network timeouts (seconds).
TIMEOUT_MODELS = 15
TIMEOUT_CHAT = 30

GATEWAY_ERROR_SPEECH = "模型服务暂时没有响应，请稍后再试。"
TOOL_LOOP_ERROR_SPEECH = "设备操作没有完成，请换一种说法再试。"
DEEP_TASK_ACK_SPEECH = "我会继续分析，完成后发到 Home Assistant 通知里。"
