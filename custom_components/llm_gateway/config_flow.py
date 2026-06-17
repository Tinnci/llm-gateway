"""Config flow for the LLM Gateway integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_API_KEY, CONF_LLM_HASS_API, CONF_PROMPT
from homeassistant.core import callback
from homeassistant.helpers import llm
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TemplateSelector,
)

from .api import LLMGatewayAuthError, LLMGatewayClient, LLMGatewayError
from .const import (
    CONF_BASE_URL,
    CONF_CHAT_MODEL,
    CONF_MAX_TOKENS,
    CONF_TEMPERATURE,
    CONF_TOP_P,
    DEFAULT_BASE_URL,
    DEFAULT_NAME,
    DOMAIN,
    RECOMMENDED_CHAT_MODEL,
    RECOMMENDED_MAX_TOKENS,
    RECOMMENDED_TEMPERATURE,
    RECOMMENDED_TOP_P,
)

if TYPE_CHECKING:
    from .config_entry import LLMGatewayConfigEntry

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
        vol.Required(CONF_API_KEY): str,
    }
)


class LLMGatewayConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the LLM Gateway config flow."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the connection step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            client = LLMGatewayClient(
                async_get_clientsession(self.hass),
                user_input[CONF_BASE_URL],
                user_input[CONF_API_KEY],
            )
            try:
                await client.async_list_models()
            except LLMGatewayAuthError:
                errors["base"] = "invalid_auth"
            except LLMGatewayError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title=DEFAULT_NAME, data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: LLMGatewayConfigEntry,  # noqa: ARG004 - HA-supplied, unused
    ) -> LLMGatewayOptionsFlow:
        """Return the options flow."""
        return LLMGatewayOptionsFlow()


class LLMGatewayOptionsFlow(OptionsFlow):
    """Handle options: model selection and generation settings."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            # An empty multi-select means "no Home Assistant control".
            if not user_input.get(CONF_LLM_HASS_API):
                user_input.pop(CONF_LLM_HASS_API, None)
            return self.async_create_entry(title="", data=user_input)

        entry: LLMGatewayConfigEntry = self.config_entry
        client = LLMGatewayClient(
            async_get_clientsession(self.hass),
            entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL),
            entry.data[CONF_API_KEY],
        )
        try:
            models = await client.async_list_models()
        except LLMGatewayError:
            models = []
        if RECOMMENDED_CHAT_MODEL not in models:
            models = [RECOMMENDED_CHAT_MODEL, *models]
        model_options = [SelectOptionDict(value=m, label=m) for m in models]

        hass_apis = [
            SelectOptionDict(value=api.id, label=api.name)
            for api in llm.async_get_apis(self.hass)
        ]

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_CHAT_MODEL, default=RECOMMENDED_CHAT_MODEL
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=model_options,
                        mode=SelectSelectorMode.DROPDOWN,
                        custom_value=True,
                    )
                ),
                vol.Optional(CONF_LLM_HASS_API): SelectSelector(
                    SelectSelectorConfig(options=hass_apis, multiple=True)
                ),
                vol.Optional(CONF_PROMPT): TemplateSelector(),
                vol.Optional(
                    CONF_MAX_TOKENS, default=RECOMMENDED_MAX_TOKENS
                ): NumberSelector(
                    NumberSelectorConfig(min=1, max=8192, mode=NumberSelectorMode.BOX)
                ),
                vol.Optional(
                    CONF_TEMPERATURE, default=RECOMMENDED_TEMPERATURE
                ): NumberSelector(NumberSelectorConfig(min=0, max=2, step=0.05)),
                vol.Optional(CONF_TOP_P, default=RECOMMENDED_TOP_P): NumberSelector(
                    NumberSelectorConfig(min=0, max=1, step=0.05)
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                schema, dict(self.config_entry.options)
            ),
        )
