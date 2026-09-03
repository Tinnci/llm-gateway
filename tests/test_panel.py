"""Tests for the Voice Harness panel."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components import frontend
from homeassistant.const import CONF_API_KEY
from homeassistant.setup import async_setup_component

from custom_components.llm_gateway.api import (
    LatencySample,
    LLMGatewayAuthError,
    LLMGatewayClient,
    _delta_text,
)
from custom_components.llm_gateway.const import (
    CONF_BASE_URL,
    CONF_CHAT_MODEL,
    CONF_DIAGNOSTIC_TRACES,
    CONF_FAST_CHAT_TIMEOUT,
    CONF_FAST_MAX_TOKENS,
    CONF_FAST_MODEL,
    CONF_FIRST_RESPONSE_LOCAL_SERVICE,
    CONF_FIRST_RESPONSE_MEDIA_PLAYER,
    CONF_FIRST_RESPONSE_PLAYBACK_ADAPTER,
    CONF_FIRST_RESPONSE_TTS_ENTITY,
    CONF_PROVIDER_PROFILES,
    CONF_SEARCH_ENABLED,
    CONF_TAVILY_API_KEY,
    CONF_TRACE_INCLUDE_RAW_MESSAGES,
    CONF_TRACE_MAX_RUNS,
    CONF_TRACE_RETENTION_HOURS,
    DEFAULT_BASE_URL,
    RECOMMENDED_FAST_MODEL,
    ROUTING_MODE_MID,
)
from custom_components.llm_gateway.memory import VoiceMemory
from custom_components.llm_gateway.panel import (
    PANEL_MODULE,
    PANEL_TITLE,
    PANEL_URL,
    async_setup_panel,
)
from custom_components.llm_gateway.traces import TraceStore, TraceTurn
from custom_components.llm_gateway.views import SATELLITE_STATE_ENTITIES


async def test_panel_registers_sidebar_entry(hass):
    """Voice Harness is exposed as an admin-only custom panel."""
    assert await async_setup_component(hass, "http", {})

    await async_setup_panel(hass)

    panel = hass.data[frontend.DATA_PANELS][PANEL_URL]
    assert panel.sidebar_title == PANEL_TITLE
    assert panel.sidebar_icon == "mdi:microphone-message"
    assert panel.require_admin
    assert panel.config_panel_domain is None
    assert panel.config["_panel_custom"]["name"] == "voice-harness-panel"
    assert panel.config["_panel_custom"]["module_url"] == PANEL_MODULE
    assert panel.config["api_base"] == "/api/llm_gateway"
    module_url = panel.config["_panel_custom"]["module_url"]
    assert module_url.startswith("/llm_gateway/static/")


async def test_panel_static_module_is_served(hass, hass_client):
    """The registered custom element module is reachable through HA HTTP."""
    assert await async_setup_component(hass, "http", {})

    await async_setup_panel(hass)
    client = await hass_client()

    response = await client.get(PANEL_MODULE)
    assert response.status == 200
    assert response.content_type == "text/javascript"
    body = await response.text()
    assert "customElements.define" in body
    assert "voice-harness-panel" in body
    assert "Phosh lock screen is running" in body
    assert "Phosh 锁屏运行中" in body
    for module in ("voice-harness-api.js", "voice-harness-components.js"):
        dependency = await client.get(f"/llm_gateway/static/{module}")
        assert dependency.status == 200
        assert dependency.content_type == "text/javascript"


async def test_panel_uses_task_navigation_and_one_config_form(hass, hass_client):
    """The panel serves four task views and no legacy settings form."""
    assert await async_setup_component(hass, "http", {})

    await async_setup_panel(hass)
    client = await hass_client()

    response = await client.get(PANEL_MODULE)
    assert response.status == 200
    body = await response.text()
    # The task navigation is small and the settings view keeps one config form.
    assert 'labelKey: "tab.overview"' in body
    assert 'labelKey: "tab.runs"' in body
    assert 'labelKey: "tab.test"' in body
    assert 'labelKey: "tab.settings"' in body
    assert "<voice-harness-overview>" in body
    assert 'data-form="config"' in body
    assert "configCard" in body
    assert "config.group_core" in body
    assert "config.group_audio_traces" in body
    # Legacy Settings form and its API path are gone from the bundle.
    assert 'data-form="settings"' not in body
    assert 'labelKey: "tab.config"' not in body
    assert 'labelKey: "tab.satellite"' not in body
    assert 'labelKey: "tab.policies"' not in body
    assert 'labelKey: "tab.scenarios"' not in body
    assert 'labelKey: "tab.memory"' not in body
    # Earcons stay inside Settings instead of returning as a dedicated tab.
    assert '"tab.earcons"' not in body
    assert "_renderEarcons()" in body


async def test_harness_config_api_get_redacts_secrets(
    hass, hass_client, mock_config_entry
):
    """Config GET returns write-only secret fields only as has_* booleans."""
    assert await async_setup_component(hass, "http", {})
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={
            **mock_config_entry.options,
            CONF_TAVILY_API_KEY: "tavily-secret",
            CONF_PROVIDER_PROFILES: (
                '{"providers":[{"name":"fallback","base_url":"https://fallback.test/v1",'
                '"api_key":"profile-secret","models":{"fast":"fallback-fast"}}]}'
            ),
        },
    )
    await async_setup_panel(hass)
    client = await hass_client()

    response = await client.get("/api/llm_gateway/harness/config")

    assert response.status == 200
    data = await response.json()
    entry = data["entries"][0]
    assert entry["base_url"] == DEFAULT_BASE_URL
    assert entry["has_api_key"] is True
    assert entry["api_key_hint"] == "\u2022\u2022\u2022\u2022"
    assert "api_key" not in entry
    assert entry["revision"]
    assert entry["options"]["has_tavily_api_key"] is True
    assert "tavily_api_key" not in entry["options"]
    profiles = entry["options"]["provider_profiles"]
    assert profiles[0]["name"] == "fallback"
    assert profiles[0]["has_api_key"] is True
    assert "api_key" not in profiles[0]


async def test_harness_config_api_post_updates_entry(
    hass, hass_client, aioclient_mock, mock_config_entry
):
    """Config POST validates provider credentials and updates the entry."""
    assert await async_setup_component(hass, "http", {})
    aioclient_mock.get(
        "https://example.test/v1/models",
        json={"data": [{"id": "m1"}, {"id": "m2"}]},
    )
    mock_config_entry.add_to_hass(hass)
    await async_setup_panel(hass)
    client = await hass_client()

    response = await client.post(
        "/api/llm_gateway/harness/config",
        json={
            "entry_id": mock_config_entry.entry_id,
            "data": {
                "base_url": "https://example.test/v1",
                "api_key": "new-key",
            },
            "options": {
                "routing_mode": ROUTING_MODE_MID,
                "models": {"fast": "m1", "mid": "m2", "deep": "m2"},
                "max_tokens": {"fast": 512, "mid": 1024, "deep": 2048},
                "timeouts": {"fast": 30, "mid": 90, "deep": 180},
                "temperature": 0.5,
                "top_p": 0.9,
                "search_enabled": True,
                "llm_hass_api": [],
                "prompt": "",
            },
        },
    )

    assert response.status == 200
    data = await response.json()
    assert data["entry"]["base_url"] == "https://example.test/v1"
    assert data["entry"]["has_api_key"] is True
    assert mock_config_entry.data[CONF_BASE_URL] == "https://example.test/v1"
    assert mock_config_entry.data[CONF_API_KEY] == "new-key"
    assert mock_config_entry.options[CONF_FAST_MODEL] == "m1"
    assert mock_config_entry.options[CONF_SEARCH_ENABLED] is True


async def test_harness_config_api_rejects_invalid_connection(
    hass, hass_client, aioclient_mock, mock_config_entry
):
    """Config POST keeps the old entry when provider credentials are invalid."""
    assert await async_setup_component(hass, "http", {})
    aioclient_mock.get("https://bad.test/v1/models", status=401)
    mock_config_entry.add_to_hass(hass)
    await async_setup_panel(hass)
    client = await hass_client()

    response = await client.post(
        "/api/llm_gateway/harness/config",
        json={
            "entry_id": mock_config_entry.entry_id,
            "data": {
                "base_url": "https://bad.test/v1",
                "api_key": "bad-key",
            },
        },
    )

    assert response.status == 400
    data = await response.json()
    assert data["code"] == "invalid_auth"
    assert mock_config_entry.data[CONF_BASE_URL] == DEFAULT_BASE_URL
    assert mock_config_entry.data[CONF_API_KEY] == "test-key"


async def test_harness_config_api_revision_fencing(
    hass, hass_client, aioclient_mock, mock_config_entry
):
    """A stale revision is rejected with 409 and nothing is written."""
    assert await async_setup_component(hass, "http", {})
    aioclient_mock.get(
        "https://example.test/v1/models",
        json={"data": [{"id": "m1"}]},
    )
    mock_config_entry.add_to_hass(hass)
    await async_setup_panel(hass)
    client = await hass_client()

    payload = {
        "entry_id": mock_config_entry.entry_id,
        "data": {
            "base_url": "https://example.test/v1",
            "api_key": "new-key",
        },
    }
    first = await client.post("/api/llm_gateway/harness/config", json=payload)
    assert first.status == 200
    first_data = await first.json()
    revision = first_data["entry"]["revision"]
    assert revision

    stale = await client.post(
        "/api/llm_gateway/harness/config",
        json={**payload, "revision": "2020-01-01T00:00:00+00:00"},
    )
    assert stale.status == 409
    stale_data = await stale.json()
    assert stale_data["code"] == "revision_conflict"

    fresh = await client.post(
        "/api/llm_gateway/harness/config",
        json={**payload, "revision": revision},
    )
    assert fresh.status == 200


async def test_harness_config_models_endpoint(
    hass, hass_client, aioclient_mock, mock_config_entry
):
    """The models endpoint returns live ids using stored credentials."""
    assert await async_setup_component(hass, "http", {})
    aioclient_mock.get(
        f"{DEFAULT_BASE_URL}/models",
        json={"data": [{"id": "z-model"}, {"id": "a-model"}]},
    )
    mock_config_entry.add_to_hass(hass)
    await async_setup_panel(hass)
    client = await hass_client()

    response = await client.post(
        "/api/llm_gateway/harness/config/models",
        json={"entry_id": mock_config_entry.entry_id},
    )

    assert response.status == 200
    data = await response.json()
    assert data["models"] == ["a-model", "z-model"]


async def test_latency_probe_stream_parsing():
    """Content deltas count; reasoning-only deltas are ignored."""
    assert _delta_text({"choices": [{"delta": {"content": "你好"}}]}) == "你好"
    assert _delta_text({"choices": [{"delta": {"reasoning_content": "想"}}]}) == ""
    assert _delta_text({}) == ""
    sample = LatencySample(model="m", ok=True, ttft_ms=420.0)
    assert sample.as_dict()["model"] == "m"


async def test_harness_latency_api_probes_models(hass, hass_client, mock_config_entry):
    """The latency endpoint probes models concurrently and preserves order."""
    assert await async_setup_component(hass, "http", {})
    calls: list[str] = []

    async def fake_probe(self, *, model, max_tokens=32, timeout_s=25):
        calls.append(model)
        return LatencySample(
            model=model,
            ok=True,
            ttft_ms=420.5 if model == "fast-m" else 900.0,
            tokens=10,
            tps=30.0,
            total_ms=800.0,
        )

    with patch.object(LLMGatewayClient, "async_probe_latency", fake_probe):
        mock_config_entry.add_to_hass(hass)
        await async_setup_panel(hass)
        client = await hass_client()

        response = await client.post(
            "/api/llm_gateway/harness/config/latency",
            json={
                "entry_id": mock_config_entry.entry_id,
                "models": ["deep-m", "fast-m", "fast-m"],
            },
        )

    assert response.status == 200
    data = await response.json()
    results = data["results"]
    assert [r["model"] for r in results] == ["deep-m", "fast-m"]
    assert results[1]["ttft_ms"] == 420.5
    assert calls == ["deep-m", "fast-m"]


async def test_harness_latency_api_maps_auth_error(
    hass, hass_client, mock_config_entry
):
    """Auth failures become per-model error samples instead of HTTP 500."""
    assert await async_setup_component(hass, "http", {})

    async def fake_probe(self, *, model, max_tokens=32, timeout_s=25):
        raise LLMGatewayAuthError("bad key")

    with patch.object(LLMGatewayClient, "async_probe_latency", fake_probe):
        mock_config_entry.add_to_hass(hass)
        await async_setup_panel(hass)
        client = await hass_client()

        response = await client.post(
            "/api/llm_gateway/harness/config/latency",
            json={"entry_id": mock_config_entry.entry_id, "models": ["m1"]},
        )

    assert response.status == 200
    data = await response.json()
    assert data["results"][0]["ok"] is False
    assert data["results"][0]["error"] == "invalid_auth"


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ({"models": []}, "no_models"),
        ({"models": [f"m{i}" for i in range(9)]}, "too_many_models"),
        ({}, "no_models"),
    ],
)
async def test_harness_latency_api_rejects_bad_input(
    hass, hass_client, mock_config_entry, payload, code
):
    """Malformed model lists fail fast without probing."""
    assert await async_setup_component(hass, "http", {})
    mock_config_entry.add_to_hass(hass)
    await async_setup_panel(hass)
    client = await hass_client()

    response = await client.post(
        "/api/llm_gateway/harness/config/latency",
        json={"entry_id": mock_config_entry.entry_id, **payload},
    )

    assert response.status == 400
    data = await response.json()
    assert data["code"] == code


async def test_harness_status_api(hass, hass_client):
    """The panel status API returns sample scenarios."""
    assert await async_setup_component(hass, "http", {})
    hass.states.async_set(
        "binary_sensor.kukui_voice_paused",
        "off",
        {"friendly_name": "Kukui 语音暂停"},
    )
    hass.states.async_set(
        "input_number.kukui_voice_pause_minutes",
        "30",
        {"friendly_name": "Kukui 语音暂停分钟数", "unit_of_measurement": "min"},
    )
    hass.states.async_set(
        "sensor.kukui_asr_metrics",
        "streaming",
        {
            "friendly_name": "Kukui ASR 指标",
            "phase": "streaming",
            "interim_results": 1,
            "final_results": 0,
            "frames": 3,
            "first_result_latency_ms": 120,
            "stale": False,
            "observed_stable_for_ms": 0,
            "stale_after_ms": 30000,
            "metrics": {
                "phase": "streaming",
                "interim_results": 1,
                "final_results": 0,
                "frames": 3,
                "first_result_latency_ms": 120,
                "stale": False,
                "observed_stable_for_ms": 0,
                "stale_after_ms": 30000,
                "endpoint": {
                    "state": "partial",
                    "speech_started": True,
                    "endpoint_detected": False,
                    "interrupt_ready": True,
                },
            },
            "endpoint": {
                "state": "partial",
                "speech_started": True,
                "endpoint_detected": False,
                "interrupt_ready": True,
            },
        },
    )
    hass.states.async_set(
        "sensor.kukui_diagnostic_snapshot",
        "ok",
        {
            "schema_version": 1,
            "generated_at": "2026-06-21T00:00:00+00:00",
            "snapshot": {
                "schema_version": 1,
                "pipewire_graph": {"aec_enabled": True},
                "audio_topology": {
                    "concurrency": {
                        "multi_room_manager": False,
                        "session_model": "single_room_single_active_turn",
                        "future_multi_room_orchestrator": {
                            "implemented": False,
                            "seam": "room_session_orchestrator_above_satellite_paths",
                        },
                    }
                },
                "audio_frontend_graph": {
                    "model": "user_space_pipewire_graph",
                    "gaps": [
                        {
                            "id": "orchestration.multi_room",
                            "state": "not_implemented",
                            "requirement": "multi_room_parallel_streams",
                        }
                    ],
                },
                "playback_interrupt": {
                    "schema_version": 1,
                    "phase": "interrupted",
                    "owner": "phosh-ha-status",
                    "source": "kukui-display-agent",
                    "reason": "asr_endpoint",
                    "request_id": "request-1",
                    "barge_in_stop_latency_ms": 42,
                    "targets": [
                        {
                            "pattern": "snd-command-wrapper.sh",
                            "matched_before": 1,
                            "remaining_after": 0,
                        }
                    ],
                    "signals": ["TERM", "KILL"],
                },
                "checks": [
                    {
                        "id": "pipewire.nodes.visible",
                        "status": "warning",
                        "layer": "pipewire",
                    },
                    {
                        "id": "voice.entities.available",
                        "status": "error",
                        "layer": "homeassistant",
                        "depends_on": ["pipewire.nodes.visible"],
                    },
                    {
                        "id": "tts.entity.available",
                        "status": "error",
                        "layer": "tts",
                        "depends_on": ["voice.entities.available"],
                    },
                ],
            },
        },
    )
    await async_setup_panel(hass)
    client = await hass_client()

    response = await client.get("/api/llm_gateway/harness/status")

    assert response.status == 200
    data = await response.json()
    assert data["panel"]["url_path"] == PANEL_URL
    assert data["panel"]["title_i18n"]["zh-Hans"] == "语音测试台"
    assert data["panel"]["title_i18n"]["en"] == PANEL_TITLE
    assert data["earcons"]["pack"] == "ha_voice_minimal_v0"
    assert data["earcons"]["base_url"].startswith("/llm_gateway/static/")
    assert not data["earcons"]["base_url"].startswith("/api/")
    for file in data["earcons"]["files"].values():
        assert file["url"].startswith("/llm_gateway/static/")
        assert not file["url"].startswith("/api/")
    assert data["earcons"]["files"]["confirmation"]["url"].startswith(
        "/llm_gateway/static/"
    )
    assert data["earcons"]["files"]["confirmation"]["url"].endswith("/confirmation.wav")
    assert data["earcons"]["files"]["processing_loop"]["url"].endswith(
        "/processing_loop.wav"
    )
    assert data["earcons"]["files"]["provider_fallback"]["url"].endswith(
        "/provider_fallback.wav"
    )
    assert data["prompt_policies"]
    assert any(policy["id"] == "latency_wait" for policy in data["prompt_policies"])
    assert data["sample_scenarios"]
    assert data["editable"]["routing_modes"]
    assert RECOMMENDED_FAST_MODEL in data["editable"]["models"]
    assert "local" in data["editable"]["first_response_playback_adapters"]
    assert data["editable"]["max_tokens"]["max"] >= 16384
    assert data["satellite"]["states"]["voice_paused"]["state"] == "off"
    assert data["satellite"]["states"]["pause_minutes"]["unit"] == "min"
    assert (
        data["satellite"]["states"]["pause_requested"]["entity_id"]
        == "input_boolean.kukui_voice_pause_requested"
    )
    assert data["satellite"]["states"]["asr_metrics"]["state"] == "streaming"
    assert (
        data["satellite"]["states"]["asr_metrics"]["attributes"]["interim_results"] == 1
    )
    assert (
        data["satellite"]["states"]["asr_metrics"]["attributes"]["metrics"]["phase"]
        == "streaming"
    )
    assert data["satellite"]["states"]["asr_metrics"]["attributes"]["endpoint"][
        "interrupt_ready"
    ]
    assert data["satellite"]["states"]["asr_metrics"]["attributes"]["stale"] is False
    assert (
        data["satellite"]["states"]["asr_metrics"]["attributes"][
            "observed_stable_for_ms"
        ]
        == 0
    )
    assert data["satellite"]["diagnostic_snapshot"]["schema_version"] == 1
    assert data["satellite"]["diagnostic_snapshot"]["pipewire_graph"]["aec_enabled"]
    assert (
        data["satellite"]["diagnostic_snapshot"]["audio_topology"]["concurrency"][
            "session_model"
        ]
        == "single_room_single_active_turn"
    )
    assert (
        data["satellite"]["diagnostic_snapshot"]["audio_frontend_graph"]["gaps"][0][
            "id"
        ]
        == "orchestration.multi_room"
    )
    assert (
        data["satellite"]["diagnostic_snapshot"]["playback_interrupt"][
            "barge_in_stop_latency_ms"
        ]
        == 42
    )
    assert (
        data["satellite"]["states"]["diagnostic_snapshot"]["attributes"]["snapshot"][
            "checks"
        ][0]["id"]
        == "pipewire.nodes.visible"
    )
    assert (
        data["satellite"]["diagnostic_snapshot"]["first_failing_check"]["id"]
        == "pipewire.nodes.visible"
    )
    assert (
        "voice.entities.available"
        in data["satellite"]["diagnostic_snapshot"]["first_failing_check"][
            "blocking_dependents"
        ]
    )


def test_satellite_status_reads_canonical_display_brightness_entity() -> None:
    assert (
        SATELLITE_STATE_ENTITIES["screen_brightness"]
        == "sensor.kukui_display_brightness"
    )


async def test_harness_status_api_reports_first_response_audio_route(
    hass, hass_client, mock_config_entry
):
    """The status API exposes the local playback adapter and fallback candidates."""
    assert await async_setup_component(hass, "http", {})
    mock_config_entry.add_to_hass(hass)
    hass.services.async_register(
        "rest_command",
        "kukui_voice_feedback",
        lambda *_args: None,
    )
    hass.services.async_register("tts", "speak", lambda *_args: None)
    hass.states.async_set(
        "tts.edge_tts_service_edge_tts",
        "2026-06-19T00:00:00+00:00",
        {"friendly_name": "Edge TTS Service Edge TTS"},
    )
    hass.states.async_set(
        "media_player.ke_ting_433",
        "idle",
        {"friendly_name": "Homepod mini"},
    )
    await async_setup_panel(hass)
    client = await hass_client()

    response = await client.get("/api/llm_gateway/harness/status")

    assert response.status == 200
    data = await response.json()
    audio = data["entries"][0]["first_response_audio"]
    assert audio["adapter"] == "local"
    assert audio["route"]["backend"] == "rest_command.kukui_voice_feedback"
    assert audio["route"]["adapter"] == "local"
    assert audio["can_play"] is True
    assert audio["candidates"]["local_services"][0]["service"] == (
        "rest_command.kukui_voice_feedback"
    )
    assert data["entries"][0]["model_candidates"]
    assert RECOMMENDED_FAST_MODEL in data["entries"][0]["model_candidates"]
    assert audio["candidates"]["tts"][0]["entity_id"] == (
        "tts.edge_tts_service_edge_tts"
    )


async def test_harness_evaluate_api(hass, hass_client):
    """The ad hoc scenario API evaluates policy and spoken text."""
    assert await async_setup_component(hass, "http", {})
    await async_setup_panel(hass)
    client = await hass_client()

    response = await client.post(
        "/api/llm_gateway/harness/evaluate",
        json={
            "user": "打开前门门锁",
            "response": "要操作前门门锁吗？请确认。",
            "expected": {
                "must_search": False,
                "spoken_response": {
                    "max_sentences": 2,
                    "must_include": ["确认"],
                    "must_not_mention": ["entity_id"],
                },
            },
        },
    )

    assert response.status == 200
    data = await response.json()
    assert data["passed"]
    assert data["route"]["kind"] == "fast"
    assert not data["search"]["allowed"]
    assert data["spoken"] == "要操作前门门锁吗？请确认。"


async def test_harness_runs_api_lists_recent_runs(hass, hass_client, mock_config_entry):
    """The runs API returns the recent trace list without raw payloads."""
    assert await async_setup_component(hass, "http", {})
    mock_config_entry.add_to_hass(hass)
    trace_store = TraceStore(hass, mock_config_entry.entry_id)
    await trace_store.async_load()
    mock_config_entry.runtime_data = SimpleNamespace(
        trace_store=trace_store,
        provider_selector=SimpleNamespace(snapshot=list),
        turn_controller=SimpleNamespace(current_turn_id=None),
    )
    await async_setup_panel(hass)

    options = {
        CONF_DIAGNOSTIC_TRACES: True,
        CONF_TRACE_INCLUDE_RAW_MESSAGES: True,
        CONF_TRACE_MAX_RUNS: 40,
        CONF_TRACE_RETENTION_HOURS: 24,
    }
    for index in range(31):
        await trace_store.async_record_turn(
            options,
            TraceTurn(
                conversation_id=f"conv-{index}",
                user_text=f"打开客厅灯 {index}",
                assistant_text="好了。",
                route={"kind": "fast", "model": "fast-model"},
                latency_ms=100 + index,
                status="complete",
                raw_payload={
                    "input": {
                        "text": f"打开客厅灯 {index}",
                        "conversation_id": f"conv-{index}",
                    },
                    "speech": {"final": "好了。", "tts_cleaned": True},
                    "tool_events": [
                        {
                            "phase": "call",
                            "tool_call_id": f"ha-{index}",
                            "name": "HassTurnOn",
                            "args": {"domain": "light", "area": "客厅"},
                        }
                    ],
                    "grounding": {"status": "not_required", "verifier": {}},
                    "messages": [],
                },
            ),
        )

    client = await hass_client()
    response = await client.get("/api/llm_gateway/harness/runs")

    assert response.status == 200
    data = await response.json()
    assert data["api_version"] == 1
    assert len(data["records"]) == 30
    assert data["records"][0]["conversation_id"] == "conv-30"
    assert data["records"][0]["tools"] == ["HassTurnOn"]
    assert data["records"][0]["latency_ms"] == 130
    assert "raw_payload" not in data["records"][0]

    filtered = await client.get(
        "/api/llm_gateway/harness/runs?limit=2&route=fast&contains=30"
    )
    filtered_data = await filtered.json()
    assert filtered_data["records"][0]["conversation_id"] == "conv-30"
    assert filtered_data["has_more"] is False

    first_page = await client.get("/api/llm_gateway/harness/runs?limit=2")
    first_page_data = await first_page.json()
    assert first_page_data["has_more"] is True
    second_page = await client.get(
        f"/api/llm_gateway/harness/runs?limit=2&cursor={first_page_data['next_cursor']}"
    )
    second_page_data = await second_page.json()
    assert second_page_data["records"][0]["conversation_id"] == "conv-28"

    invalid_cursor = await client.get("/api/llm_gateway/harness/runs?cursor=not-a-run")
    assert invalid_cursor.status == 400
    invalid_since = await client.get(
        "/api/llm_gateway/harness/runs?since=2026-09-02T10:00:00"
    )
    assert invalid_since.status == 400
    invalid_boolean = await client.get(
        "/api/llm_gateway/harness/runs?has_error=sometimes"
    )
    assert invalid_boolean.status == 400

    comparison = await client.get(
        "/api/llm_gateway/harness/runs/compare"
        f"?left_run_id={data['records'][1]['run_id']}"
        f"&right_run_id={data['records'][0]['run_id']}"
    )
    comparison_data = await comparison.json()
    assert comparison_data["comparison"]["latency_ms"]["delta"] == 1

    health = await client.get("/api/llm_gateway/harness/health")
    health_data = await health.json()
    assert health_data["api_version"] == 1
    assert health_data["entries"][0]["trace_records"] == 31


async def test_harness_run_detail_api_returns_debug_record(
    hass, hass_client, mock_config_entry
):
    """The run detail API exposes timeline, first response, tools, and evidence."""
    assert await async_setup_component(hass, "http", {})
    mock_config_entry.add_to_hass(hass)
    trace_store = TraceStore(hass, mock_config_entry.entry_id)
    await trace_store.async_load()
    mock_config_entry.runtime_data = SimpleNamespace(trace_store=trace_store)
    await async_setup_panel(hass)

    await trace_store.async_record_turn(
        {
            CONF_DIAGNOSTIC_TRACES: True,
            CONF_TRACE_INCLUDE_RAW_MESSAGES: True,
            CONF_TRACE_MAX_RUNS: 30,
            CONF_TRACE_RETENTION_HOURS: 24,
        },
        TraceTurn(
            conversation_id="conv-poem",
            user_text="关关雎鸠，在河之洲，这句话是出自哪里？",
            assistant_text="这句诗出自《诗经·国风·周南·关雎》。",
            route={"kind": "mid", "model": "mid-model"},
            latency_ms=2200,
            status="complete",
            timeline=[
                {"stage": "received", "t_ms": 0, "status": "ok", "attrs": {}},
                {
                    "stage": "first_response",
                    "t_ms": 120,
                    "status": "ok",
                    "attrs": {
                        "cue": "thinking",
                        "spoken_hint": "我看一下。",
                        "deadline_ms": 300,
                    },
                },
                {
                    "stage": "search_result",
                    "t_ms": 1100,
                    "status": "ok",
                    "attrs": {"provider": "tavily"},
                },
                {
                    "stage": "verifier_audit",
                    "t_ms": 1800,
                    "status": "error",
                    "attrs": {"error": "verifier_returned_non_json"},
                },
                {"stage": "complete", "t_ms": 2200, "status": "complete", "attrs": {}},
            ],
            raw_payload={
                "input": {
                    "text": "关关雎鸠，在河之洲，这句话是出自哪里？",
                    "conversation_id": "conv-poem",
                    "language": "zh-CN",
                },
                "speech": {
                    "final": "这句诗出自《诗经·国风·周南·关雎》。",
                    "tts_cleaned": True,
                },
                "tool_events": [
                    {
                        "phase": "call",
                        "tool_call_id": "search-1",
                        "name": "search_web",
                        "external": True,
                        "args": {"query": "关关雎鸠 在河之洲 出处"},
                    },
                    {
                        "phase": "result",
                        "tool_call_id": "search-1",
                        "name": "search_web",
                        "status": "ok",
                        "result": {
                            "provider": "tavily",
                            "results": [
                                {
                                    "title": "周南·关雎",
                                    "url": "https://example.test/guanju",
                                    "content": "出自《诗经·国风·周南·关雎》。",
                                }
                            ],
                        },
                    },
                ],
                "grounding": {
                    "status": "ok",
                    "canonical_answers": ["《诗经·国风·周南·关雎》"],
                    "evidence": [
                        {
                            "evidence_id": "ev-origin",
                            "source_id": "https://example.test/guanju",
                            "evidence_type": "quote_origin",
                            "text": "《诗经·国风·周南·关雎》",
                            "included_in_final": True,
                        },
                        {
                            "evidence_id": "ev-qinjing",
                            "source_id": "https://example.test/guanju",
                            "evidence_type": "term_explanation_source",
                            "text": "《禽经》",
                            "included_in_final": False,
                        },
                    ],
                    "verifier": {
                        "mode": "cheap_evidence",
                        "audit_only": True,
                        "raw_excerpt": "verifier_returned_non_json",
                    },
                },
                "earcon_events": [
                    {
                        "turn_id": "conv-poem",
                        "earcon_name": "search",
                        "semantic_state": "searching",
                        "scheduled_at_ms": 120,
                        "played_at_ms": 120,
                        "duration_ms": 194,
                        "priority": 50,
                        "can_play_while_listening": False,
                        "quiet_hours_behavior": "attenuate",
                        "trace_event_name": "earcon_search",
                        "suppressed_reason": "",
                        "volume_profile": "normal",
                        "microphone_hot": False,
                        "quiet_hours_applied": False,
                    }
                ],
                "display_status_events": [
                    {
                        "id": "display-1",
                        "turn_id": "conv-poem",
                        "state": "searching",
                        "title": "Searching",
                        "short_text": "我看一下。",
                        "privacy_level": "private",
                        "progress": "indeterminate",
                        "action_buttons": ["cancel", "open_panel"],
                        "expires_at": "2026-06-19T00:00:45+00:00",
                        "source": "voice_gateway",
                        "deep_link": "/voice-harness/runs/conv-poem",
                        "created_at": "2026-06-19T00:00:00+00:00",
                    }
                ],
                "messages": [],
            },
        ),
    )
    run_id = trace_store.snapshot()["records"][0]["run_id"]

    client = await hass_client()
    response = await client.get(f"/api/llm_gateway/harness/runs/{run_id}")

    assert response.status == 200
    data = await response.json()
    record = data["record"]
    assert record["run_id"] == run_id
    assert record["input"]["conversation_id"] == "conv-poem"
    assert record["first_response_decision"]["spoken_hint"] == "我看一下。"
    assert record["first_response_text"] == "我看一下。"
    assert record["search_gate"]["searched"] is True
    assert record["search_debug"]["searched"] is True
    assert record["tool_calls_by_iteration"] == []
    assert record["duplicate_tool_suppressions"] == []
    assert record["debug_flags"]["polluted_evidence_present"] is True
    assert record["debug_flags"]["final_modified_by_grounding"] is False
    assert record["verifier_mode"] == "audit_only"
    assert record["grounding"]["evidence"][1]["evidence_type"] == (
        "term_explanation_source"
    )
    assert record["earcons"][0]["earcon_name"] == "search"
    assert record["display_status"]["latest"]["action_buttons"] == [
        "cancel",
        "open_panel",
    ]
    assert record["critical_path"][3]["blocking"] is False
    assert "raw_payload" not in record

    raw_response = await client.get(
        f"/api/llm_gateway/harness/runs/{run_id}?include_raw=true"
    )
    raw_record = (await raw_response.json())["record"]
    assert raw_record["raw_payload"]["speech"]["tts_cleaned"] is True

    invalid_raw = await client.get(
        f"/api/llm_gateway/harness/runs/{run_id}?include_raw=sometimes"
    )
    assert invalid_raw.status == 400

    events_response = await client.get(f"/api/llm_gateway/harness/runs/{run_id}/events")
    events = await events_response.json()
    assert events["api_version"] == 1
    assert events["run_id"] == run_id
    assert events["count"] == len(events["events"])
    assert events["events"]

    missing = await client.get("/api/llm_gateway/harness/runs/not-found")
    assert missing.status == 404


async def test_harness_replay_api_creates_side_effect_free_fork(
    hass, hass_client, mock_config_entry
):
    """The replay API stores lineage without calling a live HA service."""
    assert await async_setup_component(hass, "http", {})
    mock_config_entry.add_to_hass(hass)
    trace_store = TraceStore(hass, mock_config_entry.entry_id)
    await trace_store.async_load()
    mock_config_entry.runtime_data = SimpleNamespace(trace_store=trace_store)
    await async_setup_panel(hass)
    calls = []

    async def turn_on(call):
        calls.append(call)

    hass.services.async_register("light", "turn_on", turn_on)
    await trace_store.async_record_turn(
        {CONF_DIAGNOSTIC_TRACES: True},
        TraceTurn(
            conversation_id="conv-replay",
            user_text="打开所有灯。",
            assistant_text="已打开所有灯。",
            route={"kind": "local_action"},
            latency_ms=20,
            status="complete",
            raw_payload={"input": {"text": "打开所有灯。"}},
            run_id="source-replay",
        ),
    )

    client = await hass_client()
    response = await client.post(
        "/api/llm_gateway/harness/runs/source-replay/replay",
        json={"overrides": {"route": "local_action"}},
    )

    assert response.status == 201
    record = (await response.json())["record"]
    assert calls == []
    assert record["lineage"]["replay_of"] == "source-replay"
    assert record["lineage"]["overrides"]["route"] == "local_action"
    assert record["lineage"]["overrides"]["prompt"] == ""
    assert record["proposed_actions"][0]["target_scope"] == "all"


async def test_harness_admin_can_write_evidence_backed_fact(
    hass, hass_client, mock_config_entry
):
    """The admin API persists an explicit structured fact."""
    assert await async_setup_component(hass, "http", {})
    mock_config_entry.add_to_hass(hass)
    memory = VoiceMemory(hass, mock_config_entry.entry_id)
    memory._store.async_save = AsyncMock()
    mock_config_entry.runtime_data = SimpleNamespace(memory=memory)
    await async_setup_panel(hass)
    client = await hass_client()

    response = await client.post(
        "/api/llm_gateway/harness/memory/facts",
        json={
            "key": "night_brightness",
            "value": "10%",
            "scope": "intent:light",
            "evidence_turn_id": "turn-explicit",
        },
    )

    assert response.status == 201
    fact = (await response.json())["fact"]
    assert fact["key"] == "night_brightness"
    assert fact["evidence_turn_id"] == "turn-explicit"


async def test_harness_options_api_updates_safe_fields(
    hass, hass_client, mock_config_entry
):
    """The panel can update the safe editable subset of options."""
    assert await async_setup_component(hass, "http", {})
    mock_config_entry.add_to_hass(hass)
    await async_setup_panel(hass)
    client = await hass_client()

    response = await client.post(
        "/api/llm_gateway/harness/options",
        json={
            "entry_id": mock_config_entry.entry_id,
            "options": {
                "routing_mode": ROUTING_MODE_MID,
                "models": {
                    "fast": "fast-model",
                    "mid": "mid-model",
                    "deep": "deep-model",
                },
                "max_tokens": {"fast": 256, "mid": 1024, "deep": 4096},
                "timeouts": {"fast": 12, "mid": 45, "deep": 120},
                "trace": {
                    "enabled": True,
                    "include_raw_messages": False,
                    "max_runs": 40,
                    "retention_hours": 36,
                },
                "first_response_audio": {
                    "enabled": True,
                    "adapter": "local",
                    "local_service": "rest_command.kukui_voice_feedback",
                    "tts_entity": "tts.edge_tts_service_edge_tts",
                    "media_player_entity": "media_player.ke_ting_433",
                },
            },
        },
    )

    assert response.status == 200
    data = await response.json()
    assert data["entry"]["options"]["routing_mode"] == ROUTING_MODE_MID
    assert data["entry"]["options"]["models"]["fast"] == "fast-model"
    assert data["entry"]["options"]["first_response_audio"]["adapter"] == "local"
    assert data["entry"]["options"]["first_response_audio"]["local_service"] == (
        "rest_command.kukui_voice_feedback"
    )
    assert data["entry"]["trace"]["enabled"]
    assert mock_config_entry.options[CONF_FAST_MODEL] == "fast-model"
    assert mock_config_entry.options[CONF_CHAT_MODEL] == "fast-model"
    assert mock_config_entry.options[CONF_FAST_MAX_TOKENS] == 256
    assert mock_config_entry.options[CONF_FAST_CHAT_TIMEOUT] == 12
    assert mock_config_entry.options[CONF_DIAGNOSTIC_TRACES]
    assert mock_config_entry.options[CONF_TRACE_MAX_RUNS] == 40
    assert mock_config_entry.options[CONF_FIRST_RESPONSE_PLAYBACK_ADAPTER] == "local"
    assert mock_config_entry.options[CONF_FIRST_RESPONSE_LOCAL_SERVICE] == (
        "rest_command.kukui_voice_feedback"
    )
    assert mock_config_entry.options[CONF_FIRST_RESPONSE_TTS_ENTITY] == (
        "tts.edge_tts_service_edge_tts"
    )
    assert mock_config_entry.options[CONF_FIRST_RESPONSE_MEDIA_PLAYER] == (
        "media_player.ke_ting_433"
    )


async def test_harness_status_api_redacts_provider_profile_secrets(
    hass, hass_client, mock_config_entry
):
    """Provider fallback profiles are visible without API keys."""
    assert await async_setup_component(hass, "http", {})
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={
            **mock_config_entry.options,
            CONF_PROVIDER_PROFILES: (
                '{"providers":[{"name":"fallback","base_url":"https://fallback.test/v1",'
                '"api_key":"secret","models":{"fast":"fallback-fast"}}]}'
            ),
        },
    )
    await async_setup_panel(hass)
    client = await hass_client()

    response = await client.get("/api/llm_gateway/harness/status")

    assert response.status == 200
    data = await response.json()
    providers = data["entries"][0]["model_providers"]
    assert providers["fallback_enabled"]
    assert providers["fallbacks"][0]["name"] == "fallback"
    assert providers["fallbacks"][0]["has_api_key"] is True
    assert "api_key" not in providers["fallbacks"][0]


async def test_harness_status_api_tolerates_invalid_provider_profiles(
    hass, hass_client, mock_config_entry
):
    """Invalid provider profile JSON is reported, not a status API failure."""
    assert await async_setup_component(hass, "http", {})
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={
            **mock_config_entry.options,
            CONF_PROVIDER_PROFILES: "{bad json",
        },
    )
    await async_setup_panel(hass)
    client = await hass_client()

    response = await client.get("/api/llm_gateway/harness/status")

    assert response.status == 200
    data = await response.json()
    entry = data["entries"][0]
    assert entry["model_providers"]["config_error"]
    assert RECOMMENDED_FAST_MODEL in entry["model_candidates"]


async def test_harness_options_api_rejects_invalid_values(
    hass, hass_client, mock_config_entry
):
    """The panel options API rejects out-of-range values."""
    assert await async_setup_component(hass, "http", {})
    mock_config_entry.add_to_hass(hass)
    await async_setup_panel(hass)
    client = await hass_client()

    response = await client.post(
        "/api/llm_gateway/harness/options",
        json={
            "entry_id": mock_config_entry.entry_id,
            "options": {"timeouts": {"fast": 1, "mid": 45, "deep": 120}},
        },
    )

    assert response.status == 400
    data = await response.json()
    assert data["code"] == "invalid_options"
