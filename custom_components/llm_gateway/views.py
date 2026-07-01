"""HTTP views backing the Voice Harness panel."""

from __future__ import annotations

import json
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Any

from homeassistant.components.http.decorators import require_admin
from homeassistant.helpers.http import HomeAssistantView
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CHAT_MODEL,
    CONF_DEEP_CHAT_TIMEOUT,
    CONF_DEEP_MAX_TOKENS,
    CONF_DEEP_MODEL,
    CONF_DIAGNOSTIC_TRACES,
    CONF_FAST_CHAT_TIMEOUT,
    CONF_FAST_MAX_TOKENS,
    CONF_FAST_MODEL,
    CONF_FIRST_RESPONSE_AUDIO_ENABLED,
    CONF_FIRST_RESPONSE_LOCAL_SERVICE,
    CONF_FIRST_RESPONSE_MEDIA_PLAYER,
    CONF_FIRST_RESPONSE_PLAYBACK_ADAPTER,
    CONF_FIRST_RESPONSE_TTS_ENTITY,
    CONF_MAX_TOKENS,
    CONF_MID_CHAT_TIMEOUT,
    CONF_MID_MAX_TOKENS,
    CONF_MID_MODEL,
    CONF_PROVIDER_PROFILES,
    CONF_ROUTING_MODE,
    CONF_TRACE_INCLUDE_RAW_MESSAGES,
    CONF_TRACE_MAX_RUNS,
    CONF_TRACE_RETENTION_HOURS,
    DOMAIN,
    FIRST_RESPONSE_PLAYBACK_ADAPTERS,
    MAX_CHAT_TIMEOUT,
    MAX_CONFIGURED_TOKENS,
    MAX_TRACE_RETENTION_HOURS,
    MAX_TRACE_RUNS,
    RECOMMENDED_DEEP_CHAT_TIMEOUT,
    RECOMMENDED_DEEP_MAX_TOKENS,
    RECOMMENDED_DEEP_MODEL,
    RECOMMENDED_FAST_CHAT_TIMEOUT,
    RECOMMENDED_FAST_MAX_TOKENS,
    RECOMMENDED_FAST_MODEL,
    RECOMMENDED_MID_CHAT_TIMEOUT,
    RECOMMENDED_MID_MAX_TOKENS,
    RECOMMENDED_MID_MODEL,
    RECOMMENDED_TRACE_MAX_RUNS,
    RECOMMENDED_TRACE_RETENTION_HOURS,
    ROUTING_MODE_AUTO,
    ROUTING_MODES,
)
from .feedback import QUIET_HOURS_END, QUIET_HOURS_START
from .first_response_audio import first_response_audio_status
from .harness import evaluate_scenario
from .policy import should_allow_search
from .providers import normalize_provider_profiles_json, provider_profiles_from_options
from .router import select_model_route
from .satellite_diagnostics import satellite_diagnostic_snapshot
from .search import search_providers_from_options
from .voice_text import markdown_to_spoken_text

if TYPE_CHECKING:
    from aiohttp import web
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .router import ModelRoute

API_BASE = f"/api/{DOMAIN}"
STATIC_BASE = f"{API_BASE}/static"
EARCON_PACK = "ha_voice_minimal_v0"
MAX_MODEL_ID_LENGTH = 256
EARCON_MANIFEST = (
    Path(__file__).parent / "frontend" / "earcons" / EARCON_PACK / "manifest.json"
)

