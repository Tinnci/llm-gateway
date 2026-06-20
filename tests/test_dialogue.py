"""Tests for pending dialogue-state resolution."""

from __future__ import annotations

from custom_components.llm_gateway.capabilities import decide_route
from custom_components.llm_gateway.dialogue import (
    DialogueFrame,
    DialogueFrameStack,
    dialogue_frame_from_route,
    pending_task_from_route,
    resolve_dialogue_transaction,
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


def test_dialogue_frame_stack_fills_weather_location_referent() -> None:
    route = decide_route("明天的天气怎么样？")
    frame = dialogue_frame_from_route("turn-1", route)
    stack = DialogueFrameStack()
    assert frame is not None
    stack.push(frame)

    transaction = resolve_dialogue_transaction("上海静安。", stack)

    assert transaction.relation == "slot_fill"
    assert transaction.target_frame is frame
    assert transaction.slot_updates == {"location_hint": "上海静安"}
    assert transaction.effective_text == "上海静安明天的天气怎么样？"
    assert stack.active_frame() is None


def test_dialogue_frame_stack_suspends_weather_for_high_confidence_new_task() -> None:
    route = decide_route("明天的天气怎么样？")
    frame = dialogue_frame_from_route("turn-1", route)
    stack = DialogueFrameStack()
    assert frame is not None
    stack.push(frame)

    transaction = resolve_dialogue_transaction(
        "Do you know who is Virginia Hope?",
        stack,
    )

    assert transaction.relation == "new_task"
    assert transaction.suspended_frame is frame
    assert transaction.prompt == ""
    assert transaction.interaction_state == "classifying"
    assert frame.status == "suspended"
    assert stack.active_frame() is None


def test_dialogue_frame_stack_keeps_search_permission_as_followup() -> None:
    route = decide_route("明天的天气怎么样？")
    frame = dialogue_frame_from_route("turn-1", route)
    stack = DialogueFrameStack()
    assert frame is not None
    stack.push(frame)

    transaction = resolve_dialogue_transaction("搜索一下。", stack)

    assert transaction.relation == "permission"
    assert transaction.slot_updates == {"search_allowed": True}
    assert transaction.suspended_frame is None
    assert stack.active_frame() is frame


def test_dialogue_frame_stack_confirms_top_device_candidate() -> None:
    frame = _device_frame()
    stack = DialogueFrameStack([frame])

    transaction = resolve_dialogue_transaction("对。", stack)

    assert transaction.relation == "slot_fill"
    assert transaction.slot_updates["target_device"]["id"] == "light.devcea_1055"
    assert transaction.effective_text == "打开已确认的宜家麦希瑟E27 1055lm智能球泡灯 灯"
    assert stack.active_frame() is None


def test_dialogue_frame_stack_selects_device_candidate_by_name_fragment() -> None:
    frame = _device_frame()
    stack = DialogueFrameStack([frame])

    transaction = resolve_dialogue_transaction("宜家的那个", stack)

    assert transaction.relation == "slot_fill"
    assert transaction.slot_updates["target_device"]["id"] == "light.devcea_1055"
    assert transaction.effective_text == "打开已确认的宜家麦希瑟E27 1055lm智能球泡灯 灯"


def test_dialogue_frame_stack_selects_device_candidate_by_ordinal() -> None:
    frame = _device_frame()
    stack = DialogueFrameStack([frame])

    transaction = resolve_dialogue_transaction("第二个", stack)

    assert transaction.relation == "slot_fill"
    assert transaction.slot_updates["target_device"]["id"] == "light.monitor"
    assert transaction.effective_text == "打开已确认的Yeelight 显示器挂灯 灯"


def test_dialogue_frame_stack_suspends_device_frame_for_new_person_task() -> None:
    frame = _device_frame()
    stack = DialogueFrameStack([frame])

    transaction = resolve_dialogue_transaction(
        "Do you know who is Virginia Hope?", stack
    )

    assert transaction.relation == "new_task"
    assert transaction.suspended_frame is frame
    assert frame.status == "suspended"
    assert stack.active_frame() is None


def _device_frame() -> DialogueFrame:
    return DialogueFrame(
        id="turn-1:target_device",
        frame_type="home_control",
        operation="turn_on",
        status="awaiting_confirmation",
        missing_referents=("target_device",),
        candidates=(
            {
                "id": "light.devcea_1055",
                "name": "宜家麦希瑟E27 1055lm智能球泡灯 灯",
                "score": 0.88,
                "evidence": ["numeric_match:1055"],
            },
            {
                "id": "light.monitor",
                "name": "Yeelight 显示器挂灯 灯",
                "score": 0.47,
                "evidence": ["domain_match:light"],
            },
        ),
        last_prompt="你是说宜家 1055lm 那个灯吗？",
    )
