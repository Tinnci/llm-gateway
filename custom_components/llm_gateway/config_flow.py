"""Config flow for the LLM Gateway integration."""

from __future__ import annotations

import json
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
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TemplateSelector,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import LLMGatewayAuthError, LLMGatewayClient, LLMGatewayError
from .const import (
    CONF_BASE_URL,
    CONF_BRAVE_API_KEY,
    CONF_CHAT_MODEL,
    CONF_CHAT_TIMEOUT,
    CONF_DEEP_CHAT_TIMEOUT,
    CONF_DEEP_EXTRA_BODY,
    CONF_DEEP_MAX_TOKENS,
    CONF_DEEP_MODEL,
    CONF_EXTRA_BODY,
    CONF_FAST_CHAT_TIMEOUT,
    CONF_FAST_EXTRA_BODY,
    CONF_FAST_MAX_TOKENS,
    CONF_FAST_MODEL,
    CONF_FIRECRAWL_API_KEY,
    CONF_MAX_TOKENS,
    CONF_MID_CHAT_TIMEOUT,
    CONF_MID_EXTRA_BODY,
    CONF_MID_MAX_TOKENS,
    CONF_MID_MODEL,
    CONF_ROUTING_MODE,
    CONF_SEARCH_ENABLED,
    CONF_SERPER_API_KEY,
    CONF_TAVILY_API_KEY,
    CONF_TEMPERATURE,
    CONF_TOP_P,
    DEFAULT_BASE_URL,
    DEFAULT_NAME,
    DOMAIN,
    MAX_CHAT_TIMEOUT,
    MAX_CONFIGURED_TOKENS,
    RECOMMENDED_CHAT_MODEL,
    RECOMMENDED_CHAT_TIMEOUT,
    RECOMMENDED_DEEP_CHAT_TIMEOUT,
    RECOMMENDED_DEEP_FALLBACK_MODEL,
    RECOMMENDED_DEEP_MAX_TOKENS,
    RECOMMENDED_DEEP_MODEL,
    RECOMMENDED_FAST_CHAT_TIMEOUT,
    RECOMMENDED_FAST_MAX_TOKENS,
    RECOMMENDED_FAST_MODEL,
    RECOMMENDED_MAX_TOKENS,
    RECOMMENDED_MID_CHAT_TIMEOUT,
    RECOMMENDED_MID_MAX_TOKENS,
    RECOMMENDED_MID_MODEL,
    RECOMMENDED_TEMPERATURE,
    RECOMMENDED_TOP_P,
    ROUTING_MODE_AUTO,
    ROUTING_MODES,
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
        errors: dict[str, str] = {}
        if user_input is not None:
            # An empty multi-select means "no Home Assistant control".
            if not user_input.get(CONF_LLM_HASS_API):
                user_input.pop(CONF_LLM_HASS_API, None)
            if user_input.get(CONF_CHAT_MODEL) and not user_input.get(CONF_FAST_MODEL):
                user_input[CONF_FAST_MODEL] = user_input[CONF_CHAT_MODEL]
            for field in (
                CONF_EXTRA_BODY,
                CONF_FAST_EXTRA_BODY,
                CONF_MID_EXTRA_BODY,
                CONF_DEEP_EXTRA_BODY,
            ):
                _normalize_json_option(user_input, errors, field)
            for field in (
                CONF_TAVILY_API_KEY,
                CONF_SERPER_API_KEY,
                CONF_FIRECRAWL_API_KEY,
                CONF_BRAVE_API_KEY,
            ):
                _normalize_optional_string(user_input, field)

            if not errors:
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
        for recommended in (
            RECOMMENDED_FAST_MODEL,
            RECOMMENDED_MID_MODEL,
            RECOMMENDED_DEEP_MODEL,
            RECOMMENDED_DEEP_FALLBACK_MODEL,
            RECOMMENDED_CHAT_MODEL,
        ):
            if recommended not in models:
                models = [recommended, *models]
        model_options = [SelectOptionDict(value=m, label=m) for m in models]
        routing_options = [
            SelectOptionDict(value=mode, label=mode) for mode in ROUTING_MODES
        ]

        hass_apis = [
            SelectOptionDict(value=api.id, label=api.name)
            for api in llm.async_get_apis(self.hass)
        ]

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_ROUTING_MODE, default=ROUTING_MODE_AUTO
                ): SelectSelector(
                    SelectSelectorConfig(options=routing_options)
                ),
                vol.Required(
                    CONF_FAST_MODEL, default=RECOMMENDED_FAST_MODEL
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=model_options,
                        mode=SelectSelectorMode.DROPDOWN,
                        custom_value=True,
                    )
                ),
                vol.Required(
                    CONF_MID_MODEL, default=RECOMMENDED_MID_MODEL
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=model_options,
                        mode=SelectSelectorMode.DROPDOWN,
                        custom_value=True,
                    )
                ),
                vol.Required(
                    CONF_DEEP_MODEL, default=RECOMMENDED_DEEP_MODEL
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
                    NumberSelectorConfig(
                        min=1,
                        max=MAX_CONFIGURED_TOKENS,
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_FAST_MAX_TOKENS, default=RECOMMENDED_FAST_MAX_TOKENS
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1,
                        max=MAX_CONFIGURED_TOKENS,
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_MID_MAX_TOKENS, default=RECOMMENDED_MID_MAX_TOKENS
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1,
                        max=MAX_CONFIGURED_TOKENS,
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_DEEP_MAX_TOKENS, default=RECOMMENDED_DEEP_MAX_TOKENS
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1,
                        max=MAX_CONFIGURED_TOKENS,
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_TEMPERATURE, default=RECOMMENDED_TEMPERATURE
                ): NumberSelector(NumberSelectorConfig(min=0, max=2, step=0.05)),
                vol.Optional(CONF_TOP_P, default=RECOMMENDED_TOP_P): NumberSelector(
                    NumberSelectorConfig(min=0, max=1, step=0.05)
                ),
                vol.Optional(CONF_EXTRA_BODY): TextSelector(
                    TextSelectorConfig(multiline=True)
                ),
                vol.Optional(CONF_FAST_EXTRA_BODY): TextSelector(
                    TextSelectorConfig(multiline=True)
                ),
                vol.Optional(CONF_MID_EXTRA_BODY): TextSelector(
                    TextSelectorConfig(multiline=True)
                ),
                vol.Optional(CONF_DEEP_EXTRA_BODY): TextSelector(
                    TextSelectorConfig(multiline=True)
                ),
                vol.Optional(
                    CONF_CHAT_TIMEOUT, default=RECOMMENDED_CHAT_TIMEOUT
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=5,
                        max=MAX_CHAT_TIMEOUT,
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_FAST_CHAT_TIMEOUT, default=RECOMMENDED_FAST_CHAT_TIMEOUT
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=5,
                        max=MAX_CHAT_TIMEOUT,
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_MID_CHAT_TIMEOUT, default=RECOMMENDED_MID_CHAT_TIMEOUT
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=5,
                        max=MAX_CHAT_TIMEOUT,
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_DEEP_CHAT_TIMEOUT, default=RECOMMENDED_DEEP_CHAT_TIMEOUT
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=5,
                        max=MAX_CHAT_TIMEOUT,
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(CONF_SEARCH_ENABLED, default=False): BooleanSelector(),
                vol.Optional(CONF_TAVILY_API_KEY): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
                vol.Optional(CONF_SERPER_API_KEY): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
                vol.Optional(CONF_FIRECRAWL_API_KEY): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
                vol.Optional(CONF_BRAVE_API_KEY): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
            }
        )

        suggested = dict(self.config_entry.options)
        if CONF_CHAT_MODEL in suggested and CONF_FAST_MODEL not in suggested:
            suggested[CONF_FAST_MODEL] = suggested[CONF_CHAT_MODEL]

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                schema, suggested
            ),
            errors=errors,
        )


def _normalize_json_option(
    user_input: dict[str, Any], errors: dict[str, str], field: str
) -> None:
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


def _normalize_optional_string(user_input: dict[str, Any], field: str) -> None:
    value = (user_input.get(field) or "").strip()
    if value:
        user_input[field] = value
    else:
        user_input.pop(field, None)
