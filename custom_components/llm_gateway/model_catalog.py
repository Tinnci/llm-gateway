"""Persistent, validator-aware cache of provider model catalogs.

Model lists are a "cache plus conditional request" problem, not a
"download every time" problem: the panel's refresh button should feel
instant and a flaky provider must not blank the picker. The store keeps
per-provider validators (ETag / Last-Modified) so revalidation downloads
nothing on 304, and serves the stale catalog when the provider is
unreachable — facts persist, freshness is best-effort.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.storage import Store

from .api import (
    LLMGatewayAuthError,
    LLMGatewayCatalogNotModifiedError,
    LLMGatewayClient,
    LLMGatewayError,
    LLMGatewayQuotaExhaustedError,
)
from .const import DOMAIN, LOGGER

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

STORAGE_KEY = f"{DOMAIN}.model_catalog"
STORAGE_VERSION = 1

# Revalidate at most every four hours (mirrors pi's remote catalog cadence).
CATALOG_TTL_S = 4 * 60 * 60

# Bound persisted providers so long-lived instances cannot grow the file.
_MAX_PROVIDERS = 8


@dataclass(slots=True)
class CatalogLookup:
    """One resolved catalog with how it was obtained."""

    models: list[str]
    source: str  # "cache" | "revalidated" | "fetched"
    stale: bool = False


def _normalize_base_url(base_url: str) -> str:
    return (base_url or "").strip().rstrip("/")


class ModelCatalogCache:
    """Per-provider model-id catalog backed by HA Store."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._data: dict[str, dict[str, Any]] = {}
        self._loaded = False

    async def _async_load(self) -> None:
        if self._loaded:
            return
        stored = await self._store.async_load()
        self._data = stored if isinstance(stored, dict) else {}
        self._loaded = True

    async def _async_save(self) -> None:
        await self._store.async_save(self._data)

    @staticmethod
    def _entry_valid(entry: dict[str, Any] | None, now: float) -> bool:
        if not entry:
            return False
        checked_at = entry.get("checked_at")
        models = entry.get("models")
        return (
            isinstance(checked_at, (int, float))
            and isinstance(models, list)
            and bool(models)
            and now - checked_at < CATALOG_TTL_S
        )

    def _prune_locked(self, keep_key: str) -> None:
        """Keep the freshest few providers; always retain the one just used."""
        while len(self._data) > _MAX_PROVIDERS:
            oldest_key = min(
                (key for key in self._data if key != keep_key),
                key=lambda key: self._data[key].get("checked_at") or 0.0,
                default=None,
            )
            if oldest_key is None:
                break
            del self._data[oldest_key]

    async def async_get(
        self,
        *,
        client: LLMGatewayClient,
        base_url: str,
        force: bool = False,
    ) -> CatalogLookup:
        """Return provider model ids via TTL cache + conditional requests."""
        await self._async_load()
        key = _normalize_base_url(base_url)
        entry = self._data.get(key)
        now = time.time()

        if not force and self._entry_valid(entry, now):
            return CatalogLookup(
                models=list(entry["models"]),  # type: ignore[arg-type]
                source="cache",
            )

        try:
            fetch = await client.async_list_models_conditional(
                etag=(entry or {}).get("etag"),
                last_modified=(entry or {}).get("last_modified"),
            )
        except LLMGatewayCatalogNotModifiedError as err:
            # 304: nothing downloaded; only freshness needs bumping.
            if entry is None:
                raise LLMGatewayError(
                    "Catalog revalidated without a cached copy"
                ) from err
            entry["checked_at"] = now
            if err.etag:
                entry["etag"] = err.etag
            if err.last_modified:
                entry["last_modified"] = err.last_modified
            self._prune_locked(key)
            await self._async_save()
            return CatalogLookup(models=list(entry["models"]), source="revalidated")
        except LLMGatewayAuthError:
            raise
        except LLMGatewayQuotaExhaustedError:
            raise
        except LLMGatewayError:
            if entry and entry.get("models"):
                LOGGER.warning(
                    "Model catalog refresh failed for %s; serving stale cache",
                    key,
                )
                return CatalogLookup(
                    models=list(entry["models"]),
                    source="cache",
                    stale=True,
                )
            raise

        self._data[key] = {
            "models": fetch.models,
            "etag": fetch.etag,
            "last_modified": fetch.last_modified,
            "checked_at": now,
        }
        self._prune_locked(key)
        await self._async_save()
        return CatalogLookup(models=fetch.models, source="fetched")


def model_catalog_for(hass: HomeAssistant) -> ModelCatalogCache:
    """Return the per-hass catalog singleton."""
    key = f"{DOMAIN}_model_catalog"
    cache = hass.data.get(key)
    if not isinstance(cache, ModelCatalogCache):
        cache = ModelCatalogCache(hass)
        hass.data[key] = cache
    return cache
