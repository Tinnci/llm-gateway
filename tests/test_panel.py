"""Tests for the Voice Harness panel."""

from __future__ import annotations

from types import SimpleNamespace

from homeassistant.components import frontend
from homeassistant.setup import async_setup_component

from custom_components.llm_gateway.const import (
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
    CONF_TRACE_INCLUDE_RAW_MESSAGES,
    CONF_TRACE_MAX_RUNS,
    CONF_TRACE_RETENTION_HOURS,
    ROUTING_MODE_MID,
)
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
    assert panel.config["_panel_custom"]["name"] == "voice-harness-panel"
    assert panel.config["_panel_custom"]["module_url"] == PANEL_MODULE
    assert panel.config["api_base"] == "/api/llm_gateway"


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
            "metrics": {
                "phase": "streaming",
                "interim_results": 1,
                "final_results": 0,
                "frames": 3,
                "first_result_latency_ms": 120,
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
    assert data["satellite"]["diagnostic_snapshot"]["schema_version"] == 1
    assert data["satellite"]["diagnostic_snapshot"]["pipewire_graph"]["aec_enabled"]
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
    mock_config_entry.runtime_data = SimpleNamespace(trace_store=trace_store)
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
    assert len(data["records"]) == 30
    assert data["records"][0]["input"]["conversation_id"] == "conv-30"
    assert data["records"][0]["debug_flags"]["search"] is False
    assert data["records"][0]["verifier_mode"] == "disabled"
    assert data["records"][0]["actions"][0]["domain"] == "light"
    assert "raw_payload" not in data["records"][0]


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
    assert record["raw_payload"]["speech"]["tts_cleaned"] is True

    missing = await client.get("/api/llm_gateway/harness/runs/not-found")
    assert missing.status == 404


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