PROMPT_POLICIES: list[dict[str, Any]] = [
    {
        "id": "low_risk_success",
        "title": "低风险成功",
        "title_i18n": {"en": "Low-risk success", "zh-Hans": "低风险成功"},
        "risk": "low",
        "spoken": "好了。",
        "spoken_i18n": {"en": "Done.", "zh-Hans": "好了。"},
        "rules": ["max_one_sentence", "no_tool_details", "no_entity_id"],
    },
    {
        "id": "state_query",
        "title": "状态查询",
        "title_i18n": {"en": "State query", "zh-Hans": "状态查询"},
        "risk": "low",
        "spoken": "先回答结论，不展开长解释。",
        "spoken_i18n": {
            "en": "Answer the conclusion first without long explanation.",
            "zh-Hans": "先回答结论，不展开长解释。",
        },
        "rules": ["answer_first", "no_long_list", "no_url"],
    },
    {
        "id": "clarification",
        "title": "最小澄清",
        "title_i18n": {"en": "Minimal clarification", "zh-Hans": "最小澄清"},
        "risk": "medium",
        "spoken": "一次只问一个最小澄清问题。",
        "spoken_i18n": {
            "en": "Ask only one minimal clarification question.",
            "zh-Hans": "一次只问一个最小澄清问题。",
        },
        "rules": ["one_question", "no_action_before_clarity"],
    },
    {
        "id": "high_risk_confirmation",
        "title": "高风险确认",
        "title_i18n": {"en": "High-risk confirmation", "zh-Hans": "高风险确认"},
        "risk": "high",
        "spoken": "要操作{target}吗？请确认。",
        "spoken_i18n": {
            "en": "Do you want to operate {target}? Please confirm.",
            "zh-Hans": "要操作{target}吗？请确认。",
        },
        "rules": ["must_confirm", "name_target", "no_action_before_confirmation"],
    },
    {
        "id": "search_summary",
        "title": "搜索摘要",
        "title_i18n": {"en": "Search summary", "zh-Hans": "搜索摘要"},
        "risk": "medium",
        "spoken": "先说结论，来源和长列表放到屏幕。",
        "spoken_i18n": {
            "en": "Say the conclusion first; put sources and long lists on screen.",
            "zh-Hans": "先说结论，来源和长列表放到屏幕。",
        },
        "rules": ["external_facts_only", "cite_in_panel", "short_tts"],
    },
    {
        "id": "latency_wait",
        "title": "长延迟等待提示",
        "title_i18n": {"en": "Long-latency wait", "zh-Hans": "长延迟等待提示"},
        "risk": "low",
        "spoken": "还在查询，请稍等。",
        "spoken_i18n": {
            "en": "Still checking. Please wait.",
            "zh-Hans": "还在查询，请稍等。",
        },
        "rules": [
            "local_clip_preferred",
            "do_not_repeat",
            "do_not_extend_dialog",
            "stop_when_final_tts_starts",
        ],
    },
    {
        "id": "error_repair",
        "title": "错误修复",
        "title_i18n": {"en": "Error repair", "zh-Hans": "错误修复"},
        "risk": "medium",
        "spoken": "说明下一步，而不是只说没听懂。",
        "spoken_i18n": {
            "en": "Give the next step instead of only saying you did not understand.",
            "zh-Hans": "说明下一步，而不是只说没听懂。",
        },
        "rules": ["actionable_repair", "no_blame", "one_next_step"],
    },
    {
        "id": "deep_task",
        "title": "深度任务",
        "title_i18n": {"en": "Deep task", "zh-Hans": "深度任务"},
        "risk": "low",
        "spoken": "我会继续分析，完成后发到 Home Assistant 通知里。",
        "spoken_i18n": {
            "en": (
                "I will keep analyzing and send the result to Home Assistant "
                "notifications."
            ),
            "zh-Hans": "我会继续分析，完成后发到 Home Assistant 通知里。",
        },
        "rules": ["non_blocking_voice", "no_direct_ha_action"],
    },
]

