"""Provider profile parsing and ordered chat failover."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

import aiohttp

from .api import (
    LLMGatewayAuthError,
    LLMGatewayClient,
    LLMGatewayConnectionError,
    LLMGatewayError,
    LLMGatewayHTTPError,
)
from .const import CONF_PROVIDER_PROFILES, LOGGER
from .router import ModelRoute

PROFILE_TEXT_LIMIT = 64
MODEL_TEXT_LIMIT = 256
DEFAULT_SOFT_TIMEOUTS = {"fast": 3, "mid": 8, "deep": 30}


@dataclass(frozen=True, slots=True)
class ProviderProfile:
    """One OpenAI-compatible provider profile."""

    name: str
    base_url: str
    api_key: str
    models: dict[str, str]
    soft_timeouts: dict[str, int]
    max_tokens: dict[str, int]
    extra_body: dict[str, dict[str, Any]]

    def safe_dict(self) -> dict[str, Any]:
        """Return metadata safe for traces and panels."""
        return {
            "name": self.name,
            "base_url": self.base_url,
            "models": dict(self.models),
            "soft_timeouts": dict(self.soft_timeouts),
            "max_tokens": dict(self.max_tokens),
            "has_api_key": bool(self.api_key),
        }


@dataclass(frozen=True, slots=True)
class ProviderAttempt:
    """One provider attempt result for diagnostics."""

    provider: str
    model: str
    status: str
    latency_ms: int
    error: str = ""
    retryable: bool = False

    def as_dict(self) -> dict[str, Any]:
        """Return a serializable attempt record."""
        return {
            "provider": self.provider,
            "model": self.model,
            "status": self.status,
            "latency_ms": self.latency_ms,
            "error": self.error,
            "retryable": self.retryable,
        }


@dataclass(frozen=True, slots=True)
class ChatFallbackResult:
    """Chat completion result plus provider diagnostics."""

    message: dict[str, Any]
    provider: dict[str, Any]
    attempts: list[dict[str, Any]]


def provider_profiles_from_options(options: dict[str, Any]) -> list[ProviderProfile]:
    """Parse configured fallback provider profiles."""
    raw = options.get(CONF_PROVIDER_PROFILES)
    if raw in (None, ""):
        return []
    return parse_provider_profiles(raw)


def parse_provider_profiles(raw: object) -> list[ProviderProfile]:
    """Parse provider profiles from JSON text or already-decoded data."""
    data = _decode_profiles(raw)
    if isinstance(data, dict):
        data = data.get("providers")
    if data in (None, ""):
        return []
    if not isinstance(data, list):
        raise ValueError("provider_profiles must be a list or {providers: [...]}")

    profiles: list[ProviderProfile] = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"provider profile {index} must be an object")
        profiles.append(_profile_from_dict(item, index))
    return profiles


def normalize_provider_profiles_json(raw: object) -> str:
    """Validate and compact provider profiles JSON for config storage."""
    profiles = parse_provider_profiles(raw)
    return json.dumps(
        {"providers": [_profile_to_storage_dict(profile) for profile in profiles]},
        ensure_ascii=False,
        separators=(",", ":"),
    )


async def async_chat_completion_with_fallback(  # noqa: PLR0913
    *,
    session: aiohttp.ClientSession,
    primary_client: LLMGatewayClient,
    route: ModelRoute,
    options: dict[str, Any],
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
    tool_choice: str | None,
    temperature: float,
    top_p: float,
) -> ChatFallbackResult:
    """Run chat completion through primary provider and ordered fallbacks."""
    attempts: list[ProviderAttempt] = []
    candidates = [
        ("primary", primary_client, route),
        *[
            (
                profile.name,
                LLMGatewayClient(session, profile.base_url, profile.api_key),
                route_for_provider(route, profile),
            )
            for profile in provider_profiles_from_options(options)
        ],
    ]

    last_error: LLMGatewayError | None = None
    for index, (provider_name, client, candidate_route) in enumerate(candidates):
        started = time.monotonic()
        try:
            message = await client.async_chat_completion(
                model=candidate_route.model,
                messages=messages,
                tools=tools,
                tool_choice=tool_choice,
                extra_body=candidate_route.extra_body,
                timeout_s=candidate_route.timeout_s,
                max_tokens=candidate_route.max_tokens,
                temperature=temperature,
                top_p=top_p,
            )
        except LLMGatewayError as err:
            retryable = _is_retryable(err)
            last_error = err
            attempts.append(
                ProviderAttempt(
                    provider=provider_name,
                    model=candidate_route.model,
                    status="error",
                    latency_ms=int((time.monotonic() - started) * 1000),
                    error=type(err).__name__,
                    retryable=retryable,
                )
            )
            LOGGER.warning(
                "Provider attempt failed provider=%s model=%s route=%s "
                "retryable=%s error=%s",
                provider_name,
                candidate_route.model,
                candidate_route.kind,
                retryable,
                type(err).__name__,
            )
            if not retryable or index == len(candidates) - 1:
                raise
            continue

        attempts.append(
            ProviderAttempt(
                provider=provider_name,
                model=candidate_route.model,
                status="complete",
                latency_ms=int((time.monotonic() - started) * 1000),
            )
        )
        if index:
            LOGGER.info(
                "Provider fallback succeeded provider=%s model=%s route=%s attempts=%d",
                provider_name,
                candidate_route.model,
                candidate_route.kind,
                len(attempts),
            )
        return ChatFallbackResult(
            message=message,
            provider={
                "name": provider_name,
                "model": candidate_route.model,
                "fallback_used": index > 0,
                "fallback_reason": type(last_error).__name__ if index else "",
            },
            attempts=[attempt.as_dict() for attempt in attempts],
        )

    raise LLMGatewayConnectionError("No provider candidates available")


def route_for_provider(route: ModelRoute, profile: ProviderProfile) -> ModelRoute:
    """Return route settings overridden by a fallback provider profile."""
    kind = route.kind
    return ModelRoute(
        kind=route.kind,
        model=profile.models.get(kind) or route.model,
        max_tokens=profile.max_tokens.get(kind) or route.max_tokens,
        timeout_s=profile.soft_timeouts.get(kind) or route.timeout_s,
        extra_body=profile.extra_body.get(kind) or route.extra_body,
        async_deep_task=route.async_deep_task,
    )


def _decode_profiles(raw: object) -> object:
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        try:
            return json.loads(text)
        except ValueError as err:
            raise ValueError("provider_profiles must be valid JSON") from err
    return raw


def _profile_from_dict(data: dict[str, Any], index: int) -> ProviderProfile:
    name = _text(data.get("name") or f"provider-{index}", "name", PROFILE_TEXT_LIMIT)
    base_url = _text(data.get("base_url"), f"{name}.base_url", 512).rstrip("/")
    api_key = _text(data.get("api_key"), f"{name}.api_key", 4096)
    if not base_url.startswith(("http://", "https://")):
        raise ValueError(f"{name}.base_url must start with http:// or https://")

    models = _tier_text_map(data, "model")
    soft_timeouts = _tier_int_map(
        data.get("soft_timeout_s") or data.get("timeouts"),
        default=DEFAULT_SOFT_TIMEOUTS,
        field=f"{name}.soft_timeout_s",
        minimum=1,
        maximum=300,
    )
    max_tokens = _tier_int_map(
        data.get("max_tokens"),
        default={},
        field=f"{name}.max_tokens",
        minimum=1,
        maximum=16384,
    )
    extra_body = _tier_object_map(data.get("extra_body"), f"{name}.extra_body")

    return ProviderProfile(
        name=name,
        base_url=base_url,
        api_key=api_key,
        models=models,
        soft_timeouts=soft_timeouts,
        max_tokens=max_tokens,
        extra_body=extra_body,
    )


def _profile_to_storage_dict(profile: ProviderProfile) -> dict[str, Any]:
    return {
        "name": profile.name,
        "base_url": profile.base_url,
        "api_key": profile.api_key,
        "models": profile.models,
        "soft_timeout_s": profile.soft_timeouts,
        "max_tokens": profile.max_tokens,
        "extra_body": profile.extra_body,
    }


def _tier_text_map(data: dict[str, Any], suffix: str) -> dict[str, str]:
    nested = data.get("models")
    values = nested if isinstance(nested, dict) else data
    result: dict[str, str] = {}
    for tier in ("fast", "mid", "deep"):
        value = values.get(tier) or values.get(f"{tier}_{suffix}")
        if value:
            result[tier] = _text(value, f"models.{tier}", MODEL_TEXT_LIMIT)
    return result


def _tier_int_map(
    raw: object,
    *,
    default: dict[str, int],
    field: str,
    minimum: int,
    maximum: int,
) -> dict[str, int]:
    if raw in (None, ""):
        return dict(default)
    if isinstance(raw, int | float):
        value = _bounded_int(raw, field, minimum=minimum, maximum=maximum)
        return {"fast": value, "mid": value, "deep": value}
    if not isinstance(raw, dict):
        raise ValueError(f"{field} must be a number or object")
    result = dict(default)
    for tier in ("fast", "mid", "deep"):
        if tier in raw:
            result[tier] = _bounded_int(
                raw[tier], f"{field}.{tier}", minimum=minimum, maximum=maximum
            )
    return result


def _tier_object_map(raw: object, field: str) -> dict[str, dict[str, Any]]:
    if raw in (None, ""):
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"{field} must be an object")
    result: dict[str, dict[str, Any]] = {}
    for tier in ("fast", "mid", "deep"):
        value = raw.get(tier) or raw.get(f"{tier}_extra_body")
        if value is None:
            continue
        if not isinstance(value, dict):
            raise ValueError(f"{field}.{tier} must be an object")
        result[tier] = value
    return result


def _text(value: object, field: str, limit: int) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field} is required")
    if len(text) > limit:
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


def _is_retryable(err: LLMGatewayError) -> bool:
    if isinstance(err, LLMGatewayConnectionError | LLMGatewayAuthError):
        return True
    if isinstance(err, LLMGatewayHTTPError):
        return err.status == HTTPStatus.TOO_MANY_REQUESTS or err.status >= 500
    return False
