from types import SimpleNamespace

from homeassistant.const import CONF_API_KEY, CONF_PROMPT
from homeassistant.helpers.redact import REDACTED

from custom_components.llm_gateway.diagnostics import async_get_config_entry_diagnostics
from custom_components.llm_gateway.system_health import system_health_info


class _TraceStore:
    def snapshot(self, *, include_raw: bool = True):
        assert include_raw is False
        return {
            "records": [{"user_text": "private"}],
            "storage": {"records": 2, "compressed_bytes": 123},
        }


class _ProviderSelector:
    def snapshot(self):
        return [
            {
                "provider": "primary",
                "route": "fast",
                "failures": 1,
                "cooldown_remaining_s": 5,
                "last_error": "secret-bearing provider error",
            }
        ]


async def test_diagnostics_redacts_secrets_and_omits_turn_text(hass, mock_config_entry):
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        data={**mock_config_entry.data, CONF_API_KEY: "secret-key"},
        options={CONF_PROMPT: "private prompt", "fast_model": "model-a"},
    )
    mock_config_entry.runtime_data = SimpleNamespace(
        trace_store=_TraceStore(),
        provider_selector=_ProviderSelector(),
        turn_controller=SimpleNamespace(current_turn_id="turn-private"),
        voice_runs=SimpleNamespace(snapshot=lambda: [{"user_text": "private"}]),
    )

    result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    assert result["entry"][CONF_API_KEY] == REDACTED
    assert result["options"][CONF_PROMPT] == REDACTED
    assert result["options"]["fast_model"] == "model-a"
    assert result["runtime"]["trace_records"] == 2
    assert "last_error" not in result["runtime"]["provider_health"][0]
    assert "private" not in str(result)


async def test_system_health_is_aggregate_only(hass, mock_config_entry):
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry, options={"diagnostic_traces": True}
    )
    mock_config_entry.runtime_data = SimpleNamespace(
        provider_selector=_ProviderSelector()
    )

    result = await system_health_info(hass)

    assert result == {
        "configured_entries": 1,
        "loaded_entries": 1,
        "provider_failures": 1,
        "providers_in_cooldown": 1,
        "diagnostic_traces_enabled": True,
    }