SAMPLE_SCENARIOS: list[dict[str, Any]] = [
    {
        "id": "fast-light",
        "name": "普通灯光控制",
        "name_i18n": {"en": "Basic light control", "zh-Hans": "普通灯光控制"},
        "user": "打开客厅灯",
        "user_i18n": {
            "en": "Turn on the living room light",
            "zh-Hans": "打开客厅灯",
        },
        "response": "已打开客厅灯。",
        "response_i18n": {
            "en": "Living room light is on.",
            "zh-Hans": "已打开客厅灯。",
        },
        "expected": {
            "must_search": False,
            "route_decision": {
                "task_family": "home_control",
                "requires_llm": False,
                "next_action": "execute_local",
                "route": "local_action",
            },
            "spoken_response": {"max_sentences": 2},
        },
    },
    {
        "id": "mid-search",
        "name": "最新信息查询",
        "name_i18n": {"en": "Fresh information query", "zh-Hans": "最新信息查询"},
        "user": "查一下 Home Assistant 2026.6 的最新语音更新",
        "user_i18n": {
            "en": "Look up the latest Home Assistant 2026.6 voice updates",
            "zh-Hans": "查一下 Home Assistant 2026.6 的最新语音更新",
        },
        "response": "我查到有语音相关更新。详情已整理在文本里。",
        "response_i18n": {
            "en": "I found voice-related updates. Details are in the text view.",
            "zh-Hans": "我查到有语音相关更新。详情已整理在文本里。",
        },
        "expected": {
            "must_search": True,
            "route_decision": {
                "task_family": "external_current_info",
                "requires_llm": True,
                "next_action": "search",
            },
            "spoken_response": {"max_sentences": 2},
        },
    },
    {
        "id": "risk-confirmation",
        "name": "高风险动作确认",
        "name_i18n": {
            "en": "High-risk action confirmation",
            "zh-Hans": "高风险动作确认",
        },
        "user": "打开前门门锁",
        "user_i18n": {
            "en": "Unlock the front door",
            "zh-Hans": "打开前门门锁",
        },
        "response": "要操作前门门锁吗？请确认。",
        "response_i18n": {
            "en": "Do you want to unlock the front door? Please confirm.",
            "zh-Hans": "要操作前门门锁吗？请确认。",
        },
        "expected": {
            "must_search": False,
            "must_not_call_service_without_confirmation": True,
            "route_decision": {
                "task_family": "home_control",
                "requires_user_confirmation": True,
                "next_action": "ask_confirmation",
            },
            "spoken_response": {
                "max_sentences": 2,
                "must_include": ["确认"],
                "must_not_mention": ["entity_id"],
            },
        },
        "expected_i18n": {
            "en": {
                "must_search": False,
                "must_not_call_service_without_confirmation": True,
                "spoken_response": {
                    "max_sentences": 2,
                    "must_include": ["confirm"],
                    "must_not_mention": ["entity_id"],
                },
            },
            "zh-Hans": {
                "must_search": False,
                "must_not_call_service_without_confirmation": True,
                "spoken_response": {
                    "max_sentences": 2,
                    "must_include": ["确认"],
                    "must_not_mention": ["entity_id"],
                },
            },
        },
    },
    {
        "id": "local-home-state",
        "name": "本地状态查询",
        "name_i18n": {"en": "Local state query", "zh-Hans": "本地状态查询"},
        "user": "当前客厅的温度是多少？",
        "response": "客厅现在 27.8 度。",
        "expected": {
            "must_search": False,
            "route_decision": {
                "task_family": "home_state",
                "requires_llm": False,
                "next_action": "call_tool_then_local_render",
                "route": "local_live_context",
            },
            "spoken_response": {
                "max_sentences": 1,
                "must_not_mention": ["已暴露给助手", "GetLiveContext", "policy"],
            },
        },
    },
    {
        "id": "stable-literary-knowledge",
        "name": "文学常识",
        "name_i18n": {"en": "Literary knowledge", "zh-Hans": "文学常识"},
        "user": "张若虚有什么样的诗？",
        "response": "张若虚以《春江花月夜》最有代表性。",
        "expected": {
            "must_search": False,
            "route_decision": {
                "task_family": "stable_knowledge",
                "requires_llm": True,
                "next_action": "answer_with_llm",
            },
            "spoken_response": {"max_sentences": 2},
        },
    },
    {
        "id": "nearby-place-missing-location",
        "name": "附近地点缺位置",
        "name_i18n": {
            "en": "Nearby place without location",
            "zh-Hans": "附近地点缺位置",
        },
        "user": "附近最近的麦当劳在哪里？",
        "response": "我需要知道你的位置才能查附近地点。要使用当前位置吗？",
        "expected": {
            "must_search": False,
            "route_decision": {
                "task_family": "location_dependent_query",
                "requires_location": True,
                "requires_llm": False,
                "next_action": "ask_location_permission",
            },
            "spoken_response": {"max_questions": 1},
        },
    },
    {
        "id": "assistant-volume-local",
        "name": "助手音量本地控制",
        "name_i18n": {
            "en": "Assistant volume local control",
            "zh-Hans": "助手音量本地控制",
        },
        "user": "把自己的音量调到最大",
        "response": "我说话的音量已调整。",
        "expected": {
            "must_search": False,
            "route_decision": {
                "task_family": "volume_control",
                "requires_llm": False,
                "next_action": "execute_local",
                "route": "local_action",
            },
            "spoken_response": {"max_sentences": 1},
        },
    },
    {
        "id": "media-volume-local",
        "name": "媒体音量本地控制",
        "name_i18n": {
            "en": "Media volume local control",
            "zh-Hans": "媒体音量本地控制",
        },
        "user": "把客厅音箱音量调到最大",
        "response": "已把客厅音箱音量调到最大。",
        "expected": {
            "must_search": False,
            "route_decision": {
                "task_family": "volume_control",
                "requires_llm": False,
                "next_action": "execute_local",
                "route": "local_action",
            },
            "spoken_response": {"max_sentences": 1},
        },
    },
]


