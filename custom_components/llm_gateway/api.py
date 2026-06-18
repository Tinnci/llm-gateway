"""Thin async client for an OpenAI-compatible chat endpoint."""

from __future__ import annotations

import asyncio
import json
import time
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


class LLMGatewayHTTPError(LLMGatewayError):
    """Endpoint returned an HTTP error status."""

    def __init__(self, status: int, body: str) -> None:
        """Initialize the HTTP error."""
        self.status = status
        self.body = body
        super().__init__(f"Endpoint returned {status}: {body[:300]}")


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
        self,
        method: str,
        path: str,
        *,
        json_payload: dict[str, Any] | None,
        timeout_s: int,
    ) -> dict[str, Any]:
        url = f"{self._base_url}/{path.lstrip('/')}"
        started = time.monotonic()
        timeout_s = max(1, int(timeout_s))
        payload_bytes = (
            len(json.dumps(json_payload, ensure_ascii=False).encode())
            if json_payload is not None
            else 0
        )
        LOGGER.info(
            "Gateway request started method=%s path=%s payload_bytes=%d timeout_s=%d",
            method,
            path,
            payload_bytes,
            timeout_s,
        )
        try:
            async with asyncio.timeout(timeout_s):
                async with self._session.request(
                    method,
                    url,
                    headers=self._headers,
                    json=json_payload,
                    timeout=aiohttp.ClientTimeout(total=timeout_s),
                ) as resp:
                    body = await resp.text()
                    LOGGER.info(
                        "Gateway request completed method=%s path=%s status=%d "
                        "elapsed_s=%.3f response_bytes=%d",
                        method,
                        path,
                        resp.status,
                        time.monotonic() - started,
                        len(body.encode()),
                    )
                    if resp.status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
                        raise LLMGatewayAuthError(
                            f"Authentication failed ({resp.status}); check the API key"
                        )
                    if resp.status >= HTTPStatus.BAD_REQUEST:
                        raise LLMGatewayHTTPError(resp.status, body)
                    return _parse_json(body)
        except TimeoutError as err:
            LOGGER.warning(
                "Gateway request timed out method=%s path=%s elapsed_s=%.3f "
                "payload_bytes=%d timeout_s=%d",
                method,
                path,
                time.monotonic() - started,
                payload_bytes,
                timeout_s,
            )
            raise LLMGatewayConnectionError(f"Timeout contacting {url}") from err
        except aiohttp.ClientError as err:
            LOGGER.warning(
                "Gateway request failed method=%s path=%s elapsed_s=%.3f error=%s",
                method,
                path,
                time.monotonic() - started,
                type(err).__name__,
            )
            raise LLMGatewayConnectionError(f"Cannot reach {url}: {err}") from err

    async def async_list_models(self) -> list[str]:
        """Return the model ids the endpoint advertises (sorted)."""
        data = await self._request(
            "GET", "models", json_payload=None, timeout_s=TIMEOUT_MODELS
        )
        models = [m["id"] for m in data.get("data", []) if m.get("id")]
        return sorted(models)

    async def async_chat_completion(  # noqa: PLR0913 - explicit OpenAI-style kwargs
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
        extra_body: dict[str, Any] | None = None,
        timeout_s: int = TIMEOUT_CHAT,
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
        for key, value in (extra_body or {}).items():
            if key == "stream":
                LOGGER.warning("Ignoring unsupported streaming extra_body option")
                continue
            if key in payload:
                LOGGER.warning("Ignoring extra_body override for reserved key: %s", key)
                continue
            payload[key] = value
        if tools:
            payload["tools"] = tools
            if tool_choice:
                payload["tool_choice"] = tool_choice
        LOGGER.info(
            "Chat completion model=%s messages=%d tools=%d tool_choice=%s "
            "max_tokens=%d extra_body_keys=%s",
            model,
            len(messages),
            len(tools or []),
            tool_choice or "auto",
            max_tokens,
            ",".join(sorted((extra_body or {}).keys())) or "none",
        )
        data = await self._request(
            "POST",
            "chat/completions",
            json_payload=payload,
            timeout_s=timeout_s,
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
