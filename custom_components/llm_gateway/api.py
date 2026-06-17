"""Thin async client for an OpenAI-compatible chat endpoint (e.g. NVIDIA NIM)."""

from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any

import aiohttp
from homeassistant.exceptions import HomeAssistantError

from .const import LOGGER, TIMEOUT_CHAT, TIMEOUT_MODELS


class LLMGatewayError(HomeAssistantError):
    """Base error talking to the gateway."""


class LLMGatewayAuthError(LLMGatewayError):
    """Authentication failed (bad or missing API key)."""


class LLMGatewayConnectionError(LLMGatewayError):
    """Could not reach the endpoint."""


class LLMGatewayClient:
    """Minimal OpenAI-compatible client over aiohttp."""

    def __init__(
        self, session: aiohttp.ClientSession, base_url: str, api_key: str
    ) -> None:
        """Initialize the client."""
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def _request(
        self, method: str, path: str, *, json: dict[str, Any] | None, timeout_s: int
    ) -> dict[str, Any]:
        url = f"{self._base_url}/{path.lstrip('/')}"
        try:
            async with self._session.request(
                method,
                url,
                headers=self._headers,
                json=json,
                timeout=aiohttp.ClientTimeout(total=timeout_s),
            ) as resp:
                body = await resp.text()
                if resp.status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
                    raise LLMGatewayAuthError(
                        f"Authentication failed ({resp.status}); check the API key"
                    )
                if resp.status >= HTTPStatus.BAD_REQUEST:
                    raise LLMGatewayError(
                        f"Endpoint returned {resp.status}: {body[:300]}"
                    )
                return _parse_json(body)
        except TimeoutError as err:
            raise LLMGatewayConnectionError(f"Timeout contacting {url}") from err
        except aiohttp.ClientError as err:
            raise LLMGatewayConnectionError(f"Cannot reach {url}: {err}") from err

    async def async_list_models(self) -> list[str]:
        """Return the model ids the endpoint advertises (sorted)."""
        data = await self._request("GET", "models", json=None, timeout_s=TIMEOUT_MODELS)
        models = [m["id"] for m in data.get("data", []) if m.get("id")]
        return sorted(models)

    async def async_chat_completion(  # noqa: PLR0913 - explicit OpenAI-style kwargs
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int,
        temperature: float,
        top_p: float,
    ) -> dict[str, Any]:
        """Run a (non-streaming) chat completion and return the assistant message."""
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
        }
        if tools:
            payload["tools"] = tools
        data = await self._request(
            "POST", "chat/completions", json=payload, timeout_s=TIMEOUT_CHAT
        )
        try:
            return data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as err:
            LOGGER.debug("Unexpected completion payload: %s", data)
            raise LLMGatewayError("Malformed response from endpoint") from err


def _parse_json(body: str) -> dict[str, Any]:
    try:
        return json.loads(body)
    except ValueError as err:
        raise LLMGatewayError(f"Non-JSON response: {body[:200]}") from err