def async_register_views(hass: HomeAssistant) -> None:
    """Register Voice Harness API views."""
    hass.http.register_view(HarnessStatusView)
    hass.http.register_view(HarnessRunsView)
    hass.http.register_view(HarnessRunDetailView)
    hass.http.register_view(HarnessEvaluateView)
    hass.http.register_view(HarnessOptionsView)


class HarnessStatusView(HomeAssistantView):
    """Return current LLM Gateway state for the panel."""

    name = f"api:{DOMAIN}:harness:status"
    url = f"{API_BASE}/harness/status"

    @require_admin
    async def get(self, request: web.Request) -> web.Response:
        """Handle status requests."""
        hass: HomeAssistant = request.app["hass"]
        return self.json(
            {
                "domain": DOMAIN,
                "panel": {
                    "title": "Voice Harness",
                    "title_i18n": {
                        "en": "Voice Harness",
                        "zh-Hans": "语音测试台",
                    },
                    "url_path": "voice-harness",
                    "api_base": API_BASE,
                },
                "entries": [_entry_status(hass, entry) for entry in _entries(hass)],
                "satellite": _satellite_status(hass),
                "editable": _editable_schema(),
                "earcons": await hass.async_add_executor_job(_earcon_pack_status),
                "prompt_policies": PROMPT_POLICIES,
                "sample_scenarios": SAMPLE_SCENARIOS,
            }
        )


class HarnessRunsView(HomeAssistantView):
    """Return recent Voice Harness runs."""

    name = f"api:{DOMAIN}:harness:runs"
    url = f"{API_BASE}/harness/runs"

    @require_admin
    async def get(self, request: web.Request) -> web.Response:
        """Handle recent run list requests."""
        hass: HomeAssistant = request.app["hass"]
        entry = _select_entry(hass, request.query.get("entry_id"))
        if entry is None:
            return self.json_message(
                "No LLM Gateway config entry found",
                HTTPStatus.NOT_FOUND,
                "entry_not_found",
            )
        runtime = getattr(entry, "runtime_data", None)
        if runtime is None:
            return self.json({"records": []})
        limit = _bounded_query_int(request.query.get("limit"), default=30, maximum=200)
        return self.json({"records": runtime.trace_store.list_runs(limit=limit)})


class HarnessRunDetailView(HomeAssistantView):
    """Return one Voice Harness run detail."""

    name = f"api:{DOMAIN}:harness:run_detail"
    url = f"{API_BASE}/harness/runs/{{run_id}}"

    @require_admin
    async def get(self, request: web.Request, run_id: str) -> web.Response:
        """Handle run detail requests."""
        hass: HomeAssistant = request.app["hass"]
        entry = _select_entry(hass, request.query.get("entry_id"))
        if entry is None:
            return self.json_message(
                "No LLM Gateway config entry found",
                HTTPStatus.NOT_FOUND,
                "entry_not_found",
            )
        runtime = getattr(entry, "runtime_data", None)
        record = runtime.trace_store.get_run(run_id) if runtime else None
        if record is None:
            return self.json_message(
                "Voice run not found",
                HTTPStatus.NOT_FOUND,
                "run_not_found",
            )
        return self.json({"record": record})


class HarnessEvaluateView(HomeAssistantView):
    """Evaluate one ad hoc voice scenario."""

    name = f"api:{DOMAIN}:harness:evaluate"
    url = f"{API_BASE}/harness/evaluate"

    @require_admin
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


