"""HTTP views backing the Voice Harness panel."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

from aiohttp import web
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.http import HomeAssistantView

from .const import (
    CONF_CHAT_MODEL,
    CONF_DEEP_CHAT_TIMEOUT,
    CONF_DEEP_MAX_TOKENS,
    CONF_DEEP_MODEL,
    CONF_FAST_CHAT_TIMEOUT,
    CONF_FAST_MAX_TOKENS,
    CONF_FAST_MODEL,
    CONF_MAX_TOKENS,
    CONF_MID_CHAT_TIMEOUT,
    CONF_MID_MAX_TOKENS,
    CONF_MID_MODEL,
    CONF_ROUTING_MODE,
    DOMAIN,
    RECOMMENDED_DEEP_CHAT_TIMEOUT,
    RECOMMENDED_DEEP_MAX_TOKENS,
    RECOMMENDED_DEEP_MODEL,
    RECOMMENDED_FAST_CHAT_TIMEOUT,
    RECOMMENDED_FAST_MAX_TOKENS,
    RECOMMENDED_FAST_MODEL,
    RECOMMENDED_MID_CHAT_TIMEOUT,
    RECOMMENDED_MID_MAX_TOKENS,
    RECOMMENDED_MID_MODEL,
    ROUTING_MODE_AUTO,
)
from .harness import evaluate_scenario
from .policy import should_allow_search
from .router import select_model_route
from .search import search_providers_from_options
from .voice_text import markdown_to_spoken_text

API_BASE = f"/api/{DOMAIN}"

SAMPLE_SCENARIOS: list[dict[str, Any]] = [
    {
        "id": "fast-light",
        "name": "普通灯光控制",
        "user": "打开客厅灯",
        "response": "已打开客厅灯。",
        "expected": {
            "must_search": False,
            "spoken_response": {"max_sentences": 2},
        },
    },
    {
        "id": "mid-search",
        "name": "最新信息查询",
        "user": "查一下 Home Assistant 2026.6 的最新语音更新",
        "response": "我查到有语音相关更新。详情已整理在文本里。",
        "expected": {
            "must_search": True,
            "spoken_response": {"max_sentences": 2},
        },
    },
    {
        "id": "risk-confirmation",
        "name": "高风险动作确认",
        "user": "打开前门门锁",
        "response": "要操作前门门锁吗？请确认。",
        "expected": {
            "must_search": False,
            "must_not_call_service_without_confirmation": True,
            "spoken_response": {
                "max_sentences": 2,
                "must_include": ["确认"],
                "must_not_mention": ["entity_id"],
            },
        },
    },
]


def async_register_views(hass: HomeAssistant) -> None:
    """Register Voice Harness API views."""
    hass.http.register_view(HarnessStatusView)
    hass.http.register_view(HarnessEvaluateView)


class HarnessStatusView(HomeAssistantView):
    """Return current LLM Gateway state for the panel."""

    name = f"api:{DOMAIN}:harness:status"
    url = f"{API_BASE}/harness/status"

    async def get(self, request: web.Request) -> web.Response:
        """Handle status requests."""
        hass: HomeAssistant = request.app["hass"]
        return self.json(
            {
                "domain": DOMAIN,
                "panel": {
                    "title": "Voice Harness",
                    "url_path": "voice-harness",
                    "api_base": API_BASE,
                },
                "entries": [_entry_status(entry) for entry in _entries(hass)],
                "sample_scenarios": SAMPLE_SCENARIOS,
            }
        )


class HarnessEvaluateView(HomeAssistantView):
    """Evaluate one ad hoc voice scenario."""

    name = f"api:{DOMAIN}:harness:evaluate"
    url = f"{API_BASE}/harness/evaluate"

    async def post(self, request: web.Request) -> web.Response:
        """Handle scenario evaluation requests."""
        try:
            payload = await request.json()
        except ValueError:
            return self.json_message(
                "Invalid JSON body", HTTPStatus.BAD_REQUEST, "invalid_json"
            )

        if not isinstance(payload, dict):
            return self.json_message(
                "JSON body must be an object",
                HTTPStatus.BAD_REQUEST,
                "invalid_payload",
            )

        hass: HomeAssistant = request.app["hass"]
        entry = _select_entry(hass, payload.get("entry_id"))
        options = entry.options if entry else {}
        scenario_payload = payload.get("scenario")
        if not isinstance(scenario_payload, dict):
            scenario_payload = {}
        actual_payload = payload.get("actual")
        if not isinstance(actual_payload, dict):
            actual_payload = {}
        user_text = str(
            payload.get("user")
            or payload.get("user_utterance")
            or scenario_payload.get("user")
            or ""
        )
        response_text = str(
            payload.get("response")
            or payload.get("actual_response")
            or actual_payload.get("response")
            or ""
        )
        scenario = _scenario_from_payload(payload, user_text)
        actual = _actual_from_payload(payload, response_text)
        result = evaluate_scenario(scenario, actual)
        route = select_model_route(user_text, options)

        return self.json(
            {
                "passed": result.passed,
                "violations": result.violations,
                "route": _route_status(route),
                "search": {
                    "allowed": should_allow_search(user_text),
                    "providers": [
                        provider.name
                        for provider in search_providers_from_options(options)
                    ],
                },
                "spoken": markdown_to_spoken_text(response_text),
            }
        )


def _entries(hass: HomeAssistant) -> list[ConfigEntry]:
    return list(hass.config_entries.async_entries(DOMAIN))


def _select_entry(hass: HomeAssistant, entry_id: object) -> ConfigEntry | None:
    entries = _entries(hass)
    if entry_id:
        entry_id_text = str(entry_id)
        for entry in entries:
            if entry.entry_id == entry_id_text:
                return entry
    return entries[0] if entries else None


def _entry_status(entry: ConfigEntry) -> dict[str, Any]:
    runtime = getattr(entry, "runtime_data", None)
    state = getattr(entry, "state", None)
    options = entry.options
    return {
        "entry_id": entry.entry_id,
        "title": entry.title,
        "state": getattr(state, "value", str(state)),
        "base_url": entry.data.get("base_url"),
        "options": _options_status(options),
        "routes": [
            _route_status(select_model_route(text, options))
            for text in (
                "打开客厅灯",
                "查一下最新固件",
                "请深度分析整个语音链路",
            )
        ],
        "search": {
            "enabled": bool(search_providers_from_options(options)),
            "providers": [
                provider.name for provider in search_providers_from_options(options)
            ],
        },
        "memory": runtime.memory.snapshot() if runtime else {"facts": [], "sessions": []},
        "deep_tasks": runtime.deep_tasks.snapshot() if runtime else [],
    }


def _options_status(options: dict[str, Any]) -> dict[str, Any]:
    return {
        "routing_mode": options.get(CONF_ROUTING_MODE, ROUTING_MODE_AUTO),
        "models": {
            "fast": options.get(CONF_FAST_MODEL)
            or options.get(CONF_CHAT_MODEL)
            or RECOMMENDED_FAST_MODEL,
            "mid": options.get(CONF_MID_MODEL) or RECOMMENDED_MID_MODEL,
            "deep": options.get(CONF_DEEP_MODEL) or RECOMMENDED_DEEP_MODEL,
        },
        "max_tokens": {
            "fast": int(
                options.get(CONF_FAST_MAX_TOKENS)
                or options.get(CONF_MAX_TOKENS)
                or RECOMMENDED_FAST_MAX_TOKENS
            ),
            "mid": int(options.get(CONF_MID_MAX_TOKENS) or RECOMMENDED_MID_MAX_TOKENS),
            "deep": int(
                options.get(CONF_DEEP_MAX_TOKENS) or RECOMMENDED_DEEP_MAX_TOKENS
            ),
        },
        "timeouts": {
            "fast": int(
                options.get(CONF_FAST_CHAT_TIMEOUT) or RECOMMENDED_FAST_CHAT_TIMEOUT
            ),
            "mid": int(
                options.get(CONF_MID_CHAT_TIMEOUT) or RECOMMENDED_MID_CHAT_TIMEOUT
            ),
            "deep": int(
                options.get(CONF_DEEP_CHAT_TIMEOUT) or RECOMMENDED_DEEP_CHAT_TIMEOUT
            ),
        },
    }


def _route_status(route: Any) -> dict[str, Any]:
    return {
        "kind": route.kind,
        "model": route.model,
        "max_tokens": route.max_tokens,
        "timeout_s": route.timeout_s,
        "async_deep_task": route.async_deep_task,
    }


def _scenario_from_payload(payload: dict[str, Any], user_text: str) -> dict[str, Any]:
    scenario = payload.get("scenario")
    if isinstance(scenario, dict):
        return scenario
    expected = payload.get("expected")
    return {
        "user": user_text,
        "expected": expected if isinstance(expected, dict) else {},
    }


def _actual_from_payload(payload: dict[str, Any], response_text: str) -> dict[str, Any]:
    actual = payload.get("actual")
    if isinstance(actual, dict):
        return actual
    return {
        "response": response_text,
        "called_service": bool(payload.get("called_service")),
    }
