"""Tests for pending dialogue-state resolution."""

from __future__ import annotations

from custom_components.llm_gateway.capabilities import decide_route
from custom_components.llm_gateway.dialogue import (
    pending_task_from_route,
    resolve_pending_task,
)


def test_weather_location_followup_fills_pending_slot() -> None:
    route = decide_route("明天的天气怎么样？")
    pending = pending_task_from_route("turn-1", route)

    resolution = resolve_pending_task("上海静安。", pending)

    assert resolution.relation == "slot_fill"
    assert resolution.slot_updates == {"location_hint": "上海静安"}
    assert resolution.interaction_state == "slot_filled"
    assert resolution.effective_text == "上海静安明天的天气怎么样？"


def test_search_permission_does_not_become_weather_query_without_location() -> None:
    route = decide_route("明天的天气怎么样？")
    pending = pending_task_from_route("turn-1", route)

    resolution = resolve_pending_task("搜索一下。", pending)

    assert resolution.relation == "permission"
    assert resolution.slot_updates == {"search_allowed": True}
    assert resolution.effective_text == ""
    assert "哪个地方" in resolution.prompt


def test_pending_task_can_be_cancelled() -> None:
    route = decide_route("明天的天气怎么样？")
    pending = pending_task_from_route("turn-1", route)

    resolution = resolve_pending_task("不用了", pending)

    assert resolution.relation == "cancellation"
    assert resolution.interaction_state == "cancelled"
    assert "取消" in resolution.prompt


def test_pending_task_expiry_is_explicit() -> None:
    route = decide_route("明天的天气怎么样？")
    pending = pending_task_from_route("turn-1", route)
    assert pending is not None
    pending.turns_seen = pending.expires_after_turns

    resolution = resolve_pending_task("随便", pending)

    assert resolution.relation == "unresolved"
    assert resolution.expired is True