class HarnessOptionsView(HomeAssistantView):
    """Update a safe subset of config entry options from the panel."""

    name = f"api:{DOMAIN}:harness:options"
    url = f"{API_BASE}/harness/options"

    @require_admin
    async def post(self, request: web.Request) -> web.Response:
        """Handle safe option updates."""
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
        if entry is None:
            return self.json_message(
                "No LLM Gateway config entry found",
                HTTPStatus.NOT_FOUND,
                "entry_not_found",
            )

        options_payload = payload.get("options")
        if not isinstance(options_payload, dict):
            return self.json_message(
                "options must be an object",
                HTTPStatus.BAD_REQUEST,
                "invalid_options",
            )

        try:
            updates = _validate_editable_options(options_payload)
        except ValueError as err:
            return self.json_message(
                str(err), HTTPStatus.BAD_REQUEST, "invalid_options"
            )

        new_options = dict(entry.options)
        new_options.update(updates)
        if updates.get(CONF_FAST_MODEL):
            new_options[CONF_CHAT_MODEL] = updates[CONF_FAST_MODEL]
        hass.config_entries.async_update_entry(entry, options=new_options)

        return self.json({"entry": _entry_status(hass, entry)})


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


def _bounded_query_int(value: object, *, default: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(maximum, parsed))


