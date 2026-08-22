"""Tests for typed, policy-guarded HA action plans."""

from custom_components.llm_gateway.action_plan import ActionPlan, ActionPlanExecutor


async def test_action_plan_executes_when_state_condition_matches(hass) -> None:
    calls = []
    hass.states.async_set("binary_sensor.window", "on")

    async def turn_on(call):
        calls.append(call.data)

    hass.services.async_register("light", "turn_on", turn_on)
    plan = ActionPlan.from_payload(
        {
            "reads": [{"alias": "window", "entity_id": "binary_sensor.window"}],
            "conditions": [{"read": "window", "equals": "on"}],
            "actions": [
                {
                    "domain": "light",
                    "service": "turn_on",
                    "entity_id": "light.corridor",
                    "data": {"rgb_color": [255, 255, 0]},
                }
            ],
            "success_speech": "已将走廊灯设为黄色。",
        }
    )

    result = await ActionPlanExecutor().async_execute(hass, plan)

    assert result.status == "executed"
    assert calls == [
        {"entity_id": "light.corridor", "rgb_color": [255, 255, 0]}
    ]
    assert {item["stage"] for item in result.policy} == {
        "before_plan",
        "before_execute",
        "after_execute",
        "before_playback",
    }


async def test_action_plan_dry_run_never_calls_service(hass) -> None:
    calls = []

    async def turn_off(call):
        calls.append(call)

    hass.services.async_register("light", "turn_off", turn_off)
    plan = ActionPlan.from_payload(
        {
            "actions": [
                {
                    "domain": "light",
                    "service": "turn_off",
                    "entity_id": "light.all",
                }
            ]
        }
    )

    result = await ActionPlanExecutor().async_execute(hass, plan, dry_run=True)

    assert result.status == "dry_run"
    assert calls == []
    assert result.actions[0]["entity_id"] == "light.all"


async def test_action_plan_blocks_high_risk_or_unbounded_service(hass) -> None:
    plan = ActionPlan.from_payload(
        {
            "actions": [
                {"domain": "lock", "service": "unlock", "entity_id": "lock.front"}
            ]
        }
    )

    result = await ActionPlanExecutor().async_execute(hass, plan)

    assert result.status == "blocked"
    assert result.reason == "service_not_allowed"


async def test_action_plan_reports_total_execution_failure_as_error(hass) -> None:
    plan = ActionPlan.from_payload(
        {
            "actions": [
                {
                    "domain": "light",
                    "service": "turn_on",
                    "entity_id": "light.missing",
                }
            ]
        }
    )

    result = await ActionPlanExecutor().async_execute(hass, plan)

    assert result.status == "error"
    assert result.reason == "execution_failed"
    assert result.actions == ()
    assert result.failed_actions[0]["entity_id"] == "light.missing"
