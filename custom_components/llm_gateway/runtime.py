"""Runtime data for the LLM Gateway config entry."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from homeassistant.components import persistent_notification
from homeassistant.util import ulid

from .api import LLMGatewayClient, LLMGatewayError
from .const import DOMAIN, LOGGER
from .providers import ProviderSelector, async_chat_completion_with_fallback

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    import aiohttp
    from homeassistant.core import HomeAssistant

    from .feedback import VoiceFeedbackStore
    from .first_response_audio import FirstResponsePlayer
    from .memory import VoiceMemory
    from .router import ModelRoute
    from .traces import TraceStore
    from .voice_runs import VoiceRunRecorder


@dataclass(slots=True)
class DeepTaskRecord:
    """A queued/running/completed deep-model task."""

    id: str
    request: str
    model: str
    status: str = "queued"
    result: str | None = None
    error: str | None = None
    provider: dict[str, Any] | None = None
    provider_attempts: list[dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


@dataclass(slots=True)
class LLMGatewayRuntimeData:
    """Runtime objects shared by Gateway platforms."""

    client: LLMGatewayClient
    session: aiohttp.ClientSession
    memory: VoiceMemory
    deep_tasks: DeepTaskManager
    trace_store: TraceStore
    feedback: VoiceFeedbackStore
    first_response_player: FirstResponsePlayer
    provider_selector: ProviderSelector
    voice_runs: VoiceRunRecorder


class DeepTaskManager:
    """Run deep-model tasks outside the voice critical path."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: LLMGatewayClient,
        session: aiohttp.ClientSession,
        options_getter: Callable[[], Mapping[str, Any]],
        provider_selector: ProviderSelector,
    ) -> None:
        self._hass = hass
        self._client = client
        self._session = session
        self._options_getter = options_getter
        self._provider_selector = provider_selector
        self.records: dict[str, DeepTaskRecord] = {}

    def submit(
        self,
        *,
        route: ModelRoute,
        messages: list[dict[str, Any]],
        user_text: str,
        temperature: float,
        top_p: float,
    ) -> str:
        """Submit a deep-model task and return its id."""
        task_id = ulid.ulid_now()
        self.records[task_id] = DeepTaskRecord(
            id=task_id, request=user_text, model=route.model
        )
        self._hass.async_create_task(
            self._async_run(task_id, route, messages, temperature, top_p),
            name=f"{DOMAIN}_deep_task_{task_id}",
        )
        return task_id

    def snapshot(self) -> list[dict[str, Any]]:
        """Return task records for the Voice Harness panel."""
        return [
            {
                "id": record.id,
                "request": record.request,
                "model": record.model,
                "status": record.status,
                "result": record.result,
                "error": record.error,
                "provider": record.provider,
                "provider_attempts": record.provider_attempts,
                "created_at": record.created_at,
            }
            for record in sorted(
                self.records.values(), key=lambda item: item.created_at, reverse=True
            )
        ]

    async def _async_run(
        self,
        task_id: str,
        route: ModelRoute,
        messages: list[dict[str, Any]],
        temperature: float,
        top_p: float,
    ) -> None:
        record = self.records[task_id]
        record.status = "running"
        try:
            result = await async_chat_completion_with_fallback(
                session=self._session,
                primary_client=self._client,
                route=route,
                options=dict(self._options_getter()),
                messages=messages,
                tools=None,
                tool_choice=None,
                temperature=temperature,
                top_p=top_p,
                selector=self._provider_selector,
                processing_cues=False,
            )
            message = result.message
        except LLMGatewayError as err:
            record.status = "error"
            record.error = str(err)
            LOGGER.warning("Deep task failed task_id=%s error=%s", task_id, err)
            persistent_notification.async_create(
                self._hass,
                f"深度分析任务失败：{err}",
                title="LLM Gateway 深度任务",
                notification_id=f"{DOMAIN}_{task_id}",
            )
            return

        record.status = "complete"
        record.provider = result.provider
        record.provider_attempts = result.attempts
        record.model = str(result.provider.get("model") or record.model)
        record.result = str(message.get("content") or "").strip()
        persistent_notification.async_create(
            self._hass,
            record.result or "深度分析完成，但模型没有返回正文。",
            title="LLM Gateway 深度任务完成",
            notification_id=f"{DOMAIN}_{task_id}",
        )