def _entry_status(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    runtime = getattr(entry, "runtime_data", None)
    feedback = getattr(runtime, "feedback", None) if runtime else None
    state = getattr(entry, "state", None)
    options = entry.options
    return {
        "entry_id": entry.entry_id,
        "title": entry.title,
        "state": getattr(state, "value", str(state)),
        "base_url": entry.data.get("base_url"),
        "options": _options_status(options),
        "first_response_audio": first_response_audio_status(hass, options),
        "feedback_policy": _feedback_policy_status(),
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
        "model_providers": _model_provider_status(entry),
        "provider_health": (runtime.provider_selector.snapshot() if runtime else []),
        "memory": (
            runtime.memory.snapshot() if runtime else {"facts": [], "sessions": []}
        ),
        "trace": _trace_status(options),
        "traces": (
            runtime.trace_store.snapshot()
            if runtime
            else {"records": [], "storage": {"encoding": "json+zlib+base64"}}
        ),
        "voice_runs": runtime.voice_runs.snapshot() if runtime else [],
        "feedback": (
            feedback.snapshot()
            if feedback
            else {"latest_display": None, "display_events": [], "earcon_events": []}
        ),
        "deep_tasks": runtime.deep_tasks.snapshot() if runtime else [],
    }


SATELLITE_STATE_ENTITIES = {
    "voice_pipeline": "binary_sensor.kukui_voice_pipeline",
    "voice_paused": "binary_sensor.kukui_voice_paused",
    "display_awake": "binary_sensor.kukui_display_awake",
    "pause_requested": "input_boolean.kukui_voice_pause_requested",
    "pause_minutes": "input_number.kukui_voice_pause_minutes",
    "wake_threshold": "input_number.kukui_wake_threshold",
    "wake_trigger_level": "input_number.kukui_wake_trigger_level",
    "wake_refractory_seconds": "input_number.kukui_wake_refractory_seconds",
    "mic_volume_multiplier": "input_number.kukui_mic_volume_multiplier",
    "tts_volume_day": "input_number.kukui_tts_volume_day",
    "tts_volume_night": "input_number.kukui_tts_volume_night",
    "fallback_clip_volume": "input_number.kukui_fallback_clip_volume",
    "voice_config": "sensor.kukui_voice_config",
    "asr_metrics": "sensor.kukui_asr_metrics",
    "diagnostic_snapshot": "sensor.kukui_diagnostic_snapshot",
    "ambient_light": "sensor.kukui_ambient_light",
    "screen_brightness": "sensor.kukui_display_brightness",
}


def _satellite_status(hass: HomeAssistant) -> dict[str, Any]:
    """Return safe HA-exposed satellite controls and state for the panel."""
    states = {
        key: _entity_state(hass, entity_id)
        for key, entity_id in SATELLITE_STATE_ENTITIES.items()
    }
    return {
        "states": states,
        "diagnostic_snapshot": _satellite_diagnostic_snapshot(hass),
        "services": {
            "pause": hass.services.has_service("script", "kukui_voice_pause"),
            "resume": hass.services.has_service("script", "kukui_voice_resume"),
            "apply_config": hass.services.has_service(
                "script", "kukui_voice_apply_config"
            ),
            "set_pause_minutes": hass.services.has_service("input_number", "set_value"),
            "set_number": hass.services.has_service("input_number", "set_value"),
        },
    }


def _satellite_diagnostic_snapshot(hass: HomeAssistant) -> dict[str, Any]:
    return satellite_diagnostic_snapshot(hass)


def _entity_state(hass: HomeAssistant, entity_id: str) -> dict[str, Any]:
    state = hass.states.get(entity_id)
    if state is None:
        return {
            "entity_id": entity_id,
            "state": "missing",
            "available": False,
            "name": entity_id,
        }
    return {
        "entity_id": entity_id,
        "state": state.state,
        "available": True,
        "name": state.attributes.get("friendly_name") or entity_id,
        "unit": state.attributes.get("unit_of_measurement") or "",
        "attributes": {
            key: value
            for key, value in state.attributes.items()
            if key
            in {
                "paused_until",
                "remaining_seconds",
                "detail",
                "summary",
                "friendly_name",
                "unit_of_measurement",
                "wake_threshold",
                "trigger_level",
                "refractory_seconds",
                "mic_volume_multiplier",
                "tts_volume_day",
                "tts_volume_night",
                "fallback_volume",
                "metrics",
                "snapshot",
                "checks",
                "pipewire_graph",
                "schema_version",
                "generated_at",
                "phase",
                "total_latency_ms",
                "first_result_latency_ms",
                "final_result_latency_ms",
                "audio_bytes",
                "frames",
                "response_events",
                "vad_events",
                "interim_results",
                "final_results",
                "vad_start_seen",
                "vad_finished_seen",
                "endpoint",
                "stale",
                "observed_at",
                "observed_stable_for_ms",
                "stale_after_ms",
                "transcript_chars",
            }
        },
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
        "provider_profiles_configured": bool(
            str(options.get(CONF_PROVIDER_PROFILES) or "").strip()
        ),
        "first_response_audio": {
            "enabled": options.get(CONF_FIRST_RESPONSE_AUDIO_ENABLED, True)
            is not False,
            "adapter": str(
                options.get(CONF_FIRST_RESPONSE_PLAYBACK_ADAPTER) or "local"
            ),
            "local_service": str(options.get(CONF_FIRST_RESPONSE_LOCAL_SERVICE) or ""),
            "tts_entity": str(options.get(CONF_FIRST_RESPONSE_TTS_ENTITY) or ""),
            "media_player_entity": str(
                options.get(CONF_FIRST_RESPONSE_MEDIA_PLAYER) or ""
            ),
        },
    }


def _editable_schema() -> dict[str, Any]:
    return {
        "routing_modes": list(ROUTING_MODES),
        "max_tokens": {"min": 1, "max": MAX_CONFIGURED_TOKENS},
        "timeouts": {"min": 5, "max": MAX_CHAT_TIMEOUT},
        "trace_max_runs": {"min": 1, "max": MAX_TRACE_RUNS},
        "trace_retention_hours": {"min": 1, "max": MAX_TRACE_RETENTION_HOURS},
        "entity_id": {"max_length": MAX_MODEL_ID_LENGTH},
        "first_response_playback_adapters": list(FIRST_RESPONSE_PLAYBACK_ADAPTERS),
    }


def _validate_editable_options(payload: dict[str, Any]) -> dict[str, Any]:  # noqa: PLR0912
    updates: dict[str, Any] = {}

    if CONF_ROUTING_MODE in payload:
        routing_mode = str(payload[CONF_ROUTING_MODE]).strip()
        if routing_mode not in ROUTING_MODES:
            raise ValueError("routing_mode is not supported")
        updates[CONF_ROUTING_MODE] = routing_mode

    models = payload.get("models")
    if models is not None:
        if not isinstance(models, dict):
            raise ValueError("models must be an object")
        updates.update(
            {
                CONF_FAST_MODEL: _required_text(models.get("fast"), "models.fast"),
                CONF_MID_MODEL: _required_text(models.get("mid"), "models.mid"),
                CONF_DEEP_MODEL: _required_text(models.get("deep"), "models.deep"),
            }
        )

    max_tokens = payload.get("max_tokens")
    if max_tokens is not None:
        if not isinstance(max_tokens, dict):
            raise ValueError("max_tokens must be an object")
        updates.update(
            {
                CONF_FAST_MAX_TOKENS: _bounded_int(
                    max_tokens.get("fast"),
                    "max_tokens.fast",
                    minimum=1,
                    maximum=MAX_CONFIGURED_TOKENS,
                ),
                CONF_MID_MAX_TOKENS: _bounded_int(
                    max_tokens.get("mid"),
                    "max_tokens.mid",
                    minimum=1,
                    maximum=MAX_CONFIGURED_TOKENS,
                ),
                CONF_DEEP_MAX_TOKENS: _bounded_int(
                    max_tokens.get("deep"),
                    "max_tokens.deep",
                    minimum=1,
                    maximum=MAX_CONFIGURED_TOKENS,
                ),
            }
        )

    timeouts = payload.get("timeouts")
    if timeouts is not None:
        if not isinstance(timeouts, dict):
            raise ValueError("timeouts must be an object")
        updates.update(
            {
                CONF_FAST_CHAT_TIMEOUT: _bounded_int(
                    timeouts.get("fast"),
                    "timeouts.fast",
                    minimum=5,
                    maximum=MAX_CHAT_TIMEOUT,
                ),
                CONF_MID_CHAT_TIMEOUT: _bounded_int(
                    timeouts.get("mid"),
                    "timeouts.mid",
                    minimum=5,
                    maximum=MAX_CHAT_TIMEOUT,
                ),
                CONF_DEEP_CHAT_TIMEOUT: _bounded_int(
                    timeouts.get("deep"),
                    "timeouts.deep",
                    minimum=5,
                    maximum=MAX_CHAT_TIMEOUT,
                ),
            }
        )

    trace = payload.get("trace")
    if trace is not None:
        if not isinstance(trace, dict):
            raise ValueError("trace must be an object")
        updates.update(
            {
                CONF_DIAGNOSTIC_TRACES: bool(trace.get("enabled")),
                CONF_TRACE_INCLUDE_RAW_MESSAGES: bool(
                    trace.get("include_raw_messages")
                ),
                CONF_TRACE_MAX_RUNS: _bounded_int(
                    trace.get("max_runs"),
                    "trace.max_runs",
                    minimum=1,
                    maximum=MAX_TRACE_RUNS,
                ),
                CONF_TRACE_RETENTION_HOURS: _bounded_int(
                    trace.get("retention_hours"),
                    "trace.retention_hours",
                    minimum=1,
                    maximum=MAX_TRACE_RETENTION_HOURS,
                ),
            }
        )

    first_response_audio = payload.get("first_response_audio")
    if first_response_audio is not None:
        if not isinstance(first_response_audio, dict):
            raise ValueError("first_response_audio must be an object")
        updates[CONF_FIRST_RESPONSE_AUDIO_ENABLED] = bool(
            first_response_audio.get("enabled")
        )
        adapter = str(first_response_audio.get("adapter") or "local").strip()
        if adapter not in FIRST_RESPONSE_PLAYBACK_ADAPTERS:
            raise ValueError("first_response_audio.adapter is not supported")
        updates[CONF_FIRST_RESPONSE_PLAYBACK_ADAPTER] = adapter
        updates[CONF_FIRST_RESPONSE_LOCAL_SERVICE] = _optional_service_id(
            first_response_audio.get("local_service"),
            "first_response_audio.local_service",
            allowed_domains={"rest_command", "script"},
        )
        updates[CONF_FIRST_RESPONSE_TTS_ENTITY] = _optional_entity_id(
            first_response_audio.get("tts_entity"),
            "first_response_audio.tts_entity",
            expected_domain="tts",
        )
        updates[CONF_FIRST_RESPONSE_MEDIA_PLAYER] = _optional_entity_id(
            first_response_audio.get("media_player_entity")
            or first_response_audio.get("media_player"),
            "first_response_audio.media_player_entity",
            expected_domain="media_player",
        )

    provider_profiles = payload.get("provider_profiles")
    if provider_profiles is not None:
        if not isinstance(provider_profiles, str):
            raise ValueError("provider_profiles must be JSON text")
        text = provider_profiles.strip()
        if text:
            updates[CONF_PROVIDER_PROFILES] = normalize_provider_profiles_json(text)
        else:
            updates[CONF_PROVIDER_PROFILES] = ""

    return updates


def _required_text(value: object, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field} is required")
    if len(text) > MAX_MODEL_ID_LENGTH:
        raise ValueError(f"{field} is too long")
    return text


def _bounded_int(value: object, field: str, *, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as err:
        raise ValueError(f"{field} must be an integer") from err
    if parsed < minimum or parsed > maximum:
        raise ValueError(f"{field} must be between {minimum} and {maximum}")
    return parsed


def _optional_entity_id(
    value: object,
    field: str,
    *,
    expected_domain: str,
) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) > MAX_MODEL_ID_LENGTH:
        raise ValueError(f"{field} is too long")
    if "." not in text or text.split(".", 1)[0] != expected_domain:
        raise ValueError(f"{field} must be a {expected_domain} entity_id")
    return text


def _optional_service_id(
    value: object,
    field: str,
    *,
    allowed_domains: set[str],
) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) > MAX_MODEL_ID_LENGTH:
        raise ValueError(f"{field} is too long")
    if "." not in text or text.split(".", 1)[0] not in allowed_domains:
        domains = ", ".join(sorted(allowed_domains))
        raise ValueError(f"{field} must be one of these service domains: {domains}")
    return text


