"""Thin async client for an OpenAI-compatible chat endpoint."""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import asdict, dataclass
from http import HTTPStatus
from typing import Any

import aiohttp
from homeassistant.exceptions import HomeAssistantError

from .const import LOGGER, TIMEOUT_CHAT, TIMEOUT_MODELS

type ToolChoice = str | dict[str, Any]

PROBE_SYSTEM_PROMPT = "You are a concise voice assistant."
PROBE_USER_PROMPT = "用一句简短的话介绍你自己。"
PROBE_MAX_TOKENS = 32
PROBE_TIMEOUT_S = 25


@dataclass(slots=True)
class ModelCatalogFetch:
    """One provider /models exchange, validator-aware for caching."""

    models: list[str]
    etag: str | None = None
    last_modified: str | None = None
    not_modified: bool = False


@dataclass(slots=True)
class LatencySample:
    """One streaming latency measurement for a single model."""

    model: str
    ok: bool
    ttft_ms: float | None = None
    tokens: int = 0
    tps: float | None = None
    total_ms: float | None = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe view of the sample."""
        return asdict(self)


class LLMGatewayError(HomeAssistantError):
    """Base error talking to the gateway."""


class LLMGatewayAuthError(LLMGatewayError):
    """Authentication failed (bad or missing API key)."""


class LLMGatewayConnectionError(LLMGatewayError):
    """Could not reach the endpoint."""


class LLMGatewayQuotaExhaustedError(LLMGatewayError):
    """Terminal provider-side quota/balance exhaustion (never retryable)."""


class LLMGatewayCatalogNotModifiedError(LLMGatewayError):
    """Model catalog revalidation answered 304 Not Modified."""

    def __init__(self, *, etag: str | None, last_modified: str | None) -> None:
        super().__init__("Catalog not modified")
        self.etag = etag
        self.last_modified = last_modified


class LLMGatewayHTTPError(LLMGatewayError):
    """Endpoint returned an HTTP error status."""

    def __init__(self, status: int, body: str) -> None:
        """Initialize the HTTP error."""
        self.status = status
        self.body = body
        super().__init__(f"Endpoint returned {status}: {body[:300]}")


# Terminal wording means the account itself is out of budget — retrying can
# never succeed and only burns time. Transient rate limits (plain 429 without
# this wording) deliberately stay LLMGatewayHTTPError.
_QUOTA_EXHAUSTED_RE = re.compile(
    r"\binsufficient[\s_-]+(?:quota|balance|credits?)\b"
    r"|\b(?:quota|usage[\s_-]+limit)[\s_-]+(?:exceeded|exhausted|reached)\b"
    r"|\bexceed(?:ed|s)?[\s_-]+(?:(?:your|the)[\s_-]+)?(?:current[\s_-]+)?quota\b"
    r"|\b(?:balance|credits?)[\s_-]+(?:exhausted|depleted)\b"
    r"|\bout[\s_-]+of[\s_-]+(?:credits?|budget)\b",
    re.IGNORECASE,
)


def _is_quota_exhausted(detail: str) -> bool:
    """Return True for provider text identifying an exhausted account quota."""
    return bool(_QUOTA_EXHAUSTED_RE.search(detail or ""))


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

    async def _request(  # noqa: PLR0913 - explicit keyword flags beat a params blob
        self,
        method: str,
        path: str,
        *,
        json_payload: dict[str, Any] | None,
        timeout_s: int,
        extra_headers: dict[str, str] | None = None,
        allow_not_modified: bool = False,
        return_headers: bool = False,
    ) -> dict[str, Any] | tuple[dict[str, Any], str | None, str | None]:
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
                request_headers = dict(self._headers)
                if extra_headers:
                    request_headers.update(extra_headers)
                async with self._session.request(
                    method,
                    url,
                    headers=request_headers,
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
                    etag = resp.headers.get("ETag")
                    last_modified = resp.headers.get("Last-Modified")
                    if allow_not_modified and resp.status == HTTPStatus.NOT_MODIFIED:
                        raise LLMGatewayCatalogNotModifiedError(
                            etag=etag or last_modified,
                            last_modified=last_modified,
                        )
                    if resp.status >= HTTPStatus.BAD_REQUEST:
                        if _is_quota_exhausted(body):
                            raise LLMGatewayQuotaExhaustedError(
                                f"Provider quota or balance exhausted ({resp.status})"
                            )
                        raise LLMGatewayHTTPError(resp.status, body)
                    data = _parse_json(body)
                    if return_headers:
                        return data, etag, last_modified
                    return data
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
        fetch = await self.async_list_models_conditional()
        return fetch.models

    async def async_list_models_conditional(
        self,
        *,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> ModelCatalogFetch:
        """Fetch the catalog with conditional validators for caching."""
        headers: dict[str, str] = {}
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified
        try:
            data, etag_out, last_modified_out = await self._request(
                "GET",
                "models",
                json_payload=None,
                timeout_s=TIMEOUT_MODELS,
                extra_headers=headers or None,
                allow_not_modified=bool(headers),
                return_headers=True,
            )
        except LLMGatewayCatalogNotModifiedError as err:
            return ModelCatalogFetch(
                models=[],
                etag=err.etag,
                last_modified=err.last_modified,
                not_modified=True,
            )
        models = [m["id"] for m in data.get("data", []) if m.get("id")]
        return ModelCatalogFetch(
            models=sorted(models),
            etag=etag_out,
            last_modified=last_modified_out,
        )

    async def async_probe_latency(
        self,
        *,
        model: str,
        max_tokens: int = PROBE_MAX_TOKENS,
        timeout_s: int = PROBE_TIMEOUT_S,
    ) -> LatencySample:
        """Stream a tiny completion and measure TTFT plus decode speed."""
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": PROBE_SYSTEM_PROMPT},
                {"role": "user", "content": PROBE_USER_PROMPT},
            ],
            "max_tokens": max(1, max_tokens),
            "stream": True,
        }
        url = f"{self._base_url}/chat/completions"
        started = time.monotonic()
        LOGGER.info(
            "Latency probe started model=%s max_tokens=%d timeout_s=%d",
            model,
            max_tokens,
            timeout_s,
        )
        try:
            async with asyncio.timeout(timeout_s):
                async with self._session.post(
                    url,
                    headers=self._headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=max(1, timeout_s)),
                ) as resp:
                    if resp.status in (
                        HTTPStatus.UNAUTHORIZED,
                        HTTPStatus.FORBIDDEN,
                    ):
                        raise LLMGatewayAuthError(
                            f"Authentication failed ({resp.status})"
                        )
                    if resp.status >= HTTPStatus.BAD_REQUEST:
                        raise LLMGatewayHTTPError(resp.status, await resp.text())
                    sample = await _consume_probe_stream(resp, model, started)
        except TimeoutError as err:
            raise LLMGatewayConnectionError(f"Timeout probing {model}") from err
        except aiohttp.ClientError as err:
            raise LLMGatewayConnectionError(f"Cannot reach {url}: {err}") from err
        LOGGER.info(
            "Latency probe completed model=%s ok=%s ttft_ms=%s tokens=%d tps=%s",
            model,
            sample.ok,
            sample.ttft_ms,
            sample.tokens,
            sample.tps,
        )
        return sample

    async def async_chat_completion(  # noqa: PLR0913 - explicit OpenAI-style kwargs
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: ToolChoice | None = None,
        extra_body: dict[str, Any] | None = None,
        timeout_s: int = TIMEOUT_CHAT,
        max_tokens: int,
        temperature: float,
        top_p: float,
    ) -> dict[str, Any]:
        """Run a non-streaming chat completion; return (message, usage)."""
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
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as err:
            LOGGER.debug("Unexpected completion payload: %s", data)
            raise LLMGatewayError("Malformed response from endpoint") from err
        return message, _parse_usage(data)


def _parse_json(body: str) -> dict[str, Any]:
    try:
        return json.loads(body)
    except ValueError as err:
        raise LLMGatewayError(f"Non-JSON response: {body[:200]}") from err


def _delta_text(chunk: dict[str, Any]) -> str:
    """Return assistant content text carried by one SSE chunk, if any."""
    try:
        delta = chunk["choices"][0]["delta"]
    except (KeyError, IndexError, TypeError):
        return ""
    content = delta.get("content") if isinstance(delta, dict) else None
    return str(content) if content else ""


def _parse_usage(data: dict[str, Any]) -> dict[str, int] | None:
    """Extract provider-neutral token usage from a completion response.

    Normalizes OpenAI (`prompt_tokens` + `prompt_tokens_details.cached_tokens`)
    and DeepSeek (`prompt_cache_hit_tokens`) shapes into four buckets; returns
    None when the provider reports nothing usable.
    """
    raw = data.get("usage")
    if not isinstance(raw, dict):
        return None

    def _int(value: object) -> int | None:
        return value if isinstance(value, int) and value >= 0 else None

    prompt = _int(raw.get("prompt_tokens"))
    completion = _int(raw.get("completion_tokens"))
    details = raw.get("prompt_tokens_details")
    cached = (
        _int(details.get("cached_tokens")) if isinstance(details, dict) else None
    ) or _int(raw.get("prompt_cache_hit_tokens"))
    total = _int(raw.get("total_tokens"))
    if total is None and (prompt is not None or completion is not None):
        total = (prompt or 0) + (completion or 0)
    usage: dict[str, int] = {}
    if prompt is not None:
        usage["input_tokens"] = prompt
    if completion is not None:
        usage["output_tokens"] = completion
    if total is not None:
        usage["total_tokens"] = total
    if cached is not None:
        usage["cached_input_tokens"] = cached
    return usage or None


async def _consume_probe_stream(
    resp: aiohttp.ClientResponse,
    model: str,
    started: float,
) -> LatencySample:
    """Read an SSE completion stream, timing the first content chunk."""
    ttft_ms: float | None = None
    tokens = 0
    first_at: float | None = None
    last_at: float | None = None
    async for raw in resp.content:
        line = raw.decode("utf-8", "replace").strip()
        if not line.startswith("data:"):
            continue
        body = line[5:].strip()
        if body == "[DONE]":
            break
        try:
            chunk = json.loads(body)
        except ValueError:
            continue
        if not _delta_text(chunk):
            # Reasoning-only deltas (deepseek-r1 style) are skipped on
            # purpose: they never reach the audio path, so they must not
            # count towards TTFT.
            continue
        now = time.monotonic()
        last_at = now
        if first_at is None:
            first_at = now
            ttft_ms = (now - started) * 1000
        tokens += 1
    total_ms = (time.monotonic() - started) * 1000
    if ttft_ms is None:
        return LatencySample(
            model=model,
            ok=False,
            error="no_content",
            total_ms=round(total_ms, 1),
        )
    tps: float | None = None
    if first_at is not None and last_at is not None and tokens > 1:
        span = last_at - first_at
        if span > 0:
            tps = round((tokens - 1) / span, 1)
    return LatencySample(
        model=model,
        ok=True,
        ttft_ms=round(ttft_ms, 1),
        tokens=tokens,
        tps=tps,
        total_ms=round(total_ms, 1),
    )