def _feedback_policy_status() -> dict[str, Any]:
    current_hour = dt_util.now().hour
    quiet_hours_active = (
        current_hour >= QUIET_HOURS_START or current_hour < QUIET_HOURS_END
    )
    return {
        "quiet_hours": {
            "start_hour": QUIET_HOURS_START,
            "end_hour": QUIET_HOURS_END,
            "current_local_hour": current_hour,
            "active": quiet_hours_active,
        }
    }


def _trace_status(options: dict[str, Any]) -> dict[str, Any]:
    return {
        "enabled": bool(options.get(CONF_DIAGNOSTIC_TRACES)),
        "include_raw_messages": bool(options.get(CONF_TRACE_INCLUDE_RAW_MESSAGES)),
        "max_runs": int(options.get(CONF_TRACE_MAX_RUNS) or RECOMMENDED_TRACE_MAX_RUNS),
        "retention_hours": int(
            options.get(CONF_TRACE_RETENTION_HOURS) or RECOMMENDED_TRACE_RETENTION_HOURS
        ),
        "encoding": "json+zlib+base64",
    }


def _route_status(route: ModelRoute) -> dict[str, Any]:
    return {
        "kind": route.kind,
        "model": route.model,
        "max_tokens": route.max_tokens,
        "timeout_s": route.timeout_s,
        "async_deep_task": route.async_deep_task,
    }


def _model_provider_status(entry: ConfigEntry) -> dict[str, Any]:
    options = entry.options
    primary = {
        "name": "primary",
        "base_url": entry.data.get("base_url"),
        "models": _options_status(options)["models"],
        "has_api_key": True,
    }
    try:
        fallbacks = [
            profile.safe_dict() for profile in provider_profiles_from_options(options)
        ]
    except ValueError as err:
        return {
            "primary": primary,
            "fallbacks": [],
            "fallback_enabled": False,
            "config_error": str(err),
        }
    return {
        "primary": primary,
        "fallbacks": fallbacks,
        "fallback_enabled": bool(fallbacks),
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


def _earcon_pack_status() -> dict[str, Any]:
    try:
        data = json.loads(EARCON_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {
            "pack": EARCON_PACK,
            "base_url": f"{STATIC_BASE}/earcons/{EARCON_PACK}",
            "files": {},
        }

    base_url = f"{STATIC_BASE}/earcons/{data.get('pack') or EARCON_PACK}"
    files = data.get("files") if isinstance(data.get("files"), dict) else {}
    return {
        **data,
        "base_url": base_url,
        "files": {
            name: {**item, "url": f"{base_url}/{item.get('path')}"}
            for name, item in files.items()
            if isinstance(item, dict) and item.get("path")
        },
    }
